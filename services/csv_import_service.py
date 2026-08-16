"""
CSV Import Service
---------------------
Bulk daily-entry import: lets a user fill in several days of raw habit
data in one spreadsheet instead of the check-in wizard, one day at a
time. Same guarantee as every other input path in this app: a value
the user didn't provide is never invented or defaulted - a row that
fails FEATURE_SCHEMA validation is reported with its exact error and
skipped, the rest of the file still imports.

Column contract: the CSV supplies the same RAW fields the live
check-in form collects (see RAW_CSV_COLUMNS) plus one extra column,
`date` (YYYY-MM-DD). Everything derive_features() computes (ratios,
densities, fragmentation, etc.) - and day_index/day_of_week/is_weekend,
derived here from each row's own `date` - is calculated exactly like
the live form and the What-if Simulator already do, never a second,
hand-duplicated formula.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date as date_cls
from typing import Any

from core.feature_schema import FEATURE_SCHEMA
from services.history_service import HistoryService
from services.prediction_service import PredictionService
from services.validation_service import ValidationService
from utils.feature_derivation import derive_features

# Fields derive_features() computes from the raw ones below - never
# asked for directly in the CSV, so a user can't accidentally submit a
# ratio/density that contradicts its own raw inputs.
_DERIVED_FIELDS = {
    "total_screen_min", "social_ratio", "gaming_ratio", "work_study_ratio",
    "other_ratio", "night_ratio", "pre_sleep_ratio", "notification_density",
    "pickup_density", "app_open_density", "screen_ewma_baseline",
    "screen_vs_baseline_pct", "fragmentation_index_0_100", "digital_dependence_0_100",
}
# Calendar fields auto-derived from the row's own `date` column instead
# of being asked for directly - avoids a row claiming a day_of_week that
# contradicts its own date.
_CALENDAR_FIELDS = {"day_index", "day_of_week", "is_weekend"}

# Boolean-choice fields: csv.DictReader always yields plain strings, and
# FEATURE_SCHEMA's categorical validator does an exact `value in choices`
# check - "True"/"False" strings would never match the real booleans
# [False, True], so every row would otherwise fail validation on these
# two fields alone. Coerced explicitly, once, here.
_BOOLEAN_FIELDS = {
    name for name, feat in FEATURE_SCHEMA.items()
    if feat.choices == [False, True]
}

RAW_CSV_COLUMNS = ["date"] + [
    name for name in FEATURE_SCHEMA
    if name not in _DERIVED_FIELDS and name not in _CALENDAR_FIELDS
]

_TRUE_STRINGS = {"true", "1", "yes", "y"}


def _coerce_boolean_strings(row_data: dict[str, Any]) -> None:
    for field_name in _BOOLEAN_FIELDS:
        if field_name in row_data and isinstance(row_data[field_name], str):
            row_data[field_name] = row_data[field_name].strip().lower() in _TRUE_STRINGS


_EXAMPLE_ROWS = [
    {
        "date": "2026-08-01", "age": 24, "gender": "Female", "occupation_group": "Student",
        "region_group": "Asia", "education_group": "Bachelor", "device_category": "Smartphone",
        "primary_platform": "Instagram", "purpose_group": "Social Connection",
        "is_content_creator": False, "uses_screen_time_limits": True,
        "social_min": 90, "gaming_min": 20, "work_study_min": 180, "other_min": 30,
        "video_min": 60, "night_screen_min": 15, "pre_sleep_screen_min": 10,
        "notifications_per_day": 60, "pickups_per_day": 45, "app_opens_per_day": 80,
        "sleep_hours": 7.5, "sleep_quality_1_10": 7, "stress_0_10": 3, "mental_fatigue_0_10": 3,
        "anxiety_0_27": 5, "low_mood_0_27": 4, "happiness_0_10": 7, "loneliness_1_10": 3,
        "self_esteem_1_10": 7, "fomo_1_10": 3, "social_comparison_1_10": 3,
        "life_satisfaction_1_10": 7, "focus_0_100": 70, "productivity_0_100": 68,
        "physical_activity_min_per_day": 30, "caffeine_cups_per_day": 1,
    },
    {
        "date": "2026-08-02", "age": 24, "gender": "Female", "occupation_group": "Student",
        "region_group": "Asia", "education_group": "Bachelor", "device_category": "Smartphone",
        "primary_platform": "Instagram", "purpose_group": "Social Connection",
        "is_content_creator": False, "uses_screen_time_limits": True,
        "social_min": 220, "gaming_min": 40, "work_study_min": 60, "other_min": 50,
        "video_min": 140, "night_screen_min": 90, "pre_sleep_screen_min": 60,
        "notifications_per_day": 150, "pickups_per_day": 110, "app_opens_per_day": 190,
        "sleep_hours": 5.0, "sleep_quality_1_10": 4, "stress_0_10": 7, "mental_fatigue_0_10": 7,
        "anxiety_0_27": 12, "low_mood_0_27": 10, "happiness_0_10": 4, "loneliness_1_10": 6,
        "self_esteem_1_10": 4, "fomo_1_10": 7, "social_comparison_1_10": 7,
        "life_satisfaction_1_10": 4, "focus_0_100": 35, "productivity_0_100": 30,
        "physical_activity_min_per_day": 0, "caffeine_cups_per_day": 3,
    },
]


def build_template_csv() -> str:
    """A downloadable CSV: header row + two realistic filled example
    rows (one healthy-leaning day, one at-risk-leaning day) so a user
    sees the expected format/scale, not just bare column names."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=RAW_CSV_COLUMNS)
    writer.writeheader()
    for row in _EXAMPLE_ROWS:
        writer.writerow({col: row.get(col, "") for col in RAW_CSV_COLUMNS})
    return buf.getvalue()


