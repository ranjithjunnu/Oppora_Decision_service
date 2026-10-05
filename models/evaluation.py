"""Provider-independent contracts for one manually submitted decision case."""
from datetime import datetime, timezone
import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator


class DecisionCriterion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=100)
    instructions: str = Field(min_length=1, max_length=4000)
    choices: dict[str, str] = Field(min_length=2, max_length=20)

    @field_validator('id', 'instructions')
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Must not be blank')
        return value.strip()

    @field_validator('choices')
    @classmethod
    def bounded_choices(cls, value: dict[str, str]) -> dict[str, str]:
        for label, description in value.items():
            if not label.strip() or label != label.strip() or len(label) > 100:
                raise ValueError('Choice labels must be nonblank, trimmed and at most 100 characters')
            if not description.strip() or len(description) > 1000:
                raise ValueError('Choice descriptions must be nonblank and at most 1000 characters')
        return value


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str | None = Field(default=None, min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=8000)
    structured_input: dict[str, JsonValue] | None = None
    context: str | None = Field(default=None, max_length=12000)
    criterion: DecisionCriterion | None = None

    @field_validator('query')
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Enter a nonblank query')
        return value.strip()

    @model_validator(mode='after')
    def bounded_json(self):
        if self.structured_input is not None:
            try:
                encoded = json.dumps(self.structured_input, ensure_ascii=False, allow_nan=False)
            except ValueError as exc:
                raise ValueError('Structured input must contain finite JSON values') from exc
            if len(encoded) > 20000:
                raise ValueError('Structured input exceeds 20000 serialized characters')
        return self


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    structured_input: dict[str, JsonValue] | None = None
    context: str | None = None
    criterion: DecisionCriterion


class EvaluationError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class EvaluationResult(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    request_id: str
    evaluator: str
    provider: str
    model: str | None = None
    status: Literal['success', 'error']
    decision: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_source: str | None = None
    probabilities: dict[str, float] | None = None
    evidence: list[str] = Field(default_factory=list)
    reasoning: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    queue_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    cost_source: str | None = None
    raw_model_output: Any = None
    input_fingerprint: str
    error: EvaluationError | None = None


class EvaluationComparison(BaseModel):
    same_decision: bool | None = None
    confidence_difference: float | None = None
    latency_difference_ms: float | None = None
    latency_ratio: float | None = None
    notes: list[str] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    request_id: str
    query: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    laya: EvaluationResult
    llm: EvaluationResult
    comparison: EvaluationComparison
    semantic_input: dict[str, Any]
