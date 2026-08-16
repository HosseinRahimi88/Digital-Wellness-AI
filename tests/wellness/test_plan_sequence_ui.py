"""The UI half of "the week runs in order, and a missed day costs
something".

Server behaviour lives in tests/wellness/test_plan_days_and_violations.py. This
file pins how that reaches the screen, and the small decisions that
keep it from becoming a scolding:

  - a locked day is dimmed, not hidden. Seeing what is coming is the
    point of a weekly plan; hiding it would make the week look shorter
    than it is;
  - a locked day says WHY and which day to finish. "Locked" on its own
    reads as a fault in the app rather than as the next step;
  - a refused tick rolls the checkbox back. Leaving it ticked would
    show the user a completion that exists nowhere but on their screen;
  - the violations panel is only rendered when there is something in
    it. A section reading "0 open violations" on a page about
    achievements turns a clean record into a telling-off;
  - the numbers all come from the server. Nothing is counted locally.

Run: python3 -m unittest tests.wellness.test_plan_sequence_ui -v
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

KEYS = [
    "plan_day_locked_note", "plan_day_locked_toast",
    "violations_title", "violations_count_label", "violations_lead",
    "violations_revoked", "violations_withheld",
]


class TestPlanSequenceUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.weekly_js = (JS / "pages/weekly.js").read_text(encoding="utf-8")
        cls.hall_js = (JS / "pages/hall-page.js").read_text(encoding="utf-8")
        cls.i18n_js = (JS / "core/i18n.js").read_text(encoding="utf-8")
        cls.guide_js = (JS / "guide/guide-tips.js").read_text(encoding="utf-8")
        cls.hall_html = (FRONTEND / "hall.html").read_text(encoding="utf-8")
        cls.app_css = (CSS / "app.css").read_text(encoding="utf-8")
        cls.shell_css = (CSS / "shell.css").read_text(encoding="utf-8")

    # ------------------------------------------------------ locked days
    def test_a_locked_day_is_marked_from_the_servers_flag(self):
        self.assertIn("day.locked ? ' day-card--locked' : ''", self.weekly_js)

    def test_a_locked_days_checkboxes_are_disabled(self):
        self.assertIn("day.locked ? 'disabled' : ''", self.weekly_js)

    def test_a_locked_day_is_dimmed_and_not_hidden(self):
        self.assertIn(".day-card--locked { opacity:", self.shell_css)
        self.assertNotIn(".day-card--locked { display: none", self.shell_css)

    def test_a_locked_day_says_which_day_to_finish(self):
        self.assertIn("plan_day_locked_note", self.weekly_js)
        self.assertIn("plan.unlocked_through", self.weekly_js)

    def _tick_handler(self) -> str:
        """The whole body of the checkbox `change` handler.

        Sliced between two real anchors rather than by a character
        count. The count version broke the moment anything was added to
        the handler - which says nothing about whether the behaviour it
        was pinning is still there, and is exactly the kind of failure
        that teaches people to widen the number and move on.
        """
        start = self.weekly_js.index("updatePlanTask(day.day_number")
        end = self.weekly_js.index("tasksWrap.appendChild(row)", start)
        return self.weekly_js[start:end]

    def test_a_refused_tick_rolls_the_box_back(self):
        block = self._tick_handler()
        self.assertIn("plan_day_locked_toast", block)
        self.assertIn("e.target.checked = !e.target.checked", block)

    def test_finishing_a_day_re_reads_the_plan_rather_than_guessing(self):
        # Only the server knows which day is open next; recomputing it
        # in the browser is how the two drift apart.
        block = self._tick_handler()
        self.assertIn("generatePlan(", block)
        self.assertIn("refreshed.unlocked_through !== plan.unlocked_through", block)

    def test_the_celebration_fires_off_the_servers_answer(self):
        """Ticking the last box of a day is the one thing this app
        celebrates. It must read the completion off the refreshed plan,
        not off the checkboxes - a tick that failed to save would
        otherwise get a celebration for something that did not happen."""
        block = self._tick_handler()
        self.assertIn("DWCelebrate", block)
        self.assertIn("refreshed.days", block)
        self.assertIn("t.completed", block)

    # ------------------------------------------------- the second device
    def test_the_page_falls_back_to_the_server_when_the_browser_is_empty(self):
        """localStorage is the fast path, not the source of truth.

        This page used to stop at the empty state, so a user on a second
        device - or after clearing their browser - was told "No plan
        yet" while the server held a fortnight of their check-ins and a
        frozen plan for the week. Everything pinned above (the locked
        days, the band card, the out-of-band question) lived behind that
        empty state. Reproduced in a real browser before the fix: a
        fresh profile with a real account and real server history
        rendered zero day cards.
        """
        body = self.weekly_js[self.weekly_js.index("// ---- 7-day plan ----"):]
        body = body[:body.index("document.getElementById('planContent')")]
        self.assertIn("window.DWApi.history(1, 1)", body)
        self.assertIn("window.DWApi.historyDetail(", body)
        self.assertIn("lastResult = detail.result", body)
        self.assertIn("lastPayload = detail.inputs", body)

    def test_the_empty_state_still_exists_for_an_account_with_nothing(self):
        # The fallback must not turn "nothing logged" into a broken
        # page or an invented plan.
        body = self.weekly_js[self.weekly_js.index("// ---- 7-day plan ----"):]
        body = body[:body.index("document.getElementById('planContent')")]
        self.assertIn("planEmpty", body)
        self.assertIn("if (!lastResult || !lastPayload) {", body)

    # ------------------------------------------------------- violations
    def test_the_violations_panel_exists_under_the_wall(self):
        self.assertIn('id="violationsSection"', self.hall_html)
        self.assertLess(
            self.hall_html.index('id="hallMount"'),
            self.hall_html.index('id="violationsSection"'),
            "the violations panel must sit below the badge wall, not above it",
        )

    def test_the_violations_panel_starts_hidden(self):
        idx = self.hall_html.index('id="violationsSection"')
        tag = self.hall_html[max(0, idx - 200):idx + 40]
        self.assertIn("hidden", tag)

    def test_it_stays_hidden_when_there_is_nothing_to_say(self):
        body = self.hall_js[self.hall_js.index("function renderViolations"):]
        body = body[:body.index("  async function run")]
        self.assertIn("if (!open && !revoked && !withheld)", body)
        self.assertIn("section.classList.add('hidden')", body)

    def test_every_number_comes_from_the_server(self):
        body = self.hall_js[self.hall_js.index("function renderViolations"):]
        body = body[:body.index("  async function run")]
        self.assertIn("data.open_violations", body)
        self.assertIn("data.revoked_badges", body)
        self.assertIn("data.withheld_badges", body)

    def test_the_count_is_bidi_isolated(self):
        # A bare number inside RTL prose gets reordered against
        # neighbouring punctuation without this - the badge counts on
        # the same page already carry it.
        body = self.hall_js[self.hall_js.index("function renderViolations"):]
        body = body[:body.index("  async function run")]
        self.assertIn("count.dir = 'ltr'", body)
        self.assertIn("unicodeBidi", body)

    def test_the_panel_reads_as_a_count_not_a_verdict(self):
        # Amber, and its own quieter treatment - not the red of an
        # error. Nothing on this page tells a user they failed.
        self.assertIn(".violations-section", self.app_css)
        self.assertIn("#ffc15e", self.app_css)

    # ------------------------------------------------------------ i18n
    def test_every_string_exists_in_all_four_languages(self):
        for key in KEYS:
            found = len(re.findall(rf"\b{re.escape(key)}\s*:", self.i18n_js))
            self.assertEqual(
                found, len(LANGS),
                f"{key} appears {found} time(s), expected one per language",
            )

    def test_no_string_is_left_as_english_in_another_language(self):
        for key in ("violations_title", "plan_day_locked_toast"):
            values = re.findall(rf"\b{re.escape(key)}\s*:\s*(['\"])(.*?)\1", self.i18n_js, re.S)
            texts = [v[1] for v in values]
            self.assertEqual(len(texts), len(LANGS))
            self.assertEqual(len(set(texts)), len(LANGS), f"{key}: {texts}")

    def test_the_placeholders_survive_every_translation(self):
        for key, tokens in (
            ("plan_day_locked_note", ("{day}",)),
            ("plan_day_locked_toast", ("{day}",)),
            ("violations_revoked", ("{count}",)),
            ("violations_withheld", ("{count}",)),
        ):
            values = re.findall(rf"\b{re.escape(key)}\s*:\s*(['\"])(.*?)\1", self.i18n_js, re.S)
            self.assertEqual(len(values), len(LANGS), key)
            for _, text in values:
                for token in tokens:
                    self.assertIn(token, text, f"{token} missing from a {key} translation")

    def test_the_guide_explains_the_rule_in_all_four_languages(self):
        found = len(re.findall(r"\bviolations\s*:\s*['\"]", self.guide_js))
        self.assertEqual(found, len(LANGS), "the violations guide text is not in all four languages")


if __name__ == "__main__":
    unittest.main()
