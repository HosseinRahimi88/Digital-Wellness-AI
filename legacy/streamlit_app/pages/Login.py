"""
Login / Register Page

UX ported from the Parisa project's `render_authentication()`
(login + register tabs, inline validation errors). Wired to this
project's own `AccountService` (services/identity/account_service.py) instead
of Project B's FastAPI/JWT flow - see utils/session.py for why.

Every other page keeps working exactly as before for a user who never
visits this page: `get_user_id()` transparently falls back to the
existing anonymous per-session id, so login is opt-in, not a gate.
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="Log In",
    page_icon="🔐",
    layout="centered",
)

from components.theme import Theme
Theme.load()

from services.identity.account_service import (
    AccountService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InactiveAccountError,
)
from utils.session import login, logout, get_current_account

account_service = AccountService()

st.title("🔐 Account")

current_account = get_current_account()

if current_account is not None:
    st.success(f"Logged in as **{current_account.display_name}** ({current_account.email})")
    st.caption(
        "Your prediction history and weekly insights are now tied to this "
        "account instead of an anonymous browser session."
    )
    if st.button("Log out"):
        logout()
        st.rerun()
else:
    login_tab, register_tab = st.tabs(["Log In", "Create Account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)

        if submitted:
            try:
                account = account_service.authenticate(email=email, password=password)
                login(account)
                st.rerun()
            except InvalidCredentialsError:
                st.error("Invalid email or password.")
            except InactiveAccountError:
                st.error("This account is inactive.")

    with register_tab:
        with st.form("register_form"):
            new_display_name = st.text_input("Display name", key="register_name")
            new_email = st.text_input("Email", key="register_email")
            new_password = st.text_input(
                "Password", type="password", key="register_password",
                help="At least 8 characters.",
            )
            new_password_confirm = st.text_input(
                "Confirm password", type="password", key="register_password_confirm",
            )
            register_submitted = st.form_submit_button(
                "Create Account", type="primary", use_container_width=True
            )

        if register_submitted:
            if not new_display_name.strip():
                st.error("Display name is required.")
            elif new_password != new_password_confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    # Password-length policy is enforced by
                    # AccountService.register() itself (raises
                    # ValueError) so it can't be bypassed by a caller
                    # that skips this page's own pre-check.
                    account = account_service.register(
                        email=new_email,
                        password=new_password,
                        display_name=new_display_name,
                    )
                    login(account)
                    st.success("Account created.")
                    st.rerun()
                except EmailAlreadyRegisteredError:
                    st.error("An account with this email already exists.")
                except ValueError as exc:
                    st.error(str(exc))

    st.divider()
    st.caption(
        "You can also use the app without an account - your history will "
        "just be tied to this browser session instead of a saved account."
    )
