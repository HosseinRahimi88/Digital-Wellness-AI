"""
Violation Service
-----------------
What happens when a day of the weekly plan goes by undone.

The rule the user asked for, in their words: a missed day costs a
badge; with no badges left it is recorded as a violation (تخلف); new
badges do not register while violations are outstanding, and each new
badge clears one. This file is the whole of that arithmetic.

Three deliberate constraints shape it:

  * Nothing here is retroactive. A day is only ever assessed once its
    date has PASSED, and only once - `assess_day` is idempotent per
    (week, day). A user who opens the app three times on Thursday must
    not lose three badges for the same Wednesday.

  * A day the user never had a plan for cannot be missed. The caller
    passes the days that actually existed; this service does not invent
    a seven-day obligation for someone who joined on Friday.

  * Badges are computed, not stored (services/social/badge_service.py derives
    them from the user's own check-ins every time). So a badge cannot
    be "deleted" - it is recorded here as REVOKED and filtered out at
    the boundary. That means a revoked badge stays revoked even though
    the history that earned it is still true, which is the point: it
    was spent.

On the wording: the app never tells a user they are bad at something -
see the badge service's own header. A violation is a count of days the
plan went undone, shown as a number with a way back (earn a badge,
clear one), never as a judgement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls
from datetime import datetime, timezone
from typing import Iterable, Optional

from services.wellness.plan_progress_service import current_week_key
from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for

DEFAULT_STORAGE_PATH = "storage/violations.json"

# Record kinds. Kept as strings in storage so a record written by an
# older build is still readable rather than silently reinterpreted.
MISS = "miss"          # a plan day that went undone; carries its penalty
ACKED = "acked"        # a badge that has been counted as earned
CONSUMED = "consumed"  # a badge that was spent clearing a violation

PENALTY_BADGE = "badge_revoked"
PENALTY_VIOLATION = "violation"


@dataclass(slots=True)
class ViolationState:
    """Everything a caller needs to render the situation honestly."""

    open_violations: int
    revoked_badge_ids: list[str]
    consumed_badge_ids: list[str]
    missed_days: int


class ViolationService:
    """One user's missed plan days, revoked badges and open violations."""

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or backend_for(DEFAULT_STORAGE_PATH)

    # ---------------------------------------------------------------- read
    def _mine(self) -> list[dict]:
        return [r for r in self._backend.read_all() if r.get("user_id") == self.user_id]

    def state(self) -> ViolationState:
        mine = self._mine()
        misses = [r for r in mine if r.get("kind") == MISS]
        return ViolationState(
            open_violations=sum(
                1 for r in misses
                if r.get("penalty") == PENALTY_VIOLATION and not r.get("resolved_at")
            ),
            revoked_badge_ids=[
                r["badge_id"] for r in misses
                if r.get("penalty") == PENALTY_BADGE and r.get("badge_id")
            ],
            consumed_badge_ids=[
                r["badge_id"] for r in mine
                if r.get("kind") == CONSUMED and r.get("badge_id")
            ],
            missed_days=len(misses),
        )

    def acked_badge_ids(self) -> set[str]:
        return {
            r["badge_id"] for r in self._mine()
            if r.get("kind") == ACKED and r.get("badge_id")
        }

    def _already_assessed(self, week_key: str, day_number: int) -> bool:
        return any(
            r.get("kind") == MISS
            and r.get("week_key") == week_key
            and r.get("day_number") == day_number
            for r in self._mine()
        )

    # --------------------------------------------------------------- write
    def assess_day(
        self,
        week_key: str,
        day_number: int,
        day_date: str,
        revocable_badge_ids: Iterable[str],
    ) -> Optional[str]:
        """Record one missed plan day. Returns the penalty applied, or
        None if this day had already been assessed.

        Idempotent per (week, day) on purpose: opening the app three
        times on Thursday must not cost three badges for the same
        Wednesday.
        """
        if self._already_assessed(week_key, day_number):
            return None

        state = self.state()
        spendable = [
            b for b in revocable_badge_ids
            if b and b not in set(state.revoked_badge_ids)
        ]
        if spendable:
            penalty, badge_id = PENALTY_BADGE, spendable[0]
        else:
            penalty, badge_id = PENALTY_VIOLATION, None

        self._append({
            "user_id": self.user_id,
            "kind": MISS,
            "week_key": week_key,
            "day_number": day_number,
            "date": day_date,
            "penalty": penalty,
            "badge_id": badge_id,
            "created_at_utc": _now(),
        })
        return penalty

    def absorb(self, newly_earned_badge_ids: Iterable[str]) -> list[str]:
        """Spend new badges clearing open violations, oldest first.

        Returns the ids that were spent - the caller withholds those
        from the user's badge list, because a badge that cleared a
        violation is exactly a badge that did not register. Badges left
        over after the violations are gone are acknowledged and count
        normally.
        """
        candidates = [b for b in newly_earned_badge_ids if b]
        if not candidates:
            return []

        with self._backend.transaction() as records:
            rows = list(records)
            open_misses = sorted(
                [
                    r for r in rows
                    if r.get("user_id") == self.user_id
                    and r.get("kind") == MISS
                    and r.get("penalty") == PENALTY_VIOLATION
                    and not r.get("resolved_at")
                ],
                key=lambda r: (r.get("created_at_utc") or "", r.get("day_number") or 0),
            )
            spent: list[str] = []
            for badge_id, miss in zip(candidates, open_misses):
                miss["resolved_at"] = _now()
                miss["resolved_by_badge"] = badge_id
                rows.append({
                    "user_id": self.user_id, "kind": CONSUMED,
                    "badge_id": badge_id, "created_at_utc": _now(),
                })
                spent.append(badge_id)

            for badge_id in candidates[len(spent):]:
                rows.append({
                    "user_id": self.user_id, "kind": ACKED,
                    "badge_id": badge_id, "created_at_utc": _now(),
                })
            self._backend.commit(rows)
        return spent

    def _append(self, record: dict) -> None:
        with self._backend.transaction() as records:
            rows = list(records)
            rows.append(record)
            # The backend persists through commit(), not by mutating the
            # yielded list - same contract PlanProgressService uses.
            self._backend.commit(rows)

    def clear_all(self) -> None:
        """Drop this user's entire violation record.

        Used when their history is deleted: a violation is a fact about
        days that no longer exist, and leaving it behind would penalise
        a fresh start.
        """
        with self._backend.transaction() as records:
            self._backend.commit([
                r for r in records if r.get("user_id") != self.user_id
            ])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def plan_day_date(generated_on: Optional[str], day_number: int) -> Optional[str]:
    """The calendar date plan day `day_number` falls on.

    Day 1 is the day the plan was generated, so day N is that date plus
    N-1. Returned as None when the plan has no recorded generation date
    (a snapshot from before that was stored) - the caller then assesses
    nothing, which is the right way to be unsure about whether somebody
    missed a day.
    """
    if not generated_on or day_number < 1:
        return None
    try:
        start = date_cls.fromisoformat(generated_on)
    except (TypeError, ValueError):
        return None
    from datetime import timedelta
    return (start + timedelta(days=day_number - 1)).isoformat()


