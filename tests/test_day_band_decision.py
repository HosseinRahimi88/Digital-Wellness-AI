"""
Tests: a day that falls outside the week's score band.

The weekly plan is aimed at a RANGE, not at one number - see
services/plan_lock_service.py. From the second logged day of a week
onward a day can land outside that range, and there are two genuinely
different things that can mean:

  * it was an unusual day, and letting it steer the plan would drag the
    rest of the week toward a life the user is not living;
  * it was a real change, and the plan should follow it.

Neither is a safe default, so the app asks. What is being pinned here:

  - the question is never asked on the week's FIRST day (there is
    nothing to be outside of), never asked about an ordinary day, and
    never asked twice;
  - the day is judged against the band of the OTHER days, not against a
    band it has already dragged toward itself;
  - "exception" changes no plan and does not delete the day - it stays
    in history, stays on the dashboard, and still counts toward the
    band at a reduced weight, because a day that vanishes lets a week
    be curated into a straight line;
  - "count it" rebuilds the REST of the week and leaves the days
    already lived through - and their checkmarks - alone. Wiping those
    would tell someone they had not done work they actually did.

Run: python3 -m unittest tests.test_day_band_decision -v
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from tests.test_api import APITestCase

HEALTHY = {
    "sleep_hours": 8.0, "social_min": 40, "stress_0_10": 3,
    "physical_activity_min_per_day": 45, "notifications_per_day": 50,
    "focus_0_100": 80,
}


def _this_week_dates(count: int) -> list[date]:
    """`count` dates ending today, all inside today's ISO week.

    Walks backwards from today and stops at the week's Monday, so a run
    on a Tuesday cannot silently seed days into last week and make the
    whole fixture meaningless.
    """
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    out = []
    day = today
    while len(out) < count and day >= monday:
        out.append(day)
        day -= timedelta(days=1)
    return list(reversed(out))


class TestDayBandDecision(APITestCase):

    def setUp(self):
        super().setUp()
        self.headers = self._auth_headers(self._register(email="band@example.com"))
        self.me = self.client.get("/api/v1/auth/me", headers=self.headers).json()

        # The plan lock and the day decisions both live in the backend
        # APITestCase injects (a fresh temp file per test), so nothing
        # here touches the real storage/*.json.

    # ------------------------------------------------------------ fixtures
    def _seed(self, scores: list[float]) -> list[str]:
        """Write real history rows for this week, one per score.

        Written straight through HistoryService rather than through
        /predict: the model decides the score for a real prediction, and
        these tests are about the band arithmetic, which needs the
        scores to be the ones named here.
        """
        from api.dependencies.services import get_history_storage_backend

        backend = self.app.dependency_overrides[get_history_storage_backend]()
        days = _this_week_dates(len(scores))
        if len(days) < len(scores):
            self.skipTest(f"today is {date.today():%A}; this week cannot hold {len(scores)} days")

        with backend.transaction() as records:
            rows = list(records)
            for day, score in zip(days, scores):
                rows.append({
                    "user_id": self.me["user_id"],
                    "date": day.isoformat(),
                    "day_of_week": day.strftime("%A"),
                    "health_score": float(score),
                    "health_class": "Healthy" if score >= 70 else "Moderate",
                    "excluded": False,
                })
            backend.commit(rows)
        return [d.isoformat() for d in days]

    def _status(self):
        response = self.client.get("/api/v1/plan/day-status", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _decide(self, decision, **extra):
        return self.client.post(
            "/api/v1/plan/day-decision", headers=self.headers,
            json={"decision": decision, **extra},
        )

    def _plan(self, regenerate=False):
        response = self.client.post(
            "/api/v1/plan", headers=self.headers,
            json={
                "health_class": "Healthy", "wellness_score": 80,
                "persona": None, "user_data": HEALTHY, "regenerate": regenerate,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    # ------------------------------------------------------- when to ask
    def test_no_question_on_the_weeks_first_day(self):
        # Honest note on what this does and does not prove: deleting the
        # explicit `day_number >= 2` guard leaves this test passing,
        # because on day one there are no OTHER days to build a band
        # from and `is_outside_band(score, None, None)` is False on its
        # own. Both are deliberate - the guard states the rule the spec
        # states, the band arithmetic makes it unreachable anyway - and
        # the assertion below is on the behaviour a user sees, which is
        # what has to hold however it is arrived at. The mechanism
        # itself is pinned separately by
        # test_there_is_no_band_on_the_weeks_first_day.
        self._seed([80.0])
        status = self._status()
        self.assertEqual(status["day_number"], 1)
        self.assertFalse(
            status["needs_decision"],
            "there is nothing for the first day of a week to be outside of",
        )

    def test_there_is_no_band_on_the_weeks_first_day(self):
        # Reported as null rather than as a band centred on that one
        # day: "your range is 74-86" after a single check-in would be a
        # range invented from one number.
        self._seed([80.0])
        status = self._status()
        self.assertIsNone(status["band_low"])
        self.assertIsNone(status["band_high"])
        self.assertFalse(status["outside_band"])

    def test_no_question_for_an_ordinary_second_day(self):
        self._seed([80.0, 82.0])
        status = self._status()
        self.assertEqual(status["day_number"], 2)
        self.assertFalse(status["outside_band"])
        self.assertFalse(status["needs_decision"])

    def test_a_day_far_outside_the_band_is_asked_about(self):
        self._seed([80.0, 45.0])
        status = self._status()
        self.assertEqual(status["day_number"], 2)
        self.assertTrue(status["outside_band"], status)
        self.assertTrue(status["needs_decision"], status)

    def test_the_day_is_judged_against_the_other_days_not_itself(self):
        # With the day included, an average of (80 + 45) / 2 = 62.5 gives
        # a band of 56.5-68.5 and 45 would still be outside - but a
        # milder outlier would not be. Judged against the days it is
        # being compared TO, the band is 74-86, which is the honest
        # question: "that is outside the range you have been running at".
        self._seed([80.0, 70.0])
        status = self._status()
        self.assertEqual(status["band_low"], 74.0)
        self.assertEqual(status["band_high"], 86.0)
        self.assertTrue(status["outside_band"])

    def test_the_question_is_not_asked_twice(self):
        self._seed([80.0, 45.0])
        self.assertTrue(self._status()["needs_decision"])
        self._decide("exception")
        after = self._status()
        self.assertFalse(after["needs_decision"], "a prompt that comes back is nagging")
        self.assertEqual(after["decision"], "exception")

    # -------------------------------------------------------- exception
    def test_an_exception_leaves_the_plan_alone(self):
        self._seed([80.0, 45.0])
        before = self._plan()
        self._decide("exception")
        after = self._plan()
        self.assertEqual(before["focus_areas"], after["focus_areas"])
        self.assertEqual(
            [d["theme"] for d in before["days"]],
            [d["theme"] for d in after["days"]],
        )

    def test_an_exception_day_is_not_deleted(self):
        days = self._seed([80.0, 45.0])
        self._decide("exception")
        history = self.client.get("/api/v1/history", headers=self.headers).json()
        dates = [item["date"] for item in history["items"]]
        self.assertIn(days[-1], dates, "the day was erased rather than marked")

    def test_an_exception_day_is_reported_for_the_dashboard(self):
        days = self._seed([80.0, 45.0])
        self._decide("exception")
        self.assertIn(days[-1], self._status()["exception_days"])

    def test_an_exception_day_still_moves_the_band_but_less(self):
        # 80 and 45. Counted in full the average is 62.5; at a quarter
        # weight it is (80*1 + 45*0.25) / 1.25 = 73.0. Neither 80 (which
        # would be erasure) nor 62.5 (which would be counting it).
        self._seed([80.0, 45.0])
        self._decide("exception")
        plan = self._plan(regenerate=True)
        self.assertAlmostEqual(plan["band_low"], 67.0, places=1)
        self.assertAlmostEqual(plan["band_high"], 79.0, places=1)

    def test_the_exception_weight_is_reported_rather_than_left_to_the_ui(self):
        self._seed([80.0, 45.0])
        status = self._status()
        self.assertGreater(status["exception_weight"], 0.0)
        self.assertLess(status["exception_weight"], 1.0)

    # ---------------------------------------------------------- counted
    def test_counting_it_rebuilds_the_rest_of_the_week(self):
        self._seed([80.0, 45.0])
        before = self._plan()
        response = self._decide("counted", user_data={
            "sleep_hours": 4.0, "social_min": 300, "stress_0_10": 9,
            "physical_activity_min_per_day": 5, "notifications_per_day": 250,
            "focus_0_100": 30,
        })
        self.assertEqual(response.status_code, 200, response.text)
        after = self._plan()
        day_number = response.json()["day_number"]
        changed = [
            d for d in after["days"]
            if d["day_number"] >= day_number
            and d["theme"] != next(
                b["theme"] for b in before["days"] if b["day_number"] == d["day_number"]
            )
        ]
        self.assertTrue(changed, "counting the day changed nothing about the plan")

    def test_counting_it_leaves_the_earlier_days_alone(self):
        self._seed([80.0, 45.0])
        before = self._plan()
        response = self._decide("counted", user_data={
            "sleep_hours": 4.0, "social_min": 300, "stress_0_10": 9,
            "physical_activity_min_per_day": 5, "notifications_per_day": 250,
            "focus_0_100": 30,
        })
        day_number = response.json()["day_number"]
        if day_number < 2:
            self.skipTest("no earlier day to preserve")
        after = self._plan()
        for earlier in [d for d in after["days"] if d["day_number"] < day_number]:
            original = next(b for b in before["days"] if b["day_number"] == earlier["day_number"])
            self.assertEqual(
                earlier["tasks"][0]["text"], original["tasks"][0]["text"],
                "a day already lived through was rewritten under the user",
            )

    def test_counting_it_keeps_the_checkmarks_on_the_days_it_kept(self):
        self._seed([80.0, 45.0])
        self._plan()
        tick = self.client.put(
            "/api/v1/plan/tasks", headers=self.headers,
            json={"day_number": 1, "task_index": 0, "completed": True},
        )
        self.assertEqual(tick.status_code, 200, tick.text)

        response = self._decide("counted", user_data=HEALTHY)
        if response.json()["day_number"] < 2:
            self.skipTest("no earlier day to preserve")
        after = self._plan()
        self.assertTrue(
            after["days"][0]["tasks"][0]["completed"],
            "a tick against a day the user actually lived through was wiped "
            "by a decision about a later day",
        )

    # ---------------------------------------------------------- refusals
    def test_an_unknown_decision_is_refused(self):
        self._seed([80.0, 45.0])
        response = self._decide("maybe")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["error"]["code"], "invalid_day_decision")

    def test_deciding_about_a_day_with_no_check_in_is_refused(self):
        self._seed([80.0])
        response = self._decide("exception", date="1999-01-04")
        self.assertEqual(response.status_code, 404, response.text)

    def test_day_status_is_answerable_with_no_history_at_all(self):
        status = self._status()
        self.assertFalse(status["needs_decision"])
        self.assertIsNone(status["band_low"])
        self.assertIsNone(status["score"])


if __name__ == "__main__":
    unittest.main()
