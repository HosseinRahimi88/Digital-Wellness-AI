"""Saved check-ins: the CSV a user names, downloads, and reloads.

The feature: after a check-in you name the answers you just gave, and
the app both downloads a CSV and lists it on the check-in screen. Next
time you pick it from the list and the whole form fills in, so the same
day (or the same day with one thing changed) never has to be retyped.

Two shelves - real check-ins and test check-ins - are decided by the
"don't count this" tick that was already set when the prediction ran,
so they cannot drift apart from what actually happened.

These tests run the real frontend/assets/js/csv-library.js under node
(tests/js/csv_library_runner.js), plus static checks that the two UI
surfaces are wired and translated. The end-to-end behaviour (name ->
Enter -> download + listed -> click -> form filled) was additionally
verified in a real Persian browser session.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parent / "js" / "csv_library_runner.js"
FRONTEND = REPO_ROOT / "frontend"
I18N = FRONTEND / "assets" / "js" / "i18n.js"

CSV_KEYS = [
    "csv_save_title", "csv_save_desc", "csv_save_placeholder", "csv_save_btn",
    "csv_save_needs_name", "csv_save_done", "csv_save_downloaded_not_listed",
    "csv_history_title", "csv_history_desc", "csv_history_tab_main",
    "csv_history_tab_test", "csv_history_empty_shelf", "csv_history_loaded",
    "csv_history_download", "csv_history_delete",
]


class TestCsvLibraryBehaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        r = subprocess.run([node, str(RUNNER)], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("csv_library_runner.js failed: " + r.stderr)
        cls.out = json.loads(r.stdout)

    def test_a_saved_file_round_trips_back_to_the_same_answers(self):
        # The whole point: what comes back must be what went in.
        self.assertTrue(self.out["numberStaysNumber"], "numbers came back as strings")
        self.assertTrue(self.out["commaSurvived"], "a value containing a comma broke the CSV")
        self.assertTrue(self.out["quoteSurvived"], "a value containing a quote broke the CSV")

    def test_malformed_input_returns_none_rather_than_half_filling_the_form(self):
        # Half-filling a check-in form from a broken file would be worse
        # than refusing it - the user would submit answers they never gave.
        self.assertIsNone(self.out["malformedHeaderOnly"])
        self.assertIsNone(self.out["malformedEmpty"])
        self.assertIsNone(self.out["malformedRagged"])

    def test_a_save_needs_a_real_name_and_a_real_payload(self):
        self.assertIsNone(self.out["emptyNameRejected"])
        self.assertIsNone(self.out["nonObjectPayloadRejected"])
        self.assertEqual(self.out["nameTrimmed"], "padded")

    def test_the_shelf_comes_from_the_exclude_flag(self):
        self.assertEqual(self.out["mainKind"], "main")
        self.assertEqual(self.out["testKind"], "test")
        self.assertEqual(self.out["listMain"] + self.out["listTest"], self.out["listAll"])

    def test_the_score_is_stored_rounded(self):
        self.assertEqual(self.out["scoreRounded"], 84)

    def test_removing_an_entry_actually_removes_it(self):
        self.assertTrue(self.out["removedIsGone"])

    def test_filenames_work_in_every_language_and_never_come_out_empty(self):
        names = self.out["fileNames"]
        for lang in ("fa", "en", "zh", "ar"):
            with self.subTest(lang=lang):
                self.assertTrue(names[lang].endswith(".csv"))
                self.assertGreater(len(names[lang]), len(".csv"))
        # A name made only of punctuation still has to produce a file.
        self.assertEqual(names["junkOnly"], "check-in.csv")


class TestCsvUiIsWiredAndTranslated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_html = (FRONTEND / "app.html").read_text(encoding="utf-8")
        cls.app_js = (FRONTEND / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        cls.i18n = I18N.read_text(encoding="utf-8")

    def test_the_save_box_and_the_history_list_both_exist(self):
        for el in ("csvSaveName", "csvSaveBtn", "csvSaveStatus",
                   "csvHistoryCard", "csvHistoryList", "csvTabMain", "csvTabTest"):
            with self.subTest(el=el):
                self.assertIn(f'id="{el}"', self.app_html)

    def test_the_library_script_is_loaded(self):
        self.assertIn('src="assets/js/csv-library.js"', self.app_html)

    def test_enter_in_the_name_box_saves(self):
        # Explicitly requested: type a name, press Enter, done - not a
        # trip to the mouse. Checked inside wireCsvSave() so a stray
        # "Enter" elsewhere in app.js cannot satisfy this.
        start = self.app_js.index("function wireCsvSave")
        end = self.app_js.index("function renderCsvHistory")
        body = self.app_js[start:end]
        self.assertIn("addEventListener('keydown'", body)
        self.assertIn("'Enter'", body)
        self.assertIn("doSave()", body)

    def test_loading_a_saved_entry_refills_the_wizard(self):
        self.assertIn("function applySavedCheckin", self.app_js)
        idx = self.app_js.index("function applySavedCheckin")
        body = self.app_js[idx:idx + 700]
        self.assertIn("state.wizardData", body)
        self.assertIn("renderStep()", body)
        # Must start from schema defaults so a file saved before a field
        # existed cannot leave that field undefined.
        self.assertIn("DWSchema.DEFAULTS", body)

    def test_the_user_chosen_name_is_never_injected_as_html(self):
        # Names are free text typed by the user.
        idx = self.app_js.index("csv-history-name")
        window = self.app_js[idx:idx + 900]
        self.assertIn("textContent", window)

    def test_every_new_string_exists_in_all_four_languages(self):
        for key in CSV_KEYS:
            with self.subTest(key=key):
                found = len(re.findall(rf"^\s*{key}:", self.i18n, re.MULTILINE))
                self.assertEqual(
                    found, 4,
                    f"{key} appears {found} time(s); it must exist in en, fa, ar and zh",
                )

    def test_both_new_surfaces_have_a_guide_topic(self):
        controls = (FRONTEND / "assets" / "js" / "guide-content-controls.js").read_text(encoding="utf-8")
        for topic in ("csv_save", "csv_history"):
            with self.subTest(topic=topic):
                self.assertIn(f"{topic}: {{", controls)
                self.assertIn(f'data-guide="{topic}"', self.app_html)


if __name__ == "__main__":
    unittest.main()
