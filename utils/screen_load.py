"""
utils/screen_load.py
--------------------
How heavy a day's digital load was, as a 0-100 subscore, measured
against published research thresholds rather than against a number this
project invented.

WHY THIS EXISTS. The six composite subscores the dataset ships with -
sleep, night, focus, balance, stress/fatigue, activity - describe how a
person felt and slept. Not one of them measures how much they were on a
screen. Averaging those six gave a "digital wellness score" that
correlated +0.105 with total screen minutes and +0.034 with recreational
minutes: statistically nothing, and the wrong sign both times. Grouped
by recreational hours the mean ran 62.5 (under 2h), 65.0 (2-4h), 63.7
(4-6h), 61.6 (6-8h), 60.6 (8h+) - not a decline with a little noise on
it, but a hump, with the heaviest days landing within two points of the
lightest. Measured on data/train.csv; all figures in this file are
reproducible from it.

WHERE THE NUMBERS COME FROM. The first version of this file used
config/healthy_targets.py, which is the app's own simulation table:
social 60 + gaming 60 + video 60 = 180 minutes. That was internally
consistent and externally arbitrary - three hours of recreational screen
time is more generous than any published guideline, so a score built on
it could agree with itself and with nothing else. Every threshold below
is taken from the literature instead.

THE RECREATIONAL CURVE. Two findings fix its whole shape, and no free
parameter is left over:

  * the two-hour recommendation. Youth who meet it report higher
    happiness and life satisfaction and less psychosocial difficulty,
    and depression risk begins to rise measurably above ~2.02 h/day.
    So 120 minutes is where the penalty starts.
  * the rise is not a straight line - it is sharp between two and four
    hours, and past ~2.5 h/day each additional hour carries a >15%
    increase in risk.

A logistic dose-response curve is the standard shape for that, and
those two facts pin both of its parameters: put the midpoint at three
hours (the centre of the 2-4 h band) and set the steepness so the
curve's own middle half - its 25th to 75th percentile - spans exactly
that band. There is nothing else to choose. The curve that falls out
reads in whole numbers:

    2 h -> 0.00     4 h -> 0.67     8 h -> 0.99
    3 h -> 0.33     6 h -> 0.95

PRE-SLEEP USE IS ITS OWN RISK, not a share of the daily total. Above 60
minutes with lights on, or 30 with lights off, the odds of poor sleep
quality are 2.4-2.5x; each extra hour of screen after getting into bed
is associated with 59% higher odds of insomnia symptoms and about 24
minutes less sleep. The app cannot know whether the lights were on, so
it uses 30 - the stricter published cut-off. These minutes are also
counted inside the recreational total, deliberately: the recreational
term charges for volume and this one charges for timing, and the same
minute can be wrong on both counts.

WORK AND STUDY ARE NOT RECREATION. Every threshold above is about
recreational or discretionary use. Someone doing a full day's work at a
screen is not doing the thing the research measured, and the app's own
account model carries a `work_screen_required` flag for exactly that
reason. Work time is therefore free up to a full working day and gently
charged past it - it can pull the subscore down when it is extreme, and
it can never dominate it.

HOW THE THREE COMBINE. Recreational volume is the spine: on its own it
can take the subscore to zero, because a ten-hour recreational day is a
heavy digital load whatever else was true of it. Pre-sleep and work use
are charged on top, at a quarter and a sixth of that, and the total is
capped. So the three do not divide a fixed budget between them - the
statement is "your recreational volume costs this much, and late use
and an overlong work day cost more still".

Sources:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC13113371/
  https://www.canada.ca/en/public-health/services/reports-publications/health-promotion-chronic-disease-prevention-canada-research-policy-practice/vol-45-no-7-8-2025/recreational-screen-time-mental-health-canadian-children-youth.html
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11372655/
  https://www.nature.com/articles/s41598-026-42454-7
"""

from __future__ import annotations

import math
from typing import Any, Dict

# ---------------------------------------------------------------- thresholds

# The two-hour recreational guideline, in minutes. Below it the
# recreational term is exactly zero.
RECREATIONAL_GUIDELINE_MIN: float = 120.0

# The band the literature puts the sharp rise in: two to four hours.
RECREATIONAL_STEEP_START_MIN: float = 120.0
RECREATIONAL_STEEP_END_MIN: float = 240.0

# Both logistic parameters are derived from that band, not chosen.
# Midpoint = its centre, so the curve is steepest at three hours.
RECREATIONAL_MIDPOINT_MIN: float = (
    RECREATIONAL_STEEP_START_MIN + RECREATIONAL_STEEP_END_MIN
) / 2.0

# Steepness such that the logistic's quartile-to-quartile width is the
# band itself: a standard logistic rises from 0.25 to 0.75 over
# 2*ln(3)/k, so k = 2*ln(3)/width. Half the penalty is therefore spent
# inside 2-4 hours, which is what the research says happens there.
RECREATIONAL_STEEPNESS: float = (2.0 * math.log(3.0)) / (
    RECREATIONAL_STEEP_END_MIN - RECREATIONAL_STEEP_START_MIN
)

# Screen minutes in the hour before bed: free to the stricter published
# cut-off, fully charged at two hours.
PRE_SLEEP_GUIDELINE_MIN: float = 30.0
PRE_SLEEP_FLOOR_MIN: float = 120.0

# A full working day at a screen, and the point past which work time is
# charged in full. Only the excess counts - see the module docstring.
WORK_NORMAL_MIN: float = 480.0
WORK_FLOOR_MIN: float = 840.0

