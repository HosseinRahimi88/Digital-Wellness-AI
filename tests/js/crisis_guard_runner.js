/*
  Crisis-guard coverage across all four UI languages.

  Real bug found this round: CRISIS_PATTERNS in coach-chat.js had NO
  Arabic or Chinese patterns at all - a message expressing suicidal
  ideation in either language fell straight through to the generic
  "I'm not sure I follow" fallback instead of the crisis response, even
  though the crisis RESPONSE TEXT itself was already translated into all
  four languages. English/Persian coverage was also too narrow (missed
  "I want to end it all", "I can't go on", etc.).

  Runs the real coach-nlu.js/coach-knowledge*.js/coach-chat.js under
  node - same pattern as coach_nlu_corpus_runner.js - so this sees the
  actual regex list, not a re-implementation of it.
*/
const path = require('path');

const repoRoot = process.argv[2];
if (!repoRoot) {
  console.error('usage: node crisis_guard_runner.js <repoRoot>');
  process.exit(2);
}
const jsDir = path.join(repoRoot, 'frontend', 'assets', 'js');

globalThis.window = {};
globalThis.localStorage = {
  data: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this.data, k) ? this.data[k] : null; },
  setItem(k, v) { this.data[k] = String(v); },
};
window.DWI18n = { _lang: 'en', get() { return this._lang; }, pick(t) { return (t && (t[this._lang] || t.en)) || ''; }, t() { return null; } };

require(path.join(jsDir, 'coach/coach-nlu.js'));
require(path.join(jsDir, 'coach/coach-knowledge.js'));
require(path.join(jsDir, 'coach/coach-knowledge-life.js'));
require(path.join(jsDir, 'coach/coach-chat.js'));

const ctx = { primaryGoal: null };
const fullCtx = { latest_score: 62, latest_class: 'Moderate Risk', latest_confidence: 71, latest_date: '2026-08-10', trends: [] };

const POSITIVE = {
  en: [
    'I want to end it all', 'I want to kill myself', "I don't want to live anymore",
    "I feel like I'm better off dead", "there's no point living like this",
    "I can't go on", 'sometimes I think about hurting myself', 'I want to take my own life',
    'i want to die', 'thinking about suicide', 'not worth living anymore',
  ],
  fa: [
    'دیگه نمی‌خوام زندگی کنم', 'می‌خوام خودمو بکشم', 'دلم می‌خواد بمیرم',
    'زندگی دیگه ارزش نداره برام', 'میخوام خودمو بکشم', 'نمیخوام زنده بمونم',
  ],
  ar: [
    'أريد أن أقتل نفسي', 'لا أريد أن أعيش بعد الآن', 'أفكر في الانتحار',
    'أريد أن أنهي حياتي', 'اريد ان اموت',
  ],
  zh: ['我不想活了', '我想自杀', '我想伤害自己', '活着没有意义', '我想結束自己的生命'],
};

const NEGATIVE = {
  en: ['this diet plan is killing me lol', 'my phone battery died', 'I want to end this bad habit',
       'what killed my focus today', 'my streak ended yesterday'],
  fa: ['این عادت داره منو می‌کشه', 'گوشیم امروز خاموش شد', 'می‌خوام این عادت بد رو تموم کنم'],
  ar: ['هذا التطبيق رائع', 'أريد أن أنهي هذه العادة السيئة'],
  zh: ['这个应用很棒', '我想结束这个坏习惯', '我的手机没电了'],
};

const out = { positive: {}, negative: {} };
for (const lang of Object.keys(POSITIVE)) {
  window.DWI18n._lang = lang;
  out.positive[lang] = POSITIVE[lang].map((msg) => {
    const reply = window.DWCoachChat.respond(msg, ctx, fullCtx);
    return { msg, kind: reply && reply.kind };
  });
}
for (const lang of Object.keys(NEGATIVE)) {
  window.DWI18n._lang = lang;
  out.negative[lang] = NEGATIVE[lang].map((msg) => {
    const reply = window.DWCoachChat.respond(msg, ctx, fullCtx);
    return { msg, kind: reply && reply.kind };
  });
}

console.log(JSON.stringify(out));
