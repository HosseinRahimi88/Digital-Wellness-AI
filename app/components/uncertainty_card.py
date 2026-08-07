"""
Uncertainty Card
----------------
Renders Group C Feature 55 (Prediction Uncertainty): the split-conformal
regression interval and classification prediction set produced by
`services/uncertainty_service.py`.
"""

from __future__ import annotations

import streamlit as st

_LABEL_COLORS = {
    "Low": "#1e8e3e",
    "Moderate": "#e8a33d",
    "High": "#d64545",
}


class UncertaintyCard:

    @staticmethod
    def render(uncertainty) -> None:
        """
        `uncertainty` is a `services.uncertainty_service.UncertaintyResult`
        (or `None`/an unavailable result for older/degraded call paths -
        both are handled gracefully rather than assumed away).
        """
        if uncertainty is None or not getattr(uncertainty, "available", False):
            st.caption(
                "Uncertainty estimate unavailable for this prediction."
                if uncertainty is not None
                else ""
            )
            return

        color = _LABEL_COLORS.get(uncertainty.uncertainty_label, "#888888")

        with st.expander(
            f"Prediction Uncertainty: {uncertainty.uncertainty_label}",
            expanded=(uncertainty.uncertainty_label != "Low"),
        ):
            st.markdown(
                f"<span style='color:{color}; font-weight:600;'>"
                f"{uncertainty.uncertainty_label} uncertainty</span>",
                unsafe_allow_html=True,
            )
            st.write(uncertainty.explanation)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Wellness score range (90% interval)**")
                if uncertainty.regression_lower is not None:
                    st.write(
                        f"{uncertainty.regression_lower:.1f} - "
                        f"{uncertainty.regression_upper:.1f} / 100"
                    )
                else:
                    st.write("Not available.")

            with col2:
                st.markdown("**Plausible classes (90% coverage)**")
                if uncertainty.classification_set:
                    st.write(", ".join(uncertainty.classification_set))
                else:
                    st.write("Not available.")

            st.caption(
                "Calibrated with split conformal prediction on a held-out "
                f"validation set (n={uncertainty.calibration_sample_size}). "
                "This gives a statistically guaranteed coverage rate, not "
                "just the model's raw confidence score."
            )
