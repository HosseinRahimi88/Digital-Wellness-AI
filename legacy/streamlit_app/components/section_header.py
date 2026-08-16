"""
Reusable Section Header
"""

import streamlit as st


class SectionHeader:

    @staticmethod
    def render(title: str):

        st.markdown("---")

        st.header(title)