"""api/schemas/history.py"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HistoryEntryResponse(BaseModel):
    """A stored prediction-history entry. The well-known fields below
    are always present; `extra="allow"` lets the rest of the tracked
    fields (services/history_service.py's TRACKED_FIELDS - sleep_hours,
    stress_0_10, ...) pass through without hand-duplicating that list a
    second time here."""

    model_config = ConfigDict(extra="allow")

    user_id: str
    date: str
    day_of_week: str | None = None
    health_score: float | None = None
    health_class: str | None = None
    confidence: float | None = None
    persona: str | None = None
    recorded_at: str | None = None
    top_shap_feature: str | None = None


class WeekSummaryResponse(BaseModel):
    week_key: str
    start_date: str
    end_date: str
    num_entries: int
    avg_health_score: float | None
    avg_total_screen_min: float | None
    avg_sleep_hours: float | None
    avg_focus_0_100: float | None
    avg_social_min: float | None
    avg_stress_0_10: float | None

    @staticmethod
    def from_week_summary(w) -> "WeekSummaryResponse":
        return WeekSummaryResponse(
            week_key=w.week_key, start_date=w.start_date, end_date=w.end_date,
            num_entries=w.num_entries, avg_health_score=w.avg_health_score,
            avg_total_screen_min=w.avg_total_screen_min, avg_sleep_hours=w.avg_sleep_hours,
            avg_focus_0_100=w.avg_focus_0_100, avg_social_min=w.avg_social_min,
            avg_stress_0_10=w.avg_stress_0_10,
        )
