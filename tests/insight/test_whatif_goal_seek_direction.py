"""Goal-seek must never answer a wellness question with a harmful number.

THE DEFECT, IN THE SHAPE IT SHIPPED IN

`AdvancedWhatIfService.goal_seek` picked the swept value minimising
`abs(score - target)` - the value whose score lands NEAREST the target,
in either direction. That is a reasonable thing to compute and the
wrong thing to answer, because a target is a floor, not a destination
to descend to.

Anyone already above their target - which is most people who pick a
reachable one - therefore got back the value that damages their score
the most, printed under the heading "Best value found". Real runs
against the real model, ordinary day, current score 87.67, target 80:

    sleep_hours                    ->  0 hours
    sleep_quality_1_10             ->  1 out of 10
    stress_0_10                    -> 10 out of 10
    physical_activity_min_per_day  ->  0 minutes

A wellness product recommending no sleep is not a rounding error. It is
the tool arguing for harm with a number beside it, and nothing in the
response let the page notice: `reached` did not exist, so "here is the
value that gets you there" and "nothing here gets you there" were the
same payload.

These tests use the real fitted model, because the defect only exists
in the interaction between the search and real model responses - a
stub that returns a monotonic line cannot express it.
"""

from __future__ import annotations

import unittest

from core.feature_schema import FEATURE_SCHEMA
from services.insight.advanced_whatif_service import AdvancedWhatIfService
from services.ml.prediction_service import PredictionService
from services.ml.validation_service import ValidationService
from utils.feature_derivation import derive_features

