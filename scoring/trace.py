"""Observable model inputs/outputs, without provider secrets or private reasoning."""
import json
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

from core.config import estimate_cost
from engines.llm_engine import LLMTransportError, create_llm_engine, scrub_secret
from engines.structured_output import strict_schema


PYTHON_LITERAL = re.compile(r'(:\s*|\[\s*|,\s*)(None|True|False)(?=\s*[,}\]])')


def now():
    return datetime.now(timezone.utc).isoformat()


def repair_python_literals(content):
    """DeepSeek sometimes copies the Python-style lists in Oppora's prompt and writes None/True/False."""
    return PYTHON_LITERAL.sub(lambda m: m.group(1) + {'None': 'null', 'True': 'true', 'False': 'false'}[m.group(2)], content)


async def invoke(settings, purpose, version, instructions, inputs, output_model, user_content=None):
    """`user_content` sends a prepared text prompt (Oppora's format) instead of the JSON-encoded inputs."""
    schema = output_model.model_json_schema()
    strict_schema(schema)
    messages = [{'role': 'system', 'content': instructions + '\nJSON schema: ' + json.dumps(schema)},
                {'role': 'user', 'content': user_content if user_content is not None
                 else json.dumps(inputs, ensure_ascii=False, allow_nan=False)}]
    trace = {'id': 'call_' + uuid4().hex, 'purpose': purpose, 'prompt_version': version,
             'provider': settings.provider, 'model': settings.model, 'created_at': now(),
             'messages': messages, 'schema': schema, 'output': None, 'status': 'failed',
             'error': None, 'input_tokens': None, 'cached_input_tokens': None, 'output_tokens': None,
             'reasoning_tokens': None,
             'estimated_cost_usd': None}
    started = time.perf_counter()
    parsed = None
    try:
        response = await create_llm_engine(settings).complete(messages, schema)
        trace.update(output=scrub_secret(response.content, settings.api_key),
                     input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                     cached_input_tokens=response.cached_input_tokens, reasoning_tokens=response.reasoning_tokens,
                     finish_reason=response.finish_reason)
        trace['estimated_cost_usd'] = estimate_cost(settings, response.input_tokens, response.output_tokens,
                                                    response.cached_input_tokens)
        if response.finish_reason != 'stop':
            raise ValueError('The model response was incomplete. Retry this batch or increase its output token limit.')
        try:
            parsed = output_model.model_validate_json(response.content or '')
        except ValueError:
            repaired = repair_python_literals(response.content or '')
            if repaired == (response.content or ''):
                raise
            parsed = output_model.model_validate_json(repaired)
            trace['repaired'] = 'python_literals'
        trace['status'] = 'validated'
    except LLMTransportError as exc:
        trace['error'] = exc.message
    except (ValueError, TypeError):
        trace['error'] = 'The model returned an incomplete response or JSON that does not match the required schema.'
    except Exception:
        trace['error'] = 'The AI request could not be completed.'
    trace['latency_ms'] = round((time.perf_counter() - started) * 1000, 2)
    return parsed, trace
