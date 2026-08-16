"""
api/routers/demo.py
----------------------
Demo Mode: one endpoint that populates 23 real days of history (real
model scores on a synthetic-but-plausible trajectory) plus one demo
League friend, so every feature has something to show without a
presenter manually logging real days first. See services/demo/demo_service.py
for exactly what is and isn't fabricated.
"""

from __future__ import annotations

from datetime import date, timedelta

import logging

import secrets
import uuid

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_improvement_plan_service,
    get_plan_progress_service,
    get_account_service,
    get_history_service,
    get_history_storage_backend,
    get_prediction_service,
    get_recommendation_service,
    get_validation_service,
)
from api.exceptions.errors import BadRequestError
from api.routers.auth import _issue_session
from api.routers.prediction import build_predict_response, recent_scores_from
from api.schemas.demo import (
    DemoCatalogueResponse,
    DemoPopulateResponse,
    DemoSessionRequest,
    DemoSessionResponse,
)
from services.identity.account_service import Account, AccountService
from services.demo.demo_service import (
    DEMO_BOT_USER_ID_PREFIX,
    DEMO_PROFILES,
    DemoService,
    demo_display_name,
    demo_email,
)
from services.identity.history_service import HistoryService
from services.identity.journal_service import JournalService
from services.identity.personal_service import PersonalService
from services.identity.refresh_token_service import RefreshTokenService
from services.social.league_chat_service import LeagueChatService
from services.social.league_service import LeagueService
from services.ml.prediction_service import PredictionService
from services.wellness.recommendation_service import RecommendationService
from services.wellness.plan_lock_service import PlanLockService
from services.wellness.plan_progress_service import PlanProgressService
from services.wellness.improvement_plan_service import ImprovementPlanService
from services.storage.base import StorageBackend
from services.wellness.violation_service import ViolationService
from services.ml.validation_service import ValidationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Demo Mode"])


def _purge_demo_account(
    account_service: AccountService, storage: StorageBackend | None, user_id: str,
) -> None:
    """Removes a demo account and every trace it may have created:
    its own history, any bot friends' histories, and every League
    connection/profile/chat record either side ever touched. The account
    row goes last (see end_demo_session below for why).

    Shared by two callers - the failure path in start_demo_session() and
    the DELETE /demo/session endpoint - so a demo that fails partway
    through population (friends are connected before the days loop can
    report failure - see DemoService.populate) is cleaned up exactly as
    thoroughly as one a caller explicitly ends.
    """
    league_service = LeagueService()
    chat_service = LeagueChatService()

    # Bot friends (services/demo/demo_service.py) are not real accounts - they
    # exist only as history rows and League records under a
    # "demo_bot_..." id. They are only discoverable through the demo
    # account's own connections, so read those before delete_user_data()
    # below removes them.
    league_result = league_service.delete_user_data(user_id)
    bot_ids = [
        other_id for other_id in league_result["other_user_ids"]
        if other_id.startswith(DEMO_BOT_USER_ID_PREFIX)
    ]

    chat_service.delete_user_data(user_id)
    # Same single-pass delete as _reset_demo_data below, for the same
    # reason: eleven full rewrites of the whole history file is what
    # made leaving a ten-friend demo slow.
    HistoryService(user_id=user_id, storage=storage).delete_users([user_id, *bot_ids])
    # The demo's book. Bots never write one, but they are included for
    # the same reason they are above: the set is "everything this demo
    # created", and a store that is cleaned by id cannot be harmed by
    # an id that has nothing in it.
    JournalService(user_id).delete_users([user_id, *bot_ids])
    PersonalService(user_id).delete_users([user_id, *bot_ids])
    # A demo account's sessions go with it. Leaving a live refresh token
    # behind for an account that has been deleted is how a "temporary"
    # demo turns into a thirty-day credential nobody remembers issuing.
    RefreshTokenService(user_id).delete_users([user_id, *bot_ids])
    for bot_id in bot_ids:
        league_service.delete_user_data(bot_id)  # the bot's own now-orphaned profile row

    account_service.delete_account(user_id)


