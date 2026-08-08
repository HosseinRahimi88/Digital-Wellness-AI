"""
=========================================================
SHAP Service
------------
Generate SHAP explanations for models inside sklearn Pipelines
(Supports Tree-based models, Linear models, and General Explainers).
=========================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


# =========================================================
# Data Model
# =========================================================

@dataclass(slots=True)
class SHAPFeature:
    """
    Represents one feature explanation.
    """
    feature: str
    value: Any
    shap_value: float
    abs_shap: float
    direction: str
    score: float = 0.0


# =========================================================
# SHAP Service
# =========================================================

class SHAPService:
    """
    SHAP explanation service adaptable to any model type inside sklearn Pipelines.
    """

    def __init__(self, model):
        self.raw_model = model

        if isinstance(model, Pipeline):
            self.model = model.steps[-1][1]
            self.transform_pipeline = Pipeline(model.steps[:-1])
        else:
            self.model = model
            self.transform_pipeline = None

        self.explainer = self._build_explainer(self.model)

    def _build_explainer(self, model: Any):
        """
        Dynamically selects the best SHAP explainer for the estimator.
        """
        model_name = type(model).__name__

        if (
            hasattr(model, "estimators_")
            or "Tree" in model_name
            or "XGB" in model_name
            or "Forest" in model_name
            or "Hist" in model_name
            or "GradientBoosting" in model_name
        ):
            try:
                logger.info("Using SHAP TreeExplainer for tree model: %s", model_name)
                return shap.TreeExplainer(model)
            except Exception as e:
                logger.warning("TreeExplainer failed: %s", e)

        try:
            if hasattr(model, "predict"):
                logger.info("Using SHAP Explainer with predict function for model: %s", model_name)
                n_features = getattr(model, "n_features_in_", 65)
                masker = np.zeros((1, n_features))
                return shap.Explainer(model.predict, masker)
        except Exception as exc:
            logger.warning("Failed to build function-based Explainer: %s", exc)

        return shap.Explainer(model)

    # -----------------------------------------------------

    @staticmethod
    def _source_columns_for_transformer(transformer, columns: list[str]) -> list[str]:
        """
        Expand a fitted ColumnTransformer sub-transformer's input `columns`
        into the list of *source* column names, repeated/ordered to line up
        1:1 with that sub-transformer's actual output columns.

        - Plain estimators (imputer/scaler pipelines) emit exactly one
          output column per input column, in the same order.
        - A OneHotEncoder (optionally wrapped in a Pipeline) emits
          len(categories_[i]) output columns for input column i, in order.
        """
        encoder = transformer
        if hasattr(transformer, "named_steps"):
            encoder = transformer.named_steps.get("encoder", transformer)

        categories = getattr(encoder, "categories_", None)
        if categories is not None:
            expanded: list[str] = []
            for col, cats in zip(columns, categories, strict=True):
                expanded.extend([col] * len(cats))
            return expanded

        # Non-one-hot transformer: one output per input column.
        return list(columns)

    def _prepare_input(self, X: pd.DataFrame) -> tuple[Any, list[str]]:
        """
        Pass input dataframe through preprocessing pipeline steps and
        return the transformed matrix together with, for every output
        column, the *original* (source) feature name it came from. This
        lets `explain()` look up each feature's real-world value by name
        directly on the untransformed input instead of relying on
        positional alignment with the transformed/expanded feature space.
        """
        if self.transform_pipeline is not None and len(self.transform_pipeline.steps) > 0:
            X_transformed = self.transform_pipeline.transform(X)

            if hasattr(X_transformed, "toarray"):
                X_transformed = X_transformed.toarray()

            preprocessor = self.transform_pipeline.steps[-1][1]

            source_columns: list[str] = []
            if hasattr(preprocessor, "transformers_"):
                for _name, transformer, columns in preprocessor.transformers_:
                    if transformer == "drop" or transformer == "passthrough":
                        continue
                    if not columns:
                        continue
                    source_columns.extend(
                        self._source_columns_for_transformer(transformer, list(columns))
                    )
            else:
                source_columns = [f"feature_{i}" for i in range(X_transformed.shape[1])]

            if len(source_columns) != X_transformed.shape[1]:
                # Safety net: fall back to generic names rather than mis-map.
                logger.warning(
                    "SHAP source-column count (%d) doesn't match transformed "
                    "feature count (%d); falling back to generic names.",
                    len(source_columns), X_transformed.shape[1],
                )
                source_columns = [f"feature_{i}" for i in range(X_transformed.shape[1])]

            return X_transformed, source_columns
        else:
            return X, list(X.columns)

    # -----------------------------------------------------

    def explain(
        self,
        X: pd.DataFrame,
        top_k: int = 5,
    ) -> List[SHAPFeature]:
        """
        Explain a single prediction sample.
        """
        if len(X) != 1:
            raise ValueError("SHAPService expects exactly one sample.")

        X_processed, feature_names = self._prepare_input(X)

        try:
            shap_output = self.explainer(X_processed)
            if hasattr(shap_output, "values"):
                values = shap_output.values[0]
            else:
                values = shap_output[0]
        except Exception:
            shap_values = self.explainer.shap_values(X_processed)
            if isinstance(shap_values, list):
                values = shap_values[0]
            else:
                values = shap_values[0] if getattr(shap_values, "ndim", 1) > 1 else shap_values

        if getattr(values, "ndim", 1) > 1:
            values = values[0]

        explanations: List[SHAPFeature] = []

        # `feature_names[i]` is now the true *source* column name (see
        # `_prepare_input`), so look the real-world value up on the raw,
        # untransformed input by name. This is correct regardless of how
        # many one-hot columns a categorical feature expands into, and it
        # avoids forcing a category string (e.g. "Male") through float().
        raw_row = X.iloc[0] if isinstance(X, pd.DataFrame) else None

        n_features = min(len(feature_names), len(values))

        for i in range(n_features):
            feature_name = feature_names[i]
            shap_val = values[i]

            if raw_row is not None and feature_name in raw_row.index:
                feature_val = raw_row[feature_name]
            elif hasattr(X_processed, "shape") and i < X_processed.shape[1]:
                feature_val = X_processed[0][i]
            else:
                feature_val = None

            # Keep numeric values numeric; leave categorical values as-is
            # (e.g. "Male") instead of crashing on float() conversion.
            try:
                feature_val = float(feature_val)
            except (TypeError, ValueError):
                pass

            s_val = float(shap_val)
            explanations.append(
                SHAPFeature(
                    feature=str(feature_name),
                    value=feature_val,
                    shap_value=s_val,
                    abs_shap=abs(s_val),
                    direction="increase" if s_val > 0 else "decrease",
                )
            )

        explanations.sort(
            key=lambda x: x.abs_shap,
            reverse=True,
        )

        # ----------------------------------------------
        # Normalize SHAP importance to 0-100 score
        # ----------------------------------------------
        if not explanations:
            return []

        max_importance = explanations[0].abs_shap

        for feature in explanations:
            if max_importance == 0:
                feature.score = 0.0
            else:
                feature.score = round((feature.abs_shap / max_importance) * 100, 1)

        return explanations[:top_k]

    # -----------------------------------------------------

    def explain_dict(
        self,
        X: pd.DataFrame,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Return SHAP explanations as a list of dictionaries.
        """
        features = self.explain(X, top_k)

        return [
            {
                "feature": f.feature,
                "value": f.value,
                "shap_value": f.shap_value,
                "impact": f.direction,
                "importance": f.abs_shap,
                "score": f.score,
            }
            for f in features
        ]