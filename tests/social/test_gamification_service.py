"""
Tests for services/social/gamification_service.py - pure arithmetic over
HistoryService-shaped entry dicts, no Streamlit/ML involved.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

PROJECT_ROOT = paths.PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.social.gamification_service import GamificationService


def _entry(d: date, score: float) -> dict:
    return {"date": d.isoformat(), "health_score": score}


class TestStreak(unittest.TestCase):
    def test_empty_history_has_no_streak(self):
        info = GamificationService.compute_streak([])
        self.assertEqual(info.current_streak, 0)
        self.assertEqual(info.longest_streak, 0)
        self.assertFalse(info.is_active_today_or_yesterday)

    def test_consecutive_healthy_days_build_streak(self):
        today = date(2026, 8, 6)
        entries = [
            _entry(today - timedelta(days=2), 80),
            _entry(today - timedelta(days=1), 85),
            _entry(today, 90),
        ]
        info = GamificationService.compute_streak(entries, today=today)
        self.assertEqual(info.current_streak, 3)
        self.assertEqual(info.longest_streak, 3)
        self.assertTrue(info.is_active_today_or_yesterday)

    def test_unhealthy_day_breaks_streak(self):
        today = date(2026, 8, 6)
        entries = [
            _entry(today - timedelta(days=2), 20),
            _entry(today - timedelta(days=1), 85),
            _entry(today, 90),
        ]
        info = GamificationService.compute_streak(entries, today=today)
        self.assertEqual(info.current_streak, 2)

    def test_gap_day_breaks_streak(self):
        today = date(2026, 8, 6)
        entries = [
            _entry(today - timedelta(days=5), 90),
            _entry(today - timedelta(days=1), 85),
            _entry(today, 90),
        ]
        info = GamificationService.compute_streak(entries, today=today)
        self.assertEqual(info.current_streak, 2)
        self.assertEqual(info.longest_streak, 2)

    def test_missing_today_still_counts_streak_from_yesterday(self):
        today = date(2026, 8, 6)
        entries = [
            _entry(today - timedelta(days=2), 80),
            _entry(today - timedelta(days=1), 85),
        ]
        info = GamificationService.compute_streak(entries, today=today)
        self.assertEqual(info.current_streak, 2)
        self.assertTrue(info.is_active_today_or_yesterday)


class TestLevel(unittest.TestCase):
    def test_new_user_is_level_one(self):
        info = GamificationService.compute_level([])
        self.assertEqual(info.level, 1)
        self.assertEqual(info.total_checkins, 0)
        self.assertEqual(info.progress_fraction, 0.0)

    def test_level_increases_with_checkins(self):
        entries = [_entry(date(2026, 1, i + 1), 70) for i in range(12)]
        info = GamificationService.compute_level(entries)
        self.assertGreater(info.level, 1)
        self.assertEqual(info.total_checkins, 12)

    def test_max_level_does_not_exceed_title_list(self):
        entries = [_entry(date(2026, 1, 1) + timedelta(days=i), 70) for i in range(500)]
        info = GamificationService.compute_level(entries)
        self.assertLessEqual(info.level, 10)
        self.assertEqual(info.progress_fraction, 1.0)


class TestBadges(unittest.TestCase):
    def test_no_history_no_badges_unlocked(self):
        badges = GamificationService.compute_badges([])
        self.assertTrue(all(not b.unlocked for b in badges))

    def test_first_checkin_badge_unlocks_on_one_entry(self):
        badges = GamificationService.compute_badges([_entry(date(2026, 1, 1), 50)])
        first = next(b for b in badges if b.id == "first_checkin")
        self.assertTrue(first.unlocked)

    def test_most_improved_badge(self):
        entries = [
            _entry(date(2026, 1, 1), 40),
            _entry(date(2026, 1, 2), 60),
        ]
        badges = GamificationService.compute_badges(entries)
        badge = next(b for b in badges if b.id == "most_improved")
        self.assertTrue(badge.unlocked)


class TestJourneySummary(unittest.TestCase):
    def test_empty_history(self):
        summary = GamificationService.compute_journey_summary([])
        self.assertEqual(summary.total_checkins, 0)
        self.assertIsNone(summary.avg_score)

    def test_summary_computes_improvement(self):
        entries = [
            _entry(date(2026, 1, 1), 50),
            _entry(date(2026, 1, 5), 65),
        ]
        summary = GamificationService.compute_journey_summary(entries)
        self.assertEqual(summary.total_checkins, 2)
        self.assertEqual(summary.improvement_since_first, 15.0)
        self.assertEqual(summary.best_score, 65)


if __name__ == "__main__":
    unittest.main()
