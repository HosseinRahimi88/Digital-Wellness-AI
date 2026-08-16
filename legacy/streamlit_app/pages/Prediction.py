"""
Prediction Page

Adds a "Quick Demo" tab alongside the original guided form - UX ported
from the Parisa project's `render_data_input()` "Verified demo" tab
(pick a pre-built profile, get a real prediction in one click). The
demo profile *data* is A's own (config/demo_profiles.py, built from
the real FEATURE_SCHEMA) since B's demo profiles belonged to its
discarded 58-feature model and don't apply here - see that module's
docstring. Everything downstream of "here is a user_data dict" (validate
-> predict -> render -> recommend -> log history -> PDF) is the exact
same, unmodified code path for both tabs; it was extracted into
`_run_prediction_and_render()` below purely to avoid duplicating it,
with no behavior change.
"""
import logging

import streamlit as st
import bootstrap

# Page Config MUST be called first
st.set_page_config(
    page_title="Prediction",
    page_icon="🧠",
    layout="wide"
)

from components.theme import Theme
Theme.load()

from config.demo_profiles import DEMO_PROFILES
from utils.form_generator import FormGenerator
from utils.persona import resolve_persona
from utils.session import get_user_id, set_last_persona, set_last_prediction
from services.ml.validation_service import ValidationService
from services.ml.prediction_service import PredictionService
from services.wellness.recommendation_service import RecommendationService
from services.identity.report_service import ReportService
from services.identity.history_service import HistoryService
from services.wellness.commitment_service import CommitmentService
from services.wellness.recommendation_effectiveness_service import RecommendationEffectivenessService

from components.recommendation_card import RecommendationCard
from components.metric_card import MetricCard
from components.uncertainty_card import UncertaintyCard
from components.persona_card import PersonaCard
from components.status_badge import StatusBadge
from components.probability_chart import ProbabilityChart
from components.achievement_celebration import AchievementCelebration


st.title("🧠 Digital Wellness Prediction")
st.write("Fill in the information below to evaluate your digital wellness.")
st.divider()


# Services (cached so model artifacts are loaded from disk once per
# session instead of on every Streamlit rerun/widget interaction)
@st.cache_resource(show_spinner="Loading models...")
def _load_services():
    return (
        ValidationService(),
        PredictionService(),
        RecommendationService(),
    )


try:
    validator, predictor, recommendation_service = _load_services()
except Exception as e:
    st.error(
        "Could not load the trained model artifacts. Make sure the "
        "classification/regression models have been trained and saved "
        f"under `artifacts/` before running the app.\n\n"
        f"Details: {e}"
    )
    st.stop()


def _run_prediction_and_render(user_data: dict) -> None:
    """Validate `user_data`, run the real prediction pipeline, and
    render results/recommendations/report/history - unchanged from the
    original single-form flow, just callable from more than one input
    source now."""
    validation = validator.validate(user_data)

    if not validation.is_valid:
        st.warning("Please correct the highlighted fields.")
        for _, error in validation.errors.items():
            st.error(error)
        st.stop()

    try:
        with st.spinner("Analyzing your digital habits..."):
            result = predictor.predict(validation.cleaned_data)

        st.divider()
        st.header("Prediction Result")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            MetricCard.render(title="Predicted Result", value=str(result.prediction))

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

        with col4:
            MetricCard.render(title="Model", value=result.model_name)

        with col5:
            MetricCard.render(title="Inference Time", value=f"{result.prediction_time_ms:.2f} ms")

        st.write("")
        StatusBadge.render(result.prediction)

        st.write("")
        if result.probabilities:
            ProbabilityChart.render(result.probabilities)

        st.write("")
        UncertaintyCard.render(result.uncertainty)

        # Recommendations - biased by this user's own real,
        # measured track record of which categories have actually
        # helped before (feature 56, the Recommendation Learning
        # Loop). Failure to compute a track record (e.g. brand-new
        # user with no commitments yet) must never block showing
        # recommendations, so this is best-effort.
        try:
            _commitments = CommitmentService(user_id=get_user_id()).get_all()
            _track_record = RecommendationEffectivenessService.compute_category_track_record(
                _commitments, HistoryService(user_id=get_user_id()).get_all()
            )
        except Exception:
            logging.getLogger(__name__).exception("Could not compute recommendation track record.")
            _track_record = {}

        recommendations = recommendation_service.generate(
            result.shap_features, category_track_record=_track_record
        )

        # Persist for the AI Coach page, which reads the *real* last
        # prediction instead of showing static/mock advice.
        set_last_prediction(result, recommendations, validation.cleaned_data)

        # Log this *real* prediction into the local weekly history used by
        # the Weekly Insights page (heatmap, story card, week comparison,
        # share report). This is presentation-layer logging only - it
        # reads PredictionService's output, it does not feed anything
        # back into the model.
        persona, persona_result = resolve_persona(
            prediction=result.prediction,
            user_data=validation.cleaned_data,
            regression_score=result.regression_score,
            persona_service=predictor.persona_service,
        )
        set_last_persona(persona)
        PersonaCard.render(persona_result, fallback_label=persona)
        try:
            history_service = HistoryService(user_id=get_user_id())
            recorded_entry = history_service.record(
                user_data=validation.cleaned_data,
                prediction_result=result,
                persona=persona,
            )
            # Small Achievement Celebration: compare this real recorded
            # score against the most recent *prior* recorded entry (if
            # any). Purely a UI touch on top of real history data - it
            # never influences the prediction itself.
            previous_entry = history_service.get_previous_entry(
                before_date=recorded_entry.get("date")
            )
            if previous_entry is not None:
                AchievementCelebration.render_from_scores(
                    current_score=recorded_entry.get("health_score"),
                    previous_score=previous_entry.get("health_score"),
                    context_label="since your last check-in",
                )
        except Exception:
            # Never let history logging break the core prediction flow.
            logging.getLogger(__name__).exception("Failed to record prediction history.")

        st.divider()
        st.header("💡 Personalized Recommendations")
        RecommendationCard.render_many(recommendations)

        # Report PDF Download
        report_service = ReportService()
        pdf = report_service.generate(
            user_data=validation.cleaned_data,
            prediction_result=result,
            recommendations=recommendations,
        )

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf,
            file_name="digital_wellness_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.divider()
        nav_col1, nav_col2 = st.columns(2)
        with nav_col1:
            if st.button("📅 View Weekly Insights", use_container_width=True):
                st.switch_page("pages/Weekly_Insights.py")
        with nav_col2:
            if st.button("🧪 Try the What-if Simulator", use_container_width=True):
                st.switch_page("pages/What_If_Simulator.py")
    except Exception as e:
        st.error(f"Prediction failed: {e}")


form_tab, demo_tab = st.tabs(["📋 Guided Form", "⚡ Quick Demo"])

with form_tab:
    with st.form("prediction_form"):
        user_data = FormGenerator.render()
        submitted = st.form_submit_button("🚀 Predict", type="primary")

    if submitted:
        _run_prediction_and_render(user_data)

with demo_tab:
    st.caption(
        "Skip the form and see a real prediction instantly, using one of "
        "four example profiles built from the model's own feature schema."
    )

    demo_label = st.selectbox("Choose an example profile", list(DEMO_PROFILES))
    demo_run = st.button(
        "Run this demo profile", type="primary", use_container_width=True, key="run_demo_profile"
    )

    if demo_run:
        demo_user_data = DEMO_PROFILES[demo_label]()
        _run_prediction_and_render(demo_user_data)