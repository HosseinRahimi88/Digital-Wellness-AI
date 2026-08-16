"""api/schemas/parallel_twin.py"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ParallelTwinRequest(BaseModel):
    user_data: dict[str, float | int | str | bool | None] = Field(
        ..., description="The real, current-day feature values to build a hypothetical improved 'twin' from."
    )


class TwinAdjustmentResponse(BaseModel):
    field: str
    label: str
    old_value: float
    new_value: float
    direction: str


class ParallelTwinResponse(BaseModel):
    available: bool = Field(
        ..., description="False when there were no adjustable SHAP-flagged areas to improve - a twin identical to the real user isn't a meaningful comparison, so no comparison is returned."
    )
    adjustments: list[TwinAdjustmentResponse] = []
    real_prediction: str | None = None
    real_regression_score: float | None = None
    twin_prediction: str | None = None
    twin_regression_score: float | None = None
    score_delta: float | None = None
    class_changed: bool = False
