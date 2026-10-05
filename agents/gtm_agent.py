"""Local Laya classification with explicit-request rules and workflow templates.

The service plans actions; it does not execute Oppora tools or generate emails.
"""

import re
import time
import uuid
from typing import Optional

from engines.laya_engine import get_engine
from models.decision import ChoiceAnswer, QuestionSpec
from models.planning import GTMPlanRequest, IntentDecision, TargetScope, WorkflowPlan, WorkflowStep
from taxonomy.geography import GEOGRAPHIES, GEOGRAPHY_PATTERNS
from taxonomy.industries import INDUSTRIES, INDUSTRY_PATTERNS
from taxonomy.titles import ROLE_PATTERNS, TARGET_ROLES
from workflows.catalog import GTM_INTENTS, OPPORA_TOOLS, WORKFLOW_BLUEPRINTS

# A conservative demo guardrail, not an empirically calibrated accuracy cutoff.
# Explicit rules do not use this threshold. Tune against labelled examples later.
MIN_INTENT_PROBABILITY = 0.5


def matches(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.I) is not None


def explicit_choice(label: str) -> ChoiceAnswer:
    # A deterministic match is not a model probability.
    return ChoiceAnswer(choice=label, confidence=None, source="explicit_rule")


def requested_intent(prompt: str):
    """Recognize the small set of explicit operations supported by this demo."""
    # Do not treat negated outreach as a request to start a campaign.
    text = re.sub(
        r"\b(?:do not|don't|no|without|not)\s+(?:any\s+)?"
        r"(?:outreach|outbound(?:\s+campaigns?)?|campaigns?|send(?:ing)?\s+emails?)\b",
        "", prompt, flags=re.I,
    )
    searching = matches(r"\b(?:find|search|discover|list|show|identify|look for|get)\b|\bbuild\s+(?:a\s+)?list\b", text)
    people = any(matches(pattern, text) for pattern in ROLE_PATTERNS.values())
    companies = matches(r"\b(?:companies|company|businesses|organizations|accounts)\b", text)
    if matches(r"\b(?:classify|triage|categorize|process)\b", text) and matches(
        r"\b(?:incoming|inbound|replies|reply|out[ -]of[ -]office|bounces?)\b", text
    ):
        return "inbound_triage", "Classifying incoming messages was explicitly requested."
    if matches(r"\b(?:outbound|outreach|prospecting)\b", text) or matches(
        r"\b(?:build|create|launch|generate|start|plan)\b.*\b(?:campaigns?|email sequences?)\b", text
    ):
        return "outbound_pipeline", "An outbound/outreach workflow was explicitly requested."
    records = matches(r"\b(?:crm|records?|contacts?|leads?|companies|company|emails?|addresses?|database)\b", text)
    if records and matches(r"\benrich(?:ment|ing)?\b|\b(?:fill|append)\b.*\bmissing\b", text):
        return "enrichment_only", "Filling missing fields on existing records was explicitly requested."
    if records and (matches(r"\b(?:clean(?:up)?|cleanse|purge|deduplicat(?:e|ion)|remove invalid)\b", text) or (
        not searching and matches(r"\b(?:verify|verification|validate|deliverability)\b", text)
    )):
        return "crm_cleanup", "Verification or cleanup of existing contact records was explicitly requested."
    if searching and (people or matches(r"\bemails?\b", text)):
        return "contact_hunting", "Finding people or contact details was explicitly requested."
    if searching and companies:
        return "account_discovery", "Finding companies was explicitly requested without people or outreach."
    return None, None


def resolve_scope(prompt, answer, patterns, field):
    """Preserve recognized explicit values and leave absent fields unspecified."""
    hits = [label for label, pattern in patterns.items() if matches(pattern, prompt)]
    # Specific roles/industries override their broader overlapping descriptions.
    if field == "role" and len(hits) > 1 and "general_staff" in hits:
        hits.remove("general_staff")
    if field == "industry" and len(hits) > 1:
        hits = [label for label in hits if label not in {"general_business", "other"}] or hits
    if field == "geography" and "california_west_us" in hits and "us_nationwide" in hits:
        hits.remove("us_nationwide")
    if not hits and field == "geography":
        # Detect a location phrase outside the small menu instead of replacing it
        # with a model-guessed US location. Industry/source phrases are not places.
        location = re.search(r"\b(?:in|across|within|based in|located in)\s+(.+?)(?:[.,;]|$)", prompt, re.I)
        if location:
            candidate = location.group(1)
            source_phrase = matches(r"\b(?:crm|database|lists?|records?|our|my|existing)\b", candidate)
            industry_phrase = any(matches(pattern, candidate) for pattern in INDUSTRY_PATTERNS.values())
            role_phrase = any(matches(pattern, candidate) for pattern in ROLE_PATTERNS.values())
            if not source_phrase and not industry_phrase and not role_phrase:
                hits = ["other"]
    if not hits:
        return explicit_choice("none_specified"), f"No supported target {field} was explicitly stated.", None
    if len(hits) == 1:
        return explicit_choice(hits[0]), f"Explicit {field} matched '{hits[0]}'.", None
    # The current schema has one category per field. Do not silently discard a
    # request for several distinct categories, such as India and the USA.
    warning = f"Multiple {field} categories were requested: {', '.join(hits)}."
    return answer, warning, warning


