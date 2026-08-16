# FastAPI Backend — Engineering Report

## Executive Summary

Added a production FastAPI backend (`api/`, 36 files, ~1,834 lines) as a
thin HTTP interface over the existing `services/` layer. Every endpoint
calls existing, unmodified business logic - no service's business rules
were duplicated, reimplemented, or moved into a router. The existing
Streamlit app is completely unaffected: it was re-verified passing
(357/357 tests, including 29 new ones for the API) at every step, and
the backend was verified working via **three independent methods**, not
just one: FastAPI's `TestClient` (57 assertions across 29 tests), a
real `uvicorn` server process hit with `curl`, and direct HTTP
round-trips against that real server.

Along the way, actually booting the app (rather than just reading the
code) surfaced and fixed four real, pre-existing or newly-introduced
bugs - documented in detail below, because each one is exactly the kind
of thing that only shows up when you run something for real.

---

## Architecture

```
api/
├── main.py                  # App factory: middleware, exception handlers, routers
├── core/
│   └── config.py             # pydantic-settings, .env support
├── exceptions/
│   ├── errors.py             # APIError hierarchy
│   └── handlers.py           # Centralized JSON error responses
├── middleware/
│   └── request_context.py    # Request ID + timing + security headers
├── auth/
│   └── security.py           # OAuth2 bearer wiring over AccountService's existing tokens
├── dependencies/
│   └── services.py           # DI providers for every service
├── schemas/                  # Pydantic request/response models (9 files, one per domain)
└── routers/                  # 12 routers, one per capability
```

**Deviation from the brief's example structure, and why:** the brief's
sketch put `api/` under `app/`. This project's `app/` is already the
Streamlit package (`legacy/streamlit_app/pages/`, `legacy/streamlit_app/components/`, `app/bootstrap.py`)
- nesting a second, unrelated meaning of "app" inside it would be
confusing, not clean separation. `api/` sits at the project root,
parallel to `app/`, `services/`, `models/`, `core/`, matching the
brief's own "adapt if you find a better design" allowance.

### The core rule: routers call services, never reimplement them

Every router follows the same shape: validate (via the real
`ValidationService`) → call the real service method(s) → map the
result's dataclass fields onto a Pydantic response model. No router
contains a scoring formula, a business rule, a threshold, or a
recommendation template - all of that stays exactly where it already
was. The two routers with multi-step orchestration
(`parallel_twin.py`, `reports.py`) sequence 2-3 existing service calls
in the order the Streamlit pages already sequence them - orchestration,
not logic.

### One deliberate anti-duplication design decision

`PredictRequest.user_data` (and every other endpoint that takes feature
values) is a flexible `dict[str, ...]`, not ~50 hardcoded Pydantic
fields mirroring `core.feature_schema.FEATURE_SCHEMA`. Hardcoding the
schema a second time in a different format would itself be duplicated
business logic - and a maintenance trap, since a schema change would
then need updating in two places to stay in sync. Instead, the existing
`ValidationService` (unmodified) is the single enforcement point, and
`GET /api/v1/schema/features` exposes that same schema read-only so API
clients aren't guessing field names/bounds.

---

## Endpoints (28 routes)

| Area | Routes |
|---|---|
| Health | `GET /health`, `GET /health/ready` |
| Schema | `GET /api/v1/schema/features` |
| Auth | `POST /register`, `POST /login`, `GET /me`, `PUT /me/onboarding` |
| Prediction | `POST /predict` |
| Future Path | `GET /definitions`, `POST /compare` |
| Parallel Twin | `POST /compare` |
| What-If | `POST /sweep`, `POST /goal-seek` |
| Personas | `POST /assign` |
| Cohorts | `GET /availability`, `GET /summary`, `GET /percentile`, `GET /me/comparison` |
| History | `GET /` (paginated), `GET /{date}`, `GET /weeks/current`, `GET /weeks/previous` |
| Analytics | `GET /summary` |
| Reports | `POST /pdf` |

