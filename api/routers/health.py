"""api/routers/health.py"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.core.config import Settings, get_settings
from api.dependencies.services import get_model_manager
from models.model_manager import ModelManager

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    app_version: str


class ReadinessResponse(BaseModel):
    status: str
    models_loaded: bool
    classification_model: str
    regression_model: str


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Always returns 200 if the process is up - does not touch the ML
    models. Use /health/ready to also confirm the models are loaded."""
    return HealthResponse(status="ok", app_name=settings.app_name, app_version=settings.app_version)


@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness check")
def readiness(model_manager: ModelManager = Depends(get_model_manager)) -> ReadinessResponse:
    """Confirms the singleton ModelManager has both trained models
    loaded - the same instance every prediction request will use, so a
    200 here means predictions are actually ready to serve, not just
    that the web server process started."""
    return ReadinessResponse(
        status="ok",
        models_loaded=True,
        classification_model=model_manager.classification_registry.model_name,
        regression_model=model_manager.regression_registry.model_name,
    )
