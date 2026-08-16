/*
  Exercises the three history-series coach families (trend / typical /
  steady) through the REAL frontend files - the same loading pattern
  tests/js/coach_nlu_corpus_runner.js uses: a minimal `window` stub,
  then require() the actual modules, so a change that breaks the real
  answers shows up here instead of in a re-implementation.

  Run as: node history_family_runner.js <repoRoot>
  Prints one JSON object to stdout and nothing else.

  The scenarios below are chosen so that a WRONG implementation gives a
  visibly different answer, not just a differently-worded one:

    - rising sleep vs rising stress separate "up" from "better". A file
      that assumed higher-is-always-better passes the first and fails
      the second.
    - the series is fed most-recent-first (which is what
      api/routers/history.py actually returns). An implementation that
      forgets to reverse it reports every trend backwards, so the
      from/to numbers are asserted, not just the verdict.
    - an excluded day carries an absurd value. If exception days are not
      dropped, it lands in the average and the range.
*/
const path = require('path');

const repoRoot = process.argv[2];
if (!repoRoot) {
  console.error('usage: node history_family_runner.js <repoRoot>');
  process.exit(2);
}
const jsDir = path.join(repoRoot, 'frontend', 'assets', 'js');

let LANG = 'en';
globalThis.window = {};
window.DWI18n = { get: () => LANG, pick: (t) => t && (t[LANG] || t.en) };
require(path.join(jsDir, 'coach/coach-labels.js'));
require(path.join(jsDir, 'coach/coach-field-guide.js'));
require(path.join(jsDir, 'coach/coach-curriculum.js'));
require(path.join(jsDir, 'coach/coach-breakdown.js'));
require(path.join(jsDir, 'coach/coach-history-family.js'));
require(path.join(jsDir, 'coach/ai-menu.js'));

const H = window.DWHistoryFamily;
const MENU = window.DWAIMenu;
const LANGS = ['en', 'fa', 'ar', 'zh'];

/** Newest-first, the way the real history endpoint returns it. */
function hist(field, valuesOldestFirst, opts) {
  const rows = valuesOldestFirst.map((v, i) => {
    const row = { date: `2026-01-0${i + 1}` };
    row[field] = v;
    return row;
  });
  if (opts && opts.excludedValue != null) {
    rows.push({ date: '2026-01-99', excluded: true, [field]: opts.excludedValue });
  }
  return { history: rows.reverse() };
}

const out = {};

// ---- menu shape -----------------------------------------------------
const items = MENU.allItems();
out.menuTotal = items.length;
out.familyCount = H.menuItems().length;
out.byCat = items.reduce((a, i) => { a[i.cat] = (a[i.cat] || 0) + 1; return a; }, {});
const ids = items.map((i) => i.id);
out.duplicateIds = ids.filter((x, n) => ids.indexOf(x) !== n);
out.itemsMissingALanguage = items.filter(
  (i) => LANGS.some((lg) => !i[lg] || !String(i[lg]).trim())
).map((i) => i.id);
// Every generated item must actually be answerable by some handler.
out.familyIdsNotRoutable = H.menuItems().filter((i) => !H.has(i.id)).map((i) => i.id);

// ---- direction: up is not the same as better ------------------------
const risingSleep = H.answer('trend_sleep_hours', hist('sleep_hours', [5, 5.2, 5.1, 5.5, 7.5, 8, 8.2, 8.5]));
const risingStress = H.answer('trend_stress_0_10', hist('stress_0_10', [2, 3, 2, 2, 8, 9, 8, 9]));
out.risingSleep = risingSleep;
out.risingStress = risingStress;
// "healthier" appears in the better copy; "away from" in the worse copy.
out.risingSleepSaysBetter = /direction this app treats as healthier/.test(risingSleep);
out.risingStressSaysWorse = /away from the healthier direction/.test(risingStress);

// ---- chronological order --------------------------------------------
// Oldest half averages 5.2, newest half 8.05 -> rounded 5.2 and 8.1.
// A non-reversed implementation would print these swapped.
out.trendFromToInOrder = /from about 5\.2 h to about 8\.1 h/.test(risingSleep);

// ---- too little data declines ---------------------------------------
out.minPoints = H.MIN_POINTS;
const thin = H.answer('trend_sleep_hours', hist('sleep_hours', [7, 8]));
out.thinDeclines = /only have 2 usable/.test(thin) && !/went from/.test(thin);

// ---- excluded days are dropped everywhere ---------------------------
const withOutlier = hist('total_screen_min', [295, 305, 310, 300], { excludedValue: 9999 });
const typicalOut = H.answer('typical_total_screen_min', withOutlier);
const steadyOut = H.answer('steady_total_screen_min', withOutlier);
const trendOut = H.answer('trend_total_screen_min', withOutlier);
out.excludedLeaksIntoTypical = /9999/.test(typicalOut);
out.excludedLeaksIntoSteady = /9999/.test(steadyOut);
out.excludedLeaksIntoTrend = /9999/.test(trendOut);
out.typicalCountsOnlyUsableDays = /last 4 logged days/.test(typicalOut);

// ---- steadiness discriminates ---------------------------------------
const flat = H.answer('steady_sleep_hours', hist('sleep_hours', [7.5, 7.5, 7.5, 7.5, 7.5, 7.5]));
const jumpy = H.answer('steady_sleep_hours', hist('sleep_hours', [3, 9, 4, 10, 2, 11]));
out.flatSaysSteady = /a steady field for you/.test(flat);
out.jumpySaysSwingy = /a swingy field for you/.test(jumpy);

// ---- every family answers in every language, with no leftover braces -
const probe = hist('sleep_hours', [5, 6, 7, 8, 8.5, 9]);
const langReport = {};
let untranslated = 0;
let unfilled = 0;
for (const lg of LANGS) {
  LANG = lg;
  const answers = ['trend_sleep_hours', 'typical_sleep_hours', 'steady_sleep_hours']
    .map((id) => H.answer(id, probe));
  langReport[lg] = answers.map((a) => a.slice(0, 60));
  answers.forEach((a) => {
    if (!a || !a.trim()) untranslated += 1;
    if (/\{[a-z]+\}/.test(a)) unfilled += 1;   // an unreplaced {value} slot
  });
}
LANG = 'en';
out.langSamples = langReport;
out.emptyAnswers = untranslated;
out.answersWithUnfilledPlaceholders = unfilled;

// A non-English answer that is byte-identical to the English one means
// the table fell back rather than translating.
out.langsIdenticalToEnglish = LANGS.filter(
  (lg) => lg !== 'en' && langReport[lg][0] === langReport.en[0]
);

// ---- the score field is labelled, not raw ---------------------------
const scoreHist = hist('health_score', [55, 60, 75, 80]);
const scoreLabelRaw = {};
for (const lg of LANGS) {
  LANG = lg;
  scoreLabelRaw[lg] = /health score/.test(H.answer('trend_health_score', scoreHist));
}
LANG = 'en';
out.scoreShowsRawFieldName = LANGS.filter((lg) => lg !== 'en' && scoreLabelRaw[lg]);

// ---- an unknown id is not silently answered -------------------------
out.unknownIdHandled = H.has('trend_not_a_real_field') === false
  && H.answer('trend_not_a_real_field', probe) === ''
  && H.has('whatif_sleep_hours') === false;   // belongs to another family

console.log(JSON.stringify(out));
