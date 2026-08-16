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

import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_account_service,
    get_history_service,
    get_history_storage_backend,
    get_plan_progress_service,
)
from api.exceptions.errors import BadRequestError, NotFoundError
from api.schemas.progress import (
    DayStatusEntry,
    DayStatusResponse,
    DeclineAckRequest,
    DeclineResponse,
    DataDictionaryEntryResponse,
    DataExportResponse,
    InsightsResponse,
    PersonaIdentityResponse,
    ProfileExtrasRequest,
    ProgressSummaryResponse,
)
from services.identity.account_service import Account, AccountService
from dataclasses import asdict

from services.wellness.day_status_service import (
    build_day_statuses,
    counts_by_status,
    total_penalty,
)
from services.identity.history_service import TRACKED_FIELDS
from services.insight.insight_service import InsightService
from services.identity.journal_service import JournalService
from services.identity.personal_service import PersonalService
from services.identity.refresh_token_service import RefreshTokenService
from services.identity.report_i18n import (
    field_label as report_field_label,
    normalise as normalise_report_lang,
    t as t_report,
)
from services.wellness.decline_service import ACKNOWLEDGED_RELIEF, detect as detect_decline
from services.insight.progress_service import ProgressService
from services.storage.base import StorageBackend
from services.wellness.violation_service import ViolationService
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


