"""
config/healthy_targets.py
-------------------------
Where each simulated habit is heading.

Shared by services/insight/future_path_service.py and
services/insight/parallel_twin_service.py so the two can never disagree about
what "better" means for a field - which is exactly how the original bug
would come back.
"""

from __future__ import annotations

# Where each adjustable field is heading. A path moves a fraction of the
# distance from the user's own current value to this value and stops -
# so "more effort" always means "closer to this", never "further past
# it". This is a target for a simulation, not a prescription, and
# nothing here is medical advice.
#
# The three recreational figures used to be 60 each. Nothing was wrong
# with them individually; what was wrong is that they summed to 180
# minutes, and the wellness score charges recreational screen time
# against the published two-hour guideline (utils/screen_load.py). A
# user who reached all three targets would have been told they had
# arrived while the score still took a third of their digital-load
# points off them. Two numbers for one idea is how the original bug in
# this file came back the first time, so the three now sum to the
# guideline. They are equal thirds of it because nothing in the
# research distinguishes a social minute from a video minute - the
# guideline is about the total, and the split is only there so the
# simulator has a per-field figure to move toward.
HEALTHY_TARGETS: dict[str, float] = {
    "social_min": 40.0,
    "gaming_min": 40.0,
    "video_min": 40.0,
    # Work and study screen time is frequently not the user's to choose
    # - the account model has a `work_screen_required` flag for exactly
    # that reason - so no path pushes anyone below a normal working day.
    # This said 240 while calling itself a normal working day, and the
    # score charges nothing until 480, so a path that cut someone's work
    # screen time from 400 to 240 promised a score improvement that
    # could not arrive. 480 is a full working day and is what the score
    # uses.
    "work_study_min": 480.0,
    "stress_0_10": 3.0,
    "notifications_per_day": 40.0,
    "pickups_per_day": 50.0,
    # 7.5h, the middle of the range the app's own recommendation copy
    # uses. Someone already sleeping 8 hours is left alone entirely.
    "sleep_hours": 7.5,
    "sleep_quality_1_10": 8.0,
    "physical_activity_min_per_day": 45.0,
}
