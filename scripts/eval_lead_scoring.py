"""Manual-test harness: drives the running backend's public API like the UI does and
compares DeepSeek's decisions with the labels in datasets/oppora_live_sample.json.

Makes real LLM calls (about 200 per scoring run). Usage, with a backend running on BASE:
  python scripts/eval_lead_scoring.py interpret
  python scripts/eval_lead_scoring.py score <tag> [llm|jev]  -> scores all 200 labelled people, saves data/eval_<tag>.json
  python scripts/eval_lead_scoring.py compare <tagA> <tagB>  -> stability between two saved runs
  python scripts/eval_lead_scoring.py explain <tag>          -> explanations for a few interesting people
  python scripts/eval_lead_scoring.py scenarios <file> <tag> [llm|jev]
      -> scores every scenario in datasets/<file> (e.g. lead_scoring_scenarios.json) against its own labels.
         Start the backend with DIRECTORY_FILE=<file> first. Saves data/eval_scen_<tag>.json.
Set EVAL_BASE to point at a backend other than http://127.0.0.1:8010.
"""
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx

BASE = os.environ.get('EVAL_BASE', 'http://127.0.0.1:8010')
ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / 'datasets' / 'oppora_live_sample.json'
SAMPLE = json.loads(SAMPLE_PATH.read_text(encoding='utf-8')) if SAMPLE_PATH.exists() else {'companies': []}
ICP_QUERY = ('VP of Sales, Head of Sales, SDR Managers, Revenue Operations Managers and Founders '
             'in the United States, Canada or the United Kingdom')
OBJECTIVE = 'We help sales teams replace manual outbound prospecting with an AI SDR agent'
client = httpx.Client(base_url=BASE, timeout=180)


def labels():
    out = {}
    for company in SAMPLE['companies']:
        for index, lead in enumerate(company['leads']):
            out[f"{company['company_id']}:{index}"] = {**lead['expected'], 'name': lead['first_name'] + ' ' + lead['last_name'],
                                                       'title': lead['title'], 'location': lead['location'], 'company': company['name']}
    return out


def post(path, body):
    response = client.post(path, json=body)
    try:
        data = response.json()
    except ValueError:
        data = {'raw': response.text[:300]}
    return response.status_code, data


def interpret():
    queries = [
        ('icp', ICP_QUERY),
        ('india', 'VP of Sales in India'),
        ('exclusion', 'HR directors in the United Kingdom, excluding London'),
        ('experience', 'Sales leaders in the United States with at least 5 years of experience'),
        ('explicit_meta', 'People in the Sales department at Director or Vice President seniority in Canada'),
        ('unsupported', 'SaaS companies with 50 to 200 employees that raised a Series A'),
        ('vague', 'good leads'),
        ('company_named', 'Sales leaders at Salesforce'),
    ]
    results = []
    for name, query in queries:
        started = time.perf_counter()
        status, data = post('/v1/lead-scoring/targeting', {'description': query, 'objective': OBJECTIVE})
        row = {'case': name, 'query': query, 'http': status, 'seconds': round(time.perf_counter() - started, 1)}
        if status == 200:
            row['filters'] = {k: v for k, v in data['filters'].items() if v not in ([], None)}
            row['removed_inferred'] = data.get('validation', {}).get('removed_inferred_filters')
            row['calls'] = len(data.get('interpretation_traces') or [])
        else:
            row['error'] = data.get('detail')
        results.append(row)
        print(json.dumps(row, ensure_ascii=False))
    (ROOT / 'data' / 'eval_interpret.json').write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding='utf-8')


