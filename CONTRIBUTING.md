# Contributing to Digital Wellness AI

A practical guide to working in this codebase. Not a legal agreement.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional; run.py generates a JWT secret if absent
python run.py
```

`run.py` is the way to start it. It picks a free port, serves the API and
the frontend from one origin, and refuses to start a second copy beside a
running one. `uvicorn api.main:app --reload` also works while iterating on
the backend, but the frontend's own guard will tell a user who opened the
pages any other way that they did — see the note in `run.py`'s docstring
for the evening that cost.

Trained artifacts under `artifacts/` are committed, so nothing needs
training to run the app. The raw CSVs under `data/` (93 MB, not committed)
are only needed to change training or evaluation code.

## Tests

```bash
python3 -m unittest discover -s tests -t .            # all 1,710
python3 -m unittest discover -s tests/wellness -t .   # one area
python3 -m unittest tests.api.test_auth_hardening -v  # one file
```

**unittest, not pytest** — pytest is not a dependency and the suite does
not use its fixtures. The `-t .` is not optional; it sets the top-level
directory, and without it every import inside a test resolves against
`tests/` instead of the project root.

`tests/README.md` explains the layout and the two rules that keep it
working. Run the full suite before opening a PR. A handful of tests need
`data/*.csv` and skip cleanly without them.

## Conventions

**Layering points one way.** `api/routers/*.py` stay thin: validate, call
a service, shape the response. Business logic lives in `services/`.
`services/` may import other service packages, `core/`, `utils/` and
`config/` — never `api/`. See `api/routers/whatif.py` for the pattern:
`Depends()`-injected services, a `ValidationService.validate()` call for
anything user-supplied, and a Pydantic model in `api/schemas/`.

**One definition of the project root.** `core/paths.py`. Never write
`Path(__file__).resolve().parents[N]` — it does not raise when it is
wrong, it just points somewhere else. Fourteen services wrote into
`services/storage/` for half an hour because of exactly this, and
`tests/_test_support.py` is the single file allowed to do it (it is what
puts the root on `sys.path`, so it cannot import `core` to find it).

**`core/feature_schema.py` is the only source of truth** for what a
prediction input looks like. Never write a second copy of a field's
bounds; read `FEATURE_SCHEMA`.

**Never bypass `ValidationService`** on anything reaching
`PredictionService`. It is what keeps out-of-range values away from the
trained models.

**Training and inference must call the same derivation.**
`utils/feature_derivation.py`. A feature computed one way at fit time and
another at predict time is a bug that produces plausible wrong numbers
and never raises.

**Storage goes through `StorageBackend`.** A service that opens a file
directly cannot be tested against a temp directory and cannot run on
SQLite. Every service takes an injectable backend; that is why a database
could be added without editing any of them.

**The frontend has no build step.** Vanilla HTML/CSS/JS, one controller
per page in `frontend/assets/js/pages/`, shared code in the sibling
folders (`core/`, `chrome/`, `guide/`, `coach/`, `about/`, `features/`).
A new page loads `core/shell.js` and calls `window.DWShell.init(...)` —
skipping that is how a page silently loses its language, its music and
its navigation.

**New user-facing text needs an i18n key** in every language block of
`frontend/assets/js/core/i18n.js`. English and Persian at minimum; Arabic
and Chinese fall back to English. Server-produced text that a user reads
travels as `text_i18n: {lang: text}` rather than being translated in the
browser.

**The Digital Coach has no external LLM dependency.** It answers from
rules, its refusals are guaranteed rather than probable, and its coverage
is measured (`tests/js/`). An external provider is opt-in, off by default,
called straight from the browser, and its key never touches the backend.
See `frontend/assets/js/coach/coach-chat.js`'s header before changing any
of that.

**Say what you cannot support.** Where a claim is not backed by a
measurement, the pattern in this repository is to drop the claim rather
than soften it: a seven-day regressor was trained, failed its baseline,
and is not shipped; the band model refuses to write an artifact that does
not beat the best constant. Follow that.

## Before opening a PR

1. `python3 -m unittest discover -s tests -t .` — the full suite passes.
2. Touched Python? `python3 -m compileall -q <changed files>`, and
   `ruff check` if you have it (not a dependency).
3. Touched frontend JS? `node --check <file>` — nothing else parses it.
4. Touched storage or a service? Run the API tests against both engines:
   `DWAI_STORAGE_BACKEND=sqlite python3 -m unittest discover -s tests/api -t .`
5. Describe *why*, not just what. The comments in this codebase explain
   the failure they prevent; PR descriptions should too.

CI runs 1–4 on every push. It is not a substitute for running them.
