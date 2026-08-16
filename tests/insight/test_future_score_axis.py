"""The seven-day figure is built on the axis the label actually bands.

The defect these tests exist for. `health_score_0_100` used to be the
mean of six wellbeing subscores, and `future_health_class_7d` is very
nearly a tertile band of that mean - they agree 80.2% of the time, which
is the single fact the whole seven-day estimator rests on.

Then the score gained a seventh, screen-load term. It now measures two
things that correlate -0.006 with each other, and the label bands only
one of them: against the combined score, tertile membership agrees 43.3%
of the time, against 33.3% by chance. Every piece of machinery that
reads "the class is a band of the score" was quietly calibrating against
a relationship that had stopped existing.

So the bands, the class means and the within-band ranks are all on the
wellbeing axis, and the screen-load half is CARRIED FORWARD from the
user's own day rather than forecast - nothing in this dataset predicts
next week's screen time, and the label leans the wrong way when asked.

These tests pin that split, because the failure mode is silent: every
number still renders, they are just on the wrong scale.
"""

from __future__ import annotations

import json
import unittest

from core import paths
from models.data_loader import (
    SCREEN_LOAD_WEIGHT,
    SUBSCORE_COLUMNS,
    WELLBEING_COLUMN,
)

CALIBRATION = paths.ARTIFACTS_DIR / "future_score_calibration.json"
AUGMENTATION = paths.ARTIFACTS_DIR / "future_score_augmentation.json"


def _load(path):
    if not path.exists():
        raise unittest.SkipTest(f"{path.name} is not present")
    return json.loads(path.read_text(encoding="utf-8"))


class TestTheArtifactsDeclareTheirAxis(unittest.TestCase):
    def test_the_calibration_is_measured_on_wellbeing_not_the_score(self):
        # The specific regression: calibrating on health_score_0_100
        # measured 43.3% tertile agreement against 33.3% by chance.
        self.assertEqual(_load(CALIBRATION)["score_column"], WELLBEING_COLUMN)

    def test_the_augmentation_declares_the_same_axis(self):
        self.assertEqual(_load(AUGMENTATION)["band_axis"], WELLBEING_COLUMN)

    def test_both_publish_the_weights_needed_to_recombine(self):
        for path in (CALIBRATION, AUGMENTATION):
            with self.subTest(artifact=path.name):
                block = _load(path)["recombination"]
                self.assertEqual(block["subscore_weight"], float(len(SUBSCORE_COLUMNS)))
                self.assertEqual(block["screen_load_weight"], float(SCREEN_LOAD_WEIGHT))

    def test_the_weights_match_the_score_definition(self):
        # Published rather than hard-coded in the service precisely so
        # this can be checked instead of assumed.
        block = _load(CALIBRATION)["recombination"]
        total = block["subscore_weight"] + block["screen_load_weight"]
        self.assertEqual(total, len(SUBSCORE_COLUMNS) + SCREEN_LOAD_WEIGHT)

    def test_the_class_means_are_on_the_wellbeing_scale(self):
        # On the wellbeing axis the three classes separate cleanly with
        # tight spreads. On the combined score they collapse toward each
        # other (59.0/63.7/70.8) with standard deviations near 9, which
        # is what a broken axis looks like from the outside.
        stats = _load(CALIBRATION)["class_stats"]
        means = sorted(s["mean"] for s in stats.values())
        self.assertGreater(means[-1] - means[0], 12.0)
        for label, stat in stats.items():
            with self.subTest(label=label):
                self.assertLess(stat["std"], 6.0)

    def test_the_tertile_agreement_is_the_one_the_method_relies_on(self):
        evidence = _load(CALIBRATION)["evidence"]
        agreement = evidence["tertile_membership_agrees_with_label_pct"]
        # Comfortably above the 43.3% the combined score gave, and far
        # above the 33.3% three balanced classes give by chance.
        self.assertGreater(agreement, 75.0)


class TestTheWellbeingHalfIsRecoveredExactly(unittest.TestCase):
    """Serving has the score and the user's own minute fields, so the
    wellbeing half is arithmetic rather than an estimate."""

    def setUp(self):
        from services.insight.future_score_service import _wellbeing_today
        self.recover = _wellbeing_today
        self.source = _load(CALIBRATION)

    def _combine(self, wellbeing: float, load: float) -> float:
        block = self.source["recombination"]
        total = block["subscore_weight"] + block["screen_load_weight"]
        return (block["subscore_weight"] * wellbeing
                + block["screen_load_weight"] * load) / total

    def test_it_inverts_the_combination(self):
        for wellbeing, load in ((78.0, 21.7), (55.0, 100.0), (64.0, 0.0),
                                (70.5, 66.67), (40.0, 33.33)):
            with self.subTest(wellbeing=wellbeing, load=load):
                score = self._combine(wellbeing, load)
                self.assertAlmostEqual(
                    self.recover(score, load, self.source), wellbeing, places=6)

    def test_a_perfect_screen_day_leaves_wellbeing_below_the_score(self):
        # Sanity in the direction a reader would check: someone with a
        # spotless screen day has a score flattered by it.
        score = self._combine(60.0, 100.0)
        self.assertLess(self.recover(score, 100.0, self.source), score)

    def test_without_a_screen_load_it_refuses_rather_than_assumes(self):
        self.assertIsNone(self.recover(70.0, None, self.source))


class TestTheEstimateLandsOnTheScoreScale(unittest.TestCase):
    def setUp(self):
        from services.insight.future_score_service import FutureScoreService
        self.service = FutureScoreService

    def test_a_confident_class_returns_a_number_near_the_users_own_score(self):
        # The defining property of the augmented estimator: a user the
        # classifier keeps in their current band gets their own number
        # back, because the band change is applied as a shift.
        result = self.service.estimate(
            {"Healthy": 0.98, "Moderate": 0.02, "At Risk": 0.0},
            "Healthy", today_score=72.0, screen_load_today=66.67,
        )
        if not result.available:
            self.skipTest(f"estimator unavailable: {result.reason}")
        self.assertLess(abs(result.score - 72.0), 12.0)

    def test_the_same_day_with_a_heavier_screen_load_forecasts_lower(self):
        # Two people the classifier says the same thing about, whose
        # scores differ only through digital load, must not come back
        # with the same seven-day number - that was the whole bug.
        probabilities = {"Healthy": 0.6, "Moderate": 0.3, "At Risk": 0.1}
        light = self.service.estimate(
            probabilities, "Healthy", today_score=72.0, screen_load_today=100.0)
        heavy = self.service.estimate(
            probabilities, "Healthy", today_score=57.0, screen_load_today=21.68)
        if not (light.available and heavy.available):
            self.skipTest("estimator unavailable")
        self.assertGreater(light.score, heavy.score)

    def test_it_still_answers_without_a_screen_load(self):
        # Degrades to a wellbeing-axis answer rather than failing; the
        # caller is told which via `basis`.
        result = self.service.estimate(
            {"Healthy": 0.5, "Moderate": 0.3, "At Risk": 0.2},
            "Healthy", today_score=68.0,
        )
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
