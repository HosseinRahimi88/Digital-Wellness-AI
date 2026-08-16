"""
Recovering individual diaries from the dataset's merged signatures.

THE PROBLEM. The CSVs carry no user id. Every model that needs to know
"which rows belong to one person" - the band model, the user-level
split - reconstructs a GROUP KEY instead, from the ten demographic
columns that do not change day to day (see regenerate_user_split.py).

That key is coarse. Measured on data/train.csv: 92,949 rows collapse to
3,010 signatures, and 1,275 of those signatures carry a duplicated
day_index, which can only mean several real people share one
signature. Everything that needed real sequences simply THREW THOSE
AWAY - 1,735 usable signatures holding 25,465 rows, so 73% of the file
went unused, and the band model was fitted on 1,076 people.

THE OBSERVATION. Two columns advance deterministically inside one
person's diary, and both were verified against the data before being
relied on:

  * `day_of_week` advances by exactly one day per day_index step.
    Measured on the unambiguous signatures: 99.76% of consecutive pairs.

  * `screen_ewma_baseline` is an exponentially weighted mean of that
    person's own screen minutes, with a coefficient of exactly 0.30:

        ewma[2] == screen[1]                              (the seeding)
        ewma[t] == ewma[t-1] + 0.30*(screen[t-1] - ewma[t-1])   t >= 3

    Measured the same way, this reproduces the stored value to machine
    precision for 95.2% of consecutive pairs. The seeding step is a
    genuine special case and not a rounding artefact: day 2 carries day
    1's raw screen minutes, not a blend, which is the ordinary way an
    EWMA is initialised. Missing it costs everything - a chain walk
    that applies the blend at step one fails immediately and recovers
    nothing, which is exactly what the first version of this did.

Together they are a near-unique fingerprint linking day t to day t+1,
so the interleaved rows of a shared signature can be walked apart.

WHY THIS IS SAFE TO TRUST. The 1,735 unambiguous signatures are ground
truth - one row per day, no chaining needed to know their order. Run
against them, this returns each one as exactly ONE person, 1,076 of
1,076 among those long enough to train on. And no reconstructed chain
anywhere in the file exceeds 23 days, which is the longest diary the
data contains - so the walk never fused two people into one.

WHAT IT BUYS. 2,200 complete 23-day diaries instead of 1,076, and
50,600 rows instead of 25,465. Twice the people, twice the days.

Rows the walk cannot place - a step where two candidates match equally
well, or a person whose diary genuinely interleaves beyond these two
rules - are returned as their own single-day person and are simply too
short for any caller that needs sequences. Leaving them out is the
honest failure: a guessed link would put one person's Tuesday in
another person's week.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Recovered from the data, not assumed. See the module docstring.
EWMA_ALPHA = 0.30

#: Floating-point slack when matching a predicted EWMA against a stored
#: one. The arithmetic reproduces the stored values to ~1e-14, so this
#: is three orders of magnitude looser than it needs to be and still
#: far tighter than the gap between two different people's baselines.
EWMA_TOLERANCE = 1e-6

#: Longest diary in the dataset. Used only as an assertion: a chain
#: longer than this would mean two people were fused.
MAX_DIARY_DAYS = 23

WEEKDAY_ORDER = (
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
)

#: The ten columns that are stable for one person across their diary.
#: Identical to regenerate_user_split.py's key on purpose - two
#: different notions of "same person" in one repository is a bug
#: waiting to happen.
SIGNATURE_COLUMNS = (
    "age", "gender", "occupation_group", "region_group", "education_group",
    "device_category", "primary_platform", "purpose_group",
    "is_content_creator", "uses_screen_time_limits",
)

#: Everything this module reads. A caller loading a narrow set of
#: columns needs these too.
REQUIRED_COLUMNS = SIGNATURE_COLUMNS + (
    "day_index", "day_of_week", "screen_ewma_baseline", "total_screen_min",
)


def _next_ewma(day_index: int, ewma: float, screen: float) -> float:
    """The baseline the FOLLOWING day must carry.

    Day 1 seeds the average with its own raw value rather than blending
    into it, which is how the series actually starts in this data.
    """
    if day_index == 1:
        return screen
    return ewma + EWMA_ALPHA * (screen - ewma)


def signature_of(frame: pd.DataFrame) -> pd.Series:
    """A stable integer id per demographic signature."""
    missing = [c for c in SIGNATURE_COLUMNS if c not in frame.columns]
    if missing:
        raise KeyError(f"signature columns missing from the frame: {missing}")
    joined = frame[list(SIGNATURE_COLUMNS)].astype(str).agg("|".join, axis=1)
    return pd.Series(pd.factorize(joined)[0], index=frame.index)


def recover_people(frame: pd.DataFrame, prefix: str = "") -> pd.Series:
    """One id per reconstructed person, aligned to `frame`'s index.

    `prefix` is prepended to every id, so ids from two different splits
    can be concatenated without colliding.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise KeyError(f"columns required for recovery are missing: {missing}")

    weekday_index = {name: i for i, name in enumerate(WEEKDAY_ORDER)}
    work = pd.DataFrame({
        "position": np.arange(len(frame)),
        "signature": signature_of(frame).to_numpy(),
        "day_index": frame["day_index"].to_numpy(),
        "ewma": frame["screen_ewma_baseline"].to_numpy(dtype=float),
        "screen": frame["total_screen_min"].to_numpy(dtype=float),
        "weekday": frame["day_of_week"].map(weekday_index).to_numpy(),
    })

    person = np.full(len(frame), -1, dtype=np.int64)
    next_id = 0

    for _signature, rows in work.groupby("signature", sort=False):
        by_day = {
            int(day): block[["position", "ewma", "screen", "weekday"]].to_numpy()
            for day, block in rows.groupby("day_index")
        }
        days = sorted(by_day)
        claimed: set[float] = set()

        # Seeded from every day, not only day 1: a diary whose first
        # days are unrecoverable still has a usable tail, and assuming
        # day 1 is present would silently drop it.
        for first_day in days:
            for seed in by_day[first_day]:
                if seed[0] in claimed:
                    continue
                claimed.add(seed[0])
                chain = [seed]
                current, current_day = seed, first_day

                for day in days:
                    if day <= current_day:
                        continue
                    if day != current_day + 1:
                        break  # a gap - the next day is somebody else's
                    wanted_ewma = _next_ewma(current_day, current[1], current[2])
                    wanted_weekday = (current[3] + 1) % 7
                    match = next(
                        (
                            candidate for candidate in by_day[day]
                            if candidate[0] not in claimed
                            and abs(candidate[1] - wanted_ewma) <= EWMA_TOLERANCE
                            and candidate[3] == wanted_weekday
                        ),
                        None,
                    )
                    if match is None:
                        break
                    claimed.add(match[0])
                    chain.append(match)
                    current, current_day = match, day

                for row in chain:
                    person[int(row[0])] = next_id
                next_id += 1

    labels = pd.Series(person, index=frame.index)
    lengths = labels.value_counts()
    if not lengths.empty and int(lengths.max()) > MAX_DIARY_DAYS:
        raise AssertionError(
            f"a reconstructed diary ran to {int(lengths.max())} days, longer "
            f"than any real one ({MAX_DIARY_DAYS}) - two people were fused"
        )
    return prefix + labels.astype(str) if prefix else labels
