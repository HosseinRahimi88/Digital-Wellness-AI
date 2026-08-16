"""
Tests: utils/tokens.py (JWT access tokens) and
AccountService.issue_access_token / resolve_access_token.

These exercise the REAL PyJWT library (not a stub) - the sandbox this
was authored in has PyJWT genuinely installed. Only pwdlib (used by
AccountService's account creation, unrelated to tokens themselves) is
stubbed offline - see tests/_test_support.py.

Run: python3 -m unittest tests.test_tokens -v
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import tests._test_support as ts  # noqa: F401

from utils.tokens import (
    create_access_token,
    decode_access_token,
    get_jwt_secret,
    JWTConfigurationError,
    TokenValidationError,
)

TEST_SECRET = "x" * 40  # >=32 chars, satisfies get_jwt_secret's length check


class TestGetJwtSecret(unittest.TestCase):

    def test_missing_secret_raises_configuration_error(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("JWT_SECRET_KEY", None)
            with self.assertRaises(JWTConfigurationError):
                get_jwt_secret()

    def test_short_secret_raises_configuration_error(self):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "tooshort"}):
            with self.assertRaises(JWTConfigurationError):
                get_jwt_secret()

    def test_valid_secret_is_returned(self):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": TEST_SECRET}):
            self.assertEqual(get_jwt_secret(), TEST_SECRET)


class TestCreateAndDecodeAccessToken(unittest.TestCase):

    def test_round_trip_returns_the_same_subject(self):
        token = create_access_token(subject="user-123", secret_key=TEST_SECRET)
        payload = decode_access_token(token=token, secret_key=TEST_SECRET)
        self.assertEqual(payload["sub"], "user-123")

    def test_token_carries_required_claims(self):
        token = create_access_token(subject="user-123", secret_key=TEST_SECRET)
        payload = decode_access_token(token=token, secret_key=TEST_SECRET)
        for claim in ("sub", "iat", "exp", "jti", "type", "iss"):
            self.assertIn(claim, payload)
        self.assertEqual(payload["type"], "access")

    def test_wrong_secret_is_rejected(self):
        token = create_access_token(subject="user-123", secret_key=TEST_SECRET)
        with self.assertRaises(TokenValidationError):
            decode_access_token(token=token, secret_key="y" * 40)

    def test_expired_token_is_rejected(self):
        token = create_access_token(
            subject="user-123",
            secret_key=TEST_SECRET,
            expires_delta=timedelta(seconds=-1),
        )
        with self.assertRaises(TokenValidationError):
            decode_access_token(token=token, secret_key=TEST_SECRET)

    def test_empty_token_is_rejected(self):
        with self.assertRaises(TokenValidationError):
            decode_access_token(token="", secret_key=TEST_SECRET)

    def test_garbage_token_is_rejected_not_crashed(self):
        with self.assertRaises(TokenValidationError):
            decode_access_token(token="not.a.real.token", secret_key=TEST_SECRET)

    def test_wrong_issuer_is_rejected(self):
        token = create_access_token(subject="user-123", secret_key=TEST_SECRET, issuer="someone-else")
        with self.assertRaises(TokenValidationError):
            decode_access_token(token=token, secret_key=TEST_SECRET)  # default issuer expected

    def test_two_tokens_for_the_same_subject_have_different_jti(self):
        token_a = create_access_token(subject="user-123", secret_key=TEST_SECRET)
        token_b = create_access_token(subject="user-123", secret_key=TEST_SECRET)
        payload_a = decode_access_token(token=token_a, secret_key=TEST_SECRET)
        payload_b = decode_access_token(token=token_b, secret_key=TEST_SECRET)
        self.assertNotEqual(payload_a["jti"], payload_b["jti"])


class TestTokenAttackVectors(unittest.TestCase):
    """Real JWT-specific attack scenarios, not just unit-level correctness."""

    def test_alg_none_forged_token_is_rejected(self):
        """Classic 'alg: none' attack: an attacker crafts an unsigned
        token and hopes the verifier accepts it without checking a
        signature. jwt.decode's explicit `algorithms=[...]` allowlist
        must prevent this."""
        import jwt as pyjwt
        forged = pyjwt.encode(
            {"sub": "attacker", "iat": 9999999999, "exp": 9999999999,
             "jti": "forged", "type": "access", "iss": "digital-wellness-ai"},
            key="", algorithm="none",
        )
        with self.assertRaises(TokenValidationError):
            decode_access_token(token=forged, secret_key=TEST_SECRET)

    def test_token_signed_with_wrong_secret_is_rejected(self):
        import jwt as pyjwt
        forged = pyjwt.encode(
            {"sub": "attacker", "iat": 9999999999, "exp": 9999999999,
             "jti": "forged", "type": "access", "iss": "digital-wellness-ai"},
            key="attacker-guessed-secret", algorithm="HS256",
        )
        with self.assertRaises(TokenValidationError):
            decode_access_token(token=forged, secret_key=TEST_SECRET)

    def test_tampered_payload_is_rejected(self):
        token = create_access_token(subject="real-user", secret_key=TEST_SECRET)
        header, payload, signature = token.split(".")
        tampered_payload = payload[:-1] + ("A" if payload[-1] != "A" else "B")
        tampered_token = ".".join([header, tampered_payload, signature])
        with self.assertRaises(TokenValidationError):
            decode_access_token(token=tampered_token, secret_key=TEST_SECRET)

    def test_token_missing_a_required_claim_is_rejected(self):
        import jwt as pyjwt
        incomplete = pyjwt.encode(
            {"sub": "user", "iat": 9999999999, "exp": 9999999999,
             "jti": "x", "type": "access"},  # no "iss"
            key=TEST_SECRET, algorithm="HS256",
        )
        with self.assertRaises(TokenValidationError):
            decode_access_token(token=incomplete, secret_key=TEST_SECRET)


class TestAccountServiceTokenIntegration(unittest.TestCase):

    def setUp(self):
        self._env_patch = patch.dict(os.environ, {"JWT_SECRET_KEY": TEST_SECRET})
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

        from services.storage.json_file_storage import JSONFileStorageBackend
        from services.account_service import AccountService

        tmp_dir = Path(tempfile.mkdtemp())
        self.service = AccountService(backend=JSONFileStorageBackend(tmp_dir / "accounts.json"))
        self.account = self.service.register(
            email="tok@example.com", password="hunter22", display_name="Tok"
        )

    def test_issued_token_resolves_back_to_the_same_account(self):
        token = self.service.issue_access_token(self.account)
        resolved = self.service.resolve_access_token(token)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.user_id, self.account.user_id)

    def test_garbage_token_resolves_to_none_not_an_exception(self):
        self.assertIsNone(self.service.resolve_access_token("garbage.not.a.token"))

    def test_token_for_a_deleted_account_resolves_to_none(self):
        token = self.service.issue_access_token(self.account)
        # Simulate the account no longer existing (e.g. deleted).
        with self.service._backend.transaction() as records:
            self.service._backend.commit([])
        self.assertIsNone(self.service.resolve_access_token(token))


if __name__ == "__main__":
    unittest.main()
