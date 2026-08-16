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
# Used by services/wellness/recommendation_service.py::_priority_from_score.
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

    # ------------------------------------------------------
    # Added so the model's own findings stop falling on the floor.
    # Before these, a harmful SHAP factor with no template here was
    # silently dropped by RecommendationService (`if template is None:
    # continue`) - the model would name the thing dragging a score down
    # and the result page would say nothing about it. Measured on the
    # at-risk demo profile: 2 of its 4 harmful factors produced no
    # advice at all.
    # ------------------------------------------------------
    "pickups_per_day": RecommendationTemplate(
        title="Reach for the Phone Less Often",
        description="How often you pick the phone up shapes your attention more than how long you hold it.",
        action="Park the phone across the room while you work, so a pickup costs a decision.",
        category="Focus", icon="\U0001F4F2", priority="MEDIUM",
        success_metric="Fewer daily pickups than this week's number, on most days.",
    ),
    "pickup_density": RecommendationTemplate(
        title="Break the Checking Loop",
        description="You are picking the phone up many times per hour of actual use - that is a checking loop, not usage.",
        action="Pick one hour a day and leave the phone face-down in another room for all of it.",
        category="Focus", icon="\U0001F501", priority="MEDIUM",
        success_metric="One protected phone-free hour on at least five days.",
    ),
    "app_opens_per_day": RecommendationTemplate(
        title="Open Fewer Apps, More Deliberately",
        description="A high number of app opens usually means opening without a reason in mind.",
        action="Move your two most-opened apps off the home screen so opening them takes a search.",
        category="Focus", icon="\U0001F4F1", priority="MEDIUM",
        success_metric="Fewer app opens than this week's number, on most days.",
    ),
    "app_open_density": RecommendationTemplate(
        title="Slow the App Switching",
        description="Switching between apps many times per hour of use fragments attention even when total time is fine.",
        action="Finish one thing before opening the next app - even for two minutes at a time.",
        category="Focus", icon="\U0001F500", priority="MEDIUM",
        success_metric="A lower app-open density than this week's figure.",
    ),
    "social_ratio": RecommendationTemplate(
        title="Rebalance What Your Screen Time Is For",
        description="Social apps take up a large share of your screen time, which affects mood more than the same minutes spent elsewhere.",
        action="Swap one social session a day for something else you already do on the phone.",
        category="Screen Time", icon="\u2696\uFE0F", priority="MEDIUM",
        success_metric="A smaller social share of total screen time than this week.",
    ),
    "work_study_ratio": RecommendationTemplate(
        title="Put an Edge on the Working Day",
        description="Work and study take up most of your screen time. That is not a fault - but without an end to it, recovery never starts.",
        action="Pick a time your work screen closes, and let the rest of the evening be a different kind of screen or none.",
        category="Focus", icon="\U0001F4BC", priority="MEDIUM",
        success_metric="A clear stop time kept on at least four working days.",
    ),
    "other_ratio": RecommendationTemplate(
        title="Notice the Unaccounted Screen Time",
        description="A large share of your screen time is not in any of the named categories, which usually means it is unplanned.",
        action="For two days, note what the unlabelled sessions actually were - naming it is most of the fix.",
        category="Screen Time", icon="\U0001F50D", priority="LOW",
        success_metric="A smaller unlabelled share once you know what it is.",
    ),
    "video_min": RecommendationTemplate(
        title="Make Watching a Choice, Not a Default",
        description="Video time is the easiest kind to lose track of, because nothing in it asks you to stop.",
        action="Decide what you are watching before you open the app, and stop when it ends.",
        category="Screen Time", icon="\U0001F3AC", priority="MEDIUM",
        success_metric="Under {target} minutes of video on most days this week.",
    ),
    "gaming_min": RecommendationTemplate(
        title="Give Gaming a Finish Line",
        description="Gaming is fine as a choice and costly as a default - the difference is whether it has an end.",
        action="Set the stopping point before you start: one match, one session, one hour.",
        category="Screen Time", icon="\U0001F3AE", priority="MEDIUM",
        success_metric="Under {target} minutes of gaming on most days this week.",
    ),
    "pre_sleep_ratio": RecommendationTemplate(
        title="Shift Screen Time Away From Bedtime",
        description="A large share of your screen time lands right before sleep, which is the costliest hour for it.",
        action="Move one pre-sleep habit to before dinner - the same minutes, several hours earlier.",
        category="Sleep", icon="\U0001F319", priority="HIGH",
        success_metric="A smaller pre-sleep share than this week, on most nights.",
    ),
    "mental_fatigue_0_10": RecommendationTemplate(
        title="Build In Real Breaks",
        description="Mental fatigue is the signal that recovery is not keeping up with load - not that you need to push harder.",
        action="Take one break away from all screens, outdoors if you can, in the middle of your longest working stretch.",
        category="Mental Health", icon="\U0001F50B", priority="MEDIUM",
        success_metric="One genuine screen-free break on at least five days.",
    ),
    "focus_0_100": RecommendationTemplate(
        title="Protect One Block of Focus",
        description="Your focus score is low enough to be costing you time rather than just feeling frustrating.",
        action="Protect one 25-minute block with notifications off and one task open.",
        category="Focus", icon="\U0001F3AF", priority="MEDIUM",
        success_metric="One protected focus block on at least five days.",
    ),
    "digital_dependence_0_100": RecommendationTemplate(
        title="Loosen the Pull a Little",
        description="This measures how strongly the phone pulls at you, not how much you use it - and it responds to friction, not willpower.",
        action="Add one deliberate obstacle: greyscale, a login screen, or the phone in a drawer during meals.",
        category="Screen Time", icon="\U0001F517", priority="MEDIUM",
        success_metric="One friction change kept in place for the whole week.",
    ),
    "caffeine_cups_per_day": RecommendationTemplate(
        title="Move Caffeine Earlier",
        description="Caffeine has a long tail - the cup that feels harmless at 4pm is often still working at bedtime.",
        action="Keep the same number of cups, but make the last one before 2pm.",
        category="Sleep", icon="\u2615", priority="LOW",
        success_metric="No caffeine after 2pm on at least five days.",
    ),
    "fomo_1_10": RecommendationTemplate(
        title="Test What You Actually Miss",
        description="The feeling of missing out is usually much larger than what is genuinely missed.",
        action="Leave one app closed for a full evening, then check whether anything needed you.",
        category="Mental Health", icon="\U0001F30A", priority="LOW",
        success_metric="One evening away from the app, and an honest look at what changed.",
    ),
    "social_comparison_1_10": RecommendationTemplate(
        title="Change What Your Feed Shows You",
        description="Comparison is driven far more by which accounts you see than by how long you look.",
        action="Mute or unfollow three accounts that consistently leave you feeling worse.",
        category="Mental Health", icon="\U0001FA9E", priority="MEDIUM",
        success_metric="Three accounts muted, and a week to notice the difference.",
    ),
}


