"""
api/schemas/prediction.py
----------------------------
Request/response models for the core prediction endpoint.

Deliberate design choice on the request side: `PredictRequest.user_data`
is a flexible `dict[str, float | int | str | bool]`, not ~50 individually
declared Pydantic fields mirroring core.feature_schema.FEATURE_SCHEMA.
Hardcoding every feature name/bound a second time here would be exactly
the kind of duplicated business logic this migration is required to
avoid - FEATURE_SCHEMA is already the single source of truth, enforced
by the existing ValidationService (called by the router, not
reimplemented here). GET /api/v1/schema/features exposes that same
schema read-only so API clients can build a valid payload without
guessing. Pydantic still strongly types the response side - every
field the service layer actually returns is declared below, not passed
through as a raw dict.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    user_data: dict[str, float | int | str | bool | None] = Field(
        ...,
        description=(
            "Raw feature values keyed by name - see GET /api/v1/schema/features "
            "for the full set of accepted keys, types, and bounds. Validated by "
            "the same ValidationService the Streamlit app uses; invalid values "
            "are reported per-field in a 422 response, not silently dropped."
        ),
    )
    persist: bool = Field(
        default=True,
        description="If true (default), record this prediction to the authenticated user's history, exactly like a real Prediction-page submission. Set false for a throwaway/exploratory prediction that should not appear in history or analytics.",
    )
    allow_update: bool = Field(
        default=False,
        description=(
            "Permit replacing today's already-recorded check-in. One "
            "main check-in per day is the rule; without this flag a "
            "second persisted submission for a date that already has "
            "one is refused instead of silently overwriting it. That "
            "overwrite was the old behaviour and it lost the first "
            "day's real result with no warning - verified live: an 84.01 "
            "was replaced by a 78.41 and only the second survived. The "
            "client sets this from an explicit 'I am editing today's "
            "check-in' control, never by default."
        ),
    )
    excluded_recommendation_categories: list[str] = Field(
        default_factory=list,
        description=(
            "Recommendation categories (e.g. 'Sleep', 'Notifications') the user has asked not to be "
            "coached on. This does NOT change the prediction itself - every model input is still used "
            "exactly as submitted, because the trained model requires its full feature set and silently "
            "dropping or substituting a value would produce a misleading score. It only filters which "
            "categories RecommendationService is allowed to surface."
        ),
    )


class SHAPFeatureResponse(BaseModel):
    feature: str
    value: Any
    shap_value: float
    abs_shap: float
    direction: str
    score: float

    @staticmethod
    def from_shap_feature(f) -> "SHAPFeatureResponse":
        return SHAPFeatureResponse(
            feature=f.feature, value=f.value, shap_value=f.shap_value,
            abs_shap=f.abs_shap, direction=f.direction, score=f.score,
        )


class UncertaintyResponse(BaseModel):
    available: bool
    regression_lower: float | None = None
    regression_upper: float | None = None
    regression_interval_width: float | None = None
    coverage_target: float
    classification_set: list[str]
    classification_set_size: int
    entropy: float | None = None
    entropy_normalized: float | None = None
    uncertainty_label: str
    explanation: str
    calibration_sample_size: int

    @staticmethod
    def from_uncertainty_result(u) -> "UncertaintyResponse | None":
        if u is None:
            return None
        return UncertaintyResponse(**u.to_dict())


class RecommendationResponse(BaseModel):
    title: str
    description: str
    category: str
    priority: str
    icon: str
    action: str
    success_metric: str
    safety_note: str
    source_field: str = ""
    # C-2. The user's own logged value for source_field and the target
    # the rule's deterministic formula produced from it.
    observed_value: float | None = None
    target_value: float | None = None
    # {part: {lang: text}} - title/description/action/success_metric in
    # all four languages, numbers already substituted. The English
    # fields above stay as they were, so an older client is unaffected.
    text_i18n: dict[str, dict[str, str]] = {}
    # {lang: text} each, for the two fields above that text_i18n does not
    # cover (they are shared across rules, not per-rule text).
    priority_i18n: dict[str, str] = {}
    safety_note_i18n: dict[str, str] = {}

    @staticmethod
    def from_recommendation(r) -> "RecommendationResponse":
        return RecommendationResponse(**r.to_dict())


class DimensionScoreResponse(BaseModel):
    key: str
    label: str
    score: float
    indicator_count: int


class DimensionBreakdownResponse(BaseModel):
    dimensions: list[DimensionScoreResponse]
    overall: float | None


class ConfidenceLabelResponse(BaseModel):
    level: str
    percent: float
    headline: str
    detail: str
    interval_width: float | None = None
    # {part: {lang: text}} - headline/detail in all four languages. The
    # flat English fields above stay as they were, so an older client is
    # unaffected.
    text_i18n: dict[str, dict[str, str]] = {}


class OODFlagResponse(BaseModel):
    field_name: str
    label: str
    value: float
    minimum: float
    maximum: float
    position: str


class OODReportResponse(BaseModel):
    is_out_of_distribution: bool
    flags: list[OODFlagResponse]
    message: str
    # {part: {lang: text}} - the warning in all four languages. `message`
    # stays English so an older client is unaffected.
    text_i18n: dict[str, dict[str, str]] = {}


class FutureScoreResponse(BaseModel):
    """The seven-day-ahead figure. Deliberately separate from
    `regression_score`, which is TODAY's."""

    available: bool
    score: float | None = None
    lower: float | None = None
    upper: float | None = None
    confidence_pct: int = 80
    predicted_class: str | None = None
    # Always "class_typical". The estimate is the score band typical of
    # the class the model expects in seven days, not a personal
    # projection of this user's own number - see
    # services/insight/future_score_service.py. Present so a client cannot show
    # it as a forecast by forgetting what it is.
    # "augmented_rank" (Output 2), "class_typical", or "class_only"
    # (Output 1, where available is False and only the class is shown).
    # "augmented_rank_momentum" when the reader's own recent trajectory
    # moved the band.
    basis: str = "class_typical"
    reason: str = ""
    # How many points of the band came from this user's OWN recent
    # trajectory (positive = climbing), and how many of their days that
    # was measured over. Surfaced so the UI can say WHY the band moved
    # rather than presenting a shifted number with no account of it.
    momentum_shift: float = 0.0
    momentum_days: int = 0

    @staticmethod
    def from_result(r) -> "FutureScoreResponse":
        if r is None:
            return FutureScoreResponse(available=False, reason="not_computed")
        return FutureScoreResponse(
            available=r.available, score=r.score, lower=r.lower, upper=r.upper,
            confidence_pct=r.confidence_pct, predicted_class=r.predicted_class,
            basis=r.basis, reason=r.reason,
            momentum_shift=getattr(r, "momentum_shift", 0.0),
            momentum_days=getattr(r, "momentum_days", 0),
        )


