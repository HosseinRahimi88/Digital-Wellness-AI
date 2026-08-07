"""
Model Registry
--------------
Central access point for all trained model artifacts, per task.

Backward compatible: ModelRegistry() with no arguments still loads the
classification artifacts, same filenames as before.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

_MODEL_FILENAMES = {
    "classification": "health_classifier.pkl",
    "regression": "health_regressor.pkl",
}
_FEATURE_FILENAMES = {
    "classification": "feature_columns.json",
    "regression": "feature_columns_regression.json",
}
_METRICS_FILENAMES = {
    "classification": "metrics.json",
    "regression": "metrics_regression.json",
}
_INFO_FILENAMES = {
    "classification": "model_info.json",
    "regression": "model_info_regression.json",
}


class ModelRegistry:
    """
    Central registry for loading ML artifacts.

    Loads each artifact only once and caches it in memory.
    """

    def __init__(self, task: str = "classification") -> None:

        if task not in ("classification", "regression"):
            raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")

        self.task = task

        # -----------------------------------------------------
        # Project Root & Path Resolution
        # -----------------------------------------------------

        self.project_root = Path(__file__).resolve().parent.parent

        self.artifacts_dir = self.project_root / "artifacts"

        # -----------------------------------------------------
        # Artifact Paths
        # -----------------------------------------------------

        self.model_path = self.artifacts_dir / _MODEL_FILENAMES[task]
        self.feature_columns_path = self.artifacts_dir / _FEATURE_FILENAMES[task]
        self.metrics_path = self.artifacts_dir / _METRICS_FILENAMES[task]
        self.model_info_path = self.artifacts_dir / _INFO_FILENAMES[task]

        # -----------------------------------------------------
        # Cache
        # -----------------------------------------------------

        self._model = None
        self._feature_columns = None
        self._metrics = None
        self._model_info = None

    # =====================================================
    # Internal JSON Loader
    # =====================================================

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    # =====================================================
    # Model
    # =====================================================

    @property
    def model(self):
        if self._model is None:
            logger.info("Loading trained %s model...", self.task)
            self._model = joblib.load(self.model_path)
        return self._model

    # =====================================================
    # Feature Columns
    # =====================================================

    @property
    def feature_columns(self) -> list[str]:
        if self._feature_columns is None:
            logger.info("Loading feature columns...")
            self._feature_columns = self._load_json(self.feature_columns_path)
        return self._feature_columns

    # =====================================================
    # Metrics
    # =====================================================

    @property
    def metrics(self) -> dict[str, Any]:
        if self._metrics is None:
            logger.info("Loading evaluation metrics...")
            self._metrics = self._load_json(self.metrics_path)
        return self._metrics

    # =====================================================
    # Model Info
    # =====================================================

    @property
    def model_info(self) -> dict[str, Any]:
        if self._model_info is None:
            logger.info("Loading model information...")
            self._model_info = self._load_json(self.model_info_path)
        return self._model_info

    # =====================================================
    # Convenience Properties
    # =====================================================

    @property
    def model_name(self) -> str:
        return self.model_info.get("model_name", "Unknown Model")

    @property
    def feature_count(self) -> int:
        return len(self.feature_columns)

    @property
    def classes(self):
        if self.task != "classification":
            return []

        classes = self.model_info.get("classes")
        if classes:
            return list(classes)
        return []

    # =====================================================
    # Validation
    # =====================================================

    def validate(self) -> bool:
        required_files = [
            self.model_path,
            self.feature_columns_path,
            self.metrics_path,
            self.model_info_path,
        ]

        missing = [file for file in required_files if not file.exists()]

        if missing:
            raise FileNotFoundError(
                f"Missing artifact files for task '{self.task}' in '{self.artifacts_dir}':\n"
                + "\n".join(str(file) for file in missing)
            )

        logger.info("All artifact files found for task '%s'.", self.task)
        return True