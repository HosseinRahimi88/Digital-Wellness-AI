"""
Tests: utils.dimension_scores.compute_dimension_scores - the transparent,
non-ML wellness-dimension breakdown shown alongside the model's own
prediction. Never touches the trained model; these tests check the
arithmetic contract only.

Run: python3 -m unittest tests.ml.test_dimension_scores -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401  (sys.path bootstrap)

from config.demo_profiles import at_risk_profile, healthy_profile
from utils.dimension_scores import compute_dimension_scores


class TestDimensionScores(unittest.TestCase):

    def test_healthy_profile_scores_high_overall(self):
        result = compute_dimension_scores(healthy_profile())
        self.assertGreater(result["overall"], 70)

    def test_at_risk_profile_scores_low_overall(self):
        result = compute_dimension_scores(at_risk_profile())
        self.assertLess(result["overall"], 50)

    def test_healthy_scores_higher_than_at_risk(self):
        healthy = compute_dimension_scores(healthy_profile())
        at_risk = compute_dimension_scores(at_risk_profile())
        self.assertGreater(healthy["overall"], at_risk["overall"])

    def test_every_dimension_score_is_within_0_100(self):
        for profile in (healthy_profile(), at_risk_profile()):
            result = compute_dimension_scores(profile)
            for dim in result["dimensions"]:
                self.assertGreaterEqual(dim["score"], 0.0)
                self.assertLessEqual(dim["score"], 100.0)

    def test_missing_indicators_are_skipped_not_fabricated(self):
        result = compute_dimension_scores({})
        self.assertEqual(result["dimensions"], [])
        self.assertIsNone(result["overall"])

    def test_partial_input_only_scores_dimensions_with_data(self):
        result = compute_dimension_scores({"sleep_hours": 8.0, "sleep_quality_1_10": 9.0})
        keys = {d["key"] for d in result["dimensions"]}
        self.assertEqual(keys, {"sleep"})

    def test_sleep_hours_target_is_symmetric_around_eight(self):
        under = compute_dimension_scores({"sleep_hours": 6.0})
        over = compute_dimension_scores({"sleep_hours": 10.0})
        ideal = compute_dimension_scores({"sleep_hours": 8.0})
        self.assertEqual(ideal["overall"], 100.0)
        self.assertLess(under["overall"], ideal["overall"])
        self.assertLess(over["overall"], ideal["overall"])

    def test_inverted_indicator_direction(self):
        low_stress = compute_dimension_scores({"stress_0_10": 0.0})
        high_stress = compute_dimension_scores({"stress_0_10": 10.0})
        self.assertGreater(low_stress["overall"], high_stress["overall"])

    def test_non_numeric_value_is_skipped_not_raised(self):
        result = compute_dimension_scores({"sleep_hours": "not-a-number", "focus_0_100": 80.0})
        keys = {d["key"] for d in result["dimensions"]}
        self.assertEqual(keys, {"focus"})


if __name__ == "__main__":
    unittest.main()
