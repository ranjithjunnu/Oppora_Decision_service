"""Run one interactive case through both adapters and describe this result pair."""
import asyncio

from core.config import EvaluationSettings
from models.evaluation import EvaluationCase, EvaluationComparison, EvaluationResponse
from .base import prepare_case
from .laya import LayaEvaluator
from .llm import LLMEvaluator


async def evaluate_case(case: EvaluationCase, settings: EvaluationSettings) -> EvaluationResponse:
    prepared = prepare_case(case)
    laya, llm = await asyncio.gather(LayaEvaluator().evaluate(prepared), LLMEvaluator(settings).evaluate(prepared))
    comparison = EvaluationComparison()
    if laya.status == 'success' and llm.status == 'success':
        comparison.same_decision = laya.decision == llm.decision
        if laya.confidence is not None and llm.confidence is not None:
            comparison.confidence_difference = round(llm.confidence-laya.confidence, 6)
        if laya.latency_ms is not None and llm.latency_ms is not None:
            comparison.latency_difference_ms = round(llm.latency_ms-laya.latency_ms, 2)
            if llm.latency_ms > 0:
                comparison.latency_ratio = round(laya.latency_ms/llm.latency_ms, 4)
        if comparison.same_decision is False:
            comparison.notes.append('The models selected different labels. No ground-truth correctness judgment is available for this query.')
        if llm.evidence and not laya.evidence:
            comparison.notes.append('The LLM supplied input citations; Laya did not return evidence. Citations have not been verified.')
        if laya.probabilities and not llm.probabilities:
            comparison.notes.append('Only Laya returned an option probability distribution.')
    else:
        comparison.notes.append('At least one evaluator failed. Agreement and numeric differences are unavailable for this request.')
    if llm.cost_usd is None:
        comparison.notes.append('LLM cost is unavailable unless token usage and both configured token rates are present.')
    return EvaluationResponse(request_id=case.request_id, query=case.query, laya=laya, llm=llm,
                              comparison=comparison, semantic_input=prepared.semantic_input)
