"""
=========================================================
Digital Wellness AI
Persona Model Training (Group C Feature 02 - Persona Detection)

Responsibilities
----------------
Fit an unsupervised behavioral-persona clustering model on the training
split only (no leakage - validation/test are never touched here), and
save it as its own artifact family, parallel to the classifier/regressor
(models/model_saver.py convention) but independent of them.

Why clustering, and why these specific features
-------------------------------------------------
`utils/persona.py` (existing, kept) assigns a friendly label purely from
if/else rules on the classifier's predicted class plus 1-2 raw fields.
That's fine for a lighthearted label, but it isn't a *behavioral persona*
in any real sense - two users who both land in "Moderate" get bucketed
the same way even if their actual day-to-day habits look nothing alike.

This script instead fits KMeans (Lloyd's algorithm, scikit-learn) on a
curated set of PERSONA_FEATURES - numeric, human-interpretable behavioral
and psychological fields that already exist in FEATURE_SCHEMA (never the
composite subscores or health_score itself, which would leak the
regression target into what is meant to be an unsupervised, orthogonal
signal). Standardization (zero mean, unit variance per feature) is
required before clustering because these features live on very different
scales (e.g. `sleep_hours` ~0-12 vs `fragmentation_index_0_100` ~0-100) -
without it, high-magnitude features would dominate the Euclidean distance
KMeans uses, regardless of their actual behavioral importance.

Choosing K
----------
K is not hand-picked. This script fits KMeans for K in
`CANDIDATE_K_VALUES` and selects the K that maximizes the mean silhouette
score (a measure of how well-separated and internally-cohesive the
resulting clusters are - the standard, defensible way to choose K for
KMeans without a labeled ground truth). The chosen K and its silhouette
score are recorded in `artifacts/persona_info.json` for transparency.

Cluster naming
--------------
Persona names are derived, not fabricated: for each fitted cluster, this
script compares the cluster's centroid (in the original, unstandardized
feature scale) against the *global* training-set mean and standard
deviation, keeps the features where the cluster deviates most (|z-score|
largest), and composes a name from those actual deviations via
`_PERSONA_DESCRIPTORS`. Two different training runs on materially
different data would produce different centroids and therefore different
derived names - the name is a function of the data, not a fixed lookup
table keyed by cluster index.
"""

from __future__ import annotations

import json
import logging
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

PERSONA_MODEL_PATH = ARTIFACTS_DIR / "persona_model.pkl"
PERSONA_INFO_PATH = ARTIFACTS_DIR / "persona_info.json"

RANDOM_STATE = 42
CANDIDATE_K_VALUES = [4, 5, 6, 7]

# Curated, human-interpretable behavioral/psychological features. All are
# real FEATURE_SCHEMA fields the live form actually collects (so
# inference-time assignment never has to guess at missing inputs); none
# are leakage columns (composite subscores / health_score_0_100 /
# future_* targets are all excluded, same leakage list philosophy as
# models/preprocessing.py).
PERSONA_FEATURES = [
    "sleep_hours",
    "sleep_quality_1_10",
    "stress_0_10",
    "mental_fatigue_0_10",
    "happiness_0_10",
    "loneliness_1_10",
    "life_satisfaction_1_10",
    "social_ratio",
    "gaming_ratio",
    "night_ratio",
    "fragmentation_index_0_100",
    "focus_0_100",
    "productivity_0_100",
    "digital_dependence_0_100",
    "physical_activity_min_per_day",
]

# (feature, "high"/"low") -> short descriptor used to compose a persona
# name from a cluster's actual defining traits. Directions are relative
# to the *global training mean*, not absolute thresholds.
_PERSONA_DESCRIPTORS: dict[tuple[str, str], str] = {
    ("sleep_hours", "low"): "Sleep-Deprived",
    ("sleep_hours", "high"): "Well-Rested",
    ("sleep_quality_1_10", "low"): "Restless-Sleeper",
    ("stress_0_10", "high"): "High-Stress",
    ("stress_0_10", "low"): "Low-Stress",
    ("mental_fatigue_0_10", "high"): "Fatigued",
    ("happiness_0_10", "high"): "Content",
    ("happiness_0_10", "low"): "Low-Mood",
    ("loneliness_1_10", "high"): "Isolated",
    ("life_satisfaction_1_10", "high"): "Fulfilled",
    ("life_satisfaction_1_10", "low"): "Unsatisfied",
    ("social_ratio", "high"): "Social-Media-Heavy",
    ("gaming_ratio", "high"): "Gaming-Focused",
    ("night_ratio", "high"): "Night-Owl",
    ("fragmentation_index_0_100", "high"): "Fragmented-Attention",
    ("focus_0_100", "high"): "Deep-Focus",
    ("focus_0_100", "low"): "Easily-Distracted",
    ("productivity_0_100", "high"): "Productive",
    ("productivity_0_100", "low"): "Low-Output",
    ("digital_dependence_0_100", "high"): "Digitally-Dependent",
    ("digital_dependence_0_100", "low"): "Digitally-Independent",
    ("physical_activity_min_per_day", "high"): "Active",
    ("physical_activity_min_per_day", "low"): "Sedentary",
}


