"""
=========================================================
Digital Wellness AI
Test Evaluator

Responsibilities
----------------
- Evaluate the selected model on the unseen test dataset
- Calculate final evaluation metrics
=========================================================
"""

from __future__ import annotations

import logging
from typing import Any, Dict

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
from sklearn.preprocessing import LabelEncoder

from models.preprocessing import split_features_target

logger = logging.getLogger(__name__)


# =========================================================
# Classification
# =========================================================

def evaluate_on_test_classification(
    model_pipeline,
    test_df: pd.DataFrame,
    label_encoder: LabelEncoder | None = None,
) -> Dict[str, Any]:
    X_test, y_test = split_features_target(test_df, task="classification")

    if label_encoder is None:
        logger.warning(
            "No training label_encoder supplied; fitting a new one on the "
            "test set. This can misalign labels if classes differ from training."
        )
        label_encoder = LabelEncoder()
        y_test = pd.Series(label_encoder.fit_transform(y_test), index=X_test.index)
    else:
        y_test = pd.Series(label_encoder.transform(y_test), index=X_test.index)

    class_labels = sorted(y_test.unique())

    y_pred = model_pipeline.predict(X_test)

    if hasattr(model_pipeline, "predict_proba"):
        y_proba = model_pipeline.predict_proba(X_test)
        roc_auc = roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
    else:
        roc_auc = 0.0

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, average="macro", zero_division=0),
        "recall": recall_score(y_test, y_pred, average="macro", zero_division=0),
        "f1": f1_score(y_test, y_pred, average="macro", zero_division=0),
        "roc_auc": roc_auc,
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=class_labels).tolist(),
        "classification_report": classification_report(
            y_test, y_pred, labels=class_labels, output_dict=True, zero_division=0,
        ),
    }

    logger.info(
        "Test Evaluation (classification) | Accuracy=%.4f | F1(macro)=%.4f",
        metrics["accuracy"], metrics["f1"],
    )

    return metrics


# =========================================================
# Regression
# =========================================================

def evaluate_on_test_regression(model_pipeline, test_df: pd.DataFrame) -> Dict[str, Any]:
    X_test, y_test = split_features_target(test_df, task="regression")

    y_pred = model_pipeline.predict(X_test)

    metrics = {
        "MAE": mean_absolute_error(y_test, y_pred),
        "RMSE": mean_squared_error(y_test, y_pred) ** 0.5,
        "R2": r2_score(y_test, y_pred),
    }

    logger.info(
        "Test Evaluation (regression) | MAE=%.4f | RMSE=%.4f | R2=%.4f",
        metrics["MAE"], metrics["RMSE"], metrics["R2"],
    )

    return metrics


# =========================================================
# Dispatcher
# =========================================================

def evaluate_on_test(
    task: str,
    model_pipeline,
    test_df: pd.DataFrame,
    label_encoder: LabelEncoder | None = None,
) -> Dict[str, Any]:
    if task == "classification":
        return evaluate_on_test_classification(model_pipeline, test_df, label_encoder=label_encoder)

    if task == "regression":
        return evaluate_on_test_regression(model_pipeline, test_df)

    raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")


# =========================================================
# Pretty Print
# =========================================================

def print_test_results(task: str, metrics: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print(f"FINAL TEST RESULTS ({task})")
    print("=" * 60)

    if task == "classification":
        print(f"Accuracy : {metrics['accuracy']:.4f}")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall   : {metrics['recall']:.4f}")
        print(f"F1 Score : {metrics['f1']:.4f}")
        print(f"ROC AUC  : {metrics['roc_auc']:.4f}")
        print("\nConfusion Matrix")
        for row in metrics["confusion_matrix"]:
            print(row)
    else:
        print(f"MAE : {metrics['MAE']:.4f}")
        print(f"RMSE: {metrics['RMSE']:.4f}")
        print(f"R2  : {metrics['R2']:.4f}")