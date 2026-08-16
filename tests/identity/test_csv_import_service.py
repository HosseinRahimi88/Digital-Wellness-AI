"""
Tests: services.identity.csv_import_service - bulk multi-day check-in import.

Run: python3 -m unittest tests.identity.test_csv_import_service -v
"""

from __future__ import annotations

import csv
import io
import shutil
import tempfile
import unittest
from pathlib import Path

import tests._test_support  # noqa: F401

from services.identity.csv_import_service import RAW_CSV_COLUMNS, CSVImportService, build_template_csv
from services.identity.history_service import HistoryService
from services.ml.prediction_service import PredictionService
from services.storage.json_file_storage import JSONFileStorageBackend
from services.ml.validation_service import ValidationService

_GOOD_ROW = {
    "date": "2026-08-01", "age": 24, "gender": "Female", "occupation_group": "Student",
    "region_group": "Asia", "education_group": "Bachelor", "device_category": "Smartphone",
    "primary_platform": "Instagram", "purpose_group": "Social Connection",
    "is_content_creator": "False", "uses_screen_time_limits": "True",
    "social_min": 90, "gaming_min": 20, "work_study_min": 180, "other_min": 30,
    "video_min": 60, "night_screen_min": 15, "pre_sleep_screen_min": 10,
    "notifications_per_day": 60, "pickups_per_day": 45, "app_opens_per_day": 80,
    "sleep_hours": 7.5, "sleep_quality_1_10": 7, "stress_0_10": 3, "mental_fatigue_0_10": 3,
    "anxiety_0_27": 5, "low_mood_0_27": 4, "happiness_0_10": 7, "loneliness_1_10": 3,
    "self_esteem_1_10": 7, "fomo_1_10": 3, "social_comparison_1_10": 3,
    "life_satisfaction_1_10": 7, "focus_0_100": 70, "productivity_0_100": 68,
    "physical_activity_min_per_day": 30, "caffeine_cups_per_day": 1,
}


def _csv_from_rows(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=RAW_CSV_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col, "") for col in RAW_CSV_COLUMNS})
    return buf.getvalue()


