/*
  Picking the reader's language out of a server-composed sentence.

  Some text on the result and dashboard screens is written by the backend
  rather than by i18n.js - the confidence reading, the out-of-distribution
  warning, the cold-start note, the result framing. Those sentences are
  assembled from the user's own numbers and thresholds, so they cannot
  live in the frontend dictionary; but the server has no idea which
  language the reader picked, because that choice lives in localStorage.

  So the server sends every sentence in all four languages under a
  `text_i18n: { part: { lang: text } }` map, and this picks one. It is the
  same arrangement the recommendation text already used - this module
  exists so the four call sites stop each reinventing the same three-step
  fallback, and so that fallback is written down once:

      the reader's language -> the flat English field -> empty string

  Never a blank where a sentence belongs, and never a raw `[object Object]`
  from reading the map itself by mistake.
*/
(function () {
  const FLAT_FALLBACK = {
    message: 'message',
    headline: 'headline',
    detail: 'detail',
  };

  function lang() {
    return (window.DWI18n && window.DWI18n.get && window.DWI18n.get()) || 'en';
  }

  /**
   * pick(payload, part) -> string
   *
   * `payload` is any server object carrying a `text_i18n` map (an OOD
   * report, a confidence label, a cold-start status). `part` names the
   * sentence wanted, e.g. 'message' or 'detail'.
   */
  function pick(payload, part) {
    if (!payload) return '';
    const key = part || 'message';
    const table = (payload.text_i18n || {})[key];
    if (table) {
      const own = table[lang()];
      if (typeof own === 'string' && own) return own;
      if (typeof table.en === 'string' && table.en) return table.en;
    }
    // An older response carries only the flat English field.
    const flat = payload[FLAT_FALLBACK[key] || key];
    return typeof flat === 'string' ? flat : '';
  }

  window.DWServerText = { pick };
})();