**Deliberately not exposed as separate routes:** most of
`AnalyticsService`'s ~15 chart-specific static helpers (weekday heatmap,
correlation matrix, exception-day detection, etc.) - these back
Streamlit-chart-shaped data with no obvious non-UI consumer, and
wiring all 15 up would be re-plumbing without a clear API use case.
`GET /analytics/summary` wires up the handful that generalize (score
trend, weekday pattern, field averages). Family Mode, gamification
(badges/streaks/leaderboard), and the Reflection/Commitment features
also aren't exposed - each is a real, substantial service with its own
request/response shape, and given the scope of this migration, priority
went to depth-with-real-testing on the core prediction/analysis
capabilities over shallow coverage of everything. Adding the remaining
routers is mechanical (same pattern as everything here) but each
deserves its own real end-to-end test pass, not a rushed add at the end.

---

## Bugs found and fixed while building this (in the order discovered)

### 1. Circular import in the dependency graph
Designing a combined "resolve current user + build their HistoryService"
convenience dependency created `api.dependencies.services` →
`api.auth.security` → `api.dependencies.services`. Caught before it ever
ran (would have failed at import time). Fixed by having routers compose
`Depends(get_current_account)` and `Depends(get_history_storage_backend)`
separately instead of through a combinator function.

### 2. `.env` support didn't actually reach `utils/tokens.py`
`api.core.config.Settings` (pydantic-settings) loads `.env` into its own
fields correctly, but `utils/tokens.py`'s `get_jwt_secret()` deliberately
reads `JWT_SECRET_KEY` straight from `os.environ` (by design - so this
API layer doesn't duplicate ownership of that secret). Without an
explicit `load_dotenv()` call, a `JWT_SECRET_KEY` set only in `.env` was
invisible to it. Caught by actually running `POST /auth/register`, not
by reading the code - the request failed with a 500 the first time.
Fixed with one `load_dotenv()` call at the top of `api/main.py`.

### 3. Unfamiliar FastAPI/Starlette version installed by default
An unconstrained `pip install fastapi` resolved to a very recent version
(0.141.1) with different internal route-registration behavior
(`app.routes` no longer flattens included routers the same way older
versions did) - discovered because my own route-introspection script
returned an empty list despite the app importing successfully. Rather
than trust unfamiliar internals, pinned to a range I could verify
(`fastapi>=0.115,<0.120`), additionally constrained to stay compatible
with Streamlit's own transitive `starlette` requirement so installing
the API's dependencies can never silently break Streamlit's. Verified:
all 28 routes register correctly under the pin.

### 4. My own test design would have polluted production data
While preparing to write API tests, realized `get_history_service()`
was a plain factory (not a FastAPI dependency), which meant no clean
way to redirect it to isolated test storage - the test suite as first
designed would have written into the real `storage/prediction_history.json`
the deployed app uses. Fixed *before* writing any tests: added
`get_history_storage_backend()` as a proper overridable dependency
(defaults to `None` = real production path, exactly matching today's
Streamlit behavior; tests override it to an isolated temp-file backend).

### 5. [Pre-existing, not introduced by this work] `shap` couldn't import at all via a real server process
Booting the app with a real `uvicorn` process (not `TestClient`, which
never exercises a fresh process) failed at import time:
`ImportError: Numba needs NumPy 2.4 or less. Got NumPy 2.5.` The real
`shap` package requires `numba`, which requires `numpy<=2.4`; this
sandbox's `numpy` had drifted to 2.5. **This was never caught by the
existing test suite** because `tests/_test_support.py` installs an
offline `shap` stub into `sys.modules` before any test imports
`services.shap_service` - a deliberate, well-documented workaround for
this exact sandbox's lack of network access, but one that also silently
prevented anyone from noticing the real package was unimportable. The
existing Streamlit app has had this identical exposure the whole time;
it just never got run as a standalone process outside pytest. Fixed by
pinning `numpy>=1.24,<2.5` in `requirements.txt`. Verified: `import shap`
now succeeds, the real `uvicorn` server boots and serves real requests,
and the full test suite - now exercising the real `shap.TreeExplainer`
on every SHAP-related test instead of the offline stub - dropped from
150,027 warnings to 1 and roughly halved its wall-clock time (85s → 37s).

### 6. [Pre-existing, not introduced by this work] A test wrote into real production storage
Found via a full-suite bisection (halving the test file list repeatedly)
after noticing `storage/prediction_history.json` had a leftover entry
after every full-suite run. Root cause:
`tests/frontend/test_advanced_whatif_page_render.py` runs a real Prediction-page
submission (to exercise the What-If Simulator's real predictor-calling
paths) but - unlike `tests/api/test_pages_smoke.py`, which does exactly the
same kind of real-prediction flow correctly - never redirected
`HistoryService`'s `DEFAULT_STORAGE_PATH` to an isolated location first.
Every run of that one test wrote one real entry into the actual
production history file. Fixed by adding the identical `setUp`/`tearDown`
redirection pattern `test_pages_smoke.py` already established. Verified
via the same bisection: storage stays clean across 5 consecutive full
suite runs after the fix.

---

## Other changes

- **Removed `core/dto.py`** - confirmed via project-wide grep that
  nothing imported it (verified before deletion, and the full suite
  re-passed after). It duplicated class names (`PredictionResult`,
  `Recommendation`) that conflict with the real, actually-used
  definitions in `models/schemas.py` and `models/recommendation.py` -
  dead weight that could only ever cause confusion, never provide value.
- **`requirements.txt`**: added the FastAPI stack
  (`fastapi`, `starlette`, `pydantic`, `pydantic-settings`,
  `email-validator`, `python-dotenv`), each pinned to a verified range
  with an explanatory comment, following the same precedent set by the
  `scikit-learn==1.8.0` pin from an earlier session. Tightened
  `numpy>=1.24` to `numpy>=1.24,<2.5` for bug #5 above.
- **`.env.example`** added (new) - a template documenting every
  supported environment variable, since `.env` itself is correctly
  never committed (it would contain a real secret).

---

## Testing

**357/357 tests passing** (328 existing + 29 new in `tests/api/test_api.py`,
plus the 1-line isolation fix to `test_advanced_whatif_page_render.py`).

New API tests cover, all via real HTTP requests through `TestClient`
against the real app with real services (only the storage *backend* is
swapped for isolation - no service, no business logic, no prediction
result is ever mocked):
- Health/readiness
- Registration, duplicate-email rejection, login success/failure,
  auth-required enforcement, onboarding profile round-trip
- Prediction: the same "healthy profile → zero recommendations,
  at-risk profile → targeted recommendations" behavior verified
  directly against the services in an earlier session, now re-verified
  through the actual HTTP layer; validation-error → 422 with field
  errors; `persist=false` correctly excluded from history; a real
  prediction correctly appears in history afterward
- Future-path comparison (5 paths, best-path ranking), parallel-twin
  comparison, what-if sweep point count
- Persona assignment, cohort availability/summary/404-on-unknown-field
- **Multi-tenancy isolation**: two different authenticated users never
  see each other's history or analytics - the core guarantee this API
  layer must preserve from the existing per-user `HistoryService`
- Feature-schema endpoint matches `FEATURE_SCHEMA` exactly (no drift
  possible by construction, but verified anyway)
- OpenAPI schema validity, Swagger UI serving
- PDF report generation returns real PDF bytes (`%PDF` header)

## Final verification

- `python3 -m pytest -q` → **357 passed**, 1 warning (down from 150,027),
  37-40s wall-clock (down from ~85s)
- Real `uvicorn api.main:app` process booted successfully; hit with
  `curl` for `/health`, `/health/ready`, and a real
  `POST /api/v1/auth/register` - all correct
- `python3 -m pyflakes api/` - clean
- Production `storage/*.json` confirmed empty after every verification
  step in this session, including a 5-run repeat check after the
  bug #6 fix

## Summary of files added / removed / modified

**Added:** 36 files under `api/`, `tests/api/test_api.py`, `.env.example`
(39 new files total).

**Removed:** `core/dto.py` (confirmed dead).

**Modified:** `requirements.txt` (FastAPI stack + numpy pin),
`tests/frontend/test_advanced_whatif_page_render.py` (1 isolation fix).

**Untouched:** every file in `app/`, `services/`, `models/`, `config/`,
`core/feature_schema.py`, `core/validation_result.py`, `utils/` (except
reading from, never writing to) - the entire existing business layer
and Streamlit UI, byte-for-byte as they were before this session.
