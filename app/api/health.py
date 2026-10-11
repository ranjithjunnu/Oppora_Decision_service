"""Service liveness and LLM configuration without making a provider request."""
from fastapi import APIRouter
from core.config import load_evaluation_settings
from models.health import HealthResponse

router = APIRouter()


@router.get('/health', response_model=HealthResponse, tags=['System'])
async def health_check() -> HealthResponse:
    settings = load_evaluation_settings()
    return HealthResponse(
        status='ok', model=settings.model, provider=settings.provider,
        llm_configured=not settings.issues, configuration_issues=list(settings.issues),
    )
