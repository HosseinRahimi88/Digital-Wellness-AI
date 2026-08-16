"""api/schemas/history.py"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.prediction import PredictResponse


class HistoryEntryResponse(BaseModel):
    """A stored prediction-history entry. The well-known fields below
    are always present; `extra="allow"` lets the rest of the tracked
    fields (services/identity/history_service.py's TRACKED_FIELDS - sleep_hours,
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


class HistoryDetailResponse(BaseModel):
    """One past day, reopened in full - the same `result` shape a fresh
    prediction returns, plus the inputs that produced it so the check-in
    form can be refilled from that day.

    `result.regression_score` here is the score that day was actually
    given, read back from storage rather than re-predicted (see
    services/identity/history_replay_service.py for why those differ).
    """

    date: str
    day_of_week: str | None = None
    recorded_at: str | None = None
    excluded: bool = False
    inputs: dict[str, Any]
    result: PredictResponse


class HistorySnapshotEntry(BaseModel):
    """One recorded day's ANSWERS, without rebuilding the result screen.

    `/{date}/detail` gives the full result payload - recommendations,
    dimension breakdown, tone framing - which is right for reopening one
    day and far too much for "give me every day's answers so I can write
    them out as files". This is the cheap half.
    """

    date: str
    day_of_week: str | None = None
    health_score: float | None = None
    inputs: dict[str, Any]


class HistorySnapshotsResponse(BaseModel):
    entries: list[HistorySnapshotEntry]
    # Days that exist but predate result snapshots, so their answers
    # cannot be handed back. Counted rather than silently dropped.
    unavailable: int = 0


class TodayCheckInResponse(BaseModel):
    """Today's main check-in, if there is one.

    The check-in page reads this before it lets someone submit. One main
    check-in per day is enforced on the server, so the page has to ask
    the server - a second device or a cleared browser knows nothing
    about a day that is already recorded.
    """

    date: str
    exists: bool
    recorded_at: str | None = None
    health_score: float | None = None
    health_class: str | None = None
    excluded: bool = False
    # That day's own validated answers, so "edit today's check-in" opens
    # on what the user actually said. Empty for days recorded before
    # result snapshots existed - `exists` is still correct for those.
    inputs: dict[str, Any] = {}


class CSVImportRowError(BaseModel):
    row_number: int
    date: str | None
    errors: dict[str, str]


class CSVImportRowPreview(BaseModel):
    row_number: int
    date: str
    health_score: float | None
    health_class: str | None


class CSVImportResponse(BaseModel):
    imported_count: int
    imported_dates: list[str]
    failed_rows: list[CSVImportRowError]
    previews: list[CSVImportRowPreview] = Field(
        default_factory=list,
        description=(
            "What each row that validated actually scored. In a dry run "
            "this is the whole result; in a real import it confirms the "
            "days now in the history."
        ),
    )
    dry_run: bool = Field(
        default=False,
        description="True when the upload was scored and nothing was stored.",
    )

    @staticmethod
    def from_result(r) -> "CSVImportResponse":
        return CSVImportResponse(
            imported_count=r.imported_count,
            imported_dates=r.imported_dates,
            failed_rows=[CSVImportRowError(row_number=f.row_number, date=f.date, errors=f.errors) for f in r.failed_rows],
            previews=[
                CSVImportRowPreview(
                    row_number=p.row_number, date=p.date,
                    health_score=p.health_score, health_class=p.health_class,
                )
                for p in getattr(r, "previews", [])
            ],
            dry_run=bool(getattr(r, "dry_run", False)),
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
