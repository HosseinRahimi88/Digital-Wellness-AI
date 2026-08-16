"""Nothing used to compare live inputs to the training distribution.

Every number on the model-performance page describes a held-out split
from training time. None of them say whether the rows arriving today
resemble the rows the models learned from, and a model can be 97%
accurate on its own test set while extrapolating confidently about
somebody it has no basis for.

THE MISTAKE THIS FILE EXISTS TO PREVENT
---------------------------------------
The obvious implementation is PSI per user, and it is wrong. PSI compares
two DISTRIBUTIONS, and one person's thirty days are far more concentrated
than 93,000 rows drawn from thousands of people - an ordinary user who
sleeps 6.5 to 7.5 hours lands in two or three reference deciles and
scores well past the "significant shift" threshold for that reason
alone. The first version of the service did exactly this, and a simulated
user drawn from near the training medians came back "significant" on
every single feature. A gauge that reads red for everybody is broken.

So: coverage (a tail rate) for one person, PSI for the pooled population.
`test_an_ordinary_user_is_not_flagged` is the regression, and it is the
most important test here.
"""
from __future__ import annotations

import random
import unittest

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from services.ml.drift_service import (
    EXPECTED_TAIL_RATE,
    MIN_DAYS,
    MIN_POOLED_ROWS,
    RELIABLE_DAYS,
    SIGNIFICANT_TAIL_RATE,
    DriftService,
    psi,
)

# A synthetic reference with a known, uniform 0-100 grid, so the maths
# can be checked against numbers worked out by hand rather than against
# whatever the shipped artifact happens to contain.
UNIFORM_REFERENCE = {
    "source": "test-fixture",
    "n": 10000,
    "grid_points": 101,
    "fields": {
        "score": {
            "n": 10000, "mean": 50.0, "median": 50.0, "p25": 25.0, "p75": 75.0,
            # 0, 1, 2, ... 100 - so the p5 edge is 5 and the p95 edge is 95.
            "grid": [float(i) for i in range(101)],
        },
    },
}


def _days(values, field_name="score"):
    return [{field_name: v} for v in values]


