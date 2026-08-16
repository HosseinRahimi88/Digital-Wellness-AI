"""
Tests: forgiving streak behaviour (D-7 / game 12).

The original rule zeroed the chain on any non-healthy day. Twelve days of
real progress erased by one bad Tuesday is punishment dressed up as a
metric, and it is exactly the point at which people stop logging. The rule
now costs a real but survivable amount instead.

The distinctions that matter, and that are easy to get wrong:

  * A LOGGED but unhealthy day is forgivable - that is the "bad day" the
    forgiveness is for.
  * A day with NO entry is not. It is missing data, not a bad day, and
    counting a chain through it would invent history the user never
    claimed. This was a real regression during implementation: treating
    gaps as misses let a chain run backwards across days that were never
    recorded.
  * A day the user marked as an exception is neutral. They already told us
    it was not a normal day; overruling that would make the label useless.
  * `longest_streak` stays strict. It is a record of genuinely consecutive
    healthy days, and letting the forgiving count raise it would make the
    record meaningless.
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from config.gamification_settings import (
    GRACE_DAYS_PER_MONTH,
    MAX_UNABSORBED_MISSES,
    STREAK_PENALTY_DAYS,
)
from services.social.gamification_service import GamificationService

HEALTHY = 85.0
UNHEALTHY = 40.0


def _diary(spec, start=date(2026, 3, 10)):
    """spec: list of (score|None, excluded). None means no entry logged."""
    entries = []
    for offset, (score, excluded) in enumerate(spec):
        if score is None:
            continue  # a genuinely missing day
        entry = {
            "date": (start + timedelta(days=offset)).isoformat(),
            "health_score": score,
        }
        if excluded:
            entry["excluded"] = True
        entries.append(entry)
    return entries, start + timedelta(days=len(spec) - 1)


class TestStreakIsShortenedNotReset(unittest.TestCase):

    def test_long_chain_survives_a_bad_day(self):
        """The headline behaviour: 12 good days plus two bad ones must not
        collapse to zero."""
        entries, today = _diary([(HEALTHY, False)] * 12 + [(UNHEALTHY, False)] * 2)
        info = GamificationService.compute_streak(entries, today=today)
        self.assertGreater(
            info.current_streak, 0,
            "A bad day wiped the whole chain - this is the behaviour D-7 removes",
        )
        # One miss absorbed by grace, one charged at the penalty rate.
        self.assertEqual(info.current_streak, 12 - STREAK_PENALTY_DAYS)
        self.assertEqual(info.shortened_by, STREAK_PENALTY_DAYS)

    def test_first_miss_of_the_month_costs_nothing(self):
        entries, today = _diary([(HEALTHY, False)] * 6 + [(UNHEALTHY, False)])
        info = GamificationService.compute_streak(entries, today=today)
        self.assertEqual(info.current_streak, 6)
        self.assertEqual(info.shortened_by, 0)
        self.assertEqual(info.grace_days_used, 1)
        self.assertEqual(info.grace_days_remaining, GRACE_DAYS_PER_MONTH - 1)

    def test_a_real_lapse_still_ends_the_chain(self):
        """Forgiveness must not become 'the streak never ends'."""
        entries, today = _diary(
            [(HEALTHY, False)] * 10 + [(UNHEALTHY, False)] * (MAX_UNABSORBED_MISSES + 2)
        )
        info = GamificationService.compute_streak(entries, today=today)
        self.assertLess(info.current_streak, 10)


class TestExceptionDaysAreNeutral(unittest.TestCase):

    def test_exception_day_does_not_break_the_chain(self):
        entries, today = _diary(
            [(HEALTHY, False)] * 3 + [(UNHEALTHY, True)] + [(HEALTHY, False)] * 3
        )
        info = GamificationService.compute_streak(entries, today=today)
        self.assertEqual(info.current_streak, 6, "Excluded day should be skipped, not counted as a miss")
        self.assertEqual(info.exception_days_skipped, 1)
        self.assertEqual(info.shortened_by, 0)
        self.assertEqual(info.grace_days_used, 0, "An exception must not consume grace")


class TestMissingDaysAreNotForgiven(unittest.TestCase):

    def test_unlogged_gap_still_ends_the_chain(self):
        """Regression guard: gaps are missing data, not bad days."""
        today = date(2026, 8, 6)
        entries = [
            {"date": (today - timedelta(days=5)).isoformat(), "health_score": 90},
            {"date": (today - timedelta(days=1)).isoformat(), "health_score": 85},
            {"date": today.isoformat(), "health_score": 90},
        ]
        info = GamificationService.compute_streak(entries, today=today)
        self.assertEqual(
            info.current_streak, 2,
            "The chain ran backwards across days that were never logged",
        )


class TestLongestStaysStrict(unittest.TestCase):

    def test_forgiveness_does_not_inflate_the_record(self):
        entries, today = _diary(
            [(HEALTHY, False)] * 6 + [(UNHEALTHY, False)] + [(HEALTHY, False)]
        )
        info = GamificationService.compute_streak(entries, today=today)
        # Current is forgiving (7); the record is not - the longest run of
        # genuinely consecutive healthy days is 6.
        self.assertEqual(info.longest_streak, 6)
        self.assertGreater(info.current_streak, info.longest_streak)

    def test_empty_history_is_all_zeroes(self):
        info = GamificationService.compute_streak([])
        self.assertEqual(info.current_streak, 0)
        self.assertEqual(info.longest_streak, 0)
        self.assertEqual(info.shortened_by, 0)


if __name__ == "__main__":
    unittest.main()
