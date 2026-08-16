"""
=========================================================
Digital Wellness AI
Data Loader

Responsibilities:
-----------------
- Load train, validation and test datasets
- Validate dataset files
- Perform basic dataset validation
=========================================================
"""

from pathlib import Path
from typing import Tuple

import logging
import pandas as pd

# The one definition of the project root - see core/paths.py. Computed
# by directory depth here until it wasn't, twice; a path relative to a
# file's own position is correct until something moves and silently
# wrong afterwards, because a Path that does not exist still works.
from core import paths
from utils.screen_load import screen_load_subscore_vectorized

# =========================================================
# Logging
# =========================================================

logger = logging.getLogger(__name__)

# =========================================================
# Project Paths
# =========================================================

PROJECT_ROOT = paths.PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data"

TRAIN_FILE = DATA_DIR / "train.csv"
VALIDATION_FILE = DATA_DIR / "validation.csv"
TEST_FILE = DATA_DIR / "test.csv"

# =========================================================
# Regression target reconstruction
# =========================================================
#
# `health_score_0_100` (the regression target expected by
# models/preprocessing.TARGET_COLUMNS) does not exist as a raw column
# in any of the CSVs. What the CSVs do contain are six 0-100 composite
# subscores (sleep_subscore, night_subscore, focus_subscore,
# balance_subscore, stress_fatigue_subscore, activity_context_subscore)
# that the overall health score is built from -- get_feature_columns()
# already excludes them from training as leakage for exactly this
# reason. Reconstruct the target here, once, right after loading, so
# every downstream consumer (train_classification.py,
# train_regression.py, ad-hoc analysis) sees the same target.

SUBSCORE_COLUMNS = [
    "sleep_subscore",
    "night_subscore",
    "focus_subscore",
    "balance_subscore",
    "stress_fatigue_subscore",
    "activity_context_subscore",
]

HEALTH_SCORE_COLUMN = "health_score_0_100"

# The seventh component, and the only one that measures digital load.
#
# The six subscores above describe how a person slept and felt. None of
# them looks at how long the screen was on, and averaging the six gave a
# digital wellness score correlating +0.105 with total screen minutes
# and +0.034 with recreational minutes - no relationship, and the wrong
# sign both times. Grouped by recreational hours the mean went 62.5,
# 65.0, 63.7, 61.6, 60.6 across <2h, 2-4h, 4-6h, 6-8h and 8h+: a hump
# rather than a decline, with the heaviest days within two points of the
# lightest. utils/screen_load.py carries the thresholds and their
# sources.
#
# WEIGHT. Screen load counts double, so it is 2/8 of the score - a
# quarter of it - while each of the other six is 1/8.
#
# The weight was briefly 3/9 on the argument that counting the terms
# 6-to-3 kept the six in charge. Counting them is the wrong measure. The
# screen-load subscore has a standard deviation of 33.4 across the
# training split against 7.9 for the mean of the six, so a unit of
# screen-load weight moves the score more than four times as far as a
# unit of anything else, and the term outruns its share long before its
# count does. Measured on the training split:
#
#   weight   corr(score, recreational min)   corr(score, the six)
#     1              -0.518                       +0.818
#     2              -0.754                       +0.577
#     3              -0.844                       +0.425
#     4              -0.883                       +0.331
#
# At 3 the score is more a readout of screen minutes than a wellness
# score - which is the same failure as the original +0.034, pointing the
# other way. At 2 both relationships are strong and the digital-load
# term is the larger single influence without erasing how the person
# actually slept and felt. That is the balance this score is for, so 2
# is the weight, and the numbers above are why rather than a preference.
SCREEN_LOAD_COLUMN = "screen_load_subscore"
SCREEN_LOAD_WEIGHT = 2.0

