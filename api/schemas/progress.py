"""
api/schemas/progress.py
--------------------------
Response models for the progress, insight, persona-identity and
privacy endpoints. Every field mirrors a real dataclass field produced
by services/insight/progress_service.py, services/insight/insight_service.py or
utils/persona_titles.py - nothing is computed here.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SmallWinResponse(BaseModel):
    field_name: str
    label: str
    previous_value: float
    current_value: float
    delta: float
    higher_is_better: bool


class PersonalBestResponse(BaseModel):
    metric: str
    label: str
    value: float
    achieved_on: str
    is_new: bool


class BeforeAfterResponse(BaseModel):
    available: bool
    before_days: int = 0
    after_days: int = 0
    before_avg_score: float | None = None
    after_avg_score: float | None = None
    delta: float | None = None
    is_meaningful: bool = False
    split_date: str | None = None
    # The second axis. `delta` alone reported "held a strong level all
    # week" and "went nowhere" identically, because both are a small
    # delta - so consistency was indistinguishable from improvement.
    # `pattern` is the resolved verdict over both axes and is what the
    # client should render; the raw spread is exposed alongside it so a
    # caller can show the number rather than only the label.
    before_sd: float | None = None
    after_sd: float | None = None
    consistency: float | None = None
    pattern: str = ""


class DecisionReplayStepResponse(BaseModel):
    date: str
    health_score: float | None
    health_class: str | None
    top_shap_feature: str | None
    delta_from_previous: float | None


class ProgressSummaryResponse(BaseModel):
    entry_count: int
    small_wins: list[SmallWinResponse]
    personal_bests: list[PersonalBestResponse]
    before_after: BeforeAfterResponse | None
    replay: list[DecisionReplayStepResponse]
    current_streak: int
    longest_streak: int


class ColdStartResponse(BaseModel):
    entry_count: int
    stage: str
    trend_available: bool
    weekday_pattern_available: bool
    week_comparison_available: bool
    message: str
    # {part: {lang: text}} - the same message in all four languages.
    # `message` stays English so an older client is unaffected.
    text_i18n: dict[str, dict[str, str]] = {}


class WeekdayReliabilityResponse(BaseModel):
    weekday: str
    observations: int
    average_score: float | None
    is_reliable: bool


class InsightsResponse(BaseModel):
    cold_start: ColdStartResponse
    weekday_reliability: list[WeekdayReliabilityResponse]


class PersonaTitleResponse(BaseModel):
    key: str
    title: str
    tagline: str
    icon: str
    reason: str
    match_strength: float


class BadgeResponse(BaseModel):
    key: str
    label: str
    icon: str
    description: str


class PersonaIdentityResponse(BaseModel):
    primary: PersonaTitleResponse | None
    alternates: list[PersonaTitleResponse]
    badges: list[BadgeResponse]


class DataDictionaryEntryResponse(BaseModel):
    name: str
    label: str
    dtype: str
    source: str
    required: bool
    minimum: float | None
    maximum: float | None
    choices: list[Any] | None
    how_to_measure: str
    description: str


class ProfileExtrasRequest(BaseModel):
    avatar_data_url: str | None = None
    recommendation_tone: str | None = None


class DataExportResponse(BaseModel):
    """Everything this app stores about the requesting user (P1 item 35)."""
    account: dict[str, Any]
    history: list[dict[str, Any]]
    exported_at: str


class DayStatusEntry(BaseModel):
    """One calendar day, scored on both halves.

    `status` is an id, not a label: the client maps it to a colour and
    to translated words, exactly like every badge id here. See
    services/wellness/day_status_service.py for what the four mean.
    """

    date: str
    logged: bool
    task_done: bool
    status: str                    # green | orange | grey | red
    penalty: float                 # 0.0 | -0.5 | -1.0
    score: float | None = None     # null when the day was never logged
    is_today: bool = False


class DayStatusResponse(BaseModel):
    days: list[DayStatusEntry] = []
    counts: dict[str, int] = {}
    # Reported, never subtracted from the wellness score. That number is
    # the model's reading of habits; this is a record of engagement with
    # the app, and mixing them would make one number mean two things.
    total_penalty: float = 0.0
    start_date: str | None = None
    end_date: str | None = None


class DeclineResponse(BaseModel):
    """A run of consecutive daily falls, or an explicit "no".

    `penalty` is an accountability figure recorded in the missed-day
    ledger. It is never subtracted from the wellness score - that number
    is the model's reading of the habits submitted, and editing it would
    make the app's headline something other than what the model said.
    """

    declining: bool
    days: int = 0
    drop: float = 0.0
    penalty: float = 0.0
    dates: list[str] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)
    acknowledged: bool = False
    acknowledged_reason: str | None = None
    run_id: str | None = None

    @staticmethod
    def from_report(r) -> "DeclineResponse":
        return DeclineResponse(
            declining=r.declining, days=r.days, drop=r.drop, penalty=r.penalty,
            dates=list(r.dates), scores=list(r.scores),
            acknowledged=r.acknowledged, acknowledged_reason=r.acknowledged_reason,
            run_id=r.run_id,
        )


class DeclineAckRequest(BaseModel):
    run_id: str = Field(..., description="The run being answered - its last date.")
    reason: str = Field(
        default="", max_length=280,
        description="What happened, in the user's own words. Kept, never sent anywhere.",
    )
