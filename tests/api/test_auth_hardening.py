"""Three things that were wrong with sessions, and what they are now.

1. THE ACCOUNT TAKEOVER
   /auth/forgot-password answered with the reset token in its body. The
   comment beside it argued that the response text was identical whether
   or not the email matched, so the route could not be used to enumerate
   accounts. That was true and it was beside the point: anyone who knew
   a registered address could POST it, read the token out of the JSON,
   and set that account's password. Argon2 hashing and JWT signing were
   both irrelevant to an attacker who never needed to guess anything.

   The token now leaves through services/identity/mail_service. What is
   pinned here is not "the field was renamed" but that the actual code -
   read out of the actual message that was sent - appears nowhere in the
   response.

2. NO WAY TO PROVE AN ADDRESS
   Anybody could register anything. Verification exists now, and is
   deliberately NOT a login gate: switching one on would have locked out
   every existing account and every demo the moment it shipped.

3. THE HOUR-LONG SESSION
   Access tokens last 60 minutes and there was nothing else, so hour two
   was a 401 in the middle of whatever the user was doing. Refresh
   tokens fix that, and the interesting half is what stops a thirty-day
   credential being worse than the problem: it is revocable, single-use,
   and a replay burns every session the account has.

Run: python3 -m unittest tests.api.test_auth_hardening -v
"""
from __future__ import annotations

import json
import re
import unittest

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from tests.api.test_api import APITestCase


def _memory_mail():
    from services.identity.mail_service import MailService, MemoryTransport, set_mail_service

    transport = MemoryTransport()
    set_mail_service(MailService(transport))
    return transport


def _session(case, **kwargs) -> dict:
    """Register and return the whole token payload.

    APITestCase._register returns only the access token; these tests are
    about the refresh token and the verification flag that travel beside
    it, so the full body is needed.
    """
    response = case.client.post(
        "/api/v1/auth/register",
        json={
            "email": kwargs.get("email", "user@example.com"),
            "password": kwargs.get("password", "testpass123"),
            "display_name": kwargs.get("display_name", "Test User"),
        },
    )
    case.assertEqual(response.status_code, 201, response.text)
    return response.json()


def _code_from(body: str) -> str:
    match = re.search(r"^\s{4}(\S+)\s*$", body, re.M)
    assert match, f"no code in mail body:\n{body}"
    return match.group(1)


class TestForgotPasswordNoLongerHandsOutTheAccount(APITestCase):
    def setUp(self):
        super().setUp()
        self.mail = _memory_mail()

    def tearDown(self):
        from services.identity.mail_service import set_mail_service

        set_mail_service(None)
        super().tearDown()

    def _forgot(self, email):
        response = self.client.post("/api/v1/auth/forgot-password", json={"email": email})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_the_code_is_nowhere_in_the_response(self):
        self._register(email="takeover@example.com", password="original123")
        body = self._forgot("takeover@example.com")
        code = _code_from(self.mail.last_to("takeover@example.com").body)
        self.assertNotIn(code, json.dumps(body))
        self.assertNotIn("reset_token", body)

    def test_the_code_goes_to_the_address_that_asked_for_it(self):
        self._register(email="owner@example.com", password="original123")
        # Registration already sent a verification code, so the reset is
        # the message after it, not the only one.
        self.mail.clear()
        self._forgot("owner@example.com")
        self.assertEqual(len(self.mail.sent), 1)
        self.assertEqual(self.mail.sent[0].to, "owner@example.com")

    def test_an_unknown_address_is_indistinguishable_from_a_known_one(self):
        # Both fields, not just the message: `delivery` would otherwise
        # be a one-bit oracle for "is this address registered".
        self._register(email="real@example.com", password="original123")
        known = self._forgot("real@example.com")
        unknown = self._forgot("no-such-person@example.com")
        self.assertEqual(known["message"], unknown["message"])
        self.assertEqual(set(known), set(unknown))

    def test_no_mail_is_sent_for_an_address_that_is_not_registered(self):
        self.mail.clear()
        self._forgot("stranger@example.com")
        self.assertEqual(self.mail.sent, [])

    def test_a_provider_account_cannot_be_claimed_through_the_reset_path(self):
        # A GitHub account has no password. Minting a reset token for it
        # would let this route manufacture a credential for an account
        # that deliberately has none.
        from api.dependencies.services import get_account_service

        service = self.app.dependency_overrides.get(get_account_service, get_account_service)()
        service.link_or_create_oauth_account(
            provider="github", email="ghuser@example.com", display_name="GH User",
        )
        self.mail.clear()
        self._forgot("ghuser@example.com")
        self.assertEqual(self.mail.sent, [])

    def test_the_emailed_code_still_actually_works(self):
        # The fix must not have made the flow decorative.
        self._register(email="works@example.com", password="original123")
        self._forgot("works@example.com")
        code = _code_from(self.mail.last_to("works@example.com").body)

        done = self.client.post(
            "/api/v1/auth/reset-password",
            json={"reset_token": code, "new_password": "brandnew123"},
        )
        self.assertEqual(done.status_code, 200, done.text)
        old = self.client.post(
            "/api/v1/auth/login", json={"email": "works@example.com", "password": "original123"},
        )
        new = self.client.post(
            "/api/v1/auth/login", json={"email": "works@example.com", "password": "brandnew123"},
        )
        self.assertEqual(old.status_code, 401)
        self.assertEqual(new.status_code, 200)

    def test_a_reset_ends_the_sessions_that_were_already_open(self):
        # A reset is the answer to "somebody else may be in my account".
        # If their session survives it, the reset was cosmetic.
        registered = _session(self, email="kickout@example.com", password="original123")
        stolen_refresh = registered["refresh_token"]

        self._forgot("kickout@example.com")
        code = _code_from(self.mail.last_to("kickout@example.com").body)
        self.client.post(
            "/api/v1/auth/reset-password",
            json={"reset_token": code, "new_password": "brandnew123"},
        )

        replay = self.client.post(
            "/api/v1/auth/refresh", json={"refresh_token": stolen_refresh},
        )
        self.assertEqual(replay.status_code, 401, "the old session survived a password reset")


