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

from datetime import date

import logging

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_history_service,
    get_history_storage_backend,
    get_prediction_service,
    get_recommendation_service,
    get_validation_service,
)
from api.exceptions.errors import AlreadyCheckedInError, DomainValidationError
from api.schemas.prediction import (
    ConfidenceLabelResponse,
    DimensionBreakdownResponse,
    FutureScoreResponse,
    OODReportResponse,
    PredictRequest,
    PredictResponse,
    RecommendationResponse,
    SHAPFeatureResponse,
    UncertaintyResponse,
)
from services.insight.future_score_service import FutureScoreService
from utils.feature_derivation import derive_features
from utils.screen_load import screen_load_subscore
from services.insight.insight_service import InsightService
from services.wellness.tone_service import frame_result, frame_result_i18n
from services.identity.account_service import Account
from services.ml.prediction_service import PredictionService
from services.wellness.recommendation_service import RecommendationService
from services.storage.base import StorageBackend
from services.ml.validation_service import ValidationService
from utils.dimension_scores import compute_dimension_scores

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["Prediction"])


def recent_scores_from(entries, today_score=None) -> list[float]:
    """This user's daily scores, oldest first, with today's on the end.

    Excluded days are already gone by the time they reach here (the
    caller reads history with include_excluded=False), which is the
    right behaviour: a day the user said "this was not my data" about
    should not bend the direction of their week.
    """
    ordered = sorted(
        (e for e in (entries or []) if e.get("health_score") is not None),
        key=lambda e: e.get("date") or "",
    )
    scores = [float(e["health_score"]) for e in ordered]
    if today_score is not None:
        scores.append(float(today_score))
    return scores


