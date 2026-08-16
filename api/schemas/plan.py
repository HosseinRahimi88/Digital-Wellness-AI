"""api/schemas/plan.py"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanGenerateRequest(BaseModel):
    health_class: str | None = Field(default=None, description="e.g. the 'prediction' field from a real /predict response.")
    wellness_score: float | None = Field(default=None, description="e.g. the 'regression_score' field from a real /predict response.")
    persona: str | None = None
    user_data: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    regenerate: bool = Field(
        default=False,
        description=(
            "Replace this week's stored plan instead of returning it. "
            "Opening the page must never do this: the plan is frozen for "
            "the ISO week so that a second check-in cannot silently swap "
            "the tasks out from under the user's checkmarks. Regenerating "
            "clears that week's checkmarks, because the tasks they were "
            "ticked against no longer exist."
        ),
    )


class PlanTaskResponse(BaseModel):
    task_index: int
    text: str
    completed: bool
    # The same exercise in all four languages, plus what it was built
    # from. `text` above stays English so nothing that already reads it
    # breaks; a four-language client reads `text_i18n` and never sees
    # English unless it asked for it.
    text_i18n: dict[str, str] = Field(default_factory=dict)
    theme: str = ""
    slot: str = ""
    tier: str = ""
    field_name: str = ""
    current: float | None = None
    target: float | None = None


class PlanDayResponse(BaseModel):
    day_number: int
    day_label: str
    theme: str
    icon: str
    tip: str
    tier_label: str = ""
    tasks: list[PlanTaskResponse]
    # A day is open only once the day before it is fully done. This is
    # what makes the week a sequence rather than a menu - and it is the
    # only thing that makes "you missed a day" mean anything.
    locked: bool = False
    # Why it is locked, so the card can say the true thing instead of
    # one guess: "sequence" - the day before is unfinished; "calendar" -
    # the day before IS finished but this day has not arrived yet.
    # Null when the day is open. Telling somebody to "finish day 1" when
    # they already have is the confusing half of a single-reason lock.
    lock_reason: str | None = None
    # The calendar date this plan day falls on (day 1 = the day the plan
    # was generated). Null for plans stored before that was recorded.
    day_date: str | None = None
    # {part: {lang: text}} for day_label, theme, tip and tier_label.
    # The exercises were already translated; everything wrapping them
    # was not, so a Persian reader got translated tasks under an English
    # heading. The flat fields above stay English for older clients.
    text_i18n: dict[str, dict[str, str]] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    week_key: str
    # The score range this week's plan is aimed at, built from the days
    # already logged this week rather than from one prediction. Null
    # until there is something to average. A day outside it is what the
    # client offers to mark as an exception.
    band_low: float | None = None
    band_high: float | None = None
    # How the band's width was arrived at. "model" means
    # services/ml/band_model_service predicted a half-width from this
    # user's own week; "constant" means it fell back to
    # plan_lock_service.BAND_HALF_WIDTH. Reported rather than inferred
    # so a client can say which one a reader is looking at - the same
    # reason the cohort panel names its source instead of presenting a
    # shipped reference grid as if it were the full training set.
    band_half_width: float | None = None
    band_source: str | None = None
    # The date this week's plan was actually built on (YYYY-MM-DD).
    # Exposed because updating a check-in has to rebuild the plan when
    # the plan was built FROM that day, and leave it alone otherwise -
    # a plan set on Monday should not be torn up because Thursday's
    # numbers were corrected. Null for a plan stored before this field
    # existed.
    generated_on: str | None = None
    # The highest day the user may work on right now. Day 1 is always
    # open; day N+1 opens once day N is fully ticked.
    unlocked_through: int = 1
    # Days of this week's plan whose date has passed with the day left
    # undone, and what that cost. `open_violations` is the count shown
    # under the Hall of Fame; each new badge clears one, and while any
    # remain a newly earned badge is spent clearing instead of
    # registering.
    missed_days: int = 0
    open_violations: int = 0
    revoked_badges: list[str] = Field(default_factory=list)
    intro: str
    focus_areas: list[str]
    days: list[PlanDayResponse]
    # {part: {lang: text}} - currently just "intro".
    text_i18n: dict[str, dict[str, str]] = Field(default_factory=dict)
    # One {lang: name} map per focus area, same order as `focus_areas`.
    focus_areas_i18n: list[dict[str, str]] = Field(default_factory=list)


class PlanDayStatusResponse(BaseModel):
    """Where today sits against the week's band, and whether the app
    still needs to ask about it."""

    date: str
    week_key: str
    # Today's position among this week's logged days, 1-based. The
    # question is only asked from 2 onward: on the first day of a week
    # there is nothing to be outside of.
    day_number: int
    score: float | None = None
    band_low: float | None = None
    band_high: float | None = None
    # How the band's width was arrived at. "model" means
    # services/ml/band_model_service predicted a half-width from this
    # user's own week; "constant" means it fell back to
    # plan_lock_service.BAND_HALF_WIDTH. Reported rather than inferred
    # so a client can say which one a reader is looking at - the same
    # reason the cohort panel names its source instead of presenting a
    # shipped reference grid as if it were the full training set.
    band_half_width: float | None = None
    band_source: str | None = None
    outside_band: bool = False
    # True only when the day is outside the band, is not the week's
    # first day, and has not already been answered. A prompt that
    # reappears after it has been answered is nagging, not asking.
    needs_decision: bool = False
    # "exception" | "counted" | null
    decision: str | None = None
    # Every day this week the user called an exception, for the
    # dashboard - a week with three of them is itself worth seeing.
    exception_days: list[str] = Field(default_factory=list)
    # How much of a normal day an exception day counts for in the band.
    # Sent rather than hardcoded in the UI so the explanation the user
    # reads cannot drift from the arithmetic actually applied.
    exception_weight: float = 0.25


class PlanDayDecisionRequest(BaseModel):
    decision: str = Field(
        ...,
        description=(
            "'exception' - an unusual day; the plan is left alone and "
            "the day counts for less in the week's band, but stays in "
            "history and on the dashboard. 'counted' - a real change; "
            "the REST of the week's plan is rebuilt against the new "
            "band, while days already lived through keep their tasks "
            "and their checkmarks."
        ),
    )
    date: str | None = Field(
        default=None,
        description="The day being decided (YYYY-MM-DD). Defaults to today.",
    )
    user_data: dict[str, float | int | str | bool | None] = Field(
        default_factory=dict,
        description=(
            "The check-in behind that day, used to rebuild the rest of "
            "the week when the decision is 'counted'. Ignored for "
            "'exception', which changes no plan."
        ),
    )


class SignalTrackEntry(BaseModel):
    """One signal on either track, with the user's own number on it."""

    field: str
    theme: str
    # {lang: name} for `theme`. No human-readable string is ever the
    # only copy in a response here - the app ships in four languages.
    theme_i18n: dict[str, str] = Field(default_factory=dict)
    icon: str = ""
    current: float
    target: float
    lower_is_better: bool = False
    # This user's own median for the field, when there is enough history
    # to have one. Null is honest: it means "not enough days yet", not
    # "no drift".
    baseline: float | None = None
    # On `strengthen` only: how far off it is, 0-1, the worse of the
    # absolute and personal readings - the same arithmetic the 7-day
    # plan ranks by, so the two can never disagree about what is wrong.
    severity: float | None = None
    # On `maintain` only: how far the right side of the target it sits,
    # as a fraction of the target.
    margin: float | None = None


