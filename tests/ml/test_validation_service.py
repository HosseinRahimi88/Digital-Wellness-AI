"""
Tests: ValidationService error handling.

Run: python3 -m unittest tests.ml.test_validation_service -v

Covers the "error tests" requested for Production Polish: empty input,
missing required fields, corrupted/malformed values, and out-of-range
values must all be rejected with a clear per-field error instead of
raising an unhandled exception or silently passing bad data through to
the model.
"""

from __future__ import annotations

import math
import unittest

import tests._test_support as ts

from services.ml.validation_service import ValidationService


class TestValidationService(unittest.TestCase):

    def setUp(self):
        self.validator = ValidationService()

    def test_completely_empty_input_is_rejected(self):
        result = self.validator.validate({})
        self.assertFalse(result.is_valid)
        # Every required field should be flagged - not just the first one.
        self.assertIn("age", result.errors)
        self.assertIn("sleep_hours", result.errors)

    def test_valid_baseline_profile_passes(self):
        result = self.validator.validate(ts.baseline_user_data())
        self.assertTrue(result.is_valid, msg=result.errors)
        self.assertEqual(result.errors, {})

    def test_out_of_range_numeric_is_rejected(self):
        data = ts.baseline_user_data()
        data["age"] = 500  # far outside the 10-100 schema range
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("age", result.errors)

    def test_negative_value_below_minimum_is_rejected(self):
        data = ts.baseline_user_data()
        data["sleep_hours"] = -5.0
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("sleep_hours", result.errors)

    def test_garbage_string_in_numeric_field_is_rejected(self):
        data = ts.baseline_user_data()
        data["age"] = "not-a-number"
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("age", result.errors)

    def test_nan_numeric_value_is_rejected(self):
        """NaN compares False against every bound, so without an explicit
        finite-value check it would silently bypass min/max validation."""
        data = ts.baseline_user_data()
        data["sleep_hours"] = float("nan")
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("sleep_hours", result.errors)

    def test_infinite_numeric_value_is_rejected(self):
        data = ts.baseline_user_data()
        data["total_screen_min"] = math.inf
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("total_screen_min", result.errors)

    def test_invalid_categorical_choice_is_rejected(self):
        data = ts.baseline_user_data()
        data["gender"] = "Not A Real Choice"
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("gender", result.errors)

    def test_boolean_value_in_numeric_field_is_rejected(self):
        """`bool` is a subclass of `int` in Python, so `float(True) == 1.0`
        would otherwise silently coerce a boolean into a valid number.
        The current Streamlit UI never sends a raw bool into a numeric
        field, but a future JSON API caller could - reject it explicitly
        rather than silently accepting mistyped input."""
        data = ts.baseline_user_data()
        data["sleep_hours"] = True
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("sleep_hours", result.errors)

    def test_genuine_boolean_choice_fields_still_accept_booleans(self):
        """Guard against the boolean-rejection fix above being too broad:
        fields that are genuinely typed as bool with choices=[False, True]
        (uses_screen_time_limits, is_content_creator) go through the
        categorical path, not the numeric path, and must keep working."""
        data = ts.baseline_user_data()
        data["uses_screen_time_limits"] = True
        data["is_content_creator"] = False
        result = self.validator.validate(data)
        self.assertNotIn("uses_screen_time_limits", result.errors)
        self.assertNotIn("is_content_creator", result.errors)

    def test_none_for_required_field_is_rejected_cleanly(self):
        """Every FEATURE_SCHEMA field is required today; explicitly
        setting one to None must produce a clear per-field error
        instead of raising or silently dropping the field."""
        data = ts.baseline_user_data()
        data["day_index"] = None
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("day_index", result.errors)

    def test_impossible_screen_time_combination_is_rejected(self):
        """Each of the five screen-time category fields is individually
        valid up to 1440 minutes (a full day), but their SUM must not
        exceed total_screen_min's own declared maximum - total_screen_min
        is always derived as the literal sum of these five fields (see
        utils/feature_derivation.py), so 1440 minutes in every category
        at once (7200 total) describes a physically impossible day even
        though no single field's own bound was violated."""
        data = ts.baseline_user_data()
        data["social_min"] = 1440.0
        data["gaming_min"] = 1440.0
        data["work_study_min"] = 1440.0
        data["video_min"] = 1440.0
        data["other_min"] = 1440.0
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("social_min", result.errors)

    def test_screen_time_categories_summing_to_exactly_the_max_are_accepted(self):
        """The cross-field check is a <= bound, not a stricter one - a
        combination that sums to exactly total_screen_min's maximum
        (1440) should pass, not be rejected off-by-one."""
        data = ts.baseline_user_data()
        data["social_min"] = 400.0
        data["gaming_min"] = 300.0
        data["work_study_min"] = 400.0
        data["video_min"] = 300.0
        data["other_min"] = 40.0  # sums to exactly 1440.0
        result = self.validator.validate(data)
        self.assertTrue(result.is_valid, msg=result.errors)

    def test_screen_time_cross_field_check_skipped_when_a_category_already_invalid(self):
        """If a category field already failed its own per-field bound
        (e.g. negative), the cross-field sum check should not also fire
        a second, redundant error for the same underlying bad input."""
        data = ts.baseline_user_data()
        data["social_min"] = -50.0
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("social_min", result.errors)
        # Exactly one error for social_min, not the per-field one plus a
        # second cross-field one silently overwriting/duplicating it.
        self.assertEqual(
            result.errors["social_min"], "Value must be at least 0.0."
        )


if __name__ == "__main__":
    unittest.main()
