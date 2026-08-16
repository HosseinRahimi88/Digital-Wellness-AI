"""
api/routers/badges.py
---------------------
The badge catalogue (C-3) and the hall of fame's data (D-2).

Two endpoints, and the difference between them is a privacy boundary
rather than a convenience:

  GET /badges         everything, for the signed-in user's own eyes -
                      achievement badges and private awareness
                      indicators alike.
  GET /badges/public  achievement badges only. This is what any
                      friend-facing surface reads. Awareness indicators
                      are filtered out server-side, so a client bug
                      cannot leak "a late-night pattern is active" into
                      a league table.

Nothing here re-runs a prediction or changes a score. Badges are read
from stored check-ins only.
"""

from __future__ import annotations

import logging
from collections import Counter

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_history_service,
    get_history_storage_backend,
    get_plan_side_storage_backend,
)
from api.schemas.badges import BadgeResponse, BadgesResponse
from services.identity.account_service import Account
from services.social.badge_service import BadgeService
from services.storage.base import StorageBackend
from services.wellness.violation_service import ViolationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Badges"])


def _to_response(badges, state=None, withheld=None) -> BadgesResponse:
    """Turn evaluated badges into the response, applying the violation
    ledger on the way out.

    Two things it applies, both of which the user asked for explicitly:

      * a REVOKED badge - one spent paying for a missed plan day - is
        reported as not earned, with `revoked=True` so the Hall of Fame
        can show it as spent rather than as never won. Badges are
        derived from stored check-ins on every call, so the history
        that earned it is still true; revoking is the only way for it
        to have cost anything.

      * a WITHHELD badge - newly earned while violations were still
        outstanding - is reported as not earned either. That is the
        rule: a new badge clears one violation instead of registering,
        and only once the count reaches zero do badges start counting
        again. `withheld=True` keeps that visible rather than looking
        like the badge simply failed to unlock.
    """
    revoked = set((state.revoked_badge_ids if state else []) or [])
    spent = set(withheld or [])
    items = []
    for b in badges:
        was_revoked = b.id in revoked
        was_withheld = b.id in spent
        items.append(BadgeResponse(
            id=b.id, category=b.category, icon=b.icon, tier=b.tier,
            private=b.private,
            earned=b.earned and not was_revoked and not was_withheld,
            evaluable=b.evaluable,
            progress=b.progress, target=b.target, params=b.params,
            revoked=was_revoked, withheld=was_withheld,
        ))
    tiers = Counter(
        b.tier for b, item in zip(badges, items) if item.earned and b.tier
    )
    return BadgesResponse(
        badges=items,
        earned_count=sum(1 for item in items if item.earned),
        total_count=len(items),
        earned_by_tier=dict(tiers),
        open_violations=state.open_violations if state else 0,
        revoked_badges=sorted(revoked),
        withheld_badges=sorted(spent),
    )


def _evaluate(account: Account, storage: StorageBackend | None):
    history_service = get_history_service(account, storage=storage)
    # Exception days are read: BadgeService needs to see them both to
    # exclude them from every window and to award the data-honesty badge.
    return BadgeService.evaluate(history_service.get_all(include_excluded=True))


def _settle(account: Account, badges, storage: StorageBackend | None = None):
    """Run newly earned badges through the violation ledger.

    A badge earned while violations are outstanding is SPENT clearing
    one rather than registering - that is the rule the user set, and it
    is why this has to happen on read: badges are derived, so there is
    no "moment of earning" to hook into. Doing it here means the first
    time a newly earned badge would have been shown is the moment it
    pays off a violation instead.

    Returns (state, withheld_ids). Never raises outward: a ledger that
    cannot be read must not take the Hall of Fame down with it.
    """
    try:
        service = ViolationService(account.user_id, backend=storage) if storage else ViolationService(account.user_id)
        state = service.state()
        already = service.acked_badge_ids() | set(state.consumed_badge_ids)
        revoked = set(state.revoked_badge_ids)
        newly_earned = [
            b.id for b in badges
            if b.earned and not b.private and b.id not in already and b.id not in revoked
        ]
        withheld = service.absorb(newly_earned) if newly_earned else []
        return service.state(), withheld
    except Exception:  # noqa: BLE001
        logger.warning("Could not apply the violation ledger to badges.", exc_info=True)
        return None, []


@router.get(
    "/badges", response_model=BadgesResponse,
    summary="Every badge for the signed-in user, including private awareness indicators",
)
def badges(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> BadgesResponse:
    badges_list = _evaluate(account, storage)
    state, withheld = _settle(account, badges_list, side)
    return _to_response(badges_list, state, withheld)


@router.get(
    "/badges/public", response_model=BadgesResponse,
    summary="Achievement badges only - the sharable set, safe for the league",
)
def public_badges(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
    side: StorageBackend | None = Depends(get_plan_side_storage_backend),
) -> BadgesResponse:
    badges_list = _evaluate(account, storage)
    state, withheld = _settle(account, badges_list, side)
    return _to_response(BadgeService.public_badges(badges_list), state, withheld)
