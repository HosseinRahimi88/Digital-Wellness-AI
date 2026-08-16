"""
services/behavioral_insight_service.py
--------------------------------------
The history-derived "ideas" cards (D-4, D-5, D-6, D-9, D-11), computed
from the user's OWN real check-ins - never from cohort data and never
from the model's training set.

One service rather than five because they share the same three hazards,
and getting those right once is better than getting them wrong five
times:

  * Sample size. A correlation over four days is noise with a decimal
    point. Every card declares a minimum and returns None below it, so a
    thin history produces no card rather than a confident-looking number
    (G4).
  * Correlation is not causation. Every returned payload carries the
    relationship as an OBSERVATION, and the API/UI wording that renders
    it says "moved together", never "caused". The `causal` key is
    deliberately absent - there is nothing here that could carry it.
  * Exception days. Days the user marked as exceptions are excluded from
    every statistic, exactly as they are from the trend strip. A holiday
    should not become a discovered "pattern".

Nothing here touches a model or changes a model output; these are
descriptive statistics over stored numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Optional

# Minimum usable days per card. Chosen so a correlation has enough points
# for the coefficient to mean anything at all, not so high that a normal
# user never sees a card.
MIN_DAYS_CORRELATION = 10
MIN_DAYS_DOMINO = 8
MIN_DAYS_NARRATIVE = 5
MIN_DAYS_FIRST_VS_NOW = 10
MIN_DAYS_SMALL_WIN = 2

# A correlation weaker than this is not worth showing as a "discovery" -
# below it, the line through the points is mostly imagination. This is an
# effect-size floor only; on its own it is NOT enough (see below).
MIN_ABS_CORRELATION = 0.45

# The real hazard, and the one that made the first version of this file
# wrong: multiple comparisons. Scanning 13 fields means ~78 pairs, and with
# a fortnight of data the chance that SOME pair clears |r| >= 0.45 by luck
# is high - measured at 18 out of 25 pure-noise histories. That is
# p-hacking with a friendly UI.
#
# So a pair must also survive a Bonferroni-corrected significance test:
# its p-value, multiplied by the number of pairs actually examined, has to
# stay under ALPHA. Fewer usable fields means fewer comparisons means a
# gentler correction, which is the correct behaviour rather than a fudge.
ALPHA = 0.05

# Pairs worth testing. Restricted to fields the user actually answers, so
# a "discovery" is always about something they can act on. Derived or
# composite columns are deliberately excluded - telling someone their
# night_ratio correlates with their night minutes is arithmetic, not
# insight.
CANDIDATE_FIELDS = [
    "total_screen_min",
    "social_min",
    "gaming_min",
    "video_min",
    "night_screen_min",
    "pre_sleep_screen_min",
    "sleep_hours",
    "sleep_quality_1_10",
    "stress_0_10",
    "focus_0_100",
    "productivity_0_100",
    "physical_activity_min_per_day",
    "pickups_per_day",
]

# Pairs that would be tautological (one is derived from the other) or
# medically framed. Kept explicit so the exclusion is reviewable.
_TRIVIAL_PAIRS = {
    frozenset({"total_screen_min", "social_min"}),
    frozenset({"total_screen_min", "gaming_min"}),
    frozenset({"total_screen_min", "video_min"}),
    frozenset({"night_screen_min", "pre_sleep_screen_min"}),
    frozenset({"focus_0_100", "productivity_0_100"}),
}


def _usable(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Real days only, oldest first. Exception days never contribute."""
    rows = [e for e in (entries or []) if e and not e.get("excluded")]
    return sorted(rows, key=lambda e: str(e.get("date") or ""))


def _series(rows: list[dict[str, Any]], field: str) -> list[Optional[float]]:
    out: list[Optional[float]] = []
    for r in rows:
        v = r.get(field)
        if isinstance(v, bool) or v is None:
            out.append(None)
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            out.append(None)
    return out


def _pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _p_value(r: float, n: int) -> float:
    """Two-sided p for a Pearson r under the usual t transform."""
    if n < 3:
        return 1.0
    if abs(r) >= 1.0:
        return 0.0
    from scipy import stats
    t = abs(r) * math.sqrt((n - 2) / (1 - r * r))
    return float(2 * stats.t.sf(t, n - 2))


def _paired(rows: list[dict[str, Any]], a: str, b: str) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for x, y in zip(_series(rows, a), _series(rows, b)):
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    return xs, ys


@dataclass(slots=True)
class CorrelationInsight:
    field_a: str
    field_b: str
    coefficient: float
    direction: str          # "together" | "opposite"
    sample_size: int
    # Present so the UI never has to decide this itself.
    is_observation_only: bool = True


