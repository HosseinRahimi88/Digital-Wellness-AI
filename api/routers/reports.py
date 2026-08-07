"""
api/routers/reports.py
--------------------------
Generates the same PDF ReportService already produces for the
Streamlit app - this endpoint runs a real prediction (reusing
PredictionService/RecommendationService, not reimplementing anything)
and streams ReportService.generate()'s BytesIO straight back as the
response body.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_prediction_service,
    get_recommendation_service,
    get_report_service,
    get_validation_service,
)
from api.exceptions.errors import DomainValidationError
from api.schemas.prediction import PredictRequest
from services.account_service import Account
from services.prediction_service import PredictionService
from services.recommendation_service import RecommendationService
from services.report_service import ReportService
from services.validation_service import ValidationService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/pdf", summary="Generate a downloadable PDF wellness report for a given day's feature values")
def generate_pdf_report(
    payload: PredictRequest,
    account: Account = Depends(get_current_account),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
    recommender: RecommendationService = Depends(get_recommendation_service),
    report_service: ReportService = Depends(get_report_service),
) -> StreamingResponse:
    validation = validator.validate(payload.user_data)
    if not validation.is_valid:
        raise DomainValidationError(validation.errors)

    result = predictor.predict(validation.cleaned_data)
    recommendations = recommender.generate(result.shap_features)
    pdf_buffer = report_service.generate(validation.cleaned_data, result, recommendations)
    pdf_buffer.seek(0)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=wellness_report_{account.user_id[:8]}.pdf"},
    )
