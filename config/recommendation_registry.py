"""
Recommendation Registry
-----------------------
Maps model features to recommendation templates.

IMPORTANT: keys here MUST match the real column names in
artifacts/feature_columns.json / core.feature_schema.FEATURE_SCHEMA,
because RecommendationService looks templates up by the feature name
that SHAP returns - and SHAP always reports real model feature names,
never the old ad-hoc form field names. A previous version of this file
used names like "daily_screen_time_hours" that never matched any real
SHAP feature, so recommendations were silently dropped for those
features.
"""

from __future__ import annotations
from dataclasses import dataclass


# ==========================================================
# Priority thresholds (normalized SHAP score, 0-100, -> priority)
# ==========================================================
# Used by services/recommendation_service.py::_priority_from_score.
# Pulled out here (rather than left as literals in the service) so the
# cutoffs live next to the rest of this recommendation configuration.
HIGH_PRIORITY_SCORE_THRESHOLD = 80
MEDIUM_PRIORITY_SCORE_THRESHOLD = 40


# ==========================================================
# Recommendation Template
# ==========================================================

@dataclass(frozen=True)
class RecommendationTemplate:
    title: str
    description: str
    action: str
    category: str
    icon: str
    priority: str

    # Ported concept from the Parisa project's
    # config/recommendation_guardrail_manifest.csv (a per-rule safety
    # note) and its "success_metric" field on each recommendation - see
    # that project's render_recommendations()'s "Success metric and
    # safety" expander. Text here is written fresh for A's actual
    # features/categories, not copied from B's file (its rules were
    # keyed to a different feature set). Both default to "" so this is
    # backward compatible with anything constructing a
    # RecommendationTemplate positionally without them.
    success_metric: str = ""
    safety_note: str = (
        "This is general digital-wellness guidance, not medical advice. "
        "If sleep, mood, or anxiety concerns persist, consider talking to "
        "a healthcare professional."
    )


# ==========================================================
# Registry
# ==========================================================

