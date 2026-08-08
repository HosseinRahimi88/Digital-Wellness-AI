"""
Tests: services.progress_service, services.insight_service,
utils.persona_titles, utils.data_dictionary and services.tone_service -
the P1-B progress/trust/identity layer.

None of these touch the ML pipeline; they are pure functions over
history entries and FEATURE_SCHEMA, so these tests assert the
arithmetic and the honesty rules (no fabricated values, no false
warnings), not model behaviour.

Run: python3 -m unittest tests.test_progress_and_insights -v
"""

from __future__ import annotations

import unittest

import tests._test_support  # noqa: F401

from config.demo_profiles import at_risk_profile, baseline_profile, borderline_profile, healthy_profile
from core.feature_schema import FEATURE_SCHEMA
from services.insight_service import InsightService
from services.progress_service import ProgressService
from services.tone_service import SUPPORTED_TONES, apply_tone, frame_result, normalize_tone
from utils.data_dictionary import _HOW_TO_MEASURE, availability_matrix, build_data_dictionary
from utils.persona_titles import resolve_identity


def _entries(n: int, start_score: float = 50.0, step: float = 3.0) -> list[dict]:
    return [
        {
            "date": f"2026-08-{i + 1:02d}",
            "day_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][i % 7],
            "health_score": start_score + i * step,
            "health_class": "Moderate",
            "top_shap_feature": "sleep_hours",
            "sleep_hours": 6.0 + i * 0.2,
            "total_screen_min": 500 - i * 20,
            "focus_0_100": 50 + i * 4,
            "stress_0_10": max(0.0, 7 - i * 0.3),
            "productivity_0_100": 55,
            "physical_activity_min_per_day": 5 * i,
            "social_min": 200 - i * 10,
        }
        for i in range(n)
    ]


class TestProgressService(unittest.TestCase):

    def test_empty_history_produces_no_fabricated_progress(self):
        summary = ProgressService.summarize([])
        self.assertEqual(summary.entry_count, 0)
        self.assertEqual(summary.small_wins, [])
        self.assertEqual(summary.personal_bests, [])
        self.assertFalse(summary.before_after.available)
        self.assertEqual(summary.replay, [])

    def test_small_wins_need_a_meaningful_relative_move(self):
        # A ~0.4% change on screen time must NOT be called a win.
        entries = [
            {"date": "2026-08-01", "total_screen_min": 480.0},
            {"date": "2026-08-02", "total_screen_min": 478.0},
        ]
        self.assertEqual(ProgressService.small_wins(entries), [])

    def test_small_wins_detect_a_real_improvement(self):
        entries = [
            {"date": "2026-08-01", "sleep_hours": 5.0},
            {"date": "2026-08-02", "sleep_hours": 7.5},
        ]
        wins = ProgressService.small_wins(entries)
        self.assertEqual([w.field_name for w in wins], ["sleep_hours"])
        self.assertGreater(wins[0].delta, 0)

    def test_small_wins_respect_direction(self):
        # More screen time is NOT a win, even though it's a big change.
        entries = [
            {"date": "2026-08-01", "total_screen_min": 200.0},
            {"date": "2026-08-02", "total_screen_min": 600.0},
        ]
        self.assertEqual(ProgressService.small_wins(entries), [])

    def test_personal_best_flags_a_new_record_on_the_latest_entry(self):
        bests = ProgressService.personal_bests(_entries(5))
        score_best = next(b for b in bests if b.metric == "health_score")
        self.assertTrue(score_best.is_new)
        self.assertEqual(score_best.achieved_on, "2026-08-05")

    def test_before_after_requires_enough_days_on_each_side(self):
        self.assertFalse(ProgressService.before_after(_entries(4)).available)
        self.assertTrue(ProgressService.before_after(_entries(8)).available)

    def test_before_after_flags_small_deltas_as_not_meaningful(self):
        flat = [{"date": f"2026-08-{i+1:02d}", "health_score": 60.0} for i in range(8)]
        result = ProgressService.before_after(flat)
        self.assertTrue(result.available)
        self.assertFalse(result.is_meaningful)

    def test_decision_replay_computes_day_over_day_deltas(self):
        steps = ProgressService.decision_replay(_entries(4))
        self.assertIsNone(steps[0].delta_from_previous)
        self.assertAlmostEqual(steps[1].delta_from_previous, 3.0, places=2)


