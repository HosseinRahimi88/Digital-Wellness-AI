"""
Cohort reference
-----------------
The training cohort's distribution, precomputed once and shipped as a
small JSON file, so "where do you sit against the population the model
was fitted to" still answers when data/train.csv is not present.

Why this exists
----------------
services/ml/cohort_service.py reads the real 83MB training CSV. That is
the right source when it is there - and it is not there in any
distribution of this project, because shipping 175MB of training data
to show a percentile would be absurd. Before this file, every cohort
comparison in a delivered copy answered "unavailable", which reads as a
broken feature rather than a missing file.

What is stored
---------------
Per field: n, mean, median, p25, p75, and a 101-point quantile grid
(the empirical CDF at 0%, 1%, ... 100%). A percentile is then answered
by interpolating that grid - the same rank-based question the CSV
answers, to within a percentile, from about 12 KB.

Nothing here is a model, a guess, or a smoothed curve. It is the
measured distribution of the same rows, reduced.

Rebuild it with:
    python3 -m services.ml.cohort_reference --write
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional
from core import paths

PROJECT_ROOT = paths.PROJECT_ROOT
REFERENCE_PATH = PROJECT_ROOT / "artifacts" / "cohort_reference.json"

# The grid is quantiles at whole percents, so index == percentile.
GRID_POINTS = 101


@lru_cache(maxsize=1)
def load() -> Optional[dict]:
    """The shipped reference, or None if it is missing/unreadable."""
    try:
        with open(REFERENCE_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get("fields"):
        return None
    return data


def is_available() -> bool:
    return load() is not None


def cohort_size() -> int:
    data = load()
    return int(data.get("n", 0)) if data else 0


def summary_for(field: str) -> Optional[dict[str, float]]:
    data = load()
    if not data:
        return None
    row = data["fields"].get(field)
    if not row:
        return None
    return {
        "mean": row["mean"], "median": row["median"],
        "p25": row["p25"], "p75": row["p75"],
    }


def percentile_for(field: str, value: float) -> Optional[float]:
    """What percentage of the cohort sits at or below `value`.

    Read off the stored CDF grid by bisection, then linearly
    interpolated between the two bracketing percentiles - so a value
    halfway between the 40th and 41st percentile's quantiles reports
    40.5 rather than snapping to a whole percent.
    """
    data = load()
    if not data:
        return None
    row = data["fields"].get(field)
    if not row or not row.get("grid"):
        return None
    grid = row["grid"]
    if value <= grid[0]:
        return 0.0
    if value >= grid[-1]:
        return 100.0
    low, high = 0, len(grid) - 1
    while high - low > 1:
        mid = (low + high) // 2
        if grid[mid] <= value:
            low = mid
        else:
            high = mid
    span = grid[high] - grid[low]
    within = 0.0 if span <= 0 else (value - grid[low]) / span
    step = 100.0 / (len(grid) - 1)
    return round((low + within) * step, 1)


# --------------------------------------------------------------- build

def build(write: bool = False) -> dict:
    """Compute the reference from the real training CSV.

    Only ever run by hand (or by the test that checks the shipped file
    still matches the data, when the data is present). It imports pandas
    and the cohort service on purpose - this half of the module is a
    tool, and nothing at runtime should pay for it.
    """
    from services.ml.cohort_service import COHORT_FIELDS, _load_cohort_frame

    frame = _load_cohort_frame()
    if frame is None:
        raise FileNotFoundError(
            "data/train.csv is not present, so the reference cannot be rebuilt."
        )

    fields: dict[str, dict] = {}
    for field in COHORT_FIELDS:
        if field not in frame.columns:
            continue
        column = frame[field].dropna()
        if column.empty:
            continue
        grid = [
            round(float(column.quantile(i / (GRID_POINTS - 1))), 4)
            for i in range(GRID_POINTS)
        ]
        fields[field] = {
            "n": int(len(column)),
            "mean": round(float(column.mean()), 2),
            "median": round(float(column.median()), 2),
            "p25": round(float(column.quantile(0.25)), 2),
            "p75": round(float(column.quantile(0.75)), 2),
            "grid": grid,
        }

    data = {
        "source": "data/train.csv",
        "n": int(len(frame)),
        "grid_points": GRID_POINTS,
        "fields": fields,
        "note": (
            "Empirical quantiles of the training cohort, reduced from the "
            "real CSV. The training data is synthetic; this is the "
            "distribution the shipped models were fitted to, not a "
            "measurement of any human population."
        ),
    }
    if write:
        REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REFERENCE_PATH, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1)
        load.cache_clear()
    return data


if __name__ == "__main__":  # pragma: no cover - a build tool
    import sys
    result = build(write="--write" in sys.argv)
    print(f"fields: {len(result['fields'])}  rows: {result['n']}")
    if "--write" in sys.argv:
        print(f"written: {REFERENCE_PATH} "
              f"({REFERENCE_PATH.stat().st_size / 1024:.1f} KB)")
