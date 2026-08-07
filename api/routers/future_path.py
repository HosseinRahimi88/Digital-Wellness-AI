"""api/routers/future_path.py"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_prediction_service, get_validation_service
from api.exceptions.errors import DomainValidationError
from api.schemas.future_path import (
    FuturePathRequest,
    FuturePathResponse,
    PathDefinitionResponse,
    PathResultResponse,
)
from services.account_service import Account
from services.future_path_service import PATH_DEFINITIONS, FuturePathService
from services.prediction_service import PredictionService
from services.validation_service import ValidationService

router = APIRouter(prefix="/future-path", tags=["Future Path"])


@router.get(
    "/definitions", response_model=list[PathDefinitionResponse],
    summary="Every named future-path scenario this endpoint can evaluate",
)
def list_path_definitions() -> list[PathDefinitionResponse]:
    return [
        PathDefinitionResponse(key=d.key, name=d.name, description=d.description)
        for d in PATH_DEFINITIONS
    ]


@router.post(
    "/compare", response_model=FuturePathResponse,
    summary="Compare status-quo vs. gradual/committed/detox/drift habit-change scenarios",
)
def compare_future_paths(
    payload: FuturePathRequest,
    account: Account = Depends(get_current_account),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
) -> FuturePathResponse:
    validation = validator.validate(payload.user_data)
    if not validation.is_valid:
        raise DomainValidationError(validation.errors)

    comparison = FuturePathService.compare(
        validation.cleaned_data, predictor, path_keys=payload.path_keys,
    )
    return FuturePathResponse(
        paths=[PathResultResponse.from_path_result(r) for r in comparison.paths],
        best_path_key=comparison.best_path_key,
        worst_path_key=comparison.worst_path_key,
    )
