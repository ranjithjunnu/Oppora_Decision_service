"""LLM-authored inclusion and scores; code validates and records decisions."""
import asyncio
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

from models.lead_batch import LeadFilterResult, OpporaLeadFilterResult
from . import ledger, repository
from .jev_scoring import VERSION as JEV_VERSION, judge_lead
from .normalizer import missing_facts
from .trace import invoke, now

PROMPTS = Path(__file__).parent / 'prompts'
# v1: our adaptation (instructions as system prompt, leads as JSON).
# v2: Oppora's observed format (one text message with a pipe table), the default.
PROMPT_V1 = (PROMPTS / 'lead_filter_v1.txt').read_text(encoding='utf-8')
PROMPT_V2 = (PROMPTS / 'lead_filter_oppora_v2.txt').read_text(encoding='utf-8')
V2_SYSTEM = 'Answer with a single JSON object and no prose.'
SLOTS = asyncio.Semaphore(2)
EXCLUDED_FROM_PROMPT = {'company_id', 'company_name', 'company_description', 'source', 'search_notes', 'match_state'}
ROW_FIELDS = ('title', 'location', 'department', 'management_level', 'experience_years', 'headline', 'skills', 'summary')


def listed(values):
    return '[' + ', '.join(repr(value) for value in values) + ']'


def experience_text(filters):
    low, high = filters['experience_min'], filters['experience_max']
    if low is None and high is None:
        return None
    if high is None:
        return f'at least {low:g} years'
    if low is None:
        return f'at most {high:g} years'
    return f'{low:g}-{high:g} years'


def row_aliases(chunk):
    """Oppora rows use plain numeric lead ids; ids such as "li-123:0" get cut at the colon by the model."""
    return {str(position): item['person']['id'] for position, item in enumerate(chunk, start=1)}


def oppora_prompt(company, objective, filters, number, chunk, aliases):
    """Rebuild the user message Oppora's lead_scoring sends (seen in its AI Admin traces)."""
    alias_of = {real: alias for alias, real in aliases.items()}
    applied = [(name, listed(filters[key])) for name, key in (
        ('title', 'titles'), ('departments', 'departments'), ('management_level', 'management_levels'),
        ('country', 'countries'), ('location', 'locations'), ('exclude_locations', 'exclude_locations'))
        if filters[key]]
    if experience_text(filters):
        applied.append(('experience', experience_text(filters)))
    rows = []
    for item in chunk:
        person = item['person']
        values = {field: '' if person.get(field) is None else str(person[field]) for field in ROW_FIELDS}
        values['summary'] = values['summary'][:500]
        rows.append(f"{alias_of[person['id']]} | {person['name']} | " + ' | '.join(f'{field}={values[field]}' for field in ROW_FIELDS))
    text = PROMPT_V2
    for token, value in {
        'COMPANY': company, 'OBJECTIVE': objective or 'None',
        'APPLIED_FILTERS': ', '.join(f'{name}: {value}' for name, value in applied) or 'None',
        'BATCH': str(number), 'ROWS': '\n'.join(rows),
        'DEPARTMENTS': listed(filters['departments']) if filters['departments'] else 'Not specified',
        'MANAGEMENT_LEVELS': listed(filters['management_levels']) if filters['management_levels'] else 'Not specified',
        'COUNTRY': listed(filters['countries']) if filters['countries'] else 'Not specified',
        'LOCATION': listed(filters['locations']) if filters['locations'] else 'Not specified',
        'EXCLUDE_LOCATIONS': listed(filters['exclude_locations']) if filters['exclude_locations'] else 'None',
        'TITLE': listed(filters['titles']) if filters['titles'] else 'Not specified',
        'EXPERIENCE': experience_text(filters) or 'Not specified',
    }.items():
        text = text.replace('[[' + token + ']]', value)
    return text


async def create_target(request, settings):
    from .people_search import VERSION, interpret
    interpreted, trace, traces, error = await interpret(request, settings)
    # Record every call, including failed ones, before deciding the outcome.
    for item in traces:
        ledger.record_trace(settings, item, 'search_interpretation', links={'source': 'targeting'})
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


