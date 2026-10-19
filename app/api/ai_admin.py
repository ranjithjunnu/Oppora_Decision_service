"""Read-only AI Admin: where decisions happen and what the recorded LLM calls used."""
from typing import Literal

from fastapi import APIRouter, Query

from scoring import ledger, repository

router = APIRouter(prefix='/v1/ai-admin', tags=['AI Admin'])
Range = Literal['last_24_hours', 'last_7_days', 'last_30_days', 'all_time']


@router.get('/decisions')
def decisions():
    """Every decision point, who makes it (LLM or code) and whether Jev could take it over."""
    return {'decisions': ledger.DECISIONS}


@router.get('/usage')
def usage(range: Range = 'last_7_days'):
    """Calls, tokens, estimated cost and latency per decision point."""
    return ledger.summary(range)


@router.get('/calls')
def calls(decision_point: str | None = Query(None, max_length=60), limit: int = Query(50, ge=1, le=500)):
    """Most recent ledger entries. Full prompts are in the linked run, search or target."""
    return {'calls': repository.list_llm_calls(decision_point=decision_point, limit=limit)}
