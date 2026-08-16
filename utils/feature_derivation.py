"""
utils/feature_derivation.py
----------------------------
Shared derived-feature computation.

This module contains the exact "Smart Dynamic Feature Computation" logic
that used to live only inline inside `utils/form_generator.py`. It has
been extracted, unchanged, into a standalone function so any other UI
surface that needs to send data through `PredictionService` (in
particular the What-if Simulator) computes the *same* derived / ratio /
density features from raw inputs - instead of re-implementing (and
risking drift or accidental leakage from) the formulas the trained
models were actually fit on.

This is a refactor of existing, already-shipped logic - not a change to
feature engineering. `FormGenerator.render()` now calls this same
function instead of repeating the block inline; its output is identical
to before.
"""

from __future__ import annotations

from typing import Any, Dict


def compute_total_screen_min(data: Dict[str, Any]) -> float:
    """
    The single source of truth for "total screen minutes today": the sum
    of the five usage-category minute fields the form actually collects
    (there is no independently-tracked device-level total anywhere in
    this app - see module docstring). Floored at 1.0 to avoid
    division-by-zero in every ratio/density derived from it.

    Extracted out of derive_features() so any other caller that only
    needs this one value (services/ml/cohort_service.py's population
    comparisons) can reuse the exact same formula instead of
    re-implementing "sum of five columns" a second time.

    See compute_total_screen_min_vectorized() below for the pandas
    equivalent used when operating on a whole DataFrame at once - the
    two must be kept in sync (same five columns, same floor of 1.0).
    """
    total_calc = (
        float(data.get("social_min", 0.0) or 0.0)
        + float(data.get("gaming_min", 0.0) or 0.0)
        + float(data.get("work_study_min", 0.0) or 0.0)
        + float(data.get("video_min", 0.0) or 0.0)
        + float(data.get("other_min", 0.0) or 0.0)
    )
    return max(total_calc, 1.0)


def compute_total_screen_min_vectorized(df: "Any") -> "Any":
    """
    Vectorized (pandas) equivalent of compute_total_screen_min(), for
    callers operating on a whole DataFrame at once instead of one dict
    per row (e.g. services/ml/cohort_service.py's population-level load).
    Same formula, same floor of 1.0 - see compute_total_screen_min()
    above, which single-row callers should use instead.
    """
    category_columns = ["social_min", "gaming_min", "work_study_min", "video_min", "other_min"]
    total = df[category_columns].fillna(0.0).sum(axis=1)
    return total.clip(lower=1.0)


def derive_features(user_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a dict containing the "raw" fields collected by the form
    (social_min, gaming_min, work_study_min, video_min, other_min,
    night_screen_min, pre_sleep_screen_min, first_check_after_waking_min,
    notifications_per_day, pickups_per_day, app_opens_per_day,
    sessions_per_day, ...), compute every derived/composite field the
    trained models expect:

        total_screen_min, social_ratio, gaming_ratio, work_study_ratio,
        other_ratio, night_ratio, pre_sleep_ratio, notification_density,
        pickup_density, app_open_density, screen_ewma_baseline,
        screen_vs_baseline_pct, fragmentation_index_0_100,
        digital_dependence_0_100

    and return a NEW dict with those keys added/overwritten. The input
    dict is not mutated.

    This is also, deliberately, the exact function
    models/data_loader.py uses to regenerate these same columns in
    data/{train,validation,test}.csv at load time (see
    reconstruct_derived_features() there) - training and inference
    compute every one of these features from one single code path, so
    there is no train/serve skew possible for anything in this list.
    """
    data: Dict[str, Any] = dict(user_inputs)

    # ---- Total screen time ---------------------------------------------
    data["total_screen_min"] = compute_total_screen_min(data)
    tot_screen = data["total_screen_min"]
    screen_hours = tot_screen / 60.0 if tot_screen > 0 else 1.0

    # ---- Ratios ---------------------------------------------------------
    data["social_ratio"] = round(float(data.get("social_min", 0.0) or 0.0) / tot_screen, 4)
    data["gaming_ratio"] = round(float(data.get("gaming_min", 0.0) or 0.0) / tot_screen, 4)
    data["work_study_ratio"] = round(float(data.get("work_study_min", 0.0) or 0.0) / tot_screen, 4)
    data["other_ratio"] = round(float(data.get("other_min", 0.0) or 0.0) / tot_screen, 4)
    data["night_ratio"] = round(float(data.get("night_screen_min", 0.0) or 0.0) / tot_screen, 4)
    data["pre_sleep_ratio"] = round(float(data.get("pre_sleep_screen_min", 0.0) or 0.0) / tot_screen, 4)

    # ---- Densities --------------------------------------------------------
    data["notification_density"] = round(float(data.get("notifications_per_day", 0) or 0) / screen_hours, 2)
    data["pickup_density"] = round(float(data.get("pickups_per_day", 0) or 0) / screen_hours, 2)
    data["app_open_density"] = round(float(data.get("app_opens_per_day", 0) or 0) / screen_hours, 2)

    # ---- Baselines ----------------------------------------------------
    # screen_ewma_baseline represents the user's personal recent-history
    # average. FormGenerator always computes this fresh (first-time users
    # have no history yet, so "today" is the only reasonable baseline).
    # When this helper is reused by the What-if Simulator on top of an
    # *existing* real submission that already carries a baseline, a
    # hypothetical "what if I changed today's numbers" tweak should not
    # silently redefine that personal baseline - so we only fall back to
    # "current total" when no baseline was supplied at all, matching
    # FormGenerator's original first-time-user behaviour exactly.
    if user_inputs.get("screen_ewma_baseline") is None:
        data["screen_ewma_baseline"] = tot_screen

    pop_baseline = 240.0
    raw_pct = ((tot_screen - pop_baseline) / pop_baseline) * 100.0
    # Clip to the declared FEATURE_SCHEMA range for this derived field.
    data["screen_vs_baseline_pct"] = round(max(-100.0, min(300.0, raw_pct)), 2)

    # ---- Usage Fragmentation Index (0-100) -------------------------------
    frag_score = (
        float(data.get("pickups_per_day", 0) or 0) * 0.4
        + float(data.get("sessions_per_day", 0) or 0) * 0.6
    )
    data["fragmentation_index_0_100"] = round(min(100.0, max(0.0, frag_score)), 2)

    # ---- Digital Dependence Index (0-100) --------------------------------
    recreation_min = (
        float(data.get("social_min", 0.0) or 0.0)
        + float(data.get("gaming_min", 0.0) or 0.0)
        + float(data.get("video_min", 0.0) or 0.0)
    )
    night_penalty = float(data.get("night_screen_min", 0.0) or 0.0) * 1.5
    waking_penalty = max(0.0, 60.0 - float(data.get("first_check_after_waking_min", 0.0) or 0.0)) * 0.8
    dep_score = (recreation_min / 6.0) + (night_penalty / 3.0) + waking_penalty
    data["digital_dependence_0_100"] = round(min(100.0, max(0.0, dep_score)), 2)

    return data
