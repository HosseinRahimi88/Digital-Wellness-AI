"""
Achievement Service
----------------------
Small, rule-based helper that decides whether the user has something
worth celebrating, based purely on real recorded wellness scores
(HistoryService entries built from real PredictionService output). No
model logic, no LLM - just comparing numbers that already exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Minimum improvement (in points, or in percent) before we call it an
# "achievement" instead of noise.
MIN_POINT_DELTA = 1.0
MIN_PERCENT_DELTA = 2.0


@dataclass(slots=True)
class Achievement:
    unlocked: bool
    message: str = ""
    delta_points: Optional[float] = None
    delta_percent: Optional[float] = None


class AchievementService:
    """Compares a 'current' score against a 'previous' score."""

    @staticmethod
    def _percent_change(old: float, new: float) -> Optional[float]:
        if old == 0:
            return None
        return round(((new - old) / abs(old)) * 100, 1)

    @classmethod
    def evaluate(
        cls,
        current_score: Optional[float],
        previous_score: Optional[float],
        context_label: str = "this week",
    ) -> Achievement:
        """
        Returns an Achievement describing whether `current_score` is a
        meaningful improvement over `previous_score`.
        """
        if current_score is None or previous_score is None:
            return Achievement(unlocked=False)

        delta = round(current_score - previous_score, 1)
        pct = cls._percent_change(previous_score, current_score)

        is_improvement = delta >= MIN_POINT_DELTA or (
            pct is not None and pct >= MIN_PERCENT_DELTA
        )

        if not is_improvement:
            return Achievement(unlocked=False, delta_points=delta, delta_percent=pct)

        if pct is not None:
            message = f"Congratulations! You improved by {pct:.0f}% {context_label}."
        else:
            message = f"Congratulations! Your wellness score is up {delta:+.1f} pts {context_label}."

        return Achievement(
            unlocked=True,
            message=message,
            delta_points=delta,
            delta_percent=pct,
        )