def score(tag, decision_model='llm'):
    expected = labels()
    status, target = post('/v1/lead-scoring/targeting', {'description': ICP_QUERY, 'objective': OBJECTIVE})
    assert status == 200, target
    print('target filters:', {k: v for k, v in target['filters'].items() if v not in ([], None)})
    status, lead_list = post('/v1/lead-scoring/lists', {'name': f'Eval {tag} (200 labelled real people)',
                                                       'lead_ids': list(expected), 'targeting_id': target['id']})
    assert status == 201, lead_list
    status, run = post(f"/v1/lead-scoring/lists/{lead_list['id']}/score",
                       {'expected_version': lead_list['version'], 'targeting_id': target['id'],
                        'decision_model': decision_model})
    assert status == 202, run
    started = time.perf_counter()
    while run['status'] in {'queued', 'running'}:
        time.sleep(3)
        run = client.get(f"/v1/lead-scoring/runs/{run['id']}").json()
        print(f"  {run['status']} {run['processed']}/{run['total']} matched={run['matched']} failed={run['failed']}", flush=True)
    seconds = round(time.perf_counter() - started, 1)
    report = evaluate(run, expected)
    report.update(tag=tag, list_id=lead_list['id'], run_id=run['id'], model=run['model'],
                  prompt_version=run['prompt_version'], wall_seconds=seconds, filters=target['filters'])
    (ROOT / 'data' / f'eval_{tag}.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in {'people', 'false_positives', 'false_negatives', 'borderline'}}, indent=1))
    print('false positives:', json.dumps(report['false_positives'], ensure_ascii=False, indent=1))
    print('false negatives:', json.dumps(report['false_negatives'], ensure_ascii=False, indent=1))


def evaluate(run, expected):
    people, tp, fp, fn, tn = [], [], [], [], []
    borderline, per_pool = [], defaultdict(Counter)
    tiers = Counter()
    for item in run['results']:
        pid = item['person']['id']
        label = expected[pid]
        selected = item['status'] == 'matched'
        row = {'id': pid, 'name': label['name'], 'title': label['title'], 'location': label['location'],
               'pool': label['pool'], 'label': label['label'], 'reason': label['reason'],
               'status': item['status'], 'score': item['score'], 'priority_tier': item.get('priority_tier'),
               'decided_by': item.get('decided_by')}
        if item.get('jev'):
            row['jev'] = {key: item['jev'][key] for key in ('gates', 'match_probability', 'weakest_requirement')}
        people.append(row)
        if selected:
            tiers[str(item.get('priority_tier'))] += 1
        if item['status'] == 'failed':
            per_pool[label['pool']]['failed'] += 1
            continue
        if label['label'] == 'borderline':
            borderline.append(row)
            per_pool[label['pool']]['borderline_selected' if selected else 'borderline_dropped'] += 1
            continue
        bucket = tp if selected and label['label'] == 'match' else fp if selected else fn if label['label'] == 'match' else tn
        bucket.append(row)
        per_pool[label['pool']][{id(tp): 'TP', id(fp): 'FP', id(fn): 'FN', id(tn): 'TN'}[id(bucket)]] += 1
    decided = len(tp) + len(fp) + len(fn) + len(tn)
    precision = len(tp) / (len(tp) + len(fp)) if tp or fp else None
    recall = len(tp) / (len(tp) + len(fn)) if tp or fn else None
    scores_tp = [r['score'] for r in tp]
    scores_fp = [r['score'] for r in fp]
    calls = run['traces']
    latencies = [t.get('latency_ms') or 0 for t in calls]
    return {
        'totals': {'people': len(people), 'failed': sum(r['status'] == 'failed' for r in people),
                   'selected': sum(r['status'] == 'matched' for r in people)},
        'confusion': {'TP': len(tp), 'FP': len(fp), 'FN': len(fn), 'TN': len(tn)},
        'accuracy': round((len(tp) + len(tn)) / decided, 3) if decided else None,
        'precision': round(precision, 3) if precision is not None else None,
        'recall': round(recall, 3) if recall is not None else None,
        'borderline_selected': sum(r['status'] == 'matched' for r in borderline), 'borderline_total': len(borderline),
        'score_stats_true_matches': {'min': min(scores_tp), 'median': statistics.median(scores_tp), 'max': max(scores_tp)} if scores_tp else None,
        'score_stats_false_positives': {'min': min(scores_fp), 'median': statistics.median(scores_fp), 'max': max(scores_fp)} if scores_fp else None,
        'score_histogram': dict(sorted(Counter((r['score'] // 10) * 10 for r in people if r['score'] is not None).items())),
        'priority_tier_values': dict(tiers),
        'per_pool': {pool: dict(counts) for pool, counts in sorted(per_pool.items())},
        'fallback_leads': sum(r.get('decided_by') == 'llm_fallback' for r in people),
        'llm_calls': len(calls), 'failed_calls': sum(t['status'] == 'failed' for t in calls),
        'input_tokens': sum(t.get('input_tokens') or 0 for t in calls),
        'cached_input_tokens': sum(t.get('cached_input_tokens') or 0 for t in calls),
        'output_tokens': sum(t.get('output_tokens') or 0 for t in calls),
        'latency_ms': {'median': statistics.median(latencies), 'max': max(latencies)} if latencies else None,
        'threshold_sweep': threshold_sweep(people),
        'false_positives': fp, 'false_negatives': fn, 'borderline': borderline, 'people': people,
    }


def threshold_sweep(people):
    """Jev only: how accuracy would change if every requirement had to pass a different probability."""
    rows = [p for p in people if p.get('jev') and p['label'] != 'borderline']
    if not rows:
        return None
    sweep = {}
    for threshold in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        tp = fp = fn = tn = 0
        for p in rows:
            selected = all(value >= threshold for value in p['jev']['gates'].values())
            match = p['label'] == 'match'
            tp += selected and match
            fp += selected and not match
            fn += match and not selected
            tn += not selected and not match
        sweep[str(threshold)] = {'accuracy': round((tp + tn) / len(rows), 3), 'FP': fp, 'FN': fn}
    return sweep


def compare(tag_a, tag_b):
    a = {p['id']: p for p in json.loads((ROOT / 'data' / f'eval_{tag_a}.json').read_text(encoding='utf-8'))['people']}
    b = {p['id']: p for p in json.loads((ROOT / 'data' / f'eval_{tag_b}.json').read_text(encoding='utf-8'))['people']}
    flips, diffs = [], []
    for pid, left in a.items():
        right = b[pid]
        if (left['status'] == 'matched') != (right['status'] == 'matched'):
            flips.append({'name': left['name'], 'title': left['title'], 'label': left['label'],
                          tag_a: left['status'], tag_b: right['status']})
        elif left['score'] is not None and right['score'] is not None:
            diffs.append(abs(left['score'] - right['score']))
    summary = {'people': len(a), 'decision_flips': len(flips),
               'decision_agreement': round(1 - len(flips) / len(a), 3),
               'both_selected': len(diffs), 'identical_scores': sum(d == 0 for d in diffs),
               'score_diff_mean': round(statistics.mean(diffs), 2) if diffs else None,
               'score_diff_max': max(diffs) if diffs else None, 'flips': flips}
    (ROOT / 'data' / f'eval_compare_{tag_a}_{tag_b}.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=1, ensure_ascii=False))


def explain(tag):
    report = json.loads((ROOT / 'data' / f'eval_{tag}.json').read_text(encoding='utf-8'))
    picks = (report['false_positives'][:1] + report['false_negatives'][:1]
             + [p for p in report['people'] if p['label'] == 'match' and p['status'] == 'matched'][:1])
    for person in picks:
        status, run = post(f"/v1/lead-scoring/runs/{report['run_id']}/explanation", {'lead_id': person['id']})
        item = next(r for r in run['results'] if r['person']['id'] == person['id']) if status == 200 else None
        print(json.dumps({'person': person['name'], 'title': person['title'], 'label': person['label'],
                          'status': person['status'], 'score': person['score'], 'http': status,
                          'explanation': item['explanation'] if item else run}, indent=1, ensure_ascii=False))


def scenario_labels(data):
    leads = {lead['key']: (lead, company) for company in data['companies'] for lead in company['leads']}
    out = {}
    for scenario in data['scenarios']:
        out[scenario['id']] = {}
        for key in scenario['lead_keys']:
            lead, company = leads[key]
            expected = lead['expected']
            out[scenario['id']][expected['directory_id']] = {
                'label': expected['label'], 'reason': expected['reason'], 'pool': scenario['id'],
                'name': f"{lead['first_name']} {lead['last_name']}", 'title': lead['title'],
                'location': lead['location'], 'company': company['name'], 'key': key}
    return out


def filter_differences(actual, expected):
    """Expected filter values the interpreter missed or changed. Extra fields are reported too."""
    differences = {}
    for field, value in expected.items():
        got = actual.get(field)
        if isinstance(value, list):
            if sorted(v.casefold() for v in got or []) != sorted(v.casefold() for v in value):
                differences[field] = {'expected': value, 'got': got}
        elif got != value:
            differences[field] = {'expected': value, 'got': got}
    for field, got in actual.items():
        if field not in expected and got not in ([], None):
            differences[field] = {'expected': None, 'got': got}
    return differences


def run_scenario(scenario, expected, tag, decision_model):
    status, target = post('/v1/lead-scoring/targeting', {'description': scenario['query'], 'objective': ''})
    if status != 200:
        return {'id': scenario['id'], 'holdout': scenario['holdout'], 'query': scenario['query'],
                'interpretation_error': target.get('detail'), 'people': len(expected)}
    differences = filter_differences(target['filters'], scenario['expected_filters'])
    status, lead_list = post('/v1/lead-scoring/lists', {'name': f"Eval {tag} {scenario['id']}",
                                                       'lead_ids': list(expected), 'targeting_id': target['id']})
    assert status == 201, lead_list
    status, run = post(f"/v1/lead-scoring/lists/{lead_list['id']}/score",
                       {'expected_version': lead_list['version'], 'targeting_id': target['id'],
                        'decision_model': decision_model})
    assert status == 202, run
    started = time.perf_counter()
    while run['status'] in {'queued', 'running'}:
        time.sleep(2)
        run = client.get(f"/v1/lead-scoring/runs/{run['id']}").json()
    report = evaluate(run, expected)
    report.update(id=scenario['id'], holdout=scenario['holdout'], query=scenario['query'], run_id=run['id'],
                  run_status=run['status'], model=run['model'], prompt_version=run['prompt_version'],
                  wall_seconds=round(time.perf_counter() - started, 1), filters=target['filters'],
                  filter_differences=differences, cleaned_values=target.get('validation', {}).get('cleaned_values'),
                  fallback=run.get('fallback'))
    return report


def combine(reports):
    tp = sum(r['confusion']['TP'] for r in reports if 'confusion' in r)
    fp = sum(r['confusion']['FP'] for r in reports if 'confusion' in r)
    fn = sum(r['confusion']['FN'] for r in reports if 'confusion' in r)
    tn = sum(r['confusion']['TN'] for r in reports if 'confusion' in r)
    decided = tp + fp + fn + tn
    return {'scenarios': len(reports), 'TP': tp, 'FP': fp, 'FN': fn, 'TN': tn,
            'accuracy': round((tp + tn) / decided, 3) if decided else None,
            'precision': round(tp / (tp + fp), 3) if tp + fp else None,
            'recall': round(tp / (tp + fn), 3) if tp + fn else None,
            'borderline_selected': sum(r.get('borderline_selected', 0) for r in reports),
            'borderline_total': sum(r.get('borderline_total', 0) for r in reports),
            'failed': sum(r.get('totals', {}).get('failed', 0) for r in reports),
            'fallback_leads': sum(r.get('fallback_leads', 0) for r in reports),
            'interpretation_errors': sum('interpretation_error' in r for r in reports),
            'filter_mismatches': sum(bool(r.get('filter_differences')) for r in reports),
            'wall_seconds': round(sum(r.get('wall_seconds', 0) for r in reports), 1),
            'input_tokens': sum(r.get('input_tokens', 0) for r in reports)}


def scenarios(file_name, tag, decision_model='llm'):
    data = json.loads((ROOT / 'datasets' / file_name).read_text(encoding='utf-8'))
    labels_by_scenario = scenario_labels(data)
    reports = []
    for scenario in data['scenarios']:
        report = run_scenario(scenario, labels_by_scenario[scenario['id']], tag, decision_model)
        reports.append(report)
        brief = {key: report.get(key) for key in ('id', 'accuracy', 'precision', 'recall', 'confusion', 'borderline_selected',
                                                   'borderline_total', 'fallback_leads', 'filter_differences', 'interpretation_error')}
        print(json.dumps(brief, ensure_ascii=False), flush=True)
    summary = {'tag': tag, 'file': file_name, 'decision_model': decision_model,
               'development': combine([r for r in reports if not r['holdout']]),
               'holdout': combine([r for r in reports if r['holdout']]), 'all': combine(reports), 'scenarios': reports}
    (ROOT / 'data' / f'eval_scen_{tag}.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({key: summary[key] for key in ('development', 'holdout', 'all')}, indent=1))


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'interpret':
        interpret()
    elif command == 'score':
        score(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'llm')
    elif command == 'compare':
        compare(sys.argv[2], sys.argv[3])
    elif command == 'explain':
        explain(sys.argv[2])
    elif command == 'scenarios':
        scenarios(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else 'llm')
