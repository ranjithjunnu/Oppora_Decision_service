"""LLM-authored inclusion and scores; code validates and records decisions."""
import asyncio
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

from models.lead_batch import LeadFilterResult
from . import repository
from .normalizer import missing_facts
from .trace import invoke, now

PROMPT_VERSION = 'oppora-filter-v1'
PROMPT = (Path(__file__).parent / 'prompts' / 'lead_filter_v1.txt').read_text(encoding='utf-8')
SLOTS = asyncio.Semaphore(2)


async def create_target(request, settings):
    from .people_search import VERSION, interpret
    interpreted, trace, traces, error = await interpret(request, settings)
    if interpreted is None:
        return None, error
    plan, filters, validation = interpreted
    if plan.company_names:
        return None, 'Use people search to choose the companies. Scoring targeting supports people roles, locations and explicit metadata requirements.'
    document = {'id': 'target_' + uuid4().hex, 'created_at': now(), 'description': request.description,
                'objective': request.objective.strip(), 'filters': filters,
                'prompt_version': VERSION, 'trace': trace, 'interpretation_traces': traces, 'validation': validation}
    repository.save('target', document)
    return document, None


def new_run(target, people, settings, source_list=None, persist=True):
    fingerprint = hashlib.sha256(json.dumps({'target': target['filters'], 'objective': target['objective'],
                                             'people': people, 'prompt_version': PROMPT_VERSION,
                                             'provider': settings.provider, 'model': settings.model},
                                            sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    run = {'id': 'run_' + uuid4().hex, 'created_at': now(), 'status': 'queued',
           'targeting_id': target['id'], 'targeting_description': target['description'],
           'targeting': target, 'model': settings.model, 'provider': settings.provider,
           'prompt_version': PROMPT_VERSION, 'input_fingerprint': fingerprint,
           'total': len(people), 'processed': 0, 'matched': 0, 'failed': 0,
           'results': [{'person': person, 'status': 'pending', 'score': None, 'error': None,
                        'missing_facts': missing_facts(person), 'call_id': None, 'explanation': None} for person in people],
           'traces': [], 'explanations': {}, 'source_list': source_list}
    if persist:
        repository.save('run', run)
    return run


async def execute_run(run, settings):
    async with SLOTS:
        run['status'] = 'running'
        repository.save('run', run)
        groups = defaultdict(list)
        for item in run['results']:
            groups[item['person']['company_id']].append(item)
        try:
            for items in groups.values():
                for offset in range(0, len(items), 20):
                    chunk = items[offset:offset + 20]
                    first = chunk[0]['person']
                    inputs = {'company': {'name': first['company_name'], 'description': first['company_description']},
                              'filters': run['targeting']['filters'], 'main_objective': run['targeting']['objective'] or None,
                              'leads': [{key: value for key, value in item['person'].items()
                                         if key not in {'company_id', 'company_name', 'company_description', 'source', 'search_notes', 'match_state'}} for item in chunk]}
                    output, trace = await invoke(settings, 'Filter and score people', PROMPT_VERSION, PROMPT, inputs, LeadFilterResult)
                    scores = {}
                    if output is not None:
                        ids = [lead.lead_id for lead in output.scored_leads]
                        allowed = {item['person']['id'] for item in chunk}
                        if len(ids) != len(set(ids)) or not set(ids) <= allowed:
                            trace.update(status='failed', error='The model returned duplicate IDs or IDs outside this batch.')
                        else:
                            scores = {lead.lead_id: lead.score for lead in output.scored_leads}
                    for item in chunk:
                        identifier = item['person']['id']
                        if trace['status'] == 'failed':
                            item.update(status='failed', error=trace['error'])
                        elif identifier in scores:
                            item.update(status='matched', score=scores[identifier])
                        else:
                            item['status'] = 'not_selected'
                        item['call_id'] = trace['id']
                    run['traces'].append(trace)
                    update_counts(run)
                    repository.save('run', run)
            run['status'] = 'failed' if run['failed'] == run['total'] else 'partial' if run['failed'] else 'completed'
        except Exception:
            for item in run['results']:
                if item['status'] == 'pending':
                    item.update(status='failed', error='Processing was interrupted. Retry the remaining people.')
            update_counts(run)
            run['status'] = 'partial' if run['failed'] < run['total'] else 'failed'
        finally:
            run['finished_at'] = now()
            repository.save('run', run)


def update_counts(run):
    run['processed'] = sum(item['status'] != 'pending' for item in run['results'])
    run['matched'] = sum(item['status'] == 'matched' for item in run['results'])
    run['failed'] = sum(item['status'] == 'failed' for item in run['results'])
