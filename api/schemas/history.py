"""api/schemas/history.py"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
    excluded: bool = False


class CSVImportRowError(BaseModel):
    row_number: int
    date: str | None
    errors: dict[str, str]


class CSVImportResponse(BaseModel):
    imported_count: int
    imported_dates: list[str]
    failed_rows: list[CSVImportRowError]

    @staticmethod
    def from_result(r) -> "CSVImportResponse":
        return CSVImportResponse(
            imported_count=r.imported_count,
            imported_dates=r.imported_dates,
            failed_rows=[CSVImportRowError(row_number=f.row_number, date=f.date, errors=f.errors) for f in r.failed_rows],
        )


class HistoryExcludeRequest(BaseModel):
    excluded: bool = Field(
        ...,
        description=(
            "If true, this day is left out of aggregate trend/average views (analytics summary, "
            "weekly summaries) - e.g. a day the user knows was a data-entry mistake or an outlier "
            "they don't want skewing their trend. Never affects the day's own already-computed "
            "prediction, and never changes any other day's data."
        ),
    )


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
