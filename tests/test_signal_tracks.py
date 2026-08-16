"""
Tests: the two halves of a week's plan.

A plan that only ever names what is wrong reads as a list of faults,
and it throws away the more useful half of the picture - the habits
that are already holding. So the plan produces two tracks:

  `strengthen` - the signals that need work, weakest first, ranked by
    exactly the same severity arithmetic the 7-day plan uses, so the
    two can never disagree about what is wrong.

  `maintain` - the signals comfortably the right side of their target.
    These are what the week is protecting.

The rules worth pinning are the ones that stop this becoming generic
advice:

  - a signal the user has not logged appears on NEITHER list. Guessing
    is the one thing this feature exists not to do;
  - "comfortably" is a real margin. A value one minute the right side
    of the line is not a habit worth protecting, and celebrating it
    would make the whole maintain list meaningless;
  - no signal is ever on both lists;
  - every entry carries the user's own number AND the target it is
    measured against, in all four languages.

Run: python3 -m unittest tests.test_signal_tracks -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from tests.test_api import APITestCase

LANGS = ("en", "fa", "ar", "zh")

HEALTHY = {
    "sleep_hours": 8.5, "social_min": 40, "stress_0_10": 3,
    "physical_activity_min_per_day": 60, "notifications_per_day": 45,
    "focus_0_100": 82,
}
STRUGGLING = {
    "sleep_hours": 4.0, "social_min": 300, "stress_0_10": 9,
    "physical_activity_min_per_day": 5, "notifications_per_day": 250,
    "focus_0_100": 30,
}
MIXED = {
    "sleep_hours": 8.2, "social_min": 300, "stress_0_10": 3,
    "physical_activity_min_per_day": 60, "notifications_per_day": 250,
    "focus_0_100": 82,
}


class TestSignalTracks(unittest.TestCase):

    def setUp(self):
        from services.improvement_plan_service import ImprovementPlanService
        self.service = ImprovementPlanService()

    def tracks(self, user_data, **kw):
        return self.service.signal_tracks(user_data, **kw)

    # ------------------------------------------------------- separation
    def test_a_struggling_day_has_things_to_strengthen_and_nothing_to_protect(self):
        t = self.tracks(STRUGGLING)
        self.assertTrue(t["strengthen"])
        self.assertEqual(t["maintain"], [])

    def test_a_healthy_day_has_things_to_protect_and_nothing_flagged(self):
        t = self.tracks(HEALTHY)
        self.assertEqual(t["strengthen"], [])
        self.assertTrue(t["maintain"])

    def test_a_mixed_day_splits_correctly(self):
        t = self.tracks(MIXED)
        weak = {e["field"] for e in t["strengthen"]}
        strong = {e["field"] for e in t["maintain"]}
        self.assertEqual(weak, {"social_min", "notifications_per_day"})
        self.assertIn("sleep_hours", strong)
        self.assertIn("physical_activity_min_per_day", strong)

    def test_no_signal_is_ever_on_both_lists(self):
        for profile in (HEALTHY, STRUGGLING, MIXED):
            t = self.tracks(profile)
            weak = {e["field"] for e in t["strengthen"]}
            strong = {e["field"] for e in t["maintain"]}
            self.assertFalse(weak & strong, f"{weak & strong} is on both lists")

    # ---------------------------------------------------------- honesty
    def test_an_unlogged_signal_appears_on_neither_list(self):
        # The whole point: no guessing. A field with no value is a field
        # the app has nothing true to say about.
        t = self.tracks({"sleep_hours": 8.5})
        fields = {e["field"] for e in t["strengthen"] + t["maintain"]}
        self.assertEqual(fields, {"sleep_hours"})

    def test_an_empty_check_in_yields_two_empty_lists(self):
        t = self.tracks({})
        self.assertEqual(t["strengthen"], [])
        self.assertEqual(t["maintain"], [])

    def test_a_value_barely_past_the_target_is_not_called_a_strength(self):
        # sleep target is 7.0. 7.1 hours is not a habit worth
        # protecting, and saying so would make the list meaningless.
        t = self.tracks({"sleep_hours": 7.1})
        self.assertEqual(t["maintain"], [])
        self.assertEqual(t["strengthen"], [])

    def test_a_value_comfortably_past_the_target_is(self):
        t = self.tracks({"sleep_hours": 8.5})
        self.assertEqual([e["field"] for e in t["maintain"]], ["sleep_hours"])

    def test_a_lower_is_better_signal_reads_the_right_direction(self):
        # social_min target is 90: 40 minutes is a strength, 300 is not.
        self.assertEqual(
            [e["field"] for e in self.tracks({"social_min": 40})["maintain"]],
            ["social_min"],
        )
        self.assertEqual(
            [e["field"] for e in self.tracks({"social_min": 300})["strengthen"]],
            ["social_min"],
        )

    def test_a_non_numeric_value_is_ignored_rather_than_coerced(self):
        t = self.tracks({"sleep_hours": "eight", "social_min": True})
        self.assertEqual(t["strengthen"], [])
        self.assertEqual(t["maintain"], [])

    # ---------------------------------------------------------- ranking
    def test_strengthen_is_ordered_weakest_first(self):
        severities = [e["severity"] for e in self.tracks(STRUGGLING)["strengthen"]]
        self.assertEqual(severities, sorted(severities, reverse=True))

    def test_maintain_is_ordered_by_how_much_room_there_is(self):
        margins = [e["margin"] for e in self.tracks(HEALTHY)["maintain"]]
        self.assertEqual(margins, sorted(margins, reverse=True))

    def test_the_tracks_agree_with_the_plans_own_focus_areas(self):
        # If these two disagreed, the coach would name one weakness and
        # the plan would work on another.
        plan = self.service.generate(
            health_class="At Risk", wellness_score=40, user_data=STRUGGLING,
        )
        top = self.tracks(STRUGGLING)["strengthen"][0]["theme"]
        self.assertIn(top, plan.focus_areas)

    def test_an_irregular_schedule_re_ranks_but_invents_nothing(self):
        regular = self.tracks(STRUGGLING, schedule_type="standard_day")
        irregular = self.tracks(STRUGGLING, schedule_type="rotating_shift")
        self.assertEqual(
            {e["field"] for e in regular["strengthen"]},
            {e["field"] for e in irregular["strengthen"]},
            "an irregular schedule invented a weakness the numbers did not flag",
        )
        by_field = {e["field"]: e["severity"] for e in irregular["strengthen"]}
        self.assertGreaterEqual(
            by_field["sleep_hours"],
            {e["field"]: e["severity"] for e in regular["strengthen"]}["sleep_hours"],
        )

    # ------------------------------------------------------------ shape
    def test_every_entry_carries_the_users_number_and_its_target(self):
        for profile in (HEALTHY, STRUGGLING, MIXED):
            t = self.tracks(profile)
            for entry in t["strengthen"] + t["maintain"]:
                self.assertIn("current", entry)
                self.assertIn("target", entry)
                self.assertIsInstance(entry["current"], float)
                self.assertIsInstance(entry["target"], float)

    def test_every_theme_name_comes_in_four_languages(self):
        for entry in self.tracks(STRUGGLING)["strengthen"]:
            for lang in LANGS:
                self.assertTrue(
                    entry["theme_i18n"].get(lang, "").strip(),
                    f"{entry['theme']} has no {lang} name",
                )

    def test_a_personal_drop_reaches_the_strengthen_track(self):
        # 7.4h is above the 7h target, so absolutely fine - but well
        # below this user's own 9h normal, which is exactly the drift
        # the personal baseline exists to catch.
        history = [{"sleep_hours": 9.0} for _ in range(6)]
        plain = self.tracks({"sleep_hours": 7.4})
        with_history = self.tracks({"sleep_hours": 7.4}, history=history)
        self.assertEqual(plain["strengthen"], [])
        self.assertEqual(
            [e["field"] for e in with_history["strengthen"]], ["sleep_hours"],
        )


class TestSignalTracksEndpoint(APITestCase):

    def setUp(self):
        super().setUp()
        self.headers = self._auth_headers(self._register(email="tracks@example.com"))
        # Both plan-side stores live in the backend APITestCase injects
        # (a fresh temp file per test), so nothing here touches the real
        # storage/*.json.

    def _tracks(self):
        response = self.client.get("/api/v1/plan/tracks", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_an_account_with_nothing_logged_gets_two_empty_lists(self):
        # The honest answer. Generic advice about signals nobody has
        # measured is exactly what this feature is not.
        body = self._tracks()
        self.assertEqual(body["strengthen"], [])
        self.assertEqual(body["maintain"], [])
        self.assertIsNone(body["based_on_date"])

    def test_it_reads_the_users_real_stored_check_in(self):
        import config.demo_profiles as dp
        self.client.post(
            "/api/v1/predict", headers=self.headers,
            json={"user_data": dp.at_risk_profile()},
        )
        body = self._tracks()
        self.assertTrue(body["strengthen"], body)
        self.assertIsNotNone(body["based_on_date"])
        entry = body["strengthen"][0]
        self.assertIn("current", entry)
        self.assertIn("target", entry)
        for lang in LANGS:
            self.assertTrue(entry["theme_i18n"].get(lang))

    def test_it_is_not_built_from_anything_the_client_sends(self):
        # A GET with no body at all: a browser's localStorage is not a
        # trustworthy source for this, and a second device has none.
        import config.demo_profiles as dp
        self.client.post(
            "/api/v1/predict", headers=self.headers,
            json={"user_data": dp.healthy_profile()},
        )
        first = self._tracks()
        second = self._tracks()
        self.assertEqual(first, second)

    def test_it_requires_a_login(self):
        response = self.client.get("/api/v1/plan/tracks")
        self.assertEqual(response.status_code, 401)

    def test_one_users_tracks_are_not_another_users(self):
        import config.demo_profiles as dp
        self.client.post(
            "/api/v1/predict", headers=self.headers,
            json={"user_data": dp.at_risk_profile()},
        )
        other = self._auth_headers(self._register(email="other-tracks@example.com"))
        body = self.client.get("/api/v1/plan/tracks", headers=other).json()
        self.assertEqual(body["strengthen"], [])
        self.assertEqual(body["maintain"], [])


if __name__ == "__main__":
    unittest.main()
