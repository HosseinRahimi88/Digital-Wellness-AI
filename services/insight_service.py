"""
Insight Service
------------------
Trust-and-context signals that sit *around* a prediction rather than
inside it (P1 items 13, 14, 17, 18):

  * Confidence Label      - plain-language reading of the model's own
                            probability + conformal uncertainty.
  * Out-of-Distribution   - flags an input that sits outside the range
                            the models were actually trained on, so a
                            confident-looking score on an implausible
                            day is labelled instead of trusted.
  * Cold-Start Policy     - how much of the app's history-dependent
                            output is trustworthy given how many days
                            the user has actually logged.
  * Day-of-Week Reliability - whether there is enough per-weekday data
                            to say anything about weekday patterns.

None of this changes a prediction. Every function is a pure read over
values the pipeline already produced (plus FEATURE_SCHEMA bounds), so
it can never alter the score it is describing.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional

from core.feature_schema import FEATURE_SCHEMA

# --- Cold-start thresholds -------------------------------------------
# Chosen to line up with what the downstream features actually need:
# a trend line needs a few points, weekday comparison needs repeats of
# the same weekday, and the weekly summaries group by ISO week.
COLD_START_STAGES = (
    (0, "no_data"),
    (1, "single_day"),
    (3, "early"),
    (7, "week"),
    (21, "established"),
)

# A weekday needs at least this many observations before its average is
# reported as a "pattern" rather than a single day's noise.
WEEKDAY_MIN_OBSERVATIONS = 2

# Fraction of a feature's schema range beyond which a value is treated
# as an extreme (still valid, but rare) observation.
_OOD_EDGE_FRACTION = 0.02

# Fields worth checking for out-of-distribution behaviour, each with the
# edge(s) that are genuinely implausible for that field.
#
# The direction matters and is not symmetric. Zero gaming minutes, zero
# caffeine and zero night-time screen use are all perfectly ordinary
# healthy days - flagging those as "out of distribution" would fire a
# scary warning on exactly the users doing best, which is worse than no
# warning at all. Only a maximum-edge value is implausible for those.
# A handful of fields are implausible at BOTH edges (nobody sleeps zero
# hours or uses a screen for zero minutes on a day they filled this in).
_OOD_WATCH_FIELDS: dict[str, str] = {
    "total_screen_min": "both",
    "social_min": "max",
    "gaming_min": "max",
    "video_min": "max",
    "night_screen_min": "max",
    "pre_sleep_screen_min": "max",
    "sleep_hours": "both",
    "notifications_per_day": "max",
    "pickups_per_day": "max",
    "app_opens_per_day": "max",
    "physical_activity_min_per_day": "max",
    "caffeine_cups_per_day": "max",
}


@dataclass(slots=True)
class ConfidenceLabel:
    level: str          # "high" | "moderate" | "low"
    percent: float
    headline: str
    detail: str
    interval_width: Optional[float] = None


@dataclass(slots=True)
class OODFlag:
    field_name: str
    label: str
    value: float
    minimum: float
    maximum: float
    position: str       # "at_or_below_minimum" | "at_or_above_maximum"


@dataclass(slots=True)
class OODReport:
    is_out_of_distribution: bool
    flags: list[OODFlag] = field(default_factory=list)
    message: str = ""


@dataclass(slots=True)
class ColdStartStatus:
    entry_count: int
    stage: str
    trend_available: bool
    weekday_pattern_available: bool
    week_comparison_available: bool
    message: str


@dataclass(slots=True)
class WeekdayReliability:
    weekday: str
    observations: int
    average_score: Optional[float]
    is_reliable: bool


class InsightService:

    # ------------------------------------------------------------
    # Confidence label (P1 item 17)
    # ------------------------------------------------------------

    @staticmethod
    def confidence_label(
        confidence_percent: Optional[float],
        uncertainty: Optional[Any] = None,
    ) -> ConfidenceLabel:
        """
        Turn the raw probability (and conformal interval, when
        calibration succeeded) into something a non-specialist can act
        on. The thresholds are deliberately conservative: this project's
        own leakage-fixed evaluation showed the classifier is
        *overconfident* on genuinely new users (see LEAKAGE_FIX_REPORT),
        so a raw 85% is described as "reasonably confident", never
        "very confident".
        """
        pct = float(confidence_percent or 0.0)
        width = None
        if uncertainty is not None:
            width = getattr(uncertainty, "regression_interval_width", None)
            if width is None and isinstance(uncertainty, dict):
                width = uncertainty.get("regression_interval_width")

        if pct >= 90:
            level, headline = "high", "The model is confident about this one."
            detail = "Your inputs land clearly inside one wellness category."
        elif pct >= 70:
            level, headline = "moderate", "Reasonably confident, not certain."
            detail = "Your inputs mostly point one way, with some overlap into a neighbouring category."
        else:
            level, headline = "low", "Treat this as a rough read."
            detail = "Your inputs sit close to the boundary between categories — the exact label could go either way."

        if width is not None:
            detail += f" The likely score range spans about {round(float(width))} points."

        return ConfidenceLabel(
            level=level, percent=round(pct, 2),
            headline=headline, detail=detail,
            interval_width=round(float(width), 2) if width is not None else None,
        )

    # ------------------------------------------------------------
    # Out-of-distribution warning (P1 item 18)
    # ------------------------------------------------------------

    @staticmethod
    def check_out_of_distribution(user_data: dict[str, Any]) -> OODReport:
        """
        Flags inputs pinned at (or past) the edge of their schema range.

        Why the schema range and not the training data's empirical
        distribution: the raw training CSVs are not shipped with this
        repo (see .gitignore), so an empirical percentile check would
        silently do nothing wherever the data is absent - a guard that
        quietly stops guarding is worse than a simpler one that always
        works. FEATURE_SCHEMA's bounds ARE the declared valid domain, so
        sitting at the very edge of one is the honest, always-available
        signal that this day is unlike a typical modelled day.
        """
        flags: list[OODFlag] = []

        for field_name, watch in _OOD_WATCH_FIELDS.items():
            feature = FEATURE_SCHEMA.get(field_name)
            if feature is None or feature.minimum is None or feature.maximum is None:
                continue
            raw = user_data.get(field_name)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue

            lo, hi = float(feature.minimum), float(feature.maximum)
            span = hi - lo
            if span <= 0:
                continue
            edge = span * _OOD_EDGE_FRACTION

            if watch in ("max", "both") and value >= hi - edge:
                position = "at_or_above_maximum"
            elif watch in ("min", "both") and value <= lo + edge:
                position = "at_or_below_minimum"
            else:
                continue

            flags.append(OODFlag(
                field_name=field_name, label=feature.label or field_name,
                value=value, minimum=lo, maximum=hi, position=position,
            ))

        if not flags:
            return OODReport(is_out_of_distribution=False, flags=[], message="")

        names = ", ".join(f.label for f in flags[:3])
        message = (
            f"Some of today's values sit at the very edge of what this model has seen "
            f"({names}). The score is still computed from your real inputs, but treat it "
            f"as less reliable than a typical day."
        )
        return OODReport(is_out_of_distribution=True, flags=flags, message=message)

    # ------------------------------------------------------------
    # Cold-start policy (P1 item 13)
    # ------------------------------------------------------------

    @staticmethod
    def cold_start_status(entry_count: int) -> ColdStartStatus:
        """
        States plainly which history-dependent features are meaningful
        yet. Single-day predictions always work - it's the *trend*
        features that need history, and saying so up front is better
        than rendering an empty chart with no explanation.
        """
        stage = "no_data"
        for threshold, name in COLD_START_STAGES:
            if entry_count >= threshold:
                stage = name

        messages = {
            "no_data": "No check-ins yet. Your first one gives you a full score and explanation immediately — trends need a few more days.",
            "single_day": "One check-in logged. Your score and its reasons are fully available; trends and weekday patterns need more days.",
            "early": "A few days logged. Trend direction is starting to mean something; weekday patterns still need repeats.",
            "week": "About a week of history. Trends and week-over-week comparison are now meaningful.",
            "established": "Three weeks or more logged. Every trend, weekday and before/after view here is on solid ground.",
        }

        return ColdStartStatus(
            entry_count=entry_count,
            stage=stage,
            trend_available=entry_count >= 3,
            weekday_pattern_available=entry_count >= 7,
            week_comparison_available=entry_count >= 7,
            message=messages[stage],
        )

    # ------------------------------------------------------------
    # Day-of-week reliability (P1 item 14)
    # ------------------------------------------------------------

    @staticmethod
    def weekday_reliability(entries: list[dict[str, Any]]) -> list[WeekdayReliability]:
        """
        Per-weekday averages annotated with how many observations back
        them. A weekday seen once gets `is_reliable=False` and the UI is
        expected to de-emphasise it rather than present one Tuesday as
        "your Tuesdays".
        """
        counts: Counter = Counter()
        totals: dict[str, float] = {}

        for entry in entries:
            weekday = entry.get("day_of_week")
            score = entry.get("health_score")
            if not weekday or score is None:
                continue
            try:
                value = float(score)
            except (TypeError, ValueError):
                continue
            counts[weekday] += 1
            totals[weekday] = totals.get(weekday, 0.0) + value

        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        result: list[WeekdayReliability] = []
        for weekday in order:
            n = counts.get(weekday, 0)
            avg = round(totals[weekday] / n, 2) if n else None
            result.append(WeekdayReliability(
                weekday=weekday, observations=n, average_score=avg,
                is_reliable=n >= WEEKDAY_MIN_OBSERVATIONS,
            ))
        return result