def _reset_demo_data(
    account_service: AccountService, storage: StorageBackend | None, user_id: str,
) -> None:
    """Empty a demo account without deleting the account itself.

    The account address IS the demo's identity - one fixed account per
    state - so it has to survive a rebuild. Everything hanging off it
    does not: history, league records, chats, the frozen weekly plan,
    the per-week checkmarks and the violation ledger all describe the
    previous build and would otherwise accumulate across runs, which is
    how a "3-day demo" ends up with three weeks of plan progress.
    """
    league_service = LeagueService()
    chat_service = LeagueChatService()

    league_result = league_service.delete_user_data(user_id)
    bot_ids = [
        other_id for other_id in league_result["other_user_ids"]
        if other_id.startswith(DEMO_BOT_USER_ID_PREFIX)
    ]
    chat_service.delete_user_data(user_id)
    # One locked pass over the history file for the demo user AND every
    # bot, instead of one per user. With ten friends that was eleven
    # full rewrites of a file holding every account's history - a cost
    # invisible on a fresh install and growing with total rows, which is
    # why the demo eventually timed out the more the app was used.
    HistoryService(user_id=user_id, storage=storage).delete_users([user_id, *bot_ids])
    # Rebuilt from scratch below, so last run's pages have to go first -
    # otherwise a 3-day demo opens with a book still holding the
    # twenty-three pages of the 23-day one.
    JournalService(user_id).delete_users([user_id, *bot_ids])
    for bot_id in bot_ids:
        league_service.delete_user_data(bot_id)

    # The three plan-side stores. Each is per-user, so clearing here
    # leaves every other account untouched.
    try:
        PlanLockService(user_id).clear_all()
        PlanProgressService(user_id).clear_all()
        ViolationService(user_id).clear_all()
    except Exception:  # noqa: BLE001 - a stale ledger must not block a demo
        logger.warning("Could not fully reset demo plan data for %s.", user_id, exc_info=True)


