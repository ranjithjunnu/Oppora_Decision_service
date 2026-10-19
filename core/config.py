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
    jev_api_key: str = field(default='', repr=False)
    issues: tuple[str, ...] = ()
    cached_input_cost_per_million: float | None = None
    lead_batch_size: int = 100
    lead_batch_concurrency: int = 4
    lead_prompt: str = 'oppora-filter-v2'
    thinking: str = 'provider_default'

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

    # Oppora scores leads with DeepSeek, so a stored DeepSeek key selects it
    # unless LLM_PROVIDER names another provider explicitly.
    provider = value('LLM_PROVIDER', 'deepseek' if value('DEEPSEEK_API_KEY') else 'groq').lower()
    if provider == 'groq':
        model = value('LLM_MODEL', 'openai/gpt-oss-120b')
        key = value('GROQ_API_KEY')
        base_url = 'https://api.groq.com/openai/v1'
        default_format = 'json_schema'
    elif provider == 'deepseek':
        model = value('LLM_MODEL') or value('DEEPSEEK_MODEL', 'deepseek-chat')
        key = value('DEEPSEEK_API_KEY') or value('LLM_API_KEY')
        base_url = value('LLM_BASE_URL') or value('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        default_format = 'json_object'
    else:
        model = value('LLM_MODEL', '')
        key = value('LLM_API_KEY')
        base_url = value('LLM_BASE_URL')
        default_format = 'json_schema'

    if provider not in {'groq', 'deepseek', 'openai_compatible'}:
        issues.append('LLM_PROVIDER must be groq, deepseek, or openai_compatible.')
    if provider == 'groq' and not key:
        issues.append('Add GROQ_API_KEY to the backend .env file.')
    elif provider == 'deepseek' and not key:
        issues.append('Add DEEPSEEK_API_KEY to the backend .env file.')
    elif provider == 'openai_compatible' and not key:
        issues.append('Add LLM_API_KEY to the backend .env file.')
    if not model:
        issues.append('Set LLM_MODEL in the backend .env file.')
    elif 'your_' in model.lower() or model.lower().endswith('_here'):
        name = 'DEEPSEEK_MODEL' if provider == 'deepseek' and not value('LLM_MODEL') else 'LLM_MODEL'
        issues.append(f'{name} in .env is still a placeholder. Set it to a real model name, e.g. deepseek-chat.')

    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {'http', 'https'} or not parsed_url.netloc or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment:
        issues.append('LLM_BASE_URL must be an HTTP(S) API base URL without credentials or a query string.')

    format_name = value('LLM_RESPONSE_FORMAT', default_format)
    if format_name not in {'json_schema', 'json_object'}:
        issues.append('LLM_RESPONSE_FORMAT must be json_schema or json_object.')
    timeout = number('LLM_TIMEOUT_SECONDS', 60.0, 1, 120)
    # deepseek-flash thinks before answering unless told not to; hidden reasoning tokens count
    # against the output limit. Enabled for DeepSeek: it matches Oppora's ~137 output tokens per
    # lead_scoring call (disabled gives ~16) and scored more accurately in our labelled test.
    thinking = value('LLM_THINKING', 'enabled' if provider == 'deepseek' else 'provider_default').lower()
    if thinking not in {'disabled', 'enabled', 'provider_default'}:
        issues.append('LLM_THINKING must be disabled, enabled or provider_default.')
    token_limit = number('LLM_MAX_OUTPUT_TOKENS', 8192 if thinking == 'enabled' else 2048, 256, 8192)
    if token_limit != int(token_limit):
        issues.append('LLM_MAX_OUTPUT_TOKENS must be an integer.')
    input_rate = rate('LLM_INPUT_COST_PER_MILLION')
    output_rate = rate('LLM_OUTPUT_COST_PER_MILLION')
    cached_rate = rate('LLM_CACHED_INPUT_COST_PER_MILLION')
    jev_key = value('JEV_API_KEY') or value('TYPESAFE_API_KEY')
    # Oppora sends one call per company (about 90 people observed); larger companies are split into batches.
    batch_size = number('LEAD_SCORING_BATCH_SIZE', 100, 1, 200)
    lead_prompt = value('LEAD_SCORING_PROMPT', 'oppora-filter-v2')
    if lead_prompt not in {'oppora-filter-v1', 'oppora-filter-v2'}:
        issues.append('LEAD_SCORING_PROMPT must be oppora-filter-v1 or oppora-filter-v2.')
    concurrency = number('LEAD_SCORING_CONCURRENCY', 4, 1, 16)
    for name, parsed in (('LEAD_SCORING_BATCH_SIZE', batch_size), ('LEAD_SCORING_CONCURRENCY', concurrency)):
        if parsed != int(parsed):
            issues.append(f'{name} must be an integer.')

    return EvaluationSettings(
        provider=provider, model=model, api_key=key, base_url=base_url.rstrip('/'), response_format=format_name,
        timeout_seconds=timeout, max_output_tokens=int(token_limit), input_cost_per_million=input_rate,
        output_cost_per_million=output_rate, task=value('EVALUATION_TASK', 'gtm_intent'),
        jev_api_key=jev_key, issues=tuple(issues), cached_input_cost_per_million=cached_rate,
        lead_batch_size=int(batch_size), lead_batch_concurrency=int(concurrency), lead_prompt=lead_prompt,
        thinking=thinking,
    )


def estimate_cost(settings: EvaluationSettings, input_tokens, output_tokens, cached_input_tokens=None):
    """Estimated USD from configured rates; cached input uses its own rate when set."""
    if not settings.pricing_configured or input_tokens is None or output_tokens is None:
        return None
    cached = cached_input_tokens or 0
    cached_rate = settings.cached_input_cost_per_million
    if cached_rate is None:
        cached, cached_rate = 0, 0
    fresh = max(input_tokens - cached, 0)
    return (fresh * settings.input_cost_per_million + cached * cached_rate
            + output_tokens * settings.output_cost_per_million) / 1_000_000


@dataclass(frozen=True)
class JevSettings:
    """TypeSafe Jev (System One) settings. Jev answers typed questions; it never writes text."""
    api_key: str = field(repr=False)
    base_url: str
    model: str
    timeout_seconds: float
    concurrency: int
    match_threshold: float
    input_cost_per_million: float
    issues: tuple[str, ...] = ()
    provider: str = 'typesafe'

    @property
    def configured(self) -> bool:
        return not self.issues


def load_jev_settings() -> JevSettings:
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

    key = value('JEV_API_KEY') or value('TYPESAFE_API_KEY')
    if not key:
        issues.append('Add JEV_API_KEY to the backend .env file.')
    # The docs give the host; older values ending in /v1 are accepted.
    base_url = (value('JEV_BASE_URL') or value('TYPESAFE_BASE_URL') or 'https://api.typesafe.ai').rstrip('/')
    base_url = base_url[:-3] if base_url.endswith('/v1') else base_url
    return JevSettings(
        api_key=key, base_url=base_url,
        # Pin a versioned model so probability thresholds stay meaningful (jev-latest moves).
        model=value('JEV_MODEL', 'jev-1.13.0'),
        timeout_seconds=number('JEV_TIMEOUT_SECONDS', 30.0, 1, 120),
        concurrency=int(number('JEV_CONCURRENCY', 8, 1, 32)),
        match_threshold=number('JEV_MATCH_THRESHOLD', 0.5, 0.05, 0.95),
        # Published price: $0.042 per million input tokens; output tokens are free.
        input_cost_per_million=number('JEV_INPUT_COST_PER_MILLION', 0.042, 0, 1000),
        issues=tuple(issues),
    )


def directory_path() -> Path:
    """The people directory to search, chosen by DIRECTORY_FILE; only files inside datasets/ are allowed."""
    file_values = dotenv_values(ROOT / '.env', interpolate=False) if (ROOT / '.env').exists() else {}
    name = str(os.environ.get('DIRECTORY_FILE') or file_values.get('DIRECTORY_FILE') or 'company_directory.json').strip()
    datasets = (ROOT / 'datasets').resolve()
    path = (datasets / name).resolve()
    return path if path.parent == datasets and path.suffix == '.json' else datasets / 'company_directory.json'


def is_decision_lab_enabled() -> bool:
    env = os.environ.get('ENABLE_DECISION_LAB')
    if env is not None:
        return env.strip().lower() not in {'false', '0', 'no'}
    file_values = dotenv_values(ROOT / '.env', interpolate=False) if (ROOT / '.env').exists() else {}
    file_val = file_values.get('ENABLE_DECISION_LAB')
    if file_val is not None:
        return str(file_val).strip().lower() not in {'false', '0', 'no'}
    return True


