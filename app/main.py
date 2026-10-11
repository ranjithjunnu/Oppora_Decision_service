"""LLM-first scoring; local-model Decision Lab is an explicit startup option."""
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import is_decision_lab_enabled
from .api.health import router as health_router
from .api.scoring import router as scoring_router
from .api.discovery import router as discovery_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Provider requests happen only when a user asks for a draft or score.
    yield


app = FastAPI(
    title='Oppora AI Lead Scoring',
    description='LLM assessment of lead fit, deterministic field checks and transparent scoring.',
    version='1.4.0', lifespan=lifespan,
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
if is_decision_lab_enabled():
    from .api.evaluation import router as evaluation_router
    app.include_router(evaluation_router)

