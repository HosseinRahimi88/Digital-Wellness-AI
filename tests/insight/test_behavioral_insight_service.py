"""
Tests: behavioural insight cards (D-4, D-5, D-6, D-9, D-11).

The whole risk of this feature is producing a confident-looking
"discovery" out of nothing, so most of these tests assert that a card is
NOT produced: from a thin history, from noise, or from a day the user
marked as an exception. A statistics feature that only proves it can find
a planted signal has not been tested at all - it has to also prove it
stays quiet.
"""

from __future__ import annotations

import random
import unittest

from services.insight.behavioral_insight_service import (
    BehavioralInsightService,
    MIN_ABS_CORRELATION,
    MIN_DAYS_CORRELATION,
)


def day(i: int, **kw) -> dict:
    entry = {
        "date": f"2026-03-{i + 1:02d}",
        "health_score": 60.0,
        "sleep_hours": 7.0,
        "social_min": 120.0,
        "stress_0_10": 5.0,
        "focus_0_100": 60.0,
    }
    entry.update(kw)
    return entry


class TestDataSufficiency(unittest.TestCase):
    """G4: without enough of the user's own data, render nothing."""

    def test_thin_history_produces_no_cards(self):
        thin = [day(i) for i in range(4)]
        self.assertIsNone(BehavioralInsightService.strongest_correlation(thin))
        self.assertIsNone(BehavioralInsightService.strongest_domino(thin))
        self.assertIsNone(BehavioralInsightService.narrative_facts(thin))
        self.assertIsNone(BehavioralInsightService.first_vs_now(thin))

    def test_empty_history_is_safe(self):
        cards = BehavioralInsightService.build_all([])
        self.assertEqual(set(cards), {"correlation", "domino", "first_vs_now", "small_win", "narrative"})
        self.assertTrue(all(v is None for v in cards.values()))

    def test_just_under_the_threshold_still_declines(self):
        rows = [day(i, social_min=60.0 + i * 15, stress_0_10=2.0 + i * 0.5)
                for i in range(MIN_DAYS_CORRELATION - 1)]
        self.assertIsNone(BehavioralInsightService.strongest_correlation(rows))


class TestFindsRealSignal(unittest.TestCase):

    def test_planted_relationship_is_found_with_correct_direction(self):
        rows = [day(i, social_min=60.0 + i * 15, stress_0_10=2.0 + i * 0.55) for i in range(14)]
        c = BehavioralInsightService.strongest_correlation(rows)
        self.assertIsNotNone(c)
        self.assertEqual({c.field_a, c.field_b}, {"social_min", "stress_0_10"})
        self.assertEqual(c.direction, "together")
        self.assertGreaterEqual(abs(c.coefficient), MIN_ABS_CORRELATION)

    def test_inverse_relationship_reports_opposite(self):
        rows = [day(i, sleep_hours=4.0 + i * 0.3, stress_0_10=9.0 - i * 0.5) for i in range(14)]
        c = BehavioralInsightService.strongest_correlation(rows)
        self.assertIsNotNone(c)
        self.assertEqual(c.direction, "opposite")

    def test_result_is_always_flagged_as_observation_only(self):
        rows = [day(i, social_min=60.0 + i * 15, stress_0_10=2.0 + i * 0.55) for i in range(14)]
        c = BehavioralInsightService.strongest_correlation(rows)
        self.assertTrue(c.is_observation_only)


