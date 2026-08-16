"""
Tests: concurrent prediction load (10 simultaneous users).

Run: python3 -m unittest tests.storage.test_concurrency -v

Note on timing: `services/ml/shap_service.py` runs unmodified in these
tests, but the third-party `shap` package itself is swapped for a
lightweight real-ablation stand-in in this offline sandbox (see
tests/_test_support.py docstring) because the real optimized C++
TreeExplainer can't be pip-installed here. The stub is ~O(n_features)
model calls per explanation instead of TreeExplainer's near-instant
tree traversal, so absolute latency numbers below are pessimistic vs.
production and should not be read as the real SHAP-enabled latency -
what matters for this test is *correctness under concurrency*, not the
absolute millisecond figure.
"""

from __future__ import annotations

import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

import tests._test_support as ts

from models.model_manager import ModelManager
from services.ml.validation_service import ValidationService
from services.ml.prediction_service import PredictionService

N_CONCURRENT = 10


class TestConcurrentPredictions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ModelManager.reset()
        # Force the singleton to load once, up front, outside the timed
        # section - mirrors a warmed-up server process.
        ModelManager.instance()

    @classmethod
    def tearDownClass(cls):
        ModelManager.reset()

    def test_ten_concurrent_predictions_succeed(self):
        validator = ValidationService()
        predictor = PredictionService()

        scenarios = [
            ts.healthy_user_data(),
            ts.at_risk_user_data(),
            ts.borderline_user_data(),
        ]
        # 10 "users" hitting predict() at the same moment, cycling
        # through the three real scenarios so it isn't just the same
        # call 10 times.
        payloads = [scenarios[i % len(scenarios)] for i in range(N_CONCURRENT)]

        start_barrier = threading.Barrier(N_CONCURRENT)
        errors: list[BaseException] = []
        results: list = [None] * N_CONCURRENT
        durations_ms: list[float] = [0.0] * N_CONCURRENT

        def worker(idx: int, user_data: dict):
            validation = validator.validate(user_data)
            start_barrier.wait()  # line everyone up, fire together
            t0 = time.perf_counter()
            try:
                results[idx] = predictor.predict(validation.cleaned_data)
            except BaseException as exc:  # noqa: BLE001 - we want to catch/report everything
                errors.append(exc)
            finally:
                durations_ms[idx] = (time.perf_counter() - t0) * 1000

        wall_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=N_CONCURRENT) as pool:
            futures = [
                pool.submit(worker, i, payloads[i]) for i in range(N_CONCURRENT)
            ]
            for f in as_completed(futures):
                f.result()  # re-raise any executor-level exception
        wall_total_ms = (time.perf_counter() - wall_start) * 1000

        # ---- Assertions -----------------------------------------

        self.assertEqual(
            errors, [],
            f"{len(errors)}/{N_CONCURRENT} concurrent predictions raised: {errors}",
        )

        for i, result in enumerate(results):
            self.assertIsNotNone(result, f"Result {i} missing")
            self.assertIn(result.prediction, {"At Risk", "Moderate", "Healthy"})
            self.assertAlmostEqual(sum(result.probabilities.values()), 1.0, places=2)
            self.assertGreaterEqual(result.regression_score, 0.0)
            self.assertLessEqual(result.regression_score, 100.0)

        # Every user cycling through the *same* scenario got the *same*
        # answer - no cross-talk/state bleeding between concurrent
        # requests sharing the one PredictionService/model instance.
        for i in range(N_CONCURRENT):
            baseline = i % len(scenarios)
            self.assertEqual(
                results[i].prediction, results[baseline].prediction,
                f"Request {i} (same scenario as {baseline}) got a different "
                f"class - possible shared-state corruption under concurrency.",
            )
            self.assertAlmostEqual(
                results[i].regression_score, results[baseline].regression_score,
                places=6,
                msg=f"Request {i} got a different score than request {baseline} "
                    f"for the identical input - possible race condition.",
            )

        print(
            f"\n[concurrency] {N_CONCURRENT} concurrent predictions: "
            f"wall={wall_total_ms:.1f}ms, "
            f"per-request avg={sum(durations_ms)/len(durations_ms):.1f}ms, "
            f"min={min(durations_ms):.1f}ms, max={max(durations_ms):.1f}ms, "
            f"errors=0"
        )

    def test_model_manager_still_singleton_after_concurrent_access(self):
        """First-touch race: N threads all calling ModelManager.instance()
        for the first time at once must still produce exactly one
        instance (double-checked locking correctness)."""
        ModelManager.reset()

        seen = [None] * N_CONCURRENT
        barrier = threading.Barrier(N_CONCURRENT)

        def worker(idx):
            barrier.wait()
            seen[idx] = ModelManager.instance()

        with ThreadPoolExecutor(max_workers=N_CONCURRENT) as pool:
            list(pool.map(worker, range(N_CONCURRENT)))

        first = seen[0]
        for i, instance in enumerate(seen):
            self.assertIs(instance, first, f"Thread {i} got a different ModelManager instance")


class TestHistoryServiceUpsertRace(unittest.TestCase):
    """N concurrent record() calls for the SAME (user, date) key must
    upsert - end with exactly one entry, not N duplicates and not a
    lost write - since HistoryService.record() advertises this
    guarantee (see its docstring) but nothing exercised it under real
    concurrency until now."""

    def test_concurrent_record_same_user_same_date_upserts_not_duplicates(self):
        import tempfile
        from pathlib import Path
        from datetime import date

        from services.identity.history_service import HistoryService
        from services.storage.json_file_storage import JSONFileStorageBackend

        path = Path(tempfile.mkdtemp()) / "prediction_history.json"

        class _FakeResult:
            def __init__(self, score):
                self.regression_score = score
                self.prediction = "Healthy"
                self.confidence = 0.9
                self.shap_features = []

        def worker(i):
            service = HistoryService(user_id="same-user", storage=JSONFileStorageBackend(path))
            service.record(
                user_data={}, prediction_result=_FakeResult(float(i)),
                persona="p", on_date=date(2026, 1, 1),
            )

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_CONCURRENT)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        import json
        records = json.loads(path.read_text())
        same_key = [
            r for r in records
            if r.get("user_id") == "same-user" and r.get("date") == "2026-01-01"
        ]
        self.assertEqual(len(same_key), 1)


if __name__ == "__main__":
    unittest.main()
