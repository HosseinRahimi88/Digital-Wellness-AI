"""
Tests: one main check-in per day, and editing it is deliberate.

The bug these lock down was reproduced live against the running app
with a real account. Two persisted predictions were submitted on the
same date - the first scored 84.01, the second 78.41 - and afterwards
history held exactly ONE entry for that day: the 78.41. The 84.01 was
gone. HistoryService.record() is an upsert keyed on (user_id, date), so
the second submission silently overwrote the first, and nothing in the
API or the UI said so.

Overwriting is not the wrong behaviour - a user editing today's answers
genuinely wants the day replaced. Doing it as a *side effect* is. So a
second persisted submission is now refused with 409
`already_checked_in_today` unless the client sends `allow_update`, which
the check-in page only sets when the user has ticked "edit today's
check-in"; and when a replacement does happen the response says
`replaced_existing: true` so the page can say "updated" rather than
"saved" and can refresh the weekly plan behind it.

The same rule covers CSV upload, which is the sneakier path: the
questionnaire export is a single undated row, and an undated single row
is filed under *today* - exactly the day most likely to already exist.

Run: python3 -m unittest tests.wellness.test_one_check_in_per_day -v
"""

from __future__ import annotations

import io
import unittest
from datetime import date

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from tests.api.test_api import APITestCase


