"""
Journey Summary Card Component
----------------------------------
A single, compact overview of a user's whole recorded history (as
opposed to app/components/story_card.py's "this week vs. last week"
narrative, or week_comparison_card.py's first-week-vs-current-week
comparison). Presentation for
GamificationService.compute_journey_summary(); no aggregation logic
here.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.social.gamification_service import GamificationService
from components.metric_card import MetricCard


class JourneySummaryCard:

    @staticmethod
    def render(
        entries: list[dict[str, Any]],
        title: str = "🧭 Your Journey So Far",
    ) -> None:
        if title:
            st.subheader(title)

        summary = GamificationService.compute_journey_summary(entries)

        if summary.total_checkins == 0:
            st.info("Your journey starts with your first check-in - run a prediction to begin.")
            return

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            MetricCard.render(title="Check-ins Logged", value=str(summary.total_checkins))
        with c2:
            MetricCard.render(
                title="Days on Your Journey",
                value=str(summary.days_since_first) if summary.days_since_first is not None else "N/A",
            )
        with c3:
            MetricCard.render(
                title="Best Score",
                value=f"{summary.best_score:.1f}" if summary.best_score is not None else "N/A",
                help_text=f"on {summary.best_date}" if summary.best_date else None,
            )
        with c4:
            MetricCard.render(
                title="Since First Check-in",
                value=(
                    f"{summary.improvement_since_first:+.1f} pts"
                    if summary.improvement_since_first is not None
                    else "N/A"
                ),
            )

        st.caption(
            f"First check-in: {summary.first_date} · "
            f"Latest: {summary.last_date} · "
            f"Average score: {summary.avg_score if summary.avg_score is not None else 'N/A'}"
        )
