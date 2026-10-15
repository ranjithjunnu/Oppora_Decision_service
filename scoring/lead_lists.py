"""Named reusable lists holding immutable member facts and revision history."""
from uuid import uuid4

from . import repository
from .normalizer import selected_people
from .trace import now


def resolve_members(request):
    search = repository.get('search', request.search_id) if request.search_id else None
    if request.search_id and search is None:
        raise ValueError('The search was not found. Search again before saving people.')
    if search:
        by_id = {person['id']: person for person in search['people'] + search.get('review_people', [])}
        # Save-all always means confirmed search results. Review candidates
        # require explicit selection so unknown locations are never concealed.
        identifiers = request.lead_ids if request.lead_ids is not None else [person['id'] for person in search['people']]
        if any(identifier not in by_id for identifier in identifiers):
            raise ValueError('Some selected people do not belong to this search. Refresh and select them again.')
        people = [by_id[identifier] for identifier in identifiers]
    else:
        people = selected_people(request.lead_ids)
    if not people:
        raise ValueError('Choose at least one person to save.')
    return people, search


def create_list(request):
    people, search = resolve_members(request)
    target_id = request.targeting_id or (search['targeting']['id'] if search else None)
    target = repository.get('target', target_id) if target_id else None
    if target_id and target is None:
        raise ValueError('Apply your targeting again before saving the list.')
    timestamp = now()
    document = {'id': 'list_' + uuid4().hex, 'name': request.name, 'version': 1,
                'created_at': timestamp, 'updated_at': timestamp, 'people': people,
                'member_count': len(people), 'targeting': target,
                'search_id': search['id'] if search else None, 'search_query': search['query'] if search else None,
                'latest_run_id': None}
    repository.save('lead_list', document)
    return document


def append_members(identifier, request):
    people, _ = resolve_members(request)

    def change(document):
        existing = {person['id'] for person in document['people']}
        added = [person for person in people if person['id'] not in existing]
        if len(document['people']) + len(added) > 1000:
            raise ValueError('A local list can contain up to 1,000 people. Save these people to another list.')
        if added:
            document['people'].extend(added)
            document.update(member_count=len(document['people']), version=document['version'] + 1, updated_at=now())
    return repository.mutate_list(identifier, request.expected_version, change)


def edit_list(identifier, request):
    def change(document):
        remove = set(request.remove_ids)
        if not remove <= {person['id'] for person in document['people']}:
            raise ValueError('Some selected people are no longer in this list. Refresh the list.')
        people = [person for person in document['people'] if person['id'] not in remove]
        name = request.name if request.name is not None else document['name']
        if name != document['name'] or len(people) != len(document['people']):
            document.update(name=name, people=people, member_count=len(people), version=document['version'] + 1, updated_at=now())
    return repository.mutate_list(identifier, request.expected_version, change)
