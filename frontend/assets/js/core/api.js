/* Single point of contact with the FastAPI backend. Wraps `fetch` with
   auth-header injection, consistent error shaping (ApiError), and
   401 -> logout handling, so every page-controller script calls a
   plain `window.DWApi.xxx()` method instead of hand-rolling requests. */
(function () {
  const TOKEN_KEY = 'dwai_token';
  const REFRESH_KEY = 'dwai_refresh_token';
  const BASE_KEY = 'dwai_api_base';

  // Long enough for a PDF report on a slow machine, short enough that a
  // request which is never coming back is reported rather than waited on.
  const REQUEST_TIMEOUT_MS = 45000;

  function getBase() {
    return localStorage.getItem(BASE_KEY) || (location.origin + '/api/v1');
  }
  function setBase(url) { localStorage.setItem(BASE_KEY, url.replace(/\/$/, '')); }

  function getToken() { return localStorage.getItem(TOKEN_KEY); }

  /* The mascot greets once per sign-in, not once per page (see
     mascot.js). Both of these are the moments that legitimately reset
     that: a new token is a new session, and clearing one is a sign out.
     Kept here rather than in mascot.js because this is the only place
     that actually knows when a session begins or ends. */
  function setToken(t) {
    localStorage.setItem(TOKEN_KEY, t);
    try { localStorage.removeItem('dwai_greeted'); } catch (e) {}
  }
  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    try { localStorage.removeItem('dwai_greeted'); } catch (e) {}
  }
  function isAuthed() { return !!getToken(); }

  /* ---- refresh -----------------------------------------------------
     The access token lasts an hour. Before this existed, hour number two
     was a 401 in the middle of whatever the user was doing, an instant
     logout, and a re-typed password - and because the app polls, that
     landed as often as not on a background call rather than a click.

     `setSession` is what every auth response now goes through, so the
     refresh token is stored in exactly one place. A response without one
     (an older backend) simply leaves the app on the previous behaviour. */
  function setSession(res) {
    if (!res || !res.access_token) return res;
    setToken(res.access_token);
    if (res.refresh_token) localStorage.setItem(REFRESH_KEY, res.refresh_token);
    return res;
  }
  function getRefreshToken() { return localStorage.getItem(REFRESH_KEY); }

  /* Refreshes are funnelled through one promise. A page that fires five
     calls at once and has them all come back 401 must renew ONCE - five
     concurrent refreshes would spend the token five times, and the store
     treats a token spent twice as a stolen one and ends every session.
     Racing here would log the user out for being quick. */
  let refreshInFlight = null;

  function refreshSession() {
    if (refreshInFlight) return refreshInFlight;
    const refreshToken = getRefreshToken();
    if (!refreshToken) return Promise.resolve(false);

    refreshInFlight = fetch(getBase() + '/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).then((res) => {
      if (!res.ok) return null;
      return res.json().catch(() => null);
    }).then((body) => {
      if (!body || !body.access_token) {
        // The refresh token is spent, revoked or was never ours. Drop it
        // so the next 401 goes straight to the sign-in screen instead of
        // retrying a credential that cannot work.
        localStorage.removeItem(REFRESH_KEY);
        return false;
      }
      setSession(body);
      return true;
    }).catch(() => false).finally(() => {
      refreshInFlight = null;
    });

    return refreshInFlight;
  }

  class ApiError extends Error {
    /* `code` is the backend's stable machine-readable error code
       (the `error.code` in its JSON envelope). Callers that need to
       tell two failures with the same status apart - e.g. a day that
       was never recorded vs. one recorded before full detail was kept,
       both 404 - branch on this instead of pattern-matching the
       human-facing message, which is translated and will change. */
    constructor(message, status, fieldErrors, code) {
      super(message);
      this.status = status;
      this.fieldErrors = fieldErrors || null;
      this.code = code || null;
    }
  }

  /* ---- "you started the wrong half of the app" detection ----------
     501 Not Implemented and 405 Method Not Allowed are what a static
     file server says to a POST; Python's http.server sends exactly
     `501 Unsupported method ('POST')`. An HTML body where JSON belongs
     is the same situation seen from the other side - a directory
     listing or a 404 page. None of these can come from this API, which
     answers every route in JSON. */
  function isNotTheApi(res) {
    if (res.status === 501 || res.status === 405) return true;
    const type = res.headers.get('content-type') || '';
    return !res.ok && type.indexOf('text/html') !== -1;
  }

  const NOT_THE_API = {
    en: 'The API is not running at this address — the page you are looking at is being served by a plain file server, which can show pages but cannot sign you in. Close it, then start the app with "python run.py" (or double-click start.bat on Windows) and open the address it prints.',
    fa: 'API روی این آدرس اجرا نشده — صفحه‌ای که می‌بینی توسط یک سرور فایل ساده سرو می‌شود که می‌تواند صفحه نشان بدهد ولی نمی‌تواند تو را وارد کند. آن را ببند، بعد برنامه را با «python run.py» اجرا کن (در ویندوز روی start.bat دوبار کلیک کن) و آدرسی را که چاپ می‌کند باز کن.',
    ar: 'واجهة البرمجة غير مشغَّلة على هذا العنوان — الصفحة التي تراها يقدّمها خادم ملفات بسيط، يستطيع عرض الصفحات ولا يستطيع تسجيل دخولك. أغلقه، ثم شغّل التطبيق بـ «python run.py» (أو انقر نقراً مزدوجاً على start.bat في ويندوز) وافتح العنوان الذي يطبعه.',
    zh: '这个地址上没有运行 API——你看到的页面是由一个普通文件服务器提供的，它能显示页面，却无法为你登录。请关掉它，然后用「python run.py」启动应用（Windows 上双击 start.bat），并打开它输出的地址。',
  };

  function notTheApiMessage() {
    try {
      const lang = (window.DWI18n && window.DWI18n.get && window.DWI18n.get()) || 'en';
      return NOT_THE_API[lang] || NOT_THE_API.en;
    } catch (e) {
      return NOT_THE_API.en;
    }
  }

  /** Is a real API answering at the configured base?
   *
   *  Deliberately a GET of /health: a static file server answers GET
   *  happily, so the check cannot rely on the request failing - it
   *  relies on the ANSWER not being this API's health payload. Returns
   *  a reason rather than a bare false, because the caller's whole job
   *  is to explain the problem. */
  async function probe() {
    const root = getBase().replace(/\/api\/v1$/, '');
    let res;
    try {
      res = await fetch(root + '/health', { method: 'GET' });
    } catch (e) {
      return { ok: false, reason: 'unreachable' };
    }
    if (isNotTheApi(res) || !res.ok) return { ok: false, reason: 'not_the_api' };
    try {
      const body = await res.json();
      if (!body || typeof body !== 'object' || !('status' in body)) {
        return { ok: false, reason: 'not_the_api' };
      }
    } catch (e) {
      // 200 with a non-JSON body is a static server serving something
      // that happens to sit at that path.
      return { ok: false, reason: 'not_the_api' };
    }
    return { ok: true };
  }

  /* The one place the app's selected language becomes a request
     parameter. Server-rendered artifacts (PDF, CSV) cannot read
     DWI18n, so they have to be told. */
  function currentLang() {
    try {
      return (window.DWI18n && window.DWI18n.get && window.DWI18n.get()) || 'en';
    } catch (e) {
      return 'en';
    }
  }

  /* One retry, and only for an authenticated call that came back 401
     with a refresh token available. Everything else is passed straight
     through: an unauthenticated 401 has nothing to renew, and retrying
     a second time would loop.

     `_retried` is what stops the loop - the retry calls the same
     function with it set, so a 401 that survives the renewal reaches
     the caller as a 401 exactly like before. */
  async function request(path, options = {}) {
    try {
      return await requestOnce(path, options);
    } catch (err) {
      const canRetry = err instanceof ApiError
        && err.status === 401
        && options.auth !== false
        && !options._retried
        && !!getRefreshToken()
        && path.indexOf('/auth/refresh') === -1;
      if (!canRetry) throw err;
      const renewed = await refreshSession();
      if (!renewed) throw err;
      return requestOnce(path, Object.assign({}, options, { _retried: true }));
    }
  }

  async function requestOnce(path, { method = 'GET', body, auth = true, isBlob = false, isFormData = false, timeoutMs } = {}) {
    const headers = {};
    // FormData bodies (file uploads) must NOT get a manual Content-Type -
    // the browser sets its own with the correct multipart boundary.
    if (body !== undefined && !isFormData) headers['Content-Type'] = 'application/json';
    if (auth && getToken()) headers['Authorization'] = `Bearer ${getToken()}`;

    /* Every request is given a deadline.
       `fetch` on its own waits as long as the browser is willing to,
       which on a request that never answers means a spinner that never
       stops and, eventually, a bare gateway-timeout page that blames
       the network. Aborting ourselves turns that into a sentence, in
       the app, naming the address that failed - which is the only
       version of this a user can act on. The PDF/report calls are the
       slow ones, so the limit is generous rather than tight. */
    const controller = new AbortController();
    /* A caller may ask for longer. Building a demo is one bounded call
       that does real work - 23 days of model-scored history plus ten
       friends, each with their own diary and conversations - and on a
       modest laptop it can outrun the default deadline. When it did,
       the abort above surfaced as "the server did not answer" and threw
       the user out of a demo that was still being built correctly. */
    const deadline = timeoutMs || REQUEST_TIMEOUT_MS;
    const timer = setTimeout(() => controller.abort(), deadline);

    let res;
    try {
      res = await fetch(getBase() + path, {
        method,
        headers,
        body: isFormData ? body : (body !== undefined ? JSON.stringify(body) : undefined),
        signal: controller.signal,
      });
    } catch (networkErr) {
      if (networkErr && networkErr.name === 'AbortError') {
        throw new ApiError(
          'The server did not answer within ' + Math.round(deadline / 1000)
          + 's (' + getBase() + path + '). If another copy of the app is still '
          + 'running, close it and try again.', 0);
      }
      throw new ApiError('Network error — is the API reachable at ' + getBase() + '?', 0);
    } finally {
      clearTimeout(timer);
    }

    if (res.status === 401) {
      // Only give up when there is nothing left to try. Clearing the
      // token here unconditionally - which is what this did - meant the
      // retry above renewed a session the app had already thrown away,
      // and the 'dwai:unauthorized' listeners had already bounced the
      // user to the sign-in screen before the new token arrived.
      if (!getRefreshToken()) {
        clearToken();
        document.dispatchEvent(new CustomEvent('dwai:unauthorized'));
      }
    }

    /* The app is being served by something that is not the API.
       A static file server (`python -m http.server`, an editor's live
       preview, a plain file:// open) serves the pages perfectly well
       with GET and then answers every POST with 501, or 405, or an
       HTML 404 page. The raw status is useless to the person reading
       it: nothing in "501" suggests that the way they STARTED the app
       is the problem rather than the app itself.

       Detected here, once, and reported in words - this is the single
       place every request passes through, so no caller has to know
       about it. */
    if (isNotTheApi(res)) {
      throw new ApiError(notTheApiMessage(), res.status, null);
    }

    if (!res.ok) {
      let payload = null;
      try { payload = await res.json(); } catch (e) {}
      const errObj = payload && payload.error ? payload.error : null;
      if (errObj && errObj.field_errors) {
        throw new ApiError(errObj.message || 'Validation failed', res.status, errObj.field_errors, errObj.code);
      }
      const message = (errObj && errObj.message) || `Request failed (${res.status})`;
      throw new ApiError(message, res.status, null, errObj && errObj.code);
    }

    if (isBlob) return res.blob();
    if (res.status === 204) return null;
    const text = await res.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch (parseErr) {
      throw new ApiError('Received an invalid response from the server.', res.status, null);
    }
  }

  const Api = {
    setBase, getBase, getToken, setToken, clearToken, isAuthed, ApiError,
    setSession, refreshSession, getRefreshToken,
    probe, notTheApiMessage, isNotTheApi,

    register: (email, password, display_name, security_question, security_answer) =>
      request('/auth/register', {
        method: 'POST', auth: false,
        body: { email, password, display_name, security_question, security_answer },
      }),
    login: (email, password) =>
      request('/auth/login', { method: 'POST', body: { email, password }, auth: false }),
    me: () => request('/auth/me'),
    saveOnboarding: (payload) => request('/auth/me/onboarding', { method: 'PUT', body: payload }),
    forgotPassword: (email) => request('/auth/forgot-password', { method: 'POST', body: { email }, auth: false }),
    verifyEmail: (token) =>
      request('/auth/verify-email', { method: 'POST', body: { token }, auth: false }),
    resendVerification: () => request('/auth/resend-verification', { method: 'POST' }),
    // Ends every session server-side. The access token in hand keeps
    // working until it expires - it is stateless by design - but nothing
    // renews after it, which is the part a logout can actually promise.
    logout: () => request('/auth/logout', { method: 'POST' }).catch(() => null),
    resetPassword: (reset_token, new_password) =>
      request('/auth/reset-password', { method: 'POST', body: { reset_token, new_password }, auth: false }),

    /* The recovery route that does not need a mail server. `question`
       comes back null both for an unregistered address and for an
       account with no question - the server refuses to tell the two
       apart, so neither does this. */
    securityQuestion: (email) =>
      request('/auth/security-question', { method: 'POST', body: { email }, auth: false }),
    resetPasswordWithAnswer: (email, answer, new_password) =>
      request('/auth/reset-password-with-answer', {
        method: 'POST', auth: false, body: { email, answer, new_password },
      }),
    setSecurityQuestion: (question, answer, current_password) =>
      request('/auth/security-question/set', {
        method: 'POST', body: { question, answer, current_password },
      }),

    featureSchema: () => request('/schema/features', { auth: false }),
    demoProfiles: () => request('/schema/demo-profiles', { auth: false }),

    /* `allow_update` is the "edit today's check-in" tick. One main
       check-in per day is enforced server-side; without this flag a
       second persisted submission for today comes back 409
       `already_checked_in_today` instead of silently overwriting the
       result already saved (record() is an upsert - that overwrite was
       real, and it lost an 84.01 to a 78.41 with no warning). */
    predict: (user_data, persist = true, allow_update = false) => {
      let excluded_recommendation_categories = [];
      try { excluded_recommendation_categories = JSON.parse(localStorage.getItem('dwai_excluded_rec_categories') || '[]'); } catch (e) {}
      return request('/predict', {
        method: 'POST',
        body: { user_data, persist, allow_update, excluded_recommendation_categories },
      });
    },

    /* Whether today already has a main check-in, plus the answers it
       was built from. Asked of the server rather than read out of
       localStorage: a second device or a cleared browser knows nothing
       about a day the server has already recorded. */
    todayCheckIn: () => request('/history/today'),

    history: (page = 1, page_size = 20) => request(`/history?page=${page}&page_size=${page_size}`),
    // One past day in full, so it can be reopened on the result screen.
    // The score comes back as it was recorded, not re-predicted.
    historyDetail: (entryDate) => request(`/history/${encodeURIComponent(entryDate)}/detail`),
    /* Every recorded day's own ANSWERS, oldest first, in one call - not
       the full result payload `historyDetail` rebuilds. Used to give a
       demo the shelf of saved check-in files a person with that much
       history would really have. */
    historySnapshots: (limit = 60) => request(`/history/snapshots?limit=${limit}`),
    currentWeek: () => request('/history/weeks/current'),
    previousWeek: () => request('/history/weeks/previous'),
    setHistoryExcluded: (entryDate, excluded) =>
      request(`/history/${entryDate}/exclude`, { method: 'PUT', body: { excluded } }),
    /* Same edit tick as `predict`. The questionnaire export is a single
       undated row, and an undated single row is filed under TODAY - so
       re-uploading one is the easiest way to overwrite a day by
       accident. Rows landing on an already-recorded day come back in
       `failed_rows` with an `already_recorded:` error unless the tick
       is on. */
    /* `opts.dryRun` scores the file and stores nothing - the "I only
       want to see what this says" path. It is a separate flag rather
       than a mode string because the two are independent server-side:
       a dry run has nothing to overwrite, so allow_update is simply
       irrelevant to it. */
    importHistoryCsv: (file, allowUpdate = false, opts = {}) => {
      const form = new FormData();
      form.append('file', file);
      form.append('allow_update', allowUpdate ? 'true' : 'false');
      form.append('dry_run', opts.dryRun ? 'true' : 'false');
      return request('/history/import-csv', { method: 'POST', body: form, isFormData: true });
    },
    csvTemplateUrl: () => getBase() + '/schema/csv-template',

    // Progress / identity / privacy
    progressSummary: () => request('/progress/summary'),
    insights: () => request('/insights'),
    insightCards: () => request('/insights/cards'),
    // C-3 / D-2. `badges` is the user's own view and includes private
    // awareness indicators; `publicBadges` is the achievement-only set
    // and is the only one a friend-facing surface may read.
    badges: () => request('/badges'),
    publicBadges: () => request('/badges/public'),

    // D-1: League chat. Note what is NOT sent anywhere here - no member
    // list, no sender id, no conversation membership. Everything that
    // decides who may read or write is resolved server-side per request.
    chatConversations: () => request('/league/chat/conversations'),
    chatOpenDirect: (friend_user_id) =>
      request('/league/chat/direct', { method: 'POST', body: { friend_user_id } }),
    chatCreateGroup: (title, member_ids) =>
      request('/league/chat/groups', { method: 'POST', body: { title, member_ids } }),
    chatLeaveGroup: (conversationId) =>
      request(`/league/chat/groups/${conversationId}/leave`, { method: 'POST' }),
    chatMessages: (conversationId, limit = 50) =>
      request(`/league/chat/conversations/${conversationId}/messages?limit=${limit}`),
    chatSend: (conversationId, body) =>
      request(`/league/chat/conversations/${conversationId}/messages`, { method: 'POST', body: { body } }),
    chatRenameConversation: (conversationId, title) =>
      request(`/league/chat/conversations/${conversationId}/title`, { method: 'PUT', body: { title } }),
    chatDeleteMessage: (messageId) =>
      request(`/league/chat/messages/${messageId}`, { method: 'DELETE' }),
    chatReport: (message_id, reason, also_block = false) =>
      request('/league/chat/report', { method: 'POST', body: { message_id, reason, also_block } }),
    chatBlock: (user_id) => request('/league/chat/block', { method: 'POST', body: { user_id } }),
    chatUnblock: (user_id) => request('/league/chat/unblock', { method: 'POST', body: { user_id } }),
    personaIdentity: () => request('/personas/identity'),
    dataDictionary: () => request('/schema/data-dictionary', { auth: false }),
    saveProfileExtras: (payload) => request('/auth/me/profile-extras', { method: 'PUT', body: payload }),
    // Fetched rather than linked: the export endpoint is authenticated,
    // and a plain <a href> cannot carry the Authorization header, so a
    // direct link would just 401. Returns a Blob the caller saves.
    exportMyData: () => request('/privacy/export.json', { isBlob: true }),
    // C-5-7: one CSV in the language the user picked, with a UTF-8 BOM
    // so a spreadsheet opens fa/ar/zh correctly instead of as mojibake.
    exportMyDataCsv: () => request('/privacy/export.csv?lang=' + currentLang(), { isBlob: true }),
    deleteMyData: () => request('/privacy/me', { method: 'DELETE' }),
    analyticsSummary: () => request('/analytics/summary'),

    personaAssign: (user_data) => request('/personas/assign', { method: 'POST', body: { user_data } }),
    // C-5-9: the report is generated in the language the app is showing.
    // If the server cannot typeset that language it returns an English
    // report carrying a note that says so, rather than blank boxes.
    reportPdf: (user_data, persist = false) =>
      request('/reports/pdf?lang=' + currentLang(), {
        method: 'POST', body: { user_data, persist }, isBlob: true,
      }),

    generatePlan: (payload) => request('/plan', { method: 'POST', body: payload }),
    /* Whether today fell outside this week's score band and still needs
       an answer. Decided entirely server-side - the band, the day's
       position in the week and the score all live there, and a browser
       that recomputed any of them would either nag about an ordinary
       day or quietly skip a real one. */
    planDayStatus: () => request('/plan/day-status'),
    /* The two halves of the week's plan: signals to strengthen, and the
       ones already worth protecting. Built server-side from the user's
       most recent STORED check-in, so a second device or a cleared
       browser gets the same answer. */
    planTracks: () => request('/plan/tracks'),
    /* Each recent day scored on both halves - logged, and plan task
       done - which is what the dashboard's colours mean. */
    dayStatuses: (days = 28) => request(`/progress/days?days=${days}`),
    /* Three days down in a row - the clearest early signal this data
       produces, and the one the dashboard used to draw and say nothing
       about. See services/wellness/decline_service.py for the run rule and why
       the penalty is an accountability figure, never an edit to the
       score. */
    declineCheck: () => request('/progress/decline'),
    acknowledgeDecline: (runId, reason) => request('/progress/decline/ack', {
      method: 'POST', body: { run_id: runId, reason: reason || '' },
    }),
    planDayDecision: (decision, user_data = {}, date = null) =>
      request('/plan/day-decision', { method: 'POST', body: { decision, user_data, date } }),
    updatePlanTask: (day_number, task_index, completed) =>
      request('/plan/tasks', { method: 'PUT', body: { day_number, task_index, completed } }),

    modelPerformance: () => request('/model-performance', { auth: false }),

    futurePathDefinitions: () => request('/future-path/definitions', { auth: false }),
    futurePathCompare: (user_data, path_keys) => request('/future-path/compare', { method: 'POST', body: { user_data, path_keys } }),
    parallelTwin: (user_data) => request('/parallel-twin/compare', { method: 'POST', body: { user_data } }),

    whatifSweep: (user_data, field, num_points = 9) =>
      request('/whatif/sweep', { method: 'POST', body: { user_data, field, num_points } }),
    whatifGoalSeek: (user_data, field, target_score, num_points = 15) =>
      request('/whatif/goal-seek', { method: 'POST', body: { user_data, field, target_score, num_points } }),

    cohortAvailability: () => request('/cohorts/availability', { auth: false }),
    cohortComparison: () => request('/cohorts/me/comparison'),

    // Friends League
    leagueMe: () => request('/league/me'),
    leagueAcceptRules: () => request('/league/rules/accept', { method: 'POST' }),
    // shared_categories must be forwarded: league.js passes the user's
    // ticked boxes, and dropping them here made every request arrive with
    // an empty sharing list (the backend field defaults to []), so the
    // friend saw nothing even though the user had chosen what to share.
    leagueRedeemInvite: (invite_code, shared_categories = []) =>
      request('/league/invite/redeem', { method: 'POST', body: { invite_code, shared_categories } }),
    leaguePendingRequests: () => request('/league/requests/pending'),
    leagueSentRequests: () => request('/league/requests/sent'),
    leagueRespondRequest: (connection_id, approve, shared_categories) =>
      request(`/league/requests/${connection_id}/respond`, { method: 'POST', body: { approve, shared_categories } }),
    leagueSharingUpdate: (connection_id, shared_categories) =>
      request(`/league/connections/${connection_id}/sharing`, { method: 'PUT', body: { shared_categories } }),
    leagueConnections: () => request('/league/connections'),
    leagueLeaderboard: () => request('/league/leaderboard'),
    leagueRevoke: (connection_id) => request(`/league/connections/${connection_id}`, { method: 'DELETE' }),

    /* The book on the About page. One page per day, keyed by ISO date -
       writing the same date twice edits that page rather than adding a
       second one, which is the server's rule and not the client's. */
    journalList: (limit = 120) => request(`/journal?limit=${encodeURIComponent(limit)}`),
    journalDay: (day) => request(`/journal/${encodeURIComponent(day)}`),
    journalSave: (day, text, mood = null) =>
      request(`/journal/${encodeURIComponent(day)}`, { method: 'PUT', body: { text, mood } }),
    journalDelete: (day) => request(`/journal/${encodeURIComponent(day)}`, { method: 'DELETE' }),
    /* The whole book as a PDF. Server-rendered, so it has to be TOLD
       the language - see currentLang() above for why that is a
       parameter rather than something the backend can read. */
    journalPdf: (lang) => request(
      `/journal.pdf?lang=${encodeURIComponent(lang || currentLang())}`, { isBlob: true },
    ),

    /* The personal dossier: measured time in the app, this account
       against the cohort, a model fitted on its own days, and the facts
       its history supports. The heartbeat posts SECONDS THE BROWSER
       MEASURED; the server caps them, so an honest client and a
       dishonest one produce the same ceiling. */
    personalInsight: () => request('/personal/insight'),
    personalHeartbeat: (seconds) => request('/personal/heartbeat', { method: 'POST', body: { seconds } }),
    personalBirthDate: (birth_date) =>
      request('/personal/birth-date', { method: 'PUT', body: { birth_date } }),

    demoPopulate: () => request('/demo/populate', { method: 'POST' }),
    // A demo runs in its own account and hands back its own token - see
    // assets/js/demo.js for why populating the signed-in account was the
    // wrong shape.
    demoCatalogue: () => request('/demo/catalogue', { auth: false }),
    /* `with_violations` picks the LAPSED variant of a demo state: real
       gaps in the history, plan days left undone, badges spent paying
       for them and violations left over. It is what takes the demo
       catalogue from sixteen states to thirty-two, and the only way to
       reach the greyed/red day strip, the violations panel and an
       empty badge wall. */
    demoSession: (days, profile, friends, with_violations = false) =>
      request('/demo/session', {
        method: 'POST',
        body: { days, profile, friends, with_violations },
        /* The heaviest state - 23 days, ten friends, lapsed - scores
           every day through the real model and writes ten friends'
           diaries and conversations. It finishes well inside this on a
           server, but the default 45s deadline was tight enough that a
           slower machine got an abort instead of a demo, which read as
           "the demo is broken" when nothing was. Four minutes is far
           past anything measured and still short of forever. */
        timeoutMs: 240000,
      }),
    endDemoSession: () => request('/demo/session', { method: 'DELETE' }),
    /* The week menu. A plan snapshot is stored per ISO week, so a
       23-day demo leaves four of them; these read what is stored and
       never generate a plan for a week that never had one. */
    planWeeks: () => request('/plan/weeks'),
    planWeek: (weekKey) => request(`/plan/weeks/${encodeURIComponent(weekKey)}`),


    coachContext: (language, mutedTopics) => request(
      `/coach/context?language=${encodeURIComponent(language || 'en')}`
      + `&muted_topics=${encodeURIComponent((mutedTopics || []).join(','))}`
    ),

    health: async () => {
      const root = getBase().replace(/\/api\/v1$/, '');
      const res = await fetch(root + '/health');
      if (!res.ok) throw new ApiError('API not reachable', res.status);
      return res.json();
    },
  };

  window.DWApi = Api;
})();
