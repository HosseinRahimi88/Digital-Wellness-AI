# Open questions

Logged per the execution directive's own rule: stop-and-ask is reserved
for (1) an irreversible high-risk action, (2) missing information the
repo can't answer, (3) no path forward except fabricating data. This
file exists so the rest of the work can proceed without blocking on
these. Each is also called out in the final report.

---

## 1. The execution directive's ground truth contradicts the user's own
   Version-2 decision from earlier in this session (P1)

**The conflict, stated precisely.**

`DWA_EXECUTION_PROMPT_1.md` §1 ("GROUND TRUTH — تنها منبع معتبر پروژه")
states: exactly two supervised models exist; "Future Health" must show
**only a class, never a number**; and explicitly bans "هیچ Future Score
عددی" (no numeric future score at all) - not from probability
conversion, not from pseudo-regression, "نه هیچ trick دیگری" (no other
trick). §2 Priority 1's Definition of Done repeats this: no numeric
range like `68–76` for the future figure anywhere in the code or UI.

This is **Version 1's (`class_only`) design, verbatim** - compare
`docs/VERSION_1_CLASS_ONLY.md`: "This build ... refuses to show a
seven-day score at all... there is no number to show."

But earlier in this same session:
- The user's own words: "فقط روی نسخه ۲ کار کن. نسخه ۱ قفل شده." (work
  ONLY on Version 2; Version 1 is locked/frozen.)
- `HANDOFF.md`, which the user pushed themselves this session, under
  "Delivery constraints": "Ship **Version 2 only** from here. Version 1
  (`class_only`) is frozen; the user has chosen Version 2 as the final
  build."
- `VERSION.md` at the repo root (the file that names which build is
  checked out) is titled "Version 2 — a seven-day number, built by data
  augmentation" and documents a real, validated two-stage estimator
  (classifier band + within-band rank persistence - NOT a third trained
  model, NOT a probability-to-score conversion) that beats the honest
  baseline by 17.21% (MAE 1.41 vs 1.70), with the rejected alternatives
  (global rank persistence, a single-stage regressor) kept on record as
  to why they were rejected. `services/future_score_service.py`'s
  `DEFAULT_MODE = os.environ.get("DWAI_FUTURE_SCORE_MODE", "augmented")`
  confirms this is the actual running default, not leftover dead code.
- This is exactly what `app.js`'s horizon card renders today
  (`futureBandEl.textContent = `${Math.round(fs.lower)}–${Math.round(fs.upper)}``
  when `fs.available`) - i.e. the checked-out code is doing precisely
  what this directive's ground truth calls a defect.

**Why I am not resolving this by deleting the augmented future score.**

Doing so would mean: deleting `models/augment_future_score.py`,
`models/train_future_regression.py`, the `artifacts/future_score_*`
files, `services/future_score_service.py`'s augmented path, the horizon
card's range display, and the passing tests that assert this behavior
(`tests/test_future_score_service.py` and others) - a large,
hard-to-reverse deletion of validated, tested, already-shipped
functionality that the user explicitly and specifically chose as the
final build earlier in this same conversation. That is exactly the
"irreversible, high-risk action" the directive itself says should not
proceed without confirmation, and reverting a deliberate recent decision
silently because a later document phrases the ground truth as if it
were Version 1 is a worse failure mode than pausing to ask once.

**What I am doing instead:** every OTHER part of Priority 1 that is
version-agnostic has been verified and holds regardless of which
ground-truth text is authoritative:
- The score ring's center number is `result.regression_score` directly
  (`app.js` lines 734/778/1127) - never a stale or hardcoded value,
  never derived from the classifier.
- The "In 7 days" figure's confidence interval and Today's regression
  interval are two separate objects in the response
  (`result.uncertainty` vs `result.future_score.lower/upper`) and are
  never merged into one number or one interval anywhere in the render
  path.
- No probability-to-score conversion exists anywhere in the codebase
  (grepped for the patterns Priority 1 names; none found outside the
  documented, tested two-stage estimator itself).

**What I need from you:** confirm which is authoritative -
(a) Version 2 stays exactly as the user chose it earlier this session
(recommended - it is already validated, tested, and was an explicit,
deliberate, informed decision with real metrics behind it), or
(b) actually revert to Version 1's `class_only` behavior, in which case
say so explicitly and I will do the deletion/rollback as its own
reviewed step, not folded silently into a broader autonomous pass.

