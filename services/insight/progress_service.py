"""
Progress Service
-------------------
The "am I actually getting anywhere?" layer (P1 items 26-30): Small
Wins, Personal Best, Before/After, and Decision Replay.

Everything here is computed from real HistoryService entries the
prediction pipeline already produced. No ML calls, no re-prediction,
no invented numbers - if the history doesn't support a claim, the
corresponding field comes back `None` and the UI shows nothing rather
than a fabricated milestone.

Streaks deliberately are NOT reimplemented here: services/
gamification_service.py already owns that logic (and its own tests),
so this service composes it instead of maintaining a second, drifting
copy of the same rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from services.social.gamification_service import GamificationService

# A day-over-day score move smaller than this is inside the noise band
# of a tree-ensemble regressor on nearly-identical inputs - calling it
# a "win" would be false precision. Same spirit as
# FuturePathService.is_delta_meaningful().
MIN_MEANINGFUL_DELTA = 1.5

# Before/After needs enough days on each side to be a comparison rather
# than two anecdotes.
BEFORE_AFTER_MIN_DAYS_PER_SIDE = 3

# Standard deviation of the recent half at or above which the run counts
# as swinging rather than steady. Calibrated against the 0-100 score:
# +/-8 points day to day is the point where a weekly average stops
# describing any actual day the user had.
VOLATILE_SD = 8.0

# A flat run only deserves to be called a success if the level it is
# flat AT is a good one. Below this, "steady" means stuck.
STEADY_STRONG_SCORE = 70.0


def _stdev(values: list[float]) -> float:
    """Population standard deviation; 0 for a single value."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def _consistency_from_sd(sd: float) -> float:
    """Spread expressed as a 0-1 steadiness score.

    1.0 is an identical score every day; it reaches 0 at twice the
    volatility threshold, so the number degrades smoothly instead of
    snapping between two states the way a bare flag would.
    """
    return max(0.0, min(1.0, 1.0 - (sd / (VOLATILE_SD * 2))))

# Habit fields worth calling out individually in a Small Win. Each maps
# to (label, "higher is better?").
_WIN_FIELDS: dict[str, tuple[str, bool]] = {
    "sleep_hours": ("Sleep duration", True),
    "focus_0_100": ("Focus", True),
    "productivity_0_100": ("Productivity", True),
    "physical_activity_min_per_day": ("Physical activity", True),
    "total_screen_min": ("Total screen time", False),
    "social_min": ("Social media time", False),
    "stress_0_10": ("Stress", False),
}

# Relative change (fraction) a habit field must move before it counts.
_WIN_FIELD_MIN_RELATIVE_CHANGE = 0.10


@dataclass(slots=True)
class SmallWin:
    field_name: str
    label: str
    previous_value: float
    current_value: float
    delta: float
    higher_is_better: bool


@dataclass(slots=True)
class PersonalBest:
    metric: str
    label: str
    value: float
    achieved_on: str
    is_new: bool  # True when the most recent entry set it


@dataclass(slots=True)
class BeforeAfter:
    available: bool
    before_days: int = 0
    after_days: int = 0
    before_avg_score: Optional[float] = None
    after_avg_score: Optional[float] = None
    delta: Optional[float] = None
    is_meaningful: bool = False
    split_date: Optional[str] = None
    # Direction alone cannot tell "held a good level steadily" apart
    # from "went nowhere", and both used to come back as the same
    # not-meaningful delta. These carry the second axis - how much the
    # score moves around underneath the average - so consistency and
    # improvement stop being the same claim.
    before_sd: Optional[float] = None
    after_sd: Optional[float] = None
    consistency: Optional[float] = None      # 0-1, higher = steadier now
    pattern: str = ""                        # see ProgressService._pattern


@dataclass(slots=True)
class DecisionReplayStep:
    date: str
    health_score: Optional[float]
    health_class: Optional[str]
    top_shap_feature: Optional[str]
    delta_from_previous: Optional[float]


@dataclass(slots=True)
class ProgressSummary:
    entry_count: int
    small_wins: list[SmallWin] = field(default_factory=list)
    personal_bests: list[PersonalBest] = field(default_factory=list)
    before_after: Optional[BeforeAfter] = None
    replay: list[DecisionReplayStep] = field(default_factory=list)
    current_streak: int = 0
    longest_streak: int = 0


