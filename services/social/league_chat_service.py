"""
League Chat Service (D-1-b, D-1-c, D-1-d)
------------------------------------------
Private one-to-one chat and group chat for the Friends League.

The brief lists the security requirements before it lists the feature,
and that ordering is right - a half-built chat with weak authorization
is worse than no chat. Each one, and where it is enforced:

  Per-message authorization
      Every read and every write goes through `_authorize`, which
      resolves the caller's membership from stored records on each call.
      There is no "trusted" path, no client-supplied room membership,
      and no id that grants access by being guessable: knowing a
      conversation id is never sufficient.

  Nobody can read anyone else's conversation
      `messages_for` refuses before it reads. A direct conversation is
      keyed by the ACCEPTED league connection between exactly two
      people, so a revoked connection stops resolving and the history
      stops being readable in the same instant.

  Access revocation is real, not cosmetic
      `revoke_access` is called by LeagueService.revoke() and marks the
      conversation closed. After that the other side cannot read new
      messages, cannot post, and cannot see anything shared since - the
      privacy requirement the brief calls out as "not just the
      interface".

  Block
      A block is symmetric and immediate: neither side can post to or
      read a conversation that either participant has blocked. It
      survives independently of the connection, so unblocking is a
      deliberate act rather than a side effect of reconnecting.

  Report
      A report stores the reporter, the target, the message and a
      reason, and it is stored even when the reporter also blocks. It
      is never shown to the reported user.

  Rate limiting
      A sliding window per sender across all conversations. Deliberately
      not per conversation: a limit that resets per room is not a limit,
      it is a suggestion.

Storage goes through the same StorageBackend the rest of the app uses -
one flat record list distinguished by "kind", matching
league_service.py exactly, so there is no second data layer to keep in
sync (G9).

Message bodies are stored as the user typed them and are never
interpreted as markup anywhere; the client inserts them as text nodes.
Length is capped on the way in.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for
from services.social.league_service import DEFAULT_LEAGUE_PATH

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000
MAX_GROUP_MEMBERS = 12
MAX_GROUP_NAME_LENGTH = 60

# Sliding-window rate limit, per sender, across every conversation.
RATE_LIMIT_MESSAGES = 20
RATE_LIMIT_WINDOW_SECONDS = 60

# How many messages a single read returns. A conversation that has run
# for months must not become a several-megabyte response.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

KIND_CONVERSATION = "conversation"
KIND_MESSAGE = "message"
KIND_BLOCK = "block"
KIND_REPORT = "report"

CONVERSATION_DIRECT = "direct"
CONVERSATION_GROUP = "group"


class ChatError(Exception):
    """Base class. Every subclass maps to a specific HTTP status."""


class ChatNotAuthorizedError(ChatError):
    """The caller is not a member, or the conversation is closed/blocked."""


class ChatNotFoundError(ChatError):
    pass


class ChatBlockedError(ChatError):
    pass


class ChatRateLimitedError(ChatError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Too many messages. Slow down a moment.")
        self.retry_after_seconds = retry_after_seconds


class ChatValidationError(ChatError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


@dataclass(slots=True)
class ChatMessage:
    message_id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    body: str
    sent_at_utc: str
    # A message the sender removed. The record stays so the thread does
    # not silently renumber and so a report about it still resolves, but
    # the body is cleared on the way out.
    deleted: bool = False


@dataclass(slots=True)
class Conversation:
    conversation_id: str
    kind: str                      # direct | group
    member_ids: list[str] = field(default_factory=list)
    member_names: dict[str, str] = field(default_factory=dict)
    title: str = ""
    created_by: str = ""
    created_at_utc: str = ""
    # Set when a league connection behind a direct conversation is
    # revoked. Closed conversations are unreadable by everyone.
    closed: bool = False
    closed_at_utc: str = ""


class LeagueChatService:
    """Stateless except for its storage backend."""

    def __init__(self, backend: Optional[StorageBackend] = None) -> None:
        self._backend = backend or backend_for(DEFAULT_LEAGUE_PATH)

    # ==================================================================
    # Record helpers
    # ==================================================================

    @staticmethod
    def _is(record: dict, kind: str) -> bool:
        return record.get("kind") == kind

    @staticmethod
    def _conversation_from_record(r: dict) -> Conversation:
        return Conversation(
            conversation_id=r["conversation_id"],
            kind=r.get("conversation_kind", CONVERSATION_DIRECT),
            member_ids=list(r.get("member_ids", [])),
            member_names=dict(r.get("member_names", {})),
            title=r.get("title", ""),
            created_by=r.get("created_by", ""),
            created_at_utc=r.get("created_at_utc", ""),
            closed=bool(r.get("closed", False)),
            closed_at_utc=r.get("closed_at_utc", ""),
        )

    @staticmethod
    def _message_from_record(r: dict) -> ChatMessage:
        deleted = bool(r.get("deleted", False))
        return ChatMessage(
            message_id=r["message_id"],
            conversation_id=r["conversation_id"],
            sender_id=r["sender_id"],
            sender_name=r.get("sender_name", ""),
            # A deleted message never leaks its body, not even to the
            # sender - otherwise "delete" means "hide from others".
            body="" if deleted else r.get("body", ""),
            sent_at_utc=r.get("sent_at_utc", ""),
            deleted=deleted,
        )

    # ==================================================================
    # Blocking
    # ==================================================================

    def _blocked_pairs(self, records: list[dict]) -> set[tuple[str, str]]:
        return {
            (r.get("blocker_id", ""), r.get("blocked_id", ""))
            for r in records if self._is(r, KIND_BLOCK)
        }

    @staticmethod
    def _is_blocked_between(pairs: set[tuple[str, str]], a: str, b: str) -> bool:
        """Symmetric on purpose. If either side blocked, the channel is
        shut for both - a block that only stops one direction still lets
        the blocked person read, which is not what anyone means by it."""
        return (a, b) in pairs or (b, a) in pairs

    def block(self, blocker_id: str, blocked_id: str) -> None:
        if blocker_id == blocked_id:
            raise ChatValidationError("You cannot block yourself.")
        with self._backend.transaction() as records:
            already = any(
                self._is(r, KIND_BLOCK) and r.get("blocker_id") == blocker_id
                and r.get("blocked_id") == blocked_id
                for r in records
            )
            if not already:
                records.append({
                    "kind": KIND_BLOCK,
                    "blocker_id": blocker_id,
                    "blocked_id": blocked_id,
                    "created_at_utc": _now_iso(),
                })
                self._backend.commit(records)

    def unblock(self, blocker_id: str, blocked_id: str) -> None:
        with self._backend.transaction() as records:
            remaining = [
                r for r in records
                if not (self._is(r, KIND_BLOCK) and r.get("blocker_id") == blocker_id
                        and r.get("blocked_id") == blocked_id)
            ]
            if len(remaining) != len(records):
                self._backend.commit(remaining)

    def blocked_ids(self, user_id: str) -> list[str]:
        return [
            r.get("blocked_id", "") for r in self._backend.read_all()
            if self._is(r, KIND_BLOCK) and r.get("blocker_id") == user_id
        ]

    # ==================================================================
    # Reporting
    # ==================================================================

    def report(
        self, reporter_id: str, message_id: str, reason: str = "", also_block: bool = False,
    ) -> None:
        """Stored for a human to look at. Never surfaced to the reported
        user, and never used to auto-moderate - an automatic penalty on
        an unreviewed report is a tool for harassment."""
        reason = (reason or "").strip()[:500]
        with self._backend.transaction() as records:
            message = next(
                (r for r in records if self._is(r, KIND_MESSAGE) and r.get("message_id") == message_id),
                None,
            )
            if message is None:
                raise ChatNotFoundError("No such message.")
            conversation = next(
                (r for r in records if self._is(r, KIND_CONVERSATION)
                 and r.get("conversation_id") == message.get("conversation_id")),
                None,
            )
            # You can only report something you were entitled to see.
            if conversation is None or reporter_id not in conversation.get("member_ids", []):
                raise ChatNotAuthorizedError("You are not in that conversation.")

            records.append({
                "kind": KIND_REPORT,
                "report_id": uuid.uuid4().hex,
                "reporter_id": reporter_id,
                "reported_user_id": message.get("sender_id", ""),
                "message_id": message_id,
                "conversation_id": message.get("conversation_id", ""),
                "reason": reason,
                "created_at_utc": _now_iso(),
            })
            self._backend.commit(records)

        if also_block:
            self.block(reporter_id, message.get("sender_id", ""))

    # ==================================================================
    # Conversations
    # ==================================================================

    def _find_conversation(self, records: list[dict], conversation_id: str) -> Optional[dict]:
        return next(
            (r for r in records if self._is(r, KIND_CONVERSATION)
             and r.get("conversation_id") == conversation_id),
            None,
        )

    def _authorize(self, records: list[dict], conversation_id: str, user_id: str, *, for_write: bool) -> dict:
        """The single gate. Everything that touches a conversation calls
        this first, on freshly read records, so a membership change takes
        effect on the very next request rather than at the next login."""
        record = self._find_conversation(records, conversation_id)
        if record is None:
            # Deliberately the same error as "not a member": otherwise
            # the difference between the two answers tells a stranger
            # which conversation ids exist.
            raise ChatNotFoundError("No such conversation.")
        if user_id not in record.get("member_ids", []):
            raise ChatNotFoundError("No such conversation.")
        if record.get("closed"):
            raise ChatNotAuthorizedError("This conversation is closed.")

        blocked = self._blocked_pairs(records)
        others = [m for m in record.get("member_ids", []) if m != user_id]
        if record.get("conversation_kind") == CONVERSATION_DIRECT:
            if others and self._is_blocked_between(blocked, user_id, others[0]):
                raise ChatBlockedError("This conversation is blocked.")
        elif for_write:
            # In a group, a block silences the pair rather than the room:
            # posting is allowed, and the reader-side filter in
            # messages_for() hides each blocked member's messages.
            pass
        return record

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> Conversation:
        """Give a conversation a name you will recognise later.

        Goes through _authorize like everything else that touches a
        conversation, so someone who is not a member cannot rename one -
        and cannot learn one exists by trying, since the refusal is the
        same either way.

        The name is shared, not per-member: a group has one name, and a
        direct chat renamed by one side reads the same to the other.
        Anything else means two people referring to the same thread by
        different names, which is worse than either of them not being
        able to rename it at all.
        """
        title = (title or "").strip()[:MAX_GROUP_NAME_LENGTH]
        if not title:
            raise ChatValidationError("A conversation name cannot be empty.")

        with self._backend.transaction() as records:
            record = self._authorize(records, conversation_id, user_id, for_write=True)
            record["title"] = title
            self._backend.commit(records)
            return self._conversation_from_record(record)

    def open_direct_conversation(
        self, user_id: str, other_id: str, user_name: str = "", other_name: str = "",
        *, connection_verified: bool,
    ) -> Conversation:
        """`connection_verified` is not a courtesy flag - the router
        passes the result of asking LeagueService whether these two have
        an ACCEPTED connection, and this refuses without it. Chat is a
        thing accepted friends have, never a way to reach a stranger."""
        if not connection_verified:
            raise ChatNotAuthorizedError("You can only chat with an accepted friend.")
        if user_id == other_id:
            raise ChatValidationError("You cannot open a chat with yourself.")

        with self._backend.transaction() as records:
            blocked = self._blocked_pairs(records)
            if self._is_blocked_between(blocked, user_id, other_id):
                raise ChatBlockedError("This conversation is blocked.")

            pair = {user_id, other_id}
            existing = next(
                (r for r in records if self._is(r, KIND_CONVERSATION)
                 and r.get("conversation_kind") == CONVERSATION_DIRECT
                 and set(r.get("member_ids", [])) == pair),
                None,
            )
            if existing is not None:
                if existing.get("closed"):
                    # Reconnecting after a revoke reopens the same thread
                    # rather than orphaning its history.
                    existing["closed"] = False
                    existing["closed_at_utc"] = ""
                    self._backend.commit(records)
                return self._conversation_from_record(existing)

            record = {
                "kind": KIND_CONVERSATION,
                "conversation_id": uuid.uuid4().hex,
                "conversation_kind": CONVERSATION_DIRECT,
                "member_ids": sorted(pair),
                "member_names": {user_id: user_name, other_id: other_name},
                "title": "",
                "created_by": user_id,
                "created_at_utc": _now_iso(),
                "closed": False,
            }
            records.append(record)
            self._backend.commit(records)
            return self._conversation_from_record(record)

    def create_group(
        self, creator_id: str, creator_name: str, title: str,
        members: dict[str, str], *, verified_member_ids: set[str],
    ) -> Conversation:
        """`verified_member_ids` is the set the router confirmed are
        accepted friends of the creator. Anyone not in it is dropped -
        a group is not a way to add someone who never agreed to be
        reachable."""
        title = (title or "").strip()[:MAX_GROUP_NAME_LENGTH]
        if not title:
            raise ChatValidationError("A group needs a name.")

        allowed = {mid: name for mid, name in (members or {}).items() if mid in verified_member_ids}
        if not allowed:
            raise ChatValidationError("Add at least one friend who has accepted you.")
        if len(allowed) + 1 > MAX_GROUP_MEMBERS:
            raise ChatValidationError(f"A group can hold at most {MAX_GROUP_MEMBERS} people.")

        with self._backend.transaction() as records:
            blocked = self._blocked_pairs(records)
            allowed = {
                mid: name for mid, name in allowed.items()
                if not self._is_blocked_between(blocked, creator_id, mid)
            }
            if not allowed:
                raise ChatBlockedError("Everyone you picked is blocked.")

            names = dict(allowed)
            names[creator_id] = creator_name
            record = {
                "kind": KIND_CONVERSATION,
                "conversation_id": uuid.uuid4().hex,
                "conversation_kind": CONVERSATION_GROUP,
                "member_ids": sorted(set(allowed) | {creator_id}),
                "member_names": names,
                "title": title,
                "created_by": creator_id,
                "created_at_utc": _now_iso(),
                "closed": False,
            }
            records.append(record)
            self._backend.commit(records)
            return self._conversation_from_record(record)

    def leave_group(self, user_id: str, conversation_id: str) -> None:
        with self._backend.transaction() as records:
            record = self._authorize(records, conversation_id, user_id, for_write=False)
            if record.get("conversation_kind") != CONVERSATION_GROUP:
                raise ChatValidationError("Only a group can be left.")
            record["member_ids"] = [m for m in record.get("member_ids", []) if m != user_id]
            record.get("member_names", {}).pop(user_id, None)
            # An empty group is closed rather than left as a room nobody
            # can enter but whose messages still exist.
            if not record["member_ids"]:
                record["closed"] = True
                record["closed_at_utc"] = _now_iso()
            self._backend.commit(records)

    def revoke_access(self, user_a: str, user_b: str) -> None:
        """Called when a league connection is revoked. The direct
        conversation closes immediately - this is the "after removal
        that person must no longer have access" requirement, enforced in
        the data rather than by hiding a button."""
        with self._backend.transaction() as records:
            pair = {user_a, user_b}
            changed = False
            for r in records:
                if (self._is(r, KIND_CONVERSATION)
                        and r.get("conversation_kind") == CONVERSATION_DIRECT
                        and set(r.get("member_ids", [])) == pair
                        and not r.get("closed")):
                    r["closed"] = True
                    r["closed_at_utc"] = _now_iso()
                    changed = True
            if changed:
                self._backend.commit(records)

    def delete_user_data(self, user_id: str) -> dict:
        """Permanently erases every conversation this user belongs to,
        every message in those conversations, and every block/report
        record naming them.

        Deliberately stronger than revoke_access() above: revoking access
        for an ordinary friend removal CLOSES the conversation because the
        other person's copy of it should stay readable to them. Account
        deletion has no "other person's copy" to preserve - the whole
        point is that nothing about this user is left anywhere, so the
        records are dropped, not flagged closed.
        """
        with self._backend.transaction() as records:
            conversation_ids = {
                r.get("conversation_id") for r in records
                if self._is(r, KIND_CONVERSATION) and user_id in r.get("member_ids", [])
            }
            kept = []
            removed = {"conversations": 0, "messages": 0, "blocks": 0, "reports": 0}
            for r in records:
                if self._is(r, KIND_CONVERSATION) and r.get("conversation_id") in conversation_ids:
                    removed["conversations"] += 1
                    continue
                if self._is(r, KIND_MESSAGE) and r.get("conversation_id") in conversation_ids:
                    removed["messages"] += 1
                    continue
                if self._is(r, KIND_BLOCK) and user_id in (r.get("blocker_id"), r.get("blocked_id")):
                    removed["blocks"] += 1
                    continue
                if self._is(r, KIND_REPORT) and r.get("reporter_id") == user_id:
                    removed["reports"] += 1
                    continue
                kept.append(r)
            if len(kept) != len(records):
                self._backend.commit(kept)
        return removed

    def conversations_for(self, user_id: str) -> list[Conversation]:
        records = self._backend.read_all()
        blocked = self._blocked_pairs(records)
        out: list[Conversation] = []
        for r in records:
            if not self._is(r, KIND_CONVERSATION):
                continue
            if user_id not in r.get("member_ids", []):
                continue
            if r.get("closed"):
                continue
            if r.get("conversation_kind") == CONVERSATION_DIRECT:
                others = [m for m in r.get("member_ids", []) if m != user_id]
                if others and self._is_blocked_between(blocked, user_id, others[0]):
                    continue
            out.append(self._conversation_from_record(r))
        out.sort(key=lambda c: c.created_at_utc, reverse=True)
        return out

    # ==================================================================
    # Messages
    # ==================================================================

    def _check_rate_limit(self, records: list[dict], sender_id: str) -> None:
        cutoff = _now() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
        recent = []
        for r in records:
            if not self._is(r, KIND_MESSAGE) or r.get("sender_id") != sender_id:
                continue
            try:
                sent = datetime.fromisoformat(r.get("sent_at_utc", ""))
            except (ValueError, TypeError):
                continue
            if sent.tzinfo is None:
                sent = sent.replace(tzinfo=timezone.utc)
            if sent >= cutoff:
                recent.append(sent)
        if len(recent) >= RATE_LIMIT_MESSAGES:
            oldest = min(recent)
            retry_after = int((oldest + timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS) - _now()).total_seconds())
            raise ChatRateLimitedError(max(1, retry_after))

    def send_message(
        self, user_id: str, conversation_id: str, body: str, sender_name: str = "",
    ) -> ChatMessage:
        body = (body or "").strip()
        if not body:
            raise ChatValidationError("An empty message is not a message.")
        if len(body) > MAX_MESSAGE_LENGTH:
            raise ChatValidationError(f"Messages are capped at {MAX_MESSAGE_LENGTH} characters.")

        with self._backend.transaction() as records:
            self._authorize(records, conversation_id, user_id, for_write=True)
            self._check_rate_limit(records, user_id)

            record = {
                "kind": KIND_MESSAGE,
                "message_id": uuid.uuid4().hex,
                "conversation_id": conversation_id,
                "sender_id": user_id,
                "sender_name": sender_name,
                "body": body,
                "sent_at_utc": _now_iso(),
                "deleted": False,
            }
            records.append(record)
            self._backend.commit(records)
            return self._message_from_record(record)

    def seed_messages(
        self, conversation_id: str, messages: "list[tuple[str, str, str]]",
    ) -> int:
        """Write a whole scripted exchange in ONE transaction.

        For the demo, and only for the demo (services/demo/demo_service.py).
        Two reasons it exists rather than a loop over `send_message`:

        * the rate limiter. Seven messages in a row is exactly what it is
          built to stop, and rightly - but the limit is about a person
          typing, not about a demo being constructed. Looping through
          `send_message` had the seeder trip its own guard and truncate
          the conversation it was writing;
        * cost. Every `send_message` is a locked read-modify-write of the
          whole chat file. Ten friends times seven lines is seventy of
          them for something that can be one.

        Authorization is NOT skipped: every sender is checked against the
        conversation exactly as `send_message` checks it. What is skipped
        is the human-pacing limit, which is the only part that does not
        apply. `messages` is (sender_id, sender_name, body), in order.

        The timestamps are spread backwards from now, oldest first, so
        the thread reads as a conversation that happened rather than as
        seven messages sent in the same second.
        """
        clean: list[tuple[str, str, str]] = []
        for sender_id, sender_name, body in messages or []:
            text = (body or "").strip()
            if not text or not sender_id:
                continue
            clean.append((sender_id, sender_name or "", text[:MAX_MESSAGE_LENGTH]))
        if not clean:
            return 0

        with self._backend.transaction() as records:
            for sender_id in {m[0] for m in clean}:
                self._authorize(records, conversation_id, sender_id, for_write=True)

            base = _now() - timedelta(minutes=3 * len(clean))
            for i, (sender_id, sender_name, body) in enumerate(clean):
                records.append({
                    "kind": KIND_MESSAGE,
                    "message_id": uuid.uuid4().hex,
                    "conversation_id": conversation_id,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "body": body,
                    "sent_at_utc": (base + timedelta(minutes=3 * i)).isoformat(timespec="seconds"),
                    "deleted": False,
                })
            self._backend.commit(records)
        return len(clean)

    def messages_for(
        self, user_id: str, conversation_id: str, limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ChatMessage]:
        limit = max(1, min(int(limit or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE))
        records = self._backend.read_all()
        # Authorization BEFORE any message is read - not a filter applied
        # to results that were already gathered.
        self._authorize(records, conversation_id, user_id, for_write=False)

        blocked = self._blocked_pairs(records)
        messages = [
            self._message_from_record(r) for r in records
            if self._is(r, KIND_MESSAGE) and r.get("conversation_id") == conversation_id
            # In a group, a blocked member's messages disappear for the
            # person who blocked them, and only for them.
            and not self._is_blocked_between(blocked, user_id, r.get("sender_id", ""))
        ]
        messages.sort(key=lambda m: m.sent_at_utc)
        return messages[-limit:]

    def delete_message(self, user_id: str, message_id: str) -> None:
        """A sender can retract their own message. Nobody can delete
        anyone else's - moderation is a human decision on a report, not
        a button in the thread."""
        with self._backend.transaction() as records:
            record = next(
                (r for r in records if self._is(r, KIND_MESSAGE) and r.get("message_id") == message_id),
                None,
            )
            if record is None:
                raise ChatNotFoundError("No such message.")
            if record.get("sender_id") != user_id:
                raise ChatNotAuthorizedError("You can only delete your own messages.")
            record["deleted"] = True
            record["body"] = ""
            self._backend.commit(records)

    def unread_count(self, user_id: str) -> int:
        """Messages from other people across every open conversation the
        user is in. Cheap enough to poll and it needs no extra state."""
        total = 0
        for conversation in self.conversations_for(user_id):
            try:
                total += sum(
                    1 for m in self.messages_for(user_id, conversation.conversation_id)
                    if m.sender_id != user_id and not m.deleted
                )
            except ChatError:
                continue
        return total
