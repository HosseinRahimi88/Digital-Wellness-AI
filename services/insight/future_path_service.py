"""
Future Path Comparison Service
--------------------------------
Group C Feature 39 - Future Path Comparison.

Compares several named, structured behavioral "paths" (Status Quo,
Gradual Improvement, Committed Change, Digital Detox, Continued Drift)
against the user's real, current input - each path is a full
`user_data` snapshot with a templated set of raw-field shifts applied,
then scored with the exact same, unmodified `PredictionService.predict()`
the rest of the app uses (real inference, real SHAP, real split-conformal
uncertainty - never a fitted forecast/response-surface model).

Relationship to existing "what-if" features
----------------------------------------------
This project already has:
  - Advanced What-if Simulator (feature 12): user-driven, one field at a
    time, sensitivity sweep + goal-seek + up to 3 ad hoc scenarios built
    directly in the page.
  - Parallel Twin (feature 45): a single hypothetical twin, auto-derived
    from *this user's own* top SHAP "areas to improve".
Future Path Comparison is neither of those: it's a **fixed, named set of
plausible futures** (not a slider sweep, not a single twin), each
representing a different level of behavior change commitment, so the
user can see "what happens if I do nothing" next to "what happens if I
make a real effort" as a single ranked comparison - closer to a
financial-planning "if you save $X/month" style comparison than a
one-off simulation.

Only raw, directly-editable habit fields are shifted (same
TWIN_ADJUSTABLE_FIELDS list `parallel_twin_service.py` already defines
and validated - reused here rather than redefined, so both features
agree on which fields have an unambiguous "healthier direction").
Every shift is clamped to the field's real FEATURE_SCHEMA bounds.
Derived/composite fields (fragmentation_index_0_100, etc.) are never
edited directly - `derive_features()` recomputes them from the shifted
raw fields, exactly like the manual simulator and the twin service do.

Real bug found and fixed during implementation
--------------------------------------------------
An early version of this service reused `base_user_data`'s
`screen_ewma_baseline` unchanged for every path (matching
`derive_features()`'s existing "don't silently redefine the personal
baseline" behavior, designed for the single-day What-if Simulator).
That produced a "Continued Drift" scenario that scored *higher* than
"Status Quo" - backwards. Root cause: `screen_ewma_baseline` and
`total_screen_min` are highly correlated in the real training data
(r=0.97, see models/preprocessing.py's feature-selection notes), but
several demo/base profiles never set `screen_ewma_baseline` explicitly,
so it silently defaults to the FEATURE_SCHEMA midpoint (720.0) rather
than a value consistent with that profile's actual screen time. Once a
path shifted the raw screen-time fields, the frozen, already-arbitrary
baseline diverged further from the new total, pushing the input into a
region far outside anything the model saw during training - the
model's non-monotonic response there was genuine extrapolation, not a
meaningful signal about the scenario. Fix: since every Future Path
represents a *sustained* future state (unlike a single-day what-if
tweak), `screen_ewma_baseline` is recomputed fresh for every non-
identity path to match that path's own `total_screen_min`, keeping the
model input self-consistent and in-distribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.feature_schema import FEATURE_SCHEMA
from utils.feature_derivation import derive_features
from config.healthy_targets import HEALTHY_TARGETS
from services.insight.parallel_twin_service import TWIN_ADJUSTABLE_FIELDS, MIN_ABSOLUTE_SHIFT


@dataclass(slots=True)
class PathDefinition:
    key: str
    name: str
    description: str
    shift_fraction: float  # negative = drift toward *less* healthy habits


# Named paths, ordered from least to most committed to change. Fractions
# are intentionally modest for "Gradual" and larger for "Committed"/
# "Detox" - mirroring realistic behavior-change effort levels rather than
# picking round numbers with no rationale. "Continued Drift" uses a
# negative fraction (habits move *away* from the healthy direction) so
# the comparison also shows the honest cost of inaction, not just upside
# scenarios.
# The fractions were 0.10 / 0.25 / 0.45 and produced paths a user could
# not tell apart. Measured on the baseline demo profile before this
# change: gradual +1.25 and committed +1.78 - half a point between
# "small sustainable changes" and "a real, consistent effort", which a
# user reported as the two paths being the same. Because the fractions
# interpolate toward a healthy target rather than scaling a habit, a
# fraction IS the share of the remaining gap that gets closed, so 0.10
# meant "close a tenth of the distance and call it an effort".
#
# They now read as what they claim: gradual closes about a third of the
# gap, committed about two thirds, detox nearly all of it. Drift is
# deepened to match, or inaction looks costless next to it.
#
# The ordering still has to come out of the real model scores - none of
# this post-processes the output, and the tests check the ordering
# rather than the fractions.
PATH_DEFINITIONS: list[PathDefinition] = [
    PathDefinition("status_quo", "Status Quo", "Your current habits, unchanged.", 0.0),
    PathDefinition("continued_drift", "Continued Drift", "Habits drift slightly further from the healthy direction.", -0.18),
    PathDefinition("gradual_improvement", "Gradual Improvement", "Small, sustainable changes to a few habits.", 0.30),
    PathDefinition("committed_change", "Committed Change", "A real, consistent effort across multiple habits.", 0.65),
    PathDefinition("digital_detox", "Digital Detox", "An aggressive reset of screen-related habits.", 0.92),
]




@dataclass(slots=True)
class PathResult:
    key: str
    name: str
    description: str
    user_data: dict[str, Any]
    adjustments: list[dict[str, Any]]
    prediction: Optional[str] = None
    regression_score: Optional[float] = None
    confidence: Optional[float] = None
    uncertainty: Any = None
    score_delta_vs_status_quo: Optional[float] = None
    error: Optional[str] = None
    # True when this path changed nothing, because the user is already
    # at or past the healthy target on every field it can adjust. That
    # is a real, good answer - and it has to be said in words, because
    # four identical cards read as a broken feature rather than as "you
    # are already there".
    already_at_target: bool = False


@dataclass(slots=True)
class FuturePathComparison:
    paths: list[PathResult] = field(default_factory=list)
    best_path_key: Optional[str] = None
    worst_path_key: Optional[str] = None

    # A delta below this magnitude is treated as within the model's own
    # noise floor rather than a meaningful directional signal - trained
    # tree ensembles (HistGradientBoosting here) are not guaranteed
    # monotonic, so near a score ceiling/floor, small simulated habit
    # shifts can occasionally move the score by a fraction of a point in
    # either direction. Surfacing that honestly (rather than always
    # claiming a confident direction) is preferable to implying
    # precision the model doesn't have.
    NOISE_FLOOR = 1.5

    def is_delta_meaningful(self, path_result: "PathResult") -> bool:
        if path_result.score_delta_vs_status_quo is None:
            return False
        return abs(path_result.score_delta_vs_status_quo) >= self.NOISE_FLOOR


class FuturePathService:
    """Builds and evaluates the named future-path scenarios."""

    @staticmethod
    def _clamp(field_name: str, value: float) -> float:
        feature = FEATURE_SCHEMA.get(field_name)
        if feature is None:
            return value
        if feature.minimum is not None:
            value = max(value, feature.minimum)
        if feature.maximum is not None:
            value = min(value, feature.maximum)
        return value

    @classmethod
    def _build_path_input(
        cls, base_user_data: dict[str, Any], shift_fraction: float,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Move each adjustable field a `shift_fraction` of the way from the
        user's current value toward that field's healthy target - never
        past it. A negative fraction models drift and moves away from the
        target instead. shift_fraction == 0 is the identity path.

        Why "toward a target" and not "by a percentage" (the real bug
        this replaced)
        ---------------------------------------------------------------
        The original version shifted every field by a fixed fraction of
        its own current value, in its healthy direction, with no ceiling
        other than the schema bounds. For a user already doing well that
        produces nonsense: 8 hours of sleep became 11.6 under "Digital
        Detox", physical activity went from 60 minutes to 87, and sleep
        quality was pushed past its own maximum. Those are not "more
        effort" - they are a different, less plausible day, and the model
        scored them lower because eleven hours of sleep genuinely is not
        healthier than eight.

        The visible symptom was the comparison telling users that trying
        harder made things worse. Measured on the four demo profiles
        before this change: for the healthy profile EVERY improvement
        path scored below Status Quo (gradual -0.64, committed -0.96,
        detox -1.60), for the baseline profile committed effort (+0.23)
        scored below gradual (+0.41), and for the at-risk profile
        Continued Drift came out *positive*.

        That was never a model defect to be papered over - it was an
        input-construction defect. The model was extrapolating outside
        the region it was trained on, where a gradient-boosted tree's
        response is arbitrary. The fix is to build inputs that stay
        inside plausible human ranges: interpolate toward a healthy
        target, stop there, and leave a field alone entirely when the
        user is already better than the target. Nothing here touches the
        model or post-processes its output - the ordering has to come
        out of the real scores or not at all.
        """
        overrides: dict[str, Any] = {}
        adjustments: list[dict[str, Any]] = []

        if shift_fraction == 0.0:
            return dict(base_user_data), adjustments

        for field_name, healthy_direction in TWIN_ADJUSTABLE_FIELDS.items():
            try:
                current = float(base_user_data.get(field_name, 0.0))
            except (TypeError, ValueError):
                continue

            target = HEALTHY_TARGETS.get(field_name)

            if shift_fraction > 0:
                if target is None:
                    continue
                # Already at or beyond the target: an "improvement" path
                # must not push a good habit further into the extreme.
                already_there = (
                    current <= target if healthy_direction == "decrease" else current >= target
                )
                if already_there:
                    continue
                new_value = current + shift_fraction * (target - current)
                # Interpolation cannot overshoot for 0 < f <= 1, but the
                # clamp below is what guarantees it for any future
                # fraction someone adds to PATH_DEFINITIONS.
                new_value = (
                    max(new_value, target) if healthy_direction == "decrease"
                    else min(new_value, target)
                )
            else:
                # Drift: there is no "unhealthy target" to aim at, so
                # this stays a proportional move away from the healthy
                # direction, bounded only by the schema.
                effective_direction = "decrease" if healthy_direction == "increase" else "increase"
                magnitude = max(abs(current) * abs(shift_fraction), MIN_ABSOLUTE_SHIFT)
                new_value = (
                    current - magnitude if effective_direction == "decrease" else current + magnitude
                )

            new_value = cls._clamp(field_name, new_value)

            if abs(new_value - current) < 1e-9:
                continue

            overrides[field_name] = new_value
            adjustments.append({
                "field": field_name,
                "label": field_name.replace("_", " ").title(),
                "old_value": round(current, 1),
                "new_value": round(new_value, 1),
            })

        path_data = dict(base_user_data)
        path_data.update(overrides)

        # Any non-identity path represents a *sustained* future state,
        # not a single day's fluctuation - so the personal EWMA baseline
        # should reflect that new steady state too, not the value
        # carried over from `base_user_data` (which may itself be an
        # unset-field schema-midpoint default, not a real measured
        # baseline - see services/insight/future_path_service.py module
        # docstring for the out-of-distribution failure mode this
        # avoids). Dropping the key here makes derive_features()
        # recompute it fresh as this path's own total_screen_min,
        # exactly like a brand-new user's first submission.
        path_data.pop("screen_ewma_baseline", None)

        path_data = derive_features(path_data)

        # Clamp AFTER derivation, not just before it.
        #
        # _clamp above bounds the fields this method edits. It cannot
        # bound the ones derive_features computes FROM them, and those
        # are the ones that go out of range: push night usage up while
        # total screen time comes down and night_ratio exceeds 1.0, at
        # which point the prediction is refused and the whole path
        # returns an error instead of a score. Deepening the drift
        # fraction is what surfaced it - the previous fraction was too
        # small to push a ratio past its bound, so the bug was latent
        # rather than absent.
        for derived_name in list(path_data.keys()):
            value = path_data.get(derived_name)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                path_data[derived_name] = cls._clamp(derived_name, float(value))
        return path_data, adjustments

    @classmethod
    def compare(
        cls,
        base_user_data: dict[str, Any],
        predictor: Any,
        path_keys: Optional[list[str]] = None,
    ) -> FuturePathComparison:
        """
        Evaluate every path in `path_keys` (default: all of
        PATH_DEFINITIONS) against the real prediction pipeline.
        `predictor` is a `PredictionService` instance (dependency-
        injected, not imported at module scope, matching the rest of
        this codebase's testability convention). A single path's
        prediction failing (e.g. a pathological input from an extreme
        shift) is captured on that `PathResult.error` rather than
        aborting the whole comparison - one bad scenario must not hide
        the others (robustness requirement).
        """
        definitions = [d for d in PATH_DEFINITIONS if path_keys is None or d.key in path_keys]

        # Status Quo is the BASELINE, not just another path, and every
        # delta below is measured against it. A caller asking for two
        # improvement paths and nothing else - which is exactly what the
        # result page does - used to get `score_delta_vs_status_quo =
        # None` on both, so `is_delta_meaningful()` said False and both
        # cards printed "not a meaningful change from today". Measured on
        # an at-risk profile: gradual scored 41 and committed 48 against
        # a status quo of 39, i.e. +1.8 and +8.8, and BOTH were reported
        # as no meaningful change.
        #
        # So it is scored whenever it is missing, and returned only if it
        # was actually asked for - the caller's `paths` list is unchanged.
        baseline_requested = any(d.key == "status_quo" for d in definitions)
        if not baseline_requested:
            definitions = [d for d in PATH_DEFINITIONS if d.key == "status_quo"] + definitions

        results: list[PathResult] = []
        for definition in definitions:
            path_data, adjustments = cls._build_path_input(base_user_data, definition.shift_fraction)

            result = PathResult(
                key=definition.key,
                name=definition.name,
                description=definition.description,
                user_data=path_data,
                adjustments=adjustments,
                already_at_target=(
                    definition.shift_fraction > 0 and not adjustments
                ),
            )

            try:
                # Only .prediction/.regression_score/.confidence/
                # .uncertainty are read below - .uncertainty comes from
                # UncertaintyService (independent of compute_shap), so
                # skipping SHAP here is safe.
                prediction_result = predictor.predict(path_data, compute_shap=False)
                result.prediction = prediction_result.prediction
                result.regression_score = prediction_result.regression_score
                result.confidence = prediction_result.confidence
                result.uncertainty = prediction_result.uncertainty
            except Exception as exc:  # noqa: BLE001
                result.error = str(exc)

            results.append(result)

        status_quo = next((r for r in results if r.key == "status_quo"), None)
        if status_quo is not None and status_quo.regression_score is not None:
            for r in results:
                if r.regression_score is not None:
                    r.score_delta_vs_status_quo = round(r.regression_score - status_quo.regression_score, 2)

        if not baseline_requested:
            # Scored purely to have something to measure against; the
            # caller did not ask for it and must not receive it.
            results = [r for r in results if r.key != "status_quo"]

        scored = [r for r in results if r.regression_score is not None]
        best_key = max(scored, key=lambda r: r.regression_score).key if scored else None
        worst_key = min(scored, key=lambda r: r.regression_score).key if scored else None

        return FuturePathComparison(paths=results, best_path_key=best_key, worst_path_key=worst_key)
