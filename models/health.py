"""Service readiness response contract."""
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """Health check status of the decision service."""
    status: str = Field(default="ok", description="Service health status.")
    model: str = Field(..., description="Active Laya decision model.")
    engine_ready: bool = Field(..., description="Whether the model weights are loaded and ready.")
    standalone: bool = Field(default=True, description="Self-hosted mode flag.")
