"""
Recommendation Card Component
-----------------------------
Streamlit component for displaying recommendations.
"""

from __future__ import annotations

import streamlit as st
from typing import Union, Optional

try:
    from models.recommendation import Recommendation
except ImportError:
    Recommendation = None


class RecommendationCard:
    """
    Render recommendation cards.
    """

    @staticmethod
    def render(
        icon_or_rec: Union[str, Recommendation],
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "General",
        priority: str = "MEDIUM",
        action: str = "Follow this guideline to improve your wellness.",
        success_metric: str = "",
        safety_note: str = "",
    ) -> None:
        """
        Render a single recommendation card.
        Supports both direct string arguments and Recommendation objects.
        """
        if hasattr(icon_or_rec, "priority"):
            rec = icon_or_rec
            icon = getattr(rec, "icon", "💡")
            title = getattr(rec, "title", "Recommendation")
            description = getattr(rec, "description", "")
            category = getattr(rec, "category", "General")
            priority = getattr(rec, "priority", "MEDIUM")
            action = getattr(rec, "action", "Follow guidelines")
            success_metric = getattr(rec, "success_metric", "")
            safety_note = getattr(rec, "safety_note", "")
        else:
            icon = str(icon_or_rec)
            title = title or "Recommendation"
            description = description or ""

        p_upper = str(priority).upper()
        if p_upper == "HIGH":
            border = "#d32f2f"
            bg_color = "rgba(211, 47, 47, 0.08)"
        elif p_upper == "MEDIUM":
            border = "#f9a825"
            bg_color = "rgba(249, 168, 37, 0.08)"
        else:
            border = "#388e3c"
            bg_color = "rgba(56, 142, 60, 0.08)"

        st.markdown(
            f"""
            <div style="
                padding: 18px;
                margin-bottom: 16px;
                border-left: 6px solid {border};
                border-radius: 12px;
                background-color: {bg_color};
                box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            ">
                <h4 style="margin-top:0; margin-bottom:8px;">
                    {icon} {title}
                </h4>
                <p style="margin-bottom:8px; opacity: 0.9;">
                    {description}
                </p>
                <div style="font-size: 0.9em; opacity: 0.8;">
                    <span><b>Category:</b> {category}</span> &nbsp;|&nbsp; 
                    <span><b>Priority:</b> {priority}</span>
                </div>
                <hr style="margin-top:12px; margin-bottom:12px; opacity: 0.2;">
                <b>Recommended Action:</b>
                <p style="margin-top:4px; margin-bottom:0; opacity: 0.9;">
                    {action}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if success_metric or safety_note:
            with st.expander("Success metric & safety"):
                if success_metric:
                    st.write(f"**Success metric:** {success_metric}")
                if safety_note:
                    st.warning(safety_note)

    @staticmethod
    def render_many(
        recommendations: list[Recommendation],
    ) -> None:
        """
        Render multiple recommendations.
        """
        if not recommendations:
            st.success("🎉 No recommendations needed. Your digital wellness looks excellent!")
            return

        for recommendation in recommendations:
            RecommendationCard.render(recommendation)