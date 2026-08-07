"""
=========================================================
Digital Wellness AI
Classification Training Pipeline
=========================================================
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.data_loader import load_datasets
from models.preprocessing import TARGET_COLUMNS, get_feature_columns
from models.model_factory import get_models
from models.evaluator import evaluate_models
from models.test_evaluator import evaluate_on_test, print_test_results
from models.model_saver import save_all
from models.metrics_logger import save_metrics

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TASK = "classification"


def main():
    logger.info("=" * 60)
    logger.info("Digital Wellness AI - Classification Training Pipeline")
    logger.info("=" * 60)

    train_df, validation_df, test_df = load_datasets()

    logger.info("Train rows      : %d", len(train_df))
    logger.info("Validation rows : %d", len(validation_df))
    logger.info("Test rows       : %d", len(test_df))
    
    feature_columns = get_feature_columns(train_df, task=TASK)
    logger.info("Feature count   : %d", len(feature_columns))

    models = get_models(task=TASK)
    logger.info("%d candidate models loaded.", len(models))

    validation_results, best_pipeline, best_model_name, label_encoder = evaluate_models(
        TASK, models, train_df, validation_df,
    )
    logger.info("Best model selected: %s", best_model_name)

    test_metrics = evaluate_on_test(TASK, best_pipeline, test_df, label_encoder=label_encoder)
    print_test_results(TASK, test_metrics)

    target_col = TARGET_COLUMNS[TASK]
    
    if label_encoder is not None and hasattr(label_encoder, "classes_"):
        unique_classes = [str(c) for c in label_encoder.classes_]
    else:
        unique_classes = [str(c) for c in train_df[target_col].unique().tolist()]

    save_all(
        task=TASK,
        pipeline=best_pipeline,
        feature_columns=feature_columns,
        model_name=best_model_name,
        target_column=target_col,
        classes=unique_classes,
    )

    save_metrics(
        task=TASK,
        validation_results=validation_results,
        test_metrics=test_metrics,
        best_model_name=best_model_name,
    )

    logger.info("=" * 60)
    logger.info("Classification Training Completed Successfully")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()