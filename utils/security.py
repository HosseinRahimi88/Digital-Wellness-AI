"""
utils/security.py
------------------
Password hashing for local user accounts.

Ported from the Parisa project's `app/core/security.py`. That project
also issued JWT bearer tokens for its FastAPI HTTP layer; when this
project had no separate HTTP client (only Streamlit, which keeps
authenticated state server-side in `st.session_state` - see
`utils/session.py`), only the hashing primitives were kept here. The
project has since grown a stateless HTTP API (api/ - see
api/auth/security.py) - its JWT issuance/validation lives in
utils/tokens.py, a separate module from this one, not merged back into
it, since password hashing and token issuance are independent concerns
with independent callers (AccountService uses both, but calls each
directly - see services/identity/account_service.py).

Uses Argon2 (via `pwdlib`), matching the algorithm choice audited and
kept from Project B - not a fallback/degraded scheme.
"""

from __future__ import annotations

import logging

from pwdlib import PasswordHash

logger = logging.getLogger(__name__)

PASSWORD_HASHER = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2. Raises on empty input."""
    if not password:
        raise ValueError("Password must not be empty.")
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Never raises - any malformed hash or verification error is treated
    as "does not match" so callers can use this directly in login flows
    without a try/except.
    """
    if not password or not password_hash:
        return False
    try:
        return PASSWORD_HASHER.verify(password, password_hash)
    except Exception:
        # Deliberately no exc_info here (unlike the other except-Exception
        # fixes elsewhere in this audit): the exception payload from a
        # password-verification failure can echo back fragments of the
        # stored hash or verifier internals, which has no business in a
        # log stream. A bare "verification failed" is all that's needed
        # to know this path was hit at all.
        logger.debug("Password verification failed (malformed hash or verifier error).")
        return False
