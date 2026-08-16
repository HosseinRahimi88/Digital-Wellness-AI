"""
Tests: the guide greets once, and the settings panel is the same panel
everywhere.

Two reported defects, and both came from the same shape of mistake -
something that should exist once existing per page.

THE GREETING. DWMascot.init() said hello 900ms after EVERY page load,
so walking dashboard -> weekly -> coach meant being greeted three times,
and with voice on, hearing it three times. It also greeted the
anonymous sign-in screen, spending the one greeting a user is entitled
to before they had told the app who they were. A greeting belongs to
signing in; a page owes the user an explanation of itself, which it
already gives on tap.

THE SETTINGS PANEL. app.html shipped its own hardcoded copy of the
settings modal. ensureSettingsModal() reuses whatever #settingsModal it
finds, so that stale copy won - and it had never gained the Digital
guide section. The guide's own switches were therefore unreachable from
the check-in page. Reported as "the coach settings are only on the
dashboard", which is exactly what it was.

Verified in a real browser before and after: anonymous screen silent,
one greeting at login, none on five subsequent pages; guide settings
present on the check-in page and on four others.

Run: python3 -m unittest tests.test_greeting_and_settings -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
JS = FRONTEND / "assets" / "js"


class TestGreetingIsOncePerSignIn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mascot = (JS / "mascot.js").read_text(encoding="utf-8")
        cls.api = (JS / "api.js").read_text(encoding="utf-8")
        cls.app = (JS / "app.js").read_text(encoding="utf-8")

    def test_init_no_longer_greets_unconditionally(self):
        # The exact line that caused it.
        self.assertNotIn("setTimeout(() => say(pack().greeting), 900);", self.mascot)
        self.assertIn("greetOnce", self.mascot)

    def test_an_anonymous_visitor_is_not_greeted(self):
        body = self.mascot[self.mascot.index("function greetOnce(opts)"):]
        body = body[:body.index("\n  }") + 4]
        self.assertIn("window.DWApi.isAuthed", body)
        self.assertIn("if (!authed) return false;", body)

    def test_the_greeting_is_remembered_so_it_does_not_repeat(self):
        body = self.mascot[self.mascot.index("function greetOnce(opts)"):]
        body = body[:body.index("\n  }") + 4]
        self.assertIn("dwai_greeted", body)
        self.assertIn("if (greeted) return false;", body)

    def test_signing_in_and_out_both_reset_it(self):
        # Otherwise the second session of the day is never greeted, and
        # the flag becomes a one-time-ever thing rather than per-session.
        for fn in ("function setToken(t)", "function clearToken()"):
            body = self.api[self.api.index(fn):]
            body = body[:body.index("\n  }") + 4]
            self.assertIn(
                "removeItem('dwai_greeted')", body,
                f"{fn} does not reset the greeting flag",
            )

    def test_signing_in_greets_without_a_page_reload(self):
        # app.html does not navigate on sign-in, so the mascot's own
        # init() already ran while the user was anonymous and correctly
        # stayed silent. Something has to greet at that moment.
        body = self.app[self.app.index("async function afterLogin()"):]
        body = body[:body.index("$('#appNavRow').classList.remove('hidden');")]
        self.assertIn("DWMascot.greetOnce", body)

    def test_greetonce_is_exported(self):
        self.assertRegex(self.mascot, r"window\.DWMascot = \{[^}]*greetOnce")

    def test_a_browser_without_storage_still_renders(self):
        # Storage disabled must not throw out of init and take the
        # mascot - and with it the guide - down with it.
        body = self.mascot[self.mascot.index("function greetOnce(opts)"):]
        body = body[:body.index("\n  }") + 4]
        self.assertIn("catch (e)", body)


class TestOneSettingsPanelEverywhere(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.chrome = (JS / "app-chrome.js").read_text(encoding="utf-8")
        cls.app = (JS / "app.js").read_text(encoding="utf-8")
        cls.pages = sorted(FRONTEND.glob("*.html"))

    def test_no_page_carries_its_own_copy_of_the_panel(self):
        offenders = [
            p.name for p in self.pages
            if 'id="settingsModal"' in p.read_text(encoding="utf-8")
        ]
        self.assertEqual(
            offenders, [],
            f"{offenders} hardcode the settings panel; ensureSettingsModal() "
            f"reuses whatever it finds, so a stale copy silently wins",
        )

    def test_the_template_carries_the_guide_section(self):
        tpl = self.chrome[self.chrome.index("function modalTemplate()"):]
        tpl = tpl[:self.chrome.index("function ensureSettingsModal")]
        for needed in ("guideSettingsGroup", "settingsGuideSwitch",
                       "settingsGuideVoiceSwitch", "guideVoiceStatus"):
            self.assertIn(needed, tpl, f"the shared panel lost {needed}")

    def test_the_template_kept_what_the_old_copy_had(self):
        # These three lived only in app.html's copy. Deleting that copy
        # without moving them would have removed working controls.
        tpl = self.chrome[self.chrome.index("function modalTemplate()"):]
        tpl = tpl[:self.chrome.index("function ensureSettingsModal")]
        for needed in ("settingsExcludedRow", "settingsResetExcludedBtn",
                       "settingsLogoutBtn"):
            self.assertIn(needed, tpl, f"the shared panel is missing {needed}")

    def test_the_check_in_page_builds_the_panel_before_wiring_it(self):
        # It no longer exists in that page's HTML, so wiring would hit
        # null and every settings control on the page would be dead.
        body = self.app[self.app.index("function wireSettings()"):]
        body = body[:body.index("function doLogout()")]
        self.assertIn("DWChrome.ensureSettingsModal()", body)
        self.assertLess(
            body.index("ensureSettingsModal()"), body.index("$('#settingsModal')"),
            "the panel is read before it is built",
        )
        self.assertIn("if (!modal) return;", body)

    def test_every_page_that_shows_the_gear_can_build_the_panel(self):
        for page in self.pages:
            text = page.read_text(encoding="utf-8")
            if 'id="settingsBtn"' not in text and "ensureNavButtons" not in text:
                continue
            self.assertIn(
                "app-chrome.js", text,
                f"{page.name} offers settings but cannot build the panel",
            )


if __name__ == "__main__":
    unittest.main()
