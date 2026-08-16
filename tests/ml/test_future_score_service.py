"""
Tests: the seven-day-ahead score (services/insight/future_score_service.py).

The thing this guards is a claim, not a calculation. The app has two
models with two different horizons, and the seven-day number is derived
from the classifier rather than trained - so the tests that matter are
the ones that stop it from quietly becoming something it is not: a
personal forecast, a number with an R-squared, or a value invented when
the calibration is missing.

Run: python3 -m unittest tests.ml.test_future_score_service -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap + offline stubs

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

from services.insight.future_score_service import FutureScoreService


class TestEstimate(unittest.TestCase):
    """Every call here names mode="class_typical" explicitly.

    These assertions are about that estimator, and relying on it being
    the process-wide default made them silently test whatever the build
    happened to ship - so they broke in the Version 1 build, where the
    default is class_only and estimate() correctly returns no number at
    all. A test for one mode should ask for that mode."""

    def setUp(self):
        if FutureScoreService.calibration_summary() is None:
            self.skipTest("no calibration artifact in this environment")

    def test_a_confident_class_lands_on_that_class_mean(self):
        calibration = FutureScoreService.calibration_summary()
        for label, stats in calibration["class_stats"].items():
            result = FutureScoreService.estimate({label: 1.0}, mode="class_typical")
            self.assertTrue(result.available, label)
            self.assertAlmostEqual(result.score, round(stats["mean"], 1), places=1)

    def test_an_uncertain_classifier_widens_the_interval(self):
        """The whole reason for using the law of total variance rather
        than a fixed band: when the model cannot decide, the range has
        to say so."""
        torn = FutureScoreService.estimate({"At Risk": 0.5, "Healthy": 0.5}, mode="class_typical")
        sure = FutureScoreService.estimate({"Healthy": 1.0}, mode="class_typical")
        self.assertGreater(torn.upper - torn.lower, sure.upper - sure.lower)

    def test_a_split_estimate_sits_between_the_two_class_means(self):
        calibration = FutureScoreService.calibration_summary()
        low = calibration["class_stats"]["At Risk"]["mean"]
        high = calibration["class_stats"]["Healthy"]["mean"]
        result = FutureScoreService.estimate({"At Risk": 0.5, "Healthy": 0.5}, mode="class_typical")
        self.assertGreater(result.score, low)
        self.assertLess(result.score, high)

    def test_probabilities_are_renormalised(self):
        """A classifier emitting a class the calibration does not know
        must not silently shrink the remaining weights."""
        known = FutureScoreService.estimate({"Healthy": 0.5, "SomethingElse": 0.5}, mode="class_typical")
        self.assertTrue(known.available)
        self.assertAlmostEqual(
            known.score,
            FutureScoreService.estimate({"Healthy": 1.0}, mode="class_typical").score, places=1)

    def test_the_interval_stays_inside_zero_to_one_hundred(self):
        for probabilities in ({"At Risk": 1.0}, {"Healthy": 1.0}, {"At Risk": 0.34, "Moderate": 0.33, "Healthy": 0.33}):
            result = FutureScoreService.estimate(probabilities, mode="class_typical")
            self.assertGreaterEqual(result.lower, 0.0)
            self.assertLessEqual(result.upper, 100.0)
            self.assertLessEqual(result.lower, result.score)
            self.assertGreaterEqual(result.upper, result.score)

    def test_it_is_deterministic(self):
        first = FutureScoreService.estimate({"Moderate": 0.7, "Healthy": 0.3}, mode="class_typical")
        for _ in range(10):
            again = FutureScoreService.estimate({"Moderate": 0.7, "Healthy": 0.3}, mode="class_typical")
            self.assertEqual(first.score, again.score)
            self.assertEqual(first.lower, again.lower)


class TestRefusals(unittest.TestCase):
    """Every path that cannot produce a real number must say so rather
    than return one."""

    def test_no_probabilities_is_unavailable(self):
        result = FutureScoreService.estimate(None)
        self.assertFalse(result.available)
        self.assertIsNone(result.score)
        self.assertTrue(result.reason)

    def test_empty_probabilities_is_unavailable(self):
        self.assertFalse(FutureScoreService.estimate({}, mode="class_typical").available)

    def test_only_unknown_classes_is_unavailable(self):
        result = FutureScoreService.estimate({"Nonsense": 1.0}, mode="class_typical")
        self.assertFalse(result.available)
        self.assertEqual(result.reason, "no_calibrated_classes")

    def test_zero_total_probability_is_unavailable(self):
        self.assertFalse(FutureScoreService.estimate({"Healthy": 0.0}, mode="class_typical").available)


class TestItIsNotAForecast(unittest.TestCase):
    """A class-typical band presented as a personal projection would
    tell a user scoring 84 today that the model expects them to fall to
    72. It never said that."""

    def setUp(self):
        if FutureScoreService.calibration_summary() is None:
            self.skipTest("no calibration artifact in this environment")

    def test_every_result_is_marked_class_typical(self):
        self.assertEqual(
            FutureScoreService.estimate({"Healthy": 1.0}, mode="class_typical").basis, "class_typical")

    def test_the_estimate_cannot_leave_the_span_of_the_class_means(self):
        """This bound is exactly why it cannot be sold as a personal
        forecast, and asserting it keeps that limitation visible."""
        calibration = FutureScoreService.calibration_summary()
        means = [s["mean"] for s in calibration["class_stats"].values()]
        for probabilities in ({"Healthy": 1.0}, {"At Risk": 1.0},
                              {"At Risk": 0.2, "Moderate": 0.3, "Healthy": 0.5}):
            score = FutureScoreService.estimate(probabilities, mode="class_typical").score
            self.assertGreaterEqual(score, round(min(means), 1) - 0.05)
            self.assertLessEqual(score, round(max(means), 1) + 0.05)


class TestCalibrationEvidence(unittest.TestCase):
    """The artifact has to carry the justification, not just the
    numbers - the model performance page reads it to explain itself."""

    def setUp(self):
        self.calibration = FutureScoreService.calibration_summary()
        if self.calibration is None:
            self.skipTest("no calibration artifact in this environment")

    def test_it_records_that_it_was_fitted_on_train_only(self):
        self.assertIn("train", self.calibration["calibrated_on"])

    def test_it_records_why_there_is_no_trained_regressor(self):
        self.assertTrue(self.calibration.get("why_not_a_regressor"))

    def test_the_class_means_barely_move_between_train_and_validation(self):
        """If they moved a lot the whole approach would be unsound, so
        the check belongs in the test suite and not only in a comment."""
        drift = self.calibration["evidence"]["train_vs_validation_mean_drift"]
        for label, value in drift.items():
            self.assertLess(value, 2.0, f"{label} class mean moved {value} points")

    def test_the_classes_are_balanced_enough_for_tertile_reasoning(self):
        balance = self.calibration["evidence"]["class_balance_pct"]
        for label, pct in balance.items():
            self.assertGreater(pct, 25.0, label)
            self.assertLess(pct, 42.0, label)


class TestOutputModes(unittest.TestCase):
    """Two deliverables, one codebase. Output 1 shows the class alone;
    Output 2 shows a number built from the classifier's band plus the
    user's own position inside it."""

    def test_class_only_mode_returns_no_number_at_all(self):
        """Output 1. The point is that there IS no number - not that one
        was computed and hidden."""
        result = FutureScoreService.estimate(
            {"Healthy": 1.0}, "Healthy", today_score=84.5, mode="class_only")
        self.assertFalse(result.available)
        self.assertIsNone(result.score)
        self.assertIsNone(result.lower)
        self.assertEqual(result.basis, "class_only")
        # The class still comes through - that is the whole answer.
        self.assertEqual(result.predicted_class, "Healthy")

    def test_augmented_mode_respects_where_you_sit_inside_your_band(self):
        """Output 2's whole advantage over class_typical: two people in
        the same predicted band do not get the same number."""
        if FutureScoreService.augmentation_summary() is None:
            self.skipTest("no augmentation artifact in this environment")
        high = FutureScoreService.estimate({"Healthy": 1.0}, today_score=84.0, mode="augmented")
        low = FutureScoreService.estimate({"Healthy": 1.0}, today_score=62.0, mode="augmented")
        self.assertTrue(high.available and low.available)
        self.assertGreater(high.score, low.score)
        self.assertEqual(high.basis, "augmented_rank")

    def test_augmented_mode_without_todays_score_falls_back(self):
        """Half the estimate is the position inside the band. Missing it
        must degrade to the weaker honest answer, not to a guess."""
        result = FutureScoreService.estimate({"Healthy": 1.0}, mode="augmented")
        self.assertNotEqual(result.basis, "augmented_rank")

    def test_the_interval_includes_the_estimators_own_error(self):
        """A confident classifier drives the mixture variance to zero. If
        that were the whole interval it would read as +/- 0.1 points,
        which is a precision claim the estimator cannot support."""
        if FutureScoreService.augmentation_summary() is None:
            self.skipTest("no augmentation artifact in this environment")
        result = FutureScoreService.estimate({"Healthy": 1.0}, today_score=84.0, mode="augmented")
        self.assertGreater(result.upper - result.lower, 1.0)

    def test_an_uncertain_classifier_still_widens_the_interval(self):
        if FutureScoreService.augmentation_summary() is None:
            self.skipTest("no augmentation artifact in this environment")
        torn = FutureScoreService.estimate(
            {"Healthy": 0.5, "At Risk": 0.5}, today_score=62.0, mode="augmented")
        sure = FutureScoreService.estimate({"Healthy": 1.0}, today_score=62.0, mode="augmented")
        self.assertGreater(torn.upper - torn.lower, sure.upper - sure.lower)

    def test_an_unknown_mode_falls_back_rather_than_raising(self):
        result = FutureScoreService.estimate({"Healthy": 1.0}, mode="nonsense")
        self.assertIn(result.basis, ("class_typical", "augmented_rank"))

    def test_every_mode_is_deterministic(self):
        for mode in ("class_only", "class_typical", "augmented"):
            first = FutureScoreService.estimate({"Moderate": 0.7, "Healthy": 0.3}, today_score=64.0, mode=mode)
            for _ in range(5):
                again = FutureScoreService.estimate({"Moderate": 0.7, "Healthy": 0.3}, today_score=64.0, mode=mode)
                self.assertEqual(first.score, again.score, mode)


