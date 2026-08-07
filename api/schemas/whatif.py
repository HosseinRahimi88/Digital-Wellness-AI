"""api/schemas/whatif.py"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SweepPointResponse(BaseModel):
    value: float
    score: float | None
    prediction: str | None


class SweepRequest(BaseModel):
    user_data: dict[str, float | int | str | bool | None]
    field: str = Field(..., description="Feature name to sweep across its full schema range - see GET /api/v1/schema/features.")
    num_points: int = Field(default=9, ge=2, le=50)


class SweepResponse(BaseModel):
    field: str
    points: list[SweepPointResponse]


class GoalSeekRequest(BaseModel):
    user_data: dict[str, float | int | str | bool | None]
    field: str
    target_score: float = Field(..., ge=0.0, le=100.0)
    num_points: int = Field(default=15, ge=2, le=100)


class GoalSeekResponse(BaseModel):
    available: bool
    field: str | None = None
    target_score: float | None = None
    best_value: float | None = None
    best_score: float | None = None
    distance: float | None = None
    points: list[SweepPointResponse] = []
