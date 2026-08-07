"""
JSON File Storage Backend
--------------------------
Concrete `StorageBackend` that persists records as a single JSON array
on disk, the same on-disk shape the project already used
(`storage/prediction_history.json`) - so no data migration is needed.

What changed vs. the original ad-hoc file IO in HistoryService
-----------------------------------------------------------------
The old code did a plain load -> mutate-in-Python -> atomic-rename-write
with *no locking at all* between the load and the write. Under
concurrent users that is a classic read-modify-write race: two requests
both load the same snapshot, both compute an "updated" list from it, and
whichever writes last silently discards the other's change - real data
loss, not just a theoretical risk, since Streamlit can happily serve
multiple sessions/threads out of one process.

This backend fixes that with a real OS-level advisory lock held around
the entire read-modify-write transaction, so concurrent writers are
serialized instead of racing. The lock is taken on a dedicated `.lock`
sidecar file (not the data file itself) so a writer can safely `open()`
and rewrite the data file via the write-to-temp + atomic-rename pattern
while still holding the lock.

Cross-platform locking
-----------------------
`fcntl.flock` (POSIX: Linux/macOS) and `msvcrt.locking` (Windows) are
both used here, selected at import time based on whichever is actually
available - there is no third "process-local only" fallback path for
either platform anymore:

  * POSIX: `fcntl.flock(fd, LOCK_EX)` on the lock file, blocking until
    acquired. This is a kernel-level lock tied to the *open file
    description*, so it correctly serializes both separate processes
    and separate threads in the same process (each `open()` call gets
    its own file description).
  * Windows: `msvcrt.locking()` on a 1-byte region of the lock file.
    Unlike `fcntl.flock`, `msvcrt.locking` has no "block forever"
    mode, so acquisition is implemented as a short poll/retry loop
    around the non-blocking `LK_NBLCK` mode. This still gives the same
    guarantee - only one process/thread can hold the byte range at a
    time - just implemented with a retry loop instead of a single
    blocking syscall.

A `threading.Lock` keyed by the resolved lock-file path is layered on
top as a cheap first line of defense for same-process contention (a
fresh `JSONFileStorageBackend` instance is often constructed per
call/service, so an *instance*-local lock would not by itself protect
concurrent instances pointed at the same file within one process). The
OS-level lock is still the mechanism that actually guarantees
correctness, including across separate processes; the thread lock is
just there to avoid unnecessary contention on it.

If neither `fcntl` nor `msvcrt` is importable (an unsupported/exotic
platform), that is logged loudly and the code falls back to the
in-process `threading.Lock` only - callers are told explicitly that
cross-process safety is not guaranteed in that case.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from services.storage.base import StorageBackend

logger = logging.getLogger(__name__)

try:
    import fcntl
    _LOCK_IMPL = "fcntl"
except ImportError:  # pragma: no cover - Windows
    try:
        import msvcrt
        _LOCK_IMPL = "msvcrt"
    except ImportError:  # pragma: no cover - neither primitive available
        _LOCK_IMPL = None


class JSONFileStorageBackend(StorageBackend):
    """Stores records as a JSON array at `path`, guarded by a file lock
    that works the same way on POSIX and Windows."""

    # Shared across all instances pointed at the same lock file, so a
    # freshly-constructed backend (the common pattern - see
    # HistoryService) still gets same-process serialization even before
    # the OS-level lock is touched.
    _thread_locks: dict[str, threading.Lock] = {}
    _thread_locks_guard = threading.Lock()

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    @classmethod
    def _thread_lock_for(cls, lock_path: Path) -> threading.Lock:
        key = str(lock_path.resolve())
        with cls._thread_locks_guard:
            lock = cls._thread_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                cls._thread_locks[key] = lock
            return lock

    # ======================================================
    # Low-level IO
    # ======================================================

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.warning("Storage file %s is malformed; ignoring.", self.path)
                return []
            return data
        except (json.JSONDecodeError, OSError):
            logger.exception("Could not read storage file %s.", self.path)
            return []

    def write_all(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)
        tmp_path.replace(self.path)  # atomic on both POSIX and Windows

    # ======================================================
    # Cross-platform OS-level file lock
    # ======================================================

    @staticmethod
    @contextmanager
    def _os_file_lock(lock_path: Path) -> Iterator[None]:
        """Exclusive advisory lock on `lock_path`, held for the duration
        of the `with` block. Implementation is chosen per-platform at
        import time (`fcntl` on POSIX, `msvcrt` on Windows)."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        if _LOCK_IMPL == "fcntl":
            lock_file = open(lock_path, "a+")
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()

        elif _LOCK_IMPL == "msvcrt":
            # msvcrt.locking() locks a byte range that must already
            # exist in the file, and has no unlimited blocking mode -
            # so make sure the byte is there, then poll LK_NBLCK.
            lock_file = open(lock_path, "a+b")
            try:
                lock_file.seek(0, 2)  # end of file
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                while True:
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.02)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
            finally:
                lock_file.close()

        else:  # pragma: no cover - neither locking primitive available
            logger.warning(
                "No OS-level file lock primitive (fcntl/msvcrt) available "
                "on this platform; falling back to in-process locking "
                "only. Concurrent *separate processes* writing to %s are "
                "not protected here.",
                lock_path,
            )
            yield

    # ======================================================
    # Locked transaction
    # ======================================================

    @contextmanager
    def transaction(self) -> Iterator[list[dict[str, Any]]]:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        thread_lock = self._thread_lock_for(self.lock_path)
        with thread_lock, self._os_file_lock(self.lock_path):
            yield self.read_all()

    def commit(self, records: list[dict[str, Any]]) -> None:
        """Alias for `write_all`, used inside a `transaction()` block."""
        self.write_all(records)
