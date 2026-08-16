# Session notes — what changed, what did not

This file is the honest record for the round of work that produced the
commits listed under "Commits" below. It is written to be read next to
`OPEN_QUESTIONS.md` (which holds the things that need a decision from
you rather than more typing from me).

---

## Fixed and verified this round

Each of these was reproduced first, fixed minimally, covered by a test,
and — where it is a UI behaviour — re-checked in a real Chromium
browser. Every test listed was also checked against the *pre-fix* code
to confirm it actually fails there (a test that passes either way
proves nothing).

| # | Bug | Where | Test |
|---|-----|-------|------|
| 1 | Crisis guard had **no Arabic or Chinese detection at all**, and even in English the word "suicide" never matched (a `\b(...)\b` grouping bug) | `coach-chat.js` | `tests/test_coach_crisis_guard.py` |
| 2 | Coach menu answers leaked raw internal error strings (`auth`, `HTTP 500`) instead of the translated per-kind message the chat box already used | `coach.js` | `tests/test_coach_connector_errors.py` |
| 3 | Double-submit on the check-in wizard left a second processing overlay stuck over the page, blocking every click on the games screen | `app.js` | `tests/test_games_eligibility.py` |
| 4 | `personalizedGuideLine()` served English to Arabic/Chinese, and printed `*_ratio` fields as raw decimals (`0.0357` instead of `4%`) | `app.js` | `tests/test_i18n_coverage.py` (new `if(lang==='fa')` scanner) |
| 5 | Dashboard cohort card was hardcoded English on every language, with a broken `23th` ordinal | `dashboard.js`, `i18n.js` | `tests/test_coach_labels.py` |
| 6 | `/auth/login` had **no rate limiting** — a script could grind a wordlist at Argon2 speed | `account_service.py` | `tests/test_account_service.py` |
| 7 | The Digital Guide greeted the user on **every page load** (bubble + speech) | `shell.js`, `app.js` | verified in browser, 4 pages |
| 8 | Top nav clipped its last item ("Hall of Fame") at 1280px — worse in fa/ar where labels are longer | `shell.css` | measured `scrollWidth == clientWidth` after |
| 9 | 169 compiled `__pycache__/*.pyc` files were tracked in git despite being in `.gitignore` | repo-wide | `git ls-files` count |

Earlier in the same session (already delivered): `DWCoachLabels` was
never defined anywhere; every binary `fa ? x : y` ternary was removed
from the frontend (`ai-menu.js` alone had 63); games moved to their own
screen between processing and the result with a settings toggle; the
demo-deletion data leak; Gemini and Grok connector providers.

---

## Asked for, but NOT done — and why

I am listing these plainly rather than implying they are covered.
Nothing below was started; assume it is untouched.

### Round 4 — final pass

