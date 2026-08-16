"""api/schemas/coach.py"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SignalTrendResponse(BaseModel):
    field_name: str
    label: str
    higher_is_better: bool
    recent_mean: float | None
    earlier_mean: float | None
    change: float | None
    direction: str = Field(description="improving | worsening | flat | unknown")


class CoachContextResponse(BaseModel):
    """
    A complete, compact read of the user's own real data. Any field the
    history cannot support is null or empty rather than imputed, and
    `data_sufficiency` / `notes` state the limits in plain language so the
    Coach can quote them instead of over-claiming.
    """

    display_name: str = ""
    language: str = "en"
    persona: str | None = None
    primary_goal: str | None = None
    preferred_effort: str | None = None
    recommendation_tone: str | None = None

    latest_score: float | None = None
    latest_class: str | None = None
    latest_confidence: float | None = None
    latest_date: str | None = None
    top_factors: list[dict[str, Any]] = []

    entry_count: int = 0
    excluded_day_count: int = 0
    streak_days: int = 0
    longest_streak: int = 0
    score_7d_ago: float | None = None
    score_change_7d: float | None = None
    best_score: float | None = None
    worst_score: float | None = None

    trends: list[SignalTrendResponse] = []
    strongest_signals: list[str] = []
    weakest_signals: list[str] = []

    plan_focus_areas: list[str] = []
    muted_topics: list[str] = []

    data_sufficiency: str = "none"
    notes: list[str] = []
