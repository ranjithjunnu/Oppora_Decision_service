"""Replaceable JSON chat transport for DeepSeek, Groq and OpenAI-compatible providers."""
from dataclasses import dataclass
import json
from typing import Any, Protocol

import httpx

from core.config import EvaluationSettings


@dataclass
class LLMResponse:
    raw: dict[str, Any]
    content: str | None
    finish_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None


class LLMTransportError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False, raw: Any = None):
        super().__init__(message)
        self.code, self.message, self.retryable, self.raw = code, message, retryable, raw


class LLMEngine(Protocol):
    async def complete(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> LLMResponse: ...


def scrub_secret(value: Any, secret: str) -> Any:
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, '[REDACTED]')
    if isinstance(value, dict):
        return {key: scrub_secret(item, secret) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_secret(item, secret) for item in value]
    return value


class CompatibleChatEngine:
    def __init__(self, settings: EvaluationSettings):
        self.settings = settings

    async def complete(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> LLMResponse:
        settings = self.settings
        response_format = {'type': 'json_object'}
        if settings.response_format == 'json_schema':
            response_format = {'type': 'json_schema', 'json_schema': {'name': 'manual_decision', 'strict': True, 'schema': schema}}
        payload = {'model': settings.model, 'messages': messages, 'response_format': response_format, 'stream': False}
        payload['max_completion_tokens' if settings.provider == 'groq' else 'max_tokens'] = settings.max_output_tokens
        if settings.provider == 'deepseek' and settings.thinking in {'enabled', 'disabled'}:
            payload['thinking'] = {'type': settings.thinking}
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if settings.api_key:
            headers['Authorization'] = 'Bearer ' + settings.api_key
        try:
            # No automatic retry: each UI action corresponds to one provider request.
            async with httpx.AsyncClient(timeout=settings.timeout_seconds, follow_redirects=False) as client:
                response = await client.post(settings.base_url + '/chat/completions', headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTransportError('provider_timeout', 'The LLM provider did not respond before its timeout.', True) from exc
        except httpx.RequestError as exc:
            raise LLMTransportError('provider_connection_error', 'Could not connect to the configured LLM provider.', True) from exc
        try:
            def reject_nonfinite(value):
                raise ValueError('Non-finite JSON constant')
            raw = scrub_secret(json.loads(response.content, parse_constant=reject_nonfinite), settings.api_key)
        except ValueError as exc:
            raw = {'response_text': scrub_secret(response.text[:16000], settings.api_key), 'http_status': response.status_code}
            raise LLMTransportError('invalid_provider_response', 'The provider returned a non-JSON response.', False, raw) from exc
        if response.is_error or response.is_redirect:
            status = response.status_code
            # Show the provider's own reason (e.g. "Model Not Exist"); the key is already scrubbed from raw.
            detail = raw.get('error') if isinstance(raw, dict) else None
            reason = detail.get('message') if isinstance(detail, dict) else detail if isinstance(detail, str) else None
            reason = f' Provider says: {str(reason)[:300]}' if reason else ''
            code, message = ('provider_error', f'The LLM provider returned HTTP {status}.{reason}')
            if status in {401, 403}:
                code, message = 'provider_auth_error', 'The provider rejected authentication or model access. Check the backend API key and model permissions.' + reason
            elif status == 429:
                code, message = 'rate_limited', 'The provider rate limit or quota was reached. Wait before retrying.' + reason
            raise LLMTransportError(code, message, status == 429 or status >= 500, raw)
        if not isinstance(raw, dict):
            raise LLMTransportError('invalid_provider_response', 'The provider response was not a JSON object.', raw=raw)
        try:
            choices = raw['choices']
            if not isinstance(choices, list) or not choices:
                raise ValueError
            first = choices[0]
            message = first['message']
            if message.get('refusal'):
                raise LLMTransportError('provider_refusal', 'The model declined to produce a decision.', raw=raw)
            content = message.get('content')
            if not isinstance(content, str):
                raise ValueError
            usage = raw.get('usage') or {}

            def count(name, source=None):
                item = (usage if source is None else source).get(name)
                return item if isinstance(item, int) and not isinstance(item, bool) and item >= 0 else None

            # DeepSeek reports prompt_cache_hit_tokens; OpenAI-style APIs report cached_tokens.
            details = usage.get('prompt_tokens_details') if isinstance(usage.get('prompt_tokens_details'), dict) else {}
            cached = count('prompt_cache_hit_tokens')
            if cached is None:
                cached = count('cached_tokens', details)
            completion = usage.get('completion_tokens_details') if isinstance(usage.get('completion_tokens_details'), dict) else {}
            return LLMResponse(raw, content, first.get('finish_reason'), count('prompt_tokens'),
                               count('completion_tokens'), cached, count('reasoning_tokens', completion))
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise LLMTransportError('invalid_provider_response', 'The provider response did not contain a usable chat completion.', raw=raw) from exc


def create_llm_engine(settings: EvaluationSettings) -> LLMEngine:
    if settings.provider not in {'deepseek', 'groq', 'openai_compatible'}:
        raise LLMTransportError('configuration_error', 'No adapter is registered for the configured provider.')
    return CompatibleChatEngine(settings)
