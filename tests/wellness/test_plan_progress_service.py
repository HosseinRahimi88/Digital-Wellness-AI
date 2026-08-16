"""
Tests: PlanProgressService (per-user, per-week plan task tracking).

Run: python3 -m unittest tests.wellness.test_plan_progress_service -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401

from services.wellness.plan_progress_service import PlanProgressService, current_week_key
from services.storage.json_file_storage import JSONFileStorageBackend


def _make_service(user_id: str = "user-1") -> PlanProgressService:
    tmp_dir = Path(tempfile.mkdtemp())
    backend = JSONFileStorageBackend(tmp_dir / "plan_progress.json")
    return PlanProgressService(user_id=user_id, backend=backend)


class TestPlanProgressService(unittest.TestCase):

    def test_new_user_has_no_completed_tasks(self):
        service = _make_service()
        self.assertEqual(service.get_completed(), set())

    def test_marking_a_task_complete_persists(self):
        service = _make_service()
        service.set_completed(day_number=1, task_index=0, completed=True)
        self.assertIn((1, 0), service.get_completed())

    def test_unmarking_a_task_removes_it(self):
        service = _make_service()
        service.set_completed(day_number=1, task_index=0, completed=True)
        service.set_completed(day_number=1, task_index=0, completed=False)
        self.assertNotIn((1, 0), service.get_completed())

    def test_persists_across_separate_service_instances_same_backend(self):
        tmp_dir = Path(tempfile.mkdtemp())
        backend_path = tmp_dir / "plan_progress.json"

        first = PlanProgressService(user_id="user-1", backend=JSONFileStorageBackend(backend_path))
        first.set_completed(day_number=2, task_index=1, completed=True)

        second = PlanProgressService(user_id="user-1", backend=JSONFileStorageBackend(backend_path))
        self.assertIn((2, 1), second.get_completed())

    def test_different_users_do_not_see_each_others_progress(self):
        tmp_dir = Path(tempfile.mkdtemp())
        backend_path = tmp_dir / "plan_progress.json"

        user_a = PlanProgressService(user_id="user-a", backend=JSONFileStorageBackend(backend_path))
        user_b = PlanProgressService(user_id="user-b", backend=JSONFileStorageBackend(backend_path))

        user_a.set_completed(day_number=1, task_index=0, completed=True)

        self.assertIn((1, 0), user_a.get_completed())
        self.assertNotIn((1, 0), user_b.get_completed())

    def test_different_weeks_are_isolated(self):
        service = _make_service()
        service.set_completed(day_number=1, task_index=0, completed=True, week_key="2026-W01")
        service.set_completed(day_number=1, task_index=0, completed=True, week_key="2026-W02")

        self.assertIn((1, 0), service.get_completed(week_key="2026-W01"))
        service.set_completed(day_number=1, task_index=0, completed=False, week_key="2026-W01")
        # Un-marking week 1's task must not touch week 2's identical task.
        self.assertNotIn((1, 0), service.get_completed(week_key="2026-W01"))
        self.assertIn((1, 0), service.get_completed(week_key="2026-W02"))

    def test_current_week_key_format(self):
        key = current_week_key()
        self.assertRegex(key, r"^\d{4}-W\d{2}$")


if __name__ == "__main__":
    unittest.main()
