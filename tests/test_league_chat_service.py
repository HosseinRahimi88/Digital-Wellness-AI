"""
Tests: services/league_chat_service.py (D-1-b, D-1-c, D-1-d).

Almost every test here is an attempt to do something that must fail.
That is the right shape for a chat feature: the failure mode is not "the
message did not send", it is "a stranger read a private conversation",
and nothing about that shows up in normal use.

Run: python3 -m unittest tests.test_league_chat_service -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap + offline stubs

from services.league_chat_service import (
    MAX_GROUP_MEMBERS,
    MAX_MESSAGE_LENGTH,
    RATE_LIMIT_MESSAGES,
    ChatBlockedError,
    ChatNotAuthorizedError,
    ChatNotFoundError,
    ChatRateLimitedError,
    ChatValidationError,
    LeagueChatService,
)
from services.storage.json_file_storage import JSONFileStorageBackend

ALICE, BOB, CAROL, MALLORY = "alice", "bob", "carol", "mallory"


class ChatTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())
        self.backend = JSONFileStorageBackend(self._tmp / "league.json")
        self.chat = LeagueChatService(backend=self.backend)

    def _direct(self, a=ALICE, b=BOB):
        return self.chat.open_direct_conversation(a, b, connection_verified=True)


class TestAuthorization(ChatTestCase):

    def test_a_direct_chat_requires_a_verified_connection(self):
        """The single most important refusal here: chat is something
        accepted friends have, never a route to a stranger."""
        with self.assertRaises(ChatNotAuthorizedError):
            self.chat.open_direct_conversation(ALICE, MALLORY, connection_verified=False)

    def test_a_non_member_cannot_read_a_conversation(self):
        conversation = self._direct()
        self.chat.send_message(ALICE, conversation.conversation_id, "private")
        with self.assertRaises(ChatNotFoundError):
            self.chat.messages_for(MALLORY, conversation.conversation_id)

    def test_a_non_member_cannot_write_to_a_conversation(self):
        conversation = self._direct()
        with self.assertRaises(ChatNotFoundError):
            self.chat.send_message(MALLORY, conversation.conversation_id, "hello")

    def test_knowing_the_id_is_never_enough(self):
        """A guessed or leaked id must be worth nothing on its own."""
        conversation = self._direct()
        self.assertTrue(conversation.conversation_id)
        with self.assertRaises(ChatNotFoundError):
            self.chat.messages_for(MALLORY, conversation.conversation_id)

    def test_a_missing_conversation_and_a_forbidden_one_look_the_same(self):
        """Different answers would confirm which ids exist."""
        conversation = self._direct()
        with self.assertRaises(ChatNotFoundError):
            self.chat.messages_for(MALLORY, conversation.conversation_id)
        with self.assertRaises(ChatNotFoundError):
            self.chat.messages_for(MALLORY, "does-not-exist")

    def test_authorization_is_re_resolved_on_every_call(self):
        """Not cached at open time - a membership change has to take
        effect on the next request."""
        conversation = self.chat.create_group(
            ALICE, "Alice", "Team", {BOB: "Bob"}, verified_member_ids={BOB},
        )
        self.chat.send_message(BOB, conversation.conversation_id, "hi")
        self.chat.leave_group(BOB, conversation.conversation_id)
        with self.assertRaises(ChatNotFoundError):
            self.chat.send_message(BOB, conversation.conversation_id, "still here?")


class TestRevocation(ChatTestCase):

    def test_revoking_access_closes_the_conversation_for_both(self):
        conversation = self._direct()
        self.chat.send_message(ALICE, conversation.conversation_id, "hello")
        self.chat.revoke_access(ALICE, BOB)
        for user in (ALICE, BOB):
            with self.assertRaises(ChatNotAuthorizedError):
                self.chat.messages_for(user, conversation.conversation_id)

    def test_a_revoked_conversation_cannot_be_posted_to(self):
        conversation = self._direct()
        self.chat.revoke_access(ALICE, BOB)
        with self.assertRaises(ChatNotAuthorizedError):
            self.chat.send_message(BOB, conversation.conversation_id, "are you there")

    def test_a_revoked_conversation_disappears_from_the_list(self):
        conversation = self._direct()
        self.assertTrue(self.chat.conversations_for(ALICE))
        self.chat.revoke_access(ALICE, BOB)
        self.assertEqual(self.chat.conversations_for(ALICE), [])

    def test_reconnecting_reopens_the_same_thread(self):
        conversation = self._direct()
        self.chat.send_message(ALICE, conversation.conversation_id, "before")
        self.chat.revoke_access(ALICE, BOB)
        reopened = self._direct()
        self.assertEqual(reopened.conversation_id, conversation.conversation_id)
        bodies = [m.body for m in self.chat.messages_for(ALICE, reopened.conversation_id)]
        self.assertIn("before", bodies)


class TestRevocationThroughLeagueService(ChatTestCase):
    """The requirement is that removing a friend cuts access, not that a
    service method exists which could."""

    def test_league_revoke_closes_the_chat(self):
        from services.league_service import LeagueService
        league = LeagueService(backend=self.backend)
        league.accept_rules(ALICE, "Alice")
        bob_profile = league.accept_rules(BOB, "Bob")
        connection = league.redeem_invite(ALICE, "Alice", bob_profile.invite_code, ["score"])
        league.respond_to_request(BOB, connection.connection_id, True, ["score"])

        conversation = self._direct()
        self.chat.send_message(ALICE, conversation.conversation_id, "hi")

        league.revoke(ALICE, connection.connection_id)

        with self.assertRaises(ChatNotAuthorizedError):
            self.chat.messages_for(BOB, conversation.conversation_id)


class TestBlocking(ChatTestCase):

    def test_a_block_is_symmetric(self):
        conversation = self._direct()
        self.chat.block(ALICE, BOB)
        for user in (ALICE, BOB):
            with self.assertRaises(ChatBlockedError):
                self.chat.messages_for(user, conversation.conversation_id)

    def test_a_blocked_person_cannot_post(self):
        conversation = self._direct()
        self.chat.block(ALICE, BOB)
        with self.assertRaises(ChatBlockedError):
            self.chat.send_message(BOB, conversation.conversation_id, "let me in")

    def test_a_block_prevents_opening_a_new_conversation(self):
        self.chat.block(ALICE, BOB)
        with self.assertRaises(ChatBlockedError):
            self.chat.open_direct_conversation(BOB, ALICE, connection_verified=True)

    def test_unblocking_restores_access(self):
        conversation = self._direct()
        self.chat.block(ALICE, BOB)
        self.chat.unblock(ALICE, BOB)
        self.assertIsInstance(self.chat.messages_for(ALICE, conversation.conversation_id), list)

    def test_in_a_group_a_block_hides_only_that_person(self):
        """Blocking someone should not make a whole group unusable for
        everyone else in it."""
        group = self.chat.create_group(
            ALICE, "Alice", "Team", {BOB: "Bob", CAROL: "Carol"},
            verified_member_ids={BOB, CAROL},
        )
        self.chat.send_message(BOB, group.conversation_id, "from bob")
        self.chat.send_message(CAROL, group.conversation_id, "from carol")
        self.chat.block(ALICE, BOB)

        visible = [m.body for m in self.chat.messages_for(ALICE, group.conversation_id)]
        self.assertNotIn("from bob", visible)
        self.assertIn("from carol", visible)
        # Carol is unaffected.
        self.assertIn("from bob", [m.body for m in self.chat.messages_for(CAROL, group.conversation_id)])

    def test_you_cannot_block_yourself(self):
        with self.assertRaises(ChatValidationError):
            self.chat.block(ALICE, ALICE)


class TestGroups(ChatTestCase):

    def test_only_verified_friends_end_up_in_a_group(self):
        """Naming someone in a list must not make them reachable."""
        group = self.chat.create_group(
            ALICE, "Alice", "Team", {BOB: "Bob", MALLORY: "Mallory"},
            verified_member_ids={BOB},
        )
        self.assertIn(BOB, group.member_ids)
        self.assertNotIn(MALLORY, group.member_ids)

    def test_a_group_with_no_verified_members_is_refused(self):
        with self.assertRaises(ChatValidationError):
            self.chat.create_group(ALICE, "Alice", "Team", {MALLORY: "M"}, verified_member_ids=set())

    def test_a_group_needs_a_name(self):
        with self.assertRaises(ChatValidationError):
            self.chat.create_group(ALICE, "Alice", "   ", {BOB: "Bob"}, verified_member_ids={BOB})

    def test_group_size_is_capped(self):
        members = {f"user{i}": f"User {i}" for i in range(MAX_GROUP_MEMBERS + 2)}
        with self.assertRaises(ChatValidationError):
            self.chat.create_group(ALICE, "Alice", "Big", members, verified_member_ids=set(members))

    def test_leaving_removes_you_from_the_member_list(self):
        group = self.chat.create_group(
            ALICE, "Alice", "Team", {BOB: "Bob"}, verified_member_ids={BOB})
        self.chat.leave_group(BOB, group.conversation_id)
        self.assertEqual(self.chat.conversations_for(BOB), [])

    def test_a_direct_conversation_cannot_be_left_like_a_group(self):
        conversation = self._direct()
        with self.assertRaises(ChatValidationError):
            self.chat.leave_group(ALICE, conversation.conversation_id)


class TestRateLimiting(ChatTestCase):

    def test_the_limit_applies_and_says_when_to_retry(self):
        conversation = self._direct()
        for i in range(RATE_LIMIT_MESSAGES):
            self.chat.send_message(ALICE, conversation.conversation_id, f"m{i}")
        with self.assertRaises(ChatRateLimitedError) as caught:
            self.chat.send_message(ALICE, conversation.conversation_id, "one too many")
        self.assertGreaterEqual(caught.exception.retry_after_seconds, 1)

    def test_the_limit_is_per_sender_not_per_conversation(self):
        """A limit that resets per room is not a limit."""
        first = self._direct(ALICE, BOB)
        second = self.chat.create_group(
            ALICE, "Alice", "Team", {CAROL: "Carol"}, verified_member_ids={CAROL})
        for i in range(RATE_LIMIT_MESSAGES):
            self.chat.send_message(ALICE, first.conversation_id, f"m{i}")
        with self.assertRaises(ChatRateLimitedError):
            self.chat.send_message(ALICE, second.conversation_id, "different room")

    def test_one_persons_limit_does_not_affect_another(self):
        conversation = self._direct()
        for i in range(RATE_LIMIT_MESSAGES):
            self.chat.send_message(ALICE, conversation.conversation_id, f"m{i}")
        self.assertTrue(self.chat.send_message(BOB, conversation.conversation_id, "still fine"))


class TestMessageContent(ChatTestCase):

    def test_an_empty_message_is_refused(self):
        conversation = self._direct()
        for body in ("", "   ", "\n\t"):
            with self.assertRaises(ChatValidationError):
                self.chat.send_message(ALICE, conversation.conversation_id, body)

    def test_an_over_long_message_is_refused(self):
        conversation = self._direct()
        with self.assertRaises(ChatValidationError):
            self.chat.send_message(ALICE, conversation.conversation_id, "x" * (MAX_MESSAGE_LENGTH + 1))

    def test_the_body_is_stored_exactly_as_typed(self):
        """Never escaped or rewritten on the way in - the client inserts
        it as a text node, and mangling it here would corrupt legitimate
        messages that happen to contain angle brackets."""
        conversation = self._direct()
        body = '<script>alert("hi")</script> & "quotes" <3'
        sent = self.chat.send_message(ALICE, conversation.conversation_id, body)
        self.assertEqual(sent.body, body)
        self.assertEqual(self.chat.messages_for(BOB, conversation.conversation_id)[-1].body, body)

    def test_messages_come_back_in_order_and_capped(self):
        conversation = self._direct()
        for i in range(10):
            self.chat.send_message(ALICE, conversation.conversation_id, f"m{i}")
        recent = self.chat.messages_for(BOB, conversation.conversation_id, limit=3)
        self.assertEqual([m.body for m in recent], ["m7", "m8", "m9"])


class TestDeletion(ChatTestCase):

    def test_you_can_retract_your_own_message(self):
        conversation = self._direct()
        sent = self.chat.send_message(ALICE, conversation.conversation_id, "oops")
        self.chat.delete_message(ALICE, sent.message_id)
        message = self.chat.messages_for(BOB, conversation.conversation_id)[-1]
        self.assertTrue(message.deleted)
        self.assertEqual(message.body, "")

    def test_you_cannot_delete_someone_elses_message(self):
        conversation = self._direct()
        sent = self.chat.send_message(ALICE, conversation.conversation_id, "mine")
        with self.assertRaises(ChatNotAuthorizedError):
            self.chat.delete_message(BOB, sent.message_id)

    def test_a_deleted_body_is_hidden_from_the_sender_too(self):
        conversation = self._direct()
        sent = self.chat.send_message(ALICE, conversation.conversation_id, "secret")
        self.chat.delete_message(ALICE, sent.message_id)
        self.assertEqual(self.chat.messages_for(ALICE, conversation.conversation_id)[-1].body, "")


class TestReporting(ChatTestCase):

    def test_a_report_is_stored_with_who_what_and_why(self):
        conversation = self._direct()
        sent = self.chat.send_message(BOB, conversation.conversation_id, "rude")
        self.chat.report(ALICE, sent.message_id, "unkind")
        reports = [r for r in self.backend.read_all() if r.get("kind") == "report"]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["reporter_id"], ALICE)
        self.assertEqual(reports[0]["reported_user_id"], BOB)
        self.assertEqual(reports[0]["reason"], "unkind")

    def test_you_cannot_report_a_message_you_could_not_see(self):
        conversation = self._direct()
        sent = self.chat.send_message(ALICE, conversation.conversation_id, "private")
        with self.assertRaises(ChatNotAuthorizedError):
            self.chat.report(MALLORY, sent.message_id, "nosy")

    def test_report_and_block_together(self):
        conversation = self._direct()
        sent = self.chat.send_message(BOB, conversation.conversation_id, "rude")
        self.chat.report(ALICE, sent.message_id, "unkind", also_block=True)
        self.assertIn(BOB, self.chat.blocked_ids(ALICE))

    def test_a_report_never_appears_in_anyones_conversation(self):
        conversation = self._direct()
        sent = self.chat.send_message(BOB, conversation.conversation_id, "rude")
        self.chat.report(ALICE, sent.message_id, "unkind")
        for user in (ALICE, BOB):
            bodies = [m.body for m in self.chat.messages_for(user, conversation.conversation_id)]
            self.assertNotIn("unkind", bodies)


if __name__ == "__main__":
    unittest.main()
