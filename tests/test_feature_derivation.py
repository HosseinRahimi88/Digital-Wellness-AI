"""
Tests: utils.feature_derivation.derive_features - shared derived/ratio/
density feature computation used by both FormGenerator and the What-if
Simulator.

Run: python3 -m unittest tests.test_feature_derivation -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401  (sys.path bootstrap)

from utils.feature_derivation import derive_features


class TestDeriveFeatures(unittest.TestCase):

    def test_all_zero_screen_time_does_not_divide_by_zero(self):
        """total_screen_min is floored at 1.0 specifically to avoid a
        ZeroDivisionError in the ratio/density calculations below it."""
        result = derive_features({
            "social_min": 0.0, "gaming_min": 0.0, "work_study_min": 0.0,
            "video_min": 0.0, "other_min": 0.0,
            "notifications_per_day": 0, "pickups_per_day": 0, "app_opens_per_day": 0,
        })
        self.assertEqual(result["total_screen_min"], 1.0)
        self.assertEqual(result["social_ratio"], 0.0)

    def test_missing_fields_default_to_zero_instead_of_crashing(self):
        result = derive_features({})
        self.assertEqual(result["total_screen_min"], 1.0)
        self.assertIn("digital_dependence_0_100", result)

    def test_input_dict_is_not_mutated(self):
        original = {"social_min": 30.0, "gaming_min": 0.0}
        derive_features(original)
        self.assertNotIn("total_screen_min", original)

    def test_screen_vs_baseline_pct_is_clipped_to_schema_range(self):
        result = derive_features({
            "social_min": 1440.0, "gaming_min": 0.0, "work_study_min": 0.0,
            "video_min": 0.0, "other_min": 0.0,
        })
        self.assertLessEqual(result["screen_vs_baseline_pct"], 300.0)

    def test_existing_baseline_is_preserved_not_overwritten(self):
        """The What-if Simulator relies on this: tweaking today's numbers
        must not silently redefine the user's stored personal baseline."""
        result = derive_features({
            "social_min": 500.0, "gaming_min": 0.0, "work_study_min": 0.0,
            "video_min": 0.0, "other_min": 0.0,
            "screen_ewma_baseline": 123.0,
        })
        self.assertEqual(result["screen_ewma_baseline"], 123.0)

    def test_fragmentation_index_is_bounded_0_to_100(self):
        result = derive_features({"pickups_per_day": 999999, "sessions_per_day": 999999})
        self.assertGreaterEqual(result["fragmentation_index_0_100"], 0.0)
        self.assertLessEqual(result["fragmentation_index_0_100"], 100.0)

    def test_total_screen_min_equals_compute_total_screen_min(self):
        """derive_features() must use compute_total_screen_min() as its
        single source of truth for total_screen_min, not a second,
        independent computation - this is the guarantee the train/serve
        consistency fix in models/data_loader.py depends on."""
        from utils.feature_derivation import compute_total_screen_min

        raw = {"social_min": 60.0, "gaming_min": 45.0, "work_study_min": 120.0,
               "video_min": 30.0, "other_min": 15.0}
        result = derive_features(raw)
        self.assertEqual(result["total_screen_min"], compute_total_screen_min(raw))

    def test_ratios_always_sum_to_one_minus_video_ratio(self):
        """Now that total_screen_min is always exactly the sum of the
        five category fields (never an independently-tracked value),
        social_ratio + gaming_ratio + work_study_ratio + other_ratio
        must always sum to exactly (1 - video_share) - there is no
        video_ratio feature (never was, in the original schema either),
        so video_min's share of the total is the only one of the five
        categories not represented in these four ratios. This was NOT
        a deterministic relationship before the train/serve consistency
        fix, when training data's stored total_screen_min could differ
        from the category sum."""
        result = derive_features({
            "social_min": 60.0, "gaming_min": 45.0, "work_study_min": 120.0,
            "video_min": 30.0, "other_min": 15.0,
        })
        ratio_sum = (
            result["social_ratio"] + result["gaming_ratio"]
            + result["work_study_ratio"] + result["other_ratio"]
        )
        expected_video_share = 30.0 / result["total_screen_min"]
        self.assertAlmostEqual(ratio_sum, 1.0 - expected_video_share, places=3)

    def test_ratios_sum_to_one_when_video_min_is_zero(self):
        """With video_min=0, the four tracked ratios (social, gaming,
        work_study, other) exhaust the whole total and must sum to
        exactly 1.0 - the clean special case of the general rule above."""
        result = derive_features({
            "social_min": 60.0, "gaming_min": 45.0, "work_study_min": 120.0,
            "video_min": 0.0, "other_min": 15.0,
        })
        ratio_sum = (
            result["social_ratio"] + result["gaming_ratio"]
            + result["work_study_ratio"] + result["other_ratio"]
        )
        self.assertAlmostEqual(ratio_sum, 1.0, places=3)


class TestComputeTotalScreenMinVectorized(unittest.TestCase):
    """utils.feature_derivation.compute_total_screen_min_vectorized() -
    the pandas equivalent used by services/cohort_service.py, which must
    stay in exact numeric agreement with the scalar
    compute_total_screen_min() every other caller uses."""

    def test_matches_scalar_version_row_by_row(self):
        import pandas as pd
        from utils.feature_derivation import compute_total_screen_min, compute_total_screen_min_vectorized

        rows = [
            {"social_min": 60.0, "gaming_min": 45.0, "work_study_min": 120.0, "video_min": 30.0, "other_min": 15.0},
            {"social_min": 0.0, "gaming_min": 0.0, "work_study_min": 0.0, "video_min": 0.0, "other_min": 0.0},
            {"social_min": 1440.0, "gaming_min": 1440.0, "work_study_min": 0.0, "video_min": 0.0, "other_min": 0.0},
        ]
        df = pd.DataFrame(rows)
        vectorized = compute_total_screen_min_vectorized(df)
        for i, row in enumerate(rows):
            self.assertEqual(vectorized.iloc[i], compute_total_screen_min(row))


if __name__ == "__main__":
    unittest.main()
