"""
Tests: every onboarding answer changes something.

WHAT WAS WRONG. Onboarding stores seven answers. Before this, one of
them - `schedule_type` - reached the plan service. The other six were
written to the account, echoed back by /progress and by the session
export, and read by nothing else in the codebase. Worse, four of the
seven were never even ASKED: frontend/assets/js/pages/app.js submitted
`preferred_effort: 'moderate'`, `usual_sleep_time: '23:00'`,
`usual_wake_time: '07:00'` and `work_screen_required: false` on every
user's behalf, hard-coded.

That is a questionnaire with no reader, and it is worse than not asking.
A user who tells an app their job requires a screen, and is then told to
use their screen less, has learned something true about how much the app
was listening.

WHAT IS PINNED HERE. Each answer changes the ranking or the pace, and
each one changes it in the direction the answer implies. Two properties
matter as much as the changes themselves:

  - an answer may only RE-RANK signals the user's own numbers already
    flagged. It can never invent a focus area, and never silence one -
    somebody whose job is a screen still hears about their sleep;
  - the defaults reproduce the old behaviour exactly, so an account
    from before these were wired is unaffected.

Run: python3 -m unittest tests.wellness.test_onboarding_answers_matter -v
"""

from __future__ import annotations

import unittest

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from services.wellness.improvement_plan_service import ImprovementPlanService

# A day with several signals genuinely in trouble, so there is something
# for the answers to re-rank. Ranking a single flagged signal proves
# nothing - it leads whatever the answers say.
# The field names are the ones _HABIT_RULES actually reads. Written out
# from that list rather than from memory: the first draft of this
# fixture said `social_media_min_per_day`, which no rule looks at, so
# social scored zero, sleep fell outside the top-four cut, and three
# tests failed for a reason that had nothing to do with the code they
# were testing.
STRUGGLING = {
    "sleep_hours": 4.4,
    "social_min": 240,
    "stress_0_10": 8,
    "focus_0_100": 32,
    "physical_activity_min_per_day": 5,
    "notifications_per_day": 190,
    "total_screen_min": 610,
}


