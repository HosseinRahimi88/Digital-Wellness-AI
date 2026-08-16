/*
  Runs every question the demo coach threads ship, in all four
  languages, through the REAL matcher - the same way
  coach_nlu_corpus_runner.js does: a window stub, then require() the
  actual frontend files, so this breaks when the real answer path
  breaks rather than when a copy of it does.

  What it checks, per language:
    · every scripted question reaches a real answer, not the "I'm not
      sure I follow" fallback, the "say more" nudge, or the off-topic /
      no-data refusals;
    · the answer is not empty;
    · every one of the thirty-two states gets at least four threads.

  A question that lands on the wrong answer is not detectable here
  (the coach has no notion of "wrong"), so the seeder's own comments
  record that each was chosen by reading what it actually returned.
  What IS detectable, and what this catches, is a question that lands
  nowhere - which is the failure that would make the demo's coach look
  broken rather than empty.

  Run as: node demo_coach_chats_runner.js <repoRoot>
  Prints one JSON object: { checked, failures: [...], threadCounts }.
*/
const path = require('path');

const repoRoot = process.argv[2];
if (!repoRoot) {
  console.error('usage: node demo_coach_chats_runner.js <repoRoot>');
  process.exit(2);
}
const jsDir = path.join(repoRoot, 'frontend', 'assets', 'js');

const LANGS = ['en', 'fa', 'ar', 'zh'];
const PROFILES = ['healthy', 'improving', 'borderline', 'at_risk'];
const LENGTHS = [3, 7, 15, 23];

let LANG = 'en';
globalThis.window = {};
window.DWI18n = { get: () => LANG, pick: (t) => (t && t[LANG]) || (t && t.en) || '' };
window.localStorage = {
  _d: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
  setItem(k, v) { this._d[k] = String(v); },
  removeItem(k) { delete this._d[k]; },
};
globalThis.localStorage = window.localStorage;

require(path.join(jsDir, 'coach/coach-nlu.js'));
require(path.join(jsDir, 'coach/coach-labels.js'));
require(path.join(jsDir, 'coach/coach-knowledge.js'));
require(path.join(jsDir, 'coach/coach-knowledge-life.js'));
require(path.join(jsDir, 'coach/coach-knowledge-app.js'));
require(path.join(jsDir, 'coach/coach-knowledge-plan.js'));
require(path.join(jsDir, 'coach/coach-chat.js'));
require(path.join(jsDir, 'coach/coach-demo-chats.js'));

/* A demo user's context, in the shape the real app produces:
   shap directions are "increase"/"decrease" (services/ml/shap_service.py),
   plan tracks carry theme/theme_i18n/current/target (api/schemas/plan.py),
   and the digest carries the fields api/schemas/coach.py declares. */
const ctx = {
  score: 61.4,
  className: 'Moderate',
  confidence: 78.2,
  persona: null,
  topSignals: [
    { feature: 'sleep_hours', direction: 'decrease', score: -6.2, value: 5.4 },
    { feature: 'screen_time_hours', direction: 'decrease', score: -4.9, value: 7.8 },
    { feature: 'exercise_minutes', direction: 'increase', score: 3.1, value: 35 },
  ],
  recommendations: [
    { title: 'Protect your sleep window', action: 'Put the phone outside the bedroom by 23:30.', metric: '7h for 5 of 7 nights', category: 'sleep', priority: 1 },
    { title: 'Cut late-night scrolling', action: 'One 20-minute block after dinner, not four.', metric: 'under 45 min after 21:00', category: 'screen_time', priority: 2 },
  ],
  raw: { sleep_hours: 5.4, screen_time_hours: 7.8 },
};
const full = {
  entry_count: 23,
  latest_score: 61.4,
  latest_class: 'Moderate',
  score_change_7d: 4.2,
  streak_days: 6,
  best_score: 74,
  worst_score: 41,
  longest_streak: 9,
  data_sufficiency: 'good',
  trends: [
    { field_name: 'sleep_hours', label: 'Sleep hours', higher_is_better: true, recent_mean: 5.4, earlier_mean: 6.3, change: -0.9, direction: 'worsening' },
    { field_name: 'exercise_minutes', label: 'Exercise minutes', higher_is_better: true, recent_mean: 35, earlier_mean: 21, change: 14, direction: 'improving' },
  ],
  top_factors: [{ feature: 'sleep_hours', impact: -6.2, direction: 'lowers' }],
  active_recommendations: [{ category: 'sleep', action: 'Put the phone outside the bedroom by 23:30.', reason: 'lowest factor' }],
  plan_tracks: {
    strengthen: [{ theme: 'sleep', theme_i18n: { en: 'Sleep', fa: 'خواب', ar: 'النوم', zh: '睡眠' }, icon: '\u{1F6CF}', current: 5.4, target: 7, gap: 0.23 }],
    maintain: [{ theme: 'movement', theme_i18n: { en: 'Movement', fa: 'تحرک', ar: 'الحركة', zh: '运动' }, icon: '\u{1F3C3}', current: 35, target: 30, margin: 0.17 }],
  },
  muted_topics: [],
  raw_latest: { sleep_hours: 5.4 },
};

const failures = [];
let checked = 0;

LANGS.forEach((code) => {
  LANG = code;
  const c = window.DWCoachChat.copy();
  // The replies that mean "I did not understand you". unknown is a
  // prefix rather than an exact match because the near-miss path
  // appends "did you mean ...".
  const exact = new Set([c.clarify, c.noData, c.offtopic, c.medical, c.crisis, c.trendUnavailable]);

  window.DWCoachDemoChats.THREADS.forEach((thread) => {
    if (!thread.title[code]) failures.push({ lang: code, thread: thread.key, why: 'untranslated title' });
    thread.asks.forEach((ask) => {
      if (!ask[code]) {
        failures.push({ lang: code, thread: thread.key, why: 'untranslated question' });
        return;
      }
      checked += 1;
      const reply = window.DWCoachChat.respond(ask[code], ctx, full);
      const text = (reply && reply.text) || '';
      if (!text.trim()) {
        failures.push({ lang: code, thread: thread.key, q: ask[code], why: 'empty answer' });
      } else if (exact.has(text) || text.indexOf(c.unknown) === 0) {
        failures.push({ lang: code, thread: thread.key, q: ask[code], why: 'fallback: ' + text.slice(0, 60) });
      }
    });
  });
});

/* A Chinese message that matches nothing must get the honest fallback
   that names the closest topics - NOT the "could you say a bit more?"
   nudge meant for a two-word message. Chinese has no spaces, so the
   original whitespace word count read every Chinese question, however
   long, as one word. Checked here rather than only in the scripted
   questions, because those now all match an intent before they ever
   reach that line. */
LANG = 'zh';
const zhCopy = window.DWCoachChat.copy();
const zhLong = window.DWCoachChat.respond(
  '这个星期我一直在想一件完全无关的事情究竟应该怎么处理才好', ctx, full,
);
const cjkNudgeBug = zhLong.text === zhCopy.clarify;

/* Every one of the thirty-two states, and how many threads it gets. */
const threadCounts = {};
PROFILES.forEach((profile) => {
  LENGTHS.forEach((days) => {
    [false, true].forEach((lapsed) => {
      const key = `${profile}:${days}:${lapsed ? 'lapsed' : 'clean'}`;
      threadCounts[key] = window.DWCoachDemoChats.scriptsFor(profile, lapsed).length;
    });
  });
});

console.log(JSON.stringify({ checked, failures, threadCounts, cjkNudgeBug }));
