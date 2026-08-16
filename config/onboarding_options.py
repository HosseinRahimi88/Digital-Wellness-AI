"""
config/onboarding_options.py
------------------------------
Label -> value option dictionaries for the onboarding preference
profile (services/identity/account_service.py::Account's primary_goal /
main_use_purpose / schedule_type fields). Ported from the Parisa
project's GOAL_OPTIONS / PURPOSE_OPTIONS / SCHEDULE_OPTIONS.

Extracted from legacy/streamlit_app/pages/Onboarding.py into its own module so
legacy/streamlit_app/pages/Profile.py can reuse the exact same option set when editing
an existing profile, instead of a second hand-copied dict silently
drifting out of sync.
"""

from __future__ import annotations

GOAL_OPTIONS = {
    "Build a better pre-sleep routine": "better_sleep",
    "Reduce late-night device use": "reduce_night_use",
    "Improve focus and reduce interruptions": "improve_focus",
    "Check my device less frequently": "reduce_pickups",
    "Manage notifications more intentionally": "manage_notifications",
    "Improve work, study, and leisure balance": "improve_balance",
    "Create more screen-free activity time": "increase_activity",
    "Maintain my current healthy habits": "maintain_habits",
}

PURPOSE_OPTIONS = {
    "Work or career": "work_career",
    "Education or study": "education",
    "Social connection": "social_connection",
    "Entertainment": "entertainment",
    "News or information": "news_information",
    "Content creation": "content_creation",
    "A mixture of purposes": "mixed",
    "Other": "other",
}

SCHEDULE_OPTIONS = {
    "Standard daytime schedule": "standard_day",
    "Early shift": "early_shift",
    "Late shift": "late_shift",
    "Rotating shifts": "rotating_shift",
    "Student or flexible schedule": "student_flexible",
    "Irregular schedule": "irregular",
    "Other": "other",
}


def label_for_value(options: dict, value: str | None) -> str:
    """Reverse lookup: the display label for a stored value (e.g. to
    preselect a selectbox when editing an existing profile). Falls
    back to the first label if `value` isn't found or is None."""
    for label, option_value in options.items():
        if option_value == value:
            return label
    return next(iter(options))
