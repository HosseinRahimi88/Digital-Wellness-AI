"""
Tests for OAuth sign-in (services/identity/oauth_service.py + the account-linking
and password-lock rules in services/identity/account_service.py).

No real provider is contacted: httpx calls are stubbed so the parsing and
security rules can be exercised deterministically. The point of these
tests is the rules, not the HTTP plumbing:
  * only a verified email is accepted (Google flag, GitHub /user/emails)
  * `state` must round-trip, and a missing stored state is a failure
  * an existing email links instead of creating a second account
  * a provider-created account cannot use the password or reset paths
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.identity.account_service import (
    AccountService,
    PasswordLoginNotAvailableError,
)
from services.identity.oauth_service import (
    EmailNotVerifiedError,
    OAuthService,
    StateMismatchError,
    _identity_from_github,
    _identity_from_google,
    _identity_from_microsoft,
    new_state,
    verify_state,
)
from services.storage.json_file_storage import JSONFileStorageBackend


class TestStateValidation(unittest.TestCase):
    def test_matching_state_passes(self):
        state = new_state()
        verify_state(state, state)  # must not raise

    def test_state_values_are_unique(self):
        self.assertNotEqual(new_state(), new_state())

    def test_mismatched_state_rejected(self):
        with self.assertRaises(StateMismatchError):
            verify_state(new_state(), new_state())

    def test_missing_stored_state_rejected(self):
        """A callback with no matching login step must not be accepted."""
        with self.assertRaises(StateMismatchError):
            verify_state(None, "whatever-came-back")

    def test_missing_returned_state_rejected(self):
        with self.assertRaises(StateMismatchError):
            verify_state(new_state(), None)


class TestGoogleParsing(unittest.TestCase):
    def test_verified_email_accepted(self):
        identity = _identity_from_google(
            {"email": "Person@Example.com", "email_verified": True, "name": "Person", "sub": "1"}
        )
        self.assertEqual(identity.email, "person@example.com")  # normalized
        self.assertEqual(identity.provider, "google")

    def test_string_true_accepted(self):
        identity = _identity_from_google(
            {"email": "a@b.com", "email_verified": "true", "name": "A", "sub": "2"}
        )
        self.assertEqual(identity.email, "a@b.com")

    def test_unverified_email_rejected(self):
        with self.assertRaises(EmailNotVerifiedError):
            _identity_from_google({"email": "a@b.com", "email_verified": False, "sub": "3"})

    def test_missing_email_rejected(self):
        with self.assertRaises(EmailNotVerifiedError):
            _identity_from_google({"email_verified": True, "sub": "4"})


class TestMicrosoftParsing(unittest.TestCase):
    def test_email_claim_used(self):
        identity = _identity_from_microsoft({"email": "X@Y.com", "name": "X", "sub": "5"})
        self.assertEqual(identity.email, "x@y.com")

    def test_missing_email_rejected(self):
        with self.assertRaises(EmailNotVerifiedError):
            _identity_from_microsoft({"name": "no email", "sub": "6"})


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeClient:
    """Stands in for httpx.AsyncClient for the /user/emails call."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self._status = status_code

    async def get(self, url, headers=None):  # noqa: ARG002
        return _FakeResponse(self._payload, self._status)


class TestGitHubParsing(unittest.TestCase):
    def _resolve(self, emails, profile=None):
        client = _FakeClient(emails)
        return asyncio.run(
            _identity_from_github(client, profile or {"login": "octo", "name": "Octo", "id": 7}, {})
        )

    def test_primary_verified_email_chosen(self):
        identity = self._resolve([
            {"email": "secondary@x.com", "primary": False, "verified": True},
            {"email": "Primary@X.com", "primary": True, "verified": True},
        ])
        self.assertEqual(identity.email, "primary@x.com")
        self.assertEqual(identity.provider, "github")

    def test_private_email_resolved_from_emails_endpoint(self):
        """The profile carries no email at all when the user hides it."""
        identity = self._resolve(
            [{"email": "hidden@x.com", "primary": True, "verified": True}],
            profile={"login": "octo", "name": None, "id": 8},
        )
        self.assertEqual(identity.email, "hidden@x.com")
        self.assertEqual(identity.display_name, "octo")

    def test_unverified_only_rejected(self):
        with self.assertRaises(EmailNotVerifiedError):
            self._resolve([{"email": "nope@x.com", "primary": True, "verified": False}])

    def test_verified_non_primary_used_when_no_primary(self):
        identity = self._resolve([{"email": "only@x.com", "primary": False, "verified": True}])
        self.assertEqual(identity.email, "only@x.com")

    def test_empty_list_rejected(self):
        with self.assertRaises(EmailNotVerifiedError):
            self._resolve([])


