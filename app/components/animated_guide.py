"""
Animated Guide Component
----------------------------
A small, dismissible onboarding-style walkthrough - a pulsing card that
steps through a few short tips for the current page. Pure CSS
animation (no JS framework, no new dependency), shown once per page
per session via st.session_state, matching the same
"seen_key"-in-session_state pattern
app/components/achievement_celebration.py already uses to avoid
replaying itself on every rerun.
"""

from __future__ import annotations

import streamlit as st


class AnimatedGuide:

    @staticmethod
    def render(
        steps: list[str],
        guide_id: str,
        title: str = "👋 Quick Tour",
    ) -> None:
        """
        `steps` is a short list of one-line tips. `guide_id` must be
        unique per page/context so dismissing one guide doesn't hide a
        different one.
        """
        if not steps:
            return

        dismissed_key = f"animated_guide_dismissed::{guide_id}"
        step_key = f"animated_guide_step::{guide_id}"

        if st.session_state.get(dismissed_key):
            return

        current_step = st.session_state.get(step_key, 0)
        current_step = max(0, min(current_step, len(steps) - 1))
        tip = steps[current_step]

        st.markdown(
            """
            <style>
            @keyframes guidePulse {
                0% { box-shadow: 0 0 0 0 rgba(25,118,210,0.25); }
                70% { box-shadow: 0 0 0 10px rgba(25,118,210,0); }
                100% { box-shadow: 0 0 0 0 rgba(25,118,210,0); }
            }
            .animated-guide-card {
                animation: guidePulse 2.2s infinite;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="animated-guide-card" style="
                padding: 14px 18px;
                border-radius: 12px;
                background: rgba(25,118,210,0.06);
                border: 1px solid rgba(25,118,210,0.2);
                margin-bottom: 8px;
            ">
                <p style="margin:0; font-weight:700;">{title} ({current_step + 1}/{len(steps)})</p>
                <p style="margin:6px 0 0 0;">{tip}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            if current_step < len(steps) - 1:
                if st.button("Next tip →", key=f"{guide_id}_next"):
                    st.session_state[step_key] = current_step + 1
                    st.rerun()
            else:
                if st.button("Got it", key=f"{guide_id}_done"):
                    st.session_state[dismissed_key] = True
                    st.rerun()
        with col2:
            if st.button("Skip tour", key=f"{guide_id}_skip"):
                st.session_state[dismissed_key] = True
                st.rerun()
