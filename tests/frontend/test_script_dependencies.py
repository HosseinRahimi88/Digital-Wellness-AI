"""
Every page must load the modules its own scripts depend on.

A missing `<script>` tag does not throw - the dependent module just sees
`window.DWSomething` as undefined and quietly takes its fallback path.
That is how the What-if simulator ended up listing its fields in English
in all four languages: whatif.js read `window.DWCoachLabels`, and
whatif.html never loaded coach-labels.js, so every lookup fell through
to the server's English schema label and nothing anywhere reported a
problem.

These tests read the real HTML and the real JS, so a page that adds a
module without its dependency fails here rather than in front of a user.
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

FRONTEND = paths.PROJECT_ROOT / "frontend"
JS_DIR = FRONTEND / "assets" / "js"

# global -> the file that defines it
PROVIDERS = {
    "DWCoachLabels": "coach/coach-labels.js",
    "DWI18n": "core/i18n.js",
    "DWOnboardingOptions": "features/onboarding-options.js",
    "DWServerText": "core/server-text.js",
    "DWCsvLibrary": "features/csv-library.js",
    "DWFieldGuide": "coach/coach-field-guide.js",
    "DWCurriculum": "coach/coach-curriculum.js",
    "DWBreakdown": "coach/coach-breakdown.js",
}

# Captures the folder too - assets/js/pages/whatif.js comes back as
# "pages/whatif.js", because that is what identifies the module now.
SCRIPT_RE = re.compile(r'assets/js/([\w.\-/]+\.js)')


def _scripts_on(page: Path) -> list[str]:
    """Script filenames in load order."""
    return SCRIPT_RE.findall(page.read_text(encoding="utf-8"))


def _reads(js_name: str, global_name: str) -> bool:
    path = JS_DIR / js_name
    if not path.exists():
        return False
    return global_name in path.read_text(encoding="utf-8")


class TestEveryPageLoadsWhatItReads(unittest.TestCase):
    def test_dependencies_are_present(self):
        failures = []
        for page in sorted(FRONTEND.glob("*.html")):
            scripts = _scripts_on(page)
            loaded = set(scripts)
            for global_name, provider in PROVIDERS.items():
                if provider in loaded:
                    continue
                readers = [
                    s for s in scripts
                    if s != provider and _reads(s, global_name)
                ]
                if readers:
                    failures.append(
                        f"{page.name} loads {readers} which read "
                        f"{global_name}, but never loads {provider}"
                    )
        self.assertEqual([], failures, "\n".join(failures))

    def test_providers_load_before_their_readers(self):
        """Order matters too: these are plain scripts, not modules.

        A reader loaded before its provider usually still works, because
        the read happens inside a function that runs later. This asserts
        the stricter, simpler rule anyway - provider first - so nobody
        has to re-derive which reads are lazy every time a script moves.
        """
        failures = []
        for page in sorted(FRONTEND.glob("*.html")):
            scripts = _scripts_on(page)
            for global_name, provider in PROVIDERS.items():
                if provider not in scripts:
                    continue
                provider_at = scripts.index(provider)
                for i, s in enumerate(scripts[:provider_at]):
                    if s != provider and _reads(s, global_name):
                        failures.append(
                            f"{page.name}: {s} (position {i}) reads "
                            f"{global_name} but {provider} loads later "
                            f"(position {provider_at})"
                        )
        self.assertEqual([], failures, "\n".join(failures))

    def test_the_check_can_fail(self):
        """A guard that cannot fail is not a guard."""
        page = FRONTEND / "whatif.html"
        scripts = _scripts_on(page)
        self.assertIn("pages/whatif.js", scripts)
        self.assertTrue(
            _reads("pages/whatif.js", "DWCoachLabels"),
            "whatif.js should read DWCoachLabels - if this changed, the "
            "dependency test above is no longer covering the bug it was "
            "written for",
        )
        self.assertNotIn(
            "definitely-not-a-real-module.js", scripts,
            "sanity check on the script parser",
        )


if __name__ == "__main__":
    unittest.main()
