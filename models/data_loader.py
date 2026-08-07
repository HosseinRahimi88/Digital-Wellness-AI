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

# =========================================================
# Logging
# =========================================================

logger = logging.getLogger(__name__)

# =========================================================
# Project Paths
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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


def _reconstruct_health_score(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Add `health_score_0_100` as the row-wise mean of the six composite
    subscores, if it isn't already present. Does nothing if the target
    already exists (e.g. a future dataset export that includes it
    directly) or if the subscore columns are missing.
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
    dataframe[HEALTH_SCORE_COLUMN] = (
        dataframe[SUBSCORE_COLUMNS].mean(axis=1).clip(0.0, 100.0)
    )

    logger.info(
        "Reconstructed '%s' as the mean of the six composite subscores.",
        HEALTH_SCORE_COLUMN,
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
# _reconstruct_health_score above - means every consumer of
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

    train_df = _reconstruct_health_score(_load_csv(TRAIN_FILE))

    validation_df = _reconstruct_health_score(_load_csv(
        VALIDATION_FILE
    ))

    test_df = _reconstruct_health_score(_load_csv(TEST_FILE))

    train_df = reconstruct_derived_features(train_df)
    validation_df = reconstruct_derived_features(validation_df)
    test_df = reconstruct_derived_features(test_df)

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