"""
Weekly Heatmap Component
-------------------------
GitHub-contribution-style grid of colored squares showing the user's
recent daily wellness, built from real HistoryService entries
(themselves built from real PredictionService outputs). No mock data.
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

# Health Score thresholds (0-100 scale, same scale PredictionService's
# regression output already uses).
GOOD_THRESHOLD = 70.0
MEDIUM_THRESHOLD = 40.0

COLOR_GOOD = "#39d353"
COLOR_MEDIUM = "#f1c40f"
COLOR_POOR = "#e74c3c"
COLOR_EMPTY = "#ebedf0"


class WeeklyHeatmap:
    """
    Renders a responsive row of colored day-squares.
    """

    @staticmethod
    def _color_for_score(score: Optional[float]) -> str:
        if score is None:
            return COLOR_EMPTY
        if score >= GOOD_THRESHOLD:
            return COLOR_GOOD
        if score >= MEDIUM_THRESHOLD:
            return COLOR_MEDIUM
        return COLOR_POOR

    @staticmethod
    def render(days: list[dict[str, Any]], title: str = "📅 Weekly Wellness Heatmap") -> None:
        """
        `days` is the output of HistoryService.get_last_n_days(), i.e. a
        list of {"date", "day_of_week", "entry"} dicts (entry may be
        None for days with no recorded prediction).
        """
        if title:
            st.subheader(title)

        if not days:
            st.info("No history yet. Run a prediction to start building your heatmap.")
            return

        squares_html = []
        for day in days:
            entry = day.get("entry")
            score = entry.get("health_score") if entry else None
            health_class = entry.get("health_class") if entry else None
            color = WeeklyHeatmap._color_for_score(score)

            if entry is None:
                tooltip = f"{day['date']} ({day['day_of_week']}) - no data"
                label = ""
            else:
                score_str = f"{score:.0f}" if score is not None else "N/A"
                tooltip = f"{day['date']} ({day['day_of_week']}) - {health_class}, Score {score_str}"
                label = score_str

            square_style = (
                "width: 42px; height: 42px; border-radius: 8px; "
                f"background-color: {color}; display: flex; "
                "align-items: center; justify-content: center; "
                "font-size: 11px; font-weight: 700; "
                "color: rgba(0,0,0,0.55); flex: 1 1 42px;"
            )
            squares_html.append(
                f'<div title="{tooltip}" style="{square_style}">{label}</div>'
            )

        day_labels = "".join(
            f'<div style="flex:1 1 42px; text-align:center; font-size:11px; opacity:0.7;">{d["day_of_week"]}</div>'
            for d in days
        )

        heatmap_html = (
            f'<div style="display:flex; gap:6px; margin-bottom:4px;">{day_labels}</div>'
            f'<div style="display:flex; gap:6px; flex-wrap: wrap;">{"".join(squares_html)}</div>'
        )
        st.markdown(heatmap_html, unsafe_allow_html=True)

        legend_html = (
            '<div style="display:flex; align-items:center; gap:14px; margin-top:10px; '
            'font-size:12px; opacity:0.8;">'
            f'<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            f'background:{COLOR_GOOD};margin-right:4px;"></span>Good ({GOOD_THRESHOLD:.0f}+)</span>'
            f'<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            f'background:{COLOR_MEDIUM};margin-right:4px;"></span>Medium '
            f'({MEDIUM_THRESHOLD:.0f}-{GOOD_THRESHOLD-1:.0f})</span>'
            f'<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            f'background:{COLOR_POOR};margin-right:4px;"></span>Poor (&lt;{MEDIUM_THRESHOLD:.0f})</span>'
            f'<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            f'background:{COLOR_EMPTY};margin-right:4px;"></span>No data</span>'
            "</div>"
        )
        st.markdown(legend_html, unsafe_allow_html=True)
