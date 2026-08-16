# Final QA

*What was checked, what was found, what was fixed, and what is still not done.*

---

## 1. What was checked

| Sweep | Scale | Result |
|---|---|---|
| Full Python suite | **1,716 tests** | all pass |
| API suite on SQLite | **250 tests** | all pass |
| Parameterless `GET` endpoints | 45 × 3 states (cold / populated / anonymous) = **135 probes** | **0 × 5xx** |
| Pages in a real browser | 13 pages × 4 languages = **52 loads** | 0 asset 404s, 0 page errors, 0 empty renders |
| JS modules parsed | **78** | all parse |
| Node coach runners | **13** | all pass |
| PDF generation | wellness × 4 languages, journal × 2 | all valid, all 3 pages |
| Concurrency | 8 simultaneous plan writes to one account | no lost update, no 5xx |
| Malformed input | 5 shapes (negative, absurd, wrong type, empty, null) | rejected, never crashed |
| Auth edges | garbage token, empty token, duplicate email, short password | correct status every time |
| Privacy delete | delete then reuse the token | account gone, token dead |

## 2. What was found and fixed

### The one that mattered: paths computed by directory depth

The test tree was regrouped into nine packages. Before moving anything,
**52 test files** computed the project root as
`Path(__file__).resolve().parents[1]`, and **10 more** located their Node
runners with `Path(__file__).resolve().parent / "js"`.

Moving them one level deeper would not have raised. They would have
pointed at a directory with no frontend and no artifacts in it, found
nothing, and **gone green by asserting over empty lists**.

This is the third time this exact pattern has bitten this repository:

1. `services/` was grouped — fourteen modules resolved one level short and
   the running app wrote real accounts, history and journals into
   `services/storage/` for about half an hour. Nothing raised. It was
   noticed only because a directory appeared that nobody had created.
2. Those files were then swept into a commit by `git add -A`.
3. `tests/` — caught this time, before the move.

So it is now **banned by a test**, not by a convention:
`tests/storage/test_no_path_is_computed_by_depth.py`. Conventions do not
survive a rename.

That test immediately found **15 more instances** nobody knew about, in
`models/` (8 training scripts), `api/core/config.py`, `models/data_loader.py`,
`models/model_registry.py`, `models/model_saver.py`,
`models/metrics_logger.py` and `utils/tokens.py`. All rewired to
`core/paths`. The training scripts lost their `sys.path` bootstraps and
are now run with `-m`.

Three files are allowlisted, each for a real reason:
`tests/_test_support.py` (it puts the root *on* `sys.path`, so importing
`core` to find `core` would be circular), `core/paths.py` (it is the
definition), and `run.py` (it stays in the root by construction and
checks that it did).

### Breakage the move caused, and how it surfaced

| What broke | How it showed | Fix |
|---|---|---|
| 10 Node runners | `Cannot find module .../tests/coach/js/crisis_guard_runner.js` | absolute path from `paths.PROJECT_ROOT` |
| 5 tests pointing at `app/` | `FileNotFoundError: .../app/Home.py` | `legacy/streamlit_app/` |
| `_test_support.py` | SyntaxError — an import inserted inside a multi-line import | put back, with the exception documented in place |

### Bugs found in the CI while writing it

CI that fails on its first push is worthless, so every job was dry-run
locally first. Two defects surfaced there rather than on GitHub:

- **The coach runners need the repository root as `argv[2]`.** Invoked
  bare, 6 of the 13 fail. The workflow now passes `"$PWD"`.
- **`/schema/features` answers with a list, not an object.** The smoke
  script assumed a dict and crashed on `.get`.

### Two probe failures that were the probe's fault, not the app's

Recorded because "found a bug" and "wrote the request wrong" look
identical in a log:

- **wellness PDF 422 ×4** — the endpoint takes a full 53-field
  `user_data`; the probe sent `{}`. With a real payload: 200 in all four
  languages, 45 KB / 55 KB / 56 KB / 4.7 KB.
- **`/history/export.csv` 404** — the path is `/privacy/export.csv`.

### One number that looked wrong and is not

The Chinese PDF is 4.7 KB where English is 45 KB. Investigated: both have
3 pages. English embeds `DejaVuSans` (~40 KB of glyphs); Chinese
*references* `STSong-Light`, a standard CJK font ReportLab names rather
than embeds. The size difference is the font, not missing content.

## 3. Structure

- `tests/` — 116 files in 9 packages mirroring `services/`, plus `js/`
- `app/` → `legacy/streamlit_app/`, so its status is visible in a
  directory listing rather than only in a paragraph of the README
- `research/` (one file) → `models/research_classification_trend.py`
- 20 MB of superseded model pickles untracked; the metrics JSON beside
  them — the actual evidence of the leakage fix — kept
- `run.py` gained `--port`, `--host`, `--no-browser`, all optional
- `CONTRIBUTING.md` was telling contributors to run **pytest** against a
  **unittest** suite, and pointed at two files that had moved
- `docs/README.md`, `tests/README.md`, `legacy/README.md`,
  `PROJECT_MAP.md` and `count.sh` (which regenerates every count quoted
  in the docs, so they cannot silently drift)

## 4. CI

Four jobs, separate because they fail for unrelated reasons.

| Job | What it would catch |
|---|---|
| `tests` | the suite, plus a second pass over the API tests on SQLite, plus a check that the installed sklearn is the one the pickles were fitted with |
| `frontend` | a JS syntax error — nothing else parses these files — and the coach's coverage, precision and refusal runners |
| `hygiene` | tracked user data at any depth, a populated secret in `.env.example`, the reset token reappearing in a response, anything that will not compile |
| `smoke` | the app not starting, models not loading, and register → refresh → rotation → reset over real HTTP; fails if the server logged an ERROR while serving |

## 5. Still not done

1. **No screenshots or demo video.** Yours to record.
2. **The training data is synthetic.** Nothing here is validated against
   human outcomes, and no amount of testing changes that.
3. **Email verification is reported, not enforced.** Deliberate — see
   `HARDENING_REPORT.md` §3.
4. **Volatile users are under-covered by the band model** (0.863 against
   a 0.90 target). Recorded in `BAND_MODEL_REPORT.md`.
5. **JSON storage is still the default.** SQLite is opt-in and tested;
   switching the default would strand existing installs.
6. **The population drift figure is visible to any signed-in user.** It
   is aggregate and identifies nobody, but if an operator role is ever
   added, it belongs behind it.
7. **The git-history user-data exposure in `SECURITY.md` is untouched**,
   as instructed.
8. **`legacy/streamlit_app/` is excluded from the path rule** — it has
   its own bootstrap and is not maintained.
