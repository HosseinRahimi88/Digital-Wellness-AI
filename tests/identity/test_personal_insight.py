"""Tests: the dossier — time in the app, the cohort, and a model of one person.

Three new claims are made on the About page, and each has a specific
way of becoming a lie:

  * TIME IN THE APP is a measurement, so it has to be capped. A client
    that posts an hour per beat, or a tab left open over a weekend,
    must not be able to inflate it - the ceilings are the difference
    between a measurement and a number the browser asserted.
  * THE COHORT is synthetic training data, and in any distribution of
    this project the training CSV is absent. The shipped reference has
    to answer the same question the CSV does, or the comparison
    silently changes meaning between a developer's machine and a
    reviewer's.
  * A MODEL OF ONE PERSON is the easiest thing here to oversell. Fitted
    on eight days it will always produce a confident-looking in-sample
    R²; what stops that being a lie is the leave-one-out number and the
    refusals. Both are pinned here, including the refusal to fit at all
    below the floor.

Run: python3 -m unittest tests.identity.test_personal_insight -v
"""

from __future__ import annotations

import math
import shutil
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path

import tests._test_support  # noqa: F401

from fastapi.testclient import TestClient

from api.main import app
from services.ml import cohort_reference
from services.ml.cohort_service import COHORT_FIELDS, CohortService, _load_cohort_frame
from services.insight.personal_facts_service import build as build_facts
from services.insight.personal_model_service import MIN_DAYS, fit
from services.identity.personal_service import (
    MAX_DAY_SECONDS,
    MAX_HEARTBEAT_SECONDS,
    PersonalService,
    PersonalValidationError,
)
from services.storage.json_file_storage import JSONFileStorageBackend


def _day(offset: int) -> str:
    return (date.today() - timedelta(days=offset)).isoformat()


class UsageIsMeasuredNotAsserted(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="wellness_personal_test_"))
        self.path = self._tmp / "personal.json"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _service(self, user_id: str) -> PersonalService:
        return PersonalService(user_id, backend=JSONFileStorageBackend(self.path))

    def test_seconds_accumulate_per_day(self) -> None:
        svc = self._service("alice")
        svc.add_seconds(60)
        svc.add_seconds(90)
        usage = svc.usage()
        self.assertEqual(usage.today_seconds, 150)
        self.assertEqual(usage.days_present, 1)

    def test_one_beat_cannot_claim_more_than_its_ceiling(self) -> None:
        """A tab that was asleep wakes up owing hours. It may not post them."""
        svc = self._service("alice")
        svc.add_seconds(60 * 60 * 5)
        self.assertEqual(svc.usage().today_seconds, MAX_HEARTBEAT_SECONDS)

    def test_a_day_cannot_exceed_its_ceiling_either(self) -> None:
        svc = self._service("alice")
        for _ in range(400):
            svc.add_seconds(MAX_HEARTBEAT_SECONDS)
        self.assertEqual(svc.usage().today_seconds, MAX_DAY_SECONDS)

    def test_nonsense_is_refused_rather_than_stored(self) -> None:
        svc = self._service("alice")
        with self.assertRaises(PersonalValidationError):
            svc.add_seconds("ten minutes")
        # Negative and zero are simply nothing to add, not errors.
        svc.add_seconds(-50)
        self.assertEqual(svc.usage().total_seconds, 0)

    def test_one_persons_tally_is_not_anothers(self) -> None:
        self._service("alice").add_seconds(120)
        self._service("bob").add_seconds(30)
        self.assertEqual(self._service("alice").usage().total_seconds, 120)
        self.assertEqual(self._service("bob").usage().total_seconds, 30)

    def test_a_birth_date_in_the_future_is_refused(self) -> None:
        svc = self._service("alice")
        with self.assertRaises(PersonalValidationError):
            svc.set_birth_date((date.today() + timedelta(days=1)).isoformat())
        with self.assertRaises(PersonalValidationError):
            svc.set_birth_date("1850-01-01")
        with self.assertRaises(PersonalValidationError):
            svc.set_birth_date("not-a-date")

    def test_a_birth_date_can_be_forgotten(self) -> None:
        svc = self._service("alice")
        svc.set_birth_date("2000-05-04")
        self.assertEqual(svc.birth_date(), "2000-05-04")
        svc.set_birth_date(None)
        self.assertIsNone(svc.birth_date())

    def test_deleting_takes_both_halves(self) -> None:
        svc = self._service("alice")
        svc.add_seconds(120)
        svc.set_birth_date("2000-05-04")
        self.assertEqual(svc.delete_all(), 1)
        self.assertIsNone(self._service("alice").birth_date())
        self.assertEqual(self._service("alice").usage().total_seconds, 0)


