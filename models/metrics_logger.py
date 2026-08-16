"""
=========================================================
Digital Wellness AI
Metrics Logger

Responsibilities
----------------
- Save validation metrics
- Save final test metrics
- Save model comparison results
  (task-aware: classification -> metrics.json, regression -> metrics_regression.json)
=========================================================
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# The one definition of the project root - see core/paths.py. Computed
# by directory depth here until it wasn't, twice; a path relative to a
# file's own position is correct until something moves and silently
# wrong afterwards, because a Path that does not exist still works.
from core import paths

logger = logging.getLogger(__name__)

PROJECT_ROOT = paths.PROJECT_ROOT
MODEL_DIR = PROJECT_ROOT / "artifacts"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

_METRICS_FILENAMES = {
    "classification": "metrics.json",
    "regression": "metrics_regression.json",
}

_VALIDATION_KEYS = {
    "classification": [
        "accuracy", "precision", "recall", "f1", "roc_auc",
        "cv_accuracy_mean", "cv_accuracy_std", "cv_f1_mean", "cv_f1_std",
        "overfit_gap", "selection_score", "training_time",
    ],
    "regression": [
        "MAE", "RMSE", "R2",
        "cv_r2_mean", "cv_r2_std", "cv_mae_mean", "cv_mae_std",
        "overfit_gap", "selection_score", "training_time",
    ],
}


def _round_float(value: Any) -> Any:
    """Round float values for cleaner JSON output."""

    if isinstance(value, float):
        return round(value, 4)
    return value


def _prepare_validation_metrics(
    task: str,
    validation_results: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Prepare validation metrics for JSON serialization."""

    keys = _VALIDATION_KEYS[task]

    output = {}
    for model_name, values in validation_results.items():
        output[model_name] = {key: _round_float(values[key]) for key in keys if key in values}

    return output


def _prepare_test_metrics(task: str, test_metrics: Dict[str, Any]) -> Dict[str, Any]:
    if task == "classification":
        return {
            "accuracy": _round_float(test_metrics["accuracy"]),
            "precision": _round_float(test_metrics["precision"]),
            "recall": _round_float(test_metrics["recall"]),
            "f1": _round_float(test_metrics["f1"]),
            "roc_auc": _round_float(test_metrics["roc_auc"]),
            "confusion_matrix": test_metrics["confusion_matrix"],
            "classification_report": test_metrics["classification_report"],
        }

    return {
        "MAE": _round_float(test_metrics["MAE"]),
        "RMSE": _round_float(test_metrics["RMSE"]),
        "R2": _round_float(test_metrics["R2"]),
    }


def save_metrics(
    *,
    task: str = "classification",
    validation_results: Dict[str, Dict[str, Any]],
    test_metrics: Dict[str, Any],
    best_model_name: str,
    filename: Optional[str] = None,
) -> Path:
    """Save all evaluation metrics for a given task."""

    filename = filename or _METRICS_FILENAMES[task]

    output = {
        "task": task,
        "best_model": best_model_name,
        "validation": _prepare_validation_metrics(task, validation_results),
        "test": _prepare_test_metrics(task, test_metrics),
    }

    output_path = MODEL_DIR / filename

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=4, ensure_ascii=False)

    logger.info("Metrics saved -> %s", output_path)
    return output_path


# =========================================================
# Debug
# =========================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    print("Metrics Logger module loaded successfully.")
