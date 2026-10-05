"""Existing decision HTTP endpoint."""
import logging
from fastapi import APIRouter, HTTPException, status
from models.decision import DecisionRequest, DecisionResponse
from engines.laya_engine import get_engine

logger = logging.getLogger("laya_decision_service.app")
router = APIRouter()

@router.post(
    "/decision",
    response_model=DecisionResponse,
    tags=["Decision Core"],
    summary="Execute low-level multi-choice decision questions"
)
async def make_decision(request: DecisionRequest) -> DecisionResponse:
    """
    Evaluates one or more decision questions against a given context state.
    """
    try:
        engine = get_engine()
        answers, latency_ms = engine.decide(
            state=request.state,
            questions=request.questions,
            model=request.model,
        )
        return DecisionResponse(
            model=request.model or engine.default_model,
            answers=answers,
            latency_ms=latency_ms,
        )
    except Exception as e:
        logger.error(f"Error processing /decision: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decision execution failed: {str(e)}"
        )
