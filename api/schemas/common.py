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
