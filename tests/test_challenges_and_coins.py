"""
Tests: WeeklyChallengeService (16 - Weekly Challenges), FocusCoinsService
(17 - Focus Coins).

Run: python3 -m unittest tests.test_challenges_and_coins -v
"""

from __future__ import annotations

import unittest
from datetime import date

import tests._test_support  # noqa: F401

from services.weekly_challenge_service import WeeklyChallengeService
from services.focus_coins_service import FocusCoinsService


def _entry(date_str, health_score, day_of_week="Monday", **fields):
    entry = {
        "user_id": "alice", "date": date_str, "day_of_week": day_of_week,
        "health_score": health_score,
    }
    entry.update(fields)
    return entry


class TestWeeklyChallengeService(unittest.TestCase):

    def test_daily_checkin_progress_counts_distinct_days_this_week(self):
        today = date(2026, 1, 7)  # a Wednesday
        entries = [
            _entry("2026-01-05", 80.0),  # Monday, same ISO week
            _entry("2026-01-06", 80.0),  # Tuesday, same week
            _entry("2025-12-29", 80.0),  # different week - should not count
        ]
        challenges = WeeklyChallengeService.generate_challenges(entries, today=today)
        daily = next(c for c in challenges if c.id == "daily_checkin_streak")
        self.assertEqual(daily.progress, 2)
        self.assertFalse(daily.completed)

    def test_daily_checkin_completes_at_seven_days(self):
        today = date(2026, 1, 11)  # Sunday of that ISO week
        entries = [_entry(f"2026-01-{5+i:02d}", 80.0) for i in range(7)]
        challenges = WeeklyChallengeService.generate_challenges(entries, today=today)
        daily = next(c for c in challenges if c.id == "daily_checkin_streak")
        self.assertTrue(daily.completed)

    def test_no_challenges_crash_with_empty_history(self):
        challenges = WeeklyChallengeService.generate_challenges([])
        self.assertIsInstance(challenges, list)
        # Daily check-in challenge always generates (progress 0/7).
        self.assertTrue(any(c.id == "daily_checkin_streak" for c in challenges))

    def test_beat_typical_score_challenge_appears_with_enough_history(self):
        today = date(2026, 1, 20)
        entries = [
            _entry("2026-01-01", 50.0), _entry("2026-01-02", 55.0), _entry("2026-01-03", 60.0),
            _entry("2026-01-19", 90.0),  # this week, well above typical
        ]
        challenges = WeeklyChallengeService.generate_challenges(entries, today=today)
        beat = next((c for c in challenges if c.id == "beat_your_typical_score"), None)
        self.assertIsNotNone(beat)
        self.assertTrue(beat.completed)


class TestFocusCoinsService(unittest.TestCase):

    def test_zero_balance_with_no_activity(self):
        balance = FocusCoinsService.compute_balance([])
        self.assertEqual(balance.total, 0)

    def test_checkins_contribute_coins(self):
        entries = [_entry(f"2026-01-{5+i:02d}", 50.0) for i in range(3)]
        balance = FocusCoinsService.compute_balance(entries)
        self.assertEqual(balance.from_checkins, 3 * 5)
        self.assertGreaterEqual(balance.total, balance.from_checkins)

    def test_completed_plan_tasks_and_commitments_add_coins(self):
        balance_without = FocusCoinsService.compute_balance([], completed_plan_tasks=0, completed_commitments=0)
        balance_with = FocusCoinsService.compute_balance([], completed_plan_tasks=4, completed_commitments=2)
        self.assertGreater(balance_with.total, balance_without.total)
        self.assertEqual(balance_with.from_plan_tasks, 4 * 3)
        self.assertEqual(balance_with.from_commitments, 2 * 25)

    def test_negative_counts_do_not_produce_negative_coins(self):
        balance = FocusCoinsService.compute_balance([], completed_plan_tasks=-5, completed_commitments=-1)
        self.assertEqual(balance.from_plan_tasks, 0)
        self.assertEqual(balance.from_commitments, 0)

    def test_total_is_sum_of_components(self):
        entries = [_entry(f"2026-01-{5+i:02d}", 90.0) for i in range(3)]
        balance = FocusCoinsService.compute_balance(entries, completed_plan_tasks=2, completed_commitments=1)
        expected = (
            balance.from_checkins + balance.from_streak + balance.from_plan_tasks
            + balance.from_commitments + balance.from_badges
        )
        self.assertEqual(balance.total, expected)


if __name__ == "__main__":
    unittest.main()
