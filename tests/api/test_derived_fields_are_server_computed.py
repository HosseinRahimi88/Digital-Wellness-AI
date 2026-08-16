"""/predict must not trust the client's arithmetic for derived fields.

The defect: total_screen_min is defined as the sum of the five category
minute fields (utils/feature_derivation.compute_total_screen_min), and
training rebuilds it that way at its single load point. The endpoint,
though, scored whatever total the client happened to send. With the same
five categories summing to 658.5 minutes, a payload carrying a stale
total of 140 scored 88.25 where the honest total scores 69.75.

That is an eighteen-point error in the one number the app exists to
report, produced by a field the server can compute itself.
"""

from __future__ import annotations

import unittest

from config import demo_profiles as dp
from services.ml.prediction_service import PredictionService
from services.ml.validation_service import ValidationService
from utils.feature_derivation import derive_features

HEAVY_DAY = {
    "social_min": 200.0, "gaming_min": 10.0, "video_min": 40.0,
    "other_min": 19.5, "work_study_min": 389.0,
}
HEAVY_TOTAL = sum(HEAVY_DAY.values())


class TestTheServerDerivesTotalScreenTime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = ValidationService()
        cls.predictor = PredictionService()

    def _payload_with_stale_total(self) -> dict:
        day = dict(dp.healthy_profile())
        day.update(HEAVY_DAY)
        # The profile's own total, left untouched: what a stale form, a
        # replayed payload or any non-browser client would send.
        day["total_screen_min"] = 140.0
        return day

    def test_the_fixture_really_does_carry_a_wrong_total(self):
        # Guards the test itself: if the profile ever changes so that its
        # total happens to match, this stops silently passing.
        payload = self._payload_with_stale_total()
        self.assertNotAlmostEqual(payload["total_screen_min"], HEAVY_TOTAL, places=1)

    def test_the_stale_total_is_replaced_with_the_real_sum(self):
        cleaned = self.validator.validate(
            derive_features(self._payload_with_stale_total())
        ).cleaned_data
        self.assertAlmostEqual(cleaned["total_screen_min"], HEAVY_TOTAL, places=1)

    def test_the_score_follows_the_real_total_not_the_sent_one(self):
        honest = self.validator.validate(
            derive_features(self._payload_with_stale_total())
        ).cleaned_data
        as_sent = self.validator.validate(self._payload_with_stale_total()).cleaned_data

        honest_score = self.predictor.predict(honest, history=[]).regression_score
        sent_score = self.predictor.predict(as_sent, history=[]).regression_score

        # A 658-minute day must not score like a 140-minute one.
        self.assertLess(
            honest_score, sent_score - 5.0,
            f"deriving changed nothing: {honest_score} vs {sent_score}",
        )

    def test_the_endpoint_itself_derives(self):
        # The router is what the fix actually changed, so read it rather
        # than only exercising the services underneath it.
        from core import paths

        source = (paths.PROJECT_ROOT / "api/routers/prediction.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("derive_features(dict(payload.user_data))", source)


class TestDerivationDoesNotDisturbCallersThatManageTheirOwn(unittest.TestCase):
    """future_path_service drops screen_ewma_baseline on purpose so the
    personal baseline is not redefined under it. Deriving inside
    ValidationService broke that; deriving at the router does not."""

    def test_validation_service_still_leaves_derived_fields_alone(self):
        day = dict(dp.healthy_profile())
        day.update(HEAVY_DAY)
        day["total_screen_min"] = 140.0
        cleaned = ValidationService().validate(day).cleaned_data
        self.assertAlmostEqual(cleaned["total_screen_min"], 140.0, places=1)


if __name__ == "__main__":
    unittest.main()
