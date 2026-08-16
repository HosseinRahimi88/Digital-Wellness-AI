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

from datetime import date as date_cls

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from api.auth.security import get_current_account
from api.core.config import Settings, get_settings
from api.dependencies.services import (
    get_history_service,
    get_history_storage_backend,
    get_prediction_service,
    get_recommendation_service,
    get_validation_service,
)
from api.exceptions.errors import BadRequestError, NotFoundError
from api.routers.prediction import build_predict_response, recent_scores_from
from api.schemas.common import PaginatedResponse, PaginationMeta
from api.schemas.history import (
    CSVImportResponse,
    HistoryDetailResponse,
    HistoryEntryResponse,
    HistoryExcludeRequest,
    HistorySnapshotEntry,
    HistorySnapshotsResponse,
    TodayCheckInResponse,
    WeekSummaryResponse,
)
from services.identity.account_service import Account
from services.identity.csv_import_service import CSVImportService
from services.identity.history_replay_service import SnapshotUnavailableError, replay
from services.ml.prediction_service import PredictionService
from services.wellness.recommendation_service import RecommendationService
from services.storage.base import StorageBackend
from services.ml.validation_service import ValidationService

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


@router.get(
    "/today", response_model=TodayCheckInResponse,
    summary="Whether today already has a check-in, and the answers it was built from",
)
def get_today_check_in(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> TodayCheckInResponse:
    """What the check-in page needs before it lets someone submit.

    One main check-in per day is the rule, and the page cannot enforce
    it from localStorage - a second device, a cleared browser, or a
    different session all know nothing about a day the server has
    already recorded. So it asks. When the day does exist, `inputs`
    carries that day's own validated answers so "edit today's check-in"
    opens the form on what the user actually said rather than on an
    empty questionnaire they would have to retype from memory.

    `inputs` is empty for days recorded before result snapshots existed.
    That is reported as an empty dict rather than a 404, because
    `exists` is the part the page must not get wrong; refilling is the
    convenience on top.

    Declared above `/{entry_date}` so "today" is read as this route and
    not as a date literal.
    """
    history_service = get_history_service(account, storage=storage)
    today = date_cls.today().isoformat()
    entry = next(
        (e for e in history_service.get_all(include_excluded=True) if e.get("date") == today),
        None,
    )
    if entry is None:
        return TodayCheckInResponse(date=today, exists=False)

    inputs: dict = {}
    try:
        validation, _ = replay(entry)
        inputs = dict(validation.cleaned_data)
    except SnapshotUnavailableError:
        inputs = {}

    return TodayCheckInResponse(
        date=today,
        exists=True,
        recorded_at=entry.get("recorded_at"),
        health_score=entry.get("health_score"),
        health_class=entry.get("health_class"),
        excluded=bool(entry.get("excluded", False)),
        inputs=inputs,
    )


@router.get(
    "/snapshots", response_model=HistorySnapshotsResponse,
    summary="Every recorded day's own answers, in one call",
)
def get_history_snapshots(
    limit: int = Query(default=60, ge=1, le=400),
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> HistorySnapshotsResponse:
    """The answers behind each day, oldest first, without the result screen.

    Added for "N days of history should mean N saved check-in files":
    the saved-check-in library holds the raw questionnaire for a day, and
    building one file per day through `/{date}/detail` would be N round
    trips each rebuilding recommendations, tone framing and a dimension
    breakdown that nothing here reads.

    Days recorded before result snapshots existed carry no answers to
    return. They are counted in `unavailable` rather than being filled in
    from the ~20 summary fields they do have - a check-in rebuilt from a
    third of its inputs is a different check-in.
    """
    history_service = get_history_service(account, storage=storage)
    entries = sorted(history_service.get_all(), key=lambda e: e.get("date") or "")
    out: list[HistorySnapshotEntry] = []
    unavailable = 0
    for entry in entries[-limit:]:
        try:
            validation, _ = replay(entry)
        except SnapshotUnavailableError:
            unavailable += 1
            continue
        out.append(HistorySnapshotEntry(
            date=entry.get("date") or "",
            day_of_week=entry.get("day_of_week"),
            health_score=entry.get("health_score"),
            inputs=validation.cleaned_data,
        ))
    return HistorySnapshotsResponse(entries=out, unavailable=unavailable)


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


@router.get(
    "/{entry_date}/detail", response_model=HistoryDetailResponse,
    summary="One past day reopened in full - the same result payload a fresh prediction returns",
)
def get_history_entry_detail(
    entry_date: str,
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    recommender: RecommendationService = Depends(get_recommendation_service),
) -> HistoryDetailResponse:
    """Rebuilds a stored day into the full result payload so the app can
    reopen it on the normal result screen.

    The model's own output is read back from that day's snapshot and
    never re-predicted: the classifier uses the user's earlier check-ins
    as trend features, so predicting an old day now would score it
    against history that did not exist yet and contradict the number
    already shown for it. Everything downstream of the model is
    regenerated through the same `build_predict_response` a live
    prediction uses, so a reopened day cannot drift into a second
    renderer.

    Days recorded before snapshots existed return 404 with
    `history_detail_unavailable` rather than a result reconstructed from
    the handful of summary fields they do carry.
    """
    history_service = get_history_service(account, storage=storage)
    entry = next((e for e in history_service.get_all() if e.get("date") == entry_date), None)
    if entry is None:
        raise NotFoundError(f"No history entry for {entry_date}.", error_code="history_entry_not_found")

    try:
        validation, result = replay(entry)
    except SnapshotUnavailableError as exc:
        raise NotFoundError(exc.message, error_code="history_detail_unavailable") from exc

    return HistoryDetailResponse(
        date=entry_date,
        day_of_week=entry.get("day_of_week"),
        recorded_at=entry.get("recorded_at"),
        excluded=bool(entry.get("excluded", False)),
        inputs=validation.cleaned_data,
        result=build_predict_response(
            validation, result, recommender, account,
            excluded_categories=set(), persisted=True,
            # Reopening the 3rd shows the seven-day band as it stood on
            # the 3rd, so the trend is read from the days up to and
            # including that one - not from days that had not happened.
            recent_scores=recent_scores_from(
                [e for e in history_service.get_all(include_excluded=False)
                 if (e.get("date") or "") <= entry_date]
            ),
        ),
    )


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
    allow_update: bool = Form(
        default=False,
        description=(
            "Permit rows that land on a day already recorded. Off by "
            "default: HistoryService.record() upserts, so an upload "
            "covering an existing day would otherwise overwrite that "
            "day's real result with no warning. The questionnaire "
            "export is a single row filed under today, which is exactly "
            "the day most likely to already exist."
        ),
    ),
    dry_run: bool = Form(
        default=False,
        description=(
            "Score the file and store nothing. This is the answer to "
            "'I only want to see what this file says': with nothing "
            "being written there is nothing to overwrite, so the "
            "duplicate-day rule does not apply and no row is refused "
            "for a reason that only matters when saving."
        ),
    ),
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
    result = importer.import_csv_text(csv_text, allow_update=allow_update, dry_run=dry_run)
    return CSVImportResponse.from_result(result)
