# Handoff — what is done, what is not, what to do next

Written at the end of a long session so the next one does not have to
re-derive any of it. Read `PROJECT_MAP.md` first for the layout, then
this.

---

## Ground rules that outrank everything else

These come from the project brief and have held for the whole build.
Breaking one is worse than leaving a feature unbuilt.

1. **No medical or diagnostic claim, anywhere.** Words like "stress" or
   "anxiety" appear only because the user rated them. Never a
   diagnosis, screening result, or treatment suggestion.
2. **No user-shaming mechanism.** Streaks carry no penalty, locked
   badges never imply failure, a bad week is reported plainly and
   without judgement.
3. **The digital guide's voice uses the browser's own speech engine.
   No API key, no external service. Absolute.**
4. **Four languages, complete: en / fa / ar / zh, with RTL.** No mixing,
   no silent English fallback. Technical model names (regression,
   classification) stay as they are; everything else translates.
5. **Never fabricate a number.** If the app cannot honestly produce a
   value it says so. An absent value is a deliberate answer.

## Delivery constraints in this environment

- **`git push` returns a genuine 403.** The session has read access
  only. Do not spend time on it. Commit locally and deliver the work as
  a ZIP through the file-sending tool; the user pushes themselves.
- The user runs **Windows** and is in **Iran** — webfont CDNs and
  similar are frequently blocked, which has already caused one bug
  (fixed: fonts are non-blocking now).
- Ship **Version 2 only** from here. Version 1 (`class_only`) is
  frozen; the user has chosen Version 2 as the final build.
- The audio tracks are delivered as a **separate 27 MB ZIP** so the app
  archive stays a single sub-30 MB file. Do not put them back in.

## How to run and verify

```bash
pip install -r requirements.txt
python run.py                 # Windows: double-click start.bat
python3 -m unittest discover -s tests -t .   # 802 tests, all passing
```

**Never** serve `frontend/` with a static file server. It shows the
pages and then answers every POST with 501; this cost the user an
evening and is why `run.py` and `api-guard.js` exist.

Chromium is available for real browser verification over CDP — several
bugs in this project were invisible to static analysis and only showed
up that way. Block `*fonts.googleapis.com*` when driving it, or pages
sit at `readyState: loading` for 25 seconds.

---

## Done in the most recent sessions

| area | state |
|---|---|
| Seven-day estimate | **fixed** — no longer punishes high scorers |
| Demo Mode | **rebuilt** — own account, 16 variants, 10 friends + chats |
| Coach conversations | **added** — saved, separate, renameable |
| League nav / guide / chat rename | **fixed** |
| Weekly plan | **rebuilt** — 7,900 value-bound exercises |
| Future paths | **fixed** — paths now visibly separated |
| Login 501 / 504 | **fixed** — launcher + guard + bounded locks |
| Terms page | **rewritten** — 12 sections, 4 languages, contact details |
| `storage/` privacy | **fixed** — untracked; see `SECURITY.md` |

Each of these has a commit message explaining the measurement behind
it. `git log` is the real record; it is written to be read.

---

## Not done — the actual backlog

Roughly in the order the user asked for them.

### 1. AI Coach depth  *(the user's largest single ask)*

"AI Coach" = the app's own rule-based coach at `coach.html`
(`coach.js`, `ai-menu.js`, `coach-knowledge.js`,
`coach-knowledge-life.js`). Not the optional external connector.
**Read this part carefully — it is the easiest thing in this document
to get wrong.**

The user's stated target is that the coach can answer on the order of
**30,000 questions**, and — the harder half — that it answers questions
which are **not phrased the way it was written for, including ones with
spelling mistakes**. "How do I grow", "comfort me" and "explain the app"
were offered as *probes that currently fail*. They are symptoms. Fixing
those three sentences and stopping would satisfy nothing: the next three
someone types would fail in exactly the same way.

So this is an **intent-coverage and robust-matching** problem, not a
"write more answers" problem.

**Why it fails today.** `coach-chat.js` routes by hand-written regular
expressions, first match wins:

```js
if (asks(/strength|doing well|good at|قوت|خوب.{0,10}چیه/i) && ...)
```

That matches the exact words someone thought of while writing it.
"scroe", "wht am i god at", "چ کاری خوب انجام میدم" all miss and drop
to a generic reply. Adding more regexes makes the file longer without
making it less brittle — the failure mode is structural.

