"""LLM semantic scoring with deterministic field checks and score arithmetic."""
import hashlib
import json
import logging
import math
import time
from uuid import uuid4

from core.config import load_evaluation_settings
from engines.llm_engine import LLMTransportError
from models.scoring import Evidence, Factor, LLMUsage, ScoreRequest, ScoreResult
from .catalog import FIELDS, POLICY_VERSION, PROMPT_VERSION, WEIGHTS
from .llm import evaluate_criteria
from .policy import axis_coverage, recommend

logger = logging.getLogger(__name__)
VALUES = {'match': 1.0, 'partial': 0.5, 'miss': 0.0, 'unknown': 0.5}
COUNTRY_ALIASES = {
    'us': 'united states', 'usa': 'united states', 'united states of america': 'united states',
    'uk': 'united kingdom', 'gb': 'united kingdom', 'great britain': 'united kingdom',
    'in': 'india', 'ca': 'canada', 'au': 'australia', 'de': 'germany', 'fr': 'france',
    'sg': 'singapore', 'ae': 'united arab emirates', 'uae': 'united arab emirates',
}


def normalize(value, field):
    if isinstance(value, str):
        cleaned = ' '.join(value.split()).casefold()
        return COUNTRY_ALIASES.get(cleaned, cleaned) if field == 'company.country' else cleaned
    return value


def finish(factor, outcome, reason, evidence=None):
    factor.outcome = outcome
    factor.value = VALUES[outcome]
    factor.reason = reason
    factor.evidence = evidence
    return factor


def structured(criterion, actual, factor, request):
    field, op, expected = criterion.field, criterion.operator, criterion.value
    evidence = Evidence(source_id=field, text=json.dumps(actual, ensure_ascii=False), kind='field_value')
    outcome = 'unknown'
    if op == 'in':
        outcome = 'match' if normalize(actual, field) in {normalize(v, field) for v in expected} else 'miss'
    elif op == 'between':
        outcome = 'match' if expected[0] <= actual <= expected[1] else 'miss'
    elif op == 'gte':
        outcome = 'match' if actual >= expected else 'miss'
    elif op == 'lte':
        # Recency is supplied as of observed_on; advance it to the requested scoring date.
        if field == 'signals.recent_funding_days':
            actual += (request.as_of - request.lead.signals.observed_on).days
            evidence.text += f'; observed_on={request.lead.signals.observed_on}; days_as_of={actual}'
        outcome = 'match' if actual <= expected else 'miss'
    elif op == 'eq':
        outcome = 'match' if actual == expected else 'miss'
    elif op in {'contains_any', 'contains_all'}:
        wanted = {normalize(v, field) for v in expected}
        present = {normalize(v, field) for v in actual}
        matched = len(wanted & present)
        if (op == 'contains_any' and matched) or wanted <= present:
            outcome = 'match'
        elif matched:
            outcome = 'partial'
        elif request.lead.company.technology_inventory_complete:
            outcome = 'miss'
        else:
            factor.status = 'missing_data'
            return finish(factor, 'unknown', 'The technology inventory is incomplete; absence cannot establish a mismatch.', evidence)
        evidence.text += f'; inventory_complete={request.lead.company.technology_inventory_complete}'
    return finish(factor, outcome, f'The supplied field was evaluated using {op}.', evidence)


def semantic(criterion, actual, factor, decision):
    """Accept a known outcome only with a quote attributed to its own input field."""
    factor.model_decision = decision.outcome
    if decision.outcome == 'unknown':
        return finish(factor, 'unknown', 'LLM assessment: ' + decision.reason)
    evidence = decision.evidence
    if (evidence is None or evidence.source_id != criterion.field
            or not evidence.quote.strip() or evidence.quote not in actual):
        factor.status = 'evidence_missing'
        return finish(factor, 'unknown', 'The LLM decision lacked a verifiable quote from this input field.')
    return finish(factor, decision.outcome, 'LLM assessment: ' + decision.reason,
                  Evidence(source_id=criterion.field, text=evidence.quote, kind='source_quote'))


