"""TypeSafe Jev (System One) transport: typed questions in, probabilities out. No text generation."""
import asyncio
from dataclasses import dataclass
import time
from typing import Any

import httpx

from core.config import JevSettings
from engines.llm_engine import LLMTransportError, scrub_secret


@dataclass
class JevResponse:
    raw: dict[str, Any]
    model: str
    answers: dict[str, dict[str, Any]]
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float


class JevEngine:
    def __init__(self, settings: JevSettings):
        self.settings = settings

    async def system_one(self, state, questions: dict[str, dict[str, Any]]) -> JevResponse:
        settings = self.settings
        body = {'model': settings.model, 'state': state, 'questions': questions}
        headers = {'Authorization': 'Bearer ' + settings.api_key, 'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        started = time.perf_counter()
        # 429 (rate limit) and 529 (overloaded) are retried with backoff, as the Jev docs recommend.
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=settings.timeout_seconds, follow_redirects=False) as client:
                    response = await client.post(settings.base_url + '/v1/systemone', headers=headers, json=body)
            except httpx.TimeoutException as exc:
                raise LLMTransportError('provider_timeout', 'Jev did not respond before its timeout.', True) from exc
            except httpx.RequestError as exc:
                raise LLMTransportError('provider_connection_error', 'Could not connect to Jev.', True) from exc
            if response.status_code in {429, 529} and attempt < 2:
                wait = response.headers.get('retry-after')
                await asyncio.sleep(min(float(wait), 10) if wait and wait.replace('.', '', 1).isdigit() else 0.5 * 2 ** attempt)
                continue
            break
        latency = round((time.perf_counter() - started) * 1000, 2)
        try:
            raw = scrub_secret(response.json(), settings.api_key)
        except ValueError as exc:
            raise LLMTransportError('invalid_provider_response', f'Jev returned HTTP {response.status_code} without JSON.',
                                    raw={'response_text': scrub_secret(response.text[:2000], settings.api_key)}) from exc
        if response.is_error:
            status = response.status_code
            detail = str(raw)[:300]
            code = {401: 'provider_auth_error', 429: 'rate_limited', 529: 'provider_overloaded'}.get(status, 'provider_error')
            raise LLMTransportError(code, f'Jev returned HTTP {status}. Provider says: {detail}', status in {429, 529} or status >= 500, raw)
        answers = raw.get('answers') if isinstance(raw, dict) else None
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise LLMTransportError('invalid_provider_response', 'Jev did not answer exactly the questions asked.', raw=raw)
        usage = raw.get('usage') or {}
        return JevResponse(raw, raw.get('model') or settings.model, answers,
                           usage.get('input_tokens'), usage.get('output_tokens'), latency)