class TestEnabledProviders(unittest.TestCase):
    def test_defaults_to_github_only(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OAUTH_ENABLED_PROVIDERS", None)
            self.assertEqual(OAuthService.enabled_providers(), {"github"})

    def test_disabled_provider_is_not_configured_even_with_credentials(self):
        env = {
            "OAUTH_ENABLED_PROVIDERS": "github",
            "GOOGLE_CLIENT_ID": "id",
            "GOOGLE_CLIENT_SECRET": "secret",
        }
        with patch.dict(os.environ, env):
            self.assertFalse(OAuthService().is_configured("google"))

    def test_unknown_provider_is_not_configured(self):
        self.assertFalse(OAuthService().is_configured("myspace"))

    def test_authorize_url_carries_state_and_minimal_scopes(self):
        env = {
            "OAUTH_ENABLED_PROVIDERS": "github",
            "GITHUB_CLIENT_ID": "cid",
            "GITHUB_CLIENT_SECRET": "csecret",
            "GITHUB_REDIRECT_URI": "http://localhost:8000/api/v1/auth/github/callback",
        }
        with patch.dict(os.environ, env):
            url = OAuthService().authorization_url("github", "STATE123")
        self.assertIn("state=STATE123", url)
        self.assertIn("read%3Auser", url)
        self.assertIn("user%3Aemail", url)
        self.assertIn("localhost%3A8000", url)
        # The secret must never appear in a URL the browser will see.
        self.assertNotIn("csecret", url)


class TestAccountLinkingAndPasswordLock(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "accounts.json"
        self.service = AccountService(backend=JSONFileStorageBackend(path))

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_signin_creates_account_without_password(self):
        account = self.service.link_or_create_oauth_account(
            email="new@example.com", display_name="New", provider="github"
        )
        self.assertEqual(account.auth_provider, "github")
        self.assertFalse(account.has_password)

    def test_second_signin_links_same_account(self):
        first = self.service.link_or_create_oauth_account(
            email="same@example.com", display_name="Same", provider="github"
        )
        second = self.service.link_or_create_oauth_account(
            email="SAME@example.com", display_name="Same", provider="github"
        )
        self.assertEqual(first.user_id, second.user_id)

    def test_existing_password_account_is_linked_not_duplicated(self):
        registered = self.service.register(
            email="both@example.com", password="RealPass123!", display_name="Both"
        )
        linked = self.service.link_or_create_oauth_account(
            email="both@example.com", display_name="Both", provider="github"
        )
        self.assertEqual(registered.user_id, linked.user_id)
        # Never downgraded: the password route still works afterwards.
        self.assertTrue(linked.has_password)
        self.assertIsNotNone(
            self.service.authenticate(email="both@example.com", password="RealPass123!")
        )

    def test_provider_account_cannot_password_login(self):
        self.service.link_or_create_oauth_account(
            email="oauth@example.com", display_name="O", provider="github"
        )
        with self.assertRaises(PasswordLoginNotAvailableError):
            self.service.authenticate(email="oauth@example.com", password="anything-at-all")

    def test_provider_account_cannot_get_reset_token(self):
        """Without this, knowing the address would be enough to take over."""
        self.service.link_or_create_oauth_account(
            email="oauth2@example.com", display_name="O", provider="github"
        )
        self.assertIsNone(self.service.issue_password_reset_token("oauth2@example.com"))

    def test_password_account_can_still_get_reset_token(self):
        self.service.register(
            email="pw@example.com", password="RealPass123!", display_name="PW"
        )
        # Minting a real reset token needs a signing secret; supply one for
        # the duration of this assertion rather than relying on the
        # ambient environment.
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "t" * 48}):
            self.assertIsNotNone(self.service.issue_password_reset_token("pw@example.com"))

    def test_setting_a_password_unlocks_password_login(self):
        account = self.service.link_or_create_oauth_account(
            email="upgrade@example.com", display_name="U", provider="github"
        )
        self.service.set_password_for_provider_account(account.user_id, "BrandNewPass1!")
        signed_in = self.service.authenticate(
            email="upgrade@example.com", password="BrandNewPass1!"
        )
        self.assertEqual(signed_in.user_id, account.user_id)
        self.assertTrue(signed_in.has_password)

    def test_short_password_rejected_when_setting(self):
        account = self.service.link_or_create_oauth_account(
            email="short@example.com", display_name="S", provider="github"
        )
        with self.assertRaises(ValueError):
            self.service.set_password_for_provider_account(account.user_id, "abc")


if __name__ == "__main__":
    unittest.main()
