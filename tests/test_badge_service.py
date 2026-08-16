"""
Tests: services/badge_service.py (C-3).

The interesting assertions here are mostly negative. A badge system's
failure mode is not "the badge didn't appear" - it is a badge that
appears for everybody, which makes all of them worthless, or a private
awareness indicator leaking into a friend-facing list, which is the
exact shaming mechanism the brief forbids.

Run: python3 -m unittest tests.test_badge_service -v
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap + offline stubs

from services.badge_service import (
    CATALOGUE,
    CATEGORY_ACHIEVEMENT,
    CATEGORY_AWARENESS,
    IMPROVEMENT_MIN_DAYS,
    WINDOW,
    BadgeService,
)

TODAY = date(2026, 6, 30)


def _day(offset: int, **fields) -> dict:
    d = TODAY - timedelta(days=offset)
    entry = {"date": d.isoformat(), "day_of_week": d.strftime("%A")}
    entry.update(fields)
    return entry


def _history(days: int, **fields) -> list[dict]:
    """`days` consecutive days ending today, all identical."""
    return [_day(days - 1 - i, **fields) for i in range(days)]


def _by_id(badges) -> dict:
    return {b.id: b for b in badges}


class TestCatalogueShape(unittest.TestCase):

    def test_ids_are_unique(self):
        ids = [d.id for d in CATALOGUE]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_badge_has_its_own_icon(self):
        """The brief asks for a dedicated icon per badge; a shared icon
        makes two badges indistinguishable in the gallery."""
        icons = [d.icon for d in CATALOGUE]
        duplicates = {i for i in icons if icons.count(i) > 1}
        self.assertEqual(duplicates, set())

    def test_achievements_have_a_tier_and_awareness_does_not(self):
        for d in CATALOGUE:
            if d.category == CATEGORY_ACHIEVEMENT:
                self.assertIn(d.tier, {"common", "rare", "legendary"}, d.id)
            else:
                self.assertIsNone(d.tier, d.id)

    def test_both_categories_are_populated(self):
        achievements = [d for d in CATALOGUE if d.category == CATEGORY_ACHIEVEMENT]
        awareness = [d for d in CATALOGUE if d.category == CATEGORY_AWARENESS]
        self.assertGreaterEqual(len(achievements), 40)
        self.assertGreaterEqual(len(awareness), 15)


class TestPrivacy(unittest.TestCase):

    def test_every_awareness_indicator_is_private(self):
        badges = BadgeService.evaluate(_history(30, health_score=70), today=TODAY)
        for b in badges:
            self.assertEqual(b.private, b.category == CATEGORY_AWARENESS, b.id)

    def test_public_badges_never_include_an_awareness_indicator(self):
        """The one guarantee the league and share card depend on."""
        entries = _history(20, health_score=40, night_screen_min=200, sleep_hours=4.0)
        badges = BadgeService.evaluate(entries, today=TODAY)
        public = BadgeService.public_badges(badges)
        self.assertTrue(any(b.category == CATEGORY_AWARENESS for b in badges),
                        "test is vacuous unless some awareness indicator fired")
        self.assertFalse(any(b.private for b in public))
        self.assertFalse(any(b.category == CATEGORY_AWARENESS for b in public))


class TestEmptyAndSparseHistory(unittest.TestCase):

    def test_no_history_earns_nothing_and_does_not_crash(self):
        badges = BadgeService.evaluate([], today=TODAY)
        self.assertEqual(BadgeService.earned_count(badges), 0)

    def test_no_history_leaves_field_based_badges_unevaluable(self):
        """'Not enough data' must be distinguishable from 'not achieved',
        or a brand-new user sees a wall of things they appear to have
        missed."""
        badges = _by_id(BadgeService.evaluate([], today=TODAY))
        self.assertFalse(badges["improve_sleep_hours"].evaluable)
        self.assertFalse(badges["week_of_sleep"].evaluable)
        self.assertFalse(badges["aware_short_sleep"].evaluable)

    def test_a_single_checkin_earns_only_the_first_checkin_badge(self):
        badges = BadgeService.evaluate([_day(0, health_score=70)], today=TODAY)
        earned = {b.id for b in badges if b.earned}
        self.assertEqual(earned, {"first_checkin"})

    def test_malformed_dates_are_skipped_rather_than_crashing(self):
        entries = [{"date": "not-a-date", "health_score": 70}, _day(0, health_score=70)]
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertTrue(badges["first_checkin"].earned)


class TestImprovementBadges(unittest.TestCase):

    def test_a_flat_history_earns_no_improvement_badge(self):
        entries = _history(IMPROVEMENT_MIN_DAYS, health_score=70, sleep_hours=7.0)
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertTrue(badges["improve_sleep_hours"].evaluable)
        self.assertFalse(badges["improve_sleep_hours"].earned)

    def test_a_real_improvement_is_recognised(self):
        early = [_day(13 - i, sleep_hours=6.0) for i in range(WINDOW)]
        recent = [_day(6 - i, sleep_hours=7.5) for i in range(WINDOW)]
        badges = _by_id(BadgeService.evaluate(early + recent, today=TODAY))
        self.assertTrue(badges["improve_sleep_hours"].earned)
        self.assertGreater(badges["improve_sleep_hours"].params["change_pct"], 10)

    def test_direction_is_respected_for_lower_is_better_fields(self):
        """Screen time going UP must not read as an improvement."""
        early = [_day(13 - i, total_screen_min=300) for i in range(WINDOW)]
        recent = [_day(6 - i, total_screen_min=420) for i in range(WINDOW)]
        badges = _by_id(BadgeService.evaluate(early + recent, today=TODAY))
        self.assertFalse(badges["improve_screen_time"].earned)

        reversed_history = (
            [_day(13 - i, total_screen_min=420) for i in range(WINDOW)]
            + [_day(6 - i, total_screen_min=300) for i in range(WINDOW)]
        )
        badges = _by_id(BadgeService.evaluate(reversed_history, today=TODAY))
        self.assertTrue(badges["improve_screen_time"].earned)

    def test_thirteen_days_is_not_enough(self):
        entries = (
            [_day(12 - i, sleep_hours=6.0) for i in range(WINDOW)]
            + [_day(5 - i, sleep_hours=8.0) for i in range(WINDOW - 1)]
        )
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertFalse(badges["improve_sleep_hours"].evaluable)


class TestSustainedBadges(unittest.TestCase):

    def test_seven_of_seven_earns_it(self):
        entries = _history(WINDOW, sleep_hours=7.5)
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertTrue(badges["week_of_sleep"].earned)

    def test_six_of_seven_does_not(self):
        entries = _history(WINDOW, sleep_hours=7.5)
        entries[3]["sleep_hours"] = 5.0
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertTrue(badges["week_of_sleep"].evaluable)
        self.assertFalse(badges["week_of_sleep"].earned)


class TestAwarenessIndicators(unittest.TestCase):

    def test_a_healthy_week_triggers_no_awareness_indicator(self):
        """If these fire for someone doing fine, they are noise."""
        entries = _history(
            30, health_score=78, total_screen_min=240, night_screen_min=10,
            pre_sleep_screen_min=10, sleep_hours=7.5, sleep_quality_1_10=8,
            stress_0_10=3, focus_0_100=75, productivity_0_100=75,
            physical_activity_min_per_day=40, pickups_per_day=50,
            notification_density=30, fragmentation_index_0_100=30,
            social_comparison_1_10=3, social_min=60, gaming_min=30, video_min=45,
        )
        badges = BadgeService.evaluate(entries, today=TODAY)
        fired = [b.id for b in badges if b.category == CATEGORY_AWARENESS and b.earned]
        self.assertEqual(fired, [])

    def test_three_late_nights_out_of_seven_is_not_yet_a_pattern(self):
        entries = _history(WINDOW, night_screen_min=10)
        for i in range(3):
            entries[i]["night_screen_min"] = 120
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertTrue(badges["aware_late_night"].evaluable)
        self.assertFalse(badges["aware_late_night"].earned)

    def test_four_late_nights_out_of_seven_is(self):
        entries = _history(WINDOW, night_screen_min=10)
        for i in range(4):
            entries[i]["night_screen_min"] = 120
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertTrue(badges["aware_late_night"].earned)
        self.assertEqual(badges["aware_late_night"].params["days"], 4)


class TestExceptionDays(unittest.TestCase):

    def test_exception_days_do_not_count_towards_a_pattern(self):
        """A day the user marked as unusual must not build a case
        against them."""
        entries = _history(WINDOW + 4, night_screen_min=10)
        for e in entries[-4:]:
            e["night_screen_min"] = 200
            e["excluded"] = True
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertFalse(badges["aware_late_night"].earned)

    def test_marking_an_exception_earns_the_data_honesty_badge(self):
        entries = _history(3, health_score=70)
        entries[0]["excluded"] = True
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertTrue(badges["exception_marker"].earned)


class TestScoreBadges(unittest.TestCase):

    def test_high_scorer_needs_a_real_high_score(self):
        low = _by_id(BadgeService.evaluate(_history(10, health_score=60), today=TODAY))
        self.assertFalse(low["high_scorer"].earned)
        high = _by_id(BadgeService.evaluate(_history(10, health_score=95), today=TODAY))
        self.assertTrue(high["high_scorer"].earned)
        self.assertTrue(high["score_90"].earned)

    def test_personal_best_only_fires_when_the_latest_day_is_the_best(self):
        rising = [_day(9 - i, health_score=60 + i) for i in range(10)]
        self.assertTrue(_by_id(BadgeService.evaluate(rising, today=TODAY))["personal_best"].earned)

        entries = list(rising)
        entries[-1] = _day(0, health_score=50)
        self.assertFalse(_by_id(BadgeService.evaluate(entries, today=TODAY))["personal_best"].earned)

    def test_steady_scores_rewards_low_variation_not_a_high_average(self):
        steady = _by_id(BadgeService.evaluate(_history(14, health_score=55), today=TODAY))
        self.assertTrue(steady["steady_scores"].earned)

        swinging = [_day(13 - i, health_score=40 if i % 2 else 90) for i in range(14)]
        self.assertFalse(_by_id(BadgeService.evaluate(swinging, today=TODAY))["steady_scores"].earned)


class TestCountBadges(unittest.TestCase):

    def test_checkin_milestones_track_the_real_count(self):
        badges = _by_id(BadgeService.evaluate(_history(30, health_score=70), today=TODAY))
        self.assertTrue(badges["checkins_10"].earned)
        self.assertTrue(badges["checkins_30"].earned)
        self.assertFalse(badges["checkins_60"].earned)
        self.assertEqual(badges["checkins_60"].progress, 30.0)

    def test_log_streak_counts_showing_up_even_on_an_unhealthy_day(self):
        """Logging honestly on a bad day is the behaviour worth
        rewarding; scoring it would punish honesty."""
        badges = _by_id(BadgeService.evaluate(_history(7, health_score=20), today=TODAY))
        self.assertTrue(badges["log_streak_7"].earned)
        self.assertFalse(badges["streak_3"].earned)

    def test_a_gap_breaks_the_logging_streak(self):
        entries = [_day(9 - i, health_score=70) for i in range(10) if (9 - i) != 4
                   ]
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertFalse(badges["log_streak_7"].earned)


class TestComebackAndRecovery(unittest.TestCase):

    def test_comeback_needs_a_real_gap_then_a_real_return(self):
        entries = [_day(40 - i, health_score=70) for i in range(5)]
        entries += [_day(2 - i, health_score=70) for i in range(3)]
        badges = _by_id(BadgeService.evaluate(entries, today=TODAY))
        self.assertTrue(badges["comeback"].earned)

    def test_uninterrupted_logging_is_not_a_comeback(self):
        badges = _by_id(BadgeService.evaluate(_history(20, health_score=70), today=TODAY))
        self.assertFalse(badges["comeback"].earned)


class TestRegistryCoverage(unittest.TestCase):
    """The Python catalogue and the four-language JS registry must agree.

    This is the A-2 failure mode in miniature: a badge added on the
    server with no registry entry renders as a raw id like
    "aware_late_night" in every language, and nothing else in the test
    suite would notice.
    """

    @classmethod
    def setUpClass(cls):
        import json
        import shutil
        import subprocess
        from pathlib import Path

        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")

        registry = Path(__file__).resolve().parents[1] / "frontend/assets/js/badge-registry.js"
        # Run the real file with a minimal window stub and dump what it
        # registered - parsing JS with a regex would quietly pass on a
        # file that does not actually load.
        script = (
            "globalThis.window = {};"
            f"require({json.dumps(str(registry))});"
            "const api = window.DWBadgeText;"
            "const out = {};"
            "for (const id of api.ids()) out[id] = true;"
            "console.log(JSON.stringify({ids: Object.keys(out)}));"
        )
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError("badge-registry.js failed to load: " + result.stderr)
        cls.registry_ids = set(json.loads(result.stdout)["ids"])
        cls.registry_source = registry.read_text(encoding="utf-8")

    def test_every_catalogue_badge_has_a_registry_entry(self):
        missing = {d.id for d in CATALOGUE} - self.registry_ids
        self.assertEqual(missing, set(), f"badges with no translated text: {sorted(missing)}")

    def test_the_registry_has_no_entries_for_badges_that_do_not_exist(self):
        extra = self.registry_ids - {d.id for d in CATALOGUE}
        self.assertEqual(extra, set(), f"translated text for unknown badges: {sorted(extra)}")

    def test_every_registry_entry_covers_all_four_languages(self):
        import re
        source = self.registry_source
        for badge_id in sorted(self.registry_ids):
            start = source.index(badge_id + ": {")
            end = source.index("\n    },", start)
            block = source[start:end]
            # The quote matters: "improve_night_screen: {" ends in
            # "en: {" and would otherwise count as an English string.
            for lang in ("en: '", "fa: '", "ar: '", "zh: '"):
                # name + desc at minimum; awareness entries add next.
                expected = 3 if "next: {" in block else 2
                self.assertEqual(
                    block.count(lang), expected,
                    f"{badge_id} is missing a {lang[:2]} string",
                )

    def test_awareness_indicators_all_carry_a_next_step(self):
        source = self.registry_source
        for d in CATALOGUE:
            if d.category != CATEGORY_AWARENESS:
                continue
            start = source.index(d.id + ": {")
            end = source.index("\n    },", start)
            self.assertIn("next: {", source[start:end],
                          f"{d.id} names a pattern without offering a step")


if __name__ == "__main__":
    unittest.main()
