"""
Tests: config/recommendation_i18n.py (C-2).

The brief's architectural constraint is the thing worth guarding here:
the recommendation engine is deliberately deterministic and must stay
that way. Personalisation comes from more parameters inside the same
fixed rules, not from randomness and not from a model. So the central
assertions are "the same input always produces the same output" and
"the target is derived from the user's own number", alongside the
four-language coverage A-2 requires.

Run: python3 -m unittest tests.test_recommendation_i18n -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap + offline stubs

from config.recommendation_i18n import (
    LANGUAGES,
    PRIORITY_I18N,
    RULE_TEXT,
    SAFETY_NOTE_I18N,
    TARGETS,
    localized_text,
    personalise,
    priority_i18n,
    safety_note_i18n,
)
from config.recommendation_registry import FEATURE_RECOMMENDATIONS
from services.recommendation_service import RecommendationService
from services.shap_service import SHAPFeature


class TestCoverage(unittest.TestCase):

    def test_every_rule_in_the_registry_has_translated_text(self):
        missing = set(FEATURE_RECOMMENDATIONS) - set(RULE_TEXT)
        self.assertEqual(missing, set(), f"rules with no translation: {sorted(missing)}")

    def test_no_translations_for_rules_that_do_not_exist(self):
        extra = set(RULE_TEXT) - set(FEATURE_RECOMMENDATIONS)
        self.assertEqual(extra, set(), f"translations for unknown rules: {sorted(extra)}")

    def test_every_rule_covers_all_four_languages_in_every_part(self):
        for field, parts in RULE_TEXT.items():
            for part in ("title", "description", "action", "success_metric"):
                self.assertIn(part, parts, f"{field} has no {part}")
                for lang in LANGUAGES:
                    self.assertTrue(parts[part].get(lang, "").strip(),
                                    f"{field}.{part} has no {lang}")

    def test_every_rule_has_a_target_formula(self):
        missing = set(RULE_TEXT) - set(TARGETS)
        self.assertEqual(missing, set())

    def test_every_safety_note_in_the_registry_has_translated_text(self):
        # Recommendation cards used to show priority ("HIGH"/"LOW") and
        # the safety note in raw English on every page regardless of the
        # reader's language - title/description/action/success_metric
        # went through RULE_TEXT, these two did not. SAFETY_NOTE_I18N is
        # keyed by the exact English string rather than by rule (three
        # notes are shared across many rules), so the thing worth
        # guarding is that every string the registry actually uses is a
        # real key here - a fourth note added to the registry without a
        # matching entry would silently degrade to English rather than
        # fail a test.
        used_notes = {
            template.safety_note
            for template in FEATURE_RECOMMENDATIONS.values()
        }
        missing = used_notes - set(SAFETY_NOTE_I18N)
        self.assertEqual(missing, set(), f"safety notes with no translation: {sorted(missing)}")

    def test_every_safety_note_covers_all_four_languages(self):
        for note, table in SAFETY_NOTE_I18N.items():
            for lang in LANGUAGES:
                self.assertTrue(table.get(lang, "").strip(), f"{note[:40]}... has no {lang}")

    def test_every_priority_level_is_translated(self):
        for level in ("high", "medium", "low"):
            table = PRIORITY_I18N.get(level)
            self.assertIsNotNone(table, f"no PRIORITY_I18N entry for {level!r}")
            for lang in LANGUAGES:
                self.assertTrue(table.get(lang, "").strip(), f"{level}.{lang} is empty")

    def test_priority_i18n_is_case_insensitive_with_a_graceful_fallback(self):
        # RecommendationService stores priority as "HIGH"/"MEDIUM"/"LOW"
        # (see Recommendation.is_high_priority's .upper() check); the
        # i18n table is keyed lowercase, so the lookup must not depend on
        # the caller getting the case right.
        self.assertEqual(priority_i18n("HIGH")["fa"], PRIORITY_I18N["high"]["fa"])
        self.assertEqual(priority_i18n("Low")["zh"], PRIORITY_I18N["low"]["zh"])
        # Deliberately-broken input: an unrecognised value must not raise
        # or silently vanish - every language falls back to the raw
        # string, same contract as localized_text()'s missing-rule case.
        fallback = priority_i18n("URGENT")
        self.assertEqual(set(fallback), set(LANGUAGES))
        self.assertTrue(all(v == "URGENT" for v in fallback.values()))

    def test_safety_note_i18n_has_a_graceful_fallback(self):
        fallback = safety_note_i18n("a note that does not exist anywhere")
        self.assertEqual(set(fallback), set(LANGUAGES))
        self.assertTrue(all(v == "a note that does not exist anywhere" for v in fallback.values()))


class TestDeterminism(unittest.TestCase):
    """The brief forbids random logic and ML in this engine."""

    def test_the_same_input_always_gives_the_same_target(self):
        for _ in range(25):
            self.assertEqual(
                personalise("total_screen_min", {"total_screen_min": 380}),
                {"observed": 380.0, "target": 332.0},
            )

    def test_two_different_users_get_different_targets(self):
        light = personalise("total_screen_min", {"total_screen_min": 200})
        heavy = personalise("total_screen_min", {"total_screen_min": 600})
        self.assertNotEqual(light["target"], heavy["target"])
        self.assertLess(light["target"], heavy["target"])

    def test_the_target_is_derived_from_the_users_own_value(self):
        result = personalise("total_screen_min", {"total_screen_min": 400})
        self.assertLess(result["target"], result["observed"])
        self.assertGreater(result["target"], result["observed"] * 0.5)


class TestTargetsAreNotDemoralising(unittest.TestCase):

    def test_an_upward_target_is_never_below_what_the_user_already_does(self):
        """Telling someone who sleeps 9 hours to 'aim for 7' is the kind
        of backwards advice this file exists to avoid."""
        result = personalise("sleep_hours", {"sleep_hours": 9.0})
        self.assertGreaterEqual(result["target"], result["observed"])

    def test_a_downward_target_is_never_above_what_the_user_already_does(self):
        result = personalise("night_screen_min", {"night_screen_min": 10})
        self.assertLessEqual(result["target"], result["observed"])

    def test_someone_already_at_the_floor_is_not_asked_for_the_impossible(self):
        result = personalise("pre_sleep_screen_min", {"pre_sleep_screen_min": 5})
        self.assertGreaterEqual(result["target"], 0)


class TestMissingData(unittest.TestCase):

    def test_an_absent_field_yields_no_numbers_rather_than_zero(self):
        self.assertEqual(personalise("sleep_hours", {}), {"observed": None, "target": None})

    def test_a_non_numeric_value_is_ignored(self):
        self.assertEqual(
            personalise("sleep_hours", {"sleep_hours": "eight"}),
            {"observed": None, "target": None},
        )

    def test_a_booleans_is_not_treated_as_a_number(self):
        self.assertEqual(
            personalise("sleep_hours", {"sleep_hours": True}),
            {"observed": None, "target": None},
        )

    def test_text_still_renders_with_the_placeholder_removed(self):
        """A sentence with a visible {observed} in it is worse than one
        that simply omits the number."""
        text = localized_text("sleep_hours", {"observed": None, "target": None})
        for lang in LANGUAGES:
            self.assertNotIn("{observed}", text["description"][lang])
            self.assertNotIn("{target}", text["action"][lang])


class TestRatioFormatting(unittest.TestCase):

    def test_a_ratio_is_shown_as_a_percentage(self):
        """0.18 means nothing on a results page."""
        result = personalise("night_ratio", {"night_ratio": 0.18})
        self.assertEqual(result["observed"], 18.0)
        self.assertLessEqual(result["target"], 18.0)


class TestServiceIntegration(unittest.TestCase):

    def _features(self):
        return [
            SHAPFeature(feature="total_screen_min", value=380, shap_value=-4.0,
                        abs_shap=4.0, direction="decrease"),
            SHAPFeature(feature="sleep_hours", value=6.0, shap_value=-3.0,
                        abs_shap=3.0, direction="decrease"),
        ]

    def test_recommendations_carry_the_users_number_and_four_languages(self):
        recs = RecommendationService().generate(
            self._features(), user_data={"total_screen_min": 380, "sleep_hours": 6.0})
        self.assertTrue(recs)
        for rec in recs:
            self.assertIsNotNone(rec.observed_value, rec.source_field)
            self.assertIsNotNone(rec.target_value, rec.source_field)
            for lang in LANGUAGES:
                self.assertTrue(rec.text_i18n["action"][lang])

    def test_the_number_in_the_text_is_the_number_the_user_submitted(self):
        recs = RecommendationService().generate(
            self._features(), user_data={"total_screen_min": 380, "sleep_hours": 6.0})
        screen = next(r for r in recs if r.source_field == "total_screen_min")
        self.assertIn("380", screen.text_i18n["description"]["en"])

    def test_calling_without_user_data_still_works(self):
        """Older call sites pass no user_data; they must keep the exact
        behaviour they had."""
        recs = RecommendationService().generate(self._features())
        self.assertTrue(recs)
        for rec in recs:
            self.assertIsNone(rec.observed_value)
            self.assertTrue(rec.title)  # the registry's English is intact


if __name__ == "__main__":
    unittest.main()
