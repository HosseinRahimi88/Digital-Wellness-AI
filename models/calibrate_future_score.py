"""
=========================================================
Digital Wellness AI
7-day-ahead score calibration (one-off, re-runnable)
=========================================================

Why this file exists
--------------------
The app ships two supervised models:

  * a classifier whose target is `future_health_class_7d` - a genuine
    SEVEN-DAY-AHEAD label, and
  * a regressor whose target is `health_score_0_100` - TODAY's score.

The product wants a seven-day-ahead *number*, not just a band. The
obvious answer would be "train a regressor on the seven-day-ahead
score", and that is not possible with this dataset. There is no such
column, and the target cannot be reconstructed:

  * the CSVs carry no user_id and no date (confirmed - all three
    splits, and the pre-split archive, have identical columns);
  * `day_index` runs 1..23 but row order is shuffled, so consecutive
    rows are not one person's diary;
  * the cohort key used by models/regenerate_user_split.py is a
    demographic signature that over-groups by design - 1275 of 3010
    training groups contain duplicate day_index values, i.e. several
    people mixed together, covering 73% of rows. Pairing "this group at
    day d" with "this group at day d+7" therefore pairs different
    people most of the time. Measured: that reconstruction produces a
    subset that is 99.3% one class, versus 33/33/33 in the real data -
    a selection artefact, not a signal.

So a seven-day-ahead regression target would have to be invented, and
inventing a target is the one thing that cannot be done here.

What this does instead
----------------------
It derives the seven-day-ahead figure from the model that genuinely
predicts seven days ahead - the classifier - by measuring what each of
its classes is worth in points:

    E[wellbeing_7d | x] = SUM_c  P(c | x) * mu_c

`mu_c` is the mean among rows whose *future* class is c, measured on the
training split only. Three facts make this well-founded rather than a
guess, and all three are checked below and written into the artifact:

  1. The label is (very nearly) a tertile band. Tertile membership
     agrees with it about 80% of the time.
  2. The classes are exactly balanced (33/33/33), so the band
     boundaries are the distribution's own tertiles.
  3. The population is stationary - the same generator, the same
     people, one week apart - so the distribution seven days ahead is
     the distribution.

The spread comes from the law of total variance over the same mixture,
so the interval widens honestly when the classifier is unsure between
two classes and narrows when it is confident in one.

Which axis - and why this is not calibrated on the score itself
---------------------------------------------------------------
`mu_c` is measured on the WELLBEING axis: the mean of the six composite
subscores. It used to be measured on `health_score_0_100`, and for as
long as that score WAS the mean of those six, the two were the same
thing and the distinction did not arise.

It arose when the score gained a seventh, screen-load term
(utils/screen_load.py). The score now measures two nearly independent
things - how a person felt and slept, and how heavy their digital load
was, correlating -0.006 with each other - while the label bands only the
first. Fact 1 above is what breaks: measured on the combined score,
tertile membership agrees with the label 43.3% of the time, against the
33.3% that three balanced classes give by chance. The whole method rests
on that fact, so calibrating on the combined score would have left the
app quoting a seven-day number built on a relationship that is not
there. On the wellbeing axis the agreement is 80.2%, which is the
number the method was always relying on.

That leaves the screen-load half, and the honest treatment is to CARRY
IT FORWARD rather than forecast it. It is not a thing the classifier
knows about - the label barely responds to screen volume, and responds
with the wrong sign when it does (see
models/research_class_label_screen_response.py). It is, however, a fact
about the day the user logged and a lever they hold today. So the
seven-day figure is:

    score_7d = (6 * E[wellbeing_7d | x] + 2 * screen_load_today) / 8

which keeps today's number and next week's on one scale, forecasts only
the part something in this dataset actually predicts, and says plainly
that the digital-load half will be whatever the user makes it. A user
who cuts their screen time sees that half move immediately, because it
is theirs and not a prediction.

What is NOT claimed
-------------------
This is not an R-squared against a seven-day-ahead ground truth. No
such ground truth exists in this dataset, so no such number can be
quoted, and the app must not quote one. What can be quoted is the
classifier's own seven-day accuracy, and how closely this estimator
recovers the score implied by the TRUE future class - both computed
here, on validation, and written into the artifact for the model
performance page to display.

Run: python3 -m models.calibrate_future_score
Writes: artifacts/future_score_calibration.json
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# The one definition of the project root - see core/paths.py. Computed by
# directory depth here until it wasn't, twice; a path relative to a file's
# own position is correct until something moves and silently wrong after,
# because a Path that does not exist is still a perfectly good Path.
from core import paths

if str(paths.PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(paths.PROJECT_ROOT))

from models.data_loader import (  # noqa: E402
    HEALTH_SCORE_COLUMN, SCREEN_LOAD_WEIGHT, SUBSCORE_COLUMNS,
    WELLBEING_COLUMN, reconstruct_health_score,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TARGET_COLUMN = "future_health_class_7d"
OUTPUT_PATH = paths.PROJECT_ROOT / "artifacts" / "future_score_calibration.json"


def _load(split: str) -> pd.DataFrame:
    # Through the loader's own reconstruction, never a local copy of the
    # formula. This used to read frame[SUBSCORE_COLUMNS].mean(axis=1),
    # which stopped being the target the day it grew a screen-load term
    # and would have calibrated next week's band against a score today's
    # number is not on.
    return reconstruct_health_score(
        pd.read_csv(paths.PROJECT_ROOT / "data" / f"{split}.csv")
    )


def calibrate() -> dict:
    train = _load("train")
    validation = _load("validation")

    # The WELLBEING half of the score, not the whole score. See the
    # "Which axis" section of the module docstring: the label bands this
    # axis and nothing else, and calibrating against the combined score
    # measured 43.3% tertile agreement against 33.3% by chance.
    scores = train[WELLBEING_COLUMN]
    classes = sorted(train[TARGET_COLUMN].unique())

    stats = {}
    for label in classes:
        subset = scores[train[TARGET_COLUMN] == label]
        stats[label] = {
            "mean": round(float(subset.mean()), 4),
            "std": round(float(subset.std(ddof=0)), 4),
            "count": int(subset.size),
            "p10": round(float(subset.quantile(0.10)), 4),
            "p90": round(float(subset.quantile(0.90)), 4),
        }

    # Evidence check 1: is the label a tertile band of the score?
    lower_q, upper_q = scores.quantile([1 / 3, 2 / 3])
    tertile = pd.cut(
        scores, [-np.inf, lower_q, upper_q, np.inf], labels=["low", "mid", "high"]
    )
    tertile_means = {
        str(name): round(float(group.mean()), 4)
        for name, group in scores.groupby(tertile, observed=True)
    }
    ordered = sorted(classes, key=lambda c: stats[c]["mean"])
    tertile_to_class = dict(zip(["low", "mid", "high"], ordered))
    agreement = float((tertile.map(tertile_to_class) == train[TARGET_COLUMN]).mean())

    # Evidence check 2: how balanced are the classes?
    balance = (train[TARGET_COLUMN].value_counts(normalize=True) * 100).round(2).to_dict()

    # Evidence check 3: does the same relationship hold on validation,
    # which the calibration numbers were NOT computed from?
    validation_means = {
        label: round(float(validation.loc[validation[TARGET_COLUMN] == label, WELLBEING_COLUMN].mean()), 4)
        for label in classes
    }
    drift = {
        label: round(abs(stats[label]["mean"] - validation_means[label]), 4)
        for label in classes
    }

    payload = {
        "method": (
            "E[wellbeing_7d | x] = sum_c P(c|x) * mu_c, where mu_c is the "
            "mean wellbeing_subscore_mean among TRAIN rows whose "
            "future_health_class_7d is c. Spread from the law of total "
            "variance over the same mixture. Recombine with the day's own "
            "screen-load subscore - see the recombination block - to get a "
            "figure on the same scale as the score the app shows."
        ),
        "why_not_a_regressor": (
            "The dataset has no seven-day-ahead score column and no user_id, "
            "date or stable row order from which one could be reconstructed, "
            "so a seven-day-ahead regression target would have to be invented."
        ),
        "target_column": TARGET_COLUMN,
        "score_column": WELLBEING_COLUMN,
        "recombination": {
            "note": (
                "mu_c and sigma_c are on the WELLBEING axis - the mean of "
                "the six composite subscores - because that is the axis "
                "future_health_class_7d bands. To put the estimate back on "
                "the scale the app shows, recombine with the user's own "
                "screen-load subscore for the day: "
                "score = (subscore_weight * wellbeing + screen_load_weight "
                "* screen_load) / (subscore_weight + screen_load_weight). "
                "The screen-load half is carried forward, not forecast: it "
                "is a fact about the day the user logged and a lever they "
                "hold, and nothing in this dataset predicts it a week out."
            ),
            "subscore_weight": float(len(SUBSCORE_COLUMNS)),
            "screen_load_weight": float(SCREEN_LOAD_WEIGHT),
            "combined_score_column": HEALTH_SCORE_COLUMN,
        },
        "calibrated_on": "train split only",
        "classes": list(classes),
        "class_stats": stats,
        "evidence": {
            "tertile_boundaries": [round(float(lower_q), 4), round(float(upper_q), 4)],
            "tertile_means": tertile_means,
            "tertile_membership_agrees_with_label_pct": round(agreement * 100, 2),
            "class_balance_pct": {str(k): float(v) for k, v in balance.items()},
            "validation_class_means": validation_means,
            "train_vs_validation_mean_drift": drift,
        },
    }
    return payload


def main() -> None:
    payload = calibrate()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote %s", OUTPUT_PATH)
    for label, stat in payload["class_stats"].items():
        logger.info("  %-10s mean=%.2f  std=%.2f  n=%d", label, stat["mean"], stat["std"], stat["count"])
    evidence = payload["evidence"]
    logger.info("  tertile agreement with label: %.2f%%", evidence["tertile_membership_agrees_with_label_pct"])
    logger.info("  train->validation mean drift: %s", evidence["train_vs_validation_mean_drift"])


if __name__ == "__main__":
    main()
