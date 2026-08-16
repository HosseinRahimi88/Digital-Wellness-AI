"""
Tests: Group C Feature 48 - Family Mode.

Run: python3 -m unittest tests.test_family_service -v
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from services.family_service import (
    FamilyService,
    AlreadyInFamilyError,
    InvalidInviteCodeError,
    NotFamilyOwnerError,
    NotInFamilyError,
)
from services.history_service import HistoryService
from services.storage.json_file_storage import JSONFileStorageBackend


class _FakeResult:
    def __init__(self, score, prediction="Moderate"):
        self.regression_score = score
        self.prediction = prediction
        self.confidence = 0.8
        self.shap_features = []


def _make_services():
    tmp = Path(tempfile.mkdtemp())
    family_backend = JSONFileStorageBackend(tmp / "families.json")
    history_backend = JSONFileStorageBackend(tmp / "history.json")
    return FamilyService(backend=family_backend), history_backend


class TestFamilyCreationAndMembership(unittest.TestCase):

    def test_create_family_adds_owner_as_sharing_member(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        self.assertEqual(len(family.members), 1)
        self.assertEqual(family.members[0].user_id, "owner1")
        self.assertTrue(family.members[0].share_summary)
        self.assertEqual(family.owner_user_id, "owner1")
        self.assertTrue(family.invite_code)

    def test_cannot_create_second_family_while_in_one(self):
        fs, _ = _make_services()
        fs.create_family("owner1", "Alex", "The Smiths")
        with self.assertRaises(AlreadyInFamilyError):
            fs.create_family("owner1", "Alex", "Another Family")

    def test_join_family_with_valid_code(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        updated = fs.join_family(family.invite_code, "child1", "Jamie", share_summary=True)
        self.assertEqual(len(updated.members), 2)
        self.assertIn("child1", [m.user_id for m in updated.members])

    def test_join_requires_explicit_sharing_decision(self):
        """share_summary has no default - must be passed explicitly."""
        import inspect
        sig = inspect.signature(FamilyService.join_family)
        self.assertNotIn("share_summary", {
            name for name, p in sig.parameters.items() if p.default is not inspect.Parameter.empty
        })

    def test_join_respects_opt_out_of_sharing(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        updated = fs.join_family(family.invite_code, "child2", "Sam", share_summary=False)
        member = next(m for m in updated.members if m.user_id == "child2")
        self.assertFalse(member.share_summary)

    def test_join_with_invalid_code_raises(self):
        fs, _ = _make_services()
        fs.create_family("owner1", "Alex", "The Smiths")
        with self.assertRaises(InvalidInviteCodeError):
            fs.join_family("NOTREAL1", "child1", "Jamie", share_summary=True)

    def test_join_is_case_insensitive_on_code(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        updated = fs.join_family(family.invite_code.lower(), "child1", "Jamie", share_summary=True)
        self.assertEqual(len(updated.members), 2)

    def test_cannot_join_second_family_while_in_one(self):
        fs, _ = _make_services()
        family_a = fs.create_family("owner1", "Alex", "Family A")
        family_b = fs.create_family("owner2", "Bri", "Family B")
        fs.join_family(family_a.invite_code, "child1", "Jamie", share_summary=True)
        with self.assertRaises(AlreadyInFamilyError):
            fs.join_family(family_b.invite_code, "child1", "Jamie", share_summary=True)

    def test_get_family_for_user_returns_none_when_not_in_one(self):
        fs, _ = _make_services()
        self.assertIsNone(fs.get_family_for_user("nobody"))


class TestLeavingAndSharingToggle(unittest.TestCase):

    def test_leave_family_removes_member(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        fs.join_family(family.invite_code, "child1", "Jamie", share_summary=True)
        fs.leave_family("child1")
        remaining = fs.get_family_for_user("owner1")
        self.assertEqual([m.user_id for m in remaining.members], ["owner1"])
        self.assertIsNone(fs.get_family_for_user("child1"))

    def test_leaving_the_last_member_deletes_the_family(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        fs.leave_family("owner1")
        self.assertIsNone(fs.get_family_for_user("owner1"))

    def test_ownership_transfers_when_owner_leaves(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        fs.join_family(family.invite_code, "child1", "Jamie", share_summary=True)
        fs.leave_family("owner1")
        remaining = fs.get_family_for_user("child1")
        self.assertEqual(remaining.owner_user_id, "child1")

    def test_set_sharing_toggles_flag(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        fs.set_sharing("owner1", False)
        updated = fs.get_family_for_user("owner1")
        self.assertFalse(updated.members[0].share_summary)
        fs.set_sharing("owner1", True)
        updated = fs.get_family_for_user("owner1")
        self.assertTrue(updated.members[0].share_summary)

    def test_set_sharing_raises_when_not_in_family(self):
        fs, _ = _make_services()
        with self.assertRaises(NotInFamilyError):
            fs.set_sharing("nobody", True)

    def test_only_owner_can_remove_a_member(self):
        fs, _ = _make_services()
        family = fs.create_family("owner1", "Alex", "The Smiths")
        fs.join_family(family.invite_code, "child1", "Jamie", share_summary=True)
        with self.assertRaises(NotFamilyOwnerError):
            fs.remove_member(family.family_id, "child1", "owner1")
        fs.remove_member(family.family_id, "owner1", "child1")
        remaining = fs.get_family_for_user("owner1")
        self.assertEqual([m.user_id for m in remaining.members], ["owner1"])


class TestFamilyDashboardPrivacy(unittest.TestCase):
    """The core privacy contract: only summary fields, only for sharing members."""

    def _populate(self, history_backend, user_id, scores, persona="TestPersona"):
        hs = HistoryService(user_id=user_id, storage=history_backend)
        base = date(2026, 1, 1)
        for i, s in enumerate(scores):
            hs.record(
                {"stress_0_10": 9.9, "sleep_hours": 1.0},  # sensitive raw fields - must never leak out
                _FakeResult(s), persona=persona, on_date=base + timedelta(days=i),
            )
        return hs

    def test_dashboard_includes_sharing_members_scores(self):
        fs, history_backend = _make_services()
        family = fs.create_family("parent1", "Alex", "The Smiths")
        fs.join_family(family.invite_code, "child1", "Jamie", share_summary=True)

        self._populate(history_backend, "parent1", [70, 72, 75])
        self._populate(history_backend, "child1", [50, 55, 60])

        dashboard = fs.family_dashboard(family.family_id, lambda uid: HistoryService(user_id=uid, storage=history_backend))
        by_id = {m.user_id: m for m in dashboard.members}
        self.assertEqual(by_id["parent1"].latest_health_score, 75)
        self.assertEqual(by_id["child1"].latest_health_score, 60)
        self.assertIsNotNone(dashboard.family_average_score)

    def test_dashboard_excludes_scores_for_nonsharing_member(self):
        fs, history_backend = _make_services()
        family = fs.create_family("parent1", "Alex", "The Smiths")
        fs.join_family(family.invite_code, "child2", "Sam", share_summary=False)
        self._populate(history_backend, "child2", [10, 20, 30])

        dashboard = fs.family_dashboard(family.family_id, lambda uid: HistoryService(user_id=uid, storage=history_backend))
        child2 = next(m for m in dashboard.members if m.user_id == "child2")
        self.assertFalse(child2.sharing)
        self.assertIsNone(child2.latest_health_score)
        self.assertIsNone(child2.latest_persona)
        self.assertEqual(child2.days_logged, 0)

    def test_nonsharing_member_excluded_from_family_average(self):
        fs, history_backend = _make_services()
        family = fs.create_family("parent1", "Alex", "The Smiths")
        fs.join_family(family.invite_code, "child2", "Sam", share_summary=False)
        self._populate(history_backend, "parent1", [80])
        self._populate(history_backend, "child2", [10])

        dashboard = fs.family_dashboard(family.family_id, lambda uid: HistoryService(user_id=uid, storage=history_backend))
        # Average should be 80 (only parent1), not (80+10)/2
        self.assertEqual(dashboard.family_average_score, 80.0)

    def test_only_summary_fields_are_exposed_never_raw_habit_data(self):
        """
        MemberSummary must structurally have no way to carry raw fields
        like stress_0_10/sleep_hours through - this test would fail if
        someone later "helpfully" widened the dashboard to include them.
        """
        from dataclasses import fields
        from services.family_service import MemberSummary
        field_names = {f.name for f in fields(MemberSummary)}
        leaky_fields = {"stress_0_10", "sleep_hours", "social_min", "gaming_min", "anxiety_0_27"}
        self.assertEqual(field_names & leaky_fields, set())

    def test_dashboard_handles_member_with_no_history_gracefully(self):
        fs, history_backend = _make_services()
        family = fs.create_family("parent1", "Alex", "The Smiths")
        dashboard = fs.family_dashboard(family.family_id, lambda uid: HistoryService(user_id=uid, storage=history_backend))
        parent = dashboard.members[0]
        self.assertIsNone(parent.latest_health_score)
        self.assertEqual(parent.days_logged, 0)

    def test_dashboard_never_raises_when_history_factory_errors(self):
        fs, history_backend = _make_services()
        family = fs.create_family("parent1", "Alex", "The Smiths")

        def broken_factory(user_id):
            raise RuntimeError("simulated storage failure")

        dashboard = fs.family_dashboard(family.family_id, broken_factory)
        self.assertEqual(len(dashboard.members), 1)
        self.assertIsNone(dashboard.members[0].latest_health_score)

    def test_dashboard_raises_for_unknown_family(self):
        fs, history_backend = _make_services()
        with self.assertRaises(NotInFamilyError):
            fs.family_dashboard("does-not-exist", lambda uid: HistoryService(user_id=uid, storage=history_backend))

    def test_trend_7d_computed_correctly(self):
        fs, history_backend = _make_services()
        family = fs.create_family("parent1", "Alex", "The Smiths")
        self._populate(history_backend, "parent1", [50, 55, 60, 65, 70])
        dashboard = fs.family_dashboard(family.family_id, lambda uid: HistoryService(user_id=uid, storage=history_backend))
        parent = dashboard.members[0]
        # latest=70, earliest in trailing window (day 0)=50 -> delta +20
        self.assertEqual(parent.trend_7d, 20.0)


if __name__ == "__main__":
    unittest.main()
