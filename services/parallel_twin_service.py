"""
Parallel Twin Service
------------------------
"Parallel Twin" (feature 45): a hypothetical "twin" of the user who
adopted better habits in the specific areas the model's own real SHAP
explanation flagged as pulling their score down - evaluated with the
exact same, unmodified PredictionService.predict() the real What-if
Simulator uses, on a snapshot input (never a multi-day forecast: this
model classifies/scores a single submitted snapshot, it does not
predict forward in time - see app/pages/Dashboard.py's own docstring
for the same "not a forecaster" boundary observed elsewhere in this
project).

Distinct from the manual, user-driven What-if Simulator (feature 12):
here the *service* decides what to change, deriving it from the top
real "areas to improve" SHAP features
(services/dashboard_service.py::DashboardService.split_shap_by_direction,
reused rather than re-derived) - i.e. "what if you'd followed the
model's own signal", not "what if I personally move this slider".

Every shift is clamped to the field's real core.feature_schema.FEATURE_SCHEMA
bounds - the same authoritative bounds validation/the live form use -
so the twin is never given a physically nonsensical input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.feature_schema import FEATURE_SCHEMA
from utils.feature_derivation import derive_features

# Only these raw, directly-editable habit fields are auto-adjusted for
# the twin - the same kind of raw slider fields
# app/components/what_if_simulator.py exposes to a human, restricted
# here to ones with an unambiguous "healthier direction". Fields like
# fragmentation_index_0_100 or digital_dependence_0_100 are *derived*
# (utils.feature_derivation computes them from raw inputs), so they
# are deliberately excluded - the twin only ever edits raw inputs and
# lets derive_features() recompute everything derived from them,
# exactly like the manual simulator does.
TWIN_ADJUSTABLE_FIELDS = {
    "social_min": "decrease",
    "gaming_min": "decrease",
    "video_min": "decrease",
    "work_study_min": "decrease",
    "stress_0_10": "decrease",
    "notifications_per_day": "decrease",
    "pickups_per_day": "decrease",
    "sleep_hours": "increase",
    "sleep_quality_1_10": "increase",
    "physical_activity_min_per_day": "increase",
}

# How far (as a fraction of the current value) each selected field is
# shifted toward its healthier direction.
TWIN_SHIFT_FRACTION = 0.15

# A field starting at (or very near) zero can't be shifted
# proportionally - this is the minimum absolute nudge applied instead
# in that case, still clamped to the field's real schema bounds.
MIN_ABSOLUTE_SHIFT = 0.5

# At most this many SHAP "areas to improve" are used to build the twin
# - keeps the comparison focused on what the model flagged as most
# impactful, not a maximal simultaneous rewrite of the user's habits.
MAX_TWIN_ADJUSTMENTS = 3


@dataclass(slots=True)
class TwinAdjustment:
    field: str
    label: str
    old_value: float
    new_value: float
    direction: str


@dataclass(slots=True)
class TwinComparison:
    twin_user_data: dict[str, Any]
    adjustments: list[TwinAdjustment]
    real_result: Any
    twin_result: Any
    score_delta: Optional[float]
    class_changed: bool


class ParallelTwinService:
    """Builds and evaluates a hypothetical 'twin' with improved habits."""

    @staticmethod
    def _clamp(field: str, value: float) -> float:
        feature = FEATURE_SCHEMA.get(field)
        if feature is None:
            return value
        if feature.minimum is not None:
            value = max(value, feature.minimum)
        if feature.maximum is not None:
            value = min(value, feature.maximum)
        return value

    @classmethod
    def build_twin_profile(
        cls, base_user_data: dict[str, Any], areas_to_improve: list[Any]
    ) -> tuple[dict[str, Any], list[TwinAdjustment]]:
        """
        `areas_to_improve` is DashboardService.split_shap_by_direction(...)
        .areas_to_improve (real SHAPFeature objects, ranked). Returns
        (fully-derived twin user_data ready for PredictionService.predict,
        the list of adjustments actually made).
        """
        adjustments: list[TwinAdjustment] = []
        overrides: dict[str, Any] = {}

        for shap_feature in areas_to_improve:
            if len(adjustments) >= MAX_TWIN_ADJUSTMENTS:
                break
            field = getattr(shap_feature, "feature", None)
            if field not in TWIN_ADJUSTABLE_FIELDS or field in overrides:
                continue

            direction = TWIN_ADJUSTABLE_FIELDS[field]
            try:
                current = float(base_user_data.get(field, 0.0))
            except (TypeError, ValueError):
                continue

            shift = max(abs(current) * TWIN_SHIFT_FRACTION, MIN_ABSOLUTE_SHIFT)
            new_value = current - shift if direction == "decrease" else current + shift
            new_value = cls._clamp(field, new_value)

            overrides[field] = new_value
            adjustments.append(TwinAdjustment(
                field=field, label=field.replace("_", " ").title(),
                old_value=round(current, 1), new_value=round(new_value, 1),
                direction=direction,
            ))

        candidate = dict(base_user_data)
        candidate.update(overrides)
        twin_user_data = derive_features(candidate)
        return twin_user_data, adjustments

    @classmethod
    def compare(
        cls,
        base_user_data: dict[str, Any],
        areas_to_improve: list[Any],
        real_result: Any,
        predictor: Any,
    ) -> Optional[TwinComparison]:
        """
        Builds the twin and runs one real prediction for it via the
        unmodified `predictor.predict()`. Returns None (not an error)
        if there were no adjustable areas to improve - a twin
        identical to the real user isn't a meaningful comparison.
        """
        twin_user_data, adjustments = cls.build_twin_profile(base_user_data, areas_to_improve)
        if not adjustments:
            return None

        # Only .regression_score/.prediction are read below - never
        # .shap_features - so skip the SHAP pass for this comparison-only
        # prediction.
        twin_result = predictor.predict(twin_user_data, compute_shap=False)

        score_delta = None
        real_score = getattr(real_result, "regression_score", None)
        twin_score = getattr(twin_result, "regression_score", None)
        if real_score is not None and twin_score is not None:
            score_delta = round(twin_score - real_score, 1)

        class_changed = getattr(real_result, "prediction", None) != getattr(twin_result, "prediction", None)

        return TwinComparison(
            twin_user_data=twin_user_data,
            adjustments=adjustments,
            real_result=real_result,
            twin_result=twin_result,
            score_delta=score_delta,
            class_changed=class_changed,
        )
