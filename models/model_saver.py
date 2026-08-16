"""
=========================================================
Digital Wellness AI
Model Saver

Artifact filenames are task-aware so classification and regression
artifacts never overwrite each other:

    classification -> health_classifier.pkl, feature_columns.json,
                       model_info.json   (unchanged, backward-compatible)
    regression      -> health_regressor.pkl, feature_columns_regression.json,
                       model_info_regression.json
=========================================================
"""

from __future__ import annotations

import json
import logging
import platform
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import joblib
import pandas
import sklearn

# The one definition of the project root - see core/paths.py. Computed
# by directory depth here until it wasn't, twice; a path relative to a
# file's own position is correct until something moves and silently
# wrong afterwards, because a Path that does not exist still works.
from core import paths

logger = logging.getLogger(__name__)

PROJECT_ROOT = paths.PROJECT_ROOT
MODEL_DIR = PROJECT_ROOT / "artifacts"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

_MODEL_FILENAMES = {
    "classification": "health_classifier.pkl",
    "regression": "health_regressor.pkl",
}
_FEATURE_FILENAMES = {
    "classification": "feature_columns.json",
    "regression": "feature_columns_regression.json",
}
_INFO_FILENAMES = {
    "classification": "model_info.json",
    "regression": "model_info_regression.json",
}


def save_best_model(pipeline, task: str = "classification") -> Path:
    """Save trained pipeline."""

    model_path = MODEL_DIR / _MODEL_FILENAMES[task]
    joblib.dump(pipeline, model_path)
    logger.info("Model saved -> %s", model_path)
    return model_path


def save_feature_columns(feature_columns: List[str], task: str = "classification") -> Path:
    """Save feature names."""

    output_path = MODEL_DIR / _FEATURE_FILENAMES[task]

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(feature_columns, file, indent=4, ensure_ascii=False)

    logger.info("Feature columns saved.")
    return output_path


def save_model_info(
    *,
    task: str = "classification",
    model_name: str,
    feature_count: int,
    target_column: str,
    classes: Optional[list] = None,
) -> Path:
    """Save metadata."""

    info = {
        "project": "Digital Wellness AI",
        "task": task,
        "version": "1.0.0",
        "saved_at": datetime.now().isoformat(),
        "model_name": model_name,
        "target_column": target_column,
        "number_of_features": feature_count,
        "python_version": platform.python_version(),
        "pandas_version": pandas.__version__,
        "sklearn_version": sklearn.__version__,
    }

    if classes is not None:
        info["classes"] = sorted(list(classes))

    output_path = MODEL_DIR / _INFO_FILENAMES[task]

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(info, file, indent=4, ensure_ascii=False)

    logger.info("Model metadata saved.")
    return output_path


def save_all(
    *,
    task: str = "classification",
    pipeline,
    feature_columns,
    model_name,
    target_column,
    classes: Optional[list] = None,
):
    """Save all project artifacts for a given task."""

    save_best_model(pipeline, task=task)
    save_feature_columns(feature_columns, task=task)

    save_model_info(
        task=task,
        model_name=model_name,
        feature_count=len(feature_columns),
        target_column=target_column,
        classes=classes,
    )

    logger.info("All artifacts saved successfully (%s).", task)
