"""Jev path for the lead filter-and-score decision: Jev classifies, code decides.

The LLM path asks one call per company to "return matching IDs with 0-100 scores". Jev cannot write
lists or numbers, so each lead becomes a few small typed questions (the Jev docs' recommended
"atomic" style). Code turns the answers into the same outcome: selected / not selected + a 0-100 score.
The rules below are written for any role family (sales leaders, engineers, nurses, founders, ...),
not for one target.
"""
import json
import math
from uuid import uuid4

from engines.jev_engine import JevEngine
from engines.llm_engine import LLMTransportError
from .trace import now

VERSION = 'jev-lead-gates-v2'
FIT_LEVELS = ['Not a fit: wrong role, function, seniority or location for the target',
              'Loose fit: a related role, but not clearly one of the target roles',
              'Reasonable fit: a recognisable variant of a target role that meets the other requirements',
              'Strong fit: clearly one of the target roles and meets every other requirement']
LEAD_FIELDS = ('title', 'headline', 'location', 'department', 'management_level', 'experience_years', 'skills', 'summary')
# Gates where a "yes" answer is bad for the lead; their probability is inverted.
INVERTED_GATES = {'in_excluded_location'}

ROLE_RULES = [
    'Judge only the current role: the title, or the headline when the title is blank. Past roles, the employer, skills and the summary do not make a role match.',
    'Variants of the same role count: seniority words (Senior, Lead, Staff, Principal), abbreviations, spelling, language and a named specialisation. '
    'Examples: Senior C++ Software Engineer is a Software Engineer; Vice President of Sales and Head of Sales are variants of VP of Sales; '
    'Co-Founder and Founder & CEO are variants of Founder; Nurse Practitioner and Enrolled Nurse are nurses; Regional Sales Manager is a Sales Manager.',
    'A role in a different function or discipline does not match even when it shares words. Examples: Mechanical Engineer, Plant Manager or '
    'Engineering Project Manager is not a Software Engineer; Sales Operations is not Sales; Data Analyst is not Data Scientist; Pre-Sales Architect is not a Sales Manager.',
    'People who recruit for, advise, coach, support, assist or report to the target role do not match it. Examples: a recruiter or headhunter for sales roles '
    'is not a Sales Manager; an HR consultant is not an HR Director; a Chief of Staff to the CEO or a Founder\'s Office associate is not a CEO or Founder.',
    'Students, interns, trainees and candidates do not match unless the target asks for them.',
    'For a leadership target (founder, chief, vice president, head, director or manager), individual contributors do not match. '
    'For an individual-contributor target, a role whose main job is managing that team is a different role.',
    'When a title lists several current roles, it matches if any one of them is a target role, unless another listed role '
    'shows the person is a student, intern or trainee.',
    'Ignore slogans, promotional phrases and descriptions of what the person built or sells; judge the role words '
    '(for example "CEO, Built X So You Do Not Have To Y" is a CEO).',
]
LOCATION_RULES = [
    "Judge by the lead's own location. A city, suburb, state, region or metro area counts when it lies inside a target place, "
    'even when no country is written (San Francisco Bay Area is in the United States; Greater Paris is in France; Delhi NCR is in India).',
    'A place with a similar name in another country does not count (Indiana is not India; Georgia the US state is not the country Georgia).',
    "A region named in the title (for example 'Sales Director Switzerland') is location evidence.",
    "Never use the company's name or headquarters as the lead's location.",
    "If the lead's location is blank and nothing contradicts the target, answer yes.",
]
EXCLUDED_RULES = [
    'An excluded city includes its suburbs, boroughs and metro area (Croydon and Greater London are London; Parramatta is Sydney; Brooklyn is New York City).',
    'A broader area that merely contains the excluded place is not excluded (England is not London; New South Wales is not Sydney).',
    'If an excluded name can mean a city or a state, treat it as the city unless the target says state.',
    "If the lead's location is blank or too broad to tell, answer no.",
]


def experience_text(filters):
    low, high = filters['experience_min'], filters['experience_max']
    if low is None and high is None:
        return None
    if high is None:
        return f'at least {low:g} years'
    if low is None:
        return f'at most {high:g} years'
    return f'between {low:g} and {high:g} years'


def noul(question, rules, yes, no, **context):
    return {'type': 'noul', 'instructions': {'question': question, **context, 'rules': rules},
            'criteria': {'true': yes, 'false': no}}


