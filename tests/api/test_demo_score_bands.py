"""A demo user labelled "healthy" has to actually score in the healthy band.

The bands the app itself uses are healthy 80-100, moderate 50-79, at risk
0-49. Before this test the demo did not respect them: measured across a
twenty-three day demo, the healthy state put 2 of 23 days in the healthy
band and touched 80 exactly once, and the borderline state put 1 of 23
days in the moderate band while spending the rest below 50. A reviewer
opening "the healthy demo" and reading 62 on the dashboard has been shown
that the classifier disagrees with the app's own labels.

Demo scores are genuine regressor output - nothing here fabricates a
number - so the only lever is the inputs. `_trajectory_fraction` places a
person on the 0 (at-risk-shaped inputs) to 1+ (healthy-shaped inputs)
axis, and `_build_daily_raw_input` interpolates the real profiles along
it. So the band a demo lands in is decided entirely by the fraction, and
that is what this test pins.

The fraction -> score calibration below was MEASURED on the shipped
regressor, median and range of fifteen days at a pinned fraction, with
the same per-feature +-4% noise the demo really uses:

    fraction  0.98  1.00  1.02  1.05  1.10  1.20  1.50
    median    79.6  84.2  85.9  86.5  87.0  86.4  86.3
    minimum   76.1  78.2  83.2  85.5  86.6  86.3  86.3

Two facts in that table drive the walls in `_PROFILE_SHAPE`. The axis does
not stop at 1.0 - `healthy_profile()` is one healthy person, not the
healthiest legal one, and stepping past it (then clamping to each
feature's own schema bounds) is a real person at the good end of every
field, worth about three more points. And the spread at a pinned fraction
is large near 1.00 (78-86 from the noise alone) but small at 1.02 and
above, because the clamping absorbs it - which is why the healthy floor
sits above 1.00 and not at it.

The floor is 1.035 rather than 1.02 because the first pass only measured
the CLEAN half of the catalogue. Measured across all thirty-two states -
both variants, four lengths, the user and every friend - the healthy
band now runs 83.2 to 87.5, improving 39.2 to 87.1, borderline 50.9 to
76.0 and at risk 38.8 to 47.1, with 106 of 106 checks in band.

This test deliberately does NOT load the model. Running the regressor
over four profiles x four lengths x ten friends is minutes of work for a
result that is already written down above; what can silently regress is
the fraction, and that is pure arithmetic. The score measurement itself
lives in scratch tooling and its result is the table above.

Run: python3 -m unittest tests.api.test_demo_score_bands -v
"""

from __future__ import annotations

import random
import unittest

from services.demo.demo_service import (
    AXIS_MAX,
    DemoService,
    DEMO_LENGTHS,
    DEMO_FRIENDS,
    _PROFILE_SHAPE,
    _trajectory_fraction,
    demo_seed,
)

# The fraction window each class must stay inside, read off the
# calibration table above. `None` means unbounded on that side.
#
#   healthy    >= 1.02  ->  >= 83, comfortably inside 80-100
#   borderline    0.58 - 0.94  ->  ~50 - 73, inside 50-79
#   at_risk    <= 0.47  ->  <= 49
#   improving  the whole arc on purpose: it starts at risk and ends
#              healthy, so it has no window - only the endpoints matter.
CLASS_WINDOW: dict[str, tuple[float | None, float | None]] = {
    # 1.035, raised from 1.02 after the LAPSED half of the catalogue was
    # measured for the first time. A lapsed demo is not the clean one
    # with days removed: `_lapsed_skips` draws from the same rng before
    # the day loop, and every skipped day is a per-feature noise draw
    # that never happens, so the noise lands differently. Two lapsed
    # healthy states produced days at 80.3 and 80.5 - in band, and below
    # what a healthy demo should ever show.
    "healthy": (1.035, None),
    "borderline": (0.58, 0.94),
    "at_risk": (None, 0.47),
    "improving": (None, None),
}


def _every_fraction(
    profile: str, days: int, lands_on: float | None = None, lapsed: bool = False,
) -> list[float]:
    """Every fraction one demo person really produces, in draw order.

    Seeded exactly as `DemoService.populate` seeds it, so these are the
    numbers the demo will use and not a fresh random sample.

    `lapsed` matters and was missed the first time round. The lapsed
    catalogue is not the clean one with days removed: `_lapsed_skips`
    draws from the SAME rng before the day loop, and each skipped day is
    a draw that never happens, so every fraction after it differs. Half
    the catalogue was going unmeasured.
    """
    rng = random.Random(demo_seed(profile, days, lapsed))
    skipped = _lapsed_skips_for(days, rng) if lapsed else set()
    return [
        _trajectory_fraction(i, days, rng, profile, lands_on)
        for i in range(days) if i not in skipped
    ]


