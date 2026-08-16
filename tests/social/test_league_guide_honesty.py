"""The Friends League guide must describe the table that actually renders.

The defect: the leaderboard guide said "Your own score comes first,
always" in English, and the Persian read "امتیاز خودت همیشه اول است" -
which a reader takes as "your score is always ranked first". Neither is
true. frontend/assets/js/pages/league.js sorts everyone who has shared a
score highest-first and gives equal scores a shared rank, so the user's
place is whatever their score earns.

A guide that tells a user they always win is worse than no guide, so
this pins the claim in every language the app ships.
"""

from __future__ import annotations

import re
import unittest

from core import paths

GUIDE = paths.PROJECT_ROOT / "frontend/assets/js/guide/guide-tips.js"
LEAGUE_PAGE = paths.PROJECT_ROOT / "frontend/assets/js/pages/league.js"

LANGUAGES = ("en", "fa", "ar", "zh")

# "always first" in each language the app ships.
FORBIDDEN = (
    "comes first, always",
    "always first",
    "همیشه اول",
    "أولاً، دائماً",
    "دائماً أولاً",
    "永远排在最前面",
    "永远第一",
)


class TestTheLeaderboardGuide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = GUIDE.read_text(encoding="utf-8")
        cls.entries = re.findall(
            r"league_leaderboard:\s*(['\"])(.+?)\1", cls.guide, re.DOTALL
        )

    def test_the_topic_is_translated_into_every_language(self):
        # One registry entry (face/priority) plus one string per language.
        self.assertEqual(
            len(self.entries), len(LANGUAGES),
            f"expected {len(LANGUAGES)} translations, found {len(self.entries)}",
        )

    def test_no_language_claims_the_user_is_always_first(self):
        for _quote, text in self.entries:
            for phrase in FORBIDDEN:
                self.assertNotIn(
                    phrase, text,
                    f"leaderboard guide still claims the user always wins: {text[:70]}",
                )

    def test_every_language_still_explains_the_sharing_rule(self):
        # The one genuinely useful thing the old copy said: friends only
        # appear for categories they opted into. Losing it while fixing
        # the false half would be a regression of its own.
        markers = ("shared", "share", "اشتراک", "مشارك", "分享")
        for _quote, text in self.entries:
            self.assertTrue(
                any(marker in text for marker in markers),
                f"sharing rule missing from: {text[:70]}",
            )


class TestThePageActuallyRanksByScore(unittest.TestCase):
    """If the page ever stops ranking by score, the new copy becomes the
    wrong description and this test is what says so."""

    @classmethod
    def setUpClass(cls):
        cls.page = LEAGUE_PAGE.read_text(encoding="utf-8")

    def test_standings_are_sorted_by_score_descending(self):
        self.assertIn(".sort((a, b) => b.score - a.score)", self.page)

    def test_equal_scores_share_a_rank(self):
        self.assertIn("entry.score === lastScore", self.page)


if __name__ == "__main__":
    unittest.main()
