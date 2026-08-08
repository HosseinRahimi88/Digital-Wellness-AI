"""
Recommendation Schema
---------------------
Data models for digital wellness recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Recommendation:
    """
    Represents a single recommendation.
    """

    title: str

    description: str

    category: str

    priority: str

    icon: str = "💡"

    action: str = ""

    # Ported concept from the Parisa project's per-recommendation
    # success metric and safety note - see
    # config/recommendation_registry.py::RecommendationTemplate for
    # where the real content lives. Defaulted so any existing code
    # constructing a Recommendation without them still works.
    success_metric: str = ""

    safety_note: str = ""

    # The real SHAP feature name this recommendation was generated from
    # (see services/recommendation_service.py) - lets the frontend show
    # the user's own actual submitted value next to the advice, instead
    # of leaving the connection between "why" and "what to do" implicit.
    source_field: str = ""

    # -------------------------------------------------

    @property
    def is_high_priority(self) -> bool:

        return self.priority.upper() == "HIGH"

    # -------------------------------------------------

    @property
    def is_medium_priority(self) -> bool:

        return self.priority.upper() == "MEDIUM"

    # -------------------------------------------------

    @property
    def is_low_priority(self) -> bool:

        return self.priority.upper() == "LOW"

    # -------------------------------------------------

    def to_dict(self) -> dict:

        return {

            "title": self.title,

            "description": self.description,

            "category": self.category,

            "priority": self.priority,

            "icon": self.icon,

            "action": self.action,

            "success_metric": self.success_metric,

            "safety_note": self.safety_note,

            "source_field": self.source_field,

        }