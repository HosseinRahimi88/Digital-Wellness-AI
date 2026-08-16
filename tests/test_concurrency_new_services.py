"""
Tests: real multi-threaded concurrency stress tests for the two new
storage-backed services (AccountService, PlanProgressService), the
same category of test A's own tests/test_concurrency.py already runs
for predictions and tests/test_history_storage.py runs for history -
extended here to cover the services this merge added.

Uses real `threading`, not mocks - these exercise the actual OS-level
file lock in services/storage/json_file_storage.py.

Run: python3 -m unittest tests.test_concurrency_new_services -v
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - installs offline pwdlib/shap stubs

from services.storage.json_file_storage import JSONFileStorageBackend
from services.account_service import AccountService, EmailAlreadyRegisteredError
from services.plan_progress_service import PlanProgressService

N_CONCURRENT = 30


class TestAccountServiceConcurrency(unittest.TestCase):

    def test_concurrent_registration_same_email_only_one_succeeds(self):
        path = Path(tempfile.mkdtemp()) / "accounts.json"
        successes = []
        unexpected_errors = []
        lock = threading.Lock()

        def worker(i):
            service = AccountService(backend=JSONFileStorageBackend(path))
            try:
                account = service.register(
                    email="race@example.com", password=f"password-{i}", display_name=f"U{i}"
                )
                with lock:
                    successes.append(account.user_id)
            except EmailAlreadyRegisteredError:
                pass
            except Exception as exc:  # pragma: no cover - failure path
                with lock:
                    unexpected_errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_CONCURRENT)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(unexpected_errors, [])
        self.assertEqual(len(successes), 1)

        records = json.loads(path.read_text())
        self.assertEqual(len(records), 1)

    def test_concurrent_registration_different_emails_no_lost_writes(self):
        path = Path(tempfile.mkdtemp()) / "accounts.json"
        lock = threading.Lock()
        results = []

        def worker(i):
            service = AccountService(backend=JSONFileStorageBackend(path))
            account = service.register(
                email=f"user{i}@example.com", password="hunter22", display_name=f"U{i}"
            )
            with lock:
                results.append(account.user_id)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_CONCURRENT)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        records = json.loads(path.read_text())
        self.assertEqual(len(records), N_CONCURRENT)
        self.assertEqual(len({r["user_id"] for r in records}), N_CONCURRENT)
        self.assertEqual(len({r["email"] for r in records}), N_CONCURRENT)


class TestPlanProgressServiceConcurrency(unittest.TestCase):

    def test_concurrent_writes_to_different_tasks_no_lost_writes(self):
        path = Path(tempfile.mkdtemp()) / "plan_progress.json"
        week = "2026-W32"

        def worker(i):
            service = PlanProgressService(user_id="u1", backend=JSONFileStorageBackend(path))
            service.set_completed(day_number=1, task_index=i, completed=True, week_key=week)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_CONCURRENT)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final = PlanProgressService(
            user_id="u1", backend=JSONFileStorageBackend(path)
        ).get_completed(week_key=week)
        self.assertEqual(len(final), N_CONCURRENT)

    def test_concurrent_flapping_writes_to_the_same_task_never_duplicate(self):
        path = Path(tempfile.mkdtemp()) / "plan_progress.json"
        week = "2026-W32"

        def worker(i):
            service = PlanProgressService(user_id="u2", backend=JSONFileStorageBackend(path))
            service.set_completed(day_number=2, task_index=0, completed=(i % 2 == 0), week_key=week)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_CONCURRENT)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        records = json.loads(path.read_text())
        matching = [
            r for r in records
            if r.get("user_id") == "u2" and r.get("day_number") == 2 and r.get("task_index") == 0
        ]
        self.assertLessEqual(len(matching), 1)


class TestNewServicesSurviveCorruptedStorage(unittest.TestCase):
    """AccountService/PlanProgressService reuse JSONFileStorageBackend,
    which A's own tests/test_storage_corruption.py already proves is
    resilient at the backend level. These are thin integration checks
    confirming that resilience is actually inherited end-to-end through
    each *service's* own read/write methods, not re-testing the backend."""

    def test_account_service_survives_corrupted_accounts_file(self):
        path = Path(tempfile.mkdtemp()) / "accounts.json"
        path.write_text("not valid json {{{")

        service = AccountService(backend=JSONFileStorageBackend(path))
        self.assertIsNone(service.get_by_email("nobody@example.com"))

        # Must still be able to write after recovering from a corrupted read.
        account = service.register(email="new@example.com", password="hunter22", display_name="New")
        self.assertIsNotNone(account.user_id)

    def test_plan_progress_service_survives_corrupted_file(self):
        path = Path(tempfile.mkdtemp()) / "plan_progress.json"
        path.write_text("not valid json {{{")

        service = PlanProgressService(user_id="u1", backend=JSONFileStorageBackend(path))
        self.assertEqual(service.get_completed(), set())

        service.set_completed(day_number=1, task_index=0, completed=True)
        self.assertIn((1, 0), service.get_completed())


if __name__ == "__main__":
    unittest.main()
