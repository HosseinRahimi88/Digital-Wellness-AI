"""
Tests: AnalyticsService's Relationships & Opportunities methods -
compute_field_correlations / build_relationship_scatter (29),
compute_habit_domino_chain (30), detect_golden_hour (44),
detect_leverage_day (46).

Run: python3 -m unittest tests.insight.test_analytics_relationships -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401  (sys.path bootstrap)

from services.insight.analytics_service import AnalyticsService


def _entry(date_str, day_of_week, health_score, recorded_at, **fields):
    entry = {
        "user_id": "alice",
        "date": date_str,
        "day_of_week": day_of_week,
        "health_score": health_score,
        "recorded_at": recorded_at,
    }
    entry.update(fields)
    return entry


class TestFieldCorrelations(unittest.TestCase):
    """Feature 29."""

    def test_none_below_minimum_entries(self):
        entries = [
            _entry(f"2026-01-{5+i:02d}", "Monday", 50.0 + i, "2026-01-05T08:00:00", sleep_hours=5.0 + i)
            for i in range(5)  # one short of MIN_ENTRIES_FOR_CORRELATION (6)
        ]
        self.assertIsNone(AnalyticsService.compute_field_correlations(entries))

    def test_perfectly_linear_fields_correlate_at_1(self):
        # health_score = 10 * sleep_hours, exactly - perfect correlation.
        sleep = [5, 5.5, 6, 7, 8, 9]
        entries = [
            _entry(f"2026-01-{5+i:02d}", "Monday", 10 * s, "2026-01-05T08:00:00", sleep_hours=s)
            for i, s in enumerate(sleep)
        ]
        corr = AnalyticsService.compute_field_correlations(entries)
        self.assertIsNotNone(corr)
        self.assertAlmostEqual(corr.loc["health_score", "sleep_hours"], 1.0, places=2)

    def test_constant_field_excluded_not_crashed(self):
        entries = [
            _entry(f"2026-01-{5+i:02d}", "Monday", 50.0 + i, "2026-01-05T08:00:00", sleep_hours=7.0)
            for i in range(6)
        ]
        corr = AnalyticsService.compute_field_correlations(entries)
        # sleep_hours is constant (zero variance) - must be excluded
        # entirely, and since it was the only other field, result is None.
        self.assertIsNone(corr)

    def test_scatter_pairs_are_real_paired_values(self):
        entries = [
            _entry(f"2026-01-{5+i:02d}", "Monday", 50.0 + i, "2026-01-05T08:00:00", sleep_hours=5.0 + i)
            for i in range(6)
        ]
        scatter = AnalyticsService.build_relationship_scatter(entries, "health_score", "sleep_hours")
        self.assertIsNotNone(scatter)
        self.assertEqual(len(scatter), 6)


class TestHabitDominoChain(unittest.TestCase):
    """Feature 30."""

    def test_none_below_minimum_entries(self):
        entries = [_entry("2026-01-05", "Monday", 80.0, "2026-01-05T08:00:00")]
        self.assertIsNone(AnalyticsService.compute_habit_domino_chain(entries))

    def test_chain_follows_strongest_correlation_first(self):
        sleep = [5, 5.5, 6, 7, 8, 9]
        # sleep correlates perfectly (r=1.0) with health_score; stress is
        # only strongly (not perfectly) negatively correlated, so sleep
        # must be picked first, deterministically.
        stress = [8, 7, 7, 5, 4, 3]
        entries = [
            _entry(
                f"2026-01-{5+i:02d}", "Monday", 10 * s, "2026-01-05T08:00:00",
                sleep_hours=s, stress_0_10=st,
            )
            for i, (s, st) in enumerate(zip(sleep, stress))
        ]
        chain = AnalyticsService.compute_habit_domino_chain(entries)
        self.assertIsNotNone(chain)
        self.assertEqual(chain[0]["field"], "health_score")
        self.assertEqual(chain[1]["field"], "sleep_hours")
        self.assertAlmostEqual(chain[0]["correlation_to_next"], 1.0, places=2)
        self.assertEqual(chain[2]["field"], "stress_0_10")
        self.assertIsNone(chain[-1]["correlation_to_next"])

    def test_no_chain_when_no_correlation_clears_threshold(self):
        # health_score is essentially unrelated (near-zero slope) to
        # sleep_hours here - shouldn't build a misleading chain.
        entries = [
            _entry(f"2026-01-{5+i:02d}", "Monday", 50.0, "2026-01-05T08:00:00", sleep_hours=float(i % 2) + 5.0)
            for i in range(6)
        ]
        chain = AnalyticsService.compute_habit_domino_chain(entries)
        # health_score is constant here (zero variance) so it's excluded
        # from the correlation matrix entirely -> no chain possible.
        self.assertIsNone(chain)


class TestGoldenHour(unittest.TestCase):
    """Feature 44."""

    def test_none_below_minimum_entries(self):
        entries = [_entry("2026-01-05", "Monday", 80.0, "2026-01-05T08:00:00")]
        self.assertIsNone(AnalyticsService.detect_golden_hour(entries))

    def test_none_without_enough_distinct_hours(self):
        # 5 entries but only 2 distinct hours - below MIN_DISTINCT_HOURS (3).
        entries = [
            _entry(f"2026-01-{5+i:02d}", "Monday", 80.0, f"2026-01-{5+i:02d}T08:00:00")
            for i in range(3)
        ] + [
            _entry(f"2026-01-{8+i:02d}", "Thursday", 60.0, f"2026-01-{8+i:02d}T20:00:00")
            for i in range(2)
        ]
        self.assertIsNone(AnalyticsService.detect_golden_hour(entries))

    def test_finds_correct_golden_and_toughest_hour(self):
        entries = [
            _entry("2026-01-05", "Monday", 90.0, "2026-01-05T08:00:00"),
            _entry("2026-01-12", "Monday", 90.0, "2026-01-12T08:15:00"),
            _entry("2026-01-06", "Tuesday", 60.0, "2026-01-06T14:00:00"),
            _entry("2026-01-13", "Tuesday", 60.0, "2026-01-13T14:30:00"),
            _entry("2026-01-07", "Wednesday", 20.0, "2026-01-07T23:00:00"),
        ]
        golden = AnalyticsService.detect_golden_hour(entries)
        self.assertIsNotNone(golden)
        self.assertEqual(golden["golden_hour"], 8)
        self.assertAlmostEqual(golden["golden_hour_avg_score"], 90.0)
        self.assertEqual(golden["golden_hour_count"], 2)
        self.assertEqual(golden["toughest_hour"], 23)
        self.assertAlmostEqual(golden["toughest_hour_avg_score"], 20.0)


class TestLeverageDay(unittest.TestCase):
    """Feature 46."""

    def test_none_without_enough_samples_per_weekday(self):
        entries = [
            _entry("2026-01-05", "Monday", 80.0, "2026-01-05T08:00:00"),
            _entry("2026-01-12", "Monday", 40.0, "2026-01-12T08:00:00"),
        ]  # only 2 Mondays, below MIN_SAMPLES_PER_WEEKDAY_FOR_LEVERAGE (3)
        self.assertIsNone(AnalyticsService.detect_leverage_day(entries))

    def test_finds_highest_variance_weekday(self):
        entries = [
            # Monday: wildly inconsistent (high std dev)
            _entry("2026-01-05", "Monday", 20.0, "2026-01-05T08:00:00", top_shap_feature="stress_0_10"),
            _entry("2026-01-12", "Monday", 90.0, "2026-01-12T08:00:00", top_shap_feature="stress_0_10"),
            _entry("2026-01-19", "Monday", 55.0, "2026-01-19T08:00:00", top_shap_feature="sleep_hours"),
            # Tuesday: rock steady
            _entry("2026-01-06", "Tuesday", 70.0, "2026-01-06T08:00:00"),
            _entry("2026-01-13", "Tuesday", 71.0, "2026-01-13T08:00:00"),
            _entry("2026-01-20", "Tuesday", 69.0, "2026-01-20T08:00:00"),
        ]
        leverage = AnalyticsService.detect_leverage_day(entries)
        self.assertIsNotNone(leverage)
        self.assertEqual(leverage["day_of_week"], "Monday")
        self.assertEqual(leverage["likely_lever"], "stress_0_10")
        self.assertGreater(leverage["std_dev"], 1.0)


if __name__ == "__main__":
    unittest.main()