class SignalTracksResponse(BaseModel):
    """The two halves of a week's plan.

    A plan that only names what is wrong reads as a list of faults and
    throws away the more useful half of the picture. `maintain` is what
    the week is protecting; `strengthen` is what it is working on.
    """

    strengthen: list[SignalTrackEntry] = Field(default_factory=list)
    maintain: list[SignalTrackEntry] = Field(default_factory=list)
    # The check-in these were read from, so a client can say how fresh
    # they are rather than implying they are live.
    based_on_date: str | None = None
    band_low: float | None = None
    band_high: float | None = None
    # How the band's width was arrived at. "model" means
    # services/ml/band_model_service predicted a half-width from this
    # user's own week; "constant" means it fell back to
    # plan_lock_service.BAND_HALF_WIDTH. Reported rather than inferred
    # so a client can say which one a reader is looking at - the same
    # reason the cohort panel names its source instead of presenting a
    # shipped reference grid as if it were the full training set.
    band_half_width: float | None = None
    band_source: str | None = None


class PlanTaskUpdateRequest(BaseModel):
    day_number: int
    task_index: int
    completed: bool


class PlanWeekSummary(BaseModel):
    """One entry in the week menu."""

    week_key: str
    # 0 for the user's first stored week, counting up. The label the menu
    # shows ("Week 0", "Week 1", ...) rather than the ISO key, which
    # means nothing to a reader.
    index: int
    day_count: int
    completed_tasks: int
    total_tasks: int
    is_current: bool


class PlanWeeksResponse(BaseModel):
    weeks: list[PlanWeekSummary]
    current_week_key: str
