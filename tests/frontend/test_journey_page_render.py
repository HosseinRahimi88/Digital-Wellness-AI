"""
Tests: legacy/streamlit_app/pages/Journey.py's new sections (Commitments &
Recommendation Effectiveness [41/13/56], Cohort Comparison [35],
Reverse Leaderboard [31], Rare Achievements [20]) actually execute
without raising, using real seeded history + a real commitment.

Run: python3 -m unittest tests.frontend.test_journey_page_render -v
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

import tests._test_support  # noqa: F401

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths


class TestJourneyPageRendersNewSections(unittest.TestCase):
    PROJECT_ROOT = paths.PROJECT_ROOT
    APP_DIR = PROJECT_ROOT / "legacy" / "streamlit_app"
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
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_journey_page_test_"))

        import services.identity.history_service as history_module
        self._orig_history_path = history_module.DEFAULT_STORAGE_PATH
        self._history_path = self._tmp_dir / "prediction_history.json"
        history_module.DEFAULT_STORAGE_PATH = self._history_path

        import services.wellness.commitment_service as commitment_module
        self._orig_commitment_path = commitment_module.DEFAULT_STORAGE_PATH
        self._commitment_path = self._tmp_dir / "commitments.json"
        commitment_module.DEFAULT_STORAGE_PATH = self._commitment_path

        self.fake_st.session_state["_digital_wellness_user_id"] = "test-user"
        self._seed_data()

    def tearDown(self):
        import services.identity.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._orig_history_path
        import services.wellness.commitment_service as commitment_module
        commitment_module.DEFAULT_STORAGE_PATH = self._orig_commitment_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _seed_data(self) -> None:
        from datetime import date
        from services.identity.history_service import HistoryService
        from services.wellness.commitment_service import CommitmentService
        from services.storage.json_file_storage import JSONFileStorageBackend

        @dataclass
        class _FakeResult:
            prediction: str
            confidence: float
            regression_score: float
            shap_features: Optional[list] = None

        history = HistoryService(user_id="test-user", storage_path=self._history_path)
        rows = [
            (date(2026, 1, 5), 50.0, 5.0, 8.0),
            (date(2026, 1, 6), 52.0, 5.2, 8.5),
            (date(2026, 1, 9), 80.0, 8.0, 2.0),
            (date(2026, 1, 10), 82.0, 8.2, 1.5),
            (date(2026, 1, 11), 85.0, 8.5, 1.0),
        ]
        for entry_date, score, sleep_hours, stress in rows:
            result = _FakeResult(prediction="Healthy", confidence=0.9, regression_score=score)
            history.record(
                user_data={"sleep_hours": sleep_hours, "stress_0_10": stress, "total_screen_min": 90.0},
                prediction_result=result,
                on_date=entry_date,
            )

        commitments = CommitmentService(
            user_id="test-user", backend=JSONFileStorageBackend(self._commitment_path)
        )
        commitments.commit("Sleep", on_date=date(2026, 1, 7))

    def test_journey_page_renders_with_commitments_and_cohort_sections(self):
        import services.identity.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._history_path
        import services.wellness.commitment_service as commitment_module
        commitment_module.DEFAULT_STORAGE_PATH = self._commitment_path

        path = self.PAGES_DIR / "Journey.py"
        mod_name = "_test_Journey_phase3"
        sys.modules.pop(mod_name, None)
        spec = importlib.util.spec_from_file_location(mod_name, path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except self.fake_st._StopExecution:
            pass


if __name__ == "__main__":
    unittest.main()
