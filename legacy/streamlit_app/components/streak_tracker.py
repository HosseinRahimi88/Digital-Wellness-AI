"""
Streak Tracker Component
----------------------------
Presentation for GamificationService.compute_streak() - shows the
user's current and longest "healthy day" streak. All streak logic
lives in services/social/gamification_service.py; this only renders it.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.social.gamification_service import GamificationService, StreakInfo


class StreakTracker:

    @staticmethod
    def render(
        entries: list[dict[str, Any]],
        title: str = "🔥 Healthy Streak",
        compact: bool = False,
    ) -> StreakInfo:
        info = GamificationService.compute_streak(entries)

        if compact:
            st.metric(
                label=title,
                value=f"{info.current_streak} day{'s' if info.current_streak != 1 else ''}",
                help=f"Longest streak so far: {info.longest_streak} day(s).",
            )
            return info

        if title:
            st.caption(title)

        if not entries:
            st.info("No history yet - your streak starts with your first check-in.")
            return info

        flame = "🔥" if info.current_streak > 0 else "💤"
        st.markdown(
            f"""
            <div style="display:flex; gap:18px; align-items:center;">
                <div style="font-size:34px;">{flame}</div>
                <div>
                    <div style="font-weight:700; font-size:20px;">{info.current_streak} day streak</div>
                    <div style="opacity:0.7; font-size:13px;">Longest so far: {info.longest_streak} day(s)</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if info.current_streak == 0:
            st.caption("A streak counts consecutive days with a healthy wellness score. Log a check-in to start one.")
        return info