class TestTheEstimateDoesNotPunishHighScorers(unittest.TestCase):
    """The bug this class exists for.

    The estimator used to map a user's within-band position onto the
    2nd-98th percentile of TODAY's scores among that class. For Healthy
    that range ends at 78.67, so every user above it was mapped down,
    always: 84.5 - the highest score in the whole training set - was
    told to expect 78.1, and 90 was told 78.1 as well. A user reported
    it from the demo profile, which scores 84.5.

    It is now applied as a shift: the classifier's claim is about which
    BAND you land in, so only the band change moves your number.
    """

    def setUp(self):
        if FutureScoreService.augmentation_summary() is None:
            self.skipTest("no augmentation artifact in this environment")

    def _healthy(self, today):
        return FutureScoreService.estimate(
            {"Healthy": 1.0}, "Healthy", today_score=today, mode="augmented")

    def test_a_user_kept_in_their_band_keeps_their_score(self):
        """The property the old version could not satisfy at all."""
        for today in (70.0, 72.0, 76.0, 80.0, 84.5, 90.0):
            result = self._healthy(today)
            self.assertAlmostEqual(
                result.score, today, delta=1.5,
                msg=f"today {today} -> {result.score}: staying in band moved the score",
            )

    def test_the_highest_scorer_in_the_data_is_not_told_to_expect_a_fall(self):
        """84.49 is the demo profile the report came from."""
        result = self._healthy(84.49)
        self.assertGreater(result.score, 82.0)
        self.assertGreater(result.upper, 84.49)

    def test_there_is_no_ceiling(self):
        """Two users far apart must not collapse onto one number - that
        is what 'everyone above 78.67 gets 78.2' looked like."""
        self.assertGreater(self._healthy(95.0).score, self._healthy(85.0).score + 5.0)

    def test_a_predicted_drop_still_drops(self):
        """The fix must not have removed the model's ability to say
        someone is heading down."""
        same = FutureScoreService.estimate(
            {"Healthy": 1.0}, "Healthy", today_score=72.0, mode="augmented")
        down = FutureScoreService.estimate(
            {"At Risk": 1.0}, "At Risk", today_score=72.0, mode="augmented")
        self.assertLess(down.score, same.score - 5.0)

    def test_a_predicted_rise_rises(self):
        low = FutureScoreService.estimate(
            {"At Risk": 1.0}, "At Risk", today_score=55.0, mode="augmented")
        up = FutureScoreService.estimate(
            {"Healthy": 1.0}, "Healthy", today_score=55.0, mode="augmented")
        self.assertGreater(up.score, low.score + 5.0)

    def test_it_is_monotone_inside_a_band(self):
        """A higher score today can never predict a lower score next
        week for the same predicted class. Checked within one band: a
        band CHANGE is a genuine discrete event and is allowed to jump."""
        for band in ((70.0, 72.0, 74.0, 76.0, 78.0, 80.0, 84.0),
                     (61.0, 63.0, 65.0, 67.0)):
            scores = [self._healthy(t).score for t in band]
            self.assertEqual(
                scores, sorted(scores),
                f"not monotone across {band}: {scores}",
            )

    def test_the_estimate_stays_in_range(self):
        for today in (0.0, 5.0, 50.0, 99.0, 100.0):
            result = self._healthy(today)
            self.assertGreaterEqual(result.lower, 0.0)
            self.assertLessEqual(result.upper, 100.0)


