"""Raw Laya choice request/response contracts and decision provenance."""
from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field

DecisionSource = Literal["model_probability", "model_score", "explicit_rule", "fixed_mapping", "unavailable"]


class QuestionSpec(BaseModel):
    """Specification of a single decision question for Laya."""
    type: str = Field(
        default="choice",
        description="Type of decision question. Defaults to 'choice'."
    )
    instructions: str = Field(
        ...,
        description="The question or directive the decision model must evaluate."
    )
    criteria: Union[Dict[str, str], List[str]] = Field(
        ...,
        description="Dictionary of label -> description, or list of labels."
    )


class DecisionRequest(BaseModel):
    """Request payload for the raw /decision endpoint."""
    state: str = Field(
        ...,
        description="The contextual state or prompt for the decision engine."
    )
    questions: Dict[str, QuestionSpec] = Field(
        ...,
        description="Dictionary mapping question IDs to their QuestionSpec."
    )
    model: Optional[str] = Field(
        default="typed-decisions",
        description="Model identifier (e.g. 'typed-decisions' or default router)."
    )


class ChoiceAnswer(BaseModel):
    """Normalized response for a single choice question."""
    choice: str = Field(..., description="Selected winner label.")
    confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Model score, not verified accuracy. Null for explicit rules or unavailable scores.")
    source: DecisionSource = Field(default="model_probability", description="Origin of the decision and its score.")
    probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Probability distribution across all candidate options."
    )


class DecisionResponse(BaseModel):
    """Response payload returned by /decision."""
    model: str = Field(..., description="The model that executed the decision.")
    answers: Dict[str, ChoiceAnswer] = Field(
        ...,
        description="Decision answers keyed by question ID."
    )
    latency_ms: float = Field(..., description="Inference latency in milliseconds.")
