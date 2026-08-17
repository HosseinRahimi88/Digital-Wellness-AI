"""Every point of a sweep has to be a day that can exist.

THE DEFECT

`_field_range` took a field's own schema minimum and maximum and swept
between them. Three of the rules that decide whether a day is valid
span TWO fields, so a per-field bound cannot see them:

  * night_screen_min and pre_sleep_screen_min are minutes drawn from
    the day's own screen total. night_ratio = night_screen_min /
    total_screen_min, capped at 1.0 - so on a 210-minute day, sweeping
    night minutes to their own 600-minute maximum spends six of nine
    points on days the validator refuses.

  * app_opens_per_day (max 1000) divided by screen hours must land
    inside app_open_density (max 100). On a 3.5-hour day that is 350
    opens, and the sweep went to 1000.

  * the five usage categories cannot sum past total_screen_min's
    maximum - this one was already handled, and is kept under test
    beside the two that were not.

A refused point comes back with score=None. The chart then drew it as
zero (`p.score ?? 0`), so the line fell off a cliff at 225 night
minutes: a wellness graph appearing to say "your score collapses to 0",
produced entirely by the sweep leaving the region where a day exists.
Both halves are fixed - the range no longer leaves it, and the chart no
longer invents a number when it does.

Run: python3 -m unittest tests.insight.test_whatif_sweep_is_scoreable -v
"""

from __future__ import annotations

import unittest

from core.feature_schema import FEATURE_SCHEMA
from services.insight.advanced_whatif_service import AdvancedWhatIfService
from services.ml.prediction_service import PredictionService
from services.ml.validation_service import ValidationService
from utils.feature_derivation import derive_features

AN_ORDINARY_DAY = {
    "age": 22, "gender": "Male", "occupation_group": "Student",
    "region_group": "Middle East", "education_group": "Bachelor",
    "device_category": "Tablet", "primary_platform": "RedNote",
    "purpose_group": "Work/Career", "is_content_creator": False,
    "uses_screen_time_limits": True, "day_of_week": "Tuesday",
    "day_index": 1, "is_weekend": False,
    # 210 minutes of screen in total - the number the two cross-field
    # rules below are measured against.
    "social_min": 45, "gaming_min": 0, "work_study_min": 120,
    "video_min": 30, "other_min": 15, "night_screen_min": 0,
    "pre_sleep_screen_min": 10, "notifications_per_day": 30,
    "pickups_per_day": 20, "app_opens_per_day": 25, "sessions_per_day": 12,
    "first_check_after_waking_min": 45, "sleep_hours": 8,
    "sleep_quality_1_10": 8.5, "stress_0_10": 2, "mental_fatigue_0_10": 2,
    "anxiety_0_27": 2, "low_mood_0_27": 1, "fomo_1_10": 2,
    "happiness_0_10": 8.5, "loneliness_1_10": 2, "self_esteem_1_10": 8,
    "social_comparison_1_10": 2, "life_satisfaction_1_10": 8.5,
    "focus_0_100": 85, "productivity_0_100": 85,
    "physical_activity_min_per_day": 60, "caffeine_cups_per_day": 1,
}

TOTAL_SCREEN_MIN = 210.0


def _clean(raw: dict) -> dict:
    validation = ValidationService().validate(derive_features(dict(raw)))
    if not validation.is_valid:
        raise AssertionError(f"the fixture day does not validate: {validation.errors}")
    return validation.cleaned_data


def _sweepable_fields() -> list[str]:
    """Every field the simulator's picker offers, from the same rule.

    Derived fields are excluded because derivation overwrites them, and
    the three bookkeeping fields because they are not habits - see
    frontend/assets/js/pages/whatif.js.
    """
    base = {name: 1.0 for name, f in FEATURE_SCHEMA.items()
            if f.dtype in (int, float) and not f.choices}
    not_a_habit = {"day_index", "screen_ewma_baseline", "age"}
    fields = []
    for name, feature in FEATURE_SCHEMA.items():
        if feature.dtype not in (int, float) or feature.choices or name in not_a_habit:
            continue
        probe = dict(base)
        probe[name] = -987654.0
        if derive_features(dict(probe)).get(name) == -987654.0:
            fields.append(name)
    return fields