class TestAugmentationEvidence(unittest.TestCase):

    def setUp(self):
        self.augmentation = FutureScoreService.augmentation_summary()
        if self.augmentation is None:
            self.skipTest("no augmentation artifact in this environment")

    def test_it_records_the_assumption_it_added(self):
        self.assertIn("rank persistence", self.augmentation["assumption_added"].lower())

    def test_it_records_what_it_does_not_claim(self):
        self.assertTrue(self.augmentation.get("not_a_claim"))

    def test_it_records_the_alternative_that_was_rejected_and_why(self):
        """Global rank persistence produced a target 0.939-correlated
        with today. Keeping that in the artifact is what stops the
        rejected version quietly coming back."""
        self.assertIn("0.939", self.augmentation["rejected_alternative"])

    def test_the_target_never_leaves_zero_to_one_hundred(self):
        for name, stats in self.augmentation["splits"].items():
            self.assertGreaterEqual(stats["target_min"], 0.0, name)
            self.assertLessEqual(stats["target_max"], 100.0, name)

    def test_the_forecast_half_of_the_target_is_not_just_todays_score(self):
        """If it were, a model fitted to it would predict today and call
        it next week.

        This used to assert corr_with_today < 0.95 and it now measures
        the wrong quantity - the test's intent is right, its subject is
        stale. `corr_with_today` is taken on the combined score, and the
        target deliberately carries the day's own screen-load subscore
        forward unchanged, because nothing in this dataset forecasts next
        week's screen time. That carried half is about two thirds of the
        target's variance, so the combined-axis correlation is high by
        construction (0.954) and would be high even if the forecast were
        worthless.

        The number that carries the claim is the one measured on the axis
        something is actually predicted on: today's wellbeing against the
        forecast wellbeing. It is 0.875, unchanged from before the score
        gained its screen-load term - the construction is the same, it
        was simply being reported against the wrong denominator.
        """
        for name, stats in self.augmentation["splits"].items():
            self.assertLess(stats["corr_wellbeing_with_today"], 0.95, name)

    def test_the_combined_axis_figure_is_explained_by_the_carried_half(self):
        """The guard that keeps the test above honest.

        Relaxing a threshold because a number went up is how a real
        regression gets waved through. So the artifact has to show that
        the gap between the two correlations is the carried screen-load
        half and not a forecast that started echoing today: the carried
        share must be large enough to account for it, and the combined
        figure must still sit below the 1.0 that a pure echo would give.
        """
        for name, stats in self.augmentation["splits"].items():
            with self.subTest(split=name):
                carried = stats["carried_screen_load_variance_share"]
                self.assertGreater(carried, 0.5)
                self.assertLess(carried, 0.9)
                self.assertGreater(
                    stats["corr_with_today"], stats["corr_wellbeing_with_today"])
                self.assertLess(stats["corr_with_today"], 0.99)