class TestStaysQuietOnNoise(unittest.TestCase):
    """The failure mode that matters: inventing a pattern."""

    def test_random_history_yields_no_correlation_card(self):
        rng = random.Random(7)
        rows = [
            day(i,
                social_min=rng.uniform(30, 240),
                stress_0_10=rng.uniform(0, 10),
                sleep_hours=rng.uniform(4, 9),
                focus_0_100=rng.uniform(10, 95),
                health_score=rng.uniform(40, 80))
            for i in range(14)
        ]
        self.assertIsNone(BehavioralInsightService.strongest_correlation(rows))

    def test_noise_across_many_seeds_rarely_produces_a_card(self):
        """A single quiet seed could be luck; most seeds must stay quiet."""
        produced = 0
        for seed in range(25):
            rng = random.Random(seed)
            rows = [
                day(i,
                    social_min=rng.uniform(30, 240),
                    stress_0_10=rng.uniform(0, 10),
                    sleep_hours=rng.uniform(4, 9),
                    focus_0_100=rng.uniform(10, 95),
                    productivity_0_100=rng.uniform(10, 95),
                    health_score=rng.uniform(40, 80))
                for i in range(14)
            ]
            if BehavioralInsightService.strongest_correlation(rows) is not None:
                produced += 1
        self.assertLessEqual(
            produced, 8,
            f"Pure noise produced a 'discovery' in {produced}/25 seeds - the "
            "correlation threshold or the candidate-pair count is too permissive",
        )


class TestExceptionDaysExcluded(unittest.TestCase):

    def _planted(self):
        return [day(i, social_min=60.0 + i * 15, stress_0_10=2.0 + i * 0.55) for i in range(14)]

    def test_exception_day_does_not_change_the_correlation(self):
        base = BehavioralInsightService.strongest_correlation(self._planted())
        polluted = self._planted() + [
            day(20, social_min=9999.0, stress_0_10=0.0, excluded=True)
        ]
        after = BehavioralInsightService.strongest_correlation(polluted)
        self.assertEqual(
            (base.field_a, base.field_b, base.coefficient),
            (after.field_a, after.field_b, after.coefficient),
            "An excluded day changed a statistic it must not contribute to",
        )

    def test_narrative_counts_exceptions_without_using_them(self):
        rows = [day(i, health_score=60.0 + i) for i in range(8)]
        rows.append(day(20, health_score=1.0, excluded=True))
        facts = BehavioralInsightService.narrative_facts(rows)
        self.assertEqual(facts.exceptions_marked, 1)
        self.assertNotEqual(facts.worst_score, 1.0, "An excluded day became the 'worst day'")


class TestSmallWin(unittest.TestCase):

    def test_noise_sized_change_is_not_celebrated(self):
        rows = [day(0, sleep_hours=7.0), day(1, sleep_hours=7.1)]
        self.assertIsNone(BehavioralInsightService.small_win(rows))

    def test_meaningful_improvement_is_reported_with_direction(self):
        rows = [day(0, sleep_hours=6.0), day(1, sleep_hours=7.5)]
        win = BehavioralInsightService.small_win(rows)
        self.assertIsNotNone(win)
        self.assertEqual(win.field, "sleep_hours")
        self.assertTrue(win.higher_is_better)

    def test_lower_is_better_field_counts_a_decrease_as_the_win(self):
        rows = [day(0, social_min=200.0, sleep_hours=7.0), day(1, social_min=120.0, sleep_hours=7.0)]
        win = BehavioralInsightService.small_win(rows)
        self.assertIsNotNone(win)
        self.assertEqual(win.field, "social_min")
        self.assertFalse(win.higher_is_better)
        self.assertLess(win.delta, 0)

    def test_a_worse_day_produces_no_win(self):
        rows = [day(0, sleep_hours=8.0, social_min=60.0), day(1, sleep_hours=5.0, social_min=300.0)]
        self.assertIsNone(BehavioralInsightService.small_win(rows))


class TestFirstVsNow(unittest.TestCase):

    def test_improvement_is_measured_over_matched_windows(self):
        rows = [day(i, health_score=50.0 + i * 1.5) for i in range(12)]
        result = BehavioralInsightService.first_vs_now(rows)
        self.assertTrue(result.improved)
        self.assertGreater(result.recent_avg, result.early_avg)
        self.assertEqual(result.window, 5)

    def test_regression_is_reported_without_being_hidden(self):
        rows = [day(i, health_score=80.0 - i * 1.5) for i in range(12)]
        result = BehavioralInsightService.first_vs_now(rows)
        self.assertFalse(result.improved)
        self.assertLess(result.delta, 0)


if __name__ == "__main__":
    unittest.main()
