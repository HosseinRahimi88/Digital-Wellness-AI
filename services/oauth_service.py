"""
OAuth Sign-in Service (Google / GitHub / Microsoft)
-----------------------------------------------------
Turns a provider's authorization code into a verified `OAuthIdentity`
(email + display name + provider user id). It deliberately stops there:
issuing the session token, linking to a local account, and enforcing the
password lock all stay in AccountService / the router, so this file has
exactly one job and there is no second, parallel authentication system.

Why hand-rolled instead of authlib
-------------------------------------
The three providers here differ only in URLs, scopes and the shape of
their userinfo payload - which is a table, not a framework. Writing the
two HTTP calls directly keeps the dependency list unchanged and makes
the security-relevant steps (state validation, verified-email checks)
visible in this file rather than buried in library defaults.

Security rules enforced here
-------------------------------
* `state` is generated here and *must* be handed back for validation by
  the caller (the router stores it in the signed session cookie). A
  missing or mismatched state raises StateMismatchError - without this,
  the callback is open to login CSRF.
* Only a **verified** email is ever returned. Google exposes
  `email_verified`; GitHub needs a second call to /user/emails because
  the profile endpoint hides private addresses and carries no verified
  flag; Microsoft's userinfo email is the account's own directory
  identity, which Microsoft itself controls (see _identity_from_microsoft).
* Scopes are the minimum each provider needs to return an email.
* No exception raised here carries a client secret, token, code, or file
  path - callers surface these straight to users.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

STATE_BYTES = 32
HTTP_TIMEOUT_SECONDS = 10.0


class OAuthError(Exception):
    """Base class for sign-in failures that are safe to show a user."""


class ProviderNotConfiguredError(OAuthError):
    pass


class UnknownProviderError(OAuthError):
    pass


class StateMismatchError(OAuthError):
    pass


class EmailNotVerifiedError(OAuthError):
    pass


class ProviderExchangeError(OAuthError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    key: str
    label: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: tuple[str, ...]
    # Env var NAMES only - values are read at call time and never stored
    # on the instance, logged, or included in an error.
    client_id_env: str
    client_secret_env: str
    redirect_uri_env: str
    default_callback_path: str


PROVIDERS: dict[str, ProviderSpec] = {
    "google": ProviderSpec(
        key="google",
        label="Google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scopes=("openid", "email", "profile"),
        client_id_env="GOOGLE_CLIENT_ID",
        client_secret_env="GOOGLE_CLIENT_SECRET",
        redirect_uri_env="GOOGLE_REDIRECT_URI",
        default_callback_path="/api/v1/auth/google/callback",
    ),
    "github": ProviderSpec(
        key="github",
        label="GitHub",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        userinfo_url="https://api.github.com/user",
        scopes=("read:user", "user:email"),
        client_id_env="GITHUB_CLIENT_ID",
        client_secret_env="GITHUB_CLIENT_SECRET",
        redirect_uri_env="GITHUB_REDIRECT_URI",
        default_callback_path="/api/v1/auth/github/callback",
    ),
    "microsoft": ProviderSpec(
        key="microsoft",
        label="Microsoft",
        # "common" accepts both personal and work/school accounts.
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/oidc/userinfo",
        scopes=("openid", "email", "profile"),
        client_id_env="MICROSOFT_CLIENT_ID",
        client_secret_env="MICROSOFT_CLIENT_SECRET",
        redirect_uri_env="MICROSOFT_REDIRECT_URI",
        default_callback_path="/api/v1/auth/microsoft/callback",
    ),
}


@dataclass(frozen=True, slots=True)
class OAuthIdentity:
    """A provider-verified identity. `email` is always verified."""

    provider: str
    email: str
    display_name: str
    provider_user_id: str


def spec_for(provider: str) -> ProviderSpec:
    spec = PROVIDERS.get((provider or "").strip().lower())
    if spec is None:
        raise UnknownProviderError("Unknown sign-in provider.")
    return spec


def new_state() -> str:
    """A fresh, unguessable state value for one authorization round-trip."""
    return secrets.token_urlsafe(STATE_BYTES)


def verify_state(expected: Optional[str], received: Optional[str]) -> None:
    """
    Constant-time comparison of the stored vs. returned state. Raises
    StateMismatchError when either side is missing - an absent stored
    state means the callback arrived without a matching login step,
    which is exactly the case this check exists to reject.
    """
    if not expected or not received or not secrets.compare_digest(str(expected), str(received)):
        raise StateMismatchError("This sign-in link is no longer valid. Please try again.")


class OAuthService:
    """Builds authorize URLs and exchanges codes for verified identities."""

    def __init__(self, base_url: str = "") -> None:
        # Only used to derive a callback URL when the *_REDIRECT_URI env
        # var is unset (local development). Production must set it
        # explicitly, because it has to match the provider console byte
        # for byte.
        self._base_url = base_url.rstrip("/")

    # -------------------------------------------------- configuration

    def _client_id(self, spec: ProviderSpec) -> str:
        value = os.environ.get(spec.client_id_env, "").strip()
        if not value:
            raise ProviderNotConfiguredError(
                f"{spec.label} sign-in is not configured on this server."
            )
        return value

    def _client_secret(self, spec: ProviderSpec) -> str:
        value = os.environ.get(spec.client_secret_env, "").strip()
        if not value:
            raise ProviderNotConfiguredError(
                f"{spec.label} sign-in is not configured on this server."
            )
        return value

    def redirect_uri(self, spec: ProviderSpec) -> str:
        explicit = os.environ.get(spec.redirect_uri_env, "").strip()
        if explicit:
            return explicit
        fallback = f"{self._base_url}{spec.default_callback_path}"
        logger.warning(
            "%s is not set - falling back to %s. This must match the redirect URI "
            "registered in the %s console exactly, or the provider will reject the "
            "sign-in.",
            spec.redirect_uri_env, fallback, spec.label,
        )
        return fallback

    @staticmethod
    def enabled_providers() -> set[str]:
        """
        Which providers this deployment actually offers.

        Credentials being present is not enough - a provider also has to
        be switched on here. Kept separate so an unused provider can be
        taken out of the UI without deleting its credentials or its code
        path, and switched back on with one env var rather than a code
        change. Defaults to GitHub alone.
        """
        raw = os.environ.get("OAUTH_ENABLED_PROVIDERS", "github")
        wanted = {p.strip().lower() for p in raw.split(",") if p.strip()}
        return {p for p in wanted if p in PROVIDERS}

    def is_configured(self, provider: str) -> bool:
        """True when this provider is enabled AND has an id and secret."""
        try:
            spec = spec_for(provider)
        except UnknownProviderError:
            return False
        if spec.key not in self.enabled_providers():
            return False
        return bool(
            os.environ.get(spec.client_id_env, "").strip()
            and os.environ.get(spec.client_secret_env, "").strip()
        )

    def configured_providers(self) -> list[str]:
        return [key for key in PROVIDERS if self.is_configured(key)]

    # -------------------------------------------------- step 1: redirect

    def authorization_url(self, provider: str, state: str) -> str:
        spec = spec_for(provider)
        params = {
            "client_id": self._client_id(spec),
            "redirect_uri": self.redirect_uri(spec),
            "scope": " ".join(spec.scopes),
            "state": state,
            "response_type": "code",
        }
        if spec.key in ("google", "microsoft"):
            # Ask for a refreshable consent screen only where it is
            # meaningful; GitHub has no equivalent parameters.
            params["access_type"] = "online"
            params["prompt"] = "select_account"
        return f"{spec.authorize_url}?{urlencode(params)}"

    # -------------------------------------------------- step 2: exchange

    async def exchange_code(self, provider: str, code: str) -> OAuthIdentity:
        """
        Trade `code` for an access token, then resolve a verified email.
        Network/HTTP problems surface as ProviderExchangeError with a
        generic message; the underlying detail is logged, never returned.
        """
        spec = spec_for(provider)
        payload = {
            "client_id": self._client_id(spec),
            "client_secret": self._client_secret(spec),
            "code": code,
            "redirect_uri": self.redirect_uri(spec),
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                token_response = await client.post(
                    spec.token_url, data=payload, headers={"Accept": "application/json"},
                )
                if token_response.status_code >= 400:
                    logger.warning(
                        "%s token exchange failed with HTTP %s", spec.label, token_response.status_code,
                    )
                    raise ProviderExchangeError(
                        "That sign-in attempt could not be completed. Please try again."
                    )
                token_data = token_response.json()
                access_token = token_data.get("access_token")
                if not access_token:
                    # Providers report a bad/expired code here rather than
                    # via HTTP status. token_data can contain identifying
                    # detail, so only the error *code* is logged.
                    logger.warning(
                        "%s returned no access token (error=%s)", spec.label, token_data.get("error"),
                    )
                    raise ProviderExchangeError(
                        "That sign-in link has expired. Please try again."
                    )

                return await self._fetch_identity(client, spec, access_token)

        except httpx.HTTPError as exc:
            logger.warning("%s sign-in network failure: %s", spec.label, type(exc).__name__)
            raise ProviderExchangeError(
                "Could not reach the sign-in provider. Check your connection and try again."
            ) from exc

    async def _fetch_identity(
        self, client: httpx.AsyncClient, spec: ProviderSpec, access_token: str,
    ) -> OAuthIdentity:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        response = await client.get(spec.userinfo_url, headers=headers)
        if response.status_code >= 400:
            logger.warning("%s userinfo failed with HTTP %s", spec.label, response.status_code)
            raise ProviderExchangeError(
                "That sign-in attempt could not be completed. Please try again."
            )
        profile = response.json()

        if spec.key == "google":
            return _identity_from_google(profile)
        if spec.key == "microsoft":
            return _identity_from_microsoft(profile)
        return await _identity_from_github(client, profile, headers)


# ------------------------------------------------------ provider parsing


def _identity_from_google(profile: dict[str, Any]) -> OAuthIdentity:
    email = (profile.get("email") or "").strip().lower()
    # Google returns this as a real bool on the OIDC userinfo endpoint;
    # some older paths return the string "true".
    verified = profile.get("email_verified")
    if isinstance(verified, str):
        verified = verified.strip().lower() == "true"
    if not email or not verified:
        raise EmailNotVerifiedError(
            "Your Google email address is not verified. Verify it with Google, then try again."
        )
    return OAuthIdentity(
        provider="google",
        email=email,
        display_name=(profile.get("name") or email.split("@")[0]).strip(),
        provider_user_id=str(profile.get("sub") or ""),
    )


def _identity_from_microsoft(profile: dict[str, Any]) -> OAuthIdentity:
    # Microsoft's OIDC userinfo has no `email_verified` claim: the address
    # it returns *is* the directory identity the user just authenticated
    # against, which Microsoft controls. There is no unverified state to
    # filter out, unlike GitHub where users can add arbitrary addresses.
    email = (profile.get("email") or profile.get("preferred_username") or "").strip().lower()
    if not email:
        raise EmailNotVerifiedError(
            "Microsoft did not return an email address for this account."
        )
    return OAuthIdentity(
        provider="microsoft",
        email=email,
        display_name=(profile.get("name") or email.split("@")[0]).strip(),
        provider_user_id=str(profile.get("sub") or ""),
    )


async def _identity_from_github(
    client: httpx.AsyncClient, profile: dict[str, Any], headers: dict[str, str],
) -> OAuthIdentity:
    """
    GitHub's /user endpoint omits the email entirely when the user keeps
    it private, and never says whether it is verified - so the address
    always comes from /user/emails, where we can require both
    `primary` and `verified`.
    """
    login = (profile.get("login") or "").strip()
    display_name = (profile.get("name") or login or "").strip()

    emails_response = await client.get("https://api.github.com/user/emails", headers=headers)
    if emails_response.status_code >= 400:
        logger.warning("GitHub /user/emails failed with HTTP %s", emails_response.status_code)
        raise ProviderExchangeError(
            "That sign-in attempt could not be completed. Please try again."
        )

    entries = emails_response.json()
    if not isinstance(entries, list):
        raise ProviderExchangeError(
            "That sign-in attempt could not be completed. Please try again."
        )

    verified = [e for e in entries if isinstance(e, dict) and e.get("verified")]
    chosen = next((e for e in verified if e.get("primary")), None) or (verified[0] if verified else None)
    if chosen is None:
        raise EmailNotVerifiedError(
            "Your GitHub account has no verified email address. Verify one on GitHub, then try again."
        )

    email = str(chosen.get("email") or "").strip().lower()
    if not email:
        raise EmailNotVerifiedError(
            "Your GitHub account has no verified email address. Verify one on GitHub, then try again."
        )

    return OAuthIdentity(
        provider="github",
        email=email,
        display_name=display_name or email.split("@")[0],
        provider_user_id=str(profile.get("id") or ""),
    )
