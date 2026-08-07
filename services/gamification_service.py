"""
Gamification Service
----------------------
Pure, rule-based helpers for the "Journey" product features (Healthy
Streak Tracker, User Level/Progress, Achievement Badges, Journey
Summary). Every input here is a real `HistoryService` entry (built
from real `PredictionService` output) - this module never touches the
ML pipeline, never re-predicts, and never re-derives features. It only
aggregates dates/scores that already exist.

Kept separate from `services/achievement_service.py` on purpose:
`AchievementService` answers one narrow question ("did the score just
improve vs. one other score?") and is already used by the celebration
banner. This module answers a different, broader set of questions
("what badges has this user earned across their whole history?",
"what's their current streak?", "what level are they?") - composing
`AchievementService` would have meant threading extra parameters
through a class that isn't shaped for it, so these are new pure
functions instead, following the existing pattern of one small
service per concern (see `dashboard_service.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional

from config.gamification_settings import (
    CHECKINS_PER_LEVEL,
    CONSISTENT_LOGGER_MIN_ENTRIES_PER_WEEK,
    HEALTHY_DAY_SCORE_THRESHOLD,
    HIGH_SCORE_BADGE_THRESHOLD,
    LEVEL_TITLES,
    MOST_IMPROVED_MIN_DELTA,
)


@dataclass(slots=True)
class StreakInfo:
    current_streak: int = 0
    longest_streak: int = 0
    is_active_today_or_yesterday: bool = False


@dataclass(slots=True)
class LevelInfo:
    level: int
    title: str
    total_checkins: int
    checkins_into_level: int
    checkins_for_next_level: int
    progress_fraction: float


@dataclass(slots=True)
class Badge:
    id: str
    name: str
    description: str
    icon: str
    unlocked: bool


@dataclass(slots=True)
class JourneySummary:
    total_checkins: int
    first_date: Optional[str]
    last_date: Optional[str]
    days_since_first: Optional[int]
    avg_score: Optional[float]
    best_score: Optional[float]
    best_date: Optional[str]
    latest_score: Optional[float]
    improvement_since_first: Optional[float]


class GamificationService:
    """Pure data-shaping helpers - no Streamlit/UI code, no I/O."""

    # ------------------------------------------------------------
    # Streaks
    # ------------------------------------------------------------
    @staticmethod
    def compute_streak(
        entries: list[dict[str, Any]],
        today: Optional[date] = None,
    ) -> StreakInfo:
        """
        `entries` must be sorted ascending by date (HistoryService.get_all()
        already returns them that way). A day counts toward the streak
        when it has a logged entry with health_score >=
        HEALTHY_DAY_SCORE_THRESHOLD. The streak breaks on any gap day or
        any logged-but-unhealthy day.
        """
        if not entries:
            return StreakInfo()

        today = today or datetime.now().date()

        by_date: dict[date, Optional[float]] = {}
        for e in entries:
            d_str = e.get("date")
            if not d_str:
                continue
            try:
                d = date.fromisoformat(d_str)
            except ValueError:
                continue
            by_date[d] = e.get("health_score")

        if not by_date:
            return StreakInfo()

        def is_healthy(d: date) -> bool:
            score = by_date.get(d)
            return score is not None and score >= HEALTHY_DAY_SCORE_THRESHOLD

        # Longest streak: scan the logged days in order, resetting the
        # run whenever a day isn't healthy OR isn't the calendar day
        # right after the previous one (a gap day with no entry breaks
        # the streak just like an unhealthy day does).
        all_days = sorted(by_date.keys())
        longest = running = 0
        previous_day: Optional[date] = None
        for d in all_days:
            if is_healthy(d) and previous_day is not None and d == previous_day + timedelta(days=1):
                running += 1
            elif is_healthy(d):
                running = 1
            else:
                running = 0
            longest = max(longest, running)
            previous_day = d

        # Current streak: walk backwards from today (or yesterday, so a
        # user who hasn't logged *today* yet doesn't lose an otherwise
        # intact streak) as long as each day is healthy.
        current = 0
        cursor = today
        if cursor not in by_date and (cursor - timedelta(days=1)) in by_date:
            cursor = cursor - timedelta(days=1)

        while is_healthy(cursor):
            current += 1
            cursor -= timedelta(days=1)

        active = current > 0 and (today - max(all_days)).days <= 1

        return StreakInfo(
            current_streak=current,
            longest_streak=max(longest, current),
            is_active_today_or_yesterday=active,
        )

    # ------------------------------------------------------------
    # Level / progress
    # ------------------------------------------------------------
    @staticmethod
    def compute_level(entries: list[dict[str, Any]]) -> LevelInfo:
        total = len(entries)
        level_index = min(total // CHECKINS_PER_LEVEL, len(LEVEL_TITLES) - 1)
        level = level_index + 1
        title = LEVEL_TITLES[level_index]

        into_level = total - (level_index * CHECKINS_PER_LEVEL)
        is_max_level = level_index == len(LEVEL_TITLES) - 1
        for_next = CHECKINS_PER_LEVEL if not is_max_level else max(into_level, 1)
        progress = 1.0 if is_max_level else min(into_level / CHECKINS_PER_LEVEL, 1.0)

        return LevelInfo(
            level=level,
            title=title,
            total_checkins=total,
            checkins_into_level=min(into_level, for_next),
            checkins_for_next_level=for_next,
            progress_fraction=progress,
        )

    # ------------------------------------------------------------
    # Badges
    # ------------------------------------------------------------
    @classmethod
    def compute_badges(
        cls,
        entries: list[dict[str, Any]],
        streak_info: Optional[StreakInfo] = None,
    ) -> list[Badge]:
        streak_info = streak_info or cls.compute_streak(entries)
        total = len(entries)

        scores = [e["health_score"] for e in entries if e.get("health_score") is not None]
        first_score = scores[0] if scores else None
        best_score = max(scores) if scores else None

        # Consistent Logger: any single calendar week with enough entries.
        week_counts: dict[str, int] = {}
        for e in entries:
            d_str = e.get("date")
            if not d_str:
                continue
            try:
                iso = date.fromisoformat(d_str).isocalendar()
            except ValueError:
                continue
            key = f"{iso[0]}-W{iso[1]:02d}"
            week_counts[key] = week_counts.get(key, 0) + 1
        has_consistent_week = any(
            c >= CONSISTENT_LOGGER_MIN_ENTRIES_PER_WEEK for c in week_counts.values()
        )

        most_improved = (
            first_score is not None
            and best_score is not None
            and (best_score - first_score) >= MOST_IMPROVED_MIN_DELTA
        )

        badges = [
            Badge(
                id="first_checkin",
                name="First Check-in",
                description="Logged your very first digital wellness check-in.",
                icon="🌱",
                unlocked=total >= 1,
            ),
            Badge(
                id="streak_3",
                name="3-Day Streak",
                description="Kept a healthy score 3 days in a row.",
                icon="🔥",
                unlocked=streak_info.longest_streak >= 3,
            ),
            Badge(
                id="streak_7",
                name="7-Day Streak",
                description="Kept a healthy score a full week in a row.",
                icon="🔥",
                unlocked=streak_info.longest_streak >= 7,
            ),
            Badge(
                id="checkins_10",
                name="10 Check-ins",
                description="Logged 10 check-ins total.",
                icon="📈",
                unlocked=total >= 10,
            ),
            Badge(
                id="checkins_30",
                name="30 Check-ins",
                description="Logged 30 check-ins total.",
                icon="🏆",
                unlocked=total >= 30,
            ),
            Badge(
                id="most_improved",
                name="Most Improved",
                description=f"Improved your score by {MOST_IMPROVED_MIN_DELTA:.0f}+ points since your first check-in.",
                icon="🚀",
                unlocked=most_improved,
            ),
            Badge(
                id="consistent_logger",
                name="Consistent Logger",
                description=f"Logged {CONSISTENT_LOGGER_MIN_ENTRIES_PER_WEEK}+ check-ins in a single week.",
                icon="🗓️",
                unlocked=has_consistent_week,
            ),
            Badge(
                id="high_scorer",
                name="High Scorer",
                description=f"Reached a wellness score of {HIGH_SCORE_BADGE_THRESHOLD:.0f}+.",
                icon="⭐",
                unlocked=best_score is not None and best_score >= HIGH_SCORE_BADGE_THRESHOLD,
            ),
        ]
        return badges

    # ------------------------------------------------------------
    # Journey summary
    # ------------------------------------------------------------
    @staticmethod
    def compute_journey_summary(entries: list[dict[str, Any]]) -> JourneySummary:
        if not entries:
            return JourneySummary(
                total_checkins=0,
                first_date=None,
                last_date=None,
                days_since_first=None,
                avg_score=None,
                best_score=None,
                best_date=None,
                latest_score=None,
                improvement_since_first=None,
            )

        ordered = sorted(entries, key=lambda e: e.get("date", ""))
        scores = [(e.get("date"), e.get("health_score")) for e in ordered if e.get("health_score") is not None]

        avg_score = round(sum(s for _, s in scores) / len(scores), 1) if scores else None
        best_date, best_score = (None, None)
        if scores:
            best_date, best_score = max(scores, key=lambda pair: pair[1])

        first_score = scores[0][1] if scores else None
        latest_score = scores[-1][1] if scores else None
        improvement = (
            round(latest_score - first_score, 1)
            if first_score is not None and latest_score is not None
            else None
        )

        first_date_str = ordered[0].get("date")
        last_date_str = ordered[-1].get("date")
        days_since_first = None
        if first_date_str:
            try:
                days_since_first = (datetime.now().date() - date.fromisoformat(first_date_str)).days
            except ValueError:
                days_since_first = None

        return JourneySummary(
            total_checkins=len(ordered),
            first_date=first_date_str,
            last_date=last_date_str,
            days_since_first=days_since_first,
            avg_score=avg_score,
            best_score=best_score,
            best_date=best_date,
            latest_score=latest_score,
            improvement_since_first=improvement,
        )
