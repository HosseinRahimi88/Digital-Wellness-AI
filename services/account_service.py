"""
services/account_service.py
----------------------------
Local multi-user accounts (register / authenticate / lookup).

Why this exists
----------------
Ported from the Parisa project's `app/services/auth.py` +
`app/db/models.py::User`, which used SQLAlchemy + SQLite. That is
reasonable for a stateless FastAPI HTTP layer, but this app already has
a purpose-built, concurrency-safe record store
(`services/storage/base.py::StorageBackend`, currently backed by
`JSONFileStorageBackend`) used for prediction history. Introducing a
second persistence stack (a DB engine, session lifecycle, migrations)
for what is a handful of small account records is unnecessary
complexity - reusing the existing backend is the cleaner, more
maintainable choice per this project's own storage abstraction design
(see `services/storage/base.py` docstring: "swapping to Postgres later
means writing one new class ... No business logic has to change").
If accounts ever need real relational queries, swap the backend passed
into `AccountService`, not this service's API.

Security properties kept from Project B (do not weaken these):
  * Passwords are hashed with Argon2 (`utils.security`), never stored
    or logged in plaintext.
  * `authenticate_user` runs a dummy `verify_password` call even when
    the email is unknown, so failing on "no such user" takes the same
    time as failing on "wrong password" (timing side-channel
    protection against user enumeration).
  * Email is normalized (`strip().lower()`) before every lookup/write
    so uniqueness checks can't be bypassed by case/whitespace.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.account_settings import MIN_PASSWORD_LENGTH
from services.storage.base import StorageBackend
from services.storage.json_file_storage import JSONFileStorageBackend
from utils.security import hash_password, verify_password

DEFAULT_ACCOUNTS_PATH = Path(__file__).resolve().parent.parent / "storage" / "accounts.json"

# Verified once at import time so `authenticate_user` always has a real
# Argon2 hash to run the dummy-verify against, even before any account
# has ever been created.
_DUMMY_PASSWORD_HASH = hash_password("TimingProtection123!")


class EmailAlreadyRegisteredError(ValueError):
    """Raised when an email is already registered."""


class InvalidCredentialsError(ValueError):
    """Raised when login credentials are invalid."""


class InactiveAccountError(ValueError):
    """Raised when a disabled account attempts login."""


@dataclass(slots=True)
class Account:
    """A local user account. `password_hash` is an Argon2 hash, never plaintext."""
    user_id: str
    email: str
    password_hash: str
    display_name: str
    is_active: bool = True
    onboarding_complete: bool = False
    created_at_utc: str = ""
    updated_at_utc: str = ""

    # Onboarding preference profile (ported field set from the Parisa
    # project's config/onboarding_questions.json / schemas/profile.py).
    # These are recommendation/planning CONTEXT only - never fed into
    # the trained classifier/regressor. See onboarding_questions.json's
    # own "model_input_notice": "Onboarding responses provide
    # recommendation context and do not replace the 58-feature
    # prediction input." services/prediction_service.py and
    # services/recommendation_service.py are unmodified and unaware
    # this profile exists.
    primary_goal: Optional[str] = None
    main_use_purpose: Optional[str] = None
    schedule_type: Optional[str] = None
    usual_sleep_time: Optional[str] = None  # "HH:MM"
    usual_wake_time: Optional[str] = None  # "HH:MM"
    preferred_effort: Optional[str] = None  # low | medium | high
    work_screen_required: bool = False

    # --- Presentation-only profile extras -------------------------------
    # Like the onboarding block above, none of these are ever fed to the
    # trained models. `avatar_data_url` holds a small, already-resized
    # data: URL produced client-side (see frontend/assets/js/profile.js) -
    # no binary upload path, no file storage, and a hard size cap enforced
    # in AccountService.save_profile_extras() so the accounts JSON can't
    # be inflated by a large image.
    avatar_data_url: Optional[str] = None
    # Tone the recommendation/coach copy is phrased in (P1 item 20).
    # Consumed by services/tone_service.py; the recommendation CONTENT
    # (which items, what priority) is unchanged by it.
    recommendation_tone: Optional[str] = None  # gentle | direct | clinical


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_ACCOUNT_FIELD_NAMES = {f.name for f in fields(Account)}


def _account_from_record(record: dict) -> Account:
    """
    Build an Account from a stored record, ignoring any keys that
    aren't (or are no longer) real Account fields. Bug hardening: a
    blind `Account(**record)` raises TypeError the moment a stored
    record has one stray/legacy key the current dataclass doesn't
    define (e.g. after a manual edit, a partial migration, or a future
    field rename) - dropping unknown keys degrades gracefully instead
    of crashing every lookup for every user.
    """
    known = {k: v for k, v in record.items() if k in _ACCOUNT_FIELD_NAMES}
    return Account(**known)


class AccountService:
    """Register, authenticate, and look up local user accounts."""

    def __init__(self, backend: Optional[StorageBackend] = None) -> None:
        self._backend = backend or JSONFileStorageBackend(DEFAULT_ACCOUNTS_PATH)

    # ------------------------------------------------------------
    # Lookups (read-only, no lock needed)
    # ------------------------------------------------------------

    def get_by_email(self, email: str) -> Optional[Account]:
        normalized = email.strip().lower()
        for record in self._backend.read_all():
            if record.get("email") == normalized:
                return _account_from_record(record)
        return None

    def get_by_id(self, user_id: str) -> Optional[Account]:
        for record in self._backend.read_all():
            if record.get("user_id") == user_id:
                return _account_from_record(record)
        return None

    # ------------------------------------------------------------
    # Mutations (must go through transaction() for the read-modify-write)
    # ------------------------------------------------------------

    def register(self, *, email: str, password: str, display_name: str) -> Account:
        """
        Create a new account. Raises EmailAlreadyRegisteredError on
        duplicate email, or ValueError if `password` is shorter than
        MIN_PASSWORD_LENGTH (this used to be checked only in
        app/pages/Login.py before calling register(); centralizing it
        here means every caller - including a future non-Streamlit one -
        gets the same policy without re-implementing it).
        """
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )

        normalized_email = email.strip().lower()

        with self._backend.transaction() as records:
            if any(r.get("email") == normalized_email for r in records):
                raise EmailAlreadyRegisteredError(
                    "An account with this email already exists."
                )

            account = Account(
                user_id=uuid.uuid4().hex,
                email=normalized_email,
                password_hash=hash_password(password),
                display_name=display_name.strip() or normalized_email.split("@")[0],
                is_active=True,
                onboarding_complete=False,
                created_at_utc=_now_iso(),
                updated_at_utc=_now_iso(),
            )
            records.append(asdict(account))
            self._backend.commit(records)

        return account

    def authenticate(self, *, email: str, password: str) -> Account:
        """Validate credentials and return the active account, or raise."""
        normalized_email = email.strip().lower()
        account = self.get_by_email(normalized_email)

        if account is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)  # timing protection
            raise InvalidCredentialsError("Invalid email or password.")

        if not verify_password(password, account.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        if not account.is_active:
            raise InactiveAccountError("This account is inactive.")

        return account

    def mark_onboarding_complete(self, user_id: str) -> None:
        with self._backend.transaction() as records:
            for record in records:
                if record.get("user_id") == user_id:
                    record["onboarding_complete"] = True
                    record["updated_at_utc"] = _now_iso()
                    break
            self._backend.commit(records)

    def save_onboarding_profile(
        self,
        user_id: str,
        *,
        primary_goal: str,
        main_use_purpose: str,
        schedule_type: str,
        usual_sleep_time: str,
        usual_wake_time: str,
        preferred_effort: str,
        work_screen_required: bool,
    ) -> Optional[Account]:
        """
        Persist the onboarding preference profile for `user_id` and mark
        onboarding complete. Returns the updated Account, or None if
        `user_id` doesn't correspond to a saved account (e.g. an
        anonymous session - callers should keep the profile in
        `st.session_state` for that case; see utils/session.py).
        """
        updated: Optional[dict] = None
        with self._backend.transaction() as records:
            for record in records:
                if record.get("user_id") == user_id:
                    record.update(
                        primary_goal=primary_goal,
                        main_use_purpose=main_use_purpose,
                        schedule_type=schedule_type,
                        usual_sleep_time=usual_sleep_time,
                        usual_wake_time=usual_wake_time,
                        preferred_effort=preferred_effort,
                        work_screen_required=work_screen_required,
                        onboarding_complete=True,
                        updated_at_utc=_now_iso(),
                    )
                    updated = record
                    break
            self._backend.commit(records)

        return _account_from_record(updated) if updated is not None else None

    # ------------------------------------------------------------
    # Profile extras + privacy controls (P1 items 20, 34, 35)
    # ------------------------------------------------------------

    # An avatar is stored inline in the accounts JSON, so it must stay
    # small. The client already downscales to 256px before encoding;
    # this is the backstop that makes that non-negotiable rather than
    # a client-side courtesy.
    MAX_AVATAR_DATA_URL_CHARS = 400_000  # ~300 KB of base64
    ALLOWED_TONES = ("gentle", "direct", "clinical")

    def save_profile_extras(
        self,
        user_id: str,
        *,
        avatar_data_url: Optional[str] = None,
        recommendation_tone: Optional[str] = None,
    ) -> Optional[Account]:
        """
        Update the presentation-only profile fields. Each argument is
        optional: `None` leaves that field untouched, so the caller can
        change the tone without resending the avatar. Pass an empty
        string to clear a field.

        Raises ValueError for an oversized avatar or an unknown tone -
        never silently truncates or falls back to a default, since both
        would leave the user looking at something they didn't choose.
        """
        if avatar_data_url:
            if len(avatar_data_url) > self.MAX_AVATAR_DATA_URL_CHARS:
                raise ValueError("Avatar image is too large. Please choose a smaller picture.")
            if not avatar_data_url.startswith("data:image/"):
                raise ValueError("Avatar must be an inline image data URL.")
        if recommendation_tone and recommendation_tone not in self.ALLOWED_TONES:
            raise ValueError(f"Tone must be one of {list(self.ALLOWED_TONES)}.")

        updated: Optional[dict] = None
        with self._backend.transaction() as records:
            for record in records:
                if record.get("user_id") == user_id:
                    if avatar_data_url is not None:
                        record["avatar_data_url"] = avatar_data_url or None
                    if recommendation_tone is not None:
                        record["recommendation_tone"] = recommendation_tone or None
                    record["updated_at_utc"] = _now_iso()
                    updated = record
                    break
            self._backend.commit(records)

        return _account_from_record(updated) if updated is not None else None

    def delete_account(self, user_id: str) -> bool:
        """
        Permanently remove this account record (P1 item 35). Returns True
        if a record was actually removed.

        Deliberately only removes the ACCOUNT row - the caller is
        responsible for deleting that user's history/plan/etc. through
        their own services, because this service has no knowledge of
        those stores and silently reaching into them from here would
        hide a destructive side effect behind an innocuous-looking call.
        See api/routers/privacy.py for the endpoint that sequences both.
        """
        removed = False
        with self._backend.transaction() as records:
            remaining = [r for r in records if r.get("user_id") != user_id]
            removed = len(remaining) != len(records)
            if removed:
                self._backend.commit(remaining)
        return removed

    # ------------------------------------------------------------
    # Access tokens - NOT used by the current Streamlit UI (it uses
    # st.session_state; see utils/session.py). Added so a future
    # stateless HTTP layer can issue/verify tokens against these same
    # accounts without re-deriving this logic. See utils/tokens.py for
    # the actual JWT implementation and its configuration requirements
    # (JWT_SECRET_KEY env var).
    # ------------------------------------------------------------

    def issue_access_token(self, account: "Account") -> str:
        """Issue a signed access token for an already-authenticated account."""
        from utils.tokens import create_access_token
        return create_access_token(subject=account.user_id)

    def resolve_access_token(self, token: str) -> Optional[Account]:
        """Validate a token and return the Account it belongs to, or
        None if the token is invalid/expired or no longer refers to a
        real account. Raises nothing on a bad token - callers treat
        None the same as "not authenticated", matching
        get_current_user's behavior in the audited Parisa original."""
        from utils.tokens import decode_access_token, TokenValidationError
        try:
            payload = decode_access_token(token=token)
        except TokenValidationError:
            return None
        return self.get_by_id(payload["sub"])
