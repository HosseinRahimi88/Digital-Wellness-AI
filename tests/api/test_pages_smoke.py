"""
Tests: execute every real, unmodified `legacy/streamlit_app/pages/*.py` module
top-to-bottom (import + all top-level widget/render calls) using a
headless fake `streamlit`/`plotly.express` (see tests/_fake_streamlit.py
for why - no network access to install the real packages here).

This directly covers section 9 of the polish request: "Streamlit را
اجرا کن ... تمام صفحات ... بدون exception باز شوند" (run every page,
confirm none raises), for both the "fresh session, no prediction yet"
state and the "after a real prediction" state - without needing the
real `streamlit` package installed.

Run: python3 -m unittest tests.api.test_pages_smoke -v
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

PROJECT_ROOT = paths.PROJECT_ROOT
APP_DIR = PROJECT_ROOT / "legacy" / "streamlit_app"
PAGES_DIR = APP_DIR / "pages"

for p in (str(PROJECT_ROOT), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import tests._test_support  # noqa: E402,F401  (installs offline shap stub)
import tests._fake_streamlit as fake_st  # noqa: E402
import tests._fake_plotly_express as fake_px  # noqa: E402


def _install_fakes():
    """Register the fake streamlit/plotly.express *before* any page or
    component module is (re)imported, so every `import streamlit as st`
    / `import plotly.express as px` anywhere in the app resolves to
    these stubs instead of failing with ModuleNotFoundError."""
    sys.modules["streamlit"] = fake_st

    plotly_pkg = sys.modules.get("plotly") or ModuleType("plotly")
    plotly_pkg.express = fake_px
    sys.modules["plotly"] = plotly_pkg
    sys.modules["plotly.express"] = fake_px


def _run_page(page_filename: str) -> None:
    """Execute a page script fresh (bypassing Python's module cache, the
    same way Streamlit re-runs the whole script on every interaction)."""
    path = PAGES_DIR / page_filename
    mod_name = f"_smoke_{page_filename.replace('.py', '')}"
    sys.modules.pop(mod_name, None)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except fake_st._StopExecution:
        # st.stop() - a normal, intentional halt (e.g. "no prediction
        # yet, go run one first"), not a bug.
        pass


ALL_PAGES = [
    "Prediction.py",
    "AI_Coach.py",
    "Analytics.py",
    "Weekly_Insights.py",
    "What_If_Simulator.py",
    "Model_Performance.py",
    "About.py",
    "Login.py",
    "Onboarding.py",
    "Dashboard.py",
    "Profile.py",
    "Journey.py",
    "Family.py",
]


class TestPagesSmoke(unittest.TestCase):
    """Every page must execute without raising, in both states a real
    user actually hits: before running any prediction, and after."""

    @classmethod
    def setUpClass(cls):
        _install_fakes()
        # Home.py bootstraps sys.path itself but isn't under legacy/streamlit_app/pages/.
        cls._home_path = APP_DIR / "Home.py"

    def setUp(self):
        fake_st.reset()
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="wellness_smoke_test_"))
        # Redirect HistoryService's default on-disk file so this test
        # never touches the project's real storage/prediction_history.json.
        import services.identity.history_service as history_module
        self._orig_default_storage_path = history_module.DEFAULT_STORAGE_PATH
        history_module.DEFAULT_STORAGE_PATH = self._tmp_dir / "prediction_history.json"

    def tearDown(self):
        import services.identity.history_service as history_module
        history_module.DEFAULT_STORAGE_PATH = self._orig_default_storage_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------
    def test_home_page_loads_without_exception(self):
        mod_name = "_smoke_Home"
        sys.modules.pop(mod_name, None)
        spec = importlib.util.spec_from_file_location(mod_name, self._home_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # should never call st.stop()

    def test_every_page_loads_without_exception_before_any_prediction(self):
        """Fresh session: session_state is empty. Every page other than
        Prediction/Model_Performance/About should hit its early
        `st.stop()` guard cleanly - not raise."""
        for page in ALL_PAGES:
            with self.subTest(page=page):
                fake_st.session_state.clear()
                _run_page(page)

    def test_every_page_loads_without_exception_after_a_real_prediction(self):
        """Simulate: user submits the Prediction form (real
        ValidationService -> real PredictionService -> real SHAP), then
        visits every other page with that real result in session_state -
        exactly the flow the app's own pages describe in their
        docstrings ('reads the *real* last prediction'). Uses the real,
        unmodified trained model artifacts - not mocks."""
        fake_st.session_state.clear()
        fake_st.set_widget_result("🚀 Predict", True)
        _run_page("Prediction.py")

        self.assertIn("last_prediction_result", fake_st.session_state)
        self.assertIn("last_user_data", fake_st.session_state)
        self.assertIn("last_persona", fake_st.session_state)

        for page in ["AI_Coach.py", "Analytics.py", "Weekly_Insights.py", "What_If_Simulator.py", "Journey.py"]:
            with self.subTest(page=page):
                _run_page(page)

    def test_model_performance_page_reads_real_metrics_without_exception(self):
        fake_st.session_state.clear()
        _run_page("Model_Performance.py")


if __name__ == "__main__":
    unittest.main()
