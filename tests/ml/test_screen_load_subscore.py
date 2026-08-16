"""The screen-load component of the wellness score.

The defect these tests exist for: the score used to be the mean of six
subscores describing sleep, night use, focus, balance, stress and
activity. None of them measured how long the screen was on, so in an
application about digital wellness the score correlated +0.105 with
total screen minutes and +0.034 with recreational minutes - nothing, and
the wrong sign both times. By recreational hours the mean ran 62.5,
65.0, 63.7, 61.6, 60.6 across <2h, 2-4h, 4-6h, 6-8h and 8h+: a hump, not
a decline.

The first fix measured load against config/healthy_targets.py, the
app's own simulation table, which put the recreational allowance at 180
minutes. That was internally consistent and externally arbitrary - it
is half an hour past the two-hour guideline the research actually
publishes - so the score could agree with itself and with nothing else.

These tests pin what replaced it: the thresholds are the published ones,
the curve has the published shape, and the subscore falls as load rises.
The exact values asserted below are stated in utils/screen_load.py's
docstring and are derivable from two facts in the literature - the
two-hour recommendation, and the sharp rise between two and four hours.
They are not tuning constants, so a change that moves them is a change
of claim and should fail here.
"""

from __future__ import annotations

import unittest

from utils.screen_load import (
    PRE_SLEEP_GUIDELINE_MIN,
    RECREATIONAL_GUIDELINE_MIN,
    RECREATIONAL_STEEP_END_MIN,
    RECREATIONAL_STEEP_START_MIN,
    WORK_NORMAL_MIN,
    recreational_penalty,
    screen_load_components,
    screen_load_excess,
    screen_load_subscore,
)


def day(**minutes: float) -> dict:
    base = {
        "social_min": 0.0,
        "gaming_min": 0.0,
        "video_min": 0.0,
        "other_min": 0.0,
        "work_study_min": 0.0,
        "pre_sleep_screen_min": 0.0,
    }
    base.update(minutes)
    return base


class TestTheThresholdsAreThePublishedOnes(unittest.TestCase):
    def test_the_recreational_guideline_is_two_hours(self):
        self.assertEqual(RECREATIONAL_GUIDELINE_MIN, 120.0)

    def test_the_steep_band_is_two_to_four_hours(self):
        self.assertEqual(RECREATIONAL_STEEP_START_MIN, 120.0)
        self.assertEqual(RECREATIONAL_STEEP_END_MIN, 240.0)

    def test_pre_sleep_uses_the_stricter_published_cut_off(self):
        # 60 minutes lights-on, 30 lights-off. The app cannot know which,
        # so it uses 30.
        self.assertEqual(PRE_SLEEP_GUIDELINE_MIN, 30.0)

    def test_a_full_working_day_of_screen_work_is_free(self):
        self.assertEqual(WORK_NORMAL_MIN, 480.0)


class TestTheCurveHasThePublishedShape(unittest.TestCase):
    """Both logistic parameters fall out of "the rise is sharp between
    two and four hours": the midpoint is that band's centre and the
    steepness is set so the curve's own middle half spans the band. The
    penalties below are what that construction produces, to 4 decimal
    places, and each is a round fraction rather than a fitted number."""

    def test_nothing_is_charged_at_or_below_the_guideline(self):
        for minutes in (0.0, 60.0, 119.0, 120.0):
            with self.subTest(minutes=minutes):
                self.assertEqual(recreational_penalty(minutes), 0.0)

    def test_three_hours_costs_exactly_one_third(self):
        self.assertAlmostEqual(recreational_penalty(180.0), 1.0 / 3.0, places=6)

    def test_four_hours_costs_exactly_two_thirds(self):
        self.assertAlmostEqual(recreational_penalty(240.0), 2.0 / 3.0, places=6)

    def test_half_the_penalty_is_spent_inside_the_steep_band(self):
        # The claim the steepness was derived from, restated as a test.
        inside = recreational_penalty(RECREATIONAL_STEEP_END_MIN) - \
            recreational_penalty(RECREATIONAL_STEEP_START_MIN)
        self.assertAlmostEqual(inside, 0.5 + 1.0 / 6.0, places=6)

    def test_it_accelerates_through_the_band_and_decelerates_after(self):
        # A straight line would have equal increments; the previous
        # version of this curve was concave where its own docstring
        # claimed convex, which is what this catches.
        def slope(a: float, b: float) -> float:
            return (recreational_penalty(b) - recreational_penalty(a)) / (b - a)

        self.assertLess(slope(130.0, 160.0), slope(165.0, 195.0))
        self.assertGreater(slope(165.0, 195.0), slope(260.0, 290.0))

    def test_it_never_reaches_a_penalty_it_cannot_exceed_early(self):
        # Monotone strictly increasing through the whole realistic range:
        # a flat stretch would mean two different days scoring the same.
        previous = -1.0
        for minutes in range(121, 600, 10):
            current = recreational_penalty(float(minutes))
            self.assertGreater(current, previous, f"flat at {minutes} min")
            previous = current


