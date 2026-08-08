# Contributing to Digital Wellness AI

Thanks for taking a look at the project. This is a short, practical guide to working in this codebase — not a legal agreement.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in JWT_SECRET_KEY, see the file for how
uvicorn api.main:app --reload
```

Trained model artifacts under `artifacts/` are committed, so you don't need to train anything to run or modify the app. You only need the raw CSVs under `data/` (not committed) if you're changing training/evaluation code itself.

## Running tests

```bash
python3 -m pytest tests/ -v
```

Run the full suite before opening a PR. A handful of tests need `data/{train,validation,test}.csv`, which aren't committed — they'll fail with a clear `FileNotFoundError` in an environment without them; that's expected and unrelated to your change.

## Project conventions

- **Layering is intentional — keep it.** `api/routers/*.py` should stay thin: validate the request, call into `services/`, shape the response. Business logic belongs in `services/`, not in a router. If you're adding a new endpoint, look at an existing router (e.g. `api/routers/whatif.py`) for the pattern: `Depends()`-injected services, a `ValidationService.validate()` call for any user-supplied `user_data`, and a Pydantic response model in `api/schemas/`.
- **`core/feature_schema.py` is the single source of truth** for what a prediction input looks like (types, bounds, choices). Never hardcode a second copy of a feature's bounds anywhere else — read from `FEATURE_SCHEMA`.
- **Never bypass `ValidationService`** for anything that reaches `PredictionService`. It's what keeps out-of-range/malformed values away from the trained models.
- **The trained models are inputs, not something routine changes touch.** If a change affects model behavior, training, or evaluation, say so explicitly in your PR description and re-run the metrics — don't silently retrain and swap `artifacts/*.pkl` in an unrelated change.
- **The frontend (`frontend/`) has no build step.** Vanilla HTML/CSS/JS, one file per page, shared code in `frontend/assets/js/`. Keep new pages consistent with the existing pattern (a `<page>.js` controller calling `window.DWShell.init(...)`, then `window.DWApi.*` for network calls).
- **New user-facing text needs an i18n key**, not a hardcoded string — add it to every language block in `frontend/assets/js/i18n.js` (English and Persian at minimum; Arabic/Chinese fall back to English automatically if you don't have a translation).
- **The AI Coach has no external LLM dependency.** Keep it that way unless a maintainer explicitly decides otherwise — see `frontend/assets/js/coach-chat.js`'s header comment for the reasoning and the guardrails that would need to carry over.

## Before opening a PR

1. `python3 -m pytest tests/ -v` — full suite passes (see the data-file caveat above).
2. If you touched Python: `python3 -m ruff check <changed files>` — no new warnings.
3. If you touched frontend JS: `node --check <changed file>.js` — no syntax errors.
4. Describe *why* the change is needed, not just what changed — future readers (including future you) will thank you.