**Server-composed text now translated.** Three sentences on the result
and dashboard screens are written by the backend, not by `i18n.js`,
because they are built from your own numbers: the confidence reading,
the out-of-distribution warning, and the cold-start note. All three were
English-only in every language. They now ship in all four under a
`text_i18n` map, with `frontend/assets/js/server-text.js` holding the
one fallback chain (reader's language → English → flat field) instead of
four call sites each inventing it. The interval clause ("the likely
score range spans about N points") is translated too — it used to be
appended in English onto an otherwise Persian paragraph.

Verified in a Persian browser: narrative, confidence paragraph and
cold-start note all render with no English words left in them.

**Letter from the future — finished.** It existed but was missing all
three things asked for. It now unlocks at a full week (was five days),
is dated from a specific day ten ahead in the reader's own calendar (a
Persian reader sees a Jalali date), and opens out of an actual envelope
whose flap swings back and releases the sheet. Every path through that
animation — reduced motion, the normal sequence, and a 2.2s safety
timeout — ends with the letter readable; a flourish that could strand
the sheet inside the envelope would hide the only thing the reader
opened it for.

**League conversation rename.** The server and `api.js` have both
supported this since the chat shipped, but nothing called it, so no
thread could actually be renamed. Now it can.

One correction worth recording: the name is **shared**, not private.
`LeagueChatService.rename_conversation` writes one title onto the record
both members read, deliberately. The confirmation says so. My first
draft of that string said "only you see this name" — I checked the
service before shipping it, then confirmed with two live accounts that a
rename by one side reads back identically to the other.

**Coach conversation history + rename** turned out to be already done
and wired (`coach-conversations.js`, translated) — this file previously
listed it as not started, which was wrong.

Guide topics added for the league group-creation button and the rename
control, in all four languages.

Full suite: **990 tests, 990 passed, 0 failed, 0 errors, 0 skipped.**

### Large features that need real design work, not a patch

- **7-day plan personalised from 10,000+ exercises.** The plan today is
  rule-generated from your weakest signals. Building a graded exercise
  bank at that scale, and a selector that varies day to day without
  repeating, is a feature project on its own.
- **Coach menu 50 → 200 questions**, each answered well. The current 55
  are each wired to real data; adding 145 more at the same standard is
  a large content effort, not a loop.
- **Coach "big data" for open-ended questions** ("how do I grow?",
  "comfort me", "explain the app"). This is the honest limit of a
  rule-based responder. It needs either a much larger curated knowledge
  base or the optional external connector switched on.
- **Demo variants: 3/7/15/23-day × 4 classes, with 10 friends and
  pre-seeded chats.** Currently one 23-day demo exists. Sixteen
  variants with social graphs is a substantial generator.
- ~~Letter from the future (unlock after 7 days, dated 10 days out,
  motion-graphic envelope).~~ **Done in round 4.**
- ~~Conversation history for Coach and for League chats, with rename.~~
  **Done.** Coach threads were already built; the League rename control
  was added in round 4.

### Round 2 — fixed after the confirmation run

| Bug | Cause found | Result |
|-----|-------------|--------|
| Hall of Fame in English, music stopped | `hall-page.js` was the only page controller that never called `DWShell.init()` — the call that applies language, starts music, wires chrome and nav | Verified in fa: title "گالری افتخار", dir=rtl, nav lit, music widget, 0 JS errors |
| Music cut ~1s on every navigation | audio element created with `preload='none'`, so fetch+decode+seek all happened *inside* the gap | `preload='auto'` + 450ms fade-in on resume |
| 7-day plan identical every day | `day_index * 3` cancelled against 3-template themes (`% len`); and `reflection` had only 3 templates for 6 days | **1 → 7 distinct days** (healthy), 7/7 (at-risk) |
| Future-path cards had no number, identical text | every path hit `already_at_target`, which returned a generic sentence with no score | at-target now carries `(84/100)`; all-at-target collapses to one card |
| Guide greeted on every page | auto `explain()`/`startTour()` timers | removed; test caught **3 more** I'd missed, incl. one firing on *every wizard step* |
| Top nav clipped "Hall of Fame" | 11 links > 1280px, worse in fa/ar | `flex-wrap`; scrollWidth == clientWidth everywhere |
| 169 `.pyc` tracked in git | committed before `.gitignore` existed | untracked (files kept on disk) |

New tests: `test_page_shell_init.py` (4), `test_plan_day_variety.py` (6).
Both verified non-vacuous against the pre-fix code.

### Still open from your list

- **#1 seven-day score** — verified *correct* on this build (84 → 82–87).
  Your 76–81 points at the older `class_typical` estimator; check
  `artifacts/future_score_augmentation.json` exists and
  `DWAI_FUTURE_SCORE_MODE` is not `class_typical`.
- **#2 coach recommendations** — not done (large).
- **#3 games before prediction** — already shipped earlier this session.
- Demo mode, letter from the future, coach/league conversation history,
  200-question menu, 16 demo variants — all still untouched.

### Round 3 — items #6 and #7, both now done

**#7 — named CSV check-ins** (`csv-library.js`, `tests/test_csv_library.py`,
14 tests). After a prediction you name the answers you just gave; Enter
downloads a CSV and files it on the check-in screen under one of two
shelves — real check-ins and test check-ins — decided by the
"don't count this" tick that was already set when the prediction ran, so
a shelf cannot disagree with what happened. Clicking an entry refills the
whole form from schema defaults upward, so a file saved before a field
existed cannot leave that field undefined. The file is written *before*
the entry is listed, so if the browser refuses to grow localStorage the
user still has their download and the status line says so instead of
claiming a save that did not happen. Malformed CSVs are refused outright
rather than half-filling the form. Driven end-to-end in a Persian
browser: name → Enter → downloaded + listed → click → form filled, 53
columns in, 53 out, no JS errors.

**#6 — reopen a past day** (`history_replay_service.py`,
`tests/test_history_detail.py` + `test_history_reopen_ui.py`, 34 tests).
Clicking a day in the dashboard heatmap opens that check-in on the
result screen.

The part worth knowing: the day is **replayed, not re-predicted**. The
classifier reads your earlier check-ins as trend features, so predicting
the 3rd of the month *today* would score it against history that did not
exist on the 3rd, and quietly disagree with the number already sitting
in that day's heatmap cell. Each entry now carries a snapshot — the full
53-field input plus the model's own output, about 2.3 KB per day, ~810 KB
per user-year — and the model output is read straight back from it.
Everything downstream (recommendations, dimensions, confidence wording,
OOD, tone framing) is regenerated through the same function a live
prediction uses, so a reopened day cannot drift into a second renderer
and it respects tone or muted-category changes made since.

Days recorded before this existed are refused with a named reason rather
than rebuilt from the ~20 summary fields they carry — a check-in
reconstructed from a third of its inputs is a different check-in. Their
summary view is unaffected.

Two things had to move, and you should know about both:

