/*
  Exercises the real frontend/assets/js/features/motivation.js under node.
*/
const path = require('path');

const FRONTEND = path.join(__dirname, '..', '..', 'frontend', 'assets', 'js');

let currentLang = 'en';
global.window = { DWI18n: { get: () => currentLang, pick: (t) => t[currentLang] || t.en } };

require(path.join(FRONTEND, 'features/motivation.js'));
const M = window.DWMotivation;

const out = {};

// Band selection must follow what actually happened.
out.bands = {
  firstEver: M.bandFor(84, null, 1),
  lowFalling: M.bandFor(30, 'down', 10),
  lowRising: M.bandFor(30, 'up', 10),
  strongHolding: M.bandFor(88, 'flat', 10),
  strongRising: M.bandFor(88, 'up', 10),
  middleFalling: M.bandFor(60, 'down', 10),
  middleRising: M.bandFor(60, 'up', 10),
  noScore: M.bandFor(null, null, 10),
};

// The score has to reach the sentence.
out.withScore = M.encouragement({ score: 84.4, direction: 'flat', entries: 10 });
out.scoreRendered = /84/.test(out.withScore);
out.noPlaceholderLeft = !/\{score\}/.test(out.withScore);

// No score -> no hole in the sentence, and no stray placeholder.
out.noScoreLine = M.encouragement({ score: null, direction: null, entries: 10 });
out.noScoreHasNoPlaceholder = !/\{score\}/.test(out.noScoreLine);

// A falling middle score and a holding strong score must not get the
// same sentence - that was the whole point of choosing by situation.
out.fallingLine = M.encouragement({ score: 60, direction: 'down', entries: 10 });
out.holdingLine = M.encouragement({ score: 88, direction: 'flat', entries: 10 });
out.differentLines = out.fallingLine !== out.holdingLine;

// Facts: topical when we know the field, still something when we do not.
out.sleepFact = M.fact('sleep');
out.unknownTopicFact = M.fact('no_such_topic');
out.nullTopicFact = M.fact(null);
out.allFactsNonEmpty = [out.sleepFact, out.unknownTopicFact, out.nullTopicFact]
  .every((f) => typeof f === 'string' && f.length > 20);

out.topicMapping = {
  sleep_hours: M.topicForField('sleep_hours'),
  pickup_density: M.topicForField('pickup_density'),
  social_comparison_1_10: M.topicForField('social_comparison_1_10'),
  unknown_field: M.topicForField('unknown_field'),
};

// Rotation must be stable within a day (re-opening a page must not
// shuffle the text under the reader).
out.stableWithinDay = M.encouragement({ score: 60, direction: 'up', entries: 10 })
  === M.encouragement({ score: 60, direction: 'up', entries: 10 });

// Every language must produce a real sentence, not an empty string.
out.perLanguage = {};
['en', 'fa', 'ar', 'zh'].forEach((lang) => {
  currentLang = lang;
  out.perLanguage[lang] = {
    enc: M.encouragement({ score: 60, direction: 'down', entries: 10 }).length,
    fact: M.fact('focus').length,
  };
});
currentLang = 'en';

// Count the library so a future edit that guts it is visible.
out.factGroups = Object.keys(M.FACTS).length;
out.factCount = Object.keys(M.FACTS).reduce((n, k) => n + M.FACTS[k].length, 0);
out.encouragementBands = Object.keys(M.ENCOURAGEMENT).length;
out.encouragementCount = Object.keys(M.ENCOURAGEMENT)
  .reduce((n, k) => n + M.ENCOURAGEMENT[k].length, 0);

// Every line, in every band and group, must carry all four languages.
const missing = [];
Object.keys(M.FACTS).forEach((g) => M.FACTS[g].forEach((f, i) => {
  ['en', 'fa', 'ar', 'zh'].forEach((l) => { if (!f[l]) missing.push(`FACTS.${g}[${i}].${l}`); });
}));
Object.keys(M.ENCOURAGEMENT).forEach((b) => M.ENCOURAGEMENT[b].forEach((e, i) => {
  ['en', 'fa', 'ar', 'zh'].forEach((l) => { if (!e[l]) missing.push(`ENC.${b}[${i}].${l}`); });
}));
out.missingLanguages = missing;

console.log(JSON.stringify(out));
