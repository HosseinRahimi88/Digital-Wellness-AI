"""
Tests: a day scored on both halves, and thirty-two fixed demo states.

DAY COLOURS. The dashboard used to colour a day by one fact - was there
a check-in - which made three different situations look identical:
logged but no plan work done, plan work done but never logged, and
nothing at all. Those are the ones worth telling apart, so a day is now
scored on two independent facts and lands in one of four states.

    logged   done    colour   penalty
    yes      yes     green     0.0
    yes      no      orange   -0.5
    no       yes     grey     -0.5
    no       no      red      -1.0

The two -0.5 cases are deliberately equal: a day lived but not recorded
costs the app its data, a day recorded but not acted on costs the user
their plan. Only missing both is a full point.

Penalties are REPORTED, never applied to the wellness score. That
number is the model's reading of habits; this is a record of engagement
with the app, and mixing them would make one number mean two things.

DEMO STATES. A demo used to mint a random account and seed its
generator from that account's id, so "the 23-day improving demo" was a
different person with different numbers every run - impossible to talk
a reviewer through. Identity and seed now come from the state alone,
and the state includes a lapsed flag, which takes the catalogue from
sixteen to thirty-two.

Verified live before writing these: a 15-day lapsed at-risk demo
rendered a red/green/green/orange strip, a -4.0 penalty line, and a
violations panel reading 3 with 4 badges spent.

Run: python3 -m unittest tests.api.test_day_status_and_demo_states -v
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths


class TestDayStatus(unittest.TestCase):

    def setUp(self):
        from services.wellness import day_status_service as svc
        self.svc = svc

    # ------------------------------------------------------ the 2x2
    def test_the_four_states(self):
        self.assertEqual(self.svc.status_for(True, True), "green")
        self.assertEqual(self.svc.status_for(True, False), "orange")
        self.assertEqual(self.svc.status_for(False, True), "grey")
        self.assertEqual(self.svc.status_for(False, False), "red")

    def test_the_penalties_match_what_was_asked_for(self):
        self.assertEqual(self.svc.PENALTY["green"], 0.0)
        self.assertEqual(self.svc.PENALTY["orange"], -0.5)
        self.assertEqual(self.svc.PENALTY["grey"], -0.5)
        self.assertEqual(self.svc.PENALTY["red"], -1.0)

    def test_missing_both_costs_more_than_missing_either(self):
        self.assertLess(self.svc.PENALTY["red"], self.svc.PENALTY["orange"])
        self.assertLess(self.svc.PENALTY["red"], self.svc.PENALTY["grey"])

    def test_the_two_half_point_states_are_equal(self):
        # Neither is worse than the other, and saying one is would be a
        # judgement the app has no basis for.
        self.assertEqual(self.svc.PENALTY["orange"], self.svc.PENALTY["grey"])

    # ------------------------------------------------------ the window
    def _build(self, history, done, start, end, today=None):
        return self.svc.build_day_statuses(history, done, start, end, today=today)

    def test_a_logged_and_done_day_is_green_and_free(self):
        d = date(2026, 8, 10)
        out = self._build(
            [{"date": "2026-08-10", "health_score": 72.0}], {"2026-08-10"},
            d, d, today=date(2026, 8, 12),
        )
        self.assertEqual(out[0].status, "green")
        self.assertEqual(out[0].penalty, 0.0)
        self.assertEqual(out[0].score, 72.0)

    def test_a_logged_but_undone_day_is_orange(self):
        d = date(2026, 8, 10)
        out = self._build([{"date": "2026-08-10", "health_score": 60.0}], set(), d, d,
                          today=date(2026, 8, 12))
        self.assertEqual(out[0].status, "orange")
        self.assertEqual(out[0].penalty, -0.5)

    def test_a_done_but_unlogged_day_is_grey(self):
        d = date(2026, 8, 10)
        out = self._build([], {"2026-08-10"}, d, d, today=date(2026, 8, 12))
        self.assertEqual(out[0].status, "grey")
        self.assertEqual(out[0].penalty, -0.5)
        self.assertIsNone(out[0].score, "a day with no check-in has no score to show")

    def test_a_day_with_neither_is_red(self):
        d = date(2026, 8, 10)
        out = self._build([], set(), d, d, today=date(2026, 8, 12))
        self.assertEqual(out[0].status, "red")
        self.assertEqual(out[0].penalty, -1.0)

    def test_today_is_reported_but_never_penalised(self):
        # It is not over. Charging someone at breakfast for a day they
        # have not finished living would be wrong, and it is the same
        # rule the violation ledger already uses.
        today = date(2026, 8, 12)
        out = self._build([], set(), today, today, today=today)
        self.assertEqual(out[0].status, "red")
        self.assertEqual(out[0].penalty, 0.0)
        self.assertTrue(out[0].is_today)

    def test_a_range_produces_one_entry_per_day(self):
        start, end = date(2026, 8, 1), date(2026, 8, 7)
        out = self._build([], set(), start, end, today=date(2026, 8, 20))
        self.assertEqual(len(out), 7)
        self.assertEqual(out[0].date, "2026-08-01")
        self.assertEqual(out[-1].date, "2026-08-07")

    def test_the_total_is_the_sum_of_the_days(self):
        start, end = date(2026, 8, 1), date(2026, 8, 3)
        history = [{"date": "2026-08-01", "health_score": 70.0}]
        out = self._build(history, {"2026-08-01"}, start, end, today=date(2026, 8, 20))
        # green + red + red
        self.assertEqual(self.svc.total_penalty(out), -2.0)
        self.assertEqual(
            self.svc.counts_by_status(out), {"green": 1, "orange": 0, "grey": 0, "red": 2},
        )

    def test_a_non_numeric_score_is_reported_as_absent(self):
        d = date(2026, 8, 10)
        out = self._build([{"date": "2026-08-10", "health_score": "high"}], set(), d, d,
                          today=date(2026, 8, 12))
        self.assertIsNone(out[0].score)
        self.assertTrue(out[0].logged, "the day was still logged")


class TestDemoStatesAreFixed(unittest.TestCase):

    def setUp(self):
        from services.demo import demo_service as svc
        self.svc = svc

    def test_there_are_thirty_two_states(self):
        combos = [
            (p, d, v)
            for p in self.svc.DEMO_PROFILES
            for d in self.svc.DEMO_LENGTHS
            for v in self.svc.DEMO_VARIANTS
        ]
        self.assertEqual(len(combos), 32)
        self.assertEqual(len({self.svc.demo_email(*c) for c in combos}), 32,
                         "two states share an address, so they share a user")

    def test_the_seed_depends_only_on_the_state(self):
        # This is what makes a demo the same person every time. It used
        # to include the account id, which changed on every run.
        a = self.svc.demo_seed("improving", 23, False)
        b = self.svc.demo_seed("improving", 23, False)
        self.assertEqual(a, b)

    def test_each_state_has_its_own_seed(self):
        seeds = {
            self.svc.demo_seed(p, d, v)
            for p in self.svc.DEMO_PROFILES
            for d in self.svc.DEMO_LENGTHS
            for v in self.svc.DEMO_VARIANTS
        }
        self.assertEqual(len(seeds), 32)

    def test_the_lapsed_variant_is_a_different_person_from_the_clean_one(self):
        self.assertNotEqual(
            self.svc.demo_seed("improving", 23, False),
            self.svc.demo_seed("improving", 23, True),
        )
        self.assertNotEqual(
            self.svc.demo_email("improving", 23, False),
            self.svc.demo_email("improving", 23, True),
        )

    def test_every_demo_address_is_recognisably_a_demo(self):
        # end_demo_session refuses to delete anything that is not, so an
        # address that fell outside this shape would be undeletable.
        for p in self.svc.DEMO_PROFILES:
            for d in self.svc.DEMO_LENGTHS:
                for v in self.svc.DEMO_VARIANTS:
                    address = self.svc.demo_email(p, d, v)
                    self.assertTrue(address.startswith("demo+"), address)
                    self.assertTrue(address.endswith("@demo.local"), address)

    def test_the_display_name_says_which_state_it_is(self):
        name = self.svc.demo_display_name("at_risk", 15, True)
        self.assertIn("15d", name)
        self.assertIn("lapsed", name)
        self.assertNotIn("lapsed", self.svc.demo_display_name("at_risk", 15, False))

    # ----------------------------------------------------- the gaps
    def test_a_lapsed_demo_skips_real_days(self):
        import random
        from services.demo.demo_service import DemoService
        service = DemoService.__new__(DemoService)
        for days in (7, 15, 23):
            skips = DemoService._lapsed_skips(service, days, random.Random("seed"))
            self.assertTrue(skips, f"{days}-day lapsed demo skipped nothing")
            self.assertLess(len(skips), days, "a lapsed demo still has to log something")

    def test_the_first_and_last_day_are_never_skipped(self):
        # The last day is the one the reviewer lands on, and a user who
        # never logged a first day has no history to speak of.
        import random
        from services.demo.demo_service import DemoService
        service = DemoService.__new__(DemoService)
        for days in (3, 7, 15, 23):
            skips = DemoService._lapsed_skips(service, days, random.Random("seed"))
            self.assertNotIn(0, skips)
            self.assertNotIn(days - 1, skips)

    def test_the_gaps_are_the_same_every_time(self):
        import random
        from services.demo.demo_service import DemoService
        service = DemoService.__new__(DemoService)
        first = DemoService._lapsed_skips(service, 23, random.Random(self.svc.demo_seed("improving", 23, True)))
        again = DemoService._lapsed_skips(service, 23, random.Random(self.svc.demo_seed("improving", 23, True)))
        self.assertEqual(first, again)


class TestTheColoursAreExplainedOnThePage(unittest.TestCase):
    """Four colours with no key is a puzzle, not a chart.

    The meaning used to be reachable only by hovering a cell - nothing
    on a touch screen, and nothing at all to someone reading a
    screenshot of the dashboard, which is how this row is most often
    seen.
    """

    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        root = paths.PROJECT_ROOT
        cls.page = (root / "frontend" / "dashboard.html").read_text(encoding="utf-8")
        cls.js = (root / "frontend" / "assets" / "js" / "pages/dashboard.js").read_text(encoding="utf-8")
        cls.css = (root / "frontend" / "assets" / "css" / "shell.css").read_text(encoding="utf-8")
        cls.i18n = (root / "frontend" / "assets" / "js" / "core/i18n.js").read_text(encoding="utf-8")

    def test_the_legend_is_on_the_page(self):
        self.assertIn('id="heatmapLegend"', self.page)

    def test_it_names_all_four_states(self):
        block = self.js[self.js.index("const legend = document.getElementById('heatmapLegend')"):]
        block = block[:block.index("// Named under the heatmap")]
        self.assertIn("['green', 'orange', 'grey', 'red']", block)

    def test_the_swatches_reuse_the_cell_classes(self):
        """One stylesheet rule paints the legend and the row, so a colour
        cannot appear on one and not the other."""
        self.assertIn("'day-legend-swatch heatmap-cell day-' + state", self.js)

    def test_the_cost_is_stated_not_only_coloured(self):
        # Half a point vs a full point is the part a colour cannot carry.
        self.assertIn("{ green: null, orange: '−0.5', grey: '−0.5', red: '−1' }", self.js)

    def test_the_legend_is_translated_in_four_languages(self):
        for key in ("day_legend_title", "day_legend_green", "day_legend_orange",
                    "day_legend_grey", "day_legend_red", "day_legend_today"):
            self.assertEqual(
                self.i18n.count(f"{key}:"), 4,
                f"{key} is not present in all four language blocks",
            )

    def test_it_repaints_when_the_language_changes(self):
        # dwai:langchange is dispatched on `document` with no bubbling,
        # so a window listener would never fire.
        self.assertIn("document.addEventListener('dwai:langchange', paint)", self.js)

    def test_the_legend_wraps_rather_than_scrolling(self):
        block = self.css[self.css.index(".day-legend {"):]
        block = block[:block.index("}")]
        self.assertIn("flex-wrap: wrap", block)

    def test_the_guide_can_narrate_it(self):
        self.assertIn('id="heatmapLegend" data-guide="day_colours"', self.page)


if __name__ == "__main__":
    unittest.main()
