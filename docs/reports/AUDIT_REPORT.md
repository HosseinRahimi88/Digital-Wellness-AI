# Final Architecture & Quality Audit

Scope of this pass: environment/dependency integrity, static dead-code sweep,
storage/concurrency verification, and ML inference-path correctness and
performance. Full test suite run before and after every change.

## Executive Summary

The codebase is, on the whole, well-engineered — the storage layer, the
`ModelManager` singleton, and `AccountService` in particular show real care
around concurrency and race conditions, with comments that correctly explain
*why*, not just *what*. The most serious issue found was not in the
application code but in **dependency pinning**: `requirements.txt` allowed
any `scikit-learn>=1.3`, while the shipped model artifacts are pickled
under 1.8.0 specifically. Under 1.9.0 this breaks **every** prediction path
outright (`ModuleNotFoundError: No module named '_loss'`) — this was
reproduced and is why the baseline test run showed 9 failures + 32 errors
before any other change was made. Fixed by pinning the dependency; all 315
tests pass after.

A real, systematic **train/serve feature mismatch** was also found in how
`total_screen_min` and its derived ratios/densities are computed (see ML
Review below). This is a data/product-level issue, not a code defect — it
was not "fixed" in this pass because doing so correctly requires either
retraining or a deliberate semantic decision, not a silent code change.
It's flagged as the top remaining risk.

Beyond those two, this pass fixed several smaller real bugs (a duplicate
import, dead UI code, a redundant model forward pass, a handful of unused
imports) and confirmed several previously-unverified areas (storage locking,
registration race-safety, ModelManager fan-out) are already correct.

**Production readiness:** the app itself is close to solid pending the
dependency pin fix (now applied). The feature-derivation mismatch is worth
a deliberate decision before this model is trusted for real user guidance,
since it affects prediction quality, not just code cleanliness.

---

## Issues Found & Fixed

### 1. [Critical] Unpinned `scikit-learn` breaks every prediction on a routine `pip install`
- **File:** `requirements.txt`
- **Evidence:** `artifacts/model_info.json` records `"sklearn_version": "1.8.0"`. Installing `scikit-learn>=1.3` today resolves to 1.9.0, and unpickling any `artifacts/*.pkl` then raises `ModuleNotFoundError: No module named '_loss'` (an internal sklearn module path that moved between 1.8 and 1.9). Reproduced directly; this was the root cause of 9 failed + 32 errored tests in the pre-fix baseline.
- **Fix:** Pinned `scikit-learn==1.8.0` with a comment explaining the pickle-compatibility constraint and what to do if artifacts are ever retrained under a newer version.
- **Verification:** Full suite: 315 passed (was 274 passed / 9 failed / 32 errored).

### 2. [Bug] Duplicate import in `core/dto.py`
- `from dataclasses import dataclass` was imported twice (harmless but a real duplicate-import bug pyflakes flagged). Removed the redundant line.

### 3. [Bug] Dead code hiding a missing UI feature — `legacy/streamlit_app/components/improvement_chain.py`
- The component built `day_labels_html` (day-of-week labels meant to sit under the progress chain) but never inserted it into the rendered markup — the variable was computed and discarded every render. Now rendered under the chain as originally intended.

### 4. [Minor] Pointless f-string — `legacy/streamlit_app/pages/Analytics.py:383`
- An `f"..."` string with no `{}` placeholders (`f"This is the day your outcomes..."`). Not a functional bug, but misleading and flagged by static analysis; converted to a plain string.

### 5. [Performance] Redundant model forward pass on every classification — `services/prediction_service.py`
- `_predict_classification` called both `.predict_proba(X)` **and** `.predict(X)` on the same input — two full forward passes through the trained `HistGradientBoostingClassifier` per call, for a value (`.predict()`) that's mathematically derivable from the first call's output (argmax of `predict_proba` — softmax preserves ranking, so this is guaranteed identical, not just usually identical).
- **Verified empirically** before changing: ran both `.predict()` and `argmax(.predict_proba())` against 1000 validation rows on the actual shipped classifier — **0 mismatches**.
- **Fix:** derive `raw_prediction` via `argmax` of the probabilities already computed; the second `.predict()` call is gone.
- **Compounding impact:** `future_path_service.py`, `advanced_whatif_service.py`, and `parallel_twin_service.py` all call `PredictionService.predict()` once per candidate/scenario (several times per single user action, e.g. every "future path" comparison). This fix roughly halves classifier inference cost across all of them, not just the main Prediction page.
- **Verification:** targeted tests (`test_prediction_pipeline`, `test_regression_safety`, `test_concurrency`, `test_shap_load`, `test_model_manager`, `test_uncertainty_service`, `test_recommendation_service`, `test_pages_smoke`) plus full suite, all passing.

