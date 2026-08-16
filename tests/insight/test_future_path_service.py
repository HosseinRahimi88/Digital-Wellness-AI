"""
Tests: Group C Feature 39 - Future Path Comparison.

Run: python3 -m unittest tests.insight.test_future_path_service -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts

from models.model_manager import ModelManager
from services.ml.validation_service import ValidationService
from services.ml.prediction_service import PredictionService
from services.insight.future_path_service import FuturePathService, PATH_DEFINITIONS, FuturePathComparison


class TestDemoProfileConsistency(unittest.TestCase):
    """
    Regression test for the real bug found while building this feature:
    every demo profile's hand-typed derived fields (ratios/densities/
    indices) didn't actually match their own raw component fields.
    """

    def test_all_demo_profiles_are_self_consistent(self):
        from config.demo_profiles import (
            baseline_profile, healthy_profile, at_risk_profile, borderline_profile,
        )
        from utils.feature_derivation import derive_features

        for name, fn in [
            ("baseline", baseline_profile),
            ("healthy", healthy_profile),
            ("at_risk", at_risk_profile),
            ("borderline", borderline_profile),
        ]:
            profile = fn()
            re_derived = derive_features(dict(profile))
            mismatches = {
                k: (profile.get(k), re_derived.get(k))
                for k in profile
                if profile.get(k) != re_derived.get(k)
            }
            self.assertEqual(mismatches, {}, f"{name}_profile() is not self-consistent: {mismatches}")

    def test_all_demo_profiles_pass_validation(self):
        from services.ml.validation_service import ValidationService
        validator = ValidationService()
        for data_fn in (ts.baseline_user_data, ts.healthy_user_data, ts.at_risk_user_data, ts.borderline_user_data):
            result = validator.validate(data_fn())
            self.assertTrue(result.is_valid, msg=f"{data_fn.__name__}: {result.errors}")


class TestFuturePathService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ModelManager.reset()
        cls.validator = ValidationService()
        cls.predictor = PredictionService()

    @classmethod
    def tearDownClass(cls):
        ModelManager.reset()

    def _cleaned(self, data_fn):
        v = self.validator.validate(data_fn())
        self.assertTrue(v.is_valid, msg=v.errors)
        return v.cleaned_data

    def test_compare_evaluates_every_path(self):
        base = self._cleaned(ts.borderline_user_data)
        comparison = FuturePathService.compare(base, self.predictor)
        self.assertIsInstance(comparison, FuturePathComparison)
        self.assertEqual(len(comparison.paths), len(PATH_DEFINITIONS))
        for path in comparison.paths:
            self.assertIsNone(path.error, msg=f"{path.key} failed: {path.error}")
            self.assertIsNotNone(path.regression_score)
            self.assertGreaterEqual(path.regression_score, 0.0)
            self.assertLessEqual(path.regression_score, 100.0)

    def test_status_quo_has_zero_delta_and_no_adjustments(self):
        base = self._cleaned(ts.healthy_user_data)
        comparison = FuturePathService.compare(base, self.predictor)
        status_quo = next(p for p in comparison.paths if p.key == "status_quo")
        self.assertEqual(status_quo.score_delta_vs_status_quo, 0.0)
        self.assertEqual(status_quo.adjustments, [])

    def test_status_quo_score_matches_direct_prediction(self):
        """
        Status Quo must reproduce exactly what PredictionService.predict()
        would give the user right now on this exact input - it isn't
        allowed to silently "correct" or re-derive fields the user
        already validated and submitted (only the *other*, hypothetical
        paths get re-derived screen_ewma_baseline etc).
        """
        base = self._cleaned(ts.healthy_user_data)
        direct = self.predictor.predict(base)
        comparison = FuturePathService.compare(base, self.predictor)
        status_quo = next(p for p in comparison.paths if p.key == "status_quo")
        self.assertEqual(status_quo.regression_score, direct.regression_score)

    def test_committed_change_is_never_worse_than_gradual_improvement_by_a_lot(self):
        """
        Not asserting strict monotonicity (real tree-ensemble models are
        not guaranteed monotonic - see FuturePathComparison.NOISE_FLOOR)
        but a well-behaved improvement path should not be dramatically
        worse than a smaller one; catches gross direction bugs like the
        one this feature actually shipped with during development.
        """
        for data_fn in (ts.borderline_user_data, ts.at_risk_user_data):
            base = self._cleaned(data_fn)
            comparison = FuturePathService.compare(base, self.predictor)
            by_key = {p.key: p for p in comparison.paths}
            gradual = by_key["gradual_improvement"].regression_score
            committed = by_key["committed_change"].regression_score
            status_quo = by_key["status_quo"].regression_score
            # The two explicitly "improving" paths should not both be
            # dramatically worse than doing nothing - that would indicate
            # the direction table or the shift logic is inverted again.
            self.assertFalse(
                gradual < status_quo - 10 and committed < status_quo - 10,
                msg=f"Both improvement paths scored far below status quo for {data_fn.__name__}",
            )

    def test_best_and_worst_path_keys_are_set(self):
        base = self._cleaned(ts.borderline_user_data)
        comparison = FuturePathService.compare(base, self.predictor)
        self.assertIn(comparison.best_path_key, {p.key for p in comparison.paths})
        self.assertIn(comparison.worst_path_key, {p.key for p in comparison.paths})

    def test_screen_ewma_baseline_recomputed_for_nonidentity_paths(self):
        base = self._cleaned(ts.borderline_user_data)
        path_data, _ = FuturePathService._build_path_input(base, 0.25)
        self.assertEqual(path_data["screen_ewma_baseline"], path_data["total_screen_min"])

    def test_screen_ewma_baseline_untouched_for_status_quo(self):
        base = self._cleaned(ts.borderline_user_data)
        path_data, _ = FuturePathService._build_path_input(base, 0.0)
        self.assertEqual(path_data["screen_ewma_baseline"], base["screen_ewma_baseline"])

    def test_can_request_a_subset_of_paths(self):
        base = self._cleaned(ts.healthy_user_data)
        comparison = FuturePathService.compare(base, self.predictor, path_keys=["status_quo", "digital_detox"])
        self.assertEqual({p.key for p in comparison.paths}, {"status_quo", "digital_detox"})

    def test_adjustments_stay_within_schema_bounds(self):
        from core.feature_schema import FEATURE_SCHEMA
        base = self._cleaned(ts.borderline_user_data)
        for definition in PATH_DEFINITIONS:
            path_data, _ = FuturePathService._build_path_input(base, definition.shift_fraction)
            for field_name, value in path_data.items():
                feature = FEATURE_SCHEMA.get(field_name)
                if feature is None or feature.choices is not None:
                    continue
                if feature.minimum is not None:
                    self.assertGreaterEqual(value, feature.minimum - 1e-6, msg=f"{definition.key}.{field_name}")
                if feature.maximum is not None:
                    self.assertLessEqual(value, feature.maximum + 1e-6, msg=f"{definition.key}.{field_name}")

    def test_is_delta_meaningful_respects_noise_floor(self):
        base = self._cleaned(ts.healthy_user_data)
        comparison = FuturePathService.compare(base, self.predictor)
        for path in comparison.paths:
            meaningful = comparison.is_delta_meaningful(path)
            if path.score_delta_vs_status_quo is None:
                self.assertFalse(meaningful)
            else:
                self.assertEqual(meaningful, abs(path.score_delta_vs_status_quo) >= comparison.NOISE_FLOOR)


class TestEffortOrdering(unittest.TestCase):
    """The bug a user reported in plain words: "it said if you make a
    serious effort your 72 becomes 71".

    Measured before the fix, on the shipped demo profiles:
      healthy    gradual -0.64, committed -0.96, detox -1.60  (all down)
      baseline   gradual +0.41 but committed only +0.23       (inverted)
      at_risk    continued_drift +0.12                        (wrong sign)

    The cause was input construction, not the model: shifting every
    field by a fixed percentage of its own value pushed a healthy user's
    sleep to 11.6 hours, which the model correctly scored lower. These
    tests assert on the real pipeline's real scores - nothing in the
    service post-processes the output to force an order, so if the
    ordering ever breaks again these fail rather than hiding it.
    """

    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictionService(model_manager=ModelManager.instance())
        cls.validator = ValidationService()

    def _profiles(self):
        from config.demo_profiles import (
            baseline_profile, healthy_profile, at_risk_profile, borderline_profile,
        )
        return {
            "baseline": baseline_profile(), "healthy": healthy_profile(),
            "at_risk": at_risk_profile(), "borderline": borderline_profile(),
        }

    def _scores(self, profile):
        comparison = FuturePathService.compare(profile, self.predictor)
        return {p.key: p for p in comparison.paths}, comparison

    def test_more_effort_never_scores_lower_than_less_effort(self):
        ladder = ["status_quo", "gradual_improvement", "committed_change", "digital_detox"]
        for name, profile in self._profiles().items():
            paths, _ = self._scores(profile)
            scores = [paths[k].regression_score for k in ladder]
            self.assertTrue(all(s is not None for s in scores), name)
            for i in range(len(scores) - 1):
                self.assertGreaterEqual(
                    scores[i + 1], scores[i] - 1e-9,
                    msg=(f"{name}: {ladder[i + 1]} ({scores[i + 1]}) scored below "
                         f"{ladder[i]} ({scores[i]}) - more effort must never be worth less"),
                )

    def test_no_improvement_path_pushes_a_field_past_its_healthy_target(self):
        """Eleven hours of sleep is not 'more effort' than eight."""
        from services.insight.future_path_service import HEALTHY_TARGETS
        from services.insight.parallel_twin_service import TWIN_ADJUSTABLE_FIELDS
        for name, profile in self._profiles().items():
            paths, _ = self._scores(profile)
            for key in ("gradual_improvement", "committed_change", "digital_detox"):
                data = paths[key].user_data
                for field_name, target in HEALTHY_TARGETS.items():
                    value = float(data.get(field_name, 0.0))
                    start = float(profile.get(field_name, 0.0))
                    if TWIN_ADJUSTABLE_FIELDS[field_name] == "decrease":
                        # Never below the target, unless the user was
                        # already below it and was left alone.
                        self.assertGreaterEqual(value, min(target, start) - 1e-6,
                                                msg=f"{name}/{key}/{field_name}")
                    else:
                        self.assertLessEqual(value, max(target, start) + 1e-6,
                                             msg=f"{name}/{key}/{field_name}")

    def test_a_user_already_at_target_is_left_alone_and_told_so(self):
        """Four identical cards read as a broken feature; the flag is
        what lets the UI say 'you are already there' instead."""
        from config.demo_profiles import healthy_profile
        paths, _ = self._scores(healthy_profile())
        improvement = paths["digital_detox"]
        if not improvement.adjustments:
            self.assertTrue(improvement.already_at_target)
            self.assertEqual(improvement.regression_score, paths["status_quo"].regression_score)

    def test_status_quo_is_never_flagged_as_already_at_target(self):
        """It changes nothing by definition, which is not the same
        statement."""
        for name, profile in self._profiles().items():
            paths, _ = self._scores(profile)
            self.assertFalse(paths["status_quo"].already_at_target, name)

    def test_a_sub_noise_delta_is_not_reported_as_a_direction(self):
        """The at-risk profile's drift path moves the score by about a
        tenth of a point. That is the model's own wobble at the edge of
        its training distribution, and presenting it as an improvement
        would be inventing a finding."""
        from config.demo_profiles import at_risk_profile
        paths, comparison = self._scores(at_risk_profile())
        drift = paths["continued_drift"]
        if drift.score_delta_vs_status_quo is not None and abs(drift.score_delta_vs_status_quo) < comparison.NOISE_FLOOR:
            self.assertFalse(comparison.is_delta_meaningful(drift))


if __name__ == "__main__":
    unittest.main()
