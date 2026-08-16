"""The UI half of "one main check-in per day".

Server behaviour lives in tests/test_one_check_in_per_day.py. This file
pins the wiring on the check-in page, because the server guard alone
produces a dead end: a user whose submission comes back 409 needs to be
shown the control that resolves it, and needs the form to still hold
what they typed.

The rules being pinned, and why each one exists:

  - The tick's state is asked of the SERVER, not read out of
    localStorage. A second device, or the same browser after a clear,
    knows nothing about a day the server already recorded, and a page
    that guesses "no check-in yet" would send the user straight into a
    409 with no explanation.
  - `allow_update` actually reaches /predict and /history/import-csv.
    Without it the tick is decoration and the day is still refused.
  - A 409 is handled as its own case, not as a generic error. The user
    did nothing wrong; the day is simply already recorded.
  - Unticking never wipes the form. Losing typed answers as a side
    effect of a checkbox is a small version of the exact data loss this
    whole feature exists to stop.
  - Every new string is translated into all four shipped languages.

Run: python3 -m unittest tests.test_edit_today_ui -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
JS = FRONTEND / "assets" / "js"

LANGS = ("en", "fa", "ar", "zh")

EDIT_KEYS = [
    "edit_today_label", "edit_today_note", "edit_today_note_locked",
    "edit_today_loaded", "edit_today_no_answers",
    "toast_already_checked_in", "toast_checkin_updated",
    "toast_plan_rebuilt", "csv_import_needs_edit_tick",
]


class TestEditTodayUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app_js = (JS / "app.js").read_text(encoding="utf-8")
        cls.api_js = (JS / "api.js").read_text(encoding="utf-8")
        cls.i18n_js = (JS / "i18n.js").read_text(encoding="utf-8")
        cls.guide_js = (JS / "guide-tips.js").read_text(encoding="utf-8")
        cls.app_html = (FRONTEND / "app.html").read_text(encoding="utf-8")
        cls.app_css = (FRONTEND / "assets" / "css" / "app.css").read_text(encoding="utf-8")

    # ---------------------------------------------------------- markup
    def test_the_tick_exists_and_starts_hidden(self):
        self.assertIn('id="editTodayRow"', self.app_html)
        self.assertIn('id="editTodayCheck"', self.app_html)
        row = self.app_html[self.app_html.index('id="editTodayRow"') - 120:]
        row = row[:row.index("</div>")]
        self.assertIn(
            "hidden", row,
            "the tick must not be on screen on a day with nothing to edit - "
            "offering to 'edit today's check-in' before one exists is an "
            "invitation to a control that cannot do anything",
        )

    def test_the_tick_is_registered_with_the_guide(self):
        self.assertIn('data-guide="edit_today"', self.app_html)
        self.assertIn("edit_today:{", self.guide_js)

    # ------------------------------------------------------- the server
    def test_the_page_asks_the_server_whether_today_is_recorded(self):
        self.assertIn("todayCheckIn: () => request('/history/today')", self.api_js)
        self.assertIn("window.DWApi.todayCheckIn()", self.app_js)

    def test_the_tick_state_is_not_taken_from_local_storage_alone(self):
        # The lock flag IS in localStorage - it records that an update
        # already happened today - but whether the day exists at all
        # must come from the server, or a cleared browser silently
        # decides there is nothing to protect.
        body = self.app_js[self.app_js.index("async function refreshTodayCheckIn"):]
        body = body[:body.index("\n  }\n")]
        self.assertIn("window.DWApi.todayCheckIn()", body)

    def test_refreshing_runs_when_the_wizard_opens(self):
        start = self.app_js.index("async function startWizard")
        self.assertIn("refreshTodayCheckIn()", self.app_js[start:start + 900])

    # ------------------------------------------------------ allow_update
    def test_the_tick_reaches_the_prediction_call(self):
        self.assertRegex(
            self.api_js,
            r"predict:\s*\(user_data,\s*persist\s*=\s*true,\s*allow_update\s*=\s*false\)",
        )
        self.assertIn("allow_update,", self.api_js)
        self.assertIn(
            "window.DWApi.predict(payload, !state.excludeFromAnalysis, state.editToday)",
            self.app_js,
            "the tick has to be passed through, or it is decoration and "
            "an edit is still refused",
        )

    def test_the_tick_reaches_the_csv_upload(self):
        self.assertIn("form.append('allow_update'", self.api_js)
        self.assertIn("window.DWApi.importHistoryCsv(file, state.editToday)", self.app_js)

    # ---------------------------------------------------------- the 409
    def test_a_409_is_handled_as_its_own_case(self):
        self.assertIn("err.code === 'already_checked_in_today'", self.app_js)
        idx = self.app_js.index("err.code === 'already_checked_in_today'")
        branch = self.app_js[idx:idx + 900]
        self.assertIn("toast_already_checked_in", branch)
        self.assertIn(
            "scrollIntoView", branch,
            "a refusal that does not show the control that resolves it is "
            "a dead end",
        )

    def test_the_409_branch_runs_before_the_generic_error_branch(self):
        # Order matters: a generic `else` reached first would report the
        # server's English sentence and never show the tick.
        self.assertLess(
            self.app_js.index("err.code === 'already_checked_in_today'"),
            self.app_js.index("} else if (err.fieldErrors) {"),
        )

    # --------------------------------------------------------- refilling
    def test_ticking_refills_the_form_from_todays_answers(self):
        self.assertIn("function applyTodayAnswers", self.app_js)
        body = self.app_js[self.app_js.index("function applyTodayAnswers"):]
        body = body[:body.index("\n  async function startWizard")]
        self.assertIn("state.wizardData = { ...window.DWSchema.DEFAULTS, ...inputs }", body)
        self.assertIn("renderStep()", body)

    def test_a_day_with_no_stored_answers_says_so(self):
        body = self.app_js[self.app_js.index("function applyTodayAnswers"):]
        body = body[:body.index("\n  async function startWizard")]
        self.assertIn("edit_today_no_answers", body)

    def test_unticking_never_wipes_the_form(self):
        idx = self.app_js.index("const editCheck = $('#editTodayCheck')")
        handler = self.app_js[idx:idx + 800]
        # Stripped of comments, so prose about the rule cannot pass for
        # the rule.
        code = re.sub(r"//.*", "", handler)
        self.assertIn("if (e.target.checked) applyTodayAnswers();", code)
        self.assertNotIn("resetWizard", code)
        self.assertNotIn("DWSchema.DEFAULTS", code)

    # ------------------------------------------------------- the lock
    def test_the_lock_is_keyed_to_the_date(self):
        # So it clears itself at midnight rather than needing cleanup,
        # and so yesterday's lock can never mark today as an edit.
        self.assertIn("dwai_edit_today_locked_on", self.app_js)
        body = self.app_js[self.app_js.index("function editLockedToday"):]
        body = body[:body.index("function lockEditForToday")]
        self.assertIn("todayIso()", body)

    def test_a_completed_update_locks_the_tick(self):
        idx = self.app_js.index("result.replaced_existing")
        branch = self.app_js[idx:idx + 700]
        self.assertIn("lockEditForToday()", branch)
        self.assertIn("toast_checkin_updated", branch)

    def test_a_locked_tick_is_rendered_checked_and_unremovable(self):
        body = self.app_js[self.app_js.index("async function refreshTodayCheckIn"):]
        body = body[:body.index("\n  /* Refills the form")]
        self.assertIn("check.checked = locked", body)
        self.assertIn("check.disabled = locked", body)
        self.assertIn("edit_today_note_locked", body)

    def test_a_fresh_wizard_never_inherits_the_tick(self):
        body = self.app_js[self.app_js.index("function resetWizard"):]
        body = body[:body.index("function findStepForField")]
        self.assertIn("state.editToday = false", body)
        self.assertIn("state.todayCheckIn = null", body)

    # ------------------------------------------------------- downstream
    def test_an_update_rebuilds_a_plan_that_was_built_from_that_day(self):
        self.assertIn("async function refreshDownstreamOfCheckIn", self.app_js)
        body = self.app_js[self.app_js.index("async function refreshDownstreamOfCheckIn"):]
        body = body[:body.index("\n  async function startWizard")]
        self.assertIn("regenerate: true", body)
        self.assertIn(
            "current.generated_on !== todayIso()", body,
            "a plan set earlier in the week must survive a correction to "
            "a later day - regenerating clears that week's checkmarks",
        )

    # -------------------------------------------------------------- CSV
    def test_a_blocked_csv_row_is_explained_rather_than_echoed(self):
        self.assertIn("already_recorded", self.app_js)
        self.assertIn("csv_import_needs_edit_tick", self.app_js)

    def test_a_wholly_blocked_upload_is_not_reported_as_a_broken_file(self):
        idx = self.app_js.index("csv_import_none_imported")
        window = self.app_js[max(0, idx - 900):idx]
        self.assertIn("blocked.length && !otherFailures.length", window)

    def test_the_server_error_carries_the_machine_readable_prefix(self):
        # The frontend keys its translated sentence off this prefix, so
        # rewording the English message must not move it off the front.
        import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path
        from services.csv_import_service import CSVImportService

        message = CSVImportService.DUPLICATE_DAY_ERROR.format(day="2026-08-13")
        self.assertTrue(
            message.startswith("already_recorded:"),
            f"the frontend matches on this prefix at index 0; got {message[:40]!r}",
        )
        self.assertIn("2026-08-13", message)

    # ------------------------------------------------------------- i18n
    def test_every_new_string_exists_in_all_four_languages(self):
        for key in EDIT_KEYS:
            found = len(re.findall(rf"\b{re.escape(key)}\s*:", self.i18n_js))
            self.assertEqual(
                found, len(LANGS),
                f"{key} appears {found} time(s) in i18n.js, expected one per "
                f"language ({', '.join(LANGS)})",
            )

    def test_the_guide_entry_exists_in_all_four_languages(self):
        found = len(re.findall(r"\bedit_today\s*:\s*['\"]", self.guide_js))
        self.assertEqual(found, len(LANGS), "edit_today guide text is not in all four languages")

    def test_no_new_string_is_left_as_english_in_another_language(self):
        # A copy-paste that leaves the English sentence under `fa` passes
        # a bare presence check while showing English to a Persian
        # reader.
        for key in ("edit_today_label", "toast_checkin_updated"):
            values = re.findall(rf"\b{re.escape(key)}\s*:\s*(['\"])(.*?)\1", self.i18n_js, re.S)
            texts = [v[1] for v in values]
            self.assertEqual(len(texts), len(LANGS))
            self.assertEqual(
                len(set(texts)), len(LANGS),
                f"{key} has duplicate values across languages: {texts}",
            )

    # -------------------------------------------------------------- css
    def test_the_row_has_its_own_styling_and_respects_reduced_motion(self):
        self.assertIn(".edit-today-row {", self.app_css)
        self.assertIn(".edit-today-row--flash", self.app_css)
        idx = self.app_css.index(".edit-today-row--flash")
        tail = self.app_css[idx:idx + 500]
        self.assertIn("prefers-reduced-motion", tail)
        self.assertIn("force-reduce-motion", tail)


if __name__ == "__main__":
    unittest.main()
