"""
Serving-path tests for the history-aware classifier.

The point is not the accuracy number (that lives in
models/research_classification_trend.py) but the two properties the
serving path must hold whatever the model scores:

  1. A brand-new user with no history still gets a prediction. Cold start
     must degrade, never fail.
  2. History is actually used - the same day submitted by a user on an
     improving run and by a user on a declining run must not be forced to
     produce the identical feature row.

Both are regression guards: the previous silent-zero-fill bug shipped
precisely because nothing asserted what happens to missing inputs.
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from utils.trend_features import (
    TREND_SOURCE_FIELDS,
    build_trend_features,
    trend_feature_names,
)


def _day(value: float) -> dict:
    return {f: value for f in TREND_SOURCE_FIELDS}


class TestColdStartServing(unittest.TestCase):
    def test_no_history_produces_every_column(self):
        out = build_trend_features(_day(50.0), [])
        self.assertEqual(set(out), set(trend_feature_names()))

    def test_no_history_leaves_deltas_unknown_not_zero(self):
        """
        NaN means "no history"; 0.0 would mean "measured, and unchanged".
        The model was trained with NaN for these, so serving must match.
        """
        out = build_trend_features(_day(50.0), [])
        self.assertTrue(np.isnan(out["sleep_hours_d1"]))
        self.assertTrue(np.isnan(out["stress_0_10_vol7"]))


class TestHistoryChangesTheFeatureRow(unittest.TestCase):
    def test_improving_and_declining_users_differ_on_the_same_day(self):
        today = _day(50.0)
        improving = [_day(20.0), _day(30.0), _day(40.0)]   # rising toward today
        declining = [_day(80.0), _day(70.0), _day(60.0)]   # falling toward today

        a = build_trend_features(today, improving)
        b = build_trend_features(today, declining)

        # Same submitted day, opposite trajectories -> opposite deltas.
        self.assertGreater(a["sleep_hours_d1"], 0)
        self.assertLess(b["sleep_hours_d1"], 0)
        # And today sits above vs below each user's own baseline.
        self.assertGreater(a["sleep_hours_dev"], 0)
        self.assertLess(b["sleep_hours_dev"], 0)

    def test_excluded_days_are_simply_not_passed(self):
        """
        The caller filters excluded days out; this asserts the function
        respects whatever it is given rather than reaching for more.
        """
        with_all = build_trend_features(_day(50.0), [_day(10.0), _day(90.0)])
        without_outlier = build_trend_features(_day(50.0), [_day(10.0)])
        self.assertNotEqual(with_all["focus_0_100_r3"], without_outlier["focus_0_100_r3"])


class TestPreparedRowKeepsTrendNaN(unittest.TestCase):
    def test_zero_fill_does_not_touch_trend_columns(self):
        """
        PredictionService fills genuine gaps with 0.0 as a safety net, but
        must exempt trend columns - otherwise a first-time user's
        "unknown" silently becomes "nothing changed".

        This asserts the built row itself rather than the source text of
        the function that builds it. The previous version matched on a
        substring, so it passed or failed on how a loop variable happened
        to be spelled and would have missed the behaviour changing under
        an identical-looking implementation.
        """
        import math

        from api.dependencies.services import get_model_manager
        from services.ml.prediction_service import PredictionService
        from utils.trend_features import trend_feature_names

        service = PredictionService(model_manager=get_model_manager())
        columns = service.feature_columns
        trend_cols = [c for c in trend_feature_names() if c in columns]
        self.assertTrue(trend_cols, "expected the classifier to use trend features")

        # A first-time user: no history at all, so every trend column is
        # genuinely unknown.
        row = service._prepare_dataframe({}, columns, [])

        for col in trend_cols:
            value = row[col].iloc[0]
            self.assertTrue(
                value is None or (isinstance(value, float) and math.isnan(value)),
                f"trend column {col} was filled with {value!r} instead of left unknown",
            )

        # The safety net still applies to ordinary numeric columns, or the
        # test above would pass for a function that fills nothing at all.
        filled = [
            c for c in columns
            if c not in trend_cols and row[c].iloc[0] == 0.0
        ]
        self.assertTrue(filled, "expected non-trend gaps to be zero-filled")

    def test_predict_accepts_history_argument(self):
        import inspect

        from services.ml.prediction_service import PredictionService

        sig = inspect.signature(PredictionService.predict)
        self.assertIn("history", sig.parameters)


if __name__ == "__main__":
    unittest.main()
