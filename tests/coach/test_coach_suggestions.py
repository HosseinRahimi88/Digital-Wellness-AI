"""The coach's improvement answer, in two halves with several ideas each.

What this replaces: the coach could answer "what is weak?" and "what am
I doing well?" as two separate questions, each returning a list of
signals with a number against a target. "Sleep 5.4 / 7.5" is a
diagnosis; it is not something to do tonight. And the question people
actually ask is neither half - it is "how do I get better", whose honest
answer has both.

What this pins:

  · both halves are always present, and the "already working" half comes
    FIRST. It is the cheaper half and the one that gets dropped first,
    so burying it under the fixes gets the emphasis backwards;
  · each named signal carries SEVERAL ideas, not one - one idea that
    does not suit you is the same as no idea;
  · every idea exists in all four languages. A half-translated bank is
    how a Persian reader ends up with English advice under a Persian
    heading;
  · an idea can only appear against the signal it was written for -
    "charge the phone in another room" must not surface under
    notifications;
  · with nothing to report on one side, that side says so plainly
    rather than inventing a strength or a fault;
  · with no plan at all, the whole thing returns null so the caller can
    say it could not read the plan instead of answering from nothing.

The node runner loads the actual frontend files - no reimplementation.

Run: python3 -m unittest tests.coach.test_coach_suggestions -v
"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

import tests._test_support  # noqa: F401

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

ROOT = paths.PROJECT_ROOT
RUNNER = ROOT / "tests" / "js" / "coach_suggestions_runner.js"
LANGS = ("en", "fa", "ar", "zh")


class CoachSuggestions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        proc = subprocess.run(
            [node, str(RUNNER)], capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            raise AssertionError(f"runner failed:\n{proc.stderr}")
        cls.out = json.loads(proc.stdout)

    # ---------------------------------------------------------- shape
    def test_both_halves_are_present_in_every_language(self):
        for lang in LANGS:
            text = self.out["languages"][lang]["full"]
            self.assertTrue(text, f"{lang}: no answer at all")
            self.assertIn("①", text, f"{lang}: the 'already working' half is missing")
            self.assertIn("②", text, f"{lang}: the 'needs work' half is missing")

    def test_the_half_that_is_already_working_comes_first(self):
        for lang in LANGS:
            text = self.out["languages"][lang]["full"]
            self.assertLess(
                text.index("①"), text.index("②"),
                f"{lang}: the fixes were put above the strengths",
            )

    def test_each_named_signal_carries_several_ideas(self):
        for lang in LANGS:
            text = self.out["languages"][lang]["full"]
            bullets = text.count("•")
            # Two signals per half, three ideas each.
            self.assertGreaterEqual(
                bullets, 12,
                f"{lang}: only {bullets} ideas across four signals - the point was several each",
            )

    def test_the_users_own_numbers_are_quoted_not_generic_advice(self):
        for lang in LANGS:
            text = self.out["languages"][lang]["full"]
            for fragment in ("5.4", "7.5", "180", "60", "55", "30"):
                self.assertIn(
                    fragment, text,
                    f"{lang}: the answer dropped the user's own number {fragment}",
                )

    # ------------------------------------------------------- the bank
    def test_every_idea_exists_in_all_four_languages(self):
        missing = {}
        for field, halves in self.out["ideaBank"].items():
            for half, ideas in halves.items():
                for i, absent in enumerate(ideas):
                    if absent:
                        missing[f"{field}.{half}[{i}]"] = absent
        self.assertEqual(missing, {}, f"ideas missing a language: {missing}")

    def test_every_signal_has_ideas_for_both_halves(self):
        for field, halves in self.out["ideaBank"].items():
            self.assertIn("fix", halves, f"{field} has no ideas for when it is weak")
            self.assertIn("keep", halves, f"{field} has no ideas for when it is strong")
            for half in ("fix", "keep"):
                self.assertGreaterEqual(
                    len(halves[half]), 3,
                    f"{field}.{half} offers fewer than three ideas",
                )

    def test_the_bank_covers_exactly_the_plans_own_signals(self):
        """A signal the plan can raise with no ideas behind it would
        print a bare number - which is the state this replaced."""
        from services.wellness.improvement_plan_service import ImprovementPlanService

        plan_fields = {r["field"] for r in ImprovementPlanService._HABIT_RULES}
        bank_fields = set(self.out["ideaBank"])
        self.assertEqual(
            plan_fields - bank_fields, set(),
            "the plan can raise a signal this bank has no ideas for",
        )
        self.assertEqual(
            bank_fields - plan_fields, set(),
            "the bank carries ideas for a signal the plan never raises",
        )

    def test_an_idea_cannot_surface_under_the_wrong_signal(self):
        """Indexed by field, so this is structural - but worth pinning,
        because the failure would be silent and embarrassing."""
        text = self.out["languages"]["en"]["full"]
        sleep_at = text.index("Sleep")
        notif_at = text.index("Notification")
        charger = text.index("Charge the phone in another room")
        self.assertLess(sleep_at, charger)
        self.assertLess(charger, notif_at, "a sleep idea appeared under notifications")

    # ------------------------------------------------------ the edges
    def test_an_empty_half_says_so_rather_than_inventing(self):
        for lang in LANGS:
            no_maintain = self.out["languages"][lang]["noMaintain"]
            no_strengthen = self.out["languages"][lang]["noStrengthen"]
            self.assertIn("①", no_maintain)
            self.assertIn("②", no_maintain)
            # With nothing to protect, the first half must not still be
            # listing bullets - it has nothing to list.
            first_half = no_maintain.split("②")[0]
            self.assertNotIn(
                "•", first_half,
                f"{lang}: named a strength when the plan reported none",
            )
            second_half = no_strengthen.split("②")[1]
            self.assertNotIn(
                "•", second_half,
                f"{lang}: named a fault when the plan reported none",
            )

    def test_no_plan_returns_nothing_rather_than_generic_advice(self):
        for lang in LANGS:
            self.assertIsNone(
                self.out["languages"][lang]["missing"],
                f"{lang}: answered with advice when there was no plan to read",
            )

    def test_asking_twice_does_not_repeat_word_for_word(self):
        """The SET of ideas is fixed; only the order rotates. Nothing is
        invented to keep it fresh, and nothing is dropped either."""
        for lang in LANGS:
            first = self.out["languages"][lang]["full"]
            second = self.out["languages"][lang]["rotated"]
            self.assertNotEqual(first, second, f"{lang}: identical on a second ask")
            self.assertEqual(
                sorted(first.split("\n")), sorted(second.split("\n")),
                f"{lang}: the rotation changed WHAT is said, not just the order",
            )


if __name__ == "__main__":
    unittest.main()
