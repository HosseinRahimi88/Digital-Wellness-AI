"""
Tests: prediction + SHAP pipeline under real load - both high thread
concurrency and sustained sequential volume.

Scope and what these do NOT test: whether Python threads give real
CPU parallelism for this pipeline is an environment/library-version
characteristic (see MERGE_REPORT.md's "SHAP concurrency" addendum for
the measured finding: with the real, installed scikit-learn in this
sandbox, both classifier.predict_proba() and SHAPService.explain()
showed ~1.0x speedup under threads - i.e. no parallel benefit, full
GIL serialization for single-row inference). That is NOT something to
assert pass/fail here - it can legitimately vary by scikit-learn
version, BLAS backend, and platform, and it says nothing about
*correctness*. What CAN and should be asserted permanently:
  1. High concurrency produces zero errors and zero cross-contaminated
     results (thread-safety of the shared ModelManager/SHAPService
     singleton).
  2. Sustained volume does not leak memory.

Run: python3 -m unittest tests.test_shap_load -v

Timing note: this file is genuinely slow in this offline sandbox (the
ablation-based SHAP stub does O(n_features) model.predict() calls per
explanation - tens to hundreds of times slower than the real, compiled
shap.TreeExplainer). In an environment with the real `shap` package
installed, this file runs in well under a second; N_CONCURRENT and N
below are deliberately kept small (10/20, matching A's own existing
tests/test_concurrency.py precedent) specifically so this stays
tolerable to run routinely even in this slower sandbox.
"""

from __future__ import annotations

import gc
import resource
import threading
import unittest

import tests._test_support as ts  # noqa: F401

from models.model_manager import ModelManager
from services.prediction_service import PredictionService
from services.validation_service import ValidationService
from config.demo_profiles import healthy_profile, at_risk_profile, borderline_profile

SCENARIOS = [healthy_profile(), at_risk_profile(), borderline_profile()]


def _rss_mb() -> float:
    """Process max-RSS in MB (Linux: ru_maxrss is KB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


class TestHighConcurrencyCorrectness(unittest.TestCase):
    """N threads hitting the shared prediction+SHAP pipeline at once
    must never error, and must never return one thread's result mixed
    into another's (would indicate the shared ModelManager/SHAPService
    singleton isn't actually safe for concurrent reads)."""

    N_CONCURRENT = 10

    @classmethod
    def setUpClass(cls):
        ModelManager.reset()
        ModelManager.instance()  # warm the singleton once, outside the timed section

    @classmethod
    def tearDownClass(cls):
        ModelManager.reset()

    def test_no_errors_and_no_cross_contamination_under_high_concurrency(self):
        predictor = PredictionService()
        results = [None] * self.N_CONCURRENT
        errors = []
        lock = threading.Lock()

        def worker(i):
            try:
                validator = ValidationService()
                data = SCENARIOS[i % len(SCENARIOS)]
                validated = validator.validate(data)
                results[i] = predictor.predict(validated.cleaned_data)
            except Exception as exc:  # pragma: no cover - failure path
                with lock:
                    errors.append((i, repr(exc)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(self.N_CONCURRENT)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"{len(errors)} request(s) raised under concurrency: {errors[:3]}")

        # Same scenario index -> must always agree on predicted class.
        for i in range(self.N_CONCURRENT):
            scenario_idx = i % len(SCENARIOS)
            peers = [
                results[j] for j in range(self.N_CONCURRENT)
                if j % len(SCENARIOS) == scenario_idx and results[j] is not None
            ]
            for peer in peers:
                self.assertEqual(
                    results[i].prediction, peer.prediction,
                    "Cross-contaminated result under concurrency - shared "
                    "singleton is not safe for concurrent predict() calls.",
                )

    def test_shap_explainer_is_a_single_shared_instance_not_rebuilt_per_request(self):
        """The expensive part (building the SHAP explainer) must happen
        once per process, not once per PredictionService/request - this
        is what actually prevents concurrent load from being expensive,
        independent of thread-parallelism characteristics."""
        a = PredictionService()
        b = PredictionService()
        self.assertIs(a.shap_service, b.shap_service)
        self.assertIs(a.shap_service, ModelManager.instance().shap_service)


class TestSustainedLoadMemoryStability(unittest.TestCase):
    """Many predictions in sequence must not grow process memory
    unboundedly - the practical 'does it explode under sustained
    traffic' question, independent of concurrency."""

    def test_memory_does_not_grow_across_many_sequential_predictions(self):
        ModelManager.reset()
        ModelManager.instance()
        predictor = PredictionService()
        validator = ValidationService()

        N = 20
        gc.collect()
        baseline_mb = _rss_mb()

        for i in range(N):
            data = validator.validate(SCENARIOS[i % len(SCENARIOS)])
            predictor.predict(data.cleaned_data)

        gc.collect()
        final_mb = _rss_mb()
        growth_mb = final_mb - baseline_mb

        # Generous threshold - this is a leak smoke test, not a tight
        # bound. A real leak (e.g. an explainer or dataframe list that
        # grows unboundedly) would show growth in the hundreds of MB
        # over just 60 predictions, not single digits.
        self.assertLess(
            growth_mb, 50,
            f"RSS grew {growth_mb:.1f}MB over {N} predictions "
            f"({baseline_mb:.1f}MB -> {final_mb:.1f}MB) - possible leak.",
        )

        ModelManager.reset()


if __name__ == "__main__":
    unittest.main()
