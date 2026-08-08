"""
api/routers/cohort.py
-------------------------
"How do I compare to everyone else" endpoints. `CohortService` (a
class-level, cached view over the training population) supplies the
population-side statistics; this router only adds the authenticated
user's own latest history entry to produce a genuine self-vs-cohort
percentile/comparison, never a fabricated placement.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.auth.security import get_current_account
from api.dependencies.services import get_cohort_service_cls, get_history_service, get_history_storage_backend
from api.exceptions.errors import NotFoundError
from api.schemas.cohort import (
    CohortAvailabilityResponse,
    CohortComparisonResponse,
    CohortComparisonRow,
    CohortPercentileResponse,
    CohortSummaryResponse,
)
from services.account_service import Account
from services.analytics_service import AnalyticsService
from services.cohort_service import CohortService
from services.storage.base import StorageBackend

router = APIRouter(prefix="/cohorts", tags=["Cohorts"])


@router.get("/availability", response_model=CohortAvailabilityResponse)
def cohort_availability(
    cohort_cls: type[CohortService] = Depends(get_cohort_service_cls),
) -> CohortAvailabilityResponse:
    return CohortAvailabilityResponse(available=cohort_cls.is_available(), cohort_size=cohort_cls.cohort_size())


@router.get("/summary", response_model=CohortSummaryResponse)
def cohort_summary(
    field: str = Query(..., description="e.g. total_screen_min, sleep_hours, stress_0_10"),
    cohort_cls: type[CohortService] = Depends(get_cohort_service_cls),
) -> CohortSummaryResponse:
    summary = cohort_cls.cohort_summary(field)
    if summary is None:
        raise NotFoundError(f"No cohort data available for field '{field}'.", error_code="cohort_field_unavailable")
    return CohortSummaryResponse(field=field, **summary)


@router.get("/percentile", response_model=CohortPercentileResponse)
def cohort_percentile(
    field: str = Query(...),
    value: float = Query(...),
    cohort_cls: type[CohortService] = Depends(get_cohort_service_cls),
) -> CohortPercentileResponse:
    percentile = cohort_cls.percentile_for(field, value)
    if percentile is None:
        raise NotFoundError(f"No cohort data available for field '{field}'.", error_code="cohort_field_unavailable")
    return CohortPercentileResponse(field=field, value=value, percentile=percentile)


@router.get(
    "/me/comparison", response_model=CohortComparisonResponse,
    summary="Compare the authenticated user's own real historical averages against the training cohort",
)
def compare_me_to_cohort(
    account: Account = Depends(get_current_account),
    cohort_cls: type[CohortService] = Depends(get_cohort_service_cls),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> CohortComparisonResponse:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.get_all()
    user_averages = AnalyticsService.compute_field_averages(entries)
    rows = cohort_cls.compare_user_to_cohort(user_averages)
    return CohortComparisonResponse(rows=[CohortComparisonRow(**row) for row in rows])
