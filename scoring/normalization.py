"""Shared normalization for retrieval. Original source labels stay unchanged."""
import math
import re
import unicodedata

EMPTY = {'', 'unknown', 'n/a', 'na', 'none', 'null', 'not available', 'not provided', '-', '—'}
COUNTRIES = {'us': 'united states', 'u s': 'united states', 'usa': 'united states', 'u s a': 'united states',
             'united states of america': 'united states', 'uk': 'united kingdom', 'u k': 'united kingdom',
             'gb': 'united kingdom', 'great britain': 'united kingdom', 'in': 'india', 'uae': 'united arab emirates'}
LEVELS = {'vp': 'vice president', 'svp': 'senior vice president', 'evp': 'executive vice president',
          'cxo': 'c level', 'c suite': 'c level', 'c suite executive': 'c level',
          'individual contributor': 'individual contributor', 'ic': 'individual contributor'}
DEPARTMENTS = {'hr': 'human resources', 'it': 'information technology', 'r d': 'research and development',
               'sales department': 'sales', 'engineering department': 'engineering'}


def clean(value, limit=3000):
    if value is None:
        return None
    value = str(value).strip()
    return None if value.casefold() in EMPTY else value[:limit]


def normalized(value):
    value = unicodedata.normalize('NFKC', str(value or '')).casefold()
    return ' '.join(re.sub(r'[^\w]+', ' ', value).split())


def canonical_country(value):
    value = normalized(value)
    return COUNTRIES.get(value, value)


def canonical_level(value):
    value = normalized(value)
    return LEVELS.get(value, value)


def canonical_department(value):
    value = normalized(value)
    return DEPARTMENTS.get(value, value)


def experience(value):
    try:
        number = float(value) if value is not None and not isinstance(value, bool) else None
        return number if number is not None and math.isfinite(number) and 0 <= number <= 100 else None
    except (ValueError, TypeError):
        return None


def person_experience(person):
    value = person.get('experience_years')
    if value is None:
        value = person.get('years_experience')
    return experience(value)


def title_tokens(value):
    value = normalized(value)
    replacements = [(r'\bsenior vice president\b', 'svp'), (r'\bexecutive vice president\b', 'evp'),
                    (r'\bvice president\b', 'vp'), (r'\bchief executive officer\b', 'ceo'),
                    (r'\bchief technology officer\b', 'cto'), (r'\bchief financial officer\b', 'cfo'),
                    (r'\bchief operating officer\b', 'coo'), (r'\bsr\b', 'senior'), (r'\bjr\b', 'junior')]
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value)
    skip = {'of', 'the', 'and', 'for'}
    return {token[:-1] if token.endswith('s') and len(token) > 4 and token not in {'sales', 'business', 'operations'} else token
            for token in value.split() if token not in skip}
