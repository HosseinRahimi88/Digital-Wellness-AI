"""
Gamification Display Settings
--------------------------------
Constants for the new Group A product/UX features (streaks, levels,
badges). No ML/business logic here - just tunable numbers pulled out
of services/gamification_service.py so thresholds aren't magic numbers
buried in code, matching config/dashboard_settings.py's existing
pattern.
"""

# A day counts as "healthy" for streak purposes when its recorded
# health_score is at/above this value (same MEDIUM_THRESHOLD boundary
# app/components/weekly_heatmap.py already uses for its "Good" color,
# so the streak definition matches what the heatmap shows as green).
HEALTHY_DAY_SCORE_THRESHOLD = 70.0

# Level titles by level number (1-indexed). Level = 1 + (total
# check-ins // CHECKINS_PER_LEVEL), capped at the last title.
CHECKINS_PER_LEVEL = 5

LEVEL_TITLES = [
    "Getting Started",
    "Building Awareness",
    "Habit Tracker",
    "Consistency Seeker",
    "Balance Builder",
    "Mindful User",
    "Wellness Regular",
    "Digital Balance Pro",
    "Wellness Champion",
    "Wellness Master",
]

# Minimum point improvement vs. the user's first recorded score to
# unlock the "Most Improved" badge.
MOST_IMPROVED_MIN_DELTA = 10.0

# Minimum entries logged in a single calendar week to unlock the
# "Consistent Logger" badge.
CONSISTENT_LOGGER_MIN_ENTRIES_PER_WEEK = 5

# Minimum score for the "High Scorer" badge.
HIGH_SCORE_BADGE_THRESHOLD = 80.0
