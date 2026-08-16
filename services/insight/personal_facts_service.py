"""
Personal facts
---------------
The things this app can say about ONE person that nothing else can,
computed from their own logged days.

Every fact is returned as a `kind` plus the numbers behind it - never
as a sentence. The four-language wording lives in the client
(frontend/assets/js/about/about-personal.js) alongside the rest of the About
page's copy; what crosses the wire is arithmetic.

The rule every fact obeys: it is either measured or it is absent. A
fact whose inputs are missing is not emitted with a hedge - it is not
emitted. Nothing here rounds a two-day average up into a "pattern".

Day-of-life facts need a birth date, which is optional
(services/identity/personal_service.py). Without one, the journey facts still
work, because they are about the days the person logged rather than the
days they have been alive.
"""

from __future__ import annotations

from datetime import date as date_cls, timedelta
from statistics import mean, pstdev
from typing import Any, Iterable, Optional

# A weekday claim needs at least this many of that weekday, or "your
# Tuesdays are hard" is a statement about one Tuesday.
MIN_PER_WEEKDAY = 2
# A pattern claim needs at least this many days overall.
MIN_DAYS_FOR_PATTERN = 5

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _scored(entries: Iterable[dict]) -> list[tuple[date_cls, float, dict]]:
    """(date, score, row) for every row that has both, oldest first."""
    out: list[tuple[date_cls, float, dict]] = []
    for row in entries or []:
        score = row.get("health_score")
        raw_date = row.get("date")
        if not raw_date or not isinstance(score, (int, float)) or isinstance(score, bool):
            continue
        try:
            day = date_cls.fromisoformat(str(raw_date))
        except ValueError:
            continue
        out.append((day, float(score), row))
    out.sort(key=lambda item: item[0])
    return out


def _longest_streak(days: list[date_cls]) -> tuple[int, Optional[date_cls]]:
    """The longest run of consecutive calendar days, and where it ended."""
    if not days:
        return 0, None
    best, run, best_end = 1, 1, days[0]
    for previous, current in zip(days, days[1:]):
        if (current - previous).days == 1:
            run += 1
            if run > best:
                best, best_end = run, current
        else:
            run = 1
    return best, best_end


def _birthday_in(born: date_cls, year: int) -> date_cls:
    """That birthday, in a given year, including 29 February.

    `date.replace(year=...)` raises for a leap-day birth date in a
    common year, which crashed the whole facts panel for anybody born
    on 29 February. The convention here is the common one: in a year
    that has no 29 February the birthday is counted on the 28th, so it
    still falls in the right month rather than sliding into March.
    """
    try:
        return born.replace(year=year)
    except ValueError:
        return born.replace(year=year, day=28)


