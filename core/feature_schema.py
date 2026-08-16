"""
Feature Schema
--------------
This module defines every input feature required by the trained model.

Cleaned Version: Removed leakage columns (like health_score_raw_0_100 and composite subscores)
to ensure proper generalization without overfitting.

Feature Selection (this revision): Removed 'operating_system' (constant
column -- always "Unknown" in every training row, zero information) from
the schema entirely, since no model uses it anymore. Also removed the
standalone ML-input status of 'screen_vs_ewma_pct', 'avg_session_min',
'sessions_per_day' and 'first_check_after_waking_min' from
models.preprocessing.get_feature_columns() (see that module for the full
evidence trail: permutation importance + correlation analysis). Those
four fields are intentionally KEPT here and in the live form because they
still feed derived indices that remain real model features
(fragmentation_index_0_100, digital_dependence_0_100,
screen_vs_baseline_pct) -- only their *direct* use as standalone model
inputs was removed, not their collection. 'screen_ewma_baseline' is also
kept here: it was dropped for classification but is still used by the
regression model.
"""

from dataclasses import dataclass
from typing import Any, Optional


# ==========================================================
# Feature Definition
# ==========================================================

@dataclass(slots=True)
class Feature:

    name: str

    dtype: type

    required: bool = True

    minimum: Optional[float] = None

    maximum: Optional[float] = None

    choices: Optional[list[Any]] = None

    label: str = ""

    description: str = ""


# ==========================================================
# Categories learned by the trained OneHotEncoder
# ==========================================================

GENDER_CHOICES = ["Female", "Male", "Non-binary", "Unknown"]

OCCUPATION_GROUP_CHOICES = [
    "Caregiver/Home", "Employee", "Freelancer", "Other",
    "Retired", "Self-employed", "Student", "Unemployed",
]

REGION_GROUP_CHOICES = [
    "Africa", "Asia", "Europe", "Latin America",
    "Middle East", "North America", "Oceania",
]

EDUCATION_GROUP_CHOICES = [
    "Bachelor", "Doctoral", "High School or Below",
    "Master", "Some College/Vocational",
]

DEVICE_CATEGORY_CHOICES = ["Desktop", "Smart TV", "Smartphone", "Tablet", "Wearable"]

PRIMARY_PLATFORM_CHOICES = [
    "Bluesky", "Discord", "Facebook", "Instagram", "LinkedIn",
    "Pinterest", "RedNote", "Reddit", "Snapchat", "Telegram",
    "Threads", "TikTok", "WhatsApp", "X (Twitter)", "YouTube",
]

PURPOSE_GROUP_CHOICES = [
    "Content Creation", "Education", "Entertainment",
    "News/Information", "Shopping", "Social Connection", "Work/Career",
]

DAY_OF_WEEK_CHOICES = [
    "Friday", "Monday", "Saturday", "Sunday",
    "Thursday", "Tuesday", "Wednesday",
]


# ==========================================================
# Feature Schema (Cleaned - No Data Leakage)
# ==========================================================

