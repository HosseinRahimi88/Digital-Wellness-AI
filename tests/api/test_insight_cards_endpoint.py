"""
Tests: GET /api/v1/insights/cards end-to-end.

This endpoint deliberately wraps every card builder in a broad
`except Exception` so that one failing card can never blank the whole
panel. That is the right behaviour for users and a trap for tests: a
card that raises on every single request looks exactly like a card that
had nothing to say. These tests therefore assert on *presence* with data
that is known to be sufficient, not just on a 200.

That is not hypothetical - the weekly-challenge list was built with
`vars()` on a `slots=True` dataclass, which raises `TypeError` every
time, and the response stayed a valid 200 with an empty list.

Run: python3 -m unittest tests.api.test_insight_cards_endpoint -v
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path bootstrap

from tests.api.test_api import APITestCase


def _history(user_id: str, days: int, end: date) -> list[dict]:
    """`days` plain, well-formed check-ins ending on `end`."""
    entries = []
    for i in range(days):
        d = end - timedelta(days=days - 1 - i)
        entries.append({
            "user_id": user_id,
            "date": d.isoformat(),
            "day_of_week": d.strftime("%A"),
            "health_score": 60 + (i % 7),
            "health_class": "Healthy",
            "total_screen_min": 300 + (i % 5) * 20,
            "sleep_hours": 7.0,
            "mood_score": 6,
            "productivity_score": 6,
        })
    return entries


class TestInsightCardsEndpoint(APITestCase):

    def _seed(self, days: int = 30, end: date | None = None) -> dict[str, str]:
        token = self._register(email="cards@example.com")
        headers = self._auth_headers(token)
        me = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me.status_code, 200, me.text)
        user_id = me.json()["user_id"]

        from api.dependencies.services import get_history_storage_backend
        backend = self.app.dependency_overrides[get_history_storage_backend]()
        backend.commit(_history(user_id, days, end or date.today()))
        return headers

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/v1/insights/cards").status_code, 401)

    def test_returns_200_with_no_history_at_all(self):
        """A brand-new account gets an empty panel, not a 500."""
        headers = self._auth_headers(self._register(email="empty@example.com"))
        response = self.client.get("/api/v1/insights/cards", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIsNone(body["correlation"])
        self.assertIsNone(body["narrative"])

    def test_weekly_challenges_are_returned_for_a_real_history(self):
        """The regression guard: an empty list here meant a raising card."""
        headers = self._seed()
        body = self.client.get("/api/v1/insights/cards", headers=headers).json()
        ids = {c["id"] for c in body["weekly_challenges"]}
        # daily_checkin_streak is unconditional; the profile-derived ones
        # need enough history, which 30 days is.
        self.assertIn("daily_checkin_streak", ids)
        self.assertIn("beat_your_typical_score", ids)

    def test_risk_alerts_carry_translated_text_through_the_real_endpoint(self):
        # insight-cards.js used to render `a.message`/`a.title`/`a.action`
        # straight from the response - always English, since that's the
        # only language RiskAlertService ever built the flat fields in.
        # text_i18n is what the client now reads instead; checked through
        # the real GET this endpoint serves, not the service directly.
        token = self._register(email="riskalert@example.com")
        headers = self._auth_headers(token)
        me = self.client.get("/api/v1/auth/me", headers=headers)
        user_id = me.json()["user_id"]

        from api.dependencies.services import get_history_storage_backend
        backend = self.app.dependency_overrides[get_history_storage_backend]()
        end = date.today()
        entries = [
            {"user_id": user_id, "date": (end - timedelta(days=3)).isoformat(),
             "day_of_week": (end - timedelta(days=3)).strftime("%A"), "health_score": 90.0, "health_class": "Healthy"},
            {"user_id": user_id, "date": (end - timedelta(days=2)).isoformat(),
             "day_of_week": (end - timedelta(days=2)).strftime("%A"), "health_score": 80.0, "health_class": "Healthy"},
            {"user_id": user_id, "date": (end - timedelta(days=1)).isoformat(),
             "day_of_week": (end - timedelta(days=1)).strftime("%A"), "health_score": 70.0, "health_class": "Healthy"},
            {"user_id": user_id, "date": end.isoformat(),
             "day_of_week": end.strftime("%A"), "health_score": 60.0, "health_class": "Healthy"},
        ]
        backend.commit(entries)

        body = self.client.get("/api/v1/insights/cards", headers=headers).json()
        alerts = body["risk_alerts"]
        decline = next((a for a in alerts if a["title"] == "Declining Trend"), None)
        self.assertIsNotNone(decline, f"expected a Declining Trend alert, got: {alerts}")
        for lang in ("en", "fa", "ar", "zh"):
            self.assertTrue(decline["text_i18n"]["title"].get(lang, "").strip())
            self.assertTrue(decline["text_i18n"]["message"].get(lang, "").strip())
        # The real numbers from this exact history, not placeholders.
        self.assertIn("90.0", decline["text_i18n"]["message"]["en"])
        self.assertIn("60.0", decline["text_i18n"]["message"]["en"])

    def test_challenge_targets_are_exposed_as_numbers_for_translation(self):
        """The client re-writes the English copy per language, so the
        numbers have to arrive separately - never parsed out of a
        sentence."""
        headers = self._seed()
        body = self.client.get("/api/v1/insights/cards", headers=headers).json()
        by_id = {c["id"]: c for c in body["weekly_challenges"]}
        beat = by_id.get("beat_your_typical_score")
        self.assertIsNotNone(beat)
        self.assertIn("typical_score", beat["params"])
        self.assertGreater(beat["params"]["typical_score"], 0)

    def test_every_challenge_has_a_coherent_progress_and_target(self):
        headers = self._seed()
        body = self.client.get("/api/v1/insights/cards", headers=headers).json()
        self.assertTrue(body["weekly_challenges"])
        for c in body["weekly_challenges"]:
            self.assertGreater(c["target"], 0, c["id"])
            self.assertGreaterEqual(c["progress"], 0, c["id"])
            self.assertLessEqual(c["progress"], c["target"], c["id"])
            self.assertEqual(c["completed"], c["progress"] >= c["target"], c["id"])

    def test_narrative_card_appears_once_there_is_a_week_of_data(self):
        headers = self._seed()
        body = self.client.get("/api/v1/insights/cards", headers=headers).json()
        self.assertIsNotNone(body["narrative"])
        self.assertGreater(body["narrative"]["days"], 0)

    def test_excluded_days_do_not_reach_the_challenge_generator(self):
        """An exception day the user marked must not count towards a
        challenge - otherwise a day they explicitly said was unusual
        still scores them."""
        token = self._register(email="excl@example.com")
        headers = self._auth_headers(token)
        user_id = self.client.get("/api/v1/auth/me", headers=headers).json()["user_id"]

        from api.dependencies.services import get_history_storage_backend
        backend = self.app.dependency_overrides[get_history_storage_backend]()

        today = date.today()
        entries = _history(user_id, 30, today)
        # Mark every day of the current ISO week as an exception day.
        week = today.isocalendar()[:2]
        for e in entries:
            if date.fromisoformat(e["date"]).isocalendar()[:2] == week:
                e["excluded"] = True
        backend.commit(entries)

        body = self.client.get("/api/v1/insights/cards", headers=headers).json()
        by_id = {c["id"]: c for c in body["weekly_challenges"]}
        self.assertEqual(by_id["daily_checkin_streak"]["progress"], 0)


if __name__ == "__main__":
    unittest.main()
