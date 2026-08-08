"""
api/routers/demo.py
----------------------
Demo Mode: one endpoint that populates 23 real days of history (real
model scores on a synthetic-but-plausible trajectory) plus one demo
League friend, so every feature has something to show without a
presenter manually logging real days first. See services/demo_service.py
for exactly what is and isn't fabricated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_account_service,
    get_history_service,
    get_history_storage_backend,
    get_prediction_service,
    get_recommendation_service,
    get_validation_service,
)
from api.exceptions.errors import BadRequestError
from api.routers.prediction import build_predict_response
from api.schemas.demo import DemoPopulateResponse
from services.account_service import Account, AccountService
from services.demo_service import DemoService
from services.prediction_service import PredictionService
from services.recommendation_service import RecommendationService
from services.storage.base import StorageBackend
from services.validation_service import ValidationService

router = APIRouter(tags=["Demo Mode"])


@router.post(
    "/demo/populate", response_model=DemoPopulateResponse,
    summary="Populate 23 days of real-model-scored demo history plus one demo League friend",
)
def populate_demo(
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
    recommender: RecommendationService = Depends(get_recommendation_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> DemoPopulateResponse:
    history_service = get_history_service(account, storage=storage)
    demo = DemoService(history_service, validator, predictor)
    result = demo.populate(account.user_id, account.display_name or account.email)

    if result.final_prediction is None or result.final_validation is None:
        raise BadRequestError("Could not generate a valid demo day.", error_code="demo_generation_failed")

    account_service.mark_onboarding_complete(account.user_id)

    final_response = build_predict_response(
        result.final_validation, result.final_prediction, recommender, account, persisted=True,
    )
    return DemoPopulateResponse(
        days_created=result.days_created, friend_connected=result.friend_connected,
        final_result=final_response, final_user_data=result.final_validation.cleaned_data,
    )
