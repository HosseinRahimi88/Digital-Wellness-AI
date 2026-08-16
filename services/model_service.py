"""
Model Service
-------------
Thin business-logic layer over `ModelRegistry` for read-only model
metadata (metrics, model info) - the kind of thing a "Model Performance"
page needs. Exists so pages ask a *service* for this instead of
constructing `ModelRegistry` directly (which used to happen straight
inside `app/pages/Model_Performance.py`, i.e. data-access logic living
in the UI layer).

Deliberately independent of `ModelManager`/`PredictionService`: reading
`metrics.json`/`model_info.json` (a few KB) should never require loading
the multi-MB classifier/regressor pickles or building a SHAP explainer,
so a cold visit to the Model Performance page doesn't pay the full
inference-stack load cost just to show accuracy numbers. `ModelRegistry`
already lazy-loads each artifact independently (`.metrics`/`.model_info`
vs. `.model`), so this class simply keeps its own registries and never
touches `.model`.
"""

from __future__ import annotations

from typing import Any

from models.model_registry import ModelRegistry


class ModelService:
    """Read-only accessor for model metrics/info (never loads the model itself)."""

    def __init__(self) -> None:
        self._classification_registry = ModelRegistry(task="classification")
        self._regression_registry = ModelRegistry(task="regression")

    # ======================================================
    # Classification
    # ======================================================

    def classification_metrics(self) -> dict[str, Any]:
        self._classification_registry.validate()
        return self._classification_registry.metrics

    def classification_info(self) -> dict[str, Any]:
        self._classification_registry.validate()
        return self._classification_registry.model_info

    # ======================================================
    # Regression
    # ======================================================

    def regression_metrics(self) -> dict[str, Any]:
        self._regression_registry.validate()
        return self._regression_registry.metrics

    def regression_info(self) -> dict[str, Any]:
        self._regression_registry.validate()
        return self._regression_registry.model_info
