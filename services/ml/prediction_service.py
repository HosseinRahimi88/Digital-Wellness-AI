"""
Prediction Service
------------------
Runs the complete machine learning inference pipeline.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

import numpy as np
import pandas as pd

from models.model_manager import ModelManager
from models.schemas import PredictionResult

from services.ml.validation_service import ValidationService

logger = logging.getLogger(__name__)


# The categorical column set is derived from FEATURE_SCHEMA, which never
# changes at runtime. Rebuilding it on every prediction cost a full pass
# over the schema per call; the demo makes 103 calls in one request.
_CATEGORICAL_COLUMNS: frozenset[str] | None = None


def _categorical_columns() -> frozenset[str]:
    global _CATEGORICAL_COLUMNS
    if _CATEGORICAL_COLUMNS is None:
        from core.feature_schema import FEATURE_SCHEMA

        _CATEGORICAL_COLUMNS = frozenset(
            name for name, feat in FEATURE_SCHEMA.items() if feat.choices is not None
        )
    return _CATEGORICAL_COLUMNS


def _coerce_float(value: Any) -> float:
    """`pd.to_numeric(errors="coerce")` for a single scalar.

    The model input is always exactly one row, so routing each column
    through pandas built a Series per column per prediction - roughly
    97,000 Series objects for one 23-day demo. This does the same
    coercion in plain Python: anything that will not read as a number
    becomes NaN, exactly as `errors="coerce"` does.
    """
    if value is None:
        return math.nan
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


# ==========================================================
# Prediction Service
# ==========================================================


class PredictionService:
    """
    Main inference pipeline.
    """

    CLASS_MAPPING = {
        0: "At Risk",
        1: "Healthy",
        2: "Moderate",
        "0": "At Risk",
        "1": "Healthy",
        "2": "Moderate",
        "at_risk": "At Risk",
        "healthy": "Healthy",
        "moderate": "Moderate",
    }

    def __init__(self, model_manager: ModelManager | None = None) -> None:
        """
        `model_manager` defaults to the process-wide singleton
        (`ModelManager.instance()`), so every `PredictionService()` in
        the process - across every Streamlit page, every thread, every
        concurrent request - shares the exact same loaded models and
        SHAP explainer instead of re-loading them from disk. Accepting
        it as a parameter (rather than hard-coding the singleton lookup)
        keeps this class trivially testable with a fake/lightweight
        manager.
        """
        logger.info("Initializing PredictionService...")

        self.validator = ValidationService()

        self._model_manager = model_manager or ModelManager.instance()

        self.classification_registry = self._model_manager.classification_registry
        self.classification_model = self._model_manager.classification_model

        self.regression_registry = self._model_manager.regression_registry
        self.regression_model = self._model_manager.regression_model

        self.feature_columns = self._model_manager.classification_feature_columns
        self.classification_feature_columns = self._model_manager.classification_feature_columns
        self.regression_feature_columns = self._model_manager.regression_feature_columns
        self.classes = self._model_manager.classes

        self.shap_service = self._model_manager.shap_service
        self.uncertainty_service = self._model_manager.uncertainty_service
        self.persona_service = self._model_manager.persona_service

        logger.info("PredictionService initialized successfully (using shared ModelManager).")

    # ======================================================
    # Helpers
    # ======================================================

    def _prepare_dataframe(
        self,
        user_data: dict[str, Any],
        feature_columns: list[str] | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> pd.DataFrame:
        """
        Convert validated dictionary into dataframe and ensure exact column types.

        `user_data` is expected to already contain every key in
        `feature_columns` (ValidationService enforces this against
        core.feature_schema.FEATURE_SCHEMA, which is a superset of both
        the classification and regression feature lists). This function
        no longer silently overwrites missing/unmapped fields with fixed
        constants (that was the root cause of every prediction collapsing
        onto the same class) - it only fills genuine gaps as a last-resort
        safety net and logs a warning so the issue is visible instead of
        silent.

        Classification and regression use slightly different feature
        subsets since Feature Selection (see models/preprocessing.py):
        regression keeps `screen_ewma_baseline` while classification does
        not. `feature_columns` lets each task reindex to its own list
        instead of assuming a single shared column set.
        """
        if feature_columns is None:
            feature_columns = self.feature_columns

        # Per-user trend columns, built by the same function training used
        # (utils.trend_features) so the two can never drift apart. Only
        # computed when the model actually asks for them, so the
        # regression task - which has no trend features - is untouched.
        from utils.trend_features import build_trend_features, trend_feature_names

        trend_cols = set(trend_feature_names())
        row = dict(user_data)
        if trend_cols.intersection(feature_columns):
            row.update(build_trend_features(user_data, history or []))

        # Everything below happens on a single row, so it is done on the
        # plain dict and the DataFrame is built once at the end. The old
        # version built the frame first and then touched it column by
        # column (a `.apply` across ~87 numeric columns, then a per-column
        # `.isna()` scan), which is where a 23-day demo spent most of its
        # time. Column selection, coercion and the missing-value rules are
        # unchanged - only where they run moved.
        categorical_cols = _categorical_columns()

        data: dict[str, Any] = {}
        # A missing trend column means "this user has no history yet", which
        # the model was trained to read as NaN. Zero-filling it would be a
        # positive claim that nothing changed - the same silent-default bug
        # that previously collapsed every prediction onto one class - so
        # these are excluded from the fallback below and left missing.
        missing: list[str] = []

        for col in feature_columns:
            value = row.get(col)

            if col in categorical_cols:
                # A categorical value is passed through untouched, including
                # an explicit None. That is not fussiness: the fitted
                # OneHotEncoder scores a None-valued column differently from
                # a NaN-valued one, so collapsing the two here would quietly
                # change predictions for any caller that sends nulls.
                # An absent key becomes NaN, which is what the old
                # `reindex` produced.
                if col in row:
                    data[col] = value
                    absent = value is None or (
                        isinstance(value, float) and math.isnan(value)
                    )
                else:
                    data[col] = np.nan
                    absent = True
                if absent and col not in trend_cols:
                    missing.append(col)
                continue

            number = _coerce_float(value)
            if math.isnan(number) and col not in trend_cols:
                missing.append(col)
                number = 0.0
            data[col] = number

        if missing:
            logger.warning(
                "Prediction input is missing values for: %s. "
                "Falling back to neutral defaults for these columns only; "
                "double-check the form/FEATURE_SCHEMA mapping.",
                missing,
            )

        X = pd.DataFrame([data], columns=list(feature_columns))

        # `_coerce_float` already returned Python floats, so pandas infers
        # float64 for every numeric column and there is normally nothing to
        # cast. Assigning the whole numeric block unconditionally is not
        # free - pandas walks it column by column internally - so only the
        # columns that actually came out wrong are touched. Categorical
        # columns keep whatever dtype pandas inferred, as before, because
        # the fitted encoder distinguishes them.
        dtypes = X.dtypes
        wrong = [
            c for c in feature_columns
            if c not in categorical_cols and dtypes[c] != np.float64
        ]
        if wrong:
            X[wrong] = X[wrong].astype(np.float64)

        return X

    @staticmethod
    def _compute_confidence(
        probabilities: np.ndarray,
    ) -> float:
        """
        Return highest probability.
        """
        return float(np.max(probabilities))

    def _predict_classification(
        self,
        X: pd.DataFrame,
    ):
        """
        Run classification model with proper label string resolution.
        """
        probabilities = self.classification_model.predict_proba(X)[0]

        # Resolve raw model classes to string labels
        if hasattr(self.classification_model, "classes_") and len(self.classification_model.classes_) > 0:
            raw_classes = self.classification_model.classes_
        elif len(self.classes) > 0:
            raw_classes = self.classes
        else:
            raw_classes = list(range(len(probabilities)))

        # Derive the predicted class from `probabilities` (argmax) instead
        # of also calling `.predict(X)` separately: for this pipeline's
        # classifier, `.predict()` internally re-runs the same forward
        # pass through the trees and then argmaxes its own decision
        # function - which is mathematically identical to argmaxing the
        # probabilities we already computed (softmax preserves ranking).
        # Calling both meant every single prediction request pushed the
        # same input through the model twice for no behavioral difference
        # - verified byte-for-byte identical against `.predict()` across
        # 1000 validation rows before making this change.
        raw_prediction = raw_classes[int(np.argmax(probabilities))]
        confidence = self._compute_confidence(probabilities)

        probability_dict = {}
        for cls, prob in zip(raw_classes, probabilities, strict=True):
            label_name = self.CLASS_MAPPING.get(cls, str(cls))
            probability_dict[label_name] = float(prob)

        final_prediction = self.CLASS_MAPPING.get(raw_prediction, str(raw_prediction))

        return (
            final_prediction,
            probability_dict,
            confidence,
        )

    # ======================================================
    # Regression
    # ======================================================

    def _predict_regression(
        self,
        X: pd.DataFrame,
    ) -> float:
        """
        Predict digital wellness score using regression model.
        """
        score = float(self.regression_model.predict(X)[0])
        score = max(0.0, min(100.0, score))
        return round(score, 2)

    # ======================================================
    # SHAP
    # ======================================================

    def _generate_shap(
        self,
        X: pd.DataFrame,
    ):
        """
        Generate SHAP explanations safely.
        """
        try:
            explanations = self.shap_service.explain(
                X,
                top_k=5,
            )
            logger.info(
                "Generated %d SHAP features.",
                len(explanations),
            )
            return explanations
        except Exception:
            logger.exception("SHAP explanation failed.")
            return []

    # ======================================================
    # Prediction Result
    # ======================================================

    def _build_result(
        self,
        prediction: str,
        confidence: float,
        probabilities: dict[str, float],
        regression_score: float,
        shap_features: Any,
        prediction_time_ms: float,
        uncertainty: Any = None,
    ) -> PredictionResult:
        """
        Create PredictionResult object.
        """
        return PredictionResult(
            prediction=str(prediction),
            confidence=confidence,
            probabilities=probabilities,
            regression_score=regression_score,
            shap_features=shap_features,
            model_name=self.classification_registry.model_name,
            prediction_time_ms=round(prediction_time_ms, 2),
            uncertainty=uncertainty,
        )

    def _estimate_uncertainty(
        self,
        probabilities: dict[str, float],
        regression_score: float,
    ):
        """
        Compute split-conformal uncertainty for this prediction. Never
        allowed to fail the whole prediction (robustness requirement) -
        any internal error degrades to an "unavailable" UncertaintyResult
        rather than propagating.
        """
        try:
            return self.uncertainty_service.estimate(probabilities, regression_score)
        except Exception:
            logger.exception("Uncertainty estimation failed; continuing without it.")
            from services.ml.uncertainty_service import UncertaintyResult
            return UncertaintyResult(available=False, explanation="Uncertainty estimation failed.")

    # ======================================================
    # Public API
    # ======================================================

    def predict(
        self,
        user_data: dict[str, Any],
        compute_shap: bool = True,
        history: list[dict[str, Any]] | None = None,
    ) -> PredictionResult:
        """
        Execute complete prediction pipeline.

        `compute_shap` defaults to True (unchanged behavior for the
        primary "real submission" call site, where the SHAP breakdown
        feeds RecommendationService and the explanation UI). Pass False
        for throwaway/comparison predictions - callers that only read
        `.prediction` / `.regression_score` / `.confidence` /
        `.uncertainty` and never touch `.shap_features` - to skip the
        explanation pass entirely.
        This matters because `predict()` is also the exact function
        called once per candidate in AdvancedWhatIfService.sweep_field()
        (9 points per sweep), FuturePathService (once per path), and
        ParallelTwinService (once per twin) - none of which read
        `.shap_features` off the result (verified: grepped for
        `.shap_features` usage in all three call sites; zero hits).
        Every one of those calls was computing and discarding a full
        SHAP explanation. See services/insight/future_path_service.py,
        services/insight/advanced_whatif_service.py, and
        services/insight/parallel_twin_service.py for the updated call sites.
        """
        start_time = time.perf_counter()

        try:
            logger.info("Starting prediction...")

            validation = self.validator.validate(user_data)
            if not validation.is_valid:
                error_msg = "; ".join([f"{k}: {v}" for k, v in validation.errors.items()])
                raise ValueError(f"Validation failed: {error_msg}")

            X_clf = self._prepare_dataframe(
                validation.cleaned_data,
                self.classification_feature_columns,
                history=history,
            )
            X_reg = self._prepare_dataframe(
                validation.cleaned_data,
                self.regression_feature_columns,
            )
            logger.info(
                "Input dataframe shapes: classification=%s, regression=%s",
                X_clf.shape, X_reg.shape,
            )

            (
                prediction,
                probabilities,
                confidence,
            ) = self._predict_classification(X_clf)
            logger.info("Classification completed.")

            regression_score = self._predict_regression(X_reg)
            logger.info("Regression score: %.4f", regression_score)

            shap_features = self._generate_shap(X_reg) if compute_shap else []

            uncertainty = self._estimate_uncertainty(probabilities, regression_score)
            logger.info("Uncertainty estimated: %s", uncertainty.uncertainty_label)

            prediction_time_ms = (time.perf_counter() - start_time) * 1000

            result = self._build_result(
                prediction=prediction,
                confidence=confidence,
                probabilities=probabilities,
                regression_score=regression_score,
                shap_features=shap_features,
                prediction_time_ms=prediction_time_ms,
                uncertainty=uncertainty,
            )

            logger.info("Prediction completed successfully.")
            return result

        except Exception:
            logger.exception("Prediction failed.")
            raise