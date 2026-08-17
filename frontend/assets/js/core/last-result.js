/* DWLastResult — the most recent RECORDED prediction, per account, with
   a server fallback.

   WHAT WAS WRONG
   Eight modules read `localStorage.getItem('dwai_last_result')` directly,
   under one fixed key with no account in it. Two consequences, both seen:

     * the Coach page said "no coaching yet" to somebody who had just
       checked in. The check-in was recorded on the server; what was
       missing was this browser's copy - a different browser, a cleared
       cache, or simply arriving at the page by a route that had not
       written it yet, and the page concluded the user had never used
       the app;

     * signing into a second account on the same machine showed the
       FIRST account's result, because the key did not distinguish them.
       The same defect as the CSV library's, in a more sensitive place:
       this is somebody's health score.

   AND THE ONE THIS MODULE NOW REFUSES
   A prediction the server did NOT record - the "I'm only testing this"
   tick, which posts `persist: false` - was cached here exactly like a
   real check-in. Everything downstream then described a day that never
   happened: with a real 87.67 on the server, a throwaway 53.06 was what
   the Coach read back, and what the dashboard, the weekly plan and the
   simulator started from. The user's own words for it: the coach
   ignores the real assessment and answers about the test one.

   Nothing downstream could have told the difference, because the flag
   that distinguishes them (`persisted`, which /predict has always
   returned) was thrown away at the cache boundary. So the boundary is
   where it is enforced: this cache holds recorded days only.

   WHAT THIS DOES
   One place that owns the cache, with the account id in the key, and an
   `ensure()` that asks the server when the cache is empty. The server is
   the source of truth for what a user has recorded; localStorage is only
   an optimisation, and treating it as authoritative is what produced a
   page confidently telling a user something false about themselves. */
(function () {
  const BASE_KEY = 'dwai_last_result';

  /* A result the server recorded, as opposed to one it merely scored.
     `persisted === false` is the explicit no. `undefined` is treated as
     a yes on purpose: a day reopened from history, or restored by a
     demo, carries no such flag and is unambiguously real. Only the
     endpoint that can say "I did not save this" gets to say it. */
  function isRecorded(result) {
    return !!result && result.persisted !== false;
  }

  /* The signed-in account, from the access token's `sub` claim.
     Decoded without verifying the signature, which is correct here and
     would be wrong anywhere else: nothing is being authorised, a storage
     key is being chosen. */
  function accountId() {
    try {
      const token = localStorage.getItem('dwai_token');
      if (!token) return 'anon';
      const claims = token.split('.')[1];
      if (!claims) return 'anon';
      const sub = JSON.parse(atob(claims.replace(/-/g, '+').replace(/_/g, '/'))).sub;
      return (typeof sub === 'string' && sub) ? sub : 'anon';
    } catch (e) {
      return 'anon';
    }
  }

  function key() { return BASE_KEY + ':' + accountId(); }

  function get() {
    try {
      const raw = localStorage.getItem(key());
      if (raw) {
        const parsed = JSON.parse(raw);
        /* Self-heal a cache poisoned before this guard existed. A
           browser that ran a test check-in on the old build still has
           that result on disk, and it would otherwise keep answering
           for the user until they checked in again. Dropped here rather
           than left for each of the eight readers to remember. */
        if (!isRecorded(parsed)) { clear(); return null; }
        return parsed;
      }
    } catch (e) {}
    /* One read of the old unscoped key, for somebody who checked in
       before this shipped and would otherwise find the app had
       forgotten them. Migrated into the scoped key and the old one
       dropped, so it happens once and never leaks to a second account. */
    try {
      const legacy = localStorage.getItem(BASE_KEY);
      if (!legacy) return null;
      localStorage.removeItem(BASE_KEY);
      const parsed = JSON.parse(legacy);
      if (!isRecorded(parsed)) return null;
      if (parsed) set(parsed);
      return parsed;
    } catch (e) {
      return null;
    }
  }

  /* A result the server did not record is refused, and refused WITHOUT
     touching what is already here: the user's real last check-in is
     still their real last check-in after they run a test, and that is
     precisely what the Coach should keep answering about. Returns null
     so a caller cannot mistake the refusal for a store. */
  function set(result) {
    if (result && !isRecorded(result)) return null;
    try {
      if (result) localStorage.setItem(key(), JSON.stringify(result));
      else localStorage.removeItem(key());
    } catch (e) {}
    return result;
  }

  function clear() { set(null); }

  /* The cache, or the newest thing the server has. Returns null only
     when the account genuinely has no recorded day - which is the one
     case an empty state is telling the truth about. */
  async function ensure() {
    const cached = get();
    if (cached) return cached;
    if (!window.DWApi || !window.DWApi.isAuthed || !window.DWApi.isAuthed()) return null;

    try {
      const history = await window.DWApi.history();
      const items = (history && history.items) || [];
      if (!items.length) return null;
      /* Sorted rather than indexed. The list arrives newest-first, and
         reaching for items[length - 1] - which is what this did at
         first - hands back the OLDEST day on the page. Sorting states
         the requirement instead of depending on an order the endpoint
         is free to change. */
      const newest = items
        .filter((entry) => entry && entry.date)
        .sort((a, b) => String(b.date).localeCompare(String(a.date)))[0];
      if (!newest) return null;
      const detail = await window.DWApi.historyDetail(newest.date);
      const result = (detail && detail.result) || detail;
      if (!result) return null;
      /* Restoring the result orphans the payload. The server hands back
         a recorded DAY; it does not hand back whatever this browser
         happened to have in `dwai_last_payload`, which may be a
         different day entirely - and, for a browser upgrading from the
         build that cached test runs, is quite likely to be the answers
         from a check-in that was never recorded. Two halves of a pair
         from two different days is the failure this module exists to
         prevent, so the stale half goes rather than being left to be
         read beside a result it does not belong to. */
      try { localStorage.removeItem('dwai_last_payload'); } catch (e2) {}
      return set(result);
    } catch (e) {
      // A failed lookup is "we do not know", not "there is nothing".
      // The caller shows its empty state either way; what matters is
      // that it is not cached as an answer.
      return null;
    }
  }

  /* The ANSWERS behind the cached result, under the same rule.
     `dwai_last_payload` is written beside `dwai_last_result` and read by
     seven modules - the Coach, the weekly plan, the league, the
     band-decision card and the simulator - each reaching into
     localStorage directly. So the guard above only half worked: a
     browser that ran a test check-in on the old build has BOTH keys
     poisoned, and clearing one left the other answering. The two are a
     pair or they are nothing - a result from one day beside the answers
     from another is worse than neither - so they are read as a pair
     here, and the payload is only handed back when the result standing
     next to it survived. */
  function payload() {
    if (!get()) return null;
    try {
      return JSON.parse(localStorage.getItem('dwai_last_payload') || 'null');
    } catch (e) {
      return null;
    }
  }

  window.DWLastResult = { get, set, clear, ensure, key, payload };
})();
