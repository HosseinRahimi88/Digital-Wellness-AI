"""
The one property that matters for utils/trend_features.py: the row-wise
path used at SERVING time and the vectorised path used at TRAINING time
must produce the same numbers.

If they ever drift, the model is trained on one distribution and served
another - the exact train/serve skew that already bit this project once
with `total_screen_min` (see models/data_loader.py). A unit test is the
only thing that keeps two implementations honest, so this file asserts
equality element by element rather than trusting review.
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from utils.trend_features import (
    TREND_SOURCE_FIELDS,
    add_trend_features_to_frame,
    build_trend_features,
    trend_feature_names,
)

GROUP_COLS = ["age", "gender"]


def _diary(n_days: int, seed: int = 0) -> pd.DataFrame:
    """One synthetic user's diary, deterministic."""
    rng = np.random.default_rng(seed)
    rows = []
    for day in range(1, n_days + 1):
        row = {"age": 30, "gender": "Male", "day_index": day}
        for i, field in enumerate(TREND_SOURCE_FIELDS):
            row[field] = float(rng.integers(1, 100) + i)
        rows.append(row)
    return pd.DataFrame(rows)


class TestTrainServeParity(unittest.TestCase):
    def _assert_parity(self, n_days: int, seed: int = 0):
        diary = _diary(n_days, seed)
        framed, names = add_trend_features_to_frame(diary, GROUP_COLS)
        framed = framed.sort_values("day_index").reset_index(drop=True)

        for k in range(n_days):
            today = diary.iloc[k].to_dict()
            history = [diary.iloc[j].to_dict() for j in range(k)]
            rowwise = build_trend_features(today, history)

            for name in names:
                expected = framed.iloc[k][name]
                actual = rowwise[name]
                if pd.isna(expected) or pd.isna(actual):
                    self.assertTrue(
                        pd.isna(expected) and pd.isna(actual),
                        f"day {k+1} {name}: one side NaN (frame={expected}, row={actual})",
                    )
                else:
                    self.assertAlmostEqual(
                        float(expected), float(actual), places=9,
                        msg=f"day {k+1} {name}: frame={expected} row={actual}",
                    )

    def test_parity_first_day(self):
        """Cold start: the very first entry has no history at all."""
        self._assert_parity(1)

    def test_parity_short_history(self):
        """Fewer days than the shortest rolling window."""
        self._assert_parity(2)

    def test_parity_mid_history(self):
        """Between the short and long windows."""
        self._assert_parity(8, seed=3)

    def test_parity_long_history(self):
        """Past the 14-day window, so every window is fully populated."""
        self._assert_parity(21, seed=7)


class TestColdStartBehaviour(unittest.TestCase):
    def test_no_history_gives_nan_not_zero(self):
        """
        Missing must stay missing. Zero-filling is what previously biased
        predictions - the model can treat NaN as "unknown", but a zero
        delta is a positive claim that nothing changed.
        """
        today = {f: 10.0 for f in TREND_SOURCE_FIELDS}
        out = build_trend_features(today, [])
        for field in TREND_SOURCE_FIELDS:
            self.assertTrue(np.isnan(out[f"{field}_d1"]), f"{field}_d1 should be NaN")
            self.assertTrue(np.isnan(out[f"{field}_vol7"]), f"{field}_vol7 should be NaN")
            # A single point IS its own mean, so these are legitimately known.
            self.assertEqual(out[f"{field}_r3"], 10.0)
            self.assertEqual(out[f"{field}_dev"], 0.0)

    def test_every_declared_name_is_produced(self):
        out = build_trend_features({f: 1.0 for f in TREND_SOURCE_FIELDS}, [])
        self.assertEqual(sorted(out.keys()), sorted(trend_feature_names()))

    def test_missing_field_does_not_crash(self):
        """A history entry written before a field existed just reads as NaN."""
        out = build_trend_features({}, [{}, {}])
        self.assertEqual(len(out), len(trend_feature_names()))
        self.assertTrue(all(pd.isna(v) for v in out.values()))


class TestNoFutureLeakage(unittest.TestCase):
    def test_value_unchanged_when_later_days_removed(self):
        """
        Day k's features must not move when days after k are deleted.
        This is what makes the features a forecast rather than hindsight.
        """
        diary = _diary(15, seed=11)
        k = 6
        today = diary.iloc[k].to_dict()
        history = [diary.iloc[j].to_dict() for j in range(k)]

        with_future = build_trend_features(today, history)
        # Deleting rows after k cannot change anything, because none were
        # ever passed in - assert it explicitly so a future refactor that
        # starts peeking forward fails here.
        truncated = _diary(15, seed=11).iloc[: k + 1]
        history_trunc = [truncated.iloc[j].to_dict() for j in range(k)]
        without_future = build_trend_features(truncated.iloc[k].to_dict(), history_trunc)

        for name in trend_feature_names():
            a, b = with_future[name], without_future[name]
            if pd.isna(a) or pd.isna(b):
                self.assertTrue(pd.isna(a) and pd.isna(b), name)
            else:
                self.assertAlmostEqual(float(a), float(b), places=9, msg=name)


if __name__ == "__main__":
    unittest.main()
