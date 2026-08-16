"""The weekly plan's opening sentence.

Run: python3 -m unittest tests.wellness.test_improvement_plan -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401

from services.wellness.improvement_plan_service import ImprovementPlanService


class TheLowerHalfOfModerate(unittest.TestCase):
    """50-60 gets its own opener, and it leads with the credit.

    It is the one place the ordinary moderate sentence lands wrong.
    Someone at 55 is either just out of the at-risk range or about to
    fall back into it, and "you're at 55, Moderate range, here are some
    adjustments" reads to them as a verdict. It is also the band where
    people are most likely to stop - far enough from healthy to feel
    pointless, close enough to at-risk to feel like failure.

    What this pins is the ORDER, not the tone: nothing may be softened
    away, so the score and the band label both still have to be in the
    sentence. They just must not be the first thing in it.
    """

    def _intro(self, score, lang="en"):
        return ImprovementPlanService._build_intro_i18n("moderate", float(score), None, [])[lang]

    def test_fifty_to_sixty_uses_the_encouraging_opener(self):
        for score in (50.0, 55.0, 59.9):
            text = self._intro(score)
            self.assertIn(
                "at-risk line", text,
                f"{score} did not get the encouraging opener",
            )

    def test_it_still_says_the_number_and_the_band(self):
        text = self._intro(55.0)
        self.assertIn("55.0/100", text, "the score was hidden rather than reordered")
        self.assertIn("Moderate", text, "the band label was dropped")

    def test_the_credit_comes_before_the_label(self):
        text = self._intro(55.0)
        self.assertLess(
            text.index("at-risk line"), text.index("Moderate"),
            "the label still leads - the point was to encourage first, explain second",
        )

    def test_outside_the_window_nothing_changes(self):
        for score in (49.9, 60.0, 61.0, 75.0):
            self.assertNotIn(
                "at-risk line", self._intro(score),
                f"{score} is outside 50-60 and should read as ordinary moderate",
            )

    def test_all_four_languages_have_it(self):
        for lang in ("en", "fa", "ar", "zh"):
            text = self._intro(55.0, lang)
            self.assertTrue(text.strip(), f"{lang} has no opener at all")
            self.assertIn("55.0/100", text, f"{lang} dropped the score")

    def test_a_missing_score_falls_back_rather_than_guessing(self):
        text = ImprovementPlanService._build_intro_i18n("moderate", None, None, [])["en"]
        self.assertNotIn("at-risk line", text)
        self.assertIn("N/A", text)


if __name__ == "__main__":
    unittest.main()
