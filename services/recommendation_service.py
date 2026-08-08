"""
Recommendation Service
----------------------
Generate personalized recommendations using SHAP explanations.
"""

from __future__ import annotations

from typing import List

from config.recommendation_registry import (
    FEATURE_RECOMMENDATIONS,
    HIGH_PRIORITY_SCORE_THRESHOLD,
    MEDIUM_PRIORITY_SCORE_THRESHOLD,
)

from models.recommendation import Recommendation
from services.shap_service import SHAPFeature


class RecommendationService:
    """
    Personalized recommendation engine powered by SHAP.
    """

    def __init__(self) -> None:

        self.registry = FEATURE_RECOMMENDATIONS

    # =====================================================
    # Public API
    # =====================================================

    def generate(
        self,
        shap_features: List[SHAPFeature],
        top_k: int = 3,
        category_track_record: dict | None = None,
        excluded_categories: set[str] | None = None,
    ) -> List[Recommendation]:
        """
        Generate personalized recommendations.

        Parameters
        ----------
        shap_features
            Ranked SHAP features.

        top_k
            Maximum number of recommendations.

        category_track_record
            Optional {category: avg_measured_score_delta} from
            services.recommendation_effectiveness_service
            .RecommendationEffectivenessService.compute_category_track_record()
            - this user's own real, measured history of whether acting
            on a category actually helped them before (feature 56, the
            Recommendation Learning Loop). When given, it only nudges
            the sort order *within* the existing HIGH/MEDIUM/LOW
            priority tiers (a real personalization signal breaking
            ties, never overriding the SHAP-driven priority itself);
            omitted or empty, behavior is identical to before this
            parameter existed.

        Returns
        -------
        list[Recommendation]
        """

        recommendations: List[Recommendation] = []

        used_categories: set[str] = set()

        # Only turn features that are genuinely dragging the score down
        # into "improve this" recommendations. `shap_features` is ranked
        # by |SHAP value| (magnitude), not sign - a feature the user is
        # already doing *well* on (direction="increase", i.e. it's
        # pushing their score UP) can easily have the single largest
        # magnitude for a healthy user, since strong positive habits are
        # exactly what a good model should weight heavily. Without this
        # filter, that feature's fixed, one-directional template copy
        # (e.g. sleep_hours's "Aim for 7-9 hours of sleep" for a user who
        # already sleeps 9 hours and that's *why* their score is high)
        # gets surfaced as a top/HIGH-priority fix-it item - backwards,
        # demotivating advice for the exact thing the user is doing
        # right. Every prior test for this method only ever constructed
        # direction="decrease" fixtures, so this path was never exercised.
        # Verified against config.demo_profiles.healthy_profile(): before
        # this filter, its top SHAP feature (night_ratio, direction=
        # "increase", i.e. already very low/good) produced a HIGH-priority
        # "Avoid Late Night Device Usage" recommendation despite that
        # being the user's strongest asset, not a problem.
        harmful_features = [f for f in shap_features if f.direction == "decrease"]

        excluded = excluded_categories or set()

        for feature in harmful_features:

            template = self.registry.get(
                feature.feature
            )

            if template is None:
                continue

            if template.category in used_categories:
                continue

            if template.category in excluded:
                continue

            recommendation = Recommendation(

                title=template.title,

                description=template.description,

                action=template.action,

                category=template.category,

                icon=template.icon,

                priority=self._priority_from_score(
                    feature.score
                ),

                success_metric=template.success_metric,

                safety_note=template.safety_note,

                source_field=feature.feature,

            )

            recommendations.append(
                recommendation
            )

            used_categories.add(
                template.category
            )

            if len(recommendations) >= top_k:
                break

        track_record = category_track_record or {}
        recommendations.sort(
            key=lambda rec: (
                self._sort_priority(rec),
                -track_record.get(rec.category, 0.0),
            )
        )

        return recommendations

    # =====================================================
    # Priority Mapping
    # =====================================================

    @staticmethod
    def _priority_from_score(
        score: float,
    ) -> str:
        """
        Convert normalized SHAP score to priority.
        """

        if score >= HIGH_PRIORITY_SCORE_THRESHOLD:
            return "HIGH"

        if score >= MEDIUM_PRIORITY_SCORE_THRESHOLD:
            return "MEDIUM"

        return "LOW"

    # =====================================================

    @staticmethod
    def _sort_priority(
        recommendation: Recommendation,
    ) -> int:
        """
        Sort recommendations by priority.
        """

        priorities = {

            "HIGH": 0,

            "MEDIUM": 1,

            "LOW": 2,

        }

        return priorities.get(
            recommendation.priority,
            99,
        )