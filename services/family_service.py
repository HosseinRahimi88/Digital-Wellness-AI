"""
Family Service
--------------
Group C Feature 48 - Family Mode.

Lets multiple accounts (services/account_service.py) opt into a shared
"family group" so a parent/guardian (or any member) can see a
privacy-conscious, aggregated comparison of the family's real wellness
data - without exposing any individual member's raw survey answers or
habit minutes to anyone else in the group.

Privacy design (deliberate, not an afterthought)
----------------------------------------------------
This is a wellness app whose data includes stress, anxiety, loneliness,
and self-esteem scores - sharing that raw data across a household by
default would be a real harm, especially if any member is a minor.
Family Mode therefore shares **only three derived, already-summary-level
fields** per member, per day: `health_score` (0-100), `health_class`
(At Risk/Moderate/Healthy), and `persona_name`. It never reads or
exposes the individual raw HistoryService fields (sleep_hours,
stress_0_10, social_min, etc.) - `FamilyService` only ever touches
`HistoryService.get_all()`'s three summary keys, nothing else in that
record.

Consent is explicit and per-member, not implied by account membership:
joining a family requires the joining member to pass
`share_summary=True` themselves (see `join_family()`) - there is no
"parent adds a child without them acting" path in this service.
`leave_family()` immediately and permanently stops that member's data
from appearing in any future `family_dashboard()` call (their historical
entries are never retroactively pulled back in, but they also can't be
compared going forward). A member can also flip `share_summary` off
without leaving (`set_sharing()`), which immediately excludes them from
the dashboard while keeping their family membership (e.g. useful for a
temporary opt-out) - so "in the family" and "currently sharing" are
deliberately two different, independently-controllable states.

Storage
-------
Same `StorageBackend` pattern as every other service here (JSON file,
OS-level-locked transactions), `storage/families.json`. A user can
belong to at most one family at a time (kept simple - multi-family
membership would need a real design discussion about which family's
data shows on which page, and isn't needed for the feature to be
useful).
"""

from __future__ import annotations

import logging
import secrets
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from services.storage.base import StorageBackend
from services.storage.json_file_storage import JSONFileStorageBackend

logger = logging.getLogger(__name__)

DEFAULT_FAMILIES_PATH = Path(__file__).resolve().parent.parent / "storage" / "families.json"

# Fields pulled from HistoryService entries - and ONLY these. Anything
# else in a HistoryService record (raw habit minutes, psychological
# survey scores, top_shap_feature, etc.) must never reach FamilyService
# output.
_SHARED_SUMMARY_FIELDS = ("date", "health_score", "health_class", "persona")


class FamilyError(Exception):
    """Base class for family-related errors."""


class AlreadyInFamilyError(FamilyError):
    pass


class NotInFamilyError(FamilyError):
    pass


class InvalidInviteCodeError(FamilyError):
    pass


