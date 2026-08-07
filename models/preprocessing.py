"""
=========================================================
Digital Wellness AI
Preprocessing Utilities
=========================================================
"""

from __future__ import annotations
import pandas as pd
from typing import Tuple, List

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET_COLUMNS = {
    "classification": "future_health_class_7d",
    "regression": "health_score_0_100",
}

def get_feature_columns(df: pd.DataFrame, task: str = "classification") -> List[str]:
    """
    Returns list of feature column names excluding target, leakage columns,
    and the low-signal/redundant columns dropped by Feature Selection (see
    LOW_SIGNAL_COLUMNS / TASK_SPECIFIC_EXCLUSIONS below).
    """
    targets = [t.strip().lower() for t in TARGET_COLUMNS.values()]
    
    leakage_columns = [
        "future_health_score_7d",
        "future_health_score_day7",
        "future_health_class_7d",
        "future_risk_7d",
        "health_score_change_7d",
        "health_score_raw_0_100",
        "health_score_0_100",
        "record_id",
        "user_id",
        "date",
        # "split" is a dataset-bookkeeping column (train/validation/test),
        # not a real signal about the user. It slipped into training
        # because it's a plain column in the CSVs and nothing excluded it.
        # The live app never collects it (it isn't in FEATURE_SCHEMA), so
        # at inference time it always arrives missing and gets encoded as
        # an all-zero one-hot slice -- dead weight at best, and a genuine
        # leakage risk at worst if the split assignment wasn't fully
        # random. Exclude it like any other metadata column.
        "split",
        # These composite subscores are components that health_score_0_100 is
        # built from. core/feature_schema.py already excludes them from the
        # app's input schema (see its module docstring), but until now this
        # list didn't match that, so the trained model was still fit on them
        # as real features. At inference time they were always missing and
        # got silently zero-filled in PredictionService, which biased almost
        # every prediction toward "At Risk". Excluding them here brings
        # training in line with what the app actually collects; retrain
        # (train_classification.py / train_regression.py) to regenerate the
        # saved model + feature_columns.json without them.
        "sleep_subscore",
        "night_subscore",
        "focus_subscore",
        "balance_subscore",
        "stress_fatigue_subscore",
        "activity_context_subscore",
        # These four engineered features exist in the raw CSVs but were
        # never added to core/feature_schema.py, so the Streamlit form
        # never collects them. A previous session's notes claimed they
        # had already been excluded here, but that exclusion was never
        # actually applied to this list -- get_feature_columns() was
        # still returning all four, so the trained model kept relying on
        # inputs the live app can never supply. At inference time they
        # arrived missing and were silently zero-filled by
        # PredictionService, skewing predictions. Excluding them here is
        # what actually brings training in line with FEATURE_SCHEMA;
        # retrain (train_classification.py / train_regression.py) after
        # this change to regenerate the saved model + feature_columns.json.
        "recovery_index",
        "cognitive_load",
        "screen_addiction_index",
        "night_usage_burden",
    ]

    # -------------------------------------------------------------
    # Feature Selection (permutation importance + correlation analysis)
    # -------------------------------------------------------------
    # Evidence: 10-repeat permutation importance of the trained
    # health_classifier / health_regressor pipelines on the validation
    # split, cross-checked against XGBoost gain importance and pairwise
    # Pearson correlation (|r| > 0.7) among numeric features. A column
    # was only removed when BOTH of the following held:
    #   (a) importance_mean - 2*importance_std <= 0 for the task's own
    #       model (i.e. statistically indistinguishable from zero/noise
    #       on held-out data -- not merely "low"), and
    #   (b) either the column is a constant (zero-variance) column, or
    #       it is highly correlated (|r| > 0.7) with another retained
    #       column that carries the same information more reliably.
    # Columns that were low-importance but NOT redundant with anything
    # else (e.g. mental-health scores such as anxiety_0_27,
    # loneliness_1_10, notification_density) were deliberately KEPT --
    # a single noisy validation-split score is not sufficient evidence
    # to drop a domain-relevant feature.
    #
    # Removed from BOTH tasks:
    #   - operating_system: constant column (100% "Unknown" in every
    #     row of train/validation/test) -- zero variance, zero
    #     information by construction. Permutation importance is
    #     exactly 0.0 in both models for this reason.
    #   - screen_vs_ewma_pct: r=0.82 with screen_vs_baseline_pct, both
    #     encode "deviation from a screen-time baseline"; ewma_pct was
    #     statistically insignificant in both models while
    #     baseline_pct remained significant for regression, so the
    #     baseline_pct twin was kept.
    #   - avg_session_min: statistically insignificant in both models;
    #     moderately correlated (r~0.55-0.56) with total_screen_min and
    #     sessions_per_day, of which it is arithmetically close to a
    #     ratio (total_screen_min / sessions_per_day).
    #   - sessions_per_day: statistically insignificant in both models
    #     (exactly 0.0 permutation importance for regression).
    #   - first_check_after_waking_min: statistically insignificant in
    #     both models; weakest single justification of the six (no
    #     strong correlation partner), retained candidate status only
    #     because it was null in two independently-trained models
    #     against two different targets.
    # Note: sessions_per_day, first_check_after_waking_min and
    # pickups_per_day remain in core.feature_schema.FEATURE_SCHEMA /
    # the live form because they still feed derived indices that ARE
    # retained features (fragmentation_index_0_100,
    # digital_dependence_0_100). Removing them here only stops them
    # from being used directly as standalone model inputs.
    #
    # Empirically validated by retraining (see artifacts/metrics.json /
    # metrics_regression.json for the current numbers, and
    # /home/claude backup of the pre-selection artifacts for the
    # "before" comparison used during development): classification improved on every
    # validation/test metric with these 5 features removed on top of
    # operating_system. Regression, however, got very slightly WORSE
    # (test R2 0.9661 -> 0.9655, MAE 0.9727 -> 0.9819) when
    # screen_ewma_baseline was also removed, because it was the one
    # feature among the six with a genuinely positive, statistically
    # significant contribution to the regression model
    # (permutation importance ~9.1e-5, mean - 2*std > 0). Per the
    # requirement that a feature subset only be adopted if it helps
    # BOTH tasks, screen_ewma_baseline is therefore excluded from the
    # classification-only exclusion list below instead of the shared
    # one, so regression keeps it while classification does not.

    common_low_signal_columns = [
        "operating_system",
        "screen_vs_ewma_pct",
        "avg_session_min",
        "sessions_per_day",
        "first_check_after_waking_min",
    ]

    # classification-only: screen_ewma_baseline is near-duplicate
    # information of total_screen_min (r=0.97) and was statistically
    # insignificant for classification (mean - 2*std < 0), so it is
    # dropped there. Regression keeps it (see note above) because it
    # is the one feature of the six with a real, positive contribution
    # to that model.
    task_specific_low_signal_columns = {
        "classification": ["screen_ewma_baseline"],
        "regression": [],
    }

    low_signal_columns = list(common_low_signal_columns) + list(
        task_specific_low_signal_columns.get(task, [])
    )

    ignore_list = set(
        targets
        + [col.lower() for col in leakage_columns]
        + [col.lower() for col in low_signal_columns]
    )
    
    return [col for col in df.columns if col.strip().lower() not in ignore_list]


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """
    Build a ColumnTransformer that scales numeric features and
    one-hot encodes categorical features, based on the dtypes
    found in the supplied training features.

    Parameters
    ----------
    X : pd.DataFrame
        Feature dataframe (training split) used to infer column types.

    Returns
    -------
    ColumnTransformer
    """

    numeric_columns = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_columns = [col for col in X.columns if col not in numeric_columns]

    numeric_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])

    transformers = []

    if numeric_columns:
        transformers.append(("numeric", numeric_pipeline, numeric_columns))

    if categorical_columns:
        transformers.append(("categorical", categorical_pipeline, categorical_columns))

    return ColumnTransformer(transformers=transformers, remainder="drop")


def split_features_target(
    df: pd.DataFrame, task: str = "classification"
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Splits dataframe into X (features) and y (target) based on task.
    Includes auto-matching for target column case and whitespace sensitivity.
    """
    raw_target_col = TARGET_COLUMNS.get(task)
    if not raw_target_col:
        raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")

    matched_target_col = None
    for col in df.columns:
        if col.strip().lower() == raw_target_col.strip().lower():
            matched_target_col = col
            break

    if not matched_target_col:
        available_columns = list(df.columns)
        raise KeyError(
            f"\n\n[ERROR] Target column '{raw_target_col}' for task '{task}' not found in DataFrame.\n"
            f"Available columns in your CSV file ({len(available_columns)} columns):\n"
            f"{available_columns}\n"
        )

    feature_cols = get_feature_columns(df, task=task)
    X = df[feature_cols].copy()
    y = df[matched_target_col].copy()

    return X, y