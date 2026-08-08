# 🧠 Digital Wellness AI

**Turn your daily screen habits into an honest, explainable wellness score — and a real plan to improve it.**

Digital Wellness AI is a full-stack machine learning application that predicts a person's digital wellness from their real daily habits (screen time, sleep, notifications, mood, focus, activity). Every prediction ships with a SHAP-based explanation of *why*, a calibrated confidence/uncertainty estimate, and personalized, guardrail-checked recommendations — never a black-box number.

---

## ✨ Features

- **Real ML predictions, not rules** — a trained classifier (risk category) and regressor (0–100 wellness score) run on every check-in, built on `HistGradientBoosting` models.
- **Explainable by design** — every score comes with SHAP feature attributions, so users see exactly what pushed it up or down, in plain language.
- **Wellness dimension breakdown** — a transparent, non-ML rollup of the same inputs into Sleep, Focus & Productivity, Emotional Wellbeing, Screen Habits, and Physical & Lifestyle, shown alongside the model's own score.
- **Personalized recommendations** — SHAP-driven, direction-aware (never tells a thriving user to "fix" their best trait), with a "don't coach me on this" opt-out per topic.
- **Uncertainty-aware** — split-conformal prediction intervals and a plain-language confidence label, not just a raw probability.
- **AI Coach** — a local, rule-based conversational layer that answers questions using the user's *own* real prediction data, with crisis/medical guardrails and an honest "I don't have enough data for that" fallback. No mandatory external LLM dependency.
- **Persona detection** — unsupervised clustering surfaces a behavioral persona (e.g. "Fragmented-Attention Night-Owl") independent of the risk prediction.
- **Weekly plans & reports** — history, rule-based 7-day improvement plans, and a downloadable PDF wellness report.
- **What-if simulation & Future Paths** — sweep a single habit, goal-seek a target score, or compare named future scenarios (Status Quo vs. Digital Detox, etc.) using the real trained model.
- **Multilingual & accessible** — English/Arabic/Chinese/Persian (with full RTL support), dark/light themes, and a `prefers-reduced-motion`-aware UI.
- **Digital Guide** — a contextual help layer that explains every page, every section and every check-in step on demand, in English or Persian.
- **Persona identity & badges** — a transparent, rule-based archetype ("The Night Owl", "The Deep Worker", …) with the exact numbers that earned it, shown alongside the statistical ML persona.
- **Progress tracking** — small wins, personal bests, streaks, before/after comparison and a decision replay of how you got here.
- **Trust signals** — a plain-language confidence label, an out-of-distribution warning when inputs sit at the edge of what the model has seen, and an honest cold-start status.
- **Bulk CSV import** — download a filled template, log several days at once, and every valid row runs a real prediction into your history.
- **Privacy controls** — export everything stored about you as a file, or delete your account and history permanently.
- **Privacy-first** — predictions are computed from the user's own data only; nothing is sold or shared; any optional AI Coach API key lives in memory for the browser tab only and is never persisted or transmitted.
- **Four-arc score ring** — the real regression score stays the primary number; four surrounding arcs (life/emotional, sleep, digital, focus) show the dimension breakdown with a genuine water-wave fill animation, a gradient per arc, and a completion "ding".
- **Sound engine** — synthesized (Web Audio API, no audio files) processing hum, water-fill cues, arc-completion dings, and a happy/sad result stinger — independently toggleable from the ambient music, in Settings or next to the music widget.
- **Personalized result page** — the Digital Guide's comment on your result is built from your own top SHAP factor and weakest dimension (never a canned line), recommendations show the exact number that earned them, and the result page itself carries an inline 7-day roadmap and a "talk to your future self" block using real re-runs of the trained model on named future patterns.
- **Our own AI: 50+ command menu** — a rule-based "AI" (openly, not claimed to be an LLM) answers 50+ ready-made questions plus free-text chat, entirely from your current real data; answers never repeat stale text once your data changes, and are tagged "updated" the first time they reflect a change.
- **Optional external connector** — OFF by default, outside this project's no-external-API competition scope: an opt-in bring-your-own-key mode that calls a provider directly from the browser (never through this app's backend) once explicitly enabled.
- **Friends League** — two-sided, per-category consent: a friend sees nothing until they enter your invite code *and* you explicitly approve, and you each independently choose exactly which categories (persona/score/rank/top factor) to share — revocable at any time. Framed as you-vs-your-own-past first, friends shown alongside.
- **Demo Mode** — one click builds 23 days of real-model-scored history (synthetic inputs, genuine predictions) plus a connected demo League friend, for exploring or recording a walkthrough without logging real days first.
- **Weekly shareable card** — a downloadable PNG summary of your real week (score, streak, persona, top factor), rendered entirely client-side.
- **Guided intro tour** — a skippable, auto-advancing first-run slideshow covering every major section including Settings and a detailed walkthrough of the Friends League consent model, replayable any time from Settings.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI, Pydantic v2, Uvicorn |
| **ML / Data** | scikit-learn (`HistGradientBoostingClassifier`/`Regressor`), SHAP, pandas, NumPy |
| **Auth** | JWT (`PyJWT`) + Argon2 password hashing (`pwdlib`) |
| **Frontend** | Vanilla HTML / CSS / JavaScript (no framework, no build step) — served directly by FastAPI |
| **Reports** | ReportLab (PDF generation) |
| **Legacy UI** | Streamlit (`app/`) — an earlier, parallel UI kept in the repo; the FastAPI + vanilla-JS frontend under `frontend/` is the primary, actively developed interface |
| **Testing** | pytest |