@router.get(
    "/privacy/export.csv", response_class=PlainTextResponse,
    summary="The same history as a spreadsheet, in the language the user picked (C-5-7)",
)
def export_my_data_csv(
    lang: str = Query("en", description="en, fa, ar or zh"),
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> PlainTextResponse:
    """One file in the user's own language, rather than four sheets.

    The brief offered either four sheets (one per language) or a single
    file in the language the user chose, and asked for whichever is
    implemented best. CSV has no concept of a sheet - four sheets means
    XLSX, which means a new dependency and a format some of this app's
    users would then have to convert back. One correct file wins.

    Two details that decide whether this actually opens:

      * A UTF-8 BOM. Excel on Windows reads a BOM-less UTF-8 CSV as the
        system code page, which turns every Persian, Arabic and Chinese
        character into mojibake. The BOM costs three bytes and is the
        difference between a readable file and a broken one.
      * CRLF line endings, for the same reason: it is what spreadsheet
        software expects.

    Note this is deliberately NOT the import template, which keeps its
    English machine-readable column names - translating those would
    break the importer that reads them back.
    """
    history_service = get_history_service(account, storage=storage)
    entries = history_service.get_all(include_excluded=True)
    language = normalise_report_lang(lang)

    columns = [
        ("date", t_report("csv_date", language)),
        ("day_of_week", t_report("csv_day", language)),
        ("health_score", t_report("csv_score", language)),
        ("health_class", t_report("csv_class", language)),
    ] + [(field, report_field_label(field, language)) for field in TRACKED_FIELDS]
    columns.append(("excluded", t_report("csv_excluded", language)))

    yes, no = t_report("csv_yes", language), t_report("csv_no", language)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow([label for _, label in columns])
    for entry in entries:
        row = []
        for key, _ in columns:
            value = entry.get(key)
            if key == "excluded":
                row.append(yes if value else no)
            else:
                row.append("" if value is None else value)
        writer.writerow(row)

    return PlainTextResponse(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=digital_wellness_history_{language}.csv",
        },
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
    # The journal is the one store holding text the user wrote in their
    # own words, so leaving it behind on a "delete everything" would be
    # the worst possible omission. Same order rule as above: it goes
    # before the account row.
    deleted_pages = JournalService(account.user_id).delete_all()
    # The usage tally and the optional birth date go the same way, for
    # the same reason: "delete everything" has to mean it.
    PersonalService(account.user_id).delete_all()
    # Sessions too. A refresh token outliving the account it belongs to
    # would be a thirty-day credential pointing at a user_id that no
    # longer exists - harmless today because /auth/refresh checks the
    # account still exists, and exactly the kind of leftover that stops
    # being harmless the first time some other lookup does not.
    RefreshTokenService(account.user_id).delete_users([account.user_id])
    account_deleted = account_service.delete_account(account.user_id)
    return {
        "account_deleted": account_deleted,
        "history_entries_deleted": deleted_entries,
        "journal_pages_deleted": deleted_pages,
    }


@router.get(
    "/progress/days", response_model=DayStatusResponse,
    summary="Each recent day coloured by whether it was logged AND whether its plan task was done",
)
def get_day_statuses(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    # 28 is the dashboard strip; the ceiling is high enough for the
    # "every day you have logged" view to colour a year of history
    # rather than silently losing the colours past day 120.
    days: int = Query(default=28, ge=1, le=400),
) -> DayStatusResponse:
    """The dashboard's day strip, scored on both halves of a day.

    It used to colour a day by one fact - was there a check-in - which
    made three quite different situations look identical: logged but no
    plan work done, plan work done but never logged, and nothing at all.
    Those are the cases worth telling apart, so they are.

    Both halves are read from real records: the check-in from history,
    the plan task from the stored per-week progress, mapped onto
    calendar dates through the plan's own start date. Nothing here is
    inferred from the other - a day can be any of the four.

    The window starts at the user's FIRST check-in, never earlier: a
    person cannot miss a day that predates their account, and opening
    the dashboard onto a wall of red for the weeks before they signed
    up would be both wrong and discouraging.
    """
    from datetime import date as _date
    from datetime import timedelta as _timedelta

    history_service = get_history_service(account, storage=storage)
    try:
        entries = list(history_service.get_all(include_excluded=True))
    except Exception:  # noqa: BLE001
        entries = []

    dated = [e for e in entries if e.get("date")]
    if not dated:
        return DayStatusResponse()

    today = _date.today()
    first_seen = min(_date.fromisoformat(e["date"]) for e in dated)
    window_start = max(first_seen, today - _timedelta(days=days - 1))

    done_dates = _completed_task_dates(account, storage)

    statuses = build_day_statuses(dated, done_dates, window_start, today, today=today)
    return DayStatusResponse(
        # asdict, not vars(): DayStatus is a slots dataclass and has
        # no __dict__ at all.
        days=[DayStatusEntry(**asdict(s)) for s in statuses],
        counts=counts_by_status(statuses),
        total_penalty=total_penalty(statuses),
        start_date=window_start.isoformat(),
        end_date=today.isoformat(),
    )


def _completed_task_dates(account: Account, storage: StorageBackend | None) -> set[str]:
    """Calendar dates whose plan task the user actually ticked.

    Progress is stored per (week, day number, task index), so it has to
    be mapped back onto real dates through each week's own plan start.
    A day counts as done when EVERY task for it is ticked - a day half
    finished is a day the plan was not followed, which is the whole
    distinction the orange state exists to show.
    """
    from services.wellness.plan_lock_service import PlanLockService
    from services.wellness.violation_service import plan_day_date

    out: set[str] = set()
    try:
        lock_service = PlanLockService(account.user_id)
        progress_service = get_plan_progress_service(account, storage=storage)
        for record in lock_service._backend.read_all():
            if record.get("user_id") != account.user_id:
                continue
            locked = PlanLockService._to_locked(record)
            if locked is None:
                continue
            generated_on = (locked.created_at_utc or "")[:10]
            completed = progress_service.get_completed(locked.week_key)
            for day in (locked.plan.get("days") or []):
                number = int(day.get("day_number") or 0)
                total = len(day.get("tasks") or [])
                if total <= 0 or number <= 0:
                    continue
                ticked = sum(1 for (d, _t) in completed if d == number)
                if ticked < total:
                    continue
                when = plan_day_date(generated_on, number)
                if when:
                    out.add(when)
    except Exception:  # noqa: BLE001 - the strip still renders without it
        return out
    return out


# ---------------------------------------------------------------------
# Three days down in a row
# ---------------------------------------------------------------------
# The clearest early signal this data produces, and nothing acted on it:
# the dashboard drew three slightly shorter bars and said nothing. See
# services/wellness/decline_service.py for the run rule, the penalty formula, and
# why the penalty is an accountability figure rather than an edit to the
# model's score.

_DECLINE_KIND = "decline_ack"


def _decline_acks(user_id: str) -> dict:
    """This user's answered runs, keyed by run id."""
    try:
        service = ViolationService(user_id)
        return {
            r.get("run_id"): r
            for r in service._mine()  # noqa: SLF001 - same package, one ledger
            if r.get("kind") == _DECLINE_KIND and r.get("run_id")
        }
    except Exception:  # noqa: BLE001 - a ledger read must never break the dashboard
        return {}


@router.get(
    "/progress/decline", response_model=DeclineResponse,
    summary="Whether the last few days have fallen three or more times in a row",
)
def get_decline(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> DeclineResponse:
    history_service = get_history_service(account, storage=storage)
    report = detect_decline(history_service.get_all(include_excluded=False))
    if report.declining and report.run_id:
        acked = _decline_acks(account.user_id).get(report.run_id)
        if acked:
            report.acknowledged = True
            report.acknowledged_reason = acked.get("reason") or ""
            report.penalty = float(acked.get("penalty") or report.penalty)
    return DeclineResponse.from_report(report)


@router.post(
    "/progress/decline/ack", response_model=DeclineResponse,
    summary="Answer a three-day decline - what happened, and take the penalty",
)
def acknowledge_decline(
    payload: DeclineAckRequest,
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> DeclineResponse:
    """Records the answer and the penalty, once per run.

    Answering halves the penalty. Naming what happened is the behaviour
    this is trying to encourage; the days still happened, so it is a
    reduction and not a waiver.
    """
    history_service = get_history_service(account, storage=storage)
    report = detect_decline(history_service.get_all(include_excluded=False))
    if not report.declining or not report.run_id:
        raise BadRequestError("There is no decline to answer.", error_code="no_decline")
    if payload.run_id != report.run_id:
        raise BadRequestError(
            "That answer is for a different run of days.", error_code="decline_run_mismatch",
        )

    service = ViolationService(account.user_id)
    existing = _decline_acks(account.user_id).get(report.run_id)
    if existing is None:
        report.penalty = round(report.penalty * ACKNOWLEDGED_RELIEF, 1)
        service._append({  # noqa: SLF001 - same package, one ledger
            "user_id": account.user_id,
            "kind": _DECLINE_KIND,
            "run_id": report.run_id,
            "days": report.days,
            "drop": report.drop,
            "penalty": report.penalty,
            "reason": (payload.reason or "").strip()[:280],
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    else:
        report.penalty = float(existing.get("penalty") or report.penalty)

    report.acknowledged = True
    report.acknowledged_reason = (payload.reason or "").strip()[:280]
    return DeclineResponse.from_report(report)
