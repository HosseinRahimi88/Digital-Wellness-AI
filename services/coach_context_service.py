"""
Coach Context Service
-----------------------
Assembles ONE complete, compact digest of everything the app really
knows about a user, so the AI Coach can read the user's whole picture
before it answers anything - rather than looking only at the single most
recent check-in that happened to be cached in the browser.

Why a digest instead of the raw rows
---------------------------------------
The full history is both large and mostly redundant: 40 diary rows of
raw minutes say far less than "screen time trending down 12% over three
weeks, sleep flat, stress up on weekdays". Sending statistics rather
than rows keeps the payload small (it also has to fit a prompt budget
when the optional external connector is switched on) while carrying
strictly more usable meaning.

Honesty rules this file inherits from the rest of the project
---------------------------------------------------------------
* Every number here traces to something the user actually logged. There
  is no imputation and no filler - a field the data cannot support is
  omitted, and `data_sufficiency` says plainly how much history exists
  so the caller can refuse to make claims it cannot back.
* Nothing here is a medical or diagnostic statement. Signals are
  described (`"stress_0_10 averaged 7.2 over 14 days"`), never
  interpreted clinically.
* Excluded days stay excluded from every average, exactly as the user
  asked, but are still counted in `excluded_day_count` so the Coach can
  mention them instead of silently dropping them.
* No model output is recomputed or altered here. Scores, classes and
  SHAP factors are read from what the real pipeline already produced.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Signals worth trending. Each entry is (history field, human label,
# "higher is better"?). Restricted to fields HistoryService actually
# stores per entry.
TRENDED_SIGNALS: list[tuple[str, str, bool]] = [
    ("health_score", "wellness score", True),
    ("total_screen_min", "total screen time", False),
    ("social_min", "social media time", False),
    ("gaming_min", "gaming time", False),
    ("sleep_hours", "sleep hours", True),
    ("sleep_quality_1_10", "sleep quality", True),
    ("stress_0_10", "stress", False),
    ("focus_0_100", "focus", True),
    ("productivity_0_100", "productivity", True),
    ("physical_activity_min_per_day", "physical activity", True),
    ("night_screen_min", "night-time screen use", False),
    ("pickups_per_day", "phone pickups", False),
]

# Below this many entries, a trend is noise rather than a trend. The
# Coach is told this rather than being handed a number it would then
# over-claim on.
MIN_ENTRIES_FOR_TREND = 5
RECENT_WINDOW = 7


@dataclass(slots=True)
class SignalTrend:
    field_name: str
    label: str
    higher_is_better: bool
    recent_mean: float
    earlier_mean: Optional[float]
    change: Optional[float]
    direction: str  # improving | worsening | flat | unknown


@dataclass(slots=True)
class CoachContext:
    """Everything the Coach reads before composing any answer."""

    # --- who the user is -------------------------------------------------
    display_name: str = ""
    language: str = "en"
    persona: Optional[str] = None
    primary_goal: Optional[str] = None
    preferred_effort: Optional[str] = None
    recommendation_tone: Optional[str] = None

    # --- where they stand now --------------------------------------------
    latest_score: Optional[float] = None
    latest_class: Optional[str] = None
    latest_confidence: Optional[float] = None
    latest_date: Optional[str] = None
    dimension_scores: dict[str, Any] = field(default_factory=dict)
    top_factors: list[dict[str, Any]] = field(default_factory=list)

    # --- how they are moving ---------------------------------------------
    entry_count: int = 0
    excluded_day_count: int = 0
    streak_days: int = 0
    longest_streak: int = 0
    score_7d_ago: Optional[float] = None
    score_change_7d: Optional[float] = None
    best_score: Optional[float] = None
    worst_score: Optional[float] = None
    trends: list[SignalTrend] = field(default_factory=list)
    strongest_signals: list[str] = field(default_factory=list)
    weakest_signals: list[str] = field(default_factory=list)

    # --- what they were told to do ---------------------------------------
    active_recommendations: list[dict[str, Any]] = field(default_factory=list)
    plan_focus_areas: list[str] = field(default_factory=list)
    muted_topics: list[str] = field(default_factory=list)

    # --- how much of this is trustworthy ---------------------------------
    data_sufficiency: str = "none"  # none | minimal | partial | good
    notes: list[str] = field(default_factory=list)

    def has_any_data(self) -> bool:
        return self.entry_count > 0 or self.latest_score is not None


def _numeric(entries: list[dict[str, Any]], key: str) -> list[float]:
    out: list[float] = []
    for entry in entries:
        value = entry.get(key)
        if isinstance(value, bool) or value is None:
            continue
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            continue
    return out


def _mean(values: list[float]) -> Optional[float]:
    return round(statistics.fmean(values), 2) if values else None


def _sufficiency(entry_count: int) -> str:
    if entry_count == 0:
        return "none"
    if entry_count < 3:
        return "minimal"
    if entry_count < MIN_ENTRIES_FOR_TREND:
        return "partial"
    return "good"


class CoachContextService:
    """Builds a CoachContext from the user's own real, stored data."""

    @classmethod
    def build(
        cls,
        *,
        entries: list[dict[str, Any]],
        account: Any = None,
        latest_result: Optional[dict[str, Any]] = None,
        latest_user_data: Optional[dict[str, Any]] = None,
        plan_focus_areas: Optional[list[str]] = None,
        muted_topics: Optional[list[str]] = None,
        language: str = "en",
        excluded_day_count: int = 0,
    ) -> CoachContext:
        """
        `entries` must already have excluded days filtered out (the
        caller owns that decision); `excluded_day_count` is passed
        separately so the Coach can still mention them.
        """
        ctx = CoachContext(language=language, excluded_day_count=excluded_day_count)

        if account is not None:
            ctx.display_name = getattr(account, "display_name", "") or ""
            ctx.primary_goal = getattr(account, "primary_goal", None)
            ctx.preferred_effort = getattr(account, "preferred_effort", None)
            ctx.recommendation_tone = getattr(account, "recommendation_tone", None)

        ctx.entry_count = len(entries)
        ctx.data_sufficiency = _sufficiency(ctx.entry_count)
        ctx.plan_focus_areas = list(plan_focus_areas or [])
        ctx.muted_topics = list(muted_topics or [])

        cls._fill_current_standing(ctx, entries, latest_result, latest_user_data)
        cls._fill_movement(ctx, entries)
        cls._fill_trends(ctx, entries)
        cls._fill_notes(ctx)
        return ctx

    # ------------------------------------------------------ current state

    @staticmethod
    def _fill_current_standing(
        ctx: CoachContext,
        entries: list[dict[str, Any]],
        latest_result: Optional[dict[str, Any]],
        latest_user_data: Optional[dict[str, Any]],
    ) -> None:
        latest_entry = entries[-1] if entries else {}
        ctx.latest_date = latest_entry.get("date")
        ctx.latest_score = latest_entry.get("health_score")
        ctx.latest_class = latest_entry.get("health_class")
        ctx.latest_confidence = latest_entry.get("confidence")
        ctx.persona = latest_entry.get("persona")

        # A just-completed prediction is fresher than the stored row and
        # carries the SHAP factors, which history does not keep in full.
        if latest_result:
            ctx.latest_score = latest_result.get("regression_score", ctx.latest_score)
            ctx.latest_class = latest_result.get("prediction", ctx.latest_class)
            factors = latest_result.get("shap_features") or []
            ctx.top_factors = [
                {
                    "feature": f.get("feature"),
                    "impact": f.get("shap_value"),
                    "direction": "raises" if (f.get("shap_value") or 0) > 0 else "lowers",
                }
                for f in factors[:6]
                if isinstance(f, dict)
            ]
            ctx.active_recommendations = [
                {
                    "category": r.get("category"),
                    "action": r.get("action") or r.get("recommendation"),
                    "reason": r.get("reason"),
                }
                for r in (latest_result.get("recommendations") or [])[:5]
                if isinstance(r, dict)
            ]
        elif latest_entry.get("top_shap_feature"):
            ctx.top_factors = [{
                "feature": latest_entry["top_shap_feature"],
                "impact": None,
                "direction": "unknown",
            }]

        if latest_user_data:
            try:
                from utils.dimension_scores import compute_dimension_scores
                ctx.dimension_scores = compute_dimension_scores(latest_user_data) or {}
            except Exception:  # noqa: BLE001 - a digest must never break the chat
                logger.debug("dimension scores unavailable for coach context", exc_info=True)

    # ---------------------------------------------------------- movement

    @staticmethod
    def _fill_movement(ctx: CoachContext, entries: list[dict[str, Any]]) -> None:
        scores = _numeric(entries, "health_score")
        if scores:
            ctx.best_score = round(max(scores), 1)
            ctx.worst_score = round(min(scores), 1)

        if len(entries) >= 8:
            week_ago = entries[-8].get("health_score")
            if week_ago is not None and ctx.latest_score is not None:
                try:
                    ctx.score_7d_ago = round(float(week_ago), 1)
                    ctx.score_change_7d = round(float(ctx.latest_score) - float(week_ago), 1)
                except (TypeError, ValueError):
                    pass

        try:
            from services.progress_service import ProgressService
            summary = ProgressService.summarize(entries)
            ctx.streak_days = getattr(summary, "current_streak", 0) or 0
            ctx.longest_streak = getattr(summary, "longest_streak", 0) or 0
        except Exception:  # noqa: BLE001
            logger.debug("progress summary unavailable for coach context", exc_info=True)

    # ------------------------------------------------------------ trends

    @classmethod
    def _fill_trends(cls, ctx: CoachContext, entries: list[dict[str, Any]]) -> None:
        if len(entries) < MIN_ENTRIES_FOR_TREND:
            return

        recent = entries[-RECENT_WINDOW:]
        earlier = entries[:-RECENT_WINDOW]

        for field_name, label, higher_is_better in TRENDED_SIGNALS:
            recent_values = _numeric(recent, field_name)
            if not recent_values:
                continue
            recent_mean = _mean(recent_values)
            earlier_mean = _mean(_numeric(earlier, field_name)) if earlier else None

            change: Optional[float] = None
            direction = "unknown"
            if recent_mean is not None and earlier_mean is not None:
                change = round(recent_mean - earlier_mean, 2)
                # A change under 3% of the earlier level is treated as
                # flat rather than reported as movement in either
                # direction - otherwise every signal always "changed".
                threshold = max(abs(earlier_mean) * 0.03, 0.01)
                if abs(change) < threshold:
                    direction = "flat"
                else:
                    improved = change > 0 if higher_is_better else change < 0
                    direction = "improving" if improved else "worsening"

            ctx.trends.append(SignalTrend(
                field_name=field_name, label=label, higher_is_better=higher_is_better,
                recent_mean=recent_mean, earlier_mean=earlier_mean,
                change=change, direction=direction,
            ))

        ctx.strongest_signals = [t.label for t in ctx.trends if t.direction == "improving"][:4]
        ctx.weakest_signals = [t.label for t in ctx.trends if t.direction == "worsening"][:4]

    # ------------------------------------------------------------- notes

    @staticmethod
    def _fill_notes(ctx: CoachContext) -> None:
        """Plain-language caveats, so the Coach can quote its own limits."""
        if ctx.entry_count == 0:
            ctx.notes.append("No check-ins logged yet, so there is nothing to read about this user.")
            return
        if ctx.entry_count < MIN_ENTRIES_FOR_TREND:
            ctx.notes.append(
                f"Only {ctx.entry_count} check-in(s) logged - too few for any trend claim; "
                "describe the latest entry only."
            )
        if ctx.excluded_day_count:
            ctx.notes.append(
                f"{ctx.excluded_day_count} day(s) are excluded from averages at the user's request."
            )
        if ctx.muted_topics:
            ctx.notes.append(
                "The user muted coaching on: " + ", ".join(ctx.muted_topics) +
                " - do not push advice on those."
            )
