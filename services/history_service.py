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
    # Added for utils/persona_titles.py: its archetype rules read the
    # night/fragmentation/social-share signals, and without these stored
    # per entry the profile page's persona was being resolved from an
    # entry that simply lacked them - which silently scored every user
    # against a partial input rather than their real day. Purely
    # additive: entries written before this existed just don't carry the
    # keys, and every reader here already treats a missing field as
    # absent rather than zero.
    "night_ratio",
    "night_screen_min",
    "pre_sleep_screen_min",
    "social_ratio",
    "work_study_ratio",
    "gaming_ratio",
    "fragmentation_index_0_100",
    "pickups_per_day",
    "notification_density",
    "social_comparison_1_10",
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

    # Snapshot version. Bumped only if the shape below changes in a way
    # a reader must notice; readers treat an unknown version as "cannot
    # reopen this day" rather than guessing at it.
    SNAPSHOT_VERSION = 1

    @staticmethod
    def _build_snapshot(user_data: dict[str, Any], prediction_result: Any) -> dict[str, Any]:
        """The two things a past day's result page cannot be rebuilt without:
        the full input the user actually submitted, and the model's own
        output for it.

        Deliberately NOT the finished response. Everything else on the
        result page - recommendations, dimension breakdown, confidence
        wording, OOD check, tone framing - is derived, so it is
        regenerated on read through the one function that already builds
        it (api/routers/prediction.build_predict_response). Storing the
        finished text instead would mean a second copy that drifts from
        the live pipeline, and would freeze four languages of
        recommendation text into every single day.

        What is stored is the part that genuinely cannot be recomputed:
        re-running the model today would score against today's history
        and produce a different number than the one already shown in the
        heatmap for that day. The score a user reopens is the score they
        were given.
        """
        shap = []
        for f in (getattr(prediction_result, "shap_features", None) or []):
            shap.append({
                "feature": getattr(f, "feature", None),
                "value": getattr(f, "value", None),
                "shap_value": getattr(f, "shap_value", 0.0),
                "abs_shap": getattr(f, "abs_shap", 0.0),
                "direction": getattr(f, "direction", ""),
                "score": getattr(f, "score", 0.0),
            })

        uncertainty = getattr(prediction_result, "uncertainty", None)
        uncertainty_dict = None
        if uncertainty is not None and hasattr(uncertainty, "to_dict"):
            uncertainty_dict = uncertainty.to_dict()

        return {
            "version": HistoryService.SNAPSHOT_VERSION,
            # The full submitted feature vector, not just TRACKED_FIELDS.
            # A check-in reopened from 20 of its 53 fields would be a
            # different check-in.
            "inputs": dict(user_data),
            "model_output": {
                "prediction": getattr(prediction_result, "prediction", None),
                "confidence": getattr(prediction_result, "confidence", None),
                "probabilities": dict(getattr(prediction_result, "probabilities", None) or {}),
                "regression_score": getattr(prediction_result, "regression_score", None),
                "model_name": getattr(prediction_result, "model_name", ""),
                "prediction_time_ms": getattr(prediction_result, "prediction_time_ms", 0.0),
                "timestamp": getattr(prediction_result, "timestamp", None),
                "shap_features": shap,
                "uncertainty": uncertainty_dict,
            },
        }

    def _build_entry(
        self,
        user_data: dict[str, Any],
        prediction_result: Any,
        persona: Optional[str] = None,
        on_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """One stored entry, without touching storage.

        Split out of `record()` so `record_many()` produces byte-identical
        rows rather than a second copy of this shape that could drift.
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

        entry["snapshot"] = self._build_snapshot(user_data, prediction_result)
        return entry

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
        entry = self._build_entry(user_data, prediction_result, persona, on_date)
        date_str = entry["date"]

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

    def record_many(
        self,
        rows: list[tuple[dict[str, Any], Any, Optional[str], date]],
    ) -> list[dict[str, Any]]:
        """Write several days for this user in ONE locked transaction.

        `record()` takes the storage lock, rewrites the whole file and
        releases it, per day. That is correct and it is what a real
        check-in should do - one day, one durable write.

        It is the wrong shape for anything that produces many days at
        once. Demo Mode builds 23 days for the user plus 8 for each of
        ten friends: 103 full read-modify-write cycles of a history file
        that is megabytes in size. Two things follow, and both were
        observed: it takes tens of seconds, and under that much lock
        traffic a write eventually hits StorageLockTimeout - which the
        demo's friend loop caught and turned into "0 friends" with no
        explanation, so the demo simply came back with no league in it.

        Same rows, same upsert rule, one lock.

        Each row is (user_data, prediction_result, persona, on_date).
        """
        if not rows:
            return []

        entries: list[dict[str, Any]] = []
        for user_data, prediction_result, persona, on_date in rows:
            entries.append(self._build_entry(user_data, prediction_result, persona, on_date))

        # Last write wins per date, matching record()'s upsert.
        by_date = {e["date"]: e for e in entries}

        with self.storage.transaction() as all_entries:
            remaining = [
                e for e in all_entries
                if not (self._entry_user_id(e) == self.user_id and e.get("date") in by_date)
            ]
            remaining.extend(by_date.values())
            remaining.sort(key=lambda e: (e.get("date", ""), self._entry_user_id(e)))
            self.storage.commit(remaining)

        logger.info(
            "Recorded %d prediction history entries for user=%s in one transaction",
            len(by_date), self.user_id,
        )
        return list(by_date.values())

    # ======================================================
    # Reading
    # ======================================================

    def get_all(self, include_excluded: bool = True) -> list[dict[str, Any]]:
        """
        All of this user's entries, sorted by date ascending.

        `include_excluded=False` drops entries the user has explicitly
        marked with `set_excluded(date, True)` - e.g. an outlier day
        they don't want counted in trend/average calculations. This
        never touches the live single-day prediction pipeline (which
        always uses the full, real input for that one request); it only
        controls which *past* days feed into aggregate views like
        analytics trends and weekly summaries. Defaults to True so
        every existing caller keeps seeing every entry unless it opts in.
        """
        entries = self._load_own_entries()
        if not include_excluded:
            entries = [e for e in entries if not e.get("excluded")]
        return sorted(entries, key=lambda e: e.get("date", ""))

    def delete_all(self) -> int:
        """
        Permanently remove every entry belonging to this instance's user
        (P1 item 35, "delete my data"). Returns how many were removed.

        Scoped to this user by the same `_entry_user_id` rule every read
        path uses, so one user's deletion can never touch another's
        rows - the whole read-modify-write runs inside the storage
        transaction for the same reason `record()` does.
        """
        removed = 0
        with self.storage.transaction() as all_entries:
            remaining = [e for e in all_entries if self._entry_user_id(e) != self.user_id]
            removed = len(all_entries) - len(remaining)
            if removed:
                self.storage.commit(remaining)
        logger.info("Deleted %d history entries for user=%s", removed, self.user_id)
        return removed

    def set_excluded(self, entry_date: str, excluded: bool) -> Optional[dict[str, Any]]:
        """
        Mark (or unmark) one of this user's own entries as excluded from
        aggregate trend/average calculations. Returns the updated entry,
        or None if no entry exists for that date. The excluded entry
        itself is never deleted - it still appears in `get_all()` (the
        default) and stays visible in raw history, only aggregate views
        that explicitly ask for `include_excluded=False` skip it.
        """
        with self.storage.transaction() as all_entries:
            updated = None
            for e in all_entries:
                if self._entry_user_id(e) == self.user_id and e.get("date") == entry_date:
                    e["excluded"] = excluded
                    updated = e
                    break
            if updated is not None:
                self.storage.commit(all_entries)
        return updated

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

    def group_by_week(self, include_excluded: bool = True) -> "dict[tuple[int, int], list[dict[str, Any]]]":
        grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for entry in self.get_all(include_excluded=include_excluded):
            key = self._week_key(entry["date"])
            grouped.setdefault(key, []).append(entry)
        return grouped

    def first_week_entries(self) -> list[dict[str, Any]]:
        grouped = self.group_by_week()
        if not grouped:
            return []
        first_key = min(grouped.keys())
        return grouped[first_key]

    def current_week_entries(self, include_excluded: bool = True) -> list[dict[str, Any]]:
        grouped = self.group_by_week(include_excluded=include_excluded)
        if not grouped:
            return []
        today_key = self._week_key(datetime.now().date().isoformat())
        if today_key in grouped:
            return grouped[today_key]
        # No entry recorded yet this calendar week - fall back to the
        # most recently recorded week so the UI still has data to show.
        latest_key = max(grouped.keys())
        return grouped[latest_key]

    def previous_week_entries(self, include_excluded: bool = True) -> list[dict[str, Any]]:
        """The calendar week immediately before the current week's, if any."""
        grouped = self.group_by_week(include_excluded=include_excluded)
        if not grouped:
            return []
        keys = sorted(grouped.keys())
        current = self.current_week_entries(include_excluded=include_excluded)
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
