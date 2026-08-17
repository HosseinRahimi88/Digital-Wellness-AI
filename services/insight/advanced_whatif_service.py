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
    # Whether `best_value` actually gets to the target, or is only the
    # furthest this one field can carry the reader. The old response had
    # no way to say "it cannot be done from here" and so said nothing,
    # which read as success.
    reached: bool = False
    # Where the reader is standing right now, so the answer can be a
    # change rather than a bare number.
    current_value: Optional[float] = None
    current_score: Optional[float] = None
    # The target is already met without touching this field.
    already_there: bool = False


_SCREEN_CATEGORY_FIELDS = (
    "social_min", "gaming_min", "work_study_min", "video_min", "other_min",
)

# Minutes of screen time that are a SUBSET of the day's total rather
# than a part of the sum. night_ratio and pre_sleep_ratio divide these
# by total_screen_min, so a value above the total produces a ratio above
# 1.0 - which ValidationService rejects, one swept point at a time.
#
# Sweeping night_screen_min on an ordinary day did exactly that: the
# first three points scored, the last six came back as gaps, and the
# chart drew each gap as a score of zero. A wellness chart that appears
# to fall off a cliff at 225 night-minutes, on a day whose whole screen
# total is 210, is not a finding about the user - it is the sweep
# leaving the range where a day can exist at all.
_SCREEN_SUBSET_FIELDS = ("night_screen_min", "pre_sleep_screen_min")

# Counts whose per-screen-hour DENSITY is a separate schema field with
# its own, much tighter ceiling. app_opens_per_day tops out at 1000 and
# app_open_density at 100, so on a 3.5-hour day anything past 350 opens
# is a day the validator will not accept - and sweeping to 1000 spent
# six of nine points outside it. Same silent-gap failure as the night
# minutes above, from the same blind spot: a per-field bound cannot see
# a rule that spans two fields.
_DENSITY_DRIVEN_FIELDS = {
    "notifications_per_day": "notification_density",
    "pickups_per_day": "pickup_density",
    "app_opens_per_day": "app_open_density",
}


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

        # The other cross-field rule the per-field bounds cannot see: a
        # night or pre-sleep minute is one of the day's OWN minutes, so
        # it cannot exceed the day's total. Sweeping past that point
        # produced a ratio above 1.0 and a run of unscoreable days - see
        # _SCREEN_SUBSET_FIELDS.
        if base_user_data is not None and field in _SCREEN_SUBSET_FIELDS:
            total = sum(
                float(base_user_data.get(category, 0.0) or 0.0)
                for category in _SCREEN_CATEGORY_FIELDS
            )
            if total > 0:
                hi = min(hi, max(float(lo), total))

        # And the third: a daily count divided by the day's screen hours
        # has to land inside its own density field's ceiling. See
        # _DENSITY_DRIVEN_FIELDS.
        if base_user_data is not None and field in _DENSITY_DRIVEN_FIELDS:
            total = sum(
                float(base_user_data.get(category, 0.0) or 0.0)
                for category in _SCREEN_CATEGORY_FIELDS
            )
            screen_hours = max(total, 1.0) / 60.0
            density = FEATURE_SCHEMA.get(_DENSITY_DRIVEN_FIELDS[field])
            density_max = density.maximum if density is not None else None
            if density_max is not None and screen_hours > 0:
                hi = min(hi, max(float(lo), float(density_max) * screen_hours))

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
        the value that REACHES `target_score`. Grid search is
        deliberate: the model is non-linear, so a monotonic relationship
        between the field and the score can't be assumed - a binary
        search would silently give a wrong answer wherever that
        assumption fails.

        WHAT THIS USED TO ANSWER, AND WHY IT WAS THE WRONG QUESTION

        It minimised `abs(score - target)` over the whole grid. That is
        the value whose score is NEAREST the target - in either
        direction. For anybody already above their target (which is
        most people who set a reachable one), the nearest point is
        therefore the one that damages their score the most, and the
        page printed it under the heading "Best value found":

            sleep_hours                    ->  0 hours    (score 85.95)
            sleep_quality_1_10             ->  1 out of 10
            stress_0_10                    -> 10 out of 10
            physical_activity_min_per_day  ->  0 minutes

        Every one of those is a real run against the real model on an
        ordinary day, target 80, from a score of 87.67. A wellness app
        telling somebody the best amount of sleep is none is not a
        rounding error; it is the tool arguing for harm, confidently,
        with a number beside it.

        WHAT IT ANSWERS NOW

        "Reaching a target" means scoring AT LEAST it. Three honest
        outcomes, and the caller is told which one it got:

          * already_there - the current value clears the target on its
            own. Nothing to change, and the answer says so instead of
            hunting for a way down to it.
          * reached - at least one value scores >= target. Among those,
            the one requiring the SMALLEST CHANGE from where the reader
            actually is, because "sleep 7.5h" beats "sleep 15h" when
            both qualify and one of them is a real thing a person does.
          * not reached - no value of this field alone gets there. Then
            best_value is the highest-scoring point, `reached` is False
            and `distance` is the shortfall, so the page can say plainly
            that this field cannot do it rather than implying it did.

        Returns None if every point failed to predict.
        """
        points = cls.sweep_field(base_user_data, predictor, field, num_points=num_points)
        scored_points = [p for p in points if p.score is not None]
        if not scored_points:
            return None

        current_value = float(base_user_data.get(field, 0.0) or 0.0)
        current_score: Optional[float] = None
        try:
            current_score = predictor.predict(
                cls.build_scenario_input(base_user_data, {}), compute_shap=False,
            ).regression_score
        except Exception:  # noqa: BLE001 - the sweep still stands without it
            logger.debug("Could not score the unchanged day for goal-seek.", exc_info=True)

        reaching = [p for p in scored_points if p.score >= target_score]

        if reaching:
            # Least change wins. Ties (the grid is symmetric around the
            # current value often enough) break towards the higher
            # score, so the answer is never the weaker of two equals.
            best = min(reaching, key=lambda p: (abs(p.value - current_value), -p.score))
            reached = True
        else:
            best = max(scored_points, key=lambda p: p.score)
            reached = False

        already_there = current_score is not None and current_score >= target_score

        return GoalSeekResult(
            field=field,
            target_score=target_score,
            best_value=best.value,
            best_score=best.score,
            # Still the gap between what this lands on and what was
            # asked for - 0.0 whenever the target was actually reached.
            distance=round(max(0.0, target_score - best.score), 1),
            points=points,
            reached=reached,
            current_value=round(current_value, 2),
            current_score=current_score,
            already_there=already_there,
        )
