"""
Future Letter Card Component
--------------------------------
UI for writing a short note to your future self and revisiting it once
unlocked. All persistence/unlock-date logic lives in
services/identity/letter_service.py; this file only renders the form and lists.
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from services.identity.letter_service import LetterService


class FutureLetterCard:

    @staticmethod
    def render(
        letter_service: LetterService,
        current_score: float | None = None,
        title: str = "✉️ Letter to Future You",
    ) -> None:
        if title:
            st.subheader(title)

        st.caption(
            "Write a short note to your future self. It stays sealed until "
            "the date you pick, then shows up here."
        )

        with st.form("future_letter_form", clear_on_submit=True):
            content = st.text_area(
                "Your letter",
                placeholder="Dear future me...",
                max_chars=1000,
                key="future_letter_content",
            )
            unlock_in_days = st.slider(
                "Unlock in how many days?",
                min_value=1,
                max_value=365,
                value=30,
                key="future_letter_unlock_days",
            )
            submitted = st.form_submit_button("🔒 Seal Letter")

        if submitted:
            try:
                letter_service.write_letter(
                    content=content,
                    unlock_date=date.today() + timedelta(days=unlock_in_days),
                    context_score=current_score,
                )
                st.success("Letter sealed! Come back after the unlock date to read it.")
            except ValueError:
                st.warning("Write something before sealing your letter.")

        unlocked = letter_service.get_unlocked_letters()
        locked = letter_service.get_locked_letters()

        if unlocked:
            with st.expander(f"📬 Unlocked letters ({len(unlocked)})"):
                for letter in reversed(unlocked):
                    st.markdown(f"**Written on {letter.written_on}:**")
                    st.write(letter.content)
                    st.divider()

        if locked:
            st.caption(
                f"🔒 {len(locked)} letter(s) still sealed - the next one unlocks "
                f"{min(l.unlock_date for l in locked)}."
            )
