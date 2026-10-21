"""Build the synthetic labelled scenario set and its review sheet from one source of truth.

Usage: python scripts/build_lead_scoring_scenarios.py   (no model calls; edit labels here, then rerun)
Writes datasets/lead_scoring_scenarios.json and docs/LEAD_SCORING_TEST_SET.md.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M, N, B = 'match', 'no_match', 'borderline'

# Each scenario: id, holdout flag, query, what it covers, expected filters, companies, people.
# Person: (first, last, title, location, years_experience, label, reason, tags, extra fields)
SCENARIOS = [
    {
        'id': 'S1', 'holdout': False,
        'query': 'Software engineers in the United States with 5+ years of experience',
        'covers': 'Individual-contributor role (not leadership), minimum experience, US metro areas without a country',
        'expected_filters': {'titles': ['Software Engineer'], 'countries': ['United States'], 'experience_min': 5},
        'companies': ['Brightwave Software', 'Kestrel Cloud', 'Orchard Systems'],
        'people': [
            ('Maya', 'Lindqvist', 'Senior Software Engineer', 'Austin, Texas, United States', 8, M, 'Software engineer variant in the US with 8 years', ['clear', 'title_variant']),
            ('Daniel', 'Okafor', 'Software Developer', 'New York, New York, United States', '6 to 10 years', M, 'Developer is a close variant; the whole band meets 5+', ['title_variant']),
            ('Priya', 'Raman', 'Backend Engineer', 'Seattle, Washington, United States', 7, M, 'Backend engineer is a software engineering role', ['title_variant']),
            ('Lucas', 'Moreau', 'Staff Software Engineer', 'San Francisco Bay Area', 11, M, 'Bay Area lies inside the US although no country is written', ['location_no_country', 'title_variant']),
            ('Hannah', 'Brooks', 'Software Engineer', 'Toronto, Ontario, Canada', 10, N, 'Located in Canada, not the US', ['wrong_location']),
            ('Ethan', 'Cole', 'Software Engineer', 'Boston, Massachusetts, United States', 2, N, 'Only 2 years of experience', ['experience_fail']),
            ('Sofia', 'Alvarez', 'Junior Software Engineer', 'Denver, Colorado, United States', 1, N, 'Junior with 1 year of experience', ['experience_fail']),
            ('Arjun', 'Mehta', 'Software Engineer', 'Bengaluru, Karnataka, India', 9, N, 'Located in India, not the US', ['wrong_location']),
            ('Grace', 'Kim', 'Data Analyst', 'Chicago, Illinois, United States', 6, N, 'Analyst, not a software engineer', ['wrong_role']),
            ('Owen', 'Fischer', 'Mechanical Engineer', 'Detroit, Michigan, United States', 10, N, 'Different engineering discipline', ['wrong_role', 'trap']),
            ('Leo', 'Tanaka', 'Software Engineering Intern', 'Palo Alto, California, United States', 0.5, N, 'Intern with under a year of experience', ['experience_fail', 'trap']),
            ('Nina', 'Petrova', 'Software Engineer in Test', 'Seattle, Washington, United States', 6, B, 'Test automation role; may or may not count as a software engineer', ['title_ambiguous']),
            ('Marcus', 'Reed', 'Engineering Manager', 'San Jose, California, United States', 12, B, 'Manages engineers; not clearly an engineer role', ['title_ambiguous']),
            ('Chloe', 'Bennett', 'Software Engineer', 'Austin, Texas, United States', None, B, 'Experience not supplied', ['unknown_field']),
        ],
    },
    {
        'id': 'S2', 'holdout': False,
        'query': 'HR directors in the United Kingdom, excluding London',
        'covers': 'Excluded location inside a target country, London boroughs and Greater London, HR title variants',
        'expected_filters': {'titles': ['HR Director'], 'countries': ['United Kingdom'], 'exclude_locations': ['London']},
        'companies': ['Harbourline Group', 'Fernhill Retail', 'Calder Logistics'],
        'people': [
            ('Emily', 'Hartley', 'HR Director', 'Manchester, England, United Kingdom', 15, M, 'HR Director in the UK outside London', ['clear']),
            ('Callum', 'Fraser', 'Director of Human Resources', 'Edinburgh, Scotland, United Kingdom', 18, M, 'Title variant; Scotland is in the UK', ['title_variant']),
            ('Aisha', 'Rahman', 'People Director', 'Bristol, England, United Kingdom', 12, M, 'People Director is the common modern HR Director title', ['title_variant']),
            ('Tom', 'Whitaker', 'HR Director', 'London, England, United Kingdom', 20, N, 'In London, which is excluded', ['excluded_location']),
            ('Olivia', 'Grant', 'HR Director', 'Greater London, England, United Kingdom', 14, N, 'Greater London counts as London', ['excluded_location']),
            ('Ravi', 'Patel', 'HR Director', 'Croydon, London, United Kingdom', 16, N, 'Croydon is a London borough', ['excluded_location', 'trap']),
            ('Sophie', 'Clarke', 'HR Manager', 'Leeds, England, United Kingdom', 8, N, 'Manager, not director', ['seniority_mismatch']),
            ('Sean', 'Byrne', 'HR Director', 'Dublin, Ireland', 17, N, 'Ireland is not part of the UK', ['wrong_location', 'trap']),
            ('Megan', 'Lewis', 'HR Business Partner', 'Birmingham, England, United Kingdom', 9, N, 'Business partner, not director', ['wrong_role']),
            ('James', 'Holt', 'Finance Director', 'Manchester, England, United Kingdom', 19, N, 'Different function', ['wrong_role']),
            ('Fiona', 'MacLeod', 'Head of HR', 'Glasgow, Scotland, United Kingdom', 13, B, 'Head of HR is often equivalent to HR Director, but not always', ['title_ambiguous']),
            ('Gareth', 'Evans', 'Chief People Officer', 'Cardiff, Wales, United Kingdom', 22, B, 'More senior than director; may or may not be wanted', ['title_ambiguous']),
            ('Laura', 'Bishop', 'HR Director EMEA', None, 16, B, 'Location not supplied; EMEA does not settle London or not', ['unknown_field']),
        ],
    },
    {
        'id': 'S3', 'holdout': False,
        'query': 'People in the Sales department at Director or Vice President seniority in Canada',
        'covers': 'Explicit department and management-level fields, field contradicting a sales-sounding title',
        'expected_filters': {'countries': ['Canada'], 'departments': ['Sales'], 'management_levels': ['Director', 'Vice President']},
        'companies': ['Maplecrest Analytics', 'Northshore Payments', 'Tundra Robotics'],
        'people': [
            ('Andre', 'Tremblay', 'Sales Director', 'Toronto, Ontario, Canada', 14, M, 'Sales department, Director level, in Canada', ['clear', 'department_field', 'seniority_field'], {'department': 'Sales', 'management_level': 'Director'}),
            ('Jessica', 'Wong', 'VP Sales', 'Vancouver, British Columbia, Canada', 16, M, 'Sales department, Vice President level', ['department_field', 'seniority_field'], {'department': 'Sales', 'management_level': 'Vice President'}),
            ('Ryan', 'MacDonald', 'Regional Sales Director', 'Calgary, Alberta, Canada', 12, M, 'Sales department, Director level', ['department_field', 'seniority_field'], {'department': 'Sales', 'management_level': 'Director'}),
            ('Isabelle', 'Gagnon', 'Sales Manager', 'Montreal, Quebec, Canada', 8, N, 'Manager level, not Director or VP', ['seniority_field', 'seniority_mismatch'], {'department': 'Sales', 'management_level': 'Manager'}),
            ('Kevin', 'Singh', 'Director of Marketing', 'Toronto, Ontario, Canada', 11, N, 'Marketing department', ['department_field'], {'department': 'Marketing', 'management_level': 'Director'}),
            ('Laura', 'Chen', 'Director of Sales Operations', 'Ottawa, Ontario, Canada', 10, N, 'Department field says Operations, which contradicts Sales', ['department_field', 'trap'], {'department': 'Operations', 'management_level': 'Director'}),
            ('Mark', 'Davies', 'Sales Director', 'Seattle, Washington, United States', 15, N, 'Located in the US, not Canada', ['wrong_location'], {'department': 'Sales', 'management_level': 'Director'}),
            ('Zoe', 'Martin', 'Account Executive', 'Toronto, Ontario, Canada', 5, N, 'Individual contributor', ['seniority_field'], {'department': 'Sales', 'management_level': 'Individual Contributor'}),
            ('Paul', 'Bouchard', 'Chief Executive Officer', 'Toronto, Ontario, Canada', 25, N, 'C-suite, not the Sales department', ['department_field', 'seniority_field'], {'department': 'C-Suite', 'management_level': 'C-Level'}),
            ('Samir', 'Haddad', 'Head of Sales', 'Toronto, Ontario, Canada', 13, B, 'Sales department, but management level not supplied', ['unknown_field', 'department_field'], {'department': 'Sales', 'management_level': None}),
            ('Claire', 'Dubois', 'Senior Vice President, Sales', 'Toronto, Ontario, Canada', 20, B, 'Senior VP is above VP; strict field matching would exclude it', ['seniority_field', 'title_ambiguous'], {'department': 'Sales', 'management_level': 'Senior Vice President'}),
        ],
    },
    {
        'id': 'S4', 'holdout': False,
        'query': 'Marketing managers in Germany or France with between 3 and 8 years of experience',
        'covers': 'Two countries, experience range with a maximum, regions without a country, manager-level role',
        'expected_filters': {'titles': ['Marketing Manager'], 'countries': ['Germany', 'France'], 'experience_min': 3, 'experience_max': 8},
        'companies': ['Lindenhof Media', 'Atelier Numérique', 'Rheinwerk Consumer'],
        'people': [
            ('Lena', 'Schröder', 'Marketing Manager', 'Berlin, Germany', 5, M, 'Marketing Manager in Germany within the range', ['clear']),
            ('Camille', 'Laurent', 'Senior Marketing Manager', 'Paris, France', '3 to 5 years', M, 'Variant in France; the whole band is inside the range', ['title_variant']),
            ('Jonas', 'Weber', 'Product Marketing Manager', 'Hamburg, Germany', 4, M, 'Product marketing manager is a marketing manager variant', ['title_variant']),
            ('Inès', 'Moreau', 'Marketing Manager', 'Île-de-France', 4, M, 'Île-de-France is a French region; no country written', ['location_no_country']),
            ('Felix', 'Wagner', 'Marketing Manager', 'Munich, Germany', 12, N, '12 years exceeds the 8-year maximum', ['experience_fail']),
            ('Manon', 'Petit', 'Marketing Manager', 'Lyon, France', 1, N, '1 year is below the 3-year minimum', ['experience_fail']),
            ('Lukas', 'Huber', 'Marketing Manager', 'Vienna, Austria', 5, N, 'Austria is not a target country', ['wrong_location', 'trap']),
            ('Noah', 'Keller', 'Marketing Manager', 'Zurich, Switzerland', 6, N, 'Switzerland is not a target country', ['wrong_location']),
            ('Anna', 'Becker', 'Sales Manager', 'Berlin, Germany', 5, N, 'Sales, not marketing', ['wrong_role']),
            ('Hugo', 'Bernard', 'Marketing Director', 'Paris, France', 7, B, 'Director is above manager; the Oppora prompt treats it as a variant', ['title_ambiguous']),
            ('Mia', 'Hoffmann', 'Marketing Manager', 'Frankfurt, Germany', '6 to 10 years', B, 'Band only partly inside the 3-8 range', ['experience_band_partial']),
            ('Paul', 'Richter', 'Marketing Manager', 'Berlin, Germany', None, B, 'Experience not supplied', ['unknown_field']),
        ],
    },
    {
        'id': 'S5', 'holdout': False,
        'query': 'Founders or CEOs in India',
        'covers': 'Founder/CEO variants, cities inside India (including Mumbai), India/Indiana and founder-office traps',
        'expected_filters': {'titles': ['Founder', 'CEO'], 'countries': ['India']},
        'companies': ['Saffron Fintech', 'Kaveri Health', 'Indus Freight', 'Monsoon Labs'],
        'people': [
            ('Rohan', 'Kapoor', 'Founder & CEO', 'Bengaluru, Karnataka, India', 12, M, 'Founder and CEO in India', ['clear']),
            ('Ananya', 'Iyer', 'Co-Founder', 'Mumbai, Maharashtra, India', 9, M, 'Co-founder; Mumbai is in India', ['title_variant', 'location_inside_country']),
            ('Vikram', 'Desai', 'Chief Executive Officer', 'Pune, Maharashtra, India', 20, M, 'CEO spelled out, in India', ['title_variant']),
            ('Neha', 'Sharma', 'Founder', 'Delhi NCR', 7, M, 'Delhi NCR is in India; no country written', ['location_no_country']),
            ('Sanjay', 'Bose', 'Managing Director & Founder', 'Kolkata, West Bengal, India', 18, M, 'Founder in the title, in India', ['title_variant']),
            ('Meera', 'Nair', 'CEO', 'Singapore', 15, N, 'Located in Singapore', ['wrong_location']),
            ('Aditya', 'Rao', 'Founder', 'London, England, United Kingdom', 10, N, 'Located in the UK; the company being Indian does not count', ['wrong_location'], {'headline': 'Founder building for India from London'}),
            ('Kavya', 'Menon', "Founder's Office Associate", 'Bengaluru, Karnataka, India', 2, N, 'Works in the founder office; not a founder', ['trap', 'wrong_role']),
            ('Arnav', 'Gupta', 'Chief of Staff to the CEO', 'Hyderabad, Telangana, India', 6, N, 'Reports to the CEO; not a CEO', ['trap', 'wrong_role']),
            ('Brian', 'Miller', 'CEO', 'Indianapolis, Indiana, United States', 22, N, 'Indiana, United States, not India', ['trap', 'wrong_location']),
            ('Pooja', 'Reddy', 'Product Manager', 'Bengaluru, Karnataka, India', 8, N, 'Current role is product manager; founding was in the past', ['trap', 'wrong_role'], {'headline': 'Product Manager | Former founder of a D2C brand'}),
            ('Farhan', 'Ali', 'Founder & Consultant', 'Chennai, Tamil Nadu, India', 11, B, 'Founder of a one-person consultancy; may not be a target', ['title_ambiguous']),
        ],
    },
    {
        'id': 'H1', 'holdout': True,
        'query': 'Nurses in Australia, excluding Sydney',
        'covers': 'Unrelated domain (healthcare), suburb inside an excluded city, student and recruiter traps',
        'expected_filters': {'titles': ['Nurse'], 'countries': ['Australia'], 'exclude_locations': ['Sydney']},
        'companies': ['Wattle Health Network', 'Coastal Care Partners'],
        'people': [
            ('Jack', 'Thompson', 'Registered Nurse', 'Melbourne, Victoria, Australia', 6, M, 'Nurse in Australia outside Sydney', ['clear']),
            ('Ruby', 'Walker', 'Nurse Practitioner', 'Brisbane, Queensland, Australia', 11, M, 'Nurse variant outside Sydney', ['title_variant']),
            ('Liam', "O'Connor", 'Enrolled Nurse', 'Canberra, Australian Capital Territory, Australia', 3, M, 'Enrolled nurse is a nursing role', ['title_variant']),
            ('Charlotte', 'Harris', 'Registered Nurse', 'Sydney, New South Wales, Australia', 8, N, 'In Sydney, which is excluded', ['excluded_location']),
            ('Noah', 'Wilson', 'Registered Nurse', 'Parramatta, New South Wales, Australia', 5, N, 'Parramatta is in Greater Sydney', ['excluded_location', 'trap']),
            ('Isla', 'Morgan', 'Registered Nurse', 'Auckland, New Zealand', 7, N, 'New Zealand, not Australia', ['wrong_location']),
            ('Harper', 'King', 'Healthcare Recruiter (Nursing)', 'Adelaide, South Australia, Australia', 4, N, 'Recruits nurses; not a nurse', ['trap', 'wrong_role']),
            ('Ella', 'Young', 'Student Nurse', 'Hobart, Tasmania, Australia', 0, N, 'Still a student', ['trap', 'experience_fail']),
            ('Oscar', 'Scott', 'Nursing Unit Manager', 'Perth, Western Australia, Australia', 15, B, 'Manages nurses; may or may not count as a nurse', ['title_ambiguous']),
            ('Amelia', 'Green', 'Registered Nurse', None, 9, B, 'Location not supplied', ['unknown_field']),
        ],
    },
    {
        'id': 'H2', 'holdout': True,
        'query': 'Data scientists in the United States or Canada with at most 4 years of experience, not in New York',
        'covers': 'Maximum experience, exclusion where "New York" may mean the city or the state, adjacent roles',
        'expected_filters': {'titles': ['Data Scientist'], 'countries': ['United States', 'Canada'], 'exclude_locations': ['New York'], 'experience_max': 4},
        'companies': ['Quillfeather AI', 'Granite Peak Insurance'],
        'people': [
            ('Ava', 'Robinson', 'Data Scientist', 'Austin, Texas, United States', 2, M, 'Data scientist in the US with 2 years', ['clear']),
            ('Ethan', 'Leblanc', 'Junior Data Scientist', 'Toronto, Ontario, Canada', 1, M, 'Junior is fine because the request sets a maximum', ['title_variant']),
            ('Mila', 'Novak', 'Data Scientist', 'New York, New York, United States', 3, N, 'In New York City, which is excluded', ['excluded_location']),
            ('Jacob', 'Stein', 'Data Scientist', 'Brooklyn, New York, United States', 2, N, 'Brooklyn is part of New York City', ['excluded_location', 'trap']),
            ('Henry', 'Clark', 'Senior Data Scientist', 'Seattle, Washington, United States', 9, N, '9 years exceeds the 4-year maximum', ['experience_fail']),
            ('Sophia', 'Turner', 'Data Analyst', 'Chicago, Illinois, United States', 2, N, 'Analyst, not data scientist', ['wrong_role']),
            ('Oliver', 'Evans', 'Data Scientist', 'London, England, United Kingdom', 2, N, 'Not in the US or Canada', ['wrong_location']),
            ('Lily', 'Adams', 'Data Scientist', 'Buffalo, New York, United States', 3, B, 'New York State but not the city; depends on what "New York" meant', ['excluded_location', 'title_ambiguous']),
            ('William', 'Tran', 'Machine Learning Engineer', 'Vancouver, British Columbia, Canada', 3, B, 'Closely related role; may or may not count', ['title_ambiguous']),
            ('Zara', 'Hughes', 'Data Scientist', 'Boston, Massachusetts, United States', '3 to 5 years', B, 'Band only partly within the 4-year maximum', ['experience_band_partial']),
            ('Leo', 'Gauthier', 'Data Science Intern', 'Montreal, Quebec, Canada', 0.5, B, 'Intern; experience fits but the role may not', ['title_ambiguous']),
        ],
    },
]

OPEN_QUESTIONS = [
    'Unknown fields (experience, location or level not supplied): include with benefit of the doubt, or exclude? Both current paths include them. They are labelled borderline here until you decide.',
    'Experience bands that only partly fit (for example "6 to 10 years" against 3-8): include or exclude?',
    'More senior titles than requested (Marketing Director for Marketing Manager, Senior VP for VP, Chief People Officer for HR Director): include?',
    'Managers of the requested role (Engineering Manager, Nursing Unit Manager): include?',
    'Adjacent roles (Software Engineer in Test, Machine Learning Engineer, Head of HR): include?',
    '"Not in New York": the city only, or the whole state?',
]


def build():
    companies, scenarios, used = [], [], 0
    for scenario in SCENARIOS:
        pool = [{'company_id': f"syn-{scenario['id'].lower()}-{index + 1}", 'name': name, 'leads': []}
                for index, name in enumerate(scenario['companies'])]
        keys = []
        for index, row in enumerate(scenario['people']):
            first, last, title, location, years, label, reason, tags, *rest = row
            extra = rest[0] if rest else {}
            company = pool[index % len(pool)]
            key = f"{scenario['id']}-{index + 1:02d}"
            company['leads'].append({
                'key': key, 'first_name': first, 'last_name': last, 'title': title, 'location': location,
                'department': extra.get('department'), 'management_level': extra.get('management_level'),
                'years_experience': years, 'headline': extra.get('headline'), 'summary': None, 'skills': None,
                'expected': {'label': label, 'reason': reason, 'pool': scenario['id'], 'tags': tags},
            })
            keys.append(key)
        for company in pool:
            company.update(industry=None, size=None, location=None, country=None, description=None,
                           provenance='synthetic_scenario')
            # Directory ids are company_id:index, so record each lead's id next to its stable key.
            for position, lead in enumerate(company['leads']):
                lead['expected']['directory_id'] = f"{company['company_id']}:{position}"
        companies += pool
        used += len(keys)
        scenarios.append({key: scenario[key] for key in ('id', 'holdout', 'query', 'covers', 'expected_filters')}
                         | {'lead_keys': keys})
    meta = {
        'purpose': 'Wider labelled test set for comparing LLM and JEV lead filter-and-score decisions across different targets.',
        'status': 'DRAFT labels proposed by Claude on 2026-10-21. Business review required before results are trusted.',
        'source': 'Synthetic. All people and companies are fictional; any resemblance to real people is coincidental. Safe to keep in Git.',
        'use': 'Load as the directory with DIRECTORY_FILE=lead_scoring_scenarios.json. Score each scenario only against its own lead_keys. Report holdout scenarios separately and never tune question rules against them.',
        'label_meaning': {'match': 'Should be selected for this scenario.',
                          'no_match': 'Should not be selected (wrong role, location, experience, department or seniority, or an excluded place).',
                          'borderline': 'Depends on a policy choice listed in open_questions; excluded from accuracy until decided.'},
        'ids': 'expected.directory_id is the id the backend assigns (company_id:index). key is stable for reviewers.',
        'people': used, 'open_questions': OPEN_QUESTIONS,
    }
    return {'_meta': meta, 'scenarios': scenarios, 'companies': companies}


def review_sheet(data):
    leads = {lead['key']: (lead, company['name']) for company in data['companies'] for lead in company['leads']}
    counts = {label: sum(lead['expected']['label'] == label for lead, _ in leads.values()) for label in (M, N, B)}
    lines = [
        '# Lead-scoring test set (draft for review)', '',
        'Source: [lead_scoring_scenarios.json](../datasets/lead_scoring_scenarios.json). Both files are generated by [build_lead_scoring_scenarios.py](../scripts/build_lead_scoring_scenarios.py); change labels there and rerun it.', '',
        '**Status: draft.** Claude proposed these labels on 21 October 2026. They define what "correct" means for the LLM vs JEV comparison, so someone who knows the business should check them. Change any label you disagree with and note why.', '',
        'All people and companies are fictional. No model calls were made to build this set.', '',
        '## Why this set exists', '',
        'The 19 October comparison used one target (sales leaders in the US, Canada or UK). JEV\'s question rules were written with that target in view, and department, seniority and experience were never exercised. This set adds different role families, explicit department and seniority fields, experience limits, exclusions, blank fields and traps. Two scenarios (H1, H2) are a **hold-out**: report them separately and never tune question rules against them.', '',
        f"**Totals:** {len(data['scenarios'])} scenarios, {len(leads)} people: {counts[M]} match, {counts[N]} no match, {counts[B]} borderline.", '',
        '## How to label', '',
        '- **match**: meets every requirement the query states.',
        '- **no match**: clearly contradicts a requirement (wrong role or function, place, excluded place, experience, department or seniority).',
        '- **borderline**: depends on a policy choice below. Excluded from accuracy until decided, then relabelled.',
        '- Judge the person\'s own current role and location. Never use the company or a past role.', '',
        '## Questions for the business', '',
        'Answering these turns most borderline labels into match or no match, and sets the JEV threshold.', '',
    ]
    lines += [f'{number}. {question}' for number, question in enumerate(OPEN_QUESTIONS, start=1)]
    for scenario in data['scenarios']:
        kind = 'hold-out' if scenario['holdout'] else 'development'
        filters = ', '.join(f'{key}={value}' for key, value in scenario['expected_filters'].items())
        lines += ['', f"## {scenario['id']} ({kind}): {scenario['query']}", '',
                  f"Covers: {scenario['covers']}.", '', f'Expected filters: `{filters}`', '',
                  '| Key | Title | Location | Experience | Dept / level | Label | Reason |',
                  '|---|---|---|---|---|---|---|']
        for key in scenario['lead_keys']:
            lead, _ = leads[key]
            meta = ' / '.join(str(lead[field]) for field in ('department', 'management_level') if lead[field]) or '—'
            years = '—' if lead['years_experience'] is None else lead['years_experience']
            label = {M: 'match', N: 'no match', B: '**borderline**'}[lead['expected']['label']]
            lines.append(f"| {key} | {lead['title']} | {lead['location'] or '—'} | {years} | {meta} | {label} | {lead['expected']['reason']} |")
    lines += ['', '## Running it', '',
              'Start the backend with `DIRECTORY_FILE=lead_scoring_scenarios.json`, then run '
              '`python scripts/eval_lead_scoring.py scenarios lead_scoring_scenarios.json <tag> jev` (or `llm`). '
              'It creates a target per scenario, scores only that scenario\'s people, checks the interpreted filters against '
              'the expected ones, and reports development and hold-out results separately in `data/eval_scen_<tag>.json`. '
              'It makes model calls.', '',
              'First results (21 October 2026, on these draft labels): JEV 100% on development and hold-out; '
              'the LLM 100% on development and 86.7% on hold-out (it accepted the Student Nurse and the Data Analyst).', '']
    return '\n'.join(lines)


data = build()
(ROOT / 'datasets' / 'lead_scoring_scenarios.json').write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
(ROOT / 'docs' / 'LEAD_SCORING_TEST_SET.md').write_text(review_sheet(data), encoding='utf-8')
print(data['_meta']['people'], 'people;', {label: sum(l['expected']['label'] == label for c in data['companies'] for l in c['leads']) for label in (M, N, B)})
