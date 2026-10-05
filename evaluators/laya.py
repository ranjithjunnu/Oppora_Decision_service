"""Wrap the existing engine once; retain raw output without planner corrections."""
import math
import logging
import json
from threading import Lock
import time

from starlette.concurrency import run_in_threadpool
from engines.laya_engine import get_engine
from models.decision import QuestionSpec
from models.evaluation import EvaluationError, EvaluationResult
from .base import Evaluator, PreparedCase


_manual_inference_lock = Lock()
logger = logging.getLogger(__name__)


class LayaEvaluator(Evaluator):
    async def evaluate(self, prepared: PreparedCase) -> EvaluationResult:
        return await run_in_threadpool(self._evaluate_sync, prepared)

    def _evaluate_sync(self, prepared: PreparedCase) -> EvaluationResult:
        started = time.perf_counter()
        raw = None
        model = 'typed-decisions'
        queue_ms = 0.0

        def capture(value):
            nonlocal raw
            try:
                json.dumps(value, allow_nan=False)
                raw = value
            except (ValueError, TypeError):
                raw = {'serialization_note': 'The raw model value is not valid JSON; its representation is retained.',
                       'raw_repr': repr(value)}

        def result_error(code, message, retryable=False):
            return EvaluationResult(
                request_id=prepared.case.request_id, evaluator='Laya', provider='local', model=model,
                status='error', raw_model_output=raw, input_fingerprint=prepared.fingerprint,
                latency_ms=round((time.perf_counter()-started)*1000, 2), queue_ms=queue_ms,
                error=EvaluationError(code=code, message=message, retryable=retryable),
            )

        if not _manual_inference_lock.acquire(timeout=1):
            return result_error('busy', 'The local model is already evaluating a manual request.', True)
        queue_ms = round((time.perf_counter()-started)*1000, 2)
        started = time.perf_counter()
        try:
            engine = get_engine()
            model = engine.default_model
            answers, _ = engine.decide(
                prepared.state,
                {'decision': QuestionSpec(type='choice', instructions=prepared.instructions, criteria=prepared.choices)},
                capture_raw=capture,
            )
            if set(answers) != {'decision'}:
                return result_error('invalid_model_output', 'Laya did not return the requested decision question.')
            answer = answers['decision']
            if answer.choice not in prepared.choices:
                return result_error('invalid_model_output', 'Laya selected a label outside the supplied choice menu.')
            if any(key not in prepared.choices or not math.isfinite(value) or not 0 <= value <= 1
                   for key, value in answer.probabilities.items()):
                return result_error('invalid_model_output', 'Laya returned an invalid probability value or label.')
            usage = raw.get('usage', {}) if isinstance(raw, dict) else {}

            def token_count(name):
                value = usage.get(name)
                return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

            return EvaluationResult(
                request_id=prepared.case.request_id, evaluator='Laya', provider='local', model=model,
                status='success', decision=answer.choice, confidence=answer.confidence,
                confidence_source=answer.source, probabilities=answer.probabilities or None,
                latency_ms=round((time.perf_counter()-started)*1000, 2), queue_ms=queue_ms,
                input_tokens=token_count('input_tokens'), output_tokens=token_count('output_tokens'),
                raw_model_output=raw, input_fingerprint=prepared.fingerprint,
            )
        except Exception:
            logger.exception('Local manual evaluation failed for request %s', prepared.case.request_id)
            # Do not expose filesystem paths or internal exception text to clients.
            return result_error('local_inference_error', 'Local Laya inference failed. Check the backend and model availability.', True)
        finally:
            _manual_inference_lock.release()
