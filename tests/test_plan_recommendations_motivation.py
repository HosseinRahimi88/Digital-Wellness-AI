"""The three content areas: the weekly plan, the recommendations, and
the motivational text.

Each had the same shape of problem in a different place:

  * The 7-day plan translated its exercises and nothing around them, so
    a Persian reader got translated tasks under an English theme title,
    an English tip, and "Day 3".

  * RecommendationService drops a harmful SHAP factor that has no
    template (`if template is None: continue`). Only 13 of 53 fields had
    one, so the model would name the thing dragging a score down and the
    result page would say nothing about it. Measured before the fix on
    the at-risk demo profile: 2 of its 4 harmful factors produced no
    advice at all.

  * "Motivate me" was one templated sentence off the score, and "tell me
    a fact" picked a knowledge topic at random - so the same words came
    back on the fifth visit as on the first, and a falling score got the
    line written for a holding one.

Run: python3 -m unittest tests.test_plan_recommendations_motivation -v
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path bootstrap

import config.demo_profiles as dp
import config.recommendation_i18n as ri
import config.recommendation_registry as reg
from core.feature_schema import FEATURE_SCHEMA
from services.improvement_plan_service import (
    LANGUAGES,
    _THEME_I18N,
    _TIP_I18N,
    _TIER_LABEL_I18N,
    ImprovementPlanService,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
JS = REPO_ROOT / "frontend" / "assets" / "js"
RUNNER = Path(__file__).resolve().parent / "js" / "motivation_runner.js"

SCRIPTS = {
    "fa": re.compile(r"[؀-ۿ]"),
    "ar": re.compile(r"[؀-ۿ]"),
    "zh": re.compile(r"[一-鿿]"),
}


# ======================================================================
# 1. The weekly plan
# ======================================================================

class TestThePlanIsTranslatedAroundceExercisesToo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = ImprovementPlanService().generate(
            "At Risk", 38.9, "Night Owl", dp.at_risk_profile())

    def test_the_intro_exists_in_every_language(self):
        intro = self.plan.text_i18n["intro"]
        self.assertEqual(set(intro), set(LANGUAGES))
        for lang in LANGUAGES:
            with self.subTest(lang=lang):
                self.assertTrue(intro[lang].strip())

    def test_the_intro_carries_the_real_score_in_every_language(self):
        # A translated sentence that lost the number would be worse than
        # the English one that kept it.
        for lang in LANGUAGES:
            with self.subTest(lang=lang):
                self.assertIn("38.9", self.plan.text_i18n["intro"][lang])

    def test_every_day_carries_label_theme_tip_and_tier(self):
        self.assertEqual(len(self.plan.days), 7)
        for day in self.plan.days:
            for part in ("day_label", "theme", "tip", "tier_label"):
                with self.subTest(day=day.day_number, part=part):
                    self.assertIn(part, day.text_i18n)
                    self.assertEqual(set(day.text_i18n[part]), set(LANGUAGES))

    def test_day_numbers_reach_the_translated_label(self):
        for day in self.plan.days:
            for lang in LANGUAGES:
                with self.subTest(day=day.day_number, lang=lang):
                    self.assertIn(str(day.day_number), day.text_i18n["day_label"][lang])

    def test_a_single_level_theme_gets_no_tier_label_in_any_language(self):
        # Day 7 is the reflection day - it has one level, so a tier label
        # would name a tier that does not exist.
        day7 = self.plan.days[-1]
        for lang in LANGUAGES:
            with self.subTest(lang=lang):
                self.assertEqual(day7.text_i18n["tier_label"][lang], "")

    def test_focus_areas_are_translated_and_index_aligned(self):
        self.assertEqual(len(self.plan.focus_areas_i18n), len(self.plan.focus_areas))
        for name, table in zip(self.plan.focus_areas, self.plan.focus_areas_i18n):
            with self.subTest(area=name):
                self.assertEqual(table["en"], name)
                self.assertEqual(set(table), set(LANGUAGES))

    def test_the_flat_english_fields_still_work(self):
        # Older clients read these.
        self.assertEqual(self.plan.intro, self.plan.text_i18n["intro"]["en"])
        for day in self.plan.days:
            with self.subTest(day=day.day_number):
                self.assertEqual(day.theme, day.text_i18n["theme"]["en"])
                self.assertEqual(day.day_label, day.text_i18n["day_label"]["en"])

    def test_every_theme_and_tip_is_translated_not_left_in_english(self):
        for name, table in _THEME_I18N.items():
            for lang in ("fa", "ar", "zh"):
                with self.subTest(theme=name, lang=lang):
                    self.assertNotEqual(table[lang], table["en"])
                    self.assertRegex(table[lang], SCRIPTS[lang])
        for name, table in _TIP_I18N.items():
            for lang in ("fa", "ar", "zh"):
                with self.subTest(tip=name, lang=lang):
                    self.assertNotEqual(table[lang], table["en"])
                    self.assertRegex(table[lang], SCRIPTS[lang])

    def test_every_theme_in_the_rules_has_a_translation(self):
        # A theme added later without a translation would silently render
        # in English for everyone.
        svc = ImprovementPlanService
        names = {r["theme"] for r in svc._HABIT_RULES}
        names.add(svc._DEFAULT_THEME["theme"])
        names.add(svc._CLOSING_THEME["theme"])
        for name in names:
            with self.subTest(theme=name):
                self.assertIn(name, _THEME_I18N)
                self.assertIn(name, _TIP_I18N)

    def test_the_three_tier_labels_are_translated(self):
        self.assertEqual(len(_TIER_LABEL_I18N), 3)
        for i, table in enumerate(_TIER_LABEL_I18N):
            for lang in ("fa", "ar", "zh"):
                with self.subTest(tier=i, lang=lang):
                    self.assertNotEqual(table[lang], table["en"])

    def test_persian_and_arabic_plan_text_are_not_the_same(self):
        for name, table in _THEME_I18N.items():
            with self.subTest(theme=name):
                self.assertNotEqual(table["fa"], table["ar"])


class TestThePlanRendererReadsTheTranslations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (JS / "weekly.js").read_text(encoding="utf-8")

    def test_it_picks_the_readers_language_for_every_part(self):
        for part in ("'intro'", "'day_label'", "'theme'", "'tip'", "'tier_label'"):
            with self.subTest(part=part):
                self.assertIn(part, self.js)
        self.assertIn("serverText(", self.js)

    def test_the_task_text_is_no_longer_forced_to_english(self):
        # The exercises always carried four languages; the renderer was
        # printing the English one regardless.
        idx = self.js.index("const taskText")
        body = self.js[idx:idx + 220]
        self.assertIn("task.text_i18n", body)

    def test_the_focus_chips_use_the_index_aligned_translations(self):
        self.assertIn("focus_areas_i18n", self.js)

    def test_the_schema_and_router_carry_the_new_fields(self):
        schema = (REPO_ROOT / "api" / "schemas" / "plan.py").read_text(encoding="utf-8")
        router = (REPO_ROOT / "api" / "routers" / "plan.py").read_text(encoding="utf-8")
        self.assertIn("text_i18n", schema)
        self.assertIn("focus_areas_i18n", schema)
        self.assertIn("text_i18n=day.text_i18n", router)
        self.assertIn("focus_areas_i18n=plan.focus_areas_i18n", router)


# ======================================================================
# 2. The recommendations
# ======================================================================

class TestAdviceExistsForWhatTheModelActuallyFlags(unittest.TestCase):

    def test_every_template_has_four_language_text(self):
        for field in reg.FEATURE_RECOMMENDATIONS:
            with self.subTest(field=field):
                self.assertIn(field, ri.RULE_TEXT, "template with no translated text")
                entry = ri.RULE_TEXT[field]
                for part in ("title", "description", "action", "success_metric"):
                    self.assertIn(part, entry)
                    self.assertEqual(set(entry[part]), set(ri.LANGUAGES))

    def test_every_translated_rule_has_a_template(self):
        # The reverse gap: text with no template is never reachable.
        for field in ri.RULE_TEXT:
            with self.subTest(field=field):
                self.assertIn(field, reg.FEATURE_RECOMMENDATIONS)

    def test_every_rule_has_a_target_formula_and_a_unit(self):
        for field in reg.FEATURE_RECOMMENDATIONS:
            with self.subTest(field=field):
                self.assertIn(field, ri.TARGETS, "no deterministic target formula")
                self.assertIn(field, ri.UNITS)

    def test_no_translation_was_left_as_the_english_placeholder(self):
        for field, entry in ri.RULE_TEXT.items():
            for part, table in entry.items():
                for lang in ("fa", "ar", "zh"):
                    with self.subTest(field=field, part=part, lang=lang):
                        self.assertNotEqual(table[lang], table["en"])
                        self.assertRegex(table[lang], SCRIPTS[lang])

    def test_persian_and_arabic_rules_are_not_the_same_text(self):
        for field, entry in ri.RULE_TEXT.items():
            for part, table in entry.items():
                with self.subTest(field=field, part=part):
                    self.assertNotEqual(table["fa"], table["ar"])

    def test_placeholders_survive_translation(self):
        # A translation that dropped {observed} or {target} would render
        # advice with the user's own number missing from it.
        for field, entry in ri.RULE_TEXT.items():
            for part, table in entry.items():
                english = table["en"]
                for token in ("{observed}", "{target}"):
                    if token not in english:
                        continue
                    for lang in ("fa", "ar", "zh"):
                        with self.subTest(field=field, part=part, lang=lang, token=token):
                            self.assertIn(token, table[lang])

    def test_the_targets_are_deterministic(self):
        # The brief forbids randomness here: same input, same target.
        for field, formula in ri.TARGETS.items():
            with self.subTest(field=field):
                self.assertEqual(formula(50.0), formula(50.0))

    def test_a_target_never_asks_for_less_than_the_user_already_does(self):
        # For the "raise" rules, a target below today's value reads as
        # mockery rather than a goal.
        for field in ("sleep_hours", "physical_activity_min_per_day",
                      "productivity_0_100", "focus_0_100", "sleep_quality_1_10"):
            with self.subTest(field=field):
                for observed in (10.0, 40.0, 90.0):
                    self.assertGreaterEqual(ri.TARGETS[field](observed), observed)

    def test_the_at_risk_profile_now_gets_advice_for_every_harmful_factor(self):
        # This is the measured regression: it used to be 2 of 4.
        from services.prediction_service import PredictionService
        from services.validation_service import ValidationService

        validation = ValidationService().validate(dp.at_risk_profile())
        result = PredictionService().predict(validation.cleaned_data)
        harmful = [f for f in result.shap_features if f.direction == "decrease"]
        self.assertTrue(harmful, "fixture produced no harmful factors to advise on")

        uncovered = [f.feature for f in harmful
                     if f.feature not in reg.FEATURE_RECOMMENDATIONS]
        self.assertEqual(
            uncovered, [],
            f"the model flagged these as harmful but nothing advises on them: {uncovered}",
        )

    def test_recommendations_come_back_with_the_users_own_numbers(self):
        from services.prediction_service import PredictionService
        from services.recommendation_service import RecommendationService
        from services.validation_service import ValidationService

        validation = ValidationService().validate(dp.at_risk_profile())
        result = PredictionService().predict(validation.cleaned_data)
        recs = RecommendationService().generate(
            result.shap_features, user_data=validation.cleaned_data)
        self.assertTrue(recs)
        for rec in recs:
            with self.subTest(field=rec.source_field):
                self.assertTrue(rec.text_i18n, "no translated text on a rendered rec")
                for lang in ri.LANGUAGES:
                    title = rec.text_i18n["title"][lang]
                    self.assertTrue(title.strip())
                # No unfilled placeholder may reach a card.
                for part, table in rec.text_i18n.items():
                    for lang, text in table.items():
                        self.assertNotIn("{observed}", text)
                        self.assertNotIn("{target}", text)


class TestSomeFieldsMustNeverGetAdvice(unittest.TestCase):
    """Refusals written down, so they do not look like oversights."""

    def test_no_template_exists_for_a_non_actionable_field(self):
        # "Your score suffers because of your region" is not advice.
        overlap = set(reg.FEATURE_RECOMMENDATIONS) & reg.NON_ACTIONABLE_FIELDS
        self.assertEqual(overlap, set(), f"advice on unchangeable fields: {overlap}")

    def test_no_template_exists_for_a_clinical_instrument(self):
        # This app's own rule is no medical framing and no diagnosis.
        # Coaching someone's anxiety or low-mood score in a seven-day
        # plan is exactly that framing.
        overlap = set(reg.FEATURE_RECOMMENDATIONS) & reg.CLINICAL_FIELDS
        self.assertEqual(overlap, set(), f"advice on clinical scales: {overlap}")

    def test_the_blocked_fields_are_real_schema_fields(self):
        # A typo in the block list would silently protect nothing.
        for field in reg.NEVER_RECOMMEND:
            with self.subTest(field=field):
                self.assertIn(field, FEATURE_SCHEMA)

    def test_the_two_reasons_are_kept_separate(self):
        self.assertTrue(reg.NON_ACTIONABLE_FIELDS)
        self.assertTrue(reg.CLINICAL_FIELDS)
        self.assertEqual(reg.NON_ACTIONABLE_FIELDS & reg.CLINICAL_FIELDS, set())
        self.assertEqual(
            reg.NEVER_RECOMMEND, reg.NON_ACTIONABLE_FIELDS | reg.CLINICAL_FIELDS)


class TestTheDashboardShowsTranslatedRecommendations(unittest.TestCase):
    def test_the_dashboard_card_reads_text_i18n(self):
        js = (JS / "dashboard.js").read_text(encoding="utf-8")
        idx = js.index("rec-title")
        body = js[max(0, idx - 700):idx + 400]
        self.assertIn("text_i18n", body,
                      "the dashboard still prints the English title/description")


# ======================================================================
# 3. The motivational content
# ======================================================================

class TestMotivationalContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        r = subprocess.run([node, str(RUNNER)], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("motivation_runner.js failed: " + r.stderr)
        cls.out = json.loads(r.stdout)

    def test_the_library_is_actually_a_library(self):
        # The thing asked for was more content, not another single line.
        self.assertGreaterEqual(self.out["factGroups"], 5)
        self.assertGreaterEqual(self.out["factCount"], 10)
        self.assertGreaterEqual(self.out["encouragementBands"], 6)
        self.assertGreaterEqual(self.out["encouragementCount"], 8)

    def test_every_line_exists_in_all_four_languages(self):
        self.assertEqual(self.out["missingLanguages"], [])

    def test_the_band_follows_what_actually_happened(self):
        b = self.out["bands"]
        self.assertEqual(b["firstEver"], "first_time")
        self.assertEqual(b["lowFalling"], "low_any")
        self.assertEqual(b["lowRising"], "low_any")
        self.assertEqual(b["strongHolding"], "strong_holding")
        self.assertEqual(b["strongRising"], "strong_rising")
        self.assertEqual(b["middleFalling"], "middle_falling")
        self.assertEqual(b["middleRising"], "middle_rising")

    def test_a_falling_score_never_gets_the_holding_line(self):
        # The point of choosing by situation rather than at random.
        self.assertTrue(self.out["differentLines"])

    def test_the_users_real_score_reaches_the_sentence(self):
        self.assertTrue(self.out["scoreRendered"])
        self.assertTrue(self.out["noPlaceholderLeft"])

    def test_no_score_leaves_no_hole_in_the_sentence(self):
        self.assertTrue(self.out["noScoreHasNoPlaceholder"])
        self.assertTrue(self.out["noScoreLine"].strip())

    def test_a_fact_is_always_available_even_for_an_unknown_topic(self):
        self.assertTrue(self.out["allFactsNonEmpty"])

    def test_facts_are_matched_to_the_users_own_weakest_signal(self):
        m = self.out["topicMapping"]
        self.assertEqual(m["sleep_hours"], "sleep")
        self.assertEqual(m["pickup_density"], "focus")
        self.assertEqual(m["social_comparison_1_10"], "social")
        self.assertIsNone(m["unknown_field"])

    def test_the_text_does_not_shuffle_within_a_day(self):
        # Re-opening a page must not change the words under the reader.
        self.assertTrue(self.out["stableWithinDay"])

    def test_every_language_produces_a_real_sentence(self):
        for lang, sizes in self.out["perLanguage"].items():
            with self.subTest(lang=lang):
                self.assertGreater(sizes["enc"], 20)
                self.assertGreater(sizes["fact"], 20)

    def test_no_fabricated_statistic_appears_in_any_fact(self):
        # The rule this file keeps: state the mechanism, never invent a
        # percentage or a study nobody can check.
        src = (JS / "motivation.js").read_text(encoding="utf-8")
        start = src.index("const FACTS")
        end = src.index("const ENCOURAGEMENT")
        body = src[start:end]
        self.assertNotRegex(body, r"\d+\s?%")
        for word in ("study", "studies", "research shows", "scientists"):
            with self.subTest(word=word):
                self.assertNotIn(word, body.lower())

    def test_the_coach_uses_it(self):
        menu = (JS / "ai-menu.js").read_text(encoding="utf-8")
        self.assertIn("DWMotivation.encouragement", menu)
        self.assertIn("DWMotivation.fact", menu)
        self.assertIn("topicForField", menu)

    def test_it_is_loaded_on_the_pages_that_use_it(self):
        for name in ("coach.html", "app.html", "dashboard.html"):
            with self.subTest(page=name):
                html = (REPO_ROOT / "frontend" / name).read_text(encoding="utf-8")
                self.assertIn("assets/js/motivation.js", html)


if __name__ == "__main__":
    unittest.main()