@dataclass(slots=True)
class DominoInsight:
    trigger_field: str
    next_day_field: str
    coefficient: float
    direction: str
    sample_size: int
    is_observation_only: bool = True


@dataclass(slots=True)
class FirstVsNowInsight:
    early_avg: float
    recent_avg: float
    delta: float
    window: int
    improved: bool


@dataclass(slots=True)
class SmallWinInsight:
    field: str
    yesterday: float
    today: float
    delta: float
    higher_is_better: bool


@dataclass(slots=True)
class NarrativeFacts:
    """Raw material for the weekly narrative (D-6). Deliberately facts,
    not prose: the sentence is composed in the user's own language on the
    client, so this service never has to hold four translations."""
    days: int
    avg_score: Optional[float]
    best_day: Optional[str]
    best_score: Optional[float]
    worst_day: Optional[str]
    worst_score: Optional[float]
    score_delta_vs_previous_week: Optional[float]
    most_improved_field: Optional[str]
    most_improved_delta: Optional[float]
    exceptions_marked: int


# Fields where a HIGHER number is the better outcome. Everything else is
# treated as lower-is-better when phrasing a change as a win.
_HIGHER_IS_BETTER = {
    "sleep_hours", "sleep_quality_1_10", "focus_0_100",
    "productivity_0_100", "physical_activity_min_per_day",
}


