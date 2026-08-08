"""
api/schemas/progress.py
--------------------------
Response models for the progress, insight, persona-identity and
privacy endpoints. Every field mirrors a real dataclass field produced
by services/progress_service.py, services/insight_service.py or
utils/persona_titles.py - nothing is computed here.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


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
