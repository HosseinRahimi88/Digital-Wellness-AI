"""
=========================================================
Digital Wellness AI
User-Level Split Regeneration (one-off data pipeline script)
=========================================================

Fixes the leakage documented in ML_AUDIT_REPORT.md section 1b/3: the
same synthetic "users" (rows sharing a stable demographic signature,
tracked across their day_index 1..N diary) were previously scattered
randomly across data/train.csv, data/validation.csv and data/test.csv,
so validation/test performance was inflated relative to genuinely new
users.

Why there's no true user_id to key on: the raw CSVs never carried one
(confirmed - 'user_id' is not a column in any of the three files, and
no data-generation script exists anywhere in this repo to regenerate
one from). This script reconstructs a user-level GROUP key instead,
from the columns that are demographically stable for a given person
across days: age, gender, occupation_group, region_group,
education_group, device_category, primary_platform, purpose_group,
is_content_creator, uses_screen_time_limits. None of these should
change day-to-day for the same person, and age is confirmed to be a
clean int (no jitter) in the data, so this reconstruction can only
ever OVER-group (merge two distinct people who happen to share every
one of these 10 fields into one group - confirmed this happens for
~42% of signatures, since the field values are coarse categories, not
a real ID) - never UNDER-group (split one real person's rows into two
different groups). Over-grouping is the safe failure mode for this
purpose: it can only make the split's effective diversity smaller,
never allow one real user's rows to leak across the train/val/test
boundary. That's why this proxy is a defensible - if imperfect -
substitute for a true user_id, and it should be treated as a "cohort"
key, not a claim that every one of these groups is exactly one person.

Method: pool the three existing CSVs, build the group key, then run
sklearn's StratifiedGroupKFold (guarantees every group's rows land
entirely in one fold, while still trying to balance the classification
target's class distribution across folds) with n_splits=18. Folds are,
by construction, a true partition of all groups - so taking fold 0 as
the new test set, fold 1 as the new validation set, and the union of
the remaining 16 as the new train set gives three mutually
group-disjoint splits with ~1/18 (~5.56%) in validation, ~5.56% in
test, ~88.9% in train - matching the original ~89.0% / 5.5% / 5.5%
split ratios.

Run once: `python3 models/regenerate_user_split.py`
Then retrain everything against the new files (train_classification.py,
train_regression.py, train_persona.py) - this script only rewrites
data/{train,validation,test}.csv and a verification report; it does
not touch any model artifact itself.
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "archive_pre_user_split_fix"

TRAIN_FILE = DATA_DIR / "train.csv"
VALIDATION_FILE = DATA_DIR / "validation.csv"
TEST_FILE = DATA_DIR / "test.csv"

REPORT_FILE = PROJECT_ROOT / "artifacts" / "leakage_verification_report.json"

# Columns that are demographically stable for the same person across
# their diary of days - see module docstring for why these and not a
# true user_id.
STABLE_SIGNATURE_COLUMNS = [
    "age",
    "gender",
    "occupation_group",
    "region_group",
    "education_group",
    "device_category",
    "primary_platform",
    "purpose_group",
    "is_content_creator",
    "uses_screen_time_limits",
]

CLASSIFICATION_TARGET = "future_health_class_7d"

N_SPLITS = 18  # 1/18 ~= 5.56% per fold -> test=1 fold, val=1 fold, train=16 folds
RANDOM_STATE = 42


def _load_pool() -> pd.DataFrame:
    train = pd.read_csv(TRAIN_FILE)
    val = pd.read_csv(VALIDATION_FILE)
    test = pd.read_csv(TEST_FILE)
    logger.info("Loaded existing splits: train=%d val=%d test=%d", len(train), len(val), len(test))
    pooled = pd.concat([train, val, test], ignore_index=True)
    return pooled


def _archive_originals() -> None:
    ARCHIVE_DIR.mkdir(exist_ok=True)
    for name, src in (("train.csv", TRAIN_FILE), ("validation.csv", VALIDATION_FILE), ("test.csv", TEST_FILE)):
        dest = ARCHIVE_DIR / name
        if not dest.exists():
            shutil.copy(src, dest)
            logger.info("Archived original %s -> %s", src, dest)
        else:
            logger.info("Archive already present for %s, leaving it alone", name)


def _build_groups(pooled: pd.DataFrame) -> np.ndarray:
    signature = pooled[STABLE_SIGNATURE_COLUMNS].astype(str).agg("|".join, axis=1)
    group_ids, _ = pd.factorize(signature)
    logger.info("Reconstructed %d unique user groups from %d rows", len(set(group_ids)), len(pooled))
    return group_ids


def main() -> None:
    pooled = _load_pool()
    _archive_originals()

    groups = _build_groups(pooled)
    y = pooled[CLASSIFICATION_TARGET].values

    skf = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    folds = list(skf.split(pooled, y, groups))

    test_idx = folds[0][1]
    val_idx = folds[1][1]
    used = set(test_idx.tolist()) | set(val_idx.tolist())
    train_idx = np.array([i for i in range(len(pooled)) if i not in used])

    # --- Hard verification before writing anything -------------------
    train_groups = set(groups[train_idx].tolist())
    val_groups = set(groups[val_idx].tolist())
    test_groups = set(groups[test_idx].tolist())

    tv = train_groups & val_groups
    tt = train_groups & test_groups
    vt = val_groups & test_groups
    assert not tv, f"Train/Validation group overlap: {len(tv)} groups"
    assert not tt, f"Train/Test group overlap: {len(tt)} groups"
    assert not vt, f"Validation/Test group overlap: {len(vt)} groups"
    assert len(train_idx) + len(val_idx) + len(test_idx) == len(pooled)
    assert len(set(train_idx.tolist()) & set(val_idx.tolist())) == 0
    assert len(set(train_idx.tolist()) & set(test_idx.tolist())) == 0
    assert len(set(val_idx.tolist()) & set(test_idx.tolist())) == 0

    new_train = pooled.iloc[train_idx].reset_index(drop=True)
    new_val = pooled.iloc[val_idx].reset_index(drop=True)
    new_test = pooled.iloc[test_idx].reset_index(drop=True)

    def class_dist(df: pd.DataFrame) -> dict:
        return (df[CLASSIFICATION_TARGET].value_counts(normalize=True).round(4) * 100).to_dict()

    report = {
        "method": "StratifiedGroupKFold(n_splits=18, shuffle=True, random_state=42); "
                  "fold 0 held-out -> test, fold 1 held-out -> validation, remaining 16 -> train",
        "group_key_columns": STABLE_SIGNATURE_COLUMNS,
        "total_rows": int(len(pooled)),
        "total_user_groups": int(len(set(groups.tolist()))),
        "rows": {"train": int(len(new_train)), "validation": int(len(new_val)), "test": int(len(new_test))},
        "row_ratios_pct": {
            "train": round(len(new_train) / len(pooled) * 100, 2),
            "validation": round(len(new_val) / len(pooled) * 100, 2),
            "test": round(len(new_test) / len(pooled) * 100, 2),
        },
        "user_groups": {
            "train": len(train_groups),
            "validation": len(val_groups),
            "test": len(test_groups),
        },
        "group_intersections": {
            "train_and_validation": len(tv),
            "train_and_test": len(tt),
            "validation_and_test": len(vt),
        },
        "class_distribution_pct": {
            "train": class_dist(new_train),
            "validation": class_dist(new_val),
            "test": class_dist(new_test),
        },
    }

    new_train.to_csv(TRAIN_FILE, index=False)
    new_val.to_csv(VALIDATION_FILE, index=False)
    new_test.to_csv(TEST_FILE, index=False)

    REPORT_FILE.parent.mkdir(exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    logger.info("=" * 60)
    logger.info("New split written. Rows: train=%d val=%d test=%d", len(new_train), len(new_val), len(new_test))
    logger.info("User groups: train=%d val=%d test=%d", len(train_groups), len(val_groups), len(test_groups))
    logger.info(
        "Intersections (must all be 0): train&val=%d train&test=%d val&test=%d",
        len(tv), len(tt), len(vt),
    )
    logger.info("Verification report written to %s", REPORT_FILE)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
