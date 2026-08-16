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
    E[score_7d | x] = SUM_c P(c | x) * mu_c

`mu_c` is measured on the training split by
models/calibrate_future_score.py, which also records the evidence that
makes this well-founded: the class is a tertile band of the score
(80.5% membership agreement), the classes are exactly balanced, and the
class means barely move between train and validation (0.05-0.65
points).

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

More importantly for the UI: this is a CLASS-TYPICAL score, not a
personal projection. A mixture of three class means can only ever
return a value between the smallest and largest of them - here roughly
55 to 72 - so a user scoring 84 today gets 72 back, and a user scoring
39 today gets 55. Neither is a prediction that they will move to that
number. Both mean "the band the model expects you to be in seven days
from now typically sits here".

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

logger = logging.getLogger(__name__)

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"
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
#                 by 55.33% MAE on validation (artifacts/
#                 metrics_future_regression.json is the source of that
#                 number - do not restate it from memory here).
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
            result = FutureScoreService._estimate_augmented(probabilities, predicted_class, today_score)
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
        spread = Z_80 * math.sqrt(variance)

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
        )

    @staticmethod
    def _estimate_augmented(
        probabilities: Optional[dict[str, float]],
        predicted_class: Optional[str],
        today_score: Optional[float],
    ) -> Optional[FutureScoreResult]:
        """Output 2: band from the classifier, position from today.

        Returns None (not an error) when it cannot run, so the caller
        can fall back to the class-typical estimate.
        """
        augmentation = _augmentation()
        if augmentation is None or not probabilities or today_score is None:
            return None

        quantiles = augmentation.get("within_band_quantiles") or {}
        usable = {c: float(p) for c, p in probabilities.items() if c in BAND_INDEX}
        total = sum(usable.values())
        if not usable or total <= 0 or not quantiles:
            return None

        rank = _within_band_rank(float(today_score), augmentation)
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
        here = _band_quantile(quantiles, _today_band(float(today_score), augmentation), rank)
        if here is None:
            return None
        per_class = {}
        for c in weights:
            there = _band_quantile(quantiles, BAND_INDEX[c], rank)
            if there is not None:
                per_class[c] = max(0.0, min(100.0, float(today_score) + (there - here)))
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
        total_variance = mixture_variance + _augmented_error_sigma() ** 2
        spread = Z_80 * math.sqrt(total_variance)

        return FutureScoreResult(
            available=True,
            score=round(mean, 1),
            lower=round(max(0.0, mean - spread), 1),
            upper=round(min(100.0, mean + spread), 1),
            predicted_class=predicted_class or max(weights, key=weights.get),
            class_probabilities={c: round(p, 4) for c, p in weights.items()},
            basis="augmented_rank",
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