- **The heatmap cell click used to mark the day as an exception.** That
  is a data edit fired from the most obvious gesture on the page, and it
  left no way to look at a past check-in at all. Marking an exception now
  has its own small button in the cell corner (keyboard-reachable,
  `aria-pressed`) that stops propagation, so it never opens the day.
- **`?day=` is honoured before the onboarding redirect.** Pressing "skip"
  on onboarding never marks it complete, so gating on it sent anyone who
  had ever skipped to the intro screen instead of the day they clicked.

Also fixed on the way, because it was the first line of the result screen
in every language: **`result_framing` was English-only**. All twelve
framings (3 tones × 4 bands) are now written in en/fa/ar/zh, sent as
`result_framing_i18n`, with the English `result_framing` field kept so
nothing older changes. Persian now opens with
"این واقعاً نتیجه‌ی خوبی است — هر کاری می‌کنی، دارد جواب می‌دهد."

Full suite after this round: **939 tests, 939 passed, 0 failed,
0 errors, 0 skipped.**

### Reported bugs I have now CONFIRMED with my own eyes

A full Persian end-to-end run (register → check-in → games → result)
put these on screen. You were right about all of them; none are fixed
yet, and each is precisely located now:

- **The 7-day plan repeats the same text every day.** Days 1-6 all read
  "Maintain Your Momentum / Look back at yesterday's plan...".
  Cause: `services/improvement_plan_service.py::_DEFAULT_THEME` has
  exactly **one** entry in its `levels` list, and a user with no
  flagged weak areas falls back to it for every single day. It cannot
  vary until that theme has per-day content.
- **"Talk to your future self" shows no numbers and identical copy.**
  On the result page both "بهبود تدریجی" and "تلاش جدی" render the same
  sentence with no score at all. (The API itself does return distinct
  numbers - measured: status quo 60.6, gradual +3.98, committed +5.79 -
  so this is a rendering bug on the result card, separate from the
  "deltas are too small" argument below.)
- **Large blocks of English on a Persian page.** The whole 7-day plan
  (themes and every task), the confidence explanation, the
  uncertainty/coverage paragraph, the result headline, and the persona
  label ("Productive Low-Stress") all render in English under RTL. The
  plan text is generated server-side in
  `improvement_plan_service.py` with no i18n path at all, so it can
  never translate as things stand.
- **SHAP factor bars render with empty fills.** The factor names are
  correctly in Persian, but the bars themselves are blank.

The 7-day band itself is **correct** in this build: today 84, seven-day
"Healthy 82–87" - above/around today, not the 76–81 you saw.

### Reported bugs I could not reproduce, or that need your build

- **Demo mode hanging 45s then erroring onto the real account.** I could
  not reproduce this here. It is the single most valuable thing to fix
  next and I would want your exact steps plus the browser console
  output — without a reproduction I would be guessing.
- **7-day score lower than today's score (84 → 76–81).** On this
  checkout the API returns **84.5 (range 82.2–86.8)** for the healthy
  demo profile — i.e. correct, and matching what you said you expected
  (82–89). What you saw looks like the older `class_typical` estimator,
  which by construction cannot exceed ~72 for any user (its own
  docstring says so). Two things to check on your copy: that
  `artifacts/future_score_augmentation.json` is present, and that
  `DWAI_FUTURE_SCORE_MODE` is not set to `class_typical`. The default is
  `augmented`.

### Where I disagree, and want to say so rather than quietly comply

- **"Committed change" should show +5 to +20 points.** Measured on the
  borderline profile: status quo 60.6, gradual +3.98, committed +5.79.
  The gap is small for high scorers *by design* — each path closes a
  fraction of the distance to a healthy target, and a user already near
  those targets has little distance left. I can widen the fractions,
  but I cannot make the model report a bigger improvement than it
  predicts, and inflating it would make the number dishonest. What I
  think is actually wrong here is the *presentation*: when there is
  little headroom the UI should say so, instead of showing two
  near-identical numbers under dry text. That I can do — say the word.

### Smaller items not reached

Remaining English strings in menus/analytics for fa/ar/zh; more
motivational/fact content; guide copy for the League new-chat/group
dialog.

Two of the English blocks listed above are now located precisely, so
whoever picks them up does not have to re-find them:

- **The 7-day plan text** is generated in
  `services/improvement_plan_service.py` / `config/exercise_library.py`.
  The exercise templates there *do* carry all four languages already —
  that was fixed in round 2 — but the surrounding theme titles and the
  plan's own framing still have no i18n path.
- **The confidence and uncertainty paragraphs** come from
  `services/insight_service.py`, which builds English sentences the same
  way `tone_service.py` did before this round. The fix is the same shape
  as the one applied to `result_framing`: return the sentence in all four
  languages and let the UI pick.

---

## Not touched, on your instruction

The user-data exposure in git history documented in `SECURITY.md`.
You asked me to leave it alone for now, so no history was rewritten and
nothing was force-pushed. It remains unresolved — see `SECURITY.md` for
what it is and `OPEN_QUESTIONS.md` for the decision it needs.
