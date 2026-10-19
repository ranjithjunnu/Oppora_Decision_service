"""One explicitly submitted case, one LLM result. No dataset execution."""
from fastapi import APIRouter, HTTPException

from core.config import load_evaluation_settings
from evaluators.service import evaluate_case
from models.evaluation import DecisionCriterion, EvaluationCase, EvaluationRequest, EvaluationResponse
from evaluators.criteria import gtm_intent_criterion


router = APIRouter(tags=['Manual evaluation'])


def configured_criterion(task: str) -> DecisionCriterion | None:
    if task != 'gtm_intent':
        return None
    return gtm_intent_criterion()


@router.get('/evaluate/config', summary='Public configuration for the manual console')
async def evaluation_config():
    settings = load_evaluation_settings()
    default = configured_criterion(settings.task)
    return {
        'llm': {'provider': settings.provider, 'model': settings.model or None, 'configured': not settings.issues,
                'issues': list(settings.issues), 'pricing_configured': settings.pricing_configured},
        'default_criterion': default.model_dump() if default else None,
        'evaluation_issues': [] if default else ['The query-only console requires EVALUATION_TASK=gtm_intent. Custom criteria can be supplied through the API.'],
        'limits': {'query_chars': 8000, 'context_chars': 12000, 'input_chars': 20000},
    }


@router.post('/evaluate', response_model=EvaluationResponse, summary='Evaluate a bounded decision with the configured LLM')
async def evaluate(request: EvaluationRequest):
    settings = load_evaluation_settings()
    criterion = request.criterion or configured_criterion(settings.task)
    if criterion is None:
        raise HTTPException(422, 'Supply a criterion with instructions and choices, or configure EVALUATION_TASK=gtm_intent.')
    values = request.model_dump(exclude={'criterion', 'request_id'})
    if request.request_id is not None:
        values['request_id'] = request.request_id
    case = EvaluationCase(**values, criterion=criterion)
    return await evaluate_case(case, settings)
