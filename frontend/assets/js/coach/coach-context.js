/*
  Coach context loader.

  The Coach must read the user's WHOLE picture before it answers
  anything - not just whichever single check-in happened to be sitting in
  localStorage. This module owns that read:

    · GET /coach/context returns the server-side digest of the user's
      full logged history (trends, streaks, best/worst, sufficiency).
    · The browser then layers on what only it has: the freshest
      prediction result (which carries the SHAP factors) and the muted
      coaching topics, both of which live in localStorage.

  Freshness over caching: the digest is re-fetched whenever a new
  prediction is recorded, and treated as stale after STALE_AFTER_MS, so
  the Coach can never quote numbers from before the user's last
  check-in. A stale-but-present digest is still returned if the network
  fails - answering from slightly old real data beats refusing to
  answer - and `stale: true` is set so callers can say so.
*/
(function () {
  const STALE_AFTER_MS = 60 * 1000;

  let cached = null;
  let cachedAt = 0;
  let inFlight = null;

  function mutedTopics() {
    try {
      const raw = localStorage.getItem('dwai_excluded_rec_categories');
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) { return []; }
  }

  function localResult() {
    try { return window.DWLastResult.get(); } catch (e) { return null; }
  }
  function localPayload() {
    // Via DWLastResult, not straight out of localStorage: the answers
    // and the result they produced are only usable as a pair, and a
    // test check-in must not reach the Coach through either half.
    try { return window.DWLastResult.payload(); } catch (e) { return null; }
  }

  /* Merge the browser-only pieces into the server digest. The server has
     no access to either, so without this the Coach would lose the SHAP
     factors and the user's mute list. */
  function enrich(digest) {
    const result = localResult();
    const payload = localPayload();
    const ctx = Object.assign({}, digest);

    if (result) {
      if (result.regression_score != null) ctx.latest_score = result.regression_score;
      if (result.prediction) ctx.latest_class = result.prediction;
      const factors = result.shap_features || [];
      if (factors.length) {
        ctx.top_factors = factors.slice(0, 6).map((f) => ({
          feature: f.feature,
          impact: f.shap_value,
          direction: (f.shap_value || 0) > 0 ? 'raises' : 'lowers',
        }));
      }
      ctx.active_recommendations = (result.recommendations || []).slice(0, 5).map((r) => ({
        category: r.category,
        action: r.action || r.recommendation,
        reason: r.reason,
      }));
    }
    ctx.raw_latest = payload || null;
    ctx.muted_topics = mutedTopics();
    return ctx;
  }

  /** True when there is genuinely nothing logged to talk about. */
  function isEmpty(ctx) {
    return !ctx || ((ctx.entry_count || 0) === 0 && ctx.latest_score == null);
  }

  /**
   * Read everything known about this user. Always resolves - never
   * throws - because a chat reply must not die on a failed fetch.
   */
  async function load(opts) {
    const force = !!(opts && opts.force);
    const fresh = cached && (Date.now() - cachedAt) < STALE_AFTER_MS;
    if (!force && fresh) return enrich(cached);
    if (inFlight) { try { await inFlight; } catch (e) {} return enrich(cached || {}); }

    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    inFlight = (async () => {
      try {
        const digest = await window.DWApi.coachContext(lang, mutedTopics());
        // The two halves of the week's plan - what to strengthen, and
        // what is already worth protecting. Fetched here rather than in
        // the answer path so the coach never has to say "let me check"
        // mid-reply, and read from the SERVER's copy of the user's last
        // check-in rather than from localStorage, which a second device
        // or a cleared browser would not have.
        try {
          digest.plan_tracks = await window.DWApi.planTracks();
        } catch (e) {
          // Additive: every other answer still works without it, and
          // the two track answers say plainly that they have nothing to
          // read rather than inventing generic advice.
          digest.plan_tracks = null;
        }
        cached = digest;
        cachedAt = Date.now();
      } catch (e) {
        // Keep whatever we had; mark it so callers can be honest.
        if (cached) cached.stale = true;
      } finally {
        inFlight = null;
      }
    })();
    await inFlight;
    return enrich(cached || {});
  }

  /** Called after a new prediction so the next answer sees it. */
  function invalidate() { cached = null; cachedAt = 0; }

  /* A compact, human-readable summary of what was just read. Used to
     open an answer with "here is what I looked at", which is the whole
     point of reading everything first - the user can see it happened. */
  function digestLine(ctx) {
    const P = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);
    if (isEmpty(ctx)) return null;

    const bits = [];
    if (ctx.entry_count) {
      bits.push(P({
        en: `${ctx.entry_count} check-in(s)`,
        fa: `${ctx.entry_count} بررسی`,
        ar: `${ctx.entry_count} تسجيل`,
        zh: `${ctx.entry_count} 次记录`,
      }));
    }
    if (ctx.latest_score != null) {
      bits.push(`${Math.round(ctx.latest_score)}/100`);
    }
    if (ctx.score_change_7d != null) {
      const sign = ctx.score_change_7d >= 0 ? '+' : '';
      bits.push(P({
        en: `${sign}${ctx.score_change_7d} vs 7d ago`,
        fa: `${sign}${ctx.score_change_7d} نسبت به ۷ روز پیش`,
        ar: `${sign}${ctx.score_change_7d} مقارنةً بـ٧ أيام`,
        zh: `${sign}${ctx.score_change_7d} 相比7天前`,
      }));
    }
    if (ctx.streak_days) {
      bits.push(P({
        en: `${ctx.streak_days}-day streak`,
        fa: `${ctx.streak_days} روز پیوسته`,
        ar: `${ctx.streak_days} يوم متتابع`,
        zh: `连续 ${ctx.streak_days} 天`,
      }));
    }
    if (!bits.length) return null;

    const prefix = P({
      en: 'Read your data', fa: 'داده‌هایت را خواندم',
      ar: 'قرأت بياناتك', zh: '已读取你的数据',
    });
    return `${prefix}: ${bits.join(' · ')}`;
  }

  window.DWCoachContext = { load, invalidate, isEmpty, digestLine };
})();
