"""
Improvement Plan Service
--------------------------
Generates a realistic, rule-based 7-day digital wellness improvement
plan from the user's most recent REAL prediction outputs:
    - predicted health class (PredictionService.CLASS_MAPPING label)
    - wellness score (PredictionService regression output, 0-100)
    - persona (utils.persona.generate_persona)
    - the raw/derived habit fields the user actually submitted

This is intentionally rule-based only - no LLM calls, no model
inference, no retraining. It is pure presentation logic layered on top
of outputs the ML pipeline already produced, exactly like
RecommendationService/StoryCard do for their features. It never
modifies user_data, never calls PredictionService, and never touches
anything under models/ or artifacts/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class DailyPlan:
    """One day of the 7-day plan."""

    day_number: int
    day_label: str
    theme: str
    icon: str
    tasks: List[str] = field(default_factory=list)
    tip: str = ""


@dataclass(slots=True)
class ImprovementPlan:
    """The full 7-day plan plus a short intro tailored to the user."""

    intro: str
    focus_areas: List[str]
    days: List[DailyPlan] = field(default_factory=list)


class ImprovementPlanService:
    """
    Builds a 7-day, rule-based improvement schedule.

    The plan is assembled from a small library of daily "themes" (sleep,
    screen boundaries, movement, mindful notifications, social balance,
    focus/deep work, reflection). Which themes get emphasized - and how
    assertive the language is - depends only on simple, transparent
    if/else rules over the real health class / wellness score / raw
    habit fields already collected. No black box, no LLM.
    """

    # Habit field -> (theme key, "needs work" test, icon, task templates)
    _HABIT_RULES = [
        {
            "field": "sleep_hours",
            "theme": "Sleep Recovery",
            "icon": "😴",
            "needs_work": lambda v: v is not None and v < 7,
            "tasks": [
                "Set a fixed bedtime and wake-up time, even on weekends.",
                "Stop screens 30-60 minutes before bed; read or stretch instead.",
                "Keep your phone charging outside the bedroom tonight.",
            ],
            "tip": "Small, consistent sleep gains compound fast - aim for +15-30 min a night rather than a big jump.",
        },
        {
            "field": "social_min",
            "theme": "Social Media Boundaries",
            "icon": "📵",
            "needs_work": lambda v: v is not None and v > 90,
            "tasks": [
                "Turn off non-essential notifications for social apps.",
                "Set a daily app timer and let it actually interrupt you.",
                "Replace one scrolling session with a call or a walk.",
            ],
            "tip": "You don't need to quit social media - just add a little friction before you open it.",
        },
        {
            "field": "stress_0_10",
            "theme": "Stress Reset",
            "icon": "🧘",
            "needs_work": lambda v: v is not None and v >= 6,
            "tasks": [
                "Do a 5-minute breathing or grounding exercise this morning.",
                "Take three screen-free breaks today, even 2 minutes each.",
                "Write down one thing that's weighing on you and one small next step.",
            ],
            "tip": "Short, frequent resets beat one long break - they interrupt the stress build-up earlier.",
        },
        {
            "field": "physical_activity_min_per_day",
            "theme": "Movement",
            "icon": "🏃",
            "needs_work": lambda v: v is None or v < 30,
            "tasks": [
                "Take a 10-15 minute walk, ideally without your phone.",
                "Stand up and move for 2 minutes every hour you're at a screen.",
                "Try one new form of movement today (stretching, stairs, a short workout).",
            ],
            "tip": "Movement is one of the fastest levers for mood and focus - even short bursts count.",
        },
        {
            "field": "notifications_per_day",
            "theme": "Mindful Notifications",
            "icon": "🔕",
            "needs_work": lambda v: v is not None and v > 100,
            "tasks": [
                "Turn off notifications for your three noisiest apps.",
                "Batch-check messages at set times instead of reacting instantly.",
                "Switch your phone to grayscale or Do Not Disturb during focus blocks.",
            ],
            "tip": "Fewer interruptions means fewer chances to fall into an unplanned scrolling session.",
        },
        {
            "field": "focus_0_100",
            "theme": "Deep Focus",
            "icon": "🎯",
            "needs_work": lambda v: v is not None and v < 60,
            "tasks": [
                "Block 25-45 minutes for one task with your phone in another room.",
                "Close unused tabs/apps before you start a focus block.",
                "Note what broke your focus today so you can remove it tomorrow.",
            ],
            "tip": "Protecting one deep-focus block a day matters more than trying to be 'always on'.",
        },
    ]

    _DEFAULT_THEME = {
        "theme": "Maintain Your Momentum",
        "icon": "✅",
        "tasks": [
            "Keep today's habits steady - consistency is the win here.",
            "Notice one habit that's working well and do it again on purpose.",
            "Check in with how you feel at the end of the day.",
        ],
        "tip": "You're already doing well on this front - protecting it is the goal, not overhauling it.",
    }

    _CLOSING_THEME = {
        "theme": "Reflect & Reset",
        "icon": "🗓️",
        "tasks": [
            "Look back at the week: which day felt best, and why?",
            "Pick ONE habit from this week to keep going into next week.",
            "Run a new prediction to see how your habits shifted.",
        ],
        "tip": "A weekly reflection turns a one-off good day into a repeatable habit.",
    }

    # ------------------------------------------------------
    # Public API
    # ------------------------------------------------------

    def generate(
        self,
        health_class: Optional[str],
        wellness_score: Optional[float],
        persona: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
    ) -> ImprovementPlan:
        user_data = user_data or {}

        focus_rules = self._select_focus_rules(user_data)
        intro = self._build_intro(health_class, wellness_score, persona, focus_rules)

        days: List[DailyPlan] = []
        for i in range(6):
            rule = focus_rules[i % len(focus_rules)] if focus_rules else self._DEFAULT_THEME
            days.append(
                DailyPlan(
                    day_number=i + 1,
                    day_label=f"Day {i + 1}",
                    theme=rule["theme"],
                    icon=rule["icon"],
                    tasks=list(rule["tasks"]),
                    tip=rule["tip"],
                )
            )

        # Day 7 is always a reflection day, regardless of focus areas.
        days.append(
            DailyPlan(
                day_number=7,
                day_label="Day 7",
                theme=self._CLOSING_THEME["theme"],
                icon=self._CLOSING_THEME["icon"],
                tasks=list(self._CLOSING_THEME["tasks"]),
                tip=self._CLOSING_THEME["tip"],
            )
        )

        return ImprovementPlan(
            intro=intro,
            focus_areas=[r["theme"] for r in focus_rules] or [self._DEFAULT_THEME["theme"]],
            days=days,
        )

    # ------------------------------------------------------
    # Internals
    # ------------------------------------------------------

    def _select_focus_rules(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Pick the habit areas that actually need work, most urgent first."""
        needing_work = []
        for rule in self._HABIT_RULES:
            value = user_data.get(rule["field"])
            try:
                if rule["needs_work"](value):
                    needing_work.append(rule)
            except TypeError:
                continue

        if needing_work:
            return needing_work[:4]

        # Nothing flagged as needing work - keep the plan useful by
        # rotating through "maintain" guidance instead of leaving it empty.
        return [self._DEFAULT_THEME]

    @staticmethod
    def _build_intro(
        health_class: Optional[str],
        wellness_score: Optional[float],
        persona: Optional[str],
        focus_rules: List[Dict[str, Any]],
    ) -> str:
        label = str(health_class or "").strip().lower()
        score_str = f"{wellness_score:.1f}/100" if wellness_score is not None else "N/A"
        persona_str = f" as a **{persona}**" if persona else ""

        if label == "at risk":
            opener = (
                f"Your current wellness score is {score_str}, which puts you in the "
                f"**At Risk** range{persona_str}. This week is about small, sustainable "
                "resets - not a total overhaul."
            )
        elif label == "moderate":
            opener = (
                f"You're at {score_str} and sitting in the **Moderate** range{persona_str}. "
                "A few focused adjustments this week can move the needle noticeably."
            )
        elif label == "healthy":
            opener = (
                f"You're at {score_str} and already in the **Healthy** range{persona_str}. "
                "This week is about protecting what's working and fine-tuning the rest."
            )
        else:
            opener = f"Your current wellness score is {score_str}{persona_str}."

        if focus_rules:
            theme_names = ", ".join(r["theme"] for r in focus_rules)
            opener += f" This plan focuses on: **{theme_names}**."

        return opener
