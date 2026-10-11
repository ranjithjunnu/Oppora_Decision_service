"""Read-only search of the local directory. No enrichment or live discovery."""
import json
from functools import lru_cache
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[1] / 'datasets' / 'company_directory.json'


def clean(value, limit=3000):
    return str(value).strip()[:limit] if value is not None and str(value).strip() else None


def text(*values):
    return ' '.join(str(v or '') for v in values).casefold()


@lru_cache(maxsize=1)
def directory():
    data = json.loads(DIRECTORY.read_text(encoding='utf-8'))
    companies, people = [], []
    for ci, raw in enumerate(data['companies']):
        company_id = str(raw.get('company_id', ci))
        size = raw.get('employee_count', raw.get('size'))
        count = int(size) if isinstance(size, (str, int)) and not isinstance(size, bool) and str(size).isdigit() else None
        if count is not None and count > 1_000_000_000:
            count = None
        company = {
            'id': company_id, 'name': clean(raw.get('name'), 200) or 'Unnamed company',
            'industry': clean(raw.get('industry'), 150), 'location': clean(raw.get('location'), 300),
            'country': clean(raw.get('country'), 100), 'size': clean(raw.get('size'), 100),
            'description': clean(raw.get('description')), 'people_count': len(raw.get('leads') or []),
            'source': 'saved_company' if raw.get('provenance') == 'oppora_saved' else 'sample_company',
        }
        companies.append((company, text(company['name'], company['industry'], raw.get('domain'))))
        for pi, person in enumerate(raw.get('leads') or []):
            person_id = f'{company_id}:{pi}'
            item = {
                'id': person_id, 'company_id': company_id,
                'name': clean(text_name := ' '.join(str(person.get(k) or '') for k in ('first_name', 'last_name')), 200) or 'Unnamed person',
                'title': clean(person.get('title'), 500), 'company_name': company['name'],
                'location': clean(person.get('location'), 300), 'source': 'sample_person',
                'lead': {
                    'id': person_id, 'company': {
                        'name': company['name'], 'industry': company['industry'], 'country': company['country'],
                        'employee_count': count, 'description': company['description'],
                        'technologies': None, 'technology_inventory_complete': False,
                    },
                    'person': {'title': clean(person.get('title'), 500), 'summary': clean(person.get('headline')),
                               'department': clean(person.get('department'), 100), 'seniority': clean(person.get('management_level'), 100)},
                    'signals': {'hiring': None, 'recent_funding_days': None, 'observed_on': None},
                },
            }
            people.append((item, text(text_name, item['title'], item['company_name'], person.get('department'))))
    return companies, people


def search(kind, query='', location='', company_id=None, offset=0, limit=20):
    companies, people = directory()
    records = companies if kind == 'companies' else people
    terms = query.casefold().split()
    place = location.strip().casefold()
    matches = [item for item, index in records
               if all(term in index for term in terms)
               and (not place or place in text(item.get('location'), item.get('country')))
               and (company_id is None or item.get('company_id') == company_id)]
    return {'items': matches[offset:offset + limit], 'total': len(matches), 'offset': offset, 'limit': limit,
            'source': 'local_directory', 'sample_people': True}
