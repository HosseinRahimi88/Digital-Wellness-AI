"""
Tests: services.league_service - the Friends League two-sided consent
model. Every test exercises the real service (a temp-file-backed
JSONFileStorageBackend), never a mock of the consent logic itself,
since the whole point of this feature is that the logic is trustworthy.

Run: python3 -m unittest tests.test_league_service -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests._test_support  # noqa: F401

from services.league_service import (
    AlreadyConnectedError,
    ConnectionNotFoundError,
    InvalidInviteCodeError,
    LeagueService,
    RulesNotAcceptedError,
)
from services.storage.json_file_storage import JSONFileStorageBackend


def _make_service() -> LeagueService:
    tmp = Path(tempfile.mkdtemp())
    return LeagueService(backend=JSONFileStorageBackend(tmp / "league.json"))


class TestProfilesAndRules(unittest.TestCase):

    def test_profile_is_created_on_first_touch_with_no_rules_accepted(self):
        svc = _make_service()
        profile = svc.get_or_create_profile("u1")
        self.assertFalse(profile.rules_accepted)
        self.assertTrue(profile.invite_code)

    def test_invite_code_is_stable_across_calls(self):
        svc = _make_service()
        first = svc.get_or_create_profile("u1").invite_code
        second = svc.get_or_create_profile("u1").invite_code
        self.assertEqual(first, second)

    def test_accept_rules_persists(self):
        svc = _make_service()
        svc.get_or_create_profile("u1")
        svc.accept_rules("u1")
        self.assertTrue(svc.get_or_create_profile("u1").rules_accepted)

    def test_cannot_send_request_before_accepting_rules(self):
        svc = _make_service()
        svc.get_or_create_profile("u1")
        svc.get_or_create_profile("u2")
        with self.assertRaises(RulesNotAcceptedError):
            svc.redeem_invite("u1", "Alice", svc.get_or_create_profile("u2").invite_code, ["score"])


class TestConnectionFlow(unittest.TestCase):

    def _two_users_with_rules_accepted(self, svc: LeagueService):
        svc.accept_rules("alice")
        svc.accept_rules("bob")
        return svc.get_or_create_profile("bob").invite_code

    def test_nothing_visible_until_target_approves(self):
        svc = _make_service()
        bob_code = self._two_users_with_rules_accepted(svc)
        conn = svc.redeem_invite("alice", "Alice", bob_code, ["score", "persona"])
        self.assertEqual(conn.status, "pending")
        # Neither side has any visible category yet - approval hasn't happened.
        self.assertEqual(conn.visible_to("alice"), [])
        self.assertEqual(conn.visible_to("bob"), ["score", "persona"])

    def test_invalid_invite_code_is_rejected(self):
        svc = _make_service()
        svc.accept_rules("alice")
        with self.assertRaises(InvalidInviteCodeError):
            svc.redeem_invite("alice", "Alice", "NOTAREALCODE", ["score"])

    def test_cannot_connect_to_self(self):
        svc = _make_service()
        code = self._two_users_with_rules_accepted(svc)
        # bob's own code, redeemed by bob
        from services.league_service import LeagueError
        with self.assertRaises(LeagueError):
            svc.redeem_invite("bob", "Bob", code, ["score"])

    def test_duplicate_pending_request_is_rejected(self):
        svc = _make_service()
        bob_code = self._two_users_with_rules_accepted(svc)
        svc.redeem_invite("alice", "Alice", bob_code, ["score"])
        with self.assertRaises(AlreadyConnectedError):
            svc.redeem_invite("alice", "Alice", bob_code, ["persona"])

    def test_approval_makes_data_mutually_visible_only_for_ticked_categories(self):
        svc = _make_service()
        bob_code = self._two_users_with_rules_accepted(svc)
        conn = svc.redeem_invite("alice", "Alice", bob_code, ["score", "persona"])
        approved = svc.respond_to_request("bob", conn.connection_id, True, ["score"])
        self.assertEqual(approved.status, "accepted")
        # Alice sees only what Bob shared (score), not persona (Bob didn't tick it).
        self.assertEqual(approved.visible_to("alice"), ["score"])
        # Bob sees everything Alice originally offered.
        self.assertEqual(approved.visible_to("bob"), ["score", "persona"])

    def test_decline_shares_nothing_and_leaves_no_accepted_connection(self):
        svc = _make_service()
        bob_code = self._two_users_with_rules_accepted(svc)
        conn = svc.redeem_invite("alice", "Alice", bob_code, ["score"])
        declined = svc.respond_to_request("bob", conn.connection_id, False, [])
        self.assertEqual(declined.status, "declined")
        self.assertEqual(svc.connections_for("alice"), [])
        self.assertEqual(svc.connections_for("bob"), [])

    def test_approving_requires_target_to_have_accepted_rules(self):
        svc = _make_service()
        svc.accept_rules("alice")
        svc.get_or_create_profile("bob")  # bob has NOT accepted rules
        bob_code = svc.get_or_create_profile("bob").invite_code
        conn = svc.redeem_invite("alice", "Alice", bob_code, ["score"])
        with self.assertRaises(RulesNotAcceptedError):
            svc.respond_to_request("bob", conn.connection_id, True, ["score"])

    def test_stranger_cannot_respond_to_someone_elses_request(self):
        svc = _make_service()
        bob_code = self._two_users_with_rules_accepted(svc)
        svc.accept_rules("carol")
        conn = svc.redeem_invite("alice", "Alice", bob_code, ["score"])
        with self.assertRaises(ConnectionNotFoundError):
            svc.respond_to_request("carol", conn.connection_id, True, ["score"])


class TestOngoingControl(unittest.TestCase):

    def _accepted_connection(self, svc: LeagueService):
        svc.accept_rules("alice")
        svc.accept_rules("bob")
        bob_code = svc.get_or_create_profile("bob").invite_code
        conn = svc.redeem_invite("alice", "Alice", bob_code, ["score", "persona"])
        return svc.respond_to_request("bob", conn.connection_id, True, ["score"])

    def test_either_side_can_change_their_own_sharing_only(self):
        svc = _make_service()
        conn = self._accepted_connection(svc)
        updated = svc.update_sharing("alice", conn.connection_id, ["plan_focus"])
        self.assertEqual(updated.requester_shared, ["plan_focus"])
        # Bob's side is untouched by Alice's change.
        self.assertEqual(updated.target_shared, ["score"])

    def test_unknown_category_is_rejected(self):
        svc = _make_service()
        conn = self._accepted_connection(svc)
        with self.assertRaises(ValueError):
            svc.update_sharing("alice", conn.connection_id, ["raw_stress_score"])

    def test_revoke_removes_the_connection_for_both_sides(self):
        svc = _make_service()
        conn = self._accepted_connection(svc)
        svc.revoke("bob", conn.connection_id)
        self.assertEqual(svc.connections_for("alice"), [])
        self.assertEqual(svc.connections_for("bob"), [])

    def test_pending_requests_only_show_up_for_the_target(self):
        svc = _make_service()
        svc.accept_rules("alice")
        svc.accept_rules("bob")
        bob_code = svc.get_or_create_profile("bob").invite_code
        svc.redeem_invite("alice", "Alice", bob_code, ["score"])
        self.assertEqual(len(svc.pending_requests_for("bob")), 1)
        self.assertEqual(len(svc.pending_requests_for("alice")), 0)


if __name__ == "__main__":
    unittest.main()
