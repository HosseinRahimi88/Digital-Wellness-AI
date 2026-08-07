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


if __name__ == "__main__":
    unittest.main()
