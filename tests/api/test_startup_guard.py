"""
Tests: the app tells you when it was started the wrong way.

The frontend is plain HTML, so a static file server serves every page
perfectly. The app looks fine. Then sign-in returns

    501 Unsupported method ('POST')

because a static server implements GET and nothing else, while every
real action here is a POST. Nothing in that status points at the cause -
the way the app was STARTED - so a user reasonably concludes the app is
broken. One did, twice, and lost an evening to it.

Reproduced exactly before the fix: `python -m http.server` in
frontend/, GET app.html -> 200, POST /api/v1/auth/login -> 501.

The fix has three parts and this file guards all three:
  * run.py / start.bat / start.sh - one command, no way to start only
    the half that cannot answer.
  * DWApi.probe() + api-guard.js - a banner, before any password is
    typed, in the user's own language.
  * request() maps 501/405/HTML-body to a sentence instead of a status.

Run: python3 -m unittest tests.api.test_startup_guard -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

PROJECT_ROOT = paths.PROJECT_ROOT
FRONTEND = PROJECT_ROOT / "frontend"
JS_DIR = FRONTEND / "assets" / "js"

LANGUAGES = ("en", "fa", "ar", "zh")


class TestLauncher(unittest.TestCase):

    def test_the_launchers_exist(self):
        for name in ("run.py", "start.bat", "start.sh"):
            self.assertTrue((PROJECT_ROOT / name).exists(), f"{name} is missing")

    def test_run_py_starts_the_api_not_a_static_server(self):
        """Checked against executable lines only: the module docstring
        names http.server precisely because that is the mistake this
        file exists to prevent."""
        source = (PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
        self.assertIn("api.main:app", source)
        self.assertIn("uvicorn", source)

        code = re.sub(r'"""[\s\S]*?"""', "", source)     # docstrings
        code = re.sub(r"^\s*#.*$", "", code, flags=re.M)  # comments
        self.assertNotIn("http.server", code, "run.py would launch a static server")

    def test_that_check_is_not_vacuous(self):
        """Prove the stripping leaves real code behind to inspect."""
        source = (PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
        code = re.sub(r'"""[\s\S]*?"""', "", source)
        code = re.sub(r"^\s*#.*$", "", code, flags=re.M)
        self.assertIn("uvicorn.run", code)

    def test_it_explains_why_it_exists(self):
        """The next person to 'simplify' this away needs to find the
        reason attached to it."""
        source = (PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
        self.assertIn("501", source)

    def test_it_survives_a_busy_port(self):
        """Address-in-use is another unhelpful traceback at the worst
        moment - a second copy of the app is exactly what a confused
        user ends up with."""
        source = (PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
        self.assertIn("_pick_port", source)

    def test_it_reports_missing_dependencies_as_an_instruction(self):
        source = (PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
        self.assertIn("pip install -r requirements.txt", source)

    def test_the_windows_launcher_points_at_run_py(self):
        source = (PROJECT_ROOT / "start.bat").read_text(encoding="utf-8")
        self.assertIn("run.py", source)
        # cd to the script's own directory, or a double-click from
        # Explorer runs it against C:\Windows\System32.
        self.assertIn("%~dp0", source)

    def test_run_py_is_syntactically_valid(self):
        import ast
        ast.parse((PROJECT_ROOT / "run.py").read_text(encoding="utf-8"))


class TestTheClientDetectsIt(unittest.TestCase):

    def setUp(self):
        self.api = (JS_DIR / "core/api.js").read_text(encoding="utf-8")
        self.guard = (JS_DIR / "core/api-guard.js").read_text(encoding="utf-8")

    def test_501_and_405_are_recognised(self):
        """The two statuses a static file server answers a POST with."""
        self.assertIn("501", self.api)
        self.assertIn("405", self.api)
        self.assertIn("isNotTheApi", self.api)

    def test_an_html_error_body_is_recognised_too(self):
        """A directory listing or a 404 page where JSON belongs is the
        same situation from the other side."""
        self.assertIn("text/html", self.api)

    def test_the_detection_runs_before_the_generic_error_message(self):
        """Otherwise the request fails with 'Request failed (501)' and
        the explanation never runs."""
        detect = self.api.index("if (isNotTheApi(res))")
        generic = self.api.index("`Request failed (${res.status})`")
        self.assertLess(detect, generic)

    def test_the_probe_is_a_get_and_checks_the_answer(self):
        """A static server answers GET happily, so the check cannot rely
        on the request failing - it has to reject the wrong answer."""
        probe = self.api[self.api.index("async function probe()"):]
        probe = probe[:probe.index("\n  }")]
        self.assertIn("/health", probe)
        self.assertIn("not_the_api", probe)

    def test_the_explanation_exists_in_all_four_languages(self):
        for language in LANGUAGES:
            self.assertRegex(self.api, rf"\n    {language}: '", f"api.js has no {language} message")
            self.assertRegex(self.guard, rf"\n    {language}: \{{", f"api-guard.js has no {language} copy")

    def test_the_banner_names_the_command_to_run(self):
        """A warning with no instruction is just a nicer dead end."""
        self.assertIn("run.py", self.guard)
        self.assertIn("start.bat", self.guard)

    def test_the_banner_clears_itself_when_the_api_appears(self):
        self.assertIn("existing.remove()", self.guard)

    def test_the_banner_follows_a_language_change(self):
        self.assertIn("dwai:langchange", self.guard)

    def test_the_banner_is_built_with_textcontent(self):
        """It only appears when something is already wrong, which is a
        poor moment to start trusting innerHTML."""
        self.assertNotIn("innerHTML", self.guard)
        self.assertIn("textContent", self.guard)


class TestEveryPageLoadsTheGuard(unittest.TestCase):

    def _pages(self):
        return [
            p for p in sorted(FRONTEND.glob("*.html"))
            if "assets/js/core/api.js" in p.read_text(encoding="utf-8")
        ]

    def test_there_are_pages_using_the_api(self):
        self.assertGreaterEqual(len(self._pages()), 12)

    def test_each_of_them_loads_the_guard(self):
        for page in self._pages():
            self.assertIn("core/api-guard.js", page.read_text(encoding="utf-8"), page.name)

    def test_the_guard_loads_after_the_api_module_it_uses(self):
        for page in self._pages():
            source = page.read_text(encoding="utf-8")
            self.assertLess(
                source.index("assets/js/core/api.js"),
                source.index("assets/js/core/api-guard.js"),
                page.name,
            )

    def test_the_banner_has_styling(self):
        css = (FRONTEND / "assets" / "css" / "components.css").read_text(encoding="utf-8")
        self.assertIn(".api-guard-banner", css)


if __name__ == "__main__":
    unittest.main()
