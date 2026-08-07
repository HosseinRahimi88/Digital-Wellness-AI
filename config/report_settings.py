"""
Report Settings
------------------
Content-selection constants for services/report_service.py's PDF
generation, pulled out of the report-building code so the field list
isn't a magic literal buried inside reportlab layout logic.
"""

# User-input fields shown in the PDF's "User Input Highlights" table,
# in display order.
REPORT_HIGHLIGHT_FEATURES = [
    "total_screen_min",
    "social_min",
    "sleep_hours",
    "stress_0_10",
    "physical_activity_min_per_day",
]
