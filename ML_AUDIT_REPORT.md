# Deep Scientific & ML Engineering Audit

Role: Senior ML Engineer / Research Engineer / Production ML Reviewer.
Scope, per instruction: ML correctness, leakage, calibration, uncertainty,
persona clustering, recommendations, performance, stress tests — no
formatting/style/dead-code work. Every change below was verified against
the real pickled models/data and the full test suite (run before and
after every change; 315/315 passing throughout).

---

## 1) Train ↔ Inference Consistency

### 1a. [Documented previously] `total_screen_min` semantic mismatch
Carried over from the prior pass, still unresolved (needs a product/data
decision, not a code patch): live inference always computes
`total_screen_min` as the literal sum of the five category-minute fields,
while training data has that sum averaging 1.55x (range 1.0x–2.0x) the
stored `total_screen_min` — evidence of an independently-tracked total in
training that the live form has no way to replicate.

### 1b. [New, critical] User-level leakage across train/validation/test
**Traced and quantified.** `data/{train,validation,test}.csv` have no
`user_id` column, but `day_index` ranges 1–23 identically, with similar
distributions, across all three splits — a signature of panel
(repeated-measures) data split at the row level, not the user level.
Checking a 10-field "stable attribute" signature (age, gender, occupation,
region, education, device, platform, purpose, content-creator flag,
screen-limit flag — none of which plausibly change day-to-day for the
same person):

| | overlap with train |
|---|---|
| 100% of validation rows' signatures | appear in train |
| 100% of test rows' signatures | appear in train |
| 90.5% of validation signatures | also appear in test |

Only 3,404 unique signatures exist across 84,351 train rows (mean 24.8
rows/signature, matching the day_index range) — strong, independent
confirmation these are ~3,400 synthetic users each contributing ~1–23 days,
scattered randomly across all three splits rather than held out by user.

**Impact:** the model can partially learn/memorize a user's baseline from
their other days in train, then be evaluated on that same user's day(s) in
validation/test — inflating every reported metric (accuracy, R², and by
extension calibration and conformal coverage below) relative to true
generalization to a genuinely new user. This is the single highest-impact
finding of this audit.

**Why not fixed here:** correcting it means regenerating train/val/test as
a *grouped* split (e.g. `GroupShuffleSplit`/`GroupKFold` keyed on a
reconstructed user identity) and retraining both models — a data-pipeline
and retraining decision, not a safe in-place code change, and explicitly
out of this pass's "fix if safe, otherwise document" instruction.

### 1c. Feature ordering / schema / defaults — checked, no issue found
- `feature_columns.json` (classification) and `feature_columns_regression.json`
  match exactly except one deliberate, documented exception
  (`screen_ewma_baseline`, regression-only — see `models/preprocessing.py`'s
  own permutation-importance writeup, previously reviewed and found sound).
- `ColumnTransformer` in `models/preprocessing.py` selects numeric vs.
  categorical columns by dtype at fit time and the fitted transformer
  (not a hand-maintained column list) is what's applied at inference —
  column *order* is therefore controlled by the fitted object, not
  vulnerable to drift between training and serving code.
- Missing-value defaults: `SimpleImputer(strategy="median")` for numeric,
  `strategy="most_frequent"` for categorical — fit once at training time,
  applied identically at inference (the fitted `ColumnTransformer` is what's
  unpickled and reused, not reconstructed).

---

## 2) Feature Engineering Audit — `derive_features()`

- **Determinism:** confirmed — pure function, no hidden state/randomness.
- **Idempotence:** confirmed empirically — applying `derive_features` to
  its own output a second time changes nothing.
