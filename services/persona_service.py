"""
Persona Service
---------------
Group C Feature 02 - Persona Detection.

Assigns a user to the behavioral persona cluster fitted by
`models/train_persona.py` (KMeans over standardized behavioral/
psychological features), using nearest-centroid assignment in the same
standardized feature space the clustering was fit on.

This deliberately sits *alongside*, not on top of, the classifier/
regressor: persona assignment is unsupervised and describes *how someone
behaves*, while the classifier predicts *future risk*. Two users with
the same predicted health class can (and often do) land in different
personas, and that's the point - `utils/persona.py`'s rule-based label
only ever varied with the predicted class plus 1-2 fields, so it could
never make that distinction.

Confidence / relative uncertainty
----------------------------------
KMeans clusters on this kind of continuous behavioral survey data are
not perfectly separated (see `artifacts/persona_info.json`'s
`silhouette_score` - it is honestly low, ~0.08, which is expected for
overlapping human-behavior distributions rather than a bug). Rather than
fabricate a false sense of certainty, this service reports a genuine
relative-distance confidence: how much closer the user is to their
assigned centroid than to the *second*-closest one. A user sitting near
the boundary between two personas gets a low confidence score and both
personas are surfaced; a user close to one centroid and far from every
other gets a high confidence score.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
PERSONA_MODEL_PATH = ARTIFACTS_DIR / "persona_model.pkl"
PERSONA_INFO_PATH = ARTIFACTS_DIR / "persona_info.json"


@dataclass(slots=True)
class PersonaResult:
    available: bool = False

    persona_name: str = ""
    cluster_id: Optional[int] = None

    # Relative-distance confidence in [0, 1]. 1.0 = extremely close to
    # this centroid and far from every other; ~0 = sitting almost exactly
    # between this centroid and the runner-up.
    confidence: Optional[float] = None

    # Second-closest persona - shown when confidence is low, since the
    # honest answer for a borderline user is "somewhere between these
    # two", not a single falsely-precise label.
    runner_up_persona: Optional[str] = None

    defining_traits: list[dict[str, Any]] = field(default_factory=list)
    cluster_size_pct: Optional[float] = None

    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "persona_name": self.persona_name,
            "cluster_id": self.cluster_id,
            "confidence": self.confidence,
            "runner_up_persona": self.runner_up_persona,
            "defining_traits": self.defining_traits,
            "cluster_size_pct": self.cluster_size_pct,
            "explanation": self.explanation,
        }


class PersonaService:
    """
    Loads the persona clustering artifact once (process-wide, via
    ModelManager) and reuses it for every `assign()` call.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._load_failed_reason: Optional[str] = None

        self._scaler = None
        self._kmeans = None
        self._feature_names: list[str] = []
        self._clusters_by_id: dict[int, dict[str, Any]] = {}

        self._load()

    # ------------------------------------------------------

    def _load(self) -> None:
        with self._lock:
            if not PERSONA_MODEL_PATH.exists() or not PERSONA_INFO_PATH.exists():
                self._load_failed_reason = (
                    "Persona model artifact not found. Run "
                    "`python -m models.train_persona` to generate it."
                )
                logger.warning(self._load_failed_reason)
                return

            try:
                import json

                artifact = joblib.load(PERSONA_MODEL_PATH)
                self._scaler = artifact["scaler"]
                self._kmeans = artifact["kmeans"]
                self._feature_names = artifact["feature_names"]

                with open(PERSONA_INFO_PATH, "r", encoding="utf-8") as f:
                    info = json.load(f)
                self._clusters_by_id = {c["cluster_id"]: c for c in info.get("clusters", [])}

                self._loaded = True
                logger.info(
                    "PersonaService loaded (%d clusters, %d features).",
                    len(self._clusters_by_id), len(self._feature_names),
                )
            except Exception as exc:  # noqa: BLE001
                self._load_failed_reason = f"Failed to load persona artifact: {exc}"
                logger.exception("Persona model failed to load.")

    # ------------------------------------------------------

    def assign(self, user_data: dict[str, Any]) -> PersonaResult:
        """
        Assign `user_data` (a validated feature dict, same shape
        PredictionService receives) to its nearest persona cluster.
        Never raises - missing/unavailable inputs degrade to an
        `available=False` result (robustness requirement).
        """
        if not self._loaded:
            return PersonaResult(
                available=False,
                explanation=self._load_failed_reason or "Persona model unavailable.",
            )

        try:
            missing = [f for f in self._feature_names if f not in user_data or user_data[f] is None]
            if missing:
                return PersonaResult(
                    available=False,
                    explanation=f"Cannot assign a persona: missing fields {missing}.",
                )

            x = np.array([[float(user_data[f]) for f in self._feature_names]])
            x_scaled = self._scaler.transform(x)

            # Distance to every centroid, not just the nearest - needed
            # for the runner-up / relative-confidence calculation below.
            centroid_distances = self._kmeans.transform(x_scaled)[0]
            order = np.argsort(centroid_distances)
            nearest_id, runner_up_id = int(order[0]), int(order[1])
            nearest_dist, runner_up_dist = centroid_distances[order[0]], centroid_distances[order[1]]

            # Relative-distance confidence: 0 when the user sits exactly
            # equidistant between the two closest centroids (genuinely
            # ambiguous), approaching 1 as the nearest centroid dominates.
            total = nearest_dist + runner_up_dist
            confidence = float(1.0 - (nearest_dist / total)) if total > 0 else 1.0
            # Rescale so "equidistant" (raw 0.5) maps to confidence 0 and
            # "infinitely closer to nearest" (raw ~1.0) maps to confidence 1.
            confidence = max(0.0, min(1.0, (confidence - 0.5) * 2))

            nearest_info = self._clusters_by_id.get(nearest_id, {})
            runner_up_info = self._clusters_by_id.get(runner_up_id, {})

            explanation = (
                f"Closest behavioral match: '{nearest_info.get('name', 'Unknown')}' "
                f"({nearest_info.get('size_pct', 0):.1f}% of the training population "
                f"shows this pattern)."
            )
            if confidence < 0.35:
                explanation += (
                    f" This is a borderline case, close to '{runner_up_info.get('name', 'Unknown')}' as well."
                )

            return PersonaResult(
                available=True,
                persona_name=nearest_info.get("name", "Unknown"),
                cluster_id=nearest_id,
                confidence=round(confidence, 3),
                runner_up_persona=runner_up_info.get("name") if confidence < 0.35 else None,
                defining_traits=nearest_info.get("defining_traits", []),
                cluster_size_pct=nearest_info.get("size_pct"),
                explanation=explanation,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Persona assignment failed.")
            return PersonaResult(available=False, explanation=f"Persona assignment failed: {exc}")
