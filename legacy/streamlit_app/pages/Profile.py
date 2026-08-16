"""
Profile Page

UX ported from the Parisa project's `render_profile_page()` (account
summary, editable preference profile, "Trust Center", sign out) - with
two deliberate scope changes from a straight port:

1. "Trust Center" in B re-displayed hardcoded model metrics
   (`"Test MAE", "2.785"` etc., literal strings in that page, not read
   from anywhere). A already has a real Model Performance page
   (app/pages/Model_Performance.py) that reads actual
   artifacts/metrics.json / metrics_regression.json - showing a second,
   duplicate (and in B's case, non-dynamic) copy here would violate
   "don't duplicate functionality, keep the better implementation".
   This page links to that page instead.

2. B's preference form included `recommendation_tone`,
   `reminder_frequency`, and `excluded_recommendation_families`. None
   of those are consumed anywhere in A today (no notification delivery
   system, and RecommendationService doesn't filter by tone/family) -
   shipping them would be settings that silently do nothing, which is
   worse than not having them. Only the fields Onboarding.py already
   established a real purpose for (primary_goal, main_use_purpose,
   schedule_type, sleep/wake routine, effort, work-screen consent) are
   editable here. See "Remaining technical debt" in the final summary
   for what a real implementation of the rest would need.
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="Profile",
    page_icon="👤",
    layout="centered",
)

from components.theme import Theme
Theme.load()

from config.onboarding_options import (
    GOAL_OPTIONS,
    PURPOSE_OPTIONS,
    SCHEDULE_OPTIONS,
    label_for_value,
)
from services.identity.account_service import AccountService
from utils.session import (
    get_current_account,
    get_onboarding_profile,
    logout,
    save_onboarding_profile,
)

account_service = AccountService()

st.title("👤 Profile")

account = get_current_account()

# ------------------------------------------------------------
# Account summary
# ------------------------------------------------------------
if account is not None:
    st.subheader("Account")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Name:**", account.display_name)
        st.write("**Email:**", account.email)
    with col2:
        st.write("**Member since:**", (account.created_at_utc or "")[:10] or "N/A")
        st.write("**Onboarding complete:**", "Yes" if account.onboarding_complete else "No")

    if st.button("Sign out", use_container_width=True):
        logout()
        st.rerun()
else:
    st.info(
        "You're using this app anonymously - your preferences are saved "
        "for this browser session only. [Log in or create an account]"
        "(./Login) to keep them permanently."
    )

st.divider()

# ------------------------------------------------------------
# Preference profile (same fields Onboarding.py collects; editable here)
# ------------------------------------------------------------
st.subheader("Preferences")

existing_profile = get_onboarding_profile() or {}

with st.form("profile_preferences_form"):
    goal_label = st.selectbox(
        "Main digital-wellness goal",
        list(GOAL_OPTIONS),
        index=list(GOAL_OPTIONS).index(
            label_for_value(GOAL_OPTIONS, existing_profile.get("primary_goal"))
        ),
    )
    purpose_label = st.selectbox(
        "Main reason for using digital devices",
        list(PURPOSE_OPTIONS),
        index=list(PURPOSE_OPTIONS).index(
            label_for_value(PURPOSE_OPTIONS, existing_profile.get("main_use_purpose"))
        ),
    )
    schedule_label = st.selectbox(
        "Weekly schedule",
        list(SCHEDULE_OPTIONS),
        index=list(SCHEDULE_OPTIONS).index(
            label_for_value(SCHEDULE_OPTIONS, existing_profile.get("schedule_type"))
        ),
    )

    sleep_column, wake_column = st.columns(2)
    with sleep_column:
        sleep_time = st.text_input(
            "Usual sleep time (HH:MM, 24h)",
            value=existing_profile.get("usual_sleep_time") or "23:00",
        )
    with wake_column:
        wake_time = st.text_input(
            "Usual wake time (HH:MM, 24h)",
            value=existing_profile.get("usual_wake_time") or "07:00",
        )

    effort_options = ["low", "medium", "high"]
    effort = st.radio(
        "Preferred plan effort",
        effort_options,
        index=effort_options.index(existing_profile.get("preferred_effort") or "low"),
        horizontal=True,
    )

    work_screen_required = st.checkbox(
        "Substantial screen use is required for my work or study.",
        value=bool(existing_profile.get("work_screen_required")),
        key="profile_work_screen_required",
    )

    save_preferences = st.form_submit_button(
        "Save preferences", type="primary", use_container_width=True
    )

if save_preferences:
    profile = {
        "primary_goal": GOAL_OPTIONS[goal_label],
        "main_use_purpose": PURPOSE_OPTIONS[purpose_label],
        "schedule_type": SCHEDULE_OPTIONS[schedule_label],
        "usual_sleep_time": sleep_time,
        "usual_wake_time": wake_time,
        "preferred_effort": effort,
        "work_screen_required": work_screen_required,
    }

    save_onboarding_profile(profile, account_service=account_service)

    st.success("Preferences updated.")
    st.rerun()

st.divider()

# ------------------------------------------------------------
# Trust / model info - links to the real page instead of duplicating it
# ------------------------------------------------------------
st.subheader("Trust Center")
st.write(
    "For real, current model accuracy, evaluation metrics, and feature "
    "info, see the Model Performance page - it reads the same "
    "`artifacts/metrics.json` this app's predictions are actually "
    "produced from."
)
if st.button("📈 View Model Performance", use_container_width=True):
    st.switch_page("pages/Model_Performance.py")

st.caption(
    "This application uses statistically synthesized data and provides "
    "non-medical digital-wellness guidance."
)
