"""Reopening a past day on the result screen.

Clicking a day in the history/heatmap has to bring back *that day* - the
score it was given, the factors it was given, and the answers that
produced them - not a fresh prediction wearing an old date.

The distinction matters because the classifier reads the user's earlier
check-ins as trend features. Re-predicting an old day today scores it
against history that did not exist then, so it would disagree with the
number already shown in that day's heatmap cell. These tests pin that
the stored output is replayed, not recomputed, and that a day with no
stored detail is refused rather than reconstructed from its summary
fields.

Run: python3 -m unittest tests.test_history_detail -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path bootstrap

import config.demo_profiles as dp

from tests.test_api import APITestCase


class TestReopeningAPastDay(APITestCase):

    def _record_a_day(
        self, token: str, profile: dict | None = None, allow_update: bool = False,
    ) -> dict:
        response = self.client.post(
            "/api/v1/predict",
            json={
                "user_data": profile or dp.healthy_profile(),
                "allow_update": allow_update,
            },
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_a_reopened_day_returns_the_score_it_was_given(self):
        token = self._register()
        original = self._record_a_day(token)
        date = self.client.get(
            "/api/v1/history", headers=self._auth_headers(token)
        ).json()["items"][0]["date"]

        response = self.client.get(
            f"/api/v1/history/{date}/detail", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 200, response.text)
        detail = response.json()

        # The headline numbers must be the same reading, not a re-run.
        self.assertEqual(
            detail["result"]["regression_score"], original["regression_score"]
        )
        self.assertEqual(detail["result"]["prediction"], original["prediction"])
        self.assertEqual(detail["result"]["probabilities"], original["probabilities"])
        self.assertEqual(detail["date"], date)

    def test_the_same_factors_come_back_in_the_same_order(self):
        # The result screen lists "what drove this" - reopening a day
        # must not reshuffle or re-rank that list.
        token = self._register()
        original = self._record_a_day(token)
        date = self.client.get(
            "/api/v1/history", headers=self._auth_headers(token)
        ).json()["items"][0]["date"]

        replayed = self.client.get(
            f"/api/v1/history/{date}/detail", headers=self._auth_headers(token)
        ).json()["result"]

        self.assertTrue(original["shap_features"], "fixture produced no SHAP factors")
        self.assertEqual(
            [f["feature"] for f in replayed["shap_features"]],
            [f["feature"] for f in original["shap_features"]],
        )
        self.assertEqual(
            [round(f["shap_value"], 9) for f in replayed["shap_features"]],
            [round(f["shap_value"], 9) for f in original["shap_features"]],
        )

    def test_the_answers_come_back_in_full_so_the_form_can_be_refilled(self):
        # Reopening exists so the user can re-run a day with one thing
        # changed. Refilling from the ~20 summary fields the entry used
        # to carry would silently submit a different check-in.
        token = self._register()
        profile = dp.healthy_profile()
        self._record_a_day(token, profile)
        date = self.client.get(
            "/api/v1/history", headers=self._auth_headers(token)
        ).json()["items"][0]["date"]

        inputs = self.client.get(
            f"/api/v1/history/{date}/detail", headers=self._auth_headers(token)
        ).json()["inputs"]

        for field, value in profile.items():
            with self.subTest(field=field):
                self.assertIn(field, inputs)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    self.assertAlmostEqual(float(inputs[field]), float(value), places=6)
                else:
                    self.assertEqual(inputs[field], value)

    def test_a_reopened_day_carries_the_whole_result_screen(self):
        # Everything downstream of the model is regenerated, so a
        # reopened day must arrive complete rather than as a stub the UI
        # then has to paper over.
        token = self._register()
        self._record_a_day(token)
        date = self.client.get(
            "/api/v1/history", headers=self._auth_headers(token)
        ).json()["items"][0]["date"]

        result = self.client.get(
            f"/api/v1/history/{date}/detail", headers=self._auth_headers(token)
        ).json()["result"]

        for key in ("recommendations", "dimension_breakdown", "confidence_label",
                    "ood", "result_framing", "future_score", "uncertainty"):
            with self.subTest(key=key):
                self.assertIn(key, result)
                self.assertIsNotNone(result[key], f"{key} came back empty")
        self.assertTrue(result["dimension_breakdown"]["dimensions"])

    def test_two_different_days_reopen_as_two_different_days(self):
        # A single stored snapshot serving every date would pass every
        # assertion above.
        token = self._register()
        headers = self._auth_headers(token)

        healthy = self._record_a_day(token, dp.healthy_profile())
        # Same user, same date -> record() upserts, so overwrite today
        # with a clearly different day and check the reopen follows.
        # `allow_update` is what makes that overwrite legal: one main
        # check-in per day is enforced now, and a second persisted
        # submission without the flag is refused precisely so a real
        # recorded result cannot be destroyed as a side effect (see
        # tests/test_one_check_in_per_day.py). Here the overwrite is the
        # point of the test, so it asks for it explicitly.
        at_risk = self._record_a_day(token, dp.at_risk_profile(), allow_update=True)
        self.assertNotEqual(healthy["regression_score"], at_risk["regression_score"],
                            "fixtures are too similar to prove anything")

        date = self.client.get("/api/v1/history", headers=headers).json()["items"][0]["date"]
        detail = self.client.get(f"/api/v1/history/{date}/detail", headers=headers).json()
        self.assertEqual(detail["result"]["regression_score"], at_risk["regression_score"])

    def test_one_users_day_is_never_reachable_by_another(self):
        token_a = self._register("a@example.com")
        token_b = self._register("b@example.com")

        self._record_a_day(token_a)
        date = self.client.get(
            "/api/v1/history", headers=self._auth_headers(token_a)
        ).json()["items"][0]["date"]

        response = self.client.get(
            f"/api/v1/history/{date}/detail", headers=self._auth_headers(token_b)
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_reopening_requires_a_login(self):
        response = self.client.get("/api/v1/history/2026-01-01/detail")
        self.assertIn(response.status_code, (401, 403), response.text)

    def test_a_day_that_was_never_recorded_is_a_plain_not_found(self):
        token = self._register()
        response = self.client.get(
            "/api/v1/history/2001-01-01/detail", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["error"]["code"], "history_entry_not_found"
        )


class TestDaysThatCannotBeReopened(APITestCase):
    """Entries written before snapshots existed, or with damaged ones.

    These must be refused with a reason - never rebuilt from the summary
    fields, which would show the user a check-in they never submitted.
    """

    def _stored_day_without_snapshot(self, token: str, mutate) -> str:
        from api.dependencies.services import get_history_storage_backend

        self.client.post(
            "/api/v1/predict",
            json={"user_data": dp.healthy_profile()},
            headers=self._auth_headers(token),
        )
        backend = self.app.dependency_overrides[get_history_storage_backend]()
        entries = backend.read_all()
        self.assertTrue(entries)
        for entry in entries:
            mutate(entry)
        backend.commit(entries)
        return entries[0]["date"]

    def test_an_entry_from_before_snapshots_is_refused_with_a_reason(self):
        token = self._register()
        date = self._stored_day_without_snapshot(token, lambda e: e.pop("snapshot", None))

        response = self.client.get(
            f"/api/v1/history/{date}/detail", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(
            response.json()["error"]["code"], "history_detail_unavailable"
        )

    def test_the_summary_endpoint_still_works_for_those_days(self):
        # The day is not lost - only its full detail is. The heatmap and
        # the summary view must keep working.
        token = self._register()
        date = self._stored_day_without_snapshot(token, lambda e: e.pop("snapshot", None))

        response = self.client.get(
            f"/api/v1/history/{date}", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNotNone(response.json()["health_score"])

    def test_a_snapshot_with_no_inputs_is_refused_rather_than_half_rendered(self):
        token = self._register()
        date = self._stored_day_without_snapshot(
            token, lambda e: e["snapshot"].update({"inputs": {}})
        )
        response = self.client.get(
            f"/api/v1/history/{date}/detail", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(
            response.json()["error"]["code"], "history_detail_unavailable"
        )

    def test_a_snapshot_from_an_unknown_future_version_is_refused(self):
        token = self._register()
        date = self._stored_day_without_snapshot(
            token, lambda e: e["snapshot"].update({"version": 99})
        )
        response = self.client.get(
            f"/api/v1/history/{date}/detail", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 404, response.text)


class TestSnapshotContents(unittest.TestCase):
    """The stored shape itself, without the HTTP layer."""

    def test_a_snapshot_keeps_every_submitted_field_not_just_tracked_ones(self):
        from services.history_service import TRACKED_FIELDS, HistoryService

        profile = dp.healthy_profile()
        snapshot = HistoryService._build_snapshot(profile, _FakeResult())

        self.assertEqual(snapshot["version"], HistoryService.SNAPSHOT_VERSION)
        self.assertEqual(set(snapshot["inputs"]), set(profile))
        # The point of storing inputs separately: there are more of them
        # than the summary list carries.
        self.assertGreater(len(snapshot["inputs"]), len(TRACKED_FIELDS))

    def test_the_snapshot_is_a_copy_not_a_live_reference(self):
        # The caller keeps using `user_data` after record(); a shared
        # dict would let later edits rewrite history.
        from services.history_service import HistoryService

        profile = dp.healthy_profile()
        snapshot = HistoryService._build_snapshot(profile, _FakeResult())
        original = profile["sleep_hours"]
        profile["sleep_hours"] = 99.0
        self.assertEqual(snapshot["inputs"]["sleep_hours"], original)

    def test_a_result_with_no_uncertainty_stores_none_not_a_fake_one(self):
        from services.history_service import HistoryService

        snapshot = HistoryService._build_snapshot(dp.healthy_profile(), _FakeResult())
        self.assertIsNone(snapshot["model_output"]["uncertainty"])


class _FakeResult:
    """Minimal stand-in - _build_snapshot only reads attributes."""

    prediction = "Healthy"
    confidence = 0.9
    probabilities = {"Healthy": 0.9}
    regression_score = 84.49
    model_name = "test"
    prediction_time_ms = 1.0
    timestamp = "2026-08-12T00:00:00"
    shap_features: list = []
    uncertainty = None


if __name__ == "__main__":
    unittest.main()
