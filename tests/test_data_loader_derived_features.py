"""
Tests: models.data_loader.reconstruct_derived_features - the train/serve
consistency fix that makes training data compute total_screen_min and
every feature derived from it via the exact same function
(utils.feature_derivation.derive_features()) that live inference uses.

Run: python3 -m unittest tests.test_data_loader_derived_features -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401  (sys.path bootstrap)

import pandas as pd

from models.data_loader import reconstruct_derived_features, _DERIVE_FEATURES_RAW_COLUMNS


def _minimal_raw_frame(**overrides) -> pd.DataFrame:
    row = {
        "social_min": 60.0, "gaming_min": 45.0, "work_study_min": 120.0,
        "video_min": 30.0, "other_min": 15.0,
        "night_screen_min": 10.0, "pre_sleep_screen_min": 5.0,
        "first_check_after_waking_min": 20.0,
        "notifications_per_day": 40, "pickups_per_day": 60,
        "app_opens_per_day": 50, "sessions_per_day": 25,
        # A stale/inconsistent stored value, as the original CSVs had -
        # reconstruct_derived_features() must overwrite this, not trust it.
        "total_screen_min": 999.0,
    }
    row.update(overrides)
    return pd.DataFrame([row])


class TestReconstructDerivedFeatures(unittest.TestCase):

    def test_total_screen_min_is_overwritten_to_the_category_sum(self):
        """The whole point of this function: total_screen_min must end
        up as the sum of the five category fields, discarding whatever
        the CSV's own stored value was (270.0 here vs. the stale 999.0
        in the input)."""
        df = _minimal_raw_frame()
        result = reconstruct_derived_features(df)
        self.assertEqual(result.loc[0, "total_screen_min"], 270.0)

    def test_ratios_are_recomputed_consistently_with_the_new_total(self):
        """social_ratio + gaming_ratio + work_study_ratio + other_ratio
        must sum to exactly (1 - video_share) given the new
        category-sum total_screen_min - there is no video_ratio feature
        (never was), so video_min's share is the one category not
        represented in these four ratios. See the matching test in
        tests/test_feature_derivation.py for the direct derive_features()
        version of this same invariant."""
        df = _minimal_raw_frame()
        result = reconstruct_derived_features(df)
        ratio_sum = (
            result.loc[0, "social_ratio"] + result.loc[0, "gaming_ratio"]
            + result.loc[0, "work_study_ratio"] + result.loc[0, "other_ratio"]
        )
        expected_video_share = 30.0 / result.loc[0, "total_screen_min"]
        self.assertAlmostEqual(ratio_sum, 1.0 - expected_video_share, places=3)

    def test_missing_raw_columns_returns_frame_unchanged(self):
        """Degrades gracefully (no crash, no partial overwrite) if the
        raw columns derive_features() needs aren't present - e.g. an
        unexpected schema on some future dataset export."""
        df = pd.DataFrame([{"total_screen_min": 999.0}])
        result = reconstruct_derived_features(df)
        self.assertEqual(result.loc[0, "total_screen_min"], 999.0)

    def test_screen_ewma_baseline_is_not_carried_through_from_input(self):
        """Every row here represents one independent day's submission,
        not a chained what-if off an existing baseline - so
        screen_ewma_baseline must always be recomputed fresh (equal to
        the row's own total_screen_min), even if the input frame already
        had some other stored value for it."""
        df = _minimal_raw_frame(screen_ewma_baseline=123456.0)
        result = reconstruct_derived_features(df)
        self.assertEqual(result.loc[0, "screen_ewma_baseline"], result.loc[0, "total_screen_min"])

    def test_all_required_raw_columns_are_actually_used(self):
        """Sanity check on the fixture/function contract itself: every
        column reconstruct_derived_features() declares as required is
        present in _minimal_raw_frame(), so the "missing columns" branch
        above is testing a genuinely different code path, not the normal
        one."""
        df = _minimal_raw_frame()
        for col in _DERIVE_FEATURES_RAW_COLUMNS:
            self.assertIn(col, df.columns)

    def test_multi_row_frame_computed_independently_per_row(self):
        df = pd.concat([
            _minimal_raw_frame(social_min=60.0),
            _minimal_raw_frame(social_min=600.0),
        ], ignore_index=True)
        result = reconstruct_derived_features(df)
        self.assertNotEqual(result.loc[0, "total_screen_min"], result.loc[1, "total_screen_min"])
        self.assertEqual(result.loc[1, "total_screen_min"], 600.0 + 45.0 + 120.0 + 30.0 + 15.0)


if __name__ == "__main__":
    unittest.main()
