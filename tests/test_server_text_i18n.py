"""Server-composed sentences, in the reader's own language.

Some text on the result and dashboard screens is written by the backend
rather than by i18n.js, because it is assembled from the user's own
numbers and thresholds: the confidence reading, the out-of-distribution
warning, the cold-start note. All three were English-only in every
language - a Persian reader got a Persian page whose explanation of how
much to trust their own score was in English.

The server cannot pick the language (that choice lives in the browser's
localStorage), so it sends every sentence in all four and the UI selects
one. These tests pin that all four exist, that none was left as an
English placeholder, and that the selection helper degrades rather than
rendering a blank where a sentence belongs.

Run: python3 -m unittest tests.test_server_text_i18n -v
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path bootstrap

from services.insight_service import (
    LANGUAGES,
    _COLD_START_MESSAGE,
    _CONFIDENCE_DETAIL,
    _CONFIDENCE_HEADLINE,
    _CONFIDENCE_RANGE,
    _OOD_MESSAGE,
    InsightService,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
JS = REPO_ROOT / "frontend" / "assets" / "js"
RUNNER = Path(__file__).resolve().parent / "js" / "server_text_runner.js"

SCRIPTS = {
    "fa": re.compile(r"[؀-ۿ]"),
    "ar": re.compile(r"[؀-ۿ]"),
    "zh": re.compile(r"[一-鿿]"),
}


def _all_tables():
    """(name, {lang: text}) for every translated sentence."""
    for level, table in _CONFIDENCE_HEADLINE.items():
        yield f"confidence_headline/{level}", table
    for level, table in _CONFIDENCE_DETAIL.items():
        yield f"confidence_detail/{level}", table
    for stage, table in _COLD_START_MESSAGE.items():
        yield f"cold_start/{stage}", table
    yield "ood_message", _OOD_MESSAGE
    yield "confidence_range", _CONFIDENCE_RANGE


class TestEverySentenceIsTranslated(unittest.TestCase):

    def test_every_sentence_exists_in_every_language(self):
        for name, table in _all_tables():
            for lang in LANGUAGES:
                with self.subTest(sentence=name, lang=lang):
                    self.assertIn(lang, table)
                    self.assertTrue(table[lang].strip(), "empty text")

    def test_nothing_was_left_as_the_english_placeholder(self):
        for name, table in _all_tables():
            for lang in ("fa", "ar", "zh"):
                with self.subTest(sentence=name, lang=lang):
                    self.assertNotEqual(table[lang], table["en"])

    def test_each_translation_is_in_its_own_script(self):
        for name, table in _all_tables():
            for lang, pattern in SCRIPTS.items():
                with self.subTest(sentence=name, lang=lang):
                    self.assertRegex(table[lang], pattern)

    def test_persian_and_arabic_are_not_the_same_text(self):
        # Both use the Arabic script, so one can be pasted into the other
        # without it looking wrong at a glance.
        for name, table in _all_tables():
            with self.subTest(sentence=name):
                self.assertNotEqual(table["fa"], table["ar"])

    def test_the_placeholders_survive_every_translation(self):
        # A translation that dropped {names} or {points} would render a
        # sentence with the user's own figure missing from it.
        for lang in LANGUAGES:
            with self.subTest(lang=lang, token="{names}"):
                self.assertIn("{names}", _OOD_MESSAGE[lang])
            with self.subTest(lang=lang, token="{points}"):
                self.assertIn("{points}", _CONFIDENCE_RANGE[lang])

    def test_the_confidence_wording_never_upgrades_to_certainty(self):
        # This project's leakage-fixed evaluation showed the classifier is
        # OVERCONFIDENT on new users, so 70-90% is deliberately described
        # as "reasonably confident, not certain". A translation that
        # promoted that to plain certainty would misstate the model.
        moderate = _CONFIDENCE_HEADLINE["moderate"]
        self.assertIn("not certain", moderate["en"])
        self.assertIn("قطعی نه", moderate["fa"])
        self.assertIn("ليس متيقناً", moderate["ar"])
        self.assertIn("并不确定", moderate["zh"])


class TestTheServiceEmitsThem(unittest.TestCase):

    def test_confidence_label_carries_both_parts_in_four_languages(self):
        label = InsightService.confidence_label(95.0, None)
        self.assertEqual(set(label.text_i18n), {"headline", "detail"})
        for part in ("headline", "detail"):
            with self.subTest(part=part):
                self.assertEqual(set(label.text_i18n[part]), set(LANGUAGES))
        # The flat English fields must keep working for older clients.
        self.assertEqual(label.headline, label.text_i18n["headline"]["en"])
        self.assertEqual(label.detail, label.text_i18n["detail"]["en"])

    def test_the_interval_sentence_is_appended_in_every_language(self):
        # The regression this covers: a translated paragraph that ended
        # in an English clause about the reader's own score range.
        class U:
            regression_interval_width = 9.0

        label = InsightService.confidence_label(95.0, U())
        for lang in LANGUAGES:
            with self.subTest(lang=lang):
                self.assertIn("9", label.text_i18n["detail"][lang])
        for lang in ("fa", "ar", "zh"):
            with self.subTest(lang=lang):
                self.assertNotIn("points", label.text_i18n["detail"][lang])

    def test_no_interval_means_no_appended_clause(self):
        label = InsightService.confidence_label(95.0, None)
        self.assertEqual(label.text_i18n["detail"]["en"], _CONFIDENCE_DETAIL["high"]["en"])

    def test_cold_start_carries_the_message_in_four_languages(self):
        for count in (0, 1, 4, 8, 30):
            with self.subTest(entries=count):
                st = InsightService.cold_start_status(count)
                self.assertEqual(set(st.text_i18n["message"]), set(LANGUAGES))
                self.assertEqual(st.message, st.text_i18n["message"]["en"])

    def test_an_in_distribution_day_carries_no_warning_at_all(self):
        # An empty warning must stay empty rather than becoming four
        # translations of nothing.
        report = InsightService.check_out_of_distribution({"sleep_hours": 7.5})
        if not report.is_out_of_distribution:
            self.assertEqual(report.message, "")


class TestTheResponseSchemasCarryIt(unittest.TestCase):

    def test_the_three_schemas_declare_text_i18n(self):
        pred = (REPO_ROOT / "api" / "schemas" / "prediction.py").read_text(encoding="utf-8")
        prog = (REPO_ROOT / "api" / "schemas" / "progress.py").read_text(encoding="utf-8")
        for cls, src in (("ConfidenceLabelResponse", pred),
                         ("OODReportResponse", pred),
                         ("ColdStartResponse", prog)):
            with self.subTest(cls=cls):
                idx = src.index(f"class {cls}(BaseModel):")
                self.assertIn("text_i18n", src[idx:idx + 700])


class TestTheHelperThatPicksOne(unittest.TestCase):
    """The real frontend server-text.js, run under node."""

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        r = subprocess.run([node, str(RUNNER)], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("server_text_runner.js failed: " + r.stderr)
        cls.out = json.loads(r.stdout)

    def test_it_returns_the_readers_language(self):
        self.assertEqual(self.out["picksFa"], "سلام")
        self.assertEqual(self.out["picksZh"], "你好")

    def test_it_falls_back_to_english_when_that_language_is_missing(self):
        self.assertEqual(self.out["missingLangFallsToEnglish"], "hello")

    def test_it_falls_back_to_the_flat_field_for_an_older_response(self):
        # A response from before text_i18n existed still has to render.
        self.assertEqual(self.out["olderResponse"], "legacy english")

    def test_it_never_returns_an_object_or_undefined(self):
        # The failure this guards: printing "[object Object]" into the
        # page by reading the map itself.
        for key in ("nullPayload", "emptyPayload", "unknownPart"):
            with self.subTest(case=key):
                self.assertEqual(self.out[key], "")
        self.assertNotIn("object", self.out["typesSeen"])

    def test_an_empty_string_translation_does_not_win_over_english(self):
        self.assertEqual(self.out["emptyTranslationFallsToEnglish"], "hello")


class TestEveryPageCanUseIt(unittest.TestCase):

    def test_the_helper_is_loaded_wherever_i18n_is(self):
        missing = []
        for html in sorted((REPO_ROOT / "frontend").glob("*.html")):
            src = html.read_text(encoding="utf-8")
            if "assets/js/i18n.js" in src and "assets/js/server-text.js" not in src:
                missing.append(html.name)
        self.assertEqual(missing, [], f"pages with i18n but no server-text.js: {missing}")

    def test_the_consumers_go_through_the_helper(self):
        for name in ("app.js", "dashboard.js", "ai-menu.js"):
            with self.subTest(file=name):
                src = (JS / name).read_text(encoding="utf-8")
                self.assertIn("DWServerText.pick", src)

    def test_no_consumer_still_reads_the_flat_field_directly(self):
        # Reading `.message` directly is exactly how these stayed English.
        dash = (JS / "dashboard.js").read_text(encoding="utf-8")
        self.assertNotIn("cold_start.message", dash)


if __name__ == "__main__":
    unittest.main()
