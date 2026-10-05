"""Compatibility entry point: uvicorn app:app and from app import app still work."""
from .main import app, lifespan
from .api.health import health_check
from .api.decision import make_decision
from .api.planning import plan_gtm_workflow

__all__ = ["app", "lifespan", "health_check", "make_decision", "plan_gtm_workflow"]
