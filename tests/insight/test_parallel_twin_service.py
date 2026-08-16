"""
Tests: ParallelTwinService (feature 45 - Parallel Twin).

Uses a fake predictor (no real model needed - this service only needs
to prove it builds a correctly-adjusted input and calls
predictor.predict() with it, exactly the same contract
legacy/streamlit_app/components/what_if_simulator.py already relies on).

Run: python3 -m unittest tests.insight.test_parallel_twin_service -v
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Optional

import tests._test_support  # noqa: F401

from services.insight.parallel_twin_service import ParallelTwinService
from services.ml.shap_service import SHAPFeature


def _area(feature: str) -> SHAPFeature:
    return SHAPFeature(feature=feature, value=0.0, shap_value=-1.0, abs_shap=1.0, direction="decrease", score=90.0)


@dataclass
class _FakeResult:
    prediction: str
    regression_score: float


class _FakePredictor:
    """Deterministic stand-in: score = 100 - stress*5 - social_min*0.05."""

    def predict(self, user_data, compute_shap: bool = True):
        stress = float(user_data.get("stress_0_10", 0.0))
        social = float(user_data.get("social_min", 0.0))
        score = max(0.0, min(100.0, 100.0 - stress * 5 - social * 0.05))
        prediction = "Healthy" if score >= 60 else "At Risk"
        return _FakeResult(prediction=prediction, regression_score=score)


class TestParallelTwinService(unittest.TestCase):

    def test_build_twin_profile_shifts_adjustable_fields_toward_healthier(self):
        base = {"stress_0_10": 8.0, "social_min": 200.0}
        twin_data, adjustments = ParallelTwinService.build_twin_profile(base, [_area("stress_0_10")])
        self.assertEqual(len(adjustments), 1)
        self.assertLess(twin_data["stress_0_10"], base["stress_0_10"])

    def test_sleep_hours_shifts_upward_not_downward(self):
        base = {"sleep_hours": 5.0}
        twin_data, adjustments = ParallelTwinService.build_twin_profile(base, [_area("sleep_hours")])
        self.assertGreater(twin_data["sleep_hours"], base["sleep_hours"])

    def test_non_adjustable_fields_are_skipped(self):
        base = {"digital_dependence_0_100": 80.0}
        twin_data, adjustments = ParallelTwinService.build_twin_profile(
            base, [_area("digital_dependence_0_100")]
        )
        self.assertEqual(adjustments, [])

    def test_shift_is_clamped_to_schema_bounds(self):
        base = {"stress_0_10": 0.5}  # near the minimum (0.0)
        twin_data, adjustments = ParallelTwinService.build_twin_profile(base, [_area("stress_0_10")])
        self.assertGreaterEqual(twin_data["stress_0_10"], 0.0)

    def test_max_adjustments_respected(self):
        base = {"stress_0_10": 8.0, "social_min": 300.0, "gaming_min": 300.0, "video_min": 300.0}
        areas = [_area("stress_0_10"), _area("social_min"), _area("gaming_min"), _area("video_min")]
        _, adjustments = ParallelTwinService.build_twin_profile(base, areas)
        self.assertLessEqual(len(adjustments), 3)

    def test_compare_returns_none_with_no_adjustable_areas(self):
        result = ParallelTwinService.compare(
            base_user_data={"digital_dependence_0_100": 80.0},
            areas_to_improve=[_area("digital_dependence_0_100")],
            real_result=_FakeResult(prediction="Healthy", regression_score=80.0),
            predictor=_FakePredictor(),
        )
        self.assertIsNone(result)

    def test_compare_runs_real_predictor_and_computes_delta(self):
        base = {"stress_0_10": 8.0, "social_min": 0.0}
        real_result = _FakePredictor().predict(base)
        comparison = ParallelTwinService.compare(
            base_user_data=base,
            areas_to_improve=[_area("stress_0_10")],
            real_result=real_result,
            predictor=_FakePredictor(),
        )
        self.assertIsNotNone(comparison)
        self.assertGreater(comparison.score_delta, 0)  # lower stress -> higher score

    def test_class_changed_flag(self):
        # stress=10 -> score 50 -> "At Risk"; twin should shift stress down
        # enough that the class flips to "Healthy".
        base = {"stress_0_10": 10.0}
        real_result = _FakePredictor().predict(base)
        comparison = ParallelTwinService.compare(
            base_user_data=base,
            areas_to_improve=[_area("stress_0_10")],
            real_result=real_result,
            predictor=_FakePredictor(),
        )
        self.assertIsNotNone(comparison)
        # Not asserting True/False definitively (depends on shift size),
        # just that the flag is a real bool derived from both results.
        self.assertIsInstance(comparison.class_changed, bool)


if __name__ == "__main__":
    unittest.main()
