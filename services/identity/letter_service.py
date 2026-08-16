"""
services/identity/letter_service.py
-----------------------------
Persists short "letters to your future self" that a user writes today
and that unlock on a future date they choose. Pure UX feature - no ML,
no prediction logic. Follows the exact same storage pattern as
services/wellness/plan_progress_service.py (a JSONFileStorageBackend-backed
service, one record per event, filtered by user_id) rather than
introducing a new persistence mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from core import paths
from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for

DEFAULT_STORAGE_PATH = paths.storage_file("future_letters.json")

# Letters can't be locked further out than this, to keep the feature
# from being (ab)used as a general-purpose long-term note store.
MAX_UNLOCK_DAYS_AHEAD = 365


@dataclass(slots=True)
class Letter:
    letter_id: str
    user_id: str
    content: str
    written_on: str
    unlock_date: str
    context_score: Optional[float]

    @property
    def is_unlocked(self) -> bool:
        try:
            return date.fromisoformat(self.unlock_date) <= datetime.now().date()
        except ValueError:
            return True


class LetterService:
    """Tracks one user's future letters."""

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or backend_for(DEFAULT_STORAGE_PATH)

    def write_letter(
        self,
        content: str,
        unlock_date: date,
        context_score: Optional[float] = None,
    ) -> Letter:
        """Save a new letter. Returns the stored Letter."""
        content = (content or "").strip()
        if not content:
            raise ValueError("Letter content cannot be empty.")

        today = datetime.now().date()
        max_date = today + timedelta(days=MAX_UNLOCK_DAYS_AHEAD)
        if unlock_date > max_date:
            unlock_date = max_date
        if unlock_date < today:
            unlock_date = today

        record = {
            "letter_id": uuid4().hex,
            "user_id": self.user_id,
            "content": content,
            "written_on": today.isoformat(),
            "unlock_date": unlock_date.isoformat(),
            "context_score": context_score,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        with self._backend.transaction() as records:
            records.append(record)
            self._backend.commit(records)

        return self._record_to_letter(record)

    def get_letters(self) -> list[Letter]:
        """All of this user's letters (locked and unlocked), oldest first."""
        records = [
            r for r in self._backend.read_all()
            if r.get("user_id") == self.user_id
        ]
        records.sort(key=lambda r: r.get("written_on", ""))
        return [self._record_to_letter(r) for r in records]

    def get_unlocked_letters(self) -> list[Letter]:
        return [l for l in self.get_letters() if l.is_unlocked]

    def get_locked_letters(self) -> list[Letter]:
        return [l for l in self.get_letters() if not l.is_unlocked]

    @staticmethod
    def _record_to_letter(record: dict) -> Letter:
        known = {"letter_id", "user_id", "content", "written_on", "unlock_date", "context_score"}
        filtered = {k: v for k, v in record.items() if k in known}
        return Letter(**filtered)
