"""
Opportunity Cost Card Component
-----------------------------------
Presentation for services/insight/opportunity_cost_service.py. Covers two
closely related Group A ideas in one card since they're the same
underlying number viewed two ways:
  - "Three Lost Days" - how much of the last week was screen time,
    expressed in full days.
  - "Opportunity Cost" - what that time projects to over a year, and
    a few concrete equivalents (books, workouts, movies).

All arithmetic lives in OpportunityCostService; this file only renders
it. Copy is deliberately framed as an estimate ("at this pace"), never
as a prediction/forecast - see that service's docstring.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.insight.opportunity_cost_service import OpportunityCostService
from components.metric_card import MetricCard


class OpportunityCostCard:

    @staticmethod
    def render(
        last_7_days_entries: list[dict[str, Any]],
        title: str = "⏳ Where Your Screen Time Goes",
    ) -> None:
        """
        `last_7_days_entries` should be the last-7-days window (e.g. the
        `entry` values from HistoryService.get_last_n_days(n=7), or any
        recent HistoryService entries) - used to compute a daily average
        that then gets projected forward.
        """
        entries = [d for d in last_7_days_entries if d]  # tolerate None placeholders

        if title:
            st.subheader(title)

        result = OpportunityCostService.compute(entries)

        if not result.has_data:
            st.info(
                "No screen-time data logged yet this week. Run a prediction "
                "to start tracking this."
            )
            return

        # ---- "Three Lost Days" framing -----------------------------
        st.markdown(
            f"""
            <div style="
                padding: 16px 20px;
                border-radius: 14px;
                background: linear-gradient(135deg, rgba(231,76,60,0.10), rgba(241,196,15,0.08));
                border: 1px solid rgba(0,0,0,0.06);
                margin-bottom: 14px;
            ">
                <p style="margin:0; font-weight:700; font-size:16px;">
                    📉 In the last {result.days_measured} logged day(s), you spent about
                    {result.lost_days_last_week:.2f} full day(s) on screens.
                </p>
                <p style="margin:6px 0 0 0; opacity:0.75; font-size:13px;">
                    Based on an average of {result.avg_daily_minutes:.0f} min/day.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---- Opportunity cost / yearly projection --------------------
        st.caption("If this pace continued for a full year, that's roughly:")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            MetricCard.render(title="Days/Year", value=f"{result.projected_days_lost_per_year:.0f}")
        with c2:
            MetricCard.render(title="Books You Could Read", value=f"{result.equivalent_books_per_year:.0f}")
        with c3:
            MetricCard.render(title="Workouts You Could Do", value=f"{result.equivalent_workouts_per_year:.0f}")
        with c4:
            MetricCard.render(title="Movies You Could Watch", value=f"{result.equivalent_movies_per_year:.0f}")

        st.caption(
            "These are rough, simple time-conversion estimates from your own logged "
            "screen time - not a prediction, and not a judgment. They're just meant "
            "to make the minutes feel more concrete."
        )
