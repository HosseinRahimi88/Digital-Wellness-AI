# Digital Wellness AI — Merge Report

**Merge direction:** Project A (Streamlit, stronger ML) is the base. Project B's FastAPI
backend was evaluated and rejected as an architecture (see §5); its product ideas —
onboarding, dashboard, weekly planning, recommendation guardrails, analytics trends,
profile management — were ported into A's existing pages and services.

**Verification method throughout:** every phase below was checked with the *real* test
suite (`python -m unittest discover -s tests`), not assumption. Final state: **92/92
tests passing**, ML artifacts byte-identical to Project A's originals (MD5-verified),
zero changes outside the application layer.

---

## 1. Files changed

### New files
| File | Purpose |
|---|---|
| `services/account_service.py` | Multi-user register/authenticate/lookup, reusing A's own `StorageBackend` (no new DB dependency) |
| `utils/security.py` | Argon2 password hashing (ported from B's `core/security.py`, JWT stripped) |
| `legacy/streamlit_app/pages/Login.py` | Login/register UI |
| `config/demo_profiles.py` | Canonical "Quick Demo" profiles, built from A's real `FEATURE_SCHEMA` |
| `legacy/streamlit_app/pages/Dashboard.py` | New unified dashboard (A had none) |
| `services/plan_progress_service.py` | Persistent per-user, per-week task completion tracking |
| `config/onboarding_options.py` | Shared goal/purpose/schedule option dicts (used by Onboarding + Profile) |
| `legacy/streamlit_app/pages/Onboarding.py` | 6-question preference onboarding flow |
| `legacy/streamlit_app/pages/Profile.py` | Account + preference management |
| `tests/test_account_service.py`, `tests/test_plan_progress_service.py` | New unit tests (26 tests) |

### Modified files
| File | Change |
|---|---|
| `utils/session.py` | `get_user_id()` now prefers a logged-in account, exactly as its own prior docstring anticipated; added onboarding-profile helpers |
| `legacy/streamlit_legacy/streamlit_app/Home.py` | Nav links to new pages, login-state greeting |
| `legacy/streamlit_app/pages/Prediction.py` | Added "Quick Demo" tab; refactored the render logic into a shared function (no behavior change) |
| `legacy/streamlit_app/pages/Weekly_Insights.py` | Added persistent Weekly Plan section |
| `legacy/streamlit_app/components/improvement_plan_card.py` | Added `render_persistent()` alongside the original (untouched) `render()` |
| `config/recommendation_registry.py`, `models/recommendation.py`, `services/recommendation_service.py` | Added `success_metric` / `safety_note` fields (guardrail content), threaded through, backward-compatible |
| `legacy/streamlit_app/components/recommendation_card.py` | New "Success metric & safety" expander |
| `legacy/streamlit_app/pages/Analytics.py` | Added real historical trend charts (Score History, Day-of-Week Pattern) from `HistoryService` |
| `tests/_fake_streamlit.py`, `tests/_test_support.py` | Test-harness gaps filled (`text_input`, `radio`, `rerun`, offline `pwdlib` stub) as each new page needed them |
| `tests/test_pages_smoke.py`, `tests/test_recommendation_service.py` | Extended coverage for new pages/content |
| `requirements.txt` | Added `pwdlib[argon2]` |

### Untouched (verified byte-identical or behaviorally unchanged)
`artifacts/*.pkl`, `data/*.csv`, `core/`, `config/validation_rules.py`, `models/` (all
training/inference code), `services/prediction_service.py`, `services/shap_service.py`,
`services/validation_service.py`, `services/history_service.py`,
`services/improvement_plan_service.py`, `services/achievement_service.py`,
`services/model_service.py`, `services/storage/`, `legacy/streamlit_app/pages/AI_Coach.py`,
`legacy/streamlit_app/pages/Model_Performance.py`, `legacy/streamlit_app/pages/About.py`, `legacy/streamlit_app/pages/What_If_Simulator.py`,
`utils/feature_derivation.py`, `utils/form_generator.py`, `utils/persona.py`.

---

## 2. Why each change was made

Every phase followed the same process: read both implementations in full, identify
what B did that A genuinely lacked, check whether porting it required touching the ML
layer, and if so, rebuild the *idea* against A's real data/services rather than copying
B's code. Two corrections came up repeatedly and are worth naming once:

- **B's model is a real 7-day forecaster; A's isn't.** B's copy ("forecast", "predicted
  future score") was accurate for B's model and would have been a false capability
  claim if copy-pasted onto A's classifier/regressor, which score *current* input, not
  future time. Every ported page (Dashboard, Analytics) was reworded around this.
- **B's demo/baseline data belonged to a 58-feature model that no longer exists in this
  app.** Nothing from B's actual feature values was reused; new demo profiles were built
  from A's real `FEATURE_SCHEMA` and cross-checked against A's own test fixtures.

## 3. What Project A kept

- Both trained models (`health_classifier.pkl`, `health_regressor.pkl`), unmodified,
  MD5-verified before and after every phase.
- All feature engineering (`core/feature_schema.py`, `utils/feature_derivation.py`,
  `models/preprocessing.py`) — never touched.
- The full prediction pipeline, SHAP explainability, validation, history storage
  (with its file-locking concurrency guarantees), achievement logic, and PDF reporting.
- Its existing 11 test files, all still passing, none weakened.
- Its architecture as the primary app (Streamlit), after B's FastAPI backend was
  evaluated and rejected (§5).

## 4. What Project B contributed (adapted, not copied)

- Multi-user authentication concept and its Argon2/timing-attack-safe auth pattern
  (`core/security.py`, `services/auth.py`) — algorithm and safety properties kept,
  storage layer rebuilt on A's own abstraction instead of SQLAlchemy.
- Onboarding flow structure and question set (6 questions + 2 consents).
- The "one-click demo profile" and dashboard layout ideas.
- The "why this plan was created" + per-task tracking concept for weekly planning.
- The idea of a per-recommendation success metric and safety note.
- Historical trend / day-of-week pattern charting idea for analytics.
- Profile page structure — with its "Trust Center" *not* ported as-is, since it
  displayed hardcoded metric strings rather than real ones (A's `Model_Performance.py`
  is linked instead — it reads the real `metrics.json`).

## 5. New architecture

```
Streamlit app (unchanged framework)
├── legacy/streamlit_app/pages/
│   ├── Home.py                 [modified: nav]
│   ├── Login.py                [new]
│   ├── Onboarding.py           [new]
│   ├── Prediction.py           [modified: +Quick Demo tab]
│   ├── Dashboard.py            [new]
│   ├── Weekly_Insights.py      [modified: +persistent Weekly Plan]
│   ├── AI_Coach.py             [unchanged]
│   ├── Analytics.py            [modified: +history trends]
│   ├── Model_Performance.py    [unchanged]
│   ├── Profile.py              [new]
│   ├── What_If_Simulator.py    [unchanged]
│   └── About.py                [unchanged]
├── services/
│   ├── account_service.py      [new — auth]
│   ├── plan_progress_service.py [new — plan persistence]
│   ├── prediction_service.py, shap_service.py, validation_service.py,
│   │   history_service.py, improvement_plan_service.py,
│   │   achievement_service.py, recommendation_service.py [unchanged logic]
│   └── storage/ (StorageBackend abstraction — reused for both new services)
├── config/
│   ├── demo_profiles.py, onboarding_options.py [new]
│   └── recommendation_registry.py [content-extended]
├── core/, models/, artifacts/, data/ [byte-identical to Project A]
└── utils/security.py [new], utils/session.py [extended]
```

**Why FastAPI (Project B's backend) was rejected:** `model_registry.py` hard-coded
SHA256/feature-count assertions and bespoke method calls (`predict_outputs`,
`residual_pipeline`) against one specific joblib artifact, with zero abstraction between
the API layer and that artifact's exact shape. Swapping in Project A's two-estimator
sklearn pipeline would have meant rewriting 5+ files' worth of hard assertions, not a
config change — a disqualifying architectural coupling for *this* merge, independent of
otherwise-solid code quality elsewhere in that backend (its auth/security code was
genuinely good and is exactly what got ported).

## 6. Remaining technical debt

Each of these was a deliberate scope cut, flagged at the time rather than silently
dropped:

1. **CSV/JSON bulk upload** (Prediction page) — B had it; A's ~40-field schema + derived
   feature computation makes a correct port a standalone feature, not a quick UX copy.
2. **Recommendation action tracking** (done/replace/not-relevant/etc.) — needs a
   persistent "recommendation event" identity model A doesn't have; recommendations are
   recomputed fresh from SHAP every run today.
3. **Personal Baseline deviation table** (Analytics) — B tracked EWMA baselines across
   many features; A only computes one (`screen_ewma_baseline`) as a model input, not a
   general-purpose tracking system.
4. **Tone / reminder-frequency / excluded-families preferences** (Profile) — deliberately
   *not* added since nothing consumes them yet; would be inert settings.
5. **`st.time_input`** (Onboarding/Profile) — using plain `HH:MM` text fields instead;
   fine today since the value is only ever stored as a string, worth revisiting if
   time-based logic (e.g. bedtime reminders) gets built later.
6. **Login is session-based, not gated** — most pages work anonymously by design (matches
   A's original no-login architecture), but nothing currently *requires* login; that's a
   product decision, not an oversight, and easy to change by wrapping pages with an
   `is_authenticated()` check if you want it.
7. **Sandbox verification gap:** this development environment has no network access, so
   `pwdlib`'s real Argon2 implementation was verified only via its documented API surface
   (stubbed) — run `pip install -r requirements.txt && python -m unittest discover -s
   tests` in a real environment before shipping to confirm identical behavior.

---

## Addendum: Bug-fix + FastAPI-readiness pass

Scope: fix any real bugs found, and prepare the backend for a future FastAPI layer
**without building that layer yet**, per explicit instruction. 15 new tests added
(107 total, all passing). No FastAPI app, routes, or endpoints were created in this pass.

### Bugs found and fixed
1. **`Account(**record)` would crash on any unknown/legacy stored key** — a plain
   `TypeError` on the very next dataclass field rename or manual data edit, for *every*
   user, not just the affected record. Fixed with `_account_from_record()`, which
   filters to known fields before construction. Covered by a new regression test
   (`test_unknown_key_in_stored_record_does_not_crash_lookup`).
2. **`requirements.txt`'s `pwdlib` pin had no upper bound** (`>=0.2`) — loosened past
   what was actually validated. Tightened to `>=0.2,<1.0`, matching Project B's own
   tested `requirements-p0.txt` pin exactly (verified by reading that file directly,
   not guessed).
3. Ran a full static sweep for the most common *real*-Streamlit bug this project's test
   harness can't catch on its own (a fake `st.form()` doesn't enforce Streamlit's actual
   rule that only `st.form_submit_button` — not `st.button` — may appear inside a form):
   no violations found across any page, new or original.
4. Full-project import sweep (27 modules directly imported, not just page-level smoke
   tests) — all clean.

### FastAPI-readiness work (backend only, no API layer)
- **`utils/tokens.py`** (new): JWT access-token issuance/validation, ported from Project
  B's already-audited `core/security.py` (same claims: `sub`/`iat`/`exp`/`jti`/`type`/
  `iss`). Reads its signing secret from the `JWT_SECRET_KEY` environment variable —
  never hardcoded, never defaulted — and raises a clear, actionable error if it's unset
  or under 32 characters. **Nothing in the Streamlit app calls this today**; it's
  intentionally inert until something (an API layer, or you) needs it.
- **`AccountService.issue_access_token()` / `resolve_access_token()`** (new methods,
  additive only): turn an `Account` into a signed token and back, using the module
  above. Verified with a real (not stubbed) PyJWT round-trip in this sandbox, plus wrong-
  secret, expired-token, garbage-token, and deleted-account cases.
- **`requirements.txt`**: added `PyJWT>=2.9,<3.0` (Project B's own validated pin).

### What this does *not* include (by design, per your instruction)
No FastAPI app, no route/endpoint definitions, no request/response Pydantic schemas, no
`main.py`, nothing wired into any page. The Streamlit app's behavior is completely
unchanged — `git diff`-style verification confirms zero pages call anything new here.
When you're ready to actually build the API layer, `services/*.py` (already
framework-agnostic) plus `utils/tokens.py` + `AccountService`'s new methods are the
starting point; still needed at that point: Pydantic request/response schemas, FastAPI
route handlers, and a decision on whether `services/storage/`'s JSON-file backend is
sufficient for expected API load or needs to become a real database.

---

## Addendum 2: Deep stress-testing pass (concurrency, adversarial input, attack vectors)

Requested: stronger, more adversarial testing of the backend, not just re-confirming
the happy path. This pass used real multi-threading (not mocks) against the actual
file-lock backend, real PyJWT (not stubbed), and deliberately hostile input. **13 new
tests added — 120 total, all passing.**

### One real bug found and fixed
**`services/validation_service.py`: booleans silently passed as valid numbers.**
`bool` is a subclass of `int` in Python, so `float(True) == 1.0` and `int(False) == 0`
both succeed without error — meaning a boolean value sent into any numeric field
(`sleep_hours`, screen-time minutes, etc.) would silently become `1.0`/`0.0` instead of
being rejected. **The current Streamlit UI can't trigger this today** (its
`number_input`/`slider` widgets never emit raw booleans), so it was latent, not
exploitable yet — but it's exactly the class of bug a future JSON API *would* expose,
since a client can send any JSON value for any field. Fixed with an explicit
`isinstance(value, bool)` check before numeric coercion. Verified the fix doesn't
affect the two fields that are genuinely boolean (`uses_screen_time_limits`,
`is_content_creator` — they go through the categorical path, untouched) and doesn't
change any real prediction output (re-ran the actual demo-profile prediction
end-to-end afterward: identical score, 78.97).

### What was stress-tested and confirmed correct (no bug found, but not previously proven)
- **Concurrent registration, same email, 30 threads:** exactly 1 success, 29 clean
  `EmailAlreadyRegisteredError`s, exactly 1 record on disk. No race condition.
- **Concurrent registration, 50 different emails:** all 50 persisted, zero ID or data
  collisions.
- **Concurrent `PlanProgressService.set_completed()`,** both different-task (40 threads)
  and same-task-flapping (40 threads racing True/False on one task): no lost writes, no
  duplicate records.
- **Concurrent `HistoryService.record()` for the same (user, date) key** (a scenario A's
  own `test_concurrency.py` didn't cover — it only tested different users): correctly
  upserts to exactly 1 record, not 30.
- **Corrupted `accounts.json` / `plan_progress.json`** (empty, truncated, garbage, valid-
  JSON-but-wrong-shape): both new services degrade gracefully and remain writable
  afterward, inheriting the resilience A's `JSONFileStorageBackend` already had —
  confirmed end-to-end through each service's own methods, not just the shared backend.
- **JWT attack vectors:** `alg: none` forged-token attack, wrong-secret forgery, payload
  tampering (bit-flip), and a token missing a required claim — all four correctly
  rejected.
- **Persian text, emoji, and mixed-script display names** (علی رضایی, Sara 🎉😊, مixed
  محمد Mohammad): register/round-trip correctly.
- **10,000-character and Persian/emoji passwords:** hash and authenticate correctly.
- **Email normalization under whitespace/case variation:** login works regardless.
- Full static sweep for Streamlit's actual `st.button`-inside-`st.form` restriction
  (which the test harness's fake `st.form` can't itself enforce): no violations in any
  page, confirmed by pattern-matching every `with st.form(...)` block's body.
- Direct import of all 27 backend/app modules (not just page-level smoke tests): clean.

All of the above were promoted from one-off verification scripts into permanent test
files (`tests/test_concurrency_new_services.py`, additions to `tests/test_tokens.py`,
`tests/test_concurrency.py`, `tests/test_validation_service.py`) so they run on every
future change, not just this one.

---

## Addendum 3: SHAP concurrency deep-dive — "will it explode under many simultaneous users?"

Direct answer: **it will not crash, corrupt data, or leak memory under concurrent or
sustained load — verified, not assumed. But it will NOT get faster with more concurrent
threads in a single process either**, and that second part is a real capacity-planning
fact you should know before you scale up traffic, not a bug to fix in this code.

### What was tested (against the real, installed scikit-learn — not a stub)

1. **Thread-safety / correctness under load:** ran the shared `PredictionService` /
   `SHAPService` through repeated concurrent bursts. **Zero errors, zero
   cross-contaminated results** across every run — two threads never received each
   other's prediction, even under sustained pressure.
2. **Memory stability:** 80 real predictions run back-to-back, process RSS sampled
   every 20. Result: **166.9 MB → 166.9 MB → 166.9 MB → 166.9 MB — completely flat**.
   No leak.
3. **Isolated GIL/parallelism measurement** (the actual finding): timed the real
   classifier's `.predict_proba()` and the real `SHAPService.explain()` in isolation,
   comparing 1 sequential call vs. 40 concurrent calls:
   - Classifier alone: **0.97x** "speedup" from 40 threads (1.0x = zero benefit, fully
     serialized).
   - SHAP alone: **1.00x** "speedup" from 40 threads (exactly zero benefit).

   In plain terms: **Python's GIL means this pipeline does not run in true parallel
   across threads for single-row inference**, regardless of CPU core count. This isn't
   specific to the offline SHAP stub — the classifier result used the real, installed
   scikit-learn 1.8.0 model, and showed the identical pattern.

### What this means in practice

- **Correctness/stability under load: solid.** No crash risk, no data-corruption risk,
  no memory-growth risk, confirmed under real concurrent and sustained stress.
- **Throughput under load: bounded by one core-equivalent per process.** If 50 users
  click "Predict" at the same moment on one Streamlit process, they queue behind each
  other rather than being served in parallel — total wait time is roughly
  `(number of waiting users) × (per-request time)`, not `per-request time` for everyone.
- **The absolute per-request time you'd see in real production is not what was measured
  here.** This sandbox's offline SHAP stand-in does O(n_features) sequential model
  calls per explanation (~900ms/request measured here); the real, compiled
  `shap.TreeExplainer` this app actually uses in production is typically single-digit
  milliseconds. Lower per-request time directly shrinks the queueing problem above, but
  doesn't eliminate the "no thread parallelism" fact.

### Recommended before a real traffic spike (deployment decisions, not code bugs)

1. **Run this same isolated timing check in your real environment** (with real `shap`
   installed) to get the true per-request number — that determines how much headroom
   you actually have before queueing becomes noticeable.
2. **Horizontal scaling, not code changes, is the fix if you need more throughput:**
   run multiple Streamlit process replicas behind a load balancer. `ModelManager` is a
   *per-process* singleton by design — each replica loads its own copy and gets its own
   independent GIL, so this sidesteps the serialization entirely. This requires no
   changes to `services/`.
3. If you later build the FastAPI layer discussed earlier, the same GIL characteristic
   applies there too — a `ProcessPoolExecutor` for the predict+SHAP step (or, again,
   multiple API process replicas) is the standard fix, not multi-threading within one
   process.

### New permanent tests added
`tests/test_shap_load.py` (3 tests): concurrency correctness at N=10 (matching A's own
existing precedent in `test_concurrency.py`), a check that the SHAP explainer is truly
a single shared instance (not rebuilt per request — the actual reason load stays cheap
regardless of thread-parallelism), and a memory-stability check across 20 sequential
predictions with a generous 50MB leak-detection threshold.




## 7. Production readiness score

**7.5 / 10**

**What earns the 7.5:** ML layer fully preserved and verified (models, features, SHAP,
accuracy — untouched, MD5-checked at every phase); 92 passing tests including new
coverage for every new service; no duplicated functionality; every new persistence
path (accounts, onboarding profiles, plan progress) uses the same concurrency-safe
storage abstraction A already had, not ad hoc file I/O; every UI addition was smoke-
tested through real (not mocked) prediction/history/SHAP output at least once.

**What holds it back from higher:**
- Real Argon2 behavior unverified in *this* sandbox (network-blocked) — needs one real
  test run before production.
- No rate limiting or brute-force protection on login (`account_service.authenticate`)
  — the timing-attack mitigation is there, but a lockout/backoff policy isn't.
- JSON-file storage (reused deliberately for consistency) will not scale past
  single-instance deployment the way a real database would if this grows to many
  concurrent users — fine for the current single-process Streamlit deployment model,
  a real constraint if that changes.
- The 7 items in §6 are real, scoped gaps, not hidden ones — but they are gaps.
