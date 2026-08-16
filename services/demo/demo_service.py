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
from services.demo.demo_journal import pages_for
from services.identity.history_service import HistoryService
from services.identity.journal_service import JournalService
from services.identity.personal_service import PersonalService
from services.social.league_service import LeagueService
from services.ml.prediction_service import PredictionService
from services.ml.validation_service import ValidationService
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
#
# These numbers are TUNED TO THE MODEL, not chosen by eye. The demo
# scores are genuine regressor output, so the only way a "healthy" demo
# can actually score in the healthy band is to feed it inputs the model
# scores that way. Measured on the shipped regressor (median of 5 days
# at a pinned fraction):
#
#     fraction  0.00  0.50  0.60  0.70  0.80  0.90  0.95  1.00
#     score     39.0  48.6  51.6  56.2  62.3  70.9  77.7  83.8
#
# The old shapes ignored this. `healthy` ran 0.78 -> 0.92, i.e. 62-72,
# so a demo user labelled healthy never once reached 80 - measured, 2 of
# 23 days were in band, and the single 80 was the maximum. `borderline`
# ran 0.46 -> 0.54, i.e. 46-50, which is the at-risk band, not the
# moderate one: 1 of 23 in band.
#
# Bands: healthy 80-100, moderate 50-79, at risk 0-49. Each shape below
# is placed so that start, end, AND the worst case (start - dip - jitter)
# all stay inside its band.
#
# The axis does not stop at 1.0. `healthy_profile()` is ONE healthy
# person, not the healthiest legal one, and every feature carries its
# own schema minimum/maximum. Walking a little past the healthy profile
# and clamping to those bounds is therefore a real person at the good
# end of each field, not invented data - and the model scores them
# accordingly. Measured (median of 15 days at a pinned fraction):
#
#     fraction  1.00  1.05  1.10  1.20  1.35  1.50
#     score     84.2  86.5  87.0  86.4  86.4  86.3
#
# Two things follow. The true ceiling is ~87, not the ~84 that fraction
# 1.0 shows. And past ~1.10 the curve is flat, because every feature has
# hit its bound - so AXIS_MAX is set just past the knee and nothing is
# gained by going further.
#
# The other lesson from that table is where the spread comes from. At
# fraction 1.00 the fifteen samples ran 78.2 - 86.5, an eight-point
# spread from the per-feature +-4% noise alone, which is exactly how a
# "healthy" demo produced days at 78 and 79. At fraction 1.05 the same
# noise produces 85.5 - 87.6, because the clamping absorbs it. Holding
# healthy a little above 1.0 is what makes the band hold.
AXIS_MAX = 1.20

# `floor` and `cap` are the profile's own walls on the axis - the demo
# clamps to these, not to [0, 1]. They are what guarantees that moving a
# friend to their own landing point (DEMO_FRIENDS' third column) makes
# them a different person without ever pushing them out of the class
# they are labelled with. A friend whose landing point sits far from the
# profile's own end spends their early days pressed against one of these
# walls; that flattening is the price of the label staying true, and it
# is why the roster spreads people across four profiles rather than
# translating one profile a long way.
_PROFILE_SHAPE: dict[str, dict[str, float]] = {
    # 1.045 -> 1.095, i.e. ~85 - 87.5, deliberately placed ON the knee
    # rather than above it. Everything past ~1.07 scores the same 87,
    # so a healthy demo pinned high draws a dead-flat line across the
    # dashboard; sitting at the knee is the only place where a healthy
    # person still has visible good days and less-good days.
    #
    # Floor 1.035, not 1.02. The first pass measured the clean
    # catalogue and stopped there. The LAPSED half is a different
    # sequence, not the same one with days removed - `_lapsed_skips`
    # draws from the same rng before the day loop, and every skipped day
    # is a per-feature noise draw that never happens - so the noise
    # lands differently, and two lapsed healthy states produced days at
    # 80.3 and 80.5. In band, and below what a healthy demo should ever
    # show. At 1.02 the measured worst case is 83.2; at 1.035 it is
    # ~84.5, which is where the whole catalogue clears comfortably.
    "healthy":    {"start": 1.045, "end": 1.095, "dip": 0.030, "jitter": 0.030,
                   "floor": 1.035, "cap": AXIS_MAX},
    # 0.20 -> 1.10: the full arc, at risk to healthy, with a real relapse
    # in the middle. ~40 climbing to ~87 - the story only lands if it
    # actually ENDS healthy, which the old end of 0.995 (~83) did not
    # once a friend's negative offset was applied.
    "improving":  {"start": 0.200, "end": 1.100, "dip": 0.100, "jitter": 0.040,
                   "floor": 0.080, "cap": AXIS_MAX},
    # 0.61 - 0.91  ->  ~52 - 71, wandering inside the moderate band.
    # Floor 0.60 is the wall that keeps a negatively offset friend off
    # 49; cap 0.93 keeps a positive one under 80.
    "borderline": {"start": 0.660, "end": 0.870, "dip": 0.050, "jitter": 0.035,
                   "floor": 0.600, "cap": 0.930},
    # 0.05 - 0.40  ->  ~39 - 44, declining. Cap 0.46 (~47) keeps it
    # inside the at-risk band whatever the offset does.
    "at_risk":    {"start": 0.400, "end": 0.050, "dip": 0.040, "jitter": 0.040,
                   "floor": 0.000, "cap": 0.460},
}