class TestOneCheckInPerDay(APITestCase):

    def setUp(self):
        super().setUp()
        self.headers = self._auth_headers(self._register(email="oneperday@example.com"))

    def _predict(self, profile, **extra):
        return self.client.post(
            "/api/v1/predict",
            json={"user_data": profile, **extra},
            headers=self.headers,
        )

    def _profiles(self):
        import config.demo_profiles as dp
        return dp.healthy_profile(), dp.at_risk_profile()

    # ------------------------------------------------------------ refusal
    def test_the_first_check_in_of_the_day_is_saved(self):
        healthy, _ = self._profiles()
        response = self._predict(healthy)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["persisted"])
        self.assertFalse(response.json()["replaced_existing"])

    def test_a_second_check_in_the_same_day_is_refused(self):
        healthy, at_risk = self._profiles()
        self._predict(healthy)
        second = self._predict(at_risk)
        self.assertEqual(second.status_code, 409, second.text)
        self.assertEqual(second.json()["error"]["code"], "already_checked_in_today")

    def test_the_refusal_leaves_the_first_days_result_intact(self):
        # The actual damage from the live bug: a real recorded score
        # disappearing. A 409 that still wrote would be worse than no
        # 409 at all.
        healthy, at_risk = self._profiles()
        first_score = self._predict(healthy).json()["regression_score"]
        self._predict(at_risk)

        entries = self.client.get("/api/v1/history", headers=self.headers).json()["items"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["health_score"], first_score)

    def test_the_refusal_names_the_day_and_says_what_to_do(self):
        healthy, at_risk = self._profiles()
        self._predict(healthy)
        message = self._predict(at_risk).json()["error"]["message"]
        self.assertIn(date.today().isoformat(), message)
        self.assertIn("Enable editing", message)

    # ------------------------------------------------------------- update
    def test_allow_update_replaces_the_day_and_says_so(self):
        healthy, at_risk = self._profiles()
        self._predict(healthy)
        updated = self._predict(at_risk, allow_update=True)
        self.assertEqual(updated.status_code, 200, updated.text)
        body = updated.json()
        self.assertTrue(body["persisted"])
        self.assertTrue(
            body["replaced_existing"],
            "a replacement that reports itself as a fresh save leaves the "
            "client unable to tell the user their earlier result is gone",
        )

    def test_the_updated_value_is_what_history_now_holds(self):
        healthy, at_risk = self._profiles()
        self._predict(healthy)
        new_score = self._predict(at_risk, allow_update=True).json()["regression_score"]

        entries = self.client.get("/api/v1/history", headers=self.headers).json()["items"]
        self.assertEqual(len(entries), 1, "an update must not add a second row for the same day")
        self.assertEqual(entries[0]["health_score"], new_score)

    def test_allow_update_on_a_day_with_nothing_recorded_is_not_a_replacement(self):
        healthy, _ = self._profiles()
        body = self._predict(healthy, allow_update=True).json()
        self.assertTrue(body["persisted"])
        self.assertFalse(
            body["replaced_existing"],
            "nothing was replaced, so reporting a replacement would tell "
            "the user they lost a day they never had",
        )

    # -------------------------------------------------------- not persisted
    def test_an_unsaved_prediction_is_never_blocked(self):
        # The What-if / exploratory path. It writes nothing, so there is
        # nothing to protect, and blocking it would break a feature that
        # has no bearing on the rule.
        healthy, at_risk = self._profiles()
        self._predict(healthy)
        exploratory = self._predict(at_risk, persist=False)
        self.assertEqual(exploratory.status_code, 200, exploratory.text)
        self.assertFalse(exploratory.json()["persisted"])
        self.assertFalse(exploratory.json()["replaced_existing"])

    def test_another_account_is_unaffected_by_this_ones_check_in(self):
        healthy, _ = self._profiles()
        self._predict(healthy)
        other = self._auth_headers(self._register(email="second@example.com"))
        response = self.client.post(
            "/api/v1/predict", json={"user_data": healthy}, headers=other,
        )
        self.assertEqual(response.status_code, 200, response.text)

    # ------------------------------------------------------------- today
    def test_today_reports_no_check_in_before_one_is_made(self):
        response = self.client.get("/api/v1/history/today", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["exists"])
        self.assertEqual(body["date"], date.today().isoformat())

    def test_today_reports_the_check_in_and_the_answers_behind_it(self):
        healthy, _ = self._profiles()
        self._predict(healthy)
        body = self.client.get("/api/v1/history/today", headers=self.headers).json()
        self.assertTrue(body["exists"])
        self.assertIsNotNone(body["health_score"])
        # Refilling the form is the whole point of returning inputs, so
        # a value the user actually entered has to survive the round
        # trip - an empty dict here would leave them retyping ~40
        # answers from memory to correct one of them.
        self.assertTrue(body["inputs"], "today's answers came back empty")
        self.assertEqual(body["inputs"]["sleep_hours"], healthy["sleep_hours"])

    def test_today_is_read_as_a_route_and_not_as_a_date(self):
        # /history/{entry_date} would happily match "today" and 404.
        response = self.client.get("/api/v1/history/today", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("exists", response.json())

    # --------------------------------------------------------------- CSV
    def _upload(self, csv_text, **data):
        return self.client.post(
            "/api/v1/history/import-csv",
            headers=self.headers,
            files={"file": ("day.csv", io.BytesIO(csv_text.encode()), "text/csv")},
            data=data,
        )

    def _questionnaire_csv(self, profile):
        """The single undated row the result page exports - filed under
        today, exactly like the real export."""
        keys = [k for k in profile]
        header = ",".join(keys)
        row = ",".join(str(profile[k]) for k in keys)
        return f"{header}\n{row}\n"

    def test_uploading_todays_questionnaire_again_is_refused(self):
        healthy, at_risk = self._profiles()
        self._predict(healthy)
        result = self._upload(self._questionnaire_csv(at_risk))
        self.assertEqual(result.status_code, 200, result.text)
        body = result.json()
        self.assertEqual(body["imported_count"], 0)
        self.assertEqual(len(body["failed_rows"]), 1)
        self.assertIn("already_recorded", body["failed_rows"][0]["errors"]["date"])

    def test_the_refused_upload_did_not_overwrite_the_day(self):
        healthy, at_risk = self._profiles()
        first_score = self._predict(healthy).json()["regression_score"]
        self._upload(self._questionnaire_csv(at_risk))
        entries = self.client.get("/api/v1/history", headers=self.headers).json()["items"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["health_score"], first_score)

    def test_uploading_with_the_edit_flag_on_replaces_the_day(self):
        healthy, at_risk = self._profiles()
        first_score = self._predict(healthy).json()["regression_score"]
        result = self._upload(self._questionnaire_csv(at_risk), allow_update="true")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["imported_count"], 1, result.text)

        entries = self.client.get("/api/v1/history", headers=self.headers).json()["items"]
        self.assertEqual(len(entries), 1)
        self.assertNotEqual(entries[0]["health_score"], first_score)

    def test_a_csv_covering_only_new_days_still_imports_untouched(self):
        # The bulk-import feature has to keep working - the rule is
        # about not destroying a recorded day, not about refusing files.
        from services.identity.csv_import_service import build_template_csv
        healthy, _ = self._profiles()
        self._predict(healthy)
        result = self._upload(build_template_csv())
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(
            result.json()["imported_count"], 2,
            "the template's two dated rows are not today and must import",
        )

    def test_a_dry_run_upload_of_todays_file_is_scored_not_refused(self):
        """The refusal above is correct only when something is being saved.

        Uploading today's questionnaire again used to be a dead end: the
        one-check-in-a-day rule refused it, and the only exit the app
        offered was the edit tick, which overwrites the very day the
        user was trying not to disturb. `dry_run` is the third answer -
        score it, show it, keep nothing.
        """
        healthy, at_risk = self._profiles()
        first_score = self._predict(healthy).json()["regression_score"]

        result = self._upload(self._questionnaire_csv(at_risk), dry_run="true")
        self.assertEqual(result.status_code, 200, result.text)
        body = result.json()

        self.assertTrue(body["dry_run"])
        self.assertEqual(body["failed_rows"], [], "a dry run was refused as a duplicate day")
        self.assertEqual(body["imported_count"], 0, "a dry run reported an import")
        self.assertEqual(len(body["previews"]), 1)
        self.assertIsNotNone(body["previews"][0]["health_score"])

        # And the real day is exactly as it was.
        entries = self.client.get("/api/v1/history", headers=self.headers).json()["items"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["health_score"], first_score)


if __name__ == "__main__":
    unittest.main()