class TestPerUserCoverage(unittest.TestCase):
    def setUp(self):
        self.service = DriftService(reference=UNIFORM_REFERENCE)

    def test_a_user_inside_the_reference_range_is_covered(self):
        report = self.service.report(_days([40, 45, 50, 55, 60, 48, 52, 47, 53, 50]))
        self.assertTrue(report.available)
        self.assertEqual(report.overall_band, "covered")
        self.assertEqual(report.features[0].tail_rate, 0.0)

    def test_an_ordinary_user_is_not_flagged(self):
        # THE regression. A narrow but entirely unremarkable person must
        # score zero, not "significant" - see the module docstring for
        # the version of this that got it wrong.
        random.seed(11)
        report = self.service.report(
            _days([random.gauss(50, 3) for _ in range(30)])
        )
        self.assertEqual(report.overall_band, "covered")
        self.assertLess(report.features[0].tail_rate, EXPECTED_TAIL_RATE)

    def test_a_user_entirely_outside_the_range_is_flagged(self):
        report = self.service.report(_days([97, 98, 99, 99, 98, 97, 99, 98, 99, 97]))
        self.assertEqual(report.overall_band, "extrapolating")
        self.assertEqual(report.features[0].tail_rate, 1.0)

    def test_the_tail_rate_is_the_share_of_days_outside_p5_to_p95(self):
        # Ten days, exactly three of them outside 5..95.
        report = self.service.report(_days([1, 2, 99, 50, 50, 50, 50, 50, 50, 50]))
        self.assertAlmostEqual(report.features[0].tail_rate, 0.3, places=4)

    def test_the_boundary_values_count_as_inside(self):
        # p5 and p95 themselves are covered - the model has data there.
        report = self.service.report(_days([5, 95] * 5))
        self.assertEqual(report.features[0].tail_rate, 0.0)

    def test_the_reference_range_is_reported_so_a_reader_can_check_it(self):
        feature = self.service.report(_days([50] * 10)).features[0]
        self.assertEqual(feature.reference_low, 5.0)
        self.assertEqual(feature.reference_high, 95.0)

    def test_too_few_days_is_a_state_not_a_number(self):
        report = self.service.report(_days([50] * (MIN_DAYS - 1)))
        self.assertFalse(report.available)
        self.assertEqual(report.reason, "not_enough_days")
        self.assertEqual(report.features, [])

    def test_a_short_history_is_answered_but_marked_unreliable(self):
        report = self.service.report(_days([50] * MIN_DAYS))
        self.assertTrue(report.available)
        self.assertFalse(report.reliable)

    def test_enough_days_is_marked_reliable(self):
        self.assertTrue(self.service.report(_days([50] * RELIABLE_DAYS)).reliable)

    def test_excluded_days_do_not_count(self):
        rows = _days([50] * 10)
        rows += [{"score": 999, "excluded": True}] * 10
        self.assertEqual(self.service.report(rows).features[0].tail_rate, 0.0)

    def test_a_field_that_is_never_logged_is_skipped_not_scored_as_zero(self):
        # Reporting drift on a column nobody records would be a finding
        # about the app's own storage, dressed as a finding about the user.
        report = self.service.report([{"something_else": 1} for _ in range(20)])
        self.assertFalse(report.available)
        self.assertEqual(report.reason, "no_usable_fields")

    def test_a_bool_is_not_a_measurement(self):
        rows = _days([50] * 10) + [{"score": True}] * 10
        self.assertEqual(self.service.report(rows).features[0].days, 10)

    def test_the_worst_feature_leads(self):
        two_fields = {
            "source": "t", "n": 1, "grid_points": 101,
            "fields": {
                "fine": {"median": 50.0, "grid": [float(i) for i in range(101)]},
                "bad": {"median": 50.0, "grid": [float(i) for i in range(101)]},
            },
        }
        service = DriftService(reference=two_fields)
        rows = [{"fine": 50, "bad": 99} for _ in range(20)]
        report = service.report(rows)
        self.assertEqual(report.worst.field_name, "bad")
        self.assertEqual(report.overall_band, "extrapolating")

    def test_no_reference_is_a_state_not_a_crash(self):
        report = DriftService(reference={}).report(_days([50] * 20))
        self.assertFalse(report.available)
        self.assertEqual(report.reason, "no_reference")

    def test_the_thresholds_are_ordered_sensibly(self):
        self.assertLess(EXPECTED_TAIL_RATE, SIGNIFICANT_TAIL_RATE)


class TestPopulationPSI(unittest.TestCase):
    def setUp(self):
        self.service = DriftService(reference=UNIFORM_REFERENCE)

    def test_a_population_matching_the_reference_is_stable(self):
        # Uniform over 0..100 against a uniform reference: every decile
        # gets its 10%, so PSI is ~0.
        rows = _days([i % 101 for i in range(MIN_POOLED_ROWS * 2)])
        report = self.service.population(rows)
        self.assertTrue(report.available)
        self.assertEqual(report.overall_band, "stable")
        self.assertLess(report.features[0].psi, 0.05)

    def test_a_shifted_population_is_flagged(self):
        rows = _days([random.uniform(90, 100) for _ in range(MIN_POOLED_ROWS * 2)])
        report = self.service.population(rows)
        self.assertEqual(report.overall_band, "significant")

    def test_a_small_pool_is_refused_rather_than_guessed_at(self):
        report = self.service.population(_days([50] * (MIN_POOLED_ROWS - 1)))
        self.assertFalse(report.available)
        self.assertEqual(report.reason, "not_enough_rows")

    def test_psi_of_a_perfectly_matching_sample_is_about_zero(self):
        grid = [float(i) for i in range(101)]
        self.assertLess(psi([i % 101 for i in range(1010)], grid), 0.01)

    def test_psi_needs_a_usable_grid(self):
        self.assertIsNone(psi([1, 2, 3], []))
        self.assertIsNone(psi([], [float(i) for i in range(101)]))

    def test_psi_survives_a_bucket_nobody_lands_in(self):
        # ln(0) is the classic way this function raises. Everything
        # crammed into one decile is the case that produces it.
        grid = [float(i) for i in range(101)]
        score = psi([50.0] * 500, grid)
        self.assertIsNotNone(score)
        self.assertGreater(score, 1.0)


