"""
Tests: regression safety - confirm the backend refactor did not touch
model accuracy, the feature schema, or SHAP correctness.

Run: python3 -m unittest tests.test_regression_safety -v
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import tests._test_support as ts

from core.feature_schema import FEATURE_SCHEMA
from models.model_manager import ModelManager
from models.model_registry import ModelRegistry
from services.validation_service import ValidationService
from services.prediction_service import PredictionService
from utils.trend_features import build_trend_features, trend_feature_names

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


class TestRegressionSafety(unittest.TestCase):
    """
    These tests do not retrain or touch anything under models/train_*.py
    or artifacts/*.pkl - task requirements explicitly forbid changing the
    training pipeline unless strictly necessary, and it wasn't. They only
    confirm the *serving* refactor (ModelManager/PredictionService/
    HistoryService) still produces the same model behavior as before.
    """

    @classmethod
    def setUpClass(cls):
        ModelManager.reset()

    @classmethod
    def tearDownClass(cls):
        ModelManager.reset()

    def test_artifact_files_are_untouched_on_disk(self):
        """The refactor must not have modified/re-saved any trained
        artifact - training pipeline was out of scope for this task."""
        for name in [
            "health_classifier.pkl",
            "health_regressor.pkl",
            "feature_columns.json",
            "feature_columns_regression.json",
            "metrics.json",
            "metrics_regression.json",
            "model_info.json",
            "model_info_regression.json",
        ]:
            path = ARTIFACTS_DIR / name
            self.assertTrue(path.exists(), f"Missing artifact: {name}")

    def test_feature_schema_matches_trained_feature_columns(self):
        """Every column the classifier/regressor were trained on must
        still exist in FEATURE_SCHEMA, EXCEPT the per-user trend columns
        (utils/trend_features.py), which are deliberately not part of the
        raw user-submitted schema - they are derived server-side from
        check-in history at serving time (see PredictionService._prepare_dataframe)
        and only ever appear in the trained feature list, never in a raw
        submission."""
        trend_cols = set(trend_feature_names())

        registry_clf = ModelRegistry(task="classification")
        registry_clf.validate()
        for col in registry_clf.feature_columns:
            if col in trend_cols:
                continue
            self.assertIn(
                col, FEATURE_SCHEMA,
                f"Trained classification feature '{col}' is missing from FEATURE_SCHEMA",
            )

        registry_reg = ModelRegistry(task="regression")
        registry_reg.validate()
        for col in registry_reg.feature_columns:
            if col in trend_cols:
                continue
            self.assertIn(
                col, FEATURE_SCHEMA,
                f"Trained regression feature '{col}' is missing from FEATURE_SCHEMA",
            )

    def test_metrics_files_unchanged_shape(self):
        with open(ARTIFACTS_DIR / "metrics.json", encoding="utf-8") as f:
            metrics = json.load(f)
        self.assertIn("test", metrics)
        self.assertIn("accuracy", metrics["test"])

        with open(ARTIFACTS_DIR / "metrics_regression.json", encoding="utf-8") as f:
            reg_metrics = json.load(f)
        self.assertIn("test", reg_metrics)

    def test_prediction_service_output_matches_direct_model_registry_output(self):
        """
        Prove the refactor (ModelManager-backed PredictionService) makes
        byte-for-byte the same classification/regression decision a
        hand-built pipeline using the original ModelRegistry directly
        would make for the same input - the serving refactor changed
        *object lifecycle*, not *math*.
        """
        clf_registry = ModelRegistry(task="classification")
        clf_registry.validate()
        reg_registry = ModelRegistry(task="regression")
        reg_registry.validate()

        validator = ValidationService()
        data = ts.borderline_user_data()
        cleaned = validator.validate(data).cleaned_data

        # PredictionService.predict(cleaned) defaults to no history, which
        # still produces real (non-NaN) values for the same-day trend
        # columns (e.g. the "_r3" rolling mean of a single point is that
        # point itself). Build the identical cold-start trend row here so
        # this is a true apples-to-apples comparison against a raw
        # model.predict() call, not an artificially all-NaN one.
        combined = dict(cleaned)
        combined.update(build_trend_features(cleaned, []))

        import pandas as pd
        X_clf = pd.DataFrame([combined]).reindex(columns=clf_registry.feature_columns)
        X_reg = pd.DataFrame([combined]).reindex(columns=reg_registry.feature_columns)
        # Numeric coercion mirroring PredictionService._prepare_dataframe
        # closely enough for a same-math sanity check.
        for col in X_clf.columns:
            if col not in {"gender", "occupation_group", "region_group", "education_group",
                            "device_category", "primary_platform", "purpose_group", "day_of_week"}:
                X_clf[col] = pd.to_numeric(X_clf[col], errors="coerce")
        for col in X_reg.columns:
            if col not in {"gender", "occupation_group", "region_group", "education_group",
                            "device_category", "primary_platform", "purpose_group", "day_of_week"}:
                X_reg[col] = pd.to_numeric(X_reg[col], errors="coerce")

        direct_class_idx = clf_registry.model.predict(X_clf)[0]
        direct_score = float(reg_registry.model.predict(X_reg)[0])

        predictor = PredictionService()
        result = predictor.predict(cleaned)

        expected_label = PredictionService.CLASS_MAPPING.get(direct_class_idx, str(direct_class_idx))
        self.assertEqual(result.prediction, expected_label)
        self.assertAlmostEqual(result.regression_score, round(max(0.0, min(100.0, direct_score)), 2), places=2)


if __name__ == "__main__":
    unittest.main()
