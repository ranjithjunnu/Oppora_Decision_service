"""Authored GTM intents, demo tools and fixed workflow templates; no execution."""

OPPORA_TOOLS = {
    "company_finder": "Discover companies matching the requested industry and location.",
    "contact_hunter": "Find people matching requested roles and company constraints.",
    "verify_emails": "Check existing or discovered email addresses for deliverability.",
    "smart_lead_scoring": "Assess lead fit against an explicitly provided customer profile.",
    "company_enrichment": "Fill missing firmographics on existing company or lead records.",
    "reply_ora": "Classify incoming replies, bounces and out-of-office messages. No reply writing in this demo.",
    "campaign_sequencer": "Plan an approved outreach sequence. No email writing or sending in this demo.",
}


GTM_INTENTS = {
    "account_discovery": "Find NEW COMPANIES or organizations. No individual people or outreach requested.",
    "contact_hunting": "Find PEOPLE, job titles or contact details. Companies may be constraints; a company list is not required.",
    "outbound_pipeline": "Explicitly build an OUTBOUND or OUTREACH workflow/campaign, including discovery and qualification.",
    "enrichment_only": "Fill MISSING FIELDS on EXISTING company or lead records. Do not discover new accounts.",
    "crm_cleanup": "VERIFY or CLEAN existing contact/email records, such as invalid addresses or duplicate records.",
    "inbound_triage": "CLASSIFY INCOMING replies, bounces or out-of-office messages. Do not start a new outbound workflow.",
}


WORKFLOW_BLUEPRINTS = {
    "account_discovery": [
        {"action": "discover_companies", "preferred_tool": "company_finder", "reasoning": "Discover companies using only the requested target constraints."},
    ],
    "contact_hunting": [
        {"action": "find_decision_makers", "preferred_tool": "contact_hunter", "reasoning": "Find people matching the requested roles and company constraints."},
        {"action": "verify_contact_data", "preferred_tool": "verify_emails", "reasoning": "Verify the requested email/contact data."},
    ],
    "outbound_pipeline": [
        {"action": "discover_companies", "preferred_tool": "company_finder", "reasoning": "Discover target accounts for the requested outbound workflow."},
        {"action": "find_decision_makers", "preferred_tool": "contact_hunter", "reasoning": "Find relevant contacts within the target accounts."},
        {"action": "verify_contact_data", "preferred_tool": "verify_emails", "reasoning": "Check contact deliverability before any future outreach."},
        {"action": "qualify_leads", "preferred_tool": "smart_lead_scoring", "reasoning": "Assess lead fit against the requested customer profile."},
    ],
    "enrichment_only": [
        {"action": "enrich_records", "preferred_tool": "company_enrichment", "reasoning": "Fill missing fields on existing records without discovering new accounts."},
    ],
    "crm_cleanup": [
        {"action": "verify_contact_data", "preferred_tool": "verify_emails", "reasoning": "Identify invalid email/contact records for review. This demo does not delete records."},
    ],
    "inbound_triage": [
        {"action": "classify_incoming_replies", "preferred_tool": "reply_ora", "reasoning": "Classify incoming messages without generating replies or starting outreach."},
    ],
}
