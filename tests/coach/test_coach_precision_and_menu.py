"""Precision, the command menu, and a lapsed demo's checkmarks.

Three things this round measured on the running app rather than assumed.

1. PRECISION. The coach understood in-scope questions well (89.9% over a
   7935-case corpus) and answered out-of-scope ones confidently, which is
   worse than refusing. 4 of 9 plainly off-topic questions got an answer:
   "how far is the moon?" was told about browser support. The cause was
   not the threshold. wordMatchesToken() did an unguarded symmetric
   substring test whenever either side contained a CJK character, so
   every CJK keyword was a wildcard for every language - "a" is inside
   "shap因素是什么", "far" inside "在safari里能用吗", "i" inside
   "教练是真的ai吗", each scoring 0.9.

2. THE MENU. All 202 menu questions were run through the real answer
   path in four languages against a real 23-day demo account. Two were
   broken in all four: "compare my first days to my most recent days"
   printed "Your early average was NaN, recent average is NaN" (it read
   before_avg / after_avg; the wire names are before_avg_score /
   after_avg_score), and "what badges do I have?" printed
   "😴 undefined, 🏃 undefined" (persona identity badges carry
   key/label/icon, never title).

   Typing a menu question instead of clicking it was a different path
   with a different outcome: 37 of the 202 came back "I'm not sure I
   follow", from an app listing that exact question in its own menu.

3. A LAPSED DEMO'S CHECKMARKS. Seeding ticks by calendar date left holes
   in the middle of the week, so a 15-day lapsed demo rendered day 2
   undone with days 3 and 4 fully ticked AND locked - a state the app
   cannot reach on its own.

Run: python3 -m unittest tests.coach.test_coach_precision_and_menu -v
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

REPO_ROOT = paths.PROJECT_ROOT
RUNNER = paths.PROJECT_ROOT / "tests" / "js" / "coach_precision_runner.js"
JS = REPO_ROOT / "frontend" / "assets" / "js"


class TestOffTopicIsDeclined(unittest.TestCase):
    """Executed under node against the real frontend files."""

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        result = subprocess.run(
            [node, str(RUNNER), str(REPO_ROOT)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise AssertionError(f"runner failed:\n{result.stderr}")
        cls.report = json.loads(result.stdout)

    def test_nothing_off_topic_is_answered(self):
        answered = self.report["answered"]
        self.assertEqual(
            answered, [],
            "these are not questions about this app, and were answered anyway:\n"
            + "\n".join(f"  [{a['lang']}] {a['q']} -> {a['text']}" for a in answered),
        )

    def test_in_scope_questions_still_get_answers(self):
        """The other half of the trade. A precision fix that starts
        declining real questions has gone too far."""
        self.assertEqual(
            self.report["wronglyDeclined"], [],
            f"declined a real question: {self.report['wronglyDeclined']}",
        )

    def test_a_cjk_keyword_is_no_longer_a_wildcard(self):
        w = self.report["wildcards"]
        self.assertEqual(w["a_in_shap"], 0, '"a" must not match "shap因素是什么"')
        self.assertEqual(w["far_in_safari"], 0, '"far" must not match "在safari里能用吗"')
        self.assertEqual(w["i_in_ai"], 0, '"i" must not match "教练是真的ai吗"')

    def test_a_whole_latin_fragment_inside_a_cjk_keyword_still_matches(self):
        """The case the branch exists for: a Chinese reader typing
        "shap" or "csv" must still reach the topic."""
        w = self.report["wildcards"]
        self.assertEqual(w["shap_in_shap"], 0.9)
        self.assertEqual(w["csv_in_csv"], 0.9)

    def test_the_known_collision_is_no_longer_answered(self):
        """"boiling" is still two edits from "failing" (0.714), above
        the 0.7 fuzzy floor, so the words still collide - but the
        question is no longer answered as if they matched.

        The previous version of this test asserted the opposite and said
        so out loud: "recorded as the current truth. If a later change
        fixes it, this flips." Weighting a keyword by how much of the
        question it accounts for is that change. A seven-letter word
        inside a longer sentence no longer carries the whole match on
        its own, so the collision stays a collision in the edit
        distance and stops being a wrong answer in the reply."""
        miss = self.report["knownMiss"]
        self.assertAlmostEqual(miss["similarity"], 0.714, places=3)
        self.assertFalse(miss["stillAnswered"])


class TestTheCJKGuardIsTheRightShape(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nlu = (JS / "coach/coach-nlu.js").read_text(encoding="utf-8")

    def test_cjk_to_cjk_keeps_the_plain_substring_rule(self):
        self.assertIn("if (isCJK(token) && isCJK(word)) {", self.nlu)

    def test_a_latin_query_word_must_match_a_whole_fragment(self):
        block = self.nlu[self.nlu.index("function wordMatchesToken"):]
        block = block[:block.index("// Short, extremely generic words")]
        self.assertIn("fragment === latinSide", block)
        self.assertIn("latinSide.length < 3", block)

    def test_the_removed_length_guard_is_explained(self):
        """It was tried, cost 2.3 points of Chinese recall, and caught
        nothing - worth recording so it is not re-added."""
        self.assertIn("87.9% -> 85.6%", self.nlu)


class TestMenuAnswers(unittest.TestCase):
    """The two answers that were broken in all four languages."""

    @classmethod
    def setUpClass(cls):
        cls.menu = (JS / "coach/ai-menu.js").read_text(encoding="utf-8")
        cls.page = (REPO_ROOT / "frontend" / "coach.html").read_text(encoding="utf-8")

    def test_before_after_reads_the_real_wire_names(self):
        self.assertIn("ba.before_avg_score", self.menu)
        self.assertIn("ba.after_avg_score", self.menu)

    def test_before_after_refuses_rather_than_printing_nan(self):
        block = self.menu[self.menu.index("case 'before_after'"):]
        block = block[:block.index("const VERDICT")]
        self.assertIn("Number.isFinite", block)

    def test_badges_are_named_from_their_key_not_a_title_that_never_existed(self):
        self.assertNotIn("${b.icon || '🥇'} ${b.title}", self.menu)
        self.assertIn("IDENTITY_BADGE_NAMES", self.menu)

    def test_every_identity_badge_is_named_in_four_languages(self):
        block = self.menu[self.menu.index("const IDENTITY_BADGE_NAMES = {"):]
        block = block[:block.index("\n  };")]
        keys = re.findall(r"^\s{4}(\w+): \{", block, re.M)
        # The eight in utils/persona_titles.py.
        self.assertEqual(len(keys), 8, f"found {keys}")
        for lang in ("en", "fa", "ar", "zh"):
            self.assertEqual(
                len(re.findall(rf"{lang}: '", block)), 8,
                f"an identity badge is missing its {lang} name",
            )

    def test_the_names_match_the_servers_badge_keys(self):
        titles = (REPO_ROOT / "utils" / "persona_titles.py").read_text(encoding="utf-8")
        server_keys = set(re.findall(r'Badge\("(\w+)"', titles))
        block = self.menu[self.menu.index("const IDENTITY_BADGE_NAMES = {"):]
        block = block[:block.index("\n  };")]
        client_keys = set(re.findall(r"^\s{4}(\w+): \{", block, re.M))
        self.assertEqual(
            server_keys, client_keys,
            "the client's badge names and the server's badge keys have drifted",
        )


class TestTypedMenuQuestionsReachTheirAnswer(unittest.TestCase):
    """Clicking a menu question and typing it were different paths with
    different outcomes - 37 of 202 typed questions were declined."""

    @classmethod
    def setUpClass(cls):
        cls.coach = (JS / "coach/coach.js").read_text(encoding="utf-8")

    def test_there_is_a_menu_fallback(self):
        self.assertIn("function menuAnswerFor(text)", self.coach)
        self.assertIn("menu.getAnswer(hit.match.key", self.coach)

    def test_it_runs_only_after_the_ordinary_path_declined(self):
        """So nothing that already worked can change."""
        respond_at = self.coach.index("let reply = window.DWCoachChat.respond(")
        fallback_at = self.coach.index("const fromMenu = await menuAnswerFor(text);")
        self.assertLess(respond_at, fallback_at)
        self.assertIn("if (reply.kind === 'info' && await isUnknownReply(reply))", self.coach)

    def test_the_threshold_is_higher_than_the_default(self):
        """The menu question has to be most of what the user typed, not
        merely share a word with it - otherwise this becomes a new way
        to answer an off-topic question."""
        match = re.search(r"classify\(text, intents, \{ threshold: ([\d.]+) \}\)", self.coach)
        self.assertIsNotNone(match)
        self.assertGreaterEqual(float(match.group(1)), 0.75)

    def test_the_decline_is_recognised_from_the_copy_not_a_keyword(self):
        """So it keeps working in all four languages."""
        block = self.coach[self.coach.index("async function isUnknownReply"):]
        block = block[:block.index("\n  }")]
        self.assertIn("c.clarify", block)
        self.assertIn("c.unknown", block)


class TestLapsedDemoTicksOnlyMissTheDaysMissed(unittest.TestCase):
    """A miss is a miss for that day, not for the rest of the run.

    This class previously asserted the opposite - that the first
    unlogged day latched a flag and stopped the week, so the ticks
    formed a prefix. That was a deliberate design, but it produced a
    23-day lapsed demo with 24 of its 28 plan days non-green: somebody
    who missed one Tuesday shown as having done nothing since. The
    product rule is that a lapsed run shows roughly three to nine
    non-green days, so the latch was removed and this test now pins the
    behaviour that replaced it. Measured after the change: 12 non-green
    of 27 past days against 24 before, of which about seven are the
    lapse itself and the rest are days that predate the account.
    """

    @classmethod
    def setUpClass(cls):
        cls.demo = (REPO_ROOT / "api" / "routers" / "demo.py").read_text(encoding="utf-8")

    def test_a_missed_day_no_longer_stops_the_whole_week(self):
        block = self.demo[self.demo.index("ticks: list[tuple[int, int]] = []"):]
        block = block[:block.index("progress_service.set_many_completed")]
        self.assertNotIn("stopped = True", block)
        self.assertNotIn("if stopped:", block)

    def test_an_unlogged_day_is_still_the_day_that_goes_unticked(self):
        block = self.demo[self.demo.index("ticks: list[tuple[int, int]] = []"):]
        block = block[:block.index("progress_service.set_many_completed")]
        self.assertIn("if with_violations and when_str not in logged_dates:", block)

    def test_the_ledger_still_charges_for_every_missed_day(self):
        """The lapse is only softened in the checkmarks, never forgiven
        in the violation ledger."""
        self.assertIn("violation_service.assess_day(", self.demo)

    def test_the_rule_it_is_matching_is_named(self):
        self.assertIn("unlocked_through", self.demo)


class TestUpcomingDaysAreMarked(unittest.TestCase):
    """A day later this week is not a day you failed - but left as a
    plain grey square it was indistinguishable from a cell that failed
    to render, which is what "the days had no colour" described."""

    @classmethod
    def setUpClass(cls):
        cls.js = (JS / "pages/dashboard.js").read_text(encoding="utf-8")
        cls.css = (REPO_ROOT / "frontend" / "assets" / "css" / "shell.css").read_text(encoding="utf-8")
        cls.i18n = (JS / "core/i18n.js").read_text(encoding="utf-8")

    def test_the_cell_gets_an_explicit_class(self):
        self.assertIn("cell.classList.add('day-upcoming')", self.js)

    def test_it_has_its_own_style(self):
        self.assertIn(".heatmap-cell.day-upcoming {", self.css)

    def test_it_is_labelled_in_four_languages(self):
        self.assertEqual(self.i18n.count("day_status_upcoming:"), 4)

    def test_an_upcoming_day_is_never_given_a_penalty(self):
        """It carries no status from the server at all, so there is
        nothing to charge - asserted here so a later change cannot
        quietly start scoring days that have not happened."""
        block = self.js[self.js.index("cell.classList.add('day-upcoming')"):]
        block = block[:block.index("} else {")]
        self.assertNotIn("penalty", block)


if __name__ == "__main__":
    unittest.main()
