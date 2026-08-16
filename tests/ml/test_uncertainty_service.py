"""
Tests: Group C Feature 55 - Prediction Uncertainty (split conformal).

Run: python3 -m unittest tests.ml.test_uncertainty_service -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts

from models.model_manager import ModelManager
from services.ml.validation_service import ValidationService
from services.ml.prediction_service import PredictionService
from services.ml.uncertainty_service import UncertaintyService, UncertaintyResult


class TestUncertaintyCalibration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ModelManager.reset()
        cls.mm = ModelManager.instance()
        cls.uncertainty_service = cls.mm.uncertainty_service

    @classmethod
    def tearDownClass(cls):
        ModelManager.reset()

    def test_calibration_succeeded(self):
        self.assertTrue(self.uncertainty_service._calibrated)
        self.assertIsNotNone(self.uncertainty_service._regression_quantile)
        self.assertIsNotNone(self.uncertainty_service._classification_quantile)
        # Validation split has thousands of rows; calibration should use
        # a real sample, not a token handful.
        self.assertGreater(self.uncertainty_service._calibration_size, 100)

    def test_quantiles_are_nonnegative(self):
        self.assertGreaterEqual(self.uncertainty_service._regression_quantile, 0.0)
        self.assertGreaterEqual(self.uncertainty_service._classification_quantile, 0.0)
        # Nonconformity score is 1 - probability, so it must be <= 1.
        self.assertLessEqual(self.uncertainty_service._classification_quantile, 1.0)

    def test_calibration_cache_is_written_and_reused(self):
        from services.ml.uncertainty_service import CALIBRATION_CACHE_FILE
        self.assertTrue(CALIBRATION_CACHE_FILE.exists())

        # A second instance against the same model artifacts should load
        # from cache rather than recomputing (same quantiles, no error).
        second = UncertaintyService(model_manager=self.mm)
        self.assertEqual(second._regression_quantile, self.uncertainty_service._regression_quantile)
        self.assertEqual(second._classification_quantile, self.uncertainty_service._classification_quantile)

    def test_empirical_coverage_near_target_on_validation_set(self):
        """
        The whole point of split conformal is a coverage *guarantee* -
        verify it actually holds empirically on the validation set itself
        (in-sample check that the math was implemented correctly; true
        out-of-sample coverage is guaranteed by the split-conformal
        theorem for any exchangeable future point).
        """
        from models.data_loader import load_datasets
        from models.preprocessing import TARGET_COLUMNS

        # data/ is gitignored (271 MB), so a packaged build ships without
        # it. The conformal quantiles themselves come from the cached
        # calibration artifact and are still checked above; only this
        # empirical re-verification needs the raw rows.
        try:
            _, validation_df, _ = load_datasets()
        except Exception:  # noqa: BLE001 - absence, not a failure
            self.skipTest("no validation dataset in this build (data/ is gitignored)")
        reg_cols = self.mm.regression_feature_columns
        target = TARGET_COLUMNS["regression"]

        X = validation_df.reindex(columns=reg_cols)
        y = validation_df[target].to_numpy(dtype=float)

        preds = self.mm.regression_model.predict(X)
        q = self.uncertainty_service._regression_quantile
        lower = preds - q
        upper = preds + q

        covered = ((y >= lower) & (y <= upper)).mean()
        # Split conformal guarantees marginal coverage >= 1 - alpha
        # (90%) up to O(1/n) slack; on thousands of rows this should be
        # very close to (and essentially never far below) 90%.
        self.assertGreaterEqual(covered, 0.85)


class TestUncertaintyEstimate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ModelManager.reset()
        cls.validator = ValidationService()
        cls.predictor = PredictionService()

    @classmethod
    def tearDownClass(cls):
        ModelManager.reset()

    def _predict(self, data_fn):
        v = self.validator.validate(data_fn())
        self.assertTrue(v.is_valid, msg=v.errors)
        return self.predictor.predict(v.cleaned_data)

    def test_uncertainty_is_attached_to_every_prediction(self):
        for data_fn in (ts.healthy_user_data, ts.at_risk_user_data, ts.borderline_user_data):
            result = self._predict(data_fn)
            self.assertIsInstance(result.uncertainty, UncertaintyResult)
            self.assertTrue(result.uncertainty.available)

    def test_regression_interval_contains_point_estimate(self):
        result = self._predict(ts.healthy_user_data)
        u = result.uncertainty
        self.assertLessEqual(u.regression_lower, result.regression_score + 1e-6)
        self.assertGreaterEqual(u.regression_upper, result.regression_score - 1e-6)
        self.assertGreaterEqual(u.regression_lower, 0.0)
        self.assertLessEqual(u.regression_upper, 100.0)

    def test_classification_set_contains_point_prediction(self):
        result = self._predict(ts.at_risk_user_data)
        u = result.uncertainty
        self.assertIn(result.prediction, u.classification_set)
        self.assertGreaterEqual(u.classification_set_size, 1)
        self.assertLessEqual(u.classification_set_size, 3)

    def test_entropy_bounds(self):
        result = self._predict(ts.borderline_user_data)
        u = result.uncertainty
        self.assertGreaterEqual(u.entropy_normalized, 0.0)
        self.assertLessEqual(u.entropy_normalized, 1.0 + 1e-9)

    def test_uncertainty_label_is_one_of_expected(self):
        result = self._predict(ts.healthy_user_data)
        self.assertIn(result.uncertainty.uncertainty_label, {"Low", "Moderate", "High"})

    def test_to_dict_is_json_safe(self):
        import json
        result = self._predict(ts.healthy_user_data)
        json.dumps(result.to_dict())  # must not raise


class TestUncertaintyRobustness(unittest.TestCase):
    """Robustness requirement: never crash, degrade gracefully."""

    def test_estimate_never_raises_on_empty_probabilities(self):
        from unittest.mock import MagicMock

        fake_mm = MagicMock()
        fake_mm.classification_registry.model_info = {"saved_at": "x"}
        fake_mm.regression_registry.model_info = {"saved_at": "y"}

        service = UncertaintyService.__new__(UncertaintyService)
        service.alpha = 0.10
        service._regression_quantile = 1.5
        service._classification_quantile = 0.3
        service._calibration_size = 500
        service._calibrated = True
        import threading
        service._lock = threading.Lock()

        result = service.estimate(probabilities={}, regression_score=None)
        self.assertIsInstance(result, UncertaintyResult)

    def test_estimate_degrades_gracefully_when_uncalibrated(self):
        service = UncertaintyService.__new__(UncertaintyService)
        service._calibrated = False
        service._calibration_size = 0
        result = service.estimate(probabilities={"Healthy": 0.7, "Moderate": 0.3}, regression_score=80.0)
        self.assertFalse(result.available)
        self.assertIsNotNone(result.explanation)


if __name__ == "__main__":
    unittest.main()
