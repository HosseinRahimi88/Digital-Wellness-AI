# User-Level Leakage Fix — Final Report

Scope: strictly the train/validation/test user-leakage issue documented in
`ML_AUDIT_REPORT.md` §1b/§3. No other code, UI, or service was touched
except where retraining/cache-invalidation required it (none did — see
"What was NOT touched" below).

---

## 1) How user identity was reconstructed

No `user_id` (or any row-identity column) exists in `data/*.csv`, and no
data-generation script exists anywhere in this repo to regenerate one from
— confirmed by search. So a group key had to be reconstructed from the
existing columns.

**Key used:** the 10 fields that are demographically stable for a real
person across their diary of days — `age, gender, occupation_group,
region_group, education_group, device_category, primary_platform,
purpose_group, is_content_creator, uses_screen_time_limits`.

**Why this is a safe reconstruction, not a guess:** `age` was confirmed to
be a clean integer with no day-to-day jitter, and the other 9 fields are
categorical demographic buckets that have no reason to change day-to-day
for the same person. That means this key can only ever **over-group**
(merge two different people who happen to share all 10 fields into one
group — confirmed this happens for ~42% of signatures, since these are
coarse categorical buckets, not a real ID) — it can never **under-group**
(split one real person's rows into two different groups). Over-grouping is
the safe failure direction for a leakage fix: it can only make the
resulting groups coarser than true individuals, never allow a real
person's rows to end up split across train/val/test. Full reasoning is in
the header docstring of `models/regenerate_user_split.py`.

---

## 2) How the new split was generated

`models/regenerate_user_split.py` (new file — the only new file this pass
added):
1. Pools the existing `train.csv` + `validation.csv` + `test.csv` (104,469 rows total).
2. Builds the group key above (3,404 unique groups).
3. Runs `sklearn.model_selection.StratifiedGroupKFold(n_splits=18, shuffle=True, random_state=42)`.
   Fold 0's held-out portion → new test set. Fold 1's held-out portion →
   new validation set. The remaining 16 folds → new train set. K-fold
   folds are a true partition by construction, so this guarantees
   zero group overlap between all three splits — not by hoping, by the
   algorithm's own guarantee, and it's asserted in code before any file
   is written.
4. Archives the original three CSVs to `data/archive_pre_user_split_fix/`
   before overwriting `data/{train,validation,test}.csv` in place.
5. Writes `artifacts/leakage_verification_report.json`.

Why `n_splits=18`: 1/18 ≈ 5.56% per fold, matching the original split's
~89.0% / 5.5% / 5.5% ratios (requirement: preserve approximately the
current ratios).

---

## 3) Leakage verification — evidence

Directly from `artifacts/leakage_verification_report.json` (asserted in
code, not just reported after the fact — the script raises before writing
any file if any of these three assertions fail):

| | Train | Validation | Test |
|---|---|---|---|
| Rows | 92,867 | 5,800 | 5,802 |
| Row share | 88.89% | 5.55% | 5.55% |
| User groups | 3,022 | 191 | 191 |

**Group intersections:**
- Train ∩ Validation = **0**
- Train ∩ Test = **0**
- Validation ∩ Test = **0**

**Class balance preserved** (classification target, `future_health_class_7d`):

| | Train | Validation | Test |
|---|---|---|---|
| At Risk | 33.34% | 33.38% | 33.35% |
| Healthy | 33.01% | 33.03% | 33.02% |
| Moderate | 33.65% | 33.59% | 33.63% |

Row counts changed only marginally from the original split (92,867 vs.
92,949 train; 5,800 vs. 5,758 validation; 5,802 vs. 5,762 test) — the new
split is group-constrained, not row-constrained, so exact row counts per
split can't be hit precisely, but they land within ~0.1% of the originals.

---

## 4) What was retrained

All three artifacts that depend on `data/train.csv`/`validation.csv` were
retrained from the new split, using the existing, **unmodified** training
scripts (`train_classification.py`, `train_regression.py`,
`train_persona.py` — no changes to any of them):

- `artifacts/health_classifier.pkl` + `feature_columns.json` + `model_info.json` + `metrics.json`
- `artifacts/health_regressor.pkl` + `feature_columns_regression.json` + `model_info_regression.json` + `metrics_regression.json`
- `artifacts/persona_model.pkl` + `persona_info.json`

**`artifacts/uncertainty_calibration.json`** did not need a code change —
it's a cache file keyed by a hash of both models' `saved_at` timestamps
(`services/uncertainty_service.py`'s existing, pre-built cache-invalidation
logic). I deleted the stale file and confirmed it regenerated automatically
against the new `validation.csv` on first load (`calibration_size: 5800`,
matching the new validation set exactly).

All previous artifacts were archived to `artifacts/archive_pre_user_split_fix/`
before being overwritten.

### What was NOT touched
No service, page, or component code was modified. `cohort_service.py`
(loads `data/train.csv` directly) needed no change — it already reads the
file fresh via its own `lru_cache`, so it picked up the new split
automatically. No test file needed a fix — the full suite passed
unmodified against the retrained artifacts (see §6).

---

## 5) Evaluation on the new, leakage-free test set

### Classification (`health_classifier.pkl`, `hist_gradient_boosting`)

| Metric | New (leak-free) | Old (leaky) |
|---|---|---|
| Accuracy | 0.7604 | 0.7775 |
| Precision (macro) | 0.8045 | 0.8212 |
| Recall (macro) | 0.7599 | 0.7723 |
| F1 (macro) | 0.7666 | 0.7826 |
| ROC-AUC | 0.9307 | 0.9404 |

Confusion matrix (rows/cols = At Risk, Healthy, Moderate):
```
[1456,    4,  475]
[   0, 1288,  628]
[ 165,  118, 1668]
```

### Regression (`health_regressor.pkl`, `hist_gradient_boosting_regressor`)

| Metric | New (leak-free) | Old (leaky) |
|---|---|---|
| MAE | 0.8749 | 0.5253 |
| RMSE | 1.1709 | 0.6778 |
| R² | 0.9794 | 0.9899 |

### Calibration (computed fresh on the new test set, same method both times: 10-bin reliability, `|confidence − accuracy|`)

| Metric | New (leak-free) | Old (leaky) |
|---|---|---|
| Expected Calibration Error (ECE) | **0.0951** | 0.0129 |
| Maximum Calibration Error (MCE) | **0.1717** | 0.0531 |
| Multiclass Brier score | **0.3470** | 0.1161 |

Reliability table (new test set):

| confidence bin | n | avg confidence | avg accuracy | gap |
|---|---|---|---|---|
| 0.3–0.4 | 3 | 0.393 | 0.333 | 0.059 |
| 0.4–0.5 | 10 | 0.472 | 0.300 | 0.172 |
| 0.5–0.6 | 530 | 0.548 | 0.534 | 0.014 |
| 0.6–0.7 | 572 | 0.650 | 0.572 | 0.079 |
| 0.7–0.8 | 663 | 0.754 | 0.628 | 0.126 |
| 0.8–0.9 | 897 | 0.854 | 0.714 | 0.141 |
| 0.9–1.0 | 3127 | 0.969 | 0.877 | 0.092 |

**This is the most important number in this report.** Point-prediction
metrics (accuracy/F1/R²) barely moved — the model still ranks risk
reasonably well even for genuinely new users. But calibration collapsed:
ECE went from 1.3% to **9.5%**, Brier nearly tripled, and every single
confidence bin is now overconfident (confidence > accuracy everywhere).
This is exactly what the leakage was hiding: the model had partially
learned to recognize *specific users* from training and was
over-trusting its own confidence on their other days in validation/test.
Point accuracy is fairly leakage-robust here because ranking "is this
person trending down" doesn't require memorizing who they are — but
*confidence calibration* is far more sensitive to it, which matters
directly for this app's uncertainty intervals and HIGH/MEDIUM/LOW
recommendation-priority framing, both of which consume these probabilities
directly.

**Not addressed in this pass, by design:** recalibrating the classifier
(e.g. Platt scaling/isotonic regression on the new validation set) would
likely help substantially given the numbers above, but that's a new
change beyond "fix the leakage," per this task's explicit scope. Flagging
it as the natural next step.

### Persona clustering (`persona_model.pkl`)

| Metric | New (leak-free) | Old (leaky) |
|---|---|---|
| Silhouette (K=4, training data) | 0.0774 | 0.0766 |

Essentially unchanged. This confirms the earlier finding from
`ML_AUDIT_REPORT.md` — the weak cluster separation is a genuine property
of this feature space, not an artifact of the leaky split.

---

## 6) Test suite

Full suite run against the retrained artifacts, **no test file modified**:

```
315 passed in 91.43s
```

No test hardcoded exact row counts or specific metric values from the old
split/models, so nothing needed fixing.

---

## 7) Files changed this pass

**New:**
- `models/regenerate_user_split.py` — the split-regeneration script
- `data/archive_pre_user_split_fix/{train,validation,test}.csv` — pre-fix backups
- `artifacts/archive_pre_user_split_fix/*` — pre-fix model/metric backups
- `artifacts/leakage_verification_report.json` — machine-checkable verification evidence

**Regenerated in place (same filenames, new content):**
- `data/{train,validation,test}.csv`
- `artifacts/health_classifier.pkl`, `feature_columns.json`, `model_info.json`, `metrics.json`
- `artifacts/health_regressor.pkl`, `feature_columns_regression.json`, `model_info_regression.json`, `metrics_regression.json`
- `artifacts/persona_model.pkl`, `persona_info.json`
- `artifacts/uncertainty_calibration.json` (auto-regenerated, no code change)

**Unchanged:** every service, page, component, and test file. `requirements.txt`'s
sklearn pin was untouched and correctly still matches (`sklearn_version: "1.8.0"`
in the freshly-written `model_info.json`/`model_info_regression.json`).
