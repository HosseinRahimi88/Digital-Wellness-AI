"""
utils/tokens.py
-----------------
JWT access-token issuance/validation - ported from the Parisa
project's `app/core/security.py` (the audited half of that file; see
utils/security.py for why the password-hashing half already got
ported and this half didn't, until now).

Nothing in the current Streamlit app calls this module. Streamlit
already keeps authenticated state server-side in `st.session_state`
(see utils/session.py) and has no need for bearer tokens. This module
exists so a future stateless HTTP layer (FastAPI or otherwise) has a
ready, already-audited token implementation to import - same claims
(sub/iat/exp/jti/type/iss), same validation rules B's version had.

Configuration
-------------
Reads the signing secret from the `JWT_SECRET_KEY` environment
variable (not hardcoded, not defaulted) - `get_jwt_secret()` raises a
clear error if it's unset or shorter than 32 characters, mirroring the
same minimum B enforced via its pydantic Settings validator. This is
lazy: importing this module, or running the existing Streamlit app,
never touches this function. It only matters once something actually
calls `create_access_token()` / `decode_access_token()`.
"""

from __future__ import annotations

import os
import secrets

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

# The one definition of the project root - see core/paths.py. Computed
# by directory depth here until it wasn't, twice; a path relative to a
# file's own position is correct until something moves and silently
# wrong afterwards, because a Path that does not exist still works.
from core import paths

DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_JWT_ISSUER = "digital-wellness-ai"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60


class TokenValidationError(ValueError):
    """Raised when an access token is invalid, expired, or malformed."""


class JWTConfigurationError(RuntimeError):
    """Raised when JWT_SECRET_KEY is missing or too weak to use."""


def get_jwt_secret() -> str:
    """
    Return the configured JWT signing secret, or raise a clear,
    actionable error. Never returns a hardcoded/default secret - a
    weak or shared secret defeats the entire point of signing tokens.
    """
    secret = os.environ.get("JWT_SECRET_KEY")

    if not secret:
        raise JWTConfigurationError(
            "JWT_SECRET_KEY is not set. Set it before issuing or "
            "validating access tokens, e.g.:\n"
            "  export JWT_SECRET_KEY=$(python -c \"import secrets; "
            "print(secrets.token_urlsafe(48))\")"
        )

    if len(secret) < 32:
        raise JWTConfigurationError(
            "JWT_SECRET_KEY must be at least 32 characters long."
        )

    return secret


def ensure_jwt_secret(env_path: "os.PathLike | None" = None) -> None:
    """
    Guarantee `JWT_SECRET_KEY` is set for the rest of this process,
    generating and persisting one if it's missing - called once, eagerly,
    at API startup (see api/main.py's lifespan) so a fresh checkout that
    never had `.env` set up still works instead of every register/login
    call failing with JWTConfigurationError.

    An explicitly-set JWT_SECRET_KEY (real env var or a value already in
    `.env`, loaded by `load_dotenv()` before this runs) is NEVER touched
    or overwritten - this only fills the gap when nothing is set at all.
    The generated secret is appended to `.env` so it survives process
    restarts; without that, every restart would mint a new secret and
    silently invalidate every previously-issued token (which looks to a
    user exactly like "session expired" on their very next action).
    """
    import logging
    import secrets as _secrets
    from pathlib import Path

    logger = logging.getLogger(__name__)

    existing = os.environ.get("JWT_SECRET_KEY")
    if existing and len(existing) >= 32:
        return

    generated = _secrets.token_urlsafe(48)
    os.environ["JWT_SECRET_KEY"] = generated

    target = Path(env_path) if env_path else paths.PROJECT_ROOT / ".env"
    try:
        line = f"JWT_SECRET_KEY={generated}\n"
        if target.exists():
            content = target.read_text(encoding="utf-8")
            if "JWT_SECRET_KEY=" in content:
                # An empty/placeholder line (e.g. the committed .env.example
                # copied verbatim) - replace it in place rather than
                # duplicating the key.
                lines = [line if l.startswith("JWT_SECRET_KEY=") else l for l in content.splitlines(keepends=True)]
                target.write_text("".join(lines), encoding="utf-8")
            else:
                with open(target, "a", encoding="utf-8") as f:
                    f.write(("\n" if content and not content.endswith("\n") else "") + line)
        else:
            target.write_text(line, encoding="utf-8")
        logger.warning(
            "JWT_SECRET_KEY was not set - generated one and saved it to %s so it stays stable "
            "across restarts. Set JWT_SECRET_KEY yourself (env var or .env) for a real deployment.",
            target,
        )
    except OSError:
        logger.warning(
            "JWT_SECRET_KEY was not set and could not be written to %s - a new one will be "
            "generated every restart, which invalidates every existing session each time. "
            "Set JWT_SECRET_KEY explicitly (env var or .env) to fix this permanently.",
            target,
        )