def build_predict_response(
    validation, result, recommender: RecommendationService, account: Account,
    excluded_categories: set[str] | None = None, persisted: bool = False,
    replaced_existing: bool = False,
    recent_scores: list[float] | None = None,
) -> PredictResponse:
    """Assembles the full `PredictResponse` (recommendations, dimension
    breakdown, confidence label, OOD check, tone-aware framing) from a
    real `ValidationResult` + `PredictionResult` pair. Pulled out of
    `predict()` so any other caller that runs the real pipeline on real
    or synthetic-but-real-model-scored inputs (e.g. services/demo/demo_service.py
    via api/routers/demo.py) gets the exact same response shape instead
    of a second, drifting reimplementation."""
    recommendations = recommender.generate(
        result.shap_features,
        excluded_categories=excluded_categories or set(),
        # C-2: the day the user actually submitted, so each
        # recommendation can quote their own number back to them.
        user_data=validation.cleaned_data,
    )
    # The seven-day-ahead figure, derived from the classifier - which is
    # the only model here whose target is genuinely seven days out.
    # today_score is half of the Output-2 estimate: the classifier picks
    # the band, this picks the position inside it.
    # `recent_scores` is this user's own daily scores, oldest first. It
    # is what makes the seven-day band personal: without it two people
    # with an identical day get an identical band, however differently
    # their weeks have been going. Optional on purpose - a caller that
    # has no history to hand (a one-off prediction for an unsaved day)
    # gets exactly the estimate this returned before.
    # `screen_load_today` is the other half. The seven-day calibration is
    # measured on the wellbeing axis, because that is the axis the class
    # label bands; the digital-load half is carried forward from the day
    # the user actually logged rather than forecast, since nothing in
    # this dataset predicts a person's screen time a week out. Computed
    # from the same cleaned data the score was, so the two halves cannot
    # come from different days.
    future_score = FutureScoreService.estimate(
        result.probabilities, result.prediction,
        today_score=result.regression_score,
        screen_load_today=screen_load_subscore(validation.cleaned_data),
        recent_scores=recent_scores,
    )
    dimension_breakdown = compute_dimension_scores(validation.cleaned_data)
    confidence_label = InsightService.confidence_label(result.confidence_percent, result.uncertainty)
    ood = InsightService.check_out_of_distribution(validation.cleaned_data)

    return PredictResponse(
        prediction=result.prediction,
        confidence=result.confidence,
        confidence_percent=result.confidence_percent,
        probabilities=result.probabilities,
        regression_score=result.regression_score,
        future_score=FutureScoreResponse.from_result(future_score),
        model_name=result.model_name,
        prediction_time_ms=result.prediction_time_ms,
        timestamp=result.timestamp,
        uncertainty=UncertaintyResponse.from_uncertainty_result(result.uncertainty),
        shap_features=[SHAPFeatureResponse.from_shap_feature(f) for f in result.shap_features],
        recommendations=[RecommendationResponse.from_recommendation(r) for r in recommendations],
        dimension_breakdown=DimensionBreakdownResponse(**dimension_breakdown),
        confidence_label=ConfidenceLabelResponse.model_validate(confidence_label, from_attributes=True),
        ood=OODReportResponse.model_validate(ood, from_attributes=True),
        result_framing=frame_result(result.regression_score, account.recommendation_tone),
        result_framing_i18n=frame_result_i18n(result.regression_score, account.recommendation_tone),
        persisted=persisted,
        replaced_existing=replaced_existing,
    )


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
    # Recompute total_screen_min and everything derived from it from the
    # raw category minutes, rather than trusting the copy the client sent.
    #
    # schema.js already does this in the browser before POSTing, so the
    # app's own form is unaffected. But this endpoint scores and records a
    # check-in from whatever arrives, and it was taking the client's
    # arithmetic as fact: with the five category fields summing to 658.5
    # minutes, a payload carrying a stale total of 140 scored 88.25 where
    # the honest total scores 69.75. An eighteen-point error in the number
    # the whole app is about, from a field the server is perfectly capable
    # of computing itself.
    #
    # Done here rather than inside ValidationService because the internal
    # callers that share that service - future_path_service and
    # parallel_twin_service - deliberately manage their own derived
    # fields, notably dropping screen_ewma_baseline so the personal
    # baseline is not silently redefined. This is the untrusted-input
    # boundary; those are not.
    validation = validator.validate(derive_features(dict(payload.user_data)))
    if not validation.is_valid:
        raise DomainValidationError(validation.errors)

    # The classifier predicts the health class SEVEN DAYS AHEAD, and where
    # somebody is heading depends on their recent trajectory - so it is
    # given this user's own earlier check-ins to build trend features
    # from. Days the user excluded from their trend are left out, matching
    # what the rest of the app already honours. A brand-new user simply
    # passes an empty list and the trend features arrive as "unknown",
    # which the model handles natively.
    try:
        prior_entries = get_history_service(account, storage=storage).get_all(
            include_excluded=False
        )
    except Exception:  # noqa: BLE001 - a history read must never block a prediction
        logger.warning("Could not read history for trend features; predicting same-day only.", exc_info=True)
        prior_entries = []

    result = predictor.predict(validation.cleaned_data, history=prior_entries)

    persisted = False
    replaced_existing = False
    if payload.persist:
        history_service = get_history_service(account, storage=storage)
        # One main check-in per day. record() is an upsert, so a second
        # persisted submission for the same date used to replace the
        # first with no warning at all - verified against the running
        # app, where an 84.01 became a 78.41 and only the second
        # survived. Losing a real recorded day is not something to do
        # as a side effect, so it now takes an explicit edit flag from
        # the client, and the response says plainly that a replacement
        # happened.
        today = date.today().isoformat()
        already = any(
            entry.get("date") == today
            for entry in history_service.get_all(include_excluded=True)
        )
        if already and not payload.allow_update:
            raise AlreadyCheckedInError(today)
        history_service.record(validation.cleaned_data, result)
        persisted = True
        replaced_existing = already

    # The same entries the classifier's trend features came from, as a
    # plain list of scores in date order, plus today's. This is what
    # makes the seven-day band move with THIS user rather than with
    # their class - see services/insight/future_score_service.py's `_momentum`.
    recent_scores = recent_scores_from(prior_entries, result.regression_score)

    return build_predict_response(
        validation, result, recommender, account,
        excluded_categories=set(payload.excluded_recommendation_categories), persisted=persisted,
        replaced_existing=replaced_existing,
        recent_scores=recent_scores,
    )
