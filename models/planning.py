"""Existing GTM planning contracts; these are not lead-scoring evaluation models."""
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator
from .decision import ChoiceAnswer, DecisionSource

class GTMPlanRequest(BaseModel):
    """User request sent to the Oppora GTM Agent."""
    prompt: str = Field(
        ...,
        min_length=1,
        example="Find SaaS founders in California and generate an outbound workflow.",
        description="User's high-level GTM, prospecting, or outbound objective."
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata such as user_id, tier, or CRM settings."
    )

    @field_validator("prompt")
    @classmethod
    def nonempty_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Prompt must contain a request, not only whitespace.")
        return value


class IntentDecision(BaseModel):
    """Decomposed intent category for the GTM request."""
    intent: str = Field(..., description="Selected GTM intent category.")
    confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Model score; null for a deterministic rule. Not calibrated accuracy.")
    source: DecisionSource = Field(default="model_probability")
    probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Probability breakdown across intent categories."
    )
    reasoning: str = Field(..., description="Why this intent was selected.")


class TargetScope(BaseModel):
    """Target audience parameters extracted via discrete decisions."""
    role: str = Field(..., description="Target role or seniority level.")
    role_confidence: Optional[float] = Field(default=None, description="Model score; null for an explicit rule.")
    role_source: DecisionSource = Field(default="model_probability")
    role_reasoning: str = Field(default="", description="Why this role category was selected.")
    industry: str = Field(..., description="Target industry vertical.")
    industry_confidence: Optional[float] = Field(default=None, description="Model score; null for an explicit rule.")
    industry_source: DecisionSource = Field(default="model_probability")
    industry_reasoning: str = Field(default="", description="Why this industry category was selected.")
    geography: str = Field(..., description="Target geographical focus.")
    geography_confidence: Optional[float] = Field(default=None, description="Model score; null for an explicit rule.")
    geography_source: DecisionSource = Field(default="model_probability")
    geography_reasoning: str = Field(default="", description="Why this geography category was selected.")


class WorkflowStep(BaseModel):
    """A planned step; this demo does not execute tools."""
    step_number: int = Field(..., description="Execution sequence index (1-indexed).")
    action: str = Field(..., description="Semantic action to perform.")
    tool: str = Field(..., description="Oppora tool selected to execute this action.")
    tool_description: str = Field(..., description="Description of the chosen tool.")
    confidence: Optional[float] = Field(default=None, description="Null for fixed tool mappings; no model score is fabricated.")
    source: DecisionSource = Field(default="fixed_mapping")
    reasoning: str = Field(..., description="Operational reasoning for this step.")


class WorkflowPlan(BaseModel):
    """Complete structured workflow returned by Oppora GTM Planner Agent."""
    workflow_id: str = Field(..., description="Unique generated plan identifier.")
    user_prompt: str = Field(..., description="Original user prompt received.")
    intent: IntentDecision = Field(..., description="Classified intent.")
    target_scope: TargetScope = Field(..., description="Discovered target criteria.")
    steps: List[WorkflowStep] = Field(
        ...,
        description="Ordered sequence of actions and tools."
    )
    status: Literal["planned", "needs_clarification", "unsupported"] = Field(default="planned", description="Only planned responses contain usable workflow steps.")
    clarification: Optional[str] = Field(default=None)
    warnings: List[str] = Field(default_factory=list)
    model_predictions: Dict[str, ChoiceAnswer] = Field(default_factory=dict, description="Original Laya predictions before explicit rules; useful for evaluating the model separately.")
    total_latency_ms: float = Field(
        ...,
        description="End-to-end multi-step planning latency in milliseconds."
    )
    model_used: str = Field(..., description="Laya checkpoint used for raw predictions; rules and templates assemble the plan.")
    standalone: bool = Field(
        default=True,
        description="True indicates 100% self-hosted local decision execution without external LLMs."
    )
