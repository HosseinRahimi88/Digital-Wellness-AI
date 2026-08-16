"""
AI Coach

Shows personalized coaching advice generated from the user's most
recent real prediction (RecommendationService, driven by SHAP feature
importances) instead of static/mock content.
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="AI Coach",
    page_icon="🤖",
    layout="wide"
)

from components.theme import Theme
from components.recommendation_card import RecommendationCard
from components.status_badge import StatusBadge
from components.improvement_plan_card import ImprovementPlanCard
from services.wellness.improvement_plan_service import ImprovementPlanService
from utils.session import get_last_persona, get_last_prediction_result, get_last_recommendations, get_last_user_data

Theme.load()

st.title("🤖 AI Coach")

result = get_last_prediction_result()
recommendations = get_last_recommendations()

if result is None or recommendations is None:
    st.info(
        "No prediction found yet for this session. Run a prediction first "
        "so the AI Coach can generate advice tailored to your actual "
        "digital habits."
    )
    if st.button("🧠 Go to Prediction", type="primary"):
        st.switch_page("pages/Prediction.py")
    st.stop()

st.write(
    "Personalized recommendations based on your most recent prediction."
)

col1, col2 = st.columns(2)
with col1:
    StatusBadge.render(result.prediction)
with col2:
    if result.regression_score is not None:
        st.metric("Wellness Score", f"{result.regression_score:.1f} / 100")

st.divider()

RecommendationCard.render_many(recommendations)

st.caption(
    "Recommendations are generated from the SHAP-ranked drivers of your "
    "predicted wellness score. Run a new prediction any time your habits "
    "change to refresh this advice."
)

st.divider()

# ---------------------------------------------------------
# 7-Day Personalized Improvement Plan
# ---------------------------------------------------------
user_data = get_last_user_data() or {}
persona = get_last_persona()


@st.cache_resource
def _get_plan_service() -> ImprovementPlanService:
    return ImprovementPlanService()


plan = _get_plan_service().generate(
    health_class=result.prediction,
    wellness_score=result.regression_score,
    persona=persona,
    user_data=user_data,
)
ImprovementPlanCard.render(plan)
