"""
Sparkline Component
----------------------
Small, axis-free trend line for a numeric field across real
HistoryService entries. Uses plotly (already an app dependency - see
app/components/probability_chart.py for prior plotly usage in this
codebase) rather than a new charting library.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


class Sparkline:

    @staticmethod
    def render(
        entries: list[dict[str, Any]],
        field_name: str = "health_score",
        title: str = "Score Trend",
        height: int = 120,
        line_color: str = "#1976d2",
    ) -> None:
        """
        `entries` should be sorted ascending by date (as
        HistoryService.get_all() already returns). Points with a missing
        `field_name` are skipped rather than plotted as zero.
        """
        points = [
            (e.get("date"), e[field_name])
            for e in entries
            if e.get(field_name) is not None
        ]

        if title:
            st.caption(title)

        if len(points) < 2:
            st.info("Not enough logged days yet for a trend line.")
            return

        df = pd.DataFrame({"date": [p[0] for p in points], "value": [p[1] for p in points]})

        fig = px.line(df, x="date", y="value", markers=True)
        fig.update_traces(line=dict(color=line_color, width=2), marker=dict(size=4))
        fig.update_xaxes(type="category")
        fig.update_layout(
            height=height,
            margin=dict(l=0, r=0, t=4, b=0),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