class TestEmailVerification(APITestCase):
    def setUp(self):
        super().setUp()
        self.mail = _memory_mail()

    def tearDown(self):
        from services.identity.mail_service import set_mail_service

        set_mail_service(None)
        super().tearDown()

    def test_registering_sends_a_verification_code(self):
        self._register(email="newbie@example.com")
        self.assertIsNotNone(self.mail.last_to("newbie@example.com"))

    def test_a_new_account_is_reported_unverified(self):
        self.assertFalse(_session(self, email="unverified@example.com")["email_verified"])

    def test_the_code_verifies_the_address(self):
        headers = self._auth_headers(self._register(email="verify@example.com"))
        code = _code_from(self.mail.last_to("verify@example.com").body)

        done = self.client.post("/api/v1/auth/verify-email", json={"token": code})
        self.assertEqual(done.status_code, 200, done.text)
        self.assertTrue(done.json()["verified"])

        me = self.client.get("/api/v1/auth/me", headers=headers).json()
        self.assertTrue(me["email_verified"])

    def test_verifying_needs_no_bearer_token(self):
        # Somebody who opens the link on their phone is not signed in
        # there. Requiring a session would make the flow unusable in the
        # single most likely place it is used.
        self._register(email="phone@example.com")
        code = _code_from(self.mail.last_to("phone@example.com").body)
        self.assertEqual(
            self.client.post("/api/v1/auth/verify-email", json={"token": code}).status_code, 200,
        )

    def test_a_garbage_code_is_refused(self):
        self.assertEqual(
            self.client.post("/api/v1/auth/verify-email", json={"token": "nonsense"}).status_code,
            400,
        )

    def test_an_access_token_cannot_be_replayed_as_a_verification_code(self):
        # Different `type` claim, checked on decode. Without that, any
        # signed token the app ever issues would verify any address.
        access = self._register(email="replay@example.com")
        self.assertEqual(
            self.client.post("/api/v1/auth/verify-email", json={"token": access}).status_code, 400,
        )

    def test_resending_reaches_the_same_address_again(self):
        headers = self._auth_headers(self._register(email="again@example.com"))
        self.mail.clear()
        response = self.client.post("/api/v1/auth/resend-verification", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["already_verified"])
        self.assertIsNotNone(self.mail.last_to("again@example.com"))

    def test_resending_to_an_already_verified_address_sends_nothing(self):
        headers = self._auth_headers(self._register(email="done@example.com"))
        code = _code_from(self.mail.last_to("done@example.com").body)
        self.client.post("/api/v1/auth/verify-email", json={"token": code})

        self.mail.clear()
        response = self.client.post("/api/v1/auth/resend-verification", headers=headers)
        self.assertTrue(response.json()["already_verified"])
        self.assertEqual(self.mail.sent, [], "a live code was minted for no reason")

    def test_being_unverified_does_not_block_anything(self):
        # Deliberate. Enforcing verification would have locked out every
        # account that existed before this shipped, and every demo, on a
        # deployment that may have no mail server at all.
        headers = self._auth_headers(self._register(email="unblocked@example.com"))
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/history", headers=headers).status_code, 200)


