"""
api/routers/journal.py
-----------------------
The daily journal: one written page per day, per account.

Every endpoint resolves the book from the token and never from the
request body, so there is no path here that reads or writes somebody
else's page. Validation (empty page, over-long page, a date that has
not happened) lives in services/identity/journal_service.py and is mapped to
400 here, once, so no endpoint invents its own status for it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse

from api.auth.security import get_current_account
from api.exceptions.errors import BadRequestError, NotFoundError
from api.schemas.journal import (
    JournalEntryResponse,
    JournalListResponse,
    SaveJournalRequest,
)
from services.identity.account_service import Account
from services.identity.journal_pdf_service import build as build_journal_pdf
from services.identity.journal_service import JournalService, JournalValidationError

router = APIRouter(tags=["Journal"])


def _journal(account: Account) -> JournalService:
    return JournalService(account.user_id)


@router.get(
    "/journal", response_model=JournalListResponse,
    summary="Every page this account has written, newest first",
)
def list_journal(
    limit: int = Query(default=120, ge=1, le=400),
    account: Account = Depends(get_current_account),
) -> JournalListResponse:
    service = _journal(account)
    entries = service.get_all(limit=limit)
    return JournalListResponse(
        entries=[JournalEntryResponse.from_entry(e) for e in entries],
        count=service.count(),
    )


@router.get(
    "/journal.pdf", response_class=StreamingResponse,
    summary="The whole book as a PDF, in the reader's own language",
)
def journal_pdf(
    lang: str = Query("en", description="en, fa, ar or zh"),
    account: Account = Depends(get_current_account),
) -> StreamingResponse:
    """Declared BEFORE /journal/{day} on purpose.

    FastAPI matches routes in declaration order, so with the parameter
    route first this address would be read as the day "journal.pdf" and
    answered with a 400 about a date the calendar does not have.
    """
    service = _journal(account)
    entries = [e.to_dict() for e in service.get_all()]
    buffer = build_journal_pdf(
        entries, lang=lang, display_name=account.display_name or "",
    )
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="book-of-days.pdf"'},
    )


@router.get(
    "/journal/{day}", response_model=JournalEntryResponse,
    summary="One day's page",
)
def get_journal_day(
    day: str,
    account: Account = Depends(get_current_account),
) -> JournalEntryResponse:
    try:
        entry = _journal(account).get(day)
    except JournalValidationError as exc:
        raise BadRequestError(str(exc), error_code="journal_invalid") from exc
    if entry is None:
        raise NotFoundError("Nothing is written on that day yet.", error_code="journal_empty_day")
    return JournalEntryResponse.from_entry(entry)


@router.put(
    "/journal/{day}", response_model=JournalEntryResponse,
    summary="Write or rewrite one day's page",
)
def save_journal_day(
    day: str,
    payload: SaveJournalRequest,
    account: Account = Depends(get_current_account),
) -> JournalEntryResponse:
    """Upsert, not append: a diary has one page per day.

    Writing the same date twice edits that page. The first write's
    timestamp survives the edit, because the book shows when a day was
    written and correcting a sentence does not make it a different day.
    """
    try:
        entry = _journal(account).save(day, payload.text, payload.mood)
    except JournalValidationError as exc:
        raise BadRequestError(str(exc), error_code="journal_invalid") from exc
    return JournalEntryResponse.from_entry(entry)


@router.delete(
    "/journal/{day}", status_code=204,
    summary="Tear one page out",
)
def delete_journal_day(
    day: str,
    account: Account = Depends(get_current_account),
) -> Response:
    try:
        removed = _journal(account).delete(day)
    except JournalValidationError as exc:
        raise BadRequestError(str(exc), error_code="journal_invalid") from exc
    if not removed:
        raise NotFoundError("Nothing is written on that day yet.", error_code="journal_empty_day")
    return Response(status_code=204)
