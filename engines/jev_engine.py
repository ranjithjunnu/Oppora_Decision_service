"""TypeSafe Jev (System One) transport: typed questions in, probabilities out. No text generation."""
import asyncio
from dataclasses import dataclass
import random
import time
from typing import Any

import httpx

from core.config import JevSettings
from engines.llm_engine import LLMTransportError, scrub_secret

# 429 rate limit and 529 overloaded are documented; other 5xx are treated as transient too.
RETRY_STATUS = {429, 500, 502, 503, 504, 529}
MAX_WAIT_SECONDS = 10.0


@dataclass
class JevResponse:
    raw: dict[str, Any]
    model: str
    answers: dict[str, dict[str, Any]]
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    attempts: int = 1


def retry_wait(response, attempt):
    """Honour a numeric retry-after header, otherwise capped exponential backoff with jitter."""
    header = response.headers.get('retry-after') if response is not None else None
    try:
        if header is not None:
            return min(max(float(header), 0.0), MAX_WAIT_SECONDS)
    except ValueError:
        pass
    return min(0.5 * 2 ** attempt, MAX_WAIT_SECONDS) * random.uniform(0.75, 1.25)


class JevEngine:
    def __init__(self, settings: JevSettings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        # A run passes one shared client so connections are reused across its leads.
        self.client = client

    async def _post(self, body, headers):
        url = self.settings.base_url + '/v1/systemone'
        if self.client is not None:
            return await self.client.post(url, headers=headers, json=body)
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds, follow_redirects=False) as client:
            return await client.post(url, headers=headers, json=body)

    async def system_one(self, state, questions: dict[str, dict[str, Any]]) -> JevResponse:
        settings = self.settings
        body = {'model': settings.model, 'state': state, 'questions': questions}
        headers = {'Authorization': 'Bearer ' + settings.api_key, 'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        started = time.perf_counter()
        attempts = max(1, settings.max_attempts)
        response = None
        for attempt in range(attempts):
            last = attempt == attempts - 1
            try:
                response = await self._post(body, headers)
            except httpx.TimeoutException as exc:
                if not last:
                    await asyncio.sleep(retry_wait(None, attempt))
                    continue
                raise LLMTransportError('provider_timeout', 'Jev did not respond before its timeout.', True) from exc
            except httpx.RequestError as exc:
                if not last:
                    await asyncio.sleep(retry_wait(None, attempt))
                    continue
                raise LLMTransportError('provider_connection_error', 'Could not connect to Jev.', True) from exc
            if response.status_code in RETRY_STATUS and not last:
                await asyncio.sleep(retry_wait(response, attempt))
                continue
            break
        latency = round((time.perf_counter() - started) * 1000, 2)
        try:
            raw = scrub_secret(response.json(), settings.api_key)
        except ValueError as exc:
            raise LLMTransportError('invalid_provider_response', f'Jev returned HTTP {response.status_code} without JSON.',
                                    response.status_code in RETRY_STATUS,
                                    raw={'response_text': scrub_secret(response.text[:2000], settings.api_key)}) from exc
        if response.is_error:
            status = response.status_code
            detail = str(raw)[:300]
            code = {401: 'provider_auth_error', 429: 'rate_limited', 529: 'provider_overloaded'}.get(status, 'provider_error')
            raise LLMTransportError(code, f'Jev returned HTTP {status}. Provider says: {detail}', status in RETRY_STATUS, raw)
        answers = raw.get('answers') if isinstance(raw, dict) else None
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise LLMTransportError('invalid_provider_response', 'Jev did not answer exactly the questions asked.', raw=raw)
        usage = raw.get('usage') or {}
        return JevResponse(raw, raw.get('model') or settings.model, answers,
                           usage.get('input_tokens'), usage.get('output_tokens'), latency, attempt + 1)
