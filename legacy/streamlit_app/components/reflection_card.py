"""
Reflection Card
----------------
Renders Group C Feature 42 (Reflection Loop): a self-rating + free-text
reflection form, the calibration analysis against real measured wellness
scores, and a data-grounded prompt for the next reflection.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.insight.reflection_service import ReflectionService


class ReflectionCard:

    @staticmethod
    def render(user_id: str, history_entries: list[dict]) -> None:
        service = ReflectionService(user_id=user_id)

        st.subheader("🔄 Reflection Loop")

        prompt = service.next_prompt(history_entries)
        st.write(f"*{prompt}*")

        today = date.today()
        existing = next((e for e in service.get_all() if e.get("date") == today.isoformat()), None)

        with st.form("reflection_form"):
            rating = st.slider(
                "How do you feel today went, honestly?",
                min_value=1, max_value=5,
                value=existing.get("self_rating", 3) if existing else 3,
                help="1 = rough day, 5 = great day",
            )
            text = st.text_area(
                "Anything you want to note?",
                value=existing.get("reflection_text", "") if existing else "",
            )
            submitted = st.form_submit_button("Save reflection")

        if submitted:
            service.record_reflection(rating, text, on_date=today)
            st.success("Reflection saved.")
            st.rerun()

        calibration = service.compute_calibration(history_entries)
        if calibration.available:
            st.markdown(f"**Calibration: {calibration.label}** (correlation: {calibration.correlation:+.2f})")
            st.caption(calibration.explanation)
        else:
            st.caption(calibration.explanation)
