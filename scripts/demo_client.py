"""
demo_client.py — Standalone Demo Runner for Oppora GTM Agent.

Demonstrates planning using local Laya predictions, explicit rules and templates.
Runs directly in-process; it does not execute tools or call the HTTP server.
"""

import json
from models.planning import GTMPlanRequest
from agents.gtm_agent import get_gtm_agent


DEMO_PROMPTS = [
    "Find IT services companies in India",
    "Find VP of engineering in the USA",
    "Find SaaS founders in California and generate an outbound workflow.",
    "Enrich existing company records with missing firmographics.",
    "Classify incoming sales replies and out-of-office responses.",
    "Find companies",
]


def format_score(score, source):
    return f"{score:.2%} ({source}; not verified accuracy)" if score is not None else f"N/A ({source}; no model score)"


def print_banner(text: str) -> None:
    width = 76
    print("\n" + "=" * width)
    print(f" {text}")
    print("=" * width)


def run_demo() -> None:
    print_banner("OPPORA STANDALONE AI DECISION SERVICE (POWERED BY LAYA)")
    print("Zero External LLM Dependency (No OpenAI, No Claude, No Hosted JEV API)")
    print("All decisions, routing, and workflow planning executed locally on PyTorch.\n")
    print("Explicit rules and fixed tool mappings are labelled separately from Laya scores.")

    agent = get_gtm_agent()

    for idx, prompt in enumerate(DEMO_PROMPTS, start=1):
        print_banner(f"TEST CASE {idx}: \"{prompt}\"")

        request = GTMPlanRequest(prompt=prompt)
        plan = agent.plan_workflow(request)

        print(f"Workflow ID       : {plan.workflow_id}")
        print(f"Total Planning Latency: {plan.total_latency_ms:.2f} ms")
        print(f"Decision Model    : {plan.model_used} (Self-Hosted: {plan.standalone})")
        print(f"Plan Status       : {plan.status}")
        if plan.clarification:
            print(f"Clarification     : {plan.clarification}")
        print("-" * 76)

        print("\n[STAGE 1: INTENT & TARGET DECOMPOSITION]")
        print(f"  Intent : {plan.intent.intent} | {format_score(plan.intent.confidence, plan.intent.source)}")
        for field in ("role", "industry", "geography"):
            target = plan.target_scope
            print(f"  {field.title()} : {getattr(target, field)} | {format_score(getattr(target, field + '_confidence'), getattr(target, field + '_source'))}")

        print("\n[STAGE 2: PLANNED WORKFLOW STEPS & TOOL SELECTION]")
        for step in plan.steps:
            print(f"  Step {step.step_number}: [{step.action.upper()}]")
            print(f"         Selected Tool : {step.tool} | {format_score(step.confidence, step.source)}")
            print(f"         Tool Purpose  : {step.tool_description}")
            print(f"         Reasoning     : {step.reasoning}")

        print("\n[STAGE 3: STRUCTURED DEMO JSON INCLUDING ORIGINAL LAYA PREDICTIONS]")
        formatted_json = json.dumps(plan.model_dump(), indent=2)
        print(formatted_json)

    print_banner("DEMO COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    run_demo()