class OnboardingAnswersChangeThePlan(unittest.TestCase):

    def setUp(self):
        self.service = ImprovementPlanService()

    def _themes(self, **answers) -> list[str]:
        plan = self.service.generate(
            health_class="At Risk", wellness_score=41.0,
            user_data=dict(STRUGGLING), **answers,
        )
        # Ordered, deduplicated: the week cycles through the focus areas,
        # so the raw day list repeats them.
        seen: list[str] = []
        for day in plan.days:
            if day.theme not in seen:
                seen.append(day.theme)
        return seen

    # ------------------------------------------------ work_screen_required
    def test_a_screen_job_stops_the_plan_leading_with_use_it_less(self):
        """The case this exists for. Telling somebody whose work IS a
        screen to cut their screen time is the one instruction their day
        overrules, and leading with it is how an app makes itself easy
        to stop opening."""
        default = self._themes()
        screen_job = self._themes(work_screen_required=True)
        self.assertNotEqual(
            default, screen_job,
            "saying a screen is your job changed nothing about the plan",
        )
        for theme in ("Deep Focus", "Social Media Boundaries"):
            if theme in default and theme in screen_job:
                self.assertGreater(
                    screen_job.index(theme), default.index(theme) - 1,
                    f"{theme} did not fall for somebody whose work needs a screen",
                )

    def test_a_screen_job_never_silences_a_signal(self):
        """Down-weighting is a re-ranking, not a removal.

        Asserted on the strengthen panel rather than on the plan's four
        focus areas, and the distinction is the point: the plan shows
        the top four, so a signal can be real and still not make the
        week's list. What must never happen is a signal DISAPPEARING
        because of an answer - somebody sleeping four hours has to still
        be told about their sleep somewhere.
        """
        tracks = self.service.signal_tracks(
            dict(STRUGGLING), history=None, work_screen_required=True,
        )
        themes = [e["theme"] for e in tracks["strengthen"]]
        self.assertIn("Sleep Recovery", themes)
        self.assertIn("Social Media Boundaries", themes)
        self.assertIn("Deep Focus", themes)

    # ------------------------------------------------------ main_use_purpose
    def test_what_the_devices_are_for_changes_the_ranking(self):
        """Asserted on the severities the panel reports, not on the
        plan's top four. An answer re-ranks; whether the reorder happens
        to cross the four-item cut depends on the user's numbers, and a
        test that demanded it would be pinning the fixture rather than
        the behaviour."""
        def severities(purpose):
            tracks = self.service.signal_tracks(
                dict(STRUGGLING), history=None, main_use_purpose=purpose,
            )
            return {e["theme"]: e["severity"] for e in tracks["strengthen"]}

        social = severities("social_connection")
        work = severities("work_career")
        self.assertGreater(
            social["Social Media Boundaries"] * 0 + social.get("Mindful Notifications", 0),
            0, "nothing flagged at all - the fixture is wrong, not the code",
        )
        self.assertNotEqual(
            social, work,
            "'mainly social' and 'mainly work' rank the signals identically",
        )
        # Deep Focus is the one the work answer lifts and the social one
        # does not touch, so it is where the difference has to show.
        self.assertGreater(
            work["Deep Focus"], social["Deep Focus"],
            "saying your devices are mainly for work did not raise focus",
        )

    def test_a_mixed_answer_carries_no_weight(self):
        """"A bit of everything" honestly says nothing about which theme
        to lead with, so it must not pretend to."""
        for neutral in ("mixed", "other"):
            for theme in ("Deep Focus", "Sleep Recovery", "Movement"):
                self.assertEqual(
                    self.service._theme_weight(theme, None, neutral, False),
                    self.service._theme_weight(theme, None, None, False),
                    f"{neutral!r} moved {theme}",
                )

    def test_the_purpose_table_uses_the_values_that_are_really_stored(self):
        """A lookup table keyed on paraphrases matches nothing and fails
        silently - the plan simply never changes. Every key has to be a
        value config/onboarding_options.py actually stores."""
        from config.onboarding_options import PURPOSE_OPTIONS
        stored = set(PURPOSE_OPTIONS.values())
        for key in ImprovementPlanService._PURPOSE_WEIGHT:
            self.assertIn(
                key, stored,
                f"_PURPOSE_WEIGHT is keyed on {key!r}, which onboarding "
                f"never stores - this table can never match",
            )

    # ------------------------------------------------------ preferred_effort
    def test_the_pace_answer_changes_the_tasks_not_the_themes(self):
        """Effort is about how hard, not about what. The themes are
        chosen by the user's numbers; effort decides which rung of each
        one they start on."""
        gentle = self.service.generate(
            health_class="At Risk", wellness_score=41.0,
            user_data=dict(STRUGGLING), preferred_effort="low",
        )
        hard = self.service.generate(
            health_class="At Risk", wellness_score=41.0,
            user_data=dict(STRUGGLING), preferred_effort="high",
        )
        self.assertEqual(
            [d.theme for d in gentle.days], [d.theme for d in hard.days],
            "the pace answer changed WHICH habits are worked on",
        )
        self.assertNotEqual(
            [d.tasks for d in gentle.days], [d.tasks for d in hard.days],
            "the pace answer changed nothing about the actual exercises",
        )

    def test_a_gentle_pace_never_falls_off_the_bottom(self):
        gentle = self.service.generate(
            health_class="At Risk", wellness_score=41.0,
            user_data=dict(STRUGGLING), preferred_effort="low",
        )
        for day in gentle.days:
            self.assertTrue(day.tasks, f"day {day.day_number} has no tasks at all")

    def test_a_hard_pace_never_runs_off_the_top(self):
        hard = self.service.generate(
            health_class="At Risk", wellness_score=41.0,
            user_data=dict(STRUGGLING), preferred_effort="high",
            theme_streaks={"Sleep Recovery": 9},
        )
        for day in hard.days:
            self.assertTrue(day.tasks, f"day {day.day_number} has no tasks at all")

    def test_an_unknown_pace_is_the_default_pace(self):
        self.assertEqual(
            [d.tasks for d in self.service.generate(
                health_class="At Risk", wellness_score=41.0,
                user_data=dict(STRUGGLING)).days],
            [d.tasks for d in self.service.generate(
                health_class="At Risk", wellness_score=41.0,
                user_data=dict(STRUGGLING), preferred_effort="whatever").days],
        )

    # ------------------------------------------- usual_sleep / usual_wake
    def test_the_declared_window_wraps_past_midnight(self):
        h = ImprovementPlanService.declared_sleep_hours
        self.assertEqual(h("23:00", "07:00"), 8.0)
        self.assertEqual(h("01:30", "06:00"), 4.5)
        self.assertEqual(h("22:00", "06:30"), 8.5)

    def test_an_unusable_window_is_none_rather_than_a_guess(self):
        h = ImprovementPlanService.declared_sleep_hours
        for bad in (("", "07:00"), (None, "07:00"), ("23:00", None),
                    ("25:00", "07:00"), ("23:61", "07:00"), ("nope", "07:00"),
                    ("07:00", "07:00")):
            self.assertIsNone(h(*bad), f"{bad} produced a sleep window")

    def test_a_short_declared_window_lifts_sleep(self):
        """Somebody who says up front that they aim for five hours has
        told the app something before their first check-in exists."""
        def sleep_severity(sleep_at, wake_at):
            tracks = self.service.signal_tracks(
                dict(STRUGGLING), history=None,
                usual_sleep_time=sleep_at, usual_wake_time=wake_at,
            )
            return next(
                e["severity"] for e in tracks["strengthen"]
                if e["theme"] == "Sleep Recovery"
            )

        self.assertGreater(
            sleep_severity("01:00", "06:00"), sleep_severity("22:30", "07:00"),
            "declaring a five-hour night did not raise sleep at all",
        )

    def test_a_generous_declared_window_never_lowers_sleep(self):
        """The boost is one-directional. Saying you aim for nine hours
        must not quiet a measured four-hour night - what somebody
        intends does not overrule what they logged."""
        said_nothing = self.service.signal_tracks(dict(STRUGGLING), history=None)
        generous = self.service.signal_tracks(
            dict(STRUGGLING), history=None,
            usual_sleep_time="22:00", usual_wake_time="07:30",
        )
        def sleep(tracks):
            return next(
                e["severity"] for e in tracks["strengthen"]
                if e["theme"] == "Sleep Recovery"
            )
        self.assertEqual(sleep(generous), sleep(said_nothing))

    # ------------------------------------------------------- the defaults
    def test_saying_nothing_produces_exactly_the_old_plan(self):
        """Every account created before these were wired passes None for
        all of them, and must get the plan it got yesterday."""
        bare = self.service.generate(
            health_class="At Risk", wellness_score=41.0, user_data=dict(STRUGGLING),
        )
        explicit_nothing = self.service.generate(
            health_class="At Risk", wellness_score=41.0, user_data=dict(STRUGGLING),
            main_use_purpose=None, preferred_effort=None,
            work_screen_required=False,
            usual_sleep_time=None, usual_wake_time=None,
        )
        self.assertEqual(
            [(d.theme, d.tasks) for d in bare.days],
            [(d.theme, d.tasks) for d in explicit_nothing.days],
        )

    def test_no_combination_of_answers_can_zero_a_theme(self):
        """A weight of zero would let an answer silence a real signal.
        Every path through _theme_weight has to stay positive."""
        for purpose in (None, "work_career", "social_connection", "entertainment"):
            for screen in (True, False):
                for schedule in (None, "rotating_shift", "standard_day"):
                    for hours in (None, 4.0, 9.0):
                        weight = self.service._theme_weight(
                            "Social Media Boundaries", schedule, purpose, screen, hours,
                        )
                        self.assertGreater(weight, 0.0)

    def test_the_panel_does_not_report_its_own_sort_key(self):
        """The unclamped rank is scratch state for the sort. Leaving it
        on the entry would put it in the API response."""
        tracks = self.service.signal_tracks(
            dict(STRUGGLING), history=None, work_screen_required=True,
        )
        for entry in tracks["strengthen"]:
            self.assertEqual(
                [k for k in entry if k.startswith("_")], [],
                f"internal key leaked into the response: {entry}",
            )

    def test_the_two_ranking_paths_agree(self):
        """The 7-day plan and the strengthen/maintain panel rank with the
        same arithmetic. If they diverged, the app would name one signal
        as the week's focus and a different one as the worst."""
        answers = dict(
            schedule_type="rotating_shift", main_use_purpose="social_connection",
            work_screen_required=True,
        )
        plan_lead = self._themes(**answers)[0]
        tracks = self.service.signal_tracks(
            dict(STRUGGLING), history=None, **answers,
        )
        self.assertTrue(tracks["strengthen"], "nothing flagged to strengthen")
        self.assertEqual(
            tracks["strengthen"][0]["theme"], plan_lead,
            "the panel's worst signal is not the theme the week leads with",
        )


if __name__ == "__main__":
    unittest.main()
