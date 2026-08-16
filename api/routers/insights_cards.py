"""
api/routers/insights_cards.py
-----------------------------
The history-derived idea cards (D-3 through D-6, D-9, D-11) in one
read-only endpoint.

Everything here is computed from the authenticated user's own stored
check-ins. Nothing calls a model, and nothing changes a model output -
these are descriptive statistics plus the existing risk-alert rules.

Cards that lack enough data are returned as null rather than as an empty
shell, so the client renders nothing at all instead of an
official-looking card with dashes in it.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_history_storage_backend, get_history_service
from api.schemas.insights_cards import (
    InsightCardsResponse, RiskAlertResponse, WeeklyChallengeCard,
)
from services.identity.account_service import Account
from services.insight.behavioral_insight_service import BehavioralInsightService
from services.wellness.risk_alert_service import RiskAlertService
from services.wellness.weekly_challenge_service import WeeklyChallengeService
from services.storage.base import StorageBackend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Insight cards"])


@router.get(
    "/insights/cards", response_model=InsightCardsResponse,
    summary="Behavioural relationship, habit domino, weekly narrative facts, first-vs-now, small win and risk alerts",
)
def insight_cards(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> InsightCardsResponse:
    history_service = get_history_service(account, storage=storage)
    # Exception days are read too: the insight service excludes them from
    # every statistic itself, and it needs to see them to count them.
    entries = history_service.get_all(include_excluded=True)

    cards = BehavioralInsightService.build_all(entries)

    # D-3. Risk rules run on the real (non-excluded) history only - an
    # exception day must not trigger an alert about a pattern.
    alerts: list[RiskAlertResponse] = []
    try:
        real = [e for e in entries if not e.get("excluded")]
        alerts = [
            RiskAlertResponse(
                severity=a.severity, title=a.title, message=a.message, action=a.action,
                text_i18n=a.text_i18n,
            )
            for a in RiskAlertService.evaluate(real)
        ]
    except Exception:  # noqa: BLE001 - a failing alert rule must not blank the whole page
        logger.exception("Risk alert evaluation failed; returning cards without alerts.")

    # D-8. WeeklyChallengeService already existed with targets derived
    # from this user's own typical profile (AnalyticsService baselines) -
    # it was simply wired to no router. Exposing it rather than writing a
    # second, competing challenge generator.
    challenges: list[WeeklyChallengeCard] = []
    try:
        challenges = [
            # asdict, not vars: Challenge is a slots dataclass and has no
            # __dict__ at all, so vars() raises - and the except below
            # would have turned that into a permanently empty list.
            WeeklyChallengeCard(**asdict(c))
            for c in WeeklyChallengeService.generate_challenges([e for e in entries if not e.get("excluded")])
        ]
    except Exception:  # noqa: BLE001 - never blank the page over one card
        logger.exception("Weekly challenge generation failed; returning cards without it.")

    return InsightCardsResponse(
        correlation=cards["correlation"],
        domino=cards["domino"],
        first_vs_now=cards["first_vs_now"],
        small_win=cards["small_win"],
        narrative=cards["narrative"],
        weekly_challenges=challenges,
        risk_alerts=alerts,
    )
