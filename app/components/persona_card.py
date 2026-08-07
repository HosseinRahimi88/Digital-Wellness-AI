"""
Persona Card
------------
Renders Group C Feature 02 (Persona Detection): the ML-assigned
behavioral persona from `services/persona_service.py`, when available.
"""

from __future__ import annotations

import streamlit as st


class PersonaCard:

    @staticmethod
    def render(persona_result, fallback_label: str) -> None:
        """
        `persona_result` is a `services.persona_service.PersonaResult`
        or `None` (rule-based fallback was used - still show the label,
        just without the ML detail).
        """
        if persona_result is None or not persona_result.available:
            st.info(f"**Persona:** {fallback_label}")
            return

        with st.expander(f"Persona: {persona_result.persona_name}", expanded=False):
            st.write(persona_result.explanation)

            if persona_result.confidence is not None:
                st.progress(
                    persona_result.confidence,
                    text=f"Match confidence: {persona_result.confidence:.0%}",
                )

            if persona_result.defining_traits:
                st.markdown("**What defines this persona:**")
                for trait in persona_result.defining_traits:
                    direction_word = "higher" if trait["direction"] == "high" else "lower"
                    st.write(
                        f"- {trait['feature'].replace('_', ' ')}: "
                        f"{direction_word} than average"
                    )

            st.caption(
                "Derived from an unsupervised behavioral cluster model "
                "(KMeans), independent of the risk prediction above - "
                "this describes how you use your device day-to-day, not "
                "your predicted wellness trajectory."
            )
