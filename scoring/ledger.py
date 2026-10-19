"""AI call ledger and decision catalog: where decisions happen and what each LLM call cost.

Every LLM request records one ledger entry: its decision point, tokens, estimated cost,
latency and a small count of what it decided. Full prompts and outputs stay in the
run, search or target traces that own them; the ledger links to them by id.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from core.config import estimate_cost
from . import repository

# One entry per place a decision is made. `decided_by` says who makes it today;
# `jev_fit` is our current judgment of whether a bounded Jev decision could take it over.
DECISIONS = [
    {'id': 'search_interpretation', 'name': 'Understand a people search', 'decided_by': 'llm',
     'prompt_version': 'people-search-v2', 'code': 'scoring/people_search.py',
     'input': 'Free-text request, e.g. "HR directors in the United States"',
     'output': 'Filters (titles, countries, locations, departments, levels, experience), title variants, supporting quotes',
     'oppora_equivalent': 'prompt_to_filters / finder_agent',
     'jev_fit': 'partial', 'jev_note': 'Titles and variants are free text, so keep the LLM. Departments and levels from a fixed list could become bounded choices.'},
    {'id': 'lead_filter_score', 'name': 'Filter and score leads', 'decided_by': 'llm',
     'prompt_version': 'oppora-filter-v2 (v1 optional)', 'code': 'scoring/batch.py',
     'input': 'One company, the targeting filters and a batch of its people',
     'output': 'IDs of matching people with a 0–100 fit score; people left out are not selected',
     'oppora_equivalent': 'lead_scoring → LeadFilterResult (deepseek-flash)',
     'jev_fit': 'strong', 'jev_note': 'Highest-volume decision. Choose LLM or Jev per run. Jev answers small yes/no checks per lead (role, location, …) plus a fit level; code selects and computes the score.'},
    {'id': 'lead_explanation', 'name': 'Explain a recorded result', 'decided_by': 'llm',
     'prompt_version': 'lead-explanation-v1', 'code': 'scoring/explanations.py',
     'input': 'Filters, the recorded status and score, and the person facts',
     'output': 'Short assessment, verified quotes and missing facts',
     'oppora_equivalent': 'None observed',
     'jev_fit': 'keep_llm', 'jev_note': 'Free-text writing.'},
    {'id': 'criterion_judgment', 'name': 'Judge one ICP criterion', 'decided_by': 'llm',
     'prompt_version': 'llm-criterion-v2', 'code': 'scoring/llm.py (POST /v1/scores)',
     'input': 'Each semantic criterion with its source text and the seller context',
     'output': 'match / partial / miss / unknown with a verbatim quote',
     'oppora_equivalent': 'None; this is the criterion design ("LLM classifies, code computes")',
     'jev_fit': 'strong', 'jev_note': 'A 4-way typed choice. Jev returns no quotes, so evidence must be handled separately.'},
    {'id': 'icp_draft', 'name': 'Draft ICP criteria', 'decided_by': 'llm',
     'prompt_version': 'profile-draft-v1', 'code': 'app/api/scoring.py (POST /v1/profiles/draft)',
     'input': 'Free-text ideal-customer description',
     'output': 'Structured criteria profile or a list of issues',
     'oppora_equivalent': 'icp / icp_deep_pass',
     'jev_fit': 'keep_llm', 'jev_note': 'Open-ended structure generation.'},
    {'id': 'intent_classification', 'name': 'Classify a request (Decision Lab)', 'decided_by': 'llm',
     'prompt_version': 'gtm-intent-v1', 'code': 'evaluators/llm.py (POST /evaluate)',
     'input': 'One query and optional context',
     'output': 'One label from a fixed menu (6 GTM intents)',
     'oppora_equivalent': 'ask_ora:classify',
     'jev_fit': 'strong', 'jev_note': 'Single bounded choice; a direct Jev comparison case.'},
    {'id': 'interpretation_validation', 'name': 'Check the search interpretation', 'decided_by': 'code',
     'code': 'scoring/search_validation.py',
     'input': 'The LLM interpretation and the original request',
     'output': 'Keeps filters backed by a quote; drops department/level inferred only from a title',
     'oppora_equivalent': 'None observed', 'jev_fit': 'n/a'},
    {'id': 'candidate_retrieval', 'name': 'Find candidates in the directory', 'decided_by': 'code',
     'code': 'scoring/people_search.py',
     'input': 'Validated filters and title variants',
     'output': 'Confirmed people, plus a review pool when location is unknown',
     'oppora_equivalent': 'get_sales_leads_bulk_in_background (Oppora uses web search + LLM extraction)', 'jev_fit': 'n/a'},
    {'id': 'batch_validation', 'name': 'Check returned lead IDs', 'decided_by': 'code',
     'code': 'scoring/batch.py',
     'input': 'The LLM result for one batch',
     'output': 'Rejects duplicate or unknown IDs; marks the whole batch failed instead of guessing',
     'oppora_equivalent': 'Not visible', 'jev_fit': 'n/a'},
    {'id': 'criterion_scoring', 'name': 'Compute score, band and recommendation', 'decided_by': 'code',
     'code': 'scoring/service.py, scoring/policy.py',
     'input': 'Criterion outcomes and weights',
     'output': 'Fit, intent, priority, band, coverage and recommendation',
     'oppora_equivalent': 'None; Oppora lets the LLM write the score', 'jev_fit': 'n/a'},
]
DECISION_IDS = {item['id'] for item in DECISIONS}
RANGES = {'last_24_hours': timedelta(hours=24), 'last_7_days': timedelta(days=7), 'last_30_days': timedelta(days=30)}


def now():
    return datetime.now(timezone.utc).isoformat()


def record(settings, decision_point, purpose, prompt_version, *, status, error=None, latency_ms=None,
           input_tokens=None, output_tokens=None, cached_input_tokens=None, items_in=None,
           decisions=None, links=None, call_id=None, reasoning_tokens=None, model=None, cost_usd=None):
    """Store one model call (LLM or Jev). Ledger failures never break the scoring request."""
    is_jev = getattr(settings, 'provider', '') == 'typesafe'
    entry = {'id': call_id or 'call_' + uuid4().hex, 'created_at': now(), 'decision_point': decision_point,
             'purpose': purpose, 'prompt_version': prompt_version, 'provider': settings.provider,
             'model': model or settings.model, 'status': status, 'error': error, 'latency_ms': latency_ms,
             'input_tokens': input_tokens, 'cached_input_tokens': cached_input_tokens,
             'output_tokens': output_tokens, 'reasoning_tokens': reasoning_tokens,
             'thinking': getattr(settings, 'thinking', None),
             'estimated_cost_usd': cost_usd if is_jev else estimate_cost(settings, input_tokens, output_tokens, cached_input_tokens),
             'items_in': items_in, 'decisions': decisions or {}, 'links': links or {}}
    try:
        repository.record_llm_call(entry)
    except Exception:
        pass
    return entry


def record_trace(settings, trace, decision_point, *, items_in=None, decisions=None, links=None):
    """Ledger entry for a call made through scoring.trace.invoke, sharing its call id."""
    return record(settings, decision_point, trace['purpose'], trace['prompt_version'],
                  status='ok' if trace['status'] == 'validated' else 'failed', error=trace.get('error'),
                  latency_ms=trace.get('latency_ms'), input_tokens=trace.get('input_tokens'),
                  output_tokens=trace.get('output_tokens'), cached_input_tokens=trace.get('cached_input_tokens'),
                  reasoning_tokens=trace.get('reasoning_tokens'), model=trace.get('model'),
                  cost_usd=trace.get('estimated_cost_usd'),
                  items_in=items_in, decisions=decisions, links=links, call_id=trace['id'])


def summary(range_name='last_7_days'):
    since = (datetime.now(timezone.utc) - RANGES[range_name]).isoformat() if range_name in RANGES else None
    calls = repository.list_llm_calls(since=since)
    groups = {}
    for call in calls:
        group = groups.setdefault(call['decision_point'], {
            'decision_point': call['decision_point'], 'calls': 0, 'ok': 0, 'failed': 0, 'items_in': 0,
            'decisions': {}, 'input_tokens': 0, 'cached_input_tokens': 0, 'output_tokens': 0, 'reasoning_tokens': 0,
            'estimated_cost_usd': None, 'latency_total_ms': 0.0, 'latency_max_ms': 0.0, 'models': set()})
        group['calls'] += 1
        group['ok' if call['status'] == 'ok' else 'failed'] += 1
        group['items_in'] += call.get('items_in') or 0
        for key, count in (call.get('decisions') or {}).items():
            if isinstance(count, (int, float)):
                group['decisions'][key] = group['decisions'].get(key, 0) + count
        for key in ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_tokens'):
            group[key] += call.get(key) or 0
        if call.get('estimated_cost_usd') is not None:
            group['estimated_cost_usd'] = (group['estimated_cost_usd'] or 0) + call['estimated_cost_usd']
        latency = call.get('latency_ms') or 0
        group['latency_total_ms'] += latency
        group['latency_max_ms'] = max(group['latency_max_ms'], latency)
        group['models'].add(call['provider'] + ':' + call['model'])
    rows = []
    for group in groups.values():
        group['avg_latency_ms'] = round(group.pop('latency_total_ms') / group['calls'], 1)
        group['models'] = sorted(group['models'])
        rows.append(group)
    rows.sort(key=lambda row: row['input_tokens'] + row['output_tokens'], reverse=True)
    total_tokens = sum(row['input_tokens'] + row['output_tokens'] for row in rows) or 1
    for row in rows:
        row['token_share'] = round((row['input_tokens'] + row['output_tokens']) / total_tokens, 4)
    costs = [row['estimated_cost_usd'] for row in rows if row['estimated_cost_usd'] is not None]
    return {'range': range_name, 'since': since,
            'totals': {'calls': len(calls), 'failed': sum(row['failed'] for row in rows),
                       'input_tokens': sum(row['input_tokens'] for row in rows),
                       'cached_input_tokens': sum(row['cached_input_tokens'] for row in rows),
                       'output_tokens': sum(row['output_tokens'] for row in rows),
                       'reasoning_tokens': sum(row['reasoning_tokens'] for row in rows),
                       'estimated_cost_usd': sum(costs) if costs else None},
            'by_decision_point': rows}