class NotFamilyOwnerError(FamilyError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class FamilyMember:
    user_id: str
    display_name: str
    joined_at_utc: str
    share_summary: bool = True


@dataclass(slots=True)
class Family:
    family_id: str
    name: str
    owner_user_id: str
    invite_code: str
    members: list[FamilyMember] = field(default_factory=list)
    created_at_utc: str = ""

    def to_record(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @staticmethod
    def from_record(record: dict[str, Any]) -> "Family":
        members = [FamilyMember(**m) for m in record.get("members", [])]
        return Family(
            family_id=record["family_id"],
            name=record["name"],
            owner_user_id=record["owner_user_id"],
            invite_code=record["invite_code"],
            members=members,
            created_at_utc=record.get("created_at_utc", ""),
        )


@dataclass(slots=True)
class MemberSummary:
    user_id: str
    display_name: str
    sharing: bool
    latest_health_score: Optional[float] = None
    latest_health_class: Optional[str] = None
    latest_persona: Optional[str] = None
    trend_7d: Optional[float] = None  # change in health_score over the last 7 logged days
    days_logged: int = 0


@dataclass(slots=True)
class FamilyDashboard:
    family_id: str
    family_name: str
    members: list[MemberSummary] = field(default_factory=list)
    family_average_score: Optional[float] = None


class FamilyService:

    def __init__(self, backend: Optional[StorageBackend] = None) -> None:
        self._backend = backend or JSONFileStorageBackend(DEFAULT_FAMILIES_PATH)

    # ------------------------------------------------------
    # Lookups
    # ------------------------------------------------------

    def get_family_for_user(self, user_id: str) -> Optional[Family]:
        for record in self._backend.read_all():
            if any(m.get("user_id") == user_id for m in record.get("members", [])):
                return Family.from_record(record)
        return None

    def _get_by_id(self, family_id: str) -> Optional[Family]:
        for record in self._backend.read_all():
            if record.get("family_id") == family_id:
                return Family.from_record(record)
        return None

    def _get_by_invite_code(self, invite_code: str) -> Optional[Family]:
        for record in self._backend.read_all():
            if record.get("invite_code") == invite_code:
                return Family.from_record(record)
        return None

    # ------------------------------------------------------
    # Mutations
    # ------------------------------------------------------

    def create_family(self, owner_user_id: str, owner_display_name: str, name: str) -> Family:
        """
        Create a new family with `owner_user_id` as its first (sharing)
        member. Raises AlreadyInFamilyError if that user already belongs
        to one - a user must leave their current family before starting
        a new one, so a stray double-create can't silently orphan them
        from data they're already comparing against.
        """
        if self.get_family_for_user(owner_user_id) is not None:
            raise AlreadyInFamilyError("You're already in a family. Leave it first.")

        family = Family(
            family_id=uuid.uuid4().hex,
            name=name.strip() or "My Family",
            owner_user_id=owner_user_id,
            invite_code=secrets.token_hex(4).upper(),
            members=[FamilyMember(
                user_id=owner_user_id,
                display_name=owner_display_name,
                joined_at_utc=_now_iso(),
                share_summary=True,
            )],
            created_at_utc=_now_iso(),
        )

        with self._backend.transaction() as records:
            records.append(family.to_record())
            self._backend.commit(records)

        logger.info("Family created: %s (owner=%s)", family.family_id, owner_user_id)
        return family

    def join_family(
        self, invite_code: str, user_id: str, display_name: str, share_summary: bool,
    ) -> Family:
        """
        Join a family by invite code. `share_summary` is a required,
        explicit argument (not defaulted to True) - the caller (a
        Streamlit checkbox the user must actively tick, in practice)
        must make the sharing decision itself; this method never assumes
        consent on the user's behalf.
        """
        if self.get_family_for_user(user_id) is not None:
            raise AlreadyInFamilyError("You're already in a family. Leave it first.")

        normalized_code = invite_code.strip().upper()

        with self._backend.transaction() as records:
            target = next((r for r in records if r.get("invite_code") == normalized_code), None)
            if target is None:
                raise InvalidInviteCodeError("No family found with that invite code.")

            target.setdefault("members", []).append(asdict(FamilyMember(
                user_id=user_id,
                display_name=display_name,
                joined_at_utc=_now_iso(),
                share_summary=bool(share_summary),
            )))
            self._backend.commit(records)
            family = Family.from_record(target)

        logger.info("User %s joined family %s (sharing=%s)", user_id, family.family_id, share_summary)
        return family

    def leave_family(self, user_id: str) -> None:
        with self._backend.transaction() as records:
            for record in records:
                members = record.get("members", [])
                if any(m.get("user_id") == user_id for m in members):
                    record["members"] = [m for m in members if m.get("user_id") != user_id]
                    # An empty family is dead weight - drop it entirely
                    # rather than leaving a zero-member record around,
                    # and reassign ownership if the owner left but
                    # members remain.
                    if not record["members"]:
                        records.remove(record)
                    elif record.get("owner_user_id") == user_id:
                        record["owner_user_id"] = record["members"][0]["user_id"]
                    break
            self._backend.commit(records)
        logger.info("User %s left their family", user_id)

    def set_sharing(self, user_id: str, share_summary: bool) -> None:
        """
        Toggle this member's sharing flag without leaving the family.
        Takes effect immediately on the next dashboard read - no
        separate "apply" step, so a user can't be stuck sharing data
        they've just decided not to.
        """
        with self._backend.transaction() as records:
            for record in records:
                for member in record.get("members", []):
                    if member.get("user_id") == user_id:
                        member["share_summary"] = bool(share_summary)
                        self._backend.commit(records)
                        return
            self._backend.commit(records)
        raise NotInFamilyError("You're not currently in a family.")

    def remove_member(self, family_id: str, requesting_user_id: str, target_user_id: str) -> None:
        """Owner-only: remove another member from the family."""
        with self._backend.transaction() as records:
            target = next((r for r in records if r.get("family_id") == family_id), None)
            if target is None:
                raise NotInFamilyError("Family not found.")
            if target.get("owner_user_id") != requesting_user_id:
                raise NotFamilyOwnerError("Only the family owner can remove members.")
            target["members"] = [m for m in target.get("members", []) if m.get("user_id") != target_user_id]
            self._backend.commit(records)

    # ------------------------------------------------------
    # Dashboard (the actual Family Mode view)
    # ------------------------------------------------------

    def family_dashboard(self, family_id: str, history_service_factory) -> FamilyDashboard:
        """
        Build the shared family comparison view. `history_service_factory`
        is a callable `(user_id) -> HistoryService`-like object with a
        `.get_all()` method - injected rather than imported directly so
        this stays trivially testable with a fake, and so it never has
        to know about HistoryService's storage details.

        Only members with `share_summary=True` contribute data. Members
        who've opted out still appear in the member list (so the family
        knows who's in the group) but with no score data attached - the
        absence itself is not hidden, only the underlying numbers are.
        """
        family = self._get_by_id(family_id)
        if family is None:
            raise NotInFamilyError("Family not found.")

        summaries: list[MemberSummary] = []
        scores_for_average: list[float] = []

        for member in family.members:
            summary = MemberSummary(
                user_id=member.user_id,
                display_name=member.display_name,
                sharing=member.share_summary,
            )

            if member.share_summary:
                try:
                    history_service = history_service_factory(member.user_id)
                    entries = sorted(
                        (e for e in history_service.get_all() if e.get("health_score") is not None),
                        key=lambda e: e.get("date", ""),
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Could not load history for family member %s", member.user_id)
                    entries = []

                if entries:
                    latest = entries[-1]
                    summary.latest_health_score = latest.get("health_score")
                    summary.latest_health_class = latest.get("health_class")
                    summary.latest_persona = latest.get("persona")
                    summary.days_logged = len(entries)

                    if summary.latest_health_score is not None:
                        scores_for_average.append(summary.latest_health_score)

                    week_ago_candidates = [e for e in entries[:-1]][-7:]
                    if week_ago_candidates and summary.latest_health_score is not None:
                        earliest_in_window = week_ago_candidates[0].get("health_score")
                        if earliest_in_window is not None:
                            summary.trend_7d = round(summary.latest_health_score - earliest_in_window, 2)

            summaries.append(summary)

        family_average = round(sum(scores_for_average) / len(scores_for_average), 2) if scores_for_average else None

        return FamilyDashboard(
            family_id=family.family_id,
            family_name=family.name,
            members=summaries,
            family_average_score=family_average,
        )
