"""
Tests: personal (not just absolute) signal severity, and telling
consistency apart from improvement.

Both come from the same complaint - that the app was reading the user
against fixed numbers instead of against themselves.

W1. Plan severity was purely absolute: a fixed threshold per field.
    That misses a real personal regression (8h of sleep down to 6.5h is
    worth naming even though 6.5h is not alarming), and it is the only
    thing standing between a chronically bad habit and being excused,
    so it cannot simply be replaced by a personal baseline either -
    someone who always sleeps four hours must not be told their sleep
    is fine because it matches their own normal.

    The rule is therefore max(absolute, personal): personalisation can
    raise urgency, never lower it below the absolute floor. Both halves
    are tested, including the case where each one alone gets it wrong.

W2. before_after reported only a delta between two averages, so a user
    holding 82-83 all week and a user who genuinely went nowhere both
    came back as "not a meaningful difference". Steadiness and
    direction are independent axes and are now both reported; a flat
    run at a strong level is a distinct, named outcome rather than the
    absence of one.

Run: python3 -m unittest tests.test_personal_signals -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap

from services.improvement_plan_service import ImprovementPlanService
from services.progress_service import (
    STEADY_STRONG_SCORE, VOLATILE_SD, ProgressService,
)

HEALTHY = {
    "sleep_hours": 8.0, "social_min": 40, "stress_0_10": 3,
    "physical_activity_min_per_day": 45, "notifications_per_day": 50,
    "focus_0_100": 80,
}


def _history(**overrides) -> list[dict]:
    row = dict(HEALTHY)
    row.update(overrides)
    return [dict(row) for _ in range(8)]


def _days(scores: list[float]) -> list[dict]:
    return [
        {"date": f"2026-01-{i + 1:02d}", "health_score": s}
        for i, s in enumerate(scores)
    ]


class TestHybridSeverity(unittest.TestCase):

    def setUp(self):
        self.service = ImprovementPlanService()

    def _focus(self, user_data, history=None, schedule_type=None):
        return self.service.generate(
            "Healthy", 80, None, user_data,
            history=history, schedule_type=schedule_type,
        ).focus_areas

    def test_a_personal_drop_is_caught_where_the_absolute_floor_says_fine(self):
        # focus_0_100 = 64 clears the absolute threshold of 60, so the
        # old purely-absolute rule flagged nothing at all here.
        slipped = dict(HEALTHY, focus_0_100=64)
        self.assertEqual(
            self._focus(slipped), ["Maintain Your Momentum"],
            "absolute-only should see nothing wrong with 64",
        )
        self.assertIn(
            "Deep Focus", self._focus(slipped, history=_history(focus_0_100=80)),
            "a drop from a personal baseline of 80 to 64 should be flagged",
        )

    def test_a_chronic_habit_is_not_excused_by_the_users_own_baseline(self):
        # The failure mode of a purely personal rule: four hours is this
        # user's normal, so "compared to yourself" says everything is
        # fine. The absolute floor has to win here.
        chronic = dict(HEALTHY, sleep_hours=4.0)
        history = _history(sleep_hours=4.0)
        self.assertEqual(
            self.service.personal_baselines(history, ["sleep_hours"]),
            {"sleep_hours": 4.0},
            "sanity: the baseline really is the bad value",
        )
        self.assertIn(
            "Sleep Recovery", self._focus(chronic, history=history),
            "a chronically low value must stay flagged even when it "
            "matches the user's own baseline",
        )

    def test_personalisation_never_lowers_urgency(self):
        # Someone whose baseline is worse than today must not have
        # today's genuinely bad value softened by the comparison.
        bad_today = dict(HEALTHY, sleep_hours=5.0)
        worse_baseline = _history(sleep_hours=3.0)
        self.assertIn("Sleep Recovery", self._focus(bad_today))
        self.assertIn(
            "Sleep Recovery", self._focus(bad_today, history=worse_baseline),
            "a worse baseline must not excuse a bad value",
        )

    def test_baselines_ignore_exception_days(self):
        """A day the user marked as unusual must not define their normal.

        Sized so the filter is actually load-bearing: the baseline is a
        median, which shrugs off a single outlier, so appending one
        excluded row proves nothing - that version of this test passed
        with the filter deleted. Four normal days against four excluded
        ones moves the median from 8.0 to 5.0 if exceptions leak in.
        """
        history = [{"sleep_hours": 8.0} for _ in range(4)]
        history += [{"sleep_hours": 2.0, "excluded": True} for _ in range(4)]
        self.assertEqual(
            self.service.personal_baselines(history, ["sleep_hours"]),
            {"sleep_hours": 8.0},
            "excluded days leaked into the personal baseline",
        )

    def test_a_baseline_needs_enough_days_to_exist(self):
        self.assertEqual(
            self.service.personal_baselines(
                [{"sleep_hours": 8.0}, {"sleep_hours": 7.5}], ["sleep_hours"],
            ),
            {}, "two points should not define a baseline",
        )

    def test_no_history_behaves_exactly_like_the_old_absolute_rule(self):
        # The compatibility guarantee: every existing caller that passes
        # no history keeps its previous behaviour.
        bad = dict(HEALTHY, sleep_hours=5.0, social_min=200)
        self.assertEqual(self._focus(bad), self._focus(bad, history=[]))

    def test_an_irregular_schedule_reranks_routine_themes(self):
        # sleep and notifications are close in severity here, so the
        # boost is what decides the order.
        close = dict(HEALTHY, sleep_hours=5.6, notifications_per_day=125)
        standard = self._focus(close, schedule_type="standard_day")
        rotating = self._focus(close, schedule_type="rotating_shift")
        self.assertEqual(standard[0], "Mindful Notifications")
        self.assertEqual(
            rotating[0], "Sleep Recovery",
            "an irregular schedule should lift the routine-anchored theme",
        )

    def test_the_schedule_boost_cannot_invent_a_focus_area(self):
        # It re-ranks what the numbers flagged; it never adds a theme.
        self.assertEqual(
            self._focus(dict(HEALTHY), schedule_type="rotating_shift"),
            ["Maintain Your Momentum"],
        )


class TestConsistencyIsNotImprovement(unittest.TestCase):

    def _pattern(self, scores):
        return ProgressService.before_after(_days(scores)).pattern

    def test_holding_a_strong_level_is_its_own_outcome(self):
        # The reported bug: this used to be indistinguishable from
        # "nothing happened".
        self.assertEqual(self._pattern([82, 83, 81, 82, 84, 83]), "steady_strong")

    def test_flat_and_low_is_not_the_same_as_flat_and_strong(self):
        self.assertEqual(self._pattern([48, 47, 49, 48, 50, 47]), "steady_low")

    def test_a_real_climb_is_distinct_from_holding_steady(self):
        self.assertEqual(self._pattern([55, 58, 62, 68, 72, 75]), "improving_steady")

    def test_a_climb_with_big_swings_is_reported_as_unstable(self):
        self.assertEqual(self._pattern([45, 70, 50, 78, 60, 88]), "improving_volatile")

    def test_a_flat_average_hiding_wild_days_is_not_called_steady(self):
        # Same average both halves, but nothing about this is consistent.
        pattern = self._pattern([40, 95, 45, 92, 42, 90])
        self.assertIn(pattern, {"volatile", "improving_volatile", "declining_volatile"})
        self.assertNotIn(pattern, {"steady_strong", "steady_low"})

    def test_a_slow_slide_is_reported_as_declining(self):
        self.assertEqual(self._pattern([80, 78, 75, 72, 69, 66]), "declining_steady")

    def test_consistency_is_a_number_not_just_a_label(self):
        steady = ProgressService.before_after(_days([82, 83, 81, 82, 84, 83]))
        swingy = ProgressService.before_after(_days([40, 95, 45, 92, 42, 90]))
        self.assertGreater(steady.consistency, 0.85)
        self.assertLess(swingy.consistency, 0.2)
        self.assertLess(steady.after_sd, VOLATILE_SD)
        self.assertGreater(swingy.after_sd, VOLATILE_SD)

    def test_the_strong_low_boundary_is_the_documented_one(self):
        just_over = STEADY_STRONG_SCORE + 1
        just_under = STEADY_STRONG_SCORE - 1
        self.assertEqual(self._pattern([just_over] * 6), "steady_strong")
        self.assertEqual(self._pattern([just_under] * 6), "steady_low")

    def test_too_little_history_still_declines_cleanly(self):
        self.assertFalse(ProgressService.before_after(_days([70, 72])).available)


if __name__ == "__main__":
    unittest.main()
