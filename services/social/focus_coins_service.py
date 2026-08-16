"""
Focus Coins Service
----------------------
"Focus Coins" (feature 17): a virtual currency computed on the fly as
a deterministic function of real, already-recorded actions - never
randomized, never stored as an independently-mutable balance (which
would risk drifting out of sync with the actions that supposedly
earned it). Every coin traces back to something real:

- check-ins logged (HistoryService)
- the user's longest real streak (GamificationService, reused not
  re-derived)
- plan tasks completed (PlanProgressService)
- commitments completed (CommitmentService)
- badges unlocked (GamificationService, reused)

Computing the balance fresh each time (rather than persisting a
running total) means it can never drift from the real actions behind
it - there is no separate ledger to fall out of sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.social.gamification_service import GamificationService

COINS_PER_CHECKIN = 5
COINS_PER_STREAK_DAY = 2  # multiplied by the user's longest real streak
COINS_PER_COMPLETED_PLAN_TASK = 3
COINS_PER_COMPLETED_COMMITMENT = 25
COINS_PER_UNLOCKED_BADGE = 15


@dataclass(slots=True)
class FocusCoinsBalance:
    total: int
    from_checkins: int
    from_streak: int
    from_plan_tasks: int
    from_commitments: int
    from_badges: int


class FocusCoinsService:
    """Computes a user's Focus Coins balance from real, existing data."""

    @classmethod
    def compute_balance(
        cls,
        entries: list[dict[str, Any]],
        completed_plan_tasks: int = 0,
        completed_commitments: int = 0,
    ) -> FocusCoinsBalance:
        streak_info = GamificationService.compute_streak(entries)
        badges = GamificationService.compute_badges(entries, streak_info=streak_info)
        unlocked_badges = sum(1 for b in badges if b.unlocked)

        from_checkins = len(entries) * COINS_PER_CHECKIN
        from_streak = streak_info.longest_streak * COINS_PER_STREAK_DAY
        from_plan_tasks = max(completed_plan_tasks, 0) * COINS_PER_COMPLETED_PLAN_TASK
        from_commitments = max(completed_commitments, 0) * COINS_PER_COMPLETED_COMMITMENT
        from_badges = unlocked_badges * COINS_PER_UNLOCKED_BADGE

        total = from_checkins + from_streak + from_plan_tasks + from_commitments + from_badges

        return FocusCoinsBalance(
            total=total,
            from_checkins=from_checkins,
            from_streak=from_streak,
            from_plan_tasks=from_plan_tasks,
            from_commitments=from_commitments,
            from_badges=from_badges,
        )
