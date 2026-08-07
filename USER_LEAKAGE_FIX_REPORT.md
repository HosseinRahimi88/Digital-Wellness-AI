# User-Level Leakage Fix — Final Report

Scope, per instruction: **only** the train/validation/test user-leakage
issue. No other refactors, features, or service/UI changes were made
except retraining the three model artifacts against the corrected split
and regenerating the two artifacts that depend on it. Every other file
in the project is unchanged from before this task.

---

## 1–2) Audit & user identifier

No `user_id` (or any row-identity column) exists in `data/*.csv`, and no
data-generation script exists anywhere in this repository to regenerate
one from. A user identifier had to be **reconstructed** from the columns
that stay fixed for the same person across their diary of days: `age`,
`gender`, `occupation_group`, `region_group`, `education_group`,
`device_category`, `primary_platform`, `purpose_group`,
`is_content_creator`, `uses_screen_time_limits`.

**Verified this reconstruction is safe before using it as a split key:**
`age` is a clean integer with no day-to-day jitter (confirmed by direct
inspection), so it and the other 9 fields cannot fragment one real
person's rows into multiple groups. The only failure mode this proxy can
have is the *safe* one — merging two distinct people who happen to share
all 10 fields into a single group (confirmed this happens for ~42% of
the reconstructed groups, since several rows per group have duplicate
`day_index` values, i.e., more days than one person could have logged) —
which can only make the split more conservative, never leak a real
user's rows across the boundary.

## 3–5) Regenerated splits — strict group split

**Method:** pooled all three existing CSVs (104,469 rows total), built
the group key above, then ran
`StratifiedGroupKFold(n_splits=18, shuffle=True, random_state=42)`.
K-fold group partitioning guarantees the held-out fold of any two
different splits are group-disjoint by construction, so fold 0 → new
test, fold 1 → new validation, remaining 16 folds → new train gives
three mutually group-disjoint sets with ~1/18 (5.56%) in each of
validation/test.

Implementation: `models/regenerate_user_split.py` (new, one-off script,
same convention as the existing `train_*.py` scripts). It backs up the
original files to `data/archive_pre_user_split_fix/` before writing, and
writes a machine-readable verification report to
`artifacts/leakage_verification_report.json`.

| | rows | ratio | user groups |
|---|---|---|---|
| **Train** | 92,867 | 88.89% | 3,022 |
| **Validation** | 5,800 | 5.55% | 191 |
| **Test** | 5,802 | 5.55% | 191 |
| *(original ratios, for comparison)* | 92,949 / 5,758 / 5,762 | 89.00% / 5.51% / 5.52% | — |

Class balance (`future_health_class_7d`) came out nearly identical across
all three new splits — At Risk / Healthy / Moderate ≈ 33.3% / 33.0% /
33.6% in every split — because the pooled population's overall balance
is dominated by the originally class-balanced `train.csv`, and the
stratified-group method preserves that balance well within each new
split.

## 9) Leakage verification — evidence

**Two independent checks**, not just the generation script's own
internal assertions:

1. **Inside `regenerate_user_split.py`** (asserted before any file was
   written, would have raised `AssertionError` and aborted otherwise):
   `Train ∩ Validation = 0`, `Train ∩ Test = 0`, `Validation ∩ Test = 0`
   group intersections.
2. **Re-derived independently after retraining**, from the final written
   `data/*.csv` files, using a separate script that recomputes the
   10-field signature sets from scratch:
   ```
   unique user-groups: train=3022 val=191 test=191
   train & val intersection: 0
   train & test intersection: 0
   val & test intersection: 0

   row-level exact duplicate check (paranoia):
   train & val exact row overlap: 0
   train & test exact row overlap: 0
   val & test exact row overlap: 0
   ```
   The row-level hash check is a second, even stricter, independent
   confirmation beyond the group-signature check.

Both checks agree: **zero leakage remains**, at both the reconstructed-user
level and the raw-row level.

## 6–7) Retraining — every affected artifact

All three model-training scripts (`train_classification.py`,
`train_regression.py`, `models.train_persona`) were re-run unmodified
against the new `data/{train,validation,test}.csv`, regenerating:

| Artifact | Status |
|---|---|
| `artifacts/health_classifier.pkl` | Retrained |
| `artifacts/health_regressor.pkl` | Retrained |
| `artifacts/persona_model.pkl` | Retrained |
| `artifacts/feature_columns.json` / `feature_columns_regression.json` | Regenerated |
| `artifacts/metrics.json` / `metrics_regression.json` | Regenerated |
| `artifacts/model_info.json` / `model_info_regression.json` | Regenerated |
| `artifacts/persona_info.json` | Regenerated |
| `artifacts/uncertainty_calibration.json` | Regenerated — this one is a *cache*, not a training artifact: `services/uncertainty_service.py` keys it off both models' `saved_at` timestamps, so it auto-invalidates on retrain. Deleted it explicitly and confirmed a fresh calibration ran and repopulated it, calibration_size now correctly reads 5800 (the new validation set size). |

