"""
Tests: the numbers the intro slides claim are true of the real app.

frontend/assets/js/intro-slides.js is marketing copy that quotes a
concrete number - "more than N ready-made questions" - in four
languages. That number went stale silently: it still said 140 after
the coach menu had grown past 200, which is the worst kind of wrong,
because nothing breaks and nobody notices.

This test reads the claim back out of the shipped file (all four
languages, including the Persian and Chinese numerals) and checks it
against the real assembled menu, built by running the actual frontend
modules through node the same way tests/test_coach_history_family.py
does. A claim larger than the truth fails; growing the menu never
does.

Run: python3 -m unittest tests.test_intro_slide_claims -v
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap

REPO_ROOT = Path(__file__).resolve().parents[1]
JS = REPO_ROOT / "frontend" / "assets" / "js"
SLIDES = JS / "intro-slides.js"

# Persian/Arabic-Indic digits -> ASCII, so the fa claim can be compared
# as a number rather than as a string.
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# Chinese writes this claim in words, not digits ("两百多个" = "more than
# two hundred"), so the numeral cannot be regex-matched the same way.
# Mapping the forms actually used in the copy is enough, and an
# unrecognised form fails loudly below rather than being skipped.
_ZH_WORD_NUMBERS = {
    "一百四十": 140,
    "两百": 200,
    "二百": 200,
    "三百": 300,
}


def _real_menu_size() -> int:
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node is not available")
    script = (
        "globalThis.window = {};"
        "window.DWI18n = { get: () => 'en', pick: (t) => t && (t.en || '') };"
        + "".join(
            f"require({json.dumps(str(JS / name))});"
            for name in (
                "coach-labels.js", "coach-field-guide.js", "coach-curriculum.js",
                "coach-breakdown.js", "coach-history-family.js", "ai-menu.js",
            )
        )
        + "console.log(window.DWAIMenu.allItems().length);"
    )
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise AssertionError("could not assemble the real menu: " + result.stderr)
    return int(result.stdout.strip())


def _claimed_counts() -> dict[str, int]:
    """The number each language's coach slide claims."""
    text = SLIDES.read_text(encoding="utf-8")
    # The coach slide is the one talking about ready-made questions.
    start = text.index("ready-made questions")
    body = text[text.rindex("body: {", 0, start):]
    body = body[: body.index("},")]

    claims: dict[str, int] = {}
    for lang in ("en", "fa", "ar", "zh"):
        m = re.search(rf"{lang}:\s*(['\"])(.*?)\1", body, re.DOTALL)
        if not m:
            continue
        line = m.group(2).translate(_DIGITS)
        digits = re.search(r"(\d{2,4})", line)
        if digits:
            claims[lang] = int(digits.group(1))
            continue
        for word, value in _ZH_WORD_NUMBERS.items():
            if word in line:
                claims[lang] = value
                break
    return claims


class TestIntroSlideQuestionCount(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.real = _real_menu_size()
        cls.claims = _claimed_counts()

    def test_the_claim_was_found_in_all_four_languages(self):
        # If a language stops being parseable the test must fail rather
        # than quietly checking three languages and passing.
        self.assertEqual(
            sorted(self.claims), ["ar", "en", "fa", "zh"],
            f"could not read the question-count claim for every language: {self.claims}",
        )

    def test_no_language_claims_more_questions_than_exist(self):
        for lang, claimed in self.claims.items():
            with self.subTest(lang=lang, claimed=claimed, real=self.real):
                self.assertLessEqual(
                    claimed, self.real,
                    f"the {lang} intro slide claims more than {claimed} ready-made "
                    f"questions, but the real assembled menu has {self.real}",
                )

    def test_every_language_claims_the_same_number(self):
        # A user switching language must not be told a different number.
        self.assertEqual(
            len(set(self.claims.values())), 1,
            f"the languages disagree about the question count: {self.claims}",
        )

    def test_the_claim_has_not_fallen_a_whole_step_behind(self):
        # This is the test for the bug that actually happened: the copy
        # said 140 while the menu held 202. Nothing above catches that -
        # 140 is a true statement about a 202-item menu, just a badly
        # outdated one.
        #
        # The rule that does catch it: the claim is a floor rounded down
        # to the nearest STEP, so it must be at least the real count
        # rounded down the same way. 202 -> 200, and 140 is a full step
        # below that. Growing the menu inside a step (202 -> 249) still
        # needs no edit; crossing one (250) does.
        step = 50
        claimed = max(self.claims.values())
        expected_floor = (self.real // step) * step
        self.assertGreaterEqual(
            claimed, expected_floor,
            f"the slides claim {claimed} ready-made questions but the menu has "
            f"{self.real}; the claim should be at least {expected_floor}",
        )


if __name__ == "__main__":
    unittest.main()
