"""The supported scoring fields; independent of GTM intent taxonomy."""
POLICY_VERSION = 'lead-score-v2'
PROMPT_VERSION = 'llm-criterion-v2'
WEIGHTS = {'high': 3, 'medium': 2, 'low': 1}
FIELDS = {
    'company.industry': {'label': 'Industry', 'axis': 'fit', 'operators': ['in']},
    'company.country': {'label': 'Country', 'axis': 'fit', 'operators': ['in']},
    'company.employee_count': {'label': 'Employee count', 'axis': 'fit', 'operators': ['between', 'gte', 'lte']},
    'company.technologies': {'label': 'Technologies', 'axis': 'fit', 'operators': ['contains_any', 'contains_all']},
    'company.description': {'label': 'Business description', 'axis': 'fit', 'operators': ['semantic']},
    'person.title': {'label': 'Job title', 'axis': 'fit', 'operators': ['semantic']},
    'person.summary': {'label': 'Role responsibilities', 'axis': 'fit', 'operators': ['semantic']},
    'person.seniority': {'label': 'Seniority', 'axis': 'fit', 'operators': ['in']},
    'person.department': {'label': 'Department', 'axis': 'fit', 'operators': ['in']},
    'signals.hiring': {'label': 'Hiring', 'axis': 'intent', 'operators': ['eq']},
    'signals.recent_funding_days': {'label': 'Funding recency (days)', 'axis': 'intent', 'operators': ['lte']},
}
OUTCOMES = {
    'match': 'The supplied facts clearly satisfy the requirement.',
    'partial': 'The supplied facts explicitly satisfy part, but not all, of the requirement. Not uncertainty.',
    'miss': 'The supplied facts explicitly contradict the requirement. Absence of information is not a miss.',
    'unknown': 'The facts are missing, ambiguous, conflicting or insufficient to decide.',
}
