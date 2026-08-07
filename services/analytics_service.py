"""
Analytics Service
--------------------
Pure data-shaping for app/pages/Analytics.py. Every method here takes
already-real data (HistoryService entries, a validated user_data dict,
or PredictionService's SHAP output) and returns a plain pandas
DataFrame/list ready for the page to hand straight to a Plotly Express
chart - no `st.*` calls, no chart objects, no HTML.

This does not compute anything new: it is the same groupby/filter/sort
logic that used to live inline in the page, moved here so Analytics.py
is a thin controller (fetch data -> ask this service to shape it ->
render).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import pandas as pd

from config.analytics_settings import (
    BEHAVIORAL_FIELD_LABELS,
    DOMINO_MIN_CORRELATION,
    EXCEPTION_Z_SCORE_THRESHOLD,
    MAX_DOMINO_CHAIN_LENGTH,
    MAX_EXCEPTION_DAYS_SHOWN,
    MIN_DISTINCT_HOURS_FOR_GOLDEN_HOUR,
    MIN_ENTRIES_FOR_CORRELATION,
    MIN_ENTRIES_FOR_EXCEPTION_DETECTION,
    MIN_ENTRIES_FOR_GOLDEN_HOUR,
    MIN_ENTRIES_FOR_HOUR_WEEKDAY_HEATMAP,
    MIN_ENTRIES_FOR_TYPICAL_DAY,
    MIN_ENTRIES_FOR_WEEKDAY_PATTERN,
    MIN_POINTS_FOR_TREND_CHART,
    MIN_SAMPLES_PER_WEEKDAY_FOR_LEVERAGE,
    MIN_WEEKDAYS_FOR_PATTERN_CHART,
    SCREEN_TIME_CATEGORY_LABELS,
    WEEKDAY_ORDER,
)
from core.feature_schema import FEATURE_SCHEMA
from services.history_service import TRACKED_FIELDS


class AnalyticsService:
    """Data-shaping helpers backing the Analytics page's charts."""

    # ------------------------------------------------------------
    # Score history (HistoryService entries -> trend chart data)
    # ------------------------------------------------------------

    @staticmethod
    def build_score_history_frame(entries: list[dict[str, Any]]) -> pd.DataFrame:
        """
        Entries -> a DataFrame sorted by date with rows missing a
        health_score dropped. Empty DataFrame if `entries` is empty.
        """
        if not entries:
            return pd.DataFrame(columns=["date", "health_score"])

        df = pd.DataFrame(entries)
        df["date"] = pd.to_datetime(df["date"])
        return df.dropna(subset=["health_score"]).sort_values("date")

    @staticmethod
    def has_enough_points_for_trend(history_df: pd.DataFrame) -> bool:
        return len(history_df) >= MIN_POINTS_FOR_TREND_CHART

    @staticmethod
    def build_weekday_pattern(history_df: pd.DataFrame) -> Optional[pd.Series]:
        """
        Average health_score grouped by day_of_week, reindexed to
        Monday->Sunday order. None if there isn't enough weekday
        variety to make the chart meaningful.
        """
        if "day_of_week" not in history_df.columns:
            return None
        if history_df["day_of_week"].nunique() <= 1:
            return None

        weekday_avg = (
            history_df.groupby("day_of_week")["health_score"]
            .mean()
            .reindex(WEEKDAY_ORDER)
            .dropna()
        )
        if len(weekday_avg) < MIN_WEEKDAYS_FOR_PATTERN_CHART:
            return None
        return weekday_avg

    # ------------------------------------------------------------
    # Screen-time breakdown (this session's validated user_data)
    # ------------------------------------------------------------

    @staticmethod
    def build_category_breakdown(user_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Rows of {"Category": label, "Minutes/Day": value} for the pie chart."""
        return [
            {"Category": label, "Minutes/Day": float(user_data[field])}
            for field, label in SCREEN_TIME_CATEGORY_LABELS.items()
            if field in user_data and user_data[field] is not None
        ]

    @staticmethod
    def build_screen_time_comparison(user_data: dict[str, Any]) -> Optional[list[dict[str, Any]]]:
        """
        Rows of {"Metric": ..., "Minutes/Day": ...} comparing today's total
        screen time against the user's personal baseline. None if either
        value is missing.
        """
        total_screen = user_data.get("total_screen_min")
        baseline = user_data.get("screen_ewma_baseline")
        if total_screen is None or baseline is None:
            return None
        return [
            {"Metric": "Today", "Minutes/Day": float(total_screen)},
            {"Metric": "Your Baseline", "Minutes/Day": float(baseline)},
        ]

    # ------------------------------------------------------------
    # SHAP explanations (this session's PredictionResult.shap_features)
    # ------------------------------------------------------------

    @staticmethod
    def feature_label(feature_name: str) -> str:
        """Human-readable label for a raw model feature name, via FEATURE_SCHEMA
        when available, else a title-cased fallback of the raw name."""
        feature = FEATURE_SCHEMA.get(feature_name)
        if feature is not None and feature.label:
            return feature.label
        return feature_name.replace("_", " ").title()

    @classmethod
    def build_shap_frame(cls, shap_features: Optional[list[Any]]) -> Optional[pd.DataFrame]:
        """
        Ranked SHAP features -> a DataFrame with Feature / SHAP Value /
        Direction columns, sorted ascending by SHAP Value (matches the
        original chart's bar ordering). None if there's nothing to show.
        """
        if not shap_features:
            return None

        rows = [
            {
                "Feature": cls.feature_label(f.feature),
                "SHAP Value": f.shap_value,
                "Direction": "Increases Score" if f.shap_value > 0 else "Decreases Score",
            }
            for f in shap_features
        ]
        return pd.DataFrame(rows).sort_values("SHAP Value")

    # ------------------------------------------------------------
    # Behavioral Patterns (all built from real HistoryService entries -
    # see services/history_service.py's own scope note: these methods
    # never touch the ML pipeline, never re-predict, and never invent
    # values. They only reshape/aggregate/statistically compare fields
    # HistoryService already persisted from real PredictionService
    # runs. Each method returns None (never raises) when there isn't
    # enough history yet for the underlying statistic to be meaningful
    # - callers render a "keep checking in" caption in that case.
    # ------------------------------------------------------------

    #: Fields these methods look at, in display order: the model's own
    #: wellness score first, then every raw/derived habit field
    #: HistoryService tracks. Sourced from HistoryService.TRACKED_FIELDS
    #: (not re-typed here) so the two never drift apart.
    _BEHAVIORAL_FIELDS = ["health_score"] + list(TRACKED_FIELDS)

    @classmethod
    def _numeric_field_series(cls, df: pd.DataFrame, field_name: str) -> pd.Series:
        """`field_name` column coerced to numeric, non-numeric/missing -> NaN."""
        return pd.to_numeric(df[field_name], errors="coerce")

    @classmethod
    def _available_behavioral_fields(cls, df: pd.DataFrame) -> list[str]:
        return [f for f in cls._BEHAVIORAL_FIELDS if f in df.columns]

    @classmethod
    def compute_field_averages(cls, entries: list[dict[str, Any]]) -> dict[str, float]:
        """
        Plain {field_name: this user's real historical average} for
        health_score + every available tracked field - raw field names
        (not display labels), the shape CohortService/LeaderboardService
        /RareAchievementService expect as input. Kept as one shared
        helper so every consumer of "this user's real average per
        field" computes it the same way instead of each re-deriving
        its own mean.
        """
        if not entries:
            return {}
        df = pd.DataFrame(entries)
        fields = cls._available_behavioral_fields(df)
        averages = {}
        for field_name in fields:
            values = cls._numeric_field_series(df, field_name).dropna()
            if not values.empty:
                averages[field_name] = float(values.mean())
        return averages

    @classmethod
    def compute_weekly_behavioral_pattern(
        cls, entries: list[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """
        Per-day-of-week averages across health_score *and* every tracked
        habit field (a superset of build_weekday_pattern above, which
        only ever looked at health_score). Answers "what does a typical
        Monday/Tuesday/... look like for this person", not just "which
        day scores highest".

        Returns None if there isn't enough weekday variety recorded
        yet. Otherwise:
            {
                "table": DataFrame indexed Monday->Sunday, one column
                         per available field, rounded to 1 decimal,
                "best_day": (weekday_name, avg_health_score) or None,
                "worst_day": (weekday_name, avg_health_score) or None,
            }
        """
        if len(entries) < MIN_ENTRIES_FOR_WEEKDAY_PATTERN:
            return None

        df = pd.DataFrame(entries)
        if "day_of_week" not in df.columns:
            return None
        if df["day_of_week"].nunique() < MIN_WEEKDAYS_FOR_PATTERN_CHART:
            return None

        fields = cls._available_behavioral_fields(df)
        if not fields:
            return None

        numeric = df[["day_of_week"]].copy()
        for field_name in fields:
            numeric[field_name] = cls._numeric_field_series(df, field_name)

        weekday_avg = (
            numeric.groupby("day_of_week")[fields]
            .mean()
            .reindex(WEEKDAY_ORDER)
            .dropna(how="all")
        )
        if weekday_avg.empty:
            return None

        best_day = worst_day = None
        if "health_score" in weekday_avg.columns:
            score_col = weekday_avg["health_score"].dropna()
            if len(score_col) >= MIN_WEEKDAYS_FOR_PATTERN_CHART:
                best_day = (str(score_col.idxmax()), round(float(score_col.max()), 1))
                worst_day = (str(score_col.idxmin()), round(float(score_col.min()), 1))

        return {
            "table": weekday_avg.round(1),
            "best_day": best_day,
            "worst_day": worst_day,
        }

    @classmethod
    def compute_typical_day_profile(
        cls, entries: list[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """
        A "typical day" profile: mean + population-independent sample
        std dev per tracked field (std dev doubles as a consistency
        signal - a small std dev means the user's days look alike; a
        large one means they vary a lot), plus a weekday-vs-weekend
        split and a latest-check-in-vs-typical comparison.

        Returns None if there isn't enough history yet. Otherwise:
            {
                "profile": DataFrame with columns
                    [Metric, Typical (avg), Consistency (std dev), n],
                "weekday_vs_weekend": {"weekday_avg", "weekend_avg"} or None,
                "latest_vs_typical": {
                    "latest_date", "latest_score", "typical_score"
                } or None,
            }
        """
        if len(entries) < MIN_ENTRIES_FOR_TYPICAL_DAY:
            return None

        df = pd.DataFrame(entries)
        fields = cls._available_behavioral_fields(df)
        if not fields:
            return None

        rows = []
        for field_name in fields:
            values = cls._numeric_field_series(df, field_name).dropna()
            if values.empty:
                continue
            std_dev = float(values.std(ddof=1)) if len(values) >= 2 else 0.0
            rows.append({
                "Metric": BEHAVIORAL_FIELD_LABELS.get(field_name, field_name),
                "Typical (avg)": round(float(values.mean()), 1),
                "Consistency (std dev)": round(std_dev, 1),
                "n": int(len(values)),
            })
        if not rows:
            return None
        profile_df = pd.DataFrame(rows)

        weekday_vs_weekend = None
        if "day_of_week" in df.columns and "health_score" in df.columns:
            is_weekend = df["day_of_week"].isin(["Saturday", "Sunday"])
            scores = cls._numeric_field_series(df, "health_score")
            weekday_scores = scores[~is_weekend].dropna()
            weekend_scores = scores[is_weekend].dropna()
            if len(weekday_scores) > 0 and len(weekend_scores) > 0:
                weekday_vs_weekend = {
                    "weekday_avg": round(float(weekday_scores.mean()), 1),
                    "weekend_avg": round(float(weekend_scores.mean()), 1),
                }

        latest_vs_typical = None
        if "health_score" in df.columns:
            ordered = sorted(entries, key=lambda e: e.get("date", ""))
            latest = ordered[-1] if ordered else None
            overall_scores = cls._numeric_field_series(df, "health_score").dropna()
            if latest is not None and latest.get("health_score") is not None and len(overall_scores) > 0:
                latest_vs_typical = {
                    "latest_date": latest.get("date"),
                    "latest_score": round(float(latest["health_score"]), 1),
                    "typical_score": round(float(overall_scores.mean()), 1),
                }

        return {
            "profile": profile_df,
            "weekday_vs_weekend": weekday_vs_weekend,
            "latest_vs_typical": latest_vs_typical,
        }

    @classmethod
    def build_hour_weekday_heatmap(
        cls, entries: list[dict[str, Any]]
    ) -> Optional[dict[str, pd.DataFrame]]:
        """
        Day-of-week x hour-of-check-in matrix of average health_score,
        built from each entry's real `recorded_at` timestamp
        (HistoryService.record() stamps this at write time - see its
        docstring). This shows *when* the user tends to check in and
        how their score looked at that time, not a claim about what
        hour they were using their devices - the model has no
        finer-than-daily behavioral timestamp to draw that from.

        Returns None if there isn't enough timestamped history yet.
        Otherwise {"scores": DataFrame (mean), "counts": DataFrame (n)},
        both indexed Monday->Sunday with hour-of-day (0-23) columns
        limited to hours that actually have at least one check-in.
        """
        if len(entries) < MIN_ENTRIES_FOR_HOUR_WEEKDAY_HEATMAP:
            return None

        rows = []
        for entry in entries:
            recorded_at = entry.get("recorded_at")
            day_of_week = entry.get("day_of_week")
            score = entry.get("health_score")
            if not recorded_at or not day_of_week or score is None:
                continue
            try:
                hour = datetime.fromisoformat(recorded_at).hour
            except ValueError:
                continue
            rows.append({"day_of_week": day_of_week, "hour": hour, "health_score": float(score)})

        if len(rows) < MIN_ENTRIES_FOR_HOUR_WEEKDAY_HEATMAP:
            return None

        hour_df = pd.DataFrame(rows)
        scores = (
            hour_df.pivot_table(index="day_of_week", columns="hour", values="health_score", aggfunc="mean")
            .reindex(WEEKDAY_ORDER)
        )
        counts = (
            hour_df.pivot_table(index="day_of_week", columns="hour", values="health_score", aggfunc="count")
            .reindex(WEEKDAY_ORDER)
        )
        if scores.dropna(how="all").empty:
            return None
        return {"scores": scores.round(1), "counts": counts}

    @classmethod
    def detect_exception_days(
        cls, entries: list[dict[str, Any]]
    ) -> Optional[list[dict[str, Any]]]:
        """
        Flags days that were statistical exceptions for *this specific
        user* - each tracked field's own historical mean/sample-std
        (computed only from that user's real entries) becomes the
        baseline, and any day where a field's z-score exceeds
        EXCEPTION_Z_SCORE_THRESHOLD is surfaced with the fields that
        deviated most, largest deviation first. This is personal-
        baseline outlier detection (each user is compared only to their
        own history), not a population/cohort comparison.

        Returns None if there isn't enough history for any field to
        have a statistically meaningful baseline yet. Otherwise a list
        of exception-day dicts (most exceptional first, capped to
        MAX_EXCEPTION_DAYS_SHOWN):
            {
                "date", "day_of_week", "health_score", "top_shap_feature",
                "deviations": [
                    {"field", "label", "value", "typical", "z_score"}, ...
                ],
                "max_abs_z": float,
            }
        """
        if len(entries) < MIN_ENTRIES_FOR_EXCEPTION_DETECTION:
            return None

        df = pd.DataFrame(entries)
        fields = cls._available_behavioral_fields(df)

        baselines: dict[str, tuple[float, float]] = {}
        for field_name in fields:
            values = cls._numeric_field_series(df, field_name).dropna()
            if len(values) < MIN_ENTRIES_FOR_EXCEPTION_DETECTION:
                continue
            std_dev = float(values.std(ddof=1))
            if std_dev == 0.0:
                # Perfectly constant field for this user - no
                # meaningful deviation is possible, skip it rather than
                # dividing by zero.
                continue
            baselines[field_name] = (float(values.mean()), std_dev)

        if not baselines:
            return None

        exceptions = []
        for _, row in df.iterrows():
            deviations = []
            for field_name, (mean, std_dev) in baselines.items():
                raw_value = row.get(field_name)
                if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
                    continue
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    continue
                z_score = (value - mean) / std_dev
                if abs(z_score) >= EXCEPTION_Z_SCORE_THRESHOLD:
                    deviations.append({
                        "field": field_name,
                        "label": BEHAVIORAL_FIELD_LABELS.get(field_name, field_name),
                        "value": round(value, 1),
                        "typical": round(mean, 1),
                        "z_score": round(z_score, 2),
                    })

            if not deviations:
                continue
            deviations.sort(key=lambda d: abs(d["z_score"]), reverse=True)
            exceptions.append({
                "date": row.get("date"),
                "day_of_week": row.get("day_of_week"),
                "health_score": row.get("health_score"),
                "top_shap_feature": row.get("top_shap_feature"),
                "deviations": deviations,
                "max_abs_z": max(abs(d["z_score"]) for d in deviations),
            })

        if not exceptions:
            return []

        exceptions.sort(key=lambda x: x["max_abs_z"], reverse=True)
        return exceptions[:MAX_EXCEPTION_DAYS_SHOWN]

    # ------------------------------------------------------------
    # Relationships & Opportunities (Phase 2 - all still built purely
    # from real HistoryService entries; same "returns None instead of
    # raising when history is too sparse" contract as the Behavioral
    # Patterns methods above).
    # ------------------------------------------------------------

    @classmethod
    def compute_field_correlations(cls, entries: list[dict[str, Any]]) -> Optional[pd.DataFrame]:
        """
        Pearson correlation matrix across health_score + every tracked
        habit field this user has enough data for. Backs both the
        Behavioral Relationship Explorer (29) and the Habit Domino
        Visualization (30), which reuses this instead of recomputing
        its own correlations.

        A field is excluded from the matrix (not just left as NaN) if
        it has fewer than MIN_ENTRIES_FOR_CORRELATION non-null values
        or zero variance - a correlation against a near-constant field
        is mathematically undefined/meaningless, not just noisy.

        Returns None if fewer than 2 fields qualify.
        """
        if len(entries) < MIN_ENTRIES_FOR_CORRELATION:
            return None

        df = pd.DataFrame(entries)
        fields = cls._available_behavioral_fields(df)
        if len(fields) < 2:
            return None

        numeric = pd.DataFrame({f: cls._numeric_field_series(df, f) for f in fields})

        usable = []
        for f in fields:
            col = numeric[f].dropna()
            if len(col) < MIN_ENTRIES_FOR_CORRELATION:
                continue
            std_dev = col.std(ddof=1)
            if std_dev is None or pd.isna(std_dev) or std_dev == 0.0:
                continue
            usable.append(f)

        if len(usable) < 2:
            return None

        corr = numeric[usable].corr(method="pearson", min_periods=MIN_ENTRIES_FOR_CORRELATION)
        return corr.round(2)

    @classmethod
    def build_relationship_scatter(
        cls, entries: list[dict[str, Any]], field_x: str, field_y: str
    ) -> Optional[pd.DataFrame]:
        """
        Paired (field_x, field_y, date) rows - real values from the same
        check-in - for the Relationship Explorer's scatter chart. Rows
        missing either value are dropped (pairwise, matching how the
        correlation matrix itself handles missing data). None if no
        complete pairs exist.
        """
        df = pd.DataFrame(entries)
        if field_x not in df.columns or field_y not in df.columns:
            return None

        paired = pd.DataFrame({
            field_x: cls._numeric_field_series(df, field_x),
            field_y: cls._numeric_field_series(df, field_y),
            "date": df.get("date"),
        }).dropna(subset=[field_x, field_y])

        if paired.empty:
            return None
        return paired

    @classmethod
    def compute_habit_domino_chain(cls, entries: list[dict[str, Any]]) -> Optional[list[dict[str, Any]]]:
        """
        A "domino chain" of real correlations, starting at
        health_score: at each step, follow the strongest-magnitude
        correlation to a habit field not already in the chain, so long
        as it clears DOMINO_MIN_CORRELATION - i.e. "your Wellness Score
        correlates most with Stress, which itself correlates most with
        Social Media minutes, which correlates most with Sleep Hours".
        This is the *same* correlation matrix compute_field_correlations
        produces, just walked as a chain instead of shown as a grid -
        no separate/duplicated statistic.

        Returns None if there isn't a usable correlation matrix, or if
        the very first (health_score) link doesn't clear the minimum
        correlation strength. Otherwise a list of
        {"field", "label", "correlation_to_next"} dicts, in chain
        order, where the last entry's `correlation_to_next` is None.
        """
        corr = cls.compute_field_correlations(entries)
        if corr is None or "health_score" not in corr.columns:
            return None

        chain: list[dict[str, Any]] = [
            {"field": "health_score", "label": BEHAVIORAL_FIELD_LABELS.get("health_score", "health_score"), "correlation_to_next": None}
        ]
        used = {"health_score"}
        current = "health_score"

        for _ in range(MAX_DOMINO_CHAIN_LENGTH - 1):
            remaining = [f for f in corr.index if f not in used]
            if not remaining:
                break
            candidates = corr.loc[remaining, current].dropna()
            if candidates.empty:
                break
            next_field = candidates.abs().idxmax()
            strength = float(candidates[next_field])
            if abs(strength) < DOMINO_MIN_CORRELATION:
                break

            chain[-1]["correlation_to_next"] = round(strength, 2)
            chain.append({
                "field": next_field,
                "label": BEHAVIORAL_FIELD_LABELS.get(next_field, next_field),
                "correlation_to_next": None,
            })
            used.add(next_field)
            current = next_field

        if len(chain) < 2:
            return None
        return chain

    @classmethod
    def detect_golden_hour(cls, entries: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """
        The check-in hour (from each entry's real `recorded_at`
        timestamp, same field build_hour_weekday_heatmap uses) with the
        highest average health_score - and, for contrast, the one with
        the lowest. Collapses across the day-of-week axis the heatmap
        keeps, since Golden Hour asks "what hour", not "what hour on
        what day".

        Returns None without enough timestamped history across enough
        distinct hours for an hour-level average to be meaningful.
        Otherwise:
            {
                "golden_hour": int (0-23), "golden_hour_avg_score": float,
                "golden_hour_count": int,
                "toughest_hour": int, "toughest_hour_avg_score": float,
                "table": DataFrame indexed by hour with mean/count columns,
            }
        """
        rows = []
        for entry in entries:
            recorded_at = entry.get("recorded_at")
            score = entry.get("health_score")
            if not recorded_at or score is None:
                continue
            try:
                hour = datetime.fromisoformat(recorded_at).hour
            except ValueError:
                continue
            rows.append({"hour": hour, "health_score": float(score)})

        if len(rows) < MIN_ENTRIES_FOR_GOLDEN_HOUR:
            return None

        hour_df = pd.DataFrame(rows)
        if hour_df["hour"].nunique() < MIN_DISTINCT_HOURS_FOR_GOLDEN_HOUR:
            return None

        grouped = hour_df.groupby("hour")["health_score"].agg(["mean", "count"])
        if grouped.empty:
            return None

        best_hour = int(grouped["mean"].idxmax())
        worst_hour = int(grouped["mean"].idxmin())

        return {
            "golden_hour": best_hour,
            "golden_hour_avg_score": round(float(grouped.loc[best_hour, "mean"]), 1),
            "golden_hour_count": int(grouped.loc[best_hour, "count"]),
            "toughest_hour": worst_hour,
            "toughest_hour_avg_score": round(float(grouped.loc[worst_hour, "mean"]), 1),
            "table": grouped.round(1),
        }

    @classmethod
    def detect_leverage_day(cls, entries: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """
        The day of week with the highest *variance* (sample std dev) in
        health_score - i.e. the day this user's outcomes are least
        predictable, so it's where a behavior change has the most
        headroom to matter. Deliberately a different statistic from
        compute_weekly_behavioral_pattern's "worst average day" (05):
        a day can have a perfectly fine average while still swinging
        wildly, and that's exactly the day with unrealized leverage.

        Returns None if no weekday has enough samples yet. Otherwise:
            {
                "day_of_week", "std_dev", "mean", "range": (min, max),
                "n", "likely_lever": most frequent top_shap_feature
                    logged on that weekday, or None,
                "all_days": the same stats for every qualifying weekday,
                    sorted most-to-least variable,
            }
        """
        df = pd.DataFrame(entries)
        if "day_of_week" not in df.columns or "health_score" not in df.columns:
            return None

        df = df.assign(_score=cls._numeric_field_series(df, "health_score"))

        stats = []
        for weekday, group in df.groupby("day_of_week"):
            values = group["_score"].dropna()
            if len(values) < MIN_SAMPLES_PER_WEEKDAY_FOR_LEVERAGE:
                continue
            stats.append({
                "day_of_week": weekday,
                "std_dev": float(values.std(ddof=1)),
                "mean": float(values.mean()),
                "min": float(values.min()),
                "max": float(values.max()),
                "n": int(len(values)),
            })

        if not stats:
            return None

        stats.sort(key=lambda s: s["std_dev"], reverse=True)
        top = stats[0]

        likely_lever = None
        if "top_shap_feature" in df.columns:
            weekday_rows = df[df["day_of_week"] == top["day_of_week"]]
            features = weekday_rows["top_shap_feature"].dropna()
            if not features.empty:
                likely_lever = features.value_counts().idxmax()

        return {
            "day_of_week": top["day_of_week"],
            "std_dev": round(top["std_dev"], 1),
            "mean": round(top["mean"], 1),
            "range": (round(top["min"], 1), round(top["max"], 1)),
            "n": top["n"],
            "likely_lever": likely_lever,
            "all_days": [
                {**s, "std_dev": round(s["std_dev"], 1), "mean": round(s["mean"], 1)}
                for s in stats
            ],
        }
