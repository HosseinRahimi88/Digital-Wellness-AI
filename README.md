# Digital Wellness AI — Final Technical Audit Report

**Scope:** Full audit, bug fixes, retraining (where required), and
production-readiness pass on the existing modular project (classification +
regression pipelines, Streamlit app, SHAP, PDF reports, recommendation
engine).

**Important correction to the starting assumptions:** the brief stated that
the regression-target and feature-mismatch issues had *already* been fixed
in a previous session. On inspection, **neither fix was actually present in
the code** — this audit found both bugs still fully active, fixed them, and
retrained from scratch to get real (not assumed) numbers. Every metric in
this report comes from an actual training run performed during this audit;
none are carried over from the brief.

---

## 1. Bugs found and fixed

### 🔴 Critical — Regression target did not exist anywhere
`health_score_0_100` (the regression target in
`models/preprocessing.py:TARGET_COLUMNS`) was not a column in `train.csv`,
`validation.csv`, `test.csv`, or `digital_wellness_feature_engineered_full.csv`,
and no code anywhere reconstructed it. As shipped, `train_regression.py`
crashed immediately with `KeyError`, and there were **no trained model
artifacts at all** in the project (no `artifacts/` folder).

**Fix:** Added `_reconstruct_health_score()` to `models/data_loader.py`,
which derives `health_score_0_100` as the row-wise mean of the six existing
composite subscores (`sleep_subscore`, `night_subscore`, `focus_subscore`,
`balance_subscore`, `stress_fatigue_subscore`, `activity_context_subscore`),
clipped to [0, 100], and wired it into `load_datasets()` so every consumer
sees it consistently. This reconstruction was validated before use: the mean
of the six subscores separates the three `future_health_class_7d` classes
cleanly (≈55 for At Risk, ≈64 for Moderate, ≈72 for Healthy on a 20k-row
sample), confirming it's a sound stand-in for the missing target rather than
an arbitrary guess.
**File modified:** `models/data_loader.py`.
**Retraining:** required and performed.

### 🔴 Critical — Feature mismatch bug was still live (not actually fixed)
`recovery_index`, `cognitive_load`, `screen_addiction_index`, and
`night_usage_burden` still exist as raw columns in every CSV, and
`models/preprocessing.py`'s leakage-exclusion list only excluded the six
subscores — **not** these four. `get_feature_columns()` was still returning
62 columns (58 real form fields + these 4), while `FEATURE_SCHEMA` and the
Streamlit form (`FormGenerator`) only ever supply 58. At inference time
those 4 would arrive missing and get silently zero-filled by
`PredictionService`, biasing every prediction — exactly the failure mode
described (but not actually resolved) in the existing code comments.

**Fix:** Added all four to the `leakage_columns` list in
`models/preprocessing.py`, with a comment documenting why (mirrors the
existing subscore-exclusion comment style already in the file).
**File modified:** `models/preprocessing.py`.
**Retraining:** required and performed.

Verified after the fix: `get_feature_columns()` now returns exactly 58
columns, and they match `core/feature_schema.py`'s `FEATURE_SCHEMA` keys
1:1 (0 missing on either side) — confirmed programmatically, not just by
inspection.

### 🟠 High — AI Coach was 100% static/mock content (confirmed)
`app/pages/AI_Coach.py` rendered four hardcoded `RecommendationCard`s
regardless of the user, with zero calls into `PredictionService`,
`RecommendationService`, or any session state. The previous reviewer's
suspicion was correct.

**Fix:** `Prediction.py` now stores the real `PredictionResult` and
generated `Recommendation` list in `st.session_state` after a successful
prediction. `AI_Coach.py` was rewritten to read that session state and
render the user's actual SHAP-driven recommendations and wellness status;
if no prediction has been run yet in the session, it shows an honest empty
state with a button to go run one, instead of fabricated advice.
**Files modified:** `app/pages/Prediction.py`, `app/pages/AI_Coach.py`.
**Retraining:** not required (app-layer wiring only).

### 🟡 Medium — Regression output was computed but never shown
`PredictionService.predict()` always computes `regression_score`, but the
Prediction page never displayed it — the entire regression pipeline's
output was silently discarded from the UI.
**Fix:** Added a "Wellness Score" metric card to the prediction result
layout (now 5 metric columns).
**File modified:** `app/pages/Prediction.py`.

### 🟡 Medium — Model Performance page had no regression section + wrong path in error text
The page only showed classification metrics, and its "no model found"
message pointed to `saved_models/metrics.json`, which has never been a real
path — `model_saver.py`/`model_registry.py` both use `artifacts/`.
**Fix:** Added a full regression metrics section (R², MAE, RMSE, best model,
per-candidate validation results) mirroring the classification section, and
corrected the path in both error messages.
**File modified:** `app/pages/Model_Performance.py`.

