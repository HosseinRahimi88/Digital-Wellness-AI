"""
Weekly Insights Page

Brings together the GitHub-style weekly heatmap, the weekly story card,
the first-week-vs-current-week comparison, and the shareable report
card - all built from real HistoryService entries (themselves built
from real PredictionService/SHAPService outputs logged by the
Prediction page). No mock data.
"""
import logging

import streamlit as st
import bootstrap

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Weekly Insights",
    page_icon="📅",
    layout="wide"
)

from components.theme import Theme
Theme.load()

from services.identity.history_service import HistoryService
from services.wellness.improvement_plan_service import ImprovementPlanService
from services.wellness.plan_progress_service import PlanProgressService
from utils.persona import resolve_persona
from utils.session import (
    get_last_persona,
    get_last_prediction_result,
    get_last_user_data,
    get_user_id,
)
from components.weekly_heatmap import WeeklyHeatmap
from components.story_card import StoryCard
from components.week_comparison_card import WeekComparisonCard
from components.share_report_card import ShareReportCard
from components.achievement_celebration import AchievementCelebration
from components.improvement_plan_card import ImprovementPlanCard
from components.sparkline import Sparkline
from components.reflection_card import ReflectionCard

st.title("📅 Weekly Insights")
st.write(
    "A weekly view of your real digital wellness history - built from "
    "every prediction you've actually run."
)
st.divider()

history_service = HistoryService(user_id=get_user_id())
all_entries = history_service.get_all()

if not all_entries:
    st.info(
        "No prediction history yet. Run a prediction to start building "
        "your weekly insights."
    )
    if st.button("🧠 Go to Prediction", type="primary"):
        st.switch_page("pages/Prediction.py")
    st.stop()

latest_entry = all_entries[-1]

# ---------------------------------------------------------
# GitHub-style Weekly Heatmap
# ---------------------------------------------------------
last_days = history_service.get_last_n_days(n=7)
WeeklyHeatmap.render(last_days)

st.divider()

# ---------------------------------------------------------
# Sparkline Trend (last 30 logged days)
# ---------------------------------------------------------
_trend_entries = history_service.get_all()[-30:]
Sparkline.render(_trend_entries, field_name="health_score", title="📈 Score Sparkline (last 30 check-ins)")

st.divider()

# ---------------------------------------------------------
# Weekly Story Card
# ---------------------------------------------------------
StoryCard.render(history_service)

st.divider()

# ---------------------------------------------------------
# Week Comparison Card
# ---------------------------------------------------------
WeekComparisonCard.render(history_service)

# ---------------------------------------------------------
# Small Achievement Celebration (current week vs. previous week,
# both built from real recorded wellness scores)
# ---------------------------------------------------------
_current_week_summary = history_service.summarize(history_service.current_week_entries())
_previous_week_summary = history_service.summarize(history_service.previous_week_entries())

if _current_week_summary and _previous_week_summary:
    AchievementCelebration.render_from_scores(
        current_score=_current_week_summary.avg_health_score,
        previous_score=_previous_week_summary.avg_health_score,
        context_label="this week",
    )

st.divider()

# ---------------------------------------------------------
# Weekly Plan (persistent across sessions - see
# services/wellness/plan_progress_service.py). Prefers this session's real
# prediction (freshest); falls back to the most recent HistoryService
# entry so the plan is still available on a later visit with no new
# prediction this session, unlike AI_Coach.py's session-only plan.
# ---------------------------------------------------------
st.header("🗓️ Weekly Plan")

_session_result = get_last_prediction_result()
_session_user_data = get_last_user_data()
_session_persona = get_last_persona()

if _session_result is not None:
    _plan_health_class = _session_result.prediction
    _plan_wellness_score = _session_result.regression_score
    _plan_persona = _session_persona
    _plan_user_data = _session_user_data or {}
else:
    _plan_health_class = latest_entry.get("health_class")
    _plan_wellness_score = latest_entry.get("health_score")
    _plan_persona = latest_entry.get("persona")
    _plan_user_data = latest_entry

_weekly_plan = ImprovementPlanService().generate(
    health_class=_plan_health_class,
    wellness_score=_plan_wellness_score,
    persona=_plan_persona,
    user_data=_plan_user_data,
)
_progress_service = PlanProgressService(user_id=get_user_id())
ImprovementPlanCard.render_persistent(_weekly_plan, _progress_service)

st.divider()

# ---------------------------------------------------------
# Reflection Loop (Group C Feature 42) - subjective self-rating vs.
# objective measured wellness score, calibration analysis, and a
# data-grounded prompt for what to reflect on next.
# ---------------------------------------------------------
ReflectionCard.render(get_user_id(), history_service.get_all())

st.divider()

# ---------------------------------------------------------
# Share Report Card
# ---------------------------------------------------------
result = get_last_prediction_result()
user_data = get_last_user_data()
persona = get_last_persona()

if result is not None:
    if not persona:
        try:
            from services.ml.prediction_service import PredictionService
            _persona_service = PredictionService().persona_service
        except Exception:
            logger.debug("Could not load PersonaService for a fresh persona lookup; falling back to rule-based persona.", exc_info=True)
            _persona_service = None
        persona, _ = resolve_persona(
            prediction=result.prediction,
            user_data=user_data or {},
            regression_score=result.regression_score,
            persona_service=_persona_service,
        )
    ShareReportCard.render(result, persona)
else:
    st.subheader("📤 Share Your Report")
    st.info(
        "Run a prediction this session to generate a shareable report card."
    )
    if st.button("🧠 Go to Prediction", type="primary", key="share_goto_prediction"):
        st.switch_page("pages/Prediction.py")
