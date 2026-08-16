"""The weekly band's half-width is a prediction, and it has to behave.

What this pins, in order of how badly each one would hurt:

  1. train/serve parity. utils/band_features.py is imported by both the
     trainer and the service; if its column list and the fitted
     artifact's ever disagree, the vector means something different at
     every position past the mismatch and the model returns confident
     nonsense. The service refuses to load in that case, and that
     refusal is tested rather than trusted.
  2. graceful degradation. No artifact, a corrupt artifact, a user with
     no days - every one of those has to fall back to the old constant,
     because a broken pickle must never cost somebody their weekly plan.
  3. the band is still the band. The centre is the weighted mean, the
     window is symmetric, and the 0-100 clamp holds. Only the WIDTH is
     new; every other rule the weekly plan runs on is unchanged.
  4. it is actually personal. A calm week and an erratic week must not
     come back with the same number - otherwise this is a constant with
     extra steps.
"""
from __future__ import annotations

import json
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

from tests.api.test_api import APITestCase

from services.ml import band_model_service
from services.wellness.plan_lock_service import BAND_HALF_WIDTH, is_outside_band, week_band
from utils.band_features import (
    PRIOR_FEATURES,
    BAND_FEATURE_COLUMNS,
    HABIT_FEATURES,
    SEQUENCE_FEATURES,
    band_feature_vector,
    build_band_features,
)

ARTIFACT = paths.artifact("band_model.pkl")

CALM = [66.0, 66.4, 65.8, 66.2, 66.1]
ERRATIC = [55.0, 74.0, 58.0, 79.0, 61.0]


class TestBandFeatures(unittest.TestCase):
    """The shared feature builder - the only thing both sides agree on."""

    def test_every_declared_column_is_produced(self):
        features = build_band_features(CALM)
        self.assertEqual(sorted(features), sorted(BAND_FEATURE_COLUMNS))

    def test_the_vector_is_in_the_declared_order(self):
        features = build_band_features(CALM)
        self.assertEqual(
            band_feature_vector(CALM),
            [features[name] for name in BAND_FEATURE_COLUMNS],
        )

    def test_columns_are_sequence_then_prior_then_habit_with_nothing_lost(self):
        """The order IS the wire format - the trained model's columns are
        stored beside it and verified on load, so a reordering here is a
        silently wrong prediction rather than an error."""
        self.assertEqual(
            BAND_FEATURE_COLUMNS,
            SEQUENCE_FEATURES + PRIOR_FEATURES + HABIT_FEATURES,
        )

    def test_the_prior_block_is_missing_rather_than_zero_without_history(self):
        """A first-week user has no earlier days. Reporting 0.0 spread
        would tell the model "this person never moves", which is the
        opposite of "we have not seen them yet" - and it is the calm
        end of the axis, so it would hand them the narrowest band in
        the app on the strength of no evidence at all."""
        features = build_band_features(CALM)
        for name in PRIOR_FEATURES:
            with self.subTest(feature=name):
                self.assertNotEqual(
                    features[name], features[name], f"{name} should be NaN",
                )

    def test_the_prior_block_reads_the_earlier_days(self):
        steady = build_band_features(CALM, prior_scores=[70.0, 70.5, 69.8, 70.2, 70.1])
        swinging = build_band_features(CALM, prior_scores=[55.0, 82.0, 61.0, 88.0, 64.0])
        self.assertEqual(steady["prior_days"], 5.0)
        self.assertLess(
            steady["prior_sd"], swinging["prior_sd"],
            "the prior block cannot tell a steady history from a swinging one",
        )
        self.assertLess(steady["prior_dev_mean"], swinging["prior_dev_mean"])

    def test_dispersion_of_one_day_is_missing_not_zero(self):
        # The SD of a single number is undefined. Reporting 0.0 would
        # tell the model "this person never moves", which is the exact
        # opposite of "we do not know yet".
        features = build_band_features([70.0])
        for name in ("score_sd", "score_mad", "score_range", "diff_mean", "slope"):
            with self.subTest(feature=name):
                self.assertNotEqual(features[name], features[name], f"{name} should be NaN")
        self.assertEqual(features["n_days"], 1.0)

    def test_absent_habit_fields_are_missing_not_zero(self):
        # A user with no stored sleep figure must not look like a user
        # who slept zero hours.
        features = build_band_features(CALM, None)
        for name in HABIT_FEATURES:
            with self.subTest(feature=name):
                self.assertNotEqual(features[name], features[name], f"{name} should be NaN")

    def test_habit_fields_are_read_from_the_latest_day(self):
        days = [{"sleep_hours": 5.0}, {"sleep_hours": 6.0}, {"sleep_hours": 8.0}]
        features = build_band_features([60.0, 61.0, 62.0], days)
        self.assertEqual(features["last_sleep_hours"], 8.0)
        self.assertGreater(features["sd_sleep_hours"], 0.0)

    def test_order_is_load_bearing(self):
        # slope, the day-to-day differences and the recency-weighted
        # volatility are all directional. A caller that passed the week
        # newest-first would invert the trend, so a reversed sequence
        # must not produce the same row.
        rising = build_band_features([60.0, 63.0, 66.0, 69.0])
        falling = build_band_features([69.0, 66.0, 63.0, 60.0])
        self.assertAlmostEqual(rising["slope"], -falling["slope"], places=6)
        self.assertNotAlmostEqual(rising["slope"], falling["slope"])

    def test_a_bool_is_not_a_score(self):
        # bool subclasses int in Python, so True would otherwise be
        # averaged in as 1.0 without anything complaining.
        self.assertEqual(
            build_band_features([70.0, True, 72.0])["n_days"], 2.0,
        )

    def test_no_usable_score_returns_a_full_row_rather_than_raising(self):
        # A feature builder that throws is a feature builder that ends
        # up wrapped in a bare except somewhere.
        features = build_band_features([])
        self.assertEqual(sorted(features), sorted(BAND_FEATURE_COLUMNS))