def create_access_token(
    *,
    subject: str,
    secret_key: str | None = None,
    algorithm: str = DEFAULT_JWT_ALGORITHM,
    issuer: str = DEFAULT_JWT_ISSUER,
    expires_delta: timedelta = timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
    now: datetime | None = None,
) -> str:
    """
    Create a signed access token for `subject` (a user_id).
    `secret_key` defaults to `get_jwt_secret()` if not passed
    explicitly (tests pass an explicit key instead of setting env vars).
    """
    if secret_key is None:
        secret_key = get_jwt_secret()

    if not secret_key:
        raise ValueError("JWT secret must not be empty.")

    current_time = now if now is not None else datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    expires_at = current_time + expires_delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": current_time,
        "exp": expires_at,
        "jti": secrets.token_hex(16),
        "type": "access",
        "iss": issuer,
    }

    return jwt.encode(payload, secret_key, algorithm=algorithm)


DEFAULT_PASSWORD_RESET_EXPIRE_MINUTES = 15


def create_password_reset_token(
    *, subject: str, secret_key: str | None = None, algorithm: str = DEFAULT_JWT_ALGORITHM,
    issuer: str = DEFAULT_JWT_ISSUER, expires_delta: timedelta = timedelta(minutes=DEFAULT_PASSWORD_RESET_EXPIRE_MINUTES),
    now: datetime | None = None,
) -> str:
    """A short-lived, single-purpose token for the forgot-password flow -
    same signing key and claim shape as an access token, but `type` is
    "password_reset" so decode_password_reset_token() (and, just as
    importantly, decode_access_token()) each only ever accept the token
    kind they were built for.

    This token used to be returned in the /auth/forgot-password
    RESPONSE, because the app had no way to send mail. That made an
    email address sufficient to take over the account it belonged to.
    It now leaves through services/identity/mail_service - a real SMTP
    server when one is configured, the server log when one is not - and
    never over HTTP. See api/routers/auth.py's forgot_password."""
    if secret_key is None:
        secret_key = get_jwt_secret()
    current_time = now if now is not None else datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": current_time,
        "exp": current_time + expires_delta,
        "jti": secrets.token_hex(16),
        "type": "password_reset",
        "iss": issuer,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_password_reset_token(
    *, token: str, secret_key: str | None = None, algorithm: str = DEFAULT_JWT_ALGORITHM, issuer: str = DEFAULT_JWT_ISSUER,
) -> dict[str, Any]:
    """Same validation as decode_access_token, but only accepts a token
    minted by create_password_reset_token - an expired/leaked access
    token can never be replayed here to change a password, and a reset
    token can never be replayed as an access token."""
    if secret_key is None:
        secret_key = get_jwt_secret()
    if not token:
        raise TokenValidationError("Token must not be empty.")
    try:
        payload = jwt.decode(
            token, secret_key, algorithms=[algorithm], issuer=issuer,
            options={"require": ["sub", "iat", "exp", "jti", "type", "iss"]},
        )
    except jwt.PyJWTError as error:
        raise TokenValidationError("Invalid or expired reset token.") from error
    if payload.get("type") != "password_reset":
        raise TokenValidationError("Invalid token type.")
    if not payload.get("sub"):
        raise TokenValidationError("Token subject is missing.")
    return payload


def decode_access_token(
    *,
    token: str,
    secret_key: str | None = None,
    algorithm: str = DEFAULT_JWT_ALGORITHM,
    issuer: str = DEFAULT_JWT_ISSUER,
) -> dict[str, Any]:
    """Validate and decode an access token, returning its payload.
    Raises TokenValidationError on any problem (expired, bad signature,
    wrong issuer/type, missing required claims)."""
    if secret_key is None:
        secret_key = get_jwt_secret()

    if not token:
        raise TokenValidationError("Token must not be empty.")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            issuer=issuer,
            options={"require": ["sub", "iat", "exp", "jti", "type", "iss"]},
        )
    except jwt.PyJWTError as error:
        raise TokenValidationError("Invalid or expired access token.") from error

    if payload.get("type") != "access":
        raise TokenValidationError("Invalid token type.")

    if not payload.get("sub"):
        raise TokenValidationError("Token subject is missing.")

    return payload