# Ten demo friends for the fullest demo, so the league, the leaderboard
# and the chat all have something real to show.
#
# The third column is the axis position each friend's LAST day lands on -
# an absolute place on the trajectory axis, not a nudge. That is the
# change, and it was made because the previous roster's small relative
# offsets did not survive the score curve. Measured on the shipped
# regressor, the ten friends' final scores came out:
#
#     87.0  87.0  87.1  86.6  86.5  83.8  72.0  66.9  39.3  39.0
#
# Five friends showing 87 and two showing 39. The cause is the shape of
# the curve rather than the offsets: everything above axis ~1.07 scores
# the same 87, and six of the ten profiles ENDED up there (three
# "healthy", three "improving", all landing at the top of the axis). An
# offset of -0.12 inside a saturated region moves nobody.
#
# So the roster is spread across the axis instead of clustered at the
# good end - two healthy, two improving, three borderline, three at
# risk - and each friend names the point they finish on. Their measured
# final scores are written beside them. A friends league whose members
# all show one number is not a league; it is the same person ten times.
# Only ONE friend runs the `healthy` profile, which looks odd until you
# read its walls: healthy floors at 1.035, and from there to AXIS_MAX the
# score curve moves 86.4 -> 86.9. Half a point of range - there is room
# for exactly one person in it. Everyone else in the good half of the
# table runs `improving` instead, whose floor is 0.080, so it can land
# anywhere on the axis. A friend on the improving arc who is currently at
# 78 is not mislabelled; they are the story mid-way through, which is a
# more useful thing for a league to show than another 87.
#
# The landing -> score map below was MEASURED on the shipped regressor,
# noise-free last day, and it is the same map for every profile because
# the score depends only on where the day sits on the axis:
#
#     axis   0.28  0.45  0.70  0.78  0.86  0.93  0.96  0.99  1.006 1.08
#     score  42.2  46.5  55.1  61.2  66.4  73.4  77.7  83.4  84.6  86.9
DEMO_FRIENDS: tuple[tuple[str, str, float], ...] = (
    ("Sam", "improving", 1.006),    # 84.6
    ("Lena", "healthy", 1.080),     # 86.9
    ("Omid", "borderline", 0.930),  # 73.4
    ("Yara", "borderline", 0.780),  # 61.2
    ("Nico", "borderline", 0.700),  # 55.1
    ("Mira", "improving", 0.990),   # 83.4
    ("Kian", "borderline", 0.860),  # 66.4
    ("Tara", "improving", 0.960),   # 77.7
    ("Reza", "at_risk", 0.450),     # 46.5
    ("Ivy", "at_risk", 0.280),      # 42.2
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
    lands_on: Optional[float] = None,
) -> float:
    """0 = fully at-risk-shaped inputs, 1 = fully healthy-shaped inputs.

    Interpolates from the profile's start to its end with a mid-story
    relapse dip and daily jitter - never a suspiciously straight line.

    `lands_on` is where this person's LAST day sits on the axis. The
    whole trajectory is translated so it finishes there, which is how
    ten demo friends end up as ten different people rather than ten
    copies of one. None means "run the profile as written", which is
    what the demo user's own history does.

    Two details that are load-bearing, both learned by measuring:

      * the last day carries neither jitter nor the relapse dip, so it
        lands exactly where it was declared to. Everywhere near the top
        of the axis the score curve is steep - eight points of score
        across 0.08 of axis - so a +-0.03 wobble is +-3 points on the
        ONE day the leaderboard reads, and friends placed a point apart
        would show noise rather than themselves. The dip matters for
        the same reason and was easy to miss: over three days its
        gaussian is still 90% open on the final day, which pulled a
        friend declared at 1.050 down to 0.960. Every other day keeps
        both, so nobody's history is a straight line;

      * the result is clamped to the PROFILE's own floor and cap rather
        than to [0, 1]. That is what makes the labels honest: a friend
        labelled healthy scores in the healthy band wherever they land,
        because the translation can only move them inside their own
        class. Translating a long way does flatten the early days
        against a wall - an at-risk friend finishing high spends their
        first days pinned to the cap - and that is the accepted cost of
        keeping the label true. Values above 1.0 are legal and
        meaningful; see the note on AXIS_MAX above.
    """
    shape = _PROFILE_SHAPE.get(profile, _PROFILE_SHAPE["improving"])
    t = day_index / max(1, total_days - 1)
    level = shape["start"] + (shape["end"] - shape["start"]) * t
    dip_center = total_days * 0.55
    spread = max(total_days * 0.09, 0.75)
    is_last_day = day_index >= total_days - 1
    dip = 0.0 if is_last_day else (
        shape["dip"] * math.exp(-((day_index - dip_center) ** 2) / (2 * spread ** 2))
    )
    # Drawn even on the last day and then discarded, so the rng stream is
    # the one every band number in tests/api/test_demo_score_bands.py was
    # measured against. `_build_daily_raw_input` keeps drawing from this
    # same rng after this call, and skipping a draw would shift every
    # per-feature noise value for the day.
    drawn = rng.uniform(-shape["jitter"], shape["jitter"])
    jitter = 0.0 if is_last_day else drawn
    translate = 0.0 if lands_on is None else (lands_on - shape["end"])
    value = level - dip + jitter + translate
    floor = shape.get("floor", 0.0)
    cap = min(shape.get("cap", 1.0), AXIS_MAX)
    return max(0.0, max(floor, min(cap, value)))


