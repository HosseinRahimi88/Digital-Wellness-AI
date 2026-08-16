"""
What the seven-day class label does and does not know about screen time.
========================================================================
Run: python3 -m models.research_class_label_screen_response  (needs data/*.csv)
Writes: artifacts/class_label_screen_response.json

WHY THIS EXISTS
---------------
The regression target was rebuilt so that digital load actually counts:
`health_score_0_100` is now the six wellbeing subscores plus a
screen-load subscore measured against published thresholds
(utils/screen_load.py), and its correlation with recreational minutes
moved from +0.034 to -0.754.

The obvious next question is whether the same repair is needed - or even
possible - on the classification side, whose target is
`future_health_class_7d`. It is not the same situation, and the
difference matters enough to be measured rather than asserted.

`future_health_class_7d` is a REAL LABEL. It is the one genuinely
forward-looking quantity in the dataset: the wellness band seven days
after each row, written by the generator. The score target could be
rebuilt because it never existed as a column - it was always something
this project computed from the six subscores. The class is not that. It
is given, and rewriting it would mean inventing ground truth and then
reporting accuracy against the invention.

So this script does not change the label. It measures it, so that what
the classifier can and cannot be expected to notice is written down.

WHAT IT MEASURES
----------------
Spearman rank correlation between the ordinal class (At Risk 0,
Moderate 1, Healthy 2) and each screen quantity, plus the
class-conditional means, on train and validation separately.

WHAT IT FINDS
-------------
The label is not screen-blind. It responds strongly, and in the right
direction, to WHEN the screen was on:

    night_ratio            -0.646
    pre_sleep_ratio        -0.512
    night_screen_min       -0.430
    pre_sleep_screen_min   -0.396

and barely at all - with the sign inverted - to HOW MUCH:

    total_screen_min       +0.176
    recreational minutes   +0.106

Class-conditional means say the same thing plainly. "Healthy" days
average about 177 recreational minutes against 159 for "At Risk", while
night-time minutes run 15.9 against 32.0. Both patterns reproduce on
the validation split, so this is the generator's model of the world and
not a quirk of one split: it encoded late-night use as harmful and
daytime volume as roughly neutral.

WHAT FOLLOWS FROM IT
--------------------
1. The classifier is left alone. Its target, its features and its
   metrics are unchanged by the screen-load work, because
   `screen_load_subscore` is excluded from the feature set as a
   component of the other target, and the class itself never moved.

2. The recreational-volume half of the guidance cannot come from this
   label, and no amount of feature engineering will make it, because
   the signal is not in the target to be learned. It comes from the
   score instead, which is now measured against the published
   thresholds directly.

3. The seven-day NUMBERS the classification pipeline produces do inherit
   the repair, because both are built from `health_score_0_100` rather
   than from the label alone: models/calibrate_future_score.py takes
   each class's mean score, and models/augment_future_score.py carries a
   row's position within its current score band into its future band.
   Both must be re-run whenever the score definition changes, which is
   why they sit in the same retraining chain.

4. Nothing in the app may present the seven-day class as a verdict on
   today's screen volume. services/insight/future_score_service.py
   already separates the two horizons; this is the measurement that says
   why that separation is not cosmetic.
"""

from __future__ import annotations

import json
import logging
import sys

import pandas as pd

from core import paths

logger = logging.getLogger(__name__)

CLASS_COLUMN = "future_health_class_7d"
CLASS_ORDER = ["At Risk", "Moderate", "Healthy"]

RECREATIONAL_FIELDS = ["social_min", "gaming_min", "video_min", "other_min"]

TIMING_COLUMNS = [
    "night_ratio",
    "pre_sleep_ratio",
    "night_screen_min",
    "pre_sleep_screen_min",
]

VOLUME_COLUMNS = ["total_screen_min", "recreational_min", "work_study_min"]

OUTPUT = paths.PROJECT_ROOT / "artifacts/class_label_screen_response.json"


def _load(split: str) -> pd.DataFrame:
    frame = pd.read_csv(paths.PROJECT_ROOT / f"data/{split}.csv")
    frame["recreational_min"] = frame[RECREATIONAL_FIELDS].sum(axis=1)
    return frame


def _measure(frame: pd.DataFrame) -> dict:
    ordinal = frame[CLASS_COLUMN].map({name: i for i, name in enumerate(CLASS_ORDER)})
    columns = TIMING_COLUMNS + VOLUME_COLUMNS

    spearman = {
        column: round(float(ordinal.corr(frame[column], method="spearman")), 4)
        for column in columns
        if column in frame.columns
    }
    means = (
        frame.groupby(CLASS_COLUMN)[[c for c in columns if c in frame.columns]]
        .mean()
        .reindex(CLASS_ORDER)
        .round(2)
    )
    return {
        "rows": int(len(frame)),
        "spearman_with_ordinal_class": spearman,
        "class_conditional_means": {
            name: means.loc[name].to_dict() for name in CLASS_ORDER
        },
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    results = {}
    for split in ("train", "validation"):
        path = paths.PROJECT_ROOT / f"data/{split}.csv"
        if not path.exists():
            logger.error("Missing %s - run from the project root with data/ present.", path)
            return 1
        results[split] = _measure(_load(split))

    train = results["train"]["spearman_with_ordinal_class"]
    timing = [train[c] for c in TIMING_COLUMNS if c in train]
    volume = [train[c] for c in ("total_screen_min", "recreational_min") if c in train]

    results["conclusion"] = {
        "label_responds_to_screen_timing": all(value < -0.3 for value in timing),
        "label_responds_to_screen_volume": any(value < -0.1 for value in volume),
        "strongest_timing_signal": min(timing),
        "strongest_volume_signal": min(volume),
        "note": (
            "future_health_class_7d is a real seven-day-ahead label and is "
            "not rewritten. It encodes late-night and pre-sleep use as "
            "harmful and daytime recreational volume as roughly neutral, "
            "with the sign inverted. The volume half of the app's guidance "
            "therefore comes from health_score_0_100, which is measured "
            "against published thresholds in utils/screen_load.py, and not "
            "from this label."
        ),
    }

    for split in ("train", "validation"):
        logger.info("=== %s (%d rows) ===", split, results[split]["rows"])
        for column, value in results[split]["spearman_with_ordinal_class"].items():
            kind = "timing" if column in TIMING_COLUMNS else "volume"
            logger.info("  %-22s %-7s %+0.4f", column, kind, value)
        logger.info("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Wrote %s", OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
