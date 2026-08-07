"""api/schemas/cohort.py"""

from __future__ import annotations

from pydantic import BaseModel


class CohortAvailabilityResponse(BaseModel):
    available: bool
    cohort_size: int


class CohortSummaryResponse(BaseModel):
    field: str
    mean: float
    median: float
    p25: float
    p75: float


class CohortPercentileResponse(BaseModel):
    field: str
    value: float
    percentile: float


class CohortComparisonRow(BaseModel):
    field: str
    user_value: float
    cohort_percentile: float
    cohort_mean: float | None


class CohortComparisonResponse(BaseModel):
    rows: list[CohortComparisonRow]
