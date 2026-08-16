"""
api/schemas/insights_cards.py
------------------------------
Response shapes for the history-derived idea cards.

Every card is Optional. A missing card means "not enough of the user's
own data to say anything", and the client is expected to render nothing
rather than an empty card - which is why there are no default zeros
anywhere in this file.
"""

from __future__ import annotations

from pydantic import BaseModel


class CorrelationCard(BaseModel):
    field_a: str
    field_b: str
    coefficient: float
    direction: str  # "together" | "opposite"
    sample_size: int
    # Always true. Present so no client can render this as causation by
    # forgetting that it is a correlation.
    is_observation_only: bool = True


class DominoCard(BaseModel):
    trigger_field: str
    next_day_field: str
    coefficient: float
    direction: str
    sample_size: int
    is_observation_only: bool = True


class FirstVsNowCard(BaseModel):
    early_avg: float
    recent_avg: float
    delta: float
    window: int
    improved: bool


class SmallWinCard(BaseModel):
    field: str
    yesterday: float
    today: float
    delta: float
    higher_is_better: bool


class NarrativeCard(BaseModel):
    days: int
    avg_score: float | None = None
    best_day: str | None = None
    best_score: float | None = None
    worst_day: str | None = None
    worst_score: float | None = None
    score_delta_vs_previous_week: float | None = None
    most_improved_field: str | None = None
    most_improved_delta: float | None = None
    exceptions_marked: int = 0


class WeeklyChallengeCard(BaseModel):
    """Mirrors services/weekly_challenge_service.Challenge, whose targets
    are already derived from this user's own typical profile rather than
    from a generic number."""
    id: str
    # English, as the service has always produced it. The web client
    # localises from `id` + `params`; these two stay as the fallback for
    # any client that does not know an id yet.
    title: str
    description: str
    icon: str
    progress: int
    target: int
    completed: bool
    params: dict[str, float] = {}


class RiskAlertResponse(BaseModel):
    severity: str  # "critical" | "warning" | "info"
    title: str
    message: str
    action: str | None = None
    # {"title": {lang: text}, "message": {lang: text}, "action": {lang: text}}
    # - "action" is present only when the alert has one, same as the
    # flat `action` field above.
    text_i18n: dict[str, dict[str, str]] = {}


class InsightCardsResponse(BaseModel):
    correlation: CorrelationCard | None = None
    domino: DominoCard | None = None
    first_vs_now: FirstVsNowCard | None = None
    small_win: SmallWinCard | None = None
    narrative: NarrativeCard | None = None
    weekly_challenges: list[WeeklyChallengeCard] = []
    risk_alerts: list[RiskAlertResponse] = []