def _advance_demo_plan(
    demo_account: Account,
    storage: StorageBackend | None,
    plan_service: ImprovementPlanService,
    history: list[dict],
    final_inputs: dict,
    final_result,
    with_violations: bool,
) -> tuple[int, int]:
    """Put the demo user where their own history says they should be.

    A demo used to hand a reviewer a 23-day history attached to a weekly
    plan sitting untouched on day 1, so every plan feature - the day
    sequence, the ticks, the tier that carries across weeks, the
    violation ledger - was invisible however long the demo was.

    The plan is weekly, so a 23-day user is not "on day 23 of one plan";
    they are three weeks done and part-way through a fourth. That is
    what this builds: a stored plan for EVERY ISO week their history
    touches, each dated to its own Monday, with every day before today
    ticked. The reviewer opening the weekly page sees a user who has
    genuinely been doing this for three weeks, and the week-2-onward
    progression (which starts a carried theme at the tier already
    reached) has real previous weeks to read.

    A LAPSED user is walked differently: days they never logged are left
    undone. The ordinary violation ledger then charges for them through
    the same code path a real user hits - nothing here writes a
    violation directly.

    Returns (day within the current week, total plan days ticked).
    """
    from services.wellness.plan_lock_service import PlanLockService, week_band_detail
    from services.wellness.plan_progress_service import current_week_key
    from services.wellness.violation_service import ViolationService, plan_day_date

    lock_service = PlanLockService(demo_account.user_id)
    progress_service = get_plan_progress_service(demo_account, storage=storage)
    violation_service = ViolationService(demo_account.user_id)

    dated = sorted(e for e in (r.get("date") for r in history) if e)
    if not dated:
        return 1, 0
    logged_dates = set(dated)
    first_day = date.fromisoformat(dated[0])
    today = date.today()

    # Every ISO week the history touches, oldest first, each anchored to
    # its own Monday so a plan day maps onto the calendar day it really
    # was.
    weeks: list[date] = []
    cursor = first_day - timedelta(days=first_day.weekday())
    while cursor <= today:
        weeks.append(cursor)
        cursor += timedelta(days=7)

    total_done = 0
    plan_day_now = 1

    for monday in weeks:
        week_key = current_week_key(monday)
        window = [
            r for r in history
            if r.get("date") and monday <= date.fromisoformat(r["date"]) < monday + timedelta(days=7)
        ]
        if not window:
            continue

        # Built from that week's OWN last day, so an improving user's
        # early weeks carry the plan they would actually have been
        # given then - not the one their final day earns.
        anchor = window[-1]
        # Rows kept beside the scores so the seeded band is the same
        # personal one a real account gets: the width comes from the
        # band model, which reads these rows' sleep/screen/stress
        # fields. Seeding a demo with the fallback constant while live
        # users get a predicted width would make the demo a different
        # product from the one it is demonstrating.
        counted = [
            r for r in window
            if isinstance(r.get("health_score"), (int, float)) and not isinstance(r.get("health_score"), bool)
        ]
        scores = [r["health_score"] for r in counted]
        low, high, _, band_source = week_band_detail(scores, None, counted)

        plan = plan_service.generate(
            health_class=anchor.get("health_class"),
            wellness_score=anchor.get("health_score"),
            persona=None,
            user_data=final_inputs if monday == weeks[-1] else _inputs_for(anchor, final_inputs),
            history=window,
            schedule_type=getattr(demo_account, "schedule_type", None),
            theme_streaks=lock_service.theme_streaks(week_key),
        )
        lock_service.save(
            _snapshot_of_plan(plan), week_key,
            band_low=low, band_high=high, band_source=band_source,
        )
        _restamp_plan(lock_service, week_key, monday)

        # Collected and written once - one locked write per week rather
        # than one per task. Seventy locked rewrites of the whole
        # progress file is what made bulk population time out before.
        # Ticks have to form an unbroken PREFIX of the week, because that
        # is the rule the plan itself enforces: day N+1 only opens once
        # day N is fully done (services/wellness/violation_service.py::
        # unlocked_through). Skipping a lapsed user's missed day and
        # carrying on ticking produced exactly the incoherence you would
        # expect - measured on the running app, a 15-day lapsed demo
        # rendered day 2 undone with days 3 and 4 fully ticked AND shown
        # as locked. A locked day with every box ticked is not a state
        # the app can reach on its own, and it reads as broken.
        #
        # So a lapse is expressed the way a real one looks: the days they
        # did not log are the days that are not ticked. The ledger below
        # still charges for every missed calendar day, so nothing is
        # forgiven - it is only the checkmarks that stay honest.
        ticks: list[tuple[int, int]] = []
        for day in plan.days:
            when_str = plan_day_date(monday.isoformat(), day.day_number)
            if not when_str:
                continue
            when = date.fromisoformat(when_str)
            if when > today:
                continue
            # Before this user existed. A 3-day demo starting on a
            # Thursday was having Monday, Tuesday and Wednesday ticked
            # off for it - three days of exercises marked done by
            # somebody whose first check-in is on the Thursday. Every
            # demo length looked identical for exactly this reason: the
            # week was filled in regardless of how much of it the demo
            # actually covers. The plan now starts where the user does.
            if when < first_day:
                continue
            if when == today:
                plan_day_now = day.day_number
                continue  # today stays open - it is not over
            # A lapsed user did not do the work on the days they did not
            # log. That is what turns a day red rather than merely grey.
            #
            # It used to stop the week: the first unlogged day latched a
            # flag and every later day stayed untouched, so a 23-day
            # lapsed demo came back with 24 of its 28 plan days non-green
            # - a person who missed one Tuesday shown as having done
            # nothing since. A miss is a miss for that day only; the days
            # they did log afterwards are days they turned up for.
            # Measured after this change: 8 non-green of 28, against 6
            # for the same demo without violations.
            if with_violations and when_str not in logged_dates:
                continue
            ticks.extend((day.day_number, i) for i in range(len(day.tasks)))
            total_done += 1
        if ticks:
            progress_service.set_many_completed(ticks, week_key)

        # The ledger charges for the days this week that went by undone,
        # through the ordinary assessment path - the same call a real
        # user's plan page makes. The user's actually-earned badges are
        # offered as payment, exactly as they are in real life, so a
        # lapsed demo shows what lapsing costs: badges spent down and
        # violations left over once there are none, rather than a
        # pristine badge wall next to a violation count.
        if with_violations:
            spendable = _revocable_badges(demo_account, storage)
            for day in plan.days:
                when_str = plan_day_date(monday.isoformat(), day.day_number)
                if not when_str or when_str >= today.isoformat():
                    continue
                if when_str in logged_dates:
                    continue
                penalty = violation_service.assess_day(
                    week_key, day.day_number, when_str, spendable,
                )
                if penalty == "badge_revoked" and spendable:
                    spendable = spendable[1:]

    return plan_day_now, total_done


def _inputs_for(row: dict, fallback: dict) -> dict:
    """That day's own answers if the snapshot kept them, else the final
    day's. Never invented: a plan built from numbers nobody entered
    would be exactly the kind of thing this app refuses to do."""
    from services.identity.history_replay_service import SnapshotUnavailableError, replay
    try:
        validation, _ = replay(row)
        return dict(validation.cleaned_data)
    except (SnapshotUnavailableError, Exception):  # noqa: BLE001
        return dict(fallback)


def _revocable_badges(account: Account, storage: StorageBackend | None) -> list[str]:
    """This account's earned public achievement badges, newest first.

    The same set api/routers/plan.py offers the ledger. Private
    awareness indicators are never included - those name a pattern
    worth a look, not something the user won.
    """
    from api.routers.plan import _revocable_badge_ids
    try:
        return list(_revocable_badge_ids(account, storage))
    except Exception:  # noqa: BLE001
        return []


