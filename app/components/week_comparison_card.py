"""
Week Comparison Card Component
--------------------------------
Compares the user's first recorded week vs. their current week, using
real HistoryService data (real regression scores from PredictionService).
"""

from __future__ import annotations



import streamlit as st

from services.history_service import HistoryService
from components.metric_card import MetricCard


class WeekComparisonCard:

    @staticmethod
    def render(
        history_service: HistoryService,
        title: str = "📊 Week Comparison: First Week vs. Current Week",
    ) -> None:
        first_entries = history_service.first_week_entries()
        current_entries = history_service.current_week_entries()

        if title:
            st.subheader(title)

        if not first_entries or not current_entries:
            st.info(
                "Not enough history yet to compare weeks. Run predictions "
                "on a few different days to unlock this comparison."
            )
            return

        first_summary = history_service.summarize(first_entries)
        current_summary = history_service.summarize(current_entries)

        same_week = first_summary.week_key == current_summary.week_key

        if same_week:
            st.info(
                "You only have one recorded week so far "
                f"({first_summary.week_key}). Come back next week to see "
                "a real comparison."
            )

        first_score = first_summary.avg_health_score
        current_score = current_summary.avg_health_score

        col1, col2, col3 = st.columns(3)
        with col1:
            MetricCard.render(
                title=f"First Week ({first_summary.week_key})",
                value=f"{first_score:.1f} / 100" if first_score is not None else "N/A",
            )
        with col2:
            MetricCard.render(
                title=f"Current Week ({current_summary.week_key})",
                value=f"{current_score:.1f} / 100" if current_score is not None else "N/A",
            )
        with col3:
            if first_score is not None and current_score is not None:
                diff = round(current_score - first_score, 1)
                pct = round((diff / first_score) * 100, 1) if first_score != 0 else None
                delta_str = f"{diff:+.1f} pts" + (f" ({pct:+.1f}%)" if pct is not None else "")
                MetricCard.render(
                    title="Score Difference",
                    value=f"{diff:+.1f} pts",
                    delta=delta_str if pct is not None else None,
                )
            else:
                MetricCard.render(title="Score Difference", value="N/A")

        with st.expander("See averages behind this comparison"):
            rows = [
                ("Avg. Screen Time (min/day)", first_summary.avg_total_screen_min, current_summary.avg_total_screen_min),
                ("Avg. Sleep (hrs)", first_summary.avg_sleep_hours, current_summary.avg_sleep_hours),
                ("Avg. Focus (0-100)", first_summary.avg_focus_0_100, current_summary.avg_focus_0_100),
                ("Avg. Social Media (min/day)", first_summary.avg_social_min, current_summary.avg_social_min),
                ("Avg. Stress (0-10)", first_summary.avg_stress_0_10, current_summary.avg_stress_0_10),
            ]
            for label, old_val, new_val in rows:
                c1, c2, c3 = st.columns(3)
                c1.write(f"**{label}**")
                c2.write(f"First week: {old_val if old_val is not None else 'N/A'}")
                c3.write(f"Current week: {new_val if new_val is not None else 'N/A'}")
