"""
core/dto.py

Data Transfer Objects used across the project.
"""

from dataclasses import dataclass, field
from typing import Dict, Any

# -------------------------------------------------------
# Prediction Result
# -------------------------------------------------------

@dataclass(slots=True)
class PredictionResult:
    """
    Standard prediction output returned by all classifiers.
    """

    prediction: str

    confidence: float

    probabilities: Dict[str, float]

    model_name: str

    prediction_time_ms: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)


# -------------------------------------------------------
# Recommendation Result
# -------------------------------------------------------

@dataclass(slots=True)
class RecommendationResult:

    title: str

    description: str

    priority: str

    category: str


# -------------------------------------------------------
# Health Report
# -------------------------------------------------------

@dataclass(slots=True)
class HealthReport:

    status: str

    health_score: float

    risk_level: str

    recommendations: list[RecommendationResult]





@dataclass(slots=True)
class Recommendation:
    """
    Represents a personalized recommendation.
    """

    title: str

    description: str

    priority: str