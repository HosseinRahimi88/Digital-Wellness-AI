"""
Tests: AccountService (register / authenticate / lookup) and the
security properties ported from the Parisa project's auth flow.

Run: python3 -m unittest tests.test_account_service -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - installs offline pwdlib/shap stubs

from services.account_service import (
    AccountService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InactiveAccountError,
)
from services.storage.json_file_storage import JSONFileStorageBackend
from utils.security import hash_password, verify_password


def _make_service() -> AccountService:
    tmp_dir = Path(tempfile.mkdtemp())
    backend = JSONFileStorageBackend(tmp_dir / "accounts.json")
    return AccountService(backend=backend)


class TestPasswordHashing(unittest.TestCase):
    """utils/security.py - the primitives everything else relies on."""

    def test_hash_is_not_plaintext(self):
        self.assertNotEqual(hash_password("hunter22"), "hunter22")

    def test_correct_password_verifies(self):
        h = hash_password("hunter22")
        self.assertTrue(verify_password("hunter22", h))

    def test_wrong_password_does_not_verify(self):
        h = hash_password("hunter22")
        self.assertFalse(verify_password("wrong-password", h))

    def test_empty_password_rejected_at_hash_time(self):
        with self.assertRaises(ValueError):
            hash_password("")

    def test_verify_never_raises_on_malformed_hash(self):
        # A corrupted/garbage stored hash must fail closed, not crash login.
        self.assertFalse(verify_password("hunter22", "not-a-real-hash"))
        self.assertFalse(verify_password("hunter22", ""))


class TestAccountRegistration(unittest.TestCase):

    def setUp(self):
        self.service = _make_service()

    def test_register_returns_account_with_hashed_password(self):
        account = self.service.register(
            email="Test@Example.com", password="hunter22", display_name="Test User"
        )
        self.assertEqual(account.email, "test@example.com")  # normalized
        self.assertNotEqual(account.password_hash, "hunter22")
        self.assertFalse(account.onboarding_complete)

    def test_duplicate_email_is_rejected(self):
        self.service.register(email="a@example.com", password="hunter22", display_name="A")
        with self.assertRaises(EmailAlreadyRegisteredError):
            self.service.register(email="A@Example.com", password="different1", display_name="A2")

    def test_blank_display_name_falls_back_to_email_local_part(self):
        account = self.service.register(email="nobody@example.com", password="hunter22", display_name="  ")
        self.assertEqual(account.display_name, "nobody")


class TestAccountAuthentication(unittest.TestCase):

    def setUp(self):
        self.service = _make_service()
        self.account = self.service.register(
            email="user@example.com", password="hunter22", display_name="User"
        )

    def test_correct_credentials_authenticate(self):
        result = self.service.authenticate(email="user@example.com", password="hunter22")
        self.assertEqual(result.user_id, self.account.user_id)

    def test_wrong_password_is_rejected(self):
        with self.assertRaises(InvalidCredentialsError):
            self.service.authenticate(email="user@example.com", password="wrong-password")

    def test_unknown_email_is_rejected_not_crashed(self):
        # Also exercises the timing-protection dummy-verify path without
        # raising anything other than InvalidCredentialsError.
        with self.assertRaises(InvalidCredentialsError):
            self.service.authenticate(email="nobody@example.com", password="hunter22")

    def test_email_lookup_is_case_and_whitespace_insensitive(self):
        result = self.service.authenticate(email="  User@Example.com  ", password="hunter22")
        self.assertEqual(result.user_id, self.account.user_id)

    def test_inactive_account_is_rejected(self):
        with self.service._backend.transaction() as records:
            for r in records:
                r["is_active"] = False
            self.service._backend.commit(records)
        with self.assertRaises(InactiveAccountError):
            self.service.authenticate(email="user@example.com", password="hunter22")


class TestAccountLookupAndOnboarding(unittest.TestCase):

    def setUp(self):
        self.service = _make_service()
        self.account = self.service.register(
            email="user@example.com", password="hunter22", display_name="User"
        )

    def test_get_by_id_roundtrips(self):
        found = self.service.get_by_id(self.account.user_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.email, "user@example.com")

    def test_get_by_id_unknown_returns_none(self):
        self.assertIsNone(self.service.get_by_id("does-not-exist"))

    def test_mark_onboarding_complete_persists(self):
        self.service.mark_onboarding_complete(self.account.user_id)
        found = self.service.get_by_id(self.account.user_id)
        self.assertTrue(found.onboarding_complete)


class TestOnboardingProfilePersistence(unittest.TestCase):
    """AccountService.save_onboarding_profile - the piece Onboarding.py
    calls for logged-in users (see app/pages/Onboarding.py)."""

    def setUp(self):
        self.service = _make_service()
        self.account = self.service.register(
            email="user@example.com", password="hunter22", display_name="User"
        )

    def test_save_onboarding_profile_persists_and_completes_onboarding(self):
        updated = self.service.save_onboarding_profile(
            self.account.user_id,
            primary_goal="better_sleep",
            main_use_purpose="work_career",
            schedule_type="standard_day",
            usual_sleep_time="23:00",
            usual_wake_time="07:00",
            preferred_effort="low",
            work_screen_required=True,
        )
        self.assertIsNotNone(updated)
        self.assertTrue(updated.onboarding_complete)
        self.assertEqual(updated.primary_goal, "better_sleep")

        reloaded = self.service.get_by_id(self.account.user_id)
        self.assertEqual(reloaded.usual_wake_time, "07:00")
        self.assertTrue(reloaded.work_screen_required)

    def test_save_onboarding_profile_for_unknown_user_returns_none(self):
        result = self.service.save_onboarding_profile(
            "does-not-exist",
            primary_goal="better_sleep",
            main_use_purpose="work_career",
            schedule_type="standard_day",
            usual_sleep_time="23:00",
            usual_wake_time="07:00",
            preferred_effort="low",
            work_screen_required=False,
        )
        self.assertIsNone(result)

    def test_account_without_profile_yet_has_none_defaults(self):
        # Regression guard: accounts created before onboarding must not
        # break because the new dataclass fields are missing on read.
        self.assertIsNone(self.account.primary_goal)
        self.assertFalse(self.account.work_screen_required)


class TestAccountRecordHardening(unittest.TestCase):
    """Bug fix: a stored record with an unknown/legacy key must not
    crash Account reconstruction (previously a blind Account(**record)
    would raise TypeError)."""

    def test_unknown_key_in_stored_record_does_not_crash_lookup(self):
        service = _make_service()
        account = service.register(email="x@example.com", password="hunter22", display_name="X")

        with service._backend.transaction() as records:
            for r in records:
                r["some_field_that_no_longer_exists"] = "legacy value"
            service._backend.commit(records)

        found = service.get_by_id(account.user_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.email, "x@example.com")


if __name__ == "__main__":
    unittest.main()
