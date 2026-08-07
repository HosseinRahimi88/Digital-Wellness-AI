"""
What-if Simulator Component
-----------------------------
Lets the user tweak a handful of habit inputs and see a LIVE predicted
Health Score / Health Class, computed by calling the real, unmodified
PredictionService on a hypothetical copy of their data.

This is a simulator only:
- It never writes to st.session_state["last_prediction_result"] /
  ["last_user_data"] (the real stored prediction Analytics/AI_Coach
  read).
- It never calls HistoryService.record(), so simulated numbers are
  never written to the weekly history/heatmap.
- Derived features are recomputed with utils.feature_derivation.derive_features
  - the exact same formulas FormGenerator uses - so the simulated
  input is a valid, consistent feature vector instead of a
  hand-edited one that could confuse the model or leak inconsistent
  data.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from utils.feature_derivation import derive_features
from components.metric_card import MetricCard
from components.status_badge import StatusBadge


class WhatIfSimulator:

    # (field, label, min, max, step)
    #
    # Public (not `_SLIDERS`) since app/pages/What_If_Simulator.py's
    # Advanced Simulation section (Sensitivity Analysis, Multi-Scenario
    # Comparison, Goal-Seek) reuses this exact same slider set rather
    # than defining its own - one place decides which raw fields are
    # user-adjustable and their real ranges.
    SLIDERS = [
        ("social_min", "Social Media Time (min/day)", 0.0, 600.0, 5.0),
        ("gaming_min", "Gaming Time (min/day)", 0.0, 600.0, 5.0),
        ("work_study_min", "Work/Study Screen Time (min/day)", 0.0, 600.0, 5.0),
        ("video_min", "Video/Entertainment Time (min/day)", 0.0, 600.0, 5.0),
        ("sleep_hours", "Sleep Duration (hrs)", 0.0, 12.0, 0.5),
        ("sleep_quality_1_10", "Sleep Quality (1-10)", 1.0, 10.0, 0.5),
        ("stress_0_10", "Stress Level (0-10)", 0.0, 10.0, 0.5),
        ("physical_activity_min_per_day", "Physical Activity (min/day)", 0.0, 180.0, 5.0),
        ("notifications_per_day", "Notifications / Day", 0.0, 500.0, 5.0),
        ("pickups_per_day", "Phone Pickups / Day", 0.0, 200.0, 5.0),
    ]
    _SLIDERS = SLIDERS  # backward-compatible alias for any existing internal references

    @staticmethod
    def _build_simulated_input(
        base_user_data: Dict[str, Any],
        overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        candidate = dict(base_user_data)
        candidate.update(overrides)
        # Recompute every derived/ratio/density field from the edited raw
        # inputs, using the SAME formulas the real form uses, so the
        # model receives a consistent, non-leaky feature vector.
        return derive_features(candidate)

    @classmethod
    def render(
        cls,
        base_user_data: Dict[str, Any],
        predictor: Any,
        real_result: Optional[Any] = None,
    ) -> None:
        st.caption(
            "🧪 **Simulation only** - adjust the sliders below to see how "
            "your predicted Health Score/Class *would* change. This never "
            "overwrites your real stored prediction or your weekly history."
        )

        overrides: Dict[str, Any] = {}
        cols = st.columns(2)
        for i, (field, label, lo, hi, step) in enumerate(cls._SLIDERS):
            default = base_user_data.get(field, lo)
            try:
                default = float(default)
            except (TypeError, ValueError):
                default = lo
            default = min(max(default, lo), hi)

            with cols[i % 2]:
                overrides[field] = st.slider(
                    label, min_value=lo, max_value=hi, value=default,
                    step=step, key=f"whatif_{field}",
                )

        simulated_input = cls._build_simulated_input(base_user_data, overrides)

        try:
            with st.spinner("Simulating..."):
                simulated_result = predictor.predict(simulated_input)
        except Exception as e:
            st.error(f"Simulation failed: {e}")
            return

        st.divider()
        st.subheader("🔮 Simulated Outcome")

        col1, col2, col3 = st.columns(3)
        with col1:
            StatusBadge.render(simulated_result.prediction)
        with col2:
            score = simulated_result.regression_score
            delta = None
            if real_result is not None and getattr(real_result, "regression_score", None) is not None and score is not None:
                delta = round(score - real_result.regression_score, 1)
            MetricCard.render(
                title="Simulated Health Score",
                value=f"{score:.1f} / 100" if score is not None else "N/A",
                delta=f"{delta:+.1f} vs. your real prediction" if delta is not None else None,
            )
        with col3:
            confidence = (
                f"{simulated_result.confidence:.1%}"
                if simulated_result.confidence is not None else "N/A"
            )
            MetricCard.render(title="Simulated Confidence", value=confidence)

        st.caption(
            "This simulated result is not saved anywhere - run a real "
            "prediction on the Prediction page to record it in your history."
        )
