"""
api/auth/security.py
----------------------
Bearer-token authentication for the API. Deliberately thin: token
issuance and verification already live in services/account_service.py
(AccountService.issue_access_token / .resolve_access_token), which in
turn delegate to utils/tokens.py's already-audited JWT implementation.
Nothing here re-implements JWT signing or verification - this module
only wires FastAPI's dependency-injection and OpenAPI-docs machinery
(the "Authorize" button in Swagger UI) on top of what already exists.
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from api.exceptions.errors import UnauthorizedError
from api.dependencies.services import get_account_service
from services.account_service import Account, AccountService

# tokenUrl is the path Swagger UI's "Authorize" dialog POSTs to - purely
# for interactive docs; the dependency below is what actually enforces
# auth on every protected route.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_account(
    token: str | None = Depends(oauth2_scheme),
    account_service: AccountService = Depends(get_account_service),
) -> Account:
    """Resolve the bearer token to an Account via the existing
    AccountService.resolve_access_token(), or raise 401. Every
    protected router depends on this, never on decoding a token itself."""
    if not token:
        raise UnauthorizedError("Not authenticated. Provide a Bearer access token.")

    account = account_service.resolve_access_token(token)
    if account is None:
        raise UnauthorizedError("Invalid or expired access token.")
    if not account.is_active:
        raise UnauthorizedError("This account is inactive.")
    return account


def get_optional_account(
    token: str | None = Depends(oauth2_scheme),
    account_service: AccountService = Depends(get_account_service),
) -> Account | None:
    """Same resolution as get_current_account, but returns None instead
    of raising when no/invalid token is supplied - for the handful of
    endpoints (cohort comparisons, health) that are useful without auth
    but can personalize if a caller happens to be authenticated."""
    if not token:
        return None
    account = account_service.resolve_access_token(token)
    if account is None or not account.is_active:
        return None
    return account