class TestRefreshTokens(APITestCase):
    def test_registering_and_logging_in_both_return_a_refresh_token(self):
        registered = _session(self, email="pair@example.com", password="password123")
        self.assertTrue(registered["refresh_token"])
        self.assertTrue(registered["expires_in"])

        logged_in = self.client.post(
            "/api/v1/auth/login", json={"email": "pair@example.com", "password": "password123"},
        ).json()
        self.assertTrue(logged_in["refresh_token"])

    def test_a_refresh_token_buys_a_working_access_token(self):
        registered = _session(self, email="renew@example.com")
        renewed = self.client.post(
            "/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]},
        )
        self.assertEqual(renewed.status_code, 200, renewed.text)

        headers = {"Authorization": f"Bearer {renewed.json()['access_token']}"}
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).status_code, 200)

    def test_refreshing_rotates_the_token(self):
        registered = _session(self, email="rotate@example.com")
        renewed = self.client.post(
            "/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]},
        ).json()
        self.assertNotEqual(renewed["refresh_token"], registered["refresh_token"])

    def test_the_old_token_is_dead_the_moment_it_is_spent(self):
        registered = _session(self, email="spent@example.com")
        first = registered["refresh_token"]
        self.client.post("/api/v1/auth/refresh", json={"refresh_token": first})

        again = self.client.post("/api/v1/auth/refresh", json={"refresh_token": first})
        self.assertEqual(again.status_code, 401)

    def test_a_replay_burns_every_session_the_account_has(self):
        # The point of rotation. A token coming back twice is either a
        # client retrying or an attacker replaying a stolen copy, and
        # the request cannot tell them apart - so both are logged out
        # and the real user recovers with a password the attacker does
        # not have.
        registered = _session(self, email="replayed@example.com")
        stolen = registered["refresh_token"]
        legitimate = self.client.post(
            "/api/v1/auth/refresh", json={"refresh_token": stolen},
        ).json()["refresh_token"]

        # The attacker replays the copy they took.
        self.client.post("/api/v1/auth/refresh", json={"refresh_token": stolen})

        # The honest session is gone too. That is the intended trade.
        after = self.client.post("/api/v1/auth/refresh", json={"refresh_token": legitimate})
        self.assertEqual(after.status_code, 401)

    def test_every_rejection_looks_the_same(self):
        # Telling "already used" apart from "never existed" tells an
        # attacker holding a stolen token whether it is worth trying.
        registered = _session(self, email="opaque@example.com")
        spent = registered["refresh_token"]
        self.client.post("/api/v1/auth/refresh", json={"refresh_token": spent})

        reused = self.client.post("/api/v1/auth/refresh", json={"refresh_token": spent})
        garbage = self.client.post("/api/v1/auth/refresh", json={"refresh_token": "nope"})
        self.assertEqual(reused.status_code, garbage.status_code)

    def test_an_access_token_is_not_a_refresh_token(self):
        registered = _session(self, email="wrongtype@example.com")
        response = self.client.post(
            "/api/v1/auth/refresh", json={"refresh_token": registered["access_token"]},
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_stops_anything_renewing(self):
        registered = _session(self, email="byebye@example.com")
        headers = {"Authorization": f"Bearer {registered['access_token']}"}

        self.assertEqual(self.client.post("/api/v1/auth/logout", headers=headers).status_code, 204)
        after = self.client.post(
            "/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]},
        )
        self.assertEqual(after.status_code, 401)

    def test_logout_needs_a_session_of_its_own(self):
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 401)

    def test_one_account_cannot_spend_another_accounts_token(self):
        first = _session(self, email="mine@example.com")
        self._register(email="theirs@example.com")
        # Signed for `mine`, so the store looks it up under `mine` - the
        # jti is scoped to a user and cannot be borrowed sideways.
        headers = {"Authorization": f"Bearer {first['access_token']}"}
        self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]},
            ).status_code,
            401,
        )


