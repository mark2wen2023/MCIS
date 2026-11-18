"""Review-only minimal liveness factory; no CLI, automatic startup or readiness claim."""
from fastapi import FastAPI

from .health import health


def create_health_app():
    app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    app.get("/api/v1/health", tags=["meta"])(health)
    return app
