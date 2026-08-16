"""Train the personal week-band model.

WHAT IT REPLACES
----------------
The weekly plan's band was `weighted mean of this week's scores +/- 6.0`.
The 6.0 was a hand-picked constant, and measured against this dataset's
per-respondent day sequences it is wrong twice over:

  * it is too wide. It covers 98.7% of days, so a day lands outside it
    once every 78 days and the "unusual day, or a real change?"
    question - a whole feature, with its own UI, its own 0.25 exception
    weight and four languages of copy - is asked about once every
    eleven weeks;
  * it is the same for everybody. The half-width a respondent actually
    needs for 90% coverage runs from 2.70 (p10) to 5.14 (p90), a 1.9x
    spread, and 19% of respondents need less than half of 6.0.

So the band's CENTRE is left exactly as it was, and only its WIDTH
becomes a prediction. Every other weekly-plan rule is untouched.

WHAT IS TRAINED
---------------
Conformalized Quantile Regression (Romano, Patterson & Candes, 2019),
which is the same family as the split-conformal wrapper the shipped
score model already uses (services/ml/uncertainty_service.py) - so this
is the project's existing uncertainty discipline applied to a second
quantity, not a new one bolted on.

  1. a HistGradientBoostingRegressor with the pinball loss at
     TARGET_COVERAGE predicts, from a user's week so far, the quantile
     of |next day - running mean|. That is the raw half-width;
  2. a group-disjoint calibration set turns it into a real guarantee:
     the conformity score is (actual deviation - predicted half-width),
     and its ceiling quantile is added to every prediction. Marginal
     coverage of at least TARGET_COVERAGE then holds distribution-free,
     without assuming the model is any good.

Step 2 is why this is worth shipping over a plain quantile model: if
the regressor is badly calibrated, the correction absorbs it and the
band is still honest, only wider.

THE HONEST BASELINE GATE
------------------------
Two baselines are scored on the same held-out days:

  * the shipped constant, 6.0;
  * the BEST possible constant - the empirical quantile of the
    calibration set's deviations. This is the strong baseline, and it
    is the one that matters: beating 6.0 is trivial, beating the best
    constant is what proves that personalisation earns its place.

If the model does not beat the best constant, `beats_baseline` is
written false and the artifact is not promoted - the same rule that
kept models/train_future_regression.py's output out of production.

HOW THE ROWS ARE BUILT
----------------------
Exactly the way the live app computes a band, and no other way:

  * respondents are recovered by the same ten-column key
    models/regenerate_user_split.py uses, and only groups whose
    day_index values are unique are kept, since a duplicated day means
    the key merged two people and their days cannot be ordered;
  * each sequence is cut into 7-day blocks, because the live band
    resets every ISO week and never sees more than seven days;
  * within a block, every prefix of length t (1 <= t <= 6) is one
    training row: features from days 1..t, target |day t+1 - mean(1..t)|.

Run:  python3 -m models.train_band_model
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


# The one definition of the project root - see core/paths.py. Computed by
# directory depth here until it wasn't, twice; a path relative to a file's
# own position is correct until something moves and silently wrong after,
# because a Path that does not exist is still a perfectly good Path.
from core import paths
from models.data_loader import HEALTH_SCORE_COLUMN, reconstruct_health_score
from models.respondent_recovery import REQUIRED_COLUMNS, recover_people
from utils.screen_load import RECREATIONAL_FIELDS
from utils.band_features import (
    BAND_FEATURE_COLUMNS,
    HABIT_LAST_FIELDS,
    HABIT_SD_FIELDS,
    PRIOR_FEATURES,
    SEQUENCE_FEATURES,
    band_feature_vector,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("train_band_model")

# --------------------------------------------------------------- settings

# How often a day should fall INSIDE the band. 0.90 means roughly one
# day in ten is worth asking the user about - about two thirds of a
# question per week, which is a prompt somebody will actually read. The
# shipped constant's 98.7% is one question every eleven weeks, which is
# a feature nobody ever sees.
TARGET_COVERAGE = 0.90

# The live band resets with the ISO week, so the model must never be
# trained on a longer window than it will ever be given.
WEEK_LENGTH = 7

# A respondent needs enough days to yield more than one week block.
MIN_SEQUENCE_DAYS = 8

# Guard rails on the served half-width. Below the floor the band is
# narrower than the noise in a single self-reported day and would
# question everything; above the ceiling it spans most of the usable
# score range and stops meaning anything. Both are recorded in the
# artifact so the service cannot drift from what was calibrated.
MIN_HALF_WIDTH = 1.5
MAX_HALF_WIDTH = 15.0


# Share of the training respondents held back for conformal
# calibration. Group-disjoint from the fitting set - calibrating on
# days the model was fitted on is the classic way to produce a
# guarantee that is not one.
CALIBRATION_SHARE = 0.30
RANDOM_SEED = 42

GROUP_KEY = [
    "age", "gender", "occupation_group", "region_group", "education_group",
    "device_category", "primary_platform", "purpose_group",
    "is_content_creator", "uses_screen_time_limits",
]
SUBSCORES = [
    "sleep_subscore", "night_subscore", "focus_subscore",
    "balance_subscore", "stress_fatigue_subscore", "activity_context_subscore",
]
# The raw minute fields the seventh subscore is computed from. Read
# alongside the six so the `usecols` read still has everything
# reconstruct_health_score needs; without them it would find the
# columns missing and hand back a frame with no target at all.
SCREEN_LOAD_COLUMNS = list(RECREATIONAL_FIELDS) + [
    "pre_sleep_screen_min", "work_study_min",
]
HABIT_COLUMNS = sorted(set(HABIT_LAST_FIELDS) | set(HABIT_SD_FIELDS))

DATA_DIR = paths.PROJECT_ROOT / "data"
MODEL_PATH = paths.artifact("band_model.pkl")
INFO_PATH = paths.artifact("band_model_info.json")
METRICS_PATH = paths.artifact("metrics_band.json")
COLUMNS_PATH = paths.artifact("feature_columns_band.json")


# --------------------------------------------------------------- loading

def _load(split: str) -> pd.DataFrame:
    """One CSV, with the health score reconstructed and people recovered.

    The score comes from models/data_loader.reconstruct_health_score,
    the one definition the shipped models are trained on. This used to
    be `frame[SUBSCORES].mean(axis=1)` written out inline, on the
    reasoning that importing the loader would drag in a screen-time
    derived-feature rebuild this model has no use for and which costs a
    minute per split. The saving was real; the copy was still a bug
    waiting to happen, and it happened the moment the score grew a
    seventh screen-load term. This band model measures how far a
    person's days fall from their own average, so a copy left behind
    would have been predicting the spread of a score the app no longer
    shows. The imported function is the cheap half of the loader - the
    target only, no derived-feature rebuild - so the reason to copy it
    is gone.

    People come from models/respondent_recovery, which walks the
    interleaved rows of a shared demographic signature apart using two
    sequence rules recovered from the data. The ten-column key alone
    left 73% of the file unusable; see that module for what the rules
    are and how they were verified.
    """
    path = DATA_DIR / f"{split}.csv"
    needed = sorted(
        set(GROUP_KEY) | set(SUBSCORES) | set(HABIT_COLUMNS)
        | set(REQUIRED_COLUMNS) | set(SCREEN_LOAD_COLUMNS) | {"day_index"}
    )
    frame = pd.read_csv(path, usecols=needed)
    frame["health_score"] = reconstruct_health_score(frame)[HEALTH_SCORE_COLUMN]
    # Prefixed per split: two splits both numbering from 0 would
    # otherwise look like the same person once frames are concatenated.
    frame["respondent"] = recover_people(frame, prefix=f"{split}-")
    return frame


def _usable_sequences(frame: pd.DataFrame) -> pd.DataFrame:
    """People with enough consecutive days to yield a week block.

    Everything shorter is a day the recovery could not link into a
    diary - two candidates matched a step equally well, or the person's
    rows interleave beyond what the two rules can separate. Those are
    left out rather than guessed at: a wrong link would put one
    person's Tuesday inside another person's week, which is precisely
    the deviation this model measures.
    """
    grouped = frame.groupby("respondent")
    return grouped.filter(lambda rows: len(rows) >= MIN_SEQUENCE_DAYS)


# --------------------------------------------------------------- rows

def _rows(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(features, target, respondent) for every prefix of every week block."""
    features: list[list[float]] = []
    targets: list[float] = []
    owners: list[str] = []

    ordered = frame.sort_values(["respondent", "day_index"])
    for respondent, sequence in ordered.groupby("respondent", sort=False):
        scores = sequence["health_score"].to_numpy(dtype=float)
        days = sequence[HABIT_COLUMNS].to_dict("records")
        for start in range(0, len(scores), WEEK_LENGTH):
            block_scores = scores[start:start + WEEK_LENGTH]
            block_days = days[start:start + WEEK_LENGTH]
            # Everything this person logged BEFORE this week. Week one
            # gets an empty list, which is what a new user really has,
            # and the prior features come out NaN for it.
            prior = list(scores[:start])
            for cut in range(1, len(block_scores)):
                prefix = block_scores[:cut]
                features.append(
                    band_feature_vector(list(prefix), block_days[:cut], prior)
                )
                targets.append(abs(float(block_scores[cut]) - float(prefix.mean())))
                owners.append(respondent)

    return (
        np.asarray(features, dtype=float),
        np.asarray(targets, dtype=float),
        np.asarray(owners, dtype=object),
    )


