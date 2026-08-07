"""
=========================================================
Digital Wellness AI
Model Evaluator (Validation & Cross-Validation)

Responsibilities
----------------
- Train every candidate model
- Perform Cross-Validation checks for Overfitting detection
- Evaluate on the validation dataset
- Select the best model
    * classification -> mirrors pipeline_CN.ipynb (best by macro F1)
    * regression     -> mirrors pipeline_RN.ipynb (best by R2)
=========================================================
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

from models.preprocessing import build_preprocessor, split_features_target

logger = logging.getLogger(__name__)


def _build_pipeline(preprocessor, estimator, step_name: str) -> Pipeline:
    return Pipeline(steps=[("preprocessor", preprocessor), (step_name, estimator)])


# =========================================================
# Classification
# =========================================================

def evaluate_models_classification(
    models: Dict[str, Any],
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
) -> Tuple[Dict[str, dict], Pipeline, str, LabelEncoder]:
    """Train every classifier, perform CV check, and evaluate on validation."""

    X_train, y_train = split_features_target(train_df, task="classification")
    X_validation, y_validation = split_features_target(validation_df, task="classification")

    # Label Encoding for XGBoost and model compatibility
    label_encoder = LabelEncoder()
    y_train = pd.Series(label_encoder.fit_transform(y_train), index=X_train.index)
    y_validation = pd.Series(label_encoder.transform(y_validation), index=X_validation.index)

    preprocessor = build_preprocessor(X_train)
    class_labels = sorted(y_train.unique())

    # Several classes ("Moderate" especially) dominate the label
    # distribution. LogisticRegression and RandomForest already correct
    # for this via class_weight="balanced", but XGBoost has no such
    # parameter -- left alone it optimizes for the majority class and
    # under-recalls the minority ones. Compute "balanced" per-sample
    # weights once and hand them to any model that doesn't already do
    # its own balancing, so all candidates are being compared on a
    # level, imbalance-aware footing.
    balanced_sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)

    results: Dict[str, dict] = {}
    best_pipeline = None
    best_model_name = None
    best_f1 = -1.0

    # Cross-validation Setup (5-Fold)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    logger.info("=" * 60)
    logger.info("Starting Classification Models Evaluation & Cross-Validation")
    logger.info("=" * 60)

    for model_name, classifier in models.items():
        logger.info("Training and validating %s...", model_name)

        pipeline = _build_pipeline(preprocessor, classifier, "clf")

        # Only apply the manual sample_weight to models that don't already
        # balance classes themselves (e.g. xgboost). Models built with
        # class_weight="balanced" (logistic_regression, random_forest)
        # are left as-is so the two corrections aren't stacked.
        needs_manual_balancing = getattr(classifier, "class_weight", None) != "balanced"
        fit_params = (
            {"clf__sample_weight": balanced_sample_weight}
            if needs_manual_balancing
            else {}
        )

        # -----------------------------------------------------
        # 1. Cross-Validation (Overfitting Test)
        # -----------------------------------------------------
        try:
            cv_scores = cross_validate(
                pipeline, X_train, y_train, cv=cv, scoring=["accuracy", "f1_macro"],
                n_jobs=-1, params=fit_params or None,
            )
            cv_acc_mean = float(np.mean(cv_scores["test_accuracy"]))
            cv_acc_std = float(np.std(cv_scores["test_accuracy"]))
            cv_f1_mean = float(np.mean(cv_scores["test_f1_macro"]))
            cv_f1_std = float(np.std(cv_scores["test_f1_macro"]))
        except Exception as exc:
            logger.warning("Cross-validation failed for %s: %s", model_name, exc)
            cv_acc_mean, cv_acc_std, cv_f1_mean, cv_f1_std = 0.0, 0.0, 0.0, 0.0

        # -----------------------------------------------------
        # 2. Standard Train & Validation Evaluation
        # -----------------------------------------------------
        start_time = time.perf_counter()
        pipeline.fit(X_train, y_train, **fit_params)
        training_time = time.perf_counter() - start_time

        y_pred = pipeline.predict(X_validation)

        # Handle predict_proba safely
        try:
            if hasattr(pipeline, "predict_proba"):
                y_proba = pipeline.predict_proba(X_validation)
                roc_auc = roc_auc_score(y_validation, y_proba, multi_class="ovr", average="macro")
            else:
                roc_auc = 0.0
        except (AttributeError, NotImplementedError, ValueError) as exc:
            logger.warning("Could not calculate ROC-AUC for %s: %s", model_name, exc)
            roc_auc = 0.0

        val_acc = accuracy_score(y_validation, y_pred)
        val_f1 = f1_score(y_validation, y_pred, average="macro", zero_division=0)

        # -----------------------------------------------------
        # 3. Overfitting-aware selection score
        # -----------------------------------------------------
        # A model can look great on one particular validation split while
        # actually being overfit. Blend the validation F1 with the 5-fold
        # CV F1 mean (50/50) and log a warning when the two disagree a lot
        # or when CV variance is high, instead of picking purely on the
        # single validation-split score.
        overfit_gap = val_f1 - cv_f1_mean
        selection_score = 0.5 * val_f1 + 0.5 * cv_f1_mean

        if abs(overfit_gap) > 0.08 or cv_f1_std > 0.05:
            logger.warning(
                "%s may be overfitting: Val F1=%.4f vs 5-Fold CV F1=%.4f (gap=%.4f, cv_std=%.4f)",
                model_name, val_f1, cv_f1_mean, overfit_gap, cv_f1_std,
            )

        metrics = {
            "accuracy": val_acc,
            "precision": precision_score(y_validation, y_pred, average="macro", zero_division=0),
            "recall": recall_score(y_validation, y_pred, average="macro", zero_division=0),
            "f1": val_f1,
            "roc_auc": roc_auc,
            "cv_accuracy_mean": cv_acc_mean,
            "cv_accuracy_std": cv_acc_std,
            "cv_f1_mean": cv_f1_mean,
            "cv_f1_std": cv_f1_std,
            "overfit_gap": overfit_gap,
            "selection_score": selection_score,
            "training_time": training_time,
            "confusion_matrix": confusion_matrix(y_validation, y_pred, labels=class_labels).tolist(),
            "classification_report": classification_report(
                y_validation, y_pred, labels=class_labels, output_dict=True, zero_division=0,
            ),
        }

        results[model_name] = metrics

        logger.info(
            "%s -> Val Acc: %.4f | Val F1: %.4f | 5-Fold CV F1: %.4f (±%.4f) | Selection Score: %.4f",
            model_name, val_acc, val_f1, cv_f1_mean, cv_f1_std, selection_score,
        )

        if selection_score > best_f1:
            best_f1 = selection_score
            best_pipeline = pipeline
            best_model_name = model_name

    logger.info("Best classification model (by Validation F1): %s", best_model_name)

    return results, best_pipeline, best_model_name, label_encoder


# =========================================================
# Regression
# =========================================================

def evaluate_models_regression(
    models: Dict[str, Any],
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
) -> Tuple[Dict[str, dict], Pipeline, str]:
    """Train every regressor and evaluate on validation. Best = highest R2."""

    X_train, y_train = split_features_target(train_df, task="regression")
    X_validation, y_validation = split_features_target(validation_df, task="regression")

    preprocessor = build_preprocessor(X_train)

    results: Dict[str, dict] = {}
    best_pipeline = None
    best_model_name = None
    best_selection_score = float("-inf")

    # Cross-validation Setup (5-Fold) -- same overfitting check the
    # classification evaluator already does. Without this, a model could
    # simply be memorizing the training split (e.g. a very deep tree)
    # and still look great on a single validation split.
    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    logger.info("=" * 60)
    logger.info("Starting Regression Models Evaluation & Cross-Validation")
    logger.info("=" * 60)

    for model_name, regressor in models.items():
        logger.info("Training and validating %s...", model_name)

        pipeline = _build_pipeline(preprocessor, regressor, "reg")

        # -----------------------------------------------------
        # 1. Cross-Validation (Overfitting Test)
        # -----------------------------------------------------
        try:
            cv_scores = cross_validate(
                pipeline, X_train, y_train, cv=cv,
                scoring=["r2", "neg_mean_absolute_error"],
                n_jobs=-1,
            )
            cv_r2_mean = float(np.mean(cv_scores["test_r2"]))
            cv_r2_std = float(np.std(cv_scores["test_r2"]))
            cv_mae_mean = float(np.mean(-cv_scores["test_neg_mean_absolute_error"]))
            cv_mae_std = float(np.std(-cv_scores["test_neg_mean_absolute_error"]))
        except Exception as exc:
            logger.warning("Cross-validation failed for %s: %s", model_name, exc)
            cv_r2_mean, cv_r2_std, cv_mae_mean, cv_mae_std = 0.0, 0.0, 0.0, 0.0

        # -----------------------------------------------------
        # 2. Standard Train & Validation Evaluation
        # -----------------------------------------------------
        start_time = time.perf_counter()
        pipeline.fit(X_train, y_train)
        training_time = time.perf_counter() - start_time

        y_pred = pipeline.predict(X_validation)

        val_r2 = r2_score(y_validation, y_pred)

        # -----------------------------------------------------
        # 3. Overfitting-aware selection score
        # -----------------------------------------------------
        # Same idea as the classifier: don't pick a model purely on a
        # single validation split. Blend validation R2 with the 5-fold
        # CV R2 mean and flag a warning when they disagree a lot or CV
        # variance is high.
        overfit_gap = val_r2 - cv_r2_mean
        selection_score = 0.5 * val_r2 + 0.5 * cv_r2_mean

        if abs(overfit_gap) > 0.08 or cv_r2_std > 0.05:
            logger.warning(
                "%s may be overfitting: Val R2=%.4f vs 5-Fold CV R2=%.4f (gap=%.4f, cv_std=%.4f)",
                model_name, val_r2, cv_r2_mean, overfit_gap, cv_r2_std,
            )

        metrics = {
            "MAE": mean_absolute_error(y_validation, y_pred),
            "RMSE": mean_squared_error(y_validation, y_pred) ** 0.5,
            "R2": val_r2,
            "cv_r2_mean": cv_r2_mean,
            "cv_r2_std": cv_r2_std,
            "cv_mae_mean": cv_mae_mean,
            "cv_mae_std": cv_mae_std,
            "overfit_gap": overfit_gap,
            "selection_score": selection_score,
            "training_time": training_time,
        }

        results[model_name] = metrics

        logger.info(
            "%s | MAE=%.4f | RMSE=%.4f | Val R2=%.4f | 5-Fold CV R2: %.4f (±%.4f) | Selection Score: %.4f",
            model_name, metrics["MAE"], metrics["RMSE"], val_r2, cv_r2_mean, cv_r2_std, selection_score,
        )

        if selection_score > best_selection_score:
            best_selection_score = selection_score
            best_pipeline = pipeline
            best_model_name = model_name

    logger.info("Best regression model (by overfitting-aware selection score): %s", best_model_name)

    return results, best_pipeline, best_model_name


# =========================================================
# Dispatcher
# =========================================================

def evaluate_models(
    task: str,
    models: Dict[str, Any],
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
) -> Union[
    Tuple[Dict[str, dict], Pipeline, str, LabelEncoder],
    Tuple[Dict[str, dict], Pipeline, str]
]:

    if task == "classification":
        return evaluate_models_classification(models, train_df, validation_df)

    if task == "regression":
        return evaluate_models_regression(models, train_df, validation_df)

    raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")