class TestInsightService(unittest.TestCase):

    def test_confidence_label_levels(self):
        self.assertEqual(InsightService.confidence_label(95).level, "high")
        self.assertEqual(InsightService.confidence_label(75).level, "moderate")
        self.assertEqual(InsightService.confidence_label(55).level, "low")

    def test_confidence_label_handles_missing_value(self):
        label = InsightService.confidence_label(None)
        self.assertEqual(label.percent, 0.0)
        self.assertTrue(label.headline)

    def test_normal_demo_profiles_are_not_flagged_out_of_distribution(self):
        """Regression guard: zero gaming/caffeine/night use are ordinary
        healthy values. Flagging them would fire a warning at exactly
        the users doing best."""
        for profile in (healthy_profile(), borderline_profile(), at_risk_profile(), baseline_profile()):
            self.assertFalse(InsightService.check_out_of_distribution(profile).is_out_of_distribution)

    def test_genuinely_extreme_values_are_flagged(self):
        extreme = dict(healthy_profile())
        extreme["total_screen_min"] = FEATURE_SCHEMA["total_screen_min"].maximum
        report = InsightService.check_out_of_distribution(extreme)
        self.assertTrue(report.is_out_of_distribution)
        self.assertTrue(report.message)

    def test_cold_start_stages_progress_with_entry_count(self):
        self.assertEqual(InsightService.cold_start_status(0).stage, "no_data")
        self.assertEqual(InsightService.cold_start_status(1).stage, "single_day")
        self.assertEqual(InsightService.cold_start_status(30).stage, "established")
        self.assertFalse(InsightService.cold_start_status(1).trend_available)
        self.assertTrue(InsightService.cold_start_status(10).weekday_pattern_available)

    def test_weekday_reliability_marks_single_observations(self):
        entries = [
            {"day_of_week": "Monday", "health_score": 70},
            {"day_of_week": "Monday", "health_score": 60},
            {"day_of_week": "Friday", "health_score": 80},
        ]
        by_day = {w.weekday: w for w in InsightService.weekday_reliability(entries)}
        self.assertTrue(by_day["Monday"].is_reliable)
        self.assertFalse(by_day["Friday"].is_reliable)
        self.assertIsNone(by_day["Sunday"].average_score)


class TestPersonaTitles(unittest.TestCase):

    def test_empty_input_yields_no_persona(self):
        identity = resolve_identity({})
        self.assertIsNone(identity.primary)
        self.assertEqual(identity.badges, [])

    def test_different_profiles_get_different_primary_personas(self):
        healthy = resolve_identity(healthy_profile()).primary
        at_risk = resolve_identity(at_risk_profile()).primary
        self.assertIsNotNone(healthy)
        self.assertIsNotNone(at_risk)
        self.assertNotEqual(healthy.key, at_risk.key)

    def test_match_strength_is_bounded(self):
        identity = resolve_identity(at_risk_profile())
        self.assertGreaterEqual(identity.primary.match_strength, 0.0)
        self.assertLessEqual(identity.primary.match_strength, 1.0)

    def test_every_persona_states_the_numbers_that_earned_it(self):
        identity = resolve_identity(healthy_profile())
        self.assertTrue(identity.primary.reason.strip())

    def test_badges_come_from_real_values_only(self):
        healthy = resolve_identity(healthy_profile())
        at_risk = resolve_identity(at_risk_profile())
        self.assertGreater(len(healthy.badges), len(at_risk.badges))


class TestDataDictionary(unittest.TestCase):

    def test_documents_every_schema_field_and_nothing_extra(self):
        self.assertEqual(len(build_data_dictionary()), len(FEATURE_SCHEMA))
        self.assertEqual(set(_HOW_TO_MEASURE), set(FEATURE_SCHEMA))

    def test_availability_matrix_partitions_the_schema(self):
        matrix = availability_matrix()
        total = sum(len(v) for v in matrix.values())
        self.assertEqual(total, len(FEATURE_SCHEMA))
        self.assertIn("total_screen_min", matrix["derived"])
        self.assertIn("sleep_hours", matrix["user_entered"])
        self.assertIn("day_of_week", matrix["calendar"])


class TestToneService(unittest.TestCase):

    def test_unknown_tone_falls_back_to_default(self):
        self.assertEqual(normalize_tone("nonsense"), "gentle")
        self.assertEqual(normalize_tone(None), "gentle")

    def test_every_supported_tone_frames_every_band(self):
        for tone in SUPPORTED_TONES:
            for score in (95, 70, 50, 20):
                self.assertTrue(frame_result(score, tone))

    def test_apply_tone_never_alters_the_advice_itself(self):
        rec = {
            "title": "Reduce Fragmented Checking", "description": "d", "action": "a",
            "category": "Focus", "priority": "HIGH", "icon": "x",
            "success_metric": "m", "safety_note": "s",
        }
        for tone in SUPPORTED_TONES:
            out = apply_tone([dict(rec)], tone)[0]
            for key in ("title", "description", "action", "category", "priority", "success_metric", "safety_note"):
                self.assertEqual(out[key], rec[key])
            self.assertTrue(out["action_lead_in"])


if __name__ == "__main__":
    unittest.main()
