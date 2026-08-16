"""
Weekly Challenge Service
---------------------------
"Weekly Challenges" (feature 16): a handful of auto-generated,
personalized challenges evaluated against the current ISO week's real
HistoryService entries. Every target is derived from this specific
user's own real history - never a generic hardcoded number - by
reusing services/analytics_service.py's existing baseline methods
(compute_typical_day_profile, detect_exception_days) rather than
re-deriving personal averages a second time.

No ML/model calls, no fabricated targets: a challenge that can't be
grounded in enough real history yet is simply omitted (graceful
degradation), same contract as every AnalyticsService method.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from services.analytics_service import AnalyticsService

# Daily check-in streak challenge target (7 = every day this week).
DAILY_CHECKIN_TARGET_DAYS = 7

# "Screen Time Discipline": stay at/under your own typical
# total_screen_min on at least this many days this week.
SCREEN_DISCIPLINE_TARGET_DAYS = 4


@dataclass(slots=True)
class Challenge:
    id: str
    title: str
    description: str
    icon: str
    progress: int
    target: int
    completed: bool
    # The English title/description above are what the Streamlit page has
    # always rendered. The web client is four-language, so it re-writes
    # both from `id` and substitutes these numbers instead - otherwise a
    # Persian page would show an English challenge. Keeping the numbers
    # here means the client never has to parse them back out of a
    # sentence, and never invents a target of its own.
    params: dict[str, float] = field(default_factory=dict)


class WeeklyChallengeService:
    """Generates + evaluates this week's personalized challenges."""

    @staticmethod
    def _current_week_entries(entries: list[dict[str, Any]], today: Optional[date] = None) -> list[dict[str, Any]]:
        today = today or datetime.now().date()
        current_key = today.isocalendar()[:2]
        result = []
        for e in entries:
            d_str = e.get("date")
            if not d_str:
                continue
            try:
                d = date.fromisoformat(d_str)
            except ValueError:
                continue
            if d.isocalendar()[:2] == current_key:
                result.append(e)
        return result

    @classmethod
    def _daily_checkin_challenge(cls, week_entries: list[dict[str, Any]]) -> Challenge:
        distinct_days = len({e.get("date") for e in week_entries if e.get("date")})
        progress = min(distinct_days, DAILY_CHECKIN_TARGET_DAYS)
        return Challenge(
            id="daily_checkin_streak",
            title="Daily Check-in Streak",
            description="Log a check-in every day this week.",
            icon="🗓️",
            progress=progress,
            target=DAILY_CHECKIN_TARGET_DAYS,
            completed=progress >= DAILY_CHECKIN_TARGET_DAYS,
        )

    @classmethod
    def _beat_typical_score_challenge(
        cls, week_entries: list[dict[str, Any]], typical_profile: Optional[dict[str, Any]]
    ) -> Optional[Challenge]:
        if typical_profile is None:
            return None
        profile_df = typical_profile["profile"]
        typical_row = profile_df[profile_df["Metric"] == "Wellness Score"]
        if typical_row.empty:
            return None
        typical_score = float(typical_row.iloc[0]["Typical (avg)"])

        week_scores = [e["health_score"] for e in week_entries if e.get("health_score") is not None]
        if not week_scores:
            progress, completed = 0, False
        else:
            week_avg = sum(week_scores) / len(week_scores)
            completed = week_avg >= typical_score
            progress = 1 if completed else 0

        return Challenge(
            id="beat_your_typical_score",
            title="Beat Your Typical Score",
            description=f"Average {typical_score:.1f}+ this week - your own personal typical score.",
            icon="📈",
            progress=progress,
            target=1,
            completed=completed,
            params={"typical_score": round(typical_score, 1)},
        )

    @classmethod
    def _screen_discipline_challenge(
        cls, week_entries: list[dict[str, Any]], typical_profile: Optional[dict[str, Any]]
    ) -> Optional[Challenge]:
        if typical_profile is None:
            return None
        profile_df = typical_profile["profile"]
        typical_row = profile_df[profile_df["Metric"] == "Total Screen Time (min)"]
        if typical_row.empty:
            return None
        typical_screen = float(typical_row.iloc[0]["Typical (avg)"])

        days_at_or_under = sum(
            1 for e in week_entries
            if e.get("total_screen_min") is not None and e["total_screen_min"] <= typical_screen
        )
        progress = min(days_at_or_under, SCREEN_DISCIPLINE_TARGET_DAYS)
        return Challenge(
            id="screen_time_discipline",
            title="Screen Time Discipline",
            description=(
                f"Stay at or under your typical screen time ({typical_screen:.0f} min) "
                f"on {SCREEN_DISCIPLINE_TARGET_DAYS} days this week."
            ),
            icon="📵",
            progress=progress,
            target=SCREEN_DISCIPLINE_TARGET_DAYS,
            completed=progress >= SCREEN_DISCIPLINE_TARGET_DAYS,
            params={"typical_screen": round(typical_screen)},
        )

    @classmethod
    def _steady_week_challenge(
        cls, week_entries: list[dict[str, Any]], all_entries: list[dict[str, Any]]
    ) -> Optional[Challenge]:
        exceptions = AnalyticsService.detect_exception_days(all_entries)
        if exceptions is None:
            return None
        week_dates = {e.get("date") for e in week_entries}
        exception_dates_this_week = {e["date"] for e in exceptions if e.get("date") in week_dates}
        completed = len(week_dates) > 0 and not exception_dates_this_week
        return Challenge(
            id="steady_week",
            title="Steady Week",
            description="Get through this week without a statistical outlier day vs. your own baseline.",
            icon="⚖️",
            progress=1 if completed else 0,
            target=1,
            completed=completed,
        )

    @classmethod
    def generate_challenges(
        cls, entries: list[dict[str, Any]], today: Optional[date] = None
    ) -> list[Challenge]:
        """Every challenge this user's real history can currently support."""
        week_entries = cls._current_week_entries(entries, today=today)
        typical_profile = AnalyticsService.compute_typical_day_profile(entries)

        challenges = [cls._daily_checkin_challenge(week_entries)]
        for builder in (cls._beat_typical_score_challenge, cls._screen_discipline_challenge):
            challenge = builder(week_entries, typical_profile)
            if challenge is not None:
                challenges.append(challenge)
        steady = cls._steady_week_challenge(week_entries, entries)
        if steady is not None:
            challenges.append(steady)

        return challenges