def new_run(target, people, settings, source_list=None, persist=True, decision_model='llm', jev_settings=None):
    # The decision model is chosen per run: the LLM (Oppora's way) or Jev (typed questions).
    jev = jev_settings if decision_model == 'jev' else None
    provider, model = (jev.provider, jev.model) if jev else (settings.provider, settings.model)
    version = JEV_VERSION if jev else settings.lead_prompt
    fingerprint = hashlib.sha256(json.dumps({'target': target['filters'], 'objective': target['objective'],
                                             'people': people, 'prompt_version': version,
                                             'provider': provider, 'model': model},
                                            sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    run = {'id': 'run_' + uuid4().hex, 'created_at': now(), 'status': 'queued',
           'targeting_id': target['id'], 'targeting_description': target['description'],
           'targeting': target, 'model': model, 'provider': provider, 'decision_model': 'jev' if jev else 'llm',
           'prompt_version': version, 'input_fingerprint': fingerprint,
           'total': len(people), 'processed': 0, 'matched': 0, 'failed': 0,
           'results': [{'person': person, 'status': 'pending', 'score': None, 'error': None,
                        'missing_facts': missing_facts(person), 'call_id': None, 'explanation': None} for person in people],
           'traces': [], 'explanations': {}, 'source_list': source_list}
    if persist:
        repository.save('run', run)
    return run


def company_batches(run, size):
    """Oppora sends one call per company; companies larger than `size` are split into batches."""
    groups = defaultdict(list)
    for item in run['results']:
        groups[item['person']['company_id']].append(item)
    for items in groups.values():
        for number, offset in enumerate(range(0, len(items), size), start=1):
            yield number, items[offset:offset + size]


async def score_batch(run, settings, number, chunk):
    first = chunk[0]['person']
    version = run.get('prompt_version', 'oppora-filter-v1')
    filters, objective = run['targeting']['filters'], run['targeting']['objective'] or None
    aliases = None
    if version == 'oppora-filter-v2':
        aliases = row_aliases(chunk)
        output, trace = await invoke(settings, 'Filter and score people', version, V2_SYSTEM, None, OpporaLeadFilterResult,
                                     user_content=oppora_prompt(first['company_name'], objective, filters, number, chunk, aliases))
        trace['row_ids'] = aliases
    else:
        inputs = {'company': {'name': first['company_name'], 'description': first['company_description']},
                  'batch': number, 'filters': filters, 'main_objective': objective,
                  'leads': [{key: value for key, value in item['person'].items() if key not in EXCLUDED_FROM_PROMPT}
                            for item in chunk]}
        output, trace = await invoke(settings, 'Filter and score people', version, PROMPT_V1, inputs, LeadFilterResult)
    scores, tiers = {}, {}
    if output is not None:
        ids = [lead.lead_id for lead in output.scored_leads]
        allowed = set(aliases) if aliases else {item['person']['id'] for item in chunk}
        if len(ids) != len(set(ids)) or not set(ids) <= allowed:
            trace.update(status='failed', error='The model returned duplicate IDs or IDs outside this batch.')
        else:
            real = (lambda lead_id: aliases[lead_id]) if aliases else (lambda lead_id: lead_id)
            scores = {real(lead.lead_id): lead.score for lead in output.scored_leads}
            tiers = {real(lead.lead_id): getattr(lead, 'priority_tier', None) for lead in output.scored_leads}
    for item in chunk:
        identifier = item['person']['id']
        if trace['status'] == 'failed':
            item.update(status='failed', error=trace['error'])
        elif identifier in scores:
            item.update(status='matched', score=scores[identifier], priority_tier=tiers.get(identifier))
        else:
            item['status'] = 'not_selected'
        item['call_id'] = trace['id']
    failed = trace['status'] == 'failed'
    ledger.record_trace(settings, trace, 'lead_filter_score', items_in=len(chunk),
                        decisions={'selected': 0 if failed else len(scores),
                                   'not_selected': 0 if failed else len(chunk) - len(scores),
                                   'failed': len(chunk) if failed else 0},
                        links={'run_id': run['id'], 'company_id': first['company_id'], 'batch': number})
    run['traces'].append(trace)
    update_counts(run)
    repository.save('run', run)


async def score_lead_with_jev(run, jev_settings, item):
    decision, trace = await judge_lead(jev_settings, item['person'], run['targeting'])
    if decision is None:
        item.update(status='failed', error=trace['error'])
    elif decision['selected']:
        item.update(status='matched', score=decision['score'], jev=decision)
    else:
        item.update(status='not_selected', jev=decision)
    item['call_id'] = trace['id']
    ledger.record_trace(jev_settings, trace, 'lead_filter_score', items_in=1,
                        decisions={'selected': int(bool(decision and decision['selected'])),
                                   'not_selected': int(bool(decision and not decision['selected'])),
                                   'failed': int(decision is None)},
                        links={'run_id': run['id'], 'lead_id': item['person']['id']})
    run['traces'].append(trace)
    update_counts(run)


async def execute_jev_run(run, jev_settings):
    """One Jev query per lead (Jev answers typed questions about one state at a time)."""
    run['batching'] = {'per': 'lead', 'concurrency': jev_settings.concurrency,
                       'match_threshold': jev_settings.match_threshold}
    limit = asyncio.Semaphore(jev_settings.concurrency)
    done = 0

    async def bounded(item):
        nonlocal done
        async with limit:
            try:
                await score_lead_with_jev(run, jev_settings, item)
            except Exception:
                if item['status'] == 'pending':
                    item.update(status='failed', error='Processing this lead failed. Retry it.')
                update_counts(run)
            done += 1
            if done % 10 == 0:
                repository.save('run', run)

    await asyncio.gather(*(bounded(item) for item in run['results']))


async def execute_run(run, settings, jev_settings=None):
    if run.get('decision_model') == 'jev':
        async with SLOTS:
            run['status'] = 'running'
            repository.save('run', run)
            try:
                await execute_jev_run(run, jev_settings)
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
        return
    async with SLOTS:
        run['status'] = 'running'
        run['batching'] = {'batch_size': settings.lead_batch_size, 'concurrency': settings.lead_batch_concurrency}
        repository.save('run', run)
        limit = asyncio.Semaphore(settings.lead_batch_concurrency)

        async def bounded(number, chunk):
            async with limit:
                try:
                    await score_batch(run, settings, number, chunk)
                except Exception:
                    # One broken batch must not stop the others; its people stay retryable.
                    for item in chunk:
                        if item['status'] == 'pending':
                            item.update(status='failed', error='Processing this batch failed. Retry these people.')
                    update_counts(run)

        try:
            await asyncio.gather(*(bounded(number, chunk)
                                   for number, chunk in company_batches(run, settings.lead_batch_size)))
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
