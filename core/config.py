"""Read server-only evaluation settings without mutating the process environment."""
from dataclasses import dataclass, field
import math
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class EvaluationSettings:
    provider: str
    model: str
    api_key: str = field(repr=False)
    base_url: str
    response_format: str
    timeout_seconds: float
    max_output_tokens: int
    input_cost_per_million: float | None
    output_cost_per_million: float | None
    task: str
    issues: tuple[str, ...] = ()

    @property
    def pricing_configured(self) -> bool:
        return self.input_cost_per_million is not None and self.output_cost_per_million is not None


def load_evaluation_settings() -> EvaluationSettings:
    file_values = dotenv_values(ROOT / '.env', interpolate=False) if (ROOT / '.env').exists() else {}
    values = {**file_values, **os.environ}
    issues = []

    def value(name, default=''):
        return str(values.get(name) or default).strip()

    def number(name, default, minimum, maximum):
        try:
            parsed = float(value(name, str(default)))
            if not math.isfinite(parsed) or not minimum <= parsed <= maximum:
                raise ValueError
            return parsed
        except ValueError:
            issues.append(f'{name} must be between {minimum} and {maximum}.')
            return default

    def rate(name):
        if not value(name):
            return None
        return number(name, None, 0, 1000000)

    provider = value('LLM_PROVIDER', 'groq').lower()
    model = value('LLM_MODEL', 'openai/gpt-oss-120b' if provider == 'groq' else '')
    if provider not in {'groq', 'openai_compatible'}:
        issues.append('LLM_PROVIDER must be groq or openai_compatible.')
    key = value('GROQ_API_KEY') if provider == 'groq' else value('LLM_API_KEY')
    if provider == 'groq' and not key:
        issues.append('Add GROQ_API_KEY to the backend .env file.')
    if not model:
        issues.append('Set LLM_MODEL in the backend .env file.')
    base_url = 'https://api.groq.com/openai/v1' if provider == 'groq' else value('LLM_BASE_URL')
    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {'http', 'https'} or not parsed_url.netloc or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment:
        issues.append('LLM_BASE_URL must be an HTTP(S) API base URL without credentials or a query string.')
    format_name = value('LLM_RESPONSE_FORMAT', 'json_schema')
    if format_name not in {'json_schema', 'json_object'}:
        issues.append('LLM_RESPONSE_FORMAT must be json_schema or json_object.')
    timeout = number('LLM_TIMEOUT_SECONDS', 60.0, 1, 120)
    token_limit = number('LLM_MAX_OUTPUT_TOKENS', 2048, 256, 8192)
    if token_limit != int(token_limit):
        issues.append('LLM_MAX_OUTPUT_TOKENS must be an integer.')
    input_rate = rate('LLM_INPUT_COST_PER_MILLION')
    output_rate = rate('LLM_OUTPUT_COST_PER_MILLION')
    return EvaluationSettings(
        provider=provider, model=model, api_key=key, base_url=base_url.rstrip('/'), response_format=format_name,
        timeout_seconds=timeout, max_output_tokens=int(token_limit), input_cost_per_million=input_rate,
        output_cost_per_million=output_rate, task=value('EVALUATION_TASK', 'gtm_intent'), issues=tuple(issues),
    )


def is_decision_lab_enabled() -> bool:
    env = os.environ.get('ENABLE_DECISION_LAB')
    if env is not None:
        return env.strip().lower() not in {'false', '0', 'no'}
    file_values = dotenv_values(ROOT / '.env', interpolate=False) if (ROOT / '.env').exists() else {}
    file_val = file_values.get('ENABLE_DECISION_LAB')
    if file_val is not None:
        return str(file_val).strip().lower() not in {'false', '0', 'no'}
    return True


