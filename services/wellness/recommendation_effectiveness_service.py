"""
Recommendation Effectiveness Service
--------------------------------------
Answers two related, real-data-only questions:

1. (Feature 13) For a resolved/active commitment
   (services/wellness/commitment_service.py), did the user's real recorded
   outcomes actually improve after they committed? Compares real
   HistoryService averages in the window *before* `committed_on`
   against the window *after* it - both the overall health_score and,
   where a category maps to one, that category's own tracked habit
   field (e.g. Sleep -> sleep_hours).

2. (Feature 56) "Recommendation Learning Loop" - aggregates every
   resolved evaluation from (1) into a per-category track record (a
   real, personal, measured average score delta), which
   RecommendationService.generate() can optionally use to gently
   re-order future recommendations toward categories that have
   actually helped *this* user before - a genuine outcome-driven
   feedback loop, without touching the ML pipeline or model at all.

No ML/model calls anywhere in this file - it only aggregates
HistoryService entries HistoryService already persisted from real
PredictionService output, plus CommitmentService records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Optional

from services.wellness.commitment_service import Commitment

# How many days of real history to average on each side of a
# commitment's `committed_on` date. Long enough to smooth day-to-day
# noise, short enough that "did this specific commitment help" stays a
# meaningful question rather than blending in unrelated later changes.
EFFECTIVENESS_WINDOW_DAYS = 7

# Need at least this many real entries on *each* side of the window
# before an effectiveness verdict is reported - fewer than that and
# "before vs after" is just noise.
MIN_ENTRIES_PER_WINDOW = 2

# A health_score delta smaller than this (in either direction) is
# treated as "no measurable effect yet" rather than a false positive/
# negative signal.
MIN_MEANINGFUL_SCORE_DELTA = 3.0

# Category -> the one HistoryService-tracked field most representative
# of that category's real target habit, and whether a *higher* value
# of that field is the healthier direction (used only for a
# human-readable "field improved" readout - the headline effectiveness
# verdict itself is always based on health_score, the model's own
# holistic output, not this proxy field).
CATEGORY_PRIMARY_FIELD = {
    "Sleep": ("sleep_hours", True),
    "Mental Health": ("stress_0_10", False),
    "Activity": ("physical_activity_min_per_day", True),
    "Screen Time": ("total_screen_min", False),
    "Focus": ("focus_0_100", True),
}


@dataclass(slots=True)
class EffectivenessResult:
    commitment_id: str
    category: str
    committed_on: str
    status: str
    before_avg_score: Optional[float]
    after_avg_score: Optional[float]
    score_delta: Optional[float]
    verdict: str  # "improved" | "declined" | "no_change" | "insufficient_data"
    field_name: Optional[str] = None
    field_before_avg: Optional[float] = None
    field_after_avg: Optional[float] = None


class RecommendationEffectivenessService:
    """Pure data-shaping over real Commitment + HistoryService records."""

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    @staticmethod
    def _avg_in_window(
        entries: list[dict[str, Any]], field_name: str, start: date, end_exclusive: date
    ) -> tuple[Optional[float], int]:
        values = []
        for e in entries:
            d_str = e.get("date")
            if not d_str:
                continue
            try:
                d = date.fromisoformat(d_str)
            except ValueError:
                continue
            if start <= d < end_exclusive and e.get(field_name) is not None:
                values.append(float(e[field_name]))
        if not values:
            return None, 0
        return round(sum(values) / len(values), 1), len(values)

    # ------------------------------------------------------------
    # Feature 13: effectiveness of a single commitment
    # ------------------------------------------------------------

    @classmethod
    def evaluate_commitment(
        cls, commitment: Commitment, entries: list[dict[str, Any]]
    ) -> EffectivenessResult:
        try:
            committed_date = date.fromisoformat(commitment.committed_on)
        except ValueError:
            return EffectivenessResult(
                commitment_id=commitment.commitment_id, category=commitment.category,
                committed_on=commitment.committed_on, status=commitment.status,
                before_avg_score=None, after_avg_score=None, score_delta=None,
                verdict="insufficient_data",
            )

        window = timedelta(days=EFFECTIVENESS_WINDOW_DAYS)
        before_avg, before_n = cls._avg_in_window(
            entries, "health_score", committed_date - window, committed_date
        )
        after_avg, after_n = cls._avg_in_window(
            entries, "health_score", committed_date, committed_date + window
        )

        field_name, _higher_is_better = CATEGORY_PRIMARY_FIELD.get(commitment.category, (None, True))
        field_before = field_after = None
        if field_name:
            field_before, _ = cls._avg_in_window(entries, field_name, committed_date - window, committed_date)
            field_after, _ = cls._avg_in_window(entries, field_name, committed_date, committed_date + window)

        if before_n < MIN_ENTRIES_PER_WINDOW or after_n < MIN_ENTRIES_PER_WINDOW:
            return EffectivenessResult(
                commitment_id=commitment.commitment_id, category=commitment.category,
                committed_on=commitment.committed_on, status=commitment.status,
                before_avg_score=before_avg, after_avg_score=after_avg, score_delta=None,
                verdict="insufficient_data", field_name=field_name,
                field_before_avg=field_before, field_after_avg=field_after,
            )

        delta = round(after_avg - before_avg, 1)
        if delta >= MIN_MEANINGFUL_SCORE_DELTA:
            verdict = "improved"
        elif delta <= -MIN_MEANINGFUL_SCORE_DELTA:
            verdict = "declined"
        else:
            verdict = "no_change"

        return EffectivenessResult(
            commitment_id=commitment.commitment_id, category=commitment.category,
            committed_on=commitment.committed_on, status=commitment.status,
            before_avg_score=before_avg, after_avg_score=after_avg, score_delta=delta,
            verdict=verdict, field_name=field_name,
            field_before_avg=field_before, field_after_avg=field_after,
        )

    @classmethod
    def evaluate_all(
        cls, commitments: list[Commitment], entries: list[dict[str, Any]]
    ) -> list[EffectivenessResult]:
        """Every commitment's effectiveness, most recent first."""
        results = [cls.evaluate_commitment(c, entries) for c in commitments]
        results.sort(key=lambda r: r.committed_on, reverse=True)
        return results

    # ------------------------------------------------------------
    # Feature 56: Recommendation Learning Loop input
    # ------------------------------------------------------------

    @classmethod
    def compute_category_track_record(
        cls, commitments: list[Commitment], entries: list[dict[str, Any]]
    ) -> dict[str, float]:
        """
        Average real health_score delta per category, across every
        commitment (active or resolved) with a measurable verdict for
        that category. Categories with no measurable history are
        simply absent from the returned dict (not zero) so
        RecommendationService can tell "no data" apart from "measured
        as neutral".

        This is the entire "learning" in the Recommendation Learning
        Loop: a real, per-user, outcome-grounded number per category,
        derived from nothing but this user's own committed history.
        """
        by_category: dict[str, list[float]] = {}
        for commitment in commitments:
            result = cls.evaluate_commitment(commitment, entries)
            if result.score_delta is None:
                continue
            by_category.setdefault(commitment.category, []).append(result.score_delta)

        return {
            category: round(sum(deltas) / len(deltas), 1)
            for category, deltas in by_category.items()
        }
