"""
Rare Achievement Service
---------------------------
"Rare Achievement System" (feature 20) - a second, statistically-tiered
achievement track alongside services/gamification_service.py's
existing common Badges (which unlock on fixed, everyone-eventually-
gets-them thresholds like "10 check-ins"). Rarity here is grounded in
real numbers two ways:

- Cohort-based tiers: this user's own real historical average for a
  field, compared against the real training dataset distribution via
  services/cohort_service.py (reused, not re-derived) - e.g. "your
  average sleep is better than 95% of the training population" is a
  real percentile, not an arbitrary badge cutoff.
- Personal-history tiers: streak length from
  services/gamification_service.py.compute_streak() - reused rather
  than recomputed, since GamificationService already owns "what
  counts as a healthy day" and streak-breaking rules.

No fabricated rarity numbers anywhere - every tier boundary below is a
percentile threshold applied to a real CohortService.percentile_for()
call, or a real streak length.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from services.cohort_service import CohortService, USER_FIELD_TO_COHORT_FIELD
from services.gamification_service import GamificationService

# Percentile thresholds (see CohortService.percentile_for's "% of
# cohort <= value" semantics; DIRECTION below decides whether that
# percentile or its complement is what counts as "rare").
TIER_THRESHOLDS = [
    ("Legendary", 99.5),
    ("Epic", 97.0),
    ("Rare", 90.0),
]

# field -> (label, direction). direction="high" means a HIGH raw value
# is what's rare/impressive (so we tier on percentile_for directly);
# direction="low" means a LOW raw value is rare (so we tier on
# 100 - percentile_for, mirroring LeaderboardService's inversion).
RARE_FIELDS = {
    "health_score": ("Wellness Score", "high"),
    "focus_0_100": ("Focus", "high"),
    "sleep_hours": ("Sleep Duration", "high"),
    "physical_activity_min_per_day": ("Physical Activity", "high"),
    "stress_0_10": ("Low Stress", "low"),
    "total_screen_min": ("Digital Minimalism", "low"),
}

# Personal-history (non-cohort) rare streak tiers.
STREAK_TIER_THRESHOLDS = [
    ("Legendary", 30),
    ("Epic", 14),
    ("Rare", 7),
]


@dataclass(slots=True)
class RareAchievement:
    id: str
    name: str
    tier: str  # "Rare" | "Epic" | "Legendary"
    description: str
    icon: str


_TIER_ICONS = {"Rare": "🔹", "Epic": "🔮", "Legendary": "👑"}


class RareAchievementService:
    """Statistically-grounded rare/epic/legendary achievements."""

    @staticmethod
    def _tier_for_percentile(percentile: float) -> Optional[str]:
        for tier_name, threshold in TIER_THRESHOLDS:
            if percentile >= threshold:
                return tier_name
        return None

    @staticmethod
    def _tier_for_streak(streak_days: int) -> Optional[str]:
        for tier_name, threshold in STREAK_TIER_THRESHOLDS:
            if streak_days >= threshold:
                return tier_name
        return None

    @classmethod
    def compute_rare_achievements(
        cls, user_averages: dict[str, float], entries: list[dict[str, Any]]
    ) -> list[RareAchievement]:
        """
        `user_averages` maps real HistoryService field names to this
        user's own real historical average (same shape
        CohortService.compare_user_to_cohort expects). `entries` is
        this user's real HistoryService entries, used only for the
        streak-based achievement via GamificationService.

        Returns unlocked rare achievements only (no "locked" rows -
        unlike the common Badge system, showing a wall of unearned
        rare tiers would just read as a to-do list of things the user
        statistically likely never unlocks).
        """
        if not CohortService.is_available():
            return []

        achievements: list[RareAchievement] = []

        for field, (label, direction) in RARE_FIELDS.items():
            value = user_averages.get(field)
            if value is None:
                continue
            cohort_field = USER_FIELD_TO_COHORT_FIELD.get(field, field)
            raw_percentile = CohortService.percentile_for(cohort_field, value)
            if raw_percentile is None:
                continue

            effective_percentile = raw_percentile if direction == "high" else round(100.0 - raw_percentile, 1)
            tier = cls._tier_for_percentile(effective_percentile)
            if tier is None:
                continue

            achievements.append(RareAchievement(
                id=f"cohort_{field}_{tier.lower()}",
                name=f"{tier} {label}",
                tier=tier,
                description=(
                    f"Your average {label.lower()} is better than "
                    f"{effective_percentile:.1f}% of the real training population."
                ),
                icon=_TIER_ICONS[tier],
            ))

        streak_info = GamificationService.compute_streak(entries)
        streak_tier = cls._tier_for_streak(streak_info.longest_streak)
        if streak_tier is not None:
            achievements.append(RareAchievement(
                id=f"streak_{streak_tier.lower()}",
                name=f"{streak_tier} Streak",
                tier=streak_tier,
                description=f"A {streak_info.longest_streak}-day healthy streak - a genuinely rare feat of consistency.",
                icon=_TIER_ICONS[streak_tier],
            ))

        tier_rank = {"Legendary": 0, "Epic": 1, "Rare": 2}
        achievements.sort(key=lambda a: tier_rank.get(a.tier, 3))
        return achievements