# ------------------------------------------------------------------
# Email verification
# ------------------------------------------------------------------
DEFAULT_EMAIL_VERIFICATION_EXPIRE_HOURS = 24


def create_email_verification_token(
    *, subject: str, email: str, secret_key: str | None = None,
    algorithm: str = DEFAULT_JWT_ALGORITHM, issuer: str = DEFAULT_JWT_ISSUER,
    expires_delta: timedelta = timedelta(hours=DEFAULT_EMAIL_VERIFICATION_EXPIRE_HOURS),
    now: datetime | None = None,
) -> str:
    """Proof that whoever holds this token can read `email`.

    Carries the address as well as the subject, and
    AccountService.verify_email() checks the two still agree. Without
    that, a token minted before an address change would verify the NEW
    address - the user would have proven they can read an inbox they no
    longer use.
    """
    if secret_key is None:
        secret_key = get_jwt_secret()
    current_time = now if now is not None else datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "email": str(email).strip().lower(),
        "iat": current_time,
        "exp": current_time + expires_delta,
        "jti": secrets.token_hex(16),
        "type": "email_verification",
        "iss": issuer,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_email_verification_token(
    *, token: str, secret_key: str | None = None,
    algorithm: str = DEFAULT_JWT_ALGORITHM, issuer: str = DEFAULT_JWT_ISSUER,
) -> dict[str, Any]:
    if secret_key is None:
        secret_key = get_jwt_secret()
    if not token:
        raise TokenValidationError("Token must not be empty.")
    try:
        payload = jwt.decode(
            token, secret_key, algorithms=[algorithm], issuer=issuer,
            options={"require": ["sub", "iat", "exp", "jti", "type", "iss"]},
        )
    except jwt.PyJWTError as error:
        raise TokenValidationError("Invalid or expired verification token.") from error
    if payload.get("type") != "email_verification":
        raise TokenValidationError("Invalid token type.")
    if not payload.get("sub") or not payload.get("email"):
        raise TokenValidationError("Verification token is missing a claim.")
    return payload


# ------------------------------------------------------------------
# Refresh tokens
# ------------------------------------------------------------------
# An access token lasts an hour and cannot be revoked; that is the whole
# reason it is short. A refresh token is the opposite - long-lived, and
# therefore only safe if it CAN be revoked, which is why its jti is
# recorded server-side by services/identity/refresh_token_service.py.
# The JWT alone is never sufficient to mint a new session.
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_refresh_token(
    *, subject: str, jti: str | None = None, secret_key: str | None = None,
    algorithm: str = DEFAULT_JWT_ALGORITHM, issuer: str = DEFAULT_JWT_ISSUER,
    expires_delta: timedelta = timedelta(days=DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS),
    now: datetime | None = None,
) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at).

    The jti comes back to the caller because it is the handle the
    revocation store keys off - generating it here and returning it is
    what keeps the token and its server-side record in step without
    decoding the token again immediately after signing it.
    """
    if secret_key is None:
        secret_key = get_jwt_secret()
    current_time = now if now is not None else datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    token_id = jti or secrets.token_hex(16)
    expires_at = current_time + expires_delta
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": current_time,
        "exp": expires_at,
        "jti": token_id,
        "type": "refresh",
        "iss": issuer,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm), token_id, expires_at


def decode_refresh_token(
    *, token: str, secret_key: str | None = None,
    algorithm: str = DEFAULT_JWT_ALGORITHM, issuer: str = DEFAULT_JWT_ISSUER,
) -> dict[str, Any]:
    if secret_key is None:
        secret_key = get_jwt_secret()
    if not token:
        raise TokenValidationError("Token must not be empty.")
    try:
        payload = jwt.decode(
            token, secret_key, algorithms=[algorithm], issuer=issuer,
            options={"require": ["sub", "iat", "exp", "jti", "type", "iss"]},
        )
    except jwt.PyJWTError as error:
        raise TokenValidationError("Invalid or expired refresh token.") from error
    if payload.get("type") != "refresh":
        raise TokenValidationError("Invalid token type.")
    if not payload.get("sub"):
        raise TokenValidationError("Token subject is missing.")
    return payload
