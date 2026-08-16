"""
Level Progress Component
----------------------------
Presentation for GamificationService.compute_level() - shows the
user's level (derived purely from total check-in count) as a titled
progress bar. All leveling logic lives in
services/gamification_service.py; this only renders it.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.gamification_service import GamificationService, LevelInfo


class LevelProgress:

    @staticmethod
    def render(
        entries: list[dict[str, Any]],
        title: str = "🎮 Your Level",
    ) -> LevelInfo:
        info = GamificationService.compute_level(entries)

        if title:
            st.caption(title)

        st.markdown(f"**Level {info.level} · {info.title}**")
        st.progress(
            info.progress_fraction,
            text=f"{info.checkins_into_level}/{info.checkins_for_next_level} check-ins to next level",
        )
        st.caption(f"Total check-ins logged: {info.total_checkins}")
        return info