def build_questions(filters):
    """Only the requirements the target actually uses become questions. Each answers one thing."""
    questions = {}
    if filters['titles']:
        questions['role_match'] = noul(
            "Is the lead's current role one of the target roles, or a recognisable variant of one?", ROLE_RULES,
            'The current role is a target role or a variant of one.',
            'The current role is a different role, function or seniority, or a role that only supports or recruits for the target role.',
            target_roles=filters['titles'])
    places = filters['countries'] + filters['locations']
    if places:
        questions['location_match'] = noul(
            'Is the lead located in one of the target places?', LOCATION_RULES,
            "The lead's location lies inside a target place, or is blank with nothing contradicting it.",
            "The lead's location lies outside every target place.", target_places=places)
    if filters['exclude_locations']:
        questions['in_excluded_location'] = noul(
            'Is the lead located in, or does the title name, one of the excluded places?', EXCLUDED_RULES,
            "The lead's location, or a region named in the title, is inside an excluded place.",
            'The lead is clearly outside every excluded place, or the location is blank or too broad to tell.',
            excluded_places=filters['exclude_locations'])
    if filters['departments']:
        questions['department_match'] = noul(
            'Does the lead work in one of the target departments?',
            ['A filled-in department that is not one of the targets means no, even when the title sounds related.',
             'If the department is blank, judge from the title; answer yes when the title is compatible.'],
            'The department is a target department, or it is blank and the title fits one.',
            'The department is filled in with another department, or the title clearly belongs to another department.',
            target_departments=filters['departments'])
    if filters['management_levels']:
        questions['seniority_match'] = noul(
            "Is the lead's seniority one of the target management levels?",
            ['A filled-in management level that is not one of the targets means no, even if the title sounds senior.',
             'If the level is blank, judge from the title; answer yes when the title is compatible.'],
            'The management level is a target level, or it is blank and the title fits one.',
            'The management level is filled in with another level, or the title clearly shows another level.',
            target_levels=filters['management_levels'])
    if experience_text(filters):
        questions['experience_match'] = noul(
            "Does the lead's years of experience meet the requirement?",
            ['A band such as "6 to 10 years" meets the requirement when any value in it can satisfy it.',
             'If experience is blank, answer yes.'],
            'The experience value or band can satisfy the requirement, or experience is blank.',
            'No value in the stated experience can satisfy the requirement.', requirement=experience_text(filters))
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


def probability(value):
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError('probability out of range')
    return number


def decide(answers, threshold):
    """Every asked requirement must pass; the score comes from the fit probabilities.

    Raises ValueError/KeyError/TypeError when an answer is missing or malformed, so the lead can fall back.
    """
    gates = {}
    for name, answer in answers.items():
        if name == 'fit':
            continue
        if answer.get('type') != 'noul':
            raise ValueError(f'{name} is not a yes/no answer')
        value = probability(answer['noul'])
        gates[name] = 1 - value if name in INVERTED_GATES else value
    fit = answers['fit']
    if fit.get('type') != 'score':
        raise ValueError('fit is not a score answer')
    levels = len(fit.get('legend') or FIT_LEVELS)
    raw_score = float(fit['score'])
    if not math.isfinite(raw_score) or not 0 <= raw_score <= levels - 1:
        raise ValueError('fit score out of range')
    match_probability = 1.0
    for value in gates.values():
        match_probability *= value
    score = max(1, min(100, round(100 * raw_score / (levels - 1))))
    weakest = min(gates, key=gates.get) if gates else None
    return {'selected': all(value >= threshold for value in gates.values()), 'score': score,
            'match_probability': round(match_probability, 4),
            'gates': {name: round(value, 4) for name, value in gates.items()},
            'weakest_requirement': weakest, 'fit_confidence': fit.get('confidence'),
            'fit_probabilities': fit.get('probabilities')}


async def judge_lead(jev_settings, person, target, client=None):
    """One Jev query for one lead. Returns (decision or None, trace)."""
    questions = build_questions(target['filters'])
    state = build_state(person, target['description'])
    trace = {'id': 'call_' + uuid4().hex, 'purpose': 'Judge one lead with Jev', 'prompt_version': VERSION,
             'provider': jev_settings.provider, 'model': jev_settings.model, 'created_at': now(),
             'messages': [{'role': 'state', 'content': json.dumps(state, ensure_ascii=False)},
                          {'role': 'questions', 'content': json.dumps(questions, ensure_ascii=False)}],
             'schema': None, 'output': None, 'status': 'failed', 'error': None, 'error_code': None, 'input_tokens': None,
             'cached_input_tokens': None, 'output_tokens': None, 'reasoning_tokens': None,
             'estimated_cost_usd': None, 'latency_ms': None, 'lead_id': person['id']}
    try:
        response = await JevEngine(jev_settings, client).system_one(state, questions)
        trace.update(output=json.dumps(response.answers, ensure_ascii=False), model=response.model,
                     input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                     latency_ms=response.latency_ms, attempts=response.attempts,
                     estimated_cost_usd=(response.input_tokens or 0) * jev_settings.input_cost_per_million / 1_000_000)
        decision = decide(response.answers, jev_settings.match_threshold)
        trace.update(status='validated', decision=decision)
        return decision, trace
    except LLMTransportError as exc:
        trace.update(error=exc.message, error_code=exc.code)
    except (KeyError, TypeError, ValueError, AttributeError):
        trace.update(error='Jev returned answers that could not be turned into a decision.', error_code='invalid_answers')
    return None, trace
