"""
Plan Lock Service
-----------------
Freezes one user's 7-day plan for the ISO week it belongs to.

Why this exists at all. The plan used to be regenerated from whatever
prediction happened to be most recent, every time the page was opened.
Two things followed, and both were reproduced against the running app:

  1. The plan churned. Two check-ins on the same day - a score of 84
     and then a score of 78 - produced two completely different plans
     under the same week key: focus went from ["Maintain Your Momentum"]
     to ["Social Media Boundaries", "Stress Reset", "Sleep Recovery"].
     A "weekly" plan that is really a daily plan repeated seven times
     is not a plan, and with an irregular week (84 / 60 / 75) it never
     settles at all.

  2. Worse, checkmarks bled. Progress is stored per
     (week_key, day_number, task_index) with no reference to what that
     task said, so a tick against "Look back at yesterday's plan"
     silently reappeared on "Your screen time was 140 min. Try landing
     under 125 min" once the plan behind it changed. That is quiet data
     corruption of the user's own record of what they did.

The fix is to make the week the unit it claims to be: the plan is
generated once, stored, and served back unchanged for the rest of that
ISO week. Regeneration is deliberate and explicit, not a side effect of
opening a page.

What still updates within a locked week, because the user asked for it
and because it does not invalidate a tick:
  - the day's exercise numbers are recomposed from the newest values,
    so "your screen time was X" stays true after an update;
  - an explicit `regenerate` request (the user's check-in changed
    materially and they chose to let it count) replaces the snapshot
    AND clears that week's checkmarks, because the tasks behind them
    no longer exist. Clearing is the honest option: silently keeping
    ticks is the bug this service was written to remove.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from services.plan_progress_service import current_week_key
from services.storage.base import StorageBackend
from services.storage.json_file_storage import JSONFileStorageBackend

DEFAULT_STORAGE_PATH = "storage/plan_locks.json"


@dataclass(slots=True)
class LockedPlan:
    """A stored plan snapshot plus how it came to be stored."""

    week_key: str
    plan: dict[str, Any]
    created_at_utc: str
    # The score range the plan was built for, so the client can say what
    # the week was aimed at and detect a day that falls outside it.
    band_low: Optional[float] = None
    band_high: Optional[float] = None
    # Bumped every time the week's plan is deliberately regenerated.
    revision: int = 1


class PlanLockService:
    """One stored plan per user per ISO week."""

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or JSONFileStorageBackend(DEFAULT_STORAGE_PATH)

    # ---------------------------------------------------------------- read
    def get(self, week_key: Optional[str] = None) -> Optional[LockedPlan]:
        """This user's stored plan for the week, or None if unset."""
        week_key = week_key or current_week_key()
        for record in self._backend.read_all():
            if record.get("user_id") == self.user_id and record.get("week_key") == week_key:
                return self._to_locked(record)
        return None

    @staticmethod
    def _to_locked(record: dict[str, Any]) -> Optional[LockedPlan]:
        """Records are stored with the plan as a JSON string.

        A snapshot that will not parse is treated as absent rather than
        raising: the caller then generates a fresh plan, which is a far
        better outcome for the user than a 500 on the weekly page.
        """
        raw = record.get("plan")
        try:
            plan = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except (TypeError, ValueError):
            return None
        if not isinstance(plan, dict) or not plan:
            return None
        return LockedPlan(
            week_key=record.get("week_key", ""),
            plan=plan,
            created_at_utc=record.get("created_at_utc", ""),
            band_low=record.get("band_low"),
            band_high=record.get("band_high"),
            revision=int(record.get("revision") or 1),
        )

    # --------------------------------------------------------------- write
    def save(
        self,
        plan: dict[str, Any],
        week_key: Optional[str] = None,
        band_low: Optional[float] = None,
        band_high: Optional[float] = None,
        revision: Optional[int] = None,
    ) -> LockedPlan:
        """Store (or replace) this user's plan for the week."""
        week_key = week_key or current_week_key()
        existing = self.get(week_key)
        next_revision = revision if revision is not None else (
            (existing.revision + 1) if existing else 1
        )
        record = {
            "user_id": self.user_id,
            "week_key": week_key,
            # Serialised rather than nested so the flat-record storage
            # backend keeps working unchanged for every other caller.
            "plan": json.dumps(plan, ensure_ascii=False),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "band_low": band_low,
            "band_high": band_high,
            "revision": next_revision,
        }
        with self._backend.transaction() as records:
            remaining = [
                r for r in records
                if not (r.get("user_id") == self.user_id and r.get("week_key") == week_key)
            ]
            remaining.append(record)
            # The backend persists through commit(), not through
            # mutating the yielded list - matching PlanProgressService.
            self._backend.commit(remaining)
        return self._to_locked(record)

    def clear_all(self) -> None:
        """Drop every stored plan for this user, in every week.

        Only used when a demo account is rebuilt: a frozen plan from a
        previous build describes days that no longer exist.
        """
        with self._backend.transaction() as records:
            self._backend.commit([
                r for r in records if r.get("user_id") != self.user_id
            ])

    def theme_streaks(self, before_week: Optional[str] = None, look_back: int = 6) -> dict[str, int]:
        """How many CONSECUTIVE previous weeks each theme has been a
        focus area, counting back from the week before `before_week`.

        This is what makes week two onward a continuation instead of a
        restart. A theme the user has already spent two weeks on should
        not open with "set a fixed bedtime" for a third time; the plan
        starts it at the tier they have actually reached.

        Consecutive is the operative word, and it is why this walks
        backwards a week at a time rather than counting appearances. A
        theme worked on in weeks 1 and 5 is not a five-week habit - the
        streak broke, and picking up at the hardest tier after a month
        away would be setting someone up to fail. A missing week (no
        plan stored at all) ends the walk for the same reason.
        """
        from datetime import date as _date
        from datetime import timedelta

        anchor = before_week or current_week_key()
        stored = {
            r.get("week_key"): r for r in self._backend.read_all()
            if r.get("user_id") == self.user_id
        }

        # Week keys are not arithmetic ("2026-W01" minus one week is not
        # "2026-W00"), so the walk goes through real dates.
        try:
            iso_year, iso_week = anchor.split("-W")
            cursor = _date.fromisocalendar(int(iso_year), int(iso_week), 1)
        except (AttributeError, ValueError):
            return {}

        streaks: dict[str, int] = {}
        alive: Optional[set[str]] = None
        for _ in range(max(0, look_back)):
            cursor -= timedelta(days=7)
            key = current_week_key(cursor)
            record = stored.get(key)
            if record is None:
                break
            locked = self._to_locked(record)
            if locked is None:
                break
            themes = {t for t in (locked.plan.get("focus_areas") or []) if t}
            # Only themes that have been present in EVERY week walked so
            # far keep counting; anything else broke its streak.
            alive = themes if alive is None else (alive & themes)
            if not alive:
                break
            for theme in alive:
                streaks[theme] = streaks.get(theme, 0) + 1
        return streaks

    def clear(self, week_key: Optional[str] = None) -> None:
        """Drop this user's snapshot for the week."""
        week_key = week_key or current_week_key()
        with self._backend.transaction() as records:
            self._backend.commit([
                r for r in records
                if not (r.get("user_id") == self.user_id and r.get("week_key") == week_key)
            ])


