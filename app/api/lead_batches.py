"""Local lead-scoring runs. Background processing is owned by one API process."""
import asyncio
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from core.config import load_evaluation_settings
from models.lead_batch import BatchRequest, ExplanationRequest, TargetingRequest
from models.lead_lists import AppendLeadList, CreateLeadList, EditLeadList, PeopleSearchRequest, ScoreLeadList
from scoring import repository
from scoring.batch import create_target, execute_run, new_run
from scoring.explanations import explain
from scoring.normalizer import selected_people
from scoring.people_search import search_page, search_people
from scoring.lead_lists import append_members, create_list, edit_list

router = APIRouter(prefix='/v1/lead-scoring', tags=['Batch lead scoring'])
EXPLANATION_LOCK = asyncio.Lock()


def configured():
    settings = load_evaluation_settings()
    if settings.issues:
        raise HTTPException(503, 'Configure the backend LLM provider before using AI scoring.')
    return settings


def require_run(identifier):
    run = repository.get('run', identifier)
    if run is None:
        raise HTTPException(404, 'This scoring run was not found.')
    return run


def require_list(identifier):
    document = repository.get('lead_list', identifier)
    if document is None:
        raise HTTPException(404, 'This lead list was not found.')
    return document


@router.post('/searches')
async def people_search(request: PeopleSearchRequest):
    try:
        document, error = await search_people(request, configured())
    except (OSError, KeyError, TypeError, ValueError):
        raise HTTPException(503, 'The local directory could not be searched. Refresh the page and try again.')
    if document is None:
        raise HTTPException(422, error)
    return search_page(document)


@router.get('/searches/{search_id}')
def read_search(search_id: str, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50),
                pool: Literal['confirmed', 'review'] = 'confirmed'):
    document = repository.get('search', search_id)
    if document is None:
        raise HTTPException(404, 'This search was not found. Search again.')
    return search_page(document, offset, limit, pool)


@router.get('/lists')
def lists():
    return repository.list_lead_lists()


@router.post('/lists', status_code=201)
def save_list(request: CreateLeadList):
    try:
        return create_list(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (OSError, KeyError, TypeError):
        raise HTTPException(503, 'The list could not be saved from the local directory.')


@router.get('/lists/{list_id}')
def read_list(list_id: str):
    return require_list(list_id)


@router.post('/lists/{list_id}/members')
def add_members(list_id: str, request: AppendLeadList):
    try:
        return append_members(list_id, request)
    except KeyError:
        raise HTTPException(404, 'This lead list was not found.')
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (OSError, TypeError):
        raise HTTPException(503, 'The local directory could not be read.')


@router.post('/lists/{list_id}/edit')
def update_list(list_id: str, request: EditLeadList):
    try:
        return edit_list(list_id, request)
    except KeyError:
        raise HTTPException(404, 'This lead list was not found.')
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post('/lists/{list_id}/score', status_code=202)
def score_list(list_id: str, request: ScoreLeadList, background: BackgroundTasks):
    settings = configured()
    override = repository.get('target', request.targeting_id) if request.targeting_id else None
    if request.targeting_id and override is None:
        raise HTTPException(404, 'Apply your targeting again before scoring.')
    runs = []

    def capture(document):
        if not document['people']:
            raise ValueError('Add people to this list before scoring.')
        target = override or document.get('targeting')
        if target is None:
            raise ValueError('Apply scoring targeting before scoring this list.')
        source = {'id': document['id'], 'name': document['name'], 'version': document['version'], 'search_id': document.get('search_id')}
        run = new_run(target, document['people'], settings, source_list=source, persist=False)
        runs.append(run)
        document['latest_run_id'] = run['id']

    try:
        repository.mutate_list(list_id, request.expected_version, capture)
    except KeyError:
        raise HTTPException(404, 'This lead list was not found.')
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    run = runs[0]
    repository.save('run', run)
    background.add_task(execute_run, run, settings)
    return run


@router.post('/targeting')
async def targeting(request: TargetingRequest):
    target, error = await create_target(request, configured())
    if target is None:
        raise HTTPException(422, error)
    return target


@router.post('/runs', status_code=202)
def start_run(request: BatchRequest, background: BackgroundTasks):
    settings = configured()
    target = repository.get('target', request.targeting_id)
    if target is None:
        raise HTTPException(404, 'Apply your targeting again before scoring.')
    try:
        people = selected_people(request.lead_ids)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (OSError, KeyError, TypeError):
        raise HTTPException(503, 'The local directory could not be read.')
    run = new_run(target, people, settings)
    background.add_task(execute_run, run, settings)
    return run


@router.get('/runs')
def history():
    return repository.list_runs()


@router.get('/runs/{run_id}')
def read_run(run_id: str):
    return require_run(run_id)


@router.post('/runs/{run_id}/retry', status_code=202)
def retry_failed(run_id: str, background: BackgroundTasks):
    settings = configured()
    previous = require_run(run_id)
    if previous['status'] in {'queued', 'running'}:
        raise HTTPException(409, 'Wait for this run to finish before retrying.')
    people = [item['person'] for item in previous['results'] if item['status'] == 'failed']
    if not people:
        raise HTTPException(409, 'There are no failed people to retry.')
    run = new_run(previous['targeting'], people, settings, source_list=previous.get('source_list'))
    run['retry_of'] = previous['id']
    repository.save('run', run)
    background.add_task(execute_run, run, settings)
    return run


@router.post('/runs/{run_id}/explanation')
async def explanation(run_id: str, request: ExplanationRequest):
    async with EXPLANATION_LOCK:
        run = require_run(run_id)
        if run['status'] in {'queued', 'running'}:
            raise HTTPException(409, 'Wait for scoring to finish before requesting an explanation.')
        item = next((r for r in run['results'] if r['person']['id'] == request.lead_id), None)
        if item is None:
            raise HTTPException(404, 'This person is not in the scoring run.')
        if item['status'] not in {'matched', 'not_selected'}:
            raise HTTPException(409, 'Retry scoring this person before requesting an explanation.')
        if item['explanation'] is None or item['explanation']['source'] == 'template':
            item['explanation'], trace = await explain(run, item, configured())
            run['traces'].append(trace)
            repository.save('run', run)
        return run
