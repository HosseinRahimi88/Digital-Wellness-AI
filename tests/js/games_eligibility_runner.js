/*
  Checks G4 ("a game whose data is not sufficient does not render at
  all - eligible(context) is the only gate") and G6 (all four languages)
  for every game in the real games.js, plus a minimal sanity check that
  each game's `eligible()` is genuinely reachable (not vacuously false
  for every input, which would make the "insufficient data" checks below
  meaningless).

  Deliberately does NOT call game.render() - that touches document.*,
  and this repo has no DOM shim available (see tests/social/test_badge_service.py
  for the established node-execution pattern this follows instead).

  Run as: node games_eligibility_runner.js <repoRoot>
  Prints one JSON object to stdout.
*/
const path = require('path');

const repoRoot = process.argv[2];
if (!repoRoot) {
  console.error('usage: node games_eligibility_runner.js <repoRoot>');
  process.exit(2);
}
const jsDir = path.join(repoRoot, 'frontend', 'assets', 'js');

const store = {};
globalThis.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = v; },
};
globalThis.window = {};
window.DWI18n = { get: () => 'en', pick: (t) => t.en, t: (k) => k };
window.DWBadgeText = { name: (id) => 'Badge:' + id };
require(path.join(jsDir, 'features/games.js'));

const GAMES = window.DWGames.GAMES;

// A context deliberately missing everything every game needs - the
// baseline "insufficient data" case (G4).
const EMPTY_CONTEXT = {};

// A context rich enough to make EVERY game eligible at once, used only
// to prove eligible() can return true at all (catches a game whose
// condition is accidentally unsatisfiable).
const FULL_CONTEXT = {
  score: 72,
  shapFeatures: [
    { feature: 'sleep_hours', direction: 'increase', shap_value: 5, score: 5 },
    { feature: 'notification_density', direction: 'decrease', shap_value: -8, score: -8 },
  ],
  dimensions: [
    { key: 'sleep', score: 80 },
    { key: 'focus', score: 55 },
  ],
  confidenceLevel: 'high',
  confidencePercent: 92,
  futureClass: 'Healthy',
  entryCount: 10,
  unlabelledDay: { date: '2024-01-01', health_score: 70 },
  correlation: { field_a: 'sleep_hours', field_b: 'focus_0_100', direction: 'together', sample_size: 20 },
  streak: { current_streak: 4 },
  weekdayVsWeekend: { weekday_avg: 70, weekend_avg: 60 },
  lockedBadges: [
    { id: 'a', progress: 0.8, target: 1 },
    { id: 'b', progress: 0.3, target: 1 },
  ],
  pastScores: [60, 62, 58, 65, 61, 59, 63],
};

const results = GAMES.map((g) => {
  let emptyOk = null;
  let fullOk = null;
  try { emptyOk = !!g.eligible(EMPTY_CONTEXT); } catch (e) { emptyOk = 'threw: ' + e.message; }
  try { fullOk = !!g.eligible(FULL_CONTEXT); } catch (e) { fullOk = 'threw: ' + e.message; }
  const langs = ['en', 'fa', 'ar', 'zh'].filter((l) => !g.title || !g.title[l]);
  return {
    key: g.key,
    phase: g.phase || null,
    hasGuideTopic: !!g.guideTopic,
    emptyContextEligible: emptyOk,
    fullContextEligible: fullOk,
    missingTitleLanguages: langs,
  };
});

// render()'s own phase filter, called for real rather than
// re-implemented: each game's eligible() is swapped for a spy that
// records its key and returns false, so render() never reaches
// game.render() (which needs a DOM this harness does not have) while
// still exercising the exact candidate list render() built internally -
// `shown` stays 0 by construction, `seen` is the real answer.
function candidatesConsideredFor(phase) {
  const originals = GAMES.map((g) => g.eligible);
  const seen = [];
  GAMES.forEach((g) => { g.eligible = () => { seen.push(g.key); return false; }; });
  const fakeMount = { innerHTML: '', closest: () => null };
  window.DWGames.render(fakeMount, {}, { phase, limit: 100 });
  GAMES.forEach((g, i) => { g.eligible = originals[i]; });
  return seen.sort();
}

const preCandidates = candidatesConsideredFor('pre');
const postCandidates = candidatesConsideredFor('post');

const preCount = GAMES.filter((g) => g.phase === 'pre').length;
const postCount = GAMES.filter((g) => g.phase === 'post').length;
const untagged = GAMES.filter((g) => g.phase !== 'pre' && g.phase !== 'post').map((g) => g.key);

console.log(JSON.stringify({
  count: GAMES.length, results, preCount, postCount, untagged,
  preCandidates, postCandidates,
}));