**What it needs instead, roughly in order of value:**

1. **Normalisation before matching.** Lowercase, strip punctuation and
   diacritics, collapse whitespace — and for Persian/Arabic
   specifically: unify `ی/ي`, `ک/ك`, `ه/ة`, normalise ZWNJ and Arabic-
   Indic digits. A large share of "typos" in fa/ar are really just
   different codepoints for the same letter, so this alone recovers a
   lot.
2. **Fuzzy matching, not equality.** Damerau-Levenshtein or trigram
   similarity against each intent's keyword set, with a threshold that
   scales with word length. This is what makes "scroe" reach `score`.
3. **Score every intent, then pick the best** — replacing first-match-
   wins. Two intents both matching should be resolved by which matched
   better, not by which `if` came first.
4. **Synonym and stem expansion per intent**, in all four languages,
   so one intent covers a family of phrasings rather than one phrasing.
5. **An honest fallback.** When nothing scores above the threshold, say
   so and offer the closest two intents as suggestions. Never guess an
   answer to a question that was not understood — that violates ground
   rule 5.

**How the 30,000 figure is actually reached.** Not by writing 30,000
answers. Roughly: ~200 intents x a synonym/paraphrase set per intent x
four languages, with fuzzy matching absorbing the misspellings. The
number to report is *measured coverage over a test corpus*, not a count
of hand-written strings.

**Acceptance must be measured, not asserted.** Build a labelled corpus:
for each intent, several paraphrases and several deliberately
misspelled variants, in all four languages. Report the percentage
answered correctly, and keep the corpus as a test so it cannot regress.
"Those three examples work now" is not an acceptance criterion.

**Command menu:** 55 items today, the user wants **200**. See
`frontend/assets/js/ai-menu.js` — each item is a `case` in
`localAnswer()`. Prefer generating question families over
dimensions/metrics to writing 145 bespoke cases, and note the menu and
the free-text matcher should share one intent registry rather than
drifting into two lists of the same thing.
- **Providers.** `frontend/assets/js/connector.js` holds a `PROVIDERS`
  map. Today: OpenAI (3 models), Anthropic (3), Groq (1), OpenRouter
  (2), plus a freeform custom/self-hosted entry.

  The user wants **Gemini and Grok added**, AND every existing provider
  filled out with its **full model range — weak, mid and strong — not
  just the two new ones**. Groq with a single model and OpenRouter with
  two are the clearest gaps. Keep the existing `tier` label on each
  entry ("fast · cheap" / "strong · mid" / "strongest · pricier") so the
  picker stays readable.

  Note the `shape` field: `openai` means the `/chat/completions`
  convention (Groq, OpenRouter, Gemini's compat endpoint and xAI all
  speak it), `anthropic` means `/v1/messages`. A new provider usually
  needs only a `PROVIDERS` entry, not new transport code.
- Conversation history exists already
  (`frontend/assets/js/coach-conversations.js`) — build on it.

### 2. Games — 5 of 13 built

**Built** (in `frontend/assets/js/games.js`, keys as they appear there):

| key | what it does |
|---|---|
| `game_guess_score` | shows a real logged day, user guesses its score |
| `game_which_factor` | which of four signals moved the score most |
| `game_baseline_or_exception` | was this day typical for you, or an outlier |
| `game_fill_the_blank` | recall one of your own logged values |
| `game_keep_the_streak` | pick the choice that protects a streak |

**Not built — eight remain.** The original brief listed thirteen but
the other eight are not written down anywhere in this repo, so treat
them as a design task, not a recall task. Ask the user for the list
before inventing one; if they want you to propose them, the five above
show the shape: each uses the user's OWN data, is answerable in under a
minute, and teaches something about how the score works.

**Every game must obey rules G1–G9**, which ARE recorded — read the
header comment of `games.js`. In short: no shaming, no fabricated data,
no score effect, honest "not enough data" states.

**Placement change requested:** games should appear on their own screen
**after the processing animation and before the prediction result**,
with a settings switch to disable that step. They currently sit on the
dashboard.

### 3. History review + CSV questionnaire

**History review:** clicking an entry in the history list should reopen
that entry's full prediction/result page. Not implemented — the list is
currently read-only rows.

