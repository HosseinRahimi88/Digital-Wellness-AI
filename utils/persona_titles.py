"""
Persona Titles
-----------------
Six human-readable persona archetypes plus earned badges, derived from
a user's own real check-in values.

Relationship to services/ml/persona_service.py (important, don't confuse
the two): that service runs the trained, unsupervised KMeans model and
answers "which of 4 statistical clusters is this person nearest?". Its
own artifact metadata records a low silhouette score (~0.077), so it is
honest but statistically soft.

This module is a different, deliberately *transparent* layer: a small
set of documented rules over raw fields that produces a friendly title
("The Night Owl") and badges. It exists because the product wants a
recognisable identity for every user, and a rule the user can have
explained to them in one sentence is a better fit for that than a
cluster index they can't interrogate. Nothing here feeds the model,
and it never overrides the ML persona - both are shown, labelled for
what they are.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class PersonaTitle:
    key: str
    title: str
    tagline: str
    icon: str
    reason: str          # the specific, real numbers that earned it
    match_strength: float  # 0..1, how strongly the rule fired


@dataclass(slots=True)
class Badge:
    key: str
    label: str
    icon: str
    description: str


@dataclass(slots=True)
class PersonaIdentity:
    primary: Optional[PersonaTitle]
    alternates: list[PersonaTitle] = field(default_factory=list)
    badges: list[Badge] = field(default_factory=list)


def _num(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = data.get(key, default)
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


# Each archetype scores itself 0..1 from the user's own values. The
# highest scorer becomes the primary title; anything else above
# _ALTERNATE_THRESHOLD is offered as a secondary label, because real
# people are usually a blend rather than exactly one box.
_ALTERNATE_THRESHOLD = 0.45


def _score_night_owl(d: dict[str, Any]) -> tuple[float, str]:
    night_ratio = _num(d, "night_ratio")
    pre_sleep = _num(d, "pre_sleep_screen_min")
    score = min(1.0, night_ratio * 2.5 + min(pre_sleep / 120.0, 1.0) * 0.5)
    return score, f"{round(night_ratio * 100)}% of your screen time happens at night, plus {round(pre_sleep)} min right before sleep."


def _score_deep_worker(d: dict[str, Any]) -> tuple[float, str]:
    work_ratio = _num(d, "work_study_ratio")
    focus = _num(d, "focus_0_100") / 100.0
    frag = _num(d, "fragmentation_index_0_100") / 100.0
    score = min(1.0, work_ratio * 1.4 + focus * 0.5 - frag * 0.4)
    return max(0.0, score), f"{round(work_ratio * 100)}% of your screen time is work/study, with focus at {round(focus * 100)}/100."


def _score_social_connector(d: dict[str, Any]) -> tuple[float, str]:
    social_ratio = _num(d, "social_ratio")
    comparison = _num(d, "social_comparison_1_10") / 10.0
    score = min(1.0, social_ratio * 2.0 + comparison * 0.2)
    return score, f"Social apps are {round(social_ratio * 100)}% of your screen time."


def _score_scattered_checker(d: dict[str, Any]) -> tuple[float, str]:
    frag = _num(d, "fragmentation_index_0_100") / 100.0
    pickups = min(_num(d, "pickups_per_day") / 150.0, 1.0)
    notif = min(_num(d, "notification_density") / 30.0, 1.0)
    score = min(1.0, frag * 0.5 + pickups * 0.3 + notif * 0.2)
    return score, f"Fragmentation index {round(frag * 100)}/100 across {round(_num(d, 'pickups_per_day'))} pickups a day."


def _score_balanced_steward(d: dict[str, Any]) -> tuple[float, str]:
    sleep = _num(d, "sleep_hours")
    sleep_fit = max(0.0, 1.0 - abs(sleep - 8.0) / 4.0)
    activity = min(_num(d, "physical_activity_min_per_day") / 60.0, 1.0)
    stress = 1.0 - min(_num(d, "stress_0_10") / 10.0, 1.0)
    night = 1.0 - min(_num(d, "night_ratio") * 3.0, 1.0)
    score = min(1.0, (sleep_fit * 0.3 + activity * 0.25 + stress * 0.25 + night * 0.2))
    return score, f"{sleep:.1f}h sleep, {round(_num(d, 'physical_activity_min_per_day'))} min activity, stress {round(_num(d, 'stress_0_10'))}/10."


def _score_entertainment_seeker(d: dict[str, Any]) -> tuple[float, str]:
    video = _num(d, "video_min")
    gaming_ratio = _num(d, "gaming_ratio")
    total = max(_num(d, "total_screen_min", 1.0), 1.0)
    video_ratio = video / total
    score = min(1.0, video_ratio * 1.8 + gaming_ratio * 1.8)
    return score, f"Video and gaming make up {round((video_ratio + gaming_ratio) * 100)}% of your screen time."


_ARCHETYPES = [
    ("night_owl", "The Night Owl", "Your best ideas arrive after midnight — your sleep disagrees.", "🦉", _score_night_owl),
    ("deep_worker", "The Deep Worker", "Long, purposeful sessions. Screens are a tool, not a habit.", "🎯", _score_deep_worker),
    ("social_connector", "The Social Connector", "You stay close to people — and that keeps you on the feed.", "💬", _score_social_connector),
    ("scattered_checker", "The Scattered Checker", "Not long sessions, just constant ones. Attention pays the price.", "⚡", _score_scattered_checker),
    ("balanced_steward", "The Balanced Steward", "Sleep, movement and screens actually in proportion. Rare.", "🌿", _score_balanced_steward),
    ("entertainment_seeker", "The Unwinder", "Screens are how you decompress — the question is how much.", "🎮", _score_entertainment_seeker),
]


def _badges(user_data: dict[str, Any], history: Optional[list[dict[str, Any]]] = None) -> list[Badge]:
    """Badges earned strictly from real values - each one names the
    threshold it required, so nothing is unexplainable."""
    earned: list[Badge] = []
    history = history or []

    sleep = _num(user_data, "sleep_hours")
    if 7.0 <= sleep <= 9.0:
        earned.append(Badge("well_rested", "Well Rested", "😴", "Slept 7-9 hours on your latest check-in."))

    if _num(user_data, "physical_activity_min_per_day") >= 30:
        earned.append(Badge("mover", "On the Move", "🏃", "30+ minutes of physical activity logged."))

    if _num(user_data, "night_ratio") <= 0.05:
        earned.append(Badge("night_guard", "Night Guard", "🌙", "Almost no screen time in night hours."))

    if _num(user_data, "fragmentation_index_0_100") <= 25:
        earned.append(Badge("focused", "Unfragmented", "🧠", "Low usage-fragmentation index."))

    if _num(user_data, "stress_0_10") <= 3:
        earned.append(Badge("calm", "Low Stress", "🧘", "Self-reported stress at 3/10 or below."))

    if len(history) >= 7:
        earned.append(Badge("consistent", "Consistent Logger", "📅", "Seven or more check-ins recorded."))
    if len(history) >= 30:
        earned.append(Badge("dedicated", "Month of Data", "🏅", "Thirty or more check-ins recorded."))

    scores = [h.get("health_score") for h in history if h.get("health_score") is not None]
    if scores and max(scores) >= 85:
        earned.append(Badge("high_score", "Peak Week", "⭐", "Reached a wellness score of 85 or higher."))

    return earned


def resolve_identity(
    user_data: dict[str, Any],
    history: Optional[list[dict[str, Any]]] = None,
) -> PersonaIdentity:
    """
    Score every archetype against this user's real values and return the
    strongest as `primary`, any other strong match as an alternate, plus
    earned badges. Returns `primary=None` for an empty input rather than
    defaulting to an arbitrary archetype.
    """
    if not user_data:
        return PersonaIdentity(primary=None, alternates=[], badges=[])

    scored: list[PersonaTitle] = []
    for key, title, tagline, icon, scorer in _ARCHETYPES:
        strength, reason = scorer(user_data)
        scored.append(PersonaTitle(
            key=key, title=title, tagline=tagline, icon=icon,
            reason=reason, match_strength=round(max(0.0, min(1.0, strength)), 3),
        ))

    scored.sort(key=lambda p: p.match_strength, reverse=True)
    primary = scored[0]
    alternates = [p for p in scored[1:] if p.match_strength >= _ALTERNATE_THRESHOLD][:2]

    return PersonaIdentity(
        primary=primary,
        alternates=alternates,
        badges=_badges(user_data, history),
    )
