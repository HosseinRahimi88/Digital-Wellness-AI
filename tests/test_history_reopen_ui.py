"""The two UI halves of reopening a past day.

Backend behaviour lives in tests/test_history_detail.py. This file pins
the wiring that turns a heatmap cell into a reopened result screen, and
the honesty guard that stops an old score from reading as today's.

The end-to-end flow (check-in -> dashboard -> click the day -> the same
score comes back under a banner naming the date, in Persian) was driven
in a real browser; these are the checks that keep it from silently
regressing.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
JS = FRONTEND / "assets" / "js"

REOPEN_KEYS = [
    "heatmap_open_tip", "history_reopened", "history_reopen_unavailable",
    "history_reopen_banner", "history_reopen_rerun",
]


class TestClickingADayOpensIt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dashboard = (JS / "dashboard.js").read_text(encoding="utf-8")
        cls.app_js = (JS / "app.js").read_text(encoding="utf-8")
        cls.api_js = (JS / "api.js").read_text(encoding="utf-8")

    def test_the_cell_click_navigates_to_that_day(self):
        self.assertIn("app.html?day=", self.dashboard)
        # The date has to be escaped into the URL, not concatenated raw.
        self.assertIn("encodeURIComponent(iso)", self.dashboard)

    def test_the_cell_click_no_longer_silently_excludes_the_day(self):
        # The regression this replaced: the most obvious gesture on the
        # page performed a data edit and offered no way to view the day.
        start = self.dashboard.index("const cell = document.createElement('div')")
        end = self.dashboard.index("heatmap.appendChild(cell)")
        body = re.sub(r"//.*", "", self.dashboard[start:end])
        self.assertIn("cell.addEventListener('click', open)", body)
        self.assertNotIn("cell.addEventListener('click', toggle)", body)

    def test_marking_an_exception_still_exists_as_its_own_control(self):
        # Replacing the click must not remove the ability - only move it.
        self.assertIn("heatmap-flag", self.dashboard)
        self.assertIn("setHistoryExcluded", self.dashboard)

    def test_the_exception_toggle_never_opens_the_day_as_a_side_effect(self):
        idx = self.dashboard.index("mark.addEventListener('click'")
        body = self.dashboard[idx:idx + 400]
        self.assertIn("stopPropagation()", body)

    def test_the_exception_toggle_is_reachable_without_a_mouse(self):
        # A <button> carries keyboard activation and a role for free;
        # a styled <div> would not.
        self.assertIn("document.createElement('button')", self.dashboard)
        self.assertIn("aria-pressed", self.dashboard)
        self.assertIn("aria-label", self.dashboard)

    def test_the_api_client_asks_for_the_detail_endpoint(self):
        self.assertIn("historyDetail:", self.api_js)
        self.assertIn("/detail", self.api_js)
        idx = self.api_js.index("historyDetail:")
        self.assertIn("encodeURIComponent", self.api_js[idx:idx + 160])


class TestAReopenedDayIsMarkedAsPast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_js = (JS / "app.js").read_text(encoding="utf-8")
        cls.app_html = (FRONTEND / "app.html").read_text(encoding="utf-8")
        cls.i18n = (JS / "i18n.js").read_text(encoding="utf-8")

    def test_the_banner_exists_and_names_the_day(self):
        self.assertIn('id="pastDayBanner"', self.app_html)
        self.assertIn('id="pastDayBannerText"', self.app_html)
        self.assertIn("history_reopen_banner", self.app_js)

    def test_a_fresh_result_always_clears_the_banner_first(self):
        # Otherwise a banner left over from a reopened day would label
        # the next real check-in as history.
        idx = self.app_js.index("function renderResult")
        body = self.app_js[idx:idx + 900]
        self.assertIn("pastDayBanner", body)
        self.assertIn("classList.add('hidden')", body)

    def test_the_banner_is_shown_after_the_result_is_rendered_not_before(self):
        # renderResult() hides it; showing it earlier would be undone.
        idx = self.app_js.index("async function openPastDay")
        body = self.app_js[idx:self.app_js.index("function formatHistoryDate")]
        self.assertLess(
            body.index("renderResult(detail.result)"),
            body.index("classList.remove('hidden')"),
            "the banner is shown before renderResult() hides it again",
        )

    def test_the_day_query_is_honoured_before_the_onboarding_redirect(self):
        # Skipping onboarding never marks it complete, so gating the
        # reopen on it would send anyone who pressed "skip" to the intro
        # screen instead of the day they clicked.
        idx = self.app_js.index("async function afterLogin")
        body = self.app_js[idx:idx + 1400]
        self.assertLess(
            body.index("openPastDay(day)"),
            body.index("onboarding_complete"),
            "onboarding is checked before the requested day",
        )

    def test_a_day_that_cannot_be_opened_falls_through_instead_of_stranding(self):
        idx = self.app_js.index("async function openPastDay")
        body = self.app_js[idx:idx + 1200]
        self.assertIn("return false", body)
        self.assertIn("DWToast.error", body)

    def test_the_missing_detail_case_is_told_apart_by_code_not_by_message(self):
        # Messages are translated and will change; the code will not.
        self.assertIn("history_detail_unavailable", self.app_js)
        # And the client has to actually carry the code through.
        api_js = (JS / "api.js").read_text(encoding="utf-8")
        self.assertIn("this.code", api_js)

    def test_a_reopened_day_lands_on_the_csv_shelf_it_belongs_to(self):
        idx = self.app_js.index("async function openPastDay")
        body = self.app_js[idx:idx + 1600]
        self.assertIn("state.excludeFromAnalysis = !!detail.excluded", body)

    def test_run_this_day_again_refills_rather_than_resubmits(self):
        idx = self.app_js.index("pastDayRerunBtn")
        body = self.app_js[idx:idx + 900]
        self.assertIn("startWizard()", body)
        self.assertIn("DWSchema.DEFAULTS", body)
        self.assertNotIn("submitPrediction", body)

    def test_every_new_string_exists_in_all_four_languages(self):
        for key in REOPEN_KEYS:
            with self.subTest(key=key):
                found = len(re.findall(rf"^\s*{key}:", self.i18n, re.MULTILINE))
                self.assertEqual(
                    found, 4,
                    f"{key} appears {found} time(s); it must exist in en, fa, ar and zh",
                )

    def test_the_date_in_the_banner_follows_the_readers_language(self):
        # A Persian reader should see a Jalali date, not an ISO string.
        idx = self.app_js.index("function formatHistoryDate")
        body = self.app_js[idx:idx + 500]
        self.assertIn("LOCALE_FOR_LANG", body)
        self.assertIn("toLocaleDateString", body)
        # An unavailable locale must degrade to the raw date, not throw.
        self.assertIn("return iso", body)


class TestHeatmapStyling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = (FRONTEND / "assets" / "css" / "shell.css").read_text(encoding="utf-8")

    def test_the_exception_toggle_can_be_positioned_inside_the_cell(self):
        idx = self.css.index(".heatmap-cell {")
        self.assertIn("position: relative", self.css[idx:idx + 400])
        self.assertIn(".heatmap-flag", self.css)

    def test_the_toggle_sits_on_the_same_side_in_rtl_and_ltr(self):
        idx = self.css.index(".heatmap-flag {")
        body = self.css[idx:idx + 400]
        self.assertIn("inset-inline-start", body)
        self.assertNotIn("left:", body)

    def test_an_excluded_day_strikes_the_score_not_the_toggle(self):
        # Striking through the whole cell made the toggle unreadable on
        # exactly the days it needs to be pressed.
        self.assertIn(".heatmap-cell.excluded .heatmap-score", self.css)
        idx = self.css.index(".heatmap-cell.excluded {")
        self.assertNotIn("text-decoration", self.css[idx:idx + 120])


if __name__ == "__main__":
    unittest.main()
