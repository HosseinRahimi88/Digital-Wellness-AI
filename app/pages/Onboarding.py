"""
Onboarding Page

Content and flow ported from the Parisa project's `render_onboarding()`
and `config/onboarding_questions.json` (goal, purpose, schedule, sleep
routine, effort level, two consent checkboxes). That project's own
questionnaire notice is preserved here as the operating principle:

    "Onboarding responses provide recommendation context and do not
    replace the 58-feature prediction input."

This page does not touch, call, or modify `services/prediction_service.py`,
`services/shap_service.py`, or `services/recommendation_service.py` -
it only saves a small preference profile (via `AccountService` for
logged-in users, or `st.session_state` for anonymous ones) that later
pages/features can optionally read through
`utils.session.get_onboarding_profile()`.
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="Onboarding",
    page_icon="🧭",
    layout="centered",
)

from components.theme import Theme
Theme.load()

from config.onboarding_options import GOAL_OPTIONS, PURPOSE_OPTIONS, SCHEDULE_OPTIONS
from services.account_service import AccountService
from utils.session import (
    get_current_account,
    get_onboarding_profile,
    save_onboarding_profile,
)

account_service = AccountService()

st.title("🧭 Build Your First Personalized Plan")
st.write(
    "Six short questions and two responsible-use confirmations. "
    "Estimated time: 90 seconds."
)
st.divider()

existing_profile = get_onboarding_profile()
if existing_profile is not None:
    st.success("You've already completed onboarding. You can update your answers below.")

with st.form("onboarding_form"):
    goal_label = st.selectbox("What is your main digital-wellness goal?", list(GOAL_OPTIONS))
    purpose_label = st.selectbox(
        "What is your main reason for using digital devices?", list(PURPOSE_OPTIONS)
    )
    schedule_label = st.selectbox(
        "Which schedule best describes your normal week?", list(SCHEDULE_OPTIONS)
    )

    sleep_column, wake_column = st.columns(2)
    with sleep_column:
        sleep_time = st.text_input("Usual sleep time (HH:MM, 24h)", value="23:00")
    with wake_column:
        wake_time = st.text_input("Usual wake time (HH:MM, 24h)", value="07:00")

    effort = st.radio(
        "How challenging should your first plan be?",
        ["low", "medium", "high"],
        horizontal=True,
    )

    work_screen_required = st.checkbox(
        "Substantial screen use is required for my work or study.",
        key="work_screen_required",
    )

    responsible_consent = st.checkbox(
        "I understand that this is non-medical digital-wellness guidance.",
        key="responsible_consent",
    )
    storage_consent = st.checkbox(
        "I agree to store my profile and preferences to personalize this app.",
        key="storage_consent",
    )

    submitted = st.form_submit_button(
        "Complete onboarding", type="primary", use_container_width=True
    )

if submitted:
    if not responsible_consent or not storage_consent:
        st.error("Both confirmations are required.")
    else:
        profile = {
            "primary_goal": GOAL_OPTIONS[goal_label],
            "main_use_purpose": PURPOSE_OPTIONS[purpose_label],
            "schedule_type": SCHEDULE_OPTIONS[schedule_label],
            "usual_sleep_time": sleep_time,
            "usual_wake_time": wake_time,
            "preferred_effort": effort,
            "work_screen_required": work_screen_required,
        }

        account = get_current_account()
        save_onboarding_profile(profile, account_service=account_service)

        st.success("Onboarding completed.")
        if account is None:
            st.caption(
                "You're not logged in, so these preferences are saved for this "
                "browser session only. [Log in or create an account](./Login) "
                "to keep them permanently."
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Go to Prediction", use_container_width=True, type="primary"):
                st.switch_page("pages/Prediction.py")
        with col2:
            if st.button("🏠 Back to Home", use_container_width=True):
                st.switch_page("Home.py")
