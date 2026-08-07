"""
History Service
----------------
Local persistence for each user's daily real predictions, used by the
Weekly Insights features (GitHub-style heatmap, weekly story card, week
comparison, share report).

Important scope note: this service does NOT touch the ML pipeline. It
only reads the *outputs* PredictionService already produced
(PredictionResult) plus the already-validated user_data dict, and writes
a small, flat record per (user_id, date) so those outputs can be
reviewed across days/weeks. It never re-predicts, re-trains, or modifies
model inputs/outputs.

Storage: delegated to a `StorageBackend` (see services/storage/), by
default `JSONFileStorageBackend` pointed at
`<project_root>/storage/prediction_history.json` - the same on-disk file
and shape the project always used, so no migration step is required.
`HistoryService` itself never opens a file directly; swapping to
Postgres later means constructing `HistoryService(storage=PostgresStorageBackend(...))`
- nothing else in this class changes.

User isolation
---------------
Every entry now carries a `user_id`. Records are keyed by
`(user_id, date)`: running a prediction again on the same day for the
same user updates that day's entry; it no longer touches (or overwrites)
any other user's entry for that date, which the previous date-only
keying did. There is no authentication system yet, so callers are free
to pass any stable per-session identifier as `user_id` - see
`utils/session.get_user_id()` for the one the Streamlit pages use today.
For backward compatibility, entries written before this field existed
(no `user_id` key) are treated as belonging to `"default"`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Optional

from services.storage.base import StorageBackend
from services.storage.json_file_storage import JSONFileStorageBackend

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORAGE_PATH = PROJECT_ROOT / "storage" / "prediction_history.json"

DEFAULT_USER_ID = "default"

# Raw/derived user_data fields worth keeping per entry for trend
# summaries (story card, week comparison). Kept intentionally small -
# this is a log for UI features, not a copy of the full feature vector.
#
# Public name (`TRACKED_FIELDS`) so other modules that shape the same
# entries for their own charts (see services/analytics_service.py's
# behavioral-pattern methods) can reuse this exact list instead of
# hand-duplicating it - `_TRACKED_FIELDS` kept as an alias since it's
# referenced elsewhere (services/opportunity_cost_service.py's
# docstring) and this is additive, not a rename.
TRACKED_FIELDS = [
    "total_screen_min",
    "social_min",
    "gaming_min",
    "work_study_min",
    "video_min",
    "sleep_hours",
    "sleep_quality_1_10",
    "stress_0_10",
    "focus_0_100",
    "productivity_0_100",
    "physical_activity_min_per_day",
]
_TRACKED_FIELDS = TRACKED_FIELDS


@dataclass(slots=True)
class WeekSummary:
    """Aggregated averages for a set of history entries (one "week")."""

    week_key: str
    start_date: str
    end_date: str
    num_entries: int
    avg_health_score: Optional[float]
    avg_total_screen_min: Optional[float]
    avg_sleep_hours: Optional[float]
    avg_focus_0_100: Optional[float]
    avg_social_min: Optional[float]
    avg_stress_0_10: Optional[float]


class HistoryService:
    """
    Reads/writes one user's prediction history log.

    Each `HistoryService` instance is scoped to a single `user_id` -
    every read method returns only that user's entries, and `record()`
    only ever upserts that user's `(user_id, date)` entry. This mirrors
    how the Streamlit pages already use it (one instance per page render)
    and keeps every call site unchanged except for the constructor.
    """

    def __init__(
        self,
        user_id: str = DEFAULT_USER_ID,
        storage: Optional[StorageBackend] = None,
        storage_path: Optional[Path] = None,
    ) -> None:
        self.user_id = user_id or DEFAULT_USER_ID
        if storage is not None:
            self.storage = storage
        else:
            path = Path(storage_path) if storage_path else DEFAULT_STORAGE_PATH
            self.storage = JSONFileStorageBackend(path)

    # ======================================================
    # Internal helpers
    # ======================================================

    @staticmethod
    def _entry_user_id(entry: dict[str, Any]) -> str:
        """Entries written before user_id existed belong to DEFAULT_USER_ID."""
        return entry.get("user_id") or DEFAULT_USER_ID

    def _load_own_entries(self) -> list[dict[str, Any]]:
        """All entries in storage, filtered down to this instance's user."""
        return [
            e for e in self.storage.read_all()
            if self._entry_user_id(e) == self.user_id
        ]

    # ======================================================
    # Writing
    # ======================================================

    def record(
        self,
        user_data: dict[str, Any],
        prediction_result: Any,
        persona: Optional[str] = None,
        on_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Upsert today's (or `on_date`'s) entry for this instance's user
        from a *real* prediction. Returns the stored entry.

        Concurrency: the whole load -> replace-this-user's-entry-for-this-date
        -> save cycle happens inside `storage.transaction()`, so two
        concurrent `record()` calls (same or different users) are
        serialized instead of racing and silently dropping one write.
        """
        entry_date = on_date or datetime.now().date()
        date_str = entry_date.isoformat()

        entry: dict[str, Any] = {
            "user_id": self.user_id,
            "date": date_str,
            "day_of_week": entry_date.strftime("%A"),
            "health_score": getattr(prediction_result, "regression_score", None),
            "health_class": getattr(prediction_result, "prediction", None),
            "confidence": getattr(prediction_result, "confidence", None),
            "persona": persona,
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
        }

        for field_name in _TRACKED_FIELDS:
            if field_name in user_data:
                entry[field_name] = user_data[field_name]

        shap_features = getattr(prediction_result, "shap_features", None)
        if shap_features:
            top = shap_features[0]
            entry["top_shap_feature"] = getattr(top, "feature", None)

        with self.storage.transaction() as all_entries:
            # Drop only *this user's* entry for this date - every other
            # user's (and every other date's) entries are left untouched.
            remaining = [
                e for e in all_entries
                if not (self._entry_user_id(e) == self.user_id and e.get("date") == date_str)
            ]
            remaining.append(entry)
            remaining.sort(key=lambda e: (e.get("date", ""), self._entry_user_id(e)))
            self.storage.commit(remaining)

        logger.info("Recorded prediction history entry for user=%s date=%s", self.user_id, date_str)
        return entry

    # ======================================================
    # Reading
    # ======================================================

    def get_all(self) -> list[dict[str, Any]]:
        """All of this user's entries, sorted by date ascending."""
        return sorted(self._load_own_entries(), key=lambda e: e.get("date", ""))

    def get_last_n_days(self, n: int = 7, end_date: Optional[date] = None) -> list[dict[str, Any]]:
        """
        Return a list of length `n`, one dict per calendar day ending
        at `end_date` (default: today), each shaped as:
            {"date": "...", "day_of_week": "...", "entry": <entry or None>}
        Used by the heatmap so missing days still render as empty cells.
        """
        end = end_date or datetime.now().date()
        by_date = {e.get("date"): e for e in self._load_own_entries()}

        days = []
        for offset in range(n - 1, -1, -1):
            d = end - timedelta(days=offset)
            d_str = d.isoformat()
            days.append({
                "date": d_str,
                "day_of_week": d.strftime("%a"),
                "entry": by_date.get(d_str),
            })
        return days

    def get_previous_entry(self, before_date: Optional[str]) -> Optional[dict[str, Any]]:
        """
        This user's entry immediately preceding `before_date` in the
        sorted (ascending) entry list, or None if there isn't one.

        Centralizes a rule that used to be duplicated ad hoc at call
        sites (Dashboard.py took `all_entries[-2]`; Prediction.py
        searched for the index of the just-recorded entry and looked
        one back) - same result, one place the rule lives.
        """
        if before_date is None:
            return None
        ordered = self.get_all()
        idx = next((i for i, e in enumerate(ordered) if e.get("date") == before_date), None)
        if idx is None or idx == 0:
            return None
        return ordered[idx - 1]

    # ------------------------------------------------------
    # Week grouping
    # ------------------------------------------------------

    @staticmethod
    def _week_key(date_str: str) -> tuple[int, int]:
        d = date.fromisoformat(date_str)
        iso = d.isocalendar()
        return (iso[0], iso[1])  # (iso_year, iso_week)

    def group_by_week(self) -> "dict[tuple[int, int], list[dict[str, Any]]]":
        grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for entry in self.get_all():
            key = self._week_key(entry["date"])
            grouped.setdefault(key, []).append(entry)
        return grouped

    def first_week_entries(self) -> list[dict[str, Any]]:
        grouped = self.group_by_week()
        if not grouped:
            return []
        first_key = min(grouped.keys())
        return grouped[first_key]

    def current_week_entries(self) -> list[dict[str, Any]]:
        grouped = self.group_by_week()
        if not grouped:
            return []
        today_key = self._week_key(datetime.now().date().isoformat())
        if today_key in grouped:
            return grouped[today_key]
        # No entry recorded yet this calendar week - fall back to the
        # most recently recorded week so the UI still has data to show.
        latest_key = max(grouped.keys())
        return grouped[latest_key]

    def previous_week_entries(self) -> list[dict[str, Any]]:
        """The calendar week immediately before the current week's, if any."""
        grouped = self.group_by_week()
        if not grouped:
            return []
        keys = sorted(grouped.keys())
        current = self.current_week_entries()
        if not current:
            return []
        current_key = self._week_key(current[0]["date"])
        idx = keys.index(current_key) if current_key in keys else -1
        if idx <= 0:
            return []
        return grouped[keys[idx - 1]]

    # ------------------------------------------------------
    # Summaries
    # ------------------------------------------------------

    @staticmethod
    def _avg(entries: list[dict[str, Any]], field_name: str) -> Optional[float]:
        values = [
            float(e[field_name])
            for e in entries
            if e.get(field_name) is not None
        ]
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def summarize(self, entries: list[dict[str, Any]]) -> Optional[WeekSummary]:
        if not entries:
            return None
        ordered = sorted(entries, key=lambda e: e.get("date", ""))
        year, week = self._week_key(ordered[0]["date"])
        return WeekSummary(
            week_key=f"{year}-W{week:02d}",
            start_date=ordered[0]["date"],
            end_date=ordered[-1]["date"],
            num_entries=len(ordered),
            avg_health_score=self._avg(ordered, "health_score"),
            avg_total_screen_min=self._avg(ordered, "total_screen_min"),
            avg_sleep_hours=self._avg(ordered, "sleep_hours"),
            avg_focus_0_100=self._avg(ordered, "focus_0_100"),
            avg_social_min=self._avg(ordered, "social_min"),
            avg_stress_0_10=self._avg(ordered, "stress_0_10"),
        )