# ==========================================================
# Fields that must never carry a recommendation
# ==========================================================
# SHAP can rank any model input, including ones a user cannot act on.
# Leaving them merely "not covered" makes a deliberate refusal look like
# an oversight someone will later fill in, so the refusals are written
# down and enforced by tests/wellness/test_plan_recommendations_motivation.py.
#
# Two separate reasons, kept separate on purpose:

# 1. Nothing to act on. Advice framed around who someone is, or what day
#    it happens to be, is either nonsense or blame ("your score suffers
#    because of your region"). The model may legitimately use these to
#    predict; the coach must not turn them into instructions.
NON_ACTIONABLE_FIELDS = frozenset({
    "age", "gender", "occupation_group", "region_group", "education_group",
    "device_category", "primary_platform", "purpose_group", "is_content_creator",
    "day_index", "day_of_week", "is_weekend",
    "screen_ewma_baseline", "screen_vs_baseline_pct",
})

# 2. Clinical instruments. anxiety_0_27 and low_mood_0_27 are scored
#    like screening questionnaires, and loneliness/self-esteem/life
#    satisfaction are validated psychological scales. This app's own
#    rule is that it never uses medical framing and never diagnoses.
#    "Your anxiety score is dragging your wellness down, here is how to
#    lower it in seven days" is exactly that framing, and it is the kind
#    of advice that can do harm to the person most likely to read it.
#
#    So the app stays silent on these rather than coaching them. The
#    crisis guard in coach-chat.js is what responds when someone raises
#    them directly - a support route, not a task list.
CLINICAL_FIELDS = frozenset({
    "anxiety_0_27", "low_mood_0_27", "loneliness_1_10",
    "self_esteem_1_10", "life_satisfaction_1_10", "happiness_0_10",
})

NEVER_RECOMMEND = NON_ACTIONABLE_FIELDS | CLINICAL_FIELDS
