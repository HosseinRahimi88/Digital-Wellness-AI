"""The feature vector behind the personal week band.

ONE definition of the band model's inputs, imported by both sides:

  * models/train_band_model.py builds rows with it from the dataset's
    per-respondent day sequences;
  * services/ml/band_model_service.py builds a single row with it from
    the user's own logged days at request time.

That is deliberate and it is the same discipline
utils/feature_derivation.py already enforces for the two shipped
models: a feature computed one way at fit time and another way at
predict time is the failure that does not raise, does not show up in a
test that only ever calls one side, and quietly makes the served model
a different model from the trained one.

WHAT THE MODEL IS FOR
---------------------
The week band used to be `running mean +/- 6.0`, a constant. Measured
against the dataset's real per-respondent sequences, that constant
covers 98.7% of days - a day lands outside it once every 78 days, so
the "was that unusual, or a real change?" question is asked roughly
once every eleven weeks. And it is the same width for everybody, while
the half-width users actually need at 90% coverage spans 2.70 to 5.14
(p10 to p90 across respondents), a 1.9x range.

So the band's CENTRE stays exactly what it was - the weighted mean of
the days logged this week - and only its WIDTH becomes a prediction:
how far this particular person's next day is likely to fall from their
own running mean. Every other plan rule is untouched.

WHAT IS AND IS NOT IN HERE
--------------------------
Two families, and the split matters:

  * sequence features, from the scores of the days logged so far this
    week. Always available - a band exists only when at least one day
    has been logged.
  * habit features, from the same days' stored check-in fields. These
    are optional. The app keeps a small flat set of fields per history
    entry (services/identity/history_service.TRACKED_FIELDS), so they
    are normally there, but an entry written before that list grew, or
    a caller that has scores and nothing else, simply has not got them.

Absent habit features are emitted as NaN rather than as zero, and the
model is a HistGradientBoostingRegressor, which handles NaN natively as
"missing" instead of as "the value happened to be nought". Zero-filling
is what would make a user with no stored sleep figure look like a user
who slept zero hours.

Dispersion features are NaN for a single day for the same reason: the
standard deviation of one number is not zero, it is undefined, and the
n_days feature is what tells the model how much the rest is worth.
"""
from __future__ import annotations

from math import isfinite, nan
from typing import Any, Iterable, Mapping, Optional, Sequence

# --------------------------------------------------------------- schema

# Statistics of the score sequence itself. Ordered, and the order is
# the wire format - the trained model's columns are stored alongside it
# in artifacts/feature_columns_band.json and verified on load.
SEQUENCE_FEATURES: list[str] = [
    "n_days",          # how many days this week already count
    "score_mean",      # the band's own centre
    "score_sd",        # the single strongest predictor of next-day spread
    "score_mad",       # mean absolute deviation - robust twin of the SD
    "score_range",     # max - min
    "last_dev",        # |latest score - running mean|
    "slope",           # OLS slope over the week so far: a trend, not noise
    "diff_mean",       # mean |day-to-day change| - volatility, not spread
    "diff_max",
    "ewma_vol",        # recency-weighted volatility (alpha = 0.5)
    "score_last",
    "score_min",
    "score_max",
]

# What this person's EARLIER weeks say about how much they move.
#
# THIS IS THE PART THE MODEL WAS MISSING. Coverage was measured per
# respondent and split three ways by how far their days really wander:
# the calmest third came out at 0.95 against a 0.90 promise and the
# most volatile third at 0.84, and that gap held at EVERY prefix
# length - one day into the week and six days in alike. So it was
# never a shortage of days within the week, and no amount of extra
# training data moved it (measured: doubling the respondents changed
# the gap by half a point, in the wrong direction).
#
# The reason is simply that a volatile person's first three days can
# look exactly like a calm person's. The evidence that tells them apart
# is in the weeks BEFORE this one, and the feature vector could not
# see it. A user who has been logging for a month has twenty days of
# testimony about their own volatility, and the band was being drawn
# from the four days since Monday.
#
# All four are NaN for somebody in their first week, which is honest -
# there is no history to read - and the model handles NaN natively.
PRIOR_FEATURES: list[str] = [
    "prior_days",      # how much earlier evidence there is
    "prior_sd",        # spread of everything before this week
    "prior_mad",       # robust twin, for a history with one bad day in it
    "prior_dev_mean",  # mean |day - running mean| historically: this is
                       # the target's own distribution for this person,
                       # which is the most direct thing there is to say
]

# Fields taken from the LATEST logged day. Every one of them is in
# history_service.TRACKED_FIELDS, so what training reads out of the
# dataset is the same field the app stores per entry.
HABIT_LAST_FIELDS: list[str] = [
    "sleep_hours",
    "sleep_quality_1_10",
    "total_screen_min",
    "night_ratio",
    "social_ratio",
    "stress_0_10",
    "focus_0_100",
    "fragmentation_index_0_100",
    "pickups_per_day",
    "physical_activity_min_per_day",
]

# Fields whose own variability across the week is the feature. Someone
# whose sleep swings by three hours has a wider band than someone whose
# sleep is the same every night, and that is exactly the signal a
# score-only model cannot see until the score has already moved.
HABIT_SD_FIELDS: list[str] = [
    "sleep_hours",
    "total_screen_min",
]

HABIT_FEATURES: list[str] = (
    [f"last_{name}" for name in HABIT_LAST_FIELDS]
    + [f"sd_{name}" for name in HABIT_SD_FIELDS]
)

