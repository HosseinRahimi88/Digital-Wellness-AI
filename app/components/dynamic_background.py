"""
Dynamic Background Component
--------------------------------
Applies a subtle full-page background gradient tint based on the
user's latest wellness score/class. Purely presentational CSS, applied
*in addition to* app/components/theme.py's Theme.load() (never
modifies that file) - so pages that don't opt into this keep the exact
same look they always had.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

GOOD_THRESHOLD = 70.0
MEDIUM_THRESHOLD = 40.0

_GRADIENTS = {
    "good": "linear-gradient(180deg, rgba(57,211,83,0.06) 0%, rgba(255,255,255,0) 320px)",
    "medium": "linear-gradient(180deg, rgba(241,196,15,0.07) 0%, rgba(255,255,255,0) 320px)",
    "poor": "linear-gradient(180deg, rgba(231,76,60,0.06) 0%, rgba(255,255,255,0) 320px)",
    "neutral": "linear-gradient(180deg, rgba(25,118,210,0.05) 0%, rgba(255,255,255,0) 320px)",
}


class DynamicBackground:

    @staticmethod
    def _band_for_score(score: Optional[float]) -> str:
        if score is None:
            return "neutral"
        if score >= GOOD_THRESHOLD:
            return "good"
        if score >= MEDIUM_THRESHOLD:
            return "medium"
        return "poor"

    @classmethod
    def apply(cls, score: Optional[float]) -> None:
        band = cls._band_for_score(score)
        gradient = _GRADIENTS[band]
        st.markdown(
            f"""
            <style>
            [data-testid="stAppViewContainer"] > .main {{
                background-image: {gradient};
                background-repeat: no-repeat;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
