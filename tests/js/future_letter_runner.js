/*
  Exercises the real frontend/assets/js/features/future-letter.js under node.
  Stubs only what the module touches: window.DWI18n for language, and
  DWCoachLabels for field names.
*/
const path = require('path');

const FRONTEND = path.join(__dirname, '..', '..', 'frontend', 'assets', 'js');

let currentLang = 'en';
global.window = {
  DWI18n: {
    get: () => currentLang,
    pick: (t) => t[currentLang] || t.en,
  },
  DWCoachLabels: { sleep_hours: 'sleep hours' },
};

require(path.join(FRONTEND, 'features/future-letter.js'));
const F = window.DWFutureLetter;

// A fixed "today" so the dateline assertion is not a race against midnight.
const NOW = new Date('2026-08-12T09:00:00Z');

const ctx = (days) => ({
  days,
  recentScore: 78,
  direction: 'up',
  bestDay: 'Tuesday',
  bestScore: 88,
  improvedField: 'sleep_hours',
  now: NOW,
});

const out = {
  minDays: F.MIN_DAYS,
  daysAhead: F.DAYS_AHEAD,
  noDays: F.compose(ctx(0)),
  atSixDays: F.compose(ctx(6)),
  atSevenDays: F.compose(ctx(7)),
};

// The dateline must be exactly DAYS_AHEAD past the letter's "now".
currentLang = 'en';
out.datelineEn = F.datelineFor(NOW);
const parsed = new Date(out.datelineEn);
out.datelineOffsetDays = Math.round((parsed - NOW) / 86400000);

currentLang = 'fa';
out.datelineFa = F.datelineFor(NOW);

// An unknown language must not throw - it falls back to a plain date.
currentLang = 'xx';
out.datelineJunkLocale = F.datelineFor(NOW);

console.log(JSON.stringify(out));