class OpporaGTMAgent:
    def __init__(self) -> None:
        self.engine = get_engine()

    def plan_workflow(self, request: GTMPlanRequest) -> WorkflowPlan:
        start = time.perf_counter()
        prompt = request.prompt
        questions = {
            "intent": QuestionSpec(instructions="Choose the requested operation: new companies, people, outbound campaign, missing-field enrichment, existing-record cleanup, or incoming-message classification. Do not assume outreach.", criteria=GTM_INTENTS),
            "role": QuestionSpec(instructions="Choose only a target job role explicitly stated. Otherwise choose none_specified.", criteria=TARGET_ROLES),
            "industry": QuestionSpec(instructions="Choose only the stated industry. Choose none_specified if absent, other if outside the menu. Job roles do not imply industries.", criteria=INDUSTRIES),
            "geography": QuestionSpec(instructions="Choose only the stated location. Choose none_specified if absent, other if outside the menu. Do not assume the United States.", criteria=GEOGRAPHIES),
        }
        answers, _ = self.engine.decide(prompt, questions)
        intent = answers["intent"]
        label, rule_reason = requested_intent(prompt)
        if label:
            intent = explicit_choice(label)

        warnings = []
        status = "planned"
        clarification = None
        if not label and (intent.confidence is None or intent.confidence < MIN_INTENT_PROBABILITY):
            status = "needs_clarification"
            clarification = "Do you want to find companies, find people, plan outbound, enrich existing records, clean contacts, or classify incoming replies?"
            warnings.append("The model's intent score is below the conservative demo threshold; no workflow was expanded.")

        scope = {}
        for field, patterns in (("role", ROLE_PATTERNS), ("industry", INDUSTRY_PATTERNS), ("geography", GEOGRAPHY_PATTERNS)):
            answer, reasoning, warning = resolve_scope(prompt, answers[field], patterns, field)
            scope[field] = answer.choice
            scope[f"{field}_confidence"] = answer.confidence
            scope[f"{field}_source"] = answer.source
            scope[f"{field}_reasoning"] = reasoning
            if warning or answer.choice == "other":
                status = "needs_clarification"
                warnings.append(warning or f"The requested {field} is outside the demo's supported categories.")
                clarification = "Please choose one supported category per target field, or extend the demo taxonomy to represent your request."

        blueprint = WORKFLOW_BLUEPRINTS.get(intent.choice)
        if blueprint is None:
            status = "unsupported"
            clarification = "This intent has no configured workflow. No outbound fallback was applied."
            warnings.append(f"Unsupported intent: {intent.choice}.")
        if blueprint and intent.choice == "contact_hunting" and not matches(
            r"\b(?:emails?|verify|verification|validate|deliverability)\b", prompt
        ):
            blueprint = [step for step in blueprint if step["action"] != "verify_contact_data"]

        steps = []
        if status == "planned":
            for number, template in enumerate(blueprint, 1):
                tool = template["preferred_tool"]
                steps.append(WorkflowStep(
                    step_number=number, action=template["action"], tool=tool,
                    tool_description=OPPORA_TOOLS[tool], confidence=None,
                    source="fixed_mapping",
                    reasoning=f"{template['reasoning']} Tool '{tool}' comes from the configured blueprint, not a model tool-selection score.",
                ))

        return WorkflowPlan(
            workflow_id=f"wf_{uuid.uuid4().hex[:8]}", user_prompt=prompt,
            intent=IntentDecision(
                intent=intent.choice, confidence=intent.confidence,
                source=intent.source, probabilities=intent.probabilities,
                reasoning=(rule_reason + " Selected using an explicit-text rule.") if label else f"Laya selected this category: {GTM_INTENTS.get(intent.choice, 'unsupported intent')}. Its score is not verified accuracy.",
            ),
            target_scope=TargetScope(**scope), steps=steps, status=status,
            clarification=clarification, warnings=warnings,
            model_predictions=answers,
            total_latency_ms=round((time.perf_counter() - start) * 1000, 2),
            model_used=self.engine.default_model, standalone=True,
        )


_agent_instance: Optional[OpporaGTMAgent] = None


def get_gtm_agent() -> OpporaGTMAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = OpporaGTMAgent()
    return _agent_instance
