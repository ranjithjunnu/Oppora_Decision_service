"""Existing planning HTTP endpoint."""
import logging
from fastapi import APIRouter, HTTPException, status
from models.planning import GTMPlanRequest, WorkflowPlan
from agents.gtm_agent import get_gtm_agent

logger = logging.getLogger("laya_decision_service.app")
router = APIRouter()

@router.post(
    "/agent/plan",
    response_model=WorkflowPlan,
    tags=["Oppora GTM Agent"],
    summary="Plan a GTM workflow using Laya, explicit rules and configured templates"
)
async def plan_gtm_workflow(request: GTMPlanRequest) -> WorkflowPlan:
    """
    Standalone planning demo that:
    1. Classifies user intent.
    2. Extracts target scope (role, vertical, territory).
    3. Breaks the objective into workflow steps.
    4. Maps actions to configured demo tools (no tool execution).
    5. Returns JSON with decision sources, model scores and reasoning.
    Uncertain or unsupported requests return no steps and a clarification.
    """
    try:
        agent = get_gtm_agent()
        plan = agent.plan_workflow(request)
        return plan
    except Exception as e:
        logger.error(f"Error processing /agent/plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow planning failed: {str(e)}"
        )