# What each term can cost. Recreational volume is the spine and carries
# the whole scale; the other two are charged on top of it.
RECREATIONAL_MAX_PENALTY: float = 1.00
PRE_SLEEP_MAX_PENALTY: float = 0.25
WORK_MAX_PENALTY: float = 0.15

RECREATIONAL_FIELDS = ("social_min", "gaming_min", "video_min", "other_min")


def _minutes(source: Dict[str, Any], field: str) -> float:
    value = source.get(field, 0.0)
    try:
        return max(0.0, float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _ramp(value: float, free_until: float, spent_at: float) -> float:
    """0.0 at or below `free_until`, rising to 1.0 at `spent_at`."""
    if value <= free_until:
        return 0.0
    if value >= spent_at:
        return 1.0
    return (value - free_until) / (spent_at - free_until)


def recreational_penalty(minutes: float) -> float:
    """0.0 to 1.0 along the logistic curve described in the docstring.

    Zero at or below the two-hour guideline, one third at three hours,
    two thirds at four, and approaching one thereafter. Rescaled so it
    meets zero exactly at the guideline: the guideline sits at the
    logistic's own 25th percentile by construction, so the rescaling is
    a division by 0.75 and nothing more.
    """
    if minutes <= RECREATIONAL_GUIDELINE_MIN:
        return 0.0

    raw = 1.0 / (
        1.0
        + math.exp(
            -RECREATIONAL_STEEPNESS * (minutes - RECREATIONAL_MIDPOINT_MIN)
        )
    )
    at_guideline = 1.0 / (
        1.0
        + math.exp(
            -RECREATIONAL_STEEPNESS
            * (RECREATIONAL_GUIDELINE_MIN - RECREATIONAL_MIDPOINT_MIN)
        )
    )
    return min(1.0, (raw - at_guideline) / (1.0 - at_guideline))


def screen_load_components(data: Dict[str, Any]) -> Dict[str, float]:
    """Each term's own penalty, so a caller can explain the number."""
    recreational = sum(_minutes(data, field) for field in RECREATIONAL_FIELDS)
    pre_sleep = _minutes(data, "pre_sleep_screen_min")
    work = _minutes(data, "work_study_min")

    return {
        "recreational_min": recreational,
        "recreational_penalty": (
            RECREATIONAL_MAX_PENALTY * recreational_penalty(recreational)
        ),
        "pre_sleep_min": pre_sleep,
        "pre_sleep_penalty": PRE_SLEEP_MAX_PENALTY * _ramp(
            pre_sleep, PRE_SLEEP_GUIDELINE_MIN, PRE_SLEEP_FLOOR_MIN
        ),
        "work_min": work,
        "work_penalty": WORK_MAX_PENALTY * _ramp(
            work, WORK_NORMAL_MIN, WORK_FLOOR_MIN
        ),
    }


def screen_load_excess(data: Dict[str, Any]) -> float:
    """The combined 0-1 penalty across the three terms."""
    parts = screen_load_components(data)
    return min(
        1.0,
        parts["recreational_penalty"]
        + parts["pre_sleep_penalty"]
        + parts["work_penalty"],
    )


def screen_load_subscore(data: Dict[str, Any]) -> float:
    """0-100, where 100 is a day inside every published threshold."""
    return round(100.0 * (1.0 - screen_load_excess(data)), 4)


def screen_load_subscore_vectorized(df: "Any") -> "Any":
    """Whole-DataFrame equivalent, for building the training target.

    Must stay in step with screen_load_subscore() above - same
    thresholds, same curve, same ceilings. Training and serving compute
    this from one definition or the number means two different things,
    and tests/ml/test_screen_load_subscore.py checks the two agree
    row by row.
    """
    import numpy as np

    def column(name: str):
        if name in df.columns:
            return df[name].fillna(0.0).clip(lower=0.0)
        return 0.0

    recreational = sum(column(field) for field in RECREATIONAL_FIELDS)
    pre_sleep = column("pre_sleep_screen_min")
    work = column("work_study_min")

    at_guideline = 1.0 / (
        1.0
        + math.exp(
            -RECREATIONAL_STEEPNESS
            * (RECREATIONAL_GUIDELINE_MIN - RECREATIONAL_MIDPOINT_MIN)
        )
    )
    raw = 1.0 / (
        1.0
        + np.exp(
            -RECREATIONAL_STEEPNESS * (recreational - RECREATIONAL_MIDPOINT_MIN)
        )
    )
    recreational_term = (
        RECREATIONAL_MAX_PENALTY
        * ((raw - at_guideline) / (1.0 - at_guideline)).clip(lower=0.0, upper=1.0)
    )
    # Below the guideline the rescaled curve is already negative and has
    # been clipped to zero, which is the same thing recreational_penalty()
    # does with its early return.

    pre_sleep_term = PRE_SLEEP_MAX_PENALTY * (
        (pre_sleep - PRE_SLEEP_GUIDELINE_MIN).clip(lower=0.0)
        / (PRE_SLEEP_FLOOR_MIN - PRE_SLEEP_GUIDELINE_MIN)
    ).clip(upper=1.0)

    work_term = WORK_MAX_PENALTY * (
        (work - WORK_NORMAL_MIN).clip(lower=0.0)
        / (WORK_FLOOR_MIN - WORK_NORMAL_MIN)
    ).clip(upper=1.0)

    excess = (recreational_term + pre_sleep_term + work_term).clip(upper=1.0)
    return (100.0 * (1.0 - excess)).clip(lower=0.0, upper=100.0)