class NoSweepLeavesTheRegionWhereADayExists(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictionService()
        cls.day = _clean(AN_ORDINARY_DAY)

    def test_the_fixture_really_is_a_210_minute_day(self):
        # The two caps below are relative to this number, so a fixture
        # that drifted would make them test nothing.
        self.assertAlmostEqual(float(self.day["total_screen_min"]), TOTAL_SCREEN_MIN, places=1)

    def test_night_minutes_never_exceed_the_day_they_come_from(self):
        points = AdvancedWhatIfService.sweep_field(
            self.day, self.predictor, "night_screen_min", num_points=9)
        self.assertTrue(points)
        self.assertLessEqual(
            max(p.value for p in points), TOTAL_SCREEN_MIN,
            "sweeping night minutes past the day's own screen total makes "
            "night_ratio exceed 1.0, which the validator refuses")

    def test_pre_sleep_minutes_never_exceed_the_day_they_come_from(self):
        points = AdvancedWhatIfService.sweep_field(
            self.day, self.predictor, "pre_sleep_screen_min", num_points=9)
        self.assertLessEqual(max(p.value for p in points), TOTAL_SCREEN_MIN)

    def test_app_opens_stay_inside_the_density_ceiling(self):
        points = AdvancedWhatIfService.sweep_field(
            self.day, self.predictor, "app_opens_per_day", num_points=9)
        screen_hours = TOTAL_SCREEN_MIN / 60.0
        ceiling = FEATURE_SCHEMA["app_open_density"].maximum * screen_hours
        self.assertLessEqual(max(p.value for p in points), ceiling + 0.01)

    def test_every_offered_field_sweeps_without_a_single_gap(self):
        """The general form, over the whole picker.

        A gap is not merely untidy: the chart had no way to draw one
        except as a number, and the number it chose was zero.
        """
        for field in _sweepable_fields():
            with self.subTest(field=field):
                points = AdvancedWhatIfService.sweep_field(
                    self.day, self.predictor, field, num_points=9)
                self.assertTrue(points, f"{field} produced no points at all")
                unscoreable = [p.value for p in points if p.score is None]
                self.assertEqual(
                    unscoreable, [],
                    f"{field} swept to values that cannot be scored: {unscoreable}")

    def test_a_capped_sweep_still_covers_real_ground(self):
        # A cap that collapsed the range to a single point would remove
        # the gaps and the usefulness together.
        for field in ("night_screen_min", "app_opens_per_day"):
            with self.subTest(field=field):
                points = AdvancedWhatIfService.sweep_field(
                    self.day, self.predictor, field, num_points=9)
                spread = max(p.value for p in points) - min(p.value for p in points)
                self.assertGreater(spread, 0.0, f"{field} collapsed to a single value")
                self.assertEqual(len({p.value for p in points}), 9)


class TheOfferedFieldsAreOnesThatCanMove(unittest.TestCase):
    """A field derivation overwrites cannot be swept at all.

    Thirteen were in the picker. Setting one and then deriving replaces
    it, so every point scored identically and the chart was a flat line
    across the full range - most conspicuously on total_screen_min, the
    first field most people would reach for.
    """

    def test_the_picker_rule_excludes_every_derived_field(self):
        offered = set(_sweepable_fields())
        for name in ("total_screen_min", "social_ratio", "night_ratio",
                     "notification_density", "app_open_density",
                     "fragmentation_index_0_100", "digital_dependence_0_100",
                     "screen_vs_baseline_pct"):
            with self.subTest(name=name):
                self.assertNotIn(name, offered)

    def test_the_rule_still_offers_the_habits(self):
        offered = set(_sweepable_fields())
        for name in ("sleep_hours", "social_min", "gaming_min", "video_min",
                     "stress_0_10", "night_screen_min", "notifications_per_day",
                     "physical_activity_min_per_day"):
            with self.subTest(name=name):
                self.assertIn(name, offered)


if __name__ == "__main__":
    unittest.main()
