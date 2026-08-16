/* Single point of contact with the FastAPI backend. Wraps `fetch` with
   auth-header injection, consistent error shaping (ApiError), and
   401 -> logout handling, so every page-controller script calls a
   plain `window.DWApi.xxx()` method instead of hand-rolling requests. */
(function () {
  const TOKEN_KEY = 'dwai_token';
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
    try { localStorage.removeItem('dwai_greeted'); } catch (e) {}
  }
  function isAuthed() { return !!getToken(); }

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

  async function request(path, { method = 'GET', body, auth = true, isBlob = false, isFormData = false } = {}) {
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
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

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
          'The server did not answer within ' + Math.round(REQUEST_TIMEOUT_MS / 1000)
          + 's (' + getBase() + path + '). If another copy of the app is still '
          + 'running, close it and try again.', 0);
      }
      throw new ApiError('Network error — is the API reachable at ' + getBase() + '?', 0);
    } finally {
      clearTimeout(timer);
    }

    if (res.status === 401) {
      clearToken();
      document.dispatchEvent(new CustomEvent('dwai:unauthorized'));
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
    probe, notTheApiMessage, isNotTheApi,

    register: (email, password, display_name) =>
      request('/auth/register', { method: 'POST', body: { email, password, display_name }, auth: false }),
    login: (email, password) =>
      request('/auth/login', { method: 'POST', body: { email, password }, auth: false }),
    me: () => request('/auth/me'),
    saveOnboarding: (payload) => request('/auth/me/onboarding', { method: 'PUT', body: payload }),
    forgotPassword: (email) => request('/auth/forgot-password', { method: 'POST', body: { email }, auth: false }),
    resetPassword: (reset_token, new_password) =>
      request('/auth/reset-password', { method: 'POST', body: { reset_token, new_password }, auth: false }),

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
    importHistoryCsv: (file, allowUpdate = false) => {
      const form = new FormData();
      form.append('file', file);
      form.append('allow_update', allowUpdate ? 'true' : 'false');
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
      }),
    endDemoSession: () => request('/demo/session', { method: 'DELETE' }),

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
