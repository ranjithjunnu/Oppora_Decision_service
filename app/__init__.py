"""Lead scoring entry point: uvicorn app:app and python app.py."""
from .main import app, lifespan
from .api.health import health_check

__all__ = ['app', 'lifespan', 'health_check']