# The wellbeing half of the score, on its own.
#
# `health_score_0_100` now measures two things that are very nearly
# independent - how a person felt and slept, and how heavy their digital
# load was (the two correlate -0.006). Most of the app wants them
# combined, which is what the score is for. Two places need them apart,
# because `future_health_class_7d` is a band on the WELLBEING axis only
# and says nothing about volume:
#
#   * models/calibrate_future_score.py, whose method rests on the class
#     being a tertile band of what it is calibrated against, and
#   * models/augment_future_score.py, which carries a row's rank within
#     its own band into its future band.
#
# Measured: tertile membership agrees with the label 80.2% of the time
# on the wellbeing mean and 43.3% on the combined score - barely above
# the 33.3% three balanced classes give by chance. Calibrating either
# file against the combined score would therefore have been calibrating
# against a relationship that is not there. They use this column, and
# the screen-load half is carried forward separately from the user's own
# day; see those modules for what that means for the seven-day figure.
WELLBEING_COLUMN = "wellbeing_subscore_mean"


def reconstruct_health_score(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Add `health_score_0_100` as the weighted mean of the six composite
    subscores plus the screen-load subscore, if it isn't already present.
    Does nothing if the target already exists (e.g. a future dataset
    export that includes it directly) or if the subscore columns are
    missing.

    PUBLIC ON PURPOSE. Three other modules used to carry their own copy
    of this formula - calibrate_future_score, augment_future_score and
    train_band_model each wrote `frame[SUBSCORES].mean(axis=1)` inline,
    and train_band_model documented the duplication as a deliberate
    saving, on the grounds that importing the loader would drag in the
    derived-feature rebuild it has no use for. That reasoning was sound
    and the conclusion was still wrong: the moment the target grew a
    seventh term, all three silently kept computing the old one, and the
    app would have shown a screen-aware score for today beside a
    screen-blind band for next week. This function is the cheap half of
    the loader - no derived-feature rebuild, just the target - so there
    is now something to import and no reason left to copy it.
    """

    if HEALTH_SCORE_COLUMN in dataframe.columns:
        return dataframe

    missing_subscores = [c for c in SUBSCORE_COLUMNS if c not in dataframe.columns]
    if missing_subscores:
        logger.warning(
            "Cannot reconstruct '%s': missing subscore columns %s",
            HEALTH_SCORE_COLUMN, missing_subscores,
        )
        return dataframe

    dataframe = dataframe.copy()
    dataframe[SCREEN_LOAD_COLUMN] = screen_load_subscore_vectorized(dataframe)
    dataframe[WELLBEING_COLUMN] = (
        dataframe[SUBSCORE_COLUMNS].mean(axis=1).clip(0.0, 100.0)
    )

    weighted_total = (
        dataframe[SUBSCORE_COLUMNS].sum(axis=1)
        + SCREEN_LOAD_WEIGHT * dataframe[SCREEN_LOAD_COLUMN]
    )
    dataframe[HEALTH_SCORE_COLUMN] = (
        weighted_total / (len(SUBSCORE_COLUMNS) + SCREEN_LOAD_WEIGHT)
    ).clip(0.0, 100.0)

    logger.info(
        "Reconstructed '%s' from %d subscores plus screen load at weight %.0f.",
        HEALTH_SCORE_COLUMN, len(SUBSCORE_COLUMNS), SCREEN_LOAD_WEIGHT,
    )

    return dataframe


# =========================================================
# Screen-time derived-feature reconstruction (train/serve consistency)
# =========================================================
#
# The raw CSVs' stored `total_screen_min` was generated with different
# semantics than the live app can ever produce: it reflects an
# independently-tracked device total that legitimately overlaps with
# the category-minute breakdown (e.g. background video while gaming),
# averaging ~1.55x the category-minute sum across the dataset. The live
# Streamlit form has no such independent measurement - it can only ever
# report total_screen_min as the literal sum of the five category
# fields (see utils/feature_derivation.py). Every ratio, density, and
# baseline-comparison feature computed FROM total_screen_min was
# therefore trained on a systematically different distribution than
# inference could ever produce for a real user.
#
# Fix: at load time, discard the stored values for every affected
# column and recompute them from each row's own raw category/behavior
# fields via derive_features() - the exact same function
# PredictionService / FormGenerator / AdvancedWhatIfService use at
# inference time. This can only be done here (not by hand-editing the
# CSVs) because it has to be the identical function call to guarantee
# zero skew, and doing it at load time - the same pattern as
# reconstruct_health_score above - means every consumer of
# load_datasets() gets it automatically and it can never drift out of
# sync again.

_DERIVE_FEATURES_RAW_COLUMNS = [
    "social_min", "gaming_min", "work_study_min", "video_min", "other_min",
    "night_screen_min", "pre_sleep_screen_min", "first_check_after_waking_min",
    "notifications_per_day", "pickups_per_day", "app_opens_per_day", "sessions_per_day",
]

_DERIVE_FEATURES_OVERWRITE_COLUMNS = [
    "total_screen_min", "social_ratio", "gaming_ratio", "work_study_ratio",
    "other_ratio", "night_ratio", "pre_sleep_ratio", "notification_density",
    "pickup_density", "app_open_density", "screen_vs_baseline_pct",
    "screen_ewma_baseline", "fragmentation_index_0_100", "digital_dependence_0_100",
]


def reconstruct_derived_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Overwrite total_screen_min and every feature derived from it with
    values recomputed by utils.feature_derivation.derive_features(), so
    training data and live inference compute these features from one
    single code path. See the module-level comment above for why.

    No-op (returns the frame unchanged) if any raw column
    derive_features() needs is missing, so this degrades gracefully
    rather than crashing on an unexpected schema.
    """
    from utils.feature_derivation import derive_features

    missing = [c for c in _DERIVE_FEATURES_RAW_COLUMNS if c not in dataframe.columns]
    if missing:
        logger.warning(
            "Cannot reconstruct derived screen-time features: missing raw columns %s",
            missing,
        )
        return dataframe

    dataframe = dataframe.copy()

    # screen_ewma_baseline must NOT be carried through into
    # derive_features() here: every row in these CSVs represents one
    # independent day's submission, not a chained "what-if off an
    # existing baseline" - so it should always take derive_features()'s
    # "no baseline supplied" branch, exactly like a real first-time
    # FormGenerator submission would.
    raw_records = (
        dataframe[_DERIVE_FEATURES_RAW_COLUMNS]
        .assign(screen_ewma_baseline=None)
        .to_dict(orient="records")
    )
    derived_records = [derive_features(row) for row in raw_records]
    derived_df = pd.DataFrame(derived_records, index=dataframe.index)

    for column in _DERIVE_FEATURES_OVERWRITE_COLUMNS:
        if column in derived_df.columns:
            dataframe[column] = derived_df[column].values

    logger.info(
        "Reconstructed %d derived screen-time features via derive_features() "
        "for train/serve consistency.",
        len(_DERIVE_FEATURES_OVERWRITE_COLUMNS),
    )

    return dataframe


# =========================================================
# Helpers
# =========================================================

def _check_files_exist() -> None:
    """
    Verify that all dataset files exist.
    """

    required_files = [
        TRAIN_FILE,
        VALIDATION_FILE,
        TEST_FILE,
    ]

    missing_files = [
        file for file in required_files
        if not file.exists()
    ]

    if missing_files:

        message = "\n".join(
            str(file)
            for file in missing_files
        )

        raise FileNotFoundError(
            f"\nMissing dataset files:\n{message}"
        )


def _load_csv(file_path: Path) -> pd.DataFrame:
    """
    Load a CSV file.

    Parameters
    ----------
    file_path : Path

    Returns
    -------
    pd.DataFrame
    """

    logger.info("Loading %s", file_path.name)

    return pd.read_csv(file_path)


def _validate_dataframe(
    dataframe: pd.DataFrame,
    dataset_name: str,
) -> None:
    """
    Perform basic dataframe validation.
    """

    if dataframe.empty:

        raise ValueError(
            f"{dataset_name} dataset is empty."
        )

    logger.info(
        "%s loaded successfully | Rows=%d | Columns=%d",
        dataset_name,
        dataframe.shape[0],
        dataframe.shape[1],
    )


# =========================================================
# Public API
# =========================================================


# ---------------------------------------------------------------------
# Per-user trend features
# ---------------------------------------------------------------------
# The raw CSVs carry no user id, so a user is reconstructed from the ten
# demographic columns that stay fixed for one person across their diary -
# the same key models/regenerate_user_split.py uses, and for the same
# reason (it can only ever over-group, never split one person in two).
TREND_GROUP_COLUMNS = [
    "age", "gender", "occupation_group", "region_group", "education_group",
    "device_category", "primary_platform", "purpose_group",
    "is_content_creator", "uses_screen_time_limits",
]


def _add_trend_features(dataframe: pd.DataFrame, label: str) -> pd.DataFrame:
    """Attach trend columns, or log clearly and continue without them."""
    from utils.trend_features import add_trend_features_to_frame, TREND_SOURCE_FIELDS

    missing_group = [c for c in TREND_GROUP_COLUMNS if c not in dataframe.columns]
    missing_src = [c for c in TREND_SOURCE_FIELDS if c not in dataframe.columns]
    if missing_group or missing_src or "day_index" not in dataframe.columns:
        logger.warning(
            "%s: cannot build trend features (missing group=%s, source=%s, day_index=%s). "
            "Continuing without them - the model will fall back to same-day signals only.",
            label, missing_group, missing_src, "day_index" not in dataframe.columns,
        )
        return dataframe

    out, names = add_trend_features_to_frame(dataframe, TREND_GROUP_COLUMNS)
    logger.info("%s: added %d per-user trend features.", label, len(names))
    return out


def load_datasets() -> Tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Load Train, Validation and Test datasets.

    Returns
    -------
    train_df
    validation_df
    test_df
    """

    logger.info("Checking dataset files...")

    _check_files_exist()

    train_df = reconstruct_health_score(_load_csv(TRAIN_FILE))

    validation_df = reconstruct_health_score(_load_csv(
        VALIDATION_FILE
    ))

    test_df = reconstruct_health_score(_load_csv(TEST_FILE))

    train_df = reconstruct_derived_features(train_df)
    validation_df = reconstruct_derived_features(validation_df)
    test_df = reconstruct_derived_features(test_df)

    # Per-user trend features. Added here, next to the other
    # reconstruction steps, so every consumer of load_datasets() gets them
    # automatically and training can never quietly diverge from serving.
    # The identical values are produced at inference time by
    # utils.trend_features.build_trend_features() from the user's own
    # saved check-ins - tests/ml/test_trend_features.py asserts the two paths
    # match element by element.
    train_df = _add_trend_features(train_df, "Train")
    validation_df = _add_trend_features(validation_df, "Validation")
    test_df = _add_trend_features(test_df, "Test")

    _validate_dataframe(
        train_df,
        "Train",
    )

    _validate_dataframe(
        validation_df,
        "Validation",
    )

    _validate_dataframe(
        test_df,
        "Test",
    )

    logger.info("All datasets loaded successfully.")

    return (
        train_df,
        validation_df,
        test_df,
    )


def load_validation_set() -> pd.DataFrame:
    """The validation split alone, prepared exactly as load_datasets() does.

    The conformal calibration in services/ml/uncertainty_service.py needs
    this one file and nothing else. Routing it through load_datasets()
    made it depend on train.csv and test.csv as well: a deployment that
    carried only the calibration set - which is the whole training corpus
    the running app actually reads - lost its uncertainty intervals to a
    FileNotFoundError about two files it never wanted. It also parsed and
    derived features for 80,000 training rows on every cold calibration,
    then discarded them.
    """
    if not VALIDATION_FILE.exists():
        raise FileNotFoundError(f"Missing validation set: {VALIDATION_FILE}")

    validation_df = reconstruct_health_score(_load_csv(VALIDATION_FILE))
    validation_df = reconstruct_derived_features(validation_df)
    validation_df = _add_trend_features(validation_df, "Validation")
    _validate_dataframe(validation_df, "Validation")
    return validation_df


# =========================================================
# Debug
# =========================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s",
    )

    train, validation, test = load_datasets()

    print()

    print(train.head())

    print()

    print(validation.head())

    print()

    print(test.head())