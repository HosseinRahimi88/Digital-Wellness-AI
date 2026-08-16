"""Tests: the journal over HTTP, and the book a demo comes with.

The service tests (tests/identity/test_journal_service.py) pin the storage
rules. These pin the things only the wired-up app can be wrong about:
that a page needs a token, that one account cannot read another's
book, that a demo person's book is already written in four languages
with TODAY deliberately left blank for the reviewer, and that ending a
demo takes its pages with it.

Run: python3 -m unittest tests.api.test_journal_api -v
"""

from __future__ import annotations

import time
import unittest
from datetime import date, timedelta

import tests._test_support  # noqa: F401 - sys.path bootstrap + offline stubs

from fastapi.testclient import TestClient

from api.main import app
from services.identity.journal_service import JournalService


TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def _register(client: TestClient, tag: str) -> dict:
    email = f"journal-{tag}-{time.time_ns()}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd!x", "display_name": tag,
    })
    token = client.post("/api/v1/auth/login", json={
        "email": email, "password": "Passw0rd!x",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class JournalEndpointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.auth = _register(cls.client, "owner")

    def test_a_page_written_over_http_comes_back(self) -> None:
        response = self.client.put(
            f"/api/v1/journal/{TODAY}",
            json={"text": "Wrote this from the book.", "mood": "good"},
            headers=self.auth,
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["text"], "Wrote this from the book.")

        listed = self.client.get("/api/v1/journal", headers=self.auth)
        self.assertEqual(listed.status_code, 200, listed.text)
        dates = [e["date"] for e in listed.json()["entries"]]
        self.assertIn(TODAY, dates)

    def test_the_book_needs_a_token(self) -> None:
        self.assertEqual(self.client.get("/api/v1/journal").status_code, 401)
        self.assertEqual(
            self.client.put(f"/api/v1/journal/{TODAY}", json={"text": "hi"}).status_code, 401,
        )

    def test_one_account_cannot_read_anothers_book(self) -> None:
        self.client.put(
            f"/api/v1/journal/{YESTERDAY}",
            json={"text": "Private to the owner."}, headers=self.auth,
        )
        stranger = _register(self.client, "stranger")
        seen = self.client.get("/api/v1/journal", headers=stranger).json()
        self.assertEqual(seen["entries"], [])
        self.assertEqual(
            self.client.get(f"/api/v1/journal/{YESTERDAY}", headers=stranger).status_code, 404,
        )

    def test_a_day_that_has_not_happened_is_a_400_not_a_500(self) -> None:
        response = self.client.put(
            f"/api/v1/journal/{TOMORROW}", json={"text": "Tomorrow went well."}, headers=self.auth,
        )
        self.assertEqual(response.status_code, 400, response.text)

    def test_an_empty_page_is_a_400(self) -> None:
        response = self.client.put(
            f"/api/v1/journal/{TODAY}", json={"text": "   "}, headers=self.auth,
        )
        self.assertEqual(response.status_code, 400, response.text)

    def test_an_unwritten_day_is_a_404(self) -> None:
        auth = _register(self.client, "blank")
        self.assertEqual(
            self.client.get(f"/api/v1/journal/{YESTERDAY}", headers=auth).status_code, 404,
        )

    def test_a_page_can_be_torn_out(self) -> None:
        auth = _register(self.client, "tearer")
        self.client.put(f"/api/v1/journal/{TODAY}", json={"text": "Bin this."}, headers=auth)
        self.assertEqual(
            self.client.delete(f"/api/v1/journal/{TODAY}", headers=auth).status_code, 204,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/journal/{TODAY}", headers=auth).status_code, 404,
        )

    def test_deleting_the_account_takes_the_book_with_it(self) -> None:
        """The book is the most personal store here; "delete everything"
        that leaves it behind would be the worst possible omission."""
        auth = _register(self.client, "leaver")
        self.client.put(f"/api/v1/journal/{TODAY}", json={"text": "Still here?"}, headers=auth)
        me = self.client.get("/api/v1/auth/me", headers=auth).json()
        user_id = me["user_id"]
        self.assertEqual(JournalService(user_id).count(), 1)

        deleted = self.client.delete("/api/v1/privacy/me", headers=auth)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["journal_pages_deleted"], 1)
        self.assertEqual(JournalService(user_id).count(), 0)


class DemoBookTests(unittest.TestCase):
    """A demo person arrives with a book that has already been written."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.auth = _register(cls.client, "demo-book")

    def _demo(self, days: int = 7, profile: str = "improving"):
        response = self.client.post(
            "/api/v1/demo/session",
            json={"days": days, "profile": profile, "friends": 0},
            headers=self.auth,
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        return body, {"Authorization": f"Bearer {body['access_token']}"}

    def test_a_demo_book_has_pages_in_all_four_languages(self) -> None:
        _, demo_auth = self._demo(days=7, profile="improving")
        listed = self.client.get("/api/v1/journal", headers=demo_auth).json()
        self.assertGreaterEqual(listed["count"], 2, "the demo book is empty")
        for entry in listed["entries"]:
            self.assertEqual(
                set(entry["text_i18n"]), {"en", "fa", "ar", "zh"},
                f"the page for {entry['date']} is missing a language",
            )
            self.assertTrue(entry["text"].strip())

    def test_today_is_left_blank_for_the_reviewer(self) -> None:
        """The point of the book is writing in it. A demo that has
        already written today gives the reader nothing to do."""
        _, demo_auth = self._demo(days=7, profile="healthy")
        listed = self.client.get("/api/v1/journal", headers=demo_auth).json()
        self.assertNotIn(TODAY, [e["date"] for e in listed["entries"]])
        written = self.client.put(
            f"/api/v1/journal/{TODAY}", json={"text": "Read the demo, wrote a page."},
            headers=demo_auth,
        )
        self.assertEqual(written.status_code, 200, written.text)

    def test_every_demo_page_lands_on_a_day_the_person_logged(self) -> None:
        """A page on a day with no check-in would be a person who wrote
        about a day they never recorded - which is precisely the shape of
        a lapsed demo's gap, and it should stay a gap."""
        _, demo_auth = self._demo(days=7, profile="borderline")
        pages = {e["date"] for e in self.client.get("/api/v1/journal", headers=demo_auth).json()["entries"]}
        history = self.client.get("/api/v1/history?page_size=100", headers=demo_auth).json()
        logged = {e["date"] for e in history["items"]}
        self.assertTrue(pages)
        self.assertTrue(pages <= logged, f"pages with no check-in: {sorted(pages - logged)}")

    def test_leaving_the_demo_takes_its_book_with_it(self) -> None:
        body, demo_auth = self._demo(days=7, profile="at_risk")
        demo_user_id = body["demo_user_id"]
        self.assertGreater(JournalService(demo_user_id).count(), 0)
        ended = self.client.delete("/api/v1/demo/session", headers=demo_auth)
        self.assertEqual(ended.status_code, 204, ended.text)
        self.assertEqual(JournalService(demo_user_id).count(), 0)

    def test_rebuilding_a_demo_does_not_stack_two_books(self) -> None:
        body, _ = self._demo(days=7, profile="improving")
        first = JournalService(body["demo_user_id"]).count()
        body_again, _ = self._demo(days=7, profile="improving")
        self.assertEqual(body_again["demo_user_id"], body["demo_user_id"])
        self.assertEqual(JournalService(body["demo_user_id"]).count(), first)


if __name__ == "__main__":
    unittest.main()
