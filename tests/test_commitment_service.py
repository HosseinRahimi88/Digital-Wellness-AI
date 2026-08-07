"""
Tests: CommitmentService (feature 41 - Commitment Tracking).

Run: python3 -m unittest tests.test_commitment_service -v
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import tests._test_support  # noqa: F401

from services.commitment_service import CommitmentService, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_ABANDONED
from services.storage.json_file_storage import JSONFileStorageBackend


class TestCommitmentService(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_commitment_test_"))
        self.storage_path = self._tmp_dir / "commitments.json"

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _service(self, user_id: str) -> CommitmentService:
        return CommitmentService(user_id=user_id, backend=JSONFileStorageBackend(self.storage_path))

    def test_commit_creates_active_commitment(self):
        svc = self._service("alice")
        commitment = svc.commit("Sleep", on_date=date(2026, 1, 5))
        self.assertEqual(commitment.status, STATUS_ACTIVE)
        self.assertEqual(commitment.category, "Sleep")
        self.assertEqual(commitment.committed_on, "2026-01-05")

    def test_recommitting_to_same_active_category_is_a_noop(self):
        svc = self._service("alice")
        first = svc.commit("Sleep", on_date=date(2026, 1, 5))
        second = svc.commit("Sleep", on_date=date(2026, 1, 10))
        self.assertEqual(first.commitment_id, second.commitment_id)
        self.assertEqual(len(svc.get_all()), 1)

    def test_resolve_marks_completed(self):
        svc = self._service("alice")
        commitment = svc.commit("Sleep", on_date=date(2026, 1, 5))
        svc.resolve(commitment.commitment_id, STATUS_COMPLETED, on_date=date(2026, 1, 12))
        resolved = svc.get_all()[0]
        self.assertEqual(resolved.status, STATUS_COMPLETED)
        self.assertEqual(resolved.resolved_on, "2026-01-12")
        self.assertEqual(svc.get_active(), [])

    def test_resolve_rejects_invalid_status(self):
        svc = self._service("alice")
        commitment = svc.commit("Sleep")
        with self.assertRaises(ValueError):
            svc.resolve(commitment.commitment_id, "bogus_status")

    def test_users_do_not_see_each_others_commitments(self):
        alice = self._service("alice")
        bob = self._service("bob")
        alice.commit("Sleep", on_date=date(2026, 1, 5))
        bob.commit("Focus", on_date=date(2026, 1, 5))
        self.assertEqual([c.category for c in alice.get_all()], ["Sleep"])
        self.assertEqual([c.category for c in bob.get_all()], ["Focus"])

    def test_after_completion_recommitting_creates_a_new_record(self):
        svc = self._service("alice")
        first = svc.commit("Sleep", on_date=date(2026, 1, 5))
        svc.resolve(first.commitment_id, STATUS_COMPLETED, on_date=date(2026, 1, 12))
        second = svc.commit("Sleep", on_date=date(2026, 1, 13))
        self.assertNotEqual(first.commitment_id, second.commitment_id)
        self.assertEqual(len(svc.get_all()), 2)
        self.assertEqual(len(svc.get_active()), 1)


if __name__ == "__main__":
    unittest.main()
