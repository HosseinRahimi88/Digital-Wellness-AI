"""
Tests: AdvancedWhatIfService (feature 12 - Advanced What-if Simulator's
Sensitivity Analysis + Goal-Seek).

Run: python3 -m unittest tests.test_advanced_whatif_service -v
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass

import tests._test_support  # noqa: F401

from services.advanced_whatif_service import AdvancedWhatIfService


@dataclass
class _FakeResult:
    prediction: str
    regression_score: float


class _FakeStressPredictor:
    """score decreases linearly as stress_0_10 increases."""

    def predict(self, user_data, compute_shap: bool = True):
        stress = float(user_data.get("stress_0_10", 0.0))
        score = max(0.0, min(100.0, 100.0 - stress * 10))
        return _FakeResult(prediction="Healthy" if score >= 50 else "At Risk", regression_score=score)


class _FailingPredictor:
    def predict(self, user_data, compute_shap: bool = True):
        raise RuntimeError("boom")


class TestSweepField(unittest.TestCase):

    def test_sweep_produces_expected_number_of_points(self):
        points = AdvancedWhatIfService.sweep_field(
            {"stress_0_10": 5.0}, _FakeStressPredictor(), "stress_0_10", num_points=9
        )
        self.assertEqual(len(points), 9)

    def test_sweep_covers_the_real_schema_range(self):
        points = AdvancedWhatIfService.sweep_field(
            {"stress_0_10": 5.0}, _FakeStressPredictor(), "stress_0_10", num_points=5
        )
        values = [p.value for p in points]
        self.assertAlmostEqual(min(values), 0.0)
        self.assertAlmostEqual(max(values), 10.0)  # stress_0_10 schema max

    def test_sweep_scores_move_with_the_swept_field(self):
        points = AdvancedWhatIfService.sweep_field(
            {"stress_0_10": 5.0}, _FakeStressPredictor(), "stress_0_10", num_points=5
        )
        scores = [p.score for p in points]
        self.assertEqual(scores, sorted(scores, reverse=True))  # score falls as stress rises

    def test_prediction_failure_yields_none_score_not_raise(self):
        points = AdvancedWhatIfService.sweep_field(
            {"stress_0_10": 5.0}, _FailingPredictor(), "stress_0_10", num_points=3
        )
        self.assertEqual(len(points), 3)
        self.assertTrue(all(p.score is None for p in points))


class TestGoalSeek(unittest.TestCase):

    def test_finds_value_closest_to_target(self):
        result = AdvancedWhatIfService.goal_seek(
            {"stress_0_10": 5.0}, _FakeStressPredictor(), "stress_0_10", target_score=70.0, num_points=11
        )
        self.assertIsNotNone(result)
        # score = 100 - stress*10 = 70 -> stress = 3.0
        self.assertAlmostEqual(result.best_value, 3.0, delta=1.5)
        self.assertLessEqual(result.distance, 10.0)

    def test_returns_none_when_predictor_always_fails(self):
        result = AdvancedWhatIfService.goal_seek(
            {"stress_0_10": 5.0}, _FailingPredictor(), "stress_0_10", target_score=70.0
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