### 🟡 Medium — Recommendation registry only covered 8 of 58 features
Real end-to-end testing (see §2) showed several features that frequently
rank in the SHAP top-5 (`fragmentation_index_0_100`, `gaming_ratio`,
`night_screen_min`, `productivity_0_100`, `sleep_quality_1_10`) had no
recommendation template, so `RecommendationService.generate()` silently
dropped them — recommendations were sparser than they should be.
**Fix:** Added templates for those five features, in the same style/schema
as the existing entries.
**File modified:** `config/recommendation_registry.py`.

### 🟢 Low — Duplicated code
`models/model_registry.py` computed `self.project_root / "artifacts"` twice
(once into a discarded local variable, once into `self.artifacts_dir`).
**Fix:** removed the redundant line.
**File modified:** `models/model_registry.py`.

### 🟢 Low — Dead code (confirmed zero references, then removed)
- `core/dto.py` — a second, unused `PredictionResult`/`Recommendation`
  definition duplicating `models/schemas.py` / `models/recommendation.py`.
  Never imported anywhere.
- `config/validation_rules.py` — explicitly self-documented in its own
  docstring as unused (validation actually runs against
  `core.feature_schema.FEATURE_SCHEMA`). Never imported anywhere.

Both were verified with a project-wide `grep` for any import before
deletion.

### 🟢 Low — Missing project hygiene files
There was no `requirements.txt` and no `.gitignore` anywhere in the project.
**Fix:** Added both. `requirements.txt` lists exactly the packages actually
imported across the codebase (pandas, numpy, scikit-learn, joblib, xgboost
[optional], shap, streamlit, plotly, reportlab). `.gitignore` excludes
`__pycache__/`, `.streamlit/`, notebook checkpoints, etc.

---

## 2. Prediction page — full simulated test

Since a real browser/Streamlit session isn't available in this environment,
the full pipeline (`ValidationService → PredictionService → SHAPService →
RecommendationService → ReportService`) was exercised directly, in-process,
against the retrained models, for three realistic personas built by hand
(not sampled from the training data) and passed through the *same* derived-
feature logic `FormGenerator` uses:

| Persona | Predicted class | Confidence | Wellness score | Recommendations |
|---|---|---|---|---|
| Healthy-leaning (good sleep, low stress, moderate use) | **Healthy** | 76.9% | 92.1 / 100 | Night usage, stress management |
| Moderate (average habits across the board) | **Moderate** | 48.6% | 62.8 / 100 | Physical activity, night usage |
| At-risk (heavy night use, high stress, poor sleep, low activity) | **At Risk** | 67.7% | 32.2 / 100 | Fragmented checking, night screen time, physical activity |

All three:
- Passed `ValidationService` (including a separate check that out-of-range
  values, invalid categorical choices, and missing required fields are all
  correctly rejected with clear per-field messages, and that the one
  optional field, `operating_system`, is correctly *not* required).
- Produced classification + regression predictions that move sensibly in
  the same direction (e.g. the At Risk persona gets both the "At Risk"
  label and the lowest wellness score, 32.2).
- Produced 5 ranked SHAP features each, with plausible directionality
  (e.g. for the At-risk persona: high fragmentation, high night-screen
  minutes, and low physical activity all push the score down).
- Produced non-empty, relevant recommendations after the registry
  expansion in §1.
- Produced a valid PDF (verified by checking the `%PDF` file signature and
  non-trivial byte count) containing the prediction summary, input
  highlights, and recommendations.