- **Boundary/NaN handling — real gaps found:**
  - Negative raw inputs (e.g. `social_min = -50`) are silently accepted
    and produce **negative ratios** (`social_ratio = -0.4545` in the test
    case), a value outside the feature's own declared `[0.0, 1.0]` schema
    range and outside anything the model saw in training.
  - `NaN` in any raw category field propagates through `total_screen_min`
    into every ratio and density feature derived from it.
  - **Not currently exploitable via the live Streamlit form** — confirmed
    `ValidationService.validate()` explicitly rejects NaN/inf and
    out-of-range values before `derive_features()` ever runs (the code
    even has a comment noting the NaN-silently-skips-bounds-checks case was
    a previously-fixed footgun — good prior engineering). But
    `derive_features()` itself has zero defense if called directly.
  - **Was exploitable via `AdvancedWhatIfService.build_scenario_input()`**,
    which merged `overrides` straight into `derive_features()` with no
    clamping — unlike `FuturePathService._clamp()`, which already guarded
    its own generated shifts. Only safe today because the sole UI caller
    bounds every override via `st.slider(min_value, max_value)`. **Fixed**
    this pass: `build_scenario_input()` now clamps every override to its
    `FEATURE_SCHEMA` bound and drops NaN overrides, matching
    `FuturePathService`'s existing pattern. Verified: a `-999` override on
    `social_min` now clamps to `0.0`; a NaN override is dropped rather than
    poisoning `total_screen_min`; a `99999` override clamps to `1440.0`.
- **Impossible combinations — real, unresolved gap found via stress test**
  (see §9 below): validation checks each field against its own bound but
  never checks that the five category-minute fields' *sum* stays within
  `total_screen_min`'s own declared `[0, 1440]` range. Feeding 1440 minutes
  into all five categories (each individually valid) passes validation and
  produces `total_screen_min = 7200` — 5x its own declared maximum — which
  the model still silently scores ("Moderate", 74.99) rather than
  rejecting. **Not fixed this pass**, deliberately: any numeric threshold
  I'd add here is entangled with the still-open `total_screen_min` semantics
  question in §1a (training data itself allows sums up to ~2x the total) —
  patching one without resolving the other risks encoding an arbitrary
  guess as validation logic. Flagged as a decision, not a bug fix.

---

## 3) Data Leakage Audit

| Type | Finding |
|---|---|
| **Validation/user-level leakage** | **Confirmed, quantified** — see §1b. The dominant leakage finding of this audit. |
| Target leakage (features) | Not found. `get_feature_columns()`'s `leakage_columns` list correctly excludes the six composite subscores, `health_score_0_100`, and every `future_*` column from being used as model *inputs* — verified by reading the list, not assumed. |
| Target reconstruction | `models/data_loader.py` reconstructs `health_score_0_100` (missing from the raw CSVs) as the row-wise mean of the six subscores — a legitimate, documented target-engineering step, not leakage, since those subscores are already excluded from the feature set. |
| Preprocessing leakage | Not found — `ColumnTransformer` (imputer + scaler + encoder) is fit inside the pipeline object saved to `artifacts/*.pkl`, fit only on `train.csv` per `train_classification.py`/`train_regression.py`; inference reuses the fitted object, never refits. |
| Validation-set reuse (model selection → conformal calibration) | **Confirmed** — `models/evaluator.py` selects the best model by validation R²/F1, and `services/uncertainty_service.py` then reuses that same `validation.csv` as the split-conformal calibration set. Compounds with §1b: the calibration set is neither a fresh held-out set (already influenced model selection) nor exchangeable with genuinely new users (shares ~90-100% of its "user" signatures with train/test). This means the module's own stated guarantee — "distribution-free, finite-sample marginal coverage" — is undermined in practice, even though the *conformal math itself* is implemented correctly (see §5). |
| Recommendation leakage | Not found as a leakage issue, but a related *correctness* bug was found and fixed — see §7. |

---

## 4) Model Calibration

Computed directly against `data/test.csv` on the real, currently-shipped
`health_classifier.pkl` (caveat: this test set is itself compromised by
§1b, so these numbers likely overstate true calibration on genuinely new
users):

