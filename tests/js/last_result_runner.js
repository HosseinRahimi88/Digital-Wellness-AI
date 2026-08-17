/* Runs the real frontend/assets/js/core/last-result.js under node.

   THE DEFECT

   A prediction the server did not record - the "I'm only testing this"
   tick, which posts `persist: false` - was cached exactly like a real
   check-in. Everything downstream then described a day that never
   happened. Measured in a real browser before the fix: the server held
   a recorded 87.67, a throwaway test scored 53.06, and the Coach read
   back 53.06.

   The flag that distinguishes them (`persisted`) has always been on the
   /predict response; it was simply dropped at the cache boundary. So
   the boundary is where it is enforced, and this exercises the real
   module rather than a description of it. */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..', '..');

// A localStorage good enough for this module: get/set/remove of strings.
const store = new Map();
global.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};

// A signed-in account. The module reads the `sub` claim to scope its
// key; only the middle segment is ever decoded.
function token(sub) {
  const claims = Buffer.from(JSON.stringify({ sub })).toString('base64')
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return `header.${claims}.signature`;
}

global.window = {};
global.atob = (b64) => Buffer.from(b64, 'base64').toString('binary');

// eslint-disable-next-line no-eval
eval(fs.readFileSync(path.join(ROOT, 'frontend/assets/js/core/last-result.js'), 'utf8'));
const DWLastResult = global.window.DWLastResult;

const results = [];
function check(name, fn) {
  try { fn(); results.push(['PASS', name]); }
  catch (e) { results.push(['FAIL', name, e.message]); }
}

function reset() {
  store.clear();
  store.set('dwai_token', token('user-a'));
}

// ------------------------------------------------------------------
reset();
check('a recorded result is cached', () => {
  DWLastResult.set({ regression_score: 87.67, persisted: true });
  assert.strictEqual(DWLastResult.get().regression_score, 87.67);
});

reset();
check('a result with no persisted flag is cached (history, demo)', () => {
  // A day reopened from history carries no such flag and is real.
  DWLastResult.set({ regression_score: 71.2 });
  assert.strictEqual(DWLastResult.get().regression_score, 71.2);
});

reset();
check('a NON-persisted result is refused', () => {
  const stored = DWLastResult.set({ regression_score: 53.06, persisted: false });
  assert.strictEqual(stored, null, 'set() should report the refusal');
  assert.strictEqual(DWLastResult.get(), null);
});

reset();
check('a test run leaves the real recorded result standing', () => {
  // The exact scenario reported: check in for real, then run a test.
  // The Coach must keep answering about the real one.
  DWLastResult.set({ regression_score: 87.67, persisted: true });
  DWLastResult.set({ regression_score: 53.06, persisted: false });
  assert.strictEqual(DWLastResult.get().regression_score, 87.67);
});

reset();
check('a cache poisoned by the old build heals on read', () => {
  // A browser that ran a test check-in before this guard existed still
  // has that result on disk under the scoped key.
  store.set(DWLastResult.key(), JSON.stringify({ regression_score: 53.06, persisted: false }));
  assert.strictEqual(DWLastResult.get(), null);
  assert.strictEqual(store.get(DWLastResult.key()), undefined, 'and is dropped, not re-read');
});

reset();
check('the payload comes back with a recorded result', () => {
  DWLastResult.set({ regression_score: 87.67, persisted: true });
  store.set('dwai_last_payload', JSON.stringify({ sleep_hours: 8 }));
  assert.strictEqual(DWLastResult.payload().sleep_hours, 8);
});

reset();
check('the payload is withheld when the result beside it is a test', () => {
  // Both keys are poisoned on a browser that ran a test on the old
  // build. Healing one and not the other leaves the answers from a day
  // that was never recorded answering for the user.
  store.set(DWLastResult.key(), JSON.stringify({ regression_score: 53.06, persisted: false }));
  store.set('dwai_last_payload', JSON.stringify({ sleep_hours: 4 }));
  assert.strictEqual(DWLastResult.payload(), null);
});

reset();
check('the payload is withheld when there is no result at all', () => {
  store.set('dwai_last_payload', JSON.stringify({ sleep_hours: 8 }));
  assert.strictEqual(DWLastResult.payload(), null);
});

reset();
check('a second account does not see the first account cached result', () => {
  DWLastResult.set({ regression_score: 87.67, persisted: true });
  store.set('dwai_token', token('user-b'));
  assert.strictEqual(DWLastResult.get(), null);
});

// ---- ensure(): restoring from the server must not orphan a payload --
//
// The upgrade path that reaches this: a browser poisoned by the old
// build holds a test result AND the test payload. get() drops the
// result, ensure() then restores the user's REAL recorded day from the
// server - and the test day's answers would still be sitting beside it,
// now passing the "is there a result?" check.
const asyncChecks = [];

function checkAsync(name, fn) {
  asyncChecks.push(
    fn().then(
      () => results.push(['PASS', name]),
      (e) => results.push(['FAIL', name, e.message]),
    ),
  );
}

function serverWith(day) {
  global.window.DWApi = {
    isAuthed: () => true,
    history: async () => ({ items: [{ date: '2026-08-17' }] }),
    historyDetail: async () => ({ result: day }),
  };
}

reset();
checkAsync('ensure() restores the recorded day from the server', async () => {
  serverWith({ regression_score: 87.67 });
  const restored = await DWLastResult.ensure();
  assert.strictEqual(restored.regression_score, 87.67);
});

reset();
checkAsync('ensure() drops a payload it cannot vouch for', async () => {
  store.set(DWLastResult.key(), JSON.stringify({ regression_score: 53.06, persisted: false }));
  store.set('dwai_last_payload', JSON.stringify({ sleep_hours: 4 }));
  serverWith({ regression_score: 87.67 });
  await DWLastResult.ensure();
  assert.strictEqual(DWLastResult.get().regression_score, 87.67, 'the real day is restored');
  assert.strictEqual(
    DWLastResult.payload(), null,
    'the test day answers must not survive beside the restored real result');
});

Promise.all(asyncChecks).then(finish);

function finish() {
  const failedChecks = results.filter((r) => r[0] === 'FAIL');
  results.forEach((r) => console.log(r.join(' :: ')));
  console.log(`\n${results.length - failedChecks.length}/${results.length} passed`);
  process.exit(failedChecks.length ? 1 : 0);
}

