/*
  Precision, not recall: does the coach DECLINE questions that are not
  about this app?

  tests/js/coach_nlu_corpus_runner.js measures the opposite property -
  that an in-scope question is understood. Both matter, and only one was
  measured, which is how the following shipped: every keyword containing
  a CJK character acted as a wildcard for EVERY language, because
  wordMatchesToken() did an unguarded symmetric substring test. The
  query word "a" is inside "shap因素是什么"; "far" is inside
  "在safari里能用吗"; "i" is inside "教练是真的ai吗". Each scored 0.9,
  so "how far is the moon?" out-scored the honest refusal and was
  answered with a note about browser support.

  Run as: node coach_precision_runner.js <repoRoot>
  Prints { checked, answered: [...], declined } as JSON.
*/
const path = require('path');

const repoRoot = process.argv[2];
if (!repoRoot) {
  console.error('usage: node coach_precision_runner.js <repoRoot>');
  process.exit(2);
}
const jsDir = path.join(repoRoot, 'frontend', 'assets', 'js');

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

/* A user with plenty of data, so nothing declines merely for lack of
   it - the refusals below have to come from scope, not emptiness. */
const ctx = {
  score: 61.4, className: 'Moderate', confidence: 78.2, persona: null,
  topSignals: [
    { feature: 'sleep_hours', direction: 'decrease', score: -6.2, value: 5.4 },
    { feature: 'exercise_minutes', direction: 'increase', score: 3.1, value: 35 },
  ],
  recommendations: [
    { title: 'Protect your sleep window', action: 'Phone out of the bedroom by 23:30.', metric: '7h', category: 'sleep', priority: 1 },
  ],
  raw: { sleep_hours: 5.4 },
};
const full = {
  entry_count: 23, latest_score: 61.4, latest_class: 'Moderate',
  score_change_7d: 4.2, streak_days: 6, best_score: 74, worst_score: 41,
  trends: [], top_factors: [], active_recommendations: [], muted_topics: [],
  plan_tracks: { strengthen: [], maintain: [] },
};

/* Plainly outside digital wellbeing, and none of them naming a domain
   that OFF_TOPIC_HINTS enumerates - these have to be declined because
   nothing matched, not because a blocklist caught them. */
const OFF_TOPIC = {
  en: [
    'What is the airspeed of a swallow?',
    'How far is the moon?',
    'How do I fix my car engine?',
    'Tell me about quantum physics',
    'Who won the world cup in 1998?',
  ],
  fa: ['قیمت دلار چنده؟', 'پایتخت ژاپن کجاست؟'],
  ar: ['ما هي عاصمة فرنسا؟', 'كم يبعد القمر؟'],
  zh: ['长城有多长？', '珠穆朗玛峰有多高？'],
};

/* Must keep being answered. If a precision fix starts declining these,
   it has gone too far. */
const IN_SCOPE = {
  en: [
    'How do I sleep better?',
    'What is my score today?',
    'Why was a badge taken away from me?',
    'What do the colours mean on the dashboard?',
    'How do I build a habit that sticks?',
  ],
  fa: ['امتیاز امروزم چند است؟', 'چرا نشانم گرفته شد؟'],
  ar: ['ما درجتي اليوم؟', 'لماذا سُحبت شارتي؟'],
  zh: ['我今天的分数是多少？', '仪表盘上日期的颜色是什么意思？'],
};

function isDecline(reply) {
  const c = window.DWCoachChat.copy();
  const t = (reply && reply.text) || '';
  return t === c.clarify || t === c.offtopic || t === c.noData || t.indexOf(c.unknown) === 0;
}

const answered = [];
const wronglyDeclined = [];
let checked = 0;

Object.keys(OFF_TOPIC).forEach((lang) => {
  LANG = lang;
  OFF_TOPIC[lang].forEach((q) => {
    checked += 1;
    const reply = window.DWCoachChat.respond(q, ctx, full);
    if (!isDecline(reply)) {
      answered.push({ lang, q, text: (reply.text || '').slice(0, 80) });
    }
  });
});

Object.keys(IN_SCOPE).forEach((lang) => {
  LANG = lang;
  IN_SCOPE[lang].forEach((q) => {
    checked += 1;
    const reply = window.DWCoachChat.respond(q, ctx, full);
    if (isDecline(reply)) wronglyDeclined.push({ lang, q });
  });
});

/* A known, accepted miss - reported rather than hidden.

   "What is the boiling point of water?" is still answered, because
   "boiling" is two edits from "failing" (similarity 0.714, just over
   the 0.7 fuzzy floor) and "failing" is a reassurance keyword. The
   floor cannot be raised: "routine"/"routeen" sits at 0.71 and must
   keep matching.

   The one clean structural fix would be to require self-reference
   before the fuzzy emotional intents fire, the way the strength and
   why answers already do. That was deliberately NOT done: messages
   like "feeling hopeless" or "can't keep going" carry no self-
   reference token, and those are the messages where a missed match
   costs the most. One odd answer about water is the cheaper error. */
const knownMiss = (() => {
  LANG = 'en';
  const reply = window.DWCoachChat.respond('What is the boiling point of water?', ctx, full);
  return { stillAnswered: !isDecline(reply), similarity: nluSimilarity() };
  function nluSimilarity() {
    return Math.round(window.DWCoachNLU.wordSimilarity('boiling', 'failing') * 1000) / 1000;
  }
})();

/* The specific collisions that caused the wildcard bug, asserted
   directly so a regression names itself. */
const nlu = window.DWCoachNLU;
const wildcards = {
  a_in_shap: nlu.phraseScore(['a'], nlu.normalize('shap因素是什么')),
  far_in_safari: nlu.phraseScore(['far'], nlu.normalize('在safari里能用吗')),
  i_in_ai: nlu.phraseScore(['i'], nlu.normalize('教练是真的ai吗')),
  // The legitimate case: a whole Latin fragment inside a CJK keyword.
  shap_in_shap: nlu.phraseScore(['shap'], nlu.normalize('shap因素是什么')),
  csv_in_csv: nlu.phraseScore(['csv'], nlu.normalize('保存为csv')),
};

console.log(JSON.stringify({ checked, answered, wronglyDeclined, wildcards, knownMiss }));
