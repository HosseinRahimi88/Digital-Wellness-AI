"""
Friends League Service
-----------------------
Peer-to-peer version of services/social/family_service.py's consent model,
rebuilt for one-to-one friend connections instead of a single shared
group: every user has their own stable invite code, a connection
between two users only exists once BOTH sides have explicitly agreed
to it, and - unlike Family Mode's single shared sharing flag - each
side independently chooses exactly which categories of their OWN data
that specific friend can see, and can change that at any time without
affecting anyone else.

Consent flow (mirrors family_service.py's explicit-consent philosophy,
extended to two sides instead of one)
--------------------------------------------------------------------
1. Both users must have accepted the League rules at least once
   (`accept_rules`) before they can send OR approve a request - there
   is no path that connects two accounts without both having seen the
   rules.
2. User A enters user B's invite code and picks which categories of
   A's OWN data to share *if* B accepts (`redeem_invite`). This creates
   a `pending` connection - B is not yet visible to A, and A is not yet
   visible to B.
3. B sees the pending request (`pending_requests_for`) - the in-app
   "notification" is simply this list, not a push notification, per
   the product decision that this must never leave the app. B must
   explicitly approve, and in the same action picks which categories of
   B's OWN data to share back (`respond_to_request`). Declining leaves
   both sides exactly as before - no data crosses at any point.
4. Once accepted, either side can change what THEY share at any time
   (`update_sharing`) or end the connection entirely (`revoke`), which
   immediately stops data flowing in both directions.

What can ever be shared
------------------------
Only four derived, already-summary-level categories - never a raw
survey/habit field:
    persona     - the rule-based persona title (utils/persona_titles)
    score       - latest real regression_score
    rank        - this friend's position in a shared leaderboard
    plan_focus  - the single real factor currently driving that
                  friend's score most (their latest logged
                  top_shap_feature) - never the full recommendation text
A category a friend has NOT ticked is simply absent from what the
other side can read - never zero-filled, never guessed.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core import paths
from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for

logger = logging.getLogger(__name__)

DEFAULT_LEAGUE_PATH = paths.storage_file("league.json")

ALLOWED_CATEGORIES = frozenset({"persona", "score", "rank", "plan_focus"})

# Invite codes are read off a screen and typed by hand, often from a photo
# or across a table, so the alphabet excludes every character pair people
# reliably confuse: 0/O, 1/I/L. Digits 2-9 and the remaining 23 letters
# leave 31 symbols; at 8 characters that is ~8.5e11 combinations, so a code
# cannot be found by guessing even though it is short enough to read aloud.
INVITE_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_CODE_LENGTH = 8
# Collisions are astronomically unlikely, but "unlikely" is not "checked" -
# uniqueness is verified against existing codes inside the same locked
# transaction that writes the profile, so two users cannot race into the
# same code.
_INVITE_CODE_MAX_ATTEMPTS = 12


def _random_invite_code() -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


def _unique_invite_code(records: list[dict]) -> str:
    """A code no existing profile holds. Must be called inside a
    `transaction()` block so the read and the later write are atomic."""
    taken = {
        r.get("invite_code")
        for r in records
        if r.get("kind") == "profile" and r.get("invite_code")
    }
    for _ in range(_INVITE_CODE_MAX_ATTEMPTS):
        code = _random_invite_code()
        if code not in taken:
            return code
    # Exhausting 12 attempts means the space is saturated or something is
    # badly wrong; failing loudly beats handing out a duplicate.
    raise LeagueError("Could not allocate a unique invite code. Please try again.")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_categories(categories: list[str] | None) -> list[str]:
    cats = list(dict.fromkeys(categories or []))  # de-dupe, preserve order
    unknown = [c for c in cats if c not in ALLOWED_CATEGORIES]
    if unknown:
        raise ValueError(f"Unknown sharing categor{'y' if len(unknown) == 1 else 'ies'}: {', '.join(unknown)}")
    return cats


class LeagueError(Exception):
    """Base class for League-related errors."""


class RulesNotAcceptedError(LeagueError):
    pass


class InvalidInviteCodeError(LeagueError):
    pass


class AlreadyConnectedError(LeagueError):
    pass


class ConnectionNotFoundError(LeagueError):
    pass


@dataclass(slots=True)
class LeagueProfile:
    user_id: str
    invite_code: str
    rules_accepted: bool = False
    created_at_utc: str = ""
    # Stored so a *requester* can be shown the target's real name. Without
    # it, redeem_invite() had nothing to read and every outgoing request
    # rendered as a nameless connection.
    display_name: str = ""


@dataclass(slots=True)
class LeagueConnection:
    connection_id: str
    requester_id: str
    requester_name: str
    target_id: str
    target_name: str
    status: str = "pending"  # pending | accepted | declined
    requester_shared: list[str] = field(default_factory=list)
    target_shared: list[str] = field(default_factory=list)
    requested_at_utc: str = ""
    responded_at_utc: str = ""

    def other_side(self, user_id: str) -> tuple[str, str]:
        """Returns (other_user_id, other_display_name)."""
        if user_id == self.requester_id:
            return self.target_id, self.target_name
        return self.requester_id, self.requester_name

    def shared_by(self, user_id: str) -> list[str]:
        """What `user_id` has agreed to share INTO this connection."""
        return self.requester_shared if user_id == self.requester_id else self.target_shared

    def visible_to(self, user_id: str) -> list[str]:
        """What `user_id` is allowed to SEE from the other side."""
        return self.target_shared if user_id == self.requester_id else self.requester_shared


class LeagueService:

    def __init__(self, backend: Optional[StorageBackend] = None) -> None:
        self._backend = backend or backend_for(DEFAULT_LEAGUE_PATH)

    # ------------------------------------------------------
    # Records are a single flat list distinguished by "kind".
    # ------------------------------------------------------

    @staticmethod
    def _is_profile(r: dict) -> bool:
        return r.get("kind") == "profile"

    @staticmethod
    def _is_connection(r: dict) -> bool:
        return r.get("kind") == "connection"

    @staticmethod
    def _profile_from_record(r: dict) -> LeagueProfile:
        return LeagueProfile(
            user_id=r["user_id"], invite_code=r["invite_code"],
            rules_accepted=bool(r.get("rules_accepted", False)),
            created_at_utc=r.get("created_at_utc", ""),
            display_name=r.get("display_name", ""),
        )

    @staticmethod
    def _connection_from_record(r: dict) -> LeagueConnection:
        return LeagueConnection(
            connection_id=r["connection_id"], requester_id=r["requester_id"],
            requester_name=r.get("requester_name", ""), target_id=r["target_id"],
            target_name=r.get("target_name", ""), status=r.get("status", "pending"),
            requester_shared=list(r.get("requester_shared", [])),
            target_shared=list(r.get("target_shared", [])),
            requested_at_utc=r.get("requested_at_utc", ""),
            responded_at_utc=r.get("responded_at_utc", ""),
        )

    # ------------------------------------------------------
    # Profiles (invite code + rules acceptance)
    # ------------------------------------------------------

    def get_or_create_profile(self, user_id: str, display_name: str = "") -> LeagueProfile:
        with self._backend.transaction() as records:
            for r in records:
                if self._is_profile(r) and r.get("user_id") == user_id:
                    # Keep the stored name in step with the account's current
                    # one, so a rename shows up for people who already hold
                    # this invite code.
                    if display_name and r.get("display_name") != display_name:
                        r["display_name"] = display_name
                        self._backend.commit(records)
                    return self._profile_from_record(r)
            profile = LeagueProfile(
                user_id=user_id, invite_code=_unique_invite_code(records), created_at_utc=_now_iso(),
                display_name=display_name,
            )
            record = asdict(profile)
            record["kind"] = "profile"
            records.append(record)
            self._backend.commit(records)
            return profile

    def accept_rules(self, user_id: str, display_name: str = "") -> LeagueProfile:
        with self._backend.transaction() as records:
            for r in records:
                if self._is_profile(r) and r.get("user_id") == user_id:
                    r["rules_accepted"] = True
                    if display_name:
                        r["display_name"] = display_name
                    self._backend.commit(records)
                    return self._profile_from_record(r)
            profile = LeagueProfile(
                user_id=user_id, invite_code=_unique_invite_code(records),
                rules_accepted=True, created_at_utc=_now_iso(),
                display_name=display_name,
            )
            record = asdict(profile)
            record["kind"] = "profile"
            records.append(record)
            self._backend.commit(records)
            return profile

    def _find_profile_by_code(self, records: list[dict], code: str) -> Optional[dict]:
        normalized = code.strip().upper()
        return next((r for r in records if self._is_profile(r) and r.get("invite_code") == normalized), None)

    # ------------------------------------------------------
    # Connections
    # ------------------------------------------------------

    def redeem_invite(
        self, user_id: str, display_name: str, invite_code: str, shared_categories: list[str],
    ) -> LeagueConnection:
        categories = _validate_categories(shared_categories)
        with self._backend.transaction() as records:
            own_profile = next((r for r in records if self._is_profile(r) and r.get("user_id") == user_id), None)
            if own_profile is None or not own_profile.get("rules_accepted"):
                raise RulesNotAcceptedError("Accept the League rules before sending a connection request.")

            target = self._find_profile_by_code(records, invite_code)
            if target is None:
                raise InvalidInviteCodeError("No League member found with that invite code.")
            target_id = target["user_id"]
            if target_id == user_id:
                raise LeagueError("You can't connect with your own invite code.")

            existing = next((
                r for r in records if self._is_connection(r)
                and r.get("status") in ("pending", "accepted")
                and {r.get("requester_id"), r.get("target_id")} == {user_id, target_id}
            ), None)
            if existing is not None:
                raise AlreadyConnectedError("You already have a pending or active connection with this person.")

            connection = LeagueConnection(
                connection_id=uuid.uuid4().hex, requester_id=user_id, requester_name=display_name,
                target_id=target_id, target_name=target.get("display_name", ""),
                status="pending", requester_shared=categories, target_shared=[],
                requested_at_utc=_now_iso(),
            )
            record = asdict(connection)
            record["kind"] = "connection"
            records.append(record)
            self._backend.commit(records)
            return connection

    def pending_requests_for(self, user_id: str) -> list[LeagueConnection]:
        records = self._backend.read_all()
        return [
            self._connection_from_record(r) for r in records
            if self._is_connection(r) and r.get("target_id") == user_id and r.get("status") == "pending"
        ]

    def sent_requests_for(self, user_id: str) -> list[LeagueConnection]:
        records = self._backend.read_all()
        return [
            self._connection_from_record(r) for r in records
            if self._is_connection(r) and r.get("requester_id") == user_id and r.get("status") == "pending"
        ]

    def respond_to_request(
        self, user_id: str, connection_id: str, approve: bool, shared_categories: list[str] | None,
    ) -> LeagueConnection:
        categories = _validate_categories(shared_categories) if approve else []
        with self._backend.transaction() as records:
            own_profile = next((r for r in records if self._is_profile(r) and r.get("user_id") == user_id), None)
            if approve and (own_profile is None or not own_profile.get("rules_accepted")):
                raise RulesNotAcceptedError("Accept the League rules before approving a connection request.")

            target_record = next((
                r for r in records if self._is_connection(r) and r.get("connection_id") == connection_id
                and r.get("target_id") == user_id and r.get("status") == "pending"
            ), None)
            if target_record is None:
                raise ConnectionNotFoundError("No pending request with that id for you.")

            target_record["status"] = "accepted" if approve else "declined"
            target_record["target_shared"] = categories
            target_record["responded_at_utc"] = _now_iso()
            self._backend.commit(records)
            return self._connection_from_record(target_record)

    def update_sharing(self, user_id: str, connection_id: str, shared_categories: list[str]) -> LeagueConnection:
        categories = _validate_categories(shared_categories)
        with self._backend.transaction() as records:
            record = next((
                r for r in records if self._is_connection(r) and r.get("connection_id") == connection_id
                and r.get("status") == "accepted" and user_id in (r.get("requester_id"), r.get("target_id"))
            ), None)
            if record is None:
                raise ConnectionNotFoundError("No active connection with that id for you.")
            if user_id == record["requester_id"]:
                record["requester_shared"] = categories
            else:
                record["target_shared"] = categories
            self._backend.commit(records)
            return self._connection_from_record(record)

    def revoke(self, user_id: str, connection_id: str) -> None:
        """Remove a connection - and with it, every access it granted.

        D-1-d makes the point explicitly: after removal the other person
        must no longer have access to anything, and that has to be true
        in the data rather than in the interface. Deleting the
        connection record already ends data sharing, because every
        sharing read resolves through it. The direct chat has its own
        records, so it is closed here in the same call - otherwise a
        removed friend would keep a readable conversation, which is
        exactly the "interface-only" revocation the brief warns about.
        """
        other_id = None
        with self._backend.transaction() as records:
            match = next((
                r for r in records if self._is_connection(r) and r.get("connection_id") == connection_id
                and user_id in (r.get("requester_id"), r.get("target_id"))
            ), None)
            if match is None:
                raise ConnectionNotFoundError("No connection with that id for you.")
            other_id = (
                match.get("target_id") if user_id == match.get("requester_id")
                else match.get("requester_id")
            )
            records.remove(match)
            self._backend.commit(records)

        if other_id:
            # Imported here rather than at module scope: the chat service
            # imports this module for its storage path, and a top-level
            # import each way is a cycle.
            from services.social.league_chat_service import LeagueChatService
            LeagueChatService(backend=self._backend).revoke_access(user_id, other_id)

    def are_connected(self, user_id: str, other_id: str) -> bool:
        """Whether these two have an ACCEPTED connection right now.

        The chat router asks this before opening or joining anything, so
        chat membership is always derived from a live check rather than
        from something the client sent.
        """
        return any(
            r for r in self._backend.read_all()
            if self._is_connection(r) and r.get("status") == "accepted"
            and {r.get("requester_id"), r.get("target_id")} == {user_id, other_id}
        )

    def connections_for(self, user_id: str) -> list[LeagueConnection]:
        records = self._backend.read_all()
        return [
            self._connection_from_record(r) for r in records
            if self._is_connection(r) and r.get("status") == "accepted"
            and user_id in (r.get("requester_id"), r.get("target_id"))
        ]

    def delete_user_data(self, user_id: str) -> dict:
        """Permanently removes this user's own League profile and every
        connection - any status, not just accepted - they are part of.

        Unlike revoke() this is for ACCOUNT deletion, not one friend
        removal: there is no "other side" left to notify or leave a
        closed-but-visible trace for. Returns the ids on the other end of
        each removed connection so a caller doing a cascading delete (see
        api/routers/demo.py, where a demo's bot friends are not real
        accounts and only exist through these connections) knows who else
        needs cleaning up without a second read of the store.
        """
        other_ids: set[str] = set()
        profiles_removed = 0
        connections_removed = 0
        with self._backend.transaction() as records:
            kept = []
            for r in records:
                if self._is_profile(r) and r.get("user_id") == user_id:
                    profiles_removed += 1
                    continue
                if self._is_connection(r) and user_id in (r.get("requester_id"), r.get("target_id")):
                    connections_removed += 1
                    other = r.get("target_id") if r.get("requester_id") == user_id else r.get("requester_id")
                    if other:
                        other_ids.add(other)
                    continue
                kept.append(r)
            if len(kept) != len(records):
                self._backend.commit(kept)
        return {
            "profiles_removed": profiles_removed,
            "connections_removed": connections_removed,
            "other_user_ids": sorted(other_ids),
        }
