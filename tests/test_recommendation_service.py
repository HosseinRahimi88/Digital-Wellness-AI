"""
Tests: RecommendationService (pure rule-based mapping from SHAP
features -> recommendation templates, no model/training involved).

Run: python3 -m unittest tests.test_recommendation_service -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401  (sys.path bootstrap)

from services.recommendation_service import RecommendationService
from services.shap_service import SHAPFeature


def _feature(name: str, score: float) -> SHAPFeature:
    return SHAPFeature(
        feature=name, value=0.0, shap_value=-1.0, abs_shap=1.0,
        direction="decrease", score=score,
    )


class TestRecommendationService(unittest.TestCase):

    def setUp(self):
        self.service = RecommendationService()

    def test_empty_shap_list_yields_no_recommendations(self):
        self.assertEqual(self.service.generate([]), [])

    def test_unknown_feature_names_are_skipped_not_crashed(self):
        """SHAP can surface engineered/derived feature names that have no
        registry entry (e.g. demographic fields) - these must be skipped
        silently, never raise."""
        recs = self.service.generate([_feature("some_unmapped_feature_xyz", 90.0)])
        self.assertEqual(recs, [])

    def test_known_feature_produces_a_recommendation(self):
        recs = self.service.generate([_feature("sleep_hours", 90.0)])
        self.assertEqual(len(recs), 1)
        self.assertTrue(recs[0].title)

    def test_duplicate_categories_are_deduplicated(self):
        """Two SHAP features mapping to templates in the same category
        should only produce one recommendation for that category."""
        recs = self.service.generate([
            _feature("sleep_hours", 95.0),
            _feature("sleep_quality_1_10", 90.0),
        ])
        categories = [r.category for r in recs]
        self.assertEqual(len(categories), len(set(categories)))

    def test_top_k_limits_recommendation_count(self):
        recs = self.service.generate(
            [
                _feature("sleep_hours", 95.0),
                _feature("stress_0_10", 90.0),
                _feature("social_min", 85.0),
                _feature("physical_activity_min_per_day", 80.0),
            ],
            top_k=2,
        )
        self.assertLessEqual(len(recs), 2)

    def test_recommendations_sorted_high_priority_first(self):
        recs = self.service.generate([
            _feature("physical_activity_min_per_day", 10.0),  # -> LOW
            _feature("sleep_hours", 95.0),  # -> HIGH
        ])
        priorities = [r.priority for r in recs]
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        self.assertEqual(priorities, sorted(priorities, key=lambda p: order.get(p, 99)))

    def test_every_recommendation_carries_a_success_metric(self):
        # Guards against the guardrail-content phase silently regressing:
        # every template in the registry must define a real success
        # metric, not just inherit the empty default.
        recs = self.service.generate([
            _feature("sleep_hours", 95.0),
            _feature("stress_0_10", 90.0),
            _feature("social_min", 85.0),
            _feature("physical_activity_min_per_day", 80.0),
        ])
        for rec in recs:
            self.assertTrue(rec.success_metric, f"{rec.title} has no success_metric")

    def test_every_recommendation_carries_a_safety_note(self):
        recs = self.service.generate([
            _feature("sleep_hours", 95.0),
            _feature("stress_0_10", 90.0),
        ])
        for rec in recs:
            self.assertTrue(rec.safety_note, f"{rec.title} has no safety_note")

    def test_mental_health_recommendation_has_a_specific_crisis_safety_note(self):
        recs = self.service.generate([_feature("stress_0_10", 95.0)])
        stress_rec = next(r for r in recs if r.category == "Mental Health")
        self.assertIn("professional", stress_rec.safety_note.lower())

    def test_every_registered_template_has_success_metric_and_safety_note(self):
        # Direct registry check (not just the ones a particular SHAP
        # list happens to trigger) - every one of the 13 templates must
        # have real guardrail content, not the empty default.
        from config.recommendation_registry import FEATURE_RECOMMENDATIONS
        for feature_name, template in FEATURE_RECOMMENDATIONS.items():
            self.assertTrue(template.success_metric, f"{feature_name} has no success_metric")
            self.assertTrue(template.safety_note, f"{feature_name} has no safety_note")


if __name__ == "__main__":
    unittest.main()