# --------------------------------------------------------------- scoring

def _conformal_offset(deviations: np.ndarray, predicted: np.ndarray) -> float:
    """The CQR correction added to every predicted half-width.

    The conformity score is how far the true deviation overshot the
    predicted half-width; its ceiling quantile at TARGET_COVERAGE is
    what has to be added for the guarantee to hold. The (n+1)/n
    adjustment is the finite-sample correction - without it the
    guarantee is asymptotic only, and the calibration sets here are a
    few hundred respondents, not millions.
    """
    scores = deviations - predicted
    n = len(scores)
    if n == 0:
        return 0.0
    level = min(1.0, np.ceil((n + 1) * TARGET_COVERAGE) / n)
    return float(np.quantile(scores, level, method="higher"))


def _evaluate(
    deviations: np.ndarray, half_widths: np.ndarray, owners: np.ndarray,
) -> dict:
    """Coverage and width, marginally and per volatility tercile.

    The tercile split is the point of the exercise. A constant band can
    always hit its marginal coverage on average by being too wide for
    calm users and too narrow for volatile ones; the only way to see
    that is to bucket users by how much they actually move and check
    coverage inside each bucket. `worst_tercile_gap` is how far the
    worst bucket falls below target, and it is the number that decides
    whether personalisation was worth doing.
    """
    inside = deviations <= half_widths
    per_owner = pd.DataFrame(
        {"owner": owners, "dev": deviations, "in": inside, "width": half_widths}
    )
    volatility = per_owner.groupby("owner")["dev"].mean()
    # Three buckets by the respondent's own mean deviation. `duplicates`
    # guards the degenerate case of a tiny evaluation set whose tercile
    # edges collide.
    buckets = pd.qcut(volatility, 3, labels=["calm", "middle", "volatile"], duplicates="drop")
    per_owner["bucket"] = per_owner["owner"].map(buckets)

    # The width per bucket is what separates a personal band from a
    # constant at a glance: a constant reports the same number three
    # times, a personal one should widen from calm to volatile.
    by_bucket = {
        str(name): {
            "coverage": round(float(rows["in"].mean()), 4),
            "mean_half_width": round(float(rows["width"].mean()), 3),
            "days": int(len(rows)),
        }
        for name, rows in per_owner.groupby("bucket", observed=True)
    }
    worst = min((b["coverage"] for b in by_bucket.values()), default=float("nan"))
    low, mid, high = np.percentile(half_widths, [10, 50, 90])

    return {
        "coverage": round(float(inside.mean()), 4),
        "mean_half_width": round(float(np.mean(half_widths)), 3),
        "median_half_width": round(float(np.median(half_widths)), 3),
        # A constant collapses this to a single repeated number, which
        # is the whole difference being measured.
        "half_width_spread": {
            "p10": round(float(low), 3),
            "p50": round(float(mid), 3),
            "p90": round(float(high), 3),
            "min": round(float(np.min(half_widths)), 3),
            "max": round(float(np.max(half_widths)), 3),
        },
        "days": int(len(deviations)),
        "respondents": int(len(volatility)),
        "coverage_by_volatility": by_bucket,
        "worst_tercile_coverage": round(float(worst), 4),
        "worst_tercile_gap": round(float(TARGET_COVERAGE - worst), 4),
    }


