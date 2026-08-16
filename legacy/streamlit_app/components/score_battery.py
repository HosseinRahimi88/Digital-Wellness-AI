"""
Score Battery Component
--------------------------
Renders a wellness score (0-100, the same scale
services/ml/prediction_service.py's regression output already uses) as a
battery-fill graphic. Presentation only - takes a plain float, does no
scoring/prediction itself.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

GOOD_THRESHOLD = 70.0
MEDIUM_THRESHOLD = 40.0

COLOR_GOOD = "#39d353"
COLOR_MEDIUM = "#f1c40f"
COLOR_POOR = "#e74c3c"
COLOR_EMPTY = "#ebedf0"


class ScoreBattery:

    @staticmethod
    def _color_for_score(score: float) -> str:
        if score >= GOOD_THRESHOLD:
            return COLOR_GOOD
        if score >= MEDIUM_THRESHOLD:
            return COLOR_MEDIUM
        return COLOR_POOR

    @classmethod
    def render(
        cls,
        score: Optional[float],
        title: str = "🔋 Wellness Battery",
    ) -> None:
        if title:
            st.caption(title)

        if score is None:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:8px;">
                    <div style="width:120px; height:46px; border:3px solid #ccc;
                                border-radius:8px; position:relative; background:{COLOR_EMPTY};">
                    </div>
                    <div style="width:6px; height:20px; background:#ccc; border-radius:0 3px 3px 0;"></div>
                </div>
                <p style="margin:6px 0 0 0; opacity:0.7; font-size:13px;">No score yet</p>
                """,
                unsafe_allow_html=True,
            )
            return

        pct = max(0.0, min(100.0, score))
        color = cls._color_for_score(pct)

        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:120px; height:46px; border:3px solid #444;
                            border-radius:8px; position:relative; background:{COLOR_EMPTY}; overflow:hidden;">
                    <div style="position:absolute; left:0; top:0; bottom:0; width:{pct:.0f}%;
                                background:{color}; transition: width 0.4s ease;"></div>
                    <div style="position:absolute; inset:0; display:flex; align-items:center;
                                justify-content:center; font-weight:700; font-size:14px;
                                color:rgba(0,0,0,0.75);">{pct:.0f}%</div>
                </div>
                <div style="width:6px; height:20px; background:#444; border-radius:0 3px 3px 0;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
