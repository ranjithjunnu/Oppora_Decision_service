"""Existing health HTTP endpoint."""
import logging
from fastapi import APIRouter, HTTPException, status
from models.health import HealthResponse
from engines.laya_engine import get_engine

logger = logging.getLogger("laya_decision_service.app")
router = APIRouter()

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check and engine readiness"
)
async def health_check() -> HealthResponse:
    """Returns the operational status of the Laya Decision Engine."""
    engine = get_engine()
    return HealthResponse(
        status="ok",
        model=engine.default_model,
        engine_ready=engine.ready,
        standalone=True,
    )