class TestTheSubscoreFallsAsLoadRises(unittest.TestCase):
    def test_a_day_inside_every_threshold_scores_full_marks(self):
        self.assertEqual(
            screen_load_subscore(
                day(social_min=60, video_min=60, work_study_min=400,
                    pre_sleep_screen_min=25)
            ),
            100.0,
        )

    def test_it_is_monotone_decreasing_in_recreational_minutes(self):
        previous = 100.0
        for minutes in range(0, 900, 30):
            current = screen_load_subscore(day(social_min=float(minutes)))
            self.assertLessEqual(current, previous, f"rose at {minutes} min")
            previous = current

    def test_the_published_hours_land_where_the_docstring_says(self):
        for hours, expected in ((2, 100.0), (3, 66.67), (4, 33.33), (6, 4.76)):
            with self.subTest(hours=hours):
                self.assertAlmostEqual(
                    screen_load_subscore(day(social_min=hours * 60.0)),
                    expected, places=1,
                )

    def test_recreational_volume_alone_can_bottom_the_subscore_out(self):
        # The spine of the subscore. A ten-hour recreational day is a
        # heavy digital load whatever else was true of it, and an
        # earlier version floored it at 40 because the term only owned
        # 60% of the scale.
        self.assertLess(screen_load_subscore(day(social_min=600.0)), 1.0)

    def test_every_recreational_category_counts(self):
        for field in ("social_min", "gaming_min", "video_min", "other_min"):
            with self.subTest(field=field):
                self.assertLess(
                    screen_load_subscore(day(**{field: 240.0})), 40.0
                )

    def test_the_categories_are_summed_not_taken_separately(self):
        split = day(social_min=60, gaming_min=60, video_min=60, other_min=60)
        together = day(social_min=240)
        self.assertAlmostEqual(
            screen_load_subscore(split), screen_load_subscore(together), places=4
        )


class TestPreSleepUseIsChargedOnItsOwn(unittest.TestCase):
    """Timing, not volume. The same minute can be wrong on both counts,
    so pre-sleep minutes are also inside the recreational total and that
    double count is deliberate."""

    def test_under_the_cut_off_is_free(self):
        self.assertEqual(screen_load_subscore(day(pre_sleep_screen_min=30.0)), 100.0)

    def test_past_the_cut_off_it_costs(self):
        self.assertLess(screen_load_subscore(day(pre_sleep_screen_min=90.0)), 100.0)

    def test_it_cannot_bottom_the_subscore_out_by_itself(self):
        self.assertGreater(screen_load_subscore(day(pre_sleep_screen_min=600.0)), 70.0)

    def test_it_adds_to_the_recreational_penalty_rather_than_sharing_it(self):
        without = screen_load_excess(day(social_min=240.0))
        with_late = screen_load_excess(day(social_min=240.0, pre_sleep_screen_min=120.0))
        self.assertAlmostEqual(with_late - without, 0.25, places=6)


class TestWorkTimeIsTreatedAsObligated(unittest.TestCase):
    """HEALTHY_TARGETS says work screen time "is frequently not the
    user's to choose", and the account model carries a
    work_screen_required flag for it. Every threshold in the research is
    about recreational use, so charging work time at the same rate would
    tell someone to fix what the app itself says may not be theirs to
    fix."""

    def test_a_full_working_day_is_free(self):
        self.assertEqual(screen_load_subscore(day(work_study_min=480.0)), 100.0)

    def test_a_long_working_day_costs_something(self):
        self.assertLess(screen_load_subscore(day(work_study_min=700.0)), 100.0)

    def test_it_cannot_bottom_the_subscore_out_by_itself(self):
        self.assertGreaterEqual(screen_load_subscore(day(work_study_min=1440.0)), 85.0)

    def test_work_costs_far_less_than_the_same_recreational_minutes(self):
        work = screen_load_excess(day(work_study_min=600.0))
        recreation = screen_load_excess(day(social_min=600.0))
        self.assertLess(work, recreation / 4.0)


