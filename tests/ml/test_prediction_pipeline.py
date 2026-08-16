"""
Tests: end-to-end prediction pipeline correctness.

Run: python3 -m unittest tests.ml.test_prediction_pipeline -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts

from models.model_manager import ModelManager
from services.ml.validation_service import ValidationService
from services.ml.prediction_service import PredictionService


class TestPredictionPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ModelManager.reset()
        cls.validator = ValidationService()
        cls.predictor = PredictionService()

    @classmethod
    def tearDownClass(cls):
        ModelManager.reset()

    def _run(self, user_data: dict):
        validation = self.validator.validate(user_data)
        self.assertTrue(validation.is_valid, msg=f"Validation errors: {validation.errors}")
        return self.predictor.predict(validation.cleaned_data)

    def _assert_structurally_valid(self, result):
        self.assertIn(result.prediction, {"At Risk", "Moderate", "Healthy"})
        self.assertIsNotNone(result.confidence)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0 + 1e-9)

        self.assertAlmostEqual(sum(result.probabilities.values()), 1.0, places=2)
        for p in result.probabilities.values():
            self.assertGreaterEqual(p, -1e-9)
            self.assertLessEqual(p, 1.0 + 1e-9)

        self.assertIsNotNone(result.regression_score)
        self.assertGreaterEqual(result.regression_score, 0.0)
        self.assertLessEqual(result.regression_score, 100.0)

        self.assertIsInstance(result.shap_features, list)
        self.assertGreater(len(result.shap_features), 0, "SHAP explanation should not be empty")

        self.assertGreater(result.prediction_time_ms, 0.0)

    # ------------------------------------------------------

    def test_healthy_profile_predicts_successfully(self):
        result = self._run(ts.healthy_user_data())
        self._assert_structurally_valid(result)

    def test_at_risk_profile_predicts_successfully(self):
        result = self._run(ts.at_risk_user_data())
        self._assert_structurally_valid(result)
        # This extreme, deliberately unhealthy synthetic profile should
        # be recognized as the worst of the three scenarios.
        self.assertEqual(result.prediction, "At Risk")

    def test_borderline_profile_predicts_successfully(self):
        result = self._run(ts.borderline_user_data())
        self._assert_structurally_valid(result)

    def test_wellness_score_ordering_is_sane(self):
        """
        Not a claim about exact model internals - just a basic sanity
        check that the regression head responds to habit quality in the
        expected direction: healthy > borderline > at_risk.
        """
        healthy = self._run(ts.healthy_user_data())
        borderline = self._run(ts.borderline_user_data())
        at_risk = self._run(ts.at_risk_user_data())

        self.assertGreater(healthy.regression_score, borderline.regression_score)
        self.assertGreater(borderline.regression_score, at_risk.regression_score)

    def test_invalid_input_is_rejected_before_reaching_the_model(self):
        bad_data = ts.healthy_user_data()
        bad_data["sleep_hours"] = 999  # out of schema range (max 15)
        validation = self.validator.validate(bad_data)
        self.assertFalse(validation.is_valid)
        self.assertIn("sleep_hours", validation.errors)

    def test_repeated_predictions_are_deterministic(self):
        """Same input, same (non-random) trained model -> identical output."""
        data = ts.borderline_user_data()
        r1 = self._run(data)
        r2 = self._run(data)
        self.assertEqual(r1.prediction, r2.prediction)
        self.assertAlmostEqual(r1.regression_score, r2.regression_score, places=6)


if __name__ == "__main__":
    unittest.main()
