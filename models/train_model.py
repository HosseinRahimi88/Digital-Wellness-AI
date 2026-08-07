"""
=========================================================
Digital Wellness AI
Training Entry Point (Main Dispatcher & Orchestrator)

Usage
-----
    python -m models.train_model                     # Trains BOTH Classification & Regression
    python -m models.train_model --task classification # Trains Classification only
    python -m models.train_model --task regression     # Trains Regression only
=========================================================
"""

from __future__ import annotations

import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Train the Digital Wellness AI models.")
    parser.add_argument(
        "--task",
        choices=["all", "classification", "regression"],
        default="all",
        help="Which pipeline to train (default: all).",
    )
    args = parser.parse_args()

    if args.task in ["all", "classification"]:
        logger.info("\n>>> STARTING CLASSIFICATION PIPELINE <<<\n")
        from models.train_classification import main as run_classification
        run_classification()

    if args.task in ["all", "regression"]:
        logger.info("\n>>> STARTING REGRESSION PIPELINE <<<\n")
        from models.train_regression import main as run_regression
        run_regression()


if __name__ == "__main__":
    main()