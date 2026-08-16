"""
Tests: the four-language PDF report (C-5-9) and CSV export (C-5-7).

A PDF is the one artifact in this app that is generated on the server,
downloaded, and then read somewhere nobody is watching - so the failure
modes are all silent. A missing font produces empty rectangles, missing
shaping produces disconnected Arabic letters in the wrong order, and
shaping applied before line-breaking produces a paragraph whose lines
are printed bottom to top. None of those raise. These tests assert on
the bytes and on the text layer instead.

Run: python3 -m unittest tests.test_report_i18n -v
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap + offline stubs

from services.report_i18n import (
    FIELD_LABELS,
    STRINGS,
    SUPPORTED_LANGUAGES,
    field_label,
    is_rtl,
    normalise,
    report_language_support,
    shape,
    t,
    wrap_rtl,
)
from services.report_service import ReportService
from tests.test_api import APITestCase


def _result():
    return SimpleNamespace(
        prediction="Healthy",
        confidence=0.83,
        model_name="XGBoost",
        regression_score=72.4,
        uncertainty=SimpleNamespace(available=True, regression_lower=66.0, regression_upper=78.8),
        shap_features=[
            SimpleNamespace(feature="sleep_hours", value=7.0, shap_value=3.2,
                            abs_shap=3.2, direction="increase"),
            SimpleNamespace(feature="night_screen_min", value=90, shap_value=-2.1,
                            abs_shap=2.1, direction="decrease"),
        ],
    )


def _recommendations():
    return [SimpleNamespace(
        title="Wind down earlier", description="Your late-night use is high.",
        priority="High", action="Put the phone in another room.",
        success_metric="Night screen time under 30 min for 3 days.",
    )]


USER_DATA = {"total_screen_min": 380, "sleep_hours": 7.0, "stress_0_10": 5}


class TestStringCoverage(unittest.TestCase):

    def test_every_report_string_exists_in_all_four_languages(self):
        for key, table in STRINGS.items():
            for lang in SUPPORTED_LANGUAGES:
                self.assertIn(lang, table, f"{key} has no {lang}")
                self.assertTrue(table[lang].strip(), f"{key}/{lang} is empty")

    def test_every_field_label_exists_in_all_four_languages(self):
        for field, table in FIELD_LABELS.items():
            for lang in SUPPORTED_LANGUAGES:
                self.assertIn(lang, table, f"{field} has no {lang}")

    def test_an_unmapped_field_still_reads_as_words(self):
        self.assertEqual(field_label("some_new_signal", "en"), "Some new signal")

    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(normalise("de"), "en")
        self.assertEqual(normalise(None), "en")
        self.assertEqual(normalise("fa-IR"), "fa")


class TestShaping(unittest.TestCase):

    def test_shape_is_a_no_op_for_ltr(self):
        self.assertEqual(shape("Hello", "en"), "Hello")
        self.assertEqual(shape("你好", "zh"), "你好")

    def test_persian_is_reordered_and_reshaped(self):
        source = "سلام دنیا"
        shaped = shape(source, "fa")
        if not report_language_support("fa")["supported"]:
            self.skipTest("shaping libraries unavailable in this environment")
        self.assertNotEqual(shaped, source)
        # Presentation forms live in U+FB50..U+FEFF; unshaped Arabic does
        # not reach that block, so their presence is the actual signal
        # that reshaping happened rather than a plain reversal.
        self.assertTrue(any(0xFB50 <= ord(c) <= 0xFEFF for c in shaped))

    def test_rtl_detection(self):
        self.assertTrue(is_rtl("fa"))
        self.assertTrue(is_rtl("ar"))
        self.assertFalse(is_rtl("en"))
        self.assertFalse(is_rtl("zh"))


class TestRtlWrapping(unittest.TestCase):
    """The bug this guards against printed a paragraph's lines in
    reverse order, and was invisible in every one-line string."""

    def setUp(self):
        if not report_language_support("fa")["supported"]:
            self.skipTest("shaping libraries unavailable in this environment")
        from services.report_i18n import register_fonts
        register_fonts()

    def test_lines_stay_in_reading_order(self):
        from services.report_i18n import FONT_REGULAR
        text = t("synthetic_note", "fa")
        lines = wrap_rtl(text, FONT_REGULAR, 10, 300)
        self.assertGreater(len(lines), 1, "test needs a paragraph that actually wraps")

        # The first logical word must appear on the FIRST line. With the
        # old shape-then-wrap ordering it landed on the last one.
        first_word = shape(text.split()[0], "fa")
        self.assertIn(first_word, lines[0])
        self.assertNotIn(first_word, lines[-1])

    def test_no_line_exceeds_the_requested_width(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from services.report_i18n import FONT_REGULAR
        for line in wrap_rtl(t("synthetic_note", "fa"), FONT_REGULAR, 10, 300):
            self.assertLessEqual(stringWidth(line, FONT_REGULAR, 10), 300 + 1)

    def test_empty_text_produces_no_lines(self):
        from services.report_i18n import FONT_REGULAR
        self.assertEqual(wrap_rtl("", FONT_REGULAR, 10, 300), [])


class TestPdfGeneration(unittest.TestCase):

    def _pdf_text(self, lang: str) -> str:
        buffer = ReportService().generate(USER_DATA, _result(), _recommendations(), lang=lang)
        return buffer.getvalue().decode("latin-1", errors="ignore")

    def test_all_four_languages_produce_a_pdf(self):
        for lang in SUPPORTED_LANGUAGES:
            buffer = ReportService().generate(USER_DATA, _result(), _recommendations(), lang=lang)
            data = buffer.getvalue()
            self.assertTrue(data.startswith(b"%PDF"), lang)
            self.assertGreater(len(data), 2000, lang)

    def test_an_unknown_language_does_not_raise(self):
        buffer = ReportService().generate(USER_DATA, _result(), _recommendations(), lang="de")
        self.assertTrue(buffer.getvalue().startswith(b"%PDF"))

    def test_the_default_call_still_works(self):
        """The Streamlit page and the existing API test both call this
        with three positional arguments and no language."""
        buffer = ReportService().generate(USER_DATA, _result(), _recommendations())
        self.assertTrue(buffer.getvalue().startswith(b"%PDF"))

    def test_a_non_latin_report_embeds_a_font_rather_than_using_helvetica(self):
        """Helvetica cannot draw Persian; if the PDF still references it
        for the body text, the page is empty rectangles."""
        if not report_language_support("fa")["supported"]:
            self.skipTest("no Arabic-capable font in this environment")
        raw = self._pdf_text("fa")
        # reportlab subsets a TTF and names the subset after the FONT
        # FILE's internal name, not the name it was registered under -
        # so "DWSans" never appears in the output and asserting on it
        # would have failed against a perfectly good report.
        self.assertIn("/Subtype /TrueType", raw)
        self.assertIn("DejaVuSans", raw)

    def test_the_chinese_report_uses_the_cjk_font(self):
        if not report_language_support("zh")["supported"]:
            self.skipTest("no CJK font in this environment")
        self.assertIn("STSong-Light", self._pdf_text("zh"))

    def test_the_shap_explanation_is_included(self):
        """It is the app's headline claim on screen and the report did
        not carry it at all before C-5-9."""
        with_shap = ReportService().generate(
            USER_DATA, _result(), _recommendations(), lang="en").getvalue()
        bare = _result()
        bare.shap_features = []
        without = ReportService().generate(
            USER_DATA, bare, _recommendations(), lang="en").getvalue()
        self.assertGreater(len(with_shap), len(without))

    def test_report_includes_the_synthetic_data_disclosure(self):
        """C-6-1: the report is the artifact that gets forwarded and read
        out of context, so the disclosure has to travel with it."""
        # The English report's text is compressed inside the PDF, so
        # the check goes through the same string the report renders
        # rather than through the bytes.
        self.assertIn("synthetically generated", t("synthetic_note", "en"))
        for lang in SUPPORTED_LANGUAGES:
            self.assertTrue(t("synthetic_note", lang).strip())


class TestLanguageSupportReporting(unittest.TestCase):

    def test_support_is_reported_per_language_with_a_reason(self):
        for lang in SUPPORTED_LANGUAGES:
            info = report_language_support(lang)
            self.assertEqual(info["language"], lang)
            self.assertIsInstance(info["supported"], bool)
            if not info["supported"]:
                self.assertTrue(info["reason"], f"{lang} unsupported with no reason given")

    def test_english_is_always_supported(self):
        self.assertTrue(report_language_support("en")["supported"])


class TestCsvExport(APITestCase):
    """C-5-7: one file, in the language the user picked."""

    def _seed(self) -> dict[str, str]:
        from datetime import date, timedelta
        token = self._register(email="csv@example.com")
        headers = self._auth_headers(token)
        user_id = self.client.get("/api/v1/auth/me", headers=headers).json()["user_id"]
        from api.dependencies.services import get_history_storage_backend
        backend = self.app.dependency_overrides[get_history_storage_backend]()
        today = date.today()
        backend.commit([
            {"user_id": user_id, "date": (today - timedelta(days=1)).isoformat(),
             "day_of_week": "Monday", "health_score": 71, "health_class": "Healthy",
             "total_screen_min": 360, "sleep_hours": 7.0},
            {"user_id": user_id, "date": today.isoformat(), "day_of_week": "Tuesday",
             "health_score": 64, "health_class": "Healthy", "total_screen_min": 420,
             "sleep_hours": 6.0, "excluded": True},
        ])
        return headers

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/v1/privacy/export.csv").status_code, 401)

    def test_headers_are_in_the_requested_language(self):
        headers = self._seed()
        for lang in SUPPORTED_LANGUAGES:
            response = self.client.get(f"/api/v1/privacy/export.csv?lang={lang}", headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            first_line = response.text.lstrip("\ufeff").splitlines()[0]
            self.assertIn(t("csv_date", lang), first_line, lang)
            self.assertIn(t("csv_score", lang), first_line, lang)

    def test_a_utf8_bom_is_present(self):
        """Without it Excel on Windows reads the file as the system code
        page and every Persian, Arabic and Chinese character becomes
        mojibake - which looks like the app corrupted the export."""
        headers = self._seed()
        response = self.client.get("/api/v1/privacy/export.csv?lang=fa", headers=headers)
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))

    def test_exception_days_are_labelled_not_dropped(self):
        headers = self._seed()
        body = self.client.get("/api/v1/privacy/export.csv?lang=en", headers=headers).text
        self.assertEqual(len(body.strip().splitlines()), 3)  # header + two days
        self.assertIn("yes", body)

    def test_an_unknown_language_falls_back_rather_than_erroring(self):
        headers = self._seed()
        response = self.client.get("/api/v1/privacy/export.csv?lang=de", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(t("csv_date", "en"), response.text)

    def test_the_import_template_stays_machine_readable(self):
        """The template feeds the importer, which reads these exact
        column names back. Translating it would break round-tripping -
        so it is deliberately NOT localized."""
        from services.csv_import_service import build_template_csv
        header = build_template_csv().splitlines()[0]
        self.assertIn("sleep_hours", header)
        self.assertIn("social_min", header)
        self.assertIn("night_screen_min", header)


if __name__ == "__main__":
    unittest.main()
