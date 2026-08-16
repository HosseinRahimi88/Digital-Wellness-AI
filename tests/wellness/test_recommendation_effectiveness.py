"""
Tests: RecommendationEffectivenessService (feature 13 - effectiveness,
feature 56 - the learning-loop track record it feeds), plus
RecommendationService.generate()'s optional category_track_record
parameter.

Run: python3 -m unittest tests.wellness.test_recommendation_effectiveness -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401

from services.wellness.commitment_service import Commitment, STATUS_ACTIVE
from services.wellness.recommendation_effectiveness_service import RecommendationEffectivenessService
from services.wellness.recommendation_service import RecommendationService
from services.ml.shap_service import SHAPFeature


def _entry(date_str: str, health_score: float, **fields) -> dict:
    entry = {"user_id": "alice", "date": date_str, "health_score": health_score}
    entry.update(fields)
    return entry


def _commitment(category: str, committed_on: str) -> Commitment:
    return Commitment(
        commitment_id=f"c-{committed_on}-{category}",
        user_id="alice",
        category=category,
        committed_on=committed_on,
        status=STATUS_ACTIVE,
    )


class TestEvaluateCommitment(unittest.TestCase):

    def test_insufficient_data_with_sparse_entries(self):
        commitment = _commitment("Sleep", "2026-01-10")
        entries = [_entry("2026-01-09", 50.0)]
        result = RecommendationEffectivenessService.evaluate_commitment(commitment, entries)
        self.assertEqual(result.verdict, "insufficient_data")

    def test_detects_real_improvement(self):
        commitment = _commitment("Sleep", "2026-01-10")
        entries = [
            _entry("2026-01-08", 50.0, sleep_hours=5.0),
            _entry("2026-01-09", 52.0, sleep_hours=5.2),
            _entry("2026-01-10", 51.0, sleep_hours=5.1),
            _entry("2026-01-11", 80.0, sleep_hours=8.0),
            _entry("2026-01-12", 82.0, sleep_hours=8.2),
        ]
        result = RecommendationEffectivenessService.evaluate_commitment(commitment, entries)
        self.assertEqual(result.verdict, "improved")
        self.assertGreater(result.score_delta, 0)
        self.assertEqual(result.field_name, "sleep_hours")
        self.assertGreater(result.field_after_avg, result.field_before_avg)

    def test_detects_real_decline(self):
        commitment = _commitment("Screen Time", "2026-01-10")
        entries = [
            _entry("2026-01-08", 80.0, total_screen_min=100.0),
            _entry("2026-01-09", 82.0, total_screen_min=110.0),
            _entry("2026-01-11", 50.0, total_screen_min=300.0),
            _entry("2026-01-12", 48.0, total_screen_min=310.0),
        ]
        result = RecommendationEffectivenessService.evaluate_commitment(commitment, entries)
        self.assertEqual(result.verdict, "declined")

    def test_small_delta_is_no_change(self):
        commitment = _commitment("Focus", "2026-01-10")
        entries = [
            _entry("2026-01-08", 80.0),
            _entry("2026-01-09", 81.0),
            _entry("2026-01-11", 81.0),
            _entry("2026-01-12", 80.0),
        ]
        result = RecommendationEffectivenessService.evaluate_commitment(commitment, entries)
        self.assertEqual(result.verdict, "no_change")


class TestCategoryTrackRecord(unittest.TestCase):

    def test_only_includes_categories_with_measurable_data(self):
        commitments = [
            _commitment("Sleep", "2026-01-10"),   # has enough data below
            _commitment("Activity", "2026-06-10"),  # no supporting entries at all
        ]
        entries = [
            _entry("2026-01-08", 50.0),
            _entry("2026-01-09", 52.0),
            _entry("2026-01-11", 80.0),
            _entry("2026-01-12", 82.0),
        ]
        track_record = RecommendationEffectivenessService.compute_category_track_record(commitments, entries)
        self.assertIn("Sleep", track_record)
        self.assertNotIn("Activity", track_record)

    def test_averages_across_multiple_commitments_same_category(self):
        commitments = [
            _commitment("Sleep", "2026-01-10"),
            _commitment("Sleep", "2026-02-10"),
        ]
        entries = [
            # First commitment window: +30 improvement
            _entry("2026-01-08", 50.0), _entry("2026-01-09", 50.0),
            _entry("2026-01-11", 80.0), _entry("2026-01-12", 80.0),
            # Second commitment window: +10 improvement
            _entry("2026-02-08", 60.0), _entry("2026-02-09", 60.0),
            _entry("2026-02-11", 70.0), _entry("2026-02-12", 70.0),
        ]
        track_record = RecommendationEffectivenessService.compute_category_track_record(commitments, entries)
        self.assertAlmostEqual(track_record["Sleep"], 20.0)  # avg(30, 10)


class TestLearningLoopIntegration(unittest.TestCase):
    """RecommendationService.generate()'s optional track-record nudge."""

    def _feature(self, name: str, score: float) -> SHAPFeature:
        return SHAPFeature(feature=name, value=0.0, shap_value=-1.0, abs_shap=1.0, direction="decrease", score=score)

    def test_generate_without_track_record_is_unchanged(self):
        service = RecommendationService()
        recs = service.generate([self._feature("sleep_hours", 90.0), self._feature("stress_0_10", 90.0)])
        self.assertEqual(len(recs), 2)

    def test_track_record_breaks_ties_within_same_priority_tier(self):
        service = RecommendationService()
        # Both features score 90 -> both HIGH priority -> same tier,
        # so track record should decide the order.
        features = [self._feature("sleep_hours", 90.0), self._feature("stress_0_10", 90.0)]
        recs_no_bias = service.generate(features)
        recs_biased = service.generate(
            features, category_track_record={"Mental Health": 20.0, "Sleep": 0.0}
        )
        self.assertEqual(recs_biased[0].category, "Mental Health")
        # Sanity: without bias, order follows SHAP/registry iteration, not asserted exactly.
        self.assertEqual(len(recs_no_bias), len(recs_biased))


if __name__ == "__main__":
    unittest.main()
