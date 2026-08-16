"""
Per-user trend features (shared by training AND serving)
==========================================================
The classification target is the health class SEVEN DAYS AHEAD, but the
model was only ever shown a single day. Where somebody is heading is
largely a function of their recent trajectory, so this module turns a
user's own recent check-ins into the trend signals that carry that
information.

Why this lives in ONE module used by both sides
--------------------------------------------------
This project has already been burned once by train/serve skew: the raw
CSVs' `total_screen_min` was generated with different semantics than the
live form could ever produce, so every ratio derived from it was trained
on a distribution the app never sees (see models/data_loader.py). The
lesson taken from that is structural - training and inference must build
these columns by calling the same function, not by two implementations
that are "kept in sync" by hand. `build_trend_features()` is that
function, and both `models/train_classification.py` and
`services/ml/prediction_service.py` route through it.

What is deliberately NOT here
--------------------------------
`day_index` and any cumulative day counter. Those encode where a row sits
inside a synthetic user's generated diary, and the generator wrote each
user's trajectory against day number - so they predict the target
extremely well and mean nothing for a real person (a real user's "day 15"
says nothing about their wellness next week). Including either inflates
accuracy while making the model useless in production. See
models/research_classification_trend.py for the measurements.

Every source signal below is already stored per entry by
services/history_service.TRACKED_FIELDS, so nothing new has to be
collected - the history the app already keeps is enough.

Cold start
-------------
A user with no prior check-ins gets NaN for every trend column, which
HistGradientBoosting handles natively as "missing" rather than as zero.
Accuracy then degrades toward the same-day-only baseline instead of
breaking, and `history_days` tells the caller how much history backed the
prediction so the UI can be honest about it.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd

# Signals to trend. Each is present in HistoryService.TRACKED_FIELDS, so
# each is reproducible at serving time from the user's saved check-ins.
TREND_SOURCE_FIELDS: list[str] = [
    "total_screen_min",
    "social_min",
    "gaming_min",
    "work_study_min",
    "video_min",
    "night_screen_min",
    "pre_sleep_screen_min",
    "sleep_hours",
    "sleep_quality_1_10",
    "stress_0_10",
    "focus_0_100",
    "productivity_0_100",
    "physical_activity_min_per_day",
    "pickups_per_day",
    "night_ratio",
    "social_ratio",
    "fragmentation_index_0_100",
    "notification_density",
    "social_comparison_1_10",
]

# Suffixes, in the order they are generated. Kept as data so the feature
# name list can be derived rather than written out twice.
TREND_SUFFIXES: tuple[str, ...] = ("d1", "r3", "r7", "sl7", "sl14", "vol7", "dev")

SHORT_WINDOW = 3
MEDIUM_WINDOW = 7
LONG_WINDOW = 14


def trend_feature_names() -> list[str]:
    """Every column build_trend_features() produces, in a stable order."""
    return [f"{field}_{suffix}" for field in TREND_SOURCE_FIELDS for suffix in TREND_SUFFIXES]


def _series(history: list[dict[str, Any]], field: str, today: Any) -> pd.Series:
    """Oldest-to-newest values for one field, with today's value last."""
    values: list[float] = []
    for entry in history:
        raw = entry.get(field)
        try:
            values.append(float(raw)) if raw is not None and not isinstance(raw, bool) else values.append(np.nan)
        except (TypeError, ValueError):
            values.append(np.nan)
    try:
        values.append(float(today) if today is not None and not isinstance(today, bool) else np.nan)
    except (TypeError, ValueError):
        values.append(np.nan)
    return pd.Series(values, dtype="float64")


def build_trend_features(
    user_data: dict[str, Any],
    history: Optional[Iterable[dict[str, Any]]] = None,
) -> dict[str, float]:
    """
    Trend columns for ONE prediction.

    `history` is that user's earlier check-ins, oldest first, EXCLUDING
    today - the caller owns that ordering because only it knows which
    entries the user chose to exclude from their trend. Days the user
    marked as exceptions should not be passed in.

    Returns a plain dict so the caller can merge it into the feature row
    without depending on pandas here.
    """
    entries = list(history or [])
    out: dict[str, float] = {}

    for field in TREND_SOURCE_FIELDS:
        s = _series(entries, field, user_data.get(field))
        today = s.iloc[-1]

        r3 = s.rolling(SHORT_WINDOW, min_periods=1).mean().iloc[-1]
        r7 = s.rolling(MEDIUM_WINDOW, min_periods=1).mean().iloc[-1]
        r14 = s.rolling(LONG_WINDOW, min_periods=1).mean().iloc[-1]
        # std needs two points to mean anything; one point is not "zero
        # volatility", it is unknown volatility.
        vol7 = s.rolling(MEDIUM_WINDOW, min_periods=2).std().iloc[-1]
        # First-ever entry has no previous day, so no delta exists.
        d1 = today - s.iloc[-2] if len(s) >= 2 else np.nan

        out[f"{field}_d1"] = d1
        out[f"{field}_r3"] = r3
        out[f"{field}_r7"] = r7
        out[f"{field}_sl7"] = r3 - r7        # short vs medium: recent shift
        out[f"{field}_sl14"] = r7 - r14      # medium vs long: sustained drift
        out[f"{field}_vol7"] = vol7
        out[f"{field}_dev"] = today - r7     # today vs personal baseline

    return out


def add_trend_features_to_frame(
    df: pd.DataFrame,
    group_columns: list[str],
    order_column: str = "day_index",
) -> tuple[pd.DataFrame, list[str]]:
    """
    Vectorised equivalent of build_trend_features() for TRAINING, where
    every user's whole diary is present at once.

    `group_columns` reconstructs the per-user key (the raw CSVs carry no
    user id - see models/regenerate_user_split.py for why these ten
    demographic columns are the available stand-in). `order_column` only
    sequences each user's rows; it is never emitted as a feature.

    Must stay numerically identical to build_trend_features() - the tests
    in tests/ml/test_trend_features.py assert exactly that, because a silent
    divergence here is the train/serve skew this module exists to prevent.
    """
    df = df.copy()
    uid = df[group_columns].astype(str).agg("|".join, axis=1)
    df["__uid"] = uid
    df = df.sort_values(["__uid", order_column])
    grouped = df.groupby("__uid", sort=False)

    # Built into a dict and concatenated once. Assigning 133 columns one
    # at a time re-allocates the frame on every insert, which is slow
    # enough to matter on the full 93k-row training set.
    built: dict[str, pd.Series] = {}
    for field in TREND_SOURCE_FIELDS:
        r3 = grouped[field].transform(lambda s: s.rolling(SHORT_WINDOW, min_periods=1).mean())
        r7 = grouped[field].transform(lambda s: s.rolling(MEDIUM_WINDOW, min_periods=1).mean())
        r14 = grouped[field].transform(lambda s: s.rolling(LONG_WINDOW, min_periods=1).mean())

        built[f"{field}_d1"] = grouped[field].diff(1)
        built[f"{field}_r3"] = r3
        built[f"{field}_r7"] = r7
        built[f"{field}_sl7"] = r3 - r7
        built[f"{field}_sl14"] = r7 - r14
        built[f"{field}_vol7"] = grouped[field].transform(
            lambda s: s.rolling(MEDIUM_WINDOW, min_periods=2).std()
        )
        built[f"{field}_dev"] = df[field] - r7

    df = pd.concat([df, pd.DataFrame(built, index=df.index)], axis=1)

    df = df.drop(columns="__uid")
    return df, trend_feature_names()