class PredictResponse(BaseModel):
    # NOTE ON HORIZONS - the two headline figures below are about
    # different points in time, which is exactly what was being conflated
    # before:
    #   `prediction`       - the class SEVEN DAYS from now
    #                        (classifier target: future_health_class_7d)
    #   `regression_score` - TODAY's score
    #                        (regressor target: health_score_0_100)
    #   `future_score`     - the seven-day-ahead band, derived from the
    #                        classifier (see FutureScoreResponse)
    # Every one of these is labelled with its horizon in the UI. Showing
    # a number about today next to a label about next week, with neither
    # marked, is how a user ends up believing the app forecast their
    # score and got it wrong.
    prediction: str
    confidence: float | None
    confidence_percent: float
    probabilities: dict[str, float]
    regression_score: float | None
    future_score: FutureScoreResponse | None = None
    model_name: str
    prediction_time_ms: float
    timestamp: str | None
    uncertainty: UncertaintyResponse | None
    shap_features: list[SHAPFeatureResponse]
    recommendations: list[RecommendationResponse]
    dimension_breakdown: DimensionBreakdownResponse
    confidence_label: ConfidenceLabelResponse
    ood: OODReportResponse
    result_framing: str
    # The same sentence in every shipped language, keyed by language
    # code. `result_framing` above stays English so older clients are
    # unaffected; the UI reads this and falls back to that.
    result_framing_i18n: dict[str, str] = {}
    persisted: bool
    # True when this submission replaced a check-in that was already
    # recorded for today (only reachable with allow_update). The client
    # needs to know, because a replacement is what makes the weekly plan
    # and the improvements stale - and because telling the user "updated"
    # rather than "saved" is the difference between an edit they meant
    # and one they did not notice.
    replaced_existing: bool = False
