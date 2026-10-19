"""People search and persistent lead-list request contracts."""
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from models.lead_batch import FilterText, LeadFilters, TargetingRequest
from models.scoring import StrictModel

LeadID = Annotated[str, Field(min_length=1, max_length=100)]


class PeopleSearchRequest(TargetingRequest):
    company_id: str | None = Field(default=None, max_length=100)


class SearchRequirement(StrictModel):
    field: Literal['titles', 'countries', 'locations', 'exclude_locations', 'departments', 'management_levels',
                   'experience_min', 'experience_max', 'company_names']
    quote: str = Field(min_length=1, max_length=500)


class SearchPlan(StrictModel):
    filters: LeadFilters | None
    title_variants: list[FilterText] = Field(max_length=40)
    company_names: list[FilterText] = Field(max_length=20)
    issues: list[str] = Field(max_length=12)
    requirements: list[SearchRequirement] = Field(default_factory=list, max_length=60)


class ListMembers(StrictModel):
    search_id: str | None = Field(default=None, pattern=r'^search_[a-f0-9]{32}$')
    lead_ids: list[LeadID] | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode='after')
    def require_source(self):
        if self.search_id is None and self.lead_ids is None:
            raise ValueError('Select people or choose a saved search.')
        if self.lead_ids and len(self.lead_ids) != len(set(self.lead_ids)):
            raise ValueError('Choose each person only once.')
        return self


class CreateLeadList(ListMembers):
    name: str = Field(min_length=1, max_length=120)
    targeting_id: str | None = Field(default=None, pattern=r'^target_[a-f0-9]{32}$')

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError('Give your list a name.')
        return value.strip()


class AppendLeadList(ListMembers):
    expected_version: int = Field(ge=1, strict=True)


class EditLeadList(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    remove_ids: list[LeadID] = Field(default_factory=list, max_length=1000)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        if value is not None and not value.strip():
            raise ValueError('Give your list a name.')
        return value.strip() if value is not None else value


class ScoreLeadList(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    targeting_id: str | None = Field(default=None, pattern=r'^target_[a-f0-9]{32}$')
    decision_model: Literal['llm', 'jev'] = 'llm'
