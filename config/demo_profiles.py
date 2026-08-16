"""
config/demo_profiles.py
------------------------
Canonical example profiles, one valid value per `core.feature_schema
.FEATURE_SCHEMA` field.

Why this exists / why it moved here
------------------------------------
These four profiles (`baseline`, `healthy`, `at_risk`, `borderline`)
previously lived only in `tests/_test_support.py`, hand-tuned against
the *real* trained model to plausibly land in different prediction
classes. Project B's UX had a "verified demo profile" quick-start tab
(`render_data_input()`'s "Verified demo" tab) that let a user get a
real prediction in one click - a genuinely good idea worth porting,
but its actual profile *data* belonged to B's discarded model and
can't be reused (different 58-feature contract entirely).

Rather than inventing new numbers, this module promotes A's own
already-validated fixtures to a shared, non-test location so the
Prediction page's new "Quick Demo" tab (legacy/streamlit_app/pages/Prediction.py) and
the test suite (tests/_test_support.py) use the exact same source of
truth - no drift between what's demoed in the UI and what's tested.

None of this touches core/feature_schema.py, models/, or artifacts/ -
it only reads FEATURE_SCHEMA to build example inputs.
"""

from __future__ import annotations

from typing import Any, Dict

from core.feature_schema import FEATURE_SCHEMA
from utils.feature_derivation import derive_features


def _midpoint(feature) -> float:
    lo = feature.minimum if feature.minimum is not None else 0.0
    hi = feature.maximum if feature.maximum is not None else lo + 10.0
    return (lo + hi) / 2.0


