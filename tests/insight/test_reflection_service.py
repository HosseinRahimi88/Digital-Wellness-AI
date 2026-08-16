"""
Tests: Group C Feature 42 - Reflection Loop.

Run: python3 -m unittest tests.insight.test_reflection_service -v
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from services.insight.reflection_service import ReflectionService, CalibrationResult
from services.storage.json_file_storage import JSONFileStorageBackend


def _make_service(user_id: str = "u1") -> ReflectionService:
    tmp_dir = Path(tempfile.mkdtemp())
    storage = JSONFileStorageBackend(tmp_dir / "reflections.json")
    return ReflectionService(user_id=user_id, storage=storage)


class TestReflectionRecording(unittest.TestCase):

    def test_record_and_get_all(self):
        svc = _make_service()
        svc.record_reflection(4, "Felt good today", on_date=date(2026, 1, 1))
        svc.record_reflection(2, "Rough day", on_date=date(2026, 1, 2))

        entries = svc.get_all()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["self_rating"], 4)
        self.assertEqual(entries[1]["reflection_text"], "Rough day")

    def test_upsert_same_date_overwrites(self):
        svc = _make_service()
        svc.record_reflection(3, "first", on_date=date(2026, 1, 1))
        svc.record_reflection(5, "updated", on_date=date(2026, 1, 1))

        entries = svc.get_all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["self_rating"], 5)
        self.assertEqual(entries[0]["reflection_text"], "updated")

    def test_rejects_out_of_range_rating(self):
        svc = _make_service()
        with self.assertRaises(ValueError):
            svc.record_reflection(0, "bad")
        with self.assertRaises(ValueError):
            svc.record_reflection(6, "bad")

    def test_users_are_isolated(self):
        tmp_dir = Path(tempfile.mkdtemp())
        storage = JSONFileStorageBackend(tmp_dir / "reflections.json")
        svc_a = ReflectionService(user_id="alice", storage=storage)
        svc_b = ReflectionService(user_id="bob", storage=storage)

        svc_a.record_reflection(5, "alice's day", on_date=date(2026, 1, 1))
        svc_b.record_reflection(1, "bob's day", on_date=date(2026, 1, 1))

        self.assertEqual(len(svc_a.get_all()), 1)
        self.assertEqual(len(svc_b.get_all()), 1)
        self.assertEqual(svc_a.get_all()[0]["self_rating"], 5)
        self.assertEqual(svc_b.get_all()[0]["self_rating"], 1)


class TestCalibration(unittest.TestCase):

    def _history(self, base, scores, top_feature="stress_0_10"):
        return [
            {"date": (base + timedelta(days=i)).isoformat(), "health_score": s, "top_shap_feature": top_feature}
            for i, s in enumerate(scores)
        ]

    def test_insufficient_data_when_few_entries(self):
        svc = _make_service()
        svc.record_reflection(3, on_date=date(2026, 1, 1))
        result = svc.compute_calibration(self._history(date(2026, 1, 1), [50]))
        self.assertIsInstance(result, CalibrationResult)
        self.assertFalse(result.available)

    def test_perfectly_aligned_ratings_and_scores_are_well_calibrated(self):
        svc = _make_service()
        base = date(2026, 1, 1)
        ratings = [1, 2, 3, 4, 5, 4, 3]
        scores = [10, 20, 30, 40, 50, 40, 30]  # moves in lockstep with ratings
        for i, r in enumerate(ratings):
            svc.record_reflection(r, on_date=base + timedelta(days=i))

        result = svc.compute_calibration(self._history(base, scores))
        self.assertTrue(result.available)
        self.assertGreater(result.correlation, 0.9)
        self.assertEqual(result.label, "Well-calibrated")

    def test_inversely_related_ratings_and_scores_are_flagged(self):
        svc = _make_service()
        base = date(2026, 1, 1)
        ratings = [5, 4, 3, 2, 1, 2, 3]
        scores = [10, 20, 30, 40, 50, 40, 30]  # moves opposite ratings
        for i, r in enumerate(ratings):
            svc.record_reflection(r, on_date=base + timedelta(days=i))

        result = svc.compute_calibration(self._history(base, scores))
        self.assertTrue(result.available)
        self.assertLess(result.correlation, -0.5)
        self.assertEqual(result.label, "Inversely calibrated")

    def test_no_history_dates_overlap_reflections(self):
        svc = _make_service()
        base = date(2026, 1, 1)
        for i in range(6):
            svc.record_reflection(3, on_date=base + timedelta(days=i))
        # History entries dated a month later - zero date overlap.
        disjoint_history = self._history(base + timedelta(days=60), [10, 20, 30, 40, 50, 60])
        result = svc.compute_calibration(disjoint_history)
        self.assertFalse(result.available)

    def test_never_raises_on_degenerate_input(self):
        svc = _make_service()
        base = date(2026, 1, 1)
        for i in range(6):
            svc.record_reflection(3, on_date=base + timedelta(days=i))  # constant rating, zero variance
        result = svc.compute_calibration(self._history(base, [50, 50, 50, 50, 50, 50]))
        self.assertIsInstance(result, CalibrationResult)  # must not raise, even with zero-variance input
        self.assertFalse(result.available)


class TestNextPrompt(unittest.TestCase):

    def test_generic_prompt_with_no_history(self):
        svc = _make_service()
        prompt = svc.next_prompt([])
        self.assertTrue(prompt)
        self.assertIsInstance(prompt, str)

    def test_prompt_references_score_increase(self):
        svc = _make_service()
        history = [
            {"date": "2026-01-01", "health_score": 50.0, "top_shap_feature": "sleep_hours"},
            {"date": "2026-01-02", "health_score": 60.0, "top_shap_feature": "sleep_hours"},
        ]
        prompt = svc.next_prompt(history)
        self.assertIn("rose", prompt.lower())

    def test_prompt_references_score_decrease(self):
        svc = _make_service()
        history = [
            {"date": "2026-01-01", "health_score": 60.0, "top_shap_feature": "stress_0_10"},
            {"date": "2026-01-02", "health_score": 45.0, "top_shap_feature": "stress_0_10"},
        ]
        prompt = svc.next_prompt(history)
        self.assertIn("dropped", prompt.lower())

    def test_prompt_never_raises_on_missing_fields(self):
        svc = _make_service()
        history = [{"date": "2026-01-01"}, {"date": "2026-01-02"}]
        prompt = svc.next_prompt(history)
        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt)


if __name__ == "__main__":
    unittest.main()
