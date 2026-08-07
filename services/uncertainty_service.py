"""
Uncertainty Service
--------------------
Group C Feature 55 - Prediction Uncertainty.

Provides statistically-grounded uncertainty quantification for both the
classification and regression outputs of PredictionService, using
**split conformal prediction** (Vovk et al.; Lei et al. 2018 "Distribution-
Free Predictive Inference for Regression").

Why split conformal (and not raw softmax confidence or bootstrap ensembles)
-----------------------------------------------------------------------------
- The deployed models are `HistGradientBoostingClassifier` /
  `HistGradientBoostingRegressor`. Neither exposes a bag of independent
  estimators the way `RandomForest` does (no `.estimators_` list of fully
  independent trees fit on bootstrap samples), so tree-variance-based
  uncertainty (the usual RF trick) is not a sound option here without
  retraining a different model family - which the brief says to avoid
  unless genuinely required.
- Training an ensemble of bootstrap-resampled models purely for
  uncertainty would multiply training cost and drift from the production
  model's actual predictions (the uncertainty would describe a different
  model than the one making the prediction).
- Split conformal prediction instead wraps the *existing, unmodified*
  trained model. It calibrates a single correction quantity (a residual
  quantile for regression, a nonconformity quantile for classification)
  on a held-out split the model never trained on, and gets a
  **distribution-free, finite-sample marginal coverage guarantee**
  (e.g. "the true value falls in this interval at least 90% of the time,
  provably, with no assumption on the model or the data distribution").
  This is the strongest calibration guarantee available without
  retraining, which is why it was chosen over ad-hoc heuristics.

No leakage
-----------
Calibration is computed once against `data/validation.csv` - a split the
model has never been trained on and that is disjoint from `data/test.csv`
(which remains untouched, preserving an honest held-out set for any
future evaluation). Calibration never touches `data/train.csv`.

Caching
-------
Calibration (one pass over ~the validation set) is expensive to redo on
every process start for no benefit, since it only changes when the
underlying models change. The result is cached to
`artifacts/uncertainty_calibration.json`, keyed by the `saved_at`
timestamps of the current classification/regression models (from
`artifacts/model_info*.json`) - if either model is retrained, the cache
key changes and recalibration happens automatically instead of silently
serving a stale calibration against a new model.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
CALIBRATION_CACHE_FILE = ARTIFACTS_DIR / "uncertainty_calibration.json"

# Two-sided marginal coverage target for both the regression interval and
# the classification prediction set. 90% is the conventional default for
# conformal prediction (matches the standard used in the reference
# literature); exposed as a constant rather than hard-coded inline so a
# future page can offer 80%/95% without touching the calibration math.
DEFAULT_ALPHA = 0.10  # => 90% target coverage


# ==========================================================
# Result object
# ==========================================================

@dataclass(slots=True)
class UncertaintyResult:
    """
    Output of UncertaintyService.estimate().

    All fields degrade to `None`/empty rather than raising if calibration
    could not be computed (e.g. validation.csv unavailable) - callers
    (PredictionService, UI) must be able to render a result with no
    uncertainty info rather than crash.
    """

    available: bool = False

    # --- Regression: split conformal prediction interval ---
    regression_lower: Optional[float] = None
    regression_upper: Optional[float] = None
    regression_interval_width: Optional[float] = None
    coverage_target: float = 1.0 - DEFAULT_ALPHA

    # --- Classification: split conformal prediction set ---
    # The set of classes that cannot be statistically ruled out at the
    # target coverage level - NOT just "top-1 vs rest". A set size of 1
    # means the model is confidently and correctly calibrated-certain;
    # a set size of 2-3 means the case is genuinely ambiguous.
    classification_set: list[str] = field(default_factory=list)
    classification_set_size: int = 0

    # --- Distribution-shape uncertainty (always computable, no calibration needed) ---
    entropy: Optional[float] = None
    entropy_normalized: Optional[float] = None  # 0 (certain) - 1 (maximally uncertain)

    # --- Human-facing summary ---
    uncertainty_label: str = "Unknown"
    explanation: str = ""

    calibration_sample_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "regression_lower": self.regression_lower,
            "regression_upper": self.regression_upper,
            "regression_interval_width": self.regression_interval_width,
            "coverage_target": self.coverage_target,
            "classification_set": self.classification_set,
            "classification_set_size": self.classification_set_size,
            "entropy": self.entropy,
            "entropy_normalized": self.entropy_normalized,
            "uncertainty_label": self.uncertainty_label,
            "explanation": self.explanation,
            "calibration_sample_size": self.calibration_sample_size,
        }


# ==========================================================
# Uncertainty Service
# ==========================================================

class UncertaintyService:
    """
    Computes split-conformal calibration once (cached) and reuses it for
    every subsequent `estimate()` call - calibration is O(validation set
    size) and must not be repeated per-prediction (perf requirement).
    """

    def __init__(self, model_manager=None, alpha: float = DEFAULT_ALPHA) -> None:
        from models.model_manager import ModelManager

        self._model_manager = model_manager or ModelManager.instance()
        self.alpha = alpha

        self._lock = threading.Lock()
        self._regression_quantile: Optional[float] = None
        self._classification_quantile: Optional[float] = None
        self._calibration_size: int = 0
        self._calibrated = False
        self._calibration_failed_reason: Optional[str] = None

        self._calibrate()

    # ------------------------------------------------------
    # Calibration
    # ------------------------------------------------------

    def _cache_key(self) -> str:
        """
        Stable key tying a cached calibration to the exact model
        artifacts it was computed against, so a retrain invalidates it
        automatically instead of silently reusing a stale calibration.
        """
        clf_info = getattr(self._model_manager.classification_registry, "model_info", {}) or {}
        reg_info = getattr(self._model_manager.regression_registry, "model_info", {}) or {}
        return f"{clf_info.get('saved_at', '')}|{reg_info.get('saved_at', '')}|alpha={self.alpha}"

    def _load_cache(self) -> Optional[dict]:
        if not CALIBRATION_CACHE_FILE.exists():
            return None
        try:
            with open(CALIBRATION_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
        except (OSError, json.JSONDecodeError):
            logger.warning("Uncertainty calibration cache unreadable; recalibrating.")
            return None

        if cached.get("cache_key") != self._cache_key():
            logger.info("Uncertainty calibration cache is stale (model changed); recalibrating.")
            return None
        return cached

    def _save_cache(self) -> None:
        payload = {
            "cache_key": self._cache_key(),
            "regression_quantile": self._regression_quantile,
            "classification_quantile": self._classification_quantile,
            "calibration_size": self._calibration_size,
            "alpha": self.alpha,
        }
        try:
            ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            with open(CALIBRATION_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError:
            logger.warning("Could not persist uncertainty calibration cache.", exc_info=True)

    def _calibrate(self) -> None:
        with self._lock:
            cached = self._load_cache()
            if cached is not None:
                self._regression_quantile = cached["regression_quantile"]
                self._classification_quantile = cached["classification_quantile"]
                self._calibration_size = cached["calibration_size"]
                self._calibrated = True
                logger.info(
                    "Uncertainty calibration loaded from cache (n=%d).",
                    self._calibration_size,
                )
                return

            try:
                self._calibrate_from_validation_set()
                self._calibrated = True
                self._save_cache()
            except Exception as exc:  # noqa: BLE001 - must degrade gracefully, never crash the app
                logger.exception("Uncertainty calibration failed; uncertainty will be unavailable.")
                self._calibrated = False
                self._calibration_failed_reason = str(exc)

    def _calibrate_from_validation_set(self) -> None:
        from models.data_loader import load_datasets
        from models.preprocessing import TARGET_COLUMNS

        _, validation_df, _ = load_datasets()
        if validation_df is None or validation_df.empty:
            raise ValueError("Validation set is empty; cannot calibrate.")

        mm = self._model_manager

        # ---- Regression calibration: |y - yhat| quantile ----
        reg_target = TARGET_COLUMNS["regression"]
        reg_cols = mm.regression_feature_columns
        if reg_target in validation_df.columns and all(c in validation_df.columns for c in reg_cols):
            X_reg = validation_df.reindex(columns=reg_cols)
            y_reg = validation_df[reg_target].to_numpy(dtype=float)
            valid_mask = ~pd.isna(y_reg)
            X_reg = X_reg.loc[valid_mask]
            y_reg = y_reg[valid_mask]

            if len(y_reg) >= 20:
                preds = mm.regression_model.predict(X_reg)
                residuals = np.abs(y_reg - preds)
                n = len(residuals)
                # Split-conformal correction: ceil((n+1) * (1-alpha)) / n
                # quantile of absolute residuals (Lei et al. 2018).
                q_level = min(1.0, math.ceil((n + 1) * (1 - self.alpha)) / n)
                # method="higher" (not the default "linear"): split-conformal's
                # finite-sample coverage guarantee requires the *exact*
                # ceil((n+1)(1-alpha))-th order statistic of the residuals,
                # not a value interpolated between two order statistics.
                # Linear interpolation can land slightly below that exact
                # value, which would make the guarantee only approximate
                # rather than provable. "higher" always rounds up to the
                # correct order statistic, matching Lei et al. 2018's
                # Algorithm 1 exactly. At this calibration set's size the
                # numeric difference is tiny, but "higher" is the
                # textbook-correct choice regardless of sample size.
                self._regression_quantile = float(np.quantile(residuals, q_level, method="higher"))
            else:
                logger.warning("Too few valid regression rows (%d) to calibrate.", len(y_reg))

        # ---- Classification calibration: 1 - p(true class) quantile ----
        clf_target = TARGET_COLUMNS["classification"]
        clf_cols = mm.classification_feature_columns
        if clf_target in validation_df.columns and all(c in validation_df.columns for c in clf_cols):
            X_clf = validation_df.reindex(columns=clf_cols)
            y_clf_raw = validation_df[clf_target]
            valid_mask = ~y_clf_raw.isna()
            X_clf = X_clf.loc[valid_mask]
            y_clf = y_clf_raw.loc[valid_mask].astype(str).str.strip()

            from services.prediction_service import PredictionService
            class_mapping = PredictionService.CLASS_MAPPING
            y_clf_norm = y_clf.map(lambda v: class_mapping.get(v, class_mapping.get(v.lower(), v)))

            if len(X_clf) >= 20:
                proba = mm.classification_model.predict_proba(X_clf)
                model_classes = list(mm.classification_model.classes_)
                label_names = [class_mapping.get(c, str(c)) for c in model_classes]

                nonconformity = []
                for row_proba, true_label in zip(proba, y_clf_norm):
                    if true_label in label_names:
                        idx = label_names.index(true_label)
                        nonconformity.append(1.0 - row_proba[idx])
                nonconformity = np.array(nonconformity)

                if len(nonconformity) >= 20:
                    n = len(nonconformity)
                    q_level = min(1.0, math.ceil((n + 1) * (1 - self.alpha)) / n)
                    # See the matching comment on the regression quantile
                    # above: method="higher" is required for the provable
                    # coverage guarantee, not just the default interpolation.
                    self._classification_quantile = float(np.quantile(nonconformity, q_level, method="higher"))
                    self._calibration_size = n
                else:
                    logger.warning("Too few valid classification rows to calibrate.")

    # ------------------------------------------------------
    # Public API
    # ------------------------------------------------------

    def estimate(
        self,
        probabilities: dict[str, float],
        regression_score: Optional[float],
    ) -> UncertaintyResult:
        """
        Build an UncertaintyResult from an already-computed prediction.
        Never raises - any internal failure yields `available=False` with
        an explanatory message, so callers can render a graceful empty
        state (robustness requirement).
        """
        result = UncertaintyResult(calibration_sample_size=self._calibration_size)

        # Entropy is always computable from the probability vector alone,
        # independent of calibration success.
        probs = np.array(list(probabilities.values()), dtype=float)
        probs = probs[probs > 0]
        if probs.size > 0:
            entropy = float(-np.sum(probs * np.log(probs)))
            max_entropy = math.log(max(len(probabilities), 2))
            result.entropy = round(entropy, 4)
            result.entropy_normalized = round(entropy / max_entropy, 4) if max_entropy > 0 else 0.0

        if not self._calibrated:
            result.available = False
            result.explanation = (
                "Uncertainty estimation is unavailable right now "
                "(calibration could not be computed)."
            )
            return result

        result.available = True

        # ---- Regression interval ----
        if self._regression_quantile is not None and regression_score is not None:
            lower = max(0.0, regression_score - self._regression_quantile)
            upper = min(100.0, regression_score + self._regression_quantile)
            result.regression_lower = round(lower, 2)
            result.regression_upper = round(upper, 2)
            result.regression_interval_width = round(upper - lower, 2)

        # ---- Classification prediction set ----
        if self._classification_quantile is not None and probabilities:
            threshold = 1.0 - self._classification_quantile
            pred_set = [
                label for label, p in probabilities.items()
                if p >= threshold
            ]
            if not pred_set:
                # Guard against an empty set (possible when the top
                # probability itself is below threshold on a genuinely
                # hard case) by falling back to the single most likely
                # class, so the set is never empty/uninformative.
                pred_set = [max(probabilities, key=probabilities.get)]
            # Keep deterministic, confidence-descending order for display.
            pred_set.sort(key=lambda label: probabilities.get(label, 0.0), reverse=True)
            result.classification_set = pred_set
            result.classification_set_size = len(pred_set)

        result.uncertainty_label, result.explanation = self._summarize(result)
        return result

    @staticmethod
    def _summarize(result: UncertaintyResult) -> tuple[str, str]:
        set_size = result.classification_set_size
        entropy_norm = result.entropy_normalized or 0.0

        if set_size <= 1 and entropy_norm < 0.35:
            label = "Low"
            explanation = (
                "The model is statistically confident: at the 90% coverage "
                "level, only one class remains plausible for this input."
            )
        elif set_size >= 3 or entropy_norm >= 0.75:
            label = "High"
            explanation = (
                "This prediction is genuinely ambiguous: multiple wellness "
                "classes remain statistically plausible for this input. "
                "Treat the point prediction as a best guess, not a certainty."
            )
        else:
            label = "Moderate"
            explanation = (
                "The model is reasonably but not fully confident: more than "
                "one wellness class cannot be ruled out at the 90% "
                "coverage level."
            )

        if result.regression_interval_width is not None:
            explanation += (
                f" The wellness score could plausibly fall anywhere in a "
                f"{result.regression_interval_width:.0f}-point range around "
                f"the point estimate."
            )

        return label, explanation
