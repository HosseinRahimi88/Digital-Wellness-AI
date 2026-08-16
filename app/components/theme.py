"""
Application Theme
"""

import streamlit as st


class Theme:
    """
    Global application theme.
    """

    @staticmethod
    def load():
        st.markdown(
            """
            <style>

            .main {
                padding-top: 1rem;
            }

            .stButton > button {
                width: 100%;
                border-radius: 10px;
                font-weight: 600;
            }

            .stMetric {
                border-radius: 10px;
                padding: 10px;
            }

            div[data-testid="stMetric"] {
                border: 1px solid #e6e6e6;
                border-radius: 12px;
                padding: 12px;
            }

            </style>
            """,
            unsafe_allow_html=True,
        )