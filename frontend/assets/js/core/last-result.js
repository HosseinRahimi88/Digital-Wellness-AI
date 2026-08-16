/* DWLastResult — the most recent prediction, per account, with a server fallback.

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

   WHAT THIS DOES
   One place that owns the cache, with the account id in the key, and an
   `ensure()` that asks the server when the cache is empty. The server is
   the source of truth for what a user has recorded; localStorage is only
   an optimisation, and treating it as authoritative is what produced a
   page confidently telling a user something false about themselves. */
(function () {
  const BASE_KEY = 'dwai_last_result';

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
      if (raw) return JSON.parse(raw);
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
      if (parsed) set(parsed);
      return parsed;
    } catch (e) {
      return null;
    }
  }

  function set(result) {
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
      return result ? set(result) : null;
    } catch (e) {
      // A failed lookup is "we do not know", not "there is nothing".
      // The caller shows its empty state either way; what matters is
      // that it is not cached as an answer.
      return null;
    }
  }

  window.DWLastResult = { get, set, clear, ensure, key };
})();
