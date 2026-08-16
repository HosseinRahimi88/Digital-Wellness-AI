"""The coach half of the two plan tracks.

The service and endpoint are covered by tests/api/test_signal_tracks.py.
This pins the wiring that lets someone ask "what should I work on?" and
"what am I already doing well?" in the chat and get their own numbers
back, plus the rules that keep those answers honest:

  - the tracks are fetched from the SERVER alongside the coach's
    digest, not recomputed in the browser and not read out of
    localStorage, which a second device would not have;
  - when there is nothing to read, both answers say so. A coach that
    invents a weakness for someone who has logged nothing is worse than
    one that admits it has not seen anything yet;
  - both answers quote the user's number against its target. "Work on
    your sleep" is advice anybody could have written;
  - the patterns use flat top-level alternatives only, because
    coach-nlu.js::extractKeywords() splits a regex source on every `|`
    with no bracket awareness - a nested group produces keyword
    fragments that match nothing;
  - four languages, including the starter chips.

Run: python3 -m unittest tests.coach.test_coach_plan_tracks_ui -v
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

REPO_ROOT = paths.PROJECT_ROOT
JS = REPO_ROOT / "frontend" / "assets" / "js"

LANGS = ("en", "fa", "ar", "zh")


class TestCoachPlanTracksUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.chat = (JS / "coach/coach-chat.js").read_text(encoding="utf-8")
        cls.context = (JS / "coach/coach-context.js").read_text(encoding="utf-8")
        cls.knowledge = (JS / "coach/coach-knowledge.js").read_text(encoding="utf-8")
        cls.api = (JS / "core/api.js").read_text(encoding="utf-8")

    # ------------------------------------------------------------- wiring
    def test_the_endpoint_is_wired(self):
        self.assertIn("planTracks: () => request('/plan/tracks')", self.api)

    def test_the_tracks_are_loaded_with_the_coachs_digest(self):
        self.assertIn("window.DWApi.planTracks()", self.context)
        self.assertIn("digest.plan_tracks", self.context)

    def test_a_failed_track_fetch_does_not_break_every_other_answer(self):
        idx = self.context.index("window.DWApi.planTracks()")
        block = self.context[idx - 200:idx + 400]
        self.assertIn("catch", block)
        self.assertIn("digest.plan_tracks = null", block)

    def test_both_intents_reach_their_answers(self):
        self.assertIn("PLAN_STRENGTHEN_PATTERNS", self.chat)
        self.assertIn("PLAN_MAINTAIN_PATTERNS", self.chat)
        self.assertIn("text: strengthenAnswer(full)", self.chat)
        self.assertIn("text: maintainAnswer(full)", self.chat)

    def test_a_paraphrase_still_lands_through_the_fuzzy_table(self):
        self.assertIn("{ key: 'plan_strengthen', keywords: kw(PLAN_STRENGTHEN_PATTERNS) }", self.chat)
        self.assertIn("{ key: 'plan_maintain', keywords: kw(PLAN_MAINTAIN_PATTERNS) }", self.chat)

    # -------------------------------------------------------- the regexes
    def test_the_patterns_use_flat_alternatives_only(self):
        """extractKeywords() splits on EVERY `|` with zero bracket
        awareness, so a nested group like (a|(b|c)) yields fragments
        that match nothing. Checked by counting bracket depth at each
        top-level alternation."""
        for name in ("PLAN_STRENGTHEN_PATTERNS", "PLAN_MAINTAIN_PATTERNS"):
            block = self.chat[self.chat.index(f"const {name} = ["):]
            block = block[:block.index("];")]
            for source in re.findall(r"/(.+?)/[a-z]*,", block):
                depth = 0
                for i, ch in enumerate(source):
                    if ch == "\\":
                        continue
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                    elif ch == "|" and depth > 1:
                        self.fail(
                            f"{name}: nested alternation at depth {depth} in "
                            f"/{source}/ - extractKeywords cannot split this"
                        )

    def test_the_patterns_cover_all_four_languages(self):
        for name in ("PLAN_STRENGTHEN_PATTERNS", "PLAN_MAINTAIN_PATTERNS"):
            block = self.chat[self.chat.index(f"const {name} = ["):]
            block = block[:block.index("];")]
            self.assertRegex(block, r"[؀-ۿ]", f"{name} has no Persian/Arabic")
            self.assertRegex(block, r"[一-鿿]", f"{name} has no Chinese")
            self.assertGreaterEqual(len(re.findall(r"^\s+/", block, re.M)), 4)

    # ------------------------------------------------------- the answers
    def test_neither_answer_invents_advice_when_there_is_nothing_to_read(self):
        for fn in ("strengthenAnswer", "maintainAnswer"):
            body = self.chat[self.chat.index(f"function {fn}(full)"):]
            body = body[:body.index("\n  }\n") + 4]
            self.assertIn("if (!tracks)", body, f"{fn} does not handle a missing fetch")
            self.assertIn("if (!list.length)", body, f"{fn} does not handle an empty track")

    def test_both_answers_quote_the_users_number_against_its_target(self):
        body = self.chat[self.chat.index("function trackLines"):]
        body = body[:body.index("\n  function strengthenAnswer")]
        self.assertIn("e.current", body)
        self.assertIn("e.target", body)

    def test_the_theme_label_is_translated_rather_than_the_english_key(self):
        body = self.chat[self.chat.index("function trackLabel"):]
        body = body[:body.index("\n  function trackLines")]
        self.assertIn("theme_i18n", body)
        self.assertIn("table[lang]", body)

    def test_every_answer_branch_exists_in_all_four_languages(self):
        for fn in ("strengthenAnswer", "maintainAnswer"):
            body = self.chat[self.chat.index(f"function {fn}(full)"):]
            body = body[:body.index("\n  }\n") + 4]
            blocks = re.findall(r"P\(\{(.*?)\}\)", body, re.S)
            self.assertGreaterEqual(len(blocks), 3, f"{fn} has fewer branches than expected")
            for block in blocks:
                for lang in LANGS:
                    self.assertRegex(
                        block, rf"\b{lang}\s*:",
                        f"{fn} has a branch missing {lang}",
                    )

    # -------------------------------------------------------- the chips
    def test_both_questions_are_offered_as_starter_prompts(self):
        block = self.knowledge[self.knowledge.index("const SUGGESTIONS = {"):]
        block = block[:block.index("\n  };")]
        for lang in LANGS:
            line = re.search(rf"^\s+{lang}: \[(.*?)\],?$", block, re.M)
            self.assertIsNotNone(line, f"no suggestions for {lang}")
            items = line.group(1).count("',") + 1
            self.assertGreaterEqual(
                items, 9,
                f"{lang} did not gain the two plan-track chips",
            )

    # -------------------------------------------------- runs in a browser
    def test_the_chat_module_parses(self):
        # A syntax error here takes the whole coach page down, and these
        # are plain scripts with no build step to catch it.
        for name in ("coach/coach-chat.js", "coach/coach-context.js", "coach/coach-knowledge.js"):
            result = subprocess.run(
                ["node", "--check", str(JS / name)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
