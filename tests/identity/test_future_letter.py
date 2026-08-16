"""The letter from your future self: when it unlocks, and what it says.

Three things were asked for and are checked here: it stays locked until
a full week of the reader's own days exists, it is dated from a specific
day ahead rather than a vague "a few weeks", and it arrives out of an
envelope.

The envelope matters less than one property of it: every path through
the animation has to END with the letter readable. A flourish that can
strand the sheet inside the envelope hides the one thing the reader
opened it for.

Run: python3 -m unittest tests.identity.test_future_letter -v
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
JS = REPO_ROOT / "frontend" / "assets" / "js"
CSS = REPO_ROOT / "frontend" / "assets" / "css" / "app.css"
RUNNER = paths.PROJECT_ROOT / "tests" / "js" / "future_letter_runner.js"


class TestWhenTheLetterUnlocks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        r = subprocess.run([node, str(RUNNER)], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("future_letter_runner.js failed: " + r.stderr)
        cls.out = json.loads(r.stdout)

    def test_it_takes_a_full_week_of_days(self):
        self.assertEqual(self.out["minDays"], 7)

    def test_six_days_is_not_enough(self):
        self.assertIsNone(self.out["atSixDays"])

    def test_seven_days_produces_a_letter(self):
        self.assertIsNotNone(self.out["atSevenDays"])
        self.assertTrue(self.out["atSevenDays"]["lines"])

    def test_no_history_at_all_produces_nothing_rather_than_a_blank_letter(self):
        self.assertIsNone(self.out["noDays"])


class TestTheDateline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        r = subprocess.run([node, str(RUNNER)], capture_output=True, text=True, timeout=30)
        cls.out = json.loads(r.stdout)

    def test_it_is_written_from_ten_days_ahead(self):
        self.assertEqual(self.out["daysAhead"], 10)
        self.assertEqual(self.out["datelineOffsetDays"], 10)

    def test_the_letter_carries_it(self):
        self.assertTrue(self.out["atSevenDays"]["dateline"])

    def test_it_is_in_the_readers_own_calendar(self):
        # A Persian reader should see a Jalali date, not a Gregorian one.
        self.assertNotEqual(self.out["datelineFa"], self.out["datelineEn"])
        self.assertRegex(self.out["datelineFa"], r"[۰-۹0-9]")

    def test_an_unavailable_locale_degrades_to_a_plain_date(self):
        self.assertRegex(self.out["datelineJunkLocale"], r"\d")


class TestTheEnvelope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (JS / "features/future-letter.js").read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")

    def test_the_envelope_is_built(self):
        for part in ("letter-envelope", "env-flap", "env-body", "env-seal"):
            with self.subTest(part=part):
                self.assertIn(part, self.js)
                self.assertIn(part, self.css)

    def test_the_envelope_is_hidden_from_screen_readers(self):
        # It carries no text; announcing it would just be noise.
        idx = self.js.index("letter-envelope")
        self.assertIn("aria-hidden", self.js[idx:idx + 400])

    def test_the_animation_always_ends_with_the_letter_readable(self):
        # Three paths: reduced motion, the normal sequence, and the
        # safety timeout. All must land on the static open state.
        self.assertIn("letter-instant", self.js)
        self.assertIn("prefersReduced()", self.js)
        self.assertIn("setTimeout", self.js)
        idx = self.css.index(".letter-instant .letter-card")
        body = self.css[idx:idx + 140]
        self.assertIn("opacity: 1", body)
        self.assertIn("transform: none", body)

    def test_reduced_motion_is_honoured_in_css_as_well_as_js(self):
        # The JS check covers the app's own toggle; the media query
        # covers an OS-level preference the app never sees.
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        self.assertIn(".force-reduce-motion .letter-envelope", self.css)

    def test_the_envelope_sits_on_the_same_side_in_rtl_and_ltr(self):
        idx = self.css.index(".letter-envelope {")
        self.assertIn("inset-inline-start", self.css[idx:idx + 300])


class TestTheLetterIsNeverInjectedAsMarkup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (JS / "features/future-letter.js").read_text(encoding="utf-8")

    def test_every_line_is_set_as_text(self):
        # The lines carry the reader's own stored values - their best
        # day's name among them - which must never reach the page as
        # markup.
        idx = self.js.index("function render(")
        body = self.js[idx:]
        self.assertIn("textContent", body)
        # The only innerHTML left is the envelope, which is fixed markup
        # with no user data in it.
        for match in re.finditer(r"innerHTML\s*=\s*(.+)", body):
            line = match.group(1)
            with self.subTest(line=line[:60]):
                self.assertFalse(
                    "letter.lines" in line or "letter.title" in line
                    or "letter.signOff" in line or "letter.dateline" in line,
                    "letter content assigned via innerHTML",
                )


class TestTheTextIsTranslated(unittest.TestCase):
    def test_every_letter_line_exists_in_all_four_languages(self):
        js = (JS / "features/future-letter.js").read_text(encoding="utf-8")
        start = js.index("const L = {")
        end = js.index("  /**", start)
        table = js[start:end]
        keys = re.findall(r"^\s{4}(\w+):\s*\{", table, re.MULTILINE)
        self.assertGreaterEqual(len(keys), 8, "letter text table looks truncated")
        for key in keys:
            with self.subTest(key=key):
                idx = table.index(f"{key}: {{")
                block = table[idx:idx + 1400]
                for lang in ("en:", "fa:", "ar:", "zh:"):
                    self.assertIn(lang, block, f"{key} is missing {lang}")


if __name__ == "__main__":
    unittest.main()
