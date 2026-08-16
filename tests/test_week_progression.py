"""
Tests: week two onward continues where the user actually got to.

Week one is a starting point. Without this, every Monday reset the plan
to its gentlest tier, so somebody in their third week on sleep was
handed "set a fixed bedtime and wake-up time" for the third time - which
is not a plan, it is a loop, and it is exactly what the user meant by
asking for week two onward to follow their own progress.

The rule: a theme carried over from the previous week starts at the
tier already reached. `theme_streaks` counts how many CONSECUTIVE
previous weeks each theme has been a focus area.

Consecutive is the whole point, and it is what most of these tests are
about:

  - a theme worked on in weeks 1 and 5 is not a five-week habit. The
    streak broke, and opening at the hardest tier after a month away
    would be setting somebody up to fail;
  - a week with no plan stored at all ends the walk for the same
    reason - the app does not know what happened, and guessing that it
    went well is the wrong way to be unsure;
  - a first week, or a theme met for the first time, behaves exactly as
    it always did. That is what keeps every existing plan valid.

Run: python3 -m unittest tests.test_week_progression -v
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

STRUGGLING = {
    "sleep_hours": 4.0, "social_min": 300, "stress_0_10": 9,
    "physical_activity_min_per_day": 5, "notifications_per_day": 250,
    "focus_0_100": 30,
}


def week_key_for(offset_weeks: int) -> str:
    from services.plan_progress_service import current_week_key
    return current_week_key(date.today() - timedelta(days=7 * offset_weeks))


class TestTierProgression(unittest.TestCase):
    """The service half: a carried-over theme starts further along."""

    def setUp(self):
        from services.improvement_plan_service import ImprovementPlanService
        self.service = ImprovementPlanService()

    def _plan(self, **kw):
        return self.service.generate(
            health_class="At Risk", wellness_score=40, user_data=STRUGGLING, **kw,
        )

    def _first_day_for(self, plan, theme):
        return next(d for d in plan.days if d.theme == theme)

    def test_week_one_is_unchanged(self):
        # Everything already stored and every existing caller depends on
        # this staying exactly as it was.
        without = self._plan()
        with_empty = self._plan(theme_streaks={})
        self.assertEqual(
            [d.tasks for d in without.days], [d.tasks for d in with_empty.days],
        )
        self.assertEqual(without.days[0].tier_label, "Getting started")

    def test_a_carried_theme_opens_further_along(self):
        theme = self._plan().days[0].theme
        week_three = self._plan(theme_streaks={theme: 2})
        self.assertNotEqual(
            self._first_day_for(week_three, theme).tier_label, "Getting started",
            "the third week on this theme opened at the beginner tier again",
        )

    def test_the_tasks_themselves_change_not_only_the_label(self):
        # A label that says "Locking it in" over the same three beginner
        # tasks would be worse than no progression at all.
        theme = self._plan().days[0].theme
        first = self._first_day_for(self._plan(), theme).tasks
        later = self._first_day_for(self._plan(theme_streaks={theme: 2}), theme).tasks
        self.assertNotEqual(first, later)

    def test_a_theme_met_for_the_first_time_is_unaffected(self):
        plan = self._plan()
        themes = [d.theme for d in plan.days]
        carried = self._plan(theme_streaks={"Some Theme Not In This Plan": 3})
        self.assertEqual([d.theme for d in carried.days], themes)
        self.assertEqual(carried.days[0].tier_label, plan.days[0].tier_label)

    def test_a_long_streak_saturates_the_tier_without_running_out_of_tasks(self):
        # The tier is a finite ladder and tops out; the exercises are a
        # library and keep rotating. Both are deliberate: someone in
        # their fiftieth week is at the hardest tier there is, but
        # handing them the same three sentences they got in week ten
        # would be the loop this whole feature exists to break. Never
        # off the end of either list - a fiftieth week must still get
        # real tasks, not an IndexError or an empty day.
        theme = self._plan().days[0].theme
        ten = self._first_day_for(self._plan(theme_streaks={theme: 10}), theme)
        fifty = self._first_day_for(self._plan(theme_streaks={theme: 50}), theme)
        self.assertTrue(ten.tasks)
        self.assertTrue(fifty.tasks)
        self.assertEqual(len(ten.tasks), len(fifty.tasks))
        self.assertEqual(ten.tier_label, "Locking it in")
        self.assertEqual(fifty.tier_label, "Locking it in")

    def test_consecutive_weeks_do_not_repeat_the_same_three_tasks(self):
        theme = self._plan().days[0].theme
        weeks = [
            tuple(self._first_day_for(self._plan(theme_streaks={theme: n}), theme).tasks)
            for n in range(4)
        ]
        self.assertEqual(
            len(set(weeks)), len(weeks),
            "two of the first four weeks on this theme are word-for-word "
            "identical - that is the loop this feature exists to break",
        )

    def test_a_nonsense_streak_value_does_not_break_the_plan(self):
        for bad in ({"Sleep Recovery": None}, {"Sleep Recovery": -3}, {}):
            plan = self._plan(theme_streaks=bad)
            self.assertEqual(len(plan.days), 7)
            self.assertTrue(all(d.tasks for d in plan.days))


class TestThemeStreaks(unittest.TestCase):
    """The storage half: what counts as a consecutive week."""

    def setUp(self):
        from services import plan_lock_service
        from services.plan_lock_service import PlanLockService
        from services.storage.json_file_storage import JSONFileStorageBackend
        self._path = tempfile.mktemp(suffix=".json")
        self.service = PlanLockService(
            "user-1", backend=JSONFileStorageBackend(self._path),
        )

    def _store(self, weeks_ago: int, focus_areas: list[str]):
        self.service.save(
            {"focus_areas": focus_areas, "days": []},
            week_key_for(weeks_ago),
        )

    def test_no_history_means_no_streaks(self):
        self.assertEqual(self.service.theme_streaks(), {})

    def test_one_previous_week_gives_a_streak_of_one(self):
        self._store(1, ["Sleep Recovery", "Movement"])
        self.assertEqual(
            self.service.theme_streaks(),
            {"Sleep Recovery": 1, "Movement": 1},
        )

    def test_two_consecutive_weeks_give_a_streak_of_two(self):
        self._store(1, ["Sleep Recovery"])
        self._store(2, ["Sleep Recovery"])
        self.assertEqual(self.service.theme_streaks(), {"Sleep Recovery": 2})

    def test_a_theme_that_dropped_out_stops_counting(self):
        self._store(1, ["Sleep Recovery"])
        self._store(2, ["Sleep Recovery", "Movement"])
        streaks = self.service.theme_streaks()
        self.assertEqual(streaks.get("Sleep Recovery"), 2)
        self.assertNotIn(
            "Movement", streaks,
            "a theme absent from last week is not on a streak",
        )

    def test_a_gap_week_breaks_the_streak(self):
        # Weeks 1 and 3, nothing in week 2. Not a three-week habit -
        # opening at the hardest tier after a month away sets someone up
        # to fail.
        self._store(1, ["Sleep Recovery"])
        self._store(3, ["Sleep Recovery"])
        self.assertEqual(self.service.theme_streaks(), {"Sleep Recovery": 1})

    def test_the_current_week_is_not_counted_as_a_previous_one(self):
        self._store(0, ["Sleep Recovery"])
        self.assertEqual(
            self.service.theme_streaks(), {},
            "this week's own plan was counted as a week already completed",
        )

    def test_one_users_streaks_are_not_another_users(self):
        from services.plan_lock_service import PlanLockService
        from services.storage.json_file_storage import JSONFileStorageBackend
        self._store(1, ["Sleep Recovery"])
        other = PlanLockService("user-2", backend=JSONFileStorageBackend(self._path))
        self.assertEqual(other.theme_streaks(), {})

    def test_an_unreadable_snapshot_ends_the_walk_rather_than_raising(self):
        self._store(1, ["Sleep Recovery"])
        backend = self.service._backend
        with backend.transaction() as records:
            rows = list(records)
            for row in rows:
                row["plan"] = "{not json"
            backend.commit(rows)
        self.assertEqual(self.service.theme_streaks(), {})

    def test_a_malformed_week_key_is_answered_with_nothing(self):
        self._store(1, ["Sleep Recovery"])
        self.assertEqual(self.service.theme_streaks(before_week="not-a-week"), {})


class TestWeekProgressionIsExplained(unittest.TestCase):
    """The rule is invisible unless it is said out loud.

    A plan that quietly starts week three at a harder tier looks like a
    plan that changed its mind. The guide entry is what turns that into
    a rule the user can rely on - so it has to exist, in all four
    languages, attached to something on the page.
    """

    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        cls.guide = (root / "frontend" / "assets" / "js" / "guide-tips.js").read_text(encoding="utf-8")
        cls.weekly_html = (root / "frontend" / "weekly.html").read_text(encoding="utf-8")

    def test_the_guide_explains_it_in_all_four_languages(self):
        import re
        found = len(re.findall(r"\bplan_week_progress\s*:\s*['\"]", self.guide))
        self.assertEqual(found, 4, "plan_week_progress is not in all four languages")

    def test_it_is_attached_to_something_on_the_weekly_page(self):
        self.assertIn('data-guide="plan_week_progress"', self.weekly_html)

    def test_it_is_registered_with_a_real_mascot_face(self):
        import re
        match = re.search(r"plan_week_progress:\s*\{\s*face:\s*'([a-z]+)'", self.guide)
        self.assertIsNotNone(match, "plan_week_progress has no registry entry")
        valid = {"borderline", "confused", "good", "great", "neutral", "risk", "thinking"}
        self.assertIn(match.group(1), valid)


if __name__ == "__main__":
    unittest.main()
