"""Renaming a league conversation, and saying who sees the new name.

The server has supported renaming since the feature shipped, and the API
client had a method for it - but nothing in the UI ever called it, so in
practice a thread could not be renamed at all and four rows reading
"Direct chat" stayed indistinguishable.

The part that needed care is not the button. The name is shared by
design (LeagueChatService.rename_conversation: two people calling one
thread different names is worse than neither being able to rename it),
so the confirmation has to say so. A user who believes a rename is
private, and discovers it was not, has been misled by the interface.

Run: python3 -m unittest tests.social.test_league_chat_rename -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path bootstrap

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

REPO_ROOT = paths.PROJECT_ROOT
FRONTEND = REPO_ROOT / "frontend"
JS = FRONTEND / "assets" / "js"


class TestTheRenameControlExists(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (JS / "pages/league-chat.js").read_text(encoding="utf-8")
        cls.api = (JS / "core/api.js").read_text(encoding="utf-8")

    def test_the_ui_actually_calls_the_rename_endpoint(self):
        # This is the whole bug: the method existed and nothing used it.
        self.assertIn("chatRenameConversation", self.api)
        self.assertIn("DWApi.chatRenameConversation", self.js)

    def test_renaming_never_opens_the_thread_as_a_side_effect(self):
        idx = self.js.index("renameBtn.addEventListener('click'")
        body = self.js[idx:idx + 300]
        self.assertIn("stopPropagation()", body)

    def test_an_empty_or_cancelled_rename_is_not_sent(self):
        # window.prompt returns null on cancel and '' on an empty box;
        # neither should reach the server as a title.
        idx = self.js.index("renameBtn.addEventListener('click'")
        body = self.js[idx:idx + 700]
        self.assertIn("next === null", body)
        self.assertIn("trim()", body)
        self.assertIn("if (!trimmed) return", body)

    def test_the_control_is_reachable_without_a_mouse(self):
        idx = self.js.index("const renameBtn")
        body = self.js[idx:idx + 400]
        self.assertIn("el('button'", body)
        self.assertIn("aria-label", body)

    def test_a_failed_rename_is_reported_rather_than_silently_dropped(self):
        idx = self.js.index("renameBtn.addEventListener('click'")
        body = self.js[idx:idx + 900]
        self.assertIn("catch", body)
        self.assertIn("DWToast.error", body)


class TestTheNameIsShownHonestly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (JS / "pages/league-chat.js").read_text(encoding="utf-8")

    def test_the_confirmation_says_the_name_is_shared(self):
        # The rename is shared server-side. Telling the user it is
        # private would be a straightforward lie about who sees what.
        idx = self.js.index("renamed: {")
        body = self.js[idx:idx + 700]
        self.assertIn("Everyone in this conversation", body)
        self.assertIn("همه‌ی کسانی که در این گفتگو هستند", body)
        for token in ("كل من في هذه المحادثة", "所有人"):
            with self.subTest(token=token):
                self.assertIn(token, body)

    def test_the_confirmation_does_not_claim_privacy(self):
        idx = self.js.index("renamed: {")
        body = self.js[idx:idx + 700]
        for wrong in ("Only you", "only you see"):
            with self.subTest(phrase=wrong):
                self.assertNotIn(wrong, body)

    def test_the_service_really_does_share_the_name(self):
        # If this ever became per-member, the message above would turn
        # into a lie in the other direction - so pin the actual behaviour.
        svc = (REPO_ROOT / "services" / "social" / "league_chat_service.py").read_text(encoding="utf-8")
        idx = svc.index("def rename_conversation")
        body = svc[idx:idx + 1400]
        self.assertIn('record["title"] = title', body)
        self.assertNotIn("per_member", body)

    def test_a_renamed_thread_keeps_its_name_whatever_kind_it_is(self):
        # A direct chat used to ignore `title` entirely and always show
        # the other person's name, so renaming one had no visible effect.
        idx = self.js.index("const name = c.title")
        body = self.js[idx:idx + 260]
        self.assertIn("c.title", body)
        self.assertIn("member_names", body)

    def test_every_new_string_exists_in_all_four_languages(self):
        start = self.js.index("const T = {")
        end = self.js.index("// ---- rendering", start)
        table = self.js[start:end]
        for key in ("rename", "renamePrompt", "renamed"):
            with self.subTest(key=key):
                idx = table.index(f"{key}: {{")
                block = table[idx:idx + 900]
                for lang in ("en:", "fa:", "ar:", "zh:"):
                    self.assertIn(lang, block, f"{key} is missing {lang}")


class TestTheGuideExplainsTheseControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (JS / "guide/guide-content-chat.js").read_text(encoding="utf-8")
        cls.html = (FRONTEND / "league.html").read_text(encoding="utf-8")

    def test_both_controls_have_a_guide_topic(self):
        for topic in ("league_new_group", "league_chat_rename"):
            with self.subTest(topic=topic):
                self.assertIn(f"{topic}: {{", self.content)
                self.assertIn(f'data-guide="{topic}"', self.html)

    def test_each_topic_is_written_in_all_four_languages(self):
        for topic in ("league_new_group", "league_chat_rename"):
            idx = self.content.index(f"{topic}: {{")
            block = self.content[idx:idx + 4000]
            for lang in ("en:", "fa:", "ar:", "zh:"):
                with self.subTest(topic=topic, lang=lang):
                    self.assertIn(lang, block)

    def test_the_rename_topic_warns_that_the_name_is_shared(self):
        idx = self.content.index("league_chat_rename: {")
        block = self.content[idx:idx + 4000]
        self.assertIn("shared, not private", block)

    def test_the_group_topic_says_who_can_be_added(self):
        # The question a reader actually has: can a stranger get in?
        idx = self.content.index("league_new_group: {")
        block = self.content[idx:idx + 4000]
        self.assertIn("already accepted you", block)


class TestLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = (FRONTEND / "assets" / "css" / "app.css").read_text(encoding="utf-8")

    def test_the_row_and_its_rename_button_are_styled(self):
        self.assertIn(".chat-conversation-row", self.css)
        self.assertIn(".chat-conversation-rename", self.css)

    def test_the_row_stops_growing_on_a_narrow_screen(self):
        # The sidebar becomes a horizontal strip below 640px; a row that
        # keeps flex-grow there scrolls one conversation at a time.
        idx = self.css.index("@media (max-width: 640px)")
        block = self.css[idx:idx + 700]
        self.assertIn(".chat-conversation-row { flex: 0 0 auto; }", block)


if __name__ == "__main__":
    unittest.main()
