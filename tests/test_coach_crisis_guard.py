"""AI Coach crisis guard - coverage across all four UI languages (P6).

Two real, safety-critical bugs found and fixed this round, while doing
the mixed-language/typo testing this priority calls for:

1. CRISIS_PATTERNS in coach-chat.js had regex coverage for English and
   Persian ONLY. A message expressing suicidal ideation in Arabic or
   Chinese had no pattern to match at all and fell straight through to
   the generic "I'm not sure I follow" fallback - even though the
   crisis RESPONSE TEXT itself (c.crisis) was already fully translated
   into all four languages. The gap was purely in detection.

2. Even within English, `/\b(...|suicid|...)\b/i` never actually
   matched the word "suicide" - wrapping the whole alternation in a
   shared `\b...\b` group means "suicid" has to be a complete word on
   its own, but "suicide"/"suicidal" always continue past the "d" with
   a word character ("e"/"al"), so there is never a boundary there.
   "i want to kill myself" (the one pre-existing test) happened to use
   a different alternative and never exercised this path.

Both are now fixed: CRISIS_PATTERNS covers en/fa/ar/zh with broader,
more natural phrasings (biased toward recall - a false positive costs
one extra "please talk to a professional" sentence; a false negative
means real distress gets a chirpy stats reply), and "suicid" is now
"suicid\\w*".

Runs the real coach-nlu.js/coach-knowledge*.js/coach-chat.js under node
(tests/js/crisis_guard_runner.js), same established pattern as
tests/test_coach_nlu_coverage.py, so this sees the actual regex list.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parent / "js" / "crisis_guard_runner.js"


class TestCrisisGuardCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        result = subprocess.run(
            [node, str(RUNNER), str(REPO_ROOT)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise AssertionError("crisis_guard_runner.js failed: " + result.stderr)
        cls.report = json.loads(result.stdout)

    def test_every_language_has_positive_crisis_cases_covered(self):
        for lang, cases in self.report["positive"].items():
            offenders = [c["msg"] for c in cases if c["kind"] != "crisis"]
            self.assertEqual(
                offenders, [],
                f"lang={lang}: these real crisis phrasings were NOT caught: {offenders}",
            )

    def test_all_four_languages_have_at_least_one_positive_case(self):
        # Guards against the corpus itself silently losing a language
        # bucket (which would make the test above vacuously pass for it).
        self.assertEqual(set(self.report["positive"]), {"en", "fa", "ar", "zh"})
        for lang, cases in self.report["positive"].items():
            self.assertGreaterEqual(len(cases), 4, f"lang={lang} has too few positive cases")

    def test_ordinary_messages_with_superficially_similar_words_are_not_flagged(self):
        # The other direction: "killing me" (hyperbole), "ended" (a streak,
        # a bad habit), etc. must NOT trip the guard - a false positive
        # every time someone says a habit is "ending" would make the
        # coach useless, and would also be its own kind of alarming.
        for lang, cases in self.report["negative"].items():
            offenders = [c["msg"] for c in cases if c["kind"] == "crisis"]
            self.assertEqual(
                offenders, [],
                f"lang={lang}: these ordinary messages were wrongly flagged as crisis: {offenders}",
            )

    def test_the_word_suicide_itself_is_caught_in_english(self):
        # The specific regression this file pins: "suicid" wrapped in a
        # shared \b(...)\b group never matched "suicide" at all.
        en_cases = {c["msg"]: c["kind"] for c in self.report["positive"]["en"]}
        self.assertIn("thinking about suicide", en_cases)
        self.assertEqual(en_cases["thinking about suicide"], "crisis")


if __name__ == "__main__":
    unittest.main()