@unittest.skipUnless(ARTIFACT.exists(), "no band model artifact in this checkout")
class TestTheServedHalfWidth(unittest.TestCase):
    def setUp(self):
        band_model_service.reset_cache()

    def tearDown(self):
        band_model_service.reset_cache()

    def test_the_artifact_loads(self):
        self.assertTrue(band_model_service.available())

    def test_it_is_personal_rather_than_a_constant_in_disguise(self):
        calm = band_model_service.half_width(CALM)
        erratic = band_model_service.half_width(ERRATIC)
        self.assertIsNotNone(calm)
        self.assertIsNotNone(erratic)
        self.assertLess(
            calm, erratic,
            "a steady week and an erratic week came back with the same width - "
            "that is a constant with extra steps",
        )

    def test_the_width_stays_inside_the_calibrated_clamp(self):
        info = json.loads(paths.artifact("band_model_info.json").read_text(encoding="utf-8"))
        low, high = info["min_half_width"], info["max_half_width"]
        for scores in ([50.0], CALM, ERRATIC, [0.0, 100.0, 0.0, 100.0], [95.0] * 6):
            with self.subTest(scores=scores[:3]):
                width = band_model_service.half_width(scores)
                self.assertGreaterEqual(width, low)
                self.assertLessEqual(width, high)

    def test_habit_fields_are_actually_consulted(self):
        # Same scores, different stored days. If the habit half of the
        # vector were being ignored these would be identical.
        days = [
            {"sleep_hours": h, "total_screen_min": s, "stress_0_10": 8}
            for h, s in [(4.0, 700), (9.5, 200), (4.5, 680), (9.0, 220), (4.0, 720)]
        ]
        self.assertNotAlmostEqual(
            band_model_service.half_width(CALM),
            band_model_service.half_width(CALM, days),
            places=3,
        )

    def test_no_usable_score_means_no_opinion(self):
        self.assertIsNone(band_model_service.half_width([]))
        self.assertIsNone(band_model_service.half_width([None, "x", True]))

    def test_a_prediction_failure_falls_back_rather_than_raising(self):
        band_model_service.available()
        with mock.patch.object(
            band_model_service, "_model",
            mock.Mock(predict=mock.Mock(side_effect=RuntimeError("boom"))),
        ):
            self.assertIsNone(band_model_service.half_width(CALM))


class TestItRefusesAModelItDoesNotUnderstand(unittest.TestCase):
    def tearDown(self):
        band_model_service.reset_cache()

    def test_mismatched_feature_columns_are_refused(self):
        # Somebody adds a feature to utils/band_features.py and forgets
        # to retrain. Every position past the insertion point now means
        # a different thing, and the model would answer anyway - with a
        # number that looks completely reasonable. Refusing is the only
        # safe response.
        band_model_service.reset_cache()
        with mock.patch.object(band_model_service, "COLUMNS_PATH") as columns_path:
            columns_path.exists.return_value = True
            columns_path.read_text.return_value = json.dumps(
                {"features": ["something", "entirely", "different"]}
            )
            self.assertFalse(band_model_service.available())
            self.assertIsNone(band_model_service.half_width(CALM))

    def test_a_missing_artifact_is_not_an_error(self):
        band_model_service.reset_cache()
        with mock.patch.object(band_model_service, "MODEL_PATH", Path("/nonexistent/band.pkl")):
            self.assertFalse(band_model_service.available())
            self.assertIsNone(band_model_service.half_width(CALM))