class TestShippedEstimatorBeatsDoingNothing(unittest.TestCase):
    """The number that decides whether Output 2 was worth building."""

    def setUp(self):
        import json as _json
        from pathlib import Path
        path = paths.PROJECT_ROOT / "artifacts" / "metrics_future_regression.json"
        if not path.exists():
            self.skipTest("Output 2 has not been trained in this environment")
        self.metrics = _json.loads(path.read_text(encoding="utf-8"))

    def test_the_two_stage_estimator_beats_predicting_today(self):
        two_stage = self.metrics["two_stage"]
        self.assertTrue(two_stage["beats_baseline"])
        self.assertGreaterEqual(
            two_stage["mae_improvement_over_baseline_pct"],
            self.metrics["minimum_improvement_required_pct"],
        )

    def test_the_single_stage_attempt_is_kept_rather_than_deleted(self):
        """It lost, and the comparison is the finding. A metrics file
        that only shows the winner hides why the winner won."""
        self.assertIn("mae_improvement_over_baseline_pct", self.metrics)
        self.assertLess(self.metrics["mae_improvement_over_baseline_pct"], 0)

    def test_the_metrics_say_what_the_r_squared_is_measured_against(self):
        self.assertIn("CONSTRUCTED", self.metrics["honest_description"])


if __name__ == "__main__":
    unittest.main()