**Sandbox limitation, stated plainly:** this environment has no network
access, so `shap`, `streamlit`, `xgboost`, and `plotly` could not be
`pip install`-ed here. `xgboost` is already handled gracefully by
`model_factory.py` (candidate model list shrinks to sklearn-only models when
it's absent — confirmed by the training logs). For `shap`, a small local
stub package was used purely to exercise the *integration* (does
`SHAPService` get called with the right shapes, do results flow correctly
into `RecommendationService`) — it approximates feature attribution with
simple zero-baseline occlusion, **not** real SHAP's algorithm. The
`SHAPService` code itself (explainer selection, source-column mapping back
through the `ColumnTransformer`, categorical value passthrough) was verified
by careful static review; its numeric output should be checked once in a
real environment with `shap` installed, but the wiring is confirmed sound.
Streamlit page logic (`Prediction.py`, `AI_Coach.py`, `Model_Performance.py`)
was verified by `py_compile` (no syntax errors) and manual trace-through
against the now-verified service layer, but not by actually launching the
Streamlit server.

---

## 3. Services cross-check

| Service | Status |
|---|---|
| `PredictionService` | Verified end-to-end (3 personas above). Class-index → label mapping (`CLASS_MAPPING`) double-checked against `LabelEncoder`'s alphabetical ordering of `["At Risk","Healthy","Moderate"]` → confirms 0/1/2 mapping is correct. |
| `ValidationService` | Verified: required/optional handling, numeric bounds, categorical choice enforcement all correct. |
| `SHAPService` | Wiring verified via stub (see limitation above); source-column reconstruction logic for one-hot-encoded categoricals reviewed and is correct. |
| `RecommendationService` | Verified: correctly deduplicates by category, sorts by priority, respects `top_k`; coverage gap found and fixed (§1). |
| `ReportService` | Verified: produces a well-formed PDF from real `PredictionResult` + recommendation objects for all 3 personas. |
| `ModelRegistry` / `model_saver` | Verified: task-aware filenames (classification vs. regression) don't collide; `validate()` correctly raises `FileNotFoundError` with an accurate path when artifacts are missing. |

---

## 4. Retraining — real results (this session)

Both pipelines were retrained after the fixes above, using the actual
`train.csv` / `validation.csv` / `test.csv` (46,000 / 5,750 / 5,750 rows).
`xgboost` was unavailable in this sandbox (no network access), so the
candidate pool was sklearn-only; `model_factory.py`'s existing
`XGBOOST_AVAILABLE` guard handled this without any code changes.

**Classification** (target: `future_health_class_7d`, 58 features)
- Best model selected: `random_forest` (over `logistic_regression`)
- **Test set:** Accuracy 83.6%, Precision 79.5%, Recall 85.8%, F1 (macro) 81.8%, ROC AUC 96.0%

**Regression** (target: reconstructed `health_score_0_100`, 58 features)
- Best model selected: `linear_regression` (outperformed `random_forest_regressor`
  and `extra_trees_regressor` — expected, since the reconstructed target is
  itself a linear combination of subscore-related signal)
- **Test set:** R² 0.879, MAE 1.89, RMSE 2.35

**On the numbers in the brief:** the classification numbers above
(83.6% / 81.8% / 96.0%) land close to the brief's claimed 84% / 82% / 96%,
which is reassuring. The regression numbers do **not** match the brief's
claimed R²≈97%/MAE≈0.89 — real R² here is 0.879 and MAE is 1.89. Given that
(a) the regression target didn't exist in any file before this session and
(b) no regression artifacts existed to check, the brief's regression numbers
could not be verified and are not carried forward. The 0.879 R² / 1.89 MAE
above are from an actual run in this session, on the corrected (leakage-free)
feature set, and should be treated as the real baseline going forward.

Both artifact sets (`artifacts/health_classifier.pkl`,
`artifacts/health_regressor.pkl`, feature columns, metrics, model info) are
included in the delivered project.

---

## 5. Files modified in this session

- `models/preprocessing.py` — excluded the 4 leaked engineered features
- `models/data_loader.py` — reconstructs `health_score_0_100`
- `models/model_registry.py` — removed duplicated line
- `config/recommendation_registry.py` — added 5 more feature templates
- `app/pages/Prediction.py` — shows wellness score; persists result to session state
- `app/pages/AI_Coach.py` — rewritten to use the real pipeline via session state
- `app/pages/Model_Performance.py` — added regression metrics section, fixed wrong path in error text
- `requirements.txt` — added (new file)
- `.gitignore` — added (new file)
- `core/dto.py` — removed (dead code, zero references)
- `config/validation_rules.py` — removed (dead code, zero references)

## 6. Retraining performed

Yes, both classification and regression pipelines were retrained — required
because the feature-mismatch fix changes the training feature set, and the
regression pipeline had literally never produced a model before this
session (target didn't exist). No unnecessary retraining was done beyond
this.

---

## 7. Final project health score

**8/10 — production-ready with known, documented gaps.**

Reasoning: both critical (previously-unfixed) bugs are now genuinely fixed
and verified with real retraining; the AI Coach mock-data issue is resolved;
all services were exercised together successfully end-to-end. Points held
back for: the SHAP numeric path being verified only by static review (not a
live run) due to sandbox network restrictions, and the remaining lower-
priority items in §8.

## 8. Remaining issues / suggestions before final submission

1. **Run one real training + Streamlit session in an environment with
   network access**, to confirm `xgboost` and real `shap` behave as
   expected (they were structurally verified here but not numerically
   exercised). This is the single most important remaining step.
2. **Analytics page still uses static demo data** (`app/pages/Analytics.py`
   explicitly comments this). It isn't wired to any per-user history store
   because none exists in the project — this is a scope/architecture
   decision, not a bug, but the page should probably say "Sample Data" in
   the UI so it's not mistaken for the current user's real analytics.
3. **`data/digital_wellness_feature_engineered_full.csv` (49 MB) is unused**
   by any code path in the project. It was left in place since it's a data
   file rather than dead code, but it's a strong candidate for removal or
   documentation of its intended purpose before pushing to GitHub.
4. **Recommendation registry still doesn't cover every one of the 58
   features** — only the ones observed in top-5 SHAP rankings during this
   audit's testing were added. Categorical features (e.g. `purpose_group`,
   `primary_platform`) still have no template and likely shouldn't (no
   single universal action applies), but a few more numeric features may
   surface as top drivers for other user profiles and could be added
   opportunistically.
5. **`health_classifier.pkl` is ~31 MB** (300-tree, depth-10 RandomForest).
   Fine for this project's scale, but worth knowing if deploying somewhere
   with a small cold-start budget.