def _build_daily_raw_input(
    day_index: int,
    total_days: int,
    the_date: date_cls,
    rng: random.Random,
    profile: str = "improving",
    lands_on: Optional[float] = None,
) -> dict[str, Any]:
    lo_profile = at_risk_profile()
    hi_profile = healthy_profile()
    fraction = _trajectory_fraction(day_index, total_days, rng, profile, lands_on)

    # The final day is built noise-free, for the same reason it carries
    # no axis jitter: it is the ONE day of a demo friend that anybody
    # ever sees, and the leaderboard reads it. Measured, the per-feature
    # +-4% alone moved an improving friend's last day across 73.2, 82.7
    # and 76.0 on three different seeds - a nine-point swing on the
    # number that is supposed to say who this person is. Every earlier
    # day keeps its noise, so no history is a straight line; only the
    # headline is exact.
    quiet = day_index >= total_days - 1

    data: dict[str, Any] = {}
    for name, feature in FEATURE_SCHEMA.items():
        if name in lo_profile and name in hi_profile and feature.dtype in (int, float):
            lo, hi = float(lo_profile[name]), float(hi_profile[name])
            value = lo + (hi - lo) * fraction
            span = abs(hi - lo) or 1.0
            # Drawn either way, so the rng stream does not shift.
            drawn = rng.uniform(-0.04, 0.04) * span
            value += 0.0 if quiet else drawn
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
        self._seed_journal(user_id, profile, [row[3] for row in pending])
        self._seed_personal(user_id, profile, days, [row[3] for row in pending])

        connected = self._connect_demo_friends(user_id, display_name, rng, days, friends)

        return DemoPopulateResult(
            days_created=days - len(skipped), final_prediction=final_prediction,
            final_validation=final_validation, friend_connected=connected > 0,
            friends_connected=connected, profile=profile,
            friend_error=self.last_friend_error,
        )

    # Roughly how much of a demo history carries a written page. Nobody
    # journals every single day, and a book with an entry on every date
    # reads as generated rather than lived.
    _JOURNAL_DENSITY = 0.6

    def _seed_journal(self, user_id: str, profile: str, dates: list) -> int:
        """Fill this demo person's book, leaving today's page blank.

        Two deliberate choices:

        * TODAY IS LEFT EMPTY. A reviewer opening the book should be
          able to write the current day themselves and watch it save -
          that is the feature. Every day behind it is already written,
          so the book is a book and not an onboarding screen.
        * NO RNG. The pages are placed by even spacing across the days
          that were actually logged, and chosen from the profile's own
          staged bank in order. Drawing from `rng` here would consume
          numbers the day loop's per-feature noise depends on, which
          would move every score in the demo and quietly invalidate the
          band measurements in tests/api/test_demo_score_bands.py.

        A lapsed demo has gaps in `dates` already (the day loop skipped
        them), so its book has gaps in exactly the same places - which
        is the honest version: a person who stopped logging also stopped
        writing.
        """
        eligible = [d for d in dates][:-1]  # today stays for the reader
        if not eligible:
            return 0
        bank = pages_for(profile)
        wanted = min(len(bank), len(eligible), max(2, round(len(eligible) * self._JOURNAL_DENSITY)))
        wanted = max(1, wanted)

        def _at(count: int, span: int, index: int) -> int:
            """Index `index` of `count` spread evenly across `span` slots."""
            if count <= 1:
                return span - 1
            return round(index * (span - 1) / (count - 1))

        pages = []
        for k in range(wanted):
            when = eligible[_at(wanted, len(eligible), k)]
            mood, text_i18n = bank[_at(wanted, len(bank), k)]
            pages.append((when, text_i18n["en"], mood, dict(text_i18n)))

        try:
            return JournalService(user_id).save_many(pages)
        except Exception:  # noqa: BLE001 - a demo without a book still works
            logger.warning("Could not seed the demo journal for %s.", user_id, exc_info=True)
            return 0

    # A demo person has been using the app, so the personal panel has
    # to have something in it. Both numbers below are written into the
    # real store through the real service, and both are the kind of
    # number a person would actually produce - not a round figure
    # chosen to look good.
    _DEMO_BIRTH_YEARS = {"healthy": 1996, "improving": 2001, "borderline": 1993, "at_risk": 2004}
    _DEMO_SECONDS_PER_DAY = {"healthy": 260, "improving": 340, "borderline": 300, "at_risk": 210}

    def _seed_personal(self, user_id: str, profile: str, days: int, dates: list) -> None:
        """A birth date and a measured-looking usage tally for a demo.

        The seconds are attributed to the days the demo person actually
        logged, one write per day through the same capped path a real
        heartbeat takes - so the tally obeys the same ceilings and
        nothing here can produce a number the live app could not.

        No rng: like the journal, drawing here would consume numbers the
        day loop's per-feature noise depends on and move every score in
        the demo.
        """
        try:
            personal = PersonalService(user_id)
            year = self._DEMO_BIRTH_YEARS.get(profile, 1998)
            # A fixed day per profile, so the demo person is the same
            # person every time this is rebuilt.
            personal.set_birth_date(f"{year}-0{1 + (days % 9)}-1{profile.count('_') + 4}")
            base = self._DEMO_SECONDS_PER_DAY.get(profile, 280)
            for index, when in enumerate(dates):
                # A little variation across days, deterministic in the
                # day's own index rather than random.
                personal.add_seconds(base + (index % 5) * 37, when)
        except Exception:  # noqa: BLE001 - a demo without a usage tally still works
            logger.warning("Could not seed demo personal data for %s.", user_id, exc_info=True)

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
        # Every friend's days are collected here and written in ONE
        # locked transaction after the loop. Each friend used to call
        # record_many() itself, so ten friends meant ten full rewrites
        # of a history file holding every account's rows - the dominant
        # cost of a large demo once the file has grown, and what made it
        # exceed the client's timeout.
        pending_sink: dict[str, list] = {}
        for name, friend_profile, lands_on in DEMO_FRIENDS[:wanted]:
            try:
                if self._connect_one_friend(
                    user_id, name, friend_profile, lands_on, rng, days, invite_code,
                    pending_sink, display_name,
                ):
                    connected += 1
                else:
                    failures.append(name)
            except Exception as exc:  # noqa: BLE001 - one bad friend must not sink the demo
                logger.exception("Demo friend %s could not be connected.", name)
                failures.append(f"{name} ({type(exc).__name__})")

        # One locked write for every friend's history at once.
        if pending_sink:
            self.history_service.record_many_users(pending_sink)

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
        lands_on: float,
        rng: random.Random,
        days: int,
        invite_code: str,
        pending_sink: dict[str, list],
        user_display_name: str = "You",
    ) -> bool:
        """Builds one demo friend's own history on their own trajectory
        and connects them to `user_id` through the REAL LeagueService
        consent flow - both sides "accept the rules" and the request goes
        through redeem/respond exactly like two real humans would, just
        scripted here for demo speed. Then opens a direct conversation
        and plays a real exchange into it, so the chat has a conversation
        in it the moment it is opened rather than one line and silence.

        Each friend runs their own profile and finishes on their own
        point of the axis (`lands_on`), so the leaderboard shows a
        spread of people instead of ten of the same one - which is the
        only way it demonstrates anything.
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
            raw = _build_daily_raw_input(i, friend_days, the_date, rng, friend_profile, lands_on)
            raw = derive_features(raw)
            validation = self.validator.validate(raw)
            if not validation.is_valid:
                continue
            # Never SHAP here: nothing displays a demo friend's own
            # explanation, so computing it would be pure cost.
            prediction = self.predictor.predict(validation.cleaned_data, compute_shap=False)
            bot_pending.append((validation.cleaned_data, prediction, None, the_date))

        # Collected, not written: _connect_demo_friends writes every
        # friend's days in one transaction after the loop.
        if bot_pending:
            pending_sink[bot_id] = bot_pending

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

        self._seed_conversation(user_id, bot_id, name, rng, friend_profile, user_display_name)
        return True

    def _seed_conversation(
        self, user_id: str, bot_id: str, name: str, rng: random.Random,
        friend_profile: str = "improving", user_name: str = "You",
    ) -> None:
        """An opened conversation with a real exchange already in it.

        Written through the real chat service, so what the demo shows is
        the real authorization path - an empty chat list is the one part
        of the League that looks broken rather than merely new.
        """
        from services.social.league_chat_service import LeagueChatService

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
            script = self._CONVERSATIONS.get(friend_profile) or self._CONVERSATIONS["improving"]
            thread = rng.choice(script)
            # One write for the whole exchange. Looping through
            # send_message() would trip the chat's own rate limit - seven
            # messages in a row is exactly what it exists to stop - and
            # would rewrite the whole chat file once per line.
            chat.seed_messages(
                conversation.conversation_id,
                [
                    (
                        bot_id if who == "them" else user_id,
                        f"{name} (demo)" if who == "them" else user_name,
                        line.format(name=name),
                    )
                    for who, line in thread
                ],
            )
        except Exception:  # noqa: BLE001 - never fatal, but never silent either
            logger.exception("Could not seed the demo conversation with %s.", name)

    # Real exchanges, not an opening line.
    #
    # A single message from the friend and silence after it is not a
    # conversation - it is a notification, and the League's chat looked
    # like a feature nobody had used. What a reviewer needs to see is
    # two people talking: someone says something, the other answers,
    # and it goes somewhere.
    #
    # Keyed by the FRIEND's own profile, so the chat matches the person
    # on the leaderboard: the friend sitting at 87 does not open with "my
    # sleep is a mess". Every thread runs both ways - "them" is the
    # friend, "you" is the demo user - and each is deliberately mundane.
    # Scripted banter reads as marketing copy; these are the things
    # people actually type to someone tracking the same week.
    _CONVERSATIONS: dict[str, tuple[tuple[tuple[str, str], ...], ...]] = {
        "healthy": (
            (
                ("them", "Hey! Just joined. How's your week looking?"),
                ("you", "Mixed. Started well, then a couple of late nights."),
                ("them", "Late nights are the whole thing for me too. I moved the charger out of the bedroom in March and honestly that was most of it."),
                ("you", "That simple?"),
                ("them", "That simple and that annoying. I still reach for it and it isn't there."),
                ("you", "Might try it tonight."),
                ("them", "Tell me on Friday whether it held."),
            ),
            (
                ("them", "Your streak is showing on the board - nice one."),
                ("you", "Thanks. It doesn't feel like much day to day."),
                ("them", "It never does. Mine only looked like anything after about three weeks."),
                ("you", "What are you doing differently to me?"),
                ("them", "Nothing clever. Same wake-up time every day, including weekends. That's the whole trick."),
                ("you", "Weekends are exactly where I lose it."),
                ("them", "Then that's your week sorted."),
            ),
        ),
        "improving": (
            (
                ("them", "Starting again after a bad stretch. Wish me luck."),
                ("you", "How bad are we talking?"),
                ("them", "Two weeks of nothing. Didn't log a single day."),
                ("you", "The app doesn't hold that against you, for what it's worth."),
                ("them", "No, but I did. Anyway - three days in a row now."),
                ("you", "That's the hard part done."),
                ("them", "We'll see. Ask me again next week."),
            ),
            (
                ("them", "Notifications off after 9pm has been the one that actually helped."),
                ("you", "Everything, or just some apps?"),
                ("them", "Everything that isn't a person. Took about a minute in settings and cut my count by half."),
                ("you", "Half?"),
                ("them", "Half. Most of what was buzzing at me was a shop."),
                ("you", "Right, doing that now."),
                ("them", "Report back. I want to know if it's just me."),
            ),
        ),
        "borderline": (
            (
                ("them", "My sleep score is a mess this week. How are you doing?"),
                ("you", "Not much better. What's going on with yours?"),
                ("them", "Deadline. I keep telling myself I'll catch up at the weekend."),
                ("you", "Does that ever work?"),
                ("them", "It has never once worked."),
                ("you", "Same. I've stopped pretending it will."),
                ("them", "Let's both just aim for one earlier night this week and call it a win."),
            ),
            (
                ("them", "How do you read the seven-day band? Mine says 62-76 and I can't tell if that's good."),
                ("you", "It's the range it expects you in, not a promise."),
                ("them", "So the top of it is the version of me that sleeps."),
                ("you", "Pretty much."),
                ("them", "Fine. Sleeping it is."),
            ),
        ),
        "at_risk": (
            (
                ("them", "Honestly this week has been rough. Numbers are all over the place."),
                ("you", "Anything in particular, or just everything?"),
                ("them", "Bit of everything. Sleeping late, on the phone until 2, then wondering why I can't focus."),
                ("you", "That's a loop I know well."),
                ("them", "The app keeps telling me the same thing and it keeps being right, which is the annoying part."),
                ("you", "Pick one. Don't do all of it."),
                ("them", "Phone out of the bedroom. Just that. I'll tell you if I manage three nights."),
            ),
            (
                ("them", "Saw you've been consistent - what changed?"),
                ("you", "Nothing dramatic. I just stopped trying to fix everything at once."),
                ("them", "That's what I keep doing. Big Sunday plan, gone by Tuesday."),
                ("you", "One thing. Same thing, every day, until it's boring."),
                ("them", "Boring sounds achievable."),
                ("you", "That's the idea."),
                ("them", "Okay. One thing. Starting tonight."),
            ),
        ),
    }
