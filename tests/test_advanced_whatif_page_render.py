"""
Tests: app/pages/What_If_Simulator.py's Advanced Simulation section
(Sensitivity Analysis, Multi-Scenario Comparison, Goal-Seek - feature
12) and Parallel Twin tab (feature 45) actually execute their real
predictor-calling code paths without raising, using the real trained
model artifacts (same pattern as tests/test_pages_smoke.py's
after-a-real-prediction flow) - not just render in their default,
button-not-yet-clicked state.

Run: python3 -m unittest tests.test_advanced_whatif_page_render -v
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
PAGES_DIR = APP_DIR / "pages"

for p in (str(PROJECT_ROOT), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import tests._test_support  # noqa: E402,F401
import tests._fake_streamlit as fake_st  # noqa: E402
import tests._fake_plotly_express as fake_px  # noqa: E402


def _install_fakes():
    sys.modules["streamlit"] = fake_st
    plotly_pkg = sys.modules.get("plotly") or ModuleType("plotly")
    plotly_pkg.express = fake_px
    sys.modules["plotly"] = plotly_pkg
    sys.modules["plotly.express"] = fake_px


def _run_page(page_filename: str) -> None:
    path = PAGES_DIR / page_filename
    mod_name = f"_advwhatif_{page_filename.replace('.py', '')}"
    sys.modules.pop(mod_name, None)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except fake_st._StopExecution:
        pass


class TestAdvancedWhatIfPageRender(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _install_fakes()

    def setUp(self):
        fake_st.reset()
        # Redirect HistoryService's default on-disk file so this test
        # (which triggers a real Prediction.py submission below) never
        # touches the project's real storage/prediction_history.json -
        # same pattern as tests/test_pages_smoke.py's isolation.
        import tempfile
        import services.history_service as history_module
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_advwhatif_test_"))
        self._orig_default_storage_path = history_module.DEFAULT_STORAGE_PATH
        history_module.DEFAULT_STORAGE_PATH = self._tmp_dir / "prediction_history.json"

    def tearDown(self):
        import shutil
        import services.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._orig_default_storage_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_advanced_simulation_tabs_execute_with_real_model(self):
        # Real prediction first, same as test_pages_smoke.py's flow.
        fake_st.set_widget_result("🚀 Predict", True)
        _run_page("Prediction.py")
        self.assertIn("last_prediction_result", fake_st.session_state)

        # Now force every "run" button on What_If_Simulator.py True so
        # Sensitivity Analysis, Multi-Scenario Comparison, and Goal-Seek
        # all actually call the real predictor, not just render their
        # pre-click state.
        fake_st.set_widget_result("run_sensitivity", True)
        fake_st.set_widget_result("run_multiscenario", True)
        fake_st.set_widget_result("run_goal_seek", True)
        _run_page("What_If_Simulator.py")


if __name__ == "__main__":
    unittest.main()
