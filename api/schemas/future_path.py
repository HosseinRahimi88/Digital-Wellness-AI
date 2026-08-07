"""api/schemas/future_path.py"""

from __future__ import annotations

from pydantic import BaseModel, Field

from api.schemas.prediction import UncertaintyResponse


class FuturePathRequest(BaseModel):
    user_data: dict[str, float | int | str | bool | None] = Field(
        ..., description="Base-day feature values each path is a hypothetical shift away from."
    )
    path_keys: list[str] | None = Field(
        default=None,
        description="Subset of path keys to evaluate (see GET /api/v1/future-path/definitions for the full list). Omit to evaluate every defined path.",
    )


class PathResultResponse(BaseModel):
    key: str
    name: str
    description: str
    prediction: str | None
    regression_score: float | None
    confidence: float | None
    uncertainty: UncertaintyResponse | None
    score_delta_vs_status_quo: float | None
    error: str | None

    @staticmethod
    def from_path_result(r) -> "PathResultResponse":
        return PathResultResponse(
            key=r.key, name=r.name, description=r.description,
            prediction=r.prediction, regression_score=r.regression_score,
            confidence=r.confidence,
            uncertainty=UncertaintyResponse.from_uncertainty_result(r.uncertainty),
            score_delta_vs_status_quo=r.score_delta_vs_status_quo,
            error=r.error,
        )


class FuturePathResponse(BaseModel):
    paths: list[PathResultResponse]
    best_path_key: str | None
    worst_path_key: str | None


class PathDefinitionResponse(BaseModel):
    key: str
    name: str
    description: str