**CSV questionnaire round-trip.** The goal in the user's words: fill the
check-in once, download a CSV, and next time upload it instead of
re-entering everything.

Two of the three pieces already exist:

- `GET /api/v1/schema/csv-template` returns a header-only template. Its
  columns are the real feature names — `date,age,gender,
  occupation_group,...,social_min,sleep_hours,stress_0_10,...` — get the
  authoritative list by calling it, not from memory.
- `POST /api/v1/history/import-csv` accepts a filled file.

**Missing:** an export of the user's OWN last answers in that exact
column order, so the downloaded file is already filled in and can be
edited and re-uploaded. Match the template's columns exactly or the
import will reject it, and reuse `services/report_i18n.py` for the
UTF-8 BOM so a spreadsheet opens fa/ar/zh without mojibake (the JSON/CSV
privacy export already does this).

### 4. Letter from the future
- Should unlock after **seven days of continuous activity** and deliver
  a message dated ten days out, based on the user's real trend.
- Wants **motion graphics** — an envelope opening. `future-letter.js`
  exists; the unlock rule and the animation do not.

### 5. Remaining translation gaps
- Menus, analytics labels and some names still render English under
  fa / ar / zh. `tests/test_i18n_coverage.py` is the place to extend.
- **46 strings** in `coach.js` / `coach-chat.js` and **111 binary
  ternaries** (`fa() ? ... : ...`) still bypass `pick()`.

### 6. Guide behaviour
- It greets on **every** page open and speaks aloud each time. The user
  finds this irritating. Suppress the automatic greeting; keep the
  guide fully available on demand. Fatigue controls already exist in
  `guide-tips.js` — the auto-greet path is what needs changing.
- Guide topics for everything added in items 1–5 above, in four
  languages, with voice.

### 7. More content
- Motivational lines and "did you know" facts should be substantially
  expanded.

### 8. Known defects still open
- **Demo deletion leaks.** `DELETE /demo/session` removes only the
  account row. `AccountService.delete_account` deliberately leaves
  history to the caller (see its docstring, and
  `api/routers/progress.py` for the correct two-step order). The demo's
  history, its bot friends' histories, league connections and chats all
  survive. The user was told deletion was complete — it is not. Fix by
  sequencing the same way the privacy route does.
- **Healthy profile future paths show +0.00** for all three improvement
  paths because it is already at every healthy target
  (`already_at_target` is set). The answer is honest; the presentation
  makes it look broken. This is a UI change, not a scoring one.
- **`at_risk` continued-drift scores slightly positive** (+0.14).
  Small, but drift should never be an improvement.
- **Emoji vs SVG.** 253 emoji remain against 154 inline SVG. The badge
  and game glyphs were deliberately left as emoji — 63 near-identical
  abstract marks would be worse than the emoji they replaced. The user
  asked for all of them; this is a stated partial.
- **`terms.html` has no guide layer.** It is a standalone document with
  no app scripts by design.

---

## Things already tried and rejected — do not redo them

- **Global rank persistence** for the seven-day target: produced a
  target correlated **0.939** with today's score, i.e. predicting today
  and calling it next week. Recorded in
  `artifacts/future_score_augmentation.json` under
  `rejected_alternative`, and a test asserts it stays rejected.
- **A single-stage regressor** on the augmented target: **19.53% worse**
  than "predict today unchanged". Kept in
  `artifacts/metrics_future_regression.json` rather than deleted,
  because the comparison is the finding.
- **Reconstructing a real seven-day score** from the dataset: not
  possible. No user id, no date, shuffled rows; the cohort key
  over-groups 73% of rows and pairing yields a 99.3%-one-class subset.
  `models/calibrate_future_score.py` documents the measurements.

## Habits this codebase expects

- Every fix carries a **measurement**, not an assertion. Reproduce a
  bug before fixing it, and put the numbers in the commit message.
- **Verify checkers against known-broken input.** Several tests in this
  repo would have passed vacuously; the ones that survived say so in
  their docstrings.
- Comments carry the **why**, especially the rejected alternative. The
  next person needs to know what not to try.
- When something is only partly done, **say so in the reply**. The user
  has been explicit that a half-finished thing presented as finished is
  the worst outcome.
