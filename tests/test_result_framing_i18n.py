"""The opening line of the result screen, in the reader's own language.

`result_framing` is the first sentence a user reads about their score.
It was English-only in all four languages - so a Persian, Arabic or
Chinese reader opened their result on a sentence they might not read at
all, in the one place the app is supposed to be speaking to them.

The three tones (gentle / direct / clinical) have to stay genuinely
distinct in each language too. A "direct" line translated to read as
gently as the gentle one is not the tone the user chose, and tone_service
exists specifically to keep those apart.

Run: python3 -m unittest tests.test_result_framing_i18n -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path bootstrap

from services.tone_service import (
    LANGUAGES,
    SUPPORTED_TONES,
    _RESULT_FRAMING,
    band_for_score,
    frame_result,
    frame_result_i18n,
)

BANDS = ("great", "good", "borderline", "risk")
REPO_ROOT = Path(__file__).resolve().parents[1]


class TestEveryFramingIsTranslated(unittest.TestCase):

    def test_every_tone_and_band_exists_in_every_language(self):
        for tone in SUPPORTED_TONES:
            for band in BANDS:
                for lang in LANGUAGES:
                    with self.subTest(tone=tone, band=band, lang=lang):
                        text = _RESULT_FRAMING[tone][band][lang]
                        self.assertTrue(text.strip(), "empty framing text")

    def test_no_translation_was_left_as_the_english_string(self):
        # The failure mode this guards: pasting the English in as a
        # placeholder, which passes a "key exists" check but ships an
        # untranslated line.
        for tone in SUPPORTED_TONES:
            for band in BANDS:
                english = _RESULT_FRAMING[tone][band]["en"]
                for lang in ("fa", "ar", "zh"):
                    with self.subTest(tone=tone, band=band, lang=lang):
                        self.assertNotEqual(_RESULT_FRAMING[tone][band][lang], english)

    def test_the_non_latin_translations_are_actually_in_their_script(self):
        scripts = {
            "fa": re.compile(r"[؀-ۿ]"),
            "ar": re.compile(r"[؀-ۿ]"),
            "zh": re.compile(r"[一-鿿]"),
        }
        for tone in SUPPORTED_TONES:
            for band in BANDS:
                for lang, pattern in scripts.items():
                    with self.subTest(tone=tone, band=band, lang=lang):
                        self.assertRegex(_RESULT_FRAMING[tone][band][lang], pattern)

    def test_persian_and_arabic_are_not_the_same_text(self):
        # Both use the Arabic script, which makes it easy to fill one in
        # with the other's copy and never notice.
        for tone in SUPPORTED_TONES:
            for band in BANDS:
                with self.subTest(tone=tone, band=band):
                    self.assertNotEqual(
                        _RESULT_FRAMING[tone][band]["fa"],
                        _RESULT_FRAMING[tone][band]["ar"],
                    )

    def test_the_three_tones_stay_distinct_in_every_language(self):
        for band in BANDS:
            for lang in LANGUAGES:
                with self.subTest(band=band, lang=lang):
                    texts = {_RESULT_FRAMING[t][band][lang] for t in SUPPORTED_TONES}
                    self.assertEqual(
                        len(texts), len(SUPPORTED_TONES),
                        f"two tones read identically for {band}/{lang}",
                    )

    def test_the_four_bands_stay_distinct_in_every_language(self):
        for tone in SUPPORTED_TONES:
            for lang in LANGUAGES:
                with self.subTest(tone=tone, lang=lang):
                    texts = {_RESULT_FRAMING[tone][b][lang] for b in BANDS}
                    self.assertEqual(len(texts), len(BANDS))


class TestTheAccessors(unittest.TestCase):

    def test_frame_result_still_returns_the_english_sentence(self):
        # Existing callers and older clients read this field.
        for tone in SUPPORTED_TONES:
            for score in (95.0, 70.0, 50.0, 20.0):
                with self.subTest(tone=tone, score=score):
                    self.assertEqual(
                        frame_result(score, tone),
                        _RESULT_FRAMING[tone][band_for_score(score)]["en"],
                    )

    def test_the_i18n_accessor_returns_all_four_languages(self):
        got = frame_result_i18n(84.0, "gentle")
        self.assertEqual(set(got), set(LANGUAGES))
        self.assertEqual(got["en"], frame_result(84.0, "gentle"))

    def test_an_unknown_tone_falls_back_rather_than_raising(self):
        # A bad stored preference must never block a result.
        self.assertEqual(frame_result_i18n(84.0, "shouty"), frame_result_i18n(84.0, "gentle"))
        self.assertEqual(frame_result_i18n(84.0, None), frame_result_i18n(84.0, "gentle"))

    def test_a_missing_score_still_produces_a_line(self):
        got = frame_result_i18n(None, "gentle")
        for lang in LANGUAGES:
            with self.subTest(lang=lang):
                self.assertTrue(got[lang].strip())

    def test_the_caller_cannot_mutate_the_shared_table(self):
        got = frame_result_i18n(84.0, "gentle")
        got["fa"] = "tampered"
        self.assertNotEqual(frame_result_i18n(84.0, "gentle")["fa"], "tampered")


class TestItReachesTheScreen(unittest.TestCase):

    def test_the_response_carries_the_translated_field(self):
        schema = (REPO_ROOT / "api" / "schemas" / "prediction.py").read_text(encoding="utf-8")
        self.assertIn("result_framing_i18n", schema)
        router = (REPO_ROOT / "api" / "routers" / "prediction.py").read_text(encoding="utf-8")
        self.assertIn("frame_result_i18n(", router)

    def test_the_result_screen_picks_the_readers_language(self):
        app_js = (REPO_ROOT / "frontend" / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        idx = app_js.index("result_framing_i18n")
        body = app_js[idx - 200:idx + 400]
        self.assertIn("window.DWI18n.get()", body)
        # And still degrades to the English field, then the local summary.
        self.assertIn("result.result_framing", body)
        self.assertIn("narrativeSummary(result)", body)


if __name__ == "__main__":
    unittest.main()
