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

    @staticmethod
    def from_recommendation(r) -> "RecommendationResponse":
        return RecommendationResponse(**r.to_dict())


class PredictResponse(BaseModel):
    prediction: str
    confidence: float | None
    confidence_percent: float
    probabilities: dict[str, float]
    regression_score: float | None
    model_name: str
    prediction_time_ms: float
    timestamp: str | None
    uncertainty: UncertaintyResponse | None
    shap_features: list[SHAPFeatureResponse]
    recommendations: list[RecommendationResponse]
    persisted: bool