BAND_FEATURE_COLUMNS: list[str] = SEQUENCE_FEATURES + PRIOR_FEATURES + HABIT_FEATURES


# --------------------------------------------------------------- helpers

def _clean(values: Iterable[Any]) -> list[float]:
    """Finite floats only.

    bool is excluded explicitly: it is a subclass of int in Python, and
    a True that slipped into a score list would otherwise be averaged
    in as 1.0 without anything complaining.
    """
    out: list[float] = []
    for value in values or ():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if isfinite(number):
            out.append(number)
    return out


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _sd(values: Sequence[float]) -> float:
    """Sample standard deviation, undefined below two points."""
    if len(values) < 2:
        return nan
    average = _mean(values)
    variance = sum((v - average) ** 2 for v in values) / (len(values) - 1)
    return variance ** 0.5


def _slope(values: Sequence[float]) -> float:
    """OLS slope of the sequence against 0, 1, 2, ...

    Separates a week that is genuinely trending from one that is merely
    noisy: both widen the SD, but only one of them means the next day
    is expected somewhere other than the middle.
    """
    n = len(values)
    if n < 2:
        return nan
    mean_x = (n - 1) / 2.0
    mean_y = _mean(values)
    numerator = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    return numerator / denominator if denominator else nan


def _numeric(row: Optional[Mapping[str, Any]], field: str) -> float:
    if not row:
        return nan
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return nan
    number = float(value)
    return number if isfinite(number) else nan


# --------------------------------------------------------------- builder

def prior_features(prior_scores: Optional[Sequence[float]]) -> dict[str, float]:
    """What this person's earlier days say about their own volatility.

    All NaN when there is no history, which is the truthful answer for
    somebody in their first week rather than a zero pretending to be
    one. `prior_dev_mean` is the mean distance between a day and the
    running mean of everything before it - the same quantity the model
    predicts, measured on this person's own past.
    """
    series = _clean(prior_scores or [])
    if len(series) < 2:
        return {name: nan for name in PRIOR_FEATURES}

    deviations = []
    for i in range(1, len(series)):
        deviations.append(abs(series[i] - _mean(series[:i])))

    return {
        "prior_days": float(len(series)),
        "prior_sd": _sd(series),
        "prior_mad": _mean([abs(v - _mean(series)) for v in series]),
        "prior_dev_mean": _mean(deviations) if deviations else nan,
    }


def build_band_features(
    scores: Sequence[float],
    days: Optional[Sequence[Mapping[str, Any]]] = None,
    prior_scores: Optional[Sequence[float]] = None,
) -> dict[str, float]:
    """One feature row for the band model.

    `scores`        the week's scores so far, OLDEST FIRST. Order is load
                    bearing: slope, the day-to-day differences and the
                    recency-weighted volatility are all directional, and
                    a newest-first list would silently invert the trend.
    `days`          optionally the stored history entries those scores
                    came from, in the same order, for the habit
                    features. Anything missing becomes NaN.
    `prior_scores`  optionally this person's days from BEFORE this week,
                    oldest first. Omitted, the four prior features are
                    NaN and the row is exactly what it was before they
                    existed - which is also what a first-week user
                    genuinely has.

    Returns every key in BAND_FEATURE_COLUMNS, always, so a caller can
    build the vector by list comprehension over that order and get the
    same layout the model was fitted on.
    """
    series = _clean(scores)
    if not series:
        # No usable day. Callers are expected to skip the model
        # entirely here (there is no band without a centre either), but
        # returning a full all-NaN row rather than raising keeps this
        # function total - a feature builder that throws is a feature
        # builder that gets wrapped in a bare except somewhere.
        return {name: nan for name in BAND_FEATURE_COLUMNS}

    n = len(series)
    average = _mean(series)
    deltas = [abs(series[i] - series[i - 1]) for i in range(1, n)]

    if deltas:
        # Recency-weighted volatility. Half the weight on the most
        # recent change, so a week that has just become erratic widens
        # the band now instead of after it has averaged out.
        ewma = deltas[0]
        for delta in deltas[1:]:
            ewma = 0.5 * delta + 0.5 * ewma
    else:
        ewma = nan

    features: dict[str, float] = {
        "n_days": float(n),
        "score_mean": average,
        "score_sd": _sd(series),
        "score_mad": (_mean([abs(v - average) for v in series]) if n >= 2 else nan),
        "score_range": (max(series) - min(series)) if n >= 2 else nan,
        "last_dev": abs(series[-1] - average),
        "slope": _slope(series),
        "diff_mean": _mean(deltas) if deltas else nan,
        "diff_max": max(deltas) if deltas else nan,
        "ewma_vol": ewma,
        "score_last": series[-1],
        "score_min": min(series),
        "score_max": max(series),
    }

    features.update(prior_features(prior_scores))

    rows = list(days or ())
    latest = rows[-1] if rows else None
    for field in HABIT_LAST_FIELDS:
        features[f"last_{field}"] = _numeric(latest, field)
    for field in HABIT_SD_FIELDS:
        column = _clean([_numeric(row, field) for row in rows])
        features[f"sd_{field}"] = _sd(column) if len(column) >= 2 else nan

    return features


def band_feature_vector(
    scores: Sequence[float],
    days: Optional[Sequence[Mapping[str, Any]]] = None,
    prior_scores: Optional[Sequence[float]] = None,
) -> list[float]:
    """The same row as a list in BAND_FEATURE_COLUMNS order."""
    features = build_band_features(scores, days, prior_scores)
    return [features[name] for name in BAND_FEATURE_COLUMNS]
