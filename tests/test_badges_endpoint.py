"""
Tests: GET /api/v1/badges and /api/v1/badges/public.

The public endpoint is a privacy boundary, not a convenience filter: an
awareness indicator appearing there would put "a late-night pattern is
active" in front of the user's friends. That is asserted here at the
HTTP layer, not only in the service, because the filter is what any
future league surface will actually rely on.

Run: python3 -m unittest tests.test_badges_endpoint -v
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path bootstrap

from tests.test_api import APITestCase


class TestBadgesEndpoint(APITestCase):

    def _seed(self, **fields) -> dict[str, str]:
        token = self._register(email="badges@example.com")
        headers = self._auth_headers(token)
        user_id = self.client.get("/api/v1/auth/me", headers=headers).json()["user_id"]

        from api.dependencies.services import get_history_storage_backend
        backend = self.app.dependency_overrides[get_history_storage_backend]()

        today = date.today()
        entries = []
        for i in range(30):
            d = today - timedelta(days=29 - i)
            entry = {"user_id": user_id, "date": d.isoformat(), "health_score": 70}
            entry.update(fields)
            entries.append(entry)
        backend.commit(entries)
        return headers

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/v1/badges").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/badges/public").status_code, 401)

    def test_new_account_gets_the_full_catalogue_with_nothing_earned(self):
        headers = self._auth_headers(self._register(email="fresh@example.com"))
        body = self.client.get("/api/v1/badges", headers=headers).json()
        self.assertGreater(body["total_count"], 40)
        self.assertEqual(body["earned_count"], 0)

    def test_real_history_earns_real_badges(self):
        headers = self._seed()
        body = self.client.get("/api/v1/badges", headers=headers).json()
        earned = {b["id"] for b in body["badges"] if b["earned"]}
        self.assertIn("checkins_30", earned)
        self.assertIn("first_week", earned)

    def test_public_endpoint_never_returns_a_private_badge(self):
        # night_screen_min high enough that awareness indicators fire.
        headers = self._seed(night_screen_min=200, sleep_hours=4.0, stress_0_10=9)

        full = self.client.get("/api/v1/badges", headers=headers).json()
        self.assertTrue(
            any(b["private"] and b["earned"] for b in full["badges"]),
            "test is vacuous unless a private indicator actually fired",
        )

        public = self.client.get("/api/v1/badges/public", headers=headers).json()
        self.assertFalse(any(b["private"] for b in public["badges"]))
        self.assertFalse(any(b["category"] == "awareness" for b in public["badges"]))

    def test_no_human_readable_text_is_returned(self):
        """Names and descriptions are rendered client-side in four
        languages; an English string here would reappear untranslated."""
        headers = self._seed()
        body = self.client.get("/api/v1/badges", headers=headers).json()
        for b in body["badges"]:
            self.assertNotIn("name", b)
            self.assertNotIn("description", b)

    def test_earned_by_tier_counts_only_earned_achievements(self):
        headers = self._seed()
        body = self.client.get("/api/v1/badges", headers=headers).json()
        earned_achievements = [
            b for b in body["badges"] if b["earned"] and b["category"] == "achievement"
        ]
        self.assertEqual(sum(body["earned_by_tier"].values()), len(earned_achievements))


if __name__ == "__main__":
    unittest.main()
