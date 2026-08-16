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

# The one definition of the project root - see core/paths.py. Computed
# by directory depth here until it wasn't, twice; a path relative to a
# file's own position is correct until something moves and silently
# wrong afterwards, because a Path that does not exist still works.
from core import paths

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

        self.project_root = paths.PROJECT_ROOT

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
        self._check_feature_columns_match_the_model()
        return True

    def _check_feature_columns_match_the_model(self) -> None:
        """The column list and the pickle beside it must be one pair.

        Both files are loaded here already, and until this check existed
        nothing compared them. They can drift apart in one step: retrain
        and commit the new .pkl while an older feature_columns.json is
        still on disk, and every file is present, every checksum is a
        valid file, and the app starts.

        It then breaks somewhere useless. The fitted ColumnTransformer
        is the thing that actually knows its input schema, so the first
        complaint arrives from deep inside sklearn - during split-conformal
        calibration, several frames below any code in this repository -
        as `ValueError: columns are missing: {...}` listing 133 names.
        That was the shape of it in practice: a classifier fitted on 184
        columns paired with a 52-column list, which is what a merge that
        took the model from one tree and the list from another produces.
        The app came up "healthy", answered /health, and could not score
        a single day.

        So it is checked at load, named plainly, and refused. A mismatched
        pair cannot serve a correct prediction, and starting anyway only
        moves the discovery somewhere harder to read.
        """
        expected = getattr(self.model, "feature_names_in_", None)
        if expected is None:
            # A pipeline records the schema on its first step, not on
            # itself. Estimators that record nothing at all are left
            # alone rather than guessed at.
            first_step = getattr(self.model, "steps", None)
            if first_step:
                expected = getattr(first_step[0][1], "feature_names_in_", None)
        if expected is None:
            return

        expected = list(expected)
        declared = self.feature_columns

        if list(declared) == expected:
            return

        missing = [name for name in expected if name not in set(declared)]
        unexpected = [name for name in declared if name not in set(expected)]

        detail = [
            f"'{self.feature_columns_path.name}' does not match the model it "
            f"is paired with for task '{self.task}'.",
            f"  {self.model_path.name} was fitted on {len(expected)} columns",
            f"  {self.feature_columns_path.name} lists {len(declared)}",
        ]
        if missing:
            detail.append(
                f"  {len(missing)} the model needs are absent from the list, "
                f"e.g. {', '.join(sorted(missing)[:5])}"
            )
        if unexpected:
            detail.append(
                f"  {len(unexpected)} in the list the model does not know, "
                f"e.g. {', '.join(sorted(unexpected)[:5])}"
            )
        if not missing and not unexpected:
            detail.append("  same names, different order")
        detail.append(
            "Retrain (models/train_classification.py, models/train_regression.py) "
            "so both are written together, or restore the pair that belong to "
            "each other. Every prediction is wrong until they agree."
        )
        raise ValueError("\n".join(detail))