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

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from api.schemas.common import FeatureSchemaField
from config.demo_profiles import DEMO_PROFILES
from core.feature_schema import FEATURE_SCHEMA
from services.identity.csv_import_service import build_template_csv

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


@router.get(
    "/demo-profiles", response_model=dict[str, dict[str, Any]],
    summary="Fully-derived example inputs (Healthy/Borderline/At Risk/Baseline) for a one-click demo prediction",
)
def list_demo_profiles() -> dict[str, dict[str, Any]]:
    # Calls the exact same config.demo_profiles builders the Streamlit
    # Prediction page's "Quick Demo" tab and the test suite use - no
    # second, hand-copied set of demo numbers maintained here.
    return {label: builder() for label, builder in DEMO_PROFILES.items()}


@router.get(
    "/csv-template", response_class=PlainTextResponse,
    summary="Downloadable CSV template (with two filled example days) for bulk daily check-in import",
)
def download_csv_template() -> PlainTextResponse:
    return PlainTextResponse(
        content=build_template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=digital_wellness_checkin_template.csv"},
    )
