"""A 7-day plan must not be the same day printed seven times.

Real bug: a healthy user's plan repeated ONE day six times, verbatim.
Two causes stacked:

1. `_compose_exercises` indexed templates as `day_index * 3 + offset*2`,
   and `compose()` selects with `template_index % len(templates)`. Most
   themes have 3 or 6 templates, so `day_index * 3` cancelled out
   completely for 3-template themes (reflection, night, movement) -
   every day produced byte-identical text - and collapsed 6-template
   themes to two distinct days. The day index literally did not matter.

2. Even with the stride fixed, the `reflection` theme used for
   maintenance weeks had only three templates, which cannot fill six
   days however you index them.

Both are fixed; this pins the OUTCOME (days differ) rather than the
arithmetic, so a future change to the indexing scheme is free to be
different but not free to be repetitive.
"""
from __future__ import annotations

import unittest

import tests._test_support as ts  # noqa: F401 - offline stubs

from services.wellness.improvement_plan_service import ImprovementPlanService

HEALTHY = {
    "sleep_hours": 8.0, "sleep_quality_1_10": 9, "stress_0_10": 2,
    "focus_0_100": 85, "productivity_0_100": 85,
    "physical_activity_min_per_day": 60, "notifications_per_day": 20,
    "pickups_per_day": 30, "social_min": 30, "gaming_min": 10,
    "video_min": 30, "work_study_min": 200, "total_screen_min": 300,
    "night_ratio": 0.05, "pre_sleep_ratio": 0.05,
}

AT_RISK = {
    "sleep_hours": 5.0, "sleep_quality_1_10": 4, "stress_0_10": 8,
    "focus_0_100": 35, "productivity_0_100": 40,
    "physical_activity_min_per_day": 5, "notifications_per_day": 160,
    "pickups_per_day": 140, "social_min": 240, "gaming_min": 120,
    "video_min": 180, "work_study_min": 300, "total_screen_min": 900,
    "night_ratio": 0.42, "pre_sleep_ratio": 0.5,
}


def _plan(user_data, health_class, score):
    return ImprovementPlanService().generate(
        health_class=health_class, wellness_score=score,
        persona=None, user_data=user_data,
    )


class TestPlanDaysAreDistinct(unittest.TestCase):
    def test_a_healthy_week_is_not_one_day_repeated(self):
        # The exact reported case: nothing flagged as needing work, so
        # the plan falls back to maintenance guidance.
        plan = _plan(HEALTHY, "Healthy", 84.0)
        task_sets = [tuple(d.tasks) for d in plan.days]
        self.assertEqual(
            len(set(task_sets)), len(task_sets),
            "a maintenance week repeats itself:\n  "
            + "\n  ".join(t[0][:70] if t else "(empty)" for t in task_sets),
        )

    def test_an_at_risk_week_is_also_all_distinct(self):
        plan = _plan(AT_RISK, "At Risk", 38.0)
        task_sets = [tuple(d.tasks) for d in plan.days]
        self.assertEqual(len(set(task_sets)), len(task_sets))

    def test_every_day_actually_has_tasks(self):
        # Guards the other direction: a variety fix that produced empty
        # days would pass the distinctness check vacuously.
        for user_data, klass, score in ((HEALTHY, "Healthy", 84.0), (AT_RISK, "At Risk", 38.0)):
            plan = _plan(user_data, klass, score)
            for day in plan.days:
                with self.subTest(klass=klass, day=day.day_number):
                    self.assertTrue(day.tasks, f"day {day.day_number} has no tasks")

    def test_the_day_index_actually_changes_the_exercises(self):
        # Directly targets cause (1): the day must not cancel out of the
        # template selection for ANY theme, whatever its template count.
        from config.exercise_library import THEMES_BY_KEY

        svc = ImprovementPlanService()
        for key, theme in THEMES_BY_KEY.items():
            rule = {"exercise_theme": key, "field": theme.field}
            first = [
                tuple(e["text"].get("en") for e in svc._compose_exercises(rule, HEALTHY, day, 0))
                for day in range(len(theme.templates))
            ]
            with self.subTest(theme=key):
                self.assertGreater(
                    len(set(first)), 1,
                    f"theme {key!r} produces the same exercises on every day - "
                    f"the day index is cancelling out of the template selection again",
                )

    def test_maintenance_theme_has_enough_templates_for_a_full_week(self):
        # Cause (2): three templates cannot fill six days.
        from config.exercise_library import THEMES_BY_KEY
        self.assertGreaterEqual(len(THEMES_BY_KEY["reflection"].templates), 6)

    def test_every_reflection_template_is_translated_into_all_four_languages(self):
        from config.exercise_library import THEMES_BY_KEY
        for i, tmpl in enumerate(THEMES_BY_KEY["reflection"].templates):
            text = tmpl(None, None)
            with self.subTest(template=i):
                for lang in ("en", "fa", "ar", "zh"):
                    self.assertTrue(text.get(lang), f"template {i} missing {lang}")


if __name__ == "__main__":
    unittest.main()
