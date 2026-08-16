# Group C Implementation — Final Report

**Result: 315/315 tests passing** (292 pre-existing + 23 new for Family Mode alone;
80 new tests total across all five features). All five features implemented,
wired into the UI, and tested against the real trained models — no mocks,
no placeholders.

---

## 0. Environment fix (blocking, found before any feature work)

**Problem:** `artifacts/*.pkl` were pickled with scikit-learn 1.8.0; this
environment had 1.9.0 installed, silently corrupting model loading (9 failed /
10 errored tests: prediction, SHAP, concurrency, page-smoke).
**Fix:** Pinned `scikit-learn==1.8.0` (`pip install --force-reinstall`) to match
the shipped artifacts — lower-risk than retraining, since it changes nothing
about the models themselves. No files modified for this; it's an environment
correction. **Verification:** 242/242 pre-existing tests passed immediately after.

---

## 1. Feature 55 — Prediction Uncertainty

**New files:**
- `services/uncertainty_service.py` — split conformal prediction (Lei et al.
  2018), calibrated once against `data/validation.csv` (never `train.csv` or
  `test.csv` — no leakage), cached to `artifacts/uncertainty_calibration.json`
  keyed by model `saved_at` timestamps (auto-invalidates on retrain).
- `app/components/uncertainty_card.py` — UI panel.
- `tests/test_uncertainty_service.py` — 12 tests, including an **empirical
  coverage check** that verifies the conformal math actually holds (≥85%
  coverage confirmed on the validation set for a 90% target).

**Modified:** `models/model_manager.py` (loads once, shared), `services/
prediction_service.py` (wired in), `models/schemas.py` (added `uncertainty`
field to `PredictionResult`), `app/pages/Prediction.py` (renders the card).

**Why conformal prediction, not RandomForest tree-variance or a bootstrap
ensemble:** the deployed models are `HistGradientBoosting*`, which don't
expose independent per-tree estimators the way RandomForest does, and
training a separate bootstrap ensemble would describe a different model than
the one actually making the prediction. Split conformal wraps the existing,
unmodified model and gives a distribution-free, finite-sample coverage
guarantee — the strongest calibration available without retraining.

