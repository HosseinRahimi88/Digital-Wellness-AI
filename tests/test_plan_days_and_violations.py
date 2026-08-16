"""
Tests: the week runs in order, and a missed day costs something.

Two rules, and they only work together.

  DAY LOCKING. Day 1 is open; day N+1 opens once day N is fully ticked.
  Enforced on the server, not only in the UI - a locked day that a
  direct PUT can tick anyway is not locked, and "you missed a day" only
  means anything if the days had to be done in order.

  THE COST. A plan day whose date has passed with the day undone costs
  a badge. With no badges left it is recorded as a violation instead.
  While violations are outstanding a newly earned badge is SPENT
  clearing one rather than registering, and only once the count reaches
  zero do badges start counting again.

The things most worth pinning are the ways this could quietly do harm:

  - charging twice for the same day (opening the app three times on
    Thursday must not cost three badges for Wednesday);
  - charging for TODAY, a day the user has not finished living;
  - charging at all when the plan has no recorded start date, where the
    app does not actually know which calendar day a plan day was;
  - taking a PRIVATE awareness indicator as payment. Those name a
    pattern worth a look, not something the user won.

Run: python3 -m unittest tests.test_plan_days_and_violations -v
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


class TestUnlockedThrough(unittest.TestCase):
    """The sequencing rule on its own, with no HTTP in the way."""

    def setUp(self):
        from services.violation_service import unlocked_through
        self.unlocked_through = unlocked_through

    def test_day_one_is_open_from_the_start(self):
        self.assertEqual(self.unlocked_through(set(), {1: 2, 2: 2, 3: 2}), 1)

    def test_a_partly_done_day_does_not_open_the_next(self):
        self.assertEqual(self.unlocked_through({(1, 0)}, {1: 2, 2: 2}), 1)

    def test_finishing_a_day_opens_the_next(self):
        self.assertEqual(self.unlocked_through({(1, 0), (1, 1)}, {1: 2, 2: 2}), 2)

    def test_it_stops_at_the_first_gap(self):
        # Ticks on day 3 cannot open day 4 while day 2 is unfinished -
        # otherwise a user could skip ahead and the sequence means
        # nothing.
        completed = {(1, 0), (1, 1), (3, 0), (3, 1)}
        self.assertEqual(self.unlocked_through(completed, {1: 2, 2: 2, 3: 2, 4: 2}), 2)

    def test_a_day_with_no_tasks_does_not_block_the_week(self):
        self.assertEqual(self.unlocked_through(set(), {1: 0, 2: 2}), 1)


class TestPlanDaysAndViolations(APITestCase):

    def setUp(self):
        super().setUp()
        self.headers = self._auth_headers(self._register(email="seq@example.com"))
        self.me = self.client.get("/api/v1/auth/me", headers=self.headers).json()

        # The plan lock, the day decisions and the violation ledger all
        # live in the backend APITestCase injects (a fresh temp file per
        # test), so nothing here touches the real storage/*.json.

    # ------------------------------------------------------------ helpers
    def _plan(self):
        response = self.client.post(
            "/api/v1/plan", headers=self.headers,
            json={"health_class": "Healthy", "wellness_score": 80,
                  "persona": None, "user_data": HEALTHY},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _tick(self, day_number, task_index, completed=True):
        return self.client.put(
            "/api/v1/plan/tasks", headers=self.headers,
            json={"day_number": day_number, "task_index": task_index,
                  "completed": completed},
        )

    def _finish_day(self, plan, day_number):
        day = next(d for d in plan["days"] if d["day_number"] == day_number)
        for task in day["tasks"]:
            response = self._tick(day_number, task["task_index"])
            self.assertEqual(response.status_code, 200, response.text)

    def _backdate_plan(self, days_ago):
        """Move the stored plan's start date into the past.

        The only way to reach "a plan day whose date has passed" inside
        a test that runs in a second, and it edits the same field the
        router reads (`created_at_utc`) rather than mocking the clock,
        so what is exercised is the real code path.
        """
        from services.plan_lock_service import PlanLockService
        service = PlanLockService(self.me["user_id"], backend=self._plan_side_backend)
        backend = service._backend
        stamp = (date.today() - timedelta(days=days_ago)).isoformat() + "T09:00:00+00:00"
        with backend.transaction() as records:
            rows = list(records)
            for row in rows:
                if row.get("user_id") == self.me["user_id"]:
                    row["created_at_utc"] = stamp
            backend.commit(rows)

    def _violations(self):
        from services.violation_service import ViolationService
        return ViolationService(self.me["user_id"], backend=self._plan_side_backend).state()

    # ------------------------------------------------------- day locking
    def test_the_first_day_is_open(self):
        plan = self._plan()
        self.assertEqual(plan["unlocked_through"], 1)
        self.assertFalse(plan["days"][0]["locked"])

    def test_later_days_start_locked(self):
        plan = self._plan()
        self.assertTrue(plan["days"][1]["locked"])
        self.assertTrue(plan["days"][6]["locked"])

    def test_ticking_a_locked_day_is_refused(self):
        self._plan()
        response = self._tick(2, 0)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["error"]["code"], "plan_day_locked")

    def test_a_refused_tick_is_not_quietly_saved_anyway(self):
        plan = self._plan()
        self._tick(2, 0)
        again = self._plan()
        day_two = next(d for d in again["days"] if d["day_number"] == 2)
        self.assertFalse(any(t["completed"] for t in day_two["tasks"]))
        self.assertEqual(again["unlocked_through"], plan["unlocked_through"])

    def test_finishing_day_one_opens_day_two(self):
        plan = self._plan()
        self._finish_day(plan, 1)
        after = self._plan()
        self.assertEqual(after["unlocked_through"], 2)
        self.assertFalse(next(d for d in after["days"] if d["day_number"] == 2)["locked"])
        self.assertEqual(self._tick(2, 0).status_code, 200)

    def test_unticking_is_never_gated(self):
        # A mis-tap on the last task of a day must be undoable. Gating
        # the un-tick would make one wrong tap permanent.
        plan = self._plan()
        self._finish_day(plan, 1)
        self.assertEqual(self._tick(2, 0).status_code, 200)
        self.assertEqual(self._tick(2, 0, completed=False).status_code, 200)
        # And undoing day 1 closes day 2 again.
        self.assertEqual(self._tick(1, 0, completed=False).status_code, 200)
        self.assertEqual(self._plan()["unlocked_through"], 1)

    def test_each_day_carries_the_date_it_falls_on(self):
        plan = self._plan()
        self.assertEqual(plan["days"][0]["day_date"], plan["generated_on"])
        expected = (date.fromisoformat(plan["generated_on"]) + timedelta(days=2)).isoformat()
        self.assertEqual(plan["days"][2]["day_date"], expected)

    # -------------------------------------------------------- the cost
    def test_today_is_never_charged_for(self):
        # The day is not over. Penalising someone at breakfast for a day
        # they have not finished living would simply be wrong.
        self._plan()
        self._plan()
        self.assertEqual(self._violations().missed_days, 0)

    def test_a_past_day_left_undone_is_charged_for(self):
        self._plan()
        self._backdate_plan(2)
        self._plan()
        self.assertGreaterEqual(self._violations().missed_days, 1)

    def test_a_past_day_that_was_done_costs_nothing(self):
        plan = self._plan()
        self._finish_day(plan, 1)
        self._backdate_plan(1)
        self._plan()
        state = self._violations()
        self.assertEqual(state.missed_days, 0, "a completed day was charged for")

    def test_the_same_day_is_never_charged_for_twice(self):
        self._plan()
        self._backdate_plan(2)
        self._plan()
        first = self._violations().missed_days
        self._plan()
        self._plan()
        self.assertEqual(
            self._violations().missed_days, first,
            "opening the app again charged for the same day a second time",
        )

    def test_a_plan_with_no_start_date_charges_nobody(self):
        # Not knowing which calendar day a plan day was is a reason to
        # charge nobody, not a reason to guess.
        self._plan()
        from services.plan_lock_service import PlanLockService
        backend = PlanLockService(self.me["user_id"], backend=self._plan_side_backend)._backend
        with backend.transaction() as records:
            rows = list(records)
            for row in rows:
                row["created_at_utc"] = ""
            backend.commit(rows)
        self._plan()
        self.assertEqual(self._violations().missed_days, 0)

    def test_a_miss_with_no_badges_becomes_a_violation(self):
        # A brand-new account has no earned achievement badges, so there
        # is nothing to spend and the miss is recorded as a violation.
        self._plan()
        self._backdate_plan(2)
        plan = self._plan()
        self.assertGreaterEqual(plan["open_violations"], 1)
        self.assertEqual(plan["revoked_badges"], [])

    def test_the_violation_count_is_reported_to_the_client(self):
        self._plan()
        self._backdate_plan(3)
        plan = self._plan()
        self.assertEqual(plan["open_violations"], self._violations().open_violations)

    # ------------------------------------------------------ the ledger
    def test_a_badge_pays_for_a_miss_before_a_violation_is_recorded(self):
        from services.violation_service import ViolationService
        service = ViolationService(self.me["user_id"], backend=self._plan_side_backend)
        penalty = service.assess_day("2026-W01", 1, "2026-01-01", ["first_checkin"])
        self.assertEqual(penalty, "badge_revoked")
        state = service.state()
        self.assertEqual(state.open_violations, 0)
        self.assertEqual(state.revoked_badge_ids, ["first_checkin"])

    def test_the_same_badge_is_never_spent_twice(self):
        from services.violation_service import ViolationService
        service = ViolationService(self.me["user_id"], backend=self._plan_side_backend)
        service.assess_day("2026-W01", 1, "2026-01-01", ["only_badge"])
        service.assess_day("2026-W01", 2, "2026-01-02", ["only_badge"])
        state = service.state()
        self.assertEqual(state.revoked_badge_ids, ["only_badge"])
        self.assertEqual(
            state.open_violations, 1,
            "the second miss re-spent a badge that was already gone",
        )

    def test_a_new_badge_clears_one_violation_and_does_not_register(self):
        from services.violation_service import ViolationService
        service = ViolationService(self.me["user_id"], backend=self._plan_side_backend)
        service.assess_day("2026-W01", 1, "2026-01-01", [])
        service.assess_day("2026-W01", 2, "2026-01-02", [])
        self.assertEqual(service.state().open_violations, 2)

        spent = service.absorb(["shiny_new_badge"])
        self.assertEqual(spent, ["shiny_new_badge"])
        self.assertEqual(service.state().open_violations, 1)

    def test_badges_register_normally_once_the_count_reaches_zero(self):
        from services.violation_service import ViolationService
        service = ViolationService(self.me["user_id"], backend=self._plan_side_backend)
        service.assess_day("2026-W01", 1, "2026-01-01", [])
        service.absorb(["clears_it"])
        self.assertEqual(service.state().open_violations, 0)

        spent = service.absorb(["free_and_clear"])
        self.assertEqual(spent, [], "a badge was spent with nothing left to pay for")
        self.assertIn("free_and_clear", service.acked_badge_ids())

    def test_a_spent_badge_is_not_offered_again_on_the_next_read(self):
        from services.violation_service import ViolationService
        service = ViolationService(self.me["user_id"], backend=self._plan_side_backend)
        service.assess_day("2026-W01", 1, "2026-01-01", [])
        service.assess_day("2026-W01", 2, "2026-01-02", [])
        service.absorb(["one_badge"])
        self.assertIn("one_badge", service.state().consumed_badge_ids)
        self.assertEqual(service.state().open_violations, 1)

    # ------------------------------------------------------ the endpoint
    def test_the_badges_endpoint_reports_the_violation_count(self):
        self._plan()
        self._backdate_plan(2)
        self._plan()
        response = self.client.get("/api/v1/badges", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertGreaterEqual(response.json()["open_violations"], 1)

    def test_a_revoked_badge_is_reported_as_spent_not_as_never_won(self):
        from services.violation_service import ViolationService
        # A real check-in first - a brand-new account has no earned
        # badge to spend, and a skipped test proves nothing.
        import config.demo_profiles as dp
        recorded = self.client.post(
            "/api/v1/predict", headers=self.headers,
            json={"user_data": dp.healthy_profile()},
        )
        self.assertEqual(recorded.status_code, 200, recorded.text)

        badges = self.client.get("/api/v1/badges", headers=self.headers).json()["badges"]
        earned = [b for b in badges if b["earned"] and not b["private"]]
        self.assertTrue(
            earned,
            "one real check-in earned no public achievement badge, so this "
            "test cannot exercise revocation - the fixture needs revisiting",
        )

        ViolationService(self.me["user_id"], backend=self._plan_side_backend).assess_day(
            "2026-W01", 1, "2026-01-01", [earned[0]["id"]],
        )
        after = self.client.get("/api/v1/badges", headers=self.headers).json()
        badge = next(b for b in after["badges"] if b["id"] == earned[0]["id"])
        self.assertFalse(badge["earned"])
        self.assertTrue(badge["revoked"], "a spent badge must not read as one never won")
        self.assertIn(earned[0]["id"], after["revoked_badges"])

    def _seed_history_that_earns_both_kinds(self):
        """Twenty real-shaped days that earn public achievements AND
        private awareness indicators.

        Needed because the check is "no private indicator is offered as
        payment": with nothing private earned, that check passes for the
        wrong reason. This fixture earns aware_late_night,
        aware_high_stress, aware_low_focus, aware_social_heavy and
        aware_rising_screen_time alongside first_checkin, log_streak_7
        and the rest, so both halves are real.
        """
        from api.dependencies.services import get_history_storage_backend
        backend = self.app.dependency_overrides[get_history_storage_backend]()
        today = date.today()
        with backend.transaction() as records:
            rows = list(records)
            for i in range(20, 0, -1):
                day = today - timedelta(days=i)
                rows.append({
                    "user_id": self.me["user_id"], "date": day.isoformat(),
                    "day_of_week": day.strftime("%A"),
                    "health_score": 40 + (20 - i) * 0.2,
                    "health_class": "At Risk", "excluded": False,
                    "total_screen_min": 200 + (20 - i) * 12,
                    "sleep_hours": 4 + ((i % 4) * 1.3),
                    "night_screen_min": 90, "social_min": 250,
                    "stress_0_10": 8, "focus_0_100": 35,
                    "notifications_per_day": 220,
                })
            backend.commit(rows)
        return backend

    def test_a_private_indicator_is_never_taken_as_payment(self):
        # Awareness indicators name a pattern worth a look, not
        # something the user won. Spending one would be meaningless.
        from api.routers.plan import _revocable_badge_ids
        backend = self._seed_history_that_earns_both_kinds()
        account = self._test_account_service.get_by_email("seq@example.com")
        self.assertIsNotNone(account, "account lookup shape changed")

        all_badges = self.client.get("/api/v1/badges", headers=self.headers).json()["badges"]
        private_earned = {b["id"] for b in all_badges if b["private"] and b["earned"]}
        self.assertTrue(
            private_earned,
            "this fixture earned no private indicator, so the check below "
            "would pass for the wrong reason",
        )

        ids = _revocable_badge_ids(account, backend)
        self.assertTrue(ids, "no public badge was offered as payment either")
        self.assertFalse(
            set(ids) & private_earned,
            "a private awareness indicator was offered up as payment",
        )

    def test_the_public_endpoint_still_hides_private_badges(self):
        # The ledger must not have widened what the friend-facing
        # endpoint is willing to send.
        response = self.client.get("/api/v1/badges/public", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse([b for b in response.json()["badges"] if b["private"]])


if __name__ == "__main__":
    unittest.main()
