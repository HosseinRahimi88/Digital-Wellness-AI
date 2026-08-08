"""api/schemas/plan.py"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanGenerateRequest(BaseModel):
    health_class: str | None = Field(default=None, description="e.g. the 'prediction' field from a real /predict response.")
    wellness_score: float | None = Field(default=None, description="e.g. the 'regression_score' field from a real /predict response.")
    persona: str | None = None
    user_data: dict[str, float | int | str | bool | None] = Field(default_factory=dict)


class PlanTaskResponse(BaseModel):
    task_index: int
    text: str
    completed: bool


class PlanDayResponse(BaseModel):
    day_number: int
    day_label: str
    theme: str
    icon: str
    tip: str
    tasks: list[PlanTaskResponse]


class PlanResponse(BaseModel):
    week_key: str
    intro: str
    focus_areas: list[str]
    days: list[PlanDayResponse]


class PlanTaskUpdateRequest(BaseModel):
    day_number: int
    task_index: int
    completed: bool
