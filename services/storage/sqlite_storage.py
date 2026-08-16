"""A SQLite StorageBackend, behind the interface the app already has.

WHAT IT FIXES
-------------
The JSON backend is careful and correct and it has a ceiling that no
amount of care raises: every write rewrites the whole file, and every
read-modify-write serialises behind one OS-level advisory lock. That is
fine for one process serving one person. It means that two workers is
not a supported deployment, and that the cost of writing one journal
page grows with the total size of every account's journal.

This backend is the same interface with a real transaction underneath.
`transaction()` opens `BEGIN IMMEDIATE`, so concurrent writers queue in
the database instead of on a lock file, readers are never blocked (WAL),
and a commit writes the rows that changed rather than the file that
contains them.

WHY IT IS NOT THE DEFAULT
-------------------------
Because the JSON files are what exists, and switching the default would
silently strand every current install's data behind an empty database.
Selection is explicit:

    DWAI_STORAGE_BACKEND=sqlite            # opt in
    DWAI_SQLITE_PATH=/path/to/dwai.db      # optional

and `python3 -m services.storage.import_json` copies the JSON stores in.
The default stays `json` until somebody chooses otherwise.

THE SHAPE
---------
`records(id, store, data, user_id, written_at_utc)` - see
services/storage/migrations.py for why the payload stays JSON rather
than becoming typed columns. One backend instance addresses one `store`,
which is exactly the role one JSON file used to play, so every service
constructs it the same way it constructed the old one.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from core import paths
from services.storage.base import StorageBackend
from services.storage.migrations import SCHEMA_VERSION, migrate

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_PATH = paths.storage_file("dwai.db")

# How long a writer waits for another writer before giving up. The JSON
# backend's lock timeout exists for the same reason and this mirrors it:
# a request that waits forever reaches the user as a gateway timeout that
# blames the network.
BUSY_TIMEOUT_SECONDS = 10.0

# Connections are per-thread. sqlite3 objects are not safe to share
# across threads, and FastAPI serves on a thread pool.
_local = threading.local()
_migrated: set[str] = set()
_migrate_guard = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        str(path),
        timeout=BUSY_TIMEOUT_SECONDS,
        isolation_level=None,  # explicit BEGIN, so transaction() means it
    )
    connection.row_factory = sqlite3.Row
    # WAL: readers do not block the writer and the writer does not block
    # readers, which is the whole reason to be here rather than in a file
    # behind an exclusive lock.
    connection.execute("PRAGMA journal_mode=WAL")
    # NORMAL rather than FULL: with WAL this is durable across process
    # crashes (only a machine-level power loss can lose the last commit),
    # and FULL costs an fsync per write for a wellness journal.
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(f"PRAGMA busy_timeout={int(BUSY_TIMEOUT_SECONDS * 1000)}")
    return connection


def connection_for(path: Path) -> sqlite3.Connection:
    """This thread's connection to `path`, migrated on first use."""
    key = str(Path(path).resolve())
    cache = getattr(_local, "connections", None)
    if cache is None:
        cache = _local.connections = {}
    connection = cache.get(key)
    if connection is None:
        connection = cache[key] = _connect(Path(path))

    if key not in _migrated:
        # Guarded so two threads reaching a fresh database at once do not
        # both try to create the same tables. The set is checked again
        # inside the lock for the usual reason.
        with _migrate_guard:
            if key not in _migrated:
                migrate(connection)
                _migrated.add(key)
    return connection


def close_all() -> None:
    """Drop this thread's connections. For tests that delete the file."""
    cache = getattr(_local, "connections", None) or {}
    for connection in cache.values():
        try:
            connection.close()
        except Exception:  # noqa: BLE001
            pass
    cache.clear()
    with _migrate_guard:
        _migrated.clear()