FEATURE_SCHEMA: dict[str, Feature] = {

    # -----------------------------------------------------
    # Demographics
    # -----------------------------------------------------

    "age": Feature(
        name="age", dtype=int, minimum=10, maximum=100,
        label="Age", description="User age in years."
    ),

    "gender": Feature(
        name="gender", dtype=str, choices=GENDER_CHOICES,
        label="Gender"
    ),

    "occupation_group": Feature(
        name="occupation_group", dtype=str, choices=OCCUPATION_GROUP_CHOICES,
        label="Occupation"
    ),

    "region_group": Feature(
        name="region_group", dtype=str, choices=REGION_GROUP_CHOICES,
        label="Region"
    ),

    "education_group": Feature(
        name="education_group", dtype=str, choices=EDUCATION_GROUP_CHOICES,
        label="Education Level"
    ),

    "device_category": Feature(
        name="device_category", dtype=str, choices=DEVICE_CATEGORY_CHOICES,
        label="Primary Device"
    ),

    "primary_platform": Feature(
        name="primary_platform", dtype=str, choices=PRIMARY_PLATFORM_CHOICES,
        label="Primary Platform"
    ),

    "purpose_group": Feature(
        name="purpose_group", dtype=str, choices=PURPOSE_GROUP_CHOICES,
        label="Main Purpose of Use"
    ),

    "is_content_creator": Feature(
        name="is_content_creator", dtype=bool, choices=[False, True],
        label="Is a Content Creator?"
    ),

    "uses_screen_time_limits": Feature(
        name="uses_screen_time_limits", dtype=bool, choices=[False, True],
        label="Uses Screen-Time Limits?"
    ),

    # -----------------------------------------------------
    # Time / Calendar
    # -----------------------------------------------------

    "day_index": Feature(
        name="day_index", dtype=int, minimum=1, maximum=365,
        label="Tracking Day Number",
        description="Which day of your tracking period this entry represents."
    ),

    "day_of_week": Feature(
        name="day_of_week", dtype=str, choices=DAY_OF_WEEK_CHOICES,
        label="Day of the Week"
    ),

    "is_weekend": Feature(
        name="is_weekend", dtype=int, choices=[0, 1],
        label="Is it a Weekend?",
        description="0 = Weekday, 1 = Weekend."
    ),

    # -----------------------------------------------------
    # Screen Time (minutes/day)
    # -----------------------------------------------------

    "total_screen_min": Feature(
        name="total_screen_min", dtype=float, minimum=0.0, maximum=1440.0,
        label="Total Screen Time (min/day)"
    ),

    "screen_ewma_baseline": Feature(
        name="screen_ewma_baseline", dtype=float, minimum=0.0, maximum=1440.0,
        label="Personal Screen-Time Baseline (min/day)",
        description="Your typical/average screen time over recent days (exponential moving average)."
    ),

    "screen_vs_baseline_pct": Feature(
        name="screen_vs_baseline_pct", dtype=float, minimum=-100.0, maximum=300.0,
        label="Screen Time vs. Population Baseline (%)"
    ),

    "social_min": Feature(
        name="social_min", dtype=float, minimum=0.0, maximum=1440.0,
        label="Social Media Time (min/day)"
    ),

    "gaming_min": Feature(
        name="gaming_min", dtype=float, minimum=0.0, maximum=1440.0,
        label="Gaming Time (min/day)"
    ),

    "work_study_min": Feature(
        name="work_study_min", dtype=float, minimum=0.0, maximum=1440.0,
        label="Work/Study Screen Time (min/day)"
    ),

    "other_min": Feature(
        name="other_min", dtype=float, minimum=0.0, maximum=1440.0,
        label="Other Screen Time (min/day)"
    ),

    "social_ratio": Feature(
        name="social_ratio", dtype=float, minimum=0.0, maximum=1.0,
        label="Social Media Share of Screen Time (0-1)"
    ),

    "gaming_ratio": Feature(
        name="gaming_ratio", dtype=float, minimum=0.0, maximum=1.0,
        label="Gaming Share of Screen Time (0-1)"
    ),

    "work_study_ratio": Feature(
        name="work_study_ratio", dtype=float, minimum=0.0, maximum=1.0,
        label="Work/Study Share of Screen Time (0-1)"
    ),

    "other_ratio": Feature(
        name="other_ratio", dtype=float, minimum=0.0, maximum=1.0,
        label="Other Share of Screen Time (0-1)"
    ),

    "video_min": Feature(
        name="video_min", dtype=float, minimum=0.0, maximum=1440.0,
        label="Video/Entertainment Time (min/day)"
    ),

    "night_screen_min": Feature(
        name="night_screen_min", dtype=float, minimum=0.0, maximum=600.0,
        label="Night-time Screen Use (min)"
    ),

    "night_ratio": Feature(
        name="night_ratio", dtype=float, minimum=0.0, maximum=1.0,
        label="Night Share of Screen Time (0-1)"
    ),

    "pre_sleep_screen_min": Feature(
        name="pre_sleep_screen_min", dtype=float, minimum=0.0, maximum=300.0,
        label="Screen Use Before Sleep (min)"
    ),

    "pre_sleep_ratio": Feature(
        name="pre_sleep_ratio", dtype=float, minimum=0.0, maximum=1.0,
        label="Pre-Sleep Share of Screen Time (0-1)"
    ),

    # -----------------------------------------------------
    # Device Interaction
    # -----------------------------------------------------

    "notifications_per_day": Feature(
        name="notifications_per_day", dtype=int, minimum=0, maximum=2000,
        label="Notifications / Day"
    ),

    "pickups_per_day": Feature(
        name="pickups_per_day", dtype=int, minimum=0, maximum=500,
        label="Phone Pickups / Day"
    ),

    "app_opens_per_day": Feature(
        name="app_opens_per_day", dtype=int, minimum=0, maximum=1000,
        label="App Opens / Day"
    ),

    # The three densities are per HOUR of screen time, and a short screen
    # day divides by a small number: 200 notifications across 12 minutes
    # of screen is 1000 per hour, which is a real arithmetic result and
    # not a typo. The 100 ceiling these carried rejected days the models
    # were fitted on - 87 rows of the validation split exceed it for
    # notification_density (max 1127) and 28 for pickup_density (max
    # 168). A day the training data contains is not a day the validator
    # may refuse, so the ceilings are set from the observed range with
    # headroom rather than from a round number. app_open_density stays
    # at 100 because nothing in the data comes near it.
    "notification_density": Feature(
        name="notification_density", dtype=float, minimum=0.0, maximum=1500.0,
        label="Notification Density (per hour of screen time)"
    ),

    "pickup_density": Feature(
        name="pickup_density", dtype=float, minimum=0.0, maximum=1500.0,
        label="Pickup Density (per hour of screen time)"
    ),

    "app_open_density": Feature(
        name="app_open_density", dtype=float, minimum=0.0, maximum=100.0,
        label="App-Open Density (per hour of screen time)"
    ),

    "fragmentation_index_0_100": Feature(
        name="fragmentation_index_0_100", dtype=float, minimum=0.0, maximum=100.0,
        label="Usage Fragmentation Index",
        description="How broken-up/scattered device usage is throughout the day."
    ),

    # -----------------------------------------------------
    # Sleep
    # -----------------------------------------------------

    "sleep_hours": Feature(
        name="sleep_hours", dtype=float, minimum=0.0, maximum=15.0,
        label="Sleep Duration (hours)"
    ),

    "sleep_quality_1_10": Feature(
        name="sleep_quality_1_10", dtype=float, minimum=1.0, maximum=10.0,
        label="Sleep Quality (1-10)"
    ),

    # -----------------------------------------------------
    # Mental Health
    # -----------------------------------------------------

    "stress_0_10": Feature(
        name="stress_0_10", dtype=float, minimum=0.0, maximum=10.0,
        label="Stress Level (0-10)"
    ),

    "mental_fatigue_0_10": Feature(
        name="mental_fatigue_0_10", dtype=float, minimum=0.0, maximum=10.0,
        label="Mental Fatigue (0-10)"
    ),

    "anxiety_0_27": Feature(
        name="anxiety_0_27", dtype=float, minimum=0.0, maximum=27.0,
        label="Anxiety Score (0-27)"
    ),

    "low_mood_0_27": Feature(
        name="low_mood_0_27", dtype=float, minimum=0.0, maximum=27.0,
        label="Low Mood Score (0-27)"
    ),

    "happiness_0_10": Feature(
        name="happiness_0_10", dtype=float, minimum=0.0, maximum=10.0,
        label="Happiness (0-10)"
    ),

    "loneliness_1_10": Feature(
        name="loneliness_1_10", dtype=float, minimum=1.0, maximum=10.0,
        label="Loneliness (1-10)"
    ),

    "self_esteem_1_10": Feature(
        name="self_esteem_1_10", dtype=float, minimum=1.0, maximum=10.0,
        label="Self-Esteem (1-10)"
    ),

    "fomo_1_10": Feature(
        name="fomo_1_10", dtype=float, minimum=1.0, maximum=10.0,
        label="Fear of Missing Out - FOMO (1-10)"
    ),

    "social_comparison_1_10": Feature(
        name="social_comparison_1_10", dtype=float, minimum=1.0, maximum=10.0,
        label="Social Comparison Tendency (1-10)"
    ),

    "life_satisfaction_1_10": Feature(
        name="life_satisfaction_1_10", dtype=float, minimum=1.0, maximum=10.0,
        label="Life Satisfaction (1-10)"
    ),

    # -----------------------------------------------------
    # Focus / Productivity
    # -----------------------------------------------------

    "focus_0_100": Feature(
        name="focus_0_100", dtype=float, minimum=0.0, maximum=100.0,
        label="Focus Score (0-100)"
    ),

    "productivity_0_100": Feature(
        name="productivity_0_100", dtype=float, minimum=0.0, maximum=100.0,
        label="Productivity Score (0-100)"
    ),

    "digital_dependence_0_100": Feature(
        name="digital_dependence_0_100", dtype=float, minimum=0.0, maximum=100.0,
        label="Digital Dependence Score (0-100)"
    ),

    # -----------------------------------------------------
    # Lifestyle
    # -----------------------------------------------------

    "physical_activity_min_per_day": Feature(
        name="physical_activity_min_per_day", dtype=float, minimum=0.0, maximum=300.0,
        label="Physical Activity (min/day)"
    ),

    "caffeine_cups_per_day": Feature(
        name="caffeine_cups_per_day", dtype=float, minimum=0.0, maximum=20.0,
        label="Caffeine Intake (cups/day)"
    ),

}