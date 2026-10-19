"""LLM lead scoring with a separate optional LLM decision workspace."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import is_decision_lab_enabled
from .api.health import router as health_router
from .api.scoring import router as scoring_router
from .api.discovery import router as discovery_router
from .api.lead_batches import router as lead_batches_router
from .api.ai_admin import router as ai_admin_router
from scoring.repository import recover_interrupted


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Restore durable run state; no provider requests occur during startup.
    recover_interrupted()
    yield


app = FastAPI(
    title='Oppora AI Lead Scoring',
    description='LLM lead filtering and scoring, saved assessments and observable AI calls.',
    version='1.7.0', lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://127.0.0.1:5173', 'http://localhost:5173',
                   'http://127.0.0.1:4173', 'http://localhost:4173'],
    allow_credentials=False, allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type', 'Accept'],
)
app.include_router(health_router)
app.include_router(scoring_router)
app.include_router(discovery_router)
app.include_router(lead_batches_router)
app.include_router(ai_admin_router)
if is_decision_lab_enabled():
    from .api.evaluation import router as evaluation_router
    app.include_router(evaluation_router)

