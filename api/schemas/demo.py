"""api/schemas/demo.py"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from api.schemas.prediction import PredictResponse
from services.demo.demo_service import DEMO_LENGTHS, DEMO_PROFILES


class DemoPopulateResponse(BaseModel):
    days_created: int
    friend_connected: bool
    friends_connected: int = 0
    profile: str = "improving"
    final_result: PredictResponse
    final_user_data: dict


class DemoSessionRequest(BaseModel):
    """Which of the sixteen demos to build.

    Validated against the service's own tuples rather than a second copy
    of the list, so adding a profile in one place cannot leave the API
    rejecting it.
    """

    days: Literal[3, 7, 15, 23] = 23
    profile: Literal["healthy", "improving", "borderline", "at_risk"] = "improving"
    friends: int = Field(default=0, ge=0, le=10)
    with_violations: bool = Field(
        default=False,
        description=(
            "Build the lapsed version of this demo: real gaps in the "
            "history, plan days left undone, violations on the Hall of "
            "Fame and no badges. Doubles the catalogue from sixteen "
            "states to thirty-two, and is the only way to see the "
            "greyed/red days, the violation ledger and an empty badge "
            "wall - none of which a demo could reach while every demo "
            "user logged faithfully every day."
        ),
    )


class DemoSessionResponse(BaseModel):
    """A demo runs in its OWN account.

    The caller swaps to `access_token` for the duration and swaps back
    afterwards, which is what keeps a demo out of the user's real
    history. Before this, Demo Mode wrote its days into the signed-in
    account and there was no way to separate them again.
    """

    access_token: str
    token_type: str = "bearer"
    demo_user_id: str
    display_name: str
    days_created: int
    friends_connected: int
    # The final day's full result, and the inputs that produced it.
    #
    # Without these the demo was only half a demo: the days existed
    # server-side, but the Weekly Plan, the AI Coach and What-if all
    # build from the browser's own `dwai_last_result`, which a demo
    # session never set. So the pages that show the app's actual
    # thinking came up empty on a 23-day demo - the exact opposite of
    # what a demo is for. Seeded now, exactly as a real check-in does.
    final_result: PredictResponse | None = None
    final_inputs: dict[str, Any] = Field(default_factory=dict)
    # Set when the league came out smaller than requested, so a
    # presenter can see why rather than wondering.
    friend_error: str | None = None
    profile: str
    days: int
    with_violations: bool = False
    # How far through the weekly plan this demo user genuinely is, and
    # what their record looks like. A 23-day user is on day 23 with the
    # previous days actually ticked - not on day 1 of an untouched plan,
    # which is what a demo used to show however long its history was.
    plan_day: int = 1
    plan_days_completed: int = 0
    open_violations: int = 0
    missed_days: int = 0


class DemoCatalogueEntry(BaseModel):
    profile: str
    days: int


class DemoCatalogueResponse(BaseModel):
    """What the picker offers, straight from the service."""

    lengths: list[int] = list(DEMO_LENGTHS)
    profiles: list[str] = list(DEMO_PROFILES)
    max_friends: int = 10
