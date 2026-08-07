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
from services.parallel_twin_service import TWIN_ADJUSTABLE_FIELDS, MIN_ABSOLUTE_SHIFT


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
PATH_DEFINITIONS: list[PathDefinition] = [
    PathDefinition("status_quo", "Status Quo", "Your current habits, unchanged.", 0.0),
    PathDefinition("continued_drift", "Continued Drift", "Habits drift slightly further from the healthy direction.", -0.10),
    PathDefinition("gradual_improvement", "Gradual Improvement", "Small, sustainable changes to a few habits.", 0.10),
    PathDefinition("committed_change", "Committed Change", "A real, consistent effort across multiple habits.", 0.25),
    PathDefinition("digital_detox", "Digital Detox", "An aggressive reset of screen-related habits.", 0.45),
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
        Apply `shift_fraction` to every field in TWIN_ADJUSTABLE_FIELDS,
        in that field's healthy direction (or the opposite direction for
        a negative fraction, modeling drift). shift_fraction == 0 is the
        identity path (status quo) - returned unmodified.
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

            # Positive shift_fraction moves toward the healthy direction;
            # negative moves away from it (drift).
            effective_direction = healthy_direction if shift_fraction > 0 else (
                "decrease" if healthy_direction == "increase" else "increase"
            )
            magnitude = max(abs(current) * abs(shift_fraction), MIN_ABSOLUTE_SHIFT)
            new_value = current - magnitude if effective_direction == "decrease" else current + magnitude
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
        # baseline - see services/future_path_service.py module
        # docstring for the out-of-distribution failure mode this
        # avoids). Dropping the key here makes derive_features()
        # recompute it fresh as this path's own total_screen_min,
        # exactly like a brand-new user's first submission.
        path_data.pop("screen_ewma_baseline", None)

        path_data = derive_features(path_data)
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

        results: list[PathResult] = []
        for definition in definitions:
            path_data, adjustments = cls._build_path_input(base_user_data, definition.shift_fraction)

            result = PathResult(
                key=definition.key,
                name=definition.name,
                description=definition.description,
                user_data=path_data,
                adjustments=adjustments,
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

        scored = [r for r in results if r.regression_score is not None]
        best_key = max(scored, key=lambda r: r.regression_score).key if scored else None
        worst_key = min(scored, key=lambda r: r.regression_score).key if scored else None

        return FuturePathComparison(paths=results, best_path_key=best_key, worst_path_key=worst_key)
