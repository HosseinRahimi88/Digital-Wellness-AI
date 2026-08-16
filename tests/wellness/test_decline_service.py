"""Three days down in a row, noticed and priced.

The app could say where somebody stood and said nothing about where they
were heading. A score falling three days running is the clearest early
signal this data produces, and the dashboard drew three slightly shorter
bars and moved on.

What this pins:

  · three consecutive falls, not two - two is an ordinary weekend;
  · a run of tiny falls is not a decline. The model's own noise on
    identical inputs is bigger than a point, so three drops of 0.2 are
    arithmetic, not a week going wrong. Reporting them would be reading
    noise back to the user as a fact;
  · the penalty stays inside 2-5 and rises with the size of the fall;
  · an excluded day - one the user said was not their data - neither
    breaks a run nor extends one;
  · the run is the CURRENT one. A collapse a fortnight ago that has
    since recovered is not a decline now.

Run: python3 -m unittest tests.wellness.test_decline_service -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401

from services.wellness.decline_service import (
    MIN_DROP,
    PENALTY_MAX,
    PENALTY_MIN,
    RUN_THRESHOLD,
    detect,
    penalty_for,
)


def days(*scores, start_day=1, excluded=()):
    """History rows in the shape HistoryService stores them."""
    out = []
    for i, score in enumerate(scores):
        out.append({
            "date": f"2026-08-{start_day + i:02d}",
            "health_score": None if score is None else float(score),
            "excluded": (start_day + i) in excluded,
        })
    return out


class WhenItReports(unittest.TestCase):

    def test_a_steady_week_is_not_a_decline(self):
        self.assertFalse(detect(days(70, 71, 70, 72, 71)).declining)

    def test_two_falls_are_not_a_decline(self):
        self.assertFalse(detect(days(70, 74, 68, 60)).declining)

    def test_three_falls_are(self):
        report = detect(days(70, 74, 68, 60, 52))
        self.assertTrue(report.declining)
        self.assertEqual(report.days, RUN_THRESHOLD)
        self.assertAlmostEqual(report.drop, 22.0, places=6)
        self.assertEqual(report.scores, [74.0, 68.0, 60.0, 52.0])
        self.assertEqual(len(report.dates), RUN_THRESHOLD + 1)

    def test_a_longer_run_is_reported_whole(self):
        report = detect(days(80, 76, 71, 65, 60, 55))
        self.assertTrue(report.declining)
        self.assertEqual(report.days, 5)
        self.assertEqual(report.scores[0], 80.0)
        self.assertEqual(report.scores[-1], 55.0)

    def test_three_tiny_falls_are_arithmetic_not_a_decline(self):
        """Below the model's own noise on identical inputs."""
        report = detect(days(70.0, 69.9, 69.7, 69.6))
        self.assertFalse(
            report.declining,
            f"a {70.0 - 69.6:.1f}-point slide over three days was called a decline",
        )

    def test_a_fall_exactly_at_the_floor_is_reported(self):
        report = detect(days(70.0, 69.0, 68.0, 70.0 - MIN_DROP))
        self.assertTrue(report.declining)
        self.assertGreaterEqual(report.penalty, PENALTY_MIN)

    def test_the_run_has_to_be_the_current_one(self):
        # A bad stretch a fortnight ago, recovered since.
        history = days(80, 70, 60, 50) + days(55, 62, 70, 74, start_day=10)
        self.assertFalse(detect(history).declining)

    def test_too_short_a_history_claims_nothing(self):
        for n in range(RUN_THRESHOLD + 1):
            self.assertFalse(detect(days(*range(80, 80 - n, -1))).declining)

    def test_a_day_with_no_score_is_skipped_not_treated_as_zero(self):
        report = detect(days(74, 68, None, 60, 52))
        self.assertTrue(report.declining)
        self.assertNotIn(0.0, report.scores)


class ExcludedDays(unittest.TestCase):
    """A day the user said was not their data must not be read anyway."""

    def test_an_excluded_spike_does_not_break_a_run(self):
        # 74, 68, [95 excluded], 60, 52 - still three falls.
        history = days(74, 68, 95, 60, 52, excluded=(3,))
        report = detect(history)
        self.assertTrue(report.declining, "an excluded day broke the run")
        self.assertNotIn(95.0, report.scores)

    def test_an_excluded_day_does_not_create_a_run_either(self):
        # 70, 71, [65 excluded], 72 - nothing is falling.
        history = days(70, 71, 65, 72, 73, excluded=(3,))
        self.assertFalse(detect(history).declining)


class ThePenalty(unittest.TestCase):

    def test_it_stays_inside_the_two_to_five_range(self):
        for drop in (0.1, 3, 5, 10, 18, 40, 100):
            p = penalty_for(float(drop))
            self.assertGreaterEqual(p, PENALTY_MIN if drop >= MIN_DROP else 0.0)
            self.assertLessEqual(p, PENALTY_MAX)

    def test_a_bigger_fall_costs_more(self):
        small = penalty_for(4.0)
        medium = penalty_for(10.0)
        large = penalty_for(25.0)
        self.assertLess(small, medium)
        self.assertLess(medium, large)
        self.assertEqual(large, PENALTY_MAX)

    def test_a_barely_qualifying_fall_costs_the_minimum(self):
        self.assertEqual(penalty_for(MIN_DROP), PENALTY_MIN)

    def test_no_fall_costs_nothing(self):
        self.assertEqual(penalty_for(0.0), 0.0)
        self.assertEqual(penalty_for(-5.0), 0.0)


if __name__ == "__main__":
    unittest.main()
