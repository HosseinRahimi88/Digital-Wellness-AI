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
