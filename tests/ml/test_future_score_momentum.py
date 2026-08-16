"""The seven-day band has to be about THIS person, not their class.

Before this, two users with an identical day got an identical band -
the estimate was built from the classifier's opinion plus where the
user sat inside their band today, and nothing else. Someone who had
climbed all week and someone who had fallen all week, landing on the
same score today, were told to expect exactly the same next week. That
is the "the band never adapts to me" report.

Their own recent trajectory is the missing evidence, and it is the one
thing the classifier structurally cannot see: it is handed one day at a
time. `_momentum` turns it into a bounded shift.

    slope    = OLS slope of the last k daily scores, points per day
    momentum = clamp(slope * 7, -8, +8)
    weight   = clamp((n - 2) / 5, 0, 1)
    shift    = momentum * weight

and the interval widens by the fit's residual sd, so the same slope
drawn through a jumpy week produces a wider band than through a steady
one.

What this test pins is the behaviour, not the constants: a climb lifts
the band, a fall lowers it, a flat week does neither, a four-day history
counts for less than a seven-day one, and nothing is claimed from two
days. It also pins the guard that matters most - a short or missing
history must leave the estimate exactly as it was.

Run: python3 -m unittest tests.ml.test_future_score_momentum -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401

from services.insight.future_score_service import (
    MOMENTUM_CAP,
    SCORE_CEILING,
    MOMENTUM_FULL_DAYS,
    MOMENTUM_MIN_DAYS,
    FutureScoreService,
    _momentum,
)

# A confident-Healthy classifier output, so every case below differs
# only in the history behind it.
CONFIDENT = {"Healthy": 0.86, "Moderate": 0.11, "At Risk": 0.03}


def _line(start: float, step: float, n: int) -> list[float]:
    return [start + step * i for i in range(n)]


class MomentumArithmetic(unittest.TestCase):

    def test_nothing_is_claimed_from_a_history_too_short_to_have_a_trend(self):
        for history in (None, [], [70.0], [70.0, 78.0]):
            shift, sd = _momentum(history)
            self.assertEqual((shift, sd), (0.0, 0.0), f"claimed a trend from {history}")

    def test_a_climb_lifts_and_a_fall_lowers_by_the_same_amount(self):
        up, _ = _momentum(_line(60.0, +1.0, 7))
        down, _ = _momentum(_line(66.0, -1.0, 7))
        self.assertGreater(up, 0)
        self.assertLess(down, 0)
        self.assertAlmostEqual(up, -down, places=6)

    def test_a_flat_week_moves_nothing(self):
        shift, sd = _momentum([71.0] * 7)
        self.assertAlmostEqual(shift, 0.0, places=9)
        self.assertAlmostEqual(sd, 0.0, places=9)

    def test_a_full_weeks_trend_is_carried_forward_whole(self):
        # +1.0/day over seven days, fully weighted: seven points.
        shift, _ = _momentum(_line(60.0, 1.0, MOMENTUM_FULL_DAYS))
        self.assertAlmostEqual(shift, 7.0, places=6)

    def test_four_days_of_the_same_slope_counts_for_less_than_seven(self):
        """The user's own example: a four-day user in decline.

        Four days is a real signal and a weak one. It has to move the
        band - otherwise the complaint stands - and it must not move it
        as far as the same slope measured over a week.
        """
        four, _ = _momentum(_line(70.0, -1.0, 4))
        seven, _ = _momentum(_line(70.0, -1.0, 7))
        self.assertLess(four, 0, "a four-day decline did not lower the band at all")
        self.assertGreater(four, seven, "four days counted as heavily as seven")
        self.assertAlmostEqual(four / seven, 2 / 5, places=6)

    def test_the_shift_is_bounded_however_steep_the_line(self):
        shift, _ = _momentum(_line(10.0, +9.0, 8))   # +63 points/week, raw
        self.assertLessEqual(shift, MOMENTUM_CAP + 1e-9)
        shift, _ = _momentum(_line(90.0, -9.0, 8))
        self.assertGreaterEqual(shift, -MOMENTUM_CAP - 1e-9)

    def test_a_jumpy_week_reports_more_residual_than_a_steady_one(self):
        steady = _line(60.0, 1.0, 8)
        jumpy = [60, 75, 55, 78, 58, 80, 62, 84]
        _, steady_sd = _momentum(steady)
        _, jumpy_sd = _momentum([float(v) for v in jumpy])
        self.assertAlmostEqual(steady_sd, 0.0, places=6)
        self.assertGreater(jumpy_sd, 5.0, "a week swinging 20+ points reported no noise")

    def test_only_the_recent_window_is_read(self):
        """A month-old collapse must not still be steering the band."""
        long_history = [20.0] * 30 + _line(70.0, 1.0, 7)
        windowed, _ = _momentum(long_history)
        recent_only, _ = _momentum(_line(70.0, 1.0, 7))
        self.assertGreater(windowed, 0, "an ancient dip outvoted a week of climbing")
        self.assertLess(abs(windowed - recent_only), 4.0)


class TheEstimateMovesWithThePerson(unittest.TestCase):
    """End to end through the real estimator, real artifacts."""

    def _band(self, history):
        return FutureScoreService.estimate(
            CONFIDENT, "Healthy", today_score=71.0, recent_scores=history,
        )

    def test_the_same_day_gives_different_bands_to_different_weeks(self):
        climbing = self._band(_line(64.0, 1.2, 7) + [71.0])
        falling = self._band(_line(78.0, -1.2, 7) + [71.0])
        flat = self._band([71.0] * 7)

        for r in (climbing, falling, flat):
            self.assertTrue(r.available, r.reason)

        self.assertGreater(
            climbing.score, flat.score,
            "a week of climbing produced the same band as a flat week",
        )
        self.assertLess(
            falling.score, flat.score,
            "a week of falling produced the same band as a flat week",
        )
        # And the reported reason matches what happened.
        self.assertGreater(climbing.momentum_shift, 0)
        self.assertLess(falling.momentum_shift, 0)
        self.assertEqual(flat.momentum_shift, 0.0)

    def test_a_four_day_decline_gets_a_lower_band_than_a_flat_four_days(self):
        declining = self._band([80.0, 77.0, 74.0, 71.0])
        flat = self._band([71.0, 71.0, 71.0, 71.0])
        self.assertTrue(declining.available and flat.available)
        self.assertLess(declining.score, flat.score)
        self.assertLess(declining.upper, flat.upper)

    def test_no_history_leaves_the_estimate_exactly_as_it_was(self):
        """The guard: this must be additive, never a regression."""
        without = FutureScoreService.estimate(CONFIDENT, "Healthy", today_score=71.0)
        empty = self._band([])
        short = self._band([71.0, 72.0])
        for r in (empty, short):
            self.assertEqual(r.score, without.score)
            self.assertEqual(r.lower, without.lower)
            self.assertEqual(r.upper, without.upper)
            self.assertEqual(r.momentum_shift, 0.0)

    def test_the_band_stays_inside_0_100(self):
        top = FutureScoreService.estimate(
            CONFIDENT, "Healthy", today_score=99.0,
            recent_scores=_line(60.0, 6.0, 8),
        )
        bottom = FutureScoreService.estimate(
            {"At Risk": 0.9, "Moderate": 0.08, "Healthy": 0.02}, "At Risk",
            today_score=2.0, recent_scores=_line(60.0, -8.0, 8),
        )
        for r in (top, bottom):
            self.assertGreaterEqual(r.lower, 0.0)
            self.assertLessEqual(r.upper, 100.0)
            self.assertGreaterEqual(r.score, 0.0)
            self.assertLessEqual(r.score, 100.0)

    def test_a_noisy_week_gets_a_wider_band_than_a_steady_one(self):
        steady = self._band(_line(64.0, 1.0, 8))
        noisy = self._band([64.0, 79.0, 59.0, 82.0, 62.0, 84.0, 66.0, 88.0])
        self.assertGreater(
            noisy.upper - noisy.lower, steady.upper - steady.lower,
            "a week that swung twenty points was reported as precisely as a steady climb",
        )

    def test_momentum_cannot_promise_a_score_the_model_cannot_award(self):
        """A climbing user at the top of the scale is still at the top of it.

        Without the ceiling, a user at 87 climbing a point a day was
        handed a band of 87-100 - a midpoint no inputs can reach on this
        regressor, so the extrapolation had left the model behind.
        """
        climbing_high = FutureScoreService.estimate(
            CONFIDENT, "Healthy", today_score=87.0,
            recent_scores=_line(80.0, 1.2, 8),
        )
        self.assertTrue(climbing_high.available)
        self.assertLessEqual(climbing_high.score, SCORE_CEILING + 1e-9)
        self.assertGreater(
            climbing_high.momentum_shift, 0,
            "the climb should still be recognised, just not extrapolated past the scale",
        )

    def test_the_minimum_is_where_the_docstring_says_it_is(self):
        self.assertEqual(MOMENTUM_MIN_DAYS, 3)
        self.assertGreater(MOMENTUM_FULL_DAYS, MOMENTUM_MIN_DAYS)


if __name__ == "__main__":
    unittest.main()
