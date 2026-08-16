"""
Storage Backend Interface
--------------------------
Abstraction boundary between "business logic that needs to persist a
list of records" (currently `HistoryService`) and "however those
records are actually stored on disk/in a database".

Today the only implementation is `JSONFileStorageBackend`
(services/storage/json_file_storage.py). The point of this interface is
that swapping to Postgres later means writing one new class -
`PostgresStorageBackend(StorageBackend)` - and changing the single
construction site where `HistoryService` picks its backend. No business
logic in `HistoryService` (upsert-by-key, weekly grouping, averaging,
etc.) has to change, because it never talks to files/SQL directly.

Concurrency contract
---------------------
`transaction()` is the only safe way to do a read-modify-write. It must
be used as a context manager:

    with backend.transaction() as records:
        records = [r for r in records if r["id"] != target_id]
        records.append(new_record)
        backend.commit(records)

Implementations must guarantee that the whole read-modify-write is
serialized against every other `transaction()` call - on the current
JSON backend this is a real OS-level file lock (safe across threads
*and* separate processes, e.g. multiple `streamlit run` workers); a
future SQL backend would implement this with a real DB transaction
instead.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Any


class StorageBackend(ABC):
    """Abstract persistence backend for a flat list of JSON-like records."""

    @abstractmethod
    def read_all(self) -> list[dict[str, Any]]:
        """Return every stored record. Safe to call without a lock."""
        raise NotImplementedError

    @abstractmethod
    def write_all(self, records: list[dict[str, Any]]) -> None:
        """
        Replace the entire record set atomically. Only call this from
        inside a `transaction()` block (or when you can otherwise
        guarantee no concurrent writer), otherwise concurrent writers can
        still race with each other even if each individual write is
        atomic.
        """
        raise NotImplementedError

    @abstractmethod
    def transaction(self) -> AbstractContextManager[list[dict[str, Any]]]:
        """
        Context manager that (a) acquires an exclusive lock, (b) yields
        the current records, and (c) releases the lock on exit. Callers
        must call `write_all()` (or the backend's `commit` alias) with
        the updated list *before* the `with` block ends.
        """
        raise NotImplementedError
