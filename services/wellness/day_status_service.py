"""
Day Status Service
------------------
What a single day is worth, once you look at BOTH halves of it.

The dashboard used to colour a day by one thing: was there a check-in.
That misses the more interesting failure. Logging a day and then not
doing any of the plan is not the same as never opening the app, and
neither is the same as doing the work but forgetting to log it. Three
different situations that all used to look identical.

So a day is scored on two independent facts - was it logged, and was
its plan task done - which gives four states:

    logged   done    colour   penalty   meaning
    ------   -----   ------   -------   ----------------------------
    yes      yes     green     0.0      the ordinary day
    yes      no      orange   -0.5      showed up, did not do the work
    no       yes     grey     -0.5      did the work, did not log it
    no       no      red      -1.0      neither

The two -0.5 cases are deliberately equal. One is not worse than the
other: a day the user lived but did not record costs the app its data,
and a day recorded but not acted on costs the user their plan. Only
missing both is a full point, because only then is there nothing at all
to build on.

Penalties are reported, never applied to the wellness score. The score
is the model's output about habits; this is a record of engagement with
the app, and quietly mixing the two would make the number mean two
things at once. The Hall of Fame's violation ledger is where a missed
day actually costs something (see services/wellness/violation_service.py).

Today is never penalised. It is not over.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls
from datetime import timedelta
from typing import Any, Iterable, Optional

# The four states, as stable ids. The client maps these to colours and
# to translated labels; no human-readable string is produced here, for
# the same reason the badge service produces none - the app ships in
# four languages.
GREEN = "green"
ORANGE = "orange"
GREY = "grey"
RED = "red"

PENALTY = {GREEN: 0.0, ORANGE: -0.5, GREY: -0.5, RED: -1.0}


@dataclass(slots=True)
class DayStatus:
    date: str
    logged: bool
    task_done: bool
    status: str
    penalty: float
    # None for a day with no check-in - the honest value, and what stops
    # the dashboard drawing a zero-height bar as though the day scored 0.
    score: Optional[float] = None
    # True for today, which is reported but never penalised.
    is_today: bool = False


def status_for(logged: bool, task_done: bool) -> str:
    if logged and task_done:
        return GREEN
    if logged and not task_done:
        return ORANGE
    if not logged and task_done:
        return GREY
    return RED


def build_day_statuses(
    history: Iterable[dict[str, Any]],
    done_dates: Iterable[str],
    start: date_cls,
    end: date_cls,
    today: Optional[date_cls] = None,
) -> list[DayStatus]:
    """One status per calendar day from `start` to `end` inclusive.

    `done_dates` is the set of dates whose plan task was completed -
    resolved by the caller, because only it knows how plan days map onto
    calendar dates (services/wellness/violation_service.py::plan_day_date).

    Days before the user's first check-in are not in the range the
    caller passes; a user cannot miss a day that predates their account,
    and colouring those red would open the app on a wall of failure.
    """
    today = today or date_cls.today()
    by_date: dict[str, dict[str, Any]] = {}
    for row in history or []:
        key = (row or {}).get("date")
        if key:
            by_date[key] = row

    done = {d for d in done_dates if d}

    out: list[DayStatus] = []
    day = start
    while day <= end:
        key = day.isoformat()
        row = by_date.get(key)
        logged = row is not None
        task_done = key in done
        is_today = day == today
        state = status_for(logged, task_done)
        score = row.get("health_score") if row else None
        out.append(DayStatus(
            date=key,
            logged=logged,
            task_done=task_done,
            status=state,
            # Today is still running, so it is shown in its current
            # state and costs nothing. Penalising someone at breakfast
            # for a day they have not finished living would be wrong,
            # and it is the same rule the violation ledger already uses.
            penalty=0.0 if is_today else PENALTY.get(state, 0.0),
            score=float(score) if isinstance(score, (int, float)) and not isinstance(score, bool) else None,
            is_today=is_today,
        ))
        day += timedelta(days=1)
    return out


def total_penalty(statuses: Iterable[DayStatus]) -> float:
    return round(sum(s.penalty for s in statuses), 2)


def counts_by_status(statuses: Iterable[DayStatus]) -> dict[str, int]:
    out = {GREEN: 0, ORANGE: 0, GREY: 0, RED: 0}
    for s in statuses:
        if s.status in out:
            out[s.status] += 1
    return out
