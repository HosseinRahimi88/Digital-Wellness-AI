"""
Badges Card Component
-------------------------
Presentation for GamificationService.compute_badges() - a grid of
achievement badges, unlocked ones shown in full color and locked ones
dimmed. All unlock rules live in services/gamification_service.py;
this only renders the result.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.gamification_service import GamificationService


class BadgesCard:

    @staticmethod
    def render(
        entries: list[dict[str, Any]],
        title: str = "🏅 Achievement Badges",
        columns: int = 4,
    ) -> None:
        if title:
            st.subheader(title)

        badges = GamificationService.compute_badges(entries)
        unlocked_count = sum(1 for b in badges if b.unlocked)
        st.caption(f"{unlocked_count}/{len(badges)} unlocked")

        cols = st.columns(columns)
        for i, badge in enumerate(badges):
            col = cols[i % columns]
            with col:
                opacity = "1.0" if badge.unlocked else "0.35"
                border = "rgba(56,142,60,0.4)" if badge.unlocked else "rgba(0,0,0,0.08)"
                st.markdown(
                    f"""
                    <div title="{badge.description}" style="
                        opacity:{opacity};
                        border:1px solid {border};
                        border-radius:12px;
                        padding:12px 8px;
                        text-align:center;
                        margin-bottom:10px;
                    ">
                        <div style="font-size:28px;">{badge.icon}</div>
                        <div style="font-size:12px; font-weight:600; margin-top:4px;">{badge.name}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
