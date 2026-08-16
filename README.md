# Digital Wellness AI

**You log one day of habits. You get back a wellness score, the model's own reasons for it, an honest uncertainty range, a seven-day outlook, and a plan built from your weakest signals.**

Screen-time dashboards tell you *what happened* — six hours, 140 pickups. They don't tell you whether that was bad **for you**, which part of it mattered, or what to change. This project closes that gap: two trained scikit-learn models, SHAP attribution on every prediction, conformal prediction intervals instead of a softmax percentage, and a product layer that turns all of it into something a person can act on.

<sub>Python 3.10+ · FastAPI · scikit-learn 1.8.0 (pinned) · SHAP · ReportLab · no build step · no external LLM required · 4 languages incl. RTL</sub>

---

## Run it — four commands

Requires **Python 3.10 or newer**. Nothing else: no Node, no database server, no API key, no configuration file.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

Then open:

```
http://127.0.0.1:8000
```

`run.py` starts the API, serves the web UI from the same origin, and opens your browser automatically. **The trained models are committed to this repository**, so nothing has to be trained first — the app is scoring real predictions the moment it starts.

<details>
<summary>macOS / Linux</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 run.py
```
</details>

<details>
<summary>If PowerShell blocks the activation script</summary>

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```
Current window only.
</details>

> **Do not** open `frontend/` with a static file server, a "live preview" extension, or by double-clicking an `.html` file. The pages will render and then every sign-in fails with `501 Unsupported method ('POST')`, because a static server answers GET and nothing else. `run.py` exists so that cannot happen by accident.

**Two things worth knowing:** if port 8000 is busy, `run.py` moves to the next free port and prints the address — open the one it prints. And no `.env` is needed; the JWT signing key is generated on first run.

---

## If you are reviewing this project

Register an account, then **Settings → "Populate demo data"**. Pick a story and a length; it builds a complete account in one click — up to 23 days, each one scored by the same trained models a real check-in uses, with a weekly plan walked forward to the right day, history, analytics and a written journal. The demo runs in its own separate account and deleting it leaves your own data untouched.

Then look at these, in this order:

