"""
Personal model
---------------
A model of ONE person, fitted on their own logged days.

Everything else in this app is the shipped model's opinion: it was
fitted on 93,000 other rows and it answers "what does this day look
like". This answers a different question - "what moves YOUR score" -
and it can only be answered with the days that person actually logged.

What it is
-----------
Ridge regression of the user's own health score on their own tracked
signals, standardised, with the coefficients reported in points of
score per standard deviation of that signal. Ridge rather than plain
least squares because a person's signals are correlated (screen time
and social minutes move together) and there are few rows; the penalty
is what stops one of a correlated pair getting a huge positive
coefficient and the other a huge negative one.

Why the numbers can be trusted, or not
---------------------------------------
Two R² values are reported and both are shown:

  * in-sample R² - how well the fit describes the days it was fitted
    on. With ten days and four signals this is optimistic by
    construction, and quoting it alone would be the single most
    misleading number this app could print.
  * leave-one-out R² - refit without each day and predicted for it.
    For ridge this is exact and closed-form via the hat matrix
    (residual_i / (1 - h_ii)), so it costs one extra matrix product
    rather than n refits.

If the leave-one-out R² is poor, the honest reading is "your days do
not yet explain your score", and that is what the caller is told - not
a driver list dressed up as a finding.

Refusals
---------
Below MIN_DAYS days, or when a signal never varies, nothing is
returned but the reason. A personal model fitted on four days is a
line through noise, and this module will not draw one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import numpy as np

# Under this, no model at all. Eight is not a statistical threshold so
# much as a floor of decency: with fewer days than signals-plus-a-few
# every coefficient is an artefact of which days happened to be logged.
MIN_DAYS = 8

# How many signals are fitted. Chosen by variance within THIS user's own
# days, so a person whose sleep never changes is not told about sleep.
MAX_SIGNALS = 5

# Ridge penalty, on standardised inputs. Deliberately firm: with ten
# rows the aim is a stable ordering of what matters, not the lowest
# possible training error.
RIDGE_LAMBDA = 1.0

# A driver has to be worth a sentence. Under this many points per
# standard deviation it is noise wearing a field name.
MIN_POINTS_PER_SD = 0.35

# The signals a personal model may consider. Deliberately the ones a
# person can act on - "age" and "gender" cannot be changed tonight and
# do not vary within one person's history anyway.
CANDIDATE_FIELDS = (
    "total_screen_min",
    "social_min",
    "gaming_min",
    "video_min",
    "work_study_min",
    "night_screen_min",
    "pre_sleep_screen_min",
    "notifications_per_day",
    "pickups_per_day",
    "app_opens_per_day",
    "sleep_hours",
    "sleep_quality_1_10",
    "stress_0_10",
    "mood_1_10",
    "focus_0_100",
    "productivity_0_100",
    "physical_activity_min_per_day",
    "outdoor_time_min",
    "social_offline_min",
)


@dataclass(slots=True)
class Driver:
    field: str
    points_per_sd: float     # points of score per 1 SD of this signal
    direction: str           # "up" | "down" - which way it pushes
    user_mean: float
    user_sd: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "points_per_sd": self.points_per_sd,
            "direction": self.direction,
            "user_mean": self.user_mean,
            "user_sd": self.user_sd,
        }


@dataclass(slots=True)
class PersonalModel:
    available: bool = False
    reason: str = "not_enough_days"   # a key the client translates
    days: int = 0
    signals: int = 0
    r2: Optional[float] = None        # in-sample
    r2_loo: Optional[float] = None    # leave-one-out
    score_mean: Optional[float] = None
    score_sd: Optional[float] = None
    trustworthy: bool = False
    drivers: list[Driver] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "reason": self.reason,
            "days": self.days,
            "signals": self.signals,
            "r2": self.r2,
            "r2_loo": self.r2_loo,
            "score_mean": self.score_mean,
            "score_sd": self.score_sd,
            "trustworthy": self.trustworthy,
            "drivers": [d.to_dict() for d in self.drivers],
        }


def _rows(entries: Iterable[dict]) -> list[dict]:
    """History rows that carry both a score and their own answers."""
    out = []
    for entry in entries or []:
        score = entry.get("health_score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            continue
        out.append(entry)
    return out


def fit(entries: Iterable[dict]) -> PersonalModel:
    """Fit this person's own model, or say why not."""
    rows = _rows(entries)
    if len(rows) < MIN_DAYS:
        return PersonalModel(days=len(rows), reason="not_enough_days")

    y = np.array([float(r["health_score"]) for r in rows], dtype=float)
    score_sd = float(y.std(ddof=0))
    if score_sd < 1e-6:
        # Every day scored the same. Nothing to explain, and dividing by
        # this would manufacture infinite drivers.
        return PersonalModel(
            days=len(rows), reason="score_never_moves",
            score_mean=round(float(y.mean()), 1), score_sd=0.0,
        )

    # Which of this person's signals actually move. A column that is
    # constant carries no information and would only add a coefficient
    # of zero with a confident-looking name attached.
    usable: list[tuple[str, np.ndarray]] = []
    for name in CANDIDATE_FIELDS:
        values = []
        for row in rows:
            value = row.get(name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                values = []
                break
            values.append(float(value))
        if not values:
            continue
        column = np.array(values, dtype=float)
        if column.std(ddof=0) < 1e-9:
            continue
        usable.append((name, column))

    if not usable:
        return PersonalModel(
            days=len(rows), reason="signals_never_move",
            score_mean=round(float(y.mean()), 1), score_sd=round(score_sd, 2),
        )

    # The most variable signals first: within one person, a signal that
    # barely moves cannot explain a score that does.
    usable.sort(key=lambda item: float(item[1].std(ddof=0) / (abs(item[1].mean()) + 1e-9)), reverse=True)
    chosen = usable[:MAX_SIGNALS]

    names = [name for name, _ in chosen]
    matrix = np.column_stack([column for _, column in chosen])
    means = matrix.mean(axis=0)
    sds = matrix.std(axis=0, ddof=0)
    sds[sds < 1e-9] = 1.0
    x = (matrix - means) / sds
    y_centred = y - y.mean()

    # Ridge, closed form on standardised, centred data.
    gram = x.T @ x + RIDGE_LAMBDA * np.eye(x.shape[1])
    try:
        beta = np.linalg.solve(gram, x.T @ y_centred)
    except np.linalg.LinAlgError:  # pragma: no cover - singular even with the penalty
        return PersonalModel(days=len(rows), reason="fit_failed")

    fitted = x @ beta
    residuals = y_centred - fitted
    ss_total = float((y_centred ** 2).sum())
    r2 = 1.0 - float((residuals ** 2).sum()) / ss_total if ss_total > 0 else None

    # Leave-one-out, exactly, through the ridge hat matrix.
    hat = x @ np.linalg.solve(gram, x.T)
    leverage = np.clip(np.diag(hat), 0.0, 1.0 - 1e-9)
    loo_residuals = residuals / (1.0 - leverage)
    r2_loo = 1.0 - float((loo_residuals ** 2).sum()) / ss_total if ss_total > 0 else None

    drivers = []
    for name, coefficient, mean, sd in zip(names, beta, means, sds):
        points = float(coefficient)
        if abs(points) < MIN_POINTS_PER_SD:
            continue
        drivers.append(Driver(
            field=name,
            points_per_sd=round(abs(points), 2),
            direction="up" if points > 0 else "down",
            user_mean=round(float(mean), 2),
            user_sd=round(float(sd), 2),
        ))
    drivers.sort(key=lambda d: d.points_per_sd, reverse=True)

    if not drivers:
        return PersonalModel(
            days=len(rows), signals=len(names), reason="no_clear_driver",
            r2=round(r2, 3) if r2 is not None else None,
            r2_loo=round(r2_loo, 3) if r2_loo is not None else None,
            score_mean=round(float(y.mean()), 1), score_sd=round(score_sd, 2),
        )

    # "Trustworthy" is a claim about the leave-one-out number, not the
    # in-sample one, and it is stated rather than implied so the UI can
    # lead with the caveat when it is false.
    trustworthy = bool(r2_loo is not None and r2_loo >= 0.25 and len(rows) >= 12)

    return PersonalModel(
        available=True, reason="ok", days=len(rows), signals=len(names),
        r2=round(r2, 3) if r2 is not None else None,
        r2_loo=round(r2_loo, 3) if r2_loo is not None else None,
        score_mean=round(float(y.mean()), 1), score_sd=round(score_sd, 2),
        trustworthy=trustworthy, drivers=drivers,
    )