def _num(entry: dict[str, Any], key: str) -> Optional[float]:
    value = entry.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ProgressService:
    """Aggregates real history entries into progress-flavoured views."""

    @staticmethod
    def small_wins(entries: list[dict[str, Any]]) -> list[SmallWin]:
        """
        Genuine improvements between the two most recent check-ins.
        Requires both a meaningful absolute AND relative move, so a
        rounding-level wobble on a large number (e.g. 480 -> 478
        screen minutes) never gets celebrated.
        """
        if len(entries) < 2:
            return []
        previous, current = entries[-2], entries[-1]

        wins: list[SmallWin] = []
        for field_name, (label, higher_is_better) in _WIN_FIELDS.items():
            before, after = _num(previous, field_name), _num(current, field_name)
            if before is None or after is None:
                continue
            delta = after - before
            improved = delta > 0 if higher_is_better else delta < 0
            if not improved:
                continue
            scale = max(abs(before), 1.0)
            if abs(delta) / scale < _WIN_FIELD_MIN_RELATIVE_CHANGE:
                continue
            wins.append(SmallWin(
                field_name=field_name, label=label,
                previous_value=round(before, 2), current_value=round(after, 2),
                delta=round(delta, 2), higher_is_better=higher_is_better,
            ))

        wins.sort(key=lambda w: abs(w.delta) / max(abs(w.previous_value), 1.0), reverse=True)
        return wins

    @staticmethod
    def personal_bests(entries: list[dict[str, Any]]) -> list[PersonalBest]:
        """Best value ever recorded per tracked metric, plus whether the
        latest entry is the one that set it."""
        if not entries:
            return []

        latest_date = entries[-1].get("date")
        bests: list[PersonalBest] = []

        specs = [("health_score", "Wellness score", True)] + [
            (name, label, higher) for name, (label, higher) in _WIN_FIELDS.items()
        ]

        for metric, label, higher_is_better in specs:
            scored = [(e, _num(e, metric)) for e in entries]
            scored = [(e, v) for e, v in scored if v is not None]
            if not scored:
                continue
            best_entry, best_value = (
                max(scored, key=lambda pair: pair[1]) if higher_is_better
                else min(scored, key=lambda pair: pair[1])
            )
            bests.append(PersonalBest(
                metric=metric, label=label, value=round(best_value, 2),
                achieved_on=best_entry.get("date", ""),
                is_new=best_entry.get("date") == latest_date and len(entries) > 1,
            ))
        return bests

    @staticmethod
    def before_after(entries: list[dict[str, Any]], split_index: Optional[int] = None) -> BeforeAfter:
        """
        Split the history in two and compare average wellness score.
        Defaults to the midpoint; `split_index` lets a caller anchor the
        comparison on a specific day (e.g. the day a commitment started).
        """
        usable = [e for e in entries if _num(e, "health_score") is not None]
        if len(usable) < BEFORE_AFTER_MIN_DAYS_PER_SIDE * 2:
            return BeforeAfter(available=False)

        idx = split_index if split_index is not None else len(usable) // 2
        idx = max(BEFORE_AFTER_MIN_DAYS_PER_SIDE, min(idx, len(usable) - BEFORE_AFTER_MIN_DAYS_PER_SIDE))

        before, after = usable[:idx], usable[idx:]
        before_scores = [_num(e, "health_score") for e in before]
        after_scores = [_num(e, "health_score") for e in after]
        before_avg = sum(before_scores) / len(before_scores)
        after_avg = sum(after_scores) / len(after_scores)
        delta = after_avg - before_avg

        before_sd = _stdev(before_scores)
        after_sd = _stdev(after_scores)
        consistency = _consistency_from_sd(after_sd)

        return BeforeAfter(
            available=True,
            before_days=len(before), after_days=len(after),
            before_avg_score=round(before_avg, 2), after_avg_score=round(after_avg, 2),
            delta=round(delta, 2), is_meaningful=abs(delta) >= MIN_MEANINGFUL_DELTA,
            split_date=after[0].get("date"),
            before_sd=round(before_sd, 2), after_sd=round(after_sd, 2),
            consistency=round(consistency, 3),
            pattern=ProgressService._pattern(delta, after_avg, after_sd),
        )

    @staticmethod
    def _pattern(delta: float, after_avg: float, after_sd: float) -> str:
        """Name what the two halves actually show, on two axes at once.

        Direction and steadiness are independent, and reporting only
        direction is what made "held a strong level all week" and "went
        nowhere" come back as the same not-meaningful delta - the first
        is a success the app was calling a non-event.

        Returned keys (the client owns the wording):
          improving_steady    rose, and without wild swings
          improving_volatile  rose on average, but the days swing hard
          steady_strong       flat, low spread, already at a good level
          steady_low          flat, low spread, stuck at a low level
          volatile            flat on average, but swinging underneath
          declining_steady    fell consistently
          declining_volatile  fell, with big swings
        """
        rising = delta >= MIN_MEANINGFUL_DELTA
        falling = delta <= -MIN_MEANINGFUL_DELTA
        volatile = after_sd >= VOLATILE_SD

        if rising:
            return "improving_volatile" if volatile else "improving_steady"
        if falling:
            return "declining_volatile" if volatile else "declining_steady"
        if volatile:
            return "volatile"
        return "steady_strong" if after_avg >= STEADY_STRONG_SCORE else "steady_low"

    @staticmethod
    def decision_replay(entries: list[dict[str, Any]], limit: int = 14) -> list[DecisionReplayStep]:
        """
        The user's recent history as an ordered, replayable timeline:
        each day's score, class, dominant SHAP driver, and move from the
        previous day - the raw material for "walk me through how I got
        here" without re-running any prediction.
        """
        recent = entries[-limit:] if limit else entries
        steps: list[DecisionReplayStep] = []
        previous_score: Optional[float] = None

        for entry in recent:
            score = _num(entry, "health_score")
            delta = round(score - previous_score, 2) if (score is not None and previous_score is not None) else None
            steps.append(DecisionReplayStep(
                date=entry.get("date", ""),
                health_score=round(score, 2) if score is not None else None,
                health_class=entry.get("health_class"),
                top_shap_feature=entry.get("top_shap_feature"),
                delta_from_previous=delta,
            ))
            if score is not None:
                previous_score = score
        return steps

    @classmethod
    def summarize(cls, entries: list[dict[str, Any]], today: Optional[date] = None) -> ProgressSummary:
        streak = GamificationService.compute_streak(entries, today=today)
        return ProgressSummary(
            entry_count=len(entries),
            small_wins=cls.small_wins(entries),
            personal_bests=cls.personal_bests(entries),
            before_after=cls.before_after(entries),
            replay=cls.decision_replay(entries),
            current_streak=getattr(streak, "current_streak", 0),
            longest_streak=getattr(streak, "longest_streak", 0),
        )
