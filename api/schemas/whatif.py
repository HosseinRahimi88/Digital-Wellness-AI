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
    # The shortfall: how far below the target `best_score` still is.
    # 0.0 whenever the target was actually reached.
    distance: float | None = None
    # Whether `best_value` gets to the target at all. Without this the
    # response could not distinguish "here is the value that does it"
    # from "nothing this field can do gets there, here is its ceiling",
    # and the page presented both as a found answer - see
    # AdvancedWhatIfService.goal_seek.
    reached: bool = False
    # The reader's own value and score before anything changes, so the
    # answer can be expressed as a change from where they are.
    current_value: float | None = None
    current_score: float | None = None
    # The target is already met; nothing about this field needs to move.
    already_there: bool = False
    points: list[SweepPointResponse] = []