---

## 🚀 Installation & Setup

### Prerequisites
- Python **3.10+**
- pip

### 1. Clone and install dependencies
```bash
git clone <repo-url>
cd Digital-Wellness-AI
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables
Copy the template and fill in a real secret:
```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```
Paste the generated value into `.env` as `JWT_SECRET_KEY=...`. See [`.env.example`](.env.example) for every available setting.

> Trained model artifacts (`artifacts/*.pkl`, `*.json`) are already committed — no training step is required to run the app. Only the raw training CSVs under `data/` are excluded from the repo, and they're only needed if you intend to retrain the models.

### 3. Run the API + frontend
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```
Wait for `Startup complete ... ready to serve.` in the logs (this pre-warms the ML models once, at startup, so no request ever pays that cost).

### 4. (Optional) Run the legacy Streamlit UI instead
```bash
streamlit run app/Home.py
```

### Run with Docker
```bash
docker build -t digital-wellness-ai .
docker run -p 8000:8000 --env-file .env digital-wellness-ai
```

---

## 📖 Usage

Once the server is running, open your browser to:

| URL | What it is |
|---|---|
| `http://localhost:8000/` | The app itself (landing page → sign up → daily check-in) |
| `http://localhost:8000/docs` | Interactive Swagger UI — try any endpoint directly |
| `http://localhost:8000/health` | Liveness check |
| `http://localhost:8000/health/ready` | Readiness check (confirms models are loaded) |

**Typical flow:** register → optional onboarding (or Demo Mode, from Settings, to populate 23 realistic days instantly) → daily check-in (manual entry, a demo profile, or CSV import) → real-time prediction with an explained score, a 4-arc dimension ring, an inline 7-day roadmap and a "talk to your future self" projection → dashboard, weekly plan (with a downloadable card), AI Coach (50+ command menu + free chat), analytics, Friends League, and what-if simulation, all driven by that same real prediction.

---

## 📁 Project Structure

```
Digital-Wellness-AI/
├── api/                    # FastAPI application
│   ├── main.py             #   App factory, middleware, router registration, startup warm-up
│   ├── routers/            #   One module per resource (auth, predict, history, analytics, ...)
│   ├── schemas/             #   Pydantic request/response models
│   ├── dependencies/        #   FastAPI DI providers (service singletons)
│   ├── middleware/          #   Security headers, request ID, body-size limits
│   └── auth/                #   JWT auth dependency
├── frontend/                # Primary UI: vanilla HTML/CSS/JS, served by FastAPI
│   ├── *.html               #   One file per page (landing, check-in, dashboard, coach, ...)
│   └── assets/{css,js,img}  #   Shared styles, scripts, and images
├── app/                     # Legacy Streamlit UI (kept alongside the FastAPI frontend)
├── models/                  # Training, evaluation, and model-artifact management
│   ├── train_classification.py / train_regression.py / train_persona.py
│   ├── model_manager.py     #   Process-wide singleton that loads all trained artifacts once
│   └── preprocessing.py     #   Feature/target column definitions, leakage exclusions
├── services/                 # Business logic layer (framework-agnostic)
│   ├── prediction_service.py, recommendation_service.py, shap_service.py
│   ├── uncertainty_service.py, persona_service.py, history_service.py, ...
│   └── storage/              #   JSON-file-backed storage backend
├── core/                    # Shared feature schema and DTOs
├── config/                  # Static configuration (recommendation registry, demo profiles, ...)
├── utils/                   # Pure helper functions (feature derivation, dimension scores, tokens)
├── artifacts/                # Trained model files + metrics (committed to the repo)
├── tests/                   # pytest suite
└── requirements.txt
```

---

## 🔌 API Documentation

Full interactive documentation (with live request/response trying) is always available at **`/docs`** once the server is running. Summary of the main endpoints, all under `/api/v1` unless noted:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check (no auth, no model access) |
| `GET` | `/health/ready` | Readiness check — confirms trained models are loaded |
| `POST` | `/auth/register` | Create an account |
| `POST` | `/auth/login` | Log in, receive a JWT |
| `GET` | `/auth/me` | The authenticated account's profile |
| `PUT` | `/auth/me/onboarding` | Save onboarding preferences |
| `GET` | `/schema/features` | The full input feature schema (types, bounds, choices) |
| `GET` | `/schema/demo-profiles` | Pre-built demo profiles for quick testing |
| `POST` | `/predict` | **Core endpoint** — runs classification + regression + SHAP + uncertainty + recommendations on real input |
| `GET` | `/history` | Paginated prediction history |
| `GET` | `/history/{entry_date}` | A single day's entry |
| `GET` | `/history/weeks/current` \| `/weeks/previous` | Aggregated weekly summaries |
| `GET` | `/analytics/summary` | Historical trend analytics |
| `POST` | `/whatif/sweep` \| `/whatif/goal-seek` | Sensitivity sweep / goal-seeking over one input field |
| `GET` | `/future-path/definitions` · `POST` `/future-path/compare` | Compare named future behavior scenarios |
| `POST` | `/parallel-twin/compare` | Compare against a hypothetical "improved twin" of the user |
| `POST` | `/personas/assign` | Behavioral persona assignment |
| `GET` | `/cohorts/availability` \| `/summary` \| `/percentile` \| `/me/comparison` | How the user compares to the wider population |
| `POST` | `/plan` · `PUT` `/plan/tasks` | Generate / update the rule-based weekly improvement plan |
| `GET` | `/model-performance` | Real, current model metrics (accuracy, R², etc.) |
| `POST` | `/reports/pdf` | Generate a downloadable PDF wellness report |
| `GET` | `/schema/csv-template` | Download the bulk-import CSV template (with filled examples) |
| `POST` | `/history/import-csv` | Bulk-import several days from a CSV |
| `PUT` | `/history/{date}/exclude` | Mute/unmute one day from trend and average calculations |
| `GET` | `/schema/data-dictionary` | Plain-language docs for every input field |
| `GET` | `/progress/summary` | Small wins, personal bests, before/after, decision replay |
| `GET` | `/insights` | Cold-start status and per-weekday reliability |
| `GET` | `/personas/identity` | Rule-based persona title, alternates and earned badges |
| `PUT` | `/auth/me/profile-extras` | Save avatar and recommendation tone |
| `GET` | `/privacy/export` · `/privacy/export.json` | Export everything stored about you |
| `DELETE` | `/privacy/me` | Permanently delete account and all history |
| `GET`/`POST` | `/league/me` · `/league/rules/accept` | Your invite code, League status, rules acceptance |
| `POST` | `/league/invite/redeem` | Send a connection request via a friend's invite code |
| `GET` | `/league/requests/pending` | Requests waiting for your approval (the in-app notification inbox) |
| `POST` | `/league/requests/{id}/respond` | Approve/decline a request, choosing what you share back |
| `GET`/`PUT`/`DELETE` | `/league/connections[/{id}/sharing]` | List, adjust, or revoke a League connection |
| `GET` | `/league/leaderboard` | You-vs-your-past plus friends' explicitly shared categories |
| `POST` | `/demo/populate` | Populate 23 days of real-model-scored demo history plus a demo League friend |

All endpoints except `/health*`, `/auth/register`, and `/auth/login` require a `Authorization: Bearer <token>` header.

---

## 🧪 Testing

```bash
python3 -m pytest tests/ -v
```
The suite covers the ML pipeline, validation, recommendations, auth/JWT (including attack vectors), concurrency, the Friends League consent model, and API integration — 424 tests in total. A handful of tests that require the raw training CSVs (not committed, see `.gitignore`) will report `FileNotFoundError` unless you place your own `data/{train,validation,test}.csv`; every other test runs standalone against the committed model artifacts.

---

## 📄 License & Team

This project was built as a research/hackathon submission. No external LLM dependency, no third-party data sharing — predictions are computed entirely from the artifacts in this repository. Add your team's license of choice here before public release.