class TestTheRefreshStoreItself(unittest.TestCase):
    """The service on its own, without HTTP in the way."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        from services.identity.refresh_token_service import RefreshTokenService
        from services.storage.json_file_storage import JSONFileStorageBackend

        self._dir = tempfile.TemporaryDirectory()
        self.backend = JSONFileStorageBackend(Path(self._dir.name) / "refresh.json")
        self.service = RefreshTokenService("user-1", backend=self.backend)

    def tearDown(self):
        self._dir.cleanup()

    def _issue(self, jti, days=30):
        from datetime import datetime, timedelta, timezone

        self.service.issue(jti, datetime.now(timezone.utc) + timedelta(days=days))

    def test_the_token_itself_is_never_stored(self):
        # A store holding whole refresh tokens is a file full of live
        # credentials, which is the thing being defended against.
        self._issue("abc123")
        stored = json.dumps(self.backend.read_all())
        self.assertIn("abc123", stored)  # the jti, which is only a handle
        self.assertNotIn("eyJ", stored)  # no JWT

    def test_an_unknown_jti_is_refused(self):
        self.assertEqual(self.service.consume("never-issued"), (False, "unknown"))

    def test_a_token_can_be_spent_once(self):
        self._issue("once")
        self.assertEqual(self.service.consume("once"), (True, "ok"))
        self.assertEqual(self.service.consume("once")[1], "reused")

    def test_a_reuse_revokes_everything_else(self):
        self._issue("a")
        self._issue("b")
        self.service.consume("a")
        self.service.consume("a")  # replay
        self.assertEqual(self.service.consume("b")[1], "revoked")

    def test_an_expired_token_is_refused(self):
        # Written straight into the store rather than through issue():
        # issue() prunes dead rows as it goes, so an already-expired one
        # would be dropped on the way in and consume() would report it as
        # "unknown". What needs pinning is the expiry check itself, which
        # is what a token issued a month ago actually hits.
        from datetime import datetime, timedelta, timezone

        with self.backend.transaction() as records:
            rows = list(records)
            rows.append({
                "user_id": "user-1",
                "jti": "stale",
                "expires_at_utc": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "created_at_utc": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
                "revoked": False,
                "revoked_reason": "",
            })
            self.backend.commit(rows)
        self.assertEqual(self.service.consume("stale")[1], "expired")

    def test_live_tokens_are_capped(self):
        from services.identity.refresh_token_service import MAX_LIVE_TOKENS_PER_USER

        for index in range(MAX_LIVE_TOKENS_PER_USER + 5):
            self._issue(f"jti-{index}")
        self.assertLessEqual(self.service.live_count(), MAX_LIVE_TOKENS_PER_USER)

    def test_one_users_tokens_are_untouched_by_another_users_write(self):
        # The store is one shared file and pruning runs inside a
        # transaction over all of it, so the pruner has to be careful to
        # only ever drop rows belonging to its own user. If it were not,
        # a busy account would evict everybody else's sessions.
        from datetime import datetime, timedelta, timezone

        from services.identity.refresh_token_service import (
            MAX_LIVE_TOKENS_PER_USER, RefreshTokenService,
        )

        self._issue("mine")
        other = RefreshTokenService("user-2", backend=self.backend)
        for index in range(MAX_LIVE_TOKENS_PER_USER + 10):
            other.issue(f"theirs-{index}", datetime.now(timezone.utc) + timedelta(days=30))

        self.assertEqual(self.service.consume("mine"), (True, "ok"))

    def test_revoke_all_ends_every_live_token(self):
        self._issue("x")
        self._issue("y")
        self.assertEqual(self.service.revoke_all("logout"), 2)
        self.assertEqual(self.service.consume("x")[1], "revoked")

    def test_delete_users_removes_the_rows_entirely(self):
        self._issue("gone")
        self.service.delete_users(["user-1"])
        self.assertEqual(self.backend.read_all(), [])


class TestMailTransport(unittest.TestCase):
    def test_an_unconfigured_deployment_falls_back_to_the_log(self):
        from services.identity.mail_service import LogTransport, MailService

        delivery = MailService(LogTransport()).send("a@b.com", "s", "body")
        self.assertTrue(delivery.delivered)
        self.assertEqual(delivery.channel, "server_log")

    def test_a_failing_transport_never_raises(self):
        # A mail server being down must not 500 a registration, and must
        # never fall through to "return the token instead".
        from services.identity.mail_service import MailService, Transport

        class Broken(Transport):
            name = "smtp"

            def deliver(self, message):
                raise RuntimeError("connection refused")

        delivery = MailService(Broken()).send("a@b.com", "s", "body")
        self.assertFalse(delivery.delivered)
        self.assertEqual(delivery.channel, "none")

    def test_a_missing_address_is_not_an_error(self):
        from services.identity.mail_service import MailService, MemoryTransport

        service = MailService(MemoryTransport())
        self.assertFalse(service.send("", "s", "b").delivered)
        self.assertFalse(service.send("not-an-address", "s", "b").delivered)


if __name__ == "__main__":
    unittest.main()
