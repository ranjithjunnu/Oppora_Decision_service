"""Run one explicitly submitted case with the current LLM baseline."""

from core.config import EvaluationSettings
from models.evaluation import EvaluationCase, EvaluationResponse
from scoring import ledger
from .base import prepare_case
from .llm import LLMEvaluator


async def evaluate_case(case: EvaluationCase, settings: EvaluationSettings) -> EvaluationResponse:
    prepared = prepare_case(case)
    llm = await LLMEvaluator(settings).evaluate(prepared)
    # A configuration error never reached the provider, so it is not an LLM call.
    if not (llm.error and llm.error.code == 'configuration_error'):
        ledger.record(settings, 'intent_classification', 'Classify request: ' + case.criterion.id,
                      case.criterion.id + '-v1', status='ok' if llm.status == 'success' else 'failed',
                      error=llm.error.message if llm.error else None, latency_ms=llm.latency_ms,
                      input_tokens=llm.input_tokens, output_tokens=llm.output_tokens, items_in=1,
                      decisions={llm.decision: 1} if llm.decision else {}, links={'request_id': case.request_id})
    return EvaluationResponse(request_id=case.request_id, query=case.query,
                              llm=llm, semantic_input=prepared.semantic_input)
