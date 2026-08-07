"""
api/routers/schema.py
------------------------
Read-only introspection of core.feature_schema.FEATURE_SCHEMA - the
single source of truth for what PredictRequest.user_data accepts. This
endpoint exists specifically so that source of truth is never
duplicated into a second, hand-maintained list of fields/bounds
anywhere in the API layer.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas.common import FeatureSchemaField
from core.feature_schema import FEATURE_SCHEMA

router = APIRouter(prefix="/schema", tags=["Schema"])


@router.get(
    "/features", response_model=list[FeatureSchemaField],
    summary="Every feature accepted by prediction/what-if/future-path/twin endpoints",
)
def list_feature_schema() -> list[FeatureSchemaField]:
    return [
        FeatureSchemaField(
            name=feature.name,
            dtype=feature.dtype.__name__,
            required=feature.required,
            minimum=feature.minimum,
            maximum=feature.maximum,
            choices=feature.choices,
            label=feature.label,
            description=feature.description,
        )
        for feature in FEATURE_SCHEMA.values()
    ]