@dataclass
class RowError:
    row_number: int
    date: str | None
    errors: dict[str, str]


@dataclass
class ImportResult:
    imported_count: int = 0
    imported_dates: list[str] = field(default_factory=list)
    failed_rows: list[RowError] = field(default_factory=list)
    # Dates this import had to assume rather than read (see
    # `import_csv_text`). Never left silent: the caller shows these back
    # to the user, because a health record filed under the wrong day is
    # worse than an import that refused.
    assumed_dates: list[str] = field(default_factory=list)
    # Columns the file carried that this importer recomputes itself.
    # Reported so a user who hand-edited one of them understands why
    # their edit did not survive.
    ignored_columns: list[str] = field(default_factory=list)


class CSVImportService:
    """Parses, validates, predicts, and persists one CSV upload for a
    single authenticated user - one row (= one day) at a time."""

    def __init__(
        self,
        history_service: HistoryService,
        validator: ValidationService,
        predictor: PredictionService,
    ) -> None:
        self.history_service = history_service
        self.validator = validator
        self.predictor = predictor

    # Shown against the `date` field of any row that would land on a day
    # the user has already recorded. Deliberately says what to do, not
    # just what went wrong: the fix is a control on the check-in page,
    # and a user who does not know that is stuck with a file that keeps
    # being refused. The frontend swaps this for a translated sentence
    # keyed off `already_recorded`; this English wording is the fallback
    # and is what the API itself returns.
    DUPLICATE_DAY_ERROR = (
        "already_recorded: {day} already has a check-in. Turn on "
        "\"Edit today's check-in\" before uploading, or this file would "
        "overwrite the result already saved for that day."
    )

    def import_csv_text(self, csv_text: str, allow_update: bool = False) -> ImportResult:
        """Import a CSV of daily entries.

        Two shapes of file reach this method, and both are accepted:

        * the bulk template from `build_template_csv()` - many rows, each
          with its own `date`;
        * the single-row questionnaire CSV the result page exports, which
          is a snapshot of one check-in.

        The questionnaire export carries the *validated* payload, so it
        includes the derived columns (ratios, densities, and the user's
        personal `screen_ewma_baseline`). Those are dropped rather than
        trusted: they are recomputed from the raw numbers anyway, and
        `screen_ewma_baseline` is specific to the account that produced
        the file - carrying it into a different account would quietly
        seed that account's baseline with a stranger's history.

        `allow_update` is the same explicit edit flag the live check-in
        takes. record() upserts, so without it an upload covering a day
        the user already logged would silently destroy that day's real
        result - and the questionnaire export is a single row filed
        under *today*, which is precisely the day most likely to already
        exist. Rows that would overwrite are refused individually and
        reported by date; the rest of the file still imports.
        """
        result = ImportResult()
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        existing_dates: set[str] = set()
        if not allow_update:
            try:
                existing_dates = {
                    entry.get("date")
                    for entry in self.history_service.get_all(include_excluded=True)
                    if entry.get("date")
                }
            except Exception:  # noqa: BLE001
                # A history read failing must not become a blanket
                # refusal of the whole file: that would be a worse
                # outcome than the behaviour every earlier release had.
                existing_dates = set()

        # day_index reflects this row's position within the *uploaded
        # batch* (matching FEATURE_SCHEMA's "which day of your tracking
        # period" description), sorted by date so it stays monotonic
        # even if the file itself wasn't in date order.
        def _row_date(r: dict[str, Any]) -> str:
            return (r.get("date") or "").strip()

        rows.sort(key=_row_date)

        # A questionnaire export has no `date` column at all. When the
        # file holds exactly one row there is no ambiguity about which
        # day it describes, so it is filed under today and the assumption
        # is reported back. With several undated rows there is nothing to
        # guess from, and each row still fails with the explicit error.
        header = list(rows[0].keys()) if rows else []
        undated_single_row = (
            len(rows) == 1 and not _row_date(rows[0])
        )

        ignored = sorted(
            {
                key for key in header
                if key and (key in _DERIVED_FIELDS or key in _CALENDAR_FIELDS)
            }
        )
        result.ignored_columns = ignored

        for i, raw_row in enumerate(rows, start=1):
            date_str = _row_date(raw_row)
            if not date_str and undated_single_row:
                parsed_date = date_cls.today()
                date_str = parsed_date.isoformat()
                result.assumed_dates.append(date_str)
            elif not date_str:
                result.failed_rows.append(RowError(i, None, {"date": "Missing required 'date' column (YYYY-MM-DD)."}))
                continue
            else:
                try:
                    parsed_date = date_cls.fromisoformat(date_str)
                except ValueError:
                    result.failed_rows.append(RowError(i, date_str, {"date": f"'{date_str}' is not a valid YYYY-MM-DD date."}))
                    continue

            if date_str in existing_dates:
                result.failed_rows.append(RowError(
                    i, date_str,
                    {"date": self.DUPLICATE_DAY_ERROR.format(day=date_str)},
                ))
                continue

            # Only the non-empty columns the file actually provided -
            # a blank cell is left absent, not filled with a default,
            # so ValidationService reports it as missing exactly like a
            # blank field in the manual entry form would (item 8's
            # "never silently default a missing input" rule).
            row_data: dict[str, Any] = {
                key: value for key, value in raw_row.items()
                if key not in (None, "date")
                and key not in _DERIVED_FIELDS
                and key not in _CALENDAR_FIELDS
                and value is not None and str(value).strip() != ""
            }
            _coerce_boolean_strings(row_data)

            row_data["day_index"] = i
            row_data["day_of_week"] = parsed_date.strftime("%A")
            row_data["is_weekend"] = 1 if parsed_date.weekday() >= 5 else 0

            derived = derive_features(row_data)

            validation = self.validator.validate(derived)
            if not validation.is_valid:
                result.failed_rows.append(RowError(i, date_str, validation.errors))
                continue

            prediction_result = self.predictor.predict(validation.cleaned_data)
            self.history_service.record(validation.cleaned_data, prediction_result, on_date=parsed_date)

            result.imported_count += 1
            result.imported_dates.append(date_str)

        return result