def aggregate(request, factors):
    weighted = [f for f in factors if not f.hard_requirement]
    total_weight = sum(f.weight for f in weighted)
    known_weight = sum(f.weight for f in weighted if f.outcome != 'unknown')
    coverage = known_weight / total_weight
    disqualified = [f.criterion_id for f in factors if f.hard_requirement and f.outcome == 'miss']
    unresolved_hard = any(f.hard_requirement and f.outcome not in {'match', 'miss'} for f in factors)
    has_error = any(f.status == 'model_error' for f in factors)

    def axis_value(axis):
        items = [f for f in weighted if f.axis == axis]
        weight = sum(f.weight for f in items)
        return (100 * sum(f.weight * f.value for f in items) / weight) if weight else None

    fit = axis_value('fit')
    has_intent = any(f.axis == 'intent' for f in weighted)
    intent = axis_value('intent') if has_intent else None
    alpha = request.profile.alpha_fit if has_intent else 1.0
    priority = alpha * fit + (1 - alpha) * (intent if intent is not None else 0)
    for factor in weighted:
        axis_weight = sum(f.weight for f in weighted if f.axis == factor.axis)
        multiplier = alpha if factor.axis == 'fit' else (1 - alpha)
        factor.impact = round(100 * factor.weight * (factor.value - 0.5) / axis_weight * multiplier, 6)

    if has_error:
        status = 'failed'
    elif (coverage < request.profile.min_coverage
          or axis_coverage(factors, 'fit') < request.profile.min_coverage
          or (unresolved_hard and not disqualified)):
        status = 'insufficient_data'
    else:
        status = 'scored'
    # A known hard miss remains visible even when other data prevents a number.
    band = 'disqualified' if disqualified else None
    if status != 'scored':
        return status, None, None, None, coverage, band, disqualified
    nearest = lambda value: math.floor(value + 0.5)
    rounded = nearest(priority)
    if band is None:
        band = 'hot' if rounded >= request.profile.hot_threshold else 'warm' if rounded >= request.profile.warm_threshold else 'cold'
    return status, None if disqualified else rounded, nearest(fit), nearest(intent) if intent is not None else None, coverage, band, disqualified


