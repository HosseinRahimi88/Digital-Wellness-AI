"""The UI half of "that day sits outside your week's range".

Server behaviour lives in tests/wellness/test_day_band_decision.py. This file
pins the wiring that turns that server answer into a question the user
actually sees, and the rules that keep the question honest:

  - nothing in the browser decides WHETHER to ask. The band, the day's
    position in the week and the score all live on the server; a page
    that recomputed any of them would either nag someone about an
    ordinary day or quietly skip a real one;
  - the question is asked AFTER the day's score is on screen. It quotes
    that score back, and asking someone to judge a number they have not
    been shown is not a question they can answer;
  - both options carry their consequence in the UI, because the two
    consequences are genuinely different - one changes nothing, the
    other rewrites the rest of the week;
  - there is no dismiss control. Two real answers, and closing it would
    leave the week in neither state;
  - an exception day is marked differently from an excluded day, since
    they mean different things;
  - every string exists in all four shipped languages.

Run: python3 -m unittest tests.wellness.test_band_decision_ui -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

REPO_ROOT = paths.PROJECT_ROOT
FRONTEND = REPO_ROOT / "frontend"
JS = FRONTEND / "assets" / "js"
CSS = FRONTEND / "assets" / "css"

LANGS = ("en", "fa", "ar", "zh")

BAND_KEYS = [
    "band_decision_title", "band_decision_lead",
    "band_decision_exception", "band_decision_exception_note",
    "band_decision_counted", "band_decision_counted_note",
    "band_decision_done_exception", "band_decision_done_counted",
    "heatmap_exception_tip", "heatmap_exception_summary",
]


class TestBandDecisionUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.band_js = (JS / "features/band-decision.js").read_text(encoding="utf-8")
        cls.app_js = (JS / "pages/app.js").read_text(encoding="utf-8")
        cls.api_js = (JS / "core/api.js").read_text(encoding="utf-8")
        cls.weekly_js = (JS / "pages/weekly.js").read_text(encoding="utf-8")
        cls.dashboard_js = (JS / "pages/dashboard.js").read_text(encoding="utf-8")
        cls.i18n_js = (JS / "core/i18n.js").read_text(encoding="utf-8")
        cls.guide_js = (JS / "guide/guide-tips.js").read_text(encoding="utf-8")
        cls.app_html = (FRONTEND / "app.html").read_text(encoding="utf-8")
        cls.weekly_html = (FRONTEND / "weekly.html").read_text(encoding="utf-8")
        cls.dashboard_html = (FRONTEND / "dashboard.html").read_text(encoding="utf-8")
        cls.app_css = (CSS / "app.css").read_text(encoding="utf-8")
        cls.shell_css = (CSS / "shell.css").read_text(encoding="utf-8")

    # ------------------------------------------------------------- api
    def test_both_endpoints_are_wired(self):
        self.assertIn("planDayStatus: () => request('/plan/day-status')", self.api_js)
        self.assertIn("planDayDecision: (decision", self.api_js)
        self.assertIn("'/plan/day-decision'", self.api_js)

    # ------------------------------------------------- the server decides
    def test_the_browser_never_decides_whether_to_ask(self):
        # `needs_decision` comes back from the server and is the only
        # gate. A locally recomputed band is the failure mode this is
        # guarding: it would nag about ordinary days.
        self.assertIn("state.needs_decision", self.band_js)
        code = re.sub(r"/\*.*?\*/", "", self.band_js, flags=re.S)
        code = re.sub(r"//.*", "", code)
        for invented in ("BAND_HALF_WIDTH", "band_low +", "band_high -"):
            self.assertNotIn(
                invented, code,
                f"{invented} suggests the band is being recomputed in the browser",
            )

    def test_a_failed_status_call_asks_nothing_rather_than_breaking(self):
        body = self.band_js[self.band_js.index("async function status"):]
        body = body[:body.index("\n  function fmt")]
        self.assertIn("catch", body)
        self.assertIn("lastStatus = null", body)

    # --------------------------------------------------------- the ask
    def test_the_question_is_asked_after_the_score_is_on_screen(self):
        # It quotes the day's own score back. Asking before the result
        # view renders would ask someone to judge a number they have not
        # been shown.
        idx = self.app_js.index("DWBandDecision.maybeAsk")
        before = self.app_js[:idx]
        self.assertIn("renderResult(result);", before)
        self.assertLess(before.rindex("renderResult(result);"), idx)

    def test_both_pages_mount_it(self):
        self.assertIn('id="bandDecisionMount"', self.app_html)
        self.assertIn('id="bandDecisionMount"', self.weekly_html)
        self.assertIn("assets/js/features/band-decision.js", self.app_html)
        self.assertIn("assets/js/features/band-decision.js", self.weekly_html)
        self.assertIn("DWBandDecision.maybeAsk", self.weekly_js)

    def test_both_options_state_their_consequence(self):
        self.assertIn("band_decision_exception_note", self.band_js)
        self.assertIn("band_decision_counted_note", self.band_js)

    def test_there_is_no_dismiss_control(self):
        code = re.sub(r"/\*.*?\*/", "", self.band_js, flags=re.S)
        code = re.sub(r"//.*", "", code)
        for dismissal in ("band-decision-close", "'dismiss'", "Later", "skip"):
            self.assertNotIn(
                dismissal, code,
                "closing the question would leave the week in neither state",
            )

    def test_the_reduced_weight_shown_comes_from_the_server(self):
        # The sentence says "about N% of a normal day". Hardcoding N in
        # the UI is how the explanation drifts from the arithmetic that
        # is actually applied.
        self.assertIn("state.exception_weight", self.band_js)
        self.assertIn("exception_weight: float", (REPO_ROOT / "api" / "schemas" / "plan.py").read_text(encoding="utf-8"))

    # ------------------------------------------------------ after "count"
    def test_counting_it_re_reads_the_plan_rather_than_patching_it(self):
        idx = self.weekly_js.index("DWBandDecision.maybeAsk")
        body = self.weekly_js[idx:idx + 1400]
        self.assertIn("decision !== 'counted'", body)
        self.assertIn("window.DWApi.generatePlan(", body)
        self.assertIn("renderPlanBody()", body)

    # ---------------------------------------------------- the dashboard
    def test_exception_days_are_shown_on_the_dashboard(self):
        self.assertIn("planDayStatus()", self.dashboard_js)
        self.assertIn("exception_days", self.dashboard_js)
        self.assertIn("heatmap_exception_summary", self.dashboard_js)
        self.assertIn('id="heatmapExceptionLine"', self.dashboard_html)

    def test_an_exception_day_is_not_marked_like_an_excluded_day(self):
        # They mean different things - one is "this is not my data" and
        # drops out entirely, the other happened and still counts. The
        # same glyph for both would say they are one decision.
        self.assertIn(".heatmap-exception", self.shell_css)
        self.assertIn(".heatmap-cell.exception-day", self.shell_css)
        self.assertNotEqual(
            self.dashboard_js.count("'⊘'"), 0,
            "the excluded-day marker disappeared",
        )
        self.assertIn("'~'", self.dashboard_js)

    def test_the_dashboard_still_renders_if_the_status_call_fails(self):
        idx = self.dashboard_js.index("planDayStatus()")
        block = self.dashboard_js[max(0, idx - 300):idx + 300]
        self.assertIn("catch", block)

    # ----------------------------------------------------------- i18n
    def test_the_language_listener_is_on_document(self):
        # i18n.js dispatches dwai:langchange on `document` with no
        # bubbling, so a listener on `window` never fires. This exact
        # mistake shipped once already.
        self.assertIn("document.addEventListener('dwai:langchange'", self.band_js)
        self.assertNotIn("window.addEventListener('dwai:langchange'", self.band_js)

    def test_every_string_exists_in_all_four_languages(self):
        for key in BAND_KEYS:
            found = len(re.findall(rf"\b{re.escape(key)}\s*:", self.i18n_js))
            self.assertEqual(
                found, len(LANGS),
                f"{key} appears {found} time(s), expected one per language",
            )

    def test_no_string_is_left_as_english_in_another_language(self):
        for key in ("band_decision_title", "band_decision_counted"):
            values = re.findall(rf"\b{re.escape(key)}\s*:\s*(['\"])(.*?)\1", self.i18n_js, re.S)
            texts = [v[1] for v in values]
            self.assertEqual(len(texts), len(LANGS))
            self.assertEqual(len(set(texts)), len(LANGS), f"{key}: {texts}")

    def test_the_placeholders_survive_every_translation(self):
        # {score}/{low}/{high} are substituted by the renderer; a
        # translation that dropped one would print a sentence with a
        # hole in it where the user's own number should be.
        values = re.findall(r"\bband_decision_lead\s*:\s*(['\"])(.*?)\1", self.i18n_js, re.S)
        self.assertEqual(len(values), len(LANGS))
        for _, text in values:
            for token in ("{score}", "{low}", "{high}"):
                self.assertIn(token, text, f"{token} missing from a translation")

    def test_the_guide_explains_both_options_in_all_four_languages(self):
        for key in ("band_decision", "heatmap_exceptions"):
            found = len(re.findall(rf"\b{re.escape(key)}\s*:\s*['\"]", self.guide_js))
            self.assertEqual(found, len(LANGS), f"{key} guide text is not in all four languages")

    # ------------------------------------------------------------- css
    def test_the_card_is_styled_and_works_in_rtl(self):
        self.assertIn(".band-decision {", self.app_css)
        self.assertIn('[dir="rtl"] .band-decision', self.app_css)
        self.assertIn(".band-decision-options", self.app_css)


if __name__ == "__main__":
    unittest.main()