class BehavioralInsightService:
    """Descriptive statistics over one user's real history."""

    # ---------------- D-4: behavioural relationship ----------------

    @staticmethod
    def strongest_correlation(entries: list[dict[str, Any]]) -> Optional[CorrelationInsight]:
        rows = _usable(entries)
        if len(rows) < MIN_DAYS_CORRELATION:
            return None

        best: Optional[CorrelationInsight] = None
        best_r = 0.0
        best_n = 0
        comparisons = 0
        for i, a in enumerate(CANDIDATE_FIELDS):
            for b in CANDIDATE_FIELDS[i + 1:]:
                if frozenset({a, b}) in _TRIVIAL_PAIRS:
                    continue
                xs, ys = _paired(rows, a, b)
                if len(xs) < MIN_DAYS_CORRELATION:
                    continue
                # Counted whether or not it clears the effect-size floor:
                # the correction must reflect how many chances there were
                # to get lucky, not how many happened to look good.
                comparisons += 1
                r = _pearson(xs, ys)
                if r is None or abs(r) < MIN_ABS_CORRELATION:
                    continue
                if best is None or abs(r) > abs(best_r):
                    best_r, best_n = r, len(xs)
                    best = CorrelationInsight(
                        field_a=a, field_b=b, coefficient=round(r, 3),
                        direction="together" if r > 0 else "opposite",
                        sample_size=len(xs),
                    )

        if best is None:
            return None
        # Bonferroni: surviving one test out of many is not surviving.
        if _p_value(best_r, best_n) * max(1, comparisons) >= ALPHA:
            return None
        return best

    # ---------------- D-5: one-day-lag domino ----------------

    @staticmethod
    def strongest_domino(entries: list[dict[str, Any]]) -> Optional[DominoInsight]:
        """Does today's value of one field track TOMORROW's value of
        another? Same correlation maths, shifted by a day - which is why
        it stays an observation: a lag is suggestive, not proof."""
        rows = _usable(entries)
        if len(rows) < MIN_DAYS_DOMINO + 1:
            return None

        best: Optional[DominoInsight] = None
        best_r = 0.0
        best_n = 0
        comparisons = 0
        for a in CANDIDATE_FIELDS:
            today_all = _series(rows[:-1], a)
            for b in CANDIDATE_FIELDS:
                if a == b or frozenset({a, b}) in _TRIVIAL_PAIRS:
                    continue
                next_all = _series(rows[1:], b)
                xs, ys = [], []
                for x, y in zip(today_all, next_all):
                    if x is not None and y is not None:
                        xs.append(x)
                        ys.append(y)
                if len(xs) < MIN_DAYS_DOMINO:
                    continue
                comparisons += 1
                r = _pearson(xs, ys)
                if r is None or abs(r) < MIN_ABS_CORRELATION:
                    continue
                if best is None or abs(r) > abs(best_r):
                    best_r, best_n = r, len(xs)
                    best = DominoInsight(
                        trigger_field=a, next_day_field=b, coefficient=round(r, 3),
                        direction="together" if r > 0 else "opposite",
                        sample_size=len(xs),
                    )

        if best is None:
            return None
        # A lagged scan searches even more pairs than the same-day one, so
        # it needs the correction at least as much.
        if _p_value(best_r, best_n) * max(1, comparisons) >= ALPHA:
            return None
        return best

    # ---------------- D-9: first week vs now ----------------

    @staticmethod
    def first_vs_now(entries: list[dict[str, Any]], window: int = 5) -> Optional[FirstVsNowInsight]:
        rows = _usable(entries)
        if len(rows) < MIN_DAYS_FIRST_VS_NOW:
            return None
        scores = [s for s in _series(rows, "health_score") if s is not None]
        if len(scores) < MIN_DAYS_FIRST_VS_NOW:
            return None
        w = min(window, len(scores) // 2)
        early = scores[:w]
        recent = scores[-w:]
        early_avg = sum(early) / len(early)
        recent_avg = sum(recent) / len(recent)
        delta = recent_avg - early_avg
        return FirstVsNowInsight(
            early_avg=round(early_avg, 1), recent_avg=round(recent_avg, 1),
            delta=round(delta, 1), window=w, improved=delta >= 0,
        )

    # ---------------- D-11: a small win worth noting ----------------

    @staticmethod
    def small_win(entries: list[dict[str, Any]]) -> Optional[SmallWinInsight]:
        """The single clearest day-over-day improvement. Intentionally
        returns at most one: congratulating six things at once is how
        congratulation stops meaning anything."""
        rows = _usable(entries)
        if len(rows) < MIN_DAYS_SMALL_WIN:
            return None
        today, yesterday = rows[-1], rows[-2]

        best: Optional[SmallWinInsight] = None
        best_ratio = 0.0
        for field in CANDIDATE_FIELDS:
            t, y = today.get(field), yesterday.get(field)
            try:
                t = float(t); y = float(y)
            except (TypeError, ValueError):
                continue
            if y == 0:
                continue
            higher_better = field in _HIGHER_IS_BETTER
            delta = t - y
            improved = delta > 0 if higher_better else delta < 0
            if not improved:
                continue
            ratio = abs(delta) / abs(y)
            # Below 8% is inside normal day-to-day noise; calling it a win
            # would be flattery, not feedback.
            if ratio < 0.08:
                continue
            if ratio > best_ratio:
                best_ratio = ratio
                best = SmallWinInsight(
                    field=field, yesterday=round(y, 1), today=round(t, 1),
                    delta=round(delta, 1), higher_is_better=higher_better,
                )
        return best

    # ---------------- D-6: weekly narrative facts ----------------

    @staticmethod
    def narrative_facts(entries: list[dict[str, Any]]) -> Optional[NarrativeFacts]:
        rows = _usable(entries)
        if len(rows) < MIN_DAYS_NARRATIVE:
            return None
        week = rows[-7:]
        prev = rows[-14:-7]

        scores = [(r.get("date"), s) for r, s in zip(week, _series(week, "health_score")) if s is not None]
        avg = sum(s for _, s in scores) / len(scores) if scores else None
        best = max(scores, key=lambda p: p[1]) if scores else (None, None)
        worst = min(scores, key=lambda p: p[1]) if scores else (None, None)

        prev_scores = [s for s in _series(prev, "health_score") if s is not None]
        delta = None
        if avg is not None and prev_scores:
            delta = round(avg - (sum(prev_scores) / len(prev_scores)), 1)

        # Which tracked field moved most in the good direction this week?
        improved_field, improved_delta = None, None
        if prev:
            for field in CANDIDATE_FIELDS:
                cur = [v for v in _series(week, field) if v is not None]
                old = [v for v in _series(prev, field) if v is not None]
                if not cur or not old:
                    continue
                d = (sum(cur) / len(cur)) - (sum(old) / len(old))
                good = d if field in _HIGHER_IS_BETTER else -d
                if good <= 0:
                    continue
                if improved_delta is None or good > improved_delta:
                    improved_field, improved_delta = field, round(good, 1)

        excluded = sum(1 for e in (entries or []) if e and e.get("excluded"))
        return NarrativeFacts(
            days=len(week),
            avg_score=round(avg, 1) if avg is not None else None,
            best_day=best[0], best_score=round(best[1], 1) if best[1] is not None else None,
            worst_day=worst[0], worst_score=round(worst[1], 1) if worst[1] is not None else None,
            score_delta_vs_previous_week=delta,
            most_improved_field=improved_field,
            most_improved_delta=improved_delta,
            exceptions_marked=excluded,
        )

    # ---------------- aggregate ----------------

    @classmethod
    def build_all(cls, entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Every card at once; absent cards are None, never a placeholder."""
        corr = cls.strongest_correlation(entries)
        domino = cls.strongest_domino(entries)
        first_now = cls.first_vs_now(entries)
        win = cls.small_win(entries)
        facts = cls.narrative_facts(entries)
        return {
            "correlation": asdict(corr) if corr else None,
            "domino": asdict(domino) if domino else None,
            "first_vs_now": asdict(first_now) if first_now else None,
            "small_win": asdict(win) if win else None,
            "narrative": asdict(facts) if facts else None,
        }
