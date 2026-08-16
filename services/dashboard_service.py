"""
Dashboard Service
-------------------
Small business-rule helper for app/pages/Dashboard.py's "What's Driving
Your Score" section: given this session's ranked SHAP features, split
them into "strengths" (pushing the wellness score up) and "areas to
improve" (pulling it down), each capped to a display limit.

This was previously two inline list-comprehensions + slicing directly
in the page. Moving it here means the rule ("direction == 'increase' is
a strength") lives in one place instead of the page, matching the same
`direction` semantics services/prediction_service.py's SHAP output
already defines - no change in behavior, just where the rule lives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from config.dashboard_settings import MAX_SHAP_HIGHLIGHTS


@dataclass(slots=True)
class ShapHighlights:
    strengths: list[Any]
    areas_to_improve: list[Any]


class DashboardService:
    """Pure data-shaping helpers for the Dashboard page. No Streamlit/UI code."""

    @staticmethod
    def split_shap_by_direction(
        shap_features: Optional[list[Any]],
        limit: int = MAX_SHAP_HIGHLIGHTS,
    ) -> ShapHighlights:
        """
        Split `shap_features` (PredictionService's ranked SHAP output) into
        strengths (direction == "increase") and areas to improve
        (direction == "decrease"), each truncated to `limit` items.
        Returns empty lists if `shap_features` is falsy.
        """
        if not shap_features:
            return ShapHighlights(strengths=[], areas_to_improve=[])

        strengths = [f for f in shap_features if getattr(f, "direction", None) == "increase"]
        areas = [f for f in shap_features if getattr(f, "direction", None) == "decrease"]

        return ShapHighlights(
            strengths=strengths[:limit],
            areas_to_improve=areas[:limit],
        )
