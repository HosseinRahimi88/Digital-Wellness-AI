"""
Risk Alert Service
--------------------
Small, rule-based helper (same pattern as services/achievement_service.py)
that surfaces "Critical Risk Alerts" from a user's real HistoryService
entries - no model logic, no LLM, nothing invented. Three independent,
composable rules, each grounded in data the pipeline already produced:

1. Classification risk: the model's own real `health_class` output was
   "At Risk" on the latest check-in, escalated to "critical" severity
   if it's part of a real consecutive streak.
2. Trend risk: a real multi-check-in decline in `health_score`.
3. Deviation risk: reuses AnalyticsService.detect_exception_days (29's
   personal-baseline z-score statistic) to flag when the latest
   check-in itself was a real negative outlier for this specific user
   - deliberately reused rather than re-implemented, so there is only
   one place "what counts as an exception" is decided.

This never touches models/, artifacts/, or PredictionService/SHAPService
- it only reads fields HistoryService already persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from services.analytics_service import AnalyticsService

# The model's own real classification label for the at-risk class (see
# services/prediction_service.py::PredictionService.CLASS_MAPPING) -
# not re-typed as a magic string anywhere else in this file.
AT_RISK_CLASS_LABEL = "At Risk"

# A streak of at least this many consecutive At-Risk check-ins escalates
# from "warning" to "critical" severity.
CONSECUTIVE_AT_RISK_FOR_CRITICAL = 2

# A decline streak needs at least this many consecutive check-ins,
# each strictly lower than the last, AND a total drop of at least this
# many points, before it's flagged - short/small dips are normal noise.
DECLINE_STREAK_LENGTH = 3
DECLINE_STREAK_MIN_TOTAL_DROP = 10.0


@dataclass(slots=True)
class RiskAlert:
    severity: str  # "critical" | "warning" | "info"
    title: str
    message: str
    action: Optional[str] = None


class RiskAlertService:
    """Evaluates a user's real check-in history for risk signals."""

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    @staticmethod
    def _trailing_class_streak(ordered_entries: list[dict[str, Any]], class_label: str) -> int:
        """How many of the most recent entries, counting back from the
        end, have health_class == class_label (stops at the first
        entry that doesn't match, or at a missing health_class)."""
        streak = 0
        for entry in reversed(ordered_entries):
            if entry.get("health_class") != class_label:
                break
            streak += 1
        return streak

    @staticmethod
    def _detect_decline_streak(ordered_entries: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """The longest strictly-decreasing run of health_score ending at
        the most recent entry, if it's at least DECLINE_STREAK_LENGTH
        long and drops at least DECLINE_STREAK_MIN_TOTAL_DROP points in
        total. None otherwise (including when scores are missing)."""
        scores = [e.get("health_score") for e in ordered_entries]
        if any(s is None for s in scores[-DECLINE_STREAK_LENGTH:]) or len(scores) < DECLINE_STREAK_LENGTH:
            return None

        run = [scores[-1]]
        for value in reversed(scores[:-1]):
            if value is None:
                break
            if value > run[-1]:
                run.append(value)
            else:
                break
        run.reverse()  # oldest -> newest

        if len(run) < DECLINE_STREAK_LENGTH:
            return None

        total_drop = run[0] - run[-1]
        if total_drop < DECLINE_STREAK_MIN_TOTAL_DROP:
            return None

        return {"length": len(run), "start_score": run[0], "end_score": run[-1]}

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    @classmethod
    def evaluate(cls, entries: list[dict[str, Any]]) -> list[RiskAlert]:
        """
        Returns a list of active RiskAlerts for this user's real
        history, most severe first. Empty list means no active risk
        signal (a good state to render as reassuring, not just absent).
        """
        if not entries:
            return []

        ordered = sorted(entries, key=lambda e: e.get("date", ""))
        latest = ordered[-1]
        alerts: list[RiskAlert] = []

        # --- Rule 1: classification risk -------------------------------
        if latest.get("health_class") == AT_RISK_CLASS_LABEL:
            streak = cls._trailing_class_streak(ordered, AT_RISK_CLASS_LABEL)
            if streak >= CONSECUTIVE_AT_RISK_FOR_CRITICAL:
                alerts.append(RiskAlert(
                    severity="critical",
                    title="Consecutive At-Risk Check-ins",
                    message=(
                        f"Your last {streak} check-ins were all classified "
                        f"\"{AT_RISK_CLASS_LABEL}\" by the model."
                    ),
                    action=(
                        "Review the factors driving this in \"What's Driving Your "
                        "Score\" below, and consider talking to someone you trust "
                        "or a professional if this continues."
                    ),
                ))
            else:
                confidence = latest.get("confidence")
                conf_text = f" ({confidence:.0%} confidence)" if confidence is not None else ""
                alerts.append(RiskAlert(
                    severity="warning",
                    title="Latest Check-in: At Risk",
                    message=(
                        f"Your most recent check-in ({latest.get('date', 'unknown date')}) "
                        f"was classified \"{AT_RISK_CLASS_LABEL}\"{conf_text}."
                    ),
                    action="Check the factors behind this in \"What's Driving Your Score\".",
                ))

        # --- Rule 2: trend risk ------------------------------------------
        decline = cls._detect_decline_streak(ordered)
        if decline is not None:
            alerts.append(RiskAlert(
                severity="warning",
                title="Declining Trend",
                message=(
                    f"Your wellness score has dropped for {decline['length']} "
                    f"check-ins in a row ({decline['start_score']:.1f} → "
                    f"{decline['end_score']:.1f})."
                ),
                action="Worth watching closely before it becomes a longer pattern.",
            ))

        # --- Rule 3: deviation risk (reuses AnalyticsService, doesn't
        # re-derive its own z-score logic) ---------------------------
        exceptions = AnalyticsService.detect_exception_days(ordered)
        if exceptions:
            latest_date = latest.get("date")
            latest_exception = next((e for e in exceptions if e["date"] == latest_date), None)
            if latest_exception and latest_exception["deviations"]:
                worst = latest_exception["deviations"][0]
                if worst["z_score"] < 0:
                    alerts.append(RiskAlert(
                        severity="info",
                        title="Unusual Day Detected",
                        message=(
                            f"Today's {worst['label']} ({worst['value']}) is "
                            f"{abs(worst['z_score']):.1f} standard deviations below "
                            f"your typical {worst['typical']}."
                        ),
                        action=None,
                    ))

        severity_rank = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda a: severity_rank.get(a.severity, 3))
        return alerts