# --------------------------------------------------------------- score band
# How wide the week's target band is around the running average, in
# score points either side. Wide enough that an ordinary day does not
# trip it, narrow enough that a genuinely unusual day does.
BAND_HALF_WIDTH = 6.0


def week_band(
    scores: list[float],
    weights: Optional[list[float]] = None,
) -> tuple[Optional[float], Optional[float]]:
    """The score range this week is being run against.

    Built from the days already logged this week rather than from a
    single prediction, which is the whole point: a plan aimed at one
    day's number changes every time that number does. Returns
    (None, None) until there is something to average, so the caller can
    tell "no band yet" apart from "a band centred on zero".

    `weights` lets a day count for less than a full day without being
    erased - that is what a day the user marked as an exception is
    (see services/day_decision_service.py). Omitted, every day counts
    once, which is what every caller did before exceptions existed.
    """
    pairs = [
        (float(s), 1.0 if weights is None else float(weights[i]))
        for i, s in enumerate(scores)
        if isinstance(s, (int, float)) and not isinstance(s, bool)
    ]
    pairs = [(s, w) for s, w in pairs if w > 0]
    total_weight = sum(w for _, w in pairs)
    if not pairs or total_weight <= 0:
        return (None, None)
    avg = sum(s * w for s, w in pairs) / total_weight
    return (
        round(max(0.0, avg - BAND_HALF_WIDTH), 1),
        round(min(100.0, avg + BAND_HALF_WIDTH), 1),
    )


def is_outside_band(score: Optional[float], low: Optional[float], high: Optional[float]) -> bool:
    """Whether a day falls outside the week's band.

    False when there is no band or no score - an unknown is never
    reported as an exception, because prompting someone about a day the
    app cannot actually assess is worse than staying quiet.
    """
    if score is None or low is None or high is None:
        return False
    return score < low or score > high
