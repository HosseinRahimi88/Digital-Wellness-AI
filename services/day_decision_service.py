"""
Day Decision Service
--------------------
Records what a user chose to do about a day that fell outside their
week's score band.

The week's plan is aimed at a range, not at a single number - see
services/plan_lock_service.py's `week_band`. From the second logged day
of a week onward, a day can land outside that range, and there are
genuinely two different things that can mean:

  * it was an unusual day - travel, illness, a deadline - and treating
    it as a signal would drag the rest of the week's plan toward a life
    the user is not living. They mark it an EXCEPTION.

  * it was a real change, and the plan should follow it. They let it
    COUNT.

Neither is the safe default, which is exactly why this is asked rather
than assumed. An exception is not the same as deleting the day:

  * it stays in history and stays visible on the dashboard, because a
    week with three "unusual" days is itself the most useful thing the
    dashboard can tell someone;
  * it still moves the band, just less - EXCEPTION_WEIGHT of a normal
    day. Dropping it to zero would let a user quietly curate their own
    trend into a straight line, and counting it in full is precisely
    what they said it should not do.

A counted day rewrites the REST of the week's plan (from that day on)
against the new band. Days already lived through keep their tasks, and
therefore keep their checkmarks - see
PlanProgressService.clear_days_from.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls
from datetime import datetime, timezone
from typing import Optional

from services.plan_progress_service import current_week_key
from services.storage.base import StorageBackend
from services.storage.json_file_storage import JSONFileStorageBackend

DEFAULT_STORAGE_PATH = "storage/day_decisions.json"

EXCEPTION = "exception"
COUNTED = "counted"
VALID_DECISIONS = (EXCEPTION, COUNTED)

# How much of a normal day's weight an exception day keeps when the
# week's band is computed. Not zero: a day the user calls unusual is
# still a day that happened, and letting it vanish entirely would make
# the band a record of the days someone felt good about rather than of
# their week. Not one either - that is what "count it" means.
EXCEPTION_WEIGHT = 0.25


@dataclass(slots=True)
class DayDecision:
    """One answer to "that day was outside your range - what was it?"."""

    date: str
    week_key: str
    decision: str
    score: Optional[float] = None
    band_low: Optional[float] = None
    band_high: Optional[float] = None
    decided_at_utc: str = ""

    @property
    def is_exception(self) -> bool:
        return self.decision == EXCEPTION


class DayDecisionService:
    """One decision per user per date."""

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or JSONFileStorageBackend(DEFAULT_STORAGE_PATH)

    # ---------------------------------------------------------------- read
    def get(self, day: Optional[str] = None) -> Optional[DayDecision]:
        day = day or date_cls.today().isoformat()
        for record in self._backend.read_all():
            if record.get("user_id") == self.user_id and record.get("date") == day:
                return self._to_decision(record)
        return None

    def for_week(self, week_key: Optional[str] = None) -> list[DayDecision]:
        """Every decision this user made inside one ISO week, oldest first."""
        week_key = week_key or current_week_key()
        out = [
            self._to_decision(r) for r in self._backend.read_all()
            if r.get("user_id") == self.user_id and r.get("week_key") == week_key
        ]
        return sorted([d for d in out if d is not None], key=lambda d: d.date)

    def exception_dates(self, week_key: Optional[str] = None) -> set[str]:
        return {d.date for d in self.for_week(week_key) if d.is_exception}

    @staticmethod
    def _to_decision(record: dict) -> Optional[DayDecision]:
        decision = record.get("decision")
        if decision not in VALID_DECISIONS:
            # An unrecognised value is treated as absent rather than
            # guessed at: guessing here would silently apply one of two
            # opposite behaviours to a real user's week.
            return None
        return DayDecision(
            date=record.get("date", ""),
            week_key=record.get("week_key", ""),
            decision=decision,
            score=record.get("score"),
            band_low=record.get("band_low"),
            band_high=record.get("band_high"),
            decided_at_utc=record.get("decided_at_utc", ""),
        )

    # --------------------------------------------------------------- write
    def save(
        self,
        day: str,
        decision: str,
        week_key: Optional[str] = None,
        score: Optional[float] = None,
        band_low: Optional[float] = None,
        band_high: Optional[float] = None,
    ) -> DayDecision:
        if decision not in VALID_DECISIONS:
            raise ValueError(f"decision must be one of {VALID_DECISIONS}, got {decision!r}")
        week_key = week_key or current_week_key(date_cls.fromisoformat(day))
        record = {
            "user_id": self.user_id,
            "date": day,
            "week_key": week_key,
            "decision": decision,
            "score": score,
            "band_low": band_low,
            "band_high": band_high,
            "decided_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with self._backend.transaction() as records:
            remaining = [
                r for r in records
                if not (r.get("user_id") == self.user_id and r.get("date") == day)
            ]
            remaining.append(record)
            # The backend persists through commit(), not by mutating the
            # yielded list - same contract PlanProgressService uses.
            self._backend.commit(remaining)
        return self._to_decision(record)

    def clear(self, day: str) -> None:
        with self._backend.transaction() as records:
            self._backend.commit([
                r for r in records
                if not (r.get("user_id") == self.user_id and r.get("date") == day)
            ])