| Where | What it shows you |
|---|---|
| **Prediction result** | The score, the SHAP factors that produced it, and a conformal interval — not a confidence percentage invented from softmax |
| **Dashboard → weekly plan** | A target band whose **width is itself a fitted model**, personal to how much that user's days actually move |
| **What-if / future paths** | Simulations that re-run the real trained model on modified inputs, not a formula approximating it |
| **Analytics → deep facts** | A second model fitted on *that one user's days only*, reporting leave-one-out R² beside the in-sample one |
| **Model performance page** | Every metric below, read live from `artifacts/*.json` rather than typed into the UI |
| **`/docs`** | 105 endpoints, Swagger, full request/response schemas |
| **[Limitations](#limitations)** | What this project does *not* claim — stated before you have to go looking |

---

## What it actually does

```
Daily check-in (53 fields)  ──▶  validation  ──▶  shared feature derivation
                                                          │
                             ┌────────────────────────────┴───────────────────────────┐
                             ▼                                                        ▼
              Regressor: today's score 0–100                   Classifier: health class 7 days ahead
                             │                                                        │
                             ▼                                                        ▼
                   SHAP attribution                       class probabilities ──▶ 7-day score band
                             │                                                        │
                             └──────────────────────────┬─────────────────────────────┘
                                                        ▼
      conformal interval · recommendations · what-if · weekly plan · history · personal model
```

**Two horizons, kept apart on purpose.** The score is about *today*; the class is about *next week*. Both are labelled with their horizon everywhere they appear, because showing them together unlabelled reads as a forecast nobody made.

| Capability | What it does |
|---|---|
| Wellness score | Real regressor output, 0–100, for the day you logged |
| 7-day outlook | Classifier's health class plus a typical band for that class, both horizon-labelled |
| SHAP explanation | The factors that pushed *this* prediction up or down |
| Conformal interval | Distribution-free coverage guarantee, not a softmax number |
| Recommendations | Direction-aware, keyed to your weakest signals, each with a success metric |
| What-if & goal-seek | Sweep a habit, or solve for a target score, re-running the real model |
| Weekly plan | Frozen per ISO week, days unlock in order, aimed at a personally-fitted band, with a violation ledger |
| History & analytics | Trends, weekday patterns, before/after, streaks, personal bests |
| Personal dossier | Cohort position, a per-user model, facts computed from your own days |
| Journal | One page per day, exportable as PDF; never fed to any model |
| Digital Coach | Local rule-based chat over your own data, with crisis and medical guardrails |
| Friends League | Two-sided consent, per-category sharing, private chat, revocable |
| Privacy controls | Export everything stored about you as JSON, or delete the account and every store attached to it |
| Demo Mode | 32 fixed states — 4 stories × 4 lengths × kept-up/lapsed — built from real model inference |

---

## The machine learning, honestly

### Shipped models — measured on a held-out, group-isolated split

| Task | Model | Target | Metric | Test result |
|---|---|---|---|---|
| Health class, 7 days ahead | `HistGradientBoostingClassifier` | `future_health_class_7d` | Accuracy / macro-F1 / ROC-AUC | **0.898** / 0.900 / **0.980** |
| Wellness score, today | `HistGradientBoostingRegressor` | `health_score_0_100` | MAE / RMSE / R² | **0.99** / 1.35 / **0.981** |
| Weekly band half-width | `HistGradientBoostingRegressor` + CQR | \|next day − running mean\| | Coverage @ target 0.90 | **0.893** |
| Behavioural persona | `KMeans` (k=5) | unsupervised | Silhouette | 0.078 |

Both supervised models were selected over Logistic Regression and Random Forest baselines by a score that penalises the train/validation overfit gap. `artifacts/metrics*.json` records **every** candidate's numbers, not only the winner's.

### Leakage prevention

The split is **grouped, not random**. `StratifiedGroupKFold(n_splits=18)` groups rows by a ten-column demographic/behavioural signature so the same synthetic respondent cannot appear on both sides. Verified in `artifacts/leakage_verification_report.json`: **90,351 rows across 3,216 groups → 2,861 / 175 / 180 groups** in train/validation/test, with **all three pairwise group intersections equal to 0**.

`day_index` and any cumulative counter are excluded from the feature set: the generator wrote each respondent's trajectory against a day counter, so they predict the target well and mean nothing for a real person. The measurement is in `models/research_classification_trend.py`.

### What the score measures — and why it was rebuilt

`health_score_0_100` is not a raw column; it is constructed. That makes its definition part of the result, so it is stated here.

The dataset ships six composite subscores — sleep, night use, focus, balance, stress/fatigue, activity. They describe how a person *slept and felt*. **None of them measures how long the screen was on.** Averaging the six produced a "digital wellness" score correlating **+0.105** with total screen minutes and **+0.034** with recreational minutes — nothing, and the wrong sign, in an application about digital load.

A seventh subscore fixes that, and where its thresholds come from matters more than the arithmetic. `utils/screen_load.py` uses published guidelines, cited in the module:

- **Recreational volume** — free to the **two-hour** recommendation, then a logistic dose-response curve. Both parameters are *derived, not chosen*: the literature puts the sharp rise between two and four hours, so the midpoint is that band's centre and the steepness makes the curve's own middle half span exactly that band. The result reads in whole fractions — 2 h costs nothing, 3 h a third, 4 h two thirds, 6 h ~95%.
- **Pre-sleep use** — its own risk, not a share of the total. Free to **30 minutes**, the stricter of the two published cut-offs.
- **Work and study** — every threshold in the research is about *recreational* use, so work screen time is free to a full working day and gently charged past it.

**The weight is a measurement, not a preference.** The screen-load subscore has σ = 33.4 against 7.9 for the mean of the six, so counting terms does not describe the balance. At weight 3 the score correlates −0.844 with recreational minutes and only +0.425 with the six — a screen-minute readout wearing a wellness score's name. At **weight 2**: **−0.754** and **+0.577**. The full table is in `models/data_loader.py`.

### Where a claim could not be supported, it was dropped

- A **seven-day regressor was trained and is not shipped** — it failed its own baseline check (`beats_baseline: false`). The seven-day figure is a class band because that is what the data supports.
- The seven-day class label is **real ground truth** and was never rewritten. It was measured instead: it tracks screen *timing* correctly (night ratio −0.646) and screen *volume* with the sign inverted (+0.106). No feature engineering fixes that — the signal is not in the target. So the volume half of the guidance comes from the score, which measures it directly, and never from the class.
- The **per-user model refuses to fit below eight days** and leads with leave-one-out R², because in-sample R² flatters at that sample size.

### Read the regressor's R² carefully

It is 0.981, and that is not the model being brilliant. `health_score_0_100` is a deterministic function of seven subscores; all seven are excluded from the feature set, but the raw fields they are computed from *are* features, so a flexible model can partly reconstruct the target by construction. **The number that carries weight is the classifier's**, whose target is a genuine label nothing in the feature set can reconstruct.

### The data is synthetic

Every metric above is a real measurement on a held-out split of **synthetic** data. They say the pipeline learns its target cleanly. They do **not** say anything has been validated against human outcomes, and none of it is medical advice.

---

## Architecture

```
frontend/          14 pages, 80 JS modules in 7 folders, 10 stylesheets, no build step
   │  fetch → /api/v1
api/               FastAPI: 24 routers, 105 endpoints, Pydantic v2 schemas, JWT auth
   │
services/          ml/         models, SHAP, conformal uncertainty, persona, cohort
   │               wellness/   recommendations, weekly plan, violations, decline check
   │               insight/    trends, future paths, what-if, the per-user model
   │               identity/   accounts, history, journal, CSV, reports
   │               social/     League, chat, badges, achievements
   │               demo/       the 32 demo states
   │               storage/    JSON or SQLite behind one interface, with migrations
models/            registry + training scripts
artifacts/         the fitted models, feature columns, metrics, calibration, leakage report
core/              feature schema, DTOs, one definition of where the project's folders are
tests/             1,881 tests in 129 files, grouped to mirror services/
legacy/            the original Streamlit UI, kept as provenance, never run
.github/workflows/ CI: suite · frontend · hygiene · smoke
```

**Roughly 72,000 lines of Python, 32,000 of JavaScript, 27,000 of tests.**

The FastAPI app mounts `frontend/` as static files, so UI and API are same-origin and there is no second server to run. Training and live inference call **the same feature-derivation function**, so a feature cannot be computed one way at fit time and another at predict time.

**One rule holds the layout together:** nothing computes a directory by walking up from its own file. `core/paths.py` is the single definition, and a test enforces it — that pattern silently broke this repository three times, most expensively when fourteen services wrote user data into the wrong folder.

---

## Testing and CI

```bash
python -m unittest discover -s tests -t .            # everything
python -m unittest discover -s tests/wellness -t .   # one area
```

**1,881 tests across 129 files, all passing, in ~410 s** at the current commit.

Four CI jobs run on every push (`.github/workflows/ci.yml`), deliberately separate because they fail for unrelated reasons:

| Job | What it proves |
|---|---|
| **Python suite** | The full suite, on both storage backends |
| **Frontend and coach** | Every JS module parses; the coach's runners execute under Node against the real frontend files |
| **Repository hygiene** | No user data tracked, no populated secrets in `.env.example`, no reset token in a response |
| **It actually starts** | The app boots, loads models, serves a real register→refresh→reset flow, and logs no unhandled errors |

The coach's own measured properties, enforced by tests rather than asserted in prose:

- **Recall 98.2%** over a 7,935-case corpus of phrasings and typos — en 99.3 / fa+ar 99.4 / zh 94.6. Chinese trails because the corpus probes single characters, which are genuinely ambiguous.
- **Precision**: off-topic questions are declined rather than answered confidently.

---

## Security and privacy

- **Argon2** password hashing (`pwdlib`); dummy-verify on unknown accounts so timing does not leak existence; per-email login throttle.
- **JWT** bearer tokens; a **revocable, single-use refresh token** carries the session, and a replayed one revokes every session the account has.
- **Password reset codes are emailed, never returned over HTTP.** They used to be in the response body, which made knowing an address enough to take over the account.
- **Per-user isolation** — history is keyed `(user_id, date)`; every read and write is scoped to the authenticated account.
- **Server-side validation** — bounds and types per field, reported per-field in a 422, never silently coerced.
- **Privacy endpoints** — export everything stored about you; delete the account and every store attached to it.
- **`storage/` is gitignored and never shipped.** It holds real accounts and real logged history. It reached a public branch once; see [`SECURITY.md`](SECURITY.md), which also covers the part gitignoring cannot fix.

---

## Limitations

Stated plainly, because a reviewer will find them anyway.

1. **The training data is synthetic.** Nothing here has been validated against human outcomes, and none of it is medical advice.
2. **The seven-day score is a class-typical band, not a personal projection.**
3. **The persona clustering is weak.** Silhouette 0.078 at k=5 — a descriptive lens, not a finding.
4. **The per-user model is small by construction** — ridge on one person's days, which is why leave-one-out R² leads.
5. **The band model under-covers the users who move most.** 0.893 marginal coverage against a 0.90 target, but the most volatile third only reach 0.840. Better than the best constant's 0.764, and not 0.90. Three ablations are recorded in `artifacts/metrics_band.json` rather than rounded away.
6. **Storage defaults to JSON files with file locking** — single-instance only. A SQLite backend with migrations ships behind `DWAI_STORAGE_BACKEND=sqlite`.
7. **The Digital Coach is rule-based, not an LLM**, and says so. An external provider is opt-in and off by default.
8. **Text-to-speech depends on the device.** The guide only speaks a language the device has a voice for, rather than mispronouncing it.
9. **The Streamlit UI in `legacy/` is frozen** and is not maintained alongside the primary frontend.

---

## Optional configuration

Everything below is optional; the app runs fully without a `.env`. Copy `.env.example` to `.env` to set any of it.

| Variable | Purpose |
|---|---|
| `JWT_SECRET_KEY` | Signs access tokens. Auto-generated on first run; set explicitly for a real deployment. |
| `GITHUB_CLIENT_ID` / `_SECRET` / `_REDIRECT_URI` + `SESSION_SECRET_KEY` | GitHub sign-in |
| `SMTP_HOST` and friends | Real password-reset and verification emails. Without them, codes go to the server log — never to the caller. |
| `DWAI_STORAGE_BACKEND=sqlite` | SQLite instead of JSON files |

**Docker:**

```bash
docker build -t digital-wellness-api .
docker run -p 8000:8000 --env-file .env digital-wellness-api
```

---

## Deeper documentation

The README is the entry point; [`docs/`](docs/README.md) indexes the rest.

| Document | Contents |
|---|---|
| [`docs/reports/SCREEN_LOAD_ROOT_FIX.md`](docs/reports/SCREEN_LOAD_ROOT_FIX.md) | How the score's definition was rebuilt on published thresholds, and the four stale copies of it that were found |
| [`docs/reports/ML_AUDIT_REPORT.md`](docs/reports/ML_AUDIT_REPORT.md) | ML pipeline audit |
| [`docs/reports/BAND_MODEL_REPORT.md`](docs/reports/BAND_MODEL_REPORT.md) | The personal weekly band: why the constant was wrong, and what replaced it |
| [`docs/reports/LEAKAGE_FIX_REPORT.md`](docs/reports/LEAKAGE_FIX_REPORT.md) · [`USER_LEAKAGE_FIX_REPORT.md`](docs/reports/USER_LEAKAGE_FIX_REPORT.md) | How the grouped split was arrived at |
| [`docs/reports/HARDENING_REPORT.md`](docs/reports/HARDENING_REPORT.md) | Account-takeover fix, refresh tokens, email verification, drift monitoring |
| [`docs/reports/FINAL_QA_REPORT.md`](docs/reports/FINAL_QA_REPORT.md) | Every sweep run against this build, and what is still not done |
| [`SECURITY.md`](SECURITY.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`VERSION.md`](VERSION.md) | Security notes, contribution guide, version history |

---

## What makes it different

Not the score. The score is one `predict()` call.

What is unusual is that the *whole chain* is present and honest end to end: a grouped split that provably isolates respondents, one feature-derivation path so training and inference cannot drift, SHAP attributions from the actual prediction, conformal intervals instead of softmax theatre, recommendations derived from your own weakest signals, simulation that re-runs the real model, a weekly plan that remembers what you did, and a second model fitted on nothing but your own days.

And where the pipeline could not honestly support a claim, the claim was dropped rather than dressed up. A seven-day regressor was trained, failed its baseline, and is not shipped. The seven-day figure is a class band because that is what it is. The per-user model refuses to fit below eight days. **The refusals are part of the design, and they are tested.**
