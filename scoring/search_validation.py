"""Validate source-backed requirements before querying the directory."""
import re

from .normalization import canonical_level, normalized


def explicit_secondary(field, query, values, has_titles):
    text = normalized(query)
    if field == 'departments':
        if re.search(r'\b(department|dept|function|division)\b', text):
            return True
        # "people in Sales" / "VPs in Sales" explicitly scopes a function,
        # whereas "VP of Sales" already expresses the requested job title.
        return any(re.search(r'\b(?:in|within|from) (?:the )?' + re.escape(normalized(value)) + r'(?!\w)', text)
                   for value in values)
    if field == 'management_levels':
        if re.search(r'\b(seniority|management level|levels?)\b', text):
            return True
        if any(re.search(r'\b(?:at least|minimum) (?:a )?' + re.escape(normalized(value)) + r'(?!\w)', text)
               or re.search(r'\b' + re.escape(normalized(value)) + r' (?:and|or) (?:above|higher)\b', text)
               for value in values):
            return True
        return not has_titles and any(normalized(value) in text or canonical_level(value) in text for value in values)
    return True


def validate_plan(plan, query):
    filters = plan.filters.model_dump(mode='json')
    evidence = {}
    repairs, errors = [], []
    query_text = ' '.join(query.casefold().split())
    for requirement in plan.requirements:
        quote = ' '.join(requirement.quote.casefold().split())
        if quote and quote in query_text:
            evidence.setdefault(requirement.field, []).append(requirement.quote)
    for field in ('departments', 'management_levels'):
        if filters[field] and not explicit_secondary(field, query, filters[field], bool(filters['titles'])):
            repairs.append({'field': field, 'removed_values': filters[field],
                            'reason': 'This was inferred from the role, not requested as a separate restriction.'})
            filters[field] = []
    active = [field for field, value in filters.items() if value is not None and value != []]
    if plan.company_names:
        active.append('company_names')
    for field in active:
        if field not in evidence:
            errors.append(f'{field} has no supporting quote from the user request.')
    # Empty plans are allowed only for an explicit broad audience request.
    if not active and not re.search(r'\b(all|everyone|anyone|any people|any leads)\b', query_text):
        errors.append('The request did not produce a supported search requirement. Ask for a role, location or company.')
    return filters, {'status': 'needs_repair' if errors else 'validated', 'evidence': evidence,
                     'removed_inferred_filters': repairs, 'errors': errors}
