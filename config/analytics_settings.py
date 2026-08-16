"""
Analytics Display Settings
----------------------------
Small display-tuning constants for legacy/streamlit_app/pages/Analytics.py, pulled out
of the page/service so they aren't magic literals buried in logic.
"""

# Calendar weekday ordering used for the "Day-of-Week Pattern" chart's
# x-axis / groupby reindex, so bars always read Monday -> Sunday.
WEEKDAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

# Screen-time category fields shown in the "Where Your Screen Time
# Goes" breakdown, mapped feature-name -> display label. Keys must
# match real FEATURE_SCHEMA / user_data field names.
SCREEN_TIME_CATEGORY_LABELS = {
    "social_min": "Social Media",
    "gaming_min": "Gaming",
    "work_study_min": "Work/Study",
    "video_min": "Video/Entertainment",
    "other_min": "Other",
}

# Minimum data points required before rendering the score-history trend
# line / weekday-pattern chart (a single point can't show a trend).
MIN_POINTS_FOR_TREND_CHART = 2
MIN_WEEKDAYS_FOR_PATTERN_CHART = 2

# ------------------------------------------------------------
# Behavioral Patterns section (Weekly Behavioral Pattern, Typical Day
# Analysis, Hour x Weekday Heatmap, Exception Detective) - see
# services/insight/analytics_service.py. Each threshold is the smallest sample
# size below which the underlying statistic (a groupby mean, a std
# dev, a z-score) would be too noisy to show without misleading the
# user - not an arbitrary UI nicety.
# ------------------------------------------------------------

# Weekly Behavioral Pattern (per-weekday averages across several
# habit fields, not just health_score - a superset of the existing
# single-field build_weekday_pattern above).
MIN_ENTRIES_FOR_WEEKDAY_PATTERN = 4

# Typical Day Analysis (overall mean/std profile + weekday-vs-weekend
# split + latest-day-vs-typical comparison).
MIN_ENTRIES_FOR_TYPICAL_DAY = 3

# Hour x Weekday Heatmap (check-in hour, from HistoryService entries'
# real `recorded_at` timestamp, x day of week).
MIN_ENTRIES_FOR_HOUR_WEEKDAY_HEATMAP = 3

# Exception Detective (per-field z-score outlier detection against the
# user's own historical mean/std). A field needs at least this many
# non-null observations before its std dev is used as a baseline at
# all - below this, a "typical" value isn't statistically meaningful.
MIN_ENTRIES_FOR_EXCEPTION_DETECTION = 5
EXCEPTION_Z_SCORE_THRESHOLD = 1.5
# Cap on how many exception days the UI lists, most-exceptional first.
MAX_EXCEPTION_DAYS_SHOWN = 10

# Display labels for health_score + every services.identity.history_service
# .TRACKED_FIELDS entry, used by the Behavioral Patterns charts/tables.
# Kept separate from SCREEN_TIME_CATEGORY_LABELS above since that one
# is scoped to the screen-time pie chart only (a subset of fields,
# different phrasing convention - "Social Media" vs "Social Media
# (min)") and mixing the two would mean one dict serving two
# incompatible display contexts.
BEHAVIORAL_FIELD_LABELS = {
    "health_score": "Wellness Score",
    "total_screen_min": "Total Screen Time (min)",
    "social_min": "Social Media (min)",
    "gaming_min": "Gaming (min)",
    "work_study_min": "Work/Study Screen Time (min)",
    "video_min": "Video/Entertainment (min)",
    "sleep_hours": "Sleep (hours)",
    "sleep_quality_1_10": "Sleep Quality (1-10)",
    "stress_0_10": "Stress (0-10)",
    "focus_0_100": "Focus (0-100)",
    "productivity_0_100": "Productivity (0-100)",
    "physical_activity_min_per_day": "Physical Activity (min/day)",
}

# ------------------------------------------------------------
# Relationships & Opportunities section (Behavioral Relationship
# Explorer, Habit Domino Visualization, Golden Hour Detection,
# Leverage Day) - see services/insight/analytics_service.py. Same rationale
# as the Behavioral Patterns thresholds above: each number is the
# smallest sample size below which the underlying statistic (a
# Pearson correlation, an hour-of-day mean, a per-weekday std dev)
# would be too noisy to act on.
# ------------------------------------------------------------

# Behavioral Relationship Explorer / Habit Domino - a correlation
# coefficient computed from fewer points than this is treated as not
# meaningful yet and both features return None.
MIN_ENTRIES_FOR_CORRELATION = 6

# Habit Domino Visualization - stop extending the chain once the next
# strongest correlation drops below this magnitude (a weak link isn't
# a real "domino"), and cap the chain length so it stays readable.
DOMINO_MIN_CORRELATION = 0.3
MAX_DOMINO_CHAIN_LENGTH = 4

# Golden Hour Detection - needs several check-ins across at least this
# many distinct check-in hours before "your best hour is X" means
# anything more than one lucky day.
MIN_ENTRIES_FOR_GOLDEN_HOUR = 5
MIN_DISTINCT_HOURS_FOR_GOLDEN_HOUR = 3

# Leverage Day - a weekday's score std dev is only reported once at
# least this many of that weekday's check-ins have been recorded.
MIN_SAMPLES_PER_WEEKDAY_FOR_LEVERAGE = 3
