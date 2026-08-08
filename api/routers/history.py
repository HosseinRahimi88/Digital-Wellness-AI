"""
api/routers/history.py
--------------------------
Read-only access to the authenticated user's persisted check-ins
(one HistoryService record per prediction made with `persist=True`).
Covers paginated listing, a single day's entry, and pre-aggregated
current/previous ISO-week summaries - all computed from the same
underlying entries, never a separate data source.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile

from api.auth.security import get_current_account
from api.core.config import Settings, get_settings
from api.dependencies.services import (
    get_history_service,
    get_history_storage_backend,
    get_prediction_service,
    get_validation_service,
)
from api.exceptions.errors import BadRequestError, NotFoundError
from api.schemas.common import PaginatedResponse, PaginationMeta
from api.schemas.history import (
    CSVImportResponse,
    HistoryEntryResponse,
    HistoryExcludeRequest,
    WeekSummaryResponse,
)
from services.account_service import Account
from services.csv_import_service import CSVImportService
from services.prediction_service import PredictionService
from services.storage.base import StorageBackend
from services.validation_service import ValidationService

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


@router.put(
    "/{entry_date}/exclude", response_model=HistoryEntryResponse,
    summary="Include/exclude one day from aggregate trend and weekly-average calculations",
)
def set_entry_excluded(
    entry_date: str,
    payload: HistoryExcludeRequest,
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> HistoryEntryResponse:
    history_service = get_history_service(account, storage=storage)
    updated = history_service.set_excluded(entry_date, payload.excluded)
    if updated is None:
        raise NotFoundError(f"No history entry for {entry_date}.", error_code="history_entry_not_found")
    return HistoryEntryResponse(**updated)


@router.get("/weeks/current", response_model=WeekSummaryResponse | None, summary="Aggregated averages for the current calendar week")
def get_current_week_summary(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> WeekSummaryResponse | None:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.current_week_entries(include_excluded=False)
    summary = history_service.summarize(entries)
    return WeekSummaryResponse.from_week_summary(summary) if summary else None


@router.get("/weeks/previous", response_model=WeekSummaryResponse | None, summary="Aggregated averages for the previous calendar week")
def get_previous_week_summary(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> WeekSummaryResponse | None:
    history_service = get_history_service(account, storage=storage)
    entries = history_service.previous_week_entries(include_excluded=False)
    summary = history_service.summarize(entries)
    return WeekSummaryResponse.from_week_summary(summary) if summary else None


@router.post(
    "/import-csv", response_model=CSVImportResponse,
    summary="Bulk-import several days at once from a CSV (see GET /schema/csv-template for the expected format)",
)
async def import_history_csv(
    file: UploadFile = File(..., description="CSV file matching GET /schema/csv-template's column layout"),
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
) -> CSVImportResponse:
    raw = await file.read()
    try:
        csv_text = raw.decode("utf-8-sig")  # -sig strips a BOM some spreadsheet apps add
    except UnicodeDecodeError as exc:
        raise BadRequestError("The uploaded file isn't valid UTF-8 text.", error_code="invalid_csv_encoding") from exc

    history_service = get_history_service(account, storage=storage)
    importer = CSVImportService(history_service, validator, predictor)
    result = importer.import_csv_text(csv_text)
    return CSVImportResponse.from_result(result)
