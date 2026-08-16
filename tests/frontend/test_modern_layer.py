"""
Tests: the refinement layer, and the two ways a CSS layer goes wrong.

WHAT IT IS. frontend/assets/css/modern.css is a last-loaded layer that
refines type scale, depth, focus and hover without touching the palette,
the glass surfaces or the two themes. It was written as a layer rather
than as a rewrite because the existing system is coherent and heavily
asserted on; replacing it to "modernise" would have meant re-proving
contrast in four languages and two themes to arrive somewhere no better.

THE TWO WAYS THIS BREAKS. Both are invisible in the browser you happen
to be looking at, which is exactly why they are worth a test:

  1. It stops being last. The whole design depends on load order - a
     refinement loaded before the file it refines is simply overridden,
     and the page looks untouched with no error anywhere.

  2. It defines a colour only inside a [data-theme] or media block, so
     one theme renders the other theme's text on its own background.
     Every value here has to come from a token that exists in both.

Run: python3 -m unittest tests.frontend.test_modern_layer -v
"""

from __future__ import annotations

import re
import unittest

from core import paths

FRONTEND = paths.PROJECT_ROOT / "frontend"
MODERN = FRONTEND / "assets" / "css" / "modern.css"
VARIABLES = (FRONTEND / "assets" / "css" / "variables.css").read_text(encoding="utf-8")
CSS = MODERN.read_text(encoding="utf-8")

PAGES = sorted(p for p in FRONTEND.glob("*.html"))


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class TheLayerLoadsLast(unittest.TestCase):

    def test_every_page_loads_it(self):
        self.assertTrue(PAGES, "no pages found at all")
        for page in PAGES:
            self.assertIn(
                "assets/css/modern.css", page.read_text(encoding="utf-8"),
                f"{page.name} does not load the refinement layer",
            )

    def test_it_is_the_last_stylesheet_on_every_page(self):
        """A refinement loaded before what it refines is overridden, and
        the page then looks exactly as it did with no error to notice."""
        for page in PAGES:
            hrefs = re.findall(
                r'<link rel="stylesheet" href="(assets/css/[^"]+)"',
                page.read_text(encoding="utf-8"),
            )
            self.assertTrue(hrefs, f"{page.name} loads no local stylesheets")
            self.assertEqual(
                hrefs[-1], "assets/css/modern.css",
                f"{page.name} loads {hrefs[-1]} after the refinement layer, "
                f"so the refinement is silently overridden",
            )


class TheLayerWorksInBothThemes(unittest.TestCase):

    def test_it_invents_no_colours_of_its_own(self):
        """Every colour has to come from a token defined for both
        themes. A literal hex here is a colour that works in one theme
        and is wrong in the other - the classic unreadable-page bug.

        Mask declarations are excluded, and the distinction is real
        rather than a loophole: inside a mask the value is OPACITY, not
        paint - `#000` there means "fully opaque", it renders nothing,
        and it is identical in both themes. The nav's scroll-edge fade
        is the only place this file uses one.
        """
        body = _strip_comments(CSS)
        body = re.sub(r"-?(webkit-)?mask-image\s*:[^;]+;", "", body)
        literals = re.findall(r"#[0-9a-fA-F]{3,8}\b", body)
        self.assertEqual(
            literals, [],
            f"modern.css hard-codes {literals} instead of using a token",
        )

    def test_every_token_it_reads_actually_exists(self):
        """A var() naming a token nobody defines falls back to nothing,
        and the rule quietly does not apply."""
        body = _strip_comments(CSS)
        declared = set(re.findall(r"(--[\w-]+)\s*:", body))
        declared |= set(re.findall(r"(--[\w-]+)\s*:", _strip_comments(VARIABLES)))
        # A var() with a fallback is fine either way - it says what to do.
        used = set(re.findall(r"var\((--[\w-]+)\s*\)", body))
        missing = sorted(used - declared)
        self.assertEqual(
            missing, [],
            f"modern.css reads tokens nothing defines: {missing}",
        )

    def test_the_light_theme_gets_its_own_depth(self):
        """Black shadows on a light surface read as a grey smear rather
        than as height. If the light block ever disappears, light mode
        goes back to looking flat."""
        self.assertIn('[data-theme="light"]', CSS)
        light = CSS[CSS.index('[data-theme="light"]'):]
        self.assertIn("--lift-1", light)
        self.assertIn("--lift-2", light)


class TheLayerRespectsTheUsersSettings(unittest.TestCase):

    def test_motion_can_be_turned_off_two_ways(self):
        """The OS setting and the app's own toggle. Honouring only one
        means the in-app control is decorative."""
        self.assertIn("@media (prefers-reduced-motion: reduce)", CSS)
        self.assertIn(".force-reduce-motion", CSS)

    def test_reduced_motion_removes_movement_and_keeps_feedback(self):
        """Somebody who asked for less movement did not ask for less
        information - the colour and depth changes have to survive."""
        reduced = CSS[CSS.index("@media (prefers-reduced-motion: reduce)"):]
        self.assertIn("transform: none", reduced)
        self.assertNotIn("box-shadow: none", reduced)

    def test_focus_rings_are_visible_and_keyboard_only(self):
        """:focus-visible, not :focus. A ring on every mouse click is
        what leads people to delete the ring entirely, and then the
        keyboard user is the one who pays."""
        self.assertIn(":focus-visible", CSS)
        self.assertIn("outline: 2px solid var(--neon-cyan)", CSS)
        self.assertNotIn("outline: none", _strip_comments(CSS))


class TheLayerIsDirectionAgnostic(unittest.TestCase):

    def test_it_uses_logical_properties_not_sides(self):
        """Persian and Arabic flip the page. A physical `left` that
        should have been `inset-inline-start` is invisible in English
        and wrong in two of the four shipped languages.
        """
        body = _strip_comments(CSS)
        offenders = []
        for rule in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
            for prop in re.findall(r"([a-z-]+)\s*:", rule.group(2)):
                if prop in {
                    "left", "right", "margin-left", "margin-right",
                    "padding-left", "padding-right",
                    "border-left", "border-right",
                }:
                    offenders.append((rule.group(1).strip()[:60], prop))
        self.assertEqual(
            offenders, [],
            f"physical side properties in a page that flips: {offenders}",
        )

    def test_the_direction_aware_rules_read_the_direction_multiplier(self):
        """The two rules that genuinely need a side - the chip hover
        nudge and its selected bar - have to move the other way in RTL,
        and variables.css already publishes --dir-mult for exactly this.
        """
        self.assertIn("--dir-mult", CSS)
        self.assertIn("--dir-mult", VARIABLES)


if __name__ == "__main__":
    unittest.main()
