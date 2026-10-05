"""Concise manual-evaluation criteria; independent of legacy planner policy."""
from models.evaluation import DecisionCriterion


def gtm_intent_criterion() -> DecisionCriterion:
    """Keep the six existing labels/order with a compact, complete question."""
    return DecisionCriterion(
        id='gtm_intent',
        instructions=(
            'Which operation does the query explicitly request? '
            'Classify the requested action, not company details. '
            'Finding people at companies is contact hunting. '
            'Choose outbound only when outreach or a campaign workflow is requested.'
        ),
        choices={
            'account_discovery': 'Find new companies or organizations, not people.',
            'contact_hunting': 'Find people, job roles or contact details; companies can be filters.',
            'outbound_pipeline': 'Build an outbound or outreach campaign workflow.',
            'enrichment_only': 'Fill missing fields in existing company or contact records.',
            'crm_cleanup': 'Clean, deduplicate or verify existing contact or email records.',
            'inbound_triage': 'Classify incoming replies, bounces or out-of-office messages.',
        },
    )
