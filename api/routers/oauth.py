"""
api/routers/oauth.py
-----------------------
Sign in / sign up with Google, GitHub or Microsoft.

These routes are browser redirects, not JSON API calls, so they behave
differently from the rest of this package on purpose: the callback ends
in a 302 back to the frontend rather than a response body, carrying the
**existing** access token from AccountService.issue_access_token(). There
is no second token format and no parallel session system - a provider
sign-in lands in exactly the same authenticated state as a password
login.

Where the security-relevant steps live
----------------------------------------
* `state` is minted in /login, stored in the signed session cookie, and
  compared in /callback (services/oauth_service.verify_state). It is
  popped on use, so a captured callback URL cannot be replayed.
* The provider only ever gives us a verified email
  (services/oauth_service).
* Linking by email and the password lock are AccountService's job
  (link_or_create_oauth_account).
* Errors redirect back with a short, non-technical `?oauth_error=` code
  that the frontend translates. No secret, token, code, or file path is
  ever put in a redirect or a log line.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from api.dependencies.services import get_account_service
from api.routers.auth import _issue_session
from services.identity.account_service import AccountService
from services.identity.oauth_service import (
    EmailNotVerifiedError,
    OAuthError,
    OAuthService,
    ProviderExchangeError,
    ProviderNotConfiguredError,
    StateMismatchError,
    UnknownProviderError,
    new_state,
    verify_state,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["OAuth Sign-in"])

# Session keys are namespaced per provider so two tabs mid-sign-in with
# different providers cannot clobber each other's state.
def _state_key(provider: str) -> str:
    return f"oauth_state_{provider}"


def _frontend_redirect(request: Request, **params: str) -> RedirectResponse:
    """
    Back to the app's entry page. Built from the incoming request so it
    works on localhost and behind a proxy without extra configuration.
    """
    query = "&".join(f"{k}={v}" for k, v in params.items() if v)
    target = str(request.base_url).rstrip("/") + "/app.html"
    if query:
        target = f"{target}?{query}"
    return RedirectResponse(target, status_code=302)


@router.get("/{provider}/login", summary="Start sign-in with Google, GitHub or Microsoft")
def oauth_login(provider: str, request: Request) -> RedirectResponse:
    service = OAuthService(base_url=str(request.base_url).rstrip("/"))
    # A provider that is present in the registry but switched off for this
    # deployment must not be reachable by typing its URL directly.
    if not service.is_configured(provider):
        return _frontend_redirect(request, oauth_error="not_configured")
    try:
        state = new_state()
        url = service.authorization_url(provider, state)
    except UnknownProviderError:
        return _frontend_redirect(request, oauth_error="unknown_provider")
    except ProviderNotConfiguredError:
        return _frontend_redirect(request, oauth_error="not_configured")

    request.session[_state_key(provider)] = state
    return RedirectResponse(url, status_code=302)


@router.get("/{provider}/callback", summary="Complete sign-in and issue the normal access token")
async def oauth_callback(
    provider: str,
    request: Request,
    account_service: AccountService = Depends(get_account_service),
) -> RedirectResponse:
    # The user pressed "cancel" on the provider's consent screen. Not an
    # error worth a message - just put them back where they started.
    if request.query_params.get("error"):
        request.session.pop(_state_key(provider), None)
        return _frontend_redirect(request)

    code = request.query_params.get("code")
    received_state = request.query_params.get("state")
    expected_state = request.session.pop(_state_key(provider), None)

    if not code:
        return _frontend_redirect(request, oauth_error="expired")

    service = OAuthService(base_url=str(request.base_url).rstrip("/"))
    if not service.is_configured(provider):
        return _frontend_redirect(request, oauth_error="not_configured")
    try:
        verify_state(expected_state, received_state)
        identity = await service.exchange_code(provider, code)
        account = account_service.link_or_create_oauth_account(
            email=identity.email,
            display_name=identity.display_name,
            provider=identity.provider,
        )
    except StateMismatchError:
        return _frontend_redirect(request, oauth_error="state")
    except EmailNotVerifiedError:
        return _frontend_redirect(request, oauth_error="unverified_email")
    except ProviderExchangeError:
        return _frontend_redirect(request, oauth_error="exchange")
    except (UnknownProviderError, ProviderNotConfiguredError):
        return _frontend_redirect(request, oauth_error="not_configured")
    except OAuthError:
        return _frontend_redirect(request, oauth_error="exchange")
    except Exception:  # noqa: BLE001
        # Never let an unexpected failure render a stack trace into the
        # browser on an auth route.
        logger.exception("Unexpected failure completing %s sign-in", provider)
        return _frontend_redirect(request, oauth_error="exchange")

    # Through the shared helper so a GitHub sign-in gets the same
    # revocable session a password sign-in does. Issuing a bare access
    # token here is how one login path quietly ends up un-revocable.
    token = _issue_session(account, account_service).access_token
    return _frontend_redirect(request, oauth_token=token, oauth_provider=identity.provider)


@router.get("/providers", summary="Which sign-in providers this server has configured")
def oauth_providers() -> dict:
    """
    Lets the frontend show only buttons that can actually work, instead
    of advertising a provider whose credentials are absent.
    """
    service = OAuthService()
    return {"providers": service.configured_providers()}
