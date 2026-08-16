"""
Tests: JSONFileStorageBackend resilience - corrupted file on disk,
malformed (non-list) JSON, and a from-scratch empty history should
never raise up into the UI layer.

Run: python3 -m unittest tests.storage.test_storage_corruption -v
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import tests._test_support  # noqa: F401  (sys.path bootstrap)

from services.identity.history_service import HistoryService
from services.storage.json_file_storage import JSONFileStorageBackend


class TestStorageCorruption(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_corrupt_test_"))
        self.storage_path = self._tmp_dir / "prediction_history.json"

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_missing_file_reads_as_empty_list(self):
        backend = JSONFileStorageBackend(self.storage_path)
        self.assertEqual(backend.read_all(), [])

    def test_truncated_invalid_json_reads_as_empty_list_not_raise(self):
        self.storage_path.write_text("{not valid json::::", encoding="utf-8")
        backend = JSONFileStorageBackend(self.storage_path)
        self.assertEqual(backend.read_all(), [])

    def test_non_list_json_reads_as_empty_list_not_raise(self):
        self.storage_path.write_text('{"oops": "this is an object, not an array"}', encoding="utf-8")
        backend = JSONFileStorageBackend(self.storage_path)
        self.assertEqual(backend.read_all(), [])

    def test_history_service_on_empty_history_never_raises(self):
        """Every HistoryService read method must degrade gracefully to an
        empty/None result on brand-new (or corrupted-then-recovered)
        storage, since every page checks `if not all_entries: ...`."""
        service = HistoryService(user_id="u1", storage_path=self.storage_path)
        self.assertEqual(service.get_all(), [])
        self.assertEqual(service.first_week_entries(), [])
        self.assertEqual(service.current_week_entries(), [])
        self.assertEqual(service.previous_week_entries(), [])
        self.assertIsNone(service.summarize(service.get_all()))
        days = service.get_last_n_days(n=7)
        self.assertEqual(len(days), 7)
        self.assertTrue(all(d["entry"] is None for d in days))

    def test_history_service_recovers_and_writes_after_corrupted_file(self):
        """A corrupted on-disk file must not block new writes - the next
        successful record() should overwrite it with valid JSON."""
        self.storage_path.write_text("not json at all", encoding="utf-8")
        service = HistoryService(user_id="u1", storage_path=self.storage_path)

        class _FakeResult:
            prediction = "Healthy"
            confidence = 0.9
            regression_score = 80.0
            shap_features = None

        entry = service.record(user_data={"sleep_hours": 8.0}, prediction_result=_FakeResult())
        self.assertEqual(entry["health_score"], 80.0)
        self.assertEqual(len(service.get_all()), 1)


if __name__ == "__main__":
    unittest.main()