class TestTheShippedReference(unittest.TestCase):
    """Against the real artifact, not a fixture."""

    def setUp(self):
        from services.ml import drift_service

        drift_service.reset_cache()
        self.service = DriftService()
        if not self.service.reference_source or self.service.reference_source == "none":
            self.skipTest("no cohort reference artifact in this checkout")

    def test_the_reference_names_its_source_and_size(self):
        # The same rule the cohort panel follows: a reader is entitled to
        # know what they are being compared against.
        self.assertNotEqual(self.service.reference_source, "none")
        self.assertGreater(self.service.reference_rows, 0)

    def test_a_plausible_user_is_covered_against_the_real_reference(self):
        # Drawn near the artifact's own medians. If this came back
        # flagged, the metric would be reporting on its own arithmetic
        # rather than on the user.
        random.seed(3)
        fields = self.service._fields()  # noqa: SLF001 - reading the fixture, not behaviour
        rows = []
        for _ in range(30):
            row = {}
            for name, stats in fields.items():
                median = stats.get("median")
                spread = abs((stats.get("p75") or median) - (stats.get("p25") or median)) or 1.0
                row[name] = random.gauss(median, spread / 4.0)
            rows.append(row)
        report = self.service.report(rows)
        self.assertTrue(report.available)
        self.assertEqual(
            report.overall_band, "covered",
            f"an ordinary user was flagged as {report.overall_band} - "
            f"worst was {report.worst.field_name} at {report.worst.tail_rate:.0%}",
        )

    def test_an_implausible_user_is_flagged_against_the_real_reference(self):
        fields = self.service._fields()  # noqa: SLF001
        rows = []
        for _ in range(30):
            row = {}
            for name, stats in fields.items():
                grid = stats.get("grid") or [0.0]
                row[name] = grid[-1] * 3 + 1  # far beyond the observed maximum
            rows.append(row)
        report = self.service.report(rows)
        self.assertEqual(report.overall_band, "extrapolating")


class TestTheEndpoint(unittest.TestCase):
    """Through HTTP, since the schema is part of the contract."""

    @classmethod
    def setUpClass(cls):
        from tests.api.test_api import APITestCase

        cls.base = APITestCase

    def setUp(self):
        self.case = self.base("run")
        self.case.setUp()
        self.client = self.case.client
        self.headers = self.case._auth_headers(self.case._register(email="drift@example.com"))

    def tearDown(self):
        self.case.tearDown()

    def test_it_needs_a_session(self):
        self.assertEqual(self.client.get("/api/v1/model-performance/drift").status_code, 401)

    def test_a_brand_new_account_gets_a_state_not_an_error(self):
        response = self.client.get("/api/v1/model-performance/drift", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["available"])
        self.assertEqual(body["reason"], "not_enough_days")
        # The thresholds travel with the payload so the client never
        # hard-codes its own copy of them.
        self.assertGreater(body["min_days"], 0)
        self.assertGreater(body["significant_tail_rate"], 0)

    def test_the_population_block_is_always_present(self):
        body = self.client.get(
            "/api/v1/model-performance/drift", headers=self.headers,
        ).json()
        self.assertIn("population", body)
        self.assertIn(body["population"]["reason"], {"ok", "not_enough_rows", "no_reference"})

    def test_the_response_never_carries_another_users_data(self):
        # The population half is the only part that touches other
        # accounts, and it must come back as bucket proportions - never
        # as anybody's rows, ids or addresses.
        import json as _json

        other = self.base("run")
        body = self.client.get(
            "/api/v1/model-performance/drift", headers=self.headers,
        ).json()
        raw = _json.dumps(body)
        for leaked in ("user_id", "email", "@", "date"):
            self.assertNotIn(leaked, raw, f"{leaked!r} leaked into the drift response")


if __name__ == "__main__":
    unittest.main()
