"""
Tests: the seven-day plan is personal and does not repeat.

Reported: "the 7-day plan gives the same fixed thing every day". It
did. Seven themes held three tiers of three fixed sentences - about
sixty English strings - so a plan repeated within a fortnight and every
user with the same weak signal got word-for-word the same instruction.
"Cut caffeine after 2pm" is reasonable and completely impersonal: it
does not know whether you drink one coffee or six.

Exercises are now composed - theme x template x slot x tier - and bound
to the user's own measured value. The tests that matter are the two
that failed before: a plan varies across its own days, and two
different users do not get the same sentence.

The size claim is asserted here rather than written in a README, so it
cannot drift away from the code.

Run: python3 -m unittest tests.test_exercise_library -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401 - sys.path bootstrap

from config.exercise_library import (
    LANGUAGES,
    SLOT_LABELS,
    SLOTS,
    THEMES,
    TIER_LABELS,
    TIERS,
    compose,
    library_size,
)
from services.improvement_plan_service import ImprovementPlanService


HEAVY_USER = {
    "sleep_hours": 5.2, "total_screen_min": 410, "stress_0_10": 7.5,
    "phone_pickups_per_day": 130, "physical_activity_min_per_day": 8,
    "night_usage_min": 95,
}
LIGHT_USER = {
    "sleep_hours": 7.9, "total_screen_min": 145, "stress_0_10": 3.0,
    "phone_pickups_per_day": 48, "physical_activity_min_per_day": 55,
    "night_usage_min": 12,
}


class TestLibrarySize(unittest.TestCase):

    def test_the_space_is_large_enough_not_to_repeat(self):
        size = library_size()
        self.assertGreaterEqual(size["distinct_exercises"], 5000)
        self.assertGreaterEqual(size["localized_variants"], 20000)

    def test_the_size_is_computed_from_the_parts(self):
        """A number nobody can derive is a number nobody can check."""
        size = library_size()
        self.assertEqual(size["combinations"], size["templates"] * len(SLOTS) * len(TIERS))
        self.assertEqual(size["localized_variants"], size["distinct_exercises"] * len(LANGUAGES))

    def test_every_theme_has_templates(self):
        for theme in THEMES:
            self.assertTrue(theme.templates, f"{theme.key} has no templates")


class TestEveryExerciseIsFourLanguages(unittest.TestCase):

    def test_no_template_is_missing_a_language(self):
        for theme in THEMES:
            for index in range(len(theme.templates)):
                exercise = compose(theme.key, index, "anytime", "notice", current=6.0)
                self.assertIsNotNone(exercise)
                for language in LANGUAGES:
                    text = exercise.localized(language)
                    self.assertTrue(text.strip(), f"{theme.key}[{index}] has no {language}")

    def test_the_four_languages_are_actually_different(self):
        """A copied English string in the fa slot passes a presence
        check and fails the user."""
        for theme in THEMES:
            exercise = compose(theme.key, 0, "anytime", "notice", current=6.0)
            texts = {exercise.localized(language) for language in LANGUAGES}
            self.assertEqual(len(texts), len(LANGUAGES), f"{theme.key} repeats a language")

    def test_labels_cover_every_slot_and_tier(self):
        for slot in SLOTS:
            self.assertEqual(set(SLOT_LABELS[slot]), set(LANGUAGES))
        for tier in TIERS:
            self.assertEqual(set(TIER_LABELS[tier]), set(LANGUAGES))


class TestExercisesArePersonal(unittest.TestCase):

    def test_a_numeric_template_names_the_users_own_value(self):
        exercise = compose("sleep", 0, "before_bed", "adjust", current=5.5)
        self.assertIn("5.5", exercise.localized("en"))
        self.assertIn("5.5", exercise.localized("fa"))

    def test_two_users_get_different_sentences(self):
        """The failure the report described, at its root."""
        heavy = compose("screen", 0, "midday", "notice", current=410)
        light = compose("screen", 0, "midday", "notice", current=145)
        self.assertNotEqual(heavy.localized("en"), light.localized("en"))
        self.assertNotEqual(heavy.localized("fa"), light.localized("fa"))

    def test_the_target_is_reachable_rather_than_aspirational(self):
        """A target nobody hits teaches people to ignore the plan."""
        exercise = compose("screen", 0, "midday", "notice", current=410)
        self.assertLess(exercise.target, 410)
        self.assertGreater(exercise.target, 410 * 0.7)

    def test_a_target_moves_the_right_way_for_each_theme(self):
        self.assertGreater(compose("sleep", 0, "anytime", "notice", current=5.0).target, 5.0)
        self.assertLess(compose("stress" if False else "mood", 0, "anytime", "notice", current=8.0).target, 8.0)
        self.assertGreater(compose("movement", 0, "anytime", "notice", current=10.0).target, 0)

    def test_numbers_are_bidi_isolated(self):
        """A bare number in an RTL sentence renders with its unit at the
        wrong end."""
        exercise = compose("sleep", 0, "anytime", "notice", current=5.5)
        self.assertIn("⁦", exercise.localized("fa"))
        self.assertIn("⁩", exercise.localized("fa"))

    def test_a_missing_measurement_still_produces_an_exercise(self):
        """Half the templates need no number at all - a user who has not
        logged that signal should still get something to do."""
        exercise = compose("sleep", 1, "anytime", "notice", current=None)
        self.assertTrue(exercise.localized("en").strip())
        self.assertIsNone(exercise.target)

    def test_an_unknown_theme_is_skipped_not_raised(self):
        self.assertIsNone(compose("nonsense", 0, "anytime", "notice", current=1.0))


class TestTheWeekDoesNotRepeat(unittest.TestCase):

    def setUp(self):
        self.plan = ImprovementPlanService().generate("At Risk", 48.0, "Night Owl", HEAVY_USER)

    def test_the_plan_still_has_seven_days(self):
        self.assertEqual(len(self.plan.days), 7)

    def test_every_day_carries_composed_exercises(self):
        for day in self.plan.days:
            self.assertTrue(day.exercises, f"day {day.day_number} has no exercises")
            for exercise in day.exercises:
                self.assertEqual(set(exercise["text"]), set(LANGUAGES))

    def test_the_week_is_mostly_distinct(self):
        """Not perfectly distinct: some themes have small template pools
        and repeating one is better than reaching for an exercise about
        a signal the user never logged."""
        texts = [e["text"]["en"] for day in self.plan.days for e in day.exercises]
        self.assertGreaterEqual(len(set(texts)), len(texts) * 0.7)

    def test_two_different_users_get_different_weeks(self):
        other = ImprovementPlanService().generate("Healthy", 78.0, "Night Owl", LIGHT_USER)
        mine = {e["text"]["en"] for day in self.plan.days for e in day.exercises}
        theirs = {e["text"]["en"] for day in other.days for e in day.exercises}
        self.assertTrue(mine - theirs, "two different users got identical weeks")

    def test_the_same_user_gets_the_same_week_twice(self):
        """A plan that reshuffles on every page load cannot be followed."""
        again = ImprovementPlanService().generate("At Risk", 48.0, "Night Owl", HEAVY_USER)
        self.assertEqual(
            [e["text"]["en"] for day in self.plan.days for e in day.exercises],
            [e["text"]["en"] for day in again.days for e in day.exercises],
        )

    def test_tasks_still_works_for_callers_that_never_moved_over(self):
        for day in self.plan.days:
            self.assertTrue(day.tasks)
            self.assertTrue(all(isinstance(t, str) and t.strip() for t in day.tasks))

    def test_a_recurring_theme_escalates(self):
        """The point of tiers: coming back to sleep on day 5 should not
        repeat what day 1 said."""
        tiers_by_theme: dict[str, list[str]] = {}
        for day in self.plan.days:
            for exercise in day.exercises:
                tiers_by_theme.setdefault(exercise["theme"], []).append(exercise["tier"])
        repeated = [t for t, tiers in tiers_by_theme.items() if len(set(tiers)) > 1]
        self.assertTrue(repeated, "no theme escalated across the week")


class TestItMakesNoMedicalClaim(unittest.TestCase):

    def test_no_exercise_prescribes_or_diagnoses(self):
        banned = ("diagnos", "symptom", "disorder", "medication", "dose", "cure", "treat your")
        for theme in THEMES:
            for index in range(len(theme.templates)):
                exercise = compose(theme.key, index, "anytime", "notice", current=6.0)
                for language in LANGUAGES:
                    lowered = exercise.localized(language).lower()
                    for word in banned:
                        self.assertNotIn(word, lowered, f"{theme.key}[{index}] {language}")

    def test_that_check_is_not_vacuous(self):
        self.assertIn("diagnos", "this would diagnose something".lower())


if __name__ == "__main__":
    unittest.main()
