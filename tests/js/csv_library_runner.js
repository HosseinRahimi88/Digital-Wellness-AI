/*
  Exercises the real frontend/assets/js/features/csv-library.js under node, the
  same pattern as the other JS runners in this directory: stub window +
  localStorage, require() the actual shipped file, print one JSON blob.
*/
const path = require('path');

const FRONTEND = path.join(__dirname, '..', '..', 'frontend', 'assets', 'js');

global.window = {};
global.localStorage = {
  data: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this.data, k) ? this.data[k] : null; },
  setItem(k, v) { this.data[k] = String(v); },
};

require(path.join(FRONTEND, 'features/csv-library.js'));
const L = window.DWCsvLibrary;

const payload = {
  sleep_hours: 7.5,
  stress_0_10: 3,
  tricky_comma: 'has, a comma',
  tricky_quote: 'say "hi"',
  blank: '',
};

const csv = L.toCsv(payload);
const parsed = L.fromCsv(csv);

// A saved entry's shelf must come from the exclude flag, not a guess.
const savedMain = L.save('Real day', payload, { excluded: false, score: 84.4 });
const savedTest = L.save('Hypothetical', payload, { excluded: true, score: 60 });

const out = {
  csv,
  headerCols: csv.split('\n')[0].split(',').length,
  parsedKeys: Object.keys(parsed || {}).sort(),
  numberStaysNumber: typeof (parsed || {}).sleep_hours === 'number',
  commaSurvived: (parsed || {}).tricky_comma === 'has, a comma',
  quoteSurvived: (parsed || {}).tricky_quote === 'say "hi"',

  malformedHeaderOnly: L.fromCsv('a,b,c'),
  malformedEmpty: L.fromCsv(''),
  malformedRagged: L.fromCsv('a,b,c\n1,2'),

  emptyNameRejected: L.save('', payload, {}),
  nonObjectPayloadRejected: L.save('x', null, {}),

  mainKind: savedMain.entry.kind,
  testKind: savedTest.entry.kind,
  scoreRounded: savedMain.entry.score,
  nameTrimmed: L.save('   padded   ', payload, {}).entry.name,

  listAll: L.list().length,
  listMain: L.list('main').length,
  listTest: L.list('test').length,

  fileNames: {
    fa: L.fileNameFor({ name: 'سه‌شنبه‌ی کاری' }),
    en: L.fileNameFor({ name: 'My Tuesday' }),
    zh: L.fileNameFor({ name: '普通的周二' }),
    ar: L.fileNameFor({ name: 'ثلاثاء عادي' }),
    junkOnly: L.fileNameFor({ name: '!!!' }),
  },
};

// Removal must actually remove.
const firstId = L.list()[0].id;
out.removedLeaves = L.remove(firstId).length;
out.removedIsGone = L.get(firstId) === null;

/* ---- Two accounts, one browser ----------------------------------------
   The library keys off the `sub` claim of the access token, so signing
   into a second account on the same machine has to show that account's
   shelf and not the first one's. This is the whole bug: the key used to
   be one fixed string, so account B opened account A's saved check-ins -
   somebody else's answers about their own sleep, stress and screen use,
   listed under B's name.

   Exercised by swapping the token the way a real sign-in does, rather
   than by calling an internal - the token IS the mechanism, and a test
   that reached past it would pass with the bug present. */
function tokenFor(sub) {
  const claims = Buffer.from(JSON.stringify({ sub })).toString('base64')
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return 'header.' + claims + '.signature';
}

global.localStorage.data = {};           // a clean browser
localStorage.setItem('dwai_token', tokenFor('user-alice'));
L.save('Alice private day', payload, { excluded: false, score: 71 });
out.aliceSees = L.list().map((e) => e.name);

localStorage.setItem('dwai_token', tokenFor('user-bob'));
out.bobSeesAfterSwitch = L.list().map((e) => e.name);
L.save('Bob own day', payload, { excluded: false, score: 55 });
out.bobSees = L.list().map((e) => e.name);

localStorage.setItem('dwai_token', tokenFor('user-alice'));
out.aliceSeesAfterBob = L.list().map((e) => e.name);

// Signed out entirely: neither account's shelf may show.
localStorage.setItem('dwai_token', '');
out.signedOutSees = L.list().map((e) => e.name);

// And the keys really are distinct, not one key with a suffix nobody reads.
out.storedKeys = Object.keys(localStorage.data)
  .filter((k) => k.indexOf('dwai_csv_library') === 0).sort();

console.log(JSON.stringify(out));
