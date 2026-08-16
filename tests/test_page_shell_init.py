"""Every logged-in page must bootstrap through DWShell.init().

Real bug this pins: hall.html's controller (hall-page.js) never called
DWShell.init(). That one missing call is the whole reason the Hall of
Fame rendered in English with the ambient music stopped - init() is
what applies the saved language (DWI18n.init), starts the music player
(DWMusic.init), wires the shared chrome (theme/language/logout/bell),
highlights the nav link, and redirects an anonymous visitor. Skipping
it does not fail loudly; the page just quietly loses all of that, which
is exactly why it survived until someone opened the page and noticed
the app had gone silent and English.

The check is deliberately about the CLASS of bug rather than that one
file: any future page that forgets the same call fails here.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
JS_DIR = FRONTEND / "assets" / "js"

# Pages that require a signed-in account. app.html is excluded on
# purpose: it owns the auth/onboarding/wizard flow itself and is the
# page DWShell.init() redirects TO, so it cannot depend on it.
LOGGED_IN_PAGES = [
    "dashboard.html", "weekly.html", "analytics.html", "whatif.html",
    "model-performance.html", "profile.html", "league.html", "coach.html",
    "hall.html",
]


def _script_names(page: str) -> list[str]:
    html = (FRONTEND / page).read_text(encoding="utf-8")
    return re.findall(r'src="assets/js/([a-zA-Z0-9._-]+\.js)"', html)


class TestEveryLoggedInPageInitialisesTheShell(unittest.TestCase):
    def test_shell_js_is_loaded_on_every_logged_in_page(self):
        for page in LOGGED_IN_PAGES:
            with self.subTest(page=page):
                self.assertIn("shell.js", _script_names(page))

    def test_some_script_on_each_page_actually_calls_shell_init(self):
        # Loading shell.js is not enough - a page also has to CALL it.
        callers = {
            p.name for p in JS_DIR.glob("*.js")
            if "DWShell.init" in p.read_text(encoding="utf-8")
        }
        for page in LOGGED_IN_PAGES:
            with self.subTest(page=page):
                scripts = set(_script_names(page))
                self.assertTrue(
                    scripts & callers,
                    f"{page} loads no script that calls DWShell.init() - it will "
                    f"render untranslated, with no music and no shared chrome, "
                    f"exactly like hall.html did.",
                )

    def test_hall_page_specifically_initialises_the_shell(self):
        # The named regression.
        src = (JS_DIR / "hall-page.js").read_text(encoding="utf-8")
        self.assertIn("DWShell.init", src)

    def test_no_page_controller_auto_greets_with_the_guide_on_load(self):
        # The other half of what was reported: the guide must never speak
        # unprompted when a page opens. An explain()/startTour() call is
        # only allowed when it is explicitly forced (a click).
        offenders = []
        for path in JS_DIR.glob("*.js"):
            if path.name in {"guide-tips.js", "guide-click.js"}:
                continue  # the guide's own machinery, not a page controller
            src = path.read_text(encoding="utf-8")
            for m in re.finditer(r"DWGuide\.(explain|startTour)\s*\(([^;]*)", src):
                call = m.group(2)
                if "force" not in call:
                    offenders.append(f"{path.name}: {m.group(0)[:70]}")
        self.assertEqual(
            offenders, [],
            "These auto-fire the guide on page load. Pass {force: true} from a "
            "real user action instead:\n  " + "\n  ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
