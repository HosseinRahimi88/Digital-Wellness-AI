"""
Tests: the storage lock always answers.

A user reported sign-in failing with a gateway timeout. The app never
produces a 504 itself, and login over real HTTP is a tenth of a second -
but the storage layer had two unbounded waits, and an unbounded wait is
precisely the shape that reaches a browser as 504: the request is never
refused and never answered, so the only thing that eventually speaks is
whatever sits in front of the app.

The two waits were:

  1. `fcntl.flock(LOCK_EX)` / `while True: msvcrt.locking(LK_NBLCK)` -
     blocked forever if any other holder had the lock. On Windows that
     is easy to arrange by accident, because its file locks are
     mandatory rather than advisory: a force-killed previous run, a
     second copy of the app, an editor or a virus scanner with the
     `.lock` sidecar open, and the byte range is simply never released.

  2. `threading.Lock` with no timeout - a nested transaction() on one
     thread deadlocks against itself immediately and permanently.

Neither is reachable from a normal request, which is why the suite was
green while a user was locked out. These tests make the failure mode
itself the thing under test: hold the lock, and assert the app gives up
and says so rather than waiting.

Run: python3 -m unittest tests.test_storage_lock_timeout -v
"""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

import tests._test_support  # noqa: F401 - sys.path bootstrap

from services.storage import json_file_storage as jfs
from services.storage.json_file_storage import (
    JSONFileStorageBackend,
    StorageLockTimeout,
)


class _TempBackend(unittest.TestCase):

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "records.json"
        self.path.write_text("[]", encoding="utf-8")
        self.backend = JSONFileStorageBackend(self.path)
        # Keep the real timeout out of the test runtime; the behaviour
        # under test is "bounded and raises", not the exact bound.
        self._original = jfs.LOCK_TIMEOUT_SECONDS
        jfs.LOCK_TIMEOUT_SECONDS = 0.4

    def tearDown(self):
        jfs.LOCK_TIMEOUT_SECONDS = self._original
        self._dir.cleanup()


class TestItGivesUpRatherThanHanging(_TempBackend):

    def test_a_lock_held_by_another_thread_times_out(self):
        """The reported symptom, reproduced: someone else holds the
        lock and will not let go. Before this, the second caller waited
        forever and the request never returned."""
        started = threading.Event()
        release = threading.Event()

        def holder():
            with self.backend.transaction():
                started.set()
                release.wait(timeout=10)

        thread = threading.Thread(target=holder, daemon=True)
        thread.start()
        self.assertTrue(started.wait(timeout=5), "holder never acquired the lock")

        other = JSONFileStorageBackend(self.path)
        began = time.monotonic()
        try:
            with self.assertRaises(StorageLockTimeout):
                with other.transaction():
                    pass
        finally:
            release.set()
            thread.join(timeout=5)

        # The point is the bound, not just the exception: an unbounded
        # wait that happened to raise later would still be the bug.
        self.assertLess(time.monotonic() - began, 5.0)

    def test_the_message_names_the_file_and_what_to_do(self):
        """A user looking at a stuck sign-in screen needs somewhere to
        go. "Storage is busy" is not somewhere to go."""
        started, release = threading.Event(), threading.Event()

        def holder():
            with self.backend.transaction():
                started.set()
                release.wait(timeout=10)

        thread = threading.Thread(target=holder, daemon=True)
        thread.start()
        self.assertTrue(started.wait(timeout=5))
        try:
            with self.assertRaises(StorageLockTimeout) as caught:
                with JSONFileStorageBackend(self.path).transaction():
                    pass
        finally:
            release.set()
            thread.join(timeout=5)

        message = str(caught.exception)
        self.assertIn(".lock", message)
        self.assertIn("running", message.lower())

    def test_a_nested_transaction_is_refused_immediately(self):
        """Re-entry deadlocks a threading.Lock permanently. Refusing it
        by name costs nothing and turns a hung server into a stack
        trace pointing at the offending call."""
        began = time.monotonic()
        with self.assertRaises(StorageLockTimeout) as caught:
            with self.backend.transaction():
                with JSONFileStorageBackend(self.path).transaction():
                    pass
        # Refused on sight, not after the timeout elapses.
        self.assertLess(time.monotonic() - began, 0.3)
        self.assertIn("Nested", str(caught.exception))


