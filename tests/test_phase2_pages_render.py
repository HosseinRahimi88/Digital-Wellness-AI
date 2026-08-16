"""
Tests: app/pages/Analytics.py's "Relationships & Opportunities" section
and app/pages/Dashboard.py's Critical Risk Alerts banner actually
execute without raising, using real seeded history (via a real
HistoryService against a temp storage file) rich enough to clear every
Phase 2 minimum-data threshold - same rationale/pattern as
tests/test_analytics_behavioral_patterns.py's page-render test.

Run: python3 -m unittest tests.test_phase2_pages_render -v
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


class _Phase2PageRenderTestBase(unittest.TestCase):
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
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_phase2_page_test_"))

        import services.history_service as history_module
        self._orig_default_storage_path = history_module.DEFAULT_STORAGE_PATH
        self._storage_path = self._tmp_dir / "prediction_history.json"
        history_module.DEFAULT_STORAGE_PATH = self._storage_path

        self.fake_st.session_state["_digital_wellness_user_id"] = "test-user"

    def tearDown(self):
        import services.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._orig_default_storage_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _run_page(self, page_filename: str, mod_name: str) -> None:
        path = self.PAGES_DIR / page_filename
        sys.modules.pop(mod_name, None)
        spec = importlib.util.spec_from_file_location(mod_name, path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # must not raise
        except self.fake_st._StopExecution:
            pass  # normal, intentional halt - not a bug


class TestAnalyticsRelationshipsSectionRenders(_Phase2PageRenderTestBase):

    def _seed_rich_history(self) -> None:
        """Real HistoryService.record() calls with enough varied
        entries (different weekdays, different check-in hours, and a
        real linear health_score<->sleep_hours relationship) to clear
        every Phase 2 threshold: correlation (6+), golden hour (5+
        entries, 3+ distinct hours), leverage day (3+ per weekday)."""
        from datetime import date
        from services.history_service import HistoryService

        @dataclass
        class _FakeResult:
            prediction: str
            confidence: float
            regression_score: float
            shap_features: Optional[list] = None

        service = HistoryService(user_id="test-user", storage_path=self._storage_path)

        # (date, score, sleep_hours, weekday-matching hour)
        rows = [
            (date(2026, 1, 5), 50.0, 5.0, 8),    # Monday
            (date(2026, 1, 12), 90.0, 9.0, 9),   # Monday
            (date(2026, 1, 19), 30.0, 4.0, 10),  # Monday (high variance day)
            (date(2026, 1, 6), 70.0, 7.0, 14),   # Tuesday
            (date(2026, 1, 13), 71.0, 7.1, 14),  # Tuesday (steady)
            (date(2026, 1, 20), 69.0, 6.9, 20),  # Tuesday
            (date(2026, 1, 7), 80.0, 8.0, 20),   # Wednesday
        ]
        for entry_date, score, sleep_hours, hour in rows:
            result = _FakeResult(prediction="Healthy", confidence=0.85, regression_score=score)
            service.record(
                user_data={"sleep_hours": sleep_hours, "total_screen_min": 200},
                prediction_result=result,
                on_date=entry_date,
            )
            all_entries = service.storage.read_all()
            for e in all_entries:
                if e.get("user_id") == "test-user" and e.get("date") == entry_date.isoformat():
                    e["recorded_at"] = f"{entry_date.isoformat()}T{hour:02d}:00:00"
            service.storage.commit(all_entries)

    def test_analytics_page_renders_relationships_section(self):
        self._seed_rich_history()
        import services.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._storage_path
        self._run_page("Analytics.py", "_test_Analytics_phase2")


class TestDashboardRiskAlertsRenders(_Phase2PageRenderTestBase):

    def _seed_at_risk_history(self) -> None:
        from datetime import date
        from services.history_service import HistoryService

        @dataclass
        class _FakeResult:
            prediction: str
            confidence: float
            regression_score: float
            shap_features: Optional[list] = None

        service = HistoryService(user_id="test-user", storage_path=self._storage_path)
        rows = [
            (date(2026, 1, 5), "Healthy", 90.0),
            (date(2026, 1, 6), "Healthy", 70.0),
            (date(2026, 1, 7), "At Risk", 30.0),
            (date(2026, 1, 8), "At Risk", 25.0),  # consecutive -> critical
        ]
        for entry_date, health_class, score in rows:
            result = _FakeResult(prediction=health_class, confidence=0.8, regression_score=score)
            service.record(
                user_data={"total_screen_min": 300},
                prediction_result=result,
                on_date=entry_date,
            )

    def test_dashboard_page_renders_with_critical_risk_alert(self):
        self._seed_at_risk_history()
        import services.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._storage_path
        self._run_page("Dashboard.py", "_test_Dashboard_phase2")

    def test_dashboard_page_renders_with_no_risk_history(self):
        from datetime import date
        from services.history_service import HistoryService

        @dataclass
        class _FakeResult:
            prediction: str
            confidence: float
            regression_score: float
            shap_features: Optional[list] = None

        service = HistoryService(user_id="test-user", storage_path=self._storage_path)
        service.record(
            user_data={"total_screen_min": 200},
            prediction_result=_FakeResult(prediction="Healthy", confidence=0.9, regression_score=85.0),
            on_date=date(2026, 1, 5),
        )
        import services.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._storage_path
        self._run_page("Dashboard.py", "_test_Dashboard_phase2_no_risk")


if __name__ == "__main__":
    unittest.main()
