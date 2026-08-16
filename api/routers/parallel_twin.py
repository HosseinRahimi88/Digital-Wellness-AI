"""
api/routers/parallel_twin.py
-------------------------------
ParallelTwinService.compare() requires a REAL prediction result (with
SHAP features, to know which areas to improve) plus
DashboardService.split_shap_by_direction() to isolate the "areas to
improve" subset - this router runs that exact real sequence
(PredictionService.predict() with SHAP -> DashboardService split ->
ParallelTwinService.compare()) rather than reimplementing any part of
it.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_prediction_service, get_validation_service
from api.exceptions.errors import DomainValidationError
from api.schemas.parallel_twin import ParallelTwinRequest, ParallelTwinResponse, TwinAdjustmentResponse
from services.identity.account_service import Account
from services.insight.dashboard_service import DashboardService
from services.insight.parallel_twin_service import ParallelTwinService
from services.ml.prediction_service import PredictionService
from services.ml.validation_service import ValidationService

router = APIRouter(prefix="/parallel-twin", tags=["Parallel Twin"])


@router.post(
    "/compare", response_model=ParallelTwinResponse,
    summary="Compare the real prediction against a hypothetical 'twin' with SHAP-flagged habits improved",
)
def compare_parallel_twin(
    payload: ParallelTwinRequest,
    account: Account = Depends(get_current_account),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
) -> ParallelTwinResponse:
    validation = validator.validate(payload.user_data)
    if not validation.is_valid:
        raise DomainValidationError(validation.errors)

    real_result = predictor.predict(validation.cleaned_data)  # compute_shap=True (default) - needed below
    highlights = DashboardService.split_shap_by_direction(real_result.shap_features)

    comparison = ParallelTwinService.compare(
        validation.cleaned_data, highlights.areas_to_improve, real_result, predictor,
    )
    if comparison is None:
        return ParallelTwinResponse(available=False)

    return ParallelTwinResponse(
        available=True,
        adjustments=[TwinAdjustmentResponse(**asdict(a)) for a in comparison.adjustments],
        real_prediction=getattr(comparison.real_result, "prediction", None),
        real_regression_score=getattr(comparison.real_result, "regression_score", None),
        twin_prediction=getattr(comparison.twin_result, "prediction", None),
        twin_regression_score=getattr(comparison.twin_result, "regression_score", None),
        score_delta=comparison.score_delta,
        class_changed=comparison.class_changed,
    )
