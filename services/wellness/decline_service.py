"""
Three days down in a row - noticing it, and asking about it
============================================================

The app was good at telling somebody where they stood and silent about
where they were heading. A score that falls three days running is the
clearest early signal this data produces, and nothing acted on it: the
dashboard showed three slightly shorter bars and said nothing.

What this does
--------------
Reads the user's own recorded days, newest last, and reports a run of
consecutive falls. Three is the threshold, because two is a normal
weekend and one is a Tuesday.

    run   = how many consecutive days each fell against the one before
    drop  = first day of the run minus the last day of it
    penalty = 2 + 3 * clamp((drop - MIN_DROP) / (FULL_DROP - MIN_DROP), 0, 1)

so the penalty runs 2 to 5 points, 2 for a slide that is barely outside
the noise and 5 for a collapse. The bounds are the ones asked for; the
shape between them is linear in the size of the fall, which is the only
part the data can actually justify.

MIN_DROP is 3 points, because the model's own day-to-day noise on
identical habits is larger than one point (measured: fifteen samples at
a pinned input ran 78.2-86.5 near the middle of the scale), and calling
a two-point wobble a decline would be reading noise back to the user as
a fact about their week.

What the penalty is - and is not
---------------------------------
It is NOT subtracted from the wellness score. That number is the
model's reading of the habits submitted, and editing it would make the
app's headline figure something other than what the model said - the
same rule the missed-day ledger already follows (services/
day_status_service.py: reported, never subtracted).

It is an accountability figure, recorded in the same ledger as missed
plan days and shown in the same place. The user is told which it is.

Why it asks rather than just recording
---------------------------------------
Three days down has an explanation more often than not - an exam week,
illness, travel, a genuinely bad patch - and the app already has a place
for "that day was not typical" (the exception-day flag). Asking converts
a silent penalty into a conversation, and the answer is kept so the
coach and the weekly plan have something better than a number to work
from. Answering also halves the penalty: naming what happened is the
behaviour this is trying to encourage, not a way to escape a score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# Three, not two. Two consecutive falls is an ordinary weekend.
RUN_THRESHOLD = 3
# Below this the fall is inside the model's own noise on identical
# inputs, so it is not reported as a decline at all.
MIN_DROP = 3.0
# The fall that earns the full penalty.
FULL_DROP = 18.0
PENALTY_MIN = 2.0
PENALTY_MAX = 5.0
# What naming the reason is worth. Not a full waiver - the days still
# happened - but the app would rather know than not.
ACKNOWLEDGED_RELIEF = 0.5


@dataclass(slots=True)
class DeclineReport:
    """A run of consecutive falls, or an explicit "no".

    `days` counts the falls, so a run of 3 spans 4 recorded days.
    """

    declining: bool
    days: int = 0
    drop: float = 0.0
    penalty: float = 0.0
    dates: list[str] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    # Set once the user has answered for this particular run, so the
    # question is asked once rather than on every dashboard load.
    acknowledged: bool = False
    acknowledged_reason: Optional[str] = None
    # Stable id for this run - the last date in it. Answering is
    # recorded against this, so a NEW run asks again.
    run_id: Optional[str] = None


def _usable(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recorded days with a score, oldest first, excluded days dropped.

    An excluded day is one the user said was not their data; letting it
    break or extend a run would be reading it after all.
    """
    return sorted(
        (
            e for e in (entries or [])
            if e.get("health_score") is not None and not e.get("excluded")
        ),
        key=lambda e: e.get("date") or "",
    )


def penalty_for(drop: float) -> float:
    """2 to 5 points, linear in the size of the fall. See the module doc."""
    if drop <= 0:
        return 0.0
    span = max(FULL_DROP - MIN_DROP, 1e-9)
    t = max(0.0, min(1.0, (drop - MIN_DROP) / span))
    return round(PENALTY_MIN + (PENALTY_MAX - PENALTY_MIN) * t, 1)


def detect(entries: list[dict[str, Any]]) -> DeclineReport:
    """The current run of falls, if there is one worth reporting."""
    days = _usable(entries)
    if len(days) < RUN_THRESHOLD + 1:
        return DeclineReport(declining=False)

    # Walk backwards from the most recent day while each day is lower
    # than the one before it.
    run = 0
    i = len(days) - 1
    while i > 0 and float(days[i]["health_score"]) < float(days[i - 1]["health_score"]):
        run += 1
        i -= 1

    if run < RUN_THRESHOLD:
        return DeclineReport(declining=False)

    span = days[-(run + 1):]
    drop = float(span[0]["health_score"]) - float(span[-1]["health_score"])
    if drop < MIN_DROP:
        # Three falls of a tenth of a point each. Real arithmetic, not a
        # real decline.
        return DeclineReport(declining=False)

    return DeclineReport(
        declining=True,
        days=run,
        drop=round(drop, 1),
        penalty=penalty_for(drop),
        dates=[d.get("date") or "" for d in span],
        scores=[round(float(d["health_score"]), 1) for d in span],
        run_id=span[-1].get("date") or "",
    )
