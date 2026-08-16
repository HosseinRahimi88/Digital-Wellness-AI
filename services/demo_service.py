"""
Demo Mode Service
-------------------
One button, one real ~23-day history: builds a plausible day-by-day
habit trajectory (a realistic improvement story with a mid-story dip,
not a straight line) and runs every single day through the exact same
`ValidationService` -> `PredictionService` -> `HistoryService.record()`
pipeline a real check-in uses. The SCORES are always genuine model
output; only the INPUTS are synthetic - never the other way around.

Why this exists: judges reviewing a hackathon submission need to see
every feature populated (Coach, League, Weekly Plan, Analytics) without
either the presenter manually logging 23 real days on camera, or the
project resorting to a hand-typed fake history that never touched the
real model. This is the middle path.

Also creates one synthetic "friend" (a League connection with a bot
user_id, never a real Account) so the League page has something to
show immediately - built through the real `LeagueService` consent flow
(both sides accept rules, an invite is redeemed, the request is
approved with real category choices), not a hardcoded UI mock.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from datetime import date as date_cls, timedelta
from typing import Any, Optional

from config.demo_profiles import at_risk_profile, healthy_profile
from core.feature_schema import FEATURE_SCHEMA
from services.history_service import HistoryService
from services.league_service import LeagueService
from services.prediction_service import PredictionService
from services.validation_service import ValidationService
from utils.feature_derivation import derive_features

logger = logging.getLogger(__name__)

DEMO_DAYS = 23
DEMO_BOT_USER_ID_PREFIX = "demo_bot_"
_NON_NUMERIC_KEEP_FROM_HEALTHY = {"uses_screen_time_limits", "is_content_creator"}

# The four stories a demo can tell, and the four lengths it can tell
# them over. A single "improving" demo could only ever show the app
# being encouraging; a reviewer needs to see what it says to someone who
# is getting worse, and what it says when the signal is ambiguous,
# because those are the cases where an honest app and a flattering one
# look different.
DEMO_LENGTHS = (3, 7, 15, 23)
DEMO_PROFILES = ("healthy", "improving", "borderline", "at_risk")

# Each of the sixteen (profile x length) demos exists twice: once for
# somebody who kept up with their plan, and once for somebody who did
# not. That second variant is the whole reason this flag exists - the
# violation ledger, the greyed and reddened days on the dashboard and an
# empty badge wall are a large part of what the app does, and none of it
# was reachable from a demo, because every demo user was a model
# citizen. Thirty-two states, not sixteen.
DEMO_VARIANTS = (False, True)

# A demo is meant to be the SAME person every time it is opened. It used
# to mint a fresh random account and reseed from that account's id, so
# "the 23-day improving demo" was a different human with different
# numbers on every run - impossible to talk anyone through, and
# impossible to check against what you saw last time.
#
# The seed is now derived from the state alone, so state -> numbers is
# a function. The account address is derived the same way, so reopening
# a demo finds the person who is already there instead of creating a
# twin.
def demo_seed(profile: str, days: int, with_violations: bool = False) -> str:
    """The one seed for this demo state. Same state, same person."""
    return f"dwai-demo-v1:{profile}:{int(days)}:{'v' if with_violations else 'clean'}"


def demo_email(profile: str, days: int, with_violations: bool = False) -> str:
    """The fixed address of this demo state's account.

    Readable on purpose: someone looking at storage should be able to
    tell which of the thirty-two this is without decoding anything.
    """
    return f"demo+{profile}-{int(days)}d{'-lapsed' if with_violations else ''}@demo.local"


def demo_display_name(profile: str, days: int, with_violations: bool = False) -> str:
    label = {
        "healthy": "Healthy", "improving": "Improving",
        "borderline": "Borderline", "at_risk": "At Risk",
    }.get(profile, profile)
    return f"Demo · {label} · {int(days)}d{' · lapsed' if with_violations else ''}"

# Where each story starts and ends on the 0 (at-risk shaped) to 1
# (healthy shaped) axis, and how much day-to-day noise it carries.
# `borderline` deliberately sits near the middle band edge and wanders
# across it, which is the case that makes the seven-day class flip.
_PROFILE_SHAPE: dict[str, dict[str, float]] = {
    "healthy":    {"start": 0.78, "end": 0.92, "dip": 0.06, "jitter": 0.045},
    "improving":  {"start": 0.18, "end": 0.88, "dip": 0.16, "jitter": 0.050},
    "borderline": {"start": 0.46, "end": 0.54, "dip": 0.10, "jitter": 0.075},
    "at_risk":    {"start": 0.34, "end": 0.10, "dip": 0.05, "jitter": 0.050},
}

# Ten demo friends for the fullest demo, so the league, the leaderboard
# and the chat all have something real to show. Each carries its own
# offset on the same axis, so the leaderboard is a spread of people
# rather than ten copies of one.
DEMO_FRIENDS: tuple[tuple[str, str, float], ...] = (
    ("Sam", "improving", 0.00),
    ("Lena", "healthy", -0.06),
    ("Omid", "borderline", 0.04),
    ("Yara", "healthy", 0.08),
    ("Nico", "at_risk", 0.02),
    ("Mira", "improving", -0.10),
    ("Kian", "borderline", -0.05),
    ("Tara", "healthy", -0.12),
    ("Reza", "at_risk", -0.03),
    ("Ivy", "improving", 0.06),
)


def _clamp(field_name: str, value: float) -> float:
    feature = FEATURE_SCHEMA.get(field_name)
    if feature is None:
        return value
    if feature.minimum is not None:
        value = max(value, feature.minimum)
    if feature.maximum is not None:
        value = min(value, feature.maximum)
    return value


def _trajectory_fraction(
    day_index: int,
    total_days: int,
    rng: random.Random,
    profile: str = "improving",
    offset: float = 0.0,
) -> float:
    """0 = fully at-risk-shaped inputs, 1 = fully healthy-shaped inputs.

    Interpolates from the profile's start to its end with a mid-story
    relapse dip and daily jitter - never a suspiciously straight line,
    and never a value outside [0, 1]. `offset` shifts a whole person up
    or down the axis, which is how ten demo friends end up as ten
    different people rather than ten copies of one trajectory.
    """
    shape = _PROFILE_SHAPE.get(profile, _PROFILE_SHAPE["improving"])
    t = day_index / max(1, total_days - 1)
    level = shape["start"] + (shape["end"] - shape["start"]) * t
    dip_center = total_days * 0.55
    spread = max(total_days * 0.09, 0.75)
    dip = shape["dip"] * math.exp(-((day_index - dip_center) ** 2) / (2 * spread ** 2))
    jitter = rng.uniform(-shape["jitter"], shape["jitter"])
    return max(0.0, min(1.0, level - dip + jitter + offset))


def _build_daily_raw_input(
    day_index: int,
    total_days: int,
    the_date: date_cls,
    rng: random.Random,
    profile: str = "improving",
    offset: float = 0.0,
) -> dict[str, Any]:
    lo_profile = at_risk_profile()
    hi_profile = healthy_profile()
    fraction = _trajectory_fraction(day_index, total_days, rng, profile, offset)

    data: dict[str, Any] = {}
    for name, feature in FEATURE_SCHEMA.items():
        if name in lo_profile and name in hi_profile and feature.dtype in (int, float):
            lo, hi = float(lo_profile[name]), float(hi_profile[name])
            value = lo + (hi - lo) * fraction
            span = abs(hi - lo) or 1.0
            value += rng.uniform(-0.04, 0.04) * span
            data[name] = round(_clamp(name, value), 2)
        elif name in hi_profile and name in _NON_NUMERIC_KEEP_FROM_HEALTHY:
            data[name] = hi_profile[name] if fraction > 0.45 else lo_profile.get(name, hi_profile[name])
        elif name in lo_profile:
            data[name] = lo_profile[name]

    data["day_index"] = day_index + 1
    data["day_of_week"] = the_date.strftime("%A")
    data["is_weekend"] = 1 if the_date.weekday() >= 5 else 0
    return derive_features(data)


@dataclass(slots=True)
class DemoPopulateResult:
    days_created: int
    final_prediction: Any  # the real PredictionResult for the last day
    final_validation: Any  # the real ValidationResult for the last day
    friend_connected: bool
    friends_connected: int = 0
    # Why the league is smaller than asked for, when it is. None when the
    # demo came out complete.
    friend_error: Optional[str] = None
    profile: str = "improving"


class DemoService:

    def __init__(
        self,
        history_service: HistoryService,
        validator: ValidationService,
        predictor: PredictionService,
        league_service: Optional[LeagueService] = None,
    ) -> None:
        self.history_service = history_service
        self.validator = validator
        self.predictor = predictor
        self.league_service = league_service or LeagueService()
        # Set when a demo could not build its full league. None means the
        # league came out exactly as asked for.
        self.last_friend_error: Optional[str] = None

    # Which days a lapsed demo user skipped logging. Deterministic per
    # state (the rng is seeded from the state alone), so "the 23-day
    # lapsed improving demo" has the same gaps every time it is opened.
    # Roughly a third of days, never the first (a user who never logged
    # anything has no account to speak of) and never the last (the
    # reviewer lands on the result screen, which needs a day).
    _LAPSED_SKIP_FRACTION = 0.34

    def _lapsed_skips(self, days: int, rng: random.Random) -> set[int]:
        if days < 3:
            return set()
        candidates = list(range(1, days - 1))
        count = max(1, int(len(candidates) * self._LAPSED_SKIP_FRACTION))
        return set(rng.sample(candidates, min(count, len(candidates))))

    def populate(
        self,
        user_id: str,
        display_name: str,
        seed: Optional[int] = None,
        days: int = DEMO_DAYS,
        profile: str = "improving",
        friends: int = 1,
        with_violations: bool = False,
    ) -> DemoPopulateResult:
        """Build `days` scored days along `profile`, plus `friends` demo
        friends with their own histories and an opening message each.

        Every day goes through the real validator and the real model -
        a demo that fabricated scores would be showing the reviewer
        something the app cannot actually do.
        """
        days = max(1, int(days))
        profile = profile if profile in _PROFILE_SHAPE else "improving"
        # Seeded from the STATE, not from the account. A demo is meant
        # to be the same person every time somebody opens it; seeding
        # from user_id made "the 23-day improving demo" a different
        # human with different numbers on every run, which is impossible
        # to talk a reviewer through and impossible to check against
        # what you saw last time.
        rng = random.Random(
            seed if seed is not None else demo_seed(profile, days, with_violations)
        )
        today = date_cls.today()
        start = today - timedelta(days=days - 1)

        final_prediction = None
        final_validation = None
        pending: list = []

        # A lapsed demo has real GAPS in its history, not merely worse
        # numbers. That is the point: the dashboard's grey and red days,
        # the violation ledger and an empty badge wall all key off days
        # that are genuinely absent, and none of it could be shown while
        # every demo user logged faithfully every single day.
        skipped = self._lapsed_skips(days, rng) if with_violations else set()

        for i in range(days):
            if i in skipped:
                continue
            the_date = start + timedelta(days=i)
            raw = _build_daily_raw_input(i, days, the_date, rng, profile)
            validation = self.validator.validate(raw)
            if not validation.is_valid:
                # A synthetic day failing validation is a bug in the
                # generator, not a user error - skip it rather than
                # crashing the whole demo, but never silently fabricate
                # a passing result for it.
                continue
            # SHAP is the expensive half of a prediction and only the
            # day the user actually lands on displays it, so the other
            # twenty-two are scored without it. This is most of why a
            # 23-day demo takes seconds rather than a minute.
            prediction = self.predictor.predict(validation.cleaned_data, compute_shap=(i == days - 1))
            # Collected, not written yet: one locked read-modify-write of
            # the whole history file per day is what made a 23-day demo
            # take tens of seconds and eventually time out on the lock.
            pending.append((validation.cleaned_data, prediction, None, the_date))
            final_prediction = prediction
            final_validation = validation

        self.history_service.record_many(pending)

        connected = self._connect_demo_friends(user_id, display_name, rng, days, friends)

        return DemoPopulateResult(
            days_created=days - len(skipped), final_prediction=final_prediction,
            final_validation=final_validation, friend_connected=connected > 0,
            friends_connected=connected, profile=profile,
            friend_error=self.last_friend_error,
        )

    def _connect_demo_friends(
        self, user_id: str, display_name: str, rng: random.Random, days: int, wanted: int,
    ) -> int:
        wanted = max(0, wanted)
        if not wanted:
            return 0
        # Hoisted out of the loop: every storage write here is a locked
        # read-modify-write of the whole file, and accepting the user's
        # own rules ten times is ten of them for one piece of state.
        # Together with the invite code, this is twenty file rewrites
        # saved on a ten-friend demo.
        try:
            self.league_service.accept_rules(user_id)
            invite_code = self.league_service.get_or_create_profile(user_id).invite_code
        except Exception as exc:  # noqa: BLE001
            # This used to return 0 and say nothing. A demo whose whole
            # league is missing looks broken rather than empty, and the
            # presenter has no way to tell which it is - so the reason is
            # carried back to the caller now instead of being swallowed.
            logger.exception("Could not prepare the demo league profile.")
            self.last_friend_error = f"{type(exc).__name__}: {exc}"
            return 0

        connected = 0
        failures: list[str] = []
        for name, friend_profile, offset in DEMO_FRIENDS[:wanted]:
            try:
                if self._connect_one_friend(
                    user_id, name, friend_profile, offset, rng, days, invite_code,
                ):
                    connected += 1
                else:
                    failures.append(name)
            except Exception as exc:  # noqa: BLE001 - one bad friend must not sink the demo
                logger.exception("Demo friend %s could not be connected.", name)
                failures.append(f"{name} ({type(exc).__name__})")

        if failures:
            self.last_friend_error = (
                f"{len(failures)} of {wanted} demo friends could not be connected: "
                + ", ".join(failures[:5])
            )
        return connected

    def _connect_one_friend(
        self,
        user_id: str,
        name: str,
        friend_profile: str,
        offset: float,
        rng: random.Random,
        days: int,
        invite_code: str,
    ) -> bool:
        """Builds one demo friend's own history on their own trajectory
        and connects them to `user_id` through the REAL LeagueService
        consent flow - both sides "accept the rules" and the request goes
        through redeem/respond exactly like two real humans would, just
        scripted here for demo speed. Then opens a direct conversation
        and leaves an opening message in it, so the chat has something in
        it the moment it is opened.

        Each friend runs their own profile with their own offset, so the
        leaderboard shows a spread of people instead of ten of the same
        one - which is the only way it demonstrates anything.
        """
        bot_id = f"{DEMO_BOT_USER_ID_PREFIX}{name.lower()}_{user_id}"
        bot_name = f"{name} (demo)"
        bot_history = HistoryService(user_id=bot_id, storage=self.history_service.storage)

        # Friends carry fewer days than the user: their history only has
        # to support a leaderboard figure, and generating ten full-length
        # histories is what would make this slow.
        friend_days = max(3, min(days, 8))
        bot_pending: list = []
        today = date_cls.today()
        start = today - timedelta(days=friend_days - 1)
        for i in range(friend_days):
            the_date = start + timedelta(days=i)
            raw = _build_daily_raw_input(i, friend_days, the_date, rng, friend_profile, offset)
            raw = derive_features(raw)
            validation = self.validator.validate(raw)
            if not validation.is_valid:
                continue
            # Never SHAP here: nothing displays a demo friend's own
            # explanation, so computing it would be pure cost.
            prediction = self.predictor.predict(validation.cleaned_data, compute_shap=False)
            bot_pending.append((validation.cleaned_data, prediction, None, the_date))

        bot_history.record_many(bot_pending)

        try:
            self.league_service.accept_rules(bot_id)
            conn = self.league_service.redeem_invite(
                bot_id, bot_name, invite_code,
                ["score", "persona", "plan_focus"],
            )
            self.league_service.respond_to_request(
                user_id, conn.connection_id, True, ["score", "persona", "plan_focus"],
            )
        except Exception:  # noqa: BLE001 - a friend failing is never fatal to the demo
            return False

        self._seed_conversation(user_id, bot_id, name, rng)
        return True

    def _seed_conversation(
        self, user_id: str, bot_id: str, name: str, rng: random.Random,
    ) -> None:
        """One opened conversation with an opening line from the friend.

        Written through the real chat service, so what the demo shows is
        the real authorization path - an empty chat list is the one part
        of the League that looks broken rather than merely new.
        """
        from services.league_chat_service import LeagueChatService

        chat = LeagueChatService()
        # Logged rather than swallowed. A bare `except: return` here hid
        # a real bug for a whole release: the method names were wrong,
        # every seeded conversation failed, and the demo League showed
        # an empty chat list that looked like a broken feature.
        # connection_verified is true by construction here: the accepted
        # connection was just created above through the real consent
        # flow. Passing it is not a courtesy - the service refuses
        # without it, which is the behaviour that keeps chat closed to
        # anyone who is not actually a friend.
        try:
            conversation = chat.open_direct_conversation(
                bot_id, user_id, other_name=f"{name} (demo)", connection_verified=True,
            )
            chat.send_message(
                bot_id, conversation.conversation_id,
                rng.choice(self._OPENING_LINES).format(name=name),
                sender_name=f"{name} (demo)",
            )
        except Exception:  # noqa: BLE001 - never fatal, but never silent either
            logger.exception("Could not seed the demo conversation with %s.", name)

    # Deliberately mundane: a demo chat full of witty scripted banter
    # reads as marketing copy. These are the things someone actually
    # says to a friend who is also tracking their week.
    _OPENING_LINES = (
        "Hey! Just joined. How's your week looking?",
        "Managed a whole evening without the phone yesterday. Small win.",
        "My sleep score is a mess this week. How are you doing?",
        "Saw you've been consistent - what changed?",
        "Starting again after a bad stretch. Wish me luck.",
        "Notifications off after 9pm has been the one that actually helped.",
    )
