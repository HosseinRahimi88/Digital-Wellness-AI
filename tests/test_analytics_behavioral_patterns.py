"""
Tests: AnalyticsService's Behavioral Patterns methods -
compute_weekly_behavioral_pattern (05), compute_typical_day_profile (32),
build_hour_weekday_heatmap (50), detect_exception_days (51).

All four take plain entry dicts shaped exactly like what
HistoryService.get_all() returns (this is how AnalyticsService's
existing methods - build_score_history_frame, build_weekday_pattern -
are already tested/used), so entries are hand-built here rather than
routed through a real HistoryService instance, which would only add
indirection without changing what's under test.

Run: python3 -m unittest tests.test_analytics_behavioral_patterns -v
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional

import tests._test_support  # noqa: F401  (sys.path bootstrap)

from services.analytics_service import AnalyticsService


def _entry(
    date_str: str,
    day_of_week: str,
    health_score: float,
    recorded_at: str,
    **fields,
) -> dict:
    entry = {
        "user_id": "alice",
        "date": date_str,
        "day_of_week": day_of_week,
        "health_score": health_score,
        "recorded_at": recorded_at,
    }
    entry.update(fields)
    return entry


class TestWeeklyBehavioralPattern(unittest.TestCase):
    """Feature 05."""

    def test_none_below_minimum_entries(self):
        entries = [_entry("2026-01-05", "Monday", 80.0, "2026-01-05T08:00:00")]
        self.assertIsNone(AnalyticsService.compute_weekly_behavioral_pattern(entries))

    def test_none_with_only_one_weekday_represented(self):
        # Four entries, but all Mondays - no weekday *variety* yet.
        entries = [
            _entry(f"2026-01-{5 + 7*i:02d}", "Monday", 80.0, "2026-01-05T08:00:00", sleep_hours=7.0)
            for i in range(4)
        ]
        self.assertIsNone(AnalyticsService.compute_weekly_behavioral_pattern(entries))

    def test_computes_correct_weekday_averages(self):
        entries = [
            _entry("2026-01-05", "Monday", 60.0, "2026-01-05T08:00:00", sleep_hours=6.0),
            _entry("2026-01-12", "Monday", 70.0, "2026-01-12T08:00:00", sleep_hours=6.5),
            _entry("2026-01-06", "Tuesday", 90.0, "2026-01-06T08:00:00", sleep_hours=8.0),
            _entry("2026-01-13", "Tuesday", 90.0, "2026-01-13T08:00:00", sleep_hours=8.0),
        ]
        result = AnalyticsService.compute_weekly_behavioral_pattern(entries)
        self.assertIsNotNone(result)
        table = result["table"]
        self.assertAlmostEqual(table.loc["Monday", "health_score"], 65.0)
        self.assertAlmostEqual(table.loc["Tuesday", "health_score"], 90.0)
        # Rounded to 1 decimal for display (round-half-to-even: 6.25 -> 6.2)
        self.assertAlmostEqual(table.loc["Monday", "sleep_hours"], 6.2)
        self.assertEqual(result["best_day"], ("Tuesday", 90.0))
        self.assertEqual(result["worst_day"], ("Monday", 65.0))

    def test_missing_field_on_some_days_does_not_crash(self):
        entries = [
            _entry("2026-01-05", "Monday", 60.0, "2026-01-05T08:00:00", sleep_hours=6.0),
            _entry("2026-01-06", "Tuesday", 90.0, "2026-01-06T08:00:00"),  # no sleep_hours
            _entry("2026-01-12", "Monday", 70.0, "2026-01-12T08:00:00", sleep_hours=6.5),
            _entry("2026-01-13", "Tuesday", 80.0, "2026-01-13T08:00:00"),
        ]
        result = AnalyticsService.compute_weekly_behavioral_pattern(entries)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["table"].loc["Tuesday", "health_score"], 85.0)


class TestTypicalDayProfile(unittest.TestCase):
    """Feature 32."""

    def test_none_below_minimum_entries(self):
        entries = [_entry("2026-01-05", "Monday", 80.0, "2026-01-05T08:00:00")]
        self.assertIsNone(AnalyticsService.compute_typical_day_profile(entries))

    def test_computes_mean_and_std(self):
        entries = [
            _entry("2026-01-05", "Monday", 60.0, "2026-01-05T08:00:00", stress_0_10=2.0),
            _entry("2026-01-06", "Tuesday", 80.0, "2026-01-06T08:00:00", stress_0_10=4.0),
            _entry("2026-01-07", "Wednesday", 100.0, "2026-01-07T08:00:00", stress_0_10=6.0),
        ]
        result = AnalyticsService.compute_typical_day_profile(entries)
        self.assertIsNotNone(result)
        profile = result["profile"].set_index("Metric")
        self.assertAlmostEqual(profile.loc["Wellness Score", "Typical (avg)"], 80.0)
        # sample std dev (ddof=1) of [60, 80, 100] is 20.0
        self.assertAlmostEqual(profile.loc["Wellness Score", "Consistency (std dev)"], 20.0)

    def test_weekday_vs_weekend_split(self):
        entries = [
            _entry("2026-01-05", "Monday", 50.0, "2026-01-05T08:00:00"),
            _entry("2026-01-06", "Tuesday", 50.0, "2026-01-06T08:00:00"),
            _entry("2026-01-10", "Saturday", 90.0, "2026-01-10T08:00:00"),
        ]
        result = AnalyticsService.compute_typical_day_profile(entries)
        self.assertIsNotNone(result["weekday_vs_weekend"])
        self.assertAlmostEqual(result["weekday_vs_weekend"]["weekday_avg"], 50.0)
        self.assertAlmostEqual(result["weekday_vs_weekend"]["weekend_avg"], 90.0)

    def test_latest_vs_typical(self):
        entries = [
            _entry("2026-01-05", "Monday", 50.0, "2026-01-05T08:00:00"),
            _entry("2026-01-06", "Tuesday", 50.0, "2026-01-06T08:00:00"),
            _entry("2026-01-07", "Wednesday", 100.0, "2026-01-07T08:00:00"),
        ]
        result = AnalyticsService.compute_typical_day_profile(entries)
        lvt = result["latest_vs_typical"]
        self.assertEqual(lvt["latest_date"], "2026-01-07")
        self.assertAlmostEqual(lvt["latest_score"], 100.0)
        # Rounded to 1 decimal for display: 200/3 = 66.666... -> 66.7
        self.assertAlmostEqual(lvt["typical_score"], 66.7, places=1)


class TestHourWeekdayHeatmap(unittest.TestCase):
    """Feature 50."""

    def test_none_below_minimum_entries(self):
        entries = [_entry("2026-01-05", "Monday", 80.0, "2026-01-05T08:00:00")]
        self.assertIsNone(AnalyticsService.build_hour_weekday_heatmap(entries))

    def test_uses_real_recorded_at_hour(self):
        entries = [
            _entry("2026-01-05", "Monday", 60.0, "2026-01-05T08:15:00"),
            _entry("2026-01-06", "Tuesday", 90.0, "2026-01-06T21:45:00"),
            _entry("2026-01-12", "Monday", 60.0, "2026-01-12T08:05:00"),
        ]
        result = AnalyticsService.build_hour_weekday_heatmap(entries)
        self.assertIsNotNone(result)
        scores = result["scores"]
        self.assertAlmostEqual(scores.loc["Monday", 8], 60.0)
        self.assertAlmostEqual(scores.loc["Tuesday", 21], 90.0)
        self.assertEqual(result["counts"].loc["Monday", 8], 2)

    def test_entries_without_recorded_at_are_skipped_not_crashed(self):
        entries = [
            _entry("2026-01-05", "Monday", 60.0, "2026-01-05T08:15:00"),
            _entry("2026-01-13", "Tuesday", 70.0, "2026-01-13T09:00:00"),
            {"user_id": "alice", "date": "2026-01-06", "day_of_week": "Tuesday", "health_score": 90.0},
            _entry("2026-01-12", "Monday", 60.0, "2026-01-12T08:05:00"),
        ]
        # Should not raise even though one entry has no recorded_at - and
        # the remaining 3 valid entries still clear the minimum.
        result = AnalyticsService.build_hour_weekday_heatmap(entries)
        self.assertIsNotNone(result)


class TestExceptionDetective(unittest.TestCase):
    """Feature 51."""

    def test_none_below_minimum_entries(self):
        entries = [
            _entry(f"2026-01-{5+i:02d}", "Monday", 80.0, "2026-01-05T08:00:00")
            for i in range(3)
        ]
        self.assertIsNone(AnalyticsService.detect_exception_days(entries))

    def test_flags_a_real_outlier_day(self):
        # Four normal days around score ~80, one big drop.
        entries = [
            _entry("2026-01-05", "Monday", 78.0, "2026-01-05T08:00:00"),
            _entry("2026-01-06", "Tuesday", 82.0, "2026-01-06T08:00:00"),
            _entry("2026-01-07", "Wednesday", 80.0, "2026-01-07T08:00:00"),
            _entry("2026-01-08", "Thursday", 79.0, "2026-01-08T08:00:00"),
            _entry("2026-01-09", "Friday", 20.0, "2026-01-09T08:00:00"),  # outlier
        ]
        exceptions = AnalyticsService.detect_exception_days(entries)
        self.assertIsNotNone(exceptions)
        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0]["date"], "2026-01-09")
        self.assertEqual(exceptions[0]["deviations"][0]["field"], "health_score")
        self.assertLess(exceptions[0]["deviations"][0]["z_score"], 0)

    def test_empty_list_when_no_field_has_outliers(self):
        entries = [
            _entry("2026-01-05", "Monday", 80.0, "2026-01-05T08:00:00"),
            _entry("2026-01-06", "Tuesday", 81.0, "2026-01-06T08:00:00"),
            _entry("2026-01-07", "Wednesday", 79.0, "2026-01-07T08:00:00"),
            _entry("2026-01-08", "Thursday", 80.0, "2026-01-08T08:00:00"),
            _entry("2026-01-09", "Friday", 80.0, "2026-01-09T08:00:00"),
        ]
        exceptions = AnalyticsService.detect_exception_days(entries)
        self.assertEqual(exceptions, [])

    def test_constant_field_does_not_divide_by_zero(self):
        # sleep_hours is identical every day (std dev 0) - must be
        # skipped as a baseline, not raise ZeroDivisionError.
        entries = [
            _entry("2026-01-05", "Monday", 78.0, "2026-01-05T08:00:00", sleep_hours=7.0),
            _entry("2026-01-06", "Tuesday", 82.0, "2026-01-06T08:00:00", sleep_hours=7.0),
            _entry("2026-01-07", "Wednesday", 80.0, "2026-01-07T08:00:00", sleep_hours=7.0),
            _entry("2026-01-08", "Thursday", 79.0, "2026-01-08T08:00:00", sleep_hours=7.0),
            _entry("2026-01-09", "Friday", 79.0, "2026-01-09T08:00:00", sleep_hours=7.0),
        ]
        # Should simply not raise.
        exceptions = AnalyticsService.detect_exception_days(entries)
        self.assertIsInstance(exceptions, list)


class TestAnalyticsPageRendersBehavioralPatterns(unittest.TestCase):
    """
    Unit tests above only exercise AnalyticsService in isolation - they
    never prove app/pages/Analytics.py's new "Behavioral Patterns"
    section (4 st.tabs, px.imshow, selectbox, expanders) actually
    executes without raising. tests/test_pages_smoke.py's own fixture
    always starts from *empty* history, so that section's `if
    _all_entries:` branch is never entered there either. This fills
    real history first (via a real HistoryService against a temp
    storage file - same pattern as tests/test_history_storage.py) so
    the new section actually runs, using the same headless
    streamlit/plotly.express stubs as test_pages_smoke.py.

    Run: python3 -m unittest tests.test_analytics_behavioral_patterns -v
    """

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    APP_DIR = PROJECT_ROOT / "app"
    PAGES_DIR = APP_DIR / "pages"

    @classmethod
    def setUpClass(cls):
        import tests._fake_streamlit as fake_st
        import tests._fake_plotly_express as fake_px

        cls.fake_st = fake_st
        for p in (str(cls.PROJECT_ROOT), str(cls.APP_DIR)):
            if p not in sys.path:
                sys.path.insert(0, p)

        sys.modules["streamlit"] = fake_st
        plotly_pkg = sys.modules.get("plotly") or ModuleType("plotly")
        plotly_pkg.express = fake_px
        sys.modules["plotly"] = plotly_pkg
        sys.modules["plotly.express"] = fake_px

    def setUp(self):
        self.fake_st.reset()
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_analytics_page_test_"))

        import services.history_service as history_module
        self._orig_default_storage_path = history_module.DEFAULT_STORAGE_PATH
        self._storage_path = self._tmp_dir / "prediction_history.json"
        history_module.DEFAULT_STORAGE_PATH = self._storage_path

        from services.history_service import HistoryService
        self._seed_history(HistoryService(user_id="test-user", storage_path=self._storage_path))

    def tearDown(self):
        import services.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._orig_default_storage_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    @staticmethod
    def _seed_history(service) -> None:
        """Real HistoryService.record() calls (real code path, same as
        production) with varied dates/times so every Behavioral
        Patterns chart's minimum-data threshold is cleared."""
        from datetime import date

        @dataclass
        class _FakeResult:
            prediction: str
            confidence: float
            regression_score: float
            shap_features: Optional[list] = None

        rows = [
            (date(2026, 1, 5), 60.0, 6.0, 8),    # Monday, morning
            (date(2026, 1, 6), 90.0, 8.0, 21),   # Tuesday, evening
            (date(2026, 1, 7), 80.0, 7.0, 9),    # Wednesday
            (date(2026, 1, 8), 79.0, 7.0, 10),   # Thursday
            (date(2026, 1, 9), 20.0, 4.0, 23),   # Friday - outlier
            (date(2026, 1, 12), 65.0, 6.5, 8),   # Monday
            (date(2026, 1, 13), 88.0, 8.0, 21),  # Tuesday
        ]
        for entry_date, score, sleep_hours, hour in rows:
            result = _FakeResult(prediction="Healthy", confidence=0.9, regression_score=score)
            service.record(
                user_data={"sleep_hours": sleep_hours, "total_screen_min": 200},
                prediction_result=result,
                on_date=entry_date,
            )
            # HistoryService.record() stamps recorded_at with datetime.now();
            # overwrite just that field with our intended check-in hour so
            # the Hour x Weekday Heatmap has real hour variety to chart,
            # while every other field stays exactly what record() wrote.
            all_entries = service.storage.read_all()
            for e in all_entries:
                if e.get("user_id") == "test-user" and e.get("date") == entry_date.isoformat():
                    e["recorded_at"] = f"{entry_date.isoformat()}T{hour:02d}:00:00"
            service.storage.commit(all_entries)

    def test_analytics_page_renders_with_populated_history(self):
        import services.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._storage_path

        # get_user_id() reads st.session_state; force it to the same
        # user_id the seeded history was written under.
        self.fake_st.session_state["_digital_wellness_user_id"] = "test-user"

        path = self.PAGES_DIR / "Analytics.py"
        mod_name = "_test_Analytics_behavioral_patterns"
        sys.modules.pop(mod_name, None)
        spec = importlib.util.spec_from_file_location(mod_name, path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # must not raise
        except self.fake_st._StopExecution:
            # Expected: the page st.stop()s after Behavioral Patterns
            # once it finds no *session* prediction result - a normal,
            # intentional halt, not a bug.
            pass


if __name__ == "__main__":
    unittest.main()