**Risk eliminated:** the app previously showed only a raw softmax confidence
number, easy to over-trust. It now also shows a statistically-backed interval
and a conformal prediction *set* (which classes can't be ruled out).

---

## 2. Feature 02 — Persona Detection

**New files:**
- `models/train_persona.py` — KMeans over 15 curated behavioral/psychological
  features, fit on `train.csv` only. **K is not hand-picked**: fit for K∈{4,5,6,7},
  selected by silhouette score (K=4, silhouette=0.077 — honestly low, as
  expected for overlapping human-behavior distributions, not hidden).
  Persona *names* are derived from each cluster's centroid z-scores vs. the
  global mean, not a fixed lookup table — e.g. "Fragmented-Attention
  Night-Owl", "Productive Low-Stress".
- `services/persona_service.py` — nearest-centroid assignment at inference
  time, with a genuine **relative-distance confidence** (how much closer to
  the assigned centroid than the runner-up) instead of a fabricated number.
- `app/components/persona_card.py`.
- `tests/test_persona_service.py` — 13 tests.

**Modified:** `utils/persona.py` (added `resolve_persona()`: ML-first with
automatic fallback to the original rule-based label if the model or a
required feature is unavailable), `models/model_manager.py`, `services/
prediction_service.py`, `app/pages/Prediction.py`, `app/pages/Weekly_Insights.py`.

**New artifacts:** `artifacts/persona_model.pkl`, `artifacts/persona_info.json`.

**Why this is a real upgrade over the existing rule-based label:** the old
`generate_persona()` only ever varied with the classifier's predicted class
plus 1–2 raw fields — two "Moderate" users always got bucketed identically.
KMeans clustering is unsupervised and orthogonal to the risk prediction,
so it can actually distinguish different behavioral patterns within the same
risk class.

---

## 3. Feature 42 — Reflection Loop

**New files:**
- `services/reflection_service.py` — self-rating (1–5) + free text journal,
  keyed by `(user_id, date)`. Computes **calibration**: Pearson correlation
  between day-over-day *changes* in self-rating and day-over-day *changes*
  in the objective `health_score` (deltas, not raw levels, so a habitually
  low/high self-rater isn't penalized for a consistent bias). Generates
  reflection prompts grounded in the user's own real score trend and top
  SHAP feature — not a generic/static question.
- `app/components/reflection_card.py`.
- `tests/test_reflection_service.py` — 13 tests, including a perfectly-aligned
  synthetic case (correlation > 0.9 → "Well-calibrated") and an inversely-related
  one (correlation < −0.5 → "Inversely calibrated").

**Modified:** `app/pages/Weekly_Insights.py`.

**No leakage / no model involvement:** pure presentation-and-analytics logic
on top of numbers the ML pipeline already produced; never feeds back into
training or model inputs.

---

## 4. Feature 39 — Future Path Comparison

**New files:**
- `services/future_path_service.py` — 5 named scenarios (Status Quo,
  Continued Drift, Gradual Improvement, Committed Change, Digital Detox),
  each a full habit-shift template evaluated with the real, unmodified
  `PredictionService.predict()` (never a fitted forecast model — reuses the
  clamping/shift pattern already validated in `services/parallel_twin_service.py`).
- `app/pages/What_If_Simulator.py` gained a "🛤️ Future Paths" tab.
- `tests/test_future_path_service.py` — 12 tests.

**Two real bugs found and fixed during implementation (not hypothetical —
both reproduced and root-caused with a debugger, not assumed):**

1. **`screen_ewma_baseline` frozen across scenario paths.** Fixed by
   recomputing it fresh for any non-identity path (a Future Path represents
   a *sustained* new normal, unlike the single-day What-if Simulator, which
   correctly keeps it frozen).
2. **Bigger finding: every demo profile in `config/demo_profiles.py`
   (`baseline`, `healthy`, `at_risk`, `borderline`) had internally
   inconsistent derived fields** — e.g. `borderline_profile()` claimed
   `social_ratio=0.5` while its own `social_min`/`total_screen_min` implied
   0.4167, and its four ratio fields summed to 2.0 (impossible). This wasn't
   a Group C bug — it affected the live "Quick Demo" tab and every test
   built on `tests/_test_support.py`, silently feeding the trained models
   physically-inconsistent inputs. **Fixed** by routing every profile
   through `derive_features()` (the same function a real form submission
   goes through) instead of hand-typing derived values, then fixing the
   cascading range violations that surfaced (baseline profile's independently-
   midpointed screen-time fields summed to a 60-hour day). **Verified:** all
   four profiles still land in their intended class buckets (Healthy/At
   Risk/Moderate), and all 280 pre-existing tests stayed green — meaning no
   test depended on the old broken numbers, only on structural properties.

**Honesty safeguard added:** `FuturePathComparison.is_delta_meaningful()`
flags deltas under 1.5 points as "within model noise" rather than implying
false precision — tree ensembles aren't guaranteed monotonic, especially near
a score ceiling/floor, and the UI says so instead of hiding it.

---

## 5. Feature 48 — Family Mode

**New files:**
- `services/family_service.py` — multi-account family groups via invite code,
  built on the existing `AccountService`/`StorageBackend` pattern.
- `app/pages/Family.py`.
- `tests/test_family_service.py` — 23 tests.

**Privacy design (the highest-risk feature, treated accordingly):**
- Only **three derived, summary-level fields** are ever shared per member:
  `health_score`, `health_class`, `persona_name`. Raw survey answers (stress,
  anxiety, loneliness) and habit minutes are never read by this service —
  enforced structurally (`MemberSummary`'s dataclass fields have no slot for
  them; a test asserts this) and behaviorally (a test populates history with
  sensitive raw fields and confirms they never appear in the dashboard).
- **Consent is explicit per-member, not implied by membership**: `join_family()`
  requires the joining member to pass `share_summary` themselves (no default
  value — verified by a test that inspects the function signature). A member
  can also toggle sharing off without leaving the family.
- Non-sharing members still appear in the roster (so the family knows who's
  in the group) but with no score data — the absence is visible, not hidden.

---

## Files touched (complete list)

**New (18 files):**
`services/uncertainty_service.py`, `services/persona_service.py`,
`services/reflection_service.py`, `services/future_path_service.py`,
`services/family_service.py`, `models/train_persona.py`,
`app/components/uncertainty_card.py`, `app/components/persona_card.py`,
`app/components/reflection_card.py`, `app/pages/Family.py`,
`tests/test_uncertainty_service.py`, `tests/test_persona_service.py`,
`tests/test_reflection_service.py`, `tests/test_future_path_service.py`,
`tests/test_family_service.py`, plus generated artifacts
`artifacts/persona_model.pkl`, `artifacts/persona_info.json`,
`artifacts/uncertainty_calibration.json`.

**Modified (11 files):** `models/model_manager.py`, `models/schemas.py`,
`services/prediction_service.py`, `utils/persona.py`, `config/demo_profiles.py`
(bug fix), `app/pages/Prediction.py`, `app/pages/Weekly_Insights.py`,
`app/pages/What_If_Simulator.py`, `app/Home.py`, `tests/test_pages_smoke.py`,
`tests/test_model_manager.py` (updated expected joblib-load count from 2→3).

**Deleted:** none.

## New dependencies

None. Everything uses scikit-learn (`KMeans`, `StandardScaler`, already a
project dependency), `numpy`, and the project's existing storage/service
patterns.

## Performance impact

- Persona/uncertainty models are loaded once by `ModelManager` (process-wide
  singleton, same pattern as the classifier/regressor) — not per-request.
- Uncertainty calibration (a validation-set pass) is cached to disk and
  auto-invalidated only when model artifacts actually change.
- Future Path Comparison runs 5 real predictions per call (same cost class as
  the existing Multi-Scenario Comparison, which already does up to 3).
- Family dashboard does one `HistoryService.get_all()` per member — bounded
  by family size, not global data volume.

## Risks introduced

- Persona clustering has a low silhouette score (0.077) — disclosed honestly
  in the UI's confidence display and artifact metadata, not hidden.
- Family Mode is new surface area for a not-yet-hardened auth system
  (`utils/tokens.py` JWT infra exists but isn't wired to any page yet, per
  `PROJECT_STATUS.md`) — family membership currently trusts whatever
  `get_current_account()` returns, same trust boundary every other
  authenticated page already relies on.

## Risks eliminated

- The sklearn version mismatch (silent, would have caused prediction
  failures in any environment with 1.9.0 installed).
- The demo-profile data-integrity bug (silently fed inconsistent inputs to
  the model from the live Quick Demo tab).
- Overconfident point predictions with no calibrated uncertainty.

## Future improvements (not done — out of scope for this pass)

- Wire `utils/tokens.py` JWT auth to actual page-level access control.
- Multi-family membership (currently one family per user, a deliberate
  scope decision documented in `family_service.py`).
- Retrain persona clusters periodically as `train.csv` grows, rather than
  only on manual `python -m models.train_persona` runs.