class TestTheReportedRegression(unittest.TestCase):
    """The day that started this: 658.5 screen minutes scoring 78.

    269.5 of those are recreational - 4.5 hours, more than twice the
    guideline - and 389 are work, inside a normal working day.
    """

    REPORTED = day(
        social_min=200.0, gaming_min=10.0, video_min=40.0,
        other_min=19.5, work_study_min=389.0,
    )

    def test_the_work_half_of_that_day_is_not_charged(self):
        parts = screen_load_components(self.REPORTED)
        self.assertEqual(parts["work_penalty"], 0.0)
        self.assertAlmostEqual(parts["recreational_min"], 269.5, places=4)

    def test_that_day_lands_near_the_bottom_of_the_load_scale(self):
        # 21.7 on the published curve: past four hours of recreational
        # screen the penalty is already two thirds spent. Bounded on
        # both sides so a change that collapsed the penalty, or one that
        # made it total, would fail rather than pass quietly.
        score = screen_load_subscore(self.REPORTED)
        self.assertLess(score, 30.0)
        self.assertGreater(score, 12.0)

    def test_it_pulls_a_78_down_to_about_what_the_day_deserves(self):
        from models.data_loader import SCREEN_LOAD_WEIGHT, SUBSCORE_COLUMNS

        others = 78.0
        combined = (
            others * len(SUBSCORE_COLUMNS)
            + SCREEN_LOAD_WEIGHT * screen_load_subscore(self.REPORTED)
        ) / (len(SUBSCORE_COLUMNS) + SCREEN_LOAD_WEIGHT)
        # It scored 78 when screen time counted for nothing. It must come
        # down materially, and it must not collapse to something the six
        # wellbeing subscores cannot explain either.
        self.assertLess(combined, 68.0)
        self.assertGreater(combined, 55.0)

    def test_a_light_day_with_the_same_wellbeing_stays_high(self):
        from models.data_loader import SCREEN_LOAD_WEIGHT, SUBSCORE_COLUMNS

        light = day(social_min=45.0, video_min=30.0, work_study_min=200.0)
        combined = (
            78.0 * len(SUBSCORE_COLUMNS)
            + SCREEN_LOAD_WEIGHT * screen_load_subscore(light)
        ) / (len(SUBSCORE_COLUMNS) + SCREEN_LOAD_WEIGHT)
        self.assertGreater(combined, 80.0)


class TestTheTargetActuallyTracksScreenTime(unittest.TestCase):
    """The whole point, measured on the real training split rather than
    on hand-written rows: the score used to correlate +0.034 with
    recreational minutes."""

    @classmethod
    def setUpClass(cls):
        import pandas as pd

        from core import paths
        from models.data_loader import SCREEN_LOAD_WEIGHT, SUBSCORE_COLUMNS
        from utils.screen_load import screen_load_subscore_vectorized

        train = paths.PROJECT_ROOT / "data/train.csv"
        if not train.exists():
            raise unittest.SkipTest("data/train.csv is not present")

        frame = pd.read_csv(train)
        load = screen_load_subscore_vectorized(frame)
        six = frame[SUBSCORE_COLUMNS].mean(axis=1)
        cls.score = (six * 6 + SCREEN_LOAD_WEIGHT * load) / (6 + SCREEN_LOAD_WEIGHT)
        cls.recreational = frame[
            ["social_min", "gaming_min", "video_min", "other_min"]
        ].sum(axis=1)
        cls.wellbeing = six

    def test_it_now_falls_as_recreational_minutes_rise(self):
        self.assertLess(self.score.corr(self.recreational), -0.6)

    def test_it_has_not_become_a_screen_minute_readout(self):
        # The opposite failure, and the reason the weight is 2 and not 3.
        self.assertGreater(self.score.corr(self.wellbeing), 0.5)


class TestBothImplementationsAgree(unittest.TestCase):
    def test_row_by_row_and_vectorized_give_the_same_answer(self):
        import pandas as pd

        from utils.screen_load import screen_load_subscore_vectorized

        rows = [
            day(social_min=30, work_study_min=120),
            day(social_min=200, gaming_min=60, video_min=90, work_study_min=400),
            day(social_min=180),
            day(other_min=500),
            day(work_study_min=1000),
            day(social_min=119.9, pre_sleep_screen_min=29.9),
            day(social_min=240, pre_sleep_screen_min=95, work_study_min=900),
            day(social_min=0),
        ]
        frame = pd.DataFrame(rows)
        vector = screen_load_subscore_vectorized(frame).tolist()
        for index, row in enumerate(rows):
            self.assertAlmostEqual(vector[index], screen_load_subscore(row), places=4)


if __name__ == "__main__":
    unittest.main()
