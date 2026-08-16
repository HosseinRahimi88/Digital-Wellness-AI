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

from fastapi import APIRouter, Depends, Query
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
from services.identity.account_service import Account
from services.ml.prediction_service import PredictionService
from services.wellness.recommendation_service import RecommendationService
from services.identity.report_service import ReportService
from services.ml.validation_service import ValidationService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/pdf", summary="Generate a downloadable PDF wellness report for a given day's feature values")
def generate_pdf_report(
    payload: PredictRequest,
    lang: str = Query(
        "en",
        description=(
            "Report language: en, fa, ar or zh (C-5-9). If the server cannot "
            "typeset the requested language the report is produced in English "
            "with a note saying why, rather than as unreadable boxes."
        ),
    ),
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
    recommendations = recommender.generate(result.shap_features, user_data=validation.cleaned_data)
    pdf_buffer = report_service.generate(validation.cleaned_data, result, recommendations, lang=lang)
    pdf_buffer.seek(0)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=wellness_report_{account.user_id[:8]}.pdf"},
    )
