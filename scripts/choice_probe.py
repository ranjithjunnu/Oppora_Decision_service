from laya import Router

router = Router()

state = """
User wants to find SaaS founders in California
and create an outbound workflow.
"""

questions = {
    "next_action": {
        "type": "choice",
        "instructions": "What should the agent do first?",
        "criteria": {
            "search_leads": "Search for people matching the requested target.",
            "search_companies": "Search for companies matching the request.",
            "generate_email": "Generate an email for the user.",
            "create_campaign": "Create an outbound campaign."
        }
    }
}

result = router.predict(
    state,
    questions,
    model="typed-decisions"
)

print(result)
