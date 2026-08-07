"""
Tests: storage concurrency + user isolation.

Run: python3 -m unittest tests.test_history_storage -v
"""

from __future__ import annotations

import shutil
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import tests._test_support  # noqa: F401

from services.history_service import HistoryService
from services.storage.json_file_storage import JSONFileStorageBackend


@dataclass
class _FakePredictionResult:
    prediction: str
    confidence: float
    regression_score: float
    shap_features: Optional[list] = None


class TestHistoryStorage(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_history_test_"))
        self.storage_path = self._tmp_dir / "prediction_history.json"

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _service(self, user_id: str) -> HistoryService:
        return HistoryService(user_id=user_id, storage_path=self.storage_path)

    # ------------------------------------------------------

    def test_record_and_read_roundtrip(self):
        svc = self._service("alice")
        result = _FakePredictionResult(prediction="Healthy", confidence=0.9, regression_score=88.0)
        svc.record(user_data={"total_screen_min": 100}, prediction_result=result)

        entries = svc.get_all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["health_class"], "Healthy")
        self.assertEqual(entries[0]["user_id"], "alice")

    def test_users_do_not_see_each_others_entries(self):
        alice = self._service("alice")
        bob = self._service("bob")

        today = date.today()
        alice.record(
            user_data={"total_screen_min": 100},
            prediction_result=_FakePredictionResult("Healthy", 0.9, 90.0),
            on_date=today,
        )
        bob.record(
            user_data={"total_screen_min": 500},
            prediction_result=_FakePredictionResult("At Risk", 0.8, 20.0),
            on_date=today,
        )

        alice_entries = alice.get_all()
        bob_entries = bob.get_all()

        self.assertEqual(len(alice_entries), 1)
        self.assertEqual(len(bob_entries), 1)
        self.assertEqual(alice_entries[0]["health_class"], "Healthy")
        self.assertEqual(bob_entries[0]["health_class"], "At Risk")

        # This is the bug the old date-only-keyed storage had: both users
        # predicting on the same calendar date used to collide into one
        # shared entry. Confirm the raw backend actually holds 2 rows.
        raw = JSONFileStorageBackend(self.storage_path).read_all()
        self.assertEqual(len(raw), 2)

    def test_same_user_same_day_upserts_instead_of_duplicating(self):
        alice = self._service("alice")
        today = date.today()
        alice.record(
            user_data={"total_screen_min": 100},
            prediction_result=_FakePredictionResult("Healthy", 0.9, 90.0),
            on_date=today,
        )
        alice.record(
            user_data={"total_screen_min": 150},
            prediction_result=_FakePredictionResult("Moderate", 0.7, 70.0),
            on_date=today,
        )
        entries = alice.get_all()
        self.assertEqual(len(entries), 1, "second prediction same day should update, not duplicate")
        self.assertEqual(entries[0]["health_class"], "Moderate")

    def test_legacy_entries_without_user_id_are_treated_as_default(self):
        """Backward compatibility with data written before user_id existed."""
        import json
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_entry = {
            "date": "2026-01-01",
            "day_of_week": "Thursday",
            "health_score": 77.0,
            "health_class": "Moderate",
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([legacy_entry], f)

        default_user = self._service("default")
        other_user = self._service("someone-else")

        self.assertEqual(len(default_user.get_all()), 1)
        self.assertEqual(len(other_user.get_all()), 0)

    # ------------------------------------------------------
    # Concurrency
    # ------------------------------------------------------

    def test_concurrent_writes_from_many_users_no_data_loss(self):
        """
        Simulates N users each recording a prediction for a *different*
        day, all at the same instant. The old implementation's
        load -> mutate -> save with no locking could lose writes under
        this exact pattern; the new storage.transaction() lock must not.
        """
        n_users = 10
        base_day = date(2026, 1, 1)
        barrier = threading.Barrier(n_users)
        errors: list[BaseException] = []

        def worker(i: int):
            svc = self._service(f"user{i}")
            barrier.wait()
            try:
                svc.record(
                    user_data={"total_screen_min": 100 + i},
                    prediction_result=_FakePredictionResult(
                        prediction="Healthy", confidence=0.9, regression_score=float(50 + i),
                    ),
                    on_date=base_day + timedelta(days=i),
                )
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=n_users) as pool:
            list(pool.map(worker, range(n_users)))

        self.assertEqual(errors, [], f"Concurrent writes raised: {errors}")

        raw = JSONFileStorageBackend(self.storage_path).read_all()
        self.assertEqual(
            len(raw), n_users,
            f"Expected {n_users} entries (one per user), found {len(raw)} - "
            f"data was lost under concurrent writes.",
        )
        user_ids_seen = {e["user_id"] for e in raw}
        self.assertEqual(user_ids_seen, {f"user{i}" for i in range(n_users)})

    def test_concurrent_writes_same_user_many_days_no_data_loss(self):
        """Same single user, many different days, all written concurrently -
        every day's entry must survive (tests the lock, not just isolation)."""
        n_days = 15
        svc_template_user = "carol"
        base_day = date(2026, 2, 1)
        barrier = threading.Barrier(n_days)
        errors: list[BaseException] = []

        def worker(i: int):
            svc = self._service(svc_template_user)
            barrier.wait()
            try:
                svc.record(
                    user_data={"total_screen_min": 100},
                    prediction_result=_FakePredictionResult("Healthy", 0.9, float(i)),
                    on_date=base_day + timedelta(days=i),
                )
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=n_days) as pool:
            list(pool.map(worker, range(n_days)))

        self.assertEqual(errors, [])
        entries = self._service(svc_template_user).get_all()
        self.assertEqual(len(entries), n_days)
        dates_seen = {e["date"] for e in entries}
        expected_dates = {(base_day + timedelta(days=i)).isoformat() for i in range(n_days)}
        self.assertEqual(dates_seen, expected_dates)


if __name__ == "__main__":
    unittest.main()
