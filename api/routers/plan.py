"""
api/routers/plan.py
----------------------
A thin HTTP wrapper over the existing ImprovementPlanService (pure,
rule-based 7-day plan generation - no model inference) and
PlanProgressService (per-user, per-ISO-week task checkmarks). Neither
service is reimplemented here, only sequenced and translated to
Pydantic, exactly like every other router in this package.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_history_service,
    get_history_storage_backend,
    get_improvement_plan_service,
    get_plan_progress_service,
    get_plan_side_storage_backend,
)
from api.exceptions.errors import BadRequestError, DayLockedError, NotFoundError
from api.schemas.plan import (
    PlanDayDecisionRequest,
    PlanDayResponse,
    PlanDayStatusResponse,
    PlanGenerateRequest,
    PlanResponse,
    PlanTaskResponse,
    PlanTaskUpdateRequest,
    PlanWeekSummary,
    PlanWeeksResponse,
    SignalTrackEntry,
    SignalTracksResponse,
)
from services.identity.account_service import Account
from services.wellness.day_decision_service import (
    COUNTED,
    EXCEPTION,
    EXCEPTION_WEIGHT,
    DayDecisionService,
)
from services.social.badge_service import BadgeService
from services.identity.history_replay_service import SnapshotUnavailableError, replay
from services.wellness.improvement_plan_service import DailyPlan, ImprovementPlan, ImprovementPlanService
from services.wellness.plan_lock_service import (
    PlanLockService,
    is_outside_band,
    week_band_detail,
)
from services.wellness.plan_progress_service import PlanProgressService, current_week_key
from services.storage.base import StorageBackend
from services.wellness.violation_service import ViolationService, plan_day_date, unlocked_through

def _exercise_fields(exercises: list, index: int) -> dict:
    """The composed exercise behind task `index`, if there is one.

    Returns an empty dict rather than None fields when there is not, so
    the response shape is identical either way and a client never has
    to branch on whether this particular day happened to compose.
    """
    if index >= len(exercises or []):
        return {}
    exercise = exercises[index]
    return {
        "text_i18n": exercise.get("text") or {},
        "theme": exercise.get("theme") or "",
        "slot": exercise.get("slot") or "",
        "tier": exercise.get("tier") or "",
        "field_name": exercise.get("field") or "",
        "current": exercise.get("current"),
        "target": exercise.get("target"),
    }


def _recent_history(account: Account, storage: StorageBackend | None) -> list[dict]:
    """This user's recent stored days, newest last.

    Returned empty rather than raising if anything about storage is
    unavailable: the plan is still perfectly valid built from the
    submitted day alone (that is exactly what it did before personal
    baselines existed), and a history read failing is not a reason to
    deny someone their plan.
    """
    try:
        service = get_history_service(account, storage=storage)
        return list(service.get_all())[-PERSONAL_BASELINE_DAYS:]
    except Exception:
        return []


# How far back a personal baseline looks. Long enough that a median is
# meaningful, short enough that it tracks who the user is now rather
# than who they were two months ago.
PERSONAL_BASELINE_DAYS = 21


def _week_scores(
    history: list[dict], week_key: str,
    exception_dates: set[str] | None = None,
) -> tuple[list[float], list[float], list[dict]]:
    """This week's real scores, how much each one counts, and their rows.

    Days the user excluded outright are dropped - that control means
    "this is not my data". A day marked as an EXCEPTION is different and
    is deliberately not the same thing: it happened, it stays visible,
    and it still moves the band, just at EXCEPTION_WEIGHT of a normal
    day. Erasing it would let a week be curated into a straight line;
    counting it in full is exactly what the user said it should not do.

    The rows are returned alongside because the band's WIDTH is now a
    prediction (services/ml/band_model_service) and reads the sleep,
    screen and stress fields those rows carry. They are the same days in
    the same order as the scores, so the two lists index together - the
    band's centre still comes from the scores and the weights alone.
    """
    exception_dates = exception_dates or set()
    scores: list[float] = []
    weights: list[float] = []
    rows: list[dict] = []
    for row in history or []:
        if not row or row.get("excluded"):
            continue
        date_str = row.get("date")
        score = row.get("health_score")
        if not date_str or not isinstance(score, (int, float)) or isinstance(score, bool):
            continue
        try:
            if current_week_key(date.fromisoformat(date_str)) == week_key:
                scores.append(float(score))
                weights.append(EXCEPTION_WEIGHT if date_str in exception_dates else 1.0)
                rows.append(row)
        except (TypeError, ValueError):
            continue
    return scores, weights, rows


def _scores_before(history: list[dict], week_key: str) -> list[float]:
    """Every score this user logged BEFORE the given week, oldest first.

    The band's WIDTH is a prediction, and until it could see these it
    was drawn from the days since Monday alone. Measured on held-out
    respondents, that left the most volatile third covered 84% of the
    time against a 90% promise, at every prefix length - because three
    days into a week a volatile person and a steady one look the same.
    The evidence that separates them is here.

    Excluded days are dropped for the same reason they are dropped from
    the band's centre: that control means "this is not my data".
    """
    prior: list[float] = []
    for row in history or []:
        if not row or row.get("excluded"):
            continue
        date_str, score = row.get("date"), row.get("health_score")
        if not date_str or not isinstance(score, (int, float)) or isinstance(score, bool):
            continue
        try:
            if current_week_key(date.fromisoformat(date_str)) < week_key:
                prior.append(float(score))
        except (TypeError, ValueError):
            continue
    return prior


def _snapshot_of(plan: ImprovementPlan) -> dict:
    """The plan as plain data, for storing.

    Written out field by field rather than with asdict(): DailyPlan is a
    slots dataclass and the shape stored here is a wire format that has
    to stay readable by an older build, so it should change only when
    someone means to change it.
    """
    return {
        "intro": plan.intro,
        "focus_areas": list(plan.focus_areas),
        "text_i18n": plan.text_i18n,
        "focus_areas_i18n": plan.focus_areas_i18n,
        "days": [
            {
                "day_number": d.day_number, "day_label": d.day_label,
                "theme": d.theme, "icon": d.icon, "tasks": list(d.tasks),
                "tip": d.tip, "tier_label": d.tier_label,
                "exercises": d.exercises, "text_i18n": d.text_i18n,
            }
            for d in plan.days
        ],
    }


def _plan_from_snapshot(data: dict) -> ImprovementPlan:
    """Rebuild a stored snapshot into the same object generate() returns."""
    return ImprovementPlan(
        intro=data.get("intro", ""),
        focus_areas=list(data.get("focus_areas") or []),
        text_i18n=data.get("text_i18n") or {},
        focus_areas_i18n=list(data.get("focus_areas_i18n") or []),
        days=[
            DailyPlan(
                day_number=d.get("day_number", 0), day_label=d.get("day_label", ""),
                theme=d.get("theme", ""), icon=d.get("icon", ""),
                tasks=list(d.get("tasks") or []), tip=d.get("tip", ""),
                tier_label=d.get("tier_label", ""),
                exercises=list(d.get("exercises") or []),
                text_i18n=d.get("text_i18n") or {},
            )
            for d in (data.get("days") or [])
        ],
    )

def _revocable_badge_ids(account: Account, storage: StorageBackend | None) -> list[str]:
    """The user's currently-earned public achievement badges.

    Private awareness indicators are never touched: those name a
    pattern worth a look, not something the user won, so "spending" one
    as a penalty would be meaningless. Read fresh rather than cached -
    badges are derived from the user's own check-ins on every call, so
    there is nothing to cache.
    """
    try:
        entries = get_history_service(account, storage=storage).get_all()
        badges = BadgeService.evaluate(entries)
        return [
            b.id for b in badges
            if b.earned and not getattr(b, "private", False)
            and getattr(b, "category", "") == "achievement"
        ]
    except Exception:  # noqa: BLE001 - a badge read must never break the plan
        return []


def _assess_missed_days(
    account: Account,
    violation_service: ViolationService,
    plan: ImprovementPlan,
    completed: set[tuple[int, int]],
    week_key: str,
    generated_on: str | None,
    storage: StorageBackend | None = None,
) -> None:
    """Charge for plan days whose date has passed with the day undone.

    Only ever backwards, and only once per day - `assess_day` is
    idempotent per (week, day), so opening the app three times on
    Thursday cannot cost three badges for the same Wednesday. TODAY is
    never assessed: the day is not over, and penalising someone at
    breakfast for a day they have not finished living would be simply
    wrong.
    """
    if not generated_on:
        # No recorded start date means no way to know which calendar day
        # a plan day was. Being unsure is a reason to charge nobody.
        return

    today = date.today().isoformat()
    revocable = None
    for day in plan.days:
        day_date = plan_day_date(generated_on, day.day_number)
        if not day_date or day_date >= today:
            continue
        total = len(day.tasks)
        if total == 0:
            continue
        done = sum(1 for (d, _t) in completed if d == day.day_number)
        if done >= total:
            continue
        if revocable is None:
            revocable = _revocable_badge_ids(account, storage)
        penalty = violation_service.assess_day(
            week_key, day.day_number, day_date, revocable,
        )
        if penalty == "badge_revoked" and revocable:
            # One badge per missed day; the next miss spends the next
            # one rather than the same one twice.
            revocable = revocable[1:]


# The three stores that hang off the weekly plan. Their backend comes
# from get_plan_side_storage_backend, which is deliberately NOT the
# history one: HistoryService selects its records by user_id alone, so
# sharing a backend would make a stored plan snapshot show up as a
# check-in - a day with no date and no score sitting in somebody's
# history. None is the production path and lands each service on its
# own DEFAULT_STORAGE_PATH, unchanged.
def _lock_service(account: Account, storage: StorageBackend | None) -> PlanLockService:
    return PlanLockService(account.user_id, backend=storage) if storage else PlanLockService(account.user_id)


def _decision_service(account: Account, storage: StorageBackend | None) -> DayDecisionService:
    return DayDecisionService(account.user_id, backend=storage) if storage else DayDecisionService(account.user_id)


def _violation_service(account: Account, storage: StorageBackend | None) -> ViolationService:
    return ViolationService(account.user_id, backend=storage) if storage else ViolationService(account.user_id)


router = APIRouter(prefix="/plan", tags=["Weekly Plan"])


@router.post(
    "", response_model=PlanResponse,
    summary="Generate this week's rule-based 7-day improvement plan from a real prediction's outputs, with saved checkmarks merged in",
)
def generate_plan(
    payload: PlanGenerateRequest,
    account: Account = Depends(get_current_account),
    plan_service: ImprovementPlanService = Depends(get_improvement_plan_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> PlanResponse:
    # The plan used to be built from the single submitted day alone. It
    # now also gets this user's own recent history and their onboarding
    # schedule type, so a signal can be flagged for slipping from their
    # personal baseline (not only for crossing a fixed threshold) and
    # routine-anchored themes outrank screen rules for someone whose
    # days are not alike. Both are read here rather than asked of the
    # client: the browser's localStorage is not a trustworthy source for
    # either, and a user on a second device has neither.
    history = _recent_history(account, storage)
    week_key = current_week_key()
    lock_service = _lock_service(account, side)

    # Days the user called unusual. They still move the band, at
    # EXCEPTION_WEIGHT of a normal day - see day_decision_service.
    decision_service = _decision_service(account, side)
    exception_dates = decision_service.exception_dates(week_key)

    # The week is now the unit it claims to be. A plan is generated
    # once and served back unchanged for the rest of the ISO week;
    # regenerating is an explicit request, never a side effect of
    # opening the page. Two check-ins on one day used to produce two
    # completely different plans under the same week key, and because
    # checkmarks are stored per (day, task index) with no reference to
    # the task text, a tick then silently reappeared against a
    # different task.
    locked = None if payload.regenerate else lock_service.get(week_key)
    scores, weights, week_rows = _week_scores(history, week_key, exception_dates)
    band_low, band_high, band_half_width, band_source = week_band_detail(
        scores, weights, week_rows, prior_scores=_scores_before(history, week_key))
    generated_on = date.today().isoformat()

    if locked is not None:
        plan = _plan_from_snapshot(locked.plan)
        if locked.band_low is not None and locked.band_high is not None:
            band_low, band_high = locked.band_low, locked.band_high
            # Recomputed from the stored edges rather than reported from
            # this request's fresh prediction: the frozen band is what
            # the reader is being shown, and describing it with a width
            # it was not built from would be the same class of error as
            # showing a stale score under a fresh label. The source is
            # unknowable for a snapshot written before this field
            # existed, so it is left null rather than guessed at.
            band_half_width = round((band_high - band_low) / 2, 2)
            band_source = locked.band_source
        generated_on = (locked.created_at_utc or "")[:10] or None
    else:
        plan = plan_service.generate(
            health_class=payload.health_class,
            wellness_score=payload.wellness_score,
            persona=payload.persona,
            user_data=payload.user_data,
            history=history,
            schedule_type=getattr(account, "schedule_type", None),
            # The rest of what onboarding asked. These were stored and
            # echoed back by /progress and read by nothing, which made
            # them questions the app asks and then ignores. They re-rank
            # the user's own flagged signals - see _theme_weight - and
            # set the pace the exercises escalate at.
            main_use_purpose=getattr(account, "main_use_purpose", None),
            preferred_effort=getattr(account, "preferred_effort", None),
            work_screen_required=bool(getattr(account, "work_screen_required", False)),
            usual_sleep_time=getattr(account, "usual_sleep_time", None),
            usual_wake_time=getattr(account, "usual_wake_time", None),
            # Week two onward continues where the user actually got to.
            # A theme they have already spent two weeks on opens at the
            # tier they reached, not at "set a fixed bedtime" for a
            # third time.
            theme_streaks=lock_service.theme_streaks(week_key),
        )
        lock_service.save(
            _snapshot_of(plan), week_key,
            band_low=band_low, band_high=band_high, band_source=band_source,
        )

    progress_service = get_plan_progress_service(account, storage=storage)
    if payload.regenerate and locked is None:
        # The tasks those ticks referred to no longer exist. Clearing is
        # the honest option - carrying them over is exactly the silent
        # corruption this lock was introduced to stop.
        progress_service.clear_week(week_key)
    completed = progress_service.get_completed(week_key)

    # The week is a sequence, not a menu: day N+1 opens once day N is
    # fully ticked AND its own date has arrived. Assessed here as well as
    # enforced on PUT /plan/tasks, so the UI can show a locked day as
    # locked instead of letting someone tick it and be refused.
    tasks_per_day = {d.day_number: len(d.tasks) for d in plan.days}
    open_through = unlocked_through(completed, tasks_per_day, generated_on=generated_on)
    # The sequence gate on its own, so a locked day can say which of the
    # two gates is holding it. When the sequence would have opened the
    # day and only the calendar has not, the honest message is "comes
    # back tomorrow", not "finish the day you already finished".
    by_sequence = unlocked_through(completed, tasks_per_day)

    def _lock_reason(day_number: int) -> str | None:
        if day_number <= open_through:
            return None
        return "calendar" if day_number <= by_sequence else "sequence"

    violation_service = _violation_service(account, side)
    _assess_missed_days(
        account, violation_service, plan, completed, week_key, generated_on,
        storage=storage,
    )
    state = violation_service.state()

    return PlanResponse(
        week_key=week_key,
        band_low=band_low,
        band_high=band_high,
        band_half_width=band_half_width,
        band_source=band_source,
        generated_on=generated_on,
        unlocked_through=open_through,
        missed_days=state.missed_days,
        open_violations=state.open_violations,
        revoked_badges=state.revoked_badge_ids,
        intro=plan.intro,
        focus_areas=plan.focus_areas,
        text_i18n=plan.text_i18n,
        focus_areas_i18n=plan.focus_areas_i18n,
        days=[
            PlanDayResponse(
                day_number=day.day_number, day_label=day.day_label, theme=day.theme,
                icon=day.icon, tip=day.tip, tier_label=day.tier_label,
                text_i18n=day.text_i18n,
                # Zipped against `exercises` rather than replaced by it:
                # `tasks` is what carries completion state, so the two
                # must stay index-aligned. A day whose exercises failed
                # to compose still yields its English tasks.
                tasks=[
                    PlanTaskResponse(
                        task_index=i, text=task,
                        completed=(day.day_number, i) in completed,
                        **_exercise_fields(day.exercises, i),
                    )
                    for i, task in enumerate(day.tasks)
                ],
                locked=day.day_number > open_through,
                lock_reason=_lock_reason(day.day_number),
                day_date=plan_day_date(generated_on, day.day_number),
            )
            for day in plan.days
        ],
    )


def _week_rows(history: list[dict], week_key: str) -> list[dict]:
    """This week's stored days, oldest first."""
    rows = []
    for row in history or []:
        date_str = (row or {}).get("date")
        if not date_str:
            continue
        try:
            if current_week_key(date.fromisoformat(date_str)) == week_key:
                rows.append(row)
        except (TypeError, ValueError):
            continue
    return sorted(rows, key=lambda r: r.get("date") or "")


