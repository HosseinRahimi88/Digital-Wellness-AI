"""
api/schemas/personal.py
------------------------
Shapes for the personal-insight panel: measured time in the app, this
account against the training cohort, a model fitted on this account's
own days, and the facts that history supports.

Everything optional here is optional because it can genuinely be
absent - no cohort file, too few days to fit anything, no birth date
given. None of those are error states, and each is reported as itself
rather than as a zero.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class UsageResponse(BaseModel):
    total_seconds: int = 0
    total_minutes: float = 0.0
    today_seconds: int = 0
    today_minutes: float = 0.0
    days_present: int = 0
    best_day_seconds: int = 0
    best_day_minutes: float = 0.0
    best_day: str = ""
    first_seen: str = ""


class CohortFieldResponse(BaseModel):
    field: str
    user_value: float
    percentile: float
    cohort_mean: Optional[float] = None


class CohortResponse(BaseModel):
    available: bool = False
    # "dataset" | "reference" | "none" - said out loud, because a
    # distribution read from a shipped 14KB summary is not the same
    # claim as one read from the whole training set.
    source: str = "none"
    size: int = 0
    score_percentile: Optional[float] = None
    score_value: Optional[float] = None
    cohort_score_mean: Optional[float] = None
    fields: list[CohortFieldResponse] = []


class DriverResponse(BaseModel):
    field: str
    points_per_sd: float
    direction: str
    user_mean: float
    user_sd: float


class PersonalModelResponse(BaseModel):
    available: bool = False
    reason: str = "not_enough_days"
    days: int = 0
    signals: int = 0
    r2: Optional[float] = None
    r2_loo: Optional[float] = None
    score_mean: Optional[float] = None
    score_sd: Optional[float] = None
    trustworthy: bool = False
    drivers: list[DriverResponse] = []


class PersonalInsightResponse(BaseModel):
    usage: UsageResponse
    cohort: CohortResponse
    model: PersonalModelResponse
    facts: list[dict[str, Any]] = []
    birth_date: Optional[str] = None
    days_logged: int = 0


class HeartbeatRequest(BaseModel):
    seconds: int = Field(..., ge=0, le=600, description="Measured visible seconds since the last beat.")


class BirthDateRequest(BaseModel):
    birth_date: Optional[str] = Field(None, description="ISO date, or null to forget it.")