async def score_lead(request: ScoreRequest, settings=None) -> ScoreResult:
    started = time.perf_counter()
    facts = request.lead.model_dump(mode='json')
    factors = []
    warnings = ['This result uses only the supplied lead and criteria. No CRM or dataset was queried.']
    pending = []
    usage = LLMUsage()
    settings = settings or load_evaluation_settings()
    for criterion in request.profile.criteria:
        spec = FIELDS[criterion.field]
        section, key = criterion.field.split('.')
        actual = facts[section].get(key)
        factor = Factor(
            criterion_id=criterion.id, field=criterion.field,
            requirement=f'{criterion.operator} {json.dumps(criterion.value, ensure_ascii=False)}',
            axis=spec['axis'], hard_requirement=criterion.hard_requirement,
            evaluator='llm' if criterion.operator == 'semantic' else 'structured',
            weight=0 if criterion.hard_requirement else WEIGHTS[criterion.importance], reason='',
        )
        if actual is None or (isinstance(actual, str) and normalize(actual, criterion.field) in {
            '', 'unknown', 'n/a', 'not available', 'not provided', 'null', '-', '—'
        }):
            factor.status = 'missing_data'
            factor.reason = 'No value was supplied for this field.'
        elif spec['axis'] == 'intent' and (
            request.lead.signals.observed_on is None or request.lead.signals.observed_on > request.as_of
        ):
            factor.status = 'missing_data'
            factor.reason = 'Intent signals need an observation date on or before the scoring date.'
        else:
            try:
                if criterion.operator == 'semantic':
                    pending.append((criterion, actual, factor))
                else:
                    factor = structured(criterion, actual, factor, request)
                if spec['axis'] == 'intent' and factor.outcome != 'unknown':
                    age = (request.as_of - request.lead.signals.observed_on).days
                    factor.value = 0.5 + (factor.value - 0.5) * 0.5 ** (age / 30)
                    factor.reason += f' Signal contribution decays toward neutral with age ({age} days; 30-day half-life).'
            except Exception:
                logger.exception('Criterion evaluation failed: %s', criterion.id)
                factor.status = 'model_error'
                finish(factor, 'unknown', 'Evaluation failed. Retry when the decision service is available.')
        factors.append(factor)

    if pending:
        try:
            if settings.issues:
                raise ValueError('LLM configuration is incomplete.')
            context = {'offering': request.profile.offering, 'buyer_persona': request.profile.buyer_persona}
            if any(c.field.startswith('person.') for c, _, _ in pending):
                context['role_context'] = request.lead.person.model_dump(mode='json', exclude_none=True)
            decisions = await evaluate_criteria(pending, settings, usage, context)
            for criterion, actual, factor in pending:
                semantic(criterion, actual, factor, decisions[criterion.id])
        except Exception as exc:
            logger.warning('LLM scoring failed (%s).', type(exc).__name__)
            reason = exc.message if isinstance(exc, LLMTransportError) else 'The LLM returned an incomplete or invalid scoring response. Check configuration and retry.'
            for _criterion, _actual, factor in pending:
                factor.status = 'model_error'
                finish(factor, 'unknown', reason)

    status, priority, fit, intent, coverage, band, disqualified = aggregate(request, factors)
    recommendation, recommendation_reasons, eligibility = recommend(request.profile, factors, status, fit)
    if any(f.evaluator == 'llm' and f.evidence for f in factors):
        warnings.append('LLM quotes are checked against the supplied text. Semantic correctness and LLM explanations are not independently verified.')
    if status == 'failed':
        explanation = 'A criterion could not be evaluated because of a service error. No numeric score was produced.'
    elif status == 'insufficient_data':
        explanation = 'There is insufficient coverage or an unresolved hard requirement. Supply the missing facts to obtain a score.'
    elif disqualified:
        explanation = 'A mandatory requirement failed. Priority is withheld; any fit and intent scores are diagnostic only.'
    else:
        explanation = f'Priority {priority}/100 follows the configured criterion outcomes and weights.'
    if disqualified:
        explanation += ' Hard requirements failed: ' + ', '.join(disqualified) + '.'
    gaps = [f.criterion_id for f in factors if f.outcome == 'unknown']
    if gaps:
        explanation += ' Unresolved criteria: ' + ', '.join(gaps) + '.'
    versions = {'profile_id': request.profile.id, 'profile_version': request.profile.version,
                'policy': POLICY_VERSION, 'weights': 'importance-3-2-1-v1',
                'evaluator_prompt': PROMPT_VERSION,
                'llm_provider': settings.provider if pending else 'not_used',
                'llm_model': settings.model if pending else 'not_used'}
    canonical = json.dumps({'request': request.model_dump(mode='json'), 'versions': versions},
                           ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return ScoreResult(
        request_id=str(uuid4()), lead_id=request.lead.id, status=status, priority=priority,
        recommendation=recommendation, recommendation_reasons=recommendation_reasons,
        eligibility=eligibility, fit_coverage=axis_coverage(factors, 'fit'),
        intent_coverage=axis_coverage(factors, 'intent'),
        fit=fit, intent=intent, band=band, coverage=coverage, factors=factors,
        disqualified_by=disqualified, explanation=explanation, warnings=warnings, versions=versions,
        input_fingerprint=hashlib.sha256(canonical.encode()).hexdigest(), as_of=request.as_of,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        llm_usage=usage,
    )
