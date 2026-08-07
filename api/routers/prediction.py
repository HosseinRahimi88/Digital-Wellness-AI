"""
api/routers/prediction.py
----------------------------
The core prediction endpoint. Orchestrates the exact same sequence a
real Streamlit Prediction-page submission runs - ValidationService ->
PredictionService.predict() -> RecommendationService.generate() ->
HistoryService.record() (if persist=True) - none of that sequence's
logic is reimplemented here, only sequenced.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_history_service,
    get_history_storage_backend,
    get_prediction_service,
    get_recommendation_service,
    get_validation_service,
)
from api.exceptions.errors import DomainValidationError
from api.schemas.prediction import (
    PredictRequest,
    PredictResponse,
    RecommendationResponse,
    SHAPFeatureResponse,
    UncertaintyResponse,
)
from services.account_service import Account
from services.prediction_service import PredictionService
from services.recommendation_service import RecommendationService
from services.storage.base import StorageBackend
from services.validation_service import ValidationService

router = APIRouter(prefix="/predict", tags=["Prediction"])


@router.post(
    "", response_model=PredictResponse,
    summary="Run a real prediction (classification + regression + SHAP + uncertainty + recommendations)",
)
def predict(
    payload: PredictRequest,
    account: Account = Depends(get_current_account),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
    recommender: RecommendationService = Depends(get_recommendation_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> PredictResponse:
    validation = validator.validate(payload.user_data)
    if not validation.is_valid:
        raise DomainValidationError(validation.errors)

    result = predictor.predict(validation.cleaned_data)
    recommendations = recommender.generate(result.shap_features)

    persisted = False
    if payload.persist:
        history_service = get_history_service(account, storage=storage)
        history_service.record(validation.cleaned_data, result)
        persisted = True

    return PredictResponse(
        prediction=result.prediction,
        confidence=result.confidence,
        confidence_percent=result.confidence_percent,
        probabilities=result.probabilities,
        regression_score=result.regression_score,
        model_name=result.model_name,
        prediction_time_ms=result.prediction_time_ms,
        timestamp=result.timestamp,
        uncertainty=UncertaintyResponse.from_uncertainty_result(result.uncertainty),
        shap_features=[SHAPFeatureResponse.from_shap_feature(f) for f in result.shap_features],
        recommendations=[RecommendationResponse.from_recommendation(r) for r in recommendations],
        persisted=persisted,
    )
