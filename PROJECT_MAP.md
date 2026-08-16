# Digital Wellness AI — project map

A four-language (English · فارسی · العربية · 中文) digital-wellness app:
a trained model reads a day you log and returns an explainable score,
the reasons behind it, and what to do next.

Everything below is in this archive. Nothing here calls an external
service to work — the AI Coach can optionally use your own API key, and
the digital guide's voice is the browser's own speech engine.

---

## Run it

```bash
pip install -r requirements.txt
python run.py            # Windows: double-click start.bat
```

That is the whole thing. `run.py` starts the API, picks a free port if
8000 is taken, and opens your browser at the right address. The JWT
secret is generated on first run if unset.

> **Do not open the `frontend/` folder with a separate web server**
> (`python -m http.server`, an editor's live preview, or by
> double-clicking an `.html` file). The pages will load — they are
> plain HTML — and then sign-in fails with
> `501 Unsupported method ('POST')`, because a static file server
> implements GET and nothing else while every real action here is a
> POST. The app now detects this and says so in a banner, but the fix
> is to start it with the command above: the API serves the frontend
> itself, from the same origin.

Prefer to run uvicorn directly? `uvicorn api.main:app --port 8000`,
then open `http://127.0.0.1:8000`.

Tests: `python3 -m unittest discover -s tests` — 701 tests.

### Which build is this?

The project ships as **two builds**, and the difference is one default
that changes what the seven-day figure is allowed to be. Each build
carries a `VERSION.md` at its root saying which one it is and why.

| build | seven-day figure | default mode | doc |
|---|---|---|---|
| **Version 1** | the CLASS only — no number, deliberately | `class_only` | `docs/VERSION_1_CLASS_ONLY.md` |
| **Version 2** | a score + 80% range from the classifier's band and your own position in it | `augmented` | `docs/VERSION_2_AUGMENTED.md` |

Version 1 does not merely disable the number: the augmentation artifacts
and training modules are absent from that build, so there is nothing for
it to fall back to.

`DWAI_FUTURE_SCORE_MODE` overrides the default in either build:

| value | what the user sees seven days out |
|---|---|
| `class_only` | the CLASS only, no number |
| `augmented` | a score + range (needs the augmentation artifact) |
| `class_typical` | a class-typical band, no augmentation |

---

## Layout

```
api/            FastAPI: routers, schemas, auth, middleware
  routers/        one module per surface (prediction, league, league_chat,
                  badges, insights_cards, reports, progress, …)
  schemas/        request/response shapes — no human-readable text in any
                  response, because the client renders four languages
services/       all business logic; no framework imports
models/         training pipelines + the model manager
config/         thresholds, registries and every four-language text table
utils/          pure helpers (feature derivation, trend features, PDF i18n)
core/           the feature schema — the single source of truth for inputs
frontend/       plain HTML/CSS/JS, no build step
  assets/js/      one module per feature; window.DW* namespaces
  assets/css/     variables → base → components → page styles
artifacts/      trained models + metrics + calibration (JSON is readable)
data/           train/validation/test splits (synthetic)
app/            the original Streamlit pages, still working
tests/          701 tests
```

## The two models, and their horizons

This is the thing most easily misread, so it is stated plainly:

| model | target | horizon | validation |
|---|---|---|---|
| classifier | `future_health_class_7d` | **7 days ahead** | 90.34% accuracy, ROC-AUC 0.985 |
| regressor | `health_score_0_100` | **today** | R² 0.957, MAE 1.25 |

The seven-day **score** (Output 2) is not a third trained model. It is
the classifier's band plus your own position inside your current band —
validation MAE 1.48 against 3.31 for a baseline that just predicts
today, i.e. 55% better. A single 185-feature regressor was trained on
the same target first and lost to that baseline; its numbers are kept in
`artifacts/metrics_future_regression.json` because the comparison is the
finding.

**What is not claimed:** that R² measures how accurately a real
person's score seven days out is predicted. The target is constructed
(`models/augment_future_score.py` documents exactly how, and the
assumption it adds), and the training data is synthetic. The app says so
on screen.

## Where the four languages live

| content | file |
|---|---|
| UI strings | `frontend/assets/js/i18n.js` |
| digital guide (77 topics) | `guide-tips.js` + `guide-content-*.js` |
| badges (63) | `frontend/assets/js/badge-registry.js` |
| recommendations (13 rules) | `config/recommendation_i18n.py` |
| PDF + CSV | `services/report_i18n.py` |
| games (5) | `frontend/assets/js/games.js` |

Persian and Arabic mirror to RTL throughout, including the PDF — which
needs glyphs, shaping and direction handled separately;
`services/report_i18n.py` explains all three.

## The digital guide

| what | where | count |
|---|---|---|
| core topics | `frontend/assets/js/guide-tips.js` | 55 |
| feature topics | `frontend/assets/js/guide-content-*.js` | 40 |
| badge narrations | composed at click time from `badge-registry.js` | 63 |

Every topic exists in all four languages; nothing falls back to English.

`guide-click.js` is what makes the coverage total: it listens for any
click in the capture phase and resolves it outward from the clicked node
— badge tile → `[data-guide]` → `[data-guide-topic]` → nav link →
control table → the page's own overview. The last step is the reason
there is no silent click anywhere in the app.

Elements that already speak on their own handler mark themselves
`__dwGuideBound`, which is how nothing gets said twice.

## Privacy boundaries worth knowing

- **Awareness indicators are private.** `/badges/public` filters them
  server-side; a client bug cannot leak them into a friend's view.
- **Chat authorization is per message.** Membership is resolved from
  stored records on every read and write; knowing a conversation id is
  worth nothing.
- **Removing a friend closes the chat** in the same call that ends data
  sharing — revocation is in the data, not the interface.
- **Blocks are symmetric**, and reports are never shown to the reported
  user or used to auto-moderate.