class TheShippedCohortAnswersTheSameQuestion(unittest.TestCase):
    """The 14KB reference against the 83MB CSV it came from."""

    def test_the_reference_is_shipped_and_readable(self) -> None:
        self.assertTrue(
            cohort_reference.is_available(),
            "artifacts/cohort_reference.json is missing - every distributed "
            "copy would answer 'no cohort available'",
        )
        self.assertGreater(cohort_reference.cohort_size(), 1000)

    def test_every_compared_field_is_in_the_reference(self) -> None:
        data = cohort_reference.load()
        for field in COHORT_FIELDS:
            self.assertIn(
                field, data["fields"],
                f"{field} is compared in the UI but missing from the reference",
            )

    def test_the_reference_matches_the_csv_it_came_from(self) -> None:
        """Only runs where the training data is present - which is a
        developer's machine, never a distribution."""
        if _load_cohort_frame() is None:
            self.skipTest("data/train.csv is not present in this copy")
        for field, probes in (
            ("health_score_0_100", (40.0, 55.0, 64.0, 72.0, 85.0)),
            ("sleep_hours", (4.0, 6.0, 7.5, 9.0)),
            ("total_screen_min", (120.0, 300.0, 480.0, 700.0)),
        ):
            for value in probes:
                from_csv = CohortService.percentile_for(field, value)
                from_reference = cohort_reference.percentile_for(field, value)
                self.assertIsNotNone(from_reference, f"{field} missing from reference")
                self.assertLess(
                    abs(from_csv - from_reference), 1.0,
                    f"{field} at {value}: CSV says {from_csv}, reference says {from_reference}",
                )

    def test_the_source_is_named_rather_than_implied(self) -> None:
        self.assertIn(CohortService.source(), ("dataset", "reference"))


class AModelOfOnePerson(unittest.TestCase):

    @staticmethod
    def _history(days: int, driver: str = "sleep_hours", noise: float = 0.0) -> list[dict]:
        """Days where one signal really does drive the score."""
        rows = []
        for i in range(days):
            value = 4.0 + (i % 5)
            rows.append({
                "date": _day(days - i),
                "health_score": 40.0 + value * 5.0 + (noise * ((i % 3) - 1)),
                driver: value,
                # A second signal that never moves, so the fit has
                # something to correctly ignore.
                "stress_0_10": 5.0,
            })
        return rows

    def test_it_refuses_to_fit_too_few_days(self) -> None:
        model = fit(self._history(MIN_DAYS - 1))
        self.assertFalse(model.available)
        self.assertEqual(model.reason, "not_enough_days")
        self.assertEqual(model.drivers, [])

    def test_it_finds_the_signal_that_really_drives_the_score(self) -> None:
        model = fit(self._history(20))
        self.assertTrue(model.available, model.reason)
        self.assertEqual(model.drivers[0].field, "sleep_hours")
        self.assertEqual(model.drivers[0].direction, "up")
        self.assertGreater(model.r2, 0.9)

    def test_a_signal_that_never_moves_is_never_a_driver(self) -> None:
        model = fit(self._history(20))
        self.assertNotIn("stress_0_10", [d.field for d in model.drivers])

    def test_it_reports_leave_one_out_as_well_as_in_sample(self) -> None:
        """The in-sample number alone would be the most misleading
        figure in the app."""
        model = fit(self._history(20))
        self.assertIsNotNone(model.r2)
        self.assertIsNotNone(model.r2_loo)
        self.assertLessEqual(
            model.r2_loo, model.r2 + 1e-9,
            "leave-one-out beat in-sample, which cannot happen for a real fit",
        )

    def test_noise_is_not_dressed_up_as_a_finding(self) -> None:
        """Scores that do not follow the signal must not be trustworthy."""
        rows = []
        for i in range(14):
            rows.append({
                "date": _day(14 - i),
                # A score that jumps around independently of the signal.
                "health_score": 60.0 + (17 * i) % 23,
                "sleep_hours": 4.0 + (i % 5),
                "stress_0_10": 3.0 + (i % 4),
            })
        model = fit(rows)
        if model.available:
            self.assertFalse(
                model.trustworthy and model.r2_loo > 0.6,
                f"noise was reported as a confident fit: LOO {model.r2_loo}",
            )

    def test_a_flat_score_is_reported_as_nothing_to_explain(self) -> None:
        rows = [
            {"date": _day(10 - i), "health_score": 70.0, "sleep_hours": 4.0 + i}
            for i in range(10)
        ]
        model = fit(rows)
        self.assertFalse(model.available)
        self.assertEqual(model.reason, "score_never_moves")

    def test_every_number_it_reports_is_finite(self) -> None:
        model = fit(self._history(20, noise=3.0))
        for value in (model.r2, model.r2_loo, model.score_sd):
            self.assertTrue(value is None or math.isfinite(value), value)


