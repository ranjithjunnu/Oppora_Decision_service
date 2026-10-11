"""Contracts for the local, single-lead scoring workflow."""
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Company(StrictModel):
    name: str | None = Field(default=None, max_length=200)
    industry: str | None = Field(default=None, max_length=150)
    country: str | None = Field(default=None, max_length=100)
    employee_count: int | None = Field(default=None, ge=0, strict=True)
    description: str | None = Field(default=None, max_length=3000)
    technologies: list[str] | None = Field(default=None, max_length=100)
    technology_inventory_complete: bool = Field(default=False, strict=True)

    @field_validator('technologies')
    @classmethod
    def valid_technologies(cls, values):
        if values is not None and any(not v.strip() or len(v) > 100 for v in values):
            raise ValueError('Technology names must contain 1–100 characters.')
        return values


class Person(StrictModel):
    title: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=3000)
    seniority: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)


class Signals(StrictModel):
    hiring: bool | None = Field(default=None, strict=True)
    recent_funding_days: int | None = Field(default=None, ge=0, strict=True)
    observed_on: date | None = None


class Lead(StrictModel):
    id: str = Field(default='manual-lead', min_length=1, max_length=100)
    company: Company = Field(default_factory=Company)
    person: Person = Field(default_factory=Person)
    signals: Signals = Field(default_factory=Signals)


class Criterion(StrictModel):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    field: str = Field(min_length=1, max_length=100)
    operator: Literal['in', 'between', 'gte', 'lte', 'contains_any', 'contains_all', 'eq', 'semantic']
    value: str | bool | int | list[str] | list[int]
    importance: Literal['high', 'medium', 'low'] = 'medium'
    hard_requirement: bool = False

    @model_validator(mode='before')
    @classmethod
    def valid_value(cls, data):
        if not isinstance(data, dict):
            return data
        op, value = data.get('operator'), data.get('value')
        if op == 'semantic' and (not isinstance(value, str) or not value.strip() or len(value) > 1000):
            raise ValueError('A semantic criterion needs a requirement of 1–1000 characters.')
        if op in {'in', 'contains_any', 'contains_all'}:
            if (not isinstance(value, list) or not 1 <= len(value) <= 30
                    or any(not isinstance(v, str) or not v.strip() or len(v) > 150 for v in value)):
                raise ValueError('This operator needs 1–30 nonempty text values.')
        if op == 'between':
            if (not isinstance(value, list) or len(value) != 2
                    or any(type(v) is not int or v < 0 for v in value) or value[0] > value[1]):
                raise ValueError('Between needs two nonnegative integers, minimum first.')
        if op in {'gte', 'lte'} and (type(value) is not int or value < 0):
            raise ValueError('The numeric limit must be a nonnegative integer.')
        if op == 'eq' and type(value) is not bool:
            raise ValueError('The hiring criterion needs true or false.')
        return data


class Profile(StrictModel):
    id: str = Field(default='manual-icp', min_length=1, max_length=100)
    name: str = Field(default='My ideal customer', min_length=1, max_length=200)
    version: int = Field(default=1, ge=1, strict=True)
    offering: str | None = Field(default=None, max_length=2000)
    buyer_persona: str | None = Field(default=None, max_length=2000)
    criteria: list[Criterion] = Field(min_length=1, max_length=12)
    alpha_fit: float = Field(default=0.7, ge=0, le=1)
    min_coverage: float = Field(default=0.5, gt=0, le=1)
    hot_threshold: int = Field(default=80, ge=1, le=100, strict=True)
    warm_threshold: int = Field(default=55, ge=0, le=99, strict=True)

    @field_validator('offering', 'buyer_persona')
    @classmethod
    def clean_context(cls, value):
        return value.strip() or None if value is not None else None

    @model_validator(mode='after')
    def validate_profile(self):
        from scoring.catalog import FIELDS
        if self.warm_threshold >= self.hot_threshold:
            raise ValueError('The warm threshold must be lower than the hot threshold.')
        if len({c.id for c in self.criteria}) != len(self.criteria):
            raise ValueError('Criterion IDs must be unique.')
        for c in self.criteria:
            spec = FIELDS.get(c.field)
            if spec is None or c.operator not in spec['operators']:
                raise ValueError(f'Unsupported field/operator: {c.field} / {c.operator}.')
            if c.hard_requirement and c.operator == 'semantic':
                raise ValueError('Hard requirements currently support structured fields only.')
            if c.hard_requirement and spec['axis'] != 'fit':
                raise ValueError('Hard requirements must be fit criteria.')
        if not any(not c.hard_requirement and FIELDS[c.field]['axis'] == 'fit' for c in self.criteria):
            raise ValueError('Include at least one weighted fit criterion in addition to any hard requirements.')
        return self


class ScoreRequest(StrictModel):
    lead: Lead
    profile: Profile
    as_of: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())


class Evidence(StrictModel):
    source_id: str
    text: str
    kind: Literal['field_value', 'source_quote']


class Factor(StrictModel):
    criterion_id: str
    field: str
    requirement: str
    axis: Literal['fit', 'intent']
    hard_requirement: bool
    outcome: Literal['match', 'partial', 'miss', 'unknown'] = 'unknown'
    evaluator: Literal['structured', 'llm']
    status: Literal['evaluated', 'missing_data', 'model_error', 'evidence_missing'] = 'evaluated'
    weight: int
    value: float = 0.5
    impact: float = 0.0
    confidence: float | None = None
    confidence_source: str | None = None
    model_decision: str | None = None
    evidence: Evidence | None = None
    reason: str


class LLMUsage(StrictModel):
    request_count: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    latency_ms: float | None = None


class LLMEvidence(StrictModel):
    source_id: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=500)


class LLMCriterionDecision(StrictModel):
    criterion_id: str = Field(min_length=1, max_length=80)
    outcome: Literal['match', 'partial', 'miss', 'unknown']
    reason: str = Field(min_length=1, max_length=400)
    evidence: LLMEvidence | None


class LLMBatchDecision(StrictModel):
    decisions: list[LLMCriterionDecision] = Field(min_length=1, max_length=12)


class ScoreResult(StrictModel):
    request_id: str
    lead_id: str
    status: Literal['scored', 'insufficient_data', 'failed']
    recommendation: Literal['yes', 'no', 'needs_review']
    recommendation_reasons: list[str]
    eligibility: Literal['eligible', 'ineligible', 'unknown']
    fit_coverage: float
    intent_coverage: float | None
    priority: int | None = None
    fit: int | None = None
    intent: int | None = None
    band: Literal['hot', 'warm', 'cold', 'disqualified'] | None = None
    coverage: float
    factors: list[Factor]
    disqualified_by: list[str]
    explanation: str
    explanation_source: Literal['template'] = 'template'
    warnings: list[str]
    versions: dict[str, str | int]
    input_fingerprint: str
    as_of: date
    latency_ms: float
    llm_usage: LLMUsage = Field(default_factory=LLMUsage)


class ProfileDraftRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=4000)

    @field_validator('prompt')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Describe your ideal customer.')
        return value.strip()


class ProfileDraftOutput(StrictModel):
    profile: Profile | None
    issues: list[str] = Field(max_length=12)
