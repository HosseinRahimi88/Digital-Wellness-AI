"""
Status Badge Component
"""

import streamlit as st


class StatusBadge:

    COLORS = {

        "Healthy": "🟢",

        "Moderate": "🟡",

        "At Risk": "🔴",

        "Unhealthy": "🔴",

        "Low": "🟢",

        "Medium": "🟠",

        "High": "🔴"
    }

    @classmethod
    def render(cls, status: str):

        icon = cls.COLORS.get(status, "⚪")

        st.markdown(
            f"## {icon} {status}"
        )