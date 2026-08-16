/*
  Measures AI Coach intent coverage against a generated + hand-written
  corpus, using the REAL frontend files (not a re-implementation of their
  logic) - loaded the same way tests/social/test_badge_service.py loads
  badge-registry.js: a minimal `window` stub, then require() the actual
  file, so a change that breaks the real matcher shows up here.

  Run as: node coach_nlu_corpus_runner.js <repoRoot>
  Prints one JSON object to stdout: { total, correct, coverage, byBucket,
  failures } and nothing else, so the Python test can json.loads(stdout).

  Two corpus sources, because the acceptance rule is measured coverage
  over a test corpus, not "these three examples work":

  1. GENERATED: every keyword coach-nlu.js itself extracts from every
     topic's existing regex becomes a test case, in two forms - the exact
     phrase, and a corrupted ("typo") form. This exercises literally every
     topic that ships today, in bulk, without hand-writing one row per
     topic.
  2. HAND-WRITTEN: a smaller set of genuine paraphrases (not just
     misspellings of the same keyword) across a representative sample of
     topics and all four languages, because typo-tolerance on the
     original keyword and understanding a differently-worded question are
     different claims.
*/
const path = require('path');

const repoRoot = process.argv[2];
if (!repoRoot) {
  console.error('usage: node coach_nlu_corpus_runner.js <repoRoot>');
  process.exit(2);
}
const jsDir = path.join(repoRoot, 'frontend', 'assets', 'js');

globalThis.window = {};
window.DWI18n = { get: () => 'en', pick: (t) => t.en };
require(path.join(jsDir, 'coach/coach-nlu.js'));
require(path.join(jsDir, 'coach/coach-knowledge.js'));
require(path.join(jsDir, 'coach/coach-knowledge-life.js'));
require(path.join(jsDir, 'coach/coach-knowledge-app.js'));
require(path.join(jsDir, 'coach/coach-chat.js'));

const nlu = window.DWCoachNLU;
const kb = window.DWCoachKnowledge;

function isCJK(s) { return /[一-鿿]/.test(s); }
function isArabicScript(s) { return /[؀-ۿ]/.test(s); }
function bucketFor(s) {
  if (isCJK(s)) return 'zh';
  if (isArabicScript(s)) return 'fa_ar';
  return 'en';
}

/** One transposition on the longest word in a phrase - a plausible typo,
 *  same shape as "score" -> "scroe" that motivated this whole rewrite.
 *  Returns null when the phrase has no word long enough to safely
 *  fuzz-match (coach-nlu.js requires >=5 chars on each side). */
function corrupt(phrase) {
  const words = phrase.split(' ');
  let idx = -1, best = 0;
  words.forEach((w, i) => { if (w.length > best && !isCJK(w)) { best = w.length; idx = i; } });
  if (idx === -1 || best < 5) return null;
  const w = words[idx];
  const mid = Math.floor(w.length / 2);
  const swapped = w.slice(0, mid - 1) + w[mid] + w[mid - 1] + w.slice(mid + 1);
  if (swapped === w) return null;
  words[idx] = swapped;
  return words.join(' ');
}

/** For a CJK phrase, drop the last character - simulates an incomplete
 *  / shortened input rather than a Latin-style spelling mistake, since
 *  coach-nlu.js matches CJK by substring, not edit distance. */
function shortenCJK(phrase) {
  if (phrase.length < 2) return null;
  return phrase.slice(0, -1);
}

// Anchored/positional topics (see coach-nlu.js: extractKeywords returns
// [] for these on purpose) don't participate in the generated corpus -
// there is nothing to fuzz-test, by design, not by omission.
const POSITIONAL_TOPICS = new Set(['greeting']);

const cases = []; // { text, expectedKey, kind: 'exact'|'typo', bucket }

kb.allTopics().forEach((topic) => {
  if (POSITIONAL_TOPICS.has(topic.key)) return;
  const keywords = nlu.extractKeywords(topic.match.source);
  keywords.forEach((kw) => {
    const bucket = bucketFor(kw);
    cases.push({ text: kw, expectedKey: topic.key, kind: 'exact', bucket });
    const typo = isCJK(kw) ? shortenCJK(kw) : corrupt(kw);
    if (typo) cases.push({ text: typo, expectedKey: topic.key, kind: 'typo', bucket });
  });
});

// Hand-written paraphrases: genuinely different wording, not a spelling
// variant of the same keyword, across a representative sample of topics
// and all four languages this app ships.
const PARAPHRASES = [
  { text: "I can't fall asleep no matter what I try", key: 'sleep', bucket: 'en' },
  { text: 'what should my bedtime actually look like', key: 'sleep', bucket: 'en' },
  { text: 'my mind keeps wandering when I try to work', key: 'focus', bucket: 'en' },
  { text: 'too many pings are driving me crazy', key: 'notifications', bucket: 'en' },
  { text: 'I keep comparing my life to people online', key: 'social', bucket: 'en' },
  { text: 'is it bad that I stay up scrolling reels', key: 'short_video', bucket: 'en' },
  { text: 'how do I actually make a new habit last', key: 'habit_building', bucket: 'en' },
  { text: 'reading upsetting headlines over and over', key: 'doomscrolling', bucket: 'en' },
  { text: 'my neck hurts from looking down at my phone', key: 'posture', bucket: 'en' },
  { text: 'can you trust what this app tells you', key: 'accuracy', bucket: 'en' },
  { text: 'does this app sell my information to anyone', key: 'privacy', bucket: 'en' },
  { text: 'napping in the afternoon, good or bad idea', key: 'naps', bucket: 'en' },
  { text: 'خیلی سخته شبا زود بخوابم', key: 'sleep', bucket: 'fa_ar' },
  { text: 'مدام حواسم پرت میشه سر کار', key: 'focus', bucket: 'fa_ar' },
  { text: 'اعلان‌های گوشیم داره دیوونم میکنه', key: 'notifications', bucket: 'fa_ar' },
  { text: 'اطلاعاتم رو به کسی میفروشید؟', key: 'privacy', bucket: 'fa_ar' },
  { text: 'لا أستطيع التوقف عن مقارنة نفسي بالآخرين', key: 'social', bucket: 'fa_ar' },
  { text: 'رقبتي تؤلمني من النظر إلى الهاتف طويلا', key: 'posture', bucket: 'fa_ar' },
  { text: '我总是很难按时睡觉', key: 'sleep', bucket: 'zh' },
  { text: '工作的时候老是分心', key: 'focus', bucket: 'zh' },
  { text: '通知太多快把我逼疯了', key: 'notifications', bucket: 'zh' },
  { text: '你们会把我的数据卖给别人吗', key: 'privacy', bucket: 'zh' },
];
PARAPHRASES.forEach((p) => cases.push({ text: p.text, expectedKey: p.key, kind: 'paraphrase', bucket: p.bucket }));

const failures = [];
let correct = 0;
const byBucket = {};

cases.forEach((c) => {
  const got = kb.findTopic(c.text);
  const gotKey = got ? got.key : null;
  const ok = gotKey === c.expectedKey;
  byBucket[c.bucket] = byBucket[c.bucket] || { total: 0, correct: 0 };
  byBucket[c.bucket].total += 1;
  if (ok) {
    correct += 1;
    byBucket[c.bucket].correct += 1;
  } else if (failures.length < 60) {
    failures.push({ text: c.text, expected: c.expectedKey, got: gotKey, kind: c.kind, bucket: c.bucket });
  }
});

console.log(JSON.stringify({
  total: cases.length,
  correct,
  coverage: cases.length ? correct / cases.length : 0,
  byBucket,
  failures,
}));