class FactsAreMeasuredOrAbsent(unittest.TestCase):

    def test_no_history_produces_no_facts(self) -> None:
        self.assertEqual(build_facts([]), [])

    def test_the_journey_facts_come_from_the_real_dates(self) -> None:
        rows = [
            {"date": _day(4), "health_score": 60.0},
            {"date": _day(3), "health_score": 66.0},
            {"date": _day(2), "health_score": 71.0},
        ]
        kinds = {f["kind"]: f for f in build_facts(rows)}
        self.assertEqual(kinds["first_day"]["date"], _day(4))
        self.assertEqual(kinds["first_day"]["days_since"], 4)
        self.assertEqual(kinds["personal_best"]["score"], 71.0)
        self.assertEqual(kinds["longest_streak"]["days"], 3)

    def test_a_weekday_claim_needs_more_than_one_of_that_weekday(self) -> None:
        rows = [
            {"date": _day(offset), "health_score": 50.0 + offset}
            for offset in range(6)
        ]
        kinds = {f["kind"] for f in build_facts(rows)}
        self.assertNotIn(
            "best_weekday", kinds,
            "a weekday pattern was claimed from one sample of each weekday",
        )

    def test_day_of_life_facts_only_appear_with_a_birth_date(self) -> None:
        rows = [{"date": _day(1), "health_score": 70.0}]
        without = {f["kind"] for f in build_facts(rows)}
        self.assertNotIn("days_alive", without)
        with_date = {f["kind"]: f for f in build_facts(rows, birth_date="2000-02-29")}
        self.assertIn("days_alive", with_date)
        self.assertGreater(with_date["days_alive"]["days"], 8000)
        self.assertIn("next_birthday", with_date)

    def test_a_broken_birth_date_is_ignored_rather_than_crashing(self) -> None:
        rows = [{"date": _day(1), "health_score": 70.0}]
        kinds = {f["kind"] for f in build_facts(rows, birth_date="not-a-date")}
        self.assertNotIn("days_alive", kinds)


