"""
utils/persona.py
-----------------
Lightweight, rule-based "persona" labeling used only by the Share Report
Card and Weekly History log.

This is intentionally NOT a machine-learning component - it does not
touch, retrain, wrap, or reinterpret any trained model. It is a small,
human-authored set of if/else rules layered on TOP OF the real model
outputs (the classifier's predicted class and the regressor's wellness
score) plus a few raw inputs already collected by the form. Its only job
is to give the shareable report card a friendlier, more personal label
(e.g. "Focused Achiever") alongside the actual Health Score / Health
Class, which remain the authoritative, model-produced numbers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def generate_persona(
    prediction: str,
    user_data: Optional[Dict[str, Any]] = None,
    regression_score: Optional[float] = None,
) -> str:
    """
    Return a short, friendly persona label derived from the real
    prediction class plus a few raw habit fields. Falls back to a
    generic label whenever the inputs needed for a more specific rule
    aren't available.
    """
    data = user_data or {}

    sleep_hours = data.get("sleep_hours")
    stress = data.get("stress_0_10")
    social_ratio = data.get("social_ratio")
    focus = data.get("focus_0_100")
    night_ratio = data.get("night_ratio")
    physical_activity = data.get("physical_activity_min_per_day")

    label = str(prediction or "").strip().lower()

    if label == "at risk":
        if night_ratio is not None and night_ratio >= 0.25:
            return "Night Owl Scroller"
        if stress is not None and stress >= 7:
            return "Overwhelmed Scroller"
        return "Digital Burnout Risk"

    if label == "moderate":
        if social_ratio is not None and social_ratio >= 0.5:
            return "Social Media Drifter"
        if sleep_hours is not None and sleep_hours < 6:
            return "Sleep-Deprived Multitasker"
        return "Balanced Explorer"

    if label == "healthy":
        if focus is not None and focus >= 80 and (physical_activity or 0) >= 45:
            return "Focused Achiever"
        if sleep_hours is not None and sleep_hours >= 7.5:
            return "Well-Rested Optimizer"
        return "Mindful Navigator"

    return "Digital Wellness Explorer"


def resolve_persona(
    prediction: str,
    user_data: Optional[Dict[str, Any]] = None,
    regression_score: Optional[float] = None,
    persona_service: Optional[Any] = None,
) -> tuple[str, Optional[Any]]:
    """
    Group C Feature 02 - Persona Detection.

    Prefer the real ML persona (services.persona_service.PersonaService,
    an unsupervised KMeans behavioral cluster - see models/train_persona.py)
    over the rule-based label above whenever it's available. Falls back to
    `generate_persona()` when the ML model hasn't been trained yet, the
    user's data is missing a required clustering feature, or any error
    occurs - this function must always return a usable label string, since
    every existing call site (history storage, share report card,
    session state) expects one.

    Returns
    -------
    (label, persona_result)
        `label` is always a non-empty string, safe to use anywhere the
        old `generate_persona()` string was used directly.
        `persona_result` is the full `PersonaResult` (with confidence,
        defining traits, runner-up persona) when the ML path succeeded,
        or `None` when the rule-based fallback was used - callers that
        want the richer detail (e.g. a UI card) should check for `None`.
    """
    fallback_label = generate_persona(prediction, user_data, regression_score)

    if persona_service is None or user_data is None:
        return fallback_label, None

    try:
        result = persona_service.assign(user_data)
    except Exception:
        logger.debug("PersonaService.assign() failed; falling back to the rule-based persona label.", exc_info=True)
        return fallback_label, None

    if not result.available or not result.persona_name:
        return fallback_label, None

    return result.persona_name, result
