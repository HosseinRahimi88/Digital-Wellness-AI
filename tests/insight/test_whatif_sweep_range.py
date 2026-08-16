"""The what-if sweep must explore days the validator will actually accept.

The defect: sweep_field ran each field across its own FEATURE_SCHEMA
range, and a screen-time category's schema maximum is 1440 minutes - the
whole day. But ValidationService enforces a cross-field rule the per-field
bounds know nothing about: the five categories together may not exceed
total_screen_min's maximum. Sweeping video_min on the at-risk profile
therefore spent most of its grid on days the validator refused, scoring
4 of 15 points, and goal_seek returned a "best value" of 0 because the
bottom of the range was the only part still producing a day.
"""

from __future__ import annotations

import unittest

from config import demo_profiles as dp
from core.feature_schema import FEATURE_SCHEMA
from services.insight.advanced_whatif_service import (
    _SCREEN_CATEGORY_FIELDS,
    AdvancedWhatIfService,
)
from services.ml.prediction_service import PredictionService


class TestSweepStaysInsideTheCrossFieldLimit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictionService()
        cls.profile = dp.at_risk_profile()

    def test_every_screen_category_sweeps_to_a_reachable_maximum(self):
        total_max = FEATURE_SCHEMA["total_screen_min"].maximum
        for field in _SCREEN_CATEGORY_FIELDS:
            with self.subTest(field=field):
                others = sum(
                    float(self.profile.get(other, 0.0) or 0.0)
                    for other in _SCREEN_CATEGORY_FIELDS
                    if other != field
                )
                _lo, hi = AdvancedWhatIfService._field_range(
                    field, float(self.profile.get(field, 0.0) or 0.0), self.profile
                )
                self.assertLessEqual(
                    hi + others, total_max + 1e-6,
                    f"{field} sweeps to {hi}, which with the other categories "
                    f"({others}) exceeds the {total_max}-minute day",
                )

    def test_the_sweep_actually_scores_its_points(self):
        # The reproduced failure: 4 of 15. Anything that low means the
        # grid is being spent on impossible days again.
        for field in ("video_min", "gaming_min", "other_min"):
            with self.subTest(field=field):
                points = AdvancedWhatIfService.sweep_field(
                    self.profile, self.predictor, field
                )
                scored = [p for p in points if p.score is not None]
                self.assertEqual(
                    len(scored), len(points),
                    f"{field}: only {len(scored)}/{len(points)} points produced a score",
                )

    def test_goal_seek_reports_a_value_from_a_day_that_scored(self):
        result = AdvancedWhatIfService.goal_seek(
            self.profile, self.predictor, "video_min", target_score=80.0
        )
        self.assertIsNotNone(result)
        scored_values = {p.value for p in result.points if p.score is not None}
        self.assertIn(result.best_value, scored_values)


class TestNonScreenFieldsAreUnaffected(unittest.TestCase):
    def test_a_non_category_field_keeps_its_full_schema_range(self):
        feature = FEATURE_SCHEMA["sleep_hours"]
        lo, hi = AdvancedWhatIfService._field_range(
            "sleep_hours", 7.0, dp.at_risk_profile()
        )
        self.assertEqual((lo, hi), (float(feature.minimum), float(feature.maximum)))


if __name__ == "__main__":
    unittest.main()
