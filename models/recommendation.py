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
    # (see services/wellness/recommendation_service.py) - lets the frontend show
    # the user's own actual submitted value next to the advice, instead
    # of leaving the connection between "why" and "what to do" implicit.
    source_field: str = ""

    # C-2. The user's own logged value for `source_field`, and the target
    # the rule's fixed formula produces from it. Both Optional because a
    # feature can be absent from the submitted day, in which case the
    # wording falls back to the generic form rather than showing a
    # sentence with a hole in it.
    observed_value: float | None = None

    target_value: float | None = None

    # {part: {lang: text}} for title/description/action/success_metric,
    # already filled with the two numbers above. Rendered by both the web
    # client and the PDF, so there is exactly one copy of this text.
    text_i18n: dict = None  # type: ignore[assignment]

    # {lang: text} each - `priority` and `safety_note` are shared across
    # rules (three fixed safety notes, three priority levels) rather than
    # per-rule text like the fields text_i18n covers, so they get their
    # own small tables in config/recommendation_i18n.py instead of a
    # RULE_TEXT entry each.
    priority_i18n: dict = None  # type: ignore[assignment]

    safety_note_i18n: dict = None  # type: ignore[assignment]

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

            "observed_value": self.observed_value,

            "target_value": self.target_value,

            "text_i18n": self.text_i18n or {},

            "priority_i18n": self.priority_i18n or {},

            "safety_note_i18n": self.safety_note_i18n or {},

        }