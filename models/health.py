"""Liveness is separate from provider availability or model quality."""
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = 'ok'
    service: str = 'ai-lead-scoring'
    provider: str
    model: str
    llm_configured: bool
    provider_connectivity: str = 'not_checked'
    local_model_required: bool = False
    configuration_issues: list[str] = Field(default_factory=list)
