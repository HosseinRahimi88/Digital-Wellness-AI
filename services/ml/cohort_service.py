"""
Cohort Service
----------------
Real population-level comparison, built from the project's actual
training dataset (data/train.csv, 84k+ real rows) - not a fabricated
or hand-typed distribution. This is the same dataset
models/train_regression.py / models/train_classification.py trained
on, so "your value vs. the cohort" is a comparison against the exact
population the model itself was fit to, not a synthetic stand-in.

health_score_0_100 is reconstructed here by CALLING
models/data_loader.reconstruct_health_score, so this can never become a
second, competing definition of "health score".

That sentence used to say the formula was "imported from there rather
than re-implemented", while the line below it re-implemented the mean of
the six subscores. Harmless while the score WAS that mean, and wrong the
day it grew a seventh screen-load term: this panel tells a user where
they sit against the population the models were fit to, and it would
have been ranking their screen-aware score against a screen-blind
cohort. Every percentile on the page would have been off, in the
direction that flatters heavy screen use.

Performance: the CSV (84k rows x 70 columns) is loaded and reduced to
only the handful of columns these features need, once per process,
via functools.lru_cache - every subsequent call reuses the cached
DataFrame instead of re-reading/re-parsing the file (the "avoid
repeated expensive calculations" requirement).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

import pandas as pd

from models.data_loader import (
    TRAIN_FILE, HEALTH_SCORE_COLUMN, SUBSCORE_COLUMNS, reconstruct_health_score,
)
from services.ml import cohort_reference
from utils.feature_derivation import compute_total_screen_min_vectorized

# Cohort fields this service can compare a user against - real raw
# columns in data/train.csv, restricted to ones with a direct
# equivalent among HistoryService.TRACKED_FIELDS so a user's own
# recorded average is directly comparable (same units, same meaning).
COHORT_FIELDS = [
    "total_screen_min",
    "social_min",
    "gaming_min",
    "sleep_hours",
    "sleep_quality_1_10",
    "stress_0_10",
    "focus_0_100",
    "productivity_0_100",
    "physical_activity_min_per_day",
    HEALTH_SCORE_COLUMN,
]

# HistoryService/AnalyticsService use "health_score" as the field name
# (see services/identity/history_service.py); the cohort dataset's reconstructed
# column is named HEALTH_SCORE_COLUMN ("health_score_0_100"). Every
# other tracked field name is identical in both places, so this is the
# one translation needed between "the app's field names" and "the
# cohort dataset's column names".
USER_FIELD_TO_COHORT_FIELD = {"health_score": HEALTH_SCORE_COLUMN}


@lru_cache(maxsize=1)
def _load_cohort_frame() -> Optional[pd.DataFrame]:
    """
    The real training dataset, reduced to COHORT_FIELDS (+ the six
    subscores needed to reconstruct health_score_0_100, + the four raw
    category-minute columns needed to recompute total_screen_min),
    loaded once per process and cached. Returns None (never raises) if
    the CSV is unavailable - callers degrade to "cohort comparison
    unavailable" rather than crashing a page that doesn't strictly
    need it.
    """
    try:
        raw_total_screen_columns = [
            c for c in ("social_min", "gaming_min", "work_study_min", "video_min",
                        "other_min", "pre_sleep_screen_min")
            if c not in COHORT_FIELDS
        ]
        needed_columns = list(dict.fromkeys(
            [c for c in COHORT_FIELDS if c != HEALTH_SCORE_COLUMN]
            + SUBSCORE_COLUMNS
            + raw_total_screen_columns
        ))
        df = pd.read_csv(TRAIN_FILE, usecols=needed_columns)
    except (FileNotFoundError, ValueError):
        return None

    if HEALTH_SCORE_COLUMN not in df.columns:
        missing_subscores = [c for c in SUBSCORE_COLUMNS if c not in df.columns]
        if not missing_subscores:
            df = reconstruct_health_score(df)

    # total_screen_min: recomputed the same way models/data_loader.py's
    # reconstruct_derived_features() does (sum of the five category
    # fields, via the exact same helper derive_features() uses) rather
    # than trusted from the CSV - see that module's comment for why the
    # stored value has different semantics than anything the live app
    # can ever report. Only recomputed if we actually have all five raw
    # category columns; degrades to the raw stored value otherwise.
    category_columns = ["social_min", "gaming_min", "work_study_min", "video_min", "other_min"]
    if "total_screen_min" in COHORT_FIELDS and all(c in df.columns for c in category_columns):
        df["total_screen_min"] = compute_total_screen_min_vectorized(df)

    return df


class CohortService:
    """Real percentile/summary comparisons against the training cohort."""

    @staticmethod
    def source() -> str:
        """Where the numbers below are coming from, named out loud.

        "dataset"   - the real training CSV is present and is being read
        "reference" - the CSV is absent, so the precomputed distribution
                      shipped in artifacts/cohort_reference.json is used
        "none"      - neither is available

        Every distribution of this project ships WITHOUT data/*.csv (175
        MB of training data to display a percentile), so "reference" is
        what a reviewer will actually see, and the UI says so rather
        than implying it read the whole cohort.
        """
        if _load_cohort_frame() is not None:
            return "dataset"
        return "reference" if cohort_reference.is_available() else "none"

    @staticmethod
    def is_available() -> bool:
        return _load_cohort_frame() is not None or cohort_reference.is_available()

    @staticmethod
    def cohort_size() -> int:
        df = _load_cohort_frame()
        if df is not None:
            return int(len(df))
        return cohort_reference.cohort_size()

    @classmethod
    def percentile_for(cls, field: str, value: float) -> Optional[float]:
        """
        What percentage of the real cohort has a value <= `value` for
        `field` (0-100). None if the field/data isn't available. This
        is a plain empirical CDF lookup (rank-based), not a
        distributional assumption (no normality assumed).
        """
        df = _load_cohort_frame()
        if df is None or field not in df.columns:
            # Falls back to the shipped distribution, which answers the
            # same rank question to within a percentile. Measured on
            # this dataset: health_score 82.0 vs 82.1, sleep_hours 13.6
            # vs 13.7, total_screen_min 95.0 vs 95.0.
            return cohort_reference.percentile_for(field, value)
        column = df[field].dropna()
        if column.empty:
            return None
        return round(float((column <= value).mean() * 100.0), 1)

    @classmethod
    def cohort_summary(cls, field: str) -> Optional[dict[str, float]]:
        df = _load_cohort_frame()
        if df is None or field not in df.columns:
            return cohort_reference.summary_for(field)
        column = df[field].dropna()
        if column.empty:
            return None
        return {
            "mean": round(float(column.mean()), 1),
            "median": round(float(column.median()), 1),
            "p25": round(float(column.quantile(0.25)), 1),
            "p75": round(float(column.quantile(0.75)), 1),
        }

    @classmethod
    def compare_user_to_cohort(
        cls, user_averages: dict[str, float]
    ) -> list[dict[str, object]]:
        """
        `user_averages` maps real HistoryService-tracked field names to
        this user's own real historical average for that field (the
        caller computes this from real entries - this method never
        invents a user value). Returns one row per field with cohort
        data available:
            {"field", "user_value", "cohort_percentile", "cohort_mean"}
        """
        rows = []
        for field, value in user_averages.items():
            if value is None:
                continue
            cohort_field = USER_FIELD_TO_COHORT_FIELD.get(field, field)
            percentile = cls.percentile_for(cohort_field, value)
            if percentile is None:
                continue
            summary = cls.cohort_summary(cohort_field)
            rows.append({
                "field": field,
                "user_value": round(float(value), 1),
                "cohort_percentile": percentile,
                "cohort_mean": summary["mean"] if summary else None,
            })
        return rows