# --------------------------------------------------------------- main

def _fit(features: np.ndarray, targets: np.ndarray) -> HistGradientBoostingRegressor:
    """The pinball-loss regressor, one place, so the ablation is a fair test."""
    model = HistGradientBoostingRegressor(
        loss="quantile",
        quantile=TARGET_COVERAGE,
        max_iter=400,
        learning_rate=0.06,
        max_depth=6,
        min_samples_leaf=40,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=RANDOM_SEED,
    )
    model.fit(features, targets)
    return model


def main() -> int:
    logger.info("Loading splits")
    train_frame = _usable_sequences(_load("train"))
    validation_frame = _usable_sequences(_load("validation"))
    test_frame = _usable_sequences(_load("test"))
    logger.info(
        "Usable respondents - train %d, validation %d, test %d",
        train_frame["respondent"].nunique(),
        validation_frame["respondent"].nunique(),
        test_frame["respondent"].nunique(),
    )

    # The fit/calibration split is by RESPONDENT, not by row: a
    # calibration set sharing people with the fitting set would report a
    # coverage the model does not have on anybody new.
    respondents = np.array(sorted(train_frame["respondent"].unique()))
    rng = np.random.default_rng(RANDOM_SEED)
    rng.shuffle(respondents)
    cut = int(round(len(respondents) * (1.0 - CALIBRATION_SHARE)))
    fit_ids, calibration_ids = set(respondents[:cut]), set(respondents[cut:])

    fit_x, fit_y, _ = _rows(train_frame[train_frame["respondent"].isin(fit_ids)])
    cal_x, cal_y, cal_owner = _rows(train_frame[train_frame["respondent"].isin(calibration_ids)])
    val_x, val_y, val_owner = _rows(validation_frame)
    test_x, test_y, test_owner = _rows(test_frame)
    logger.info(
        "Rows - fit %d, calibration %d, validation %d, test %d",
        len(fit_y), len(cal_y), len(val_y), len(test_y),
    )

    logger.info("Fitting the quantile regressor")
    model = _fit(fit_x, fit_y)

    offset = _conformal_offset(cal_y, model.predict(cal_x))
    logger.info("Conformal offset: %+.3f", offset)

    def half_widths(features: np.ndarray) -> np.ndarray:
        return np.clip(model.predict(features) + offset, MIN_HALF_WIDTH, MAX_HALF_WIDTH)

    # The strong baseline: the best single constant anyone could pick,
    # fitted on the same calibration days the model's offset came from.
    best_constant = float(np.quantile(cal_y, TARGET_COVERAGE, method="higher"))
    logger.info("Best possible constant half-width: %.3f (shipped constant: 6.0)", best_constant)

    results = {}
    for name, x, y, owner in (
        ("calibration", cal_x, cal_y, cal_owner),
        ("validation", val_x, val_y, val_owner),
        ("test", test_x, test_y, test_owner),
    ):
        results[name] = {
            "model": _evaluate(y, half_widths(x), owner),
            "best_constant": _evaluate(y, np.full(len(y), best_constant), owner),
            "shipped_constant_6": _evaluate(y, np.full(len(y), 6.0), owner),
        }

    # Ablation, run every time rather than trusted from memory. The
    # habit fields are the part of this model that could most easily be
    # decoration - the score sequence alone already knows a lot about
    # how much someone moves - so the score-only model is refitted and
    # scored the same way, and both numbers go in the artifact. If the
    # habit fields ever stop paying, this is where it shows.
    # Three nested feature sets, each refitted and conformalised the
    # same way and scored on the same held-out respondents. Nested on
    # purpose: the difference between two neighbours is exactly what
    # the block between them is worth, which a pair of full runs with
    # different data cannot tell you.
    #
    #   sequence        this week's scores only
    #   + prior         plus what the person's EARLIER weeks looked like
    #   + habit         plus the sleep/screen/stress fields (the shipped model)
    n_sequence = len(SEQUENCE_FEATURES)
    n_prior = len(PRIOR_FEATURES)
    ablations = {}
    for name, columns in (
        ("sequence_only", slice(0, n_sequence)),
        ("sequence_and_prior", slice(0, n_sequence + n_prior)),
    ):
        logger.info("Refitting on %s (ablation)", name)
        variant = _fit(fit_x[:, columns], fit_y)
        variant_offset = _conformal_offset(cal_y, variant.predict(cal_x[:, columns]))
        variant_widths = np.clip(
            variant.predict(test_x[:, columns]) + variant_offset,
            MIN_HALF_WIDTH, MAX_HALF_WIDTH,
        )
        ablations[name] = _evaluate(test_y, variant_widths, test_owner)

    held_out = results["test"]
    # Two conditions, both required. Marginal coverage is the promise
    # the band makes; the tercile gap is the thing only a personal band
    # can fix, and a model that hits its average by over-covering calm
    # users while under-covering volatile ones has not earned anything.
    covers = held_out["model"]["coverage"] >= TARGET_COVERAGE - 0.02
    fairer = held_out["model"]["worst_tercile_gap"] < held_out["best_constant"]["worst_tercile_gap"]
    beats_baseline = bool(covers and fairer)

    metrics = {
        "task": "personal_week_band_half_width",
        "method": "conformalized quantile regression (CQR)",
        "target_coverage": TARGET_COVERAGE,
        "conformal_offset": round(offset, 4),
        "best_constant_half_width": round(best_constant, 3),
        "shipped_constant_half_width": 6.0,
        "beats_baseline": beats_baseline,
        "gate": {
            "marginal_coverage_within_2pp_of_target": bool(covers),
            "worst_volatility_tercile_fairer_than_best_constant": bool(fairer),
        },
        "results": results,
        "ablations": {
            "note": (
                "Three nested feature sets, each refitted and conformalised "
                "identically and scored on the same held-out respondents. "
                "sequence_only -> sequence_and_prior is what knowing the "
                "person's earlier weeks is worth; sequence_and_prior -> "
                "results.test.model is what the sleep/screen/stress fields "
                "are worth. Nested rather than two separate runs, so each "
                "difference is attributable to one block."
            ),
            "sequence_only": ablations["sequence_only"],
            "sequence_and_prior": ablations["sequence_and_prior"],
            "full_model": held_out["model"],
        },
        "honest_description": (
            "Trained on synthetic per-respondent day sequences from the same "
            "grouped, leakage-checked split as the shipped models. Coverage is "
            "measured on held-out respondents, not held-out days of the same "
            "people. It says the band is calibrated on this data; it is not a "
            "claim about human behaviour."
        ),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    if not beats_baseline:
        logger.warning(
            "The model did not beat the best constant - artifact NOT written. "
            "See %s", METRICS_PATH,
        )
        print(json.dumps(metrics["results"]["test"], indent=2))
        return 1

    import joblib

    joblib.dump(model, MODEL_PATH)
    COLUMNS_PATH.write_text(
        json.dumps({"features": BAND_FEATURE_COLUMNS}, indent=2), encoding="utf-8",
    )
    INFO_PATH.write_text(json.dumps({
        "model": "HistGradientBoostingRegressor(loss='quantile')",
        "target_coverage": TARGET_COVERAGE,
        "conformal_offset": round(offset, 4),
        "min_half_width": MIN_HALF_WIDTH,
        "max_half_width": MAX_HALF_WIDTH,
        "week_length": WEEK_LENGTH,
        "n_features": len(BAND_FEATURE_COLUMNS),
        "fit_rows": int(len(fit_y)),
        "calibration_rows": int(len(cal_y)),
        "fit_respondents": len(fit_ids),
        "calibration_respondents": len(calibration_ids),
    }, indent=2), encoding="utf-8")

    logger.info("Written: %s", MODEL_PATH)
    print(json.dumps(metrics["results"]["test"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
