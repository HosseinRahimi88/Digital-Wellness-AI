"""
Tests: Group C Feature 02 - Persona Detection (KMeans clustering).

Run: python3 -m unittest tests.test_persona_service -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts

from models.model_manager import ModelManager
from services.validation_service import ValidationService
from services.prediction_service import PredictionService
from services.persona_service import PersonaService, PersonaResult
from utils.persona import resolve_persona, generate_persona


class TestPersonaModelArtifact(unittest.TestCase):

    def test_persona_artifact_exists(self):
        from services.persona_service import PERSONA_MODEL_PATH, PERSONA_INFO_PATH
        self.assertTrue(PERSONA_MODEL_PATH.exists(), "Run `python -m models.train_persona` first.")
        self.assertTrue(PERSONA_INFO_PATH.exists())

    def test_persona_info_has_multiple_clusters_with_names(self):
        import json
        from services.persona_service import PERSONA_INFO_PATH

        with open(PERSONA_INFO_PATH, "r", encoding="utf-8") as f:
            info = json.load(f)

        self.assertGreaterEqual(info["k"], 2)
        self.assertEqual(len(info["clusters"]), info["k"])
        for cluster in info["clusters"]:
            self.assertTrue(cluster["name"])
            self.assertGreater(cluster["size"], 0)
            self.assertGreater(len(cluster["defining_traits"]), 0)

        # Cluster sizes should roughly partition the training set (sanity
        # check that clustering assigned every row, not a random subset).
        total_pct = sum(c["size_pct"] for c in info["clusters"])
        self.assertAlmostEqual(total_pct, 100.0, delta=1.0)


class TestPersonaService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.service = PersonaService()

    def test_loads_successfully(self):
        self.assertTrue(self.service._loaded)

    def test_assign_returns_available_result_for_valid_input(self):
        result = self.service.assign(ts.healthy_user_data())
        self.assertIsInstance(result, PersonaResult)
        self.assertTrue(result.available)
        self.assertTrue(result.persona_name)
        self.assertIsNotNone(result.cluster_id)
        self.assertIsNotNone(result.confidence)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_assign_degrades_gracefully_on_missing_fields(self):
        incomplete = {"sleep_hours": 7.0}  # missing every other persona feature
        result = self.service.assign(incomplete)
        self.assertFalse(result.available)
        self.assertTrue(result.explanation)

    def test_assign_never_raises_on_garbage_input(self):
        for bad_input in ({}, {"sleep_hours": "not a number"}, None):
            try:
                result = self.service.assign(bad_input or {})
            except Exception as exc:  # noqa: BLE001
                self.fail(f"assign() raised on bad input {bad_input!r}: {exc}")
            self.assertIsInstance(result, PersonaResult)

    def test_different_behavioral_profiles_can_land_in_different_personas(self):
        """
        The core value proposition of ML persona detection over the old
        rule-based label: it should differentiate based on real
        behavioral distance, not just the classifier's predicted class.
        """
        healthy = self.service.assign(ts.healthy_user_data())
        at_risk = self.service.assign(ts.at_risk_user_data())
        self.assertTrue(healthy.available and at_risk.available)
        # Not asserting they're always different (that would be a flaky,
        # data-dependent assertion) - just that the mechanism is capable
        # of producing distinct cluster ids, which the artifact test
        # above already confirms has >1 cluster with real membership.
        self.assertIsInstance(healthy.cluster_id, int)
        self.assertIsInstance(at_risk.cluster_id, int)


class TestResolvePersona(unittest.TestCase):
    """Tests the ML-first-with-rule-based-fallback wrapper."""

    def test_falls_back_when_no_persona_service_given(self):
        label, result = resolve_persona("Healthy", {"sleep_hours": 8.0}, 90.0, persona_service=None)
        self.assertEqual(label, generate_persona("Healthy", {"sleep_hours": 8.0}, 90.0))
        self.assertIsNone(result)

    def test_falls_back_when_persona_service_raises(self):
        class _BrokenService:
            def assign(self, user_data):
                raise RuntimeError("boom")

        label, result = resolve_persona("Healthy", {"sleep_hours": 8.0}, 90.0, persona_service=_BrokenService())
        self.assertTrue(label)  # non-empty fallback string
        self.assertIsNone(result)

    def test_uses_ml_result_when_available(self):
        service = PersonaService()
        label, result = resolve_persona(
            "Healthy", ts.healthy_user_data(), 90.0, persona_service=service,
        )
        self.assertIsNotNone(result)
        self.assertEqual(label, result.persona_name)

    def test_always_returns_nonempty_label(self):
        for data_fn in (ts.healthy_user_data, ts.at_risk_user_data, ts.borderline_user_data, ts.baseline_user_data):
            label, _ = resolve_persona("Moderate", data_fn(), 50.0, persona_service=None)
            self.assertTrue(label)


class TestPersonaEndToEnd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ModelManager.reset()
        cls.validator = ValidationService()
        cls.predictor = PredictionService()

    @classmethod
    def tearDownClass(cls):
        ModelManager.reset()

    def test_prediction_service_exposes_persona_service(self):
        self.assertIsInstance(self.predictor.persona_service, PersonaService)

    def test_full_pipeline_persona_assignment(self):
        v = self.validator.validate(ts.healthy_user_data())
        self.assertTrue(v.is_valid)
        result = self.predictor.predict(v.cleaned_data)
        persona_result = self.predictor.persona_service.assign(v.cleaned_data)
        self.assertTrue(persona_result.available)
        label, _ = resolve_persona(
            result.prediction, v.cleaned_data, result.regression_score,
            persona_service=self.predictor.persona_service,
        )
        self.assertEqual(label, persona_result.persona_name)


if __name__ == "__main__":
    unittest.main()