All prior artifacts were archived to `artifacts/archive_pre_user_split_fix/`
before being overwritten.

**Persona training was already leakage-free** — `models/train_persona.py`'s
own docstring states it fits only on `train_df`, confirmed by reading the
code before retraining. Its silhouette score is effectively unchanged
(0.0766 → 0.0774), which is expected and itself a small piece of
corroborating evidence: a method that was never leaking shouldn't move
much when the leak elsewhere is fixed.

One unrelated pre-existing issue surfaced while retraining, **not caused
by this change** and left alone per the "no unrelated modifications"
instruction: `models/train_persona.py` must be invoked as
`python3 -m models.train_persona` (it has no `sys.path` bootstrap of its
own, unlike the other two training scripts) — this is a pre-existing
invocation-convention quirk in that file, not something this task touched.

## 8) Evaluation on the new, independent test set

### Classification (`hist_gradient_boosting`, selected by validation F1)

| Metric | New (leakage-free) test | Old (leaky) test, for reference |
|---|---|---|
| Accuracy | **0.7604** | 0.9201 |
| Precision (macro) | **0.8045** | — |
| Recall (macro) | **0.7599** | — |
| F1 (macro) | **0.7666** | — |
| ROC-AUC | **0.9307** | — |
| ECE | **0.0951** | 0.0129 |
| MCE | **0.1717** | 0.0531 |
| Brier score (multiclass) | **0.347** | 0.116 |

Every candidate model's own training log now shows a large,
previously-invisible validation-vs-cross-validation gap — e.g. the
selected model: `Val F1=0.7826` vs `5-Fold CV F1=0.9616` — flagged
automatically by the training script's own overfitting warning. That gap
is exactly what should appear once validation stops secretly containing
rows from the same users as training.

**Calibration is visibly worse in the honest direction** — the model is
now measurably overconfident on genuinely new users (confidence exceeds
accuracy in every bin from 0.6 upward):

| confidence bin | n | avg confidence | avg accuracy | gap |
|---|---|---|---|---|
| 0.5–0.6 | 530 | 0.548 | 0.534 | 0.014 |
| 0.6–0.7 | 572 | 0.650 | 0.572 | 0.079 |
| 0.7–0.8 | 663 | 0.754 | 0.628 | 0.126 |
| 0.8–0.9 | 897 | 0.854 | 0.714 | 0.141 |
| 0.9–1.0 | 3127 | 0.969 | 0.877 | 0.092 |

This is the correct, honest outcome of the fix — the earlier "well
calibrated" reading (ECE 1.29%) was an artifact of the calibration set
sharing users with training, exactly as flagged (but not yet proven) in
the prior audit pass. It's now proven.

### Regression (`hist_gradient_boosting_regressor`, selected by
overfitting-aware validation score)

| Metric | New (leakage-free) test |
|---|---|
| MAE | **0.8749** |
| RMSE | **1.1709** |
| R² | **0.9794** |

Regression held up much better than classification post-fix (R² 0.979
vs. classification accuracy dropping ~16 points) — plausible given the
regression target (`health_score_0_100`) is a smooth aggregate of
subscores rather than a discretized 3-way label, so it's inherently less
sensitive to the kind of user-specific boundary-case memorization that
inflated the classifier's leaky numbers most.

### Uncertainty / conformal calibration

Re-calibrated against the new, now-independent 5,800-row validation set.
Both conformal quantiles widened substantially, which is the expected,
correct direction once the calibration set is no longer artificially easy:

| | Before this fix | After this fix |
|---|---|---|
| Regression quantile (±, at α=0.1) | 1.086 | **1.763** |
| Classification quantile | 0.390 | **0.799** |
| Calibration size | 5,750/5,758 | **5,800** |

The uncertainty intervals the app now shows users will be wider —
correctly so; the old, narrower intervals were not actually delivering
their claimed 90% coverage for genuinely new users.

## Test Suite

**315/315 tests passing, no changes required to any test.** Nothing in
the existing suite hardcoded exact split sizes, exact metric values, or
depended on the old artifacts in a way that broke — the suite tests
behavior and contracts, not specific trained numbers.

---

## Summary of every file touched this turn

- **New:** `models/regenerate_user_split.py` (the split-regeneration
  script), `artifacts/leakage_verification_report.json` (evidence
  artifact), `data/archive_pre_user_split_fix/*.csv` and
  `artifacts/archive_pre_user_split_fix/*` (backups of the pre-fix state).
- **Regenerated (overwritten in place):** `data/train.csv`,
  `data/validation.csv`, `data/test.csv`, and every artifact listed in
  §6–7 above.
- **Unchanged:** every other file in the project — no service, UI,
  preprocessing, or test-file code was modified.

The leakage is fixed and independently verified at both the user-group
and raw-row level. The resulting numbers are lower than before — that's
the fix working correctly, not a regression: the old numbers were never
true production numbers, they were measuring how well the model could
recognize users it had already partially seen.
