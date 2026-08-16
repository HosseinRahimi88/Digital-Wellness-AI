"""
api/routers/coach.py
-----------------------
One endpoint that hands the Coach a complete digest of the signed-in
user's real history, so it can read their whole picture before answering
anything instead of relying on whatever single result the browser had
cached.

The digest is assembled by services/wellness/coach_context_service.py; this
router only resolves the request to a user, filters excluded days, and
translates the dataclass to Pydantic. No statistic is computed here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.auth.security import get_current_account
from api.schemas.coach import CoachContextResponse, SignalTrendResponse
from services.identity.account_service import Account
from services.wellness.coach_context_service import CoachContextService
from services.identity.history_service import HistoryService

router = APIRouter(prefix="/coach", tags=["AI Coach"])


@router.get(
    "/context", response_model=CoachContextResponse,
    summary="Everything the app knows about you, digested for the Coach to read before it answers",
)
def coach_context(
    language: str = Query("en", description="Language the Coach should answer in."),
    muted_topics: str = Query("", description="Comma-separated coaching topics the user has muted."),
    account: Account = Depends(get_current_account),
) -> CoachContextResponse:
    history = HistoryService(user_id=account.user_id)

    # Averages must honour the user's exclusions, but the Coach still
    # needs to know how many days were set aside, so both are read.
    included = history.get_all(include_excluded=False)
    everything = history.get_all(include_excluded=True)
    excluded_count = max(0, len(everything) - len(included))

    muted = [t.strip() for t in muted_topics.split(",") if t.strip()]

    ctx = CoachContextService.build(
        entries=included,
        account=account,
        language=language,
        muted_topics=muted,
        excluded_day_count=excluded_count,
    )

    return CoachContextResponse(
        display_name=ctx.display_name,
        language=ctx.language,
        persona=ctx.persona,
        primary_goal=ctx.primary_goal,
        preferred_effort=ctx.preferred_effort,
        recommendation_tone=ctx.recommendation_tone,
        latest_score=ctx.latest_score,
        latest_class=ctx.latest_class,
        latest_confidence=ctx.latest_confidence,
        latest_date=ctx.latest_date,
        top_factors=ctx.top_factors,
        entry_count=ctx.entry_count,
        excluded_day_count=ctx.excluded_day_count,
        streak_days=ctx.streak_days,
        longest_streak=ctx.longest_streak,
        score_7d_ago=ctx.score_7d_ago,
        score_change_7d=ctx.score_change_7d,
        best_score=ctx.best_score,
        worst_score=ctx.worst_score,
        trends=[
            SignalTrendResponse(
                field_name=t.field_name, label=t.label, higher_is_better=t.higher_is_better,
                recent_mean=t.recent_mean, earlier_mean=t.earlier_mean,
                change=t.change, direction=t.direction,
            )
            for t in ctx.trends
        ],
        strongest_signals=ctx.strongest_signals,
        weakest_signals=ctx.weakest_signals,
        plan_focus_areas=ctx.plan_focus_areas,
        muted_topics=ctx.muted_topics,
        data_sufficiency=ctx.data_sufficiency,
        notes=ctx.notes,
    )
