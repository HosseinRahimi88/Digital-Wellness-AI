"""
api/routers/progress.py
--------------------------
Progress, trust-context, persona-identity and privacy endpoints - the
P1-B "does this app actually show me getting somewhere?" surface.

Every endpoint reads the authenticated user's own real HistoryService
entries and delegates the actual computation to ProgressService /
InsightService / utils.persona_titles. No prediction is ever re-run
here, so nothing on this router can change a score the user has
already been shown.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_account_service,
    get_history_service,
    get_history_storage_backend,
)
from api.exceptions.errors import BadRequestError, NotFoundError
from api.schemas.progress import (
    DataDictionaryEntryResponse,
    DataExportResponse,
    InsightsResponse,
    PersonaIdentityResponse,
    ProfileExtrasRequest,
    ProgressSummaryResponse,
)
from services.account_service import Account, AccountService
from services.insight_service import InsightService
from services.progress_service import ProgressService
from services.storage.base import StorageBackend
from utils.data_dictionary import build_data_dictionary
from utils.persona_titles import resolve_identity

router = APIRouter(tags=["Progress & Profile"])


@router.get(
    "/progress/summary", response_model=ProgressSummaryResponse,
    summary="Small wins, personal bests, before/after and decision replay from real history",
)
def progress_summary(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> ProgressSummaryResponse:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.get_all(include_excluded=False)
    summary = ProgressService.summarize(entries)
    return ProgressSummaryResponse.model_validate(summary, from_attributes=True)


@router.get(
    "/insights", response_model=InsightsResponse,
    summary="Cold-start status and per-weekday reliability for the authenticated user",
)
def insights(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> InsightsResponse:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.get_all(include_excluded=False)
    return InsightsResponse.model_validate(
        {
            "cold_start": InsightService.cold_start_status(len(entries)),
            "weekday_reliability": InsightService.weekday_reliability(entries),
        },
        from_attributes=True,
    )


@router.get(
    "/personas/identity", response_model=PersonaIdentityResponse,
    summary="Rule-based persona title, alternates and earned badges from the latest real check-in",
)
def persona_identity(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> PersonaIdentityResponse:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.get_all()
    latest = entries[-1] if entries else {}
    identity = resolve_identity(latest, history=entries)
    return PersonaIdentityResponse.model_validate(identity, from_attributes=True)


@router.get(
    "/schema/data-dictionary", response_model=list[DataDictionaryEntryResponse],
    summary="Plain-language documentation for every input field, generated from FEATURE_SCHEMA",
)
def data_dictionary() -> list[DataDictionaryEntryResponse]:
    return [
        DataDictionaryEntryResponse.model_validate(entry, from_attributes=True)
        for entry in build_data_dictionary()
    ]


@router.put(
    "/auth/me/profile-extras", summary="Save avatar and/or recommendation tone",
)
def save_profile_extras(
    payload: ProfileExtrasRequest,
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
) -> dict:
    try:
        updated = account_service.save_profile_extras(
            account.user_id,
            avatar_data_url=payload.avatar_data_url,
            recommendation_tone=payload.recommendation_tone,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc), error_code="invalid_profile_extras") from exc

    if updated is None:
        raise NotFoundError("Account not found.", error_code="account_not_found")
    return {
        "avatar_data_url": updated.avatar_data_url,
        "recommendation_tone": updated.recommendation_tone,
    }


@router.get(
    "/privacy/export", response_model=DataExportResponse,
    summary="Download everything this app stores about you (P1 item 35)",
)
def export_my_data(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> DataExportResponse:
    history_service = get_history_service(account, storage=storage)
    account_dict = {
        "user_id": account.user_id,
        "email": account.email,
        "display_name": account.display_name,
        "created_at_utc": account.created_at_utc,
        "onboarding_complete": account.onboarding_complete,
        "primary_goal": account.primary_goal,
        "main_use_purpose": account.main_use_purpose,
        "schedule_type": account.schedule_type,
        "usual_sleep_time": account.usual_sleep_time,
        "usual_wake_time": account.usual_wake_time,
        "preferred_effort": account.preferred_effort,
        "work_screen_required": account.work_screen_required,
        "recommendation_tone": account.recommendation_tone,
        "has_avatar": bool(account.avatar_data_url),
    }
    # password_hash is deliberately excluded: exporting a credential
    # hash serves no user purpose and only widens its exposure.
    return DataExportResponse(
        account=account_dict,
        history=history_service.get_all(),
        exported_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


@router.get(
    "/privacy/export.json", response_class=PlainTextResponse,
    summary="Same export, delivered as a downloadable .json file",
)
def export_my_data_file(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> PlainTextResponse:
    payload = export_my_data(account=account, storage=storage)
    return PlainTextResponse(
        content=json.dumps(payload.model_dump(), indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=digital_wellness_my_data.json"},
    )


@router.delete(
    "/privacy/me", summary="Permanently delete this account and all of its stored history",
)
def delete_my_data(
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> dict:
    # History first: if account deletion succeeded but history deletion
    # then failed, the rows would be orphaned with no owner able to
    # reach them. This order fails safe in the opposite direction -
    # worst case the account survives and can retry.
    history_service = get_history_service(account, storage=storage)
    deleted_entries = history_service.delete_all()
    account_deleted = account_service.delete_account(account.user_id)
    return {"account_deleted": account_deleted, "history_entries_deleted": deleted_entries}
