"""
Reflection Service
-------------------
Group C Feature 42 - Reflection Loop.

A structured "reflect -> compare to reality -> recalibrate" loop layered
on top of the existing prediction history (services/history_service.py).
Each reflection is the user's own subjective self-rating ("how do you
feel your week went?", 1-5) plus optional free text, tied to a specific
date. This service does two things a plain journal wouldn't:

1. **Calibration analysis** - correlates the user's self-rating *changes*
   against the *objective* wellness-score changes measured by the ML
   pipeline over the same period (Pearson correlation - a real,
   mathematically meaningful statistic, not a fabricated "insight").
   A user whose self-perception tracks the measured trend closely is
   "well-calibrated"; someone who feels fine while their measured score
   is dropping (or vice versa) gets flagged - this is genuinely useful
   signal a plain journal never surfaces.
2. **Context-aware prompting** - the next reflection prompt references
   the user's own most recent real data (score trend direction, the
   feature that most influenced their last prediction per SHAP), so the
   "loop" actually closes: yesterday's model output shapes today's
   reflection question, and today's reflection feeds the next
   calibration check.

No leakage / no model involvement
------------------------------------
This is entirely presentation-and-analytics logic on top of numbers the
ML pipeline already produced (via HistoryService). It never feeds
reflections back into training, never touches model inputs, and the
correlation is computed purely from the user's own historical entries.

Storage
-------
Same pattern as HistoryService: a `StorageBackend` (JSON file by
default, `storage/reflections.json`), OS-level-locked read-modify-write
transactions, records keyed by `(user_id, date)`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np

from services.storage.base import StorageBackend
from services.storage.json_file_storage import JSONFileStorageBackend

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORAGE_PATH = PROJECT_ROOT / "storage" / "reflections.json"

DEFAULT_USER_ID = "default"

MIN_RATING = 1
MAX_RATING = 5


@dataclass(slots=True)
class CalibrationResult:
    """Output of ReflectionService.compute_calibration()."""

    available: bool = False
    sample_size: int = 0
    correlation: Optional[float] = None
    label: str = "Insufficient data"
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "sample_size": self.sample_size,
            "correlation": self.correlation,
            "label": self.label,
            "explanation": self.explanation,
        }


class ReflectionService:

    def __init__(
        self,
        user_id: str = DEFAULT_USER_ID,
        storage: Optional[StorageBackend] = None,
    ) -> None:
        self.user_id = user_id
        self.storage = storage or JSONFileStorageBackend(DEFAULT_STORAGE_PATH)

    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------

    @staticmethod
    def _entry_user_id(entry: dict[str, Any]) -> str:
        return entry.get("user_id", DEFAULT_USER_ID)

    def _load_own_entries(self) -> list[dict[str, Any]]:
        return [
            e for e in self.storage.read_all()
            if self._entry_user_id(e) == self.user_id
        ]

    # ------------------------------------------------------
    # Writing
    # ------------------------------------------------------

    def record_reflection(
        self,
        self_rating: int,
        reflection_text: str = "",
        on_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Upsert this user's reflection for `on_date` (default: today).
        Raises ValueError on an out-of-range rating rather than silently
        clamping it - a reflection rating is a direct, meaningful user
        input, not a derived numeric field, so it should fail loudly if
        the caller (a form) passes something invalid.
        """
        if not (MIN_RATING <= self_rating <= MAX_RATING):
            raise ValueError(f"self_rating must be between {MIN_RATING} and {MAX_RATING}, got {self_rating}")

        entry_date = on_date or datetime.now().date()
        date_str = entry_date.isoformat()

        entry: dict[str, Any] = {
            "user_id": self.user_id,
            "date": date_str,
            "self_rating": int(self_rating),
            "reflection_text": (reflection_text or "").strip(),
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
        }

        with self.storage.transaction() as all_entries:
            remaining = [
                e for e in all_entries
                if not (self._entry_user_id(e) == self.user_id and e.get("date") == date_str)
            ]
            remaining.append(entry)
            remaining.sort(key=lambda e: (e.get("date", ""), self._entry_user_id(e)))
            self.storage.commit(remaining)

        logger.info("Recorded reflection for user=%s date=%s rating=%d", self.user_id, date_str, self_rating)
        return entry

    # ------------------------------------------------------
    # Reading
    # ------------------------------------------------------

    def get_all(self) -> list[dict[str, Any]]:
        """All of this user's reflections, sorted by date ascending."""
        return sorted(self._load_own_entries(), key=lambda e: e.get("date", ""))

    # ------------------------------------------------------
    # Calibration analysis
    # ------------------------------------------------------

    def compute_calibration(
        self,
        history_entries: list[dict[str, Any]],
        min_pairs: int = 4,
    ) -> CalibrationResult:
        """
        Correlate day-over-day *changes* in self_rating against
        day-over-day *changes* in the objective `health_score` from
        HistoryService entries for the same dates.

        Using deltas (not raw levels) is deliberate: two people can have
        very different baseline self-rating habits (a chronic "I'm
        always a 3" rater vs. an "I'm always a 5" rater) while both
        being perfectly well-calibrated about *changes* - correlating
        raw levels would penalize the former for no real miscalibration.
        """
        reflections = self.get_all()
        if len(reflections) < min_pairs + 1 or len(history_entries) < min_pairs + 1:
            return CalibrationResult(
                available=False,
                explanation=(
                    "Not enough reflections and check-ins yet to measure "
                    "calibration - keep logging both and this will unlock."
                ),
            )

        history_by_date = {e.get("date"): e for e in history_entries if e.get("health_score") is not None}
        reflection_by_date = {e.get("date"): e for e in reflections}

        common_dates = sorted(set(history_by_date) & set(reflection_by_date))
        if len(common_dates) < min_pairs + 1:
            return CalibrationResult(
                available=False,
                explanation=(
                    "Not enough days have both a check-in and a reflection "
                    "yet to measure calibration."
                ),
            )

        ratings = [reflection_by_date[d]["self_rating"] for d in common_dates]
        scores = [history_by_date[d]["health_score"] for d in common_dates]

        rating_deltas = np.diff(np.array(ratings, dtype=float))
        score_deltas = np.diff(np.array(scores, dtype=float))

        if len(rating_deltas) < min_pairs or np.std(rating_deltas) == 0 or np.std(score_deltas) == 0:
            return CalibrationResult(
                available=False,
                sample_size=len(rating_deltas),
                explanation=(
                    "Not enough variation yet in your ratings or scores to "
                    "measure calibration reliably."
                ),
            )

        correlation = float(np.corrcoef(rating_deltas, score_deltas)[0, 1])

        if correlation >= 0.5:
            label = "Well-calibrated"
            explanation = (
                "Your self-ratings track your measured wellness score "
                "changes closely - your instincts about how a day/week "
                "went line up well with the data."
            )
        elif correlation >= 0.15:
            label = "Loosely calibrated"
            explanation = (
                "Your self-ratings move in the same general direction as "
                "your measured score, but not tightly - there's room to "
                "notice more of what's actually driving the number."
            )
        elif correlation > -0.15:
            label = "Uncorrelated"
            explanation = (
                "Your self-ratings don't currently track your measured "
                "wellness score changes - your gut sense and the data are "
                "telling somewhat different stories."
            )
        else:
            label = "Inversely calibrated"
            explanation = (
                "Your self-ratings tend to move opposite your measured "
                "score changes - worth a closer look at what's shaping "
                "how you feel about a day versus what the data shows."
            )

        return CalibrationResult(
            available=True,
            sample_size=len(rating_deltas),
            correlation=round(correlation, 3),
            label=label,
            explanation=explanation,
        )

    # ------------------------------------------------------
    # Prompt generation
    # ------------------------------------------------------

    def next_prompt(self, history_entries: list[dict[str, Any]]) -> str:
        """
        Build a reflection prompt grounded in this user's own most
        recent real data - not a generic/static question. Degrades to a
        generic prompt if there isn't enough history yet (new user).
        """
        if not history_entries:
            return "How has your relationship with your devices felt lately? Take a moment to reflect."

        ordered = sorted(history_entries, key=lambda e: e.get("date", ""))
        latest = ordered[-1]

        if len(ordered) >= 2:
            previous = ordered[-2]
            latest_score = latest.get("health_score")
            previous_score = previous.get("health_score")
            if latest_score is not None and previous_score is not None:
                delta = latest_score - previous_score
                top_feature = latest.get("top_shap_feature")
                feature_phrase = f" ({top_feature.replace('_', ' ')} stood out most)" if top_feature else ""
                if delta > 1:
                    return (
                        f"Your wellness score rose by {delta:.1f} points since your last check-in"
                        f"{feature_phrase}. What do you think you did differently?"
                    )
                if delta < -1:
                    return (
                        f"Your wellness score dropped by {abs(delta):.1f} points since your last check-in"
                        f"{feature_phrase}. What got in the way this time?"
                    )
                return (
                    "Your wellness score has held steady since your last check-in. "
                    "Does that match how the past few days actually felt?"
                )

        persona = latest.get("persona")
        if persona:
            return f"You've been trending toward '{persona}' lately - does that feel accurate to you?"

        return "How do you feel your digital habits have been lately? Take a moment to reflect."
