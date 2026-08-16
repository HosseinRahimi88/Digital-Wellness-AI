"""
Personal store
---------------
Two small per-user things that had nowhere to live: how long this
account has actually spent in the app, and an optional birth date.

Time in the app is MEASURED, not estimated. The browser adds up the
seconds a page of this app is actually visible and focused, and sends
that total periodically; this service adds it to the day's tally. Two
rules keep the number honest rather than flattering:

  * a heartbeat is capped (MAX_HEARTBEAT_SECONDS), so a tab that was
    left open over a weekend cannot post two days of "use" at once;
  * a day is capped (MAX_DAY_SECONDS), because a number above that is
    not a person using an app, it is a clock or a bug.

The birth date is optional and asked for once. Nothing requires it -
without it the facts panel talks about the user's own history instead.
It is never sent to any model; it exists so "you have been alive
11,318 days, and you have logged 23 of them here" can be said, which is
a truer sentence about a wellness app than any score.

Storage: the same pattern as every other store here - a flat JSON
record list through JSONFileStorageBackend, one instance per user,
every read-modify-write inside a real lock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from core import paths
from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for

DEFAULT_STORAGE_PATH = paths.storage_file("personal.json")

# One heartbeat may not claim more than five minutes. The client sends
# one a minute, so anything larger is a tab that was asleep.
MAX_HEARTBEAT_SECONDS = 300
# Sixteen hours in one day is already implausible; past that it is a
# clock change or a loop, and the tally would be a lie.
MAX_DAY_SECONDS = 16 * 3600

# Nobody using this app was born before this, and nobody is born after
# today. Both ends are refused rather than clamped.
EARLIEST_BIRTH_YEAR = 1900


class PersonalValidationError(ValueError):
    """A birth date the calendar does not have, or a nonsense duration."""


@dataclass(slots=True)
class UsageSummary:
    total_seconds: int = 0
    today_seconds: int = 0
    days_present: int = 0
    best_day_seconds: int = 0
    best_day: str = ""
    first_seen: str = ""
    by_day: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_seconds": self.total_seconds,
            "total_minutes": round(self.total_seconds / 60.0, 1),
            "today_seconds": self.today_seconds,
            "today_minutes": round(self.today_seconds / 60.0, 1),
            "days_present": self.days_present,
            "best_day_seconds": self.best_day_seconds,
            "best_day_minutes": round(self.best_day_seconds / 60.0, 1),
            "best_day": self.best_day,
            "first_seen": self.first_seen,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalise_birth_date(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        day = value if isinstance(value, date_cls) else date_cls.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise PersonalValidationError("That is not a date.") from None
    if day > date_cls.today():
        raise PersonalValidationError("A birth date cannot be in the future.")
    if day.year < EARLIEST_BIRTH_YEAR:
        raise PersonalValidationError("That date is too far back to be a birth date.")
    return day.isoformat()


class PersonalService:

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or backend_for(DEFAULT_STORAGE_PATH)

    def _record(self) -> Optional[dict]:
        for row in self._backend.read_all():
            if row.get("user_id") == self.user_id:
                return row
        return None

    # ---------------------------------------------------------- usage

    def add_seconds(self, seconds: Any, day: Optional[Any] = None) -> UsageSummary:
        """Add measured seconds to a day's tally, capped at both ends."""
        try:
            amount = int(float(seconds))
        except (TypeError, ValueError):
            raise PersonalValidationError("Seconds must be a number.") from None
        if amount <= 0:
            return self.usage()
        amount = min(amount, MAX_HEARTBEAT_SECONDS)
        when = (day or date_cls.today())
        key = when.isoformat() if isinstance(when, date_cls) else str(when)

        with self._backend.transaction() as records:
            rows = list(records)
            row = next((r for r in rows if r.get("user_id") == self.user_id), None)
            if row is None:
                row = {"user_id": self.user_id, "seconds_by_day": {},
                       "birth_date": None, "created_at_utc": _now()}
                rows.append(row)
            tally = dict(row.get("seconds_by_day") or {})
            tally[key] = min(MAX_DAY_SECONDS, int(tally.get(key, 0)) + amount)
            row["seconds_by_day"] = tally
            row["updated_at_utc"] = _now()
            self._backend.commit(rows)
        return self.usage()

    def usage(self) -> UsageSummary:
        row = self._record()
        tally = {k: int(v) for k, v in (row or {}).get("seconds_by_day", {}).items() if v}
        if not tally:
            return UsageSummary()
        today = date_cls.today().isoformat()
        best_day = max(tally, key=lambda k: tally[k])
        return UsageSummary(
            total_seconds=sum(tally.values()),
            today_seconds=tally.get(today, 0),
            days_present=len(tally),
            best_day_seconds=tally[best_day],
            best_day=best_day,
            first_seen=min(tally),
            by_day=tally,
        )

    # ----------------------------------------------------- birth date

    def birth_date(self) -> Optional[str]:
        row = self._record()
        return (row or {}).get("birth_date") or None

    def set_birth_date(self, value: Any) -> Optional[str]:
        wanted = normalise_birth_date(value)
        with self._backend.transaction() as records:
            rows = list(records)
            row = next((r for r in rows if r.get("user_id") == self.user_id), None)
            if row is None:
                row = {"user_id": self.user_id, "seconds_by_day": {},
                       "created_at_utc": _now()}
                rows.append(row)
            row["birth_date"] = wanted
            row["updated_at_utc"] = _now()
            self._backend.commit(rows)
        return wanted

    # --------------------------------------------------------- delete

    def delete_all(self) -> int:
        return self.delete_users([self.user_id])

    def delete_users(self, user_ids: Iterable[str]) -> int:
        wanted = {u for u in user_ids if u}
        if not wanted:
            return 0
        removed = 0
        with self._backend.transaction() as records:
            remaining = []
            for row in records:
                if row.get("user_id") in wanted:
                    removed += 1
                    continue
                remaining.append(row)
            if removed:
                self._backend.commit(remaining)
        return removed
