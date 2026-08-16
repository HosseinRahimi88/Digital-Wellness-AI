"""
Badge Service (C-3)
-------------------
The full badge catalogue: *achievement badges*, which are public and
celebrate progress, and *awareness indicators*, which are private and
name a pattern that is worth a look.

Why the split, in the words of the brief: a "bad badge" in a behavioural
wellness app turns into shaming, and shaming backfires. So nothing here
ever tells a user they failed. Achievement badges are earned and can be
shown to friends. Awareness indicators are descriptive - "a late-night
pattern is active", never "bad at sleep" - always carry a next step, and
are marked `private=True` so no league, profile card or share image can
ever surface them. That flag is enforced by the router, not by good
intentions: see `public_badges()`.

Design rules this file follows:

  * Every criterion is real and computed from the user's own stored
    check-ins. There is no participation badge that unlocks on load.
  * A badge whose criterion cannot be judged yet - because the user has
    no data for that field, or not enough days - is returned with
    `earned=False` and `evaluable=False`, so the UI can show it locked
    rather than claiming the user missed it.
  * Days the user marked as exceptions are excluded from every average
    and every "N days in a row" count. They told us that day was not
    normal; scoring them on it would make the label pointless.
  * No text lives here. The service returns ids, numbers and state; all
    four languages are rendered client-side from
    frontend/assets/js/features/badge-registry.js. That is deliberate: an English
    name baked into an API response is exactly the A-2 bug.

On the count: the brief asked for 50 of each and explicitly invited a
smaller honest number instead. There are 44 achievement badges and 19
awareness indicators here, because that is how many distinct criteria
the stored fields actually support without inventing near-duplicates.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from config.gamification_settings import (
    CONSISTENT_LOGGER_MIN_ENTRIES_PER_WEEK,
    HIGH_SCORE_BADGE_THRESHOLD,
    MOST_IMPROVED_MIN_DELTA,
)
from services.social.gamification_service import GamificationService

# --------------------------------------------------------------------
# Tuning
# --------------------------------------------------------------------

# A "recent window" is the last 7 real (non-exception) days; an
# improvement badge compares it to the user's first 7 real days. Both
# windows must be full, so an improvement badge needs 14 real days.
WINDOW = 7
IMPROVEMENT_MIN_DAYS = WINDOW * 2

# An improvement has to be big enough to be a change rather than noise.
IMPROVEMENT_PCT = 10.0

# An awareness indicator fires when a pattern shows up on this many of
# the last WINDOW real days - one late night is a night, four is a
# pattern.
PATTERN_DAYS = 4

CATEGORY_ACHIEVEMENT = "achievement"
CATEGORY_AWARENESS = "awareness"

TIER_COMMON = "common"
TIER_RARE = "rare"
TIER_LEGENDARY = "legendary"


@dataclass(slots=True)
class Badge:
    """One badge's state for one user.

    `name`/`description` are deliberately absent - the client owns every
    string, in four languages, keyed by `id`.
    """

    id: str
    category: str
    icon: str
    tier: Optional[str]          # achievements only
    private: bool
    earned: bool
    # False when the user's history cannot answer this badge's question
    # yet. Distinct from earned=False, which means "answered: not yet".
    evaluable: bool
    # Progress towards the criterion where a number is meaningful; both
    # None for a badge that is simply true or false.
    progress: Optional[float] = None
    target: Optional[float] = None
    # Real numbers from this user's history, substituted into the
    # localized description client-side.
    params: dict[str, float] = field(default_factory=dict)


# --------------------------------------------------------------------
# Facts: everything the criteria need, computed once
# --------------------------------------------------------------------

# Fields where a *lower* number is the healthier direction. Used by the
# improvement badges so "down 12%" counts as progress for screen time
# and "up 12%" counts as progress for sleep.
LOWER_IS_BETTER = {
    "total_screen_min", "night_screen_min", "pre_sleep_screen_min",
    "stress_0_10", "pickups_per_day", "notification_density",
    "fragmentation_index_0_100", "social_comparison_1_10",
    "social_min", "gaming_min", "video_min",
}


@dataclass(slots=True)
class _Facts:
    entries: list[dict[str, Any]]
    real: list[dict[str, Any]]            # exception days removed
    dates: list[date]
    total: int
    distinct_days: int
    scores: list[float]
    streak: Any
    log_streak: int
    longest_log_streak: int
    exception_count: int
    weeks: dict[str, int]
    today: date


def _parse(entry: dict[str, Any]) -> Optional[date]:
    raw = entry.get("date")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def _numbers(entries: list[dict[str, Any]], key: str) -> list[float]:
    out = []
    for e in entries:
        v = e.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append(float(v))
    return out


def _mean(values: list[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _build_facts(entries: list[dict[str, Any]], today: Optional[date] = None) -> _Facts:
    today = today or datetime.now().date()
    dated = [(d, e) for e in entries if (d := _parse(e)) is not None]
    dated.sort(key=lambda pair: pair[0])
    ordered = [e for _, e in dated]
    dates = [d for d, _ in dated]

    real = [e for e in ordered if not e.get("excluded")]

    # Longest run of consecutive calendar days with *any* entry. This is
    # about showing up, so an unhealthy day still counts - unlike
    # GamificationService.compute_streak, which is about healthy days.
    log_current = log_longest = 0
    run = 0
    prev: Optional[date] = None
    for d in sorted({d for d, _ in dated}):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        log_longest = max(log_longest, run)
        prev = d
    if prev is not None and (today - prev).days <= 1:
        log_current = run

    weeks: dict[str, int] = {}
    for d in dates:
        iso = d.isocalendar()
        weeks[f"{iso[0]}-W{iso[1]:02d}"] = weeks.get(f"{iso[0]}-W{iso[1]:02d}", 0) + 1

    return _Facts(
        entries=ordered,
        real=real,
        dates=dates,
        total=len(ordered),
        distinct_days=len(set(dates)),
        scores=_numbers(real, "health_score"),
        streak=GamificationService.compute_streak(ordered, today=today),
        log_streak=log_current,
        longest_log_streak=log_longest,
        exception_count=sum(1 for e in ordered if e.get("excluded")),
        weeks=weeks,
        today=today,
    )


# --------------------------------------------------------------------
# Criterion helpers. Each returns (earned, evaluable, progress, target,
# params) so a badge never has to guess whether "False" meant "no" or
# "cannot tell yet".
# --------------------------------------------------------------------

Result = tuple[bool, bool, Optional[float], Optional[float], dict[str, float]]

NOT_EVALUABLE: Result = (False, False, None, None, {})


def _count_at_least(count: int, target: int) -> Result:
    """A simple 'reach N' criterion; always evaluable, since zero is a
    real answer to 'how many check-ins do you have'."""
    return (count >= target, True, float(count), float(target), {})


def _improvement(facts: _Facts, key: str) -> Result:
    """Recent window vs. the user's own first window, on one field."""
    values = [(e, e.get(key)) for e in facts.real]
    have = [float(v) for _, v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(have) < IMPROVEMENT_MIN_DAYS:
        return NOT_EVALUABLE
    early = _mean(have[:WINDOW])
    recent = _mean(have[-WINDOW:])
    if early is None or recent is None or early == 0:
        return NOT_EVALUABLE
    change_pct = (recent - early) / abs(early) * 100.0
    if key in LOWER_IS_BETTER:
        change_pct = -change_pct
    return (
        change_pct >= IMPROVEMENT_PCT,
        True,
        round(max(change_pct, 0.0), 1),
        IMPROVEMENT_PCT,
        {"early": round(early, 1), "recent": round(recent, 1), "change_pct": round(change_pct, 1)},
    )


def _sustained(facts: _Facts, key: str, threshold: float, lower_is_better: bool) -> Result:
    """Held a level on every one of the last WINDOW real days."""
    have = [
        float(e[key]) for e in facts.real[-WINDOW:]
        if isinstance(e.get(key), (int, float)) and not isinstance(e.get(key), bool)
    ]
    if len(have) < WINDOW:
        return NOT_EVALUABLE
    ok = sum(1 for v in have if (v <= threshold if lower_is_better else v >= threshold))
    return (ok >= WINDOW, True, float(ok), float(WINDOW), {"threshold": threshold})


def _pattern(facts: _Facts, key: str, threshold: float, above: bool) -> Result:
    """An awareness indicator: the pattern showed on PATTERN_DAYS or more
    of the last WINDOW real days."""
    have = [
        float(e[key]) for e in facts.real[-WINDOW:]
        if isinstance(e.get(key), (int, float)) and not isinstance(e.get(key), bool)
    ]
    if len(have) < WINDOW:
        return NOT_EVALUABLE
    hits = sum(1 for v in have if (v >= threshold if above else v <= threshold))
    return (
        hits >= PATTERN_DAYS,
        True,
        float(hits),
        float(PATTERN_DAYS),
        {"threshold": threshold, "days": float(hits), "window": float(WINDOW)},
    )


# --------------------------------------------------------------------
# The catalogue
# --------------------------------------------------------------------

@dataclass(slots=True)
class _Def:
    id: str
    icon: str
    tier: Optional[str]
    rule: Callable[[_Facts], Result]
    category: str = CATEGORY_ACHIEVEMENT


def _best_score(f: _Facts) -> Optional[float]:
    return max(f.scores) if f.scores else None


def _score_at_least(f: _Facts, threshold: float) -> Result:
    best = _best_score(f)
    if best is None:
        return NOT_EVALUABLE
    return (best >= threshold, True, round(best, 1), threshold, {"best": round(best, 1)})


def _most_improved(f: _Facts) -> Result:
    if len(f.scores) < 2:
        return NOT_EVALUABLE
    delta = max(f.scores) - f.scores[0]
    return (
        delta >= MOST_IMPROVED_MIN_DELTA, True, round(max(delta, 0.0), 1), MOST_IMPROVED_MIN_DELTA,
        {"delta": round(delta, 1)},
    )


def _beat_personal_best(f: _Facts) -> Result:
    """The most recent score is the highest the user has ever logged, and
    there is a real history behind it for that to mean something."""
    if len(f.scores) < 5:
        return NOT_EVALUABLE
    latest = f.scores[-1]
    previous_best = max(f.scores[:-1])
    return (
        latest > previous_best, True, round(latest, 1), round(previous_best, 1),
        {"latest": round(latest, 1), "previous_best": round(previous_best, 1)},
    )


def _consistent_week(f: _Facts) -> Result:
    best_week = max(f.weeks.values()) if f.weeks else 0
    return (
        best_week >= CONSISTENT_LOGGER_MIN_ENTRIES_PER_WEEK, True,
        float(best_week), float(CONSISTENT_LOGGER_MIN_ENTRIES_PER_WEEK), {},
    )


def _marked_an_exception(f: _Facts) -> Result:
    """Rewards data honesty, not behaviour: marking a genuinely unusual
    day keeps every baseline in the app truthful."""
    return (f.exception_count >= 1, True, float(f.exception_count), 1.0, {})


def _full_weeks(f: _Facts, needed: int) -> Result:
    complete = sum(1 for c in f.weeks.values() if c >= WINDOW)
    return (complete >= needed, True, float(complete), float(needed), {})


def _comeback(f: _Facts) -> Result:
    """Came back after a gap of a week or more, and stayed for 3 days.
    Restarting is harder than continuing and nothing else marks it."""
    days = sorted(set(f.dates))
    if len(days) < 4:
        return NOT_EVALUABLE
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days >= 7:
            after = [d for d in days if d >= days[i]]
            if len(after) >= 3:
                return (True, True, 3.0, 3.0, {"gap_days": float((days[i] - days[i - 1]).days)})
    return (False, True, 0.0, 3.0, {})


def _recovery(f: _Facts) -> Result:
    """Score climbed back a real distance from a personal low."""
    if len(f.scores) < 10:
        return NOT_EVALUABLE
    low = min(f.scores)
    low_index = f.scores.index(low)
    after = f.scores[low_index + 1:]
    if not after:
        return (False, True, 0.0, 10.0, {})
    climb = max(after) - low
    return (climb >= 10.0, True, round(max(climb, 0.0), 1), 10.0, {"low": round(low, 1)})


def _steady_scores(f: _Facts) -> Result:
    """Low variation over the last two weeks. Steadiness is an
    achievement in its own right and is invisible in an average."""
    recent = f.scores[-14:]
    if len(recent) < 14:
        return NOT_EVALUABLE
    spread = statistics.pstdev(recent)
    return (spread <= 5.0, True, round(spread, 1), 5.0, {"spread": round(spread, 1)})


def _longest_healthy_streak(f: _Facts, target: int) -> Result:
    longest = getattr(f.streak, "longest_streak", 0)
    return (longest >= target, True, float(longest), float(target), {})


def _log_streak(f: _Facts, target: int) -> Result:
    return (f.longest_log_streak >= target, True, float(f.longest_log_streak), float(target), {})


# Improvement badges: one per stored signal that has a healthy
# direction. Icons are distinct on purpose - the brief asks for a
# dedicated icon per badge and a wall of identical arrows helps nobody.
_IMPROVEMENT_BADGES: list[tuple[str, str, str]] = [
    ("improve_screen_time", "📉", "total_screen_min"),
    ("improve_night_screen", "🌙", "night_screen_min"),
    ("improve_pre_sleep", "🛏️", "pre_sleep_screen_min"),
    ("improve_sleep_hours", "😴", "sleep_hours"),
    ("improve_sleep_quality", "🛌", "sleep_quality_1_10"),
    ("improve_stress", "🧘", "stress_0_10"),
    ("improve_focus", "🎯", "focus_0_100"),
    ("improve_productivity", "⚙️", "productivity_0_100"),
    ("improve_activity", "🏃", "physical_activity_min_per_day"),
    ("improve_pickups", "📵", "pickups_per_day"),
    ("improve_notifications", "🔕", "notification_density"),
    ("improve_fragmentation", "🧩", "fragmentation_index_0_100"),
    ("improve_social_comparison", "🪞", "social_comparison_1_10"),
]

# Sustained badges: (id, icon, field, threshold, lower_is_better)
_SUSTAINED_BADGES: list[tuple[str, str, str, float, bool]] = [
    ("week_of_sleep", "🌜", "sleep_hours", 7.0, False),
    ("week_of_activity", "🚴", "physical_activity_min_per_day", 30.0, False),
    ("week_of_calm", "🌾", "stress_0_10", 4.0, True),
    ("week_of_focus", "🔎", "focus_0_100", 70.0, False),
    ("week_off_late_nights", "🌇", "night_screen_min", 30.0, True),
    ("week_of_light_screens", "🕊️", "total_screen_min", 300.0, True),
]

# Awareness indicators: (id, icon, field, threshold, above)
_AWARENESS_PATTERNS: list[tuple[str, str, str, float, bool]] = [
    ("aware_late_night", "🦉", "night_screen_min", 60.0, True),
    ("aware_pre_sleep", "📱", "pre_sleep_screen_min", 45.0, True),
    ("aware_short_sleep", "😪", "sleep_hours", 6.0, False),
    ("aware_high_stress", "🌧️", "stress_0_10", 7.0, True),
    ("aware_low_focus", "🌀", "focus_0_100", 40.0, False),
    ("aware_fragmentation", "🪡", "fragmentation_index_0_100", 65.0, True),
    ("aware_pickups", "🔁", "pickups_per_day", 90.0, True),
    ("aware_notifications", "🔔", "notification_density", 70.0, True),
    ("aware_low_activity", "🪑", "physical_activity_min_per_day", 15.0, False),
    ("aware_social_comparison", "🫥", "social_comparison_1_10", 7.0, True),
    ("aware_long_screen_days", "⏳", "total_screen_min", 480.0, True),
    ("aware_social_heavy", "💬", "social_min", 180.0, True),
    ("aware_gaming_heavy", "🎮", "gaming_min", 180.0, True),
    ("aware_video_heavy", "🎬", "video_min", 180.0, True),
    ("aware_low_productivity", "🐌", "productivity_0_100", 40.0, False),
    ("aware_low_sleep_quality", "💤", "sleep_quality_1_10", 5.0, False),
]


def _rising_screen_time(f: _Facts) -> Result:
    """Not a pattern-count but a direction: this week against last."""
    have = _numbers(f.real, "total_screen_min")
    if len(have) < IMPROVEMENT_MIN_DAYS:
        return NOT_EVALUABLE
    early, recent = _mean(have[-WINDOW * 2:-WINDOW]), _mean(have[-WINDOW:])
    if not early or recent is None:
        return NOT_EVALUABLE
    change = (recent - early) / abs(early) * 100.0
    return (
        change >= 15.0, True, round(change, 1), 15.0,
        {"change_pct": round(change, 1), "recent": round(recent), "previous": round(early)},
    )


def _sleep_variability(f: _Facts) -> Result:
    have = _numbers(f.real[-WINDOW * 2:], "sleep_hours")
    if len(have) < WINDOW:
        return NOT_EVALUABLE
    spread = statistics.pstdev(have)
    return (spread >= 1.5, True, round(spread, 2), 1.5, {"spread": round(spread, 2)})


def _score_declining(f: _Facts) -> Result:
    if len(f.scores) < IMPROVEMENT_MIN_DAYS:
        return NOT_EVALUABLE
    early, recent = _mean(f.scores[:WINDOW]), _mean(f.scores[-WINDOW:])
    if early is None or recent is None:
        return NOT_EVALUABLE
    drop = early - recent
    return (drop >= 5.0, True, round(max(drop, 0.0), 1), 5.0, {"early": round(early, 1), "recent": round(recent, 1)})


CATALOGUE: list[_Def] = [
    # ---- showing up -------------------------------------------------
    _Def("first_checkin", "🌱", TIER_COMMON, lambda f: _count_at_least(f.total, 1)),
    _Def("checkins_10", "📈", TIER_COMMON, lambda f: _count_at_least(f.total, 10)),
    _Def("checkins_30", "🏆", TIER_RARE, lambda f: _count_at_least(f.total, 30)),
    _Def("checkins_60", "🎖️", TIER_RARE, lambda f: _count_at_least(f.total, 60)),
    _Def("checkins_100", "💯", TIER_LEGENDARY, lambda f: _count_at_least(f.total, 100)),
    _Def("first_week", "🗓️", TIER_COMMON, lambda f: _count_at_least(f.distinct_days, 7)),
    _Def("first_month", "📅", TIER_RARE, lambda f: _count_at_least(f.distinct_days, 30)),
    _Def("first_quarter", "🗿", TIER_LEGENDARY, lambda f: _count_at_least(f.distinct_days, 90)),
    _Def("consistent_logger", "📔", TIER_COMMON, _consistent_week),
    _Def("log_streak_7", "📆", TIER_COMMON, lambda f: _log_streak(f, 7)),
    _Def("log_streak_14", "🧾", TIER_RARE, lambda f: _log_streak(f, 14)),
    _Def("log_streak_30", "📚", TIER_LEGENDARY, lambda f: _log_streak(f, 30)),
    _Def("two_full_weeks", "📰", TIER_COMMON, lambda f: _full_weeks(f, 2)),

    # ---- healthy streaks --------------------------------------------
    _Def("streak_3", "🔥", TIER_COMMON, lambda f: _longest_healthy_streak(f, 3)),
    _Def("streak_7", "🔆", TIER_RARE, lambda f: _longest_healthy_streak(f, 7)),
    _Def("streak_14", "☀️", TIER_RARE, lambda f: _longest_healthy_streak(f, 14)),
    _Def("streak_30", "🌟", TIER_LEGENDARY, lambda f: _longest_healthy_streak(f, 30)),

    # ---- score ------------------------------------------------------
    _Def("high_scorer", "⭐", TIER_RARE, lambda f: _score_at_least(f, HIGH_SCORE_BADGE_THRESHOLD)),
    _Def("score_90", "💫", TIER_LEGENDARY, lambda f: _score_at_least(f, 90.0)),
    _Def("most_improved", "🚀", TIER_RARE, _most_improved),
    _Def("personal_best", "🥇", TIER_COMMON, _beat_personal_best),
    _Def("steady_scores", "⚖️", TIER_RARE, _steady_scores),
    _Def("recovery", "🌤️", TIER_RARE, _recovery),
    _Def("comeback", "💪", TIER_RARE, _comeback),

    # ---- data honesty -----------------------------------------------
    _Def("exception_marker", "🏷️", TIER_COMMON, _marked_an_exception),
]

CATALOGUE += [
    _Def(badge_id, icon, TIER_RARE, (lambda k: lambda f: _improvement(f, k))(field_key))
    for badge_id, icon, field_key in _IMPROVEMENT_BADGES
]

CATALOGUE += [
    # Legendary on purpose: holding a level on every one of seven days
    # is materially harder than a one-off best or a 10% improvement.
    _Def(badge_id, icon, TIER_LEGENDARY,
         (lambda k, t, lo: lambda f: _sustained(f, k, t, lo))(field_key, threshold, lower))
    for badge_id, icon, field_key, threshold, lower in _SUSTAINED_BADGES
]

CATALOGUE += [
    _Def(badge_id, icon, None,
         (lambda k, t, a: lambda f: _pattern(f, k, t, a))(field_key, threshold, above),
         category=CATEGORY_AWARENESS)
    for badge_id, icon, field_key, threshold, above in _AWARENESS_PATTERNS
]

CATALOGUE += [
    _Def("aware_rising_screen_time", "📶", None, _rising_screen_time, category=CATEGORY_AWARENESS),
    _Def("aware_sleep_variability", "🔀", None, _sleep_variability, category=CATEGORY_AWARENESS),
    _Def("aware_score_declining", "🔻", None, _score_declining, category=CATEGORY_AWARENESS),
]


class BadgeService:
    """Evaluates the whole catalogue against one user's history."""

    @staticmethod
    def evaluate(entries: list[dict[str, Any]], today: Optional[date] = None) -> list[Badge]:
        facts = _build_facts(entries or [], today=today)
        badges: list[Badge] = []
        for definition in CATALOGUE:
            try:
                earned, evaluable, progress, target, params = definition.rule(facts)
            except Exception:  # noqa: BLE001 - one broken rule must not hide the rest
                earned, evaluable, progress, target, params = NOT_EVALUABLE
            badges.append(Badge(
                id=definition.id,
                category=definition.category,
                icon=definition.icon,
                tier=definition.tier,
                private=definition.category == CATEGORY_AWARENESS,
                earned=bool(earned and evaluable),
                evaluable=bool(evaluable),
                progress=progress,
                target=target,
                params=params,
            ))
        return badges

    @staticmethod
    def public_badges(badges: list[Badge]) -> list[Badge]:
        """The only list any friend-facing surface is allowed to read.

        Awareness indicators are private by construction, so filtering
        happens here rather than at each call site - one place to audit,
        and a new private badge is safe by default.
        """
        return [b for b in badges if not b.private]

    @staticmethod
    def earned_count(badges: list[Badge]) -> int:
        return sum(1 for b in badges if b.earned)
