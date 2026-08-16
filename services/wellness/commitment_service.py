"""
Commitment Service
--------------------
Persists a user's commitment to act on a recommendation category
("Sleep", "Screen Time", ...) - the stable identity
config/recommendation_registry.py templates already group by (see
RecommendationService.generate()'s `used_categories` dedup), reused
here instead of inventing a separate per-recommendation id.

Same storage pattern as services/wellness/plan_progress_service.py /
services/identity/letter_service.py: a flat JSON record list via
JSONFileStorageBackend, one instance per user_id.

This module only tracks *intent* (I'm committing to work on Sleep,
starting today). Whether it actually helped is a separate, later
question - see services/wellness/recommendation_effectiveness_service.py, which
reads these commitments plus real HistoryService entries to measure
real outcomes. Keeping "did I commit" and "did it work" as two
services mirrors the existing achievement_service/gamification_service
split: each answers one question.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from core import paths
from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for

DEFAULT_STORAGE_PATH = paths.storage_file("commitments.json")

STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_ABANDONED = "abandoned"


@dataclass(slots=True)
class Commitment:
    commitment_id: str
    user_id: str
    category: str
    committed_on: str  # ISO date
    status: str
    resolved_on: Optional[str] = None


class CommitmentService:
    """Tracks which recommendation categories a user has committed to."""

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or backend_for(DEFAULT_STORAGE_PATH)

    @staticmethod
    def _to_commitment(record: dict) -> Commitment:
        return Commitment(
            commitment_id=record["commitment_id"],
            user_id=record["user_id"],
            category=record["category"],
            committed_on=record["committed_on"],
            status=record.get("status", STATUS_ACTIVE),
            resolved_on=record.get("resolved_on"),
        )

    def get_all(self) -> list[Commitment]:
        """Every commitment this user has ever made, oldest first."""
        records = [r for r in self._backend.read_all() if r.get("user_id") == self.user_id]
        records.sort(key=lambda r: r.get("committed_on", ""))
        return [self._to_commitment(r) for r in records]

    def get_active(self) -> list[Commitment]:
        return [c for c in self.get_all() if c.status == STATUS_ACTIVE]

    def is_active(self, category: str) -> bool:
        return any(c.category == category for c in self.get_active())

    def commit(self, category: str, on_date: Optional[date] = None) -> Commitment:
        """
        Start (or restart) a commitment to `category`. If this user
        already has an active commitment to the same category, it's
        left as-is (re-committing to something you're already
        committed to is a no-op, not a duplicate record).
        """
        existing_active = next((c for c in self.get_active() if c.category == category), None)
        if existing_active is not None:
            return existing_active

        entry_date = on_date or datetime.now().date()
        record = {
            "commitment_id": uuid4().hex,
            "user_id": self.user_id,
            "category": category,
            "committed_on": entry_date.isoformat(),
            "status": STATUS_ACTIVE,
            "resolved_on": None,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with self._backend.transaction() as records:
            records.append(record)
            self._backend.commit(records)
        return self._to_commitment(record)

    def resolve(self, commitment_id: str, status: str, on_date: Optional[date] = None) -> None:
        """Mark a commitment completed or abandoned."""
        if status not in (STATUS_COMPLETED, STATUS_ABANDONED):
            raise ValueError(f"Invalid resolution status: {status!r}")

        resolved_date = (on_date or datetime.now().date()).isoformat()
        with self._backend.transaction() as records:
            for record in records:
                if record.get("user_id") == self.user_id and record.get("commitment_id") == commitment_id:
                    record["status"] = status
                    record["resolved_on"] = resolved_date
            self._backend.commit(records)