def days_elapsed_unlock(generated_on: Optional[str], today: Optional[date_cls] = None) -> Optional[int]:
    """The highest plan day the CALENDAR allows, or None if unknowable.

    Day 1 falls on the day the plan was generated, so on that day only
    day 1 has arrived; the day after, day 2 has. A plan with no recorded
    generation date returns None, and the caller then applies no
    calendar gate at all - guessing a date here would lock days for
    somebody whose plan predates the field.
    """
    if not generated_on:
        return None
    try:
        start = date_cls.fromisoformat(generated_on)
    except (TypeError, ValueError):
        return None
    day = ((today or date_cls.today()) - start).days + 1
    # A plan generated in the future (clock skew, a hand-edited
    # snapshot) still opens its first day rather than none of them.
    return max(1, day)


def unlocked_through(
    completed: set[tuple[int, int]],
    tasks_per_day: dict[int, int],
    generated_on: Optional[str] = None,
    today: Optional[date_cls] = None,
) -> int:
    """The highest plan day the user is allowed to work on.

    Two gates, and a day must clear BOTH:

      * the sequence gate - day 1 is always open, and day N+1 opens once
        day N is fully done. This is what makes the week a sequence
        instead of a menu, and it is the only way "you missed a day"
        means anything;

      * the calendar gate - day N cannot open before the day it falls
        on. Ticking day 1's three tasks in one sitting used to open day
        2 immediately, so the whole week could be "completed" in ten
        minutes. That defeats the point: these are a day's habits, not
        a checklist, and a week done in one evening is a week nobody
        actually lived.

    The calendar gate is skipped when `generated_on` is missing, because
    the only honest thing to do about an unknown start date is not to
    lock anything on it.
    """
    unlocked = 1
    for day_number in sorted(tasks_per_day):
        total = tasks_per_day.get(day_number, 0)
        done = sum(1 for (d, _t) in completed if d == day_number)
        if total > 0 and done >= total:
            unlocked = day_number + 1
        else:
            break

    by_calendar = days_elapsed_unlock(generated_on, today)
    if by_calendar is not None:
        unlocked = min(unlocked, by_calendar)
    return unlocked
