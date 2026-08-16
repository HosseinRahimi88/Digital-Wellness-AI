"""
Tests: the page-in flash (F1) and the undersized weekday chart (F2).

Both were reported from real use and both were reproduced in a real
browser against the running app before being fixed, so the numbers in
these docstrings are measured, not estimated.

F1 - "half a second of black screen with no UI on every navigation".
    shell.js added `.page-enter` to `.app-main` after the document had
    already painted, and the animation carries `both` fill, so the fill
    mode snapped the already-visible content back to `opacity: 0` and
    faded it in over .42s. Measured on an authenticated session with 15
    days of data, navigating dashboard -> analytics: `.app-main`
    computed opacity was 0 from 102ms to ~400ms while the surrounding
    chrome (nav, logo, music widget, mascot) stayed painted - which is
    exactly the "UI with a black hole in it" that was reported.

    After the fix the animation is declared on `.app-main` in CSS so it
    is already running at first paint, and starts from .35 rather than
    0. Measured across eight pages: worst opacity .35, fully opaque by
    187-276ms, and with prefers-reduced-motion the animation is off
    entirely (opacity 1 from the first frame).

F2 - "the bar chart is tiny compared to the space given to it".
    The canvas had no CSS size, so it fell back to the HTML default of
    300x150 and sat in the corner of its 418x200 wrapper - measured
    exactly those numbers in the browser. After the fix the canvas
    measures 418x200, the same as its wrapper.

These tests read the real shipped files rather than driving a browser,
so they run in the normal suite without a server. The browser was the
instrument used to find and confirm the bugs; these are the guards that
keep them fixed.

Run: python3 -m unittest tests.frontend.test_navigation_and_chart_ui -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

REPO_ROOT = paths.PROJECT_ROOT
JS = REPO_ROOT / "frontend" / "assets" / "js"
CSS = REPO_ROOT / "frontend" / "assets" / "css"


class TestPageEnterDoesNotBlankTheContent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.anim = (CSS / "animations.css").read_text(encoding="utf-8")
        cls.shell = (JS / "core/shell.js").read_text(encoding="utf-8")

    def _page_in_from_opacity(self) -> float:
        m = re.search(r"@keyframes page-in\s*\{\s*from\s*\{([^}]*)\}", self.anim)
        self.assertIsNotNone(m, "the page-in keyframe is gone")
        o = re.search(r"opacity:\s*([\d.]+)", m.group(1))
        self.assertIsNotNone(o, "page-in no longer sets a starting opacity")
        return float(o.group(1))

    def test_the_animation_never_starts_from_fully_invisible(self):
        # This is the whole bug: starting at 0 with `both` fill means the
        # content is blank for the length of the animation.
        self.assertGreater(
            self._page_in_from_opacity(), 0.0,
            "page-in starts from opacity 0, which blanks .app-main for the "
            "duration of the animation - the reported black screen",
        )

    def test_shell_no_longer_adds_the_class_after_paint(self):
        # Adding it from JS is what made the flip visible: the browser
        # painted the content, then the class took it away again.
        self.assertNotIn(
            "classList.add('page-enter')", self.shell,
            "shell.js adds page-enter after the page has painted, which "
            "re-introduces the visible-then-invisible flip",
        )

    def test_the_animation_is_declared_on_app_main_in_css(self):
        # Declared in CSS it is already running at first paint, so the
        # content's first appearance IS the start of the fade.
        self.assertRegex(
            self.anim, r"\.app-main[^{]*\{[^}]*animation:\s*page-in",
            "page-in is not declared on .app-main, so nothing animates at "
            "first paint",
        )

    def test_the_animation_is_short(self):
        m = re.search(r"animation:\s*page-in\s+([\d.]+)s", self.anim)
        self.assertIsNotNone(m)
        self.assertLessEqual(
            float(m.group(1)), 0.3,
            "the page-in animation is long enough to be noticed as a delay",
        )

    def test_reduced_motion_is_honoured_before_first_paint(self):
        # The .force-reduce-motion class is added by JS and would arrive
        # too late to stop an animation that starts at parse time, so the
        # media query has to be there as well.
        self.assertRegex(
            self.anim,
            r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{[^}]*\.app-main",
            "no prefers-reduced-motion rule covering .app-main - a "
            "reduce-motion user would still get the animation",
        )
        self.assertIn(".force-reduce-motion .app-main", self.anim)


class TestWeekdayChartFillsItsBox(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app_css = (CSS / "app.css").read_text(encoding="utf-8")
        cls.charts = (JS / "features/charts.js").read_text(encoding="utf-8")

    def test_the_canvas_is_sized_to_its_wrapper(self):
        # Without this the canvas uses the HTML default 300x150 and sits
        # in the corner of a 418x200 box.
        self.assertRegex(
            self.app_css,
            r"\.chart-canvas-wrap\s*>\s*canvas\s*\{[^}]*width:\s*100%[^}]*height:\s*100%",
            "the chart canvas has no size rule, so it falls back to 300x150",
        )

    def test_setup_canvas_still_reads_the_measured_box(self):
        # The CSS fix only works because the backing store is sized from
        # getBoundingClientRect and scaled by DPR.
        self.assertIn("getBoundingClientRect()", self.charts)
        self.assertIn("devicePixelRatio", self.charts)

    def test_hover_read_out_exists_and_is_bound_once(self):
        self.assertIn("attachBarHover", self.charts)
        self.assertIn("pointermove", self.charts)
        # drawBarChart runs again on every resize and language change;
        # binding per call would stack duplicate handlers. Asserting the
        # flag merely *appears* is not enough - deleting the early
        # return while leaving the assignment behind still passed that
        # version of this check, so require the guard itself.
        self.assertRegex(
            self.charts,
            r"if \(canvas\._dwHoverBound\)\s*return;",
            "attachBarHover has no early return on _dwHoverBound, so every "
            "redraw adds another pointermove listener to the same canvas",
        )
        self.assertRegex(self.charts, r"canvas\._dwHoverBound\s*=\s*true")

    def test_hover_geometry_comes_from_the_drawn_bars(self):
        # The tooltip must report the values actually plotted, not
        # re-derive them, so a redraw updates what hovering says.
        self.assertIn("_dwBars", self.charts)
        self.assertRegex(self.charts, r"boxes\.push\(")

    def test_the_empty_state_clears_the_hover_geometry(self):
        # Otherwise hovering an empty chart reports the previous data.
        # Scoped to drawBarChart: drawLineChart has its own identical
        # `if (!values.length)` guard, and an unscoped search matches
        # that one first and passes without checking anything real.
        start = self.charts.index("function drawBarChart")
        body = self.charts[start:]
        m = re.search(r"if \(!values\.length\) \{(.*?)\n    \}", body, re.DOTALL)
        self.assertIsNotNone(m, "the empty-state branch of drawBarChart is gone")
        self.assertIn("_dwBars = null", m.group(1))

    def test_the_extra_marks_are_derived_from_the_data(self):
        # The mean line and the highlighted bar are computed from
        # `values`; nothing is drawn that isn't in the series.
        self.assertRegex(self.charts, r"const mean = values\.reduce")
        self.assertRegex(self.charts, r"const best = values\.indexOf\(Math\.max")


if __name__ == "__main__":
    unittest.main()
