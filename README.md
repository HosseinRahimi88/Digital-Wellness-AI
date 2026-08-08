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
- **Progress tracking** — history, weekly rule-based improvement plans, streaks, and a downloadable PDF wellness report.
- **What-if simulation & Future Paths** — sweep a single habit, goal-seek a target score, or compare named future scenarios (Status Quo vs. Digital Detox, etc.) using the real trained model.
- **Multilingual & accessible** — English/Arabic/Chinese/Persian (with full RTL support), dark/light themes, and a `prefers-reduced-motion`-aware UI.
- **Privacy-first** — predictions are computed from the user's own data only; nothing is sold or shared; any optional AI Coach API key lives in memory for the browser tab only and is never persisted or transmitted.

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

**Typical flow:** register → optional onboarding → daily check-in (manual entry or a demo profile) → real-time prediction with an explained score → dashboard, weekly plan, AI Coach, analytics, and what-if simulation, all driven by that same real prediction.

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

All endpoints except `/health*`, `/auth/register`, and `/auth/login` require a `Authorization: Bearer <token>` header.

---

## 🧪 Testing

```bash
python3 -m pytest tests/ -v
```
The suite covers the ML pipeline, validation, recommendations, auth/JWT (including attack vectors), concurrency, and API integration — 372 tests in total. A handful of tests that require the raw training CSVs (not committed, see `.gitignore`) will report `FileNotFoundError` unless you place your own `data/{train,validation,test}.csv`; every other test runs standalone against the committed model artifacts.

---

## 📄 License & Team

This project was built as a research/hackathon submission. No external LLM dependency, no third-party data sharing — predictions are computed entirely from the artifacts in this repository. Add your team's license of choice here before public release.
