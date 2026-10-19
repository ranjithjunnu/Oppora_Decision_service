"""Normalize an LLM's structured response without inventing scores or evidence."""
import json
import time

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from core.config import EvaluationSettings
from engines.llm_engine import LLMEngine, LLMTransportError, create_llm_engine
from models.evaluation import EvaluationError, EvaluationResult
from .base import Evaluator, PreparedCase


class StructuredDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    decision: str
    confidence: float | None = Field(ge=0, le=1)
    reasoning: str = Field(max_length=4000)
    evidence: list[str] = Field(max_length=20)


class LLMEvaluator(Evaluator):
    def __init__(self, settings: EvaluationSettings, engine: LLMEngine | None = None):
        self.settings = settings
        self.engine = engine

    async def evaluate(self, prepared: PreparedCase) -> EvaluationResult:
        started = time.perf_counter()
        settings = self.settings
        raw = None
        input_tokens = output_tokens = None
        cost = None
        cost_source = None

        def error(code, message, retryable=False):
            return EvaluationResult(
                request_id=prepared.case.request_id, evaluator='LLM', provider=settings.provider,
                model=settings.model or None, status='error', latency_ms=round((time.perf_counter()-started)*1000, 2),
                input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost, cost_source=cost_source,
                raw_model_output=raw, input_fingerprint=prepared.fingerprint,
                error=EvaluationError(code=code, message=message, retryable=retryable),
            )

        if settings.issues:
            return error('configuration_error', ' '.join(settings.issues))
        schema = StructuredDecision.model_json_schema()
        schema['properties']['decision']['enum'] = list(prepared.choices)
        # Keep the ordered menu explicit and separate from the state facts.
        choice_menu = '\nChoices (label: description):\n' + json.dumps(
            prepared.choices, ensure_ascii=False, separators=(',', ':'))
        formatting = (
            '\n\nReturn one JSON object matching the following response schema. '
            'Confidence is your self-reported confidence, or null if unavailable. '
            'Provide a concise decision rationale, not a step-by-step thought process. '
            'Evidence must be short quotations from the supplied input, or an empty list when absent. '
            'Do not claim evidence was independently verified. Response schema: '
            + json.dumps(schema, ensure_ascii=False)
        )
        messages = [{'role': 'system', 'content': prepared.instructions + choice_menu + formatting},
                    {'role': 'user', 'content': prepared.state}]
        try:
            completion = await (self.engine or create_llm_engine(settings)).complete(messages, schema)
            raw = completion.raw
            input_tokens, output_tokens = completion.input_tokens, completion.output_tokens
            if settings.pricing_configured and input_tokens is not None and output_tokens is not None:
                cost = round((input_tokens*settings.input_cost_per_million + output_tokens*settings.output_cost_per_million)/1_000_000, 10)
            if completion.finish_reason not in {'stop', None}:
                return error('incomplete_output', 'The model did not finish a complete decision. Inspect the raw response and output token limit.')
            content = (completion.content or '').strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if len(lines) >= 2 and lines[-1].strip() == "```":
                    content = "\n".join(lines[1:-1]).strip()
                elif lines[0].startswith("```"):
                    content = "\n".join(lines[1:]).strip()
            parsed = StructuredDecision.model_validate_json(content)
            if parsed.decision not in prepared.choices:
                return error('invalid_model_output', 'The model selected a label outside the supplied choice menu.')
            return EvaluationResult(
                request_id=prepared.case.request_id, evaluator='LLM', provider=settings.provider, model=settings.model,
                status='success', decision=parsed.decision, confidence=parsed.confidence,
                confidence_source='self_reported' if parsed.confidence is not None else 'unavailable',
                evidence=parsed.evidence, reasoning=parsed.reasoning,
                latency_ms=round((time.perf_counter()-started)*1000, 2), input_tokens=input_tokens,
                output_tokens=output_tokens, cost_usd=cost, cost_source=cost_source,
                raw_model_output=raw, input_fingerprint=prepared.fingerprint,
            )
        except LLMTransportError as exc:
            raw = exc.raw
            return error(exc.code, exc.message, exc.retryable)
        except (ValidationError, ValueError, TypeError):
            return error('invalid_model_output', 'The response was not valid decision JSON. Inspect the raw model output.')
        except Exception:
            return error('evaluation_error', 'The LLM evaluator could not normalize this response.')