def _finalize(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real bug fix (found during Group C Feature 39 implementation, not a
    Group C feature itself): every profile below hand-types its
    ratio/density/index fields (social_ratio, fragmentation_index_0_100,
    etc.) as separate literal numbers alongside the raw minute fields
    they're supposed to be *computed from* (social_min, total_screen_min,
    ...). Those numbers were never actually derived from each other, so
    e.g. `borderline_profile()` claims `social_ratio=0.5` while its own
    `social_min`/`total_screen_min` imply 0.4167 - and its four ratio
    fields summed to 2.0, which is impossible for parts of a whole. A
    real live form submission never has this problem (FormGenerator
    always computes these via derive_features()); only these hardcoded
    fixtures did. Concretely, this silently fed the trained models
    physically-inconsistent, out-of-distribution inputs every time a demo
    profile was used - the Quick Demo tab on the Prediction page, and
    every test in tests/_test_support.py that imports these functions.

    Fix: recompute every derived field from each profile's own raw
    fields via the same derive_features() a real submission goes
    through, and return that instead of the hand-typed version. Raw,
    directly-authored fields (sleep_hours, stress_0_10, persona-relevant
    psychological fields, etc.) are untouched - only the fields
    derive_features() is actually responsible for computing are
    corrected.
    """
    return derive_features(data)


def baseline_profile() -> Dict[str, Any]:
    """One valid value per schema field, using the midpoint of its range
    (or its first choice for categoricals). A neutral, always-valid
    starting point the other profiles below tweak from."""
    data = {}
    for name, feature in FEATURE_SCHEMA.items():
        if feature.choices is not None:
            data[name] = feature.choices[0]
        elif feature.dtype in (int, float):
            value = _midpoint(feature)
            data[name] = int(round(value)) if feature.dtype is int else value
        else:
            data[name] = ""

    # The five screen-time component fields (social_min, gaming_min,
    # work_study_min, video_min, other_min) each have an independent
    # per-field range up to 1440 (minutes in a day), but they are not
    # actually independent - their sum becomes total_screen_min, which
    # is itself bounded at 1440. Midpointing each of the five
    # independently (720 each) sums to 3600 minutes - a physically
    # impossible ~60-hour day, and fails ValidationService outright once
    # `_finalize()` (below) recomputes total_screen_min as their real
    # sum instead of accepting a separately-midpointed, inconsistent
    # value. Set these five to a realistic, mutually-consistent daily
    # breakdown instead, so total_screen_min (240 min = 4h, a plausible
    # daily average) stays comfortably within its own valid range.
    data.update({
        "social_min": 60.0,
        "gaming_min": 40.0,
        "work_study_min": 90.0,
        "video_min": 40.0,
        "other_min": 10.0,
    })

    # Same interdependency issue, for every other field whose *derived*
    # counterpart has its own tighter bound than an independent
    # per-field midpoint respects: notifications/pickups/app_opens per
    # day feed *_density fields capped at 100 (per screen-hour), and
    # night/pre-sleep screen minutes feed ratio fields capped at 1.0
    # (can't exceed total screen time). Set these consistent with the
    # ~4-hour daily total_screen_min set above instead of their
    # independent midpoints.
    data.update({
        "notifications_per_day": 60,
        "pickups_per_day": 40,
        "app_opens_per_day": 80,
        "night_screen_min": 20.0,
        "pre_sleep_screen_min": 15.0,
    })

    return _finalize(data)


def healthy_profile() -> Dict[str, Any]:
    """A profile that should plausibly land in the 'Healthy' range."""
    data = baseline_profile()
    data.update({
        "total_screen_min": 120.0,
        "social_min": 30.0,
        "gaming_min": 10.0,
        "work_study_min": 60.0,
        "other_min": 20.0,
        "video_min": 20.0,
        "night_screen_min": 5.0,
        "night_ratio": 0.05,
        "pre_sleep_screen_min": 5.0,
        "pre_sleep_ratio": 0.05,
        "notifications_per_day": 20,
        "pickups_per_day": 15,
        "app_opens_per_day": 20,
        "sleep_hours": 8.0,
        "sleep_quality_1_10": 9.0,
        "stress_0_10": 1.0,
        "mental_fatigue_0_10": 1.0,
        "anxiety_0_27": 2.0,
        "low_mood_0_27": 2.0,
        "happiness_0_10": 9.0,
        "loneliness_1_10": 1.0,
        "self_esteem_1_10": 9.0,
        "fomo_1_10": 1.0,
        "social_comparison_1_10": 1.0,
        "life_satisfaction_1_10": 9.0,
        "focus_0_100": 90.0,
        "productivity_0_100": 90.0,
        "digital_dependence_0_100": 5.0,
        "physical_activity_min_per_day": 60.0,
        "caffeine_cups_per_day": 1.0,
        "uses_screen_time_limits": True,
        "is_content_creator": False,
    })
    return _finalize(data)


def at_risk_profile() -> Dict[str, Any]:
    """A profile that should plausibly land in the 'At Risk' range."""
    data = baseline_profile()
    data.update({
        "total_screen_min": 1200.0,
        "social_min": 600.0,
        "gaming_min": 300.0,
        "work_study_min": 30.0,
        "other_min": 100.0,
        "video_min": 170.0,
        "night_screen_min": 400.0,
        "night_ratio": 0.6,
        "pre_sleep_screen_min": 200.0,
        "pre_sleep_ratio": 0.8,
        "notifications_per_day": 1500,
        "pickups_per_day": 400,
        "app_opens_per_day": 800,
        "sleep_hours": 3.5,
        "sleep_quality_1_10": 2.0,
        "stress_0_10": 9.5,
        "mental_fatigue_0_10": 9.5,
        "anxiety_0_27": 25.0,
        "low_mood_0_27": 25.0,
        "happiness_0_10": 1.5,
        "loneliness_1_10": 9.5,
        "self_esteem_1_10": 1.5,
        "fomo_1_10": 9.5,
        "social_comparison_1_10": 9.5,
        "life_satisfaction_1_10": 1.5,
        "focus_0_100": 10.0,
        "productivity_0_100": 10.0,
        "digital_dependence_0_100": 95.0,
        "physical_activity_min_per_day": 0.0,
        "caffeine_cups_per_day": 8.0,
        "uses_screen_time_limits": False,
        "is_content_creator": False,
    })
    return _finalize(data)


def borderline_profile() -> Dict[str, Any]:
    """A profile deliberately near typical decision-boundary territory.

    The recreational minutes were 150/60/40/60 - 310 a day, or 5.2 hours.
    That was written when screen time barely moved the score, and once it
    did, this profile stopped being borderline anything: it scored 48.2,
    inside the at-risk band (0-49), while the demo went on calling it
    "borderline" and showing it in the moderate band. A demo whose label
    and whose number disagree is worse than no demo.

    180 recreational minutes is what borderline actually means here.
    Three hours is a third of the way down the published dose-response
    curve (utils/screen_load.py) - past the two-hour guideline, well
    short of the four-hour mark - and it measures 56.2, six points clear
    of the band edge with room for the +-4% per-feature noise the demo
    applies. Everything else about this person is unchanged.
    """
    data = baseline_profile()
    data.update({
        "total_screen_min": 270.0,
        "social_min": 80.0,
        "gaming_min": 30.0,
        "work_study_min": 90.0,
        "other_min": 30.0,
        "video_min": 40.0,
        "night_screen_min": 60.0,
        "night_ratio": 0.2,
        "pre_sleep_screen_min": 30.0,
        "pre_sleep_ratio": 0.3,
        "notifications_per_day": 150,
        "pickups_per_day": 80,
        "app_opens_per_day": 120,
        "sleep_hours": 6.0,
        "sleep_quality_1_10": 5.0,
        "stress_0_10": 5.0,
        "mental_fatigue_0_10": 5.0,
        "anxiety_0_27": 13.0,
        "low_mood_0_27": 13.0,
        "happiness_0_10": 5.0,
        "loneliness_1_10": 5.0,
        "self_esteem_1_10": 5.0,
        "fomo_1_10": 5.0,
        "social_comparison_1_10": 5.0,
        "life_satisfaction_1_10": 5.0,
        "focus_0_100": 50.0,
        "productivity_0_100": 50.0,
        "digital_dependence_0_100": 50.0,
        "physical_activity_min_per_day": 25.0,
        "caffeine_cups_per_day": 3.0,
        "uses_screen_time_limits": True,
        "is_content_creator": False,
    })
    return _finalize(data)


# Display label -> profile builder, in the order they should appear in
# the Prediction page's "Quick Demo" tab.
DEMO_PROFILES = {
    "Healthy - balanced digital habits": healthy_profile,
    "Borderline - mixed signals": borderline_profile,
    "At Risk - heavy, late-night use": at_risk_profile,
    "Baseline - neutral midpoint values": baseline_profile,
}
