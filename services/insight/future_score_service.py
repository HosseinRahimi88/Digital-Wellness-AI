"""
Future Score Service - the seven-day-ahead score
------------------------------------------------
Turns the classifier's seven-day-ahead class probabilities into a
seven-day-ahead score with an honest interval.

The app has two horizons and they were being shown as if they were one:

  * `regression_score` comes from a model whose target is
    `health_score_0_100` - TODAY's score.
  * `prediction` comes from a model whose target is
    `future_health_class_7d` - the class SEVEN DAYS from now.

So "your score is 72, status Healthy" was quietly mixing a number about
today with a label about next week. This service supplies the missing
piece - a seven-day-ahead number - so each figure can be labelled with
the horizon it actually belongs to.

Method
------
    E[wellbeing_7d | x] = SUM_c P(c | x) * mu_c
    score_7d            = (6 * E[wellbeing_7d | x] + 2 * load_today) / 8

`mu_c` is measured on the training split by
models/calibrate_future_score.py, which also records the evidence that
makes this well-founded: the class is a tertile band of the wellbeing
axis (80.2% membership agreement), the classes are exactly balanced,
and the class means barely move between train and validation (0.09-0.25
points).

TWO AXES, ONE OF THEM FORECAST. The score the app shows is the six
wellbeing subscores plus a screen-load subscore, and those two halves
correlate -0.006 with each other. `future_health_class_7d` bands the
wellbeing half only - on the combined score its own tertiles agree with
it 43.3% of the time, against 33.3% by chance - so the mixture above is
computed on the wellbeing axis and put back on the score's scale with
the user's own screen load for the day.

That second half is CARRIED, not predicted. Nothing in this dataset
forecasts how much someone will use their phone next week, and the label
leans the wrong way when asked (see
models/research_class_label_screen_response.py). Carrying it is also the
more useful answer: it makes the digital-load half of next week's number
the part the user changes today, rather than something the model claims
to know.

The interval uses the law of total variance over the same mixture:

    Var = SUM_c P(c) * (mu_c^2 + sigma_c^2)  -  (SUM_c P(c) * mu_c)^2

which is what makes it behave correctly: when the classifier is torn
between "At Risk" and "Healthy" the interval spans both, and when it is
confident the interval narrows to that one class's own spread. A fixed
+/- band would have hidden exactly the cases where the model is unsure.

What this is and is not - read before displaying it
---------------------------------------------------
It is not a regression model trained on a seven-day-ahead score. That
target does not exist in this dataset and cannot be reconstructed from
it (see the calibration script for the specific reasons and the
measurements behind them). Consequently there is no R-squared to quote
for it, and nothing in this app may quote one. The number that belongs
next to this estimate is the classifier's own seven-day accuracy.

More importantly for the UI, in `class_typical` mode: that is a
CLASS-TYPICAL score, not a personal projection. A mixture of three class
means can only ever return a value between the smallest and largest of
them - on the wellbeing axis, roughly 55 to 72, which the recombination
then pulls toward the user's own screen load. Neither end is a
prediction that anyone will move to that number. Both mean "the band the
model expects you to be in seven days from now typically sits here".
(The shipped `augmented` mode does not have this problem: it applies the
band change as a SHIFT on the user's own score, so a user the classifier
keeps in their band gets their own number back.)

Displaying it as "your score in 7 days: 72" would therefore be wrong,
and for the 84-today user it would read as a forecast decline the model
never made. It has to be shown as the band it is - the class, and the
range typical of that class - which is why `basis` is on the result and
why the interval, not the point, is the headline.
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from core import paths

logger = logging.getLogger(__name__)

ARTIFACTS = paths.ARTIFACTS_DIR
CALIBRATION_PATH = ARTIFACTS / "future_score_calibration.json"
AUGMENTATION_PATH = ARTIFACTS / "future_score_augmentation.json"
AUGMENTED_METRICS_PATH = ARTIFACTS / "metrics_future_regression.json"

# Which of the two outputs this deployment ships.
#
#   "class_only"  Output 1. The seven-day figure is the CLASS and
#                 nothing else. No number is shown, because no number
#                 can be produced from this dataset without adding an
#                 assumption, and the honest position is to say so.
#   "augmented"   Output 2. A seven-day SCORE, from the classifier's
#                 band plus the user's own within-band position today,
#                 against the augmented target. Beats "predict today"
#                 by 22.19% MAE on validation (artifacts/
#                 metrics_future_regression.json is the source of that
#                 number - do not restate it from memory here).
#                 That margin used to read 55.33%, against a target
#                 every point of which was forecast. Two thirds of the
#                 target's variance is now the screen-load half carried
#                 over from today, so "predict today" is a far stronger
#                 baseline than it was and 22.19% over it is the harder
#                 number, not the weaker one.
#   "class_typical"  The middle option: a class-typical band, no
#                 augmentation, no extra assumption. This is what the
#                 app shipped before either output existed.
#
# Set DWAI_FUTURE_SCORE_MODE to override. The default is the mode with
# the strongest measured result that is still defensible.
# VERSION 2 BUILD. The default is "augmented": the classifier picks
# the band and the user's own within-band position picks the place
# inside it. See docs/VERSION_2_AUGMENTED.md for the comparison
# against the baseline and the alternative that was rejected.
DEFAULT_MODE = os.environ.get("DWAI_FUTURE_SCORE_MODE", "augmented")
VALID_MODES = ("class_only", "class_typical", "augmented")

# 80% interval. Deliberately not 95%: on a three-class mixture a 95%
# band is nearly the whole 0-100 range whenever the classifier is
# uncertain, which is technically honest and useless to read. 80% is
# stated explicitly wherever the range is shown.
Z_80 = 1.2816
INTERVAL_CONFIDENCE_PCT = 80


# ---------------------------------------------------------------------
# Personal momentum
#
# The band above is built from the classifier's opinion and the user's
# position inside their band TODAY. Two people with the same day get the
# same band, even when one of them has been climbing all week and the
# other has been falling - which is what "the band never adapts to me"
# was describing. Their own recent trajectory is the missing term, and
# it is the one piece of evidence the classifier never sees: it is given
# one day at a time and has no memory of the days before it.
#
# The formula, in full:
#
#     slope      = OLS slope of the last k daily scores, points per day
#     momentum   = clamp(slope * 7, -MOMENTUM_CAP, +MOMENTUM_CAP)
#     weight     = clamp((n - 2) / 5, 0, 1)
#     shift      = momentum * weight
#     score'     = clip(score + shift, 0, 100)
#
# and the interval widens by the fit's own residual standard deviation,
# added in quadrature, so a jumpy history produces a wider band than a
# steady one at the same slope.
#
# Why each piece:
#   * OLS over the last k days, not "latest minus first": one unusual
#     day at either end would otherwise set the whole direction.
#   * times 7, because the horizon is seven days out and the slope is
#     per day. No other scaling is applied - this is the trend carried
#     forward, not an amplification of it.
#   * MOMENTUM_CAP bounds it at 8 points. A band is about a third of the
#     scale (~33 points), so a quarter of a band in a week is a strong
#     but real move; beyond that the line is fitting a spike rather than
#     a trend, and extrapolating it would promise a change the evidence
#     does not carry.
#   * `weight` is 0 with two days or fewer - two points always fit a
#     line perfectly and say nothing - and reaches 1 at seven days. A
#     four-day user therefore gets 40% of their measured trend, which is
#     the honest amount of a four-day trend to believe.
MOMENTUM_CAP = 8.0
# The highest score the shipped regressor actually awards. Measured by
# feeding it inputs at the healthy end of every field, clamped to each
# field's schema bounds: the curve is flat from about fraction 1.07
# upward and tops out near 87.6 (see the calibration table in
# services/demo/demo_service.py, which was measured the same way).
#
# It matters here because momentum extrapolates the user's own trend
# forward, and without a ceiling a user at 87 climbing a point a day was
# handed a band of 87-100 - a number this model cannot award to anybody,
# on any inputs. The trend is real; the scale it is being projected onto
# is not infinite.
# Note carefully what it does NOT do: it never pulls down an estimate
# that is already above it. A user genuinely scoring 95 today gets 95
# back - that property is deliberate and tested elsewhere. This bounds
# the EXTRAPOLATION only.
SCORE_CEILING = 88.0
MOMENTUM_MIN_DAYS = 3
MOMENTUM_FULL_DAYS = 7
MOMENTUM_WINDOW = 10


def _momentum(recent_scores: Optional[list[float]]) -> tuple[float, float]:
    """(shift in points over seven days, residual sd of the fit).

    `recent_scores` is the user's own daily scores in date order, oldest
    first. Fewer than MOMENTUM_MIN_DAYS returns (0, 0) - no trend is
    claimed from a history too short to have one.
    """
    if not recent_scores:
        return 0.0, 0.0
    ys = [float(v) for v in recent_scores[-MOMENTUM_WINDOW:] if v is not None]
    n = len(ys)
    if n < MOMENTUM_MIN_DAYS:
        return 0.0, 0.0

    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx <= 0:
        return 0.0, 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx

    # How far each day sits from the fitted line. A steady climb has a
    # small residual and earns a narrow band; a week that swung 30 points
    # either side of the same slope does not.
    intercept = mean_y - slope * mean_x
    residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
    residual_sd = math.sqrt(sum(r * r for r in residuals) / max(1, n - 2)) if n > 2 else 0.0

    momentum = max(-MOMENTUM_CAP, min(MOMENTUM_CAP, slope * 7.0))
    weight = max(0.0, min(1.0, (n - 2) / float(MOMENTUM_FULL_DAYS - 2)))
    return momentum * weight, residual_sd * weight


@dataclass(slots=True)
class FutureScoreResult:
    """The seven-day-ahead estimate, or an explicit "not available"."""

    available: bool
    score: Optional[float] = None
    lower: Optional[float] = None
    upper: Optional[float] = None
    confidence_pct: int = INTERVAL_CONFIDENCE_PCT
    # The class the classifier considers most likely seven days out,
    # and how sure it is. Carried here so a caller has the class and the
    # number from one place and cannot pair them inconsistently.
    predicted_class: Optional[str] = None
    class_probabilities: Optional[dict[str, float]] = None
    reason: str = ""
    # Always "class_typical". Present so no client can render this as a
    # personal forecast by forgetting what it is - the same reason
    # CorrelationCard carries is_observation_only.
    basis: str = "class_typical"
    # How many points of this estimate came from the user's OWN recent
    # trajectory, and how many days that trajectory was measured over.
    # Reported rather than folded in silently: a band that moved because
    # of the reader's own week should be able to say so.
    momentum_shift: float = 0.0
    momentum_days: int = 0


@lru_cache(maxsize=1)
def _augmentation() -> Optional[dict[str, Any]]:
    if not AUGMENTATION_PATH.exists():
        return None
    try:
        return json.loads(AUGMENTATION_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        logger.exception("Could not read the future-score augmentation artifact.")
        return None


@lru_cache(maxsize=1)
def _augmented_error_sigma() -> float:
    """The estimator's own measured error, as a standard deviation.

    Without this the Output-2 interval collapses to almost nothing
    whenever the classifier is confident in a single class - the mixture
    variance goes to zero and the range reads as +/- 0.1 points, which
    claims a precision the estimator does not have. Its validation MAE
    is the real error, converted with the Laplace relation
    sigma ~= 1.25 * MAE, and added in quadrature below.
    """
    try:
        metrics = json.loads(AUGMENTED_METRICS_PATH.read_text(encoding="utf-8"))
        mae = float(metrics["two_stage"]["validation"]["MAE"])
        return 1.25 * mae
    except Exception:  # noqa: BLE001 - no metrics means no widening, not a crash
        return 0.0


# Which tertile band each class label names. The bands are slices of the
# score axis, so this is also the order they sit in.
BAND_INDEX = {"At Risk": 0, "Moderate": 1, "Healthy": 2}


def _band_quantile(
    quantiles: dict[str, Any], band: int, rank: float,
) -> Optional[float]:
    """The score at position `rank` inside `band`, from the stored table.

    The table is 101 evenly spaced quantiles, so the position maps onto
    it directly and is interpolated between neighbours - without that,
    the estimate would step in ~0.15-point jumps and two users a point
    apart could come back identical.
    """
    reference = quantiles.get(str(band))
    if not reference or len(reference) < 2:
        return None
    position = max(0.0, min(1.0, rank)) * (len(reference) - 1)
    low = int(position)
    high = min(low + 1, len(reference) - 1)
    fraction = position - low
    return float(reference[low]) * (1 - fraction) + float(reference[high]) * fraction


def _today_band(today_score: float, augmentation: dict[str, Any]) -> int:
    """Which tertile band this score is in right now."""
    cuts = augmentation.get("today_band_cuts") or []
    if len(cuts) < 2:
        return 1
    return 0 if today_score < cuts[0] else (1 if today_score < cuts[1] else 2)


def _within_band_rank(today_score: float, augmentation: dict[str, Any]) -> Optional[float]:
    """Where this score sits inside its own band today, 0..1.

    Read off the stored quantiles rather than the training data, so
    serving needs no dataset - and so the number is the same one the
    offline evaluation produced.
    """
    cuts = augmentation.get("today_band_cuts") or []
    quantiles = augmentation.get("within_band_quantiles") or {}
    if len(cuts) < 2 or not quantiles:
        return None
    band = 0 if today_score < cuts[0] else (1 if today_score < cuts[1] else 2)
    reference = quantiles.get(str(band))
    if not reference:
        return None
    # Position of today_score among 101 evenly spaced quantiles.
    below = sum(1 for value in reference if value <= today_score)
    rank = below / (len(reference) - 1)
    return max(0.02, min(0.98, rank))


def _wellbeing_share(source: dict[str, Any]) -> float:
    """Wellbeing's share of the combined score, from the artifact.

    Read rather than hard-coded so it cannot drift from
    models/data_loader.py's own weights. Falls back to 1.0, which makes
    every caller behave as it did when the score WAS the wellbeing mean.
    """
    weights = source.get("recombination") or {}
    subscore_weight = float(weights.get("subscore_weight") or 0.0)
    screen_weight = float(weights.get("screen_load_weight") or 0.0)
    total = subscore_weight + screen_weight
    return subscore_weight / total if total > 0 else 1.0


def _wellbeing_today(
    today_score: float,
    screen_load_today: Optional[float],
    source: dict[str, Any],
) -> Optional[float]:
    """Recover the wellbeing half of a score the app already computed.

    The score is a fixed weighted mean of the two halves and the
    screen-load half is exactly computable from the user's own minute
    fields, so this is arithmetic, not an estimate:

        wellbeing = (score * (w_sub + w_screen) - w_screen * load) / w_sub

    Returns None when there is no screen-load figure, so the caller
    falls back rather than assuming a half it does not have.
    """
    weights = source.get("recombination") or {}
    subscore_weight = float(weights.get("subscore_weight") or 0.0)
    screen_weight = float(weights.get("screen_load_weight") or 0.0)
    if subscore_weight <= 0:
        return None
    if screen_weight <= 0:
        return today_score
    if screen_load_today is None:
        return None
    total = subscore_weight + screen_weight
    wellbeing = (today_score * total - screen_weight * float(screen_load_today))
    return max(0.0, min(100.0, wellbeing / subscore_weight))


def _recombine(
    wellbeing: float,
    variance: float,
    screen_load_today: Optional[float],
    calibration: dict[str, Any],
) -> tuple[float, float]:
    """Put a wellbeing-axis estimate back on the scale the app shows.

    models/calibrate_future_score.py measures its class means on the
    WELLBEING axis - the mean of the six composite subscores - because
    that is the axis `future_health_class_7d` bands. On the combined
    score, which also carries digital load, tertile membership agrees
    with the label 43.3% of the time against 33.3% by chance, so the
    method's own premise fails there.

    That leaves the screen-load half, which is carried forward rather
    than forecast: nothing in this dataset predicts a person's screen
    time a week out, but it is a fact about the day they logged and the
    one part of the number they can move today. Weights come from the
    artifact so this cannot drift from the score's own definition.

    With no screen-load figure to hand the estimate stays on the
    wellbeing axis and is returned unchanged - a slightly different
    quantity, but a real one, and the caller is told which via `basis`.
    """
    if screen_load_today is None:
        return wellbeing, variance

    weights = calibration.get("recombination") or {}
    subscore_weight = float(weights.get("subscore_weight") or 0.0)
    screen_weight = float(weights.get("screen_load_weight") or 0.0)
    total = subscore_weight + screen_weight
    if total <= 0:
        return wellbeing, variance

    share = subscore_weight / total
    combined = share * wellbeing + (screen_weight / total) * float(screen_load_today)
    # Only the wellbeing half is estimated, so only it carries variance;
    # today's screen load is measured, not predicted.
    return combined, variance * (share ** 2)


@lru_cache(maxsize=1)
def _calibration() -> Optional[dict[str, Any]]:
    if not CALIBRATION_PATH.exists():
        logger.warning(
            "No future-score calibration at %s; the seven-day score will be "
            "reported as unavailable rather than guessed.", CALIBRATION_PATH,
        )
        return None
    try:
        return json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a corrupt artifact must not break prediction
        logger.exception("Could not read the future-score calibration.")
        return None


class FutureScoreService:
    """Stateless. One public method."""

    @staticmethod
    def estimate(
        probabilities: Optional[dict[str, float]],
        predicted_class: Optional[str] = None,
        *,
        today_score: Optional[float] = None,
        screen_load_today: Optional[float] = None,
        recent_scores: Optional[list[float]] = None,
        mode: Optional[str] = None,
    ) -> FutureScoreResult:
        """
        `probabilities` is PredictionResult.probabilities - the real
        classifier's per-class probabilities for the seven-day-ahead
        label. Anything missing produces available=False with a reason,
        never a fabricated number.

        `mode` selects which output this deployment ships; see
        DEFAULT_MODE above. "augmented" additionally needs `today_score`,
        because the user's position inside their current band is half of
        that estimate - without it the call falls back to class_typical
        rather than guessing a position.

        `screen_load_today` is utils.screen_load.screen_load_subscore for
        the day being predicted. The calibration is measured on the
        wellbeing axis, because that is what the seven-day label bands;
        this is the other half, and it is carried forward rather than
        forecast - see `_recombine`. Omitted, the estimate stays on the
        wellbeing axis rather than pretending to be a score.

        `recent_scores` is this user's own daily scores in date order,
        oldest first. It is what makes the band personal rather than
        class-typical: see `_momentum` above. Omitted or too short, the
        estimate is exactly what it was before - no trend is invented
        from a history that cannot support one.
        """
        mode = mode or DEFAULT_MODE
        if mode not in VALID_MODES:
            mode = "class_typical"

        if mode == "class_only":
            # Output 1. The class is the answer; there is deliberately no
            # number, and the UI must show the class alone.
            return FutureScoreResult(
                available=False, reason="class_only_mode", basis="class_only",
                predicted_class=predicted_class,
            )

        if mode == "augmented":
            result = FutureScoreService._estimate_augmented(
                probabilities, predicted_class, today_score, recent_scores,
                screen_load_today,
            )
            if result is not None:
                return result
            # Falling back rather than failing: a missing augmentation
            # artifact should degrade to the weaker honest answer, not to
            # no answer at all.

        calibration = _calibration()
        if calibration is None:
            return FutureScoreResult(available=False, reason="calibration_missing")

        if not probabilities:
            return FutureScoreResult(available=False, reason="no_class_probabilities")

        stats = calibration.get("class_stats") or {}
        # Only classes the calibration actually knows about contribute.
        # A class the model emits that was never calibrated would
        # otherwise silently drop out of the weights and inflate the
        # rest.
        usable = {c: float(p) for c, p in probabilities.items() if c in stats}
        total = sum(usable.values())
        if not usable or total <= 0:
            return FutureScoreResult(available=False, reason="no_calibrated_classes")

        weights = {c: p / total for c, p in usable.items()}

        mean = sum(weights[c] * stats[c]["mean"] for c in weights)
        second_moment = sum(
            weights[c] * (stats[c]["mean"] ** 2 + stats[c]["std"] ** 2) for c in weights
        )
        variance = max(second_moment - mean ** 2, 0.0)

        # The mixture is on the wellbeing axis; put it back on the score
        # scale with the user's own screen load for the day before
        # anything else touches it, so momentum and the interval are
        # both measured in the units the app displays.
        mean, variance = _recombine(mean, variance, screen_load_today, calibration)

        shift, residual_sd = _momentum(recent_scores)
        mean = max(0.0, min(max(mean, SCORE_CEILING), mean + shift))
        spread = Z_80 * math.sqrt(variance + residual_sd ** 2)

        lower = max(0.0, mean - spread)
        upper = min(100.0, mean + spread)

        if predicted_class is None:
            predicted_class = max(weights, key=weights.get)

        return FutureScoreResult(
            available=True,
            score=round(mean, 1),
            lower=round(lower, 1),
            upper=round(upper, 1),
            predicted_class=predicted_class,
            class_probabilities={c: round(p, 4) for c, p in weights.items()},
            momentum_shift=round(shift, 1),
            momentum_days=len([v for v in (recent_scores or []) if v is not None][-MOMENTUM_WINDOW:]),
        )

    @staticmethod
    def _estimate_augmented(
        probabilities: Optional[dict[str, float]],
        predicted_class: Optional[str],
        today_score: Optional[float],
        recent_scores: Optional[list[float]] = None,
        screen_load_today: Optional[float] = None,
    ) -> Optional[FutureScoreResult]:
        """Output 2: band from the classifier, position from today.

        Returns None (not an error) when it cannot run, so the caller
        can fall back to the class-typical estimate.

        The bands are WELLBEING bands. They have to be: they are bands
        of the quantity the seven-day label actually bands, and on the
        combined score the label agrees with its own tertiles only 43.3%
        of the time against 33.3% by chance. So today's position is read
        on the wellbeing axis, the classifier's opinion is worth a shift
        in wellbeing points, and that shift is scaled by wellbeing's
        share of the score before it moves the user's number. The
        screen-load half is carried forward untouched, which is what
        makes it the user's to change.
        """
        augmentation = _augmentation()
        if augmentation is None or not probabilities or today_score is None:
            return None

        quantiles = augmentation.get("within_band_quantiles") or {}
        usable = {c: float(p) for c, p in probabilities.items() if c in BAND_INDEX}
        total = sum(usable.values())
        if not usable or total <= 0 or not quantiles:
            return None

        # With a screen-load figure the two halves separate exactly and
        # the band move is worth its share of the score. Without one,
        # fall back to reading the position off the score itself and
        # applying the move at full weight - which is precisely what
        # this estimator did before the score had two axes.
        #
        # Falling back rather than refusing matters, and briefly it did
        # refuse: every caller that omitted screen_load_today dropped
        # through to class_typical and got that class's mean back, so a
        # user on 70 and a user on 95 were both told 72.2. The property
        # this estimator exists for survives the fallback intact, because
        # a classifier that keeps someone in their band gives
        # (there - here) == 0 on any axis, and zero times any share is
        # still zero: stay in your band, keep your own number.
        if screen_load_today is None:
            share = 1.0
            wellbeing_today = float(today_score)
        else:
            share = _wellbeing_share(augmentation)
            wellbeing_today = _wellbeing_today(
                float(today_score), screen_load_today, augmentation)
            if wellbeing_today is None:
                share = 1.0
                wellbeing_today = float(today_score)

        rank = _within_band_rank(wellbeing_today, augmentation)
        if rank is None:
            return None

        weights = {c: p / total for c, p in usable.items()}
        # Each class contributes the score at the SAME position inside
        # ITS OWN band, read off that band's quantile table - the same
        # table models/augment_future_score.py built the target with, so
        # serving and training cannot drift apart.
        #
        # Reading it off the band (rather than off the spread of today's
        # scores among that class, which is what this used to do) is what
        # gives the estimate its defining property: a user the classifier
        # keeps in their current band gets their current score back,
        # instead of being dragged toward that class's average. The old
        # form capped every user above 78.67 and told the highest scorer
        # in the data to expect a fall.
        #
        # Applied as a SHIFT on the user's own score rather than as an
        # absolute read-off. The two agree wherever the user sits inside
        # the range the training data covers, and they differ exactly
        # where the read-off was wrong: above it. The training scores
        # stop at 84.5 and the Healthy band's table ends at 78.67, so an
        # absolute read-off silently pins every stronger user to 78.2 -
        # 84.5 became 78.2, and 90 became 78.2 as well. A shift says the
        # only thing the classifier actually claims: how much moving
        # band, at your position, is worth. Stay in your band and that
        # is zero, so your number is your number.
        here = _band_quantile(quantiles, _today_band(wellbeing_today, augmentation), rank)
        if here is None:
            return None
        per_class = {}
        for c in weights:
            there = _band_quantile(quantiles, BAND_INDEX[c], rank)
            if there is not None:
                # (there - here) is a move in wellbeing points; wellbeing
                # is `share` of the score, so that is what it is worth on
                # the user's own number.
                per_class[c] = max(0.0, min(
                    100.0, float(today_score) + share * (there - here)))
        if not per_class:
            return None
        weights = {c: w for c, w in weights.items() if c in per_class}
        remaining = sum(weights.values())
        if remaining <= 0:
            return None
        weights = {c: w / remaining for c, w in weights.items()}
        mean = sum(weights[c] * per_class[c] for c in weights)
        second_moment = sum(weights[c] * per_class[c] ** 2 for c in weights)
        mixture_variance = max(second_moment - mean ** 2, 0.0)
        # Two independent sources of error: which band (the mixture) and
        # how well the estimator does even when the band is right.
        # Three independent sources of error now: which band (the
        # mixture), how well the estimator does when the band is right,
        # and how noisy this user's own week has been around its trend.
        shift, residual_sd = _momentum(recent_scores)
        mean = max(0.0, min(max(mean, SCORE_CEILING), mean + shift))
        total_variance = mixture_variance + _augmented_error_sigma() ** 2 + residual_sd ** 2
        spread = Z_80 * math.sqrt(total_variance)

        return FutureScoreResult(
            available=True,
            score=round(mean, 1),
            lower=round(max(0.0, mean - spread), 1),
            upper=round(min(100.0, mean + spread), 1),
            predicted_class=predicted_class or max(weights, key=weights.get),
            class_probabilities={c: round(p, 4) for c, p in weights.items()},
            basis="augmented_rank" if not shift else "augmented_rank_momentum",
            momentum_shift=round(shift, 1),
            momentum_days=len([v for v in (recent_scores or []) if v is not None][-MOMENTUM_WINDOW:]),
        )

    @staticmethod
    def mode() -> str:
        return DEFAULT_MODE

    @staticmethod
    def augmentation_summary() -> Optional[dict[str, Any]]:
        return _augmentation()

    @staticmethod
    def calibration_summary() -> Optional[dict[str, Any]]:
        """For the model-performance page, which has to be able to show
        exactly how this number is produced."""
        return _calibration()
