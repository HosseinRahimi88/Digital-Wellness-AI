"""
Tests: ModelManager singleton / load-once behavior.

Run: python3 -m unittest tests.ml.test_model_manager -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401  (sets up sys.path + shap stub)

import joblib

from models.model_manager import ModelManager
from models.model_registry import ModelRegistry


class TestModelManagerSingleton(unittest.TestCase):

    def setUp(self):
        ModelManager.reset()

    def tearDown(self):
        ModelManager.reset()

    def test_instance_returns_same_object(self):
        a = ModelManager.instance()
        b = ModelManager.instance()
        self.assertIs(a, b, "ModelManager.instance() must return the exact same object")

    def test_prediction_service_shares_singleton(self):
        """
        Two independent PredictionService() constructions (mirroring two
        different Streamlit pages each doing their own st.cache_resource
        loader, as Prediction.py and What_If_Simulator.py do) must end up
        pointing at the *same* underlying model objects instead of each
        loading their own copy.
        """
        from services.ml.prediction_service import PredictionService

        svc_a = PredictionService()
        svc_b = PredictionService()

        self.assertIs(svc_a.classification_model, svc_b.classification_model)
        self.assertIs(svc_a.regression_model, svc_b.regression_model)
        self.assertIs(svc_a.shap_service, svc_b.shap_service)
        self.assertIs(svc_a._model_manager, svc_b._model_manager)

    def test_model_loaded_exactly_once_from_disk(self):
        """
        Regardless of how many times ModelManager.instance() or
        PredictionService() is called, joblib.load (the actual
        artifact-from-disk read) must only fire once per artifact.
        """
        call_count = {"n": 0}
        real_load = joblib.load

        def counting_load(path, *args, **kwargs):
            call_count["n"] += 1
            return real_load(path, *args, **kwargs)

        joblib.load = counting_load
        try:
            from services.ml.prediction_service import PredictionService

            PredictionService()
            PredictionService()
            PredictionService()
            ModelManager.instance()
            ModelManager.instance()
        finally:
            joblib.load = real_load

        # Exactly 3 artifact loads total for the whole process: 1
        # classifier + 1 regressor + 1 persona clustering model (Group C
        # Feature 02 - added as its own joblib artifact, loaded once by
        # ModelManager alongside the other two) - never re-loaded on
        # subsequent PredictionService()/ModelManager.instance() calls.
        self.assertEqual(
            call_count["n"], 3,
            f"Expected exactly 3 joblib.load calls (classifier+regressor+persona) "
            f"across multiple PredictionService()/ModelManager.instance() "
            f"calls, got {call_count['n']}.",
        )

    def test_direct_construction_is_blocked(self):
        """ModelManager() directly (bypassing .instance()) must fail loudly
        rather than silently duplicating the load."""
        ModelManager.instance()  # first, legitimate load
        with self.assertRaises(RuntimeError):
            ModelManager()

    def test_manager_artifacts_match_standalone_registry(self):
        """Sanity check: the singleton's loaded artifacts are equivalent
        in content to a freshly-constructed ModelRegistry (i.e. the
        refactor didn't change *what* gets loaded, only *how often*)."""
        manager = ModelManager.instance()
        standalone = ModelRegistry(task="classification")
        standalone.validate()

        self.assertEqual(
            manager.classification_feature_columns,
            standalone.feature_columns,
        )
        self.assertEqual(manager.classes, standalone.classes)


if __name__ == "__main__":
    unittest.main()