class TestTheBandIsStillTheBand(unittest.TestCase):
    """Only the width changed. Everything else the plan runs on did not."""

    def test_the_centre_is_the_plain_mean(self):
        low, high = week_band([60.0, 70.0, 80.0])
        self.assertAlmostEqual((low + high) / 2, 70.0, places=1)

    def test_the_centre_is_the_weighted_mean_when_a_day_is_an_exception(self):
        # The exception weight moves the centre and nothing else - the
        # rule that survives from before the model existed.
        low, high = week_band([80.0, 45.0], [1.0, 0.25])
        self.assertAlmostEqual((low + high) / 2, 73.0, places=1)

    def test_no_days_still_means_no_band(self):
        self.assertEqual(week_band([]), (None, None))
        self.assertEqual(week_band([70.0], [0.0]), (None, None))

    def test_an_explicit_half_width_wins_over_the_model(self):
        # The escape hatch every arithmetic test uses, so those tests
        # do not start failing whenever the model is retrained.
        self.assertEqual(week_band([70.0], None, None, 6.0), (64.0, 76.0))

    def test_the_band_is_clamped_to_the_score_range(self):
        low, _ = week_band([1.0], None, None, 6.0)
        _, high = week_band([99.0], None, None, 6.0)
        self.assertEqual(low, 0.0)
        self.assertEqual(high, 100.0)

    def test_the_constant_is_still_the_fallback(self):
        # Not a style point: this is what a checkout with no artifact
        # gets, and it must stay a real, usable band.
        self.assertEqual(BAND_HALF_WIDTH, 6.0)
        with mock.patch(
            "services.ml.band_model_service.half_width", return_value=None,
        ):
            self.assertEqual(week_band([70.0]), (64.0, 76.0))

    def test_a_symmetric_window_around_the_centre(self):
        low, high = week_band(CALM)
        centre = sum(CALM) / len(CALM)
        self.assertAlmostEqual(centre - low, high - centre, places=1)

    def test_outside_band_still_needs_a_band_and_a_score(self):
        self.assertFalse(is_outside_band(None, 60.0, 70.0))
        self.assertFalse(is_outside_band(65.0, None, None))
        self.assertTrue(is_outside_band(55.0, 60.0, 70.0))
        self.assertFalse(is_outside_band(65.0, 60.0, 70.0))


