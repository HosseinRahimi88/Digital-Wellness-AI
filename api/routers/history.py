"""api/routers/history.py"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.auth.security import get_current_account
from api.core.config import Settings, get_settings
from api.dependencies.services import get_history_service, get_history_storage_backend
from api.exceptions.errors import NotFoundError
from api.schemas.common import PaginatedResponse, PaginationMeta
from api.schemas.history import HistoryEntryResponse, WeekSummaryResponse
from services.account_service import Account
from services.storage.base import StorageBackend

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=PaginatedResponse[HistoryEntryResponse], summary="Paginated prediction history, most recent first")
def list_history(
    account: Account = Depends(get_current_account),
    settings: Settings = Depends(get_settings),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1),
) -> PaginatedResponse[HistoryEntryResponse]:
    page_size = min(page_size or settings.default_page_size, settings.max_page_size)

    history_service = get_history_service(account, storage=storage)
    all_entries = list(reversed(history_service.get_all()))  # most recent first

    total_items = len(all_entries)
    total_pages = max(1, (total_items + page_size - 1) // page_size) if total_items else 0
    start = (page - 1) * page_size
    page_items = all_entries[start:start + page_size]

    return PaginatedResponse(
        items=[HistoryEntryResponse(**e) for e in page_items],
        pagination=PaginationMeta(page=page, page_size=page_size, total_items=total_items, total_pages=total_pages),
    )


@router.get("/{entry_date}", response_model=HistoryEntryResponse, summary="A single day's entry, e.g. 2026-08-07")
def get_history_entry(
    entry_date: str,
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> HistoryEntryResponse:
    history_service = get_history_service(account, storage=storage)
    for entry in history_service.get_all():
        if entry.get("date") == entry_date:
            return HistoryEntryResponse(**entry)
    raise NotFoundError(f"No history entry for {entry_date}.", error_code="history_entry_not_found")


@router.get("/weeks/current", response_model=WeekSummaryResponse | None, summary="Aggregated averages for the current calendar week")
def get_current_week_summary(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> WeekSummaryResponse | None:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.current_week_entries()
    summary = history_service.summarize(entries)
    return WeekSummaryResponse.from_week_summary(summary) if summary else None


@router.get("/weeks/previous", response_model=WeekSummaryResponse | None, summary="Aggregated averages for the previous calendar week")
def get_previous_week_summary(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> WeekSummaryResponse | None:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.previous_week_entries()
    summary = history_service.summarize(entries)
    return WeekSummaryResponse.from_week_summary(summary) if summary else None
