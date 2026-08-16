"""Every week with a stored plan must be reachable, not just this one.

A plan snapshot has always been written once per ISO week, so a 23-day
demo leaves four of them. Nothing could list them: the weekly page
generated the current week and the earlier three were unreachable, which
is why a 23-day demo appeared to have seven days of exercises rather
than the whole run.
"""

from __future__ import annotations

import unittest

import tempfile

from services.storage.json_file_storage import JSONFileStorageBackend
from services.wellness.plan_lock_service import PlanLockService


class TestPlanLockServiceListsItsWeeks(unittest.TestCase):
    def setUp(self):
        self.backend = JSONFileStorageBackend(tempfile.mktemp(suffix=".json"))
        self.service = PlanLockService("user-1", backend=self.backend)

    def _store(self, week_key: str, days: int = 7) -> None:
        self.service.save(
            plan={"days": [{"day_number": n, "tasks": ["a", "b", "c"]}
                           for n in range(1, days + 1)]},
            week_key=week_key,
        )

    def test_an_empty_store_lists_nothing(self):
        self.assertEqual(self.service.weeks(), [])

    def test_weeks_come_back_oldest_first(self):
        for key in ("2026-W32", "2026-W30", "2026-W31"):
            self._store(key)
        self.assertEqual(
            self.service.weeks(), ["2026-W30", "2026-W31", "2026-W32"]
        )

    def test_only_this_users_weeks_are_listed(self):
        self._store("2026-W30")
        PlanLockService("user-2", backend=self.backend).save(
            plan={"days": [{"day_number": 1, "tasks": ["x"]}]},
            week_key="2026-W40",
        )
        self.assertEqual(self.service.weeks(), ["2026-W30"])

    def test_a_week_saved_twice_is_listed_once(self):
        self._store("2026-W30")
        self._store("2026-W30")
        self.assertEqual(self.service.weeks(), ["2026-W30"])

    def test_every_listed_week_actually_opens(self):
        for key in ("2026-W30", "2026-W31"):
            self._store(key)
        for key in self.service.weeks():
            with self.subTest(week=key):
                self.assertIsNotNone(self.service.get(key))

    def test_four_stored_weeks_cover_a_23_day_run(self):
        # The reported symptom: a 23-day demo showing one week of
        # exercises. Four weeks of seven days is what must be reachable.
        for key in ("2026-W30", "2026-W31", "2026-W32", "2026-W33"):
            self._store(key)
        total = sum(
            len(self.service.get(key).plan["days"]) for key in self.service.weeks()
        )
        self.assertEqual(len(self.service.weeks()), 4)
        self.assertGreaterEqual(total, 23)


if __name__ == "__main__":
    unittest.main()
