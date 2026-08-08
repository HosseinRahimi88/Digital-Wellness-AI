"""
api/routers/analytics.py
----------------------------
Read-only historical trend view over the authenticated user's own
prediction history: score-over-time, weekday pattern, and per-field
averages. All computation is delegated to AnalyticsService - this
router only fetches the account's HistoryService entries and shapes
the result into the response schema.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_history_service, get_history_storage_backend
from api.schemas.analytics import AnalyticsSummaryResponse, ScoreHistoryPoint
from services.account_service import Account
from services.analytics_service import AnalyticsService
from services.storage.base import StorageBackend

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/summary", response_model=AnalyticsSummaryResponse,
    summary="Score trend, weekday pattern, and per-field averages from the authenticated user's real history",
)
def analytics_summary(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> AnalyticsSummaryResponse:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.get_all()

    history_df = AnalyticsService.build_score_history_frame(entries)
    weekday_series = AnalyticsService.build_weekday_pattern(history_df)
    field_averages = AnalyticsService.compute_field_averages(entries)

    score_history = [
        ScoreHistoryPoint(date=row["date"].strftime("%Y-%m-%d"), health_score=float(row["health_score"]))
        for _, row in history_df.iterrows()
    ]

    return AnalyticsSummaryResponse(
        entry_count=len(entries),
        has_enough_points_for_trend=AnalyticsService.has_enough_points_for_trend(history_df),
        score_history=score_history,
        weekday_pattern=weekday_series.to_dict() if weekday_series is not None else None,
        field_averages=field_averages,
    )