def _restamp_plan(lock_service, week_key: str, start) -> None:
    """Move a stored plan's start date to `start`.

    PlanLockService stamps created_at_utc at save time, and that stamp
    is what plan_day_date() reads. For a demo the plan has to be dated
    from the user's own history instead, or a 23-day user's "day 3"
    lands on the wrong calendar day and the dashboard colours the wrong
    squares.
    """
    backend = lock_service._backend
    stamp = start.isoformat() + "T09:00:00+00:00"
    with backend.transaction() as records:
        rows = list(records)
        for row in rows:
            if row.get("user_id") == lock_service.user_id and row.get("week_key") == week_key:
                row["created_at_utc"] = stamp
        backend.commit(rows)


def _snapshot_of_plan(plan) -> dict:
    """Same wire shape api/routers/plan.py stores, reused rather than
    re-derived so a demo's stored plan is byte-comparable with a real
    one."""
    from api.routers.plan import _snapshot_of
    return _snapshot_of(plan)


@router.post(
    "/demo/populate", response_model=DemoPopulateResponse,
    summary="Populate 23 days of real-model-scored demo history plus one demo League friend",
)
def populate_demo(
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
    recommender: RecommendationService = Depends(get_recommendation_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> DemoPopulateResponse:
    history_service = get_history_service(account, storage=storage)
    demo = DemoService(history_service, validator, predictor)
    result = demo.populate(account.user_id, account.display_name or account.email)

    if result.final_prediction is None or result.final_validation is None:
        raise BadRequestError("Could not generate a valid demo day.", error_code="demo_generation_failed")

    account_service.mark_onboarding_complete(account.user_id)

    final_response = build_predict_response(
        result.final_validation, result.final_prediction, recommender, account, persisted=True,
        recent_scores=recent_scores_from(history_service.get_all(include_excluded=False)),
    )
    return DemoPopulateResponse(
        days_created=result.days_created, friend_connected=result.friend_connected,
        friends_connected=result.friends_connected, profile=result.profile,
        final_result=final_response, final_user_data=result.final_validation.cleaned_data,
    )


@router.get(
    "/demo/catalogue", response_model=DemoCatalogueResponse,
    summary="Which demo lengths and profiles exist",
)
def demo_catalogue() -> DemoCatalogueResponse:
    return DemoCatalogueResponse()


@router.post(
    "/demo/session", response_model=DemoSessionResponse,
    summary="Start a demo in its own separate account, leaving the signed-in account untouched",
)
def start_demo_session(
    payload: DemoSessionRequest,
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
    recommender: RecommendationService = Depends(get_recommendation_service),
    plan_service: ImprovementPlanService = Depends(get_improvement_plan_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> DemoSessionResponse:
    """Build a demo in a throwaway account and hand back its token.

    Demo Mode used to write its days into the caller's own account. It
    said so in a comment - "only ADDS synthetic days alongside them" -
    but that is exactly the problem: once mixed in, demo days count
    toward the user's own trends, badges and averages, and there is no
    way to separate them again. A user reported landing back on their
    real dashboard with demo data in it.

    A demo now gets its own account, its own history and its own
    friends. The caller swaps token, explores, and swaps back; nothing
    it did is visible from the real account, and deleting it removes
    every trace.
    """
    if payload.profile not in DEMO_PROFILES:
        raise BadRequestError("Unknown demo profile.", error_code="demo_unknown_profile")

    # ONE fixed account per demo state. There are thirty-two states -
    # four profiles x four lengths x with/without a lapsed record - and
    # each is a specific person who stays that person. This used to mint
    # a fresh random account on every run and seed the generator from
    # its id, so "the 23-day improving demo" was a different human with
    # different numbers each time: impossible to talk a reviewer
    # through, and impossible to check against what you saw last time.
    address = demo_email(payload.profile, payload.days, payload.with_violations)
    name = demo_display_name(payload.profile, payload.days, payload.with_violations)

    demo_account = account_service.get_by_email(address)
    if demo_account is None:
        demo_account = account_service.register(
            email=address,
            password=secrets.token_urlsafe(24),
            display_name=name,
        )
    account_service.mark_onboarding_complete(demo_account.user_id)

    history_service = get_history_service(demo_account, storage=storage)

    # Rebuilt only when it is actually stale. A demo's days are dated
    # relative to today, so one built yesterday would open showing the
    # user last logged in "yesterday" and a weekly plan a day behind.
    # Rebuilding when the newest day is not today keeps the state fixed
    # in content while staying correct in time, and makes reopening the
    # same demo on the same day instant rather than a full re-scoring.
    # Rebuilt every time, and that is not wasted work: the days are
    # dated relative to today, so a demo built yesterday would open
    # claiming the user last logged in yesterday with a weekly plan a
    # day behind. Rebuilding costs a few seconds and the generator is
    # deterministic, so the person who comes back is the same person -
    # same numbers, same story - just correctly dated.
    _reset_demo_data(account_service, storage, demo_account.user_id)
    history_service = get_history_service(demo_account, storage=storage)

    demo = DemoService(history_service, validator, predictor)
    result = demo.populate(
        demo_account.user_id, demo_account.display_name,
        days=payload.days, profile=payload.profile, friends=payload.friends,
        with_violations=payload.with_violations,
    )

    if result.final_prediction is None:
        # Leave nothing behind on a failure - a half-built demo account
        # is worse than none. Friends are connected before this check can
        # even run (see DemoService.populate), so this has to be the same
        # full cleanup as an explicit deletion, not just the account row.
        _purge_demo_account(account_service, storage, demo_account.user_id)
        raise BadRequestError("Could not generate a valid demo day.", error_code="demo_generation_failed")

    # The final day's full result, built through the SAME function a real
    # prediction uses - so the demo's Weekly Plan, Coach and What-if see
    # exactly the shape they would see for a real user, not a demo-only
    # variant that could drift from it.
    final_response = build_predict_response(
        result.final_validation, result.final_prediction, recommender, demo_account,
        excluded_categories=set(), persisted=True,
        # A demo is a person with a WEEK, and the seven-day band should
        # say so: the improving demo's band should lean up and the
        # at-risk one's down. Its own recorded days are right here.
        recent_scores=recent_scores_from(history_service.get_all(include_excluded=False)),
    )

    # The plan, walked to where this user's history says they are. A
    # 23-day demo used to hand a reviewer an untouched day 1.
    history_rows = list(history_service.get_all(include_excluded=True))
    try:
        plan_day, plan_done = _advance_demo_plan(
            demo_account, storage, plan_service, history_rows,
            dict(result.final_validation.cleaned_data), result.final_prediction,
            payload.with_violations,
        )
    except Exception:  # noqa: BLE001 - a demo without plan progress still works
        logger.warning("Could not advance the demo plan.", exc_info=True)
        plan_day, plan_done = 1, 0

    ledger = ViolationService(demo_account.user_id).state()

    return DemoSessionResponse(
        access_token=_issue_session(demo_account, account_service).access_token,
        demo_user_id=demo_account.user_id,
        display_name=demo_account.display_name,
        days_created=result.days_created,
        friends_connected=result.friends_connected,
        profile=result.profile,
        days=payload.days,
        with_violations=payload.with_violations,
        plan_day=plan_day,
        plan_days_completed=plan_done,
        open_violations=ledger.open_violations,
        missed_days=ledger.missed_days,
        final_result=final_response,
        final_inputs=dict(result.final_validation.cleaned_data),
        friend_error=result.friend_error,
    )


@router.delete(
    "/demo/session", status_code=204,
    summary="Delete the demo account the caller is currently signed in as",
)
def end_demo_session(
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> None:
    """Deletes a demo account AND every trace it created.

    The token presented here is the demo's own, so this cannot be aimed
    at a real account by mistake - but the address is checked anyway,
    because "delete the account this token belongs to" is not a call
    that should rely on the caller having been careful.

    Was: this only removed the account row.
    AccountService.delete_account() deliberately does ONLY that (see its
    docstring) - the caller is responsible for its dependent data. This
    caller was not doing so: the demo's own history, its bot friends'
    histories, and every League connection and chat message either side
    ever touched all survived, even though the user was told deletion was
    complete. Reproduced before fixing: a 3-friend demo left 7 of the
    demo's own history rows, 21 rows across its 3 bots (7 each), and all
    3 League connections behind after a 204 "deleted" response.

    Fixed by sequencing the same way /privacy/me does
    (api/routers/progress.py::delete_my_data): every dependent store
    first, the account row last, so a failure partway through leaves the
    account itself intact and the caller can retry rather than orphaning
    data with no owner able to reach it.
    """
    if not (account.email or "").startswith("demo+") or not account.email.endswith("@demo.local"):
        raise BadRequestError("This is not a demo account.", error_code="not_a_demo_account")
    _purge_demo_account(account_service, storage, account.user_id)
