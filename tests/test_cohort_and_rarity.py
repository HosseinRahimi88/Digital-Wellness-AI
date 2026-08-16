"""
Tests: CohortService (35 - Cohort Comparison), LeaderboardService
(31 - Reverse Leaderboard), RareAchievementService (20 - Rare
Achievement System). All three read the real data/train.csv - no
synthetic cohort data.

That dependency is why every class here skips when the dataset is
absent. data/ is gitignored (271 MB), so a packaged build of this
project legitimately ships without it - the services all degrade to
"cohort comparison unavailable" in that case, which is behaviour the
app supports rather than a fault. Failing instead of skipping made a
correctly-packaged archive look broken, and buried the one assertion
that actually matters here: that when the data IS present, it is real
and large enough to compare against.

Run: python3 -m unittest tests.test_cohort_and_rarity -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401

from services.cohort_service import CohortService
from services.leaderboard_service import LeaderboardService
from services.rare_achievement_service import RareAchievementService


class _NeedsCohortData(unittest.TestCase):
    """Skips the whole class when data/train.csv is not in this tree."""

    @classmethod
    def setUpClass(cls):
        if not CohortService.is_available():
            raise unittest.SkipTest("no cohort dataset in this build (data/ is gitignored)")


class TestCohortService(_NeedsCohortData):

    def test_the_dataset_is_real_and_big_enough_to_compare_against(self):
        """Not a tautology next to the skip above: is_available() only
        says a frame loaded. A hundred rows would load fine and make
        every percentile below meaningless."""
        self.assertGreater(CohortService.cohort_size(), 1000)

    def test_percentile_is_monotonic_in_value(self):
        low = CohortService.percentile_for("sleep_hours", 3.0)
        high = CohortService.percentile_for("sleep_hours", 10.0)
        self.assertIsNotNone(low)
        self.assertIsNotNone(high)
        self.assertLess(low, high)

    def test_percentile_bounds_are_0_to_100(self):
        p = CohortService.percentile_for("sleep_hours", 7.0)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 100.0)

    def test_unknown_field_returns_none_not_raise(self):
        self.assertIsNone(CohortService.percentile_for("not_a_real_field_xyz", 5.0))

    def test_health_score_field_alias_resolves(self):
        rows = CohortService.compare_user_to_cohort({"health_score": 80.0})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["field"], "health_score")
        self.assertIsInstance(rows[0]["cohort_percentile"], float)

    def test_compare_skips_none_values_without_raising(self):
        rows = CohortService.compare_user_to_cohort({"sleep_hours": None, "stress_0_10": 3.0})
        fields = [r["field"] for r in rows]
        self.assertNotIn("sleep_hours", fields)
        self.assertIn("stress_0_10", fields)

    def test_cohort_summary_has_expected_shape(self):
        summary = CohortService.cohort_summary("sleep_hours")
        self.assertIsNotNone(summary)
        for key in ("mean", "median", "p25", "p75"):
            self.assertIn(key, summary)


class TestLeaderboardService(_NeedsCohortData):

    def test_low_stress_ranks_favorably(self):
        rows = LeaderboardService.compute_reverse_leaderboard({"stress_0_10": 1.0})
        self.assertEqual(len(rows), 1)
        self.assertGreater(rows[0]["better_than_pct"], 50.0)

    def test_high_stress_ranks_poorly(self):
        rows = LeaderboardService.compute_reverse_leaderboard({"stress_0_10": 9.5})
        self.assertLess(rows[0]["better_than_pct"], 50.0)

    def test_fields_not_in_lower_is_better_are_ignored(self):
        rows = LeaderboardService.compute_reverse_leaderboard({"focus_0_100": 90.0})
        self.assertEqual(rows, [])

    def test_rank_estimate_is_within_cohort_size(self):
        rows = LeaderboardService.compute_reverse_leaderboard({"total_screen_min": 50.0})
        cohort_size = CohortService.cohort_size()
        self.assertLessEqual(rows[0]["rank_estimate"], cohort_size)
        self.assertGreaterEqual(rows[0]["rank_estimate"], 0)

    def test_results_sorted_best_first(self):
        rows = LeaderboardService.compute_reverse_leaderboard({
            "stress_0_10": 9.5,       # poor rank
            "total_screen_min": 10.0,  # excellent rank (very low screen time)
        })
        self.assertGreaterEqual(rows[0]["better_than_pct"], rows[-1]["better_than_pct"])


class TestRareAchievementService(_NeedsCohortData):

    def _entries(self, n, health_score=90.0):
        return [
            {"date": f"2026-01-{5+i:02d}", "day_of_week": "Monday", "health_score": health_score}
            for i in range(n)
        ]

    def test_no_achievements_for_average_values(self):
        achievements = RareAchievementService.compute_rare_achievements(
            {"sleep_hours": 7.0, "stress_0_10": 5.0}, entries=[]
        )
        self.assertEqual(achievements, [])

    def test_extreme_low_stress_unlocks_a_tier(self):
        achievements = RareAchievementService.compute_rare_achievements(
            {"stress_0_10": 0.0}, entries=[]
        )
        self.assertTrue(any("Stress" in a.name for a in achievements))

    def test_extreme_high_sleep_unlocks_a_tier(self):
        achievements = RareAchievementService.compute_rare_achievements(
            {"sleep_hours": 12.0}, entries=[]
        )
        self.assertTrue(any("Sleep" in a.name for a in achievements))

    def test_long_streak_unlocks_streak_achievement(self):
        entries = self._entries(10, health_score=90.0)  # well above HEALTHY_DAY_SCORE_THRESHOLD
        achievements = RareAchievementService.compute_rare_achievements({}, entries=entries)
        self.assertTrue(any("Streak" in a.name for a in achievements))

    def test_no_entries_and_average_values_yields_empty_list_not_crash(self):
        achievements = RareAchievementService.compute_rare_achievements({}, entries=[])
        self.assertEqual(achievements, [])

    def test_achievements_sorted_legendary_first(self):
        # stress=0 and screen_time=0 should both be extreme (Legendary-tier).
        achievements = RareAchievementService.compute_rare_achievements(
            {"stress_0_10": 0.0, "total_screen_min": 0.0, "sleep_hours": 7.0}, entries=[]
        )
        self.assertTrue(achievements)
        tier_rank = {"Legendary": 0, "Epic": 1, "Rare": 2}
        ranks = [tier_rank[a.tier] for a in achievements]
        self.assertEqual(ranks, sorted(ranks))


if __name__ == "__main__":
    unittest.main()
