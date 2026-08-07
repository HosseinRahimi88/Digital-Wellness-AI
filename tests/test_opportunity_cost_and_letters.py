from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.opportunity_cost_service import OpportunityCostService
from services.letter_service import LetterService
from services.storage.json_file_storage import JSONFileStorageBackend


class TestOpportunityCostService(unittest.TestCase):
    def test_empty_entries_has_no_data(self):
        result = OpportunityCostService.compute([])
        self.assertFalse(result.has_data)

    def test_missing_field_skipped_not_treated_as_zero(self):
        entries = [{"date": "2026-01-01"}, {"date": "2026-01-02", "total_screen_min": 120}]
        result = OpportunityCostService.compute(entries)
        self.assertTrue(result.has_data)
        self.assertEqual(result.days_measured, 1)
        self.assertEqual(result.avg_daily_minutes, 120.0)

    def test_projection_scales_from_daily_average(self):
        entries = [{"total_screen_min": 60}] * 3
        result = OpportunityCostService.compute(entries)
        self.assertEqual(result.avg_daily_minutes, 60.0)
        self.assertAlmostEqual(result.projected_days_lost_per_year, (60 * 365) / (24 * 60), places=1)


class TestLetterService(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="letters_test_"))
        self.backend = JSONFileStorageBackend(self._tmp_dir / "letters.json")
        self.service = LetterService(user_id="user1", backend=self.backend)

    def test_new_user_has_no_letters(self):
        self.assertEqual(self.service.get_letters(), [])

    def test_write_and_read_back_letter(self):
        future = date.today() + timedelta(days=30)
        letter = self.service.write_letter("Keep going!", unlock_date=future, context_score=75.0)
        self.assertEqual(letter.content, "Keep going!")
        letters = self.service.get_letters()
        self.assertEqual(len(letters), 1)
        self.assertFalse(letters[0].is_unlocked)

    def test_past_unlock_date_is_immediately_unlocked(self):
        past = date.today() - timedelta(days=1)
        self.service.write_letter("Hi future me", unlock_date=past)
        unlocked = self.service.get_unlocked_letters()
        self.assertEqual(len(unlocked), 1)

    def test_empty_content_rejected(self):
        with self.assertRaises(ValueError):
            self.service.write_letter("   ", unlock_date=date.today())

    def test_letters_isolated_per_user(self):
        other = LetterService(user_id="user2", backend=self.backend)
        self.service.write_letter("For me", unlock_date=date.today())
        self.assertEqual(other.get_letters(), [])


if __name__ == "__main__":
    unittest.main()
