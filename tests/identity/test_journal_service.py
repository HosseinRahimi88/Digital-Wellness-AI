"""Tests: the daily journal - the book on the About page.

This is the only store in the app holding text the user wrote in their
own words, so the things pinned here are the ones that would be worst
to get wrong: a page belongs to exactly one account, writing the same
day twice edits it instead of duplicating it, and "delete everything"
really does take the book with it.

Run: python3 -m unittest tests.identity.test_journal_service -v
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import tests._test_support  # noqa: F401

from services.identity.journal_service import (
    MAX_TEXT_LENGTH,
    JournalService,
    JournalValidationError,
)
from services.storage.json_file_storage import JSONFileStorageBackend


class JournalServiceTests(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="wellness_journal_test_"))
        self.path = self._tmp / "journal.json"
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _service(self, user_id: str) -> JournalService:
        return JournalService(user_id, backend=JSONFileStorageBackend(self.path))

    # ----------------------------------------------------------- writing

    def test_a_page_saves_and_reads_back(self) -> None:
        svc = self._service("alice")
        entry = svc.save(self.today, "  Long day. Phone stayed in the drawer.  ", "good")
        self.assertEqual(entry.date, self.today.isoformat())
        self.assertEqual(entry.text, "Long day. Phone stayed in the drawer.")
        self.assertEqual(entry.mood, "good")
        self.assertEqual(svc.get(self.today).text, entry.text)

    def test_writing_the_same_day_twice_edits_the_page(self) -> None:
        """A diary has one page per day. Two "todays" would be unreadable."""
        svc = self._service("alice")
        first = svc.save(self.today, "First go.")
        svc.save(self.today, "What I actually meant.")
        self.assertEqual(svc.count(), 1)
        page = svc.get(self.today)
        self.assertEqual(page.text, "What I actually meant.")
        # The day keeps its first-written stamp: correcting a sentence
        # does not make it a different day.
        self.assertEqual(page.created_at_utc, first.created_at_utc)

    def test_an_empty_page_is_refused(self) -> None:
        svc = self._service("alice")
        for empty in ("", "   ", "\n\t "):
            with self.assertRaises(JournalValidationError):
                svc.save(self.today, empty)
        self.assertEqual(svc.count(), 0)

    def test_an_over_long_page_is_refused(self) -> None:
        svc = self._service("alice")
        with self.assertRaises(JournalValidationError):
            svc.save(self.today, "x" * (MAX_TEXT_LENGTH + 1))
        # Exactly at the limit is fine - the boundary belongs to the user.
        svc.save(self.today, "x" * MAX_TEXT_LENGTH)
        self.assertEqual(svc.count(), 1)

    def test_a_day_that_has_not_happened_cannot_be_written(self) -> None:
        """Otherwise a mistyped year sorts ahead of every real page."""
        svc = self._service("alice")
        with self.assertRaises(JournalValidationError):
            svc.save(self.today + timedelta(days=1), "Tomorrow went well.")

    def test_yesterday_can_still_be_written(self) -> None:
        """People catch up on the day before; that is not backdating."""
        svc = self._service("alice")
        svc.save(self.yesterday, "Forgot to write this last night.")
        self.assertIsNotNone(svc.get(self.yesterday))

    def test_a_bad_date_is_refused_rather_than_stored(self) -> None:
        svc = self._service("alice")
        for bad in ("not-a-date", "2026-13-40", "", None):
            with self.assertRaises(JournalValidationError):
                svc.save(bad, "Something.")

    def test_an_unknown_mood_is_refused(self) -> None:
        svc = self._service("alice")
        with self.assertRaises(JournalValidationError):
            svc.save(self.today, "Fine.", "ecstatic")

    # -------------------------------------------------------------- scope

    def test_one_persons_book_is_not_another_persons(self) -> None:
        alice, bob = self._service("alice"), self._service("bob")
        alice.save(self.today, "Alice's day.")
        bob.save(self.today, "Bob's day.")
        self.assertEqual(alice.get(self.today).text, "Alice's day.")
        self.assertEqual(bob.get(self.today).text, "Bob's day.")
        self.assertEqual(alice.count(), 1)
        self.assertEqual(bob.count(), 1)

    def test_deleting_one_book_leaves_the_other_alone(self) -> None:
        alice, bob = self._service("alice"), self._service("bob")
        alice.save(self.today, "Alice's day.")
        bob.save(self.today, "Bob's day.")
        self.assertEqual(alice.delete_all(), 1)
        self.assertEqual(alice.count(), 0)
        self.assertEqual(bob.count(), 1)

    def test_delete_users_only_touches_the_ids_it_is_given(self) -> None:
        for who in ("demo", "demo_bot_sam", "real_person"):
            self._service(who).save(self.today, f"{who} wrote this.")
        removed = self._service("demo").delete_users(["demo", "demo_bot_sam"])
        self.assertEqual(removed, 2)
        self.assertEqual(self._service("real_person").count(), 1)

    # ------------------------------------------------------------ reading

    def test_pages_come_back_newest_first(self) -> None:
        svc = self._service("alice")
        for offset in (5, 1, 3):
            svc.save(self.today - timedelta(days=offset), f"day -{offset}")
        dates = [e.date for e in svc.get_all()]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_limit_takes_the_newest_pages_not_the_oldest(self) -> None:
        svc = self._service("alice")
        for offset in range(6):
            svc.save(self.today - timedelta(days=offset), f"day -{offset}")
        newest_two = svc.get_all(limit=2)
        self.assertEqual(len(newest_two), 2)
        self.assertEqual(newest_two[0].date, self.today.isoformat())
        self.assertEqual(newest_two[1].date, (self.today - timedelta(days=1)).isoformat())

    def test_an_unwritten_day_is_none_not_an_empty_page(self) -> None:
        self.assertIsNone(self._service("alice").get(self.yesterday))

    def test_tearing_a_page_out(self) -> None:
        svc = self._service("alice")
        svc.save(self.today, "Regret writing this.")
        self.assertTrue(svc.delete(self.today))
        self.assertIsNone(svc.get(self.today))
        self.assertFalse(svc.delete(self.today))

    # ---------------------------------------------------------- save_many

    def test_save_many_writes_a_whole_book_at_once(self) -> None:
        svc = self._service("demo")
        pages = [
            (self.today - timedelta(days=n), f"page {n}", "steady", {"en": f"page {n}", "fa": f"صفحه {n}"})
            for n in range(1, 6)
        ]
        self.assertEqual(svc.save_many(pages), 5)
        self.assertEqual(svc.count(), 5)
        self.assertEqual(svc.get(self.today - timedelta(days=3)).text_i18n["fa"], "صفحه 3")

    def test_save_many_skips_the_pages_it_cannot_write(self) -> None:
        """A bad page is dropped, not silently repaired into a good one."""
        svc = self._service("demo")
        written = svc.save_many([
            (self.today, "fine", None, {}),
            (self.today + timedelta(days=2), "the future", None, {}),
            (self.yesterday, "   ", None, {}),
        ])
        self.assertEqual(written, 1)
        self.assertEqual(svc.count(), 1)

    def test_save_many_edits_days_that_already_exist(self) -> None:
        svc = self._service("demo")
        svc.save(self.yesterday, "first version")
        svc.save_many([(self.yesterday, "rebuilt", "good", {})])
        self.assertEqual(svc.count(), 1)
        self.assertEqual(svc.get(self.yesterday).text, "rebuilt")

    def test_only_the_four_supported_languages_survive(self) -> None:
        svc = self._service("demo")
        svc.save_many([(self.today, "hi", None, {"en": "hi", "de": "hallo", "fa": "", "ar": "أهلًا"})])
        self.assertEqual(set(svc.get(self.today).text_i18n), {"en", "ar"})


if __name__ == "__main__":
    unittest.main()
