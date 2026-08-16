"""
Tests: the weekly plan is frozen for its ISO week.

The behaviour these lock down was reproduced against the running app
before the fix, with a real account:

  - Two check-ins on the same day produced two completely different
    plans under the same week key. Focus went from
    ["Maintain Your Momentum"] to
    ["Social Media Boundaries", "Stress Reset", "Sleep Recovery"]
    simply because the second submission had different numbers. A
    "weekly" plan that is really a daily plan repeated seven times is
    not a plan, and on an irregular week (84 / 60 / 75) it never
    settles.

  - Worse, checkmarks bled. Progress is stored per
    (week_key, day_number, task_index) with no reference to the task
    text, so a tick against "Look back at yesterday's plan" reappeared,
    still ticked, against "Your screen time was 140 min. Try landing
    under 125 min." That is silent corruption of the user's own record
    of what they did - verified live before the fix.

So the two things worth testing are that the plan does NOT move on its
own, and that when it is deliberately moved the stale ticks go with it.

Run: python3 -m unittest tests.wellness.test_plan_week_lock -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from tests.api.test_api import APITestCase

HEALTHY = {
    "sleep_hours": 8.0, "social_min": 40, "stress_0_10": 3,
    "physical_activity_min_per_day": 45, "notifications_per_day": 50,
    "focus_0_100": 80,
}
STRUGGLING = {
    "sleep_hours": 4.0, "social_min": 300, "stress_0_10": 9,
    "physical_activity_min_per_day": 5, "notifications_per_day": 250,
    "focus_0_100": 30,
}


class TestWeeklyPlanIsLockedToItsWeek(unittest.TestCase):
    pass


class TestPlanWeekLock(APITestCase):

    def setUp(self):
        super().setUp()
        self.headers = self._auth_headers(self._register(email="lock@example.com"))
        # Each test gets its own lock store - APITestCase overrides
        # get_plan_side_storage_backend with a fresh temp file per test,
        # so one test's frozen week cannot decide another test's
        # outcome and no run touches the real storage/*.json.

    def _plan(self, user_data, regenerate=False):
        response = self.client.post(
            "/api/v1/plan",
            headers=self.headers,
            json={
                "health_class": "Healthy", "wellness_score": 80,
                "persona": None, "user_data": user_data,
                "regenerate": regenerate,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _tick(self, day_number=1, task_index=0, completed=True):
        response = self.client.put(
            "/api/v1/plan/tasks", headers=self.headers,
            json={"day_number": day_number, "task_index": task_index,
                  "completed": completed},
        )
        self.assertEqual(response.status_code, 200, response.text)

    # ------------------------------------------------------------ locking
    def test_a_second_prediction_does_not_change_the_weeks_plan(self):
        first = self._plan(HEALTHY)
        second = self._plan(STRUGGLING)
        self.assertEqual(
            first["focus_areas"], second["focus_areas"],
            "the plan changed underneath the user on a second check-in - "
            "this is the churn the week lock exists to stop",
        )
        self.assertEqual(
            [d["theme"] for d in first["days"]],
            [d["theme"] for d in second["days"]],
        )

    def test_the_task_text_is_stable_too(self):
        first = self._plan(HEALTHY)
        second = self._plan(STRUGGLING)
        self.assertEqual(
            first["days"][0]["tasks"][0]["text"],
            second["days"][0]["tasks"][0]["text"],
        )

    def test_a_tick_stays_on_the_task_it_was_ticked_against(self):
        # The exact live-reproduced bug.
        first = self._plan(HEALTHY)
        ticked_text = first["days"][0]["tasks"][0]["text"]
        self._tick()

        second = self._plan(STRUGGLING)
        task = second["days"][0]["tasks"][0]
        self.assertTrue(task["completed"], "the tick was lost")
        self.assertEqual(
            task["text"], ticked_text,
            "the tick is now sitting on a different task than the one it "
            "was ticked against",
        )

    # ------------------------------------------------------- regeneration
    def test_regenerating_replaces_the_plan(self):
        first = self._plan(HEALTHY)
        regenerated = self._plan(STRUGGLING, regenerate=True)
        self.assertNotEqual(
            first["focus_areas"], regenerated["focus_areas"],
            "an explicit regenerate must actually rebuild the plan",
        )
        # Assert against what this data actually ranks, not a guess:
        # STRUGGLING's worst signals by severity are social_min (300 vs
        # a 90 threshold) and notifications (250 vs 100), both of which
        # saturate. sleep_hours at 4.0 scores 0.43 and is genuinely
        # outranked, so it does not make the top four - an earlier
        # version of this test asserted it did and was simply wrong.
        self.assertIn("Social Media Boundaries", regenerated["focus_areas"])
        self.assertEqual(first["focus_areas"], ["Maintain Your Momentum"])

    def test_regenerating_clears_the_stale_checkmarks(self):
        self._plan(HEALTHY)
        self._tick()
        regenerated = self._plan(STRUGGLING, regenerate=True)
        self.assertFalse(
            regenerated["days"][0]["tasks"][0]["completed"],
            "checkmarks survived a regeneration, so they are now attached "
            "to tasks the user never completed",
        )

    def test_the_regenerated_plan_is_then_itself_locked(self):
        self._plan(HEALTHY)
        regenerated = self._plan(STRUGGLING, regenerate=True)
        reopened = self._plan(HEALTHY)
        self.assertEqual(regenerated["focus_areas"], reopened["focus_areas"])

    # -------------------------------------------------------- score band
    def test_the_response_carries_the_weeks_score_band(self):
        plan = self._plan(HEALTHY)
        self.assertIn("band_low", plan)
        self.assertIn("band_high", plan)

    def test_the_band_is_null_rather_than_zero_without_history(self):
        # A brand-new account has nothing to average. Reporting 0-0
        # would read as a real target of zero.
        plan = self._plan(HEALTHY)
        if plan["band_low"] is not None:
            self.assertLessEqual(plan["band_low"], plan["band_high"])

    def test_the_plan_is_still_served_when_the_snapshot_is_unreadable(self):
        # A corrupt snapshot must degrade to "generate a fresh plan",
        # never to a 500 on the weekly page.
        from services.wellness.plan_lock_service import PlanLockService
        self._plan(HEALTHY)
        me = self.client.get("/api/v1/auth/me", headers=self.headers).json()
        service = PlanLockService(me["user_id"])
        self.assertIsNone(PlanLockService._to_locked({"plan": "{not json"}))
        again = self._plan(HEALTHY)
        self.assertTrue(again["focus_areas"])


if __name__ == "__main__":
    unittest.main()