FEATURE_RECOMMENDATIONS = {

    # ------------------------------------------------------
    # Sleep Hours
    # ------------------------------------------------------
    "sleep_hours": RecommendationTemplate(
        title="Improve Sleep Duration",
        description=(
            "Sleep duration is one of the strongest factors "
            "affecting your digital wellness."
        ),
        action=(
            "Aim for 7-9 hours of sleep daily and avoid screens "
            "during the last hour before bedtime."
        ),
        category="Sleep",
        icon="😴",
        priority="HIGH",
        success_metric="Sleep 7+ hours on at least 5 of the next 7 nights.",
    ),

    # ------------------------------------------------------
    # Night Usage / Phone before sleep
    # ------------------------------------------------------
    "pre_sleep_screen_min": RecommendationTemplate(
        title="Reduce Night Screen Time",
        description=(
            "Late-night screen exposure negatively affects "
            "sleep quality and circadian rhythm."
        ),
        action=(
            "Avoid using smartphones or laptops at least 30-60 minutes "
            "before going to sleep."
        ),
        category="Sleep",
        icon="🌙",
        priority="HIGH",
        success_metric="Cut pre-sleep screen time to under 15 minutes on most nights this week.",
    ),

    "night_ratio": RecommendationTemplate(
        title="Avoid Late Night Device Usage",
        description=(
            "Using digital devices late at night significantly "
            "disrupts your REM sleep cycles."
        ),
        action=(
            "Enable 'Do Not Disturb' mode after 10 PM and keep devices away from bed."
        ),
        category="Sleep",
        icon="🛌",
        priority="HIGH",
        success_metric="Keep night-hours device use under 10% of total screen time this week.",
    ),

    # ------------------------------------------------------
    # Stress
    # ------------------------------------------------------
    "stress_0_10": RecommendationTemplate(
        title="Manage Stress Levels",
        description=(
            "High stress is strongly associated with reduced "
            "digital wellbeing and cognitive fatigue."
        ),
        action=(
            "Practice relaxation techniques and schedule short digital breaks."
        ),
        category="Mental Health",
        icon="🧠",
        priority="HIGH",
        success_metric="Complete at least one intentional stress-reset break on 5+ days this week.",
        safety_note=(
            "This is general guidance, not a mental-health diagnosis or treatment. "
            "If stress feels overwhelming or unmanageable, please talk to a "
            "healthcare professional or a crisis line in your area."
        ),
    ),

    # ------------------------------------------------------
    # Physical Activity
    # ------------------------------------------------------
    "physical_activity_min_per_day": RecommendationTemplate(
        title="Increase Physical Activity",
        description=(
            "Regular exercise improves physical health, sleep quality, and focus."
        ),
        action=(
            "Perform at least 30 minutes of moderate physical activity daily."
        ),
        category="Activity",
        icon="🏃",
        priority="MEDIUM",
        success_metric="Log 30+ minutes of movement on at least 5 of the next 7 days.",
        safety_note=(
            "Build up activity gradually and within your own physical limits. "
            "Consult a doctor before starting a new exercise routine if you "
            "have a medical condition."
        ),
    ),

    # ------------------------------------------------------
    # Social Media
    # ------------------------------------------------------
    "social_min": RecommendationTemplate(
        title="Reduce Social Media Usage",
        description=(
            "Long social media sessions may increase digital fatigue "
            "and reduce attention span."
        ),
        action=(
            "Set daily usage limits for social media applications."
        ),
        category="Screen Time",
        icon="📱",
        priority="MEDIUM",
        success_metric="Stay under your set social media time limit on 5+ days this week.",
    ),

    # ------------------------------------------------------
    # Notifications
    # ------------------------------------------------------
    "notifications_per_day": RecommendationTemplate(
        title="Minimize Notifications",
        description=(
            "Frequent notifications interrupt attention and increase mental friction."
        ),
        action=(
            "Disable unnecessary notifications during work or study sessions."
        ),
        category="Focus",
        icon="🔔",
        priority="LOW",
        success_metric="Cut daily notification count by at least 30% from your current level.",
    ),

    # ------------------------------------------------------
    # Daily Screen Time
    # ------------------------------------------------------
    "total_screen_min": RecommendationTemplate(
        title="Control Overall Screen Time",
        description=(
            "Excessive total daily screen time strains eyes and reduces activity."
        ),
        action=(
            "Follow the 20-20-20 rule and take regular breaks away from screens."
        ),
        category="Screen Time",
        icon="💻",
        priority="HIGH",
        success_metric="Reduce total daily screen time by 10-15% from your current baseline.",
    ),

    # ------------------------------------------------------
    # Fragmentation (pickups + sessions)
    # ------------------------------------------------------
    "fragmentation_index_0_100": RecommendationTemplate(
        title="Reduce Fragmented Device Checking",
        description=(
            "Frequent, scattered check-ins throughout the day break sustained "
            "attention even when total screen time is otherwise reasonable."
        ),
        action=(
            "Batch phone checks into a few set windows instead of picking it "
            "up dozens of times a day."
        ),
        category="Focus",
        icon="🧩",
        priority="MEDIUM",
        success_metric="Cut daily pickups/app opens by at least 20% from your current level.",
    ),

    # ------------------------------------------------------
    # Gaming
    # ------------------------------------------------------
    "gaming_ratio": RecommendationTemplate(
        title="Balance Gaming Time",
        description=(
            "A high share of screen time spent gaming can crowd out sleep, "
            "study, and in-person activity."
        ),
        action=(
            "Set a daily gaming time budget and use a timer to stick to it."
        ),
        category="Screen Time",
        icon="🎮",
        priority="MEDIUM",
        success_metric="Stay within your set gaming time budget on 5+ days this week.",
    ),

    # ------------------------------------------------------
    # Night screen minutes (raw)
    # ------------------------------------------------------
    "night_screen_min": RecommendationTemplate(
        title="Cut Down Night-Time Screen Minutes",
        description=(
            "Heavy device use during night hours pushes back sleep onset "
            "and reduces sleep quality."
        ),
        action=(
            "Set a hard cutoff time for screens at night and charge devices "
            "outside the bedroom."
        ),
        category="Sleep",
        icon="🌃",
        priority="HIGH",
        success_metric="Reduce night-time screen minutes by at least 30% from your current level.",
    ),

    # ------------------------------------------------------
    # Productivity
    # ------------------------------------------------------
    "productivity_0_100": RecommendationTemplate(
        title="Rebuild Daily Productivity",
        description=(
            "Low self-rated productivity often tracks with fragmented "
            "attention and poor sleep, both influenced by digital habits."
        ),
        action=(
            "Block distraction-free focus periods and silence notifications "
            "during them."
        ),
        category="Focus",
        icon="⚡",
        priority="MEDIUM",
        success_metric="Complete at least one distraction-free focus block on 5+ days this week.",
    ),

    # ------------------------------------------------------
    # Sleep quality
    # ------------------------------------------------------
    "sleep_quality_1_10": RecommendationTemplate(
        title="Improve Sleep Quality",
        description=(
            "Poor subjective sleep quality is strongly linked to pre-sleep "
            "screen exposure and irregular routines."
        ),
        action=(
            "Keep a consistent bedtime and avoid screens in the hour before sleep."
        ),
        category="Sleep",
        icon="🌜",
        priority="HIGH",
        success_metric="Keep a consistent bedtime (within 30 min) on 5+ nights this week.",
    ),
}