class TestCSVImportService(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_csv_test_"))
        self.storage_path = self._tmp_dir / "prediction_history.json"

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _importer(self, user_id: str) -> tuple[CSVImportService, HistoryService]:
        history = HistoryService(user_id=user_id, storage=JSONFileStorageBackend(self.storage_path))
        importer = CSVImportService(history, ValidationService(), PredictionService())
        return importer, history

    def test_template_has_no_derived_or_calendar_columns(self):
        # A user should never be asked to compute a ratio/density by hand,
        # or contradict their own date with a separate day_of_week field.
        for leaked in ("total_screen_min", "social_ratio", "fragmentation_index_0_100",
                       "day_index", "day_of_week", "is_weekend"):
            self.assertNotIn(leaked, RAW_CSV_COLUMNS)
        self.assertIn("date", RAW_CSV_COLUMNS)

    def test_template_csv_round_trips_successfully(self):
        importer, history = self._importer("alice")
        result = importer.import_csv_text(build_template_csv())
        self.assertEqual(result.failed_rows, [])
        self.assertEqual(result.imported_count, 2)
        self.assertEqual(len(history.get_all()), 2)

    def test_missing_required_field_is_reported_not_defaulted(self):
        row = dict(_GOOD_ROW)
        del row["sleep_hours"]
        importer, history = self._importer("bob")
        result = importer.import_csv_text(_csv_from_rows([row]))

        self.assertEqual(result.imported_count, 0)
        self.assertEqual(len(result.failed_rows), 1)
        self.assertIn("sleep_hours", result.failed_rows[0].errors)
        self.assertEqual(history.get_all(), [])

    def test_invalid_date_is_reported_and_skipped(self):
        row = dict(_GOOD_ROW)
        row["date"] = "13/45/2026"
        importer, _ = self._importer("carol")
        result = importer.import_csv_text(_csv_from_rows([row]))

        self.assertEqual(result.imported_count, 0)
        self.assertIn("date", result.failed_rows[0].errors)

    def test_one_bad_row_does_not_block_the_rest_of_the_file(self):
        good = dict(_GOOD_ROW)
        bad = dict(_GOOD_ROW)
        bad["date"] = "2026-08-02"
        del bad["stress_0_10"]
        importer, history = self._importer("dana")
        result = importer.import_csv_text(_csv_from_rows([good, bad]))

        self.assertEqual(result.imported_count, 1)
        self.assertEqual(len(result.failed_rows), 1)
        self.assertEqual(len(history.get_all()), 1)

    def test_boolean_columns_from_csv_strings_are_coerced_correctly(self):
        row = dict(_GOOD_ROW)
        row["is_content_creator"] = "true"
        row["uses_screen_time_limits"] = "no"
        importer, history = self._importer("erin")
        result = importer.import_csv_text(_csv_from_rows([row]))

        self.assertEqual(result.failed_rows, [])
        entry = history.get_all()[0]
        self.assertEqual(result.imported_count, 1)
        self.assertIsNotNone(entry)

    def test_day_of_week_and_weekend_are_derived_from_date_not_asked_for(self):
        # 2026-08-01 is a Saturday.
        importer, history = self._importer("frank")
        result = importer.import_csv_text(_csv_from_rows([_GOOD_ROW]))
        self.assertEqual(result.imported_count, 1)
        # HistoryService's own day_of_week (stamped independently at
        # record() time from on_date) should agree with the calendar.
        self.assertEqual(history.get_all()[0]["day_of_week"], "Saturday")

    def test_multiple_valid_days_all_get_recorded(self):
        rows = []
        for i, d in enumerate(["2026-08-01", "2026-08-02", "2026-08-03"]):
            row = dict(_GOOD_ROW)
            row["date"] = d
            rows.append(row)
        importer, history = self._importer("grace")
        result = importer.import_csv_text(_csv_from_rows(rows))

        self.assertEqual(result.imported_count, 3)
        self.assertEqual(result.failed_rows, [])
        self.assertEqual({e["date"] for e in history.get_all()}, set(row["date"] for row in rows))


class TestDryRunImport(unittest.TestCase):
    """"Just show me what this file says" has to actually store nothing.

    The bug this closes: every upload was a save attempt. A file
    covering a day already logged came back refused, and the only way
    forward the app offered was to switch on the edit tick - the tick
    whose whole job is to overwrite that day. Someone who only wanted to
    read the scores had to risk their real history to see them.
    """

    def setUp(self):
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_csv_dry_"))
        self.storage_path = self._tmp_dir / "prediction_history.json"

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _importer(self, user_id: str) -> tuple[CSVImportService, HistoryService]:
        history = HistoryService(user_id=user_id, storage=JSONFileStorageBackend(self.storage_path))
        return CSVImportService(history, ValidationService(), PredictionService()), history

    def test_a_dry_run_scores_the_file_and_stores_nothing(self):
        importer, history = self._importer("dana")
        result = importer.import_csv_text(_csv_from_rows([_GOOD_ROW]), dry_run=True)

        self.assertTrue(result.dry_run)
        self.assertEqual(result.imported_count, 0, "a dry run must not report an import")
        self.assertEqual(result.imported_dates, [])
        self.assertEqual(history.get_all(), [], "a dry run wrote to storage")

        self.assertEqual(len(result.previews), 1)
        preview = result.previews[0]
        self.assertEqual(preview.date, _GOOD_ROW["date"])
        self.assertIsInstance(preview.health_score, float)
        self.assertTrue(preview.health_class)

    def test_a_dry_run_is_not_refused_for_a_day_already_recorded(self):
        """The whole point: nothing is being written, so nothing clashes."""
        importer, history = self._importer("dana")
        self.assertEqual(importer.import_csv_text(_csv_from_rows([_GOOD_ROW])).imported_count, 1)
        before = history.get_all()[0]

        result = importer.import_csv_text(_csv_from_rows([_GOOD_ROW]), dry_run=True)
        self.assertEqual(result.failed_rows, [], "a dry run was refused for a duplicate day")
        self.assertEqual(len(result.previews), 1)

        after = history.get_all()
        self.assertEqual(len(after), 1)
        self.assertEqual(after[0], before, "the already-recorded day was touched by a dry run")

    def test_a_dry_run_still_reports_rows_that_do_not_validate(self):
        """Skipping the duplicate check must not skip validation too."""
        broken = dict(_GOOD_ROW)
        broken["sleep_hours"] = 99  # outside the schema's range
        importer, history = self._importer("dana")
        result = importer.import_csv_text(_csv_from_rows([broken]), dry_run=True)

        self.assertEqual(result.previews, [])
        self.assertEqual(len(result.failed_rows), 1)
        self.assertIn("sleep_hours", result.failed_rows[0].errors)
        self.assertEqual(history.get_all(), [])

    def test_a_real_import_also_reports_what_each_row_scored(self):
        rows = []
        for d in ("2026-08-01", "2026-08-02"):
            row = dict(_GOOD_ROW)
            row["date"] = d
            rows.append(row)
        importer, history = self._importer("dana")
        result = importer.import_csv_text(_csv_from_rows(rows))

        self.assertFalse(result.dry_run)
        self.assertEqual(result.imported_count, 2)
        self.assertEqual([p.date for p in result.previews], ["2026-08-01", "2026-08-02"])
        # The preview is the same number that got stored, not a second
        # scoring of the same row.
        stored = {e["date"]: e["health_score"] for e in history.get_all()}
        for preview in result.previews:
            self.assertAlmostEqual(stored[preview.date], preview.health_score, places=6)


if __name__ == "__main__":
    unittest.main()