### 6. [Cleanup] Dead imports removed (verified each individually, not blindly stripped)
- `legacy/streamlit_app/components/share_report_card.py` (`Dict`), `story_card.py` (`Any` — kept `Optional`, which *is* used; caught and corrected a first-pass mistake here), `streak_tracker.py`, `sparkline.py` (`Optional`), `week_comparison_card.py` (`Optional`, `WeekSummary`), `services/gamification_service.py` (`field`), `services/shap_service.py` (`LinearRegression`, `LogisticRegression`, `Ridge`, `Lasso`).
- Deliberately **left alone**: `bootstrap` imports in every `legacy/streamlit_app/pages/*.py` and `tests/_test_support` imports across the test suite — both are legitimate side-effect imports (path setup, test shims for `shap`), confirmed by reading `bootstrap.py` and `_test_support.py` before deciding not to touch them. Static analysis flags these as "unused" but removing them would break the app.

---

## ML Review — the significant open finding

### Systematic mismatch between how `total_screen_min` was generated for training vs. how it's computed at inference time

**What I found:** In `data/train.csv`, the five usage-category columns
(`social_min + gaming_min + work_study_min + video_min + other_min`) do
**not** sum to `total_screen_min`. Across a 200-row sample, the category
sum averages **1.55x** the stored total, ranging from 1.0x to 2.0x, never
below — a systematic pattern (consistent with categories capturing
overlapping/multitasked screen time against an independently-tracked
device total), not noise.

**The problem:** `utils/feature_derivation.py` and `utils/form_generator.py`
(the two places that build features for a *live* prediction) both compute
`total_screen_min` as the literal sum of the category minutes — there is no
form field for an independently-tracked device total, so there's no way for
a live user's ratios to ever exceed what the training data's ratios could
be. Every ratio (`social_ratio`, `night_ratio`, ...) and density feature
(`notification_density`, `pickup_density`, ...) derived from `total_screen_min`
therefore lives on a **different distribution at serving time than at
training time** — live ratios always sum to 1.0 and live densities are
systematically ~1.5x higher (since `screen_hours` is smaller) than what the
model saw during training for a comparable user.

**Why I didn't "fix" this in-line:** there are two materially different
ways to resolve it — (a) retrain on category-sum-consistent data, or
(b) add a real device-reported total to the form and preserve the training
semantics — and picking one silently changes either the model's behavior or
the product's data collection, which goes beyond a code-quality fix and
needs a product decision, per this audit's own instruction not to change
functionality without a clear engineering benefit that stays within scope.

**Recommendation:** before treating this model's guidance as trustworthy for
real users, either regenerate `data/train.csv`/`validation.csv` with the
same sum-of-categories semantics the live app uses, or add a "total screen
time" field to the form that's tracked independently of the category
breakdown, matching the original generation process.

### Confirmed correct (checked, not assumed)
- Classification and regression feature schemas are consistent except for
  one intentional, explained exception (`screen_ewma_baseline`, present in
  regression only — documented in `models/preprocessing.py` as dropped from
  classification due to near-duplication with another feature).
- `services/storage/json_file_storage.py`: correct cross-platform OS-level
  file locking (`fcntl`/`msvcrt`) layered under a thread lock, atomic
  temp-file-then-rename writes. All 19 call sites across every service that
  writes (`account_service`, `family_service`, `history_service`,
  `commitment_service`, `letter_service`, `reflection_service`,
  `plan_progress_service`) correctly call `commit()` **inside** the
  `transaction()` lock scope — no TOCTOU gaps found.
- `AccountService.register()`'s duplicate-email check happens inside the
  same locked transaction as the write, so two concurrent registrations
  with the same email can't both succeed.
- `ModelManager` singleton: every `@st.cache_resource`-wrapped page loader
  (`Prediction.py`, `What_If_Simulator.py`, `AI_Coach.py`,
  `Model_Performance.py`) constructs a `PredictionService`/`ModelService`
  that routes through `ModelManager.instance()`, so the original "loaded
  twice" bug this class was built to fix is not regressed anywhere in the
  current page set.

---

## Remaining Technical Debt / Risks (not addressed this pass)

1. **The feature-derivation mismatch above** — highest-priority remaining
   item; affects prediction quality, not just code hygiene.
2. This pass covered dependency integrity, storage/concurrency, dead code,
   and the highest-traffic inference path. It did **not** do a
   line-by-line review of all ~30 services, all Streamlit pages, CSS/theme
   code, or the training scripts (`models/train_*.py`) themselves — a
   codebase this size warrants further focused passes rather than one claim
   of exhaustive coverage.
3. `numpy`/`shap`/`numba` version compatibility in *this* sandbox required
   the test suite's `shap` stub (`tests/_test_support.py`) to exercise
   `services/shap_service.py`; the real `shap` package couldn't be
   installed here (numba/numpy conflict). Worth confirming the real `shap`
   installs cleanly in the actual deployment target's environment, since
   this sandbox's `numpy 2.5` also isn't what `model_info.json` was
   generated under — the sklearn pin fix addresses the reproducible
   pickle-compat problem; the numpy/numba story is an environment note, not
   a code bug.

---

## Test Suite

- **Before any change:** 274 passed, 9 failed, 32 errored (root cause:
  issue #1 above).
- **After the `scikit-learn` pin fix:** 315 passed, 0 failed.
- **After all subsequent fixes (dto.py, improvement_chain.py, Analytics.py,
  prediction_service.py, dead-import cleanup):** 315 passed, 0 failed,
  confirmed on a full re-run as the final step of this pass.
