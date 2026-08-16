"""
Project Schemas
---------------
Common data models used across the application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# =========================================================
# Prediction Result
# =========================================================

@dataclass(slots=True)
class PredictionResult:
    """
    Output returned by PredictionService.
    """

    prediction: str

    confidence: Optional[float] = None

    probabilities: dict[str, float] = field(
        default_factory=dict
    )

    regression_score: Optional[float] = None

    shap_features: list[Any] = field(
        default_factory=list
    )

    model_name: str = ""

    prediction_time_ms: float = 0.0

    timestamp: Optional[str] = None

    # Group C Feature 55 - Prediction Uncertainty. Optional and additive:
    # any existing caller that only reads the fields above continues to
    # work unchanged (default is a not-available result, never None, so
    # `result.uncertainty.to_dict()` is always safe to call).
    uncertainty: Optional[Any] = None

    # -----------------------------------------------------

    @property
    def risk_level(self) -> str:
        """
        Alias for prediction label.
        """
        return self.prediction

    # -----------------------------------------------------

    @property
    def confidence_percent(self) -> float:
        """
        Confidence expressed as percentage.
        """
        if self.confidence is None:
            return 0.0

        return round(
            self.confidence * 100,
            2,
        )

    # -----------------------------------------------------

    @property
    def sorted_probabilities(
        self,
    ) -> dict[str, float]:
        """
        Return probabilities sorted descending.
        """
        return dict(
            sorted(
                self.probabilities.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )

    # -----------------------------------------------------

    def to_dict(self) -> dict:
        """
        Convert object into dictionary.
        """
        return {
            "prediction": self.prediction,
            "confidence": self.confidence,
            "confidence_percent": self.confidence_percent,
            "probabilities": self.probabilities,
            "regression_score": self.regression_score,
            "model_name": self.model_name,
            "prediction_time_ms": self.prediction_time_ms,
            "timestamp": self.timestamp,
            "uncertainty": self.uncertainty.to_dict() if self.uncertainty is not None else None,
        }