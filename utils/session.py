"""
Session Helper
--------------
Real accounts now exist (`services/identity/account_service.py`, ported from
the Parisa project's auth flow). This module is still the *one* place
that decides what identifies a "user" for backend purposes (history
isolation), exactly as originally designed - see `get_user_id()` below,
which now does what its own docstring anticipated: prefer the logged-in
account's id, and only fall back to an anonymous per-session id when
nobody is logged in. No caller of `get_user_id()` (HistoryService,
Prediction.py, Weekly_Insights.py, ...) had to change.

`login()` / `logout()` / `get_current_account()` are the new surface
pages use to drive the auth UI (see `legacy/streamlit_app/pages/Login.py`).

This intentionally does NOT touch any rendered UI - it's plumbing, not
a widget.
"""

from __future__ import annotations

import uuid
from typing import Optional

import streamlit as st

from services.identity.account_service import Account, AccountService

_ANON_SESSION_KEY = "_digital_wellness_user_id"
_ACCOUNT_SESSION_KEY = "_digital_wellness_account"


def get_user_id() -> str:
    """
    Return a stable id for the current user: the logged-in account's
    `user_id` if one is logged in, otherwise an anonymous per-session id
    (created once and cached in `st.session_state`, so every page a
    given browser tab visits during that session shares the same id).
    """
    account = get_current_account()
    if account is not None:
        return account.user_id

    if _ANON_SESSION_KEY not in st.session_state:
        st.session_state[_ANON_SESSION_KEY] = uuid.uuid4().hex
    return st.session_state[_ANON_SESSION_KEY]


def login(account: Account) -> None:
    """Mark `account` as the logged-in user for this session."""
    st.session_state[_ACCOUNT_SESSION_KEY] = account


def logout() -> None:
    """Clear the logged-in user for this session (falls back to anonymous)."""
    st.session_state.pop(_ACCOUNT_SESSION_KEY, None)


def get_current_account() -> Optional[Account]:
    """Return the logged-in `Account`, or None if nobody is logged in."""
    return st.session_state.get(_ACCOUNT_SESSION_KEY)


def is_authenticated() -> bool:
    return get_current_account() is not None


# ------------------------------------------------------------
# Onboarding profile (goal/purpose/schedule/effort context - see
# services/identity/account_service.py::Account for what these fields mean and
# why they're kept separate from the ML feature set).
# ------------------------------------------------------------

_ANON_PROFILE_SESSION_KEY = "_digital_wellness_anon_onboarding_profile"


def set_anonymous_onboarding_profile(profile: dict) -> None:
    """
    Store the onboarding profile in-session for a user who isn't
    logged in. Lost when the browser session ends - logged-in users get
    a persistent version via AccountService.save_onboarding_profile()
    instead (see legacy/streamlit_app/pages/Onboarding.py, which decides which of the
    two to call).
    """
    st.session_state[_ANON_PROFILE_SESSION_KEY] = profile


def get_onboarding_profile() -> Optional[dict]:
    """
    Return the current user's onboarding profile as a dict, preferring
    the persisted profile on a logged-in account, falling back to the
    in-session anonymous profile, or None if onboarding was never
    completed either way.
    """
    account = get_current_account()
    if account is not None and account.onboarding_complete:
        return {
            "primary_goal": account.primary_goal,
            "main_use_purpose": account.main_use_purpose,
            "schedule_type": account.schedule_type,
            "usual_sleep_time": account.usual_sleep_time,
            "usual_wake_time": account.usual_wake_time,
            "preferred_effort": account.preferred_effort,
            "work_screen_required": account.work_screen_required,
        }
    return st.session_state.get(_ANON_PROFILE_SESSION_KEY)


def save_onboarding_profile(
    profile: dict, account_service: Optional[AccountService] = None
) -> None:
    """
    Persist `profile` for whichever user is active this session:
    AccountService.save_onboarding_profile() for a logged-in account,
    or the in-session anonymous store otherwise.

    This is the one dispatch rule Onboarding.py and Profile.py each
    used to duplicate inline (`if account is not None: ... else: ...`)
    after building the same 7-key profile dict - moved here so both
    pages call one function instead of re-deciding the same rule.
    `account_service` is injectable for tests; pages can omit it.
    """
    account = get_current_account()
    if account is not None:
        service = account_service or AccountService()
        service.save_onboarding_profile(account.user_id, **profile)
    else:
        set_anonymous_onboarding_profile(profile)


# ------------------------------------------------------------
# Last-prediction session store - the shared "hand-off" state
# Prediction.py writes and Dashboard.py / Analytics.py / AI_Coach.py /
# Weekly_Insights.py / What_If_Simulator.py read. Previously each page
# read/wrote the raw `st.session_state["last_prediction_result"]` (and
# friends) directly with its own copy of the key string - moved here
# so there's one place that owns the key names and the read/write
# contract between pages. No page calls another page directly; this
# is the "service" they actually communicate through for this session
# hand-off (a real backing service isn't warranted for state that is
# intentionally session-only and never persisted).
# ------------------------------------------------------------

_LAST_PREDICTION_RESULT_KEY = "last_prediction_result"
_LAST_RECOMMENDATIONS_KEY = "last_recommendations"
_LAST_USER_DATA_KEY = "last_user_data"
_LAST_PERSONA_KEY = "last_persona"


def set_last_prediction(result, recommendations, user_data: dict) -> None:
    """Record this session's most recent real prediction + its inputs."""
    st.session_state[_LAST_PREDICTION_RESULT_KEY] = result
    st.session_state[_LAST_RECOMMENDATIONS_KEY] = recommendations
    st.session_state[_LAST_USER_DATA_KEY] = user_data


def get_last_prediction_result():
    """The most recent real PredictionResult this session, or None."""
    return st.session_state.get(_LAST_PREDICTION_RESULT_KEY)


def get_last_recommendations():
    """The most recent real recommendation list this session, or None."""
    return st.session_state.get(_LAST_RECOMMENDATIONS_KEY)


def get_last_user_data() -> Optional[dict]:
    """The validated user_data behind the most recent real prediction, or None."""
    return st.session_state.get(_LAST_USER_DATA_KEY)


def set_last_persona(persona: Optional[str]) -> None:
    st.session_state[_LAST_PERSONA_KEY] = persona


def get_last_persona() -> Optional[str]:
    return st.session_state.get(_LAST_PERSONA_KEY)
