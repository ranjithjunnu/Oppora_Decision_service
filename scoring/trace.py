"""Observable model inputs/outputs, without provider secrets or private reasoning."""
import json
import time
from datetime import datetime, timezone
from uuid import uuid4

from engines.llm_engine import LLMTransportError, create_llm_engine, scrub_secret
from engines.structured_output import strict_schema


def now():
    return datetime.now(timezone.utc).isoformat()


async def invoke(settings, purpose, version, instructions, inputs, output_model):
    schema = output_model.model_json_schema()
    strict_schema(schema)
    messages = [{'role': 'system', 'content': instructions + '\nJSON schema: ' + json.dumps(schema)},
                {'role': 'user', 'content': json.dumps(inputs, ensure_ascii=False, allow_nan=False)}]
    trace = {'id': 'call_' + uuid4().hex, 'purpose': purpose, 'prompt_version': version,
             'provider': settings.provider, 'model': settings.model, 'created_at': now(),
             'messages': messages, 'schema': schema, 'output': None, 'status': 'failed',
             'error': None, 'input_tokens': None, 'output_tokens': None, 'estimated_cost_usd': None}
    started = time.perf_counter()
    parsed = None
    try:
        response = await create_llm_engine(settings).complete(messages, schema)
        trace.update(output=scrub_secret(response.content, settings.api_key),
                     input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                     finish_reason=response.finish_reason)
        if settings.pricing_configured and response.input_tokens is not None and response.output_tokens is not None:
            trace['estimated_cost_usd'] = (response.input_tokens * settings.input_cost_per_million + response.output_tokens * settings.output_cost_per_million) / 1_000_000
        if response.finish_reason != 'stop':
            raise ValueError('The model response was incomplete. Retry this batch or increase its output token limit.')
        parsed = output_model.model_validate_json(response.content or '')
        trace['status'] = 'validated'
    except LLMTransportError as exc:
        trace['error'] = exc.message
    except (ValueError, TypeError):
        trace['error'] = 'The model returned an incomplete response or JSON that does not match the required schema.'
    except Exception:
        trace['error'] = 'The AI request could not be completed.'
    trace['latency_ms'] = round((time.perf_counter() - started) * 1000, 2)
    return parsed, trace
