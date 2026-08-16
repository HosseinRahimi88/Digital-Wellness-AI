"""
Tests: AchievementService + ImprovementPlanService (pure rule-based
presentation logic, no model/training involved).

Run: python3 -m unittest tests.test_achievement_and_plan -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401  (sys.path bootstrap)

from services.achievement_service import AchievementService
from services.improvement_plan_service import ImprovementPlanService


class TestAchievementService(unittest.TestCase):

    def test_no_achievement_when_either_score_missing(self):
        self.assertFalse(AchievementService.evaluate(None, 50.0).unlocked)
        self.assertFalse(AchievementService.evaluate(50.0, None).unlocked)
        self.assertFalse(AchievementService.evaluate(None, None).unlocked)

    def test_no_achievement_for_tiny_noise_delta(self):
        result = AchievementService.evaluate(current_score=50.3, previous_score=50.0)
        self.assertFalse(result.unlocked)

    def test_achievement_unlocked_for_meaningful_improvement(self):
        result = AchievementService.evaluate(current_score=65.0, previous_score=50.0)
        self.assertTrue(result.unlocked)
        self.assertIn("Congratulations", result.message)

    def test_no_achievement_for_decline(self):
        result = AchievementService.evaluate(current_score=40.0, previous_score=50.0)
        self.assertFalse(result.unlocked)

    def test_zero_previous_score_does_not_crash(self):
        """Percent-change against a zero baseline must not raise
        ZeroDivisionError - it should fall back to the point-delta path."""
        result = AchievementService.evaluate(current_score=5.0, previous_score=0.0)
        self.assertIsNone(result.delta_percent)
        self.assertTrue(result.unlocked)  # +5 pts clears MIN_POINT_DELTA


class TestImprovementPlanService(unittest.TestCase):

    def setUp(self):
        self.service = ImprovementPlanService()

    def test_plan_has_seven_days_for_empty_user_data(self):
        """No user_data at all (e.g. corrupted/missing history entry)
        must still produce a full, non-crashing 7-day plan."""
        plan = self.service.generate(health_class=None, wellness_score=None, user_data=None)
        self.assertEqual(len(plan.days), 7)
        self.assertEqual(plan.days[-1].theme, "Reflect & Reset")

    def test_plan_focuses_on_flagged_habit_areas(self):
        plan = self.service.generate(
            health_class="At Risk",
            wellness_score=25.0,
            user_data={"sleep_hours": 4.0, "stress_0_10": 9.0},
        )
        self.assertIn("Sleep Recovery", plan.focus_areas)
        self.assertIn("Stress Reset", plan.focus_areas)

    def test_plan_defaults_to_maintenance_when_nothing_needs_work(self):
        plan = self.service.generate(
            health_class="Healthy",
            wellness_score=95.0,
            user_data={
                "sleep_hours": 8.0,
                "social_min": 20.0,
                "stress_0_10": 1.0,
                "physical_activity_min_per_day": 60.0,
                "notifications_per_day": 10.0,
                "focus_0_100": 90.0,
            },
        )
        self.assertEqual(plan.focus_areas, ["Maintain Your Momentum"])

    def test_malformed_field_types_do_not_crash_rule_selection(self):
        """A non-numeric value in a habit field (corrupted history entry)
        must be skipped, not raise inside the rule lambdas."""
        plan = self.service.generate(
            health_class="Moderate",
            wellness_score=55.0,
            user_data={"sleep_hours": "not-a-number", "stress_0_10": None},
        )
        self.assertEqual(len(plan.days), 7)


if __name__ == "__main__":
    unittest.main()
