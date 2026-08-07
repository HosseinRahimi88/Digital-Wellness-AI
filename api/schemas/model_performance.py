"""api/schemas/model_performance.py"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TaskPerformanceResponse(BaseModel):
    model_name: str
    model_info: dict[str, Any]
    metrics: dict[str, Any]


class ModelPerformanceResponse(BaseModel):
    classification: TaskPerformanceResponse
    regression: TaskPerformanceResponse
