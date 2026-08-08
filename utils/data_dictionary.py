"""
Raw Data Dictionary
----------------------
Plain-language documentation for every field a user is ever asked to
supply (P1 item 6), plus the availability matrix describing where each
model input comes from (P1 item 2).

This is generated FROM `core.feature_schema.FEATURE_SCHEMA` rather than
hand-maintained beside it, so a field can never exist in the schema
while silently missing from the docs (or vice versa). Only the
human-facing "how do I measure this?" guidance lives here as data -
the names, types and bounds are read from the single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.feature_schema import FEATURE_SCHEMA

# How each raw field is obtained in practice. Keys must be a subset of
# FEATURE_SCHEMA - verified by tests/test_data_dictionary.py.
_HOW_TO_MEASURE: dict[str, str] = {
    "age": "Your age in years.",
    "gender": "How you identify. Used only as a model input, never displayed publicly.",
    "occupation_group": "The closest match to your main daily activity.",
    "region_group": "The world region you mostly live in.",
    "education_group": "Your highest completed education level.",
    "device_category": "The device you use most for the screen time you're reporting.",
    "primary_platform": "The single app/platform you spend the most time on.",
    "purpose_group": "The main reason you use your devices on a typical day.",
    "is_content_creator": "Whether you regularly publish content (not just browse).",
    "uses_screen_time_limits": "Whether you have any app timer or screen-time limit switched on.",
    "day_index": "Which day of your tracking period this entry is. Auto-filled for CSV imports.",
    "day_of_week": "The weekday this entry describes. Auto-derived from the date on CSV import.",
    "is_weekend": "0 for a weekday, 1 for Saturday/Sunday. Auto-derived from the date.",
    "total_screen_min": "Auto-calculated: the sum of your five category minute fields. You never enter this directly.",
    "screen_ewma_baseline": "Your typical recent daily screen time. Auto-filled from your own entry when you have no history yet.",
    "screen_vs_baseline_pct": "Auto-calculated: how far today sits from a population reference of 240 min/day.",
    "social_min": "Minutes on social apps today. Most phones report this under Screen Time / Digital Wellbeing.",
    "gaming_min": "Minutes spent gaming today.",
    "work_study_min": "Minutes of screen time that were work or study.",
    "other_min": "Any remaining screen minutes that don't fit the other four categories.",
    "video_min": "Minutes watching video or streaming.",
    "social_ratio": "Auto-calculated share of total screen time that was social.",
    "gaming_ratio": "Auto-calculated share of total screen time that was gaming.",
    "work_study_ratio": "Auto-calculated share of total screen time that was work/study.",
    "other_ratio": "Auto-calculated share of total screen time in the 'other' bucket.",
    "night_screen_min": "Minutes of screen use during night hours (roughly 11pm-5am).",
    "night_ratio": "Auto-calculated share of your screen time that happened at night.",
    "pre_sleep_screen_min": "Minutes of screen use in the hour or so directly before you fell asleep.",
    "pre_sleep_ratio": "Auto-calculated share of screen time that happened right before sleep.",
    "notifications_per_day": "Roughly how many notifications you received today.",
    "pickups_per_day": "How many times you picked up your phone. Most phones report this directly.",
    "app_opens_per_day": "How many times you opened an app.",
    "notification_density": "Auto-calculated: notifications per hour of screen time.",
    "pickup_density": "Auto-calculated: pickups per hour of screen time.",
    "app_open_density": "Auto-calculated: app opens per hour of screen time.",
    "fragmentation_index_0_100": "Auto-calculated from pickups and session count: how broken-up your usage was.",
    "sleep_hours": "Hours you actually slept last night (not time in bed).",
    "sleep_quality_1_10": "How rested you feel, 1 (terrible) to 10 (excellent).",
    "stress_0_10": "Your stress level today, 0 (none) to 10 (extreme).",
    "mental_fatigue_0_10": "How mentally drained you feel, 0 to 10.",
    "anxiety_0_27": "A 0-27 anxiety self-rating. If unsure, estimate: 0-5 none, 6-10 mild, 11-15 moderate, 16+ high.",
    "low_mood_0_27": "A 0-27 low-mood self-rating, using the same bands as anxiety.",
    "happiness_0_10": "How happy you feel overall today, 0 to 10.",
    "loneliness_1_10": "How lonely you feel today, 1 (not at all) to 10 (very).",
    "self_esteem_1_10": "How you feel about yourself today, 1 to 10.",
    "fomo_1_10": "How much you feel you're missing out on things, 1 to 10.",
    "social_comparison_1_10": "How much you compared yourself to others online today, 1 to 10.",
    "life_satisfaction_1_10": "How satisfied you feel with life right now, 1 to 10.",
    "focus_0_100": "How well you could hold attention today, 0 to 100.",
    "productivity_0_100": "How much you actually got done today, 0 to 100.",
    "digital_dependence_0_100": "Auto-calculated from your recreational, night and morning-check patterns.",
    "physical_activity_min_per_day": "Minutes of deliberate physical activity today.",
    "caffeine_cups_per_day": "Cups of coffee/tea/energy drink today.",
}

# Fields the app computes for the user; everything else is user-entered.
DERIVED_FIELDS = frozenset({
    "total_screen_min", "screen_ewma_baseline", "screen_vs_baseline_pct",
    "social_ratio", "gaming_ratio", "work_study_ratio", "other_ratio",
    "night_ratio", "pre_sleep_ratio", "notification_density",
    "pickup_density", "app_open_density", "fragmentation_index_0_100",
    "digital_dependence_0_100",
})

# Fields the app fills in from the entry's own calendar date.
CALENDAR_FIELDS = frozenset({"day_index", "day_of_week", "is_weekend"})


@dataclass(slots=True)
class DataDictionaryEntry:
    name: str
    label: str
    dtype: str
    source: str            # "user_entered" | "derived" | "calendar"
    required: bool
    minimum: Optional[float]
    maximum: Optional[float]
    choices: Optional[list[Any]]
    how_to_measure: str
    description: str


def _source_for(name: str) -> str:
    if name in DERIVED_FIELDS:
        return "derived"
    if name in CALENDAR_FIELDS:
        return "calendar"
    return "user_entered"


def build_data_dictionary() -> list[DataDictionaryEntry]:
    """Every model input, documented. Order follows FEATURE_SCHEMA."""
    return [
        DataDictionaryEntry(
            name=name,
            label=feature.label or name,
            dtype=feature.dtype.__name__,
            source=_source_for(name),
            required=feature.required,
            minimum=feature.minimum,
            maximum=feature.maximum,
            choices=feature.choices,
            how_to_measure=_HOW_TO_MEASURE.get(name, ""),
            description=feature.description or "",
        )
        for name, feature in FEATURE_SCHEMA.items()
    ]


def availability_matrix() -> dict[str, list[str]]:
    """
    P1 item 2: which inputs the user supplies vs. which the app derives.
    Useful both as documentation and as a check that the check-in form
    never asks for something it should be computing.
    """
    matrix: dict[str, list[str]] = {"user_entered": [], "derived": [], "calendar": []}
    for name in FEATURE_SCHEMA:
        matrix[_source_for(name)].append(name)
    return matrix
