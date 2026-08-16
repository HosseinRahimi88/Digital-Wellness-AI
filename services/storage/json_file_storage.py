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

  * POSIX: `fcntl.flock(fd, LOCK_EX | LOCK_NB)` on the lock file, in a
    poll loop against a deadline. This is a kernel-level lock tied to
    the *open file description*, so it correctly serializes both
    separate processes and separate threads in the same process (each
    `open()` call gets its own file description).
  * Windows: `msvcrt.locking()` on a 1-byte region of the lock file,
    the same poll loop against the same deadline. `msvcrt.locking` has
    no "block forever" mode, so the non-blocking `LK_NBLCK` mode is
    the only option there anyway.

Why every wait here is bounded
-------------------------------
Both waits used to be unbounded - `LOCK_EX` with no `LOCK_NB`, and a
bare `while True` around `LK_NBLCK`. That turns *any* failure to get
the lock into a request that never returns: no error, no log line, no
response, just a socket held open until whatever sits in front of the
app gives up and reports a gateway timeout. It is the worst failure
shape available, because the one thing the user is told (504) points
at the network rather than at the lock.

The realistic causes are all platform-specific and none of them
resolve on their own:

  * Windows file locks are mandatory and per-handle. A crashed or
    force-killed previous run, a second copy of the app started by
    accident, an editor or antivirus holding the `.lock` sidecar open -
    any of these hold the byte range indefinitely.
  * A nested `transaction()` on one thread deadlocks against the
    non-reentrant `threading.Lock` instantly and permanently.

So both are bounded now and both raise `StorageLockTimeout`, which
surfaces as a real error the user can read within seconds instead of a
hang. Nested use is detected explicitly rather than left to deadlock,
because "you cannot nest a transaction" is a fact worth stating rather
than a symptom worth waiting out.

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


# Which lock keys the *current thread* is already inside. Thread-local
# because the answer differs per request handler, and a set rather than
# a flag because one thread can legitimately hold locks on two
# different storage files at once (accounts and history, say).
_held = threading.local()


class StorageLockTimeout(RuntimeError):
    """Raised when the storage lock could not be taken in time.

    A distinct type so the API layer can turn it into a 503 with a
    sentence the user can act on, rather than letting it surface as an
    anonymous 500 - or, as it did before, as no response at all."""


# How long a request will wait for the storage lock before giving up.
# Well above any legitimate write (every transaction here is a
# sub-millisecond read-modify-write of a small JSON file) and well
# below the point where a browser or proxy would call it a gateway
# timeout, so a stuck lock is reported by the app, in the app's own
# words, instead of by whatever is in front of it.
LOCK_TIMEOUT_SECONDS = 10.0
_LOCK_POLL_SECONDS = 0.02


def _timeout_message(lock_path: Path) -> str:
    """Says which file is stuck and what to do about it.

    The user hitting this is almost always looking at a sign-in screen
    that will not move, so the message has to name the actual file - a
    generic "storage is busy" leaves them with nothing to try."""
    return (
        f"Could not get the storage lock on {lock_path} within "
        f"{LOCK_TIMEOUT_SECONDS:.0f}s. Another copy of the app is most "
        f"likely still running and holding it. Stop every other instance, "
        f"then delete that .lock file if it remains."
    )


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

        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS

        if _LOCK_IMPL == "fcntl":
            lock_file = open(lock_path, "a+")
            acquired = False
            try:
                while True:
                    try:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise StorageLockTimeout(_timeout_message(lock_path)) from None
                        time.sleep(_LOCK_POLL_SECONDS)
                yield
            finally:
                # Only unlock what was actually locked: on the timeout
                # path this handle never held the lock, and releasing it
                # would drop whichever holder legitimately has it.
                if acquired:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()

        elif _LOCK_IMPL == "msvcrt":
            # msvcrt.locking() locks a byte range that must already
            # exist in the file, and has no unlimited blocking mode -
            # so make sure the byte is there, then poll LK_NBLCK.
            lock_file = open(lock_path, "a+b")
            acquired = False
            try:
                lock_file.seek(0, 2)  # end of file
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                while True:
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        acquired = True
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise StorageLockTimeout(_timeout_message(lock_path)) from None
                        time.sleep(_LOCK_POLL_SECONDS)
                try:
                    yield
                finally:
                    if acquired:
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

        key = str(self.lock_path.resolve())
        # Re-entry is a programming error, and `threading.Lock` punishes
        # it with a permanent deadlock on the calling thread - which
        # reaches the user as a request that never answers. Naming it is
        # strictly better than waiting ten seconds to say the same thing
        # less accurately.
        if key in getattr(_held, "keys", ()):
            raise StorageLockTimeout(
                f"transaction() on {self.path} is already open on this thread. "
                f"Nested transactions cannot be granted - collect the changes "
                f"and commit them in the outer block."
            )

        thread_lock = self._thread_lock_for(self.lock_path)
        if not thread_lock.acquire(timeout=LOCK_TIMEOUT_SECONDS):
            raise StorageLockTimeout(_timeout_message(self.lock_path))
        try:
            if not hasattr(_held, "keys"):
                _held.keys = set()
            _held.keys.add(key)
            with self._os_file_lock(self.lock_path):
                yield self.read_all()
        finally:
            _held.keys.discard(key)
            thread_lock.release()

    def commit(self, records: list[dict[str, Any]]) -> None:
        """Alias for `write_all`, used inside a `transaction()` block."""
        self.write_all(records)
