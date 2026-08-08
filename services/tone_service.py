"""
Tone Service
---------------
P1 item 20: three voices for the same advice.

Hard rule this module exists to enforce: tone changes *wording only*.
The recommendation set, its priority order, the success metric and the
safety note are produced by RecommendationService from real SHAP output
and are passed through untouched. Rephrasing must never soften a HIGH
priority into sounding optional, or turn a LOW one into an alarm - so
the priority label itself is never rewritten here.

Tones:
  gentle   - encouraging, low-pressure. Default.
  direct   - blunt and specific. Directness, never shaming (the product
             brief's explicit red line).
  clinical - neutral and factual, no second person cheerleading.
"""

from __future__ import annotations

from typing import Any, Optional

DEFAULT_TONE = "gentle"
SUPPORTED_TONES = ("gentle", "direct", "clinical")

# Lead-ins prepended to a recommendation's action line, by tone and by
# the recommendation's own (unmodified) priority.
_ACTION_LEAD_IN: dict[str, dict[str, str]] = {
    "gentle": {
        "HIGH": "When you're ready, the highest-leverage change is:",
        "MEDIUM": "Worth trying this week:",
        "LOW": "A small optional tweak:",
    },
    "direct": {
        "HIGH": "Start here. This is the one that matters most:",
        "MEDIUM": "Do this next:",
        "LOW": "Minor, but it helps:",
    },
    "clinical": {
        "HIGH": "Highest-impact intervention indicated:",
        "MEDIUM": "Secondary intervention:",
        "LOW": "Low-impact adjustment:",
    },
}

# How the overall result is framed, by tone and score band.
_RESULT_FRAMING: dict[str, dict[str, str]] = {
    "gentle": {
        "great": "This is a genuinely good result — whatever you're doing, it's working.",
        "good": "You're in a solid place. Small adjustments will keep you there.",
        "borderline": "You're right on the edge. A little attention now goes a long way.",
        "risk": "This one's low, and it's worth taking seriously — but every factor behind it is changeable.",
    },
    "direct": {
        "great": "Strong result. Keep the pattern.",
        "good": "Decent. Not much to fix, but don't drift.",
        "borderline": "Borderline. Act before this slides.",
        "risk": "This is a low score. The good news: the main drivers are all things you control.",
    },
    "clinical": {
        "great": "Score falls in the upper band. Current pattern is favourable.",
        "good": "Score falls in the healthy band with minor deviations.",
        "borderline": "Score falls near the classification boundary.",
        "risk": "Score falls in the lower band. Primary contributing factors are modifiable.",
    },
}


def normalize_tone(tone: Optional[str]) -> str:
    """Unknown/absent tone falls back to the documented default rather
    than raising - a bad stored preference should never block advice."""
    return tone if tone in SUPPORTED_TONES else DEFAULT_TONE


def band_for_score(score: Optional[float]) -> str:
    """Same thresholds the result ring and mascot already use - not a
    second opinion about what counts as a good score."""
    if score is None:
        return "borderline"
    if score >= 80:
        return "great"
    if score >= 66:
        return "good"
    if score >= 40:
        return "borderline"
    return "risk"


def frame_result(score: Optional[float], tone: Optional[str] = None) -> str:
    return _RESULT_FRAMING[normalize_tone(tone)][band_for_score(score)]


def lead_in_for(priority: str, tone: Optional[str] = None) -> str:
    table = _ACTION_LEAD_IN[normalize_tone(tone)]
    return table.get((priority or "").upper(), table["MEDIUM"])


def apply_tone(recommendations: list[Any], tone: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Return each recommendation as a plain dict with one ADDED field,
    `action_lead_in`. The original title/description/action/priority/
    success_metric/safety_note are copied verbatim - this function
    deliberately cannot alter them, so a tone preference can never
    change what the user is actually being advised to do.
    """
    resolved = normalize_tone(tone)
    out: list[dict[str, Any]] = []
    for rec in recommendations:
        data = rec.to_dict() if hasattr(rec, "to_dict") else dict(rec)
        data["action_lead_in"] = lead_in_for(data.get("priority", "MEDIUM"), resolved)
        out.append(data)
    return out