@router.get(
    "/tracks", response_model=SignalTracksResponse,
    summary="The two halves of this week's plan: signals to strengthen, and the ones already worth protecting",
)
def get_signal_tracks(
    account: Account = Depends(get_current_account),
    plan_service: ImprovementPlanService = Depends(get_improvement_plan_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> SignalTracksResponse:
    """What the week is working on, and what it is protecting.

    Read from the user's most recent stored check-in rather than from
    anything the client sends: this is what the coach answers "what
    should I strengthen?" and "what am I already doing well?" with, and
    those answers have to be about the user's real logged day, not
    about whatever happens to be in that browser's localStorage.

    An account with nothing logged gets two empty lists. That is the
    honest answer - inventing generic advice about signals nobody has
    measured is exactly what this whole feature is not.
    """
    history = _recent_history(account, storage)
    latest = history[-1] if history else {}

    try:
        inputs, _ = replay(latest) if latest else (None, None)
        user_data = dict(inputs.cleaned_data) if inputs else {}
    except SnapshotUnavailableError:
        # Days recorded before snapshots existed still carry the tracked
        # summary fields, which is exactly what these rules read.
        user_data = {k: v for k, v in latest.items() if isinstance(v, (int, float))}
    except Exception:  # noqa: BLE001
        user_data = {}

    week_key = current_week_key()
    exception_dates = _decision_service(account, side).exception_dates(week_key)
    scores, weights, week_rows = _week_scores(history, week_key, exception_dates)
    band_low, band_high, band_half_width, band_source = week_band_detail(
        scores, weights, week_rows, prior_scores=_scores_before(history, week_key))

    tracks = plan_service.signal_tracks(
        user_data, history=history,
        schedule_type=getattr(account, "schedule_type", None),
        # The same three answers the plan ranks by, so this panel and
        # the week's plan cannot disagree about which signal leads.
        main_use_purpose=getattr(account, "main_use_purpose", None),
        work_screen_required=bool(getattr(account, "work_screen_required", False)),
        usual_sleep_time=getattr(account, "usual_sleep_time", None),
        usual_wake_time=getattr(account, "usual_wake_time", None),
    )
    return SignalTracksResponse(
        strengthen=[SignalTrackEntry(**e) for e in tracks["strengthen"]],
        maintain=[SignalTrackEntry(**e) for e in tracks["maintain"]],
        based_on_date=latest.get("date") if latest else None,
        band_low=band_low,
        band_high=band_high,
        band_half_width=band_half_width,
        band_source=band_source,
    )


@router.get(
    "/day-status", response_model=PlanDayStatusResponse,
    summary="Whether today fell outside this week's score band and still needs a decision",
)
def get_day_status(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> PlanDayStatusResponse:
    """Does the app need to ask about today?

    Only from the SECOND logged day of a week onward. On the first day
    there is nothing to be outside of - the band is that day - and
    asking "was that unusual?" about the only day on record is a
    question with no meaning.

    Deliberately computed here rather than in the browser: the band, the
    day's position in the week and the score all live on the server, and
    a client that got any one of them wrong would either nag a user
    about an ordinary day or quietly skip a real one.
    """
    history = _recent_history(account, storage)
    week_key = current_week_key()
    rows = _week_rows(history, week_key)

    decision_service = _decision_service(account, side)
    exception_dates = decision_service.exception_dates(week_key)

    today = date.today().isoformat()
    today_row = next((r for r in rows if r.get("date") == today), None)
    day_number = next(
        (i + 1 for i, r in enumerate(rows) if r.get("date") == today), len(rows) + 1,
    )

    # The band the day is judged against excludes the day itself -
    # otherwise a single wild number drags the range toward itself and
    # then reports that it fits comfortably inside it. With one day on
    # record and today being the second, this is that first day, which
    # is exactly what "outside the range you have been running at"
    # should mean.
    prior_scores, prior_weights, prior_rows = _week_scores(
        [r for r in rows if r.get("date") != today], week_key, exception_dates,
    )
    band_low, band_high, band_half_width, band_source = week_band_detail(
        prior_scores, prior_weights, prior_rows,
        prior_scores=_scores_before(rows, week_key))

    score = today_row.get("health_score") if today_row else None
    existing = decision_service.get(today)
    needs = (
        today_row is not None
        and day_number >= 2
        and existing is None
        and is_outside_band(score, band_low, band_high)
    )

    return PlanDayStatusResponse(
        date=today,
        week_key=week_key,
        day_number=day_number,
        score=score,
        band_low=band_low,
        band_high=band_high,
        band_half_width=band_half_width,
        band_source=band_source,
        outside_band=is_outside_band(score, band_low, band_high),
        needs_decision=needs,
        decision=existing.decision if existing else None,
        exception_days=sorted(exception_dates),
        exception_weight=EXCEPTION_WEIGHT,
    )


@router.post(
    "/day-decision", response_model=PlanDayStatusResponse,
    summary="Record whether an out-of-band day was an exception or should count",
)
def record_day_decision(
    payload: PlanDayDecisionRequest,
    account: Account = Depends(get_current_account),
    plan_service: ImprovementPlanService = Depends(get_improvement_plan_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> PlanDayStatusResponse:
    """Apply the user's answer about an out-of-band day.

    EXCEPTION leaves the plan exactly as it is. That is the point of the
    option, and it is why the day is not deleted either: it keeps its
    place in history and on the dashboard and still counts toward the
    band, at EXCEPTION_WEIGHT.

    COUNTED rewrites the REST of the week against the new band. Days
    already lived through keep their tasks - and therefore keep their
    checkmarks - because a tick records something the user actually did
    and must not be swept away by a decision about a later day.
    """
    if payload.decision not in (EXCEPTION, COUNTED):
        raise BadRequestError(
            f"decision must be '{EXCEPTION}' or '{COUNTED}'.",
            error_code="invalid_day_decision",
        )

    history = _recent_history(account, storage)
    week_key = current_week_key()
    rows = _week_rows(history, week_key)
    day = payload.date or date.today().isoformat()

    row = next((r for r in rows if r.get("date") == day), None)
    if row is None:
        raise NotFoundError(
            f"No check-in recorded for {day} this week.",
            error_code="history_entry_not_found",
        )
    day_number = next(i + 1 for i, r in enumerate(rows) if r.get("date") == day)

    decision_service = _decision_service(account, side)
    decision_service.save(
        day, payload.decision, week_key=week_key,
        score=row.get("health_score"),
    )

    exception_dates = decision_service.exception_dates(week_key)
    scores, weights, week_rows = _week_scores(history, week_key, exception_dates)
    band_low, band_high, band_half_width, band_source = week_band_detail(
        scores, weights, week_rows, prior_scores=_scores_before(history, week_key))

    lock_service = _lock_service(account, side)
    progress_service = get_plan_progress_service(account, storage=storage)

    if payload.decision == COUNTED:
        locked = lock_service.get(week_key)
        rebuilt = plan_service.generate(
            health_class=row.get("health_class"),
            wellness_score=row.get("health_score"),
            persona=row.get("persona"),
            user_data=payload.user_data or {},
            history=history,
            schedule_type=getattr(account, "schedule_type", None),
            # The rest of what onboarding asked. These were stored and
            # echoed back by /progress and read by nothing, which made
            # them questions the app asks and then ignores. They re-rank
            # the user's own flagged signals - see _theme_weight - and
            # set the pace the exercises escalate at.
            main_use_purpose=getattr(account, "main_use_purpose", None),
            preferred_effort=getattr(account, "preferred_effort", None),
            work_screen_required=bool(getattr(account, "work_screen_required", False)),
            usual_sleep_time=getattr(account, "usual_sleep_time", None),
            usual_wake_time=getattr(account, "usual_wake_time", None),
            # Same continuation the week opened with. Rebuilding the
            # rest of the week must not quietly demote a theme the user
            # has been on for a month back to its gentlest tier.
            theme_streaks=lock_service.theme_streaks(week_key),
        )
        merged = _snapshot_of(rebuilt)
        if locked is not None:
            kept = [d for d in (locked.plan.get("days") or []) if d.get("day_number", 0) < day_number]
            fresh = [d for d in merged["days"] if d.get("day_number", 0) >= day_number]
            merged["days"] = kept + fresh
            # The focus areas the week opened with stay on the record
            # alongside the new ones, so the plan does not silently
            # rewrite what the user was told they were working on.
            merged["focus_areas"] = list(
                dict.fromkeys(list(locked.plan.get("focus_areas") or []) + merged["focus_areas"])
            )
        lock_service.save(
            merged, week_key,
            band_low=band_low, band_high=band_high, band_source=band_source,
        )
        progress_service.clear_days_from(day_number, week_key)

    return PlanDayStatusResponse(
        date=day,
        week_key=week_key,
        day_number=day_number,
        score=row.get("health_score"),
        band_low=band_low,
        band_high=band_high,
        band_half_width=band_half_width,
        band_source=band_source,
        outside_band=is_outside_band(row.get("health_score"), band_low, band_high),
        needs_decision=False,
        decision=payload.decision,
        exception_days=sorted(exception_dates),
        exception_weight=EXCEPTION_WEIGHT,
    )


@router.put(
    "/tasks", response_model=dict,
    summary="Mark one plan task done/not-done for the authenticated user's current week",
)
def update_task(
    payload: PlanTaskUpdateRequest,
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> dict:
    progress_service: PlanProgressService = get_plan_progress_service(account, storage=storage)
    week_key = current_week_key()

    # Day N+1 stays shut until day N is fully done. Enforced here and
    # not only in the UI: a locked day that a direct request can tick
    # anyway is not locked, and the whole point of the sequence is that
    # "you missed a day" means something.
    #
    # Only ticking ON is gated. Un-ticking a day that is already open
    # has to stay possible, or a mis-tap on the last task of a day would
    # permanently open the next one with no way back.
    if payload.completed:
        locked = _lock_service(account, side).get(week_key)
        if locked is not None:
            tasks_per_day = {
                int(d.get("day_number") or 0): len(d.get("tasks") or [])
                for d in (locked.plan.get("days") or [])
            }
            open_through = unlocked_through(
                progress_service.get_completed(week_key), tasks_per_day,
                # The same calendar gate GET /plan applies, and applied
                # from the same field, so a day the UI shows as locked
                # is a day a direct PUT is refused. A gate that only
                # exists in the browser is not a gate.
                generated_on=(locked.created_at_utc or "")[:10] or None,
            )
            if payload.day_number > open_through:
                raise DayLockedError(payload.day_number, open_through)

    progress_service.set_completed(payload.day_number, payload.task_index, payload.completed)
    return {"ok": True}


@router.get(
    "/weeks", response_model=PlanWeeksResponse,
    summary="Every week this user has a stored plan for, oldest first",
)
def list_plan_weeks(
    account: Account = Depends(get_current_account),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> PlanWeeksResponse:
    """The week menu's contents.

    A plan snapshot has always been written once per ISO week - a 23-day
    demo leaves four of them - but nothing could list them, so the weekly
    page could only ever render the current week and every earlier one
    was unreachable. This reports what is actually stored; it does not
    generate a plan for a week that never had one.
    """
    locks = PlanLockService(account.user_id, backend=side)
    progress = PlanProgressService(account.user_id, backend=side)
    this_week = current_week_key()

    summaries: list[PlanWeekSummary] = []
    for index, week_key in enumerate(locks.weeks()):
        locked = locks.get(week_key)
        if locked is None:
            # An unparseable snapshot is treated as absent everywhere
            # else in this service; listing it would offer a menu entry
            # that opens onto nothing.
            continue
        days = locked.plan.get("days") or []
        total_tasks = sum(len(day.get("tasks") or []) for day in days)
        summaries.append(PlanWeekSummary(
            week_key=week_key,
            index=index,
            day_count=len(days),
            completed_tasks=len(progress.get_completed(week_key)),
            total_tasks=total_tasks,
            is_current=week_key == this_week,
        ))

    return PlanWeeksResponse(weeks=summaries, current_week_key=this_week)


@router.get(
    "/weeks/{week_key}", response_model=PlanResponse,
    summary="A stored plan for one specific week, with that week's checkmarks merged in",
)
def get_plan_week(
    week_key: str,
    account: Account = Depends(get_current_account),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> PlanResponse:
    """Read-only. Opening an earlier week must not regenerate it, move
    the current week on, or charge anything for days already assessed -
    so this deliberately skips the generate/assess path that POST /plan
    runs and only reads what was stored."""
    locks = PlanLockService(account.user_id, backend=side)
    locked = locks.get(week_key)
    if locked is None:
        raise NotFoundError(f"No stored plan for week {week_key}.")

    plan = _plan_from_snapshot(locked.plan)
    completed = PlanProgressService(account.user_id, backend=side).get_completed(week_key)

    # A finished week has every day open: the calendar gate that keeps
    # day N+1 shut until day N+1 arrives is about the week being lived
    # now, and applying it to a week already past would hide days the
    # user actually completed.
    open_through = len(plan.days)
    generated_on = locked.created_at_utc[:10] if locked.created_at_utc else None

    return PlanResponse(
        week_key=week_key,
        band_low=locked.band_low,
        band_high=locked.band_high,
        band_half_width=(
            round((locked.band_high - locked.band_low) / 2, 2)
            if locked.band_low is not None and locked.band_high is not None else None
        ),
        band_source=locked.band_source,
        generated_on=generated_on,
        unlocked_through=open_through,
        # Violation state is live and belongs to the week being lived,
        # not to a week being read back, so it is reported as empty here
        # rather than recomputed against a past week's dates.
        missed_days=0,
        open_violations=0,
        revoked_badges=[],
        intro=plan.intro,
        focus_areas=plan.focus_areas,
        text_i18n=plan.text_i18n,
        focus_areas_i18n=plan.focus_areas_i18n,
        days=[
            PlanDayResponse(
                day_number=day.day_number, day_label=day.day_label, theme=day.theme,
                icon=day.icon, tip=day.tip, tier_label=day.tier_label,
                text_i18n=day.text_i18n,
                tasks=[
                    PlanTaskResponse(
                        task_index=i, text=task,
                        completed=(day.day_number, i) in completed,
                        **_exercise_fields(day.exercises, i),
                    )
                    for i, task in enumerate(day.tasks)
                ],
                locked=False,
                lock_reason=None,
                day_date=plan_day_date(generated_on, day.day_number),
            )
            for day in plan.days
        ],
    )
