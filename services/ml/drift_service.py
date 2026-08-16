"""Are the models being asked about inputs they were never fitted on?

THE GAP THIS FILLS
------------------
The classifier and the regressor are pickles fitted once, on one
distribution, and then asked about whatever a live user types for as long
as the app runs. Nothing compared the two. A model can be 97% accurate on
its own held-out split and still be answering confidently about people who
look nothing like anyone it ever saw, and every number in the UI would
look exactly as sure as it does now.

TWO QUESTIONS, TWO METRICS, AND WHY NOT ONE
-------------------------------------------
The obvious implementation is Population Stability Index per user, and it
is wrong. PSI compares two DISTRIBUTIONS. One person's thirty days are
inherently far more concentrated than 93,000 rows drawn from thousands of
different people - a perfectly ordinary user who sleeps 6.5 to 7.5 hours
piles into two or three reference deciles and scores PSI above the
"significant shift" threshold for that reason alone. Measured on a
simulated user drawn from near the training medians, that is exactly what
happened: every feature came back "significant". A metric that fires for
everybody is not a warning, it is a broken gauge.

So the two questions are separated and each gets the metric that actually
answers it:

  * PER USER - "do MY days fall where this model has seen data?" That is
    not a distribution comparison, it is a coverage question, and the
    honest measure is the share of days landing in the tails of the
    training distribution (outside p5-p95). A user whose every day sits
    beyond the 95th percentile of screen time is being extrapolated
    about, and the number says so; a user with narrow but ordinary habits
    scores zero, which is the correct answer.

  * DEPLOYMENT-WIDE - "has the population using this app drifted away
    from the training population?" THAT is a distribution comparison and
    PSI is the right tool, computed over every stored check-in pooled
    together. Pooled bucket proportions describe nobody in particular, so
    this reveals nothing about any individual - which is what makes it
    safe to show to a signed-in user at all.

HONESTY
-------
Both numbers are noisy on small samples and neither is reported below its
own floor. Between MIN_DAYS and RELIABLE_DAYS the result comes back with
`reliable=False` so the caller can show it quietly rather than draw a
conclusion over eleven days.

And the reference itself is synthetic. This says whether live inputs
resemble the data the models were fitted on. It does not say the models
are right.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

from core import paths

logger = logging.getLogger(__name__)

REFERENCE_PATH = paths.artifact("cohort_reference.json")

# --- per-user coverage ------------------------------------------------
# Which reference percentiles count as "the tails". p5/p95 leaves 10% of
# the training population outside by definition, so that 10% is the
# baseline a user is compared against, not zero.
TAIL_LOW_PERCENTILE = 5
TAIL_HIGH_PERCENTILE = 95
EXPECTED_TAIL_RATE = (TAIL_LOW_PERCENTILE + (100 - TAIL_HIGH_PERCENTILE)) / 100.0  # 0.10

# How far above that baseline is worth naming. A user landing in the
# tails a third of the time is being extrapolated about; half the time
# and the models have very little to go on.
MODERATE_TAIL_RATE = 0.33
SIGNIFICANT_TAIL_RATE = 0.50

# --- deployment-wide PSI ----------------------------------------------
BUCKETS = 10
MODERATE_PSI = 0.10      # the conventional bands; this module does not
SIGNIFICANT_PSI = 0.25   # invent them
EPSILON = 1e-4           # a bucket nobody lands in would make ln(0)

# Floors. Below the first there is nothing to say; below the second there
# is something to say, said quietly.
MIN_DAYS = 8
RELIABLE_DAYS = 20
# PSI over ten buckets needs considerably more than one person's month
# before it means anything.
MIN_POOLED_ROWS = 200


@dataclass(slots=True)
class FeatureCoverage:
    """One feature, for one user."""

    field_name: str
    days: int
    tail_rate: float               # share of days outside the reference p5-p95
    band: str                      # covered | thin | extrapolating
    user_median: Optional[float]
    reference_median: Optional[float]
    reference_low: Optional[float]
    reference_high: Optional[float]

    @property
    def outside(self) -> bool:
        return self.band != "covered"


@dataclass(slots=True)
class FeaturePSI:
    """One feature, across the whole deployment."""

    field_name: str
    psi: float
    band: str                      # stable | moderate | significant
    rows: int


@dataclass(slots=True)
class DriftReport:
    available: bool
    reason: str                    # ok | not_enough_days | no_reference | no_usable_fields
    days: int = 0
    reliable: bool = False
    features: list[FeatureCoverage] = field(default_factory=list)
    # The furthest-out feature. A list of nine covered features and one
    # that is being extrapolated should not read as "mostly fine".
    worst: Optional[FeatureCoverage] = None
    overall_band: str = "covered"


@dataclass(slots=True)
class PopulationReport:
    available: bool
    reason: str                    # ok | not_enough_rows | no_reference
    rows: int = 0
    features: list[FeaturePSI] = field(default_factory=list)
    worst: Optional[FeaturePSI] = None
    overall_band: str = "stable"


# ------------------------------------------------------------- reference

_reference: Optional[dict[str, Any]] = None
_reference_loaded = False


def _load_reference() -> Optional[dict[str, Any]]:
    global _reference, _reference_loaded
    if _reference_loaded:
        return _reference
    _reference_loaded = True
    try:
        if REFERENCE_PATH.exists():
            _reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        logger.exception("Could not read the cohort reference - drift is unavailable.")
        _reference = None
    return _reference


def reset_cache() -> None:
    """Tests that install their own reference file."""
    global _reference, _reference_loaded
    _reference = None
    _reference_loaded = False


# ---------------------------------------------------------------- maths

def _grid_at(grid: Sequence[float], percentile: float) -> Optional[float]:
    """The reference value at a percentile, off the 101-point grid."""
    if not grid:
        return None
    index = int(round((len(grid) - 1) * (percentile / 100.0)))
    return float(grid[max(0, min(len(grid) - 1, index))])


def _edges(grid: Sequence[float]) -> list[float]:
    """Nine interior decile cut points from the 101-point quantile grid.

    The 0th and 100th points are the observed min and max and are
    deliberately not edges: a live value beyond either belongs in the
    outermost bucket, which is the signal being looked for.
    """
    if len(grid) < BUCKETS + 1:
        return []
    step = (len(grid) - 1) / BUCKETS
    return [float(grid[int(round(step * i))]) for i in range(1, BUCKETS)]


def _bucket(value: float, edges: Sequence[float]) -> int:
    for index, edge in enumerate(edges):
        if value < edge:
            return index
    return len(edges)


def _clean(values: Iterable[Any]) -> list[float]:
    out: list[float] = []
    for value in values or ():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if math.isfinite(number):
            out.append(number)
    return out


def _median(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def psi(values: Sequence[float], grid: Sequence[float]) -> Optional[float]:
    """Population Stability Index against a reference quantile grid.

    The reference buckets are its own deciles, so the expected proportion
    is exactly 0.1 in each by construction and no reference histogram has
    to be stored. Only meaningful for a POPULATION - see the module
    docstring for why this is not applied to one person's days.
    """
    edges = _edges(grid)
    if not edges or not values:
        return None

    counts = [0] * BUCKETS
    for value in values:
        counts[_bucket(value, edges)] += 1

    total = float(len(values))
    expected = 1.0 / BUCKETS
    score = 0.0
    for count in counts:
        actual = max(count / total, EPSILON)
        score += (actual - expected) * math.log(actual / expected)
    return round(score, 4)


def _psi_band(score: float) -> str:
    if score >= SIGNIFICANT_PSI:
        return "significant"
    if score >= MODERATE_PSI:
        return "moderate"
    return "stable"


def _coverage_band(rate: float) -> str:
    if rate >= SIGNIFICANT_TAIL_RATE:
        return "extrapolating"
    if rate >= MODERATE_TAIL_RATE:
        return "thin"
    return "covered"


_BAND_ORDER = {"covered": 0, "thin": 1, "extrapolating": 2}


# -------------------------------------------------------------- service

class DriftService:
    """Live inputs against the distribution the models were fitted on."""

    def __init__(self, reference: Optional[dict[str, Any]] = None) -> None:
        self._reference = reference if reference is not None else _load_reference()

    @property
    def reference_source(self) -> str:
        """Named rather than implied - the rule the cohort panel follows."""
        if not self._reference:
            return "none"
        return str(self._reference.get("source") or "unknown")

    @property
    def reference_rows(self) -> int:
        return int((self._reference or {}).get("n") or 0)

    def _fields(self) -> dict[str, Any]:
        return (self._reference or {}).get("fields") or {}

    # ------------------------------------------------------- per user
    def report(self, entries: Sequence[Mapping[str, Any]]) -> DriftReport:
        """How much of this user's own data sits where the model has none."""
        if not self._fields():
            return DriftReport(available=False, reason="no_reference")

        rows = [e for e in (entries or ()) if e and not e.get("excluded")]
        if len(rows) < MIN_DAYS:
            return DriftReport(available=False, reason="not_enough_days", days=len(rows))

        results: list[FeatureCoverage] = []
        for name, stats in self._fields().items():
            grid = (stats or {}).get("grid") or []
            values = _clean(row.get(name) for row in rows)
            # A field the user's entries never carried is absent, not
            # zero. Scoring it would report a problem in a column that is
            # simply not being logged.
            if len(values) < MIN_DAYS or not grid:
                continue
            low = _grid_at(grid, TAIL_LOW_PERCENTILE)
            high = _grid_at(grid, TAIL_HIGH_PERCENTILE)
            if low is None or high is None:
                continue

            outside = sum(1 for value in values if value < low or value > high)
            rate = outside / len(values)
            results.append(FeatureCoverage(
                field_name=name,
                days=len(values),
                tail_rate=round(rate, 4),
                band=_coverage_band(rate),
                user_median=_median(values),
                reference_median=(stats or {}).get("median"),
                reference_low=low,
                reference_high=high,
            ))

        if not results:
            return DriftReport(available=False, reason="no_usable_fields", days=len(rows))

        results.sort(key=lambda item: item.tail_rate, reverse=True)
        worst = results[0]
        return DriftReport(
            available=True,
            reason="ok",
            days=len(rows),
            reliable=len(rows) >= RELIABLE_DAYS,
            features=results,
            worst=worst,
            overall_band=worst.band,
        )

    # ---------------------------------------------------- whole deployment
    def population(self, entries: Sequence[Mapping[str, Any]]) -> PopulationReport:
        """PSI over every stored check-in, pooled.

        `entries` is expected to be every account's rows together. What
        comes back is ten bucket proportions per feature, which describe
        nobody in particular - that is what makes it safe to return to a
        signed-in user, and it is the only form in which this number is
        statistically meaningful.
        """
        if not self._fields():
            return PopulationReport(available=False, reason="no_reference")

        rows = [e for e in (entries or ()) if e and not e.get("excluded")]
        if len(rows) < MIN_POOLED_ROWS:
            return PopulationReport(
                available=False, reason="not_enough_rows", rows=len(rows),
            )

        results: list[FeaturePSI] = []
        for name, stats in self._fields().items():
            values = _clean(row.get(name) for row in rows)
            if len(values) < MIN_POOLED_ROWS:
                continue
            score = psi(values, (stats or {}).get("grid") or [])
            if score is None:
                continue
            results.append(FeaturePSI(
                field_name=name, psi=score, band=_psi_band(score), rows=len(values),
            ))

        if not results:
            return PopulationReport(available=False, reason="no_reference", rows=len(rows))

        results.sort(key=lambda item: item.psi, reverse=True)
        worst = results[0]
        return PopulationReport(
            available=True, reason="ok", rows=len(rows),
            features=results, worst=worst, overall_band=worst.band,
        )