Until answered, the codebase is left exactly as Version 2, unmodified
by this session's Priority 1 work.

---

## 2. Priority 3/5's "13 games, 8 remaining" figure does not match the
   repo (informational, not blocking)

`DWA_EXECUTION_PROMPT_1.md` §2 Priority 3 says: "از 13 بازی، 8 مورد
باقی‌مانده بررسی شد" (of 13 games, the remaining 8 were checked). The
repo's `games.js` actually has **11** games total: the 5 that existed
before this session (`game_guess_score`, `game_which_factor`,
`game_baseline_or_exception`, `game_fill_the_blank`,
`game_keep_the_streak`) plus 6 built earlier this session, each grounded
in real already-fetchable data (`game_dimension_duel`,
`game_confidence_guess`, `game_future_class_guess`,
`game_weekday_or_weekend`, `game_badge_race`, `game_score_vs_average`).

This "13" figure traces back to the user's own earlier message in this
session ("۵ تا ساخته شده، ۸ تای دیگر لازم است" - 5 built, 8 more
needed), which this directive appears to be carrying forward as
inherited context rather than a fresh count taken from the repo.

Per Priority 5's own explicit rule - "بازی‌های باقی‌مانده فقط در صورتی
اضافه شدند که به داده‌ی واقعی نیاز داشته باشند و آن داده موجود باشد -
هیچ داده‌ی مصنوعی برای بازی ساخته نشد" (remaining games only added if
they need real data and that data is available - no synthetic data was
built for any game) - I am not fabricating 2 more games just to reach
"13". All 11 existing games were verified this session: fully localized
(0 binary ternaries/containers anywhere in `games.js`, confirmed by
`tests/test_i18n_coverage.py`), and each already covered by the G4/G6
eligibility + language tests in `tests/test_games_eligibility.py`. If a
genuinely real-data-backed 12th/13th game concept exists that I'm not
aware of, it isn't inferable from the repo as it stands, so it isn't
built.

---

## 3. Priority 4's "55 badge tips" figure is also stale (informational,
   not blocking)

Same pattern as #2 above. `DWA_EXECUTION_PROMPT_1.md` §2 Priority 4 says
"۵۵ نکته‌ی مربوط به badgeها دست‌نخورده و سالم است" (the 55 badge-related
tips are untouched and healthy). The repo's actual badge registry
(`frontend/assets/js/badge-registry.js`, cross-checked against
`services/badge_service.py`) has **63** badges, matching the file's own
header comment ("Tone rules, applied to all 63"). This "55" also traces
to the user's original message earlier in the session. I verified the
substance of the requirement regardless of the exact number: all 63
badge entries carry complete `name`/`desc` (and `next` where relevant)
in all four languages, with zero values identical to their English
counterpart (i.e. no silent untranslated fallback), and the two guide
topics that explain the badge *surfaces* (`hall_of_fame`,
`awareness_indicators` in `guide-content-badges.js`) are likewise fully
translated. Nothing here was touched beyond one unrelated content fix
(see below) - the badge content itself was already complete and needed
no changes.

**One real content bug found and fixed while auditing guide coverage
for Priority 4:** `guide-tips.js`'s `result_ring` topic - the text the
Digital Guide speaks when a user asks about the score ring - described
three different UI designs across languages. English and the (rewritten)
Persian version correctly describe the actual current ring: a calibrated
*range* (not one exact number) plus four dimension arcs, matching what
`app.js` genuinely renders (`renderResult()`, lines ~806-819, passing
`range` from `result.uncertainty` into `DWScoreRing.render`). The
Arabic and Chinese versions instead described a fixed-threshold
single-number ring (80+/60-79/&lt;60 colour bands) that does not match
any ring design currently in the codebase - stale copy from an earlier
UI iteration that the localization pass never caught, because it's a
factual/content mismatch, not a structural gap the automated i18n
scanners check for. Rewritten both to accurately describe the real
ring, verified in a live Chromium browser afterward (`DWGuide.explain('dashboard')`
etc. render correctly in en/fa/ar with correct `dir` and translated
text - see final report for the full check). Also fixed the same class
of bug in `app.js`'s `narrativeSummary()`: the Arabic and Chinese score
sentences silently dropped the "top factor" clause that English and
Persian both include, which is again not something the binary-ternary
scanner catches since all four blocks are already `{en,fa,ar,zh}`
objects - it's a content-completeness gap, not a structural one.
