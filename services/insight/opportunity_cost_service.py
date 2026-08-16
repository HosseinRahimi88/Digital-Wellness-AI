"""
Opportunity Cost Service
---------------------------
Pure arithmetic helpers that translate a user's logged screen-time
minutes (already tracked by HistoryService - see its `_TRACKED_FIELDS`)
into human-relatable equivalents: "if this pace continued for a year,
that's roughly N full days", plus a few concrete activity equivalents
(books, workouts, movies). No ML, no new data collection - this only
re-expresses numbers HistoryService already stores.

Deliberately framed as an estimate, not a prediction: everything here
is simple unit conversion (minutes -> hours -> days), not model output,
so the UI copy must never call this a "forecast".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# Rough, clearly-labeled reference durations used only to make minutes
# tangible - not claims about any specific book/workout/movie.
MINUTES_PER_BOOK = 300  # ~an average novel read at a relaxed pace
MINUTES_PER_WORKOUT = 45
MINUTES_PER_MOVIE = 110


@dataclass(slots=True)
class OpportunityCost:
    has_data: bool
    avg_daily_minutes: Optional[float]
    days_measured: int
    total_minutes_measured: Optional[float]
    projected_days_lost_per_year: Optional[float]
    equivalent_books_per_year: Optional[float]
    equivalent_workouts_per_year: Optional[float]
    equivalent_movies_per_year: Optional[float]
    lost_days_last_week: Optional[float]


class OpportunityCostService:
    """Pure data-shaping helpers - no Streamlit/UI code, no I/O."""

    @staticmethod
    def compute(
        entries: list[dict[str, Any]],
        field_name: str = "total_screen_min",
    ) -> OpportunityCost:
        """
        `entries` should be a recent window (e.g.
        HistoryService.get_last_n_days(n=7)-style entries, or
        HistoryService.get_all() filtered by the caller) containing
        `field_name`. Missing/None values are skipped, not treated as 0.
        """
        values = [
            float(e[field_name])
            for e in entries
            if e.get(field_name) is not None
        ]

        if not values:
            return OpportunityCost(
                has_data=False,
                avg_daily_minutes=None,
                days_measured=0,
                total_minutes_measured=None,
                projected_days_lost_per_year=None,
                equivalent_books_per_year=None,
                equivalent_workouts_per_year=None,
                equivalent_movies_per_year=None,
                lost_days_last_week=None,
            )

        avg_daily = sum(values) / len(values)
        total_measured = sum(values)

        projected_year_minutes = avg_daily * 365
        projected_days_lost = projected_year_minutes / (24 * 60)

        lost_days_last_week = (avg_daily * 7) / (24 * 60)

        return OpportunityCost(
            has_data=True,
            avg_daily_minutes=round(avg_daily, 1),
            days_measured=len(values),
            total_minutes_measured=round(total_measured, 1),
            projected_days_lost_per_year=round(projected_days_lost, 1),
            equivalent_books_per_year=round(projected_year_minutes / MINUTES_PER_BOOK, 1),
            equivalent_workouts_per_year=round(projected_year_minutes / MINUTES_PER_WORKOUT, 1),
            equivalent_movies_per_year=round(projected_year_minutes / MINUTES_PER_MOVIE, 1),
            lost_days_last_week=round(lost_days_last_week, 2),
        )
