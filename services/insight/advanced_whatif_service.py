"""
Advanced What-if Service
---------------------------
Pure (no Streamlit) logic backing the Advanced What-if Simulator
(feature 12): Sensitivity Analysis (sweep one field across its real
FEATURE_SCHEMA range, see how the score actually responds) and
Goal-Seek (given a target score, search that same real range for the
value that lands closest). Both call the exact same, unmodified
PredictionService.predict() the existing manual single-scenario
simulator (legacy/streamlit_app/components/what_if_simulator.py) already uses -
repeated real inference on a real model, never a new model/pipeline
path or a fitted response-surface approximation.

Multi-Scenario Comparison (also part of feature 12) needs no separate
logic here: it's build_scenario_input() + predictor.predict() called
up to 3 times, which legacy/streamlit_app/pages/What_If_Simulator.py does directly.

Performance note: each sweep/goal-seek/comparison point is one real
predictor.predict() call with compute_shap=False (SHAP explanations are
never read from these throwaway comparison predictions - see
PredictionService.predict()'s compute_shap docstring), so resolution is
still deliberately capped (SWEEP_POINTS / GOAL_SEEK_POINTS) to bound the
number of real model forward passes, not because each point pays for a
SHAP explanation anymore.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from core.feature_schema import FEATURE_SCHEMA
from utils.feature_derivation import derive_features

logger = logging.getLogger(__name__)

SWEEP_POINTS = 9
GOAL_SEEK_POINTS = 15


@dataclass(slots=True)
class SweepPoint:
    value: float
    score: Optional[float]
    prediction: Optional[str]


@dataclass(slots=True)
class GoalSeekResult:
    field: str
    target_score: float
    best_value: float
    best_score: Optional[float]
    distance: Optional[float]
    points: list[SweepPoint]


_SCREEN_CATEGORY_FIELDS = (
    "social_min", "gaming_min", "work_study_min", "video_min", "other_min",
)


class AdvancedWhatIfService:
    """Sensitivity sweep + goal-seek over the real, unmodified predictor."""

    @staticmethod
    def build_scenario_input(base_user_data: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        """Same recompute-everything-derived contract as
        legacy/streamlit_app/components/what_if_simulator.py's private helper - kept as
        its own tiny copy here (three lines) rather than importing a
        Streamlit-importing UI component into a service module, which
        would invert this project's services-are-UI-independent
        architecture. The actual shared logic (derive_features) is
        still reused, not duplicated.

        Defensive clamp: `overrides` values are clamped to their
        FEATURE_SCHEMA bounds before being merged in. The only current
        UI caller (legacy/streamlit_app/pages/What_If_Simulator.py) already bounds every
        override via `st.slider(min_value=lo, max_value=hi)`, so this
        is currently unreachable through the app - but derive_features()
        itself does no bounds/NaN checking (it trusts its caller
        completely, unlike FuturePathService's `_clamp`, which already
        guards its own generated shifts), so any future non-UI caller
        (a REST API, a bulk scenario upload) could otherwise push
        negative or out-of-schema values straight into the model.
        """
        candidate = dict(base_user_data)
        for field_name, value in overrides.items():
            feature = FEATURE_SCHEMA.get(field_name)
            if feature is not None:
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    candidate[field_name] = value
                    continue
                if numeric_value != numeric_value:  # NaN check without importing math
                    continue  # drop silently rather than poison every derived ratio
                if feature.minimum is not None:
                    numeric_value = max(numeric_value, feature.minimum)
                if feature.maximum is not None:
                    numeric_value = min(numeric_value, feature.maximum)
                candidate[field_name] = numeric_value
            else:
                candidate[field_name] = value
        return derive_features(candidate)

    @staticmethod
    def _field_range(
        field: str, base_value: float, base_user_data: dict[str, Any] | None = None,
    ) -> tuple[float, float]:
        feature = FEATURE_SCHEMA.get(field)
        lo = feature.minimum if feature is not None and feature.minimum is not None else 0.0
        hi = feature.maximum if feature is not None and feature.maximum is not None else max(base_value * 2, 1.0)

        # A screen-time category cannot really run to its own 1440-minute
        # maximum, because ValidationService rejects any day whose five
        # categories sum past total_screen_min's maximum - a cross-field
        # rule the per-field schema bounds know nothing about. Sweeping to
        # the field maximum regardless spent most of the grid on days the
        # validator then refused: sweeping video_min on the at-risk
        # profile scored 4 of 15 points and returned a "best value" of 0,
        # because 0 was the only end of the range that still produced a
        # day. Cap at what is actually reachable with the other four
        # categories held where they are.
        if base_user_data is not None and field in _SCREEN_CATEGORY_FIELDS:
            others = sum(
                float(base_user_data.get(other, 0.0) or 0.0)
                for other in _SCREEN_CATEGORY_FIELDS
                if other != field
            )
            total_feature = FEATURE_SCHEMA.get("total_screen_min")
            total_max = total_feature.maximum if total_feature is not None else None
            if total_max is not None:
                hi = min(hi, max(float(lo), float(total_max) - others))

        return float(lo), float(hi)

    @classmethod
    def sweep_field(
        cls,
        base_user_data: dict[str, Any],
        predictor: Any,
        field: str,
        num_points: int = SWEEP_POINTS,
    ) -> list[SweepPoint]:
        """Real predicted score/class at `num_points` evenly-spaced
        values of `field` across its real schema range. Points where
        prediction fails are kept with score=None (never dropped
        silently, so the caller can show a gap rather than a wrong
        chart shape)."""
        base_value = float(base_user_data.get(field, 0.0) or 0.0)
        lo, hi = cls._field_range(field, base_value, base_user_data)
        if hi <= lo or num_points < 2:
            return []

        step = (hi - lo) / (num_points - 1)
        points: list[SweepPoint] = []
        for i in range(num_points):
            value = lo + step * i
            scenario_input = cls.build_scenario_input(base_user_data, {field: value})
            try:
                # Comparison-only prediction: only .regression_score /
                # .prediction are read below, so skip the SHAP pass -
                # see PredictionService.predict()'s compute_shap docstring.
                result = predictor.predict(scenario_input, compute_shap=False)
                points.append(SweepPoint(
                    value=round(value, 2),
                    score=result.regression_score,
                    prediction=result.prediction,
                ))
            except Exception:
                logger.debug("Sweep point at %s=%.2f failed to predict; recording as a gap.", field, value, exc_info=True)
                points.append(SweepPoint(value=round(value, 2), score=None, prediction=None))
        return points

    @classmethod
    def goal_seek(
        cls,
        base_user_data: dict[str, Any],
        predictor: Any,
        field: str,
        target_score: float,
        num_points: int = GOAL_SEEK_POINTS,
    ) -> Optional[GoalSeekResult]:
        """
        Grid search (not a binary search) over `field`'s real range for
        the value whose real predicted score is closest to
        `target_score`. Grid search is deliberate: the model is
        non-linear, so a monotonic relationship between the field and
        the score can't be assumed - a binary search would silently
        give a wrong answer wherever that assumption fails.

        Returns None if every point failed to predict.
        """
        points = cls.sweep_field(base_user_data, predictor, field, num_points=num_points)
        scored_points = [p for p in points if p.score is not None]
        if not scored_points:
            return None

        best = min(scored_points, key=lambda p: abs(p.score - target_score))
        return GoalSeekResult(
            field=field,
            target_score=target_score,
            best_value=best.value,
            best_score=best.score,
            distance=round(abs(best.score - target_score), 1),
            points=points,
        )
