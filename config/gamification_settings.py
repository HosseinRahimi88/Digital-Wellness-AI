"""
Gamification Display Settings
--------------------------------
Constants for the new Group A product/UX features (streaks, levels,
badges). No ML/business logic here - just tunable numbers pulled out
of services/social/gamification_service.py so thresholds aren't magic numbers
buried in code, matching config/dashboard_settings.py's existing
pattern.
"""

# A day counts as "healthy" for streak purposes when its recorded
# health_score is at/above this value (same MEDIUM_THRESHOLD boundary
# legacy/streamlit_app/components/weekly_heatmap.py already uses for its "Good" color,
# so the streak definition matches what the heatmap shows as green).
HEALTHY_DAY_SCORE_THRESHOLD = 70.0

# Streak forgiveness (D-7 / game 12). A chain that zeroes on one bad day
# punishes weeks of real progress and is the moment people quit, so a miss
# costs something real but survivable instead.
#   GRACE_DAYS_PER_MONTH - misses absorbed outright each calendar month
#   STREAK_PENALTY_DAYS  - days removed once grace is spent (never to zero
#                          unless the chain was already shorter than this)
GRACE_DAYS_PER_MONTH = 1
STREAK_PENALTY_DAYS = 2
# More unabsorbed misses than this means the habit genuinely lapsed, and
# the chain ends rather than shrinking forever.
MAX_UNABSORBED_MISSES = 2

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