class TheDossierOverHttp(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        email = f"dossier-{time.time_ns()}@example.com"
        cls.client.post("/api/v1/auth/register", json={
            "email": email, "password": "Passw0rd!x", "display_name": "Dossier",
        })
        token = cls.client.post("/api/v1/auth/login", json={
            "email": email, "password": "Passw0rd!x",
        }).json()["access_token"]
        cls.auth = {"Authorization": f"Bearer {token}"}

    def test_it_needs_a_token(self) -> None:
        self.assertEqual(self.client.get("/api/v1/personal/insight").status_code, 401)
        self.assertEqual(
            self.client.post("/api/v1/personal/heartbeat", json={"seconds": 60}).status_code,
            401,
        )

    def test_a_fresh_account_gets_honest_emptiness(self) -> None:
        body = self.client.get("/api/v1/personal/insight", headers=self.auth).json()
        self.assertEqual(body["days_logged"], 0)
        self.assertFalse(body["model"]["available"])
        self.assertEqual(body["model"]["reason"], "not_enough_days")
        self.assertEqual(body["facts"], [])
        self.assertIsNone(body["birth_date"])

    def test_a_heartbeat_is_capped_server_side(self) -> None:
        """The client is not trusted with the ceiling."""
        over = self.client.post(
            "/api/v1/personal/heartbeat", json={"seconds": 9999}, headers=self.auth,
        )
        self.assertEqual(over.status_code, 422, "the schema should refuse an absurd beat")
        ok = self.client.post(
            "/api/v1/personal/heartbeat", json={"seconds": 600}, headers=self.auth,
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertLessEqual(ok.json()["today_seconds"], MAX_HEARTBEAT_SECONDS)

    def test_a_birth_date_round_trips_and_can_be_cleared(self) -> None:
        saved = self.client.put(
            "/api/v1/personal/birth-date", json={"birth_date": "1999-03-14"}, headers=self.auth,
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["birth_date"], "1999-03-14")
        cleared = self.client.put(
            "/api/v1/personal/birth-date", json={"birth_date": None}, headers=self.auth,
        )
        self.assertIsNone(cleared.json()["birth_date"])

    def test_a_future_birth_date_is_a_400(self) -> None:
        response = self.client.put(
            "/api/v1/personal/birth-date",
            json={"birth_date": (date.today() + timedelta(days=2)).isoformat()},
            headers=self.auth,
        )
        self.assertEqual(response.status_code, 400, response.text)

    def test_a_demo_arrives_with_a_full_dossier(self) -> None:
        session = self.client.post(
            "/api/v1/demo/session",
            json={"days": 15, "profile": "improving", "friends": 0, "with_violations": False},
            headers=self.auth,
        )
        self.assertEqual(session.status_code, 200, session.text)
        demo_auth = {"Authorization": f"Bearer {session.json()['access_token']}"}
        body = self.client.get("/api/v1/personal/insight", headers=demo_auth).json()

        self.assertGreater(body["usage"]["total_seconds"], 0, "no measured time in a demo")
        self.assertGreaterEqual(body["usage"]["days_present"], 5)
        self.assertIsNotNone(body["birth_date"], "a demo person has no birth date")
        self.assertTrue(body["model"]["available"], body["model"]["reason"])
        self.assertTrue(body["model"]["drivers"])
        self.assertTrue(body["cohort"]["available"])
        self.assertIn(body["cohort"]["source"], ("dataset", "reference"))
        kinds = {f["kind"] for f in body["facts"]}
        for expected in ("first_day", "personal_best", "days_alive", "screen_total"):
            self.assertIn(expected, kinds)

    def test_deleting_the_account_takes_the_dossier_with_it(self) -> None:
        email = f"dossier-gone-{time.time_ns()}@example.com"
        self.client.post("/api/v1/auth/register", json={
            "email": email, "password": "Passw0rd!x", "display_name": "Gone",
        })
        token = self.client.post("/api/v1/auth/login", json={
            "email": email, "password": "Passw0rd!x",
        }).json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}
        self.client.post("/api/v1/personal/heartbeat", json={"seconds": 120}, headers=auth)
        self.client.put("/api/v1/personal/birth-date", json={"birth_date": "1998-08-08"}, headers=auth)
        user_id = self.client.get("/api/v1/auth/me", headers=auth).json()["user_id"]
        self.assertEqual(PersonalService(user_id).usage().total_seconds, 120)

        self.assertEqual(self.client.delete("/api/v1/privacy/me", headers=auth).status_code, 200)
        self.assertEqual(PersonalService(user_id).usage().total_seconds, 0)
        self.assertIsNone(PersonalService(user_id).birth_date())


if __name__ == "__main__":
    unittest.main()