class TestItStillLocksProperly(_TempBackend):
    """The timeout must not have bought responsiveness by weakening the
    guarantee the lock exists for."""

    def test_concurrent_writers_do_not_lose_each_other_s_changes(self):
        jfs.LOCK_TIMEOUT_SECONDS = 10.0
        writers = 8
        per_writer = 5

        def write(worker: int):
            for i in range(per_writer):
                backend = JSONFileStorageBackend(self.path)
                with backend.transaction() as records:
                    records.append({"worker": worker, "i": i})
                    backend.commit(records)

        threads = [threading.Thread(target=write, args=(w,)) for w in range(writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        records = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(
            len(records), writers * per_writer,
            "a read-modify-write was lost - the lock is not serializing writers",
        )

    def test_two_different_files_do_not_block_each_other(self):
        """The re-entry guard is per lock file, not per thread. One
        request legitimately touches accounts and history in turn."""
        other_path = self.path.with_name("other.json")
        other_path.write_text("[]", encoding="utf-8")
        with self.backend.transaction():
            with JSONFileStorageBackend(other_path).transaction() as records:
                self.assertEqual(records, [])

    def test_the_lock_is_released_after_a_timeout(self):
        """A caller that timed out must not leave anything behind - it
        never held the lock, so it must not unlock it either."""
        started, release = threading.Event(), threading.Event()

        def holder():
            with self.backend.transaction():
                started.set()
                release.wait(timeout=10)

        thread = threading.Thread(target=holder, daemon=True)
        thread.start()
        self.assertTrue(started.wait(timeout=5))
        with self.assertRaises(StorageLockTimeout):
            with JSONFileStorageBackend(self.path).transaction():
                pass
        release.set()
        thread.join(timeout=5)

        # Once the real holder is done, the next caller gets straight in.
        jfs.LOCK_TIMEOUT_SECONDS = 5.0
        with JSONFileStorageBackend(self.path).transaction() as records:
            self.assertIsInstance(records, list)


class TestTheApiReportsItRatherThanHanging(unittest.TestCase):

    def test_a_storage_lock_timeout_becomes_a_503_with_the_reason(self):
        """The handler is the half that reaches the user. Without it the
        exception is an anonymous 500 whose message is deliberately
        withheld - true to the security rule, useless here."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.exceptions.handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/boom")
        def boom():
            raise StorageLockTimeout("Could not get the storage lock on x.lock")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/boom")
        self.assertEqual(response.status_code, 503)
        body = response.json()["error"]
        self.assertEqual(body["code"], "storage_locked")
        self.assertIn("storage lock", body["message"])


class TestTheClientStopsWaiting(unittest.TestCase):
    """The browser side of the same failure: a request that never comes
    back has to become a message, not a permanent spinner."""

    def setUp(self):
        self.source = (
            Path(__file__).resolve().parents[1]
            / "frontend" / "assets" / "js" / "api.js"
        ).read_text(encoding="utf-8")

    def test_every_request_carries_an_abort_deadline(self):
        self.assertIn("AbortController", self.source)
        self.assertIn("signal: controller.signal", self.source)
        self.assertIn("REQUEST_TIMEOUT_MS", self.source)

    def test_the_timer_is_always_cleared(self):
        """Left running, it would abort a request that already
        succeeded."""
        self.assertIn("clearTimeout(timer)", self.source)

    def test_an_abort_is_reported_as_a_timeout_not_as_a_network_error(self):
        self.assertIn("AbortError", self.source)
        self.assertIn("did not answer within", self.source)


if __name__ == "__main__":
    unittest.main()
