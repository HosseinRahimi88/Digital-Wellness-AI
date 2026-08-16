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
    # True when the user is already at or past the healthy target on
    # every field this path can adjust, so it changed nothing.
    already_at_target: bool = False
    # False when |delta| is inside the model's own noise floor. The
    # client shows "about the same" rather than a signed number, so a
    # 0.1-point wobble never reads as a real direction.
    delta_is_meaningful: bool = False
    # What the adjustments actually were, so the card can show the user
    # which habits the path moved and to what.
    adjustments: list[dict] = []

    @staticmethod
    def from_path_result(r, comparison=None) -> "PathResultResponse":
        meaningful = bool(comparison.is_delta_meaningful(r)) if comparison is not None else False
        return PathResultResponse(
            key=r.key, name=r.name, description=r.description,
            prediction=r.prediction, regression_score=r.regression_score,
            confidence=r.confidence,
            uncertainty=UncertaintyResponse.from_uncertainty_result(r.uncertainty),
            score_delta_vs_status_quo=r.score_delta_vs_status_quo,
            error=r.error,
            already_at_target=getattr(r, "already_at_target", False),
            delta_is_meaningful=meaningful,
            adjustments=list(getattr(r, "adjustments", []) or []),
        )


class FuturePathResponse(BaseModel):
    paths: list[PathResultResponse]
    best_path_key: str | None
    worst_path_key: str | None


class PathDefinitionResponse(BaseModel):
    key: str
    name: str
    description: str