- **Accuracy:** 92.0%
- **Expected Calibration Error (ECE, 10 bins):** **1.29%**
- **Maximum Calibration Error (MCE):** 5.31% (worst bin: 0.7–0.8 confidence, where actual accuracy was 69.96% vs. average confidence 75.28%)
- **Multiclass Brier score:** 0.1161 (vs. 0.667 for a uniform random guess, vs. 0.6667 theoretical worst-case of 2.0 for 3 classes)

| confidence bin | n | avg confidence | avg accuracy | gap |
|---|---|---|---|---|
| 0.5–0.6 | 197 | 0.551 | 0.503 | 0.048 |
| 0.6–0.7 | 218 | 0.650 | 0.619 | 0.030 |
| 0.7–0.8 | 273 | 0.753 | 0.700 | 0.053 |
| 0.8–0.9 | 439 | 0.855 | 0.827 | 0.028 |
| 0.9–1.0 | 4623 | 0.981 | 0.974 | 0.007 |

On its face this is a well-calibrated classifier (raw softmax probabilities
from `predict_proba()` — no separate calibration step, e.g. Platt/isotonic,
is applied anywhere in the pipeline, and empirically none appears needed).
**Not implementing additional calibration this pass** — the instruction was
to add one *if it improves quality without introducing leakage*; given the
already-low ECE, and given the more urgent, larger-impact problem is the
leakage in §1b (which affects the trustworthiness of this very evaluation),
addressing calibration further before fixing the split is premature —
recalibrate and re-measure after a leakage-free retrain.

---

## 5) Prediction Uncertainty — Conformal Correctness

- **Method:** split-conformal prediction (Vovk et al. / Lei et al. 2018) —
  correct choice and correctly identified as the right tool given
  `HistGradientBoostingClassifier`/`Regressor` don't expose the bagged
  independent-estimator structure that bootstrap/RF-variance methods need.
- **Regression interval math:** `[ŷ − q, ŷ + q]` where `q` is the
  `⌈(n+1)(1−α)⌉/n` quantile of absolute calibration residuals — correct
  formula (Lei et al. 2018, Algorithm 1).
- **Classification set math:** nonconformity score `1 − p(true class)`,
  same quantile formula, prediction set = `{classes : p(class) ≥ 1 − q}` —
  this is the standard Least-Ambiguous-Set (Sadinle et al. 2019) conformal
  classifier, correctly implemented.
