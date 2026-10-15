"""Snapshot directory facts without inferring missing person fields."""
import json

from .discovery import DIRECTORY
from .normalization import clean, person_experience


def selected_people(identifiers):
    wanted = set(identifiers)
    found = {}
    data = json.loads(DIRECTORY.read_text(encoding='utf-8'))
    for ci, company in enumerate(data['companies']):
        company_id = str(company.get('company_id', ci))
        for pi, person in enumerate(company.get('leads') or []):
            identifier = f'{company_id}:{pi}'
            if identifier not in wanted:
                continue
            years = person_experience(person)
            found[identifier] = {
                'id': identifier, 'company_id': company_id,
                'company_name': clean(company.get('name'), 200) or 'Unnamed company',
                'company_description': clean(company.get('description')),
                'name': clean(' '.join(str(person.get(k) or '') for k in ('first_name', 'last_name')), 200) or 'Unnamed person',
                'title': clean(person.get('title'), 500), 'country': clean(person.get('country'), 100),
                'location': clean(person.get('location'), 300), 'department': clean(person.get('department'), 100),
                'management_level': clean(person.get('management_level'), 100), 'experience_years': years,
                'headline': clean(person.get('headline')), 'summary': clean(person.get('summary')),
                'skills': clean(', '.join(map(str, person['skills'])) if isinstance(person.get('skills'), list) else person.get('skills')),
                'source': 'sample_person',
            }
    if wanted != set(found):
        raise ValueError('Some selected people are no longer in the local directory. Refresh the directory and select them again.')
    return [found[identifier] for identifier in identifiers]


def missing_facts(person):
    labels = {'country': 'Country', 'location': 'Location', 'department': 'Department',
              'management_level': 'Seniority', 'experience_years': 'Experience', 'headline': 'Headline'}
    return [label for field, label in labels.items() if person.get(field) is None]