def _lapsed_skips_for(days: int, rng: random.Random) -> set[int]:
    """DemoService._lapsed_skips, called without building a service."""
    service = DemoService.__new__(DemoService)
    return service._lapsed_skips(days, rng)


class TrajectoryStaysInItsClass(unittest.TestCase):
    """Every demo person, every state, inside the band they are labelled."""

    def test_the_user_s_own_demo_stays_in_band(self) -> None:
        for lapsed in (False, True):
            for days in DEMO_LENGTHS:
                for profile, (low, high) in CLASS_WINDOW.items():
                    self._assert_in_band(
                        f"{profile} {days}d {'lapsed' if lapsed else 'clean'}",
                        _every_fraction(profile, days, lapsed=lapsed), low, high,
                    )

    def _assert_in_band(self, who, fractions, low, high) -> None:
        self.assertTrue(fractions, f"{who} produced no days at all")
        if low is not None:
            self.assertGreaterEqual(
                min(fractions), low - 1e-9,
                f"{who} dips to {min(fractions):.3f}, below its floor {low} - "
                f"days will score under the band",
            )
        if high is not None:
            self.assertLessEqual(
                max(fractions), high + 1e-9,
                f"{who} reaches {max(fractions):.3f}, above its cap {high} - "
                f"days will score over the band",
            )

    def test_every_demo_friend_stays_in_band(self) -> None:
        """A friend's landing point makes them a different person, not a different class.

        This is the case that broke first: Tara used to be translated a
        long way down and, before the per-profile walls existed, a
        "healthy" friend ran 63.8 - 71.5, i.e. the whole twenty-three
        days in the moderate band with the healthy label on top.
        """
        for lapsed in (False, True):
          for days in DEMO_LENGTHS:
            for name, profile, lands_on in DEMO_FRIENDS:
                low, high = CLASS_WINDOW[profile]
                fractions = _every_fraction(profile, days, lands_on, lapsed)
                if low is not None:
                    self.assertGreaterEqual(
                        min(fractions), low - 1e-9,
                        f"{name} ({profile} -> {lands_on:.3f}) {days}d dips to "
                        f"{min(fractions):.3f}, below {low}",
                    )
                if high is not None:
                    self.assertLessEqual(
                        max(fractions), high + 1e-9,
                        f"{name} ({profile} -> {lands_on:.3f}) {days}d reaches "
                        f"{max(fractions):.3f}, above {high}",
                    )

    def test_every_friend_finishes_where_they_are_declared_to(self) -> None:
        """The landing point is a promise, and the leaderboard reads it.

        This is the assertion the "everybody shows 87" bug would have
        failed. A friend's last day is the ONLY day of theirs anybody
        sees, so it has to be the number the roster says it is - not the
        number plus whatever the day's jitter happened to draw.
        """
        for lapsed in (False, True):
            for days in DEMO_LENGTHS:
                for name, profile, lands_on in DEMO_FRIENDS:
                    shape = _PROFILE_SHAPE[profile]
                    # Clamped to the profile's own walls, because the
                    # walls outrank the landing point: staying in the
                    # labelled band matters more than hitting a number.
                    expected = min(max(lands_on, shape["floor"]), shape["cap"])
                    got = _every_fraction(profile, days, lands_on, lapsed)[-1]
                    self.assertAlmostEqual(
                        got, expected, places=6,
                        msg=f"{name} ({profile}) {days}d finishes on {got:.4f}, "
                            f"not the {expected:.4f} the roster promises",
                    )

    def test_no_two_friends_land_on_the_same_place(self) -> None:
        """Ten friends, ten different final positions.

        The bug this test exists for: five of the ten scored 87 and two
        more scored 39, because six profiles all ended at the top of the
        axis where the score curve is flat. A gap of 0.008 on the axis
        is about a point of score at the tightest part of the curve, so
        that is the floor for "these are two different people".
        """
        landings = sorted(
            min(max(lands_on, _PROFILE_SHAPE[profile]["floor"]), _PROFILE_SHAPE[profile]["cap"])
            for _name, profile, lands_on in DEMO_FRIENDS
        )
        for lower, upper in zip(landings, landings[1:]):
            self.assertGreaterEqual(
                upper - lower, 0.008,
                f"two friends land on {lower:.3f} and {upper:.3f} - close "
                f"enough to show the same score",
            )

    def test_the_improving_story_as_written_ends_healthy(self) -> None:
        """"Improving" is a story, and the demo user's own has to land.

        Ending at 0.995 used to look fine and score 83 only on a good
        day; the arc has to ACTUALLY finish healthy or the app has told
        somebody a recovery story with no recovery in it.
        """
        for days in DEMO_LENGTHS:
            if days < 7:  # too short for an arc to read as one
                continue
            fractions = _every_fraction("improving", days)
            self.assertLess(
                fractions[0], 0.47,
                f"improving {days}d starts at {fractions[0]:.3f} - it is "
                f"supposed to start at risk",
            )
            # 1.005 is the axis position of score 80, the bottom of the
            # healthy band. The last day carries neither jitter nor
            # per-feature noise now, so the finish is exact and can be
            # asserted on the last day alone.
            self.assertGreaterEqual(
                fractions[-1], 1.005,
                f"improving {days}d finishes at {fractions[-1]:.3f} - it "
                f"never reaches healthy",
            )

    def test_a_friend_on_the_improving_arc_really_climbs(self) -> None:
        """A friend mid-arc is allowed not to have arrived yet.

        Three of the ten friends run `improving` and two of them land
        below the healthy band, which is deliberate: `healthy` has half
        a point of usable range, so the only way to show a spread of
        people in the good half of the table is to place them along the
        improving arc. What must still hold is that it IS an arc - they
        start at risk and finish a long way above where they began.
        Without this, "improving" would be free to mean anything.
        """
        friends = [(n, lands) for n, p, lands in DEMO_FRIENDS if p == "improving"]
        self.assertTrue(friends, "no friend runs the improving profile")
        for days in DEMO_LENGTHS:
            if days < 7:
                continue
            for name, lands_on in friends:
                fractions = _every_fraction("improving", days, lands_on)
                self.assertLess(
                    fractions[0], 0.47,
                    f"{name} ({days}d) starts at {fractions[0]:.3f} - an "
                    f"improving friend is supposed to start at risk",
                )
                self.assertGreaterEqual(
                    fractions[-1] - fractions[0], 0.60,
                    f"{name} ({days}d) climbs only "
                    f"{fractions[-1] - fractions[0]:.3f} on the axis - that "
                    f"is not an improvement story",
                )

    def test_a_healthy_demo_is_not_a_flat_line(self) -> None:
        """Above ~1.07 every fraction scores the same 87.

        Pinning healthy to the top of the axis does put all its days in
        band - and draws a dead-flat trend across the dashboard, which is
        its own kind of wrong. The shape sits on the knee instead, so a
        healthy person still has better and worse days.
        """
        fractions = _every_fraction("healthy", 23)
        self.assertLess(
            min(fractions), 1.05,
            "healthy never comes off the saturated part of the axis - its "
            "dashboard trend will be a flat line",
        )


