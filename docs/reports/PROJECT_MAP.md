# Project map

Where everything is, and why it is there. Regenerate the counts with
`bash scripts/count-code.sh` if they drift.

```
Digital-Wellness-AI/
│
├── run.py                  The only way to start it. Picks a free port,
│                           starts the API, serves the frontend from the
│                           same origin, opens a browser. Refuses to start
│                           a second copy beside a running one.
├── start.bat / start.sh    Double-click wrappers for the same thing.
│
├── api/                    FastAPI. 24 routers, 94 endpoints.
│   ├── routers/            One file per feature area.
│   ├── schemas/            Pydantic request/response shapes.
│   ├── dependencies/       Service construction, injectable for tests.
│   ├── auth/               Bearer-token resolution.
│   ├── middleware/         TrustedHost, CORS, size limit, headers.
│   └── exceptions/         The error envelope every route shares.
│
├── services/               All the behaviour. Six packages by subject.
│   ├── ml/                 Models, SHAP, conformal uncertainty, persona,
│   │                       cohort, the weekly-band model, input drift.
│   ├── wellness/           Weekly plan, its band, violations, decline
│   │                       check, recommendations, tone.
│   ├── insight/            Trends, what-if, future paths, the per-user
│   │                       ridge model, personal facts.
│   ├── identity/           Accounts, OAuth, history, journal, CSV,
│   │                       reports, mail, refresh tokens.
│   ├── social/             League, chat, badges, achievements, coins.
│   ├── demo/               The 32 fixed demo states.
│   └── storage/            JSON or SQLite behind one interface, plus
│                           migrations and the JSON→SQLite importer.
│
├── models/                 Training scripts and the artifact registry.
│                           Nothing here runs at request time except the
│                           registry, which loads the pickles once.
├── artifacts/              What training produced: three shipped models,
│                           feature columns, metrics, calibration, the
│                           leakage report, the cohort reference grid.
├── data/                   The synthetic CSVs. Gitignored - 93 MB.
│
├── core/                   Things every layer needs and none owns:
│                           the 53-field schema, DTOs, and paths.py -
│                           the ONE definition of where the project is.
├── utils/                  Pure functions: feature derivation, tokens,
│                           password hashing, band features.
├── config/                 Static tables: exercise library, demo
│                           profiles, onboarding options, thresholds.
│
├── frontend/               13 pages, 78 JS modules, 9 stylesheets. No
│   ├── assets/js/          framework, no build step.
│   │   ├── core/           api, i18n, theme, motion, modal, shell
│   │   ├── chrome/         mascot, music, sound, navbar
│   │   ├── guide/          the Digital Guide
│   │   ├── coach/          the Digital Coach + AI connector
│   │   ├── pages/          one controller per page
│   │   ├── about/          roadmap, team, the journal book
│   │   └── features/       cross-page widgets
│   └── assets/css/         one stylesheet per concern
│
├── tests/                  1,710 tests, grouped to mirror services/.
│                           See tests/README.md.
│
├── docs/
│   ├── VERSION_*.md        What each build decided and why.
│   └── reports/            Audits, fix records, this map.
│
├── legacy/streamlit_app/   The original UI. Kept as provenance, not run.
├── storage/                Real user data. Gitignored, never shipped.
└── .github/workflows/      CI: suite, frontend, hygiene, smoke.
```

## The rules that keep it this way

**One definition of the project root.** `core/paths.py`. Nothing computes
it from its own file depth — that is what silently broke fourteen service
modules during the `services/` reorganisation (they wrote into
`services/storage/` for half an hour and nothing raised) and what would
have broken fifty-two tests during the `tests/` one. The single exception
is `tests/_test_support.py`, which puts the root on `sys.path` and
therefore cannot import it.

**Layers point one way.** `api/` → `services/` → `core/`, `utils/`,
`config/`. Services may import from other service packages; nothing
imports from `api/`, and nothing outside `legacy/` imports from it.

**Feature derivation is shared.** `utils/feature_derivation.py` is called
by both training and inference. A feature computed one way at fit time
and another at predict time is a bug that does not raise.

**Storage is an interface.** Every service takes a `StorageBackend` and
never touches a file. That is why a SQLite backend could be added without
editing any of them.
