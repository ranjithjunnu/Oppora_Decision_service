"""Jev path for the lead filter-and-score decision: Jev classifies, code decides.

The LLM path asks one call per company to "return matching IDs with 0-100 scores". Jev cannot write
lists or numbers, so each lead becomes a few small typed questions (the Jev docs' recommended
"atomic" style). Code turns the answers into the same outcome: selected / not selected + a 0-100 score.
"""
import json
from uuid import uuid4

from engines.jev_engine import JevEngine
from engines.llm_engine import LLMTransportError
from .trace import now

VERSION = 'jev-lead-gates-v1'
FIT_LEVELS = ['Not a fit: wrong role, function, seniority or location for the target',
              'Loose fit: a related role, but not clearly one of the target roles',
              'Reasonable fit: a recognisable variant of a target role that meets the other requirements',
              'Strong fit: clearly one of the target roles and meets every other requirement']
LEAD_FIELDS = ('title', 'headline', 'location', 'department', 'management_level', 'experience_years', 'skills', 'summary')


def experience_text(filters):
    low, high = filters['experience_min'], filters['experience_max']
    if low is None and high is None:
        return None
    if high is None:
        return f'at least {low:g} years'
    if low is None:
        return f'at most {high:g} years'
    return f'between {low:g} and {high:g} years'


def build_questions(filters):
    """Only the requirements the target actually uses become questions. Each answers one thing."""
    questions = {}
    if filters['titles']:
        questions['role_match'] = {'type': 'noul', 'instructions': {
            'question': "Is the lead's current role one of the target roles, or a recognisable variant of one?",
            'target_roles': filters['titles'],
            'rules': ['Title variants count: Vice President of Sales, Sales VP and Head of Sales are variants of VP of Sales; '
                      'Co-Founder, Founder/CEO and CEO & Founder are variants of Founder.',
                      'Interns, trainees, junior roles, individual contributors and consultants do not match a leadership or manager role.',
                      'A role in a different function (for example marketing, HR, engineering) does not match.',
                      'If the title is blank, judge from the headline.']}}
    places = filters['countries'] + filters['locations']
    if places:
        questions['location_match'] = {'type': 'noul', 'instructions': {
            'question': 'Is the lead located in one of the target places?',
            'target_places': places,
            'rules': ["Judge by the lead's own location. A city, state, region or metro area counts when it lies inside a target country.",
                      "A region named in the title (for example 'Sales Director Switzerland') is location evidence.",
                      "Never use the company's name or headquarters as the lead's location.",
                      "If the lead's location is blank and nothing contradicts the target, answer yes."]}}
    if filters['exclude_locations']:
        questions['in_excluded_location'] = {'type': 'noul', 'instructions': {
            'question': 'Is the lead located in, or does the title name, one of the excluded places?',
            'excluded_places': filters['exclude_locations'],
            'rules': ['A city or area inside an excluded place counts as excluded.']}}
    if filters['departments']:
        questions['department_match'] = {'type': 'noul', 'instructions': {
            'question': "Does the lead work in one of the target departments?",
            'target_departments': filters['departments'],
            'rules': ['A filled-in department that is not one of the targets means no.',
                      'If the department is blank, judge from the title; answer yes when the title is compatible.']}}
    if filters['management_levels']:
        questions['seniority_match'] = {'type': 'noul', 'instructions': {
            'question': "Is the lead's seniority one of the target management levels?",
            'target_levels': filters['management_levels'],
            'rules': ['A filled-in management level that is not one of the targets means no, even if the title sounds senior.',
                      'If the level is blank, judge from the title; answer yes when the title is compatible.']}}
    if experience_text(filters):
        questions['experience_match'] = {'type': 'noul', 'instructions': {
            'question': "Does the lead's years of experience meet the requirement?",
            'requirement': experience_text(filters),
            'rules': ['A band such as "6 to 10 years" meets the requirement when any value in it can satisfy it.',
                      'If experience is blank, answer yes.']}}
    questions['fit'] = {'type': 'score', 'instructions': {
        'question': 'Overall, how well does the lead fit the target people?',
        'target_people': {key: value for key, value in {
            'roles': filters['titles'], 'places': places, 'excluded_places': filters['exclude_locations'],
            'departments': filters['departments'], 'management_levels': filters['management_levels'],
            'experience': experience_text(filters)}.items() if value}}, 'criteria': FIT_LEVELS}
    return questions


def build_state(person, target_description):
    lead = {field: person.get(field) for field in LEAD_FIELDS}
    if lead['summary']:
        lead['summary'] = str(lead['summary'])[:500]
    return {'target_description': target_description, 'company': person.get('company_name'), 'lead': lead}


def decide(answers, threshold):
    """Every asked requirement must pass; the score comes from the fit probabilities."""
    gates = {}
    for name, answer in answers.items():
        if answer.get('type') != 'noul':
            continue
        probability = float(answer['noul'])
        gates[name] = 1 - probability if name == 'in_excluded_location' else probability
    match_probability = 1.0
    for value in gates.values():
        match_probability *= value
    fit = answers['fit']
    levels = len(fit.get('legend') or FIT_LEVELS)
    score = max(1, min(100, round(100 * float(fit['score']) / (levels - 1))))
    weakest = min(gates, key=gates.get) if gates else None
    return {'selected': all(value >= threshold for value in gates.values()), 'score': score,
            'match_probability': round(match_probability, 4),
            'gates': {name: round(value, 4) for name, value in gates.items()},
            'weakest_requirement': weakest, 'fit_confidence': fit.get('confidence'),
            'fit_probabilities': fit.get('probabilities')}


async def judge_lead(jev_settings, person, target):
    """One Jev query for one lead. Returns (decision or None, trace)."""
    questions = build_questions(target['filters'])
    state = build_state(person, target['description'])
    trace = {'id': 'call_' + uuid4().hex, 'purpose': 'Judge one lead with Jev', 'prompt_version': VERSION,
             'provider': jev_settings.provider, 'model': jev_settings.model, 'created_at': now(),
             'messages': [{'role': 'state', 'content': json.dumps(state, ensure_ascii=False)},
                          {'role': 'questions', 'content': json.dumps(questions, ensure_ascii=False)}],
             'schema': None, 'output': None, 'status': 'failed', 'error': None, 'input_tokens': None,
             'cached_input_tokens': None, 'output_tokens': None, 'reasoning_tokens': None,
             'estimated_cost_usd': None, 'latency_ms': None, 'lead_id': person['id']}
    try:
        response = await JevEngine(jev_settings).system_one(state, questions)
        decision = decide(response.answers, jev_settings.match_threshold)
        trace.update(output=json.dumps(response.answers, ensure_ascii=False), status='validated', model=response.model,
                     input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                     latency_ms=response.latency_ms, decision=decision,
                     estimated_cost_usd=(response.input_tokens or 0) * jev_settings.input_cost_per_million / 1_000_000)
        return decision, trace
    except LLMTransportError as exc:
        trace['error'] = exc.message
    except (KeyError, TypeError, ValueError):
        trace['error'] = 'Jev returned answers that could not be turned into a decision.'
    return None, trace
