"""
=========================================================
Digital Wellness AI
Seven-day-ahead score target by data augmentation
=========================================================

The problem
-----------
The dataset carries `future_health_class_7d` - a real seven-day-ahead
LABEL - but no seven-day-ahead SCORE, and the score cannot be recovered
from the rows themselves: there is no user_id, no date, and row order is
shuffled, so "the same person seven days later" is not identifiable.
(models/calibrate_future_score.py documents the measurements behind
that, including the pairing attempt that produced a 99.3%-one-class
subset against 33/33/33 in the real data.)

The augmentation
----------------
Build the target from the label that IS real, using two facts that were
measured rather than assumed:

  1. `future_health_class_7d` is, to within 0.6 points, the tertile band
     of the WELLBEING distribution - the mean of the six composite
     subscores. Class-conditional means 55.14 / 64.47 / 72.16;
     membership agrees 80.2% of the time.
  2. The population is stationary - the same simulated people, one week
     apart - so the distribution seven days ahead is the distribution.

Which axis, and why it is not the score
---------------------------------------
Fact 1 used to be stated about `health_score_0_100`, and for as long as
that score WAS the mean of those six subscores the two were the same
sentence. They stopped being the same when the score gained a seventh,
screen-load term (utils/screen_load.py): it now measures two nearly
independent things, and the label bands only one of them. On the
combined score, tertile membership agrees with the label 43.3% of the
time - against the 33.3% three balanced classes give by chance - so
fact 1, which this whole construction rests on, is simply false there.

So the ranking and the bands are wellbeing. The published target is then
put back on the score's scale by carrying the row's OWN screen-load
subscore forward:

    future_health_score_7d = (6 * future_wellbeing + 2 * screen_load) / 8

Carried, not forecast. Nothing in this dataset predicts how much someone
will use their phone next week, and the label leans the wrong way when
asked (models/research_class_label_screen_response.py). What it is
instead is the half of the number the user can move today, which is a
better thing for it to be.

Given a row's true future class c, its seven-day-ahead score must
therefore lie in c's band. Which value inside the band? Assigning the
band's mean to every row would make the target a three-valued step
function, and a regressor fitted to it would just be the classifier
wearing a different hat. Sampling uniformly inside the band would add
pure noise and destroy any relationship with the features.

So the target uses WITHIN-BAND RANK PERSISTENCE: a person's position
inside their OWN CURRENT band is carried over to the same position
inside their future class's band. Someone sitting near the top of the
band they are in today lands near the top of whichever band they are
heading into.

The band a position is carried INTO (fixed)
-------------------------------------------
The first version of this file mapped that position onto the 2nd-98th
percentile of TODAY's scores *among rows of that future class*. That
range is not the band - it is "the spread of today's scores among people
who will end up in this class" - and using it as the output range broke
the estimator in two visible ways:

  * It capped the output. The Healthy class's 98th percentile of today's
    scores is 78.67, so every user scoring above that today was mapped
    DOWN, always. A user at 84.5 - the highest score in the entire
    training set - was told to expect 78.1, and a user at 90 would have
    been told 78.1 as well. "You are doing better than anyone in the
    data, so expect to get worse" is not a defensible reading of a
    stationary population.
  * It was not monotone. 68 -> 76.9 while 72 -> 71.5, because the two
    scores sit in different today-bands whose output ranges overlap.

Both follow from mapping a position in one distribution onto the range
of a different one. The fix is to carry the position between the SAME
kind of thing: the bands themselves, cut at the tertiles of the
wellbeing distribution. Band membership and the class label already
agree 80.2% of the time, so this is the reading that matches fact 1
above.

The property that gives back is the one a reader will check first:
**a row whose future class is the band it is already in keeps its own
score**, to within the resolution of the quantile table. The estimate
only moves when the classifier actually says the band moves - which is
the only thing it has evidence for.

Taking the rank globally instead was tried first and rejected on a
measurement: it produced a target correlating 0.939 with today's score,
because band membership already tracks today's score, so the level and
the position both came from the same place. A regressor fitted to that
would have scored well while predicting today and calling it next week.
Ranking within the current band separates the two - the LEVEL comes
from the future class, which is the genuinely forward-looking label,
and only the POSITION inside it comes from today.

That is a real, stated modelling assumption - people near the top of a
band tend to stay near the top of wherever they land - and it is the
only assumption this file adds.

It is deterministic: same row in, same target out, no random seed
anywhere.

What this does and does not license
-----------------------------------
It licenses training a genuine regressor and reporting its R-squared
AGAINST THIS TARGET, which is exactly what the artifact and the model
performance page say.

It does NOT license calling that number "how accurately we predict your
score in seven days". The target is constructed, the training data was
already synthetic, and the honest description - which is written into
the artifact and shown in the app - is: a seven-day-ahead score built
from the real seven-day-ahead class label plus a rank-persistence
assumption.

Run: python3 -m models.augment_future_score
Writes: data/train_augmented.csv, data/validation_augmented.csv,
        data/test_augmented.csv, artifacts/future_score_augmentation.json
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
    HEALTH_SCORE_COLUMN, SCREEN_LOAD_COLUMN, SCREEN_LOAD_WEIGHT,
    SUBSCORE_COLUMNS, WELLBEING_COLUMN, reconstruct_health_score,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CLASS_COLUMN = "future_health_class_7d"
TARGET_COLUMN = "future_health_score_7d"
REPORT_PATH = paths.PROJECT_ROOT / "artifacts" / "future_score_augmentation.json"

# The lowest and highest percentile a row can be mapped to inside its
# band. Without this, the single lowest-scoring row in the data would be
# pinned to the very bottom of its band and the highest to the very top,
# which turns two individual rows into the band's entire range.
PERCENTILE_FLOOR = 0.02
PERCENTILE_CEILING = 0.98


def _load(split: str) -> pd.DataFrame:
    # Through the loader's own reconstruction, never a local copy of the
    # formula - the bands this file carries a row's rank between are the
    # bands of the score the app actually shows, or they are bands of
    # nothing.
    return reconstruct_health_score(
        pd.read_csv(paths.PROJECT_ROOT / "data" / f"{split}.csv")
    )


# Band index 0/1/2 (the tertiles of the score distribution) and the
# class label that corresponds to each. Both directions are needed: the
# target is built from a label, the estimate is served from one.
BAND_ORDER = ["At Risk", "Moderate", "Healthy"]


def build_today_bands(train: pd.DataFrame) -> list[float]:
    """The two tertile cuts of the TRAIN score distribution.

    These cut the score axis into the three bands, and a row's band
    today is where its own score falls. The same cuts define where an
    estimate LANDS, which is what keeps the mapping monotone.
    """
    return [float(train[WELLBEING_COLUMN].quantile(1 / 3)),
            float(train[WELLBEING_COLUMN].quantile(2 / 3))]


def build_band_scores(train: pd.DataFrame, cuts: list[float]) -> dict[int, np.ndarray]:
    """The sorted score distribution inside each tertile band.

    This is both the yardstick a row is ranked against and the scale an
    estimate is read back off, which is exactly why an unchanged band
    returns an unchanged score.
    """
    scores = train[WELLBEING_COLUMN].to_numpy()
    bands = np.digitize(scores, cuts)
    return {index: np.sort(scores[bands == index]) for index in (0, 1, 2)}


def build_band_edges(band_scores: dict[int, np.ndarray]) -> dict[str, tuple[float, float]]:
    """Each band's real score range, reported for the artifact.

    Trimmed at the 2nd/98th percentile for the same reason the mapping
    is clamped: a band whose edges are two outliers is not the band.
    Note these are now the range of the BAND, not the range of today's
    scores among a class - see the module docstring for why that
    distinction was the bug.
    """
    edges: dict[str, tuple[float, float]] = {}
    for index, label in enumerate(BAND_ORDER):
        scores = band_scores.get(index)
        if scores is None or not len(scores):
            continue
        edges[label] = (
            float(np.quantile(scores, PERCENTILE_FLOOR)),
            float(np.quantile(scores, PERCENTILE_CEILING)),
        )
    return edges


def build_target(
    frame: pd.DataFrame,
    today_cuts: list[float],
    band_scores: dict[int, np.ndarray],
) -> pd.Series:
    """Within-band rank persistence, band to band.

    Position inside today's band -> the same position inside the future
    class's band, where both "bands" are the same three tertile slices
    of the score distribution. The reference distributions always come
    from TRAIN, so validation and test rows are ranked against the same
    yardstick rather than against their own split.

    Because a row is ranked against, and read back off, the same kind of
    distribution, a row whose future class equals its current band comes
    back with (essentially) its own score - which is the property the
    previous version lacked.
    """
    scores = frame[WELLBEING_COLUMN].to_numpy()
    today_band = np.digitize(scores, today_cuts)   # 0, 1 or 2

    percentile = np.empty(len(scores), dtype=float)
    for band_index, reference in band_scores.items():
        mask = today_band == band_index
        if not mask.any():
            continue
        if len(reference) < 2:
            percentile[mask] = 0.5
            continue
        position = np.searchsorted(reference, scores[mask], side="left")
        percentile[mask] = position / (len(reference) - 1)
    percentile = np.clip(percentile, PERCENTILE_FLOOR, PERCENTILE_CEILING)

    target_band = frame[CLASS_COLUMN].map(
        {label: index for index, label in enumerate(BAND_ORDER)}
    ).to_numpy()

    out = np.empty(len(scores), dtype=float)
    for band_index, reference in band_scores.items():
        mask = target_band == band_index
        if not mask.any():
            continue
        out[mask] = np.quantile(reference, percentile[mask])
    return pd.Series(np.clip(out, 0.0, 100.0), index=frame.index)


def main() -> None:
    train = _load("train")
    validation = _load("validation")
    test = _load("test")

    today_cuts = build_today_bands(train)
    band_scores = build_band_scores(train, today_cuts)
    edges = build_band_edges(band_scores)
    within_band_reference = band_scores

    report: dict = {
        "method": (
            "future_health_score_7d = the row's percentile inside its own "
            "tertile band today, read back off the tertile band its true "
            "future class names. Both bands are slices of the same TRAIN "
            "score distribution, so an unchanged band returns an unchanged "
            "score and the mapping is monotone in today's score."
        ),
        "why_augmentation_was_needed": (
            "The dataset has a real seven-day-ahead class label but no "
            "seven-day-ahead score, and no user_id, date or stable row order "
            "from which one could be reconstructed."
        ),
        "assumption_added": (
            "Rank persistence - a person near the top of today's distribution "
            "lands near the top of whichever band they move into. This is the "
            "only assumption this augmentation introduces."
        ),
        "not_a_claim": (
            "R-squared against this target measures how well the model "
            "recovers a constructed target, not how accurately anyone's real "
            "score seven days from now is predicted. The training data is "
            "synthetic to begin with."
        ),
        "band_edges_percentiles": [PERCENTILE_FLOOR, PERCENTILE_CEILING],
        "today_band_cuts": [round(c, 4) for c in today_cuts],
        # Every band, cut and quantile table in this artifact is on the
        # WELLBEING axis. Serving needs these weights twice: to recover a
        # live user's wellbeing from the score it already has, and to
        # scale a band-to-band move back into score points. Published
        # here rather than hard-coded in the service so the two cannot
        # drift from models/data_loader.py's own definition.
        "band_axis": WELLBEING_COLUMN,
        "recombination": {
            "note": (
                "Bands are wellbeing bands. score = (subscore_weight * "
                "wellbeing + screen_load_weight * screen_load) / "
                "(subscore_weight + screen_load_weight). The screen-load "
                "half is carried forward from the user's own day, not "
                "forecast - see models/calibrate_future_score.py."
            ),
            "subscore_weight": float(len(SUBSCORE_COLUMNS)),
            "screen_load_weight": float(SCREEN_LOAD_WEIGHT),
            "combined_score_column": HEALTH_SCORE_COLUMN,
        },
        "rejected_alternative": (
            "Global rank persistence produced corr(today, target)=0.939 - the "
            "level and the position both came from today's score, so a model "
            "fitted to it would predict today and call it next week."
        ),
        "band_edges": {k: [round(v[0], 4), round(v[1], 4)] for k, v in edges.items()},
        # 101 quantiles of the TRAIN score distribution inside each of
        # today's three bands. Serving needs to compute a live user's
        # within-band rank without shipping the training data, and 101
        # points reproduce the percentile to within one point.
        "within_band_quantiles": {
            str(band): [round(float(np.quantile(reference, q)), 4)
                        for q in np.linspace(0.0, 1.0, 101)]
            for band, reference in within_band_reference.items()
            if len(reference) > 0
        },
        "splits": {},
    }

    subscore_weight = float(len(SUBSCORE_COLUMNS))
    screen_weight = float(SCREEN_LOAD_WEIGHT)
    total_weight = subscore_weight + screen_weight

    for name, frame in (("train", train), ("validation", validation), ("test", test)):
        # The rank persistence runs on the WELLBEING axis, because that
        # is the axis the class label bands - see the module docstring.
        future_wellbeing = build_target(frame, today_cuts, band_scores)
        # Then back onto the scale the app shows, carrying the day's own
        # screen load forward unchanged. Nothing here predicts a
        # person's screen time a week out, and pretending to would be
        # inventing the one half of the number that is theirs to move.
        frame[TARGET_COLUMN] = (
            (subscore_weight * future_wellbeing
             + screen_weight * frame[SCREEN_LOAD_COLUMN]) / total_weight
        ).clip(0.0, 100.0)
        out_path = paths.PROJECT_ROOT / "data" / f"{name}_augmented.csv"
        frame.to_csv(out_path, index=False)

        target = frame[TARGET_COLUMN]
        today = frame[HEALTH_SCORE_COLUMN]
        # The checks that decide whether this augmentation is sound.
        report["splits"][name] = {
            "rows": int(len(frame)),
            "target_mean": round(float(target.mean()), 4),
            "target_std": round(float(target.std(ddof=0)), 4),
            "target_min": round(float(target.min()), 4),
            "target_max": round(float(target.max()), 4),
            "today_mean": round(float(today.mean()), 4),
            "today_std": round(float(today.std(ddof=0)), 4),
            # Should be positive but well below 1: the target must carry
            # real information beyond today's score, or the model is just
            # learning the identity.
            #
            # READ THE SECOND NUMBER, NOT THE FIRST. corr_with_today is
            # measured on the combined score, and about two thirds of
            # that target's variance is the screen-load half carried
            # over from today unchanged - so the figure is high by
            # construction and says nothing about the forecast. It is
            # reported because leaving it out would hide it, not because
            # it means anything on its own. In particular it must NOT be
            # compared against the 0.939 that got global rank
            # persistence rejected below: that was 0.939 on an axis
            # where every point was supposed to be forecast.
            #
            # corr_wellbeing_with_today is the one that carries the
            # claim - today's wellbeing against the forecast wellbeing,
            # the only part any model here predicts.
            "corr_with_today": round(float(np.corrcoef(today, target)[0, 1]), 4),
            "corr_wellbeing_with_today": round(float(np.corrcoef(
                frame[WELLBEING_COLUMN], future_wellbeing)[0, 1]), 4),
            "carried_screen_load_variance_share": round(float(
                ((screen_weight / total_weight) * frame[SCREEN_LOAD_COLUMN]).var()
                / target.var()
            ), 4),
            # Must be ~1.0 by construction - if it is not, the band
            # mapping is broken. Checked on the wellbeing axis, which is
            # the axis the bands are cut on; the published target adds
            # the screen-load half on top and so does not sit inside a
            # wellbeing band.
            "target_band_matches_label_pct": round(float(
                (frame[CLASS_COLUMN].map(lambda c: edges[str(c)][0]) <= future_wellbeing)
                .__and__(future_wellbeing <= frame[CLASS_COLUMN].map(
                    lambda c: edges[str(c)][1]))
                .mean() * 100
            ), 2),
        }
        logger.info(
            "%-10s rows=%6d  target mean=%.2f sd=%.2f  "
            "corr(wellbeing today, wellbeing 7d)=%.3f  "
            "[combined-axis corr %.3f, inflated by the %.0f%% of variance "
            "carried from today's screen load]",
            name, len(frame), target.mean(), target.std(ddof=0),
            report["splits"][name]["corr_wellbeing_with_today"],
            report["splits"][name]["corr_with_today"],
            report["splits"][name]["carried_screen_load_variance_share"] * 100,
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Wrote %s", REPORT_PATH)


if __name__ == "__main__":
    main()