class SQLiteStorageBackend(StorageBackend):
    """One logical store - the role one JSON file used to play."""

    def __init__(self, store: str, path: Optional[Path] = None) -> None:
        self.store = str(store)
        self.path = Path(path) if path is not None else _configured_path()

    # ------------------------------------------------------------- read
    def read_all(self) -> list[dict[str, Any]]:
        try:
            rows = connection_for(self.path).execute(
                "SELECT data FROM records WHERE store = ? ORDER BY id", (self.store,),
            ).fetchall()
        except sqlite3.Error:
            # Same contract as the JSON backend: an unreadable store is
            # an empty store, not an exception thrown at whoever asked.
            logger.exception("Could not read store %r from %s", self.store, self.path)
            return []

        records: list[dict[str, Any]] = []
        for row in rows:
            try:
                value = json.loads(row["data"])
            except (TypeError, ValueError):
                logger.warning("Skipping a malformed row in store %r", self.store)
                continue
            if isinstance(value, dict):
                records.append(value)
        return records

    # ------------------------------------------------------------ write
    def write_all(self, records: list[dict[str, Any]]) -> None:
        """Replace this store's rows.

        Replacement rather than a diff because that is what the interface
        promises and what every caller is written against: they read the
        whole list, change it in Python, and hand it back. Scoped to one
        store, so a rewrite of the journal never touches accounts.
        """
        connection = connection_for(self.path)
        stamp = _now()
        payload = [
            (self.store, json.dumps(record, ensure_ascii=False, default=str), stamp)
            for record in records
            if isinstance(record, dict)
        ]
        managed = _in_transaction(connection)
        if not managed:
            connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM records WHERE store = ?", (self.store,))
            if payload:
                connection.executemany(
                    "INSERT INTO records (store, data, written_at_utc) VALUES (?, ?, ?)",
                    payload,
                )
        except Exception:
            if not managed:
                connection.execute("ROLLBACK")
            raise
        if not managed:
            connection.execute("COMMIT")

    # ------------------------------------------------------ transaction
    @contextmanager
    def transaction(self) -> Iterator[list[dict[str, Any]]]:
        """A real database transaction around the read-modify-write.

        BEGIN IMMEDIATE takes the write lock up front rather than on the
        first write. Deferred would let two transactions both read, both
        decide what to write, and then have one fail to upgrade - which
        is precisely the lost-update race the JSON backend's file lock
        exists to prevent, reintroduced.
        """
        connection = connection_for(self.path)
        if _in_transaction(connection):
            # The JSON backend raises here too, for the same reason: a
            # nested transaction cannot be granted, and the alternative
            # is a deadlock that reaches the user as a request which
            # never answers.
            raise RuntimeError(
                f"transaction() on store {self.store!r} is already open on this "
                f"thread. Collect the changes and commit them in the outer block."
            )
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.read_all()
        except Exception:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")

    def commit(self, records: list[dict[str, Any]]) -> None:
        """Alias for `write_all`, used inside a `transaction()` block."""
        self.write_all(records)

    # ---------------------------------------------------------- helpers
    def schema_version(self) -> int:
        row = connection_for(self.path).execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()
        return int((row[0] if row else 0) or 0)

    def stores(self) -> list[str]:
        rows = connection_for(self.path).execute(
            "SELECT DISTINCT store FROM records ORDER BY store"
        ).fetchall()
        return [row["store"] for row in rows]


def _in_transaction(connection: sqlite3.Connection) -> bool:
    return bool(connection.in_transaction)


# ------------------------------------------------------------ selection

def _configured_path() -> Path:
    override = (os.environ.get("DWAI_SQLITE_PATH") or "").strip()
    return Path(override) if override else DEFAULT_SQLITE_PATH


def selected_backend() -> str:
    """"json" (default) or "sqlite", from DWAI_STORAGE_BACKEND."""
    choice = (os.environ.get("DWAI_STORAGE_BACKEND") or "json").strip().lower()
    return "sqlite" if choice == "sqlite" else "json"


def backend_for(json_path: Path) -> StorageBackend:
    """The configured backend for a store that used to be `json_path`.

    Every service still names its store the way it always did - by the
    path of the JSON file it used to write. This is the single place
    that decides what that name actually resolves to, so switching
    engines is one environment variable rather than fifty-nine edits.
    """
    from services.storage.json_file_storage import JSONFileStorageBackend

    if selected_backend() == "sqlite":
        return SQLiteStorageBackend(store=Path(json_path).name)
    return JSONFileStorageBackend(Path(json_path))


def describe() -> dict[str, Any]:
    """What is actually in use, for a health endpoint or a startup line."""
    if selected_backend() != "sqlite":
        return {"backend": "json", "path": str(paths.STORAGE_DIR)}
    path = _configured_path()
    return {
        "backend": "sqlite",
        "path": str(path),
        "schema_version": SCHEMA_VERSION,
        "exists": path.exists(),
    }
