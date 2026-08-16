"""
Leaderboard Service
----------------------
"Reverse Leaderboard" (feature 31): a normal leaderboard rewards the
highest raw number, but for several digital-wellness metrics the
*healthiest* place to be is at the bottom (least screen time, least
stress) - a plain percentile display would bury that under "you're
only in the 8th percentile", which reads as bad even though it's the
goal. This flips the framing for exactly those "lower is better"
fields: your real percentile position is re-expressed as "you have
less <metric> than N% of the cohort", so a low raw value shows up as
a high leaderboard rank, matching what's actually being celebrated.

Reuses services/ml/cohort_service.py's real percentile-vs-training-cohort
data - no separate/duplicated statistic, no synthetic multi-user
leaderboard (this project deliberately keeps HistoryService entries
isolated per user_id; there is no cross-user comparison of other real
app users anywhere, by design - see services/identity/history_service.py's own
"User isolation" docstring section. The only population this compares
against is the anonymous training dataset CohortService already uses).
"""

from __future__ import annotations

from services.ml.cohort_service import CohortService

# Fields where a LOWER personal average is the healthier outcome - the
# only fields this "reverse" framing applies to. Restricted to fields
# CohortService can look up (real dataset columns).
LOWER_IS_BETTER_FIELDS = {
    "total_screen_min": "Total Screen Time",
    "social_min": "Social Media Time",
    "gaming_min": "Gaming Time",
    "stress_0_10": "Stress Level",
}


class LeaderboardService:
    """Reverse-framed cohort percentile rankings for 'lower is better' fields."""

    @classmethod
    def compute_reverse_leaderboard(
        cls, user_averages: dict[str, float]
    ) -> list[dict[str, object]]:
        """
        `user_averages` maps real HistoryService field names to this
        user's own real historical average. Returns one row per
        LOWER_IS_BETTER_FIELDS entry with cohort data available,
        sorted best-rank-first:
            {
                "field", "label", "user_value",
                "better_than_pct" (% of the real cohort with a HIGHER
                    value than this user - i.e. this user has less),
                "rank_estimate" (that percentage applied to the real
                    cohort size, i.e. "you'd out-rank roughly this many
                    people in the training population"),
            }
        """
        rows = []
        for field, label in LOWER_IS_BETTER_FIELDS.items():
            value = user_averages.get(field)
            if value is None:
                continue
            percentile = CohortService.percentile_for(field, value)
            if percentile is None:
                continue
            # percentile_for() is "% of cohort <= value" - for a
            # lower-is-better field, the people you're "beating" (in
            # the healthy sense) are the ones with a HIGHER value, so
            # invert it.
            better_than_pct = round(100.0 - percentile, 1)
            cohort_size = CohortService.cohort_size()
            rows.append({
                "field": field,
                "label": label,
                "user_value": round(float(value), 1),
                "better_than_pct": better_than_pct,
                "rank_estimate": int(round((better_than_pct / 100.0) * cohort_size)) if cohort_size else None,
            })

        rows.sort(key=lambda r: r["better_than_pct"], reverse=True)
        return rows
