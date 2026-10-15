"""Contracts for the observed Oppora batch filtering/scoring workflow."""
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from models.scoring import StrictModel

FilterText = Annotated[str, Field(min_length=1, max_length=200)]


class LeadFilters(StrictModel):
    titles: list[FilterText] = Field(default_factory=list, max_length=30)
    countries: list[FilterText] = Field(default_factory=list, max_length=30)
    locations: list[FilterText] = Field(default_factory=list, max_length=30)
    exclude_locations: list[FilterText] = Field(default_factory=list, max_length=30)
    departments: list[FilterText] = Field(default_factory=list, max_length=30)
    management_levels: list[FilterText] = Field(default_factory=list, max_length=30)
    experience_min: float | None = Field(default=None, ge=0, le=100)
    experience_max: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode='after')
    def bounds(self):
        if self.experience_min is not None and self.experience_max is not None and self.experience_min > self.experience_max:
            raise ValueError('Minimum experience cannot exceed maximum experience.')
        return self


class TargetingRequest(StrictModel):
    description: str = Field(min_length=1, max_length=3000)
    objective: str = Field(default='', max_length=1500)

    @field_validator('description')
    @classmethod
    def description_required(cls, value):
        if not value.strip():
            raise ValueError('Describe the people you want to reach.')
        return value.strip()


class TargetingOutput(StrictModel):
    filters: LeadFilters | None
    issues: list[str] = Field(max_length=12)


class BatchRequest(StrictModel):
    targeting_id: str = Field(pattern=r'^target_[a-f0-9]{32}$')
    lead_ids: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(min_length=1, max_length=100)

    @field_validator('lead_ids')
    @classmethod
    def unique_ids(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('Choose each person only once.')
        return values


class ScoredLead(StrictModel):
    lead_id: str = Field(min_length=1, max_length=100)
    score: int = Field(ge=0, le=100, strict=True)


class LeadFilterResult(StrictModel):
    scored_leads: list[ScoredLead] = Field(max_length=20)


class ExplanationEvidence(StrictModel):
    field: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=500)


class LeadExplanation(StrictModel):
    assessment: str = Field(min_length=1, max_length=800)
    evidence: list[ExplanationEvidence] = Field(max_length=4)
    gaps: list[str] = Field(max_length=8)


class ExplanationRequest(StrictModel):
    lead_id: str = Field(min_length=1, max_length=100)
