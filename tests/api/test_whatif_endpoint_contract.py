"""The what-if endpoints must accept the same day /predict accepts.

THE DEFECT

    /predict      validator.validate(derive_features(user_data))
    /whatif/sweep validator.validate(user_data)

Fourteen of the fifty-three columns are computed, not typed:
total_screen_min, the five ratios, the three densities, fragmentation,
dependence, the two screen baselines. /predict derives them before
validating - that is how a browser can POST a form. The two what-if
endpoints did not, so the identical body came back 422 with
"This field is required" once per derived column, and the simulator did
nothing at all.

It looked like it worked only because the page happened to hold an
already-derived payload (/history/snapshots returns cleaned data, and
the check-in form derives client-side). Anything else - the OpenAPI
example, a script, a page starting from raw answers - hit the wall.
"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path bootstrap
from api.main import app
# The same isolated-storage harness the rest of the API tests use, so
# registering an account here never touches storage/.
from tests.api.test_api import APITestCase

RAW_DAY = {
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


class WhatIfAcceptsARawDay(APITestCase):
    def setUp(self):
        super().setUp()
        self.headers = self._auth_headers(self._register(email="whatif@example.com"))

    def test_predict_accepts_it(self):
        # The premise: this body is a valid day as far as /predict is
        # concerned. Without that, the two below prove nothing.
        response = self.client.post(
            "/api/v1/predict", headers=self.headers,
            json={"user_data": RAW_DAY, "persist": False})
        self.assertEqual(response.status_code, 200, response.text)

    def test_sweep_accepts_the_same_body(self):
        response = self.client.post(
            "/api/v1/whatif/sweep", headers=self.headers,
            json={"user_data": RAW_DAY, "field": "sleep_hours", "num_points": 5})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["points"]), 5)

    def test_goal_seek_accepts_the_same_body(self):
        response = self.client.post(
            "/api/v1/whatif/goal-seek", headers=self.headers,
            json={"user_data": RAW_DAY, "field": "sleep_hours",
                  "target_score": 80, "num_points": 5})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["available"])

    def test_a_day_that_is_genuinely_invalid_is_still_refused(self):
        # Deriving must not become a way to smuggle nonsense past the
        # validator: an age of 500 is still an age of 500.
        broken = dict(RAW_DAY, age=500)
        response = self.client.post(
            "/api/v1/whatif/sweep", headers=self.headers,
            json={"user_data": broken, "field": "sleep_hours", "num_points": 5})
        self.assertEqual(response.status_code, 422)


class TheSchemaSaysWhichFieldsAreComputed(unittest.TestCase):
    """`derived` is what lets a client stop offering a dead control.

    The simulator's field picker listed all forty-two numeric fields.
    Thirteen of them are computed by derive_features(), so sweeping one
    set a value that was overwritten a line later and the chart came
    back a flat line across the entire range - most visibly on
    total_screen_min, the single most obvious field to reach for.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.fields = cls.client.get("/api/v1/schema/features").json()

    def test_every_field_carries_the_flag(self):
        for field in self.fields:
            with self.subTest(field=field["name"]):
                self.assertIn("derived", field)

    def test_total_screen_min_is_reported_as_computed(self):
        field = next(f for f in self.fields if f["name"] == "total_screen_min")
        self.assertTrue(field["derived"])

    def test_the_ratios_and_densities_are_reported_as_computed(self):
        for name in ("social_ratio", "night_ratio", "notification_density",
                     "app_open_density", "fragmentation_index_0_100",
                     "digital_dependence_0_100"):
            with self.subTest(name=name):
                field = next(f for f in self.fields if f["name"] == name)
                self.assertTrue(field["derived"], f"{name} should be flagged as computed")

    def test_the_fields_a_person_answers_are_not_flagged(self):
        for name in ("sleep_hours", "social_min", "stress_0_10",
                     "physical_activity_min_per_day", "notifications_per_day"):
            with self.subTest(name=name):
                field = next(f for f in self.fields if f["name"] == name)
                self.assertFalse(field["derived"], f"{name} is answered, not computed")

    def test_the_flag_is_measured_rather_than_listed(self):
        """The probe must agree with what derive_features actually does.

        A hand-maintained list would drift the first time a formula
        moved, and drift silently.
        """
        from utils.feature_derivation import derive_features

        base = {f["name"]: 1.0 for f in self.fields
                if f["dtype"] in ("int", "float") and not f["choices"]}
        for field in self.fields:
            if field["dtype"] not in ("int", "float") or field["choices"]:
                continue
            probe = dict(base)
            probe[field["name"]] = -987654.0
            survived = derive_features(dict(probe)).get(field["name"]) == -987654.0
            with self.subTest(name=field["name"]):
                self.assertEqual(field["derived"], not survived)


if __name__ == "__main__":
    unittest.main()
