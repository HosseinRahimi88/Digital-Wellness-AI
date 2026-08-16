"""
Wellness Dimension Breakdown
-----------------------------
A transparent, deterministic, non-ML rollup of the same raw/derived
inputs already sent to the model, grouped into five dimensions a user
can actually act on: Sleep, Focus & Productivity, Emotional Wellbeing,
Screen Habits, Physical & Lifestyle.

This is intentionally NOT part of the trained model and never feeds
back into it - it's a read-only, documented arithmetic view computed
from `validation.cleaned_data` (the same dict PredictionService.predict()
receives) for display purposes only, alongside (not instead of) the
model's own classification/regression output.

Formula, identical for every indicator unless noted:
    normalized = 100 * clamp((value - schema_min) / (schema_max - schema_min), 0, 1)
    inverted indicators use (100 - normalized) instead, because a
    smaller raw value is the healthier direction for that field (e.g.
    stress, anxiety, fragmentation).
A dimension's score is the plain mean of whichever of its indicators
are present in the input (missing indicators are skipped, never
imputed with a fabricated value). The overall breakdown score is the
plain mean of the five dimension scores.

One deliberate exception: `sleep_hours` is scored by distance from a
target of 8 hours rather than "more is better", since very little and
very much sleep are both the unhealthy direction - the only field in
this module where that non-monotonic case actually applies.
"""

from __future__ import annotations

from typing import Any

from core.feature_schema import FEATURE_SCHEMA

SLEEP_HOURS_TARGET = 8.0


def _linear(value: Any, field: str, invert: bool = False) -> float | None:
    feature = FEATURE_SCHEMA.get(field)
    if feature is None or feature.minimum is None or feature.maximum is None:
        return None
    lo, hi = float(feature.minimum), float(feature.maximum)
    if hi <= lo:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    pct = max(0.0, min(1.0, (v - lo) / (hi - lo)))
    return (1.0 - pct) * 100.0 if invert else pct * 100.0


def _sleep_hours_score(value: Any) -> float | None:
    feature = FEATURE_SCHEMA.get("sleep_hours")
    if feature is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    lo, hi = float(feature.minimum), float(feature.maximum)
    max_deviation = max(SLEEP_HOURS_TARGET - lo, hi - SLEEP_HOURS_TARGET)
    if max_deviation <= 0:
        return None
    deviation = abs(v - SLEEP_HOURS_TARGET)
    return max(0.0, 1.0 - deviation / max_deviation) * 100.0


# (field, invert, custom_scorer) - custom_scorer overrides the default
# linear normalization for that one indicator when not None.
DIMENSIONS: dict[str, dict[str, Any]] = {
    "sleep": {
        "label": "Sleep",
        "indicators": [
            ("sleep_hours", False, _sleep_hours_score),
            ("sleep_quality_1_10", False, None),
            ("pre_sleep_ratio", True, None),
        ],
    },
    "focus": {
        "label": "Focus & Productivity",
        "indicators": [
            ("focus_0_100", False, None),
            ("productivity_0_100", False, None),
            ("fragmentation_index_0_100", True, None),
            ("notification_density", True, None),
            ("pickup_density", True, None),
        ],
    },
    "emotional": {
        "label": "Emotional Wellbeing",
        "indicators": [
            ("happiness_0_10", False, None),
            ("life_satisfaction_1_10", False, None),
            ("self_esteem_1_10", False, None),
            ("stress_0_10", True, None),
            ("mental_fatigue_0_10", True, None),
            ("anxiety_0_27", True, None),
            ("low_mood_0_27", True, None),
            ("loneliness_1_10", True, None),
            ("fomo_1_10", True, None),
            ("social_comparison_1_10", True, None),
        ],
    },
    "screen_habits": {
        "label": "Screen Habits",
        "indicators": [
            ("total_screen_min", True, None),
            ("night_ratio", True, None),
            ("digital_dependence_0_100", True, None),
            ("gaming_ratio", True, None),
        ],
    },
    "physical": {
        "label": "Physical & Lifestyle",
        "indicators": [
            ("physical_activity_min_per_day", False, None),
            ("caffeine_cups_per_day", True, None),
        ],
    },
}


def compute_dimension_scores(user_data: dict[str, Any]) -> dict[str, Any]:
    """
    Returns:
        {
          "dimensions": [
            {"key": "sleep", "label": "Sleep", "score": 82.4, "indicator_count": 3},
            ...
          ],
          "overall": 74.1,
        }
    Dimensions with zero available indicators are omitted entirely
    (never shown with a fabricated 0 or 50).
    """
    dimensions: list[dict[str, Any]] = []

    for key, spec in DIMENSIONS.items():
        values: list[float] = []
        for field, invert, custom_scorer in spec["indicators"]:
            if field not in user_data or user_data[field] is None:
                continue
            score = custom_scorer(user_data[field]) if custom_scorer else _linear(user_data[field], field, invert)
            if score is not None:
                values.append(score)

        if not values:
            continue

        dimensions.append({
            "key": key,
            "label": spec["label"],
            "score": round(sum(values) / len(values), 1),
            "indicator_count": len(values),
        })

    overall = round(sum(d["score"] for d in dimensions) / len(dimensions), 1) if dimensions else None

    return {"dimensions": dimensions, "overall": overall}