def _derive_persona_name(
    centroid_original_scale: np.ndarray,
    global_mean: np.ndarray,
    global_std: np.ndarray,
    feature_names: list[str],
    top_n: int = 2,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Rank features by |z-score| of this centroid vs. the global training
    distribution, and compose a name from the top-N most defining traits
    that have a descriptor. Falls back to a generic name only if none of
    the ranked features have a mapped descriptor (should not happen with
    the curated PERSONA_FEATURES / _PERSONA_DESCRIPTORS above, but this
    keeps naming crash-proof for future feature-set edits).
    """
    z_scores = (centroid_original_scale - global_mean) / np.where(global_std == 0, 1.0, global_std)
    order = np.argsort(-np.abs(z_scores))

    traits: list[dict[str, Any]] = []
    descriptors: list[str] = []

    for idx in order:
        if len(descriptors) >= top_n:
            break
        feature = feature_names[idx]
        z = float(z_scores[idx])
        direction = "high" if z > 0 else "low"
        descriptor = _PERSONA_DESCRIPTORS.get((feature, direction))
        traits.append({
            "feature": feature,
            "z_score": round(z, 3),
            "direction": direction,
            "value": round(float(centroid_original_scale[idx]), 2),
        })
        if descriptor:
            descriptors.append(descriptor)

    name = " ".join(descriptors) if descriptors else "Balanced Explorer"
    return name, traits


def train_persona_model() -> dict[str, Any]:
    from models.data_loader import load_datasets

    logger.info("Loading training data for persona clustering...")
    train_df, _, _ = load_datasets()

    missing = [c for c in PERSONA_FEATURES if c not in train_df.columns]
    if missing:
        raise ValueError(f"Training data is missing persona features: {missing}")

    X_raw = train_df[PERSONA_FEATURES].astype(float)
    # Drop rows with any missing value in the persona feature set rather
    # than imputing - clustering on imputed placeholder values would
    # distort centroids for a small subset of rows for no real benefit;
    # the training set is large enough that dropping is harmless.
    X_raw = X_raw.dropna()
    logger.info("Clustering on %d rows x %d features.", len(X_raw), len(PERSONA_FEATURES))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw.to_numpy())

    best_k = None
    best_score = -1.0
    best_model = None

    # Silhouette score on the full set is O(n^2); subsample for the
    # model-selection loop only (selection quality is unaffected by a
    # large, representative subsample) to keep training fast, then refit
    # the chosen K on the full dataset for the artifact that ships.
    rng = np.random.RandomState(RANDOM_STATE)
    sample_size = min(8000, len(X_scaled))
    sample_idx = rng.choice(len(X_scaled), size=sample_size, replace=False)

    for k in CANDIDATE_K_VALUES:
        candidate = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels_full = candidate.fit_predict(X_scaled)
        score = silhouette_score(X_scaled[sample_idx], labels_full[sample_idx])
        logger.info("K=%d silhouette=%.4f", k, score)
        if score > best_score:
            best_score = score
            best_k = k
            best_model = candidate

    logger.info("Selected K=%d (silhouette=%.4f).", best_k, best_score)

    kmeans = best_model
    cluster_labels = kmeans.predict(X_scaled)

    global_mean = X_raw.mean().to_numpy()
    global_std = X_raw.std().to_numpy()

    centroids_original = scaler.inverse_transform(kmeans.cluster_centers_)

    clusters_info = []
    for cluster_id in range(best_k):
        size = int((cluster_labels == cluster_id).sum())
        name, traits = _derive_persona_name(
            centroids_original[cluster_id], global_mean, global_std, PERSONA_FEATURES,
        )
        clusters_info.append({
            "cluster_id": cluster_id,
            "name": name,
            "size": size,
            "size_pct": round(100.0 * size / len(X_raw), 2),
            "defining_traits": traits,
        })
        logger.info("Cluster %d: '%s' (n=%d, %.1f%%)", cluster_id, name, size, 100.0 * size / len(X_raw))

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    artifact = {
        "scaler": scaler,
        "kmeans": kmeans,
        "feature_names": PERSONA_FEATURES,
        "global_mean": global_mean,
        "global_std": global_std,
    }
    joblib.dump(artifact, PERSONA_MODEL_PATH)
    logger.info("Persona model saved -> %s", PERSONA_MODEL_PATH)

    info = {
        "project": "Digital Wellness AI",
        "task": "persona_clustering",
        "version": "1.0.0",
        "saved_at": datetime.now().isoformat(),
        "algorithm": "KMeans",
        "k": best_k,
        "candidate_k_values": CANDIDATE_K_VALUES,
        "silhouette_score": round(float(best_score), 4),
        "training_rows": int(len(X_raw)),
        "feature_names": PERSONA_FEATURES,
        "python_version": platform.python_version(),
        "pandas_version": pd.__version__,
        "sklearn_version": sklearn.__version__,
        "clusters": clusters_info,
    }
    with open(PERSONA_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    logger.info("Persona metadata saved -> %s", PERSONA_INFO_PATH)

    return info


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    result = train_persona_model()
    print(json.dumps(result["clusters"], indent=2))
