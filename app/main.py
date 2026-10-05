"""FastAPI application construction and the existing Laya startup lifecycle."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from engines.laya_engine import get_engine
from agents.gtm_agent import get_gtm_agent
from .api.health import router as health_router
from .api.decision import router as decision_router
from .api.planning import router as planning_router
from .api.evaluation import router as evaluation_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("laya_decision_service.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load model weights into memory before accepting traffic."""
    logger.info("Lifespan: Pre-loading Laya Decision Engine & Agent...")
    _ = get_engine()
    _ = get_gtm_agent()
    logger.info("Lifespan: System fully initialized and ready to serve.")
    yield
    logger.info("Lifespan: Shutting down.")


app = FastAPI(
    title="Oppora Standalone Decision Service (Laya)",
    description=(
        "Standalone GTM planning demo using Laya, explicit rules and configured tools. "
        "Runs on local PyTorch Laya without external LLM dependencies."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

# Enable CORS for local dashboards or frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(decision_router)
app.include_router(planning_router)
app.include_router(evaluation_router)
