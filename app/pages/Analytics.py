"""
Analytics Dashboard

Shows charts, summaries and explanations built from the user's most
recent *real* prediction (PredictionService + SHAPService), the same
session-state values Prediction.py stores and AI_Coach.py already
consumes. No mock/placeholder data.

Also shows a real historical trend section (Score History, Day-of-Week
Pattern) built from HistoryService - UX idea ported from the Parisa
project's `render_insights_page()` ("Forecast trend" / "Day-of-week
pattern" charts), reworded and rebuilt on A's own data. B's chart
plotted "Current" against a genuine 7-day-ahead forecast the model
produces; A's classifier/regressor don't forecast forward in time (see
app/pages/Dashboard.py's docstring for the same distinction), so this
section plots one real series - your recorded wellness score per
check-in - not a forecast. Unlike the session-scoped section below, it
reads history directly and works even without a prediction run in this
session.
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="Analytics",
    page_icon="📊",
    layout="wide"
)

from components.theme import Theme
Theme.load()

import plotly.express as px
import pandas as pd

from components.section_header import SectionHeader
from components.metric_card import MetricCard
from components.status_badge import StatusBadge
from components.probability_chart import ProbabilityChart
from components.recommendation_card import RecommendationCard
from config.analytics_settings import BEHAVIORAL_FIELD_LABELS
from services.analytics_service import AnalyticsService
from services.history_service import HistoryService
from utils.session import (
    get_last_prediction_result,
    get_last_recommendations,
    get_last_user_data,
    get_user_id,
)

st.title("📊 Digital Wellness Analytics")

# ---------------------------------------------------------
# Score History (real HistoryService data - available even without a
# prediction run this session)
# ---------------------------------------------------------
_history_service = HistoryService(user_id=get_user_id())
_all_entries = _history_service.get_all()

if _all_entries:
    SectionHeader.render("Score History")

    _history_df = AnalyticsService.build_score_history_frame(_all_entries)

    if AnalyticsService.has_enough_points_for_trend(_history_df):
        fig_trend = px.line(
            _history_df,
            x="date",
            y="health_score",
            markers=True,
            title="Your Recorded Wellness Score Over Time",
            labels={"date": "Date", "health_score": "Wellness Score"},
        )
        fig_trend.update_yaxes(range=[0, 100])
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.caption(
            "One check-in recorded so far. This chart fills in as you "
            "run more predictions over time."
        )

    _weekday_avg = AnalyticsService.build_weekday_pattern(_history_df)
    if _weekday_avg is not None:
        st.subheader("Day-of-Week Pattern")
        fig_weekday = px.bar(
            x=_weekday_avg.index,
            y=_weekday_avg.values,
            labels={"x": "Day of Week", "y": "Avg. Wellness Score"},
            title="Average Wellness Score by Day of Week",
        )
        st.plotly_chart(fig_weekday, use_container_width=True)

    # -------------------------------------------------------
    # Behavioral Patterns: Weekly Behavioral Pattern, Typical Day
    # Analysis, Hour x Weekday Heatmap, Exception Detective - all
    # built from the same real `_all_entries` above via
    # AnalyticsService, degrading gracefully (a caption, not a crash)
    # when a given user doesn't have enough history yet for a
    # particular chart.
    # -------------------------------------------------------
    SectionHeader.render("Behavioral Patterns")

    _tab_pattern, _tab_typical, _tab_heatmap, _tab_exceptions = st.tabs(
        ["📆 Weekly Pattern", "🗓️ Typical Day", "🕒 Hour × Weekday", "🔍 Exception Detective"]
    )

    with _tab_pattern:
        _pattern = AnalyticsService.compute_weekly_behavioral_pattern(_all_entries)
        if _pattern is None:
            st.caption(
                "Check in on a few different days of the week to unlock "
                "your weekly behavioral pattern."
            )
        else:
            _table = _pattern["table"]
            if _pattern["best_day"] and _pattern["worst_day"]:
                _bcol1, _bcol2 = st.columns(2)
                with _bcol1:
                    MetricCard.render(
                        title="Best Day (avg. score)",
                        value=f"{_pattern['best_day'][0]} — {_pattern['best_day'][1]}",
                    )
                with _bcol2:
                    MetricCard.render(
                        title="Toughest Day (avg. score)",
                        value=f"{_pattern['worst_day'][0]} — {_pattern['worst_day'][1]}",
                    )

            _metric_options = [c for c in _table.columns]
            _metric_choice = st.selectbox(
                "Metric",
                options=_metric_options,
                format_func=lambda f: BEHAVIORAL_FIELD_LABELS.get(f, f),
                key="weekly_pattern_metric",
            )
            _series = _table[_metric_choice].dropna()
            fig_pattern = px.bar(
                x=_series.index,
                y=_series.values,
                labels={"x": "Day of Week", "y": BEHAVIORAL_FIELD_LABELS.get(_metric_choice, _metric_choice)},
                title=f"Average {BEHAVIORAL_FIELD_LABELS.get(_metric_choice, _metric_choice)} by Day of Week",
            )
            st.plotly_chart(fig_pattern, use_container_width=True)

            with st.expander("Full weekly pattern table"):
                st.dataframe(
                    _table.rename(columns=lambda f: BEHAVIORAL_FIELD_LABELS.get(f, f)),
                    use_container_width=True,
                )

    with _tab_typical:
        _typical = AnalyticsService.compute_typical_day_profile(_all_entries)
        if _typical is None:
            st.caption("Record a few more check-ins to see your typical-day profile.")
        else:
            if _typical["latest_vs_typical"]:
                _lvt = _typical["latest_vs_typical"]
                MetricCard.render(
                    title=f"Latest Check-in ({_lvt['latest_date']}) vs. Your Typical Score",
                    value=f"{_lvt['latest_score']}",
                    delta=round(_lvt["latest_score"] - _lvt["typical_score"], 1),
                    help_text=f"Your typical score is {_lvt['typical_score']}.",
                )

            if _typical["weekday_vs_weekend"]:
                _wvw = _typical["weekday_vs_weekend"]
                _wcol1, _wcol2 = st.columns(2)
                with _wcol1:
                    MetricCard.render(title="Weekday Avg. Score", value=_wvw["weekday_avg"])
                with _wcol2:
                    MetricCard.render(title="Weekend Avg. Score", value=_wvw["weekend_avg"])

            st.markdown("**Your typical day, field by field**")
            st.caption(
                "\"Consistency\" is the standard deviation across your check-ins - "
                "smaller means that habit looks about the same most days."
            )
            st.dataframe(_typical["profile"], use_container_width=True, hide_index=True)

    with _tab_heatmap:
        _hw = AnalyticsService.build_hour_weekday_heatmap(_all_entries)
        if _hw is None:
            st.caption(
                "Check in at a few different times of day to unlock the "
                "hour × weekday heatmap."
            )
        else:
            _scores = _hw["scores"]
            fig_hw = px.imshow(
                _scores,
                labels={"x": "Hour of Check-in", "y": "Day of Week", "color": "Avg. Wellness Score"},
                color_continuous_scale="RdYlGn",
                zmin=0,
                zmax=100,
                aspect="auto",
                title="Average Wellness Score by Check-in Hour × Day of Week",
            )
            st.plotly_chart(fig_hw, use_container_width=True)
            st.caption(
                "Built from the real timestamp of each of your check-ins - "
                "shows when you tend to check in and how your score looked "
                "then, not a claim about your device usage at that hour."
            )

    with _tab_exceptions:
        _exceptions = AnalyticsService.detect_exception_days(_all_entries)
        if _exceptions is None:
            st.caption(
                "Once you have a longer history, Exception Detective will "
                "flag days that stood out from your personal baseline."
            )
        elif not _exceptions:
            st.success("No statistical outliers yet — your days have been fairly consistent.")
        else:
            st.caption(
                "Days where at least one habit was an unusual distance from "
                "*your own* historical average (not a comparison to other "
                "users)."
            )
            for _exc in _exceptions:
                _score_str = f"{_exc['health_score']:.1f}" if _exc.get("health_score") is not None else "N/A"
                with st.expander(f"{_exc['date']} ({_exc['day_of_week']}) — Score {_score_str}"):
                    for _dev in _exc["deviations"]:
                        _direction = "above" if _dev["z_score"] > 0 else "below"
                        st.write(
                            f"- **{_dev['label']}**: {_dev['value']} "
                            f"({abs(_dev['z_score']):.1f}σ {_direction} your typical {_dev['typical']})"
                        )
                    if _exc.get("top_shap_feature"):
                        st.caption(f"Top driver that day: {_exc['top_shap_feature']}")

    st.divider()

    # -------------------------------------------------------
    # Relationships & Opportunities: Behavioral Relationship Explorer,
    # Habit Domino Visualization, Golden Hour Detection, Leverage Day -
    # same real `_all_entries` source, same graceful-degradation
    # contract as Behavioral Patterns above.
    # -------------------------------------------------------
    SectionHeader.render("Relationships & Opportunities")

    _tab_relations, _tab_domino, _tab_golden, _tab_leverage = st.tabs(
        ["🔗 Relationship Explorer", "🎲 Habit Domino", "✨ Golden Hour", "🎯 Leverage Day"]
    )

    with _tab_relations:
        _corr = AnalyticsService.compute_field_correlations(_all_entries)
        if _corr is None:
            st.caption(
                "A few more check-ins across varied days will unlock "
                "correlations between your habits and your score."
            )
        else:
            _corr_display = _corr.rename(
                columns=lambda f: BEHAVIORAL_FIELD_LABELS.get(f, f),
                index=lambda f: BEHAVIORAL_FIELD_LABELS.get(f, f),
            )
            fig_corr = px.imshow(
                _corr_display,
                text_auto=True,
                color_continuous_scale="RdBu",
                zmin=-1,
                zmax=1,
                aspect="auto",
                title="How Your Habits Relate to Each Other (Pearson r)",
            )
            st.plotly_chart(fig_corr, use_container_width=True)

            _field_options = list(_corr.columns)
            _scol1, _scol2 = st.columns(2)
            with _scol1:
                _x_field = st.selectbox(
                    "X axis",
                    options=_field_options,
                    format_func=lambda f: BEHAVIORAL_FIELD_LABELS.get(f, f),
                    key="relationship_x_field",
                )
            with _scol2:
                _default_y_index = 1 if len(_field_options) > 1 else 0
                _y_field = st.selectbox(
                    "Y axis",
                    options=_field_options,
                    index=_default_y_index,
                    format_func=lambda f: BEHAVIORAL_FIELD_LABELS.get(f, f),
                    key="relationship_y_field",
                )

            _scatter_df = AnalyticsService.build_relationship_scatter(_all_entries, _x_field, _y_field)
            if _scatter_df is not None and _x_field != _y_field:
                fig_scatter = px.scatter(
                    _scatter_df,
                    x=_x_field,
                    y=_y_field,
                    hover_data=["date"],
                    labels={
                        _x_field: BEHAVIORAL_FIELD_LABELS.get(_x_field, _x_field),
                        _y_field: BEHAVIORAL_FIELD_LABELS.get(_y_field, _y_field),
                    },
                    title=(
                        f"{BEHAVIORAL_FIELD_LABELS.get(_x_field, _x_field)} vs. "
                        f"{BEHAVIORAL_FIELD_LABELS.get(_y_field, _y_field)} "
                        f"(r = {_corr.loc[_x_field, _y_field]:.2f})"
                    ),
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

    with _tab_domino:
        _chain = AnalyticsService.compute_habit_domino_chain(_all_entries)
        if not _chain:
            st.caption(
                "No strong chain of correlations yet - keep checking in "
                "and this will surface which habits tend to move together."
            )
        else:
            _chain_parts = []
            for i, _link in enumerate(_chain):
                _chain_parts.append(f"**{_link['label']}**")
                if _link["correlation_to_next"] is not None:
                    _arrow = "→" if _link["correlation_to_next"] > 0 else "⇥"
                    _chain_parts.append(f" {_arrow} (r = {_link['correlation_to_next']:.2f}) ")
            st.markdown("".join(_chain_parts))
            st.caption(
                "Each link is a real correlation between your own recorded "
                "habits - not a causal claim, but a map of what tends to "
                "move together for you specifically."
            )

    with _tab_golden:
        _golden = AnalyticsService.detect_golden_hour(_all_entries)
        if _golden is None:
            st.caption(
                "Check in at a few more different times of day to unlock "
                "Golden Hour detection."
            )
        else:
            _gcol1, _gcol2 = st.columns(2)
            with _gcol1:
                MetricCard.render(
                    title="✨ Your Golden Hour",
                    value=f"{_golden['golden_hour']:02d}:00",
                    help_text=(
                        f"Avg. score {_golden['golden_hour_avg_score']} across "
                        f"{_golden['golden_hour_count']} check-in(s) at this hour."
                    ),
                )
            with _gcol2:
                MetricCard.render(
                    title="Toughest Check-in Hour",
                    value=f"{_golden['toughest_hour']:02d}:00",
                    help_text=f"Avg. score {_golden['toughest_hour_avg_score']}.",
                )
            fig_golden = px.bar(
                _golden["table"].reset_index(),
                x="hour",
                y="mean",
                labels={"hour": "Hour of Check-in", "mean": "Avg. Wellness Score"},
                title="Average Wellness Score by Check-in Hour",
            )
            st.plotly_chart(fig_golden, use_container_width=True)
            st.caption(
                "Based on when you actually checked in, not a claim about "
                "device usage at that hour."
            )

    with _tab_leverage:
        _leverage = AnalyticsService.detect_leverage_day(_all_entries)
        if _leverage is None:
            st.caption(
                "Record a few more check-ins on the same weekdays to "
                "unlock Leverage Day detection."
            )
        else:
            MetricCard.render(
                title="🎯 Your Leverage Day",
                value=_leverage["day_of_week"],
                help_text=(
                    f"Score swings between {_leverage['range'][0]} and "
                    f"{_leverage['range'][1]} on this day (std dev "
                    f"{_leverage['std_dev']}, n={_leverage['n']})."
                ),
            )
            st.write(
                "This is the day your outcomes are least consistent - not "
                "necessarily your worst average day, but the one with the "
                "most room for a change to make a visible difference."
            )
            if _leverage["likely_lever"]:
                st.caption(f"Most frequent driver logged on this day: {_leverage['likely_lever']}")

    st.divider()

result = get_last_prediction_result()
recommendations = get_last_recommendations()
user_data = get_last_user_data()

if result is None or user_data is None:
    st.info(
        "No prediction found yet for this session. Run a prediction first "
        "so Analytics can show charts and explanations built from your "
        "actual digital habits."
    )
    if st.button("🧠 Go to Prediction", type="primary"):
        st.switch_page("pages/Prediction.py")
    st.stop()

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------
SectionHeader.render("Prediction Summary")

col1, col2, col3 = st.columns(3)
with col1:
    StatusBadge.render(result.prediction)
with col2:
    confidence = f"{result.confidence:.1%}" if result.confidence is not None else "N/A"
    MetricCard.render(title="Confidence", value=confidence)
with col3:
    wellness_score = (
        f"{result.regression_score:.1f} / 100"
        if result.regression_score is not None
        else "N/A"
    )
    MetricCard.render(title="Wellness Score", value=wellness_score)

if result.probabilities:
    ProbabilityChart.render(result.probabilities)

# ---------------------------------------------------------
# Screen Time Breakdown (from the user's actual submitted data)
# ---------------------------------------------------------
SectionHeader.render("Screen Time Breakdown")

category_rows = AnalyticsService.build_category_breakdown(user_data)

if category_rows:
    category_df = pd.DataFrame(category_rows)
    fig_category = px.pie(
        category_df,
        values="Minutes/Day",
        names="Category",
        title="Where Your Screen Time Goes",
    )
    st.plotly_chart(fig_category, use_container_width=True)

    comparison_rows = AnalyticsService.build_screen_time_comparison(user_data)
    if comparison_rows is not None:
        comparison_df = pd.DataFrame(comparison_rows)
        fig_compare = px.bar(
            comparison_df,
            x="Metric",
            y="Minutes/Day",
            color="Metric",
            title="Total Screen Time vs. Your Personal Baseline",
        )
        st.plotly_chart(fig_compare, use_container_width=True)
else:
    st.caption("No screen-time category fields found in the submitted data.")

# ---------------------------------------------------------
# SHAP Explanations (real drivers behind the wellness score)
# ---------------------------------------------------------
SectionHeader.render("What's Driving Your Wellness Score")

shap_features = getattr(result, "shap_features", None)
shap_df = AnalyticsService.build_shap_frame(shap_features)

if shap_df is not None:
    fig_shap = px.bar(
        shap_df,
        x="SHAP Value",
        y="Feature",
        color="Direction",
        orientation="h",
        color_discrete_map={
            "Increases Score": "#388e3c",
            "Decreases Score": "#d32f2f",
        },
        title="Top Factors Behind Your Predicted Wellness Score (SHAP)",
    )
    st.plotly_chart(fig_shap, use_container_width=True)
    st.caption(
        "Values are SHAP contributions from the trained regression model "
        "for this specific prediction - not aggregate/mock statistics."
    )
else:
    st.info("No SHAP explanation is available for this prediction.")

# ---------------------------------------------------------
# Recommendations
# ---------------------------------------------------------
SectionHeader.render("Personalized Recommendations")

if recommendations:
    RecommendationCard.render_many(recommendations)
else:
    st.info("Run a prediction to generate personalized recommendations.")