class ProfileShapesAreWellFormed(unittest.TestCase):
    """The walls exist, agree with each other, and are actually reachable."""

    def test_every_shape_declares_its_walls(self) -> None:
        for profile, shape in _PROFILE_SHAPE.items():
            for key in ("start", "end", "dip", "jitter", "floor", "cap"):
                self.assertIn(key, shape, f"{profile} is missing '{key}'")
            self.assertLess(shape["floor"], shape["cap"], f"{profile} floor >= cap")
            self.assertLessEqual(
                shape["cap"], AXIS_MAX + 1e-9,
                f"{profile} caps above AXIS_MAX, where the score curve is flat",
            )

    def test_the_walls_match_the_class_windows(self) -> None:
        """A shape's own floor/cap must not permit leaving its band."""
        for profile, (low, high) in CLASS_WINDOW.items():
            shape = _PROFILE_SHAPE[profile]
            if low is not None:
                self.assertGreaterEqual(
                    shape["floor"], low - 1e-9,
                    f"{profile}'s floor {shape['floor']} is below the {low} its "
                    f"band needs",
                )
            if high is not None:
                self.assertLessEqual(
                    shape["cap"], high + 1e-9,
                    f"{profile}'s cap {shape['cap']} is above the {high} its "
                    f"band allows",
                )


if __name__ == "__main__":
    unittest.main()