def build(
    entries: Iterable[dict],
    birth_date: Optional[str] = None,
    today: Optional[date_cls] = None,
) -> list[dict[str, Any]]:
    """Every fact this person's history actually supports."""
    rows = _scored(entries)
    now = today or date_cls.today()
    facts: list[dict[str, Any]] = []
    if not rows:
        return facts

    days = [day for day, _, _ in rows]
    scores = [score for _, score, _ in rows]

    # --- the journey ------------------------------------------------
    facts.append({
        "kind": "first_day",
        "date": days[0].isoformat(),
        "days_since": (now - days[0]).days,
        "logged": len(rows),
    })

    best_index = max(range(len(scores)), key=lambda i: scores[i])
    facts.append({
        "kind": "personal_best",
        "score": round(scores[best_index], 1),
        "date": days[best_index].isoformat(),
        "days_ago": (now - days[best_index]).days,
    })

    streak, streak_end = _longest_streak(days)
    if streak >= 2:
        facts.append({
            "kind": "longest_streak",
            "days": streak,
            "ended": streak_end.isoformat() if streak_end else "",
            "ongoing": bool(streak_end and (now - streak_end).days <= 1),
        })

    # --- weekday shape ----------------------------------------------
    if len(rows) >= MIN_DAYS_FOR_PATTERN:
        buckets: dict[int, list[float]] = {}
        for day, score, _ in rows:
            buckets.setdefault(day.weekday(), []).append(score)
        eligible = {k: v for k, v in buckets.items() if len(v) >= MIN_PER_WEEKDAY}
        if len(eligible) >= 2:
            best_weekday = max(eligible, key=lambda k: mean(eligible[k]))
            worst_weekday = min(eligible, key=lambda k: mean(eligible[k]))
            if best_weekday != worst_weekday:
                facts.append({
                    "kind": "best_weekday",
                    "weekday": WEEKDAYS[best_weekday],
                    "average": round(mean(eligible[best_weekday]), 1),
                    "samples": len(eligible[best_weekday]),
                })
                facts.append({
                    "kind": "hardest_weekday",
                    "weekday": WEEKDAYS[worst_weekday],
                    "average": round(mean(eligible[worst_weekday]), 1),
                    "samples": len(eligible[worst_weekday]),
                    "gap": round(mean(eligible[best_weekday]) - mean(eligible[worst_weekday]), 1),
                })

    # --- movement ----------------------------------------------------
    if len(rows) >= 3:
        climbs = [
            (scores[i] - scores[i - 1], days[i])
            for i in range(1, len(scores))
        ]
        best_climb, climb_day = max(climbs, key=lambda item: item[0])
        if best_climb >= 3.0:
            facts.append({
                "kind": "biggest_climb",
                "points": round(best_climb, 1),
                "date": climb_day.isoformat(),
            })
        half = max(1, len(scores) // 2)
        early, late = mean(scores[:half]), mean(scores[-half:])
        facts.append({
            "kind": "trend_half",
            "early": round(early, 1),
            "late": round(late, 1),
            "change": round(late - early, 1),
            "days": len(scores),
        })
        if len(scores) >= MIN_DAYS_FOR_PATTERN:
            facts.append({
                "kind": "steadiness",
                "sd": round(pstdev(scores), 1),
                "range": round(max(scores) - min(scores), 1),
            })

    # --- what the days add up to -------------------------------------
    screen_minutes = [
        float(row["total_screen_min"]) for _, _, row in rows
        if isinstance(row.get("total_screen_min"), (int, float))
        and not isinstance(row.get("total_screen_min"), bool)
    ]
    if screen_minutes:
        facts.append({
            "kind": "screen_total",
            "hours": round(sum(screen_minutes) / 60.0, 1),
            "days": len(screen_minutes),
            "daily_average_minutes": round(mean(screen_minutes)),
        })

    sleep_hours = [
        float(row["sleep_hours"]) for _, _, row in rows
        if isinstance(row.get("sleep_hours"), (int, float))
        and not isinstance(row.get("sleep_hours"), bool)
    ]
    if len(sleep_hours) >= MIN_DAYS_FOR_PATTERN:
        facts.append({
            "kind": "sleep_average",
            "hours": round(mean(sleep_hours), 1),
            "best": round(max(sleep_hours), 1),
            "worst": round(min(sleep_hours), 1),
        })

    # --- day of life --------------------------------------------------
    if birth_date:
        try:
            born = date_cls.fromisoformat(birth_date)
        except ValueError:
            born = None
        if born and born <= now:
            alive = (now - born).days
            next_birthday = _birthday_in(born, now.year)
            if next_birthday < now:
                next_birthday = _birthday_in(born, now.year + 1)
            facts.append({
                "kind": "days_alive",
                "days": alive,
                "weeks": alive // 7,
                "born_weekday": WEEKDAYS[born.weekday()],
                "logged": len(rows),
                "share_logged": round(100.0 * len(rows) / alive, 3) if alive else 0.0,
            })
            facts.append({
                "kind": "next_birthday",
                "days": (next_birthday - now).days,
                "weekday": WEEKDAYS[next_birthday.weekday()],
                "turning": next_birthday.year - born.year,
            })
            # A birthday that is actually in the history is worth
            # naming; one that is not is simply not mentioned.
            birthdays = [
                (day, score) for day, score, _ in rows
                if (day.month, day.day) == (born.month, born.day)
            ]
            if birthdays:
                day, score = birthdays[-1]
                facts.append({
                    "kind": "birthday_logged",
                    "date": day.isoformat(),
                    "score": round(score, 1),
                    "average": round(mean(scores), 1),
                })

    return facts