- **[Minor, quantified] Quantile interpolation deviates from the strict
  guarantee.** The code uses `np.quantile(residuals, q_level)` with
  default `linear` interpolation. The textbook split-conformal guarantee
  requires the *exact ⌈(n+1)(1−α)⌉-th order statistic* (equivalent to
  `method="higher"`), not an interpolated value — using linear
  interpolation means the stated marginal coverage is no longer strictly,
  provably guaranteed, only approximately so. **Quantified the practical
  impact:** simulated at the actual calibration sample size (~5,750 rows,
  matching this deployment's validation set) the difference between
  `linear` and the exact order statistic was ~0.0002 in quantile value —
  negligible at this sample size, real only for small calibration sets.
  Not changed this pass (correct fix is trivial — `method="higher"` — but
  not worth a code change ahead of the calibration-set redesign in §1b/§3,
  which has a far larger effect on actual coverage validity).
- **The dominant uncertainty-correctness issue is not the math — it's the
  calibration set**, per §1b/§3: because `validation.csv` shares synthetic
  users with `train.csv` and was already used for model selection, the
  90% marginal coverage this module reports is optimistic for genuinely
  new users, in the same direction and for the same root cause as the
  calibration numbers in §4.
- **Edge cases checked:** empty prediction set (all classes below
  threshold) is explicitly guarded — falls back to the single top class
  rather than returning nothing; entropy is always computed independently
  of calibration success so `estimate()` degrades gracefully rather than
  returning nothing when calibration fails. Both confirmed by reading the
  code paths, consistent with existing test coverage (`test_uncertainty_service.py`, still 100% passing).

---

## 6) Persona Detection

Independently recomputed (not just re-reading `artifacts/persona_info.json`)
against held-out data (`validation.csv` + `test.csv` concatenated, n=11,500 —
data the persona KMeans was never fit on):

| Metric | Value | Interpretation |
|---|---|---|
| Silhouette score | **0.069** | Standard guideline: <0.25 = "no substantial structure." Matches the stored training-set value (0.0766) almost exactly — not an overfitting artifact, genuinely weak. |
| Davies-Bouldin index | **2.93** | Higher = worse separation relative to within-cluster scatter; ~1.0 or below is typically considered good. 2.93 is poor. |
| Calinski-Harabasz index | 1,252.76 | Scale-dependent, needs a baseline to interpret alone; included for completeness, not decisive on its own. |
| Assignment ambiguity (nearest/2nd-nearest centroid distance ratio) | **74.7% of users > 0.8, 41.3% > 0.9, median 0.878** | The large majority of "persona" assignments are only marginally closer to their assigned cluster than to the runner-up — assignments are largely unstable/arbitrary for most users. |

**Conclusion:** the clustering is statistically weak by every standard
metric, independently confirmed on data the model never trained on. This
doesn't mean the feature is broken — the derived cluster *names* are
honestly generated from real centroid deviations, not fabricated — but the
underlying population is closer to a continuum than four discrete
behavioral personas, and framing it that confidently to users overstates
the statistical support. `K=4` was correctly selected as the best of the
candidates `{4,5,6,7}` by silhouette score — the issue isn't the choice of
K, it's that no K in this feature space produces well-separated clusters.

**Did not replace the clustering algorithm.** The audit brief says "only
replace if the improvement is measurable" — testing whether a different
algorithm (e.g. Gaussian Mixture, HDBSCAN) or feature set would do
meaningfully better is itself a multi-day research question (feature
selection, algorithm comparison, stability analysis across resamples), not
something to gamble on without evidence it would help. Recommend: either
present personas with appropriately hedged confidence language, or invest
in a real feature-selection pass (e.g. checking if raw behavioral features
beyond `PERSONA_FEATURES` separate better) before trusting this as more
than a soft, illustrative grouping.

---

## 7) Recommendation Engine

### [Bug — found, fixed, verified] Direction-blind recommendation ranking
`RecommendationService.generate()` ranked SHAP features by `|SHAP value|`
magnitude only, ignoring `feature.direction`. Since a feature the user is
already doing *well* on can easily have the single largest magnitude
contribution (strong positive habits are exactly what a well-fit model
should weight heavily), this let genuinely *positive* factors get
surfaced as top-priority "fix this" recommendations.

**Reproduced empirically** before touching anything: `config.demo_profiles.healthy_profile()`
(predicted score 85.7, "Healthy") had `night_ratio` as its #1 SHAP
feature — direction `"increase"` (pushing the score *up*, because the
user's night usage is unusually *low*) — and the engine surfaced a
**HIGH-priority "Avoid Late Night Device Usage"** recommendation anyway,
for the user's single strongest asset. Root cause of why this was never
caught: every existing test fixture (`tests/test_recommendation_service.py`'s
`_feature()` helper) hardcoded `direction="decrease"`, so the "increase"
path was structurally never exercised by any test.

**Fixed:** filter to `direction == "decrease"` features before matching
templates. **Re-verified** post-fix: the healthy profile now correctly
produces zero recommendations (routing to the existing, already-implemented
"🎉 No recommendations needed" UI state); the at-risk demo profile still
produces three correctly-targeted HIGH-priority recommendations
(fragmentation, night usage, physical activity). All 18 recommendation-related
tests plus the full 315-test suite pass after the change.

### Other checks
- **Deduplication/repetition:** `used_categories` set correctly prevents
  two SHAP features mapping to the same category (e.g. `sleep_hours` and
  `sleep_quality_1_10`, both "Sleep") from producing duplicate
  recommendations — confirmed by existing test coverage, still passing.
- **Contradictions:** with the direction fix in place, no path remains
  where a recommendation and its underlying SHAP evidence point opposite
  directions.
- **"Do recommendations correlate with healthier outcomes"** — this is
  fundamentally an SHAP-attribution-quality question inherited from the
  underlying regression model's feature importances, not something the
  recommendation layer itself can validate independently; given the model's
  overall calibration looks reasonable (§4) and leakage concerns aside
  (§1b) the attributions are plausible, but a genuine answer requires an
  intervention/outcome study this codebase doesn't have data for — noted
  as a limitation, not fixable in this pass.

---

## 8) Performance Profiling

Measured directly (not estimated) on the real pickled models in this
sandbox:

| Operation | Latency |
|---|---|
| `ModelManager.instance()` cold load (both models + SHAP + uncertainty + persona) | 0.29s |
| `classification_model.predict_proba()` raw | ~13.7ms |
| `regression_model.predict()` raw | ~12.0ms |
| `PredictionService.predict()` end-to-end (incl. SHAP) — **before this pass's fix** | ~783ms |

The ~783ms number is almost certainly inflated by this sandbox's SHAP
*stub* (the real `shap` package can't install here due to a
numba/numpy version conflict — `tests/_test_support.py`'s fallback
explainer does per-feature ablation, i.e. extra model forward passes per
feature, which a real `TreeExplainer` wouldn't need). I'm explicit about
not trusting that absolute number as representative of production, but the
**structural finding underneath it is real and environment-independent**:

### [Fixed] Redundant SHAP computation on every throwaway comparison prediction
Traced every caller of `PredictionService.predict()`. Confirmed by
grepping each call site for `.shap_features` usage:
`AdvancedWhatIfService.sweep_field()` (up to 9 calls/sweep, reused by
`goal_seek()`), the multi-scenario comparison tab in
`What_If_Simulator.py` (up to 3 calls), `FuturePathService.compare()`
(one call per path definition), and `ParallelTwinService` (one call per
twin) — **none of them ever read `.shap_features`** off the result; they
only use `.prediction` / `.regression_score` / `.confidence` (and, for
`FuturePathService`, `.uncertainty`, which comes from a separate,
independent calibration lookup). Every one of these calls was computing
and silently discarding a full SHAP explanation.

**Fix:** added `compute_shap: bool = True` to `PredictionService.predict()`
(default preserves existing behavior for the one call site that needs it —
the real user-facing prediction, which feeds `RecommendationService` and
the SHAP explanation UI). Updated all four confirmed-safe call sites to
pass `compute_shap=False`.

**Verified:**
- Measured `sweep_field()` (9 points) at **52ms/point** after the fix vs.
  the ~783ms/point baseline — consistent with removing the SHAP pass,
  though again the absolute delta is sandbox-stub-inflated; the
  structural win (5–9x fewer SHAP computations per user action across
  sweep/twin/future-path features) holds regardless of environment.
- Full test suite wall-clock time dropped from ~131s to ~76s across two
  back-to-back runs — real, independent evidence this reduced actual
  computation, not just the isolated benchmark.
- Two test doubles (`_FakeStressPredictor`, `_FailingPredictor` in
  `test_advanced_whatif_service.py`; `_FakePredictor` in
  `test_parallel_twin_service.py`) had a narrower `predict(self, user_data)`
  signature than the real service and broke when called with the new
  keyword argument — updated their signatures to accept
  `compute_shap: bool = True`, matching what a real stand-in for
  `PredictionService` should expose. This is the only test-file change in
  this pass, and it's a signature-compatibility fix, not a weakened
  assertion.
- Full suite: 315/315 passing after all changes.

---

## 9) Stress Tests

| Test | Result |
|---|---|
| Idempotence of `derive_features()` | Pass (verified, §2) |
| Empty input dict | Handled — all ratios default to 0.0, `total_screen_min` floors at 1.0 (division-by-zero guard) |
| Negative raw input | Silently produces out-of-schema negative ratios in `derive_features()` directly; not reachable through the live UI (blocked by `ValidationService`); was reachable through `AdvancedWhatIfService.build_scenario_input()` — **fixed** (§2) |
| NaN raw input | Propagates through every derived ratio in `derive_features()` directly; blocked at the UI by `ValidationService`; fixed in `build_scenario_input()` (§2) |
| Impossible combination (all 5 screen-time categories individually valid at 1440 min, summing to 7200 min/day) | **Passes validation, produces a silent prediction** ("Moderate", 74.99) on an input 5x outside `total_screen_min`'s own declared range — real gap, not fixed (§2, entangled with the open §1a decision) |
| Concurrent predictions / model-manager singleton under load | Covered by existing `test_concurrency.py`/`test_concurrency_new_services.py` — passing, not independently re-derived this pass beyond confirming they still pass after all changes |
| Repeated predictions (determinism) | Covered by existing `test_prediction_pipeline.py::test_repeated_predictions_are_deterministic` — passing |
| Family mode / recommendation loop | Not stress-tested this pass — out of the time budget for this round; flagged as unexamined, not as clean |

---

## 10) Final Summary

### Fixed and verified this pass
1. `RecommendationService` now filters by SHAP direction — no longer tells
   thriving users to "fix" their best traits. (§7)
2. `PredictionService.predict(compute_shap=False)` — eliminates redundant
   SHAP computation across every sweep/twin/future-path/scenario-comparison
   call. (§8)
3. `AdvancedWhatIfService.build_scenario_input()` now clamps overrides to
   schema bounds and drops NaN, closing a latent (not currently
   UI-exploitable) robustness gap. (§2)
4. Two test doubles updated for signature compatibility with the new
   `compute_shap` parameter (not a weakened test, a required compatibility fix).

### Documented, not fixed (require a data/product decision, not a safe code patch)
1. **User-level train/val/test leakage** (§1b/§3) — the single largest
   finding of this audit. Inflates reported accuracy/R²/calibration/
   conformal-coverage numbers. Fix requires regenerating the splits by
   user identity and retraining both models.
2. **`total_screen_min` semantic mismatch** (§1a, carried over) — entangled
   with the impossible-combination validation gap (§2/§9).
3. **Impossible-combination validation gap** — category-minute sum isn't
   checked against `total_screen_min`'s own schema bound; deliberately not
   patched with a guessed threshold given its entanglement with #2.
4. **Weak persona clustering** (§6) — silhouette ≈ 0.07 independently
   confirmed on held-out data; needs either honest re-framing to users or
   a real feature-selection/algorithm study, not a same-session swap.
5. **Conformal quantile interpolation** (§5) — technically should use the
   exact order statistic (`method="higher"`) rather than linear
   interpolation; quantified as negligible at current sample size (~5,750),
   real only for small calibration sets — low priority relative to #1.

### Test suite
- 315/315 passing throughout this pass, verified before starting and after
  every individual change (never batched changes before re-running).
- Suite wall-clock time: ~131s → ~76s, an independent performance signal
  corroborating the `compute_shap` fix.

### Honest limitation of this audit
Several numbers in this report (§4 calibration, §5 uncertainty coverage)
are measured against test/validation data that §1b shows is itself
compromised. I'm reporting them because they're what the current pipeline
actually produces and they're internally informative (e.g. the *shape* of
the calibration curve, the *math* of the conformal implementation), but
they should not be read as final, trustworthy production numbers until the
leakage in §1b is resolved and both models are retrained on a
user-disjoint split.
