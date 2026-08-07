"""
Enterprise Validation Service
-----------------------------
Centralized validation for user input according to FEATURE_SCHEMA.
"""

from __future__ import annotations

from typing import Any

from core.feature_schema import FEATURE_SCHEMA, Feature
from core.validation_result import ValidationResult


class ValidationService:
    """
    Validate all user inputs according to FEATURE_SCHEMA.
    """

    def __init__(self) -> None:
        self.schema = FEATURE_SCHEMA

    # =====================================================
    # Public API
    # =====================================================

    # Now that total_screen_min is always derived as the literal sum of
    # these five category fields (utils/feature_derivation.py -
    # compute_total_screen_min(); models/data_loader.py's
    # reconstruct_derived_features() makes the training data match this
    # same semantic), a per-field-only check can still let an
    # "impossible day" through: each of the five fields individually
    # valid at up to 1440 minutes, but their SUM up to 7200 minutes -
    # 5x total_screen_min's own declared maximum. Checked as a
    # cross-field rule below, after the per-field loop.
    _SCREEN_TIME_CATEGORY_FIELDS = (
        "social_min", "gaming_min", "work_study_min", "video_min", "other_min",
    )

    def validate(
        self,
        user_data: dict[str, Any],
    ) -> ValidationResult:

        cleaned_data: dict[str, Any] = {}
        errors: dict[str, str] = {}
        warnings: dict[str, str] = {}

        for feature_name, feature in self.schema.items():
            value = user_data.get(feature_name)

            try:
                cleaned_value = self._validate_feature(
                    feature_name,
                    value,
                    feature,
                )
                cleaned_data[feature_name] = cleaned_value

            except ValueError as exc:
                errors[feature_name] = str(exc)

        self._validate_screen_time_total(cleaned_data, errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            cleaned_data=cleaned_data,
            errors=errors,
            warnings=warnings,
        )

    def _validate_screen_time_total(
        self,
        cleaned_data: dict[str, Any],
        errors: dict[str, str],
    ) -> None:
        """
        Cross-field guard: the five screen-time category fields' sum
        must not exceed total_screen_min's own declared schema maximum
        (each is individually bounded to that same maximum, but nothing
        stops all five being independently maxed out at once). Skipped
        if any category field already failed its own per-field check
        above (already reported) or is genuinely absent (not required
        individually).
        """
        if any(field in errors for field in self._SCREEN_TIME_CATEGORY_FIELDS):
            return

        values = [cleaned_data.get(field) for field in self._SCREEN_TIME_CATEGORY_FIELDS]
        if any(v is None for v in values):
            return

        total_max = self.schema["total_screen_min"].maximum
        category_sum = sum(values)
        if total_max is not None and category_sum > total_max:
            errors["social_min"] = (
                f"Combined screen-time categories (social, gaming, work/study, video, "
                f"other) total {category_sum:.0f} minutes, which exceeds the maximum "
                f"possible screen time in a day ({total_max:.0f} minutes)."
            )

    # =====================================================
    # Internal Validation
    # =====================================================

    def _validate_feature(
        self,
        feature_name: str,
        value: Any,
        feature: Feature,
    ) -> Any:

        if value is None:
            if feature.required:
                raise ValueError("This field is required.")
            return None

        if feature.choices is not None:
            return self._validate_categorical(value, feature)

        if feature.dtype in (int, float):
            return self._validate_numeric(value, feature)

        if feature.dtype == str:
            return str(value)

        return value

    # =====================================================

    def _validate_numeric(
        self,
        value: Any,
        feature: Feature,
    ) -> float | int:

        # `bool` is a subclass of `int` in Python, so `float(True) == 1.0`
        # and `int(False) == 0` both succeed silently below - meaning a
        # boolean value would pass through as a valid number without any
        # error. The current Streamlit UI never triggers this (its
        # number_input/slider widgets never emit raw booleans), so this
        # was previously unreachable in practice - but any future caller
        # that accepts raw JSON (a REST API, a bulk upload) is exactly
        # the kind of input this validator exists to guard against.
        # Reject it explicitly rather than silently coercing it.
        if isinstance(value, bool):
            raise ValueError("Must be a valid numeric value, not a boolean.")

        try:
            if feature.dtype == int:
                parsed_val = int(value)
            else:
                parsed_val = float(value)
        except Exception:
            raise ValueError("Must be a valid numeric value.")

        # `float("nan")` / `float("inf")` both succeed above, but every
        # comparison against a NaN is False - so without this check a
        # NaN would silently skip the min/max bounds below instead of
        # being rejected, and later reach the model as a real NaN input.
        if isinstance(parsed_val, float) and (parsed_val != parsed_val or parsed_val in (float("inf"), float("-inf"))):
            raise ValueError("Must be a finite numeric value.")

        minimum = feature.minimum
        maximum = feature.maximum

        if minimum is not None and parsed_val < minimum:
            raise ValueError(f"Value must be at least {minimum}.")

        if maximum is not None and parsed_val > maximum:
            raise ValueError(f"Value must be at most {maximum}.")

        return parsed_val

    # =====================================================

    def _validate_categorical(
        self,
        value: Any,
        feature: Feature,
    ) -> Any:

        choices = feature.choices

        if choices is None:
            return value

        if value not in choices:
            raise ValueError(f"Value must be one of {choices}.")

        return value