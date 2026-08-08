/* Single point of contact with the FastAPI backend. Wraps `fetch` with
   auth-header injection, consistent error shaping (ApiError), and
   401 -> logout handling, so every page-controller script calls a
   plain `window.DWApi.xxx()` method instead of hand-rolling requests. */
(function () {
  const TOKEN_KEY = 'dwai_token';
  const BASE_KEY = 'dwai_api_base';

  function getBase() {
    return localStorage.getItem(BASE_KEY) || (location.origin + '/api/v1');
  }
  function setBase(url) { localStorage.setItem(BASE_KEY, url.replace(/\/$/, '')); }

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
  function clearToken() { localStorage.removeItem(TOKEN_KEY); }
  function isAuthed() { return !!getToken(); }

  class ApiError extends Error {
    constructor(message, status, fieldErrors) {
      super(message);
      this.status = status;
      this.fieldErrors = fieldErrors || null;
    }
  }

  async function request(path, { method = 'GET', body, auth = true, isBlob = false } = {}) {
    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (auth && getToken()) headers['Authorization'] = `Bearer ${getToken()}`;

    let res;
    try {
      res = await fetch(getBase() + path, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (networkErr) {
      throw new ApiError('Network error — is the API reachable at ' + getBase() + '?', 0);
    }

    if (res.status === 401) {
      clearToken();
      document.dispatchEvent(new CustomEvent('dwai:unauthorized'));
    }

    if (!res.ok) {
      let payload = null;
      try { payload = await res.json(); } catch (e) {}
      const errObj = payload && payload.error ? payload.error : null;
      if (errObj && errObj.field_errors) {
        throw new ApiError(errObj.message || 'Validation failed', res.status, errObj.field_errors);
      }
      const message = (errObj && errObj.message) || `Request failed (${res.status})`;
      throw new ApiError(message, res.status, null);
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

    register: (email, password, display_name) =>
      request('/auth/register', { method: 'POST', body: { email, password, display_name }, auth: false }),
    login: (email, password) =>
      request('/auth/login', { method: 'POST', body: { email, password }, auth: false }),
    me: () => request('/auth/me'),
    saveOnboarding: (payload) => request('/auth/me/onboarding', { method: 'PUT', body: payload }),

    featureSchema: () => request('/schema/features', { auth: false }),
    demoProfiles: () => request('/schema/demo-profiles', { auth: false }),

    predict: (user_data, persist = true) => {
      let excluded_recommendation_categories = [];
      try { excluded_recommendation_categories = JSON.parse(localStorage.getItem('dwai_excluded_rec_categories') || '[]'); } catch (e) {}
      return request('/predict', { method: 'POST', body: { user_data, persist, excluded_recommendation_categories } });
    },

    history: (page = 1, page_size = 20) => request(`/history?page=${page}&page_size=${page_size}`),
    currentWeek: () => request('/history/weeks/current'),
    previousWeek: () => request('/history/weeks/previous'),
    analyticsSummary: () => request('/analytics/summary'),

    personaAssign: (user_data) => request('/personas/assign', { method: 'POST', body: { user_data } }),
    reportPdf: (user_data, persist = false) =>
      request('/reports/pdf', { method: 'POST', body: { user_data, persist }, isBlob: true }),

    generatePlan: (payload) => request('/plan', { method: 'POST', body: payload }),
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

    health: async () => {
      const root = getBase().replace(/\/api\/v1$/, '');
      const res = await fetch(root + '/health');
      if (!res.ok) throw new ApiError('API not reachable', res.status);
      return res.json();
    },
  };

  window.DWApi = Api;
})();
