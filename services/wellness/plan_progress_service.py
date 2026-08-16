"""
services/wellness/plan_progress_service.py
-----------------------------------
Persists which tasks in a user's 7-day improvement plan
(services/wellness/improvement_plan_service.py) have been checked off, keyed by
(user_id, ISO week). This is what `legacy/streamlit_app/components/improvement_plan_card
.py`'s own docstring/caption flagged as missing: "Checkmarks are for
this browser session only."

UX motivation ported from the Parisa project's `render_weekly_plan_page()`,
which tracked a per-item `status` (planned/done/skipped/paused) against
its own Plan/PlanItem database tables. This project has no such tables
and, per this merge's scope, isn't getting a database - so instead of
a status enum per plan item, this is the simplest persistent
equivalent for A's actual plan shape (a fixed list of tasks per day):
a completed/not-completed flag per (day_number, task_index), stored via
the same JSONFileStorageBackend used by services/identity/account_service.py.

Uses A's own ISO-week convention (see HistoryService._week_key) so a
plan's progress naturally resets when a new week's plan is generated,
without needing explicit plan versioning.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from core import paths
from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for

DEFAULT_STORAGE_PATH = paths.storage_file("plan_progress.json")


def current_week_key(on_date: Optional[date] = None) -> str:
    """ISO year-week key, e.g. '2026-W32' - same convention as
    HistoryService._week_key, just formatted as a string for use as a
    plain dict/JSON key."""
    d = on_date or datetime.now().date()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


class PlanProgressService:
    """Tracks which (day_number, task_index) tasks are checked off for
    one user's current week's plan."""

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or backend_for(DEFAULT_STORAGE_PATH)

    def get_completed(self, week_key: Optional[str] = None) -> set[tuple[int, int]]:
        """Return the set of (day_number, task_index) pairs checked off
        for this user's given week (defaults to the current week)."""
        week_key = week_key or current_week_key()
        completed = set()
        for record in self._backend.read_all():
            if record.get("user_id") == self.user_id and record.get("week_key") == week_key:
                completed.add((record["day_number"], record["task_index"]))
        return completed

    def clear_week(self, week_key: Optional[str] = None) -> None:
        """Drop every checkmark this user has for the week.

        Called when the week's plan is deliberately regenerated: the
        tasks those ticks referred to no longer exist, and carrying them
        over is what made a tick against one task reappear against a
        completely different one.
        """
        week_key = week_key or current_week_key()
        with self._backend.transaction() as records:
            self._backend.commit([
                r for r in records
                if not (
                    r.get("user_id") == self.user_id
                    and r.get("week_key") == week_key
                )
            ])

    def clear_all(self) -> None:
        """Drop every checkmark this user has, in every week.

        Only used when a demo account is rebuilt from scratch: without
        it a "3-day demo" reopened next week carries the previous
        build's ticks and reports plan progress the new history cannot
        account for.
        """
        with self._backend.transaction() as records:
            self._backend.commit([
                r for r in records if r.get("user_id") != self.user_id
            ])

    def clear_days_from(self, day_number: int, week_key: Optional[str] = None) -> None:
        """Drop this user's checkmarks for day `day_number` onward.

        The partial version of `clear_week`, for when only the REST of
        the week is rewritten - a day that fell outside the week's band
        and the user chose to let count. The days already lived through
        keep their tasks and therefore keep their ticks; wiping them
        would tell someone they had not done work they actually did.
        """
        week_key = week_key or current_week_key()
        with self._backend.transaction() as records:
            self._backend.commit([
                r for r in records
                if not (
                    r.get("user_id") == self.user_id
                    and r.get("week_key") == week_key
                    and int(r.get("day_number") or 0) >= day_number
                )
            ])

    def set_many_completed(
        self,
        pairs: list[tuple[int, int]],
        week_key: Optional[str] = None,
    ) -> None:
        """Tick many tasks in ONE locked write.

        set_completed() takes the file lock and rewrites the whole store
        per task, which is fine for a user tapping a checkbox and badly
        wrong for anything bulk: a 23-day demo ticks roughly seventy
        tasks, and seventy locked read-modify-write cycles is what made
        demo population slow enough to time out before (see
        HistoryService.record_many, added for exactly the same reason).
        """
        week_key = week_key or current_week_key()
        wanted = {(int(d), int(t)) for d, t in pairs}
        if not wanted:
            return
        stamp = datetime.now(timezone.utc).isoformat()
        with self._backend.transaction() as records:
            remaining = [
                r for r in records
                if not (
                    r.get("user_id") == self.user_id
                    and r.get("week_key") == week_key
                    and (r.get("day_number"), r.get("task_index")) in wanted
                )
            ]
            for day_number, task_index in sorted(wanted):
                remaining.append({
                    "user_id": self.user_id,
                    "week_key": week_key,
                    "day_number": day_number,
                    "task_index": task_index,
                    "updated_at_utc": stamp,
                })
            self._backend.commit(remaining)

    def set_completed(
        self,
        day_number: int,
        task_index: int,
        completed: bool,
        week_key: Optional[str] = None,
    ) -> None:
        """Mark one task done/not-done for this user's given week."""
        week_key = week_key or current_week_key()

        with self._backend.transaction() as records:
            remaining = [
                r for r in records
                if not (
                    r.get("user_id") == self.user_id
                    and r.get("week_key") == week_key
                    and r.get("day_number") == day_number
                    and r.get("task_index") == task_index
                )
            ]
            if completed:
                remaining.append({
                    "user_id": self.user_id,
                    "week_key": week_key,
                    "day_number": day_number,
                    "task_index": task_index,
                    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                })
            self._backend.commit(remaining)
