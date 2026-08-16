"""
Tests: the three history-series AI Coach menu families.

frontend/assets/js/coach-history-family.js adds `trend_<field>`,
`typical_<field>` and `steady_<field>` questions, answered from the
user's own stored history rather than from today's single check-in.
Everything below runs the REAL frontend file through node (see
tests/js/history_family_runner.js), not a Python re-implementation of
its logic, so a change to the actual shipped file is what these tests
see.

Why each assertion exists, rather than just "it returned a string":

  - "up" and "better" are different claims. Rising sleep_hours is an
    improvement; rising stress_0_10 is not. A file that assumed
    higher-is-always-better would still produce fluent, confident,
    wrong answers, so both directions are asserted separately.
  - api/routers/history.py returns history MOST RECENT FIRST. An
    implementation that iterates it as-is reports every trend
    backwards - and would still look completely plausible. The
    from/to numbers are asserted, not just the verdict word.
  - A day the user marked as an exception must not reach any
    statistic; that is the same rule the analytics cards follow. The
    fixture puts an absurd value on an excluded day, so a leak is
    unmissable rather than subtle.
  - Under MIN_POINTS days these must decline and say so, not draw a
    trend through two points.

Run: python3 -m unittest tests.test_coach_history_family -v
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tests" / "js" / "history_family_runner.js"

# The menu target this family was built to reach. Counted from the real
# assembled menu (base items + every generated family), not from one file.
MIN_MENU_ITEMS = 200
LANGS = ("en", "fa", "ar", "zh")


def _run() -> dict:
    proc = subprocess.run(
        ["node", str(RUNNER), str(REPO_ROOT)],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"history_family_runner.js failed ({proc.returncode}):\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


class TestHistoryFamilyMenu(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = _run()

    def test_the_assembled_menu_reaches_the_target_size(self):
        self.assertGreaterEqual(
            self.report["menuTotal"], MIN_MENU_ITEMS,
            f"assembled coach menu is {self.report['menuTotal']} items, "
            f"below the {MIN_MENU_ITEMS} target; byCat={self.report['byCat']}",
        )

    def test_the_three_families_are_all_present(self):
        by_cat = self.report["byCat"]
        for cat in ("trend", "typical", "steady"):
            self.assertGreater(by_cat.get(cat, 0), 0, f"no {cat} items in the menu")
        # Same field list drives all three, so they must be equal in size.
        self.assertEqual(by_cat["trend"], by_cat["typical"])
        self.assertEqual(by_cat["trend"], by_cat["steady"])

    def test_no_duplicate_menu_ids(self):
        # A duplicate id means two questions race for one answer handler.
        self.assertEqual(self.report["duplicateIds"], [])

    def test_every_menu_item_has_all_four_languages(self):
        self.assertEqual(
            self.report["itemsMissingALanguage"], [],
            "these menu items are missing at least one language",
        )

    def test_every_generated_item_is_actually_answerable(self):
        # A question in the menu that no handler claims would render as
        # an empty answer bubble.
        self.assertEqual(self.report["familyIdsNotRoutable"], [])


class TestHistoryFamilyAnswers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = _run()

    def test_rising_sleep_is_reported_as_an_improvement(self):
        self.assertTrue(
            self.report["risingSleepSaysBetter"],
            f"rising sleep_hours was not called healthier: {self.report['risingSleep']}",
        )

    def test_rising_stress_is_not_reported_as_an_improvement(self):
        # The regression this guards: treating every increase as good.
        self.assertTrue(
            self.report["risingStressSaysWorse"],
            f"rising stress_0_10 was not called worse: {self.report['risingStress']}",
        )

    def test_the_series_is_read_oldest_to_newest(self):
        # The history endpoint hands back newest-first; reading it as-is
        # inverts every trend while still sounding confident.
        self.assertTrue(
            self.report["trendFromToInOrder"],
            "trend endpoints look reversed - expected 'from about 5.2 h to "
            f"about 8.1 h', got: {self.report['risingSleep']}",
        )

    def test_too_few_days_declines_instead_of_guessing(self):
        self.assertTrue(
            self.report["thinDeclines"],
            "with 2 usable days the answer should decline, not draw a trend",
        )

    def test_exception_days_never_reach_any_statistic(self):
        for family in ("Typical", "Steady", "Trend"):
            self.assertFalse(
                self.report[f"excludedLeaksInto{family}"],
                f"an excluded day's value leaked into the {family.lower()} answer",
            )
        self.assertTrue(
            self.report["typicalCountsOnlyUsableDays"],
            "the excluded day was counted in the day total",
        )

    def test_steadiness_actually_discriminates(self):
        # A constant series and a wildly swinging one must not get the
        # same verdict - otherwise the family says nothing.
        self.assertTrue(self.report["flatSaysSteady"])
        self.assertTrue(self.report["jumpySaysSwingy"])

    def test_every_family_answers_in_every_language(self):
        self.assertEqual(self.report["emptyAnswers"], 0)
        self.assertEqual(
            self.report["langsIdenticalToEnglish"], [],
            "a non-English answer came back byte-identical to English, "
            "which means the translation table fell back instead of translating",
        )

    def test_no_answer_ships_an_unfilled_placeholder(self):
        # "{value}" reaching a user is the classic template bug.
        self.assertEqual(self.report["answersWithUnfilledPlaceholders"], 0)

    def test_the_wellness_score_is_labelled_in_every_language(self):
        self.assertEqual(
            self.report["scoreShowsRawFieldName"], [],
            "these languages showed the raw 'health score' field name "
            "instead of a translated label",
        )

    def test_an_unknown_id_is_declined_not_answered(self):
        self.assertTrue(self.report["unknownIdHandled"])


if __name__ == "__main__":
    unittest.main()
