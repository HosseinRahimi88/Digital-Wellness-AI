"""
Tests: RiskAlertService (rule-based Critical Risk Alerts, feature 06).

Run: python3 -m unittest tests.test_risk_alert_service -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401  (sys.path bootstrap)

from services.risk_alert_service import RiskAlertService


def _entry(date_str, health_score, health_class="Healthy", confidence=0.8, **fields):
    entry = {
        "user_id": "alice",
        "date": date_str,
        "day_of_week": "Monday",
        "health_score": health_score,
        "health_class": health_class,
        "confidence": confidence,
        "recorded_at": f"{date_str}T08:00:00",
    }
    entry.update(fields)
    return entry


class TestRiskAlertService(unittest.TestCase):

    def test_no_entries_no_alerts(self):
        self.assertEqual(RiskAlertService.evaluate([]), [])

    def test_healthy_stable_history_has_no_alerts(self):
        entries = [_entry(f"2026-01-{5+i:02d}", 80.0 + i, "Healthy") for i in range(5)]
        self.assertEqual(RiskAlertService.evaluate(entries), [])

    def test_single_at_risk_checkin_is_a_warning_not_critical(self):
        entries = [
            _entry("2026-01-05", 80.0, "Healthy"),
            _entry("2026-01-06", 30.0, "At Risk", confidence=0.75),
        ]
        alerts = RiskAlertService.evaluate(entries)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, "warning")
        self.assertIn("At Risk", alerts[0].title)

    def test_consecutive_at_risk_escalates_to_critical(self):
        entries = [
            _entry("2026-01-05", 30.0, "At Risk"),
            _entry("2026-01-06", 28.0, "At Risk"),
        ]
        alerts = RiskAlertService.evaluate(entries)
        self.assertTrue(any(a.severity == "critical" for a in alerts))

    def test_decline_streak_detected(self):
        entries = [
            _entry("2026-01-05", 90.0, "Healthy"),
            _entry("2026-01-06", 80.0, "Healthy"),
            _entry("2026-01-07", 70.0, "Healthy"),
            _entry("2026-01-08", 60.0, "Healthy"),  # 3-in-a-row decline, 30pt total drop
        ]
        alerts = RiskAlertService.evaluate(entries)
        self.assertTrue(any(a.title == "Declining Trend" for a in alerts))

    def test_small_decline_does_not_trigger(self):
        # Declining, but the total drop (< DECLINE_STREAK_MIN_TOTAL_DROP)
        # is too small to be worth flagging.
        entries = [
            _entry("2026-01-05", 82.0, "Healthy"),
            _entry("2026-01-06", 81.0, "Healthy"),
            _entry("2026-01-07", 80.0, "Healthy"),
            _entry("2026-01-08", 79.0, "Healthy"),
        ]
        alerts = RiskAlertService.evaluate(entries)
        self.assertFalse(any(a.title == "Declining Trend" for a in alerts))

    def test_rising_scores_never_flagged_as_decline(self):
        entries = [_entry(f"2026-01-{5+i:02d}", 50.0 + i * 10, "Healthy") for i in range(5)]
        alerts = RiskAlertService.evaluate(entries)
        self.assertFalse(any(a.title == "Declining Trend" for a in alerts))

    def test_deviation_alert_reuses_analytics_service_exceptions(self):
        # 4 steady days, then a real statistical outlier drop today.
        entries = [
            _entry("2026-01-05", 78.0, "Healthy"),
            _entry("2026-01-06", 82.0, "Healthy"),
            _entry("2026-01-07", 80.0, "Healthy"),
            _entry("2026-01-08", 79.0, "Healthy"),
            _entry("2026-01-09", 20.0, "Healthy"),  # outlier, but not "At Risk" class
        ]
        alerts = RiskAlertService.evaluate(entries)
        self.assertTrue(any(a.title == "Unusual Day Detected" for a in alerts))

    def test_alerts_sorted_critical_first(self):
        entries = [
            _entry("2026-01-05", 90.0, "Healthy"),
            _entry("2026-01-06", 80.0, "Healthy"),
            _entry("2026-01-07", 70.0, "Healthy"),
            _entry("2026-01-08", 30.0, "At Risk"),
            _entry("2026-01-09", 25.0, "At Risk"),  # decline + consecutive at-risk
        ]
        alerts = RiskAlertService.evaluate(entries)
        self.assertGreaterEqual(len(alerts), 2)
        self.assertEqual(alerts[0].severity, "critical")

    def test_missing_health_class_does_not_crash(self):
        entries = [
            {"user_id": "alice", "date": "2026-01-05", "day_of_week": "Monday", "health_score": 80.0},
            {"user_id": "alice", "date": "2026-01-06", "day_of_week": "Tuesday", "health_score": 40.0},
        ]
        # Should not raise even with no health_class/confidence fields.
        alerts = RiskAlertService.evaluate(entries)
        self.assertIsInstance(alerts, list)


class TestAlertTextIsTranslated(unittest.TestCase):
    """Every alert used to reach the client as flat English only - the
    insight-cards panel rendered `a.message`/`a.action` straight from
    these fields, in whatever language RiskAlertService happened to
    build them in (always English), regardless of the reader's own
    setting. text_i18n exists so the client can pick its own language
    instead; these tests are against the real numbers each rule
    produces, not synthetic ones, since a template with an unfilled
    placeholder is a bug the numbers themselves would expose."""

    LANGS = ("en", "fa", "ar", "zh")

    def _assert_complete(self, alert):
        self.assertIn("title", alert.text_i18n)
        self.assertIn("message", alert.text_i18n)
        for lang in self.LANGS:
            self.assertTrue(alert.text_i18n["title"].get(lang, "").strip(), f"title.{lang} empty")
            self.assertTrue(alert.text_i18n["message"].get(lang, "").strip(), f"message.{lang} empty")
            # A template placeholder that never got filled would leave a
            # literal "{...}" in the rendered sentence.
            self.assertNotIn("{", alert.text_i18n["message"][lang], f"message.{lang} has an unfilled placeholder")
        if alert.action is not None:
            self.assertIn("action", alert.text_i18n)
            for lang in self.LANGS:
                self.assertTrue(alert.text_i18n["action"].get(lang, "").strip(), f"action.{lang} empty")
        else:
            self.assertNotIn("action", alert.text_i18n)

    def test_consecutive_at_risk_alert(self):
        entries = [_entry("2026-01-05", 30.0, "At Risk"), _entry("2026-01-06", 28.0, "At Risk")]
        alerts = RiskAlertService.evaluate(entries)
        critical = next(a for a in alerts if a.severity == "critical")
        self._assert_complete(critical)
        self.assertIn("2", critical.text_i18n["message"]["en"])  # the real streak length
        self.assertIn("در معرض خطر", critical.text_i18n["message"]["fa"])  # translated class name

    def test_single_at_risk_alert_with_confidence(self):
        entries = [_entry("2026-01-05", 80.0, "Healthy"), _entry("2026-01-06", 30.0, "At Risk", confidence=0.734)]
        alerts = RiskAlertService.evaluate(entries)
        warning = next(a for a in alerts if a.title == "Latest Check-in: At Risk")
        self._assert_complete(warning)
        self.assertIn("73", warning.text_i18n["message"]["en"])  # the real confidence, rounded
        self.assertIn("2026-01-06", warning.text_i18n["message"]["fa"])  # the real date

    def test_single_at_risk_alert_without_confidence(self):
        entries = [
            {"user_id": "a", "date": "2026-01-05", "day_of_week": "Monday", "health_score": 80.0, "health_class": "Healthy"},
            {"user_id": "a", "date": "2026-01-06", "day_of_week": "Tuesday", "health_score": 30.0, "health_class": "At Risk"},
        ]
        alerts = RiskAlertService.evaluate(entries)
        warning = next(a for a in alerts if a.title == "Latest Check-in: At Risk")
        self._assert_complete(warning)
        for lang in self.LANGS:
            self.assertNotIn("%", warning.text_i18n["message"][lang])

    def test_declining_trend_alert(self):
        entries = [
            _entry("2026-01-05", 90.0, "Healthy"), _entry("2026-01-06", 80.0, "Healthy"),
            _entry("2026-01-07", 70.0, "Healthy"), _entry("2026-01-08", 60.0, "Healthy"),
        ]
        alerts = RiskAlertService.evaluate(entries)
        decline = next(a for a in alerts if a.title == "Declining Trend")
        self._assert_complete(decline)
        self.assertIn("90.0", decline.text_i18n["message"]["en"])
        self.assertIn("60.0", decline.text_i18n["message"]["zh"])

    def test_unusual_day_alert_has_translated_field_name_and_no_action(self):
        entries = [
            _entry("2026-01-05", 78.0, "Healthy"), _entry("2026-01-06", 82.0, "Healthy"),
            _entry("2026-01-07", 80.0, "Healthy"), _entry("2026-01-08", 79.0, "Healthy"),
            _entry("2026-01-09", 20.0, "Healthy"),
        ]
        alerts = RiskAlertService.evaluate(entries)
        unusual = next(a for a in alerts if a.title == "Unusual Day Detected")
        self._assert_complete(unusual)
        self.assertIsNone(unusual.action)
        self.assertNotIn("health_score", unusual.text_i18n["message"]["en"])  # the raw field key, not the label
        self.assertIn("امتیاز سلامت", unusual.text_i18n["message"]["fa"])  # the translated field label

    def test_the_completeness_check_can_actually_fail(self):
        # Prove _assert_complete is not vacuously true.
        from services.risk_alert_service import RiskAlert
        broken = RiskAlert(severity="info", title="X", message="Y", text_i18n={"title": {"en": "X"}})
        with self.assertRaises(AssertionError):
            self._assert_complete(broken)


if __name__ == "__main__":
    unittest.main()
