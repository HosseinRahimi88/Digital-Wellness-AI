"""
api/routers/personal.py
------------------------
The personal-insight panel, assembled from four sources that already
exist separately: the usage tally, the cohort distribution, a model
fitted on this account's own days, and the facts its history supports.

Nothing here computes a new opinion of its own. Its whole job is to
call four services with this account's real data and hand back what
they say, including when what they say is "not enough".
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_history_service, get_history_storage_backend
from api.exceptions.errors import BadRequestError
from api.schemas.personal import (
    BirthDateRequest,
    CohortFieldResponse,
    CohortResponse,
    HeartbeatRequest,
    PersonalInsightResponse,
    PersonalModelResponse,
    UsageResponse,
)
from services.identity.account_service import Account
from services.ml.cohort_service import CohortService
from services.identity.history_service import TRACKED_FIELDS
from services.insight.personal_facts_service import build as build_facts
from services.insight.personal_model_service import fit as fit_personal_model
from services.identity.personal_service import PersonalService, PersonalValidationError
from services.storage.base import StorageBackend

router = APIRouter(tags=["Personal insight"])

# The handful of signals worth comparing against the cohort. Every one
# of them exists in both the user's tracked fields and the cohort's
# columns; a longer list would mostly repeat itself.
COMPARED_FIELDS = (
    "total_screen_min",
    "social_min",
    "sleep_hours",
    "stress_0_10",
    "focus_0_100",
    "physical_activity_min_per_day",
)


def _averages(entries: list[dict]) -> dict[str, float]:
    """This account's own mean for each compared field, from real rows."""
    out: dict[str, float] = {}
    for field in COMPARED_FIELDS:
        if field not in TRACKED_FIELDS:
            continue
        values = [
            float(row[field]) for row in entries
            if isinstance(row.get(field), (int, float)) and not isinstance(row.get(field), bool)
        ]
        if values:
            out[field] = sum(values) / len(values)
    return out


def _cohort(entries: list[dict]) -> CohortResponse:
    if not CohortService.is_available():
        return CohortResponse(available=False, source="none")

    scores = [
        float(row["health_score"]) for row in entries
        if isinstance(row.get("health_score"), (int, float)) and not isinstance(row.get("health_score"), bool)
    ]
    score_mean = sum(scores) / len(scores) if scores else None
    summary = CohortService.cohort_summary("health_score_0_100")

    rows = []
    for row in CohortService.compare_user_to_cohort(_averages(entries)):
        rows.append(CohortFieldResponse(
            field=str(row["field"]),
            user_value=float(row["user_value"]),
            percentile=float(row["cohort_percentile"]),
            cohort_mean=row.get("cohort_mean"),
        ))

    return CohortResponse(
        available=True,
        source=CohortService.source(),
        size=CohortService.cohort_size(),
        score_value=round(score_mean, 1) if score_mean is not None else None,
        score_percentile=(
            CohortService.percentile_for("health_score_0_100", score_mean)
            if score_mean is not None else None
        ),
        cohort_score_mean=summary["mean"] if summary else None,
        fields=rows,
    )


@router.get(
    "/personal/insight", response_model=PersonalInsightResponse,
    summary="Time in the app, this account against the cohort, its own fitted model, and the facts its days support",
)
def personal_insight(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> PersonalInsightResponse:
    history = get_history_service(account, storage=storage)
    entries = list(history.get_all(include_excluded=False))

    personal = PersonalService(account.user_id)
    birth_date = personal.birth_date()

    model = fit_personal_model(entries)

    return PersonalInsightResponse(
        usage=UsageResponse(**personal.usage().to_dict()),
        cohort=_cohort(entries),
        model=PersonalModelResponse(**model.to_dict()),
        facts=build_facts(entries, birth_date=birth_date, today=date.today()),
        birth_date=birth_date,
        days_logged=len(entries),
    )


@router.post(
    "/personal/heartbeat", response_model=UsageResponse,
    summary="Add measured seconds of visible app time to today's tally",
)
def heartbeat(
    payload: HeartbeatRequest,
    account: Account = Depends(get_current_account),
) -> UsageResponse:
    """The client sends what it MEASURED, and the server caps it.

    A tab left open all weekend must not be able to post two days of
    "use" in one beat, so the per-beat and per-day ceilings in
    services/identity/personal_service.py apply here whatever the client claims.
    """
    try:
        usage = PersonalService(account.user_id).add_seconds(payload.seconds)
    except PersonalValidationError as exc:
        raise BadRequestError(str(exc), error_code="usage_invalid") from exc
    return UsageResponse(**usage.to_dict())


@router.put(
    "/personal/birth-date", response_model=PersonalInsightResponse,
    summary="Set (or forget) the optional birth date the day-of-life facts need",
)
def set_birth_date(
    payload: BirthDateRequest,
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> PersonalInsightResponse:
    """Optional, and forgettable: sending null clears it.

    It is never fed to any model. It exists so the panel can say how
    many days someone has been alive next to how many they have logged
    here, which is a truer sentence about a wellness app than a score.
    """
    try:
        PersonalService(account.user_id).set_birth_date(payload.birth_date)
    except PersonalValidationError as exc:
        raise BadRequestError(str(exc), error_code="birth_date_invalid") from exc
    return personal_insight(account=account, storage=storage)
