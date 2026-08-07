"""
Dashboard Page

Layout ported from the Parisa project's `render_dashboard_page()`
(hero score readout, metric grid, strengths/areas-to-improve tabs,
recommendations, call-to-action) - but built entirely from A's own
existing services (HistoryService, AchievementService,
RecommendationService's session output), not a new backend.

One deliberate wording change from B, not just a reskin: B's model is
a genuine 7-day-ahead forecaster ("predicted_future_health_score_7d"),
so its dashboard correctly says "forecast". A's classifier/regressor
score the digital-habit data you just entered - they do not predict
7 days into the future. This page says "latest check-in" / "vs your
previous check-in", never "forecast", so it doesn't claim capability
the model doesn't have. See services/prediction_service.py (unmodified)
for what the model actually outputs.

"Strengths" / "Areas to improve" are built from the *current session's*
SHAP explanation (utils.session.get_last_prediction_result(), set by
Prediction.py) using its `direction` field - SHAP was computed against
the regressor (services/prediction_service.py calls
`self._generate_shap(X_reg)`), so direction="increase" means the
feature is pushing the wellness score UP (a strength) and
direction="decrease" means it's pulling it down (an area to improve).
This is a real property of the existing SHAP output, not a new metric.
Older history entries only ever stored the single top SHAP feature
(see services/history_service.py's `top_shap_feature`), not the full
ranked list, so this section is scoped to "since your last check-in
this session" rather than pretending to reconstruct it from history.
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide",
)

from components.theme import Theme
Theme.load()

from services.history_service import HistoryService
from services.achievement_service import AchievementService
from services.dashboard_service import DashboardService
from services.risk_alert_service import RiskAlertService
from utils.session import get_last_prediction_result, get_last_recommendations, get_user_id

from components.metric_card import MetricCard
from components.status_badge import StatusBadge
from components.weekly_heatmap import WeeklyHeatmap
from components.recommendation_card import RecommendationCard
from components.score_battery import ScoreBattery
from components.streak_tracker import StreakTracker
from components.level_progress import LevelProgress

st.title("📊 Dashboard")

history_service = HistoryService(user_id=get_user_id())
all_entries = history_service.get_all()

if not all_entries:
    st.info(
        "Your dashboard starts with one check-in. Run a prediction "
        "(a real one, or a Quick Demo profile) to see your first "
        "summary here."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Run a Check-in", use_container_width=True, type="primary"):
            st.switch_page("pages/Prediction.py")
    with col2:
        if st.button("🧭 Personalize First", use_container_width=True):
            st.switch_page("pages/Onboarding.py")
    st.stop()

latest_entry = all_entries[-1]
previous_entry = history_service.get_previous_entry(before_date=latest_entry.get("date"))

st.write(
    f"Your latest check-in: **{latest_entry.get('date', 'unknown date')}**"
    + (f" ({latest_entry.get('persona')})" if latest_entry.get("persona") else "")
)

# ------------------------------------------------------------
# Critical Risk Alerts (06) - rule-based, built entirely from real
# history (classification streaks, score-decline trends, and
# personal-baseline deviations - see RiskAlertService). Placed above
# the hero score since a critical alert is the most important thing
# on this page when one is active.
# ------------------------------------------------------------
_risk_alerts = RiskAlertService.evaluate(all_entries)
if _risk_alerts:
    for _alert in _risk_alerts:
        _alert_text = f"**{_alert.title}** — {_alert.message}"
        if _alert.action:
            _alert_text += f"\n\n{_alert.action}"
        if _alert.severity == "critical":
            st.error(_alert_text, icon="🚨")
        elif _alert.severity == "warning":
            st.warning(_alert_text, icon="⚠️")
        else:
            st.info(_alert_text, icon="ℹ️")
else:
    st.success("No active risk signals — your recent check-ins look steady.", icon="✅")

st.divider()

# ------------------------------------------------------------
# Hero score + metric grid
# ------------------------------------------------------------
score_col, metric_col = st.columns([1, 2])

with score_col:
    health_score = latest_entry.get("health_score")
    st.metric(
        label="Latest Wellness Score",
        value=f"{health_score:.1f}" if health_score is not None else "N/A",
    )
    if health_score is not None:
        st.progress(min(max(health_score / 100.0, 0.0), 1.0))
    StatusBadge.render(latest_entry.get("health_class", "Unknown"))
    ScoreBattery.render(health_score, title="")

with metric_col:
    achievement = AchievementService.evaluate(
        current_score=latest_entry.get("health_score"),
        previous_score=(previous_entry or {}).get("health_score"),
        context_label="since your previous check-in",
    )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        MetricCard.render(
            title="Previous Score",
            value=(
                f"{previous_entry['health_score']:.1f}"
                if previous_entry and previous_entry.get("health_score") is not None
                else "N/A"
            ),
        )
    with m2:
        MetricCard.render(
            title="Change",
            value=(
                f"{achievement.delta_points:+.1f}"
                if achievement.delta_points is not None
                else "N/A"
            ),
        )
    with m3:
        confidence = latest_entry.get("confidence")
        MetricCard.render(
            title="Confidence",
            value=f"{confidence:.1%}" if confidence is not None else "N/A",
        )
    with m4:
        MetricCard.render(title="Check-ins Logged", value=str(len(all_entries)))

    if achievement.unlocked:
        st.success(achievement.message)

st.divider()

# ------------------------------------------------------------
# Weekly heatmap - reuses the same component/data Weekly_Insights.py uses
# ------------------------------------------------------------
last_days = history_service.get_last_n_days(n=7)
WeeklyHeatmap.render(last_days, title="📅 Last 7 Days")

st.divider()

# ------------------------------------------------------------
# Compact streak / level row - full detail lives on the Journey page
# ------------------------------------------------------------
streak_col, level_col = st.columns(2)
with streak_col:
    StreakTracker.render(all_entries, compact=True)
with level_col:
    LevelProgress.render(all_entries, title="🎮 Level")

st.divider()

# ------------------------------------------------------------
# Strengths / Areas to improve - from this session's real SHAP output
# ------------------------------------------------------------
st.header("🔍 What's Driving Your Score")

last_result = get_last_prediction_result()

if last_result is not None and getattr(last_result, "shap_features", None):
    highlights = DashboardService.split_shap_by_direction(last_result.shap_features)
    strengths = highlights.strengths
    areas = highlights.areas_to_improve

    strength_tab, areas_tab = st.tabs(["✅ Strengths to maintain", "⚠️ Areas to improve"])

    with strength_tab:
        if strengths:
            for feature in strengths[:5]:
                st.markdown(f"- **{feature.feature}** — pushing your score up")
        else:
            st.info("No strong positive signal in your latest check-in.")

    with areas_tab:
        if areas:
            for feature in areas[:5]:
                st.markdown(f"- **{feature.feature}** — pulling your score down")
        else:
            st.info("No strong negative signal in your latest check-in.")
else:
    st.info(
        "Run a prediction this session to see which specific factors are "
        "driving your score."
    )

st.divider()

# ------------------------------------------------------------
# Recommendations - reuses the same session output AI_Coach.py reads
# ------------------------------------------------------------
last_recommendations = get_last_recommendations()
if last_recommendations:
    st.header("💡 Recommendations")
    RecommendationCard.render_many(last_recommendations)

st.divider()

# ------------------------------------------------------------
# Call to action
# ------------------------------------------------------------
cta1, cta2, cta3, cta4 = st.columns(4)
with cta1:
    if st.button("🚀 New Check-in", use_container_width=True, type="primary"):
        st.switch_page("pages/Prediction.py")
with cta2:
    if st.button("📅 Weekly Insights", use_container_width=True):
        st.switch_page("pages/Weekly_Insights.py")
with cta3:
    if st.button("🤖 AI Coach", use_container_width=True):
        st.switch_page("pages/AI_Coach.py")
with cta4:
    if st.button("🧭 Your Journey", use_container_width=True):
        st.switch_page("pages/Journey.py")