class TestTheApiSaysWhichBandItIs(APITestCase):
    """A personal band a client cannot tell apart from a constant is half a feature.

    The cohort panel already names its source rather than presenting a
    shipped reference grid as the full training set; the band does the
    same, so a reader is never told a number is theirs when it is
    everybody's.
    """

    def setUp(self):
        super().setUp()
        self.headers = self._auth_headers(self._register(email="bandapi@example.com"))
        self.me = self.client.get("/api/v1/auth/me", headers=self.headers).json()

    def _seed(self, scores):
        from api.dependencies.services import get_history_storage_backend

        backend = self.app.dependency_overrides[get_history_storage_backend]()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        days = []
        day = today
        while len(days) < len(scores) and day >= monday:
            days.append(day)
            day -= timedelta(days=1)
        if len(days) < len(scores):
            self.skipTest(f"today is {today:%A}; this week cannot hold {len(scores)} days")
        days = list(reversed(days))
        with backend.transaction() as records:
            rows = list(records)
            for when, score in zip(days, scores):
                rows.append({
                    "user_id": self.me["user_id"],
                    "date": when.isoformat(),
                    "day_of_week": when.strftime("%A"),
                    "health_score": float(score),
                    "health_class": "Healthy" if score >= 70 else "Moderate",
                    "sleep_hours": 7.0,
                    "total_screen_min": 300,
                    "excluded": False,
                })
            backend.commit(rows)

    def _plan(self):
        response = self.client.post(
            "/api/v1/plan", headers=self.headers,
            json={"health_class": "Healthy", "wellness_score": 80, "user_data": {}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_the_plan_reports_the_width_and_where_it_came_from(self):
        self._seed([72.0, 70.0, 74.0])
        plan = self._plan()
        self.assertIn(plan["band_source"], {"model", "constant"})
        self.assertIsNotNone(plan["band_half_width"])
        # The reported width has to be the one actually applied, not a
        # second opinion computed alongside it.
        self.assertAlmostEqual(
            (plan["band_high"] - plan["band_low"]) / 2,
            plan["band_half_width"], delta=0.06,
        )

    def test_no_band_means_no_width_and_no_source(self):
        plan = self._plan()
        self.assertIsNone(plan["band_low"])
        self.assertIsNone(plan["band_half_width"])
        self.assertIsNone(plan["band_source"])

    def test_the_day_status_reports_it_too(self):
        self._seed([72.0, 70.0, 55.0])
        status = self.client.get("/api/v1/plan/day-status", headers=self.headers).json()
        self.assertIn(status["band_source"], {"model", "constant"})
        # delta, not places=1. The two ends are each rounded to one
        # decimal before they are sent, so their half-difference can sit
        # up to 0.05 from the width it was built from - and places=1
        # fails at exactly 0.05, which made this test depend on where
        # the model's output happened to land rather than on the
        # relationship it is checking.
        self.assertAlmostEqual(
            (status["band_high"] - status["band_low"]) / 2,
            status["band_half_width"], delta=0.06,
        )

    def test_a_frozen_band_is_described_by_its_own_width(self):
        # The locked band is what the reader is being shown. Describing
        # it with a width recomputed from today's fresh prediction would
        # be the same class of error as a stale score under a fresh
        # label, so the width is read back off the stored edges.
        self._seed([72.0, 70.0, 74.0])
        first = self._plan()
        second = self._plan()  # served from the lock, not regenerated
        self.assertEqual(first["band_low"], second["band_low"])
        self.assertAlmostEqual(
            (second["band_high"] - second["band_low"]) / 2,
            second["band_half_width"], places=1,
        )


@unittest.skipUnless(ARTIFACT.exists(), "no band model artifact in this checkout")
class TestTheRecordedMetrics(unittest.TestCase):
    """The claims made about this model are in the repository, not in prose."""

    def setUp(self):
        self.metrics = json.loads(
            paths.artifact("metrics_band.json").read_text(encoding="utf-8")
        )

    def test_the_shipped_artifact_passed_its_own_gate(self):
        # models/train_band_model.py refuses to write the artifact
        # otherwise, so an artifact on disk with beats_baseline false
        # would mean somebody put it there by hand.
        self.assertTrue(self.metrics["beats_baseline"])

    def test_it_covers_what_it_promises_on_held_out_respondents(self):
        target = self.metrics["target_coverage"]
        self.assertGreaterEqual(
            self.metrics["results"]["test"]["model"]["coverage"], target - 0.02,
        )

    def test_it_is_fairer_to_volatile_users_than_the_best_constant(self):
        # The entire argument for personalising. A constant hits its
        # average by over-covering calm users and under-covering the
        # ones who actually move; if this model does not fix that, it
        # has bought nothing.
        test = self.metrics["results"]["test"]
        self.assertLess(
            test["model"]["worst_tercile_gap"],
            test["best_constant"]["worst_tercile_gap"],
        )

    def test_the_widths_it_predicts_actually_vary(self):
        spread = self.metrics["results"]["test"]["model"]["half_width_spread"]
        self.assertGreater(spread["p90"] - spread["p10"], 0.5)

    def test_each_feature_block_is_recorded_as_earning_its_place(self):
        # The ablation is refitted on every training run rather than
        # quoted from memory, so this reads the numbers that run
        # produced. Three nested feature sets now, not two, so each
        # step is attributable to one block: sequence only, then plus
        # the person's earlier weeks, then plus the habit fields.
        ablations = self.metrics["ablations"]
        sequence_only = ablations["sequence_only"]["worst_tercile_gap"]
        with_prior = ablations["sequence_and_prior"]["worst_tercile_gap"]
        full = ablations["full_model"]["worst_tercile_gap"]

        self.assertLessEqual(
            with_prior, sequence_only,
            "knowing the person's earlier weeks is not paying for itself - "
            "either drop PRIOR_FEATURES from utils/band_features.py or stop "
            "claiming they help",
        )
        self.assertLessEqual(
            full, sequence_only,
            "the full feature set is no fairer than the sequence alone - "
            "either drop what it adds or stop claiming it helps",
        )

    def test_the_synthetic_caveat_is_attached_to_the_numbers(self):
        self.assertIn("synthetic", self.metrics["honest_description"].lower())


if __name__ == "__main__":
    unittest.main()