# A perfectly ordinary healthy day. Scores about 87.7, which is what
# makes it the case that broke: comfortably above any target a person
# would set, so "nearest the target" always pointed downhill.
A_GOOD_DAY = {
    "age": 22, "gender": "Male", "occupation_group": "Student",
    "region_group": "Middle East", "education_group": "Bachelor",
    "device_category": "Tablet", "primary_platform": "RedNote",
    "purpose_group": "Work/Career", "is_content_creator": False,
    "uses_screen_time_limits": True, "day_of_week": "Tuesday",
    "day_index": 1, "is_weekend": False,
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


def _clean(raw: dict) -> dict:
    validation = ValidationService().validate(derive_features(dict(raw)))
    if not validation.is_valid:
        raise AssertionError(f"the fixture day does not validate: {validation.errors}")
    return validation.cleaned_data


class TheSearchNeverPointsDownhill(unittest.TestCase):
    """The four fields that produced the harmful answers, by name."""

    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictionService()
        cls.day = _clean(A_GOOD_DAY)
        cls.base_score = cls.predictor.predict(cls.day, compute_shap=False).regression_score

    def test_the_day_is_the_one_that_broke_it(self):
        # Guards the fixture: if this day stopped scoring above the
        # target, the tests below would pass without testing anything.
        self.assertGreater(self.base_score, 80.0)

    def test_it_never_recommends_less_sleep_than_the_user_already_gets(self):
        result = AdvancedWhatIfService.goal_seek(
            self.day, self.predictor, "sleep_hours", 80.0, num_points=15)
        self.assertIsNotNone(result)
        # The exact number the old search returned was 0.0.
        self.assertGreater(
            result.best_value, 0.0,
            "goal-seek recommended zero hours of sleep to reach a wellness target")
        self.assertTrue(result.already_there)

    def test_it_never_recommends_maximising_stress(self):
        stress_max = FEATURE_SCHEMA["stress_0_10"].maximum
        result = AdvancedWhatIfService.goal_seek(
            self.day, self.predictor, "stress_0_10", 80.0, num_points=15)
        self.assertLess(
            result.best_value, stress_max,
            "goal-seek recommended maximum stress to reach a wellness target")

    def test_it_never_recommends_giving_up_exercise(self):
        result = AdvancedWhatIfService.goal_seek(
            self.day, self.predictor, "physical_activity_min_per_day", 80.0, num_points=15)
        self.assertGreater(
            result.best_value, 0.0,
            "goal-seek recommended zero exercise to reach a wellness target")

    def test_it_never_recommends_the_worst_possible_sleep_quality(self):
        quality_min = FEATURE_SCHEMA["sleep_quality_1_10"].minimum
        result = AdvancedWhatIfService.goal_seek(
            self.day, self.predictor, "sleep_quality_1_10", 80.0, num_points=15)
        self.assertGreater(result.best_value, quality_min)

    def test_the_answer_never_scores_below_the_target_when_one_reaches_it(self):
        """The general form of all four, over every sweepable field.

        Whatever the field, if any value in range reaches the target
        then the returned answer must be one of those - never a
        lower-scoring point that merely sits nearer the number.
        """
        fields = ["sleep_hours", "sleep_quality_1_10", "stress_0_10", "social_min",
                  "night_screen_min", "physical_activity_min_per_day",
                  "mental_fatigue_0_10", "focus_0_100"]
        for field in fields:
            with self.subTest(field=field):
                result = AdvancedWhatIfService.goal_seek(
                    self.day, self.predictor, field, 80.0, num_points=15)
                self.assertIsNotNone(result)
                reachable = [p for p in result.points
                             if p.score is not None and p.score >= 80.0]
                if reachable:
                    self.assertTrue(result.reached)
                    self.assertGreaterEqual(result.best_score, 80.0)
                else:
                    self.assertFalse(result.reached)


class AnUnreachableTargetSaysSo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictionService()
        cls.day = _clean(A_GOOD_DAY)

    def test_a_target_no_value_reaches_is_reported_as_not_reached(self):
        # 99 is out of reach by moving sleep alone on this day.
        result = AdvancedWhatIfService.goal_seek(
            self.day, self.predictor, "sleep_hours", 99.0, num_points=15)
        self.assertIsNotNone(result)
        self.assertFalse(result.reached)
        self.assertFalse(result.already_there)

    def test_an_unreached_target_still_returns_the_best_this_field_can_do(self):
        result = AdvancedWhatIfService.goal_seek(
            self.day, self.predictor, "sleep_hours", 99.0, num_points=15)
        scored = [p.score for p in result.points if p.score is not None]
        self.assertEqual(result.best_score, max(scored),
                         "an unreachable target should fall back to this field's ceiling")

    def test_the_shortfall_is_the_gap_that_is_left(self):
        result = AdvancedWhatIfService.goal_seek(
            self.day, self.predictor, "sleep_hours", 99.0, num_points=15)
        self.assertAlmostEqual(result.distance, round(99.0 - result.best_score, 1), places=1)

    def test_distance_is_zero_once_the_target_is_reached(self):
        result = AdvancedWhatIfService.goal_seek(
            self.day, self.predictor, "sleep_hours", 80.0, num_points=15)
        self.assertEqual(result.distance, 0.0)


class TheAnswerIsTheSmallestChangeThatWorks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictionService()

    def test_among_values_that_reach_it_the_nearest_one_wins(self):
        """Fifteen hours of sleep and seven and a half both clear 80.

        Only one of them is a thing a person does. "Closest to where you
        already are" is what makes the answer actionable rather than
        merely correct.
        """
        day = _clean(A_GOOD_DAY)
        result = AdvancedWhatIfService.goal_seek(
            day, self.predictor, "sleep_hours", 80.0, num_points=15)
        reaching = [p for p in result.points if p.score is not None and p.score >= 80.0]
        self.assertGreater(len(reaching), 1, "needs several qualifying values to be a test")
        current = float(day["sleep_hours"])
        nearest_gap = min(abs(p.value - current) for p in reaching)
        self.assertAlmostEqual(abs(result.best_value - current), nearest_gap, places=2)

    def test_the_current_value_and_score_come_back_with_the_answer(self):
        day = _clean(A_GOOD_DAY)
        result = AdvancedWhatIfService.goal_seek(
            day, self.predictor, "sleep_hours", 80.0, num_points=15)
        self.assertAlmostEqual(result.current_value, float(day["sleep_hours"]), places=2)
        self.assertIsNotNone(result.current_score)


if __name__ == "__main__":
    unittest.main()
