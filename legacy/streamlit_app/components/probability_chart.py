"""
Probability Chart Component
"""

import plotly.express as px
import pandas as pd
import streamlit as st


class ProbabilityChart:
    """
    Renders the per-class probability bar chart.

    `probabilities` is already keyed by the final human-readable class
    labels ("At Risk" / "Healthy" / "Moderate") - PredictionService
    resolves those via its own CLASS_MAPPING before this component ever
    sees the data, so no second remapping is needed here.
    """

    @staticmethod
    def render(probabilities: dict):
        if not probabilities:
            return

        df = pd.DataFrame({
            "Class": [str(c) for c in probabilities.keys()],
            "Probability": list(probabilities.values())
        })

        # ساخت متن درصد برای روی میله‌ها
        df["Percentage"] = df["Probability"].apply(lambda x: f"{x * 100:.1f}%")

        fig = px.bar(
            df,
            x="Class",
            y="Probability",
            text="Percentage",
            color="Probability",
            color_continuous_scale="Viridis",
            labels={"Probability": "Probability", "Class": "Wellness Status"}
        )

        fig.update_traces(textposition='outside')

        # اجبار Plotly به نمایش محور X به صورت متنی (Categorical)
        fig.update_xaxes(type='category')

        fig.update_layout(
            title="Prediction Probabilities",
            yaxis_range=[0, 1.15],
            showlegend=False,
            height=380,
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )