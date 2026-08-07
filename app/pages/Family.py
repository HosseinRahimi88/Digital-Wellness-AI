"""
Family Mode Page (Group C Feature 48)

Lets a logged-in account create or join a family group and see a
privacy-conscious comparison of the family's wellness scores. See
services/family_service.py's module docstring for the full privacy
design (only summary-level fields are ever shared, and only for members
who explicitly opted in).
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="Family Mode",
    page_icon="👨‍👩‍👧‍👦",
    layout="centered",
)

from components.theme import Theme
Theme.load()

from services.account_service import AccountService
from services.family_service import (
    FamilyService,
    AlreadyInFamilyError,
    InvalidInviteCodeError,
    NotFamilyOwnerError,
)
from services.history_service import HistoryService
from utils.session import get_current_account

st.title("👨‍👩‍👧‍👦 Family Mode")

account = get_current_account()

if account is None:
    st.info("Log in to use Family Mode.")
    st.stop()

family_service = FamilyService()
account_service = AccountService()

family = family_service.get_family_for_user(account.user_id)

# ------------------------------------------------------------
# No family yet: create or join
# ------------------------------------------------------------
if family is None:
    st.write(
        "Family Mode shares only a summary (wellness score, health class, "
        "and persona) with the family you choose to join - never your raw "
        "habit or survey data."
    )

    tab_create, tab_join = st.tabs(["Create a family", "Join with a code"])

    with tab_create:
        family_name = st.text_input("Family name", value="")
        if st.button("Create family"):
            try:
                new_family = family_service.create_family(
                    account.user_id, account.display_name, family_name,
                )
                st.success(f"Family created. Invite code: **{new_family.invite_code}**")
                st.rerun()
            except AlreadyInFamilyError as exc:
                st.error(str(exc))

    with tab_join:
        invite_code = st.text_input("Invite code")
        share_summary = st.checkbox(
            "Share my wellness summary (score, class, persona) with this family",
            value=True,
        )
        if st.button("Join family"):
            try:
                family_service.join_family(
                    invite_code, account.user_id, account.display_name,
                    share_summary=share_summary,
                )
                st.success("Joined!")
                st.rerun()
            except (InvalidInviteCodeError, AlreadyInFamilyError) as exc:
                st.error(str(exc))

    st.stop()

# ------------------------------------------------------------
# In a family: dashboard + management
# ------------------------------------------------------------
st.subheader(family.name)
st.caption(f"Invite code: **{family.invite_code}**")

dashboard = family_service.family_dashboard(
    family.family_id,
    lambda user_id: HistoryService(user_id=user_id),
)

if dashboard.family_average_score is not None:
    st.metric("Family average wellness score", f"{dashboard.family_average_score:.1f} / 100")

for member in dashboard.members:
    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**{member.display_name}**")
            if not member.sharing:
                st.caption("Not currently sharing their summary.")
            elif member.days_logged == 0:
                st.caption("No check-ins logged yet.")
            else:
                st.write(f"Wellness score: {member.latest_health_score:.1f} / 100 ({member.latest_health_class})")
                if member.latest_persona:
                    st.caption(f"Persona: {member.latest_persona}")
                if member.trend_7d is not None:
                    st.caption(f"7-day trend: {member.trend_7d:+.1f}")
        with col2:
            if member.user_id == account.user_id:
                new_sharing = st.checkbox(
                    "Share my summary", value=member.sharing, key=f"share_{member.user_id}",
                )
                if new_sharing != member.sharing:
                    family_service.set_sharing(account.user_id, new_sharing)
                    st.rerun()
            elif account.user_id == family.owner_user_id:
                if st.button("Remove", key=f"remove_{member.user_id}"):
                    try:
                        family_service.remove_member(family.family_id, account.user_id, member.user_id)
                        st.rerun()
                    except NotFamilyOwnerError as exc:
                        st.error(str(exc))

st.divider()
if st.button("Leave family"):
    family_service.leave_family(account.user_id)
    st.rerun()
