"""
api/schemas/analytics.py
---------------------------
A single consolidated GET /api/v1/analytics/summary response, built
from AnalyticsService's existing static helpers. AnalyticsService has
~15 chart-specific helpers backing individual Streamlit chart widgets;
this endpoint wires up the handful that are meaningful as a general-
purpose API response (score trend, weekday pattern, field averages)
rather than exposing all 15 as separate routes, which would mostly
just be re-plumbing Streamlit-chart-shaped data with no non-UI
consumer in mind. See the engineering report for what's intentionally
not yet exposed.
"""

from __future__ import annotations

from pydantic import BaseModel


class ScoreHistoryPoint(BaseModel):
    date: str
    health_score: float


class AnalyticsSummaryResponse(BaseModel):
    entry_count: int
    has_enough_points_for_trend: bool
    score_history: list[ScoreHistoryPoint]
    weekday_pattern: dict[str, float] | None
    field_averages: dict[str, float]
