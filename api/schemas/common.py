"""
api/schemas/common.py
-----------------------
Shared response envelopes used across routers.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationMeta(BaseModel):
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta


class FeatureSchemaField(BaseModel):
    """Mirrors core.feature_schema.Feature - exposed read-only via
    GET /api/v1/schema/features so API clients can build a valid
    request without a second, hand-maintained copy of FEATURE_SCHEMA
    living in client code or in this API's own request models."""

    name: str
    dtype: str
    required: bool
    minimum: float | None = None
    maximum: float | None = None
    choices: list[object] | None = None
    label: str
    description: str
    # True when utils/feature_derivation.derive_features() computes this
    # field from other answers and therefore OVERWRITES whatever is sent
    # for it. Thirteen of the fifty-three are like this.
    #
    # It matters to any client offering a field for the user to change.
    # The what-if simulator offered all forty-two numeric fields; on
    # thirteen of them - total screen time, every ratio, every density,
    # fragmentation, dependence - the sweep set the value, derivation
    # immediately replaced it, and the chart came back a dead flat line
    # across the whole range. Nothing errored, so it looked like a
    # finding about the user rather than a field that cannot be swept.
    #
    # Measured, never hand-listed: see api/routers/schema.py.
    derived: bool = False
