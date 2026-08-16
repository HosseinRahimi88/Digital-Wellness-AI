"""
=========================================================
Digital Wellness AI
Seven-day-ahead score regressor (Output 2)
=========================================================

Evaluates two ways of predicting the augmented seven-day-ahead target
built by models/augment_future_score.py, and records which one wins.

  single-stage   One HistGradientBoostingRegressor on all 185 features
                 (the same set the shipped regressor uses, which already
                 excludes both future_* columns as leakage).
  two-stage      The existing seven-day CLASSIFIER picks the band, and
                 the user's own within-band position today picks the
                 place inside it.

The single-stage model was built first and lost - decisively, and to a
baseline that does nothing at all. Its numbers are kept below rather
than deleted, because the comparison is the finding: the target has a
discontinuity at each band boundary, and a smooth regressor spends its
capacity averaging across a step it cannot represent. The classifier
already solves that part at 90% accuracy, so handing it that job and
keeping only the within-band position for the arithmetic is what turns
a losing model into a winning one.

The acceptance test
-------------------
A high R-squared here would prove nothing on its own. The augmented
target correlates 0.85 with today's score, so a model that simply
echoed today's score would already look good. The number that decides
whether this model is worth shipping is therefore not its R-squared but
how much it BEATS THAT BASELINE:

    baseline: predict today's score, unchanged
    model:    predict the seven-day-ahead target

Both are scored against the same target on the same validation split.
If the model does not clearly beat the baseline it has learned to
restate today, and the honest thing is to say so and ship Output 1
instead. That comparison is computed below and written into the metrics
artifact so it cannot be quietly dropped from the story.

Run: python3 -m models.train_future_regression
     (requires models/augment_future_score.py to have run first)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# The one definition of the project root - see core/paths.py. Computed by
# directory depth here until it wasn't, twice; a path relative to a file's
# own position is correct until something moves and silently wrong after,
# because a Path that does not exist is still a perfectly good Path.
from core import paths

if str(paths.PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(paths.PROJECT_ROOT))

from models.data_loader import (  # noqa: E402
    SCREEN_LOAD_COLUMN, _add_trend_features, reconstruct_derived_features,
)
from models.preprocessing import build_preprocessor, get_feature_columns  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TARGET_COLUMN = "future_health_score_7d"
TODAY_COLUMN = "health_score_0_100"

MODEL_PATH = paths.PROJECT_ROOT / "artifacts" / "future_score_regressor.pkl"
FEATURES_PATH = paths.PROJECT_ROOT / "artifacts" / "feature_columns_future_regression.json"
METRICS_PATH = paths.PROJECT_ROOT / "artifacts" / "metrics_future_regression.json"
INFO_PATH = paths.PROJECT_ROOT / "artifacts" / "model_info_future_regression.json"

# How much better than "just predict today" the model has to be for this
# output to be worth shipping. 15% of the baseline's error is a real
# margin rather than a rounding difference.
MIN_MAE_IMPROVEMENT_PCT = 15.0


def _load(split: str) -> pd.DataFrame:
    path = paths.PROJECT_ROOT / "data" / f"{split}_augmented.csv"
    if not path.exists():
        raise SystemExit(
            f"{path} is missing. Run models/augment_future_score.py first."
        )
    frame = pd.read_csv(path)
    frame = reconstruct_derived_features(frame)
    # The per-user trend columns (_d1, _r3, _r7, _sl7, _sl14, _vol7,
    # _dev). Without these the model sees 52 same-day features instead
    # of 185, and the first training run proved what that costs: it
    # scored WORSE than predicting today, because a single day carries
    # almost nothing about next week. Rolling means, slopes and
    # volatility are where the forward-looking signal actually lives.
    return _add_trend_features(frame, split)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    return {
        "R2": round(float(r2_score(y_true, y_pred)), 4),
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
    }


def _two_stage_metrics(frame: pd.DataFrame) -> dict:
    """Classifier picks the band, today's within-band rank picks the spot.

    Uses the same shipped classifier and the same stored quantiles the
    live app uses, so this measurement is of the thing that actually
    runs - not of a re-implementation that happens to agree.
    """
    from services.insight.future_score_service import FutureScoreService
    from models.model_manager import ModelManager

    manager = ModelManager.instance()
    registry = manager.classification_registry
    features = json.load(open(paths.PROJECT_ROOT / "artifacts" / "feature_columns.json", encoding="utf-8"))
    labels = json.load(open(paths.PROJECT_ROOT / "artifacts" / "model_info.json", encoding="utf-8"))["classes"]

    proba = registry.model.predict_proba(frame[features])
    raw_classes = list(registry.model.classes_)
    classes = [labels[int(c)] if isinstance(c, (int, np.integer)) else str(c) for c in raw_classes]

    predictions = []
    for row_index in range(len(frame)):
        probabilities = {classes[i]: float(proba[row_index, i]) for i in range(len(classes))}
        # screen_load_today is not optional here. The estimator reads
        # today's position on the WELLBEING axis and recovers it from the
        # score using this; without it every call falls back to a
        # wellbeing-axis answer and gets scored against a combined-score
        # target, which measured R2=0.137 / MAE=8.25 - a units mismatch
        # wearing the costume of a model that had stopped working.
        result = FutureScoreService.estimate(
            probabilities, today_score=float(frame["health_score_0_100"].iloc[row_index]),
            screen_load_today=float(frame[SCREEN_LOAD_COLUMN].iloc[row_index]),
            mode="augmented",
        )
        predictions.append(result.score if result.available else np.nan)

    predictions = np.asarray(predictions, dtype=float)
    usable = ~np.isnan(predictions)
    return _metrics(frame[TARGET_COLUMN].to_numpy()[usable], predictions[usable])


def main() -> None:
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import Pipeline
    import joblib

    train = _load("train")
    validation = _load("validation")
    test = _load("test")

    features = get_feature_columns(train, task="regression")
    # Belt and braces: the feature list is derived, but a leak here would
    # be invisible in every metric and fatal to the claim.
    for banned in (TARGET_COLUMN, TODAY_COLUMN, "future_health_class_7d"):
        assert banned not in features, f"{banned} leaked into the feature set"
    logger.info("Features: %d", len(features))

    X_train, y_train = train[features], train[TARGET_COLUMN]
    X_val, y_val = validation[features], validation[TARGET_COLUMN]
    X_test, y_test = test[features], test[TARGET_COLUMN]

    # The same ColumnTransformer the shipped regressor uses - numeric
    # scaled, categorical one-hot encoded with handle_unknown="ignore".
    # Reused rather than rebuilt so this model and that one can never
    # disagree about how a category is represented.
    model = Pipeline(steps=[
        ("preprocessor", build_preprocessor(X_train)),
        ("regressor", HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.06, max_depth=None,
            min_samples_leaf=40, l2_regularization=1.0,
            early_stopping=True, validation_fraction=0.12, n_iter_no_change=25,
            random_state=42,
        )),
    ])
    started = time.perf_counter()
    model.fit(X_train, y_train)
    training_seconds = round(time.perf_counter() - started, 1)
    logger.info("Trained in %.1fs", training_seconds)

    val_metrics = _metrics(y_val.to_numpy(), model.predict(X_val))
    test_metrics = _metrics(y_test.to_numpy(), model.predict(X_test))

    # The baseline that decides whether any of this was worth doing.
    baseline_val = _metrics(y_val.to_numpy(), validation[TODAY_COLUMN].to_numpy())
    improvement_pct = round(
        (baseline_val["MAE"] - val_metrics["MAE"]) / max(baseline_val["MAE"], 1e-9) * 100, 2
    )
    beats_baseline = improvement_pct >= MIN_MAE_IMPROVEMENT_PCT

    # ---- the two-stage estimator -------------------------------------
    from services.insight.future_score_service import FutureScoreService
    two_stage_val = _two_stage_metrics(validation)
    two_stage_test = _two_stage_metrics(test)
    two_stage_improvement = round(
        (baseline_val["MAE"] - two_stage_val["MAE"]) / max(baseline_val["MAE"], 1e-9) * 100, 2
    )

    cv = cross_val_score(model, X_train, y_train, cv=3, scoring="r2", n_jobs=1)
    logger.info("single-stage  R2=%.4f MAE=%.4f  (%.2f%% vs baseline)",
                val_metrics["R2"], val_metrics["MAE"], improvement_pct)
    logger.info("two-stage     R2=%.4f MAE=%.4f  (%.2f%% vs baseline)",
                two_stage_val["R2"], two_stage_val["MAE"], two_stage_improvement)
    logger.info("baseline      R2=%.4f MAE=%.4f  (predict today, unchanged)",
                baseline_val["R2"], baseline_val["MAE"])

    payload = {
        "task": "future_regression",
        "target_column": TARGET_COLUMN,
        "horizon": "7_days_ahead",
        "model_name": "hist_gradient_boosting_regressor",
        "training_seconds": training_seconds,
        "validation": val_metrics,
        "test": test_metrics,
        "cv_r2_mean": round(float(cv.mean()), 4),
        "cv_r2_std": round(float(cv.std()), 4),
        "baseline_predict_today": {
            **baseline_val,
            "description": (
                "Predicting today's score unchanged, scored against the same "
                "seven-day-ahead target on the same validation split."
            ),
        },
        "mae_improvement_over_baseline_pct": improvement_pct,
        "beats_baseline": bool(beats_baseline),
        "two_stage": {
            "description": (
                "The seven-day classifier picks the band; the user's own "
                "within-band position today picks the place inside it. No new "
                "model is trained - this reuses the shipped classifier."
            ),
            "validation": two_stage_val,
            "test": two_stage_test,
            "mae_improvement_over_baseline_pct": two_stage_improvement,
            "beats_baseline": bool(two_stage_improvement >= MIN_MAE_IMPROVEMENT_PCT),
        },
        "shipped_estimator": (
            "two_stage" if two_stage_improvement >= improvement_pct else "single_stage"
        ),
        "minimum_improvement_required_pct": MIN_MAE_IMPROVEMENT_PCT,
        "honest_description": (
            "R-squared here is measured against a CONSTRUCTED target - the "
            "real seven-day-ahead class label expanded into a score by "
            "within-band rank persistence (see "
            "models/augment_future_score.py). It is not a measurement of how "
            "accurately anyone's real score seven days from now is predicted, "
            "and the training data is synthetic to begin with."
        ),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    FEATURES_PATH.write_text(json.dumps(features, indent=2), encoding="utf-8")
    METRICS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    INFO_PATH.write_text(json.dumps({
        "project": "Digital Wellness AI",
        "task": "future_regression",
        "target_column": TARGET_COLUMN,
        "horizon": "7_days_ahead",
        "model_name": "hist_gradient_boosting_regressor",
        "number_of_features": len(features),
        "target_is_augmented": True,
    }, indent=2), encoding="utf-8")

    logger.info("Saved model -> %s", MODEL_PATH)
    best = max(improvement_pct, two_stage_improvement)
    if best >= MIN_MAE_IMPROVEMENT_PCT:
        logger.info(
            "VERDICT: shippable. Best estimator beats the predict-today "
            "baseline by %.2f%% MAE (%s).",
            best, "two-stage" if two_stage_improvement >= improvement_pct else "single-stage",
        )
    else:
        logger.warning(
            "VERDICT: nothing beats predicting today by the required %.1f%%. "
            "Ship Output 1 (class only) instead.", MIN_MAE_IMPROVEMENT_PCT,
        )


if __name__ == "__main__":
    main()
