"""
Achievement Celebration Component
------------------------------------
Shows a small celebratory animation + message whenever the user's real
recorded wellness score has meaningfully improved, using
services.achievement_service.AchievementService. Presentation only -
the comparison logic lives in the service.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from services.achievement_service import Achievement, AchievementService


class AchievementCelebration:

    @staticmethod
    def render_from_scores(
        current_score: Optional[float],
        previous_score: Optional[float],
        context_label: str = "this week",
        animation: str = "balloons",
    ) -> Achievement:
        """
        Evaluate + render in one call. Returns the Achievement so callers
        can branch further if they want.
        """
        achievement = AchievementService.evaluate(
            current_score=current_score,
            previous_score=previous_score,
            context_label=context_label,
        )
        AchievementCelebration.render(achievement, animation=animation)
        return achievement

    @staticmethod
    def render(achievement: Achievement, animation: str = "balloons") -> None:
        if not achievement.unlocked:
            return

        st.markdown(
            f"""
            <div style="
                padding: 16px 20px;
                border-radius: 14px;
                background: linear-gradient(135deg, rgba(255,193,7,0.18), rgba(56,142,60,0.14));
                border: 1px solid rgba(0,0,0,0.06);
                margin: 10px 0;
                font-weight: 600;
            ">
                🎉 {achievement.message}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Only fire the animation once per achievement per session so it
        # doesn't replay on every unrelated widget rerun.
        seen_key = f"achievement_seen::{achievement.message}"
        if not st.session_state.get(seen_key):
            st.session_state[seen_key] = True
            if animation == "snow":
                st.snow()
            else:
                st.balloons()
