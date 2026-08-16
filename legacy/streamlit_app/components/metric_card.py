"""
Metric Card Component
"""

import streamlit as st


class MetricCard:
    """
    Reusable metric card.
    """

    @staticmethod
    def render(
        title: str,
        value,
        delta=None,
        help_text: str | None = None,
    ):

        st.metric(
            label=title,
            value=value,
            delta=delta,
            help=help_text,
        )