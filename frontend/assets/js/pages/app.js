/* app.html's controller: the auth gate, onboarding, multi-step daily
   check-in wizard, and the result page (score, SHAP bars, dimension
   breakdown, recommendations) all live here since app.html is the one
   page a first-time visitor lands on before the shared post-login
   nav shell (shell.js) takes over on every other page. */
(function () {
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $all = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  /* Human label for a raw feature name (e.g. "sleep_hours"), used
     everywhere this page names a SHAP factor or a recommendation's
     source field. window.DWCoachLabels (coach-labels.js) is checked
     first - translated, all four languages. Falls back to the server
     schema's own `label` (real text, but English only - see
     core/feature_schema.py), then to the raw name as a last resort so a
     field this table has not caught up with yet is at least readable. */
  function labelFor(name) {
    if (!name) return '';
    const translated = window.DWCoachLabels && window.DWCoachLabels[name];
    if (translated) return translated;
    const def = state.featureSchemaMap[name];
    if (def && def.label) return def.label;
    return String(name).replace(/_/g, ' ');
  }

  const {
    GOAL_OPTIONS, PURPOSE_OPTIONS, SCHEDULE_OPTIONS,
    EFFORT_OPTIONS, WORK_SCREEN_OPTIONS,
  } = window.DWOnboardingOptions;

  const state = {
    featureSchemaMap: {}, demoProfiles: null, account: null,
    wizardData: {}, stepIndex: 0, demoActive: false, excludeFromAnalysis: false,
    onboard: { goal: null, purpose: null, schedule: null },
    onboardSlide: 0,
    lastPayload: null, lastResult: null,
    // One main check-in per day. `todayCheckIn` is the server's answer
    // to "does today already have one", asked fresh every time the
    // wizard opens - localStorage cannot answer it, because a second
    // device or a cleared browser knows nothing about a day the server
    // has already recorded. `editToday` is the user's explicit "yes, I
    // am editing that day" tick; nothing overwrites a recorded day
    // without it.
    todayCheckIn: null, editToday: false, prefilledFromToday: false,
  };

  // Once an update has actually gone through, the tick stays on and
  // locked for the rest of that day: from that point every further
  // submission is unambiguously another edit of the same day, and
  // letting the user untick it would only offer them a 409. Keyed by
  // date so it clears itself at midnight without any cleanup.
  const EDIT_LOCK_KEY = 'dwai_edit_today_locked_on';
  function todayIso() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }
  function editLockedToday() {
    try { return localStorage.getItem(EDIT_LOCK_KEY) === todayIso(); } catch (e) { return false; }
  }
  function lockEditForToday() {
    try { localStorage.setItem(EDIT_LOCK_KEY, todayIso()); } catch (e) { /* private mode - the tick just is not sticky */ }
  }

  function activeSteps() { return window.DWSchema.stepsFor(state.excludeFromAnalysis); }

  function showView(id) {
    $all('.view').forEach((v) => v.classList.remove('active'));
    const el = document.getElementById(id);
    if (el) el.classList.add('active');
  }

  // ===================== AUTH =====================
  function initAuthTabs() {
    $all('[data-auth-tab]').forEach((btn) => {
      btn.addEventListener('click', () => {
        $all('[data-auth-tab]').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const target = btn.dataset.authTab;
        $('#loginForm').classList.toggle('hidden', target !== 'login');
        $('#registerForm').classList.toggle('hidden', target !== 'register');
      });
    });
  }

  function clearFieldErrors(form) {
    $all('.field', form).forEach((f) => { f.classList.remove('has-error'); f.querySelector('.err').textContent = ''; });
  }
  function markFieldError(form, name, msg) {
    const input = form.querySelector(`[name="${name}"]`);
    if (!input) return;
    const field = input.closest('.field');
    if (field) { field.classList.add('has-error'); field.querySelector('.err').textContent = msg; }
  }

  async function afterLogin() {
    try {
      state.account = await window.DWApi.me();
    } catch (e) {
      window.DWToast.error(e.message);
      return;
    }
    // The one greeting a session gets, said at the only moment it is
    // actually a greeting. This page does not reload on sign-in, so the
    // mascot's own init() already ran while the user was still
    // anonymous and correctly stayed quiet.
    if (window.DWMascot && window.DWMascot.greetOnce) {
      window.DWMascot.greetOnce({ delay: 600 });
    }
    $('#logoutBtn').classList.remove('hidden');
    $('#appNavRow').classList.remove('hidden');
    const bell = $('#notifBell');
    if (bell) { bell.classList.remove('hidden'); if (window.DWChrome) window.DWChrome.wireNotifBell(); }
    // Arriving from a click on a day in the dashboard heatmap. This is
    // checked before onboarding on purpose: the user asked for one
    // specific day, and skipping onboarding does not mark it complete,
    // so gating on it would send anyone who ever pressed "skip" to the
    // intro screen instead of the day they clicked. If the day cannot be
    // opened we fall through to the normal screens rather than leaving
    // them on a dead end.
    const day = new URLSearchParams(window.location.search).get('day');
    if (day && await openPastDay(day)) return;

    if (!state.account.onboarding_complete) {
      renderOnboarding();
      showView('view-onboarding');
      // The tour used to start HERE, on top of the first preference
      // question - so the guide talked over the questionnaire it was
      // supposed to be introducing. It now waits until the answers are
      // in; see the save handler below.
    } else {
      await startWizard();
    }
  }

  /* Reopens a stored check-in on the result screen.

     The result screen is otherwise identical to one the user just
     submitted, so this always shows the banner naming the day. A past
     score read as today's would be worse than not offering this at all.

     Returns true if the day was opened, false if the caller should carry
     on to the check-in screen. */
  async function openPastDay(date) {
    let detail;
    try {
      detail = await window.DWApi.historyDetail(date);
    } catch (e) {
      // The one case worth its own wording: the day exists but predates
      // stored detail, so it is missing rather than broken. Everything
      // else keeps the server's own message.
      window.DWToast.error(e && e.code === 'history_detail_unavailable'
        ? window.DWI18n.t('history_reopen_unavailable')
        : (e && e.message) || window.DWI18n.t('history_reopen_unavailable'));
      return false;
    }

    await ensureSchemaLoaded();
    state.lastPayload = detail.inputs;
    state.viewingPastDay = date;
    // So a CSV saved from this screen lands on the same shelf the day
    // itself sits on, rather than being relabelled by whatever the last
    // live check-in happened to set.
    state.excludeFromAnalysis = !!detail.excluded;

    showView('view-result');
    renderResult(detail.result);
    wirePersonaLine(detail.inputs);

    const banner = $('#pastDayBanner');
    const text = $('#pastDayBannerText');
    const rerun = $('#pastDayRerunBtn');
    if (banner && text) {
      const shown = formatHistoryDate(date);
      text.textContent = window.DWI18n.t('history_reopen_banner').replace('{date}', shown);
      banner.classList.remove('hidden');
      if (rerun && !rerun.dataset.wired) {
        rerun.dataset.wired = '1';
        // Re-running loads that day's answers into the form so one thing
        // can be changed - it does not resubmit them behind the user's back.
        rerun.addEventListener('click', async () => {
          await startWizard();
          state.wizardData = { ...window.DWSchema.DEFAULTS, ...(state.lastPayload || {}) };
          renderStep();
        });
      }
      if (rerun) rerun.textContent = window.DWI18n.t('history_reopen_rerun');
    }
    window.DWToast.info(window.DWI18n.t('history_reopened').replace('{date}', formatHistoryDate(date)));
    return true;
  }

  /* An ISO date in the reader's own calendar and language. Falls back to
     the ISO string itself if the locale is unavailable - a raw date is
     readable, a thrown error is not. */
  function formatHistoryDate(iso) {
    try {
      const locale = LOCALE_FOR_LANG[window.DWI18n.get()] || 'en-US';
      return new Date(`${iso}T00:00:00`).toLocaleDateString(locale, {
        year: 'numeric', month: 'long', day: 'numeric',
      });
    } catch (e) { return iso; }
  }

  /* Asks the server whether today is already recorded, and renders the
     edit tick accordingly. Never throws outward: if this call fails the
     tick simply stays hidden and the server's own 409 is what stops a
     silent overwrite - the guard that matters lives there, not here. */
  async function refreshTodayCheckIn() {
    const row = $('#editTodayRow');
    const check = $('#editTodayCheck');
    const note = $('#editTodayNote');
    if (!row || !check) return;

    let today = null;
    try { today = await window.DWApi.todayCheckIn(); } catch (e) { today = null; }
    state.todayCheckIn = today;

    const exists = !!(today && today.exists);
    row.classList.toggle('hidden', !exists);
    if (!exists) {
      state.editToday = false;
      check.checked = false;
      check.disabled = false;
      return;
    }

    // Never while "just testing" is on: this function runs on every
    // return to the form, and it is what used to re-arm the edit tick
    // behind the user's back after they had chosen to test.
    const testing = !!state.excludeFromAnalysis;
    const locked = !testing && editLockedToday();
    check.checked = locked;
    check.disabled = testing || locked;
    state.editToday = locked;
    if (note) {
      note.textContent = window.DWI18n.t(
        testing ? 'edit_today_note_testing'
          : locked ? 'edit_today_note_locked'
          : 'edit_today_note',
      );
    }
    if (locked) applyTodayAnswers({ quiet: true });
  }

  /* Refills the form with the answers today's recorded check-in was
     built from. Correcting one number should not mean retyping forty,
     and typing them again from memory is how an "edit" ends up
     changing five fields the user never meant to touch. */
  function applyTodayAnswers(options) {
    const today = state.todayCheckIn;
    const inputs = today && today.inputs;
    if (!inputs || !Object.keys(inputs).length) {
      // Days recorded before result snapshots existed have no answers
      // to give back. Said out loud rather than left as a tick that
      // appears to do nothing.
      if (!(options && options.quiet)) window.DWToast.info(window.DWI18n.t('edit_today_no_answers'));
      return;
    }
    state.wizardData = { ...window.DWSchema.DEFAULTS, ...inputs };
    state.demoActive = false;
    // Remembered so that switching to "just testing" can tell an
    // untouched copy of today's answers from answers the user actually
    // typed. Cleared by the first edit - see renderStep's change
    // handler - so nothing the user wrote is ever discarded.
    state.prefilledFromToday = true;
    state.stepIndex = 0;
    renderStep();
    if (!(options && options.quiet)) window.DWToast.success(window.DWI18n.t('edit_today_loaded'));
  }

  /* Everything downstream of a check-in that an UPDATE invalidates.
     Improvements need nothing done here - they come back inside the
     prediction response itself and the result view has already been
     rerendered from it. The weekly plan is the one that can go stale:
     it is frozen for its ISO week on purpose (so a second check-in
     cannot swap tasks out from under the user's checkmarks), and the
     one case where that freeze is wrong is exactly this one - the plan
     was built FROM the day that just changed. A plan set on Monday is
     deliberately left alone when Thursday's numbers are corrected;
     tearing up four days of ticks over a corrected number would be the
     churn the freeze exists to stop. */
  async function refreshDownstreamOfCheckIn() {
    let result = null, payload = null;
    try {
      result = window.DWLastResult.get();
      payload = JSON.parse(localStorage.getItem('dwai_last_payload') || 'null');
    } catch (e) { return; }
    if (!result || !payload) return;

    const body = {
      health_class: result.prediction,
      wellness_score: result.regression_score,
      persona: localStorage.getItem('dwai_last_persona') || null,
      user_data: payload,
    };
    try {
      const current = await window.DWApi.generatePlan(body);
      if (!current || current.generated_on !== todayIso()) return;
      await window.DWApi.generatePlan({ ...body, regenerate: true });
      window.DWToast.info(window.DWI18n.t('toast_plan_rebuilt'));
    } catch (e) {
      // The plan page rebuilds from the server on its next visit
      // anyway, so a failure here costs a toast, not correctness.
    }
  }

  async function startWizard() {
    resetWizard();
    await ensureSchemaLoaded();
    renderStep();
    showView('view-predict');
    // After the view is showing, so a slow round trip never holds the
    // form back - the tick appears a moment later on the days it
    // applies to.
    refreshTodayCheckIn();
    // No automatic greeting here either - same reason as shell.js's
    // page-load path. Tapping the mascot still explains this screen.
  }

  /* Disables a submit button for the duration of an in-flight request -
     without this, a slow connection or an impatient double-click sends
     a second request while the first is still pending, which for
     /auth/register means the second one always (correctly) fails with
     "email already registered" and reads to the user like a random,
     unexplained error right after a successful signup. */
  async function withSubmitLock(btn, fn) {
    if (btn.disabled) return;
    const original = btn.textContent;
    btn.disabled = true;
    try {
      await fn();
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  function wirePasswordToggles(root) {
    $all('[data-password-toggle]', root).forEach((btn) => {
      if (btn.dataset.wired) return;
      btn.dataset.wired = '1';
      btn.addEventListener('click', () => {
        const input = btn.previousElementSibling;
        if (!input) return;
        const showing = input.type === 'text';
        input.type = showing ? 'password' : 'text';
        btn.textContent = showing ? '👁️' : '🙈';
        btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
      });
    });
  }

  /* GitHub sign-in. A full-page navigation, not fetch(): the provider's
     consent screen has to render in the top-level window, and the `state`
     cookie the backend sets must travel with the redirect back. */
  function wireSocialButtons() {
    const btn = $('#githubLoginBtn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      btn.disabled = true;
      if (window.DWSound) window.DWSound.click();
      window.location.href = `${window.DWApi.getBase()}/auth/github/login`;
    });
  }

  /* Completion half of the OAuth round-trip. The backend redirects here
     with either ?oauth_token= or ?oauth_error=. The token is stored the
     same way a password login stores it - one session concept, not two -
     and the query string is scrubbed from history immediately so the
     token is not left sitting in the address bar or a bookmark. */
  function consumeOAuthRedirect() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('oauth_token');
    const error = params.get('oauth_error');
    if (!token && !error) return false;

    const clean = window.location.pathname;
    window.history.replaceState({}, document.title, clean);

    if (error) {
      const messages = {
        state: 'oauth_err_state',
        expired: 'oauth_err_expired',
        exchange: 'oauth_err_exchange',
        unverified_email: 'oauth_err_unverified',
        not_configured: 'oauth_err_not_configured',
        unknown_provider: 'oauth_err_not_configured',
      };
      window.DWToast.error(window.DWI18n.t(messages[error] || 'oauth_err_exchange'));
      return false;
    }

    window.DWApi.setToken(token);
    window.DWToast.success(window.DWI18n.t('oauth_welcome'));
    if (window.DWSound) window.DWSound.ding();
    return true;
  }

  function wireForgotPassword() {
    const openLink = $('#forgotPasswordLink');
    const backLink = $('#backToLoginLink');
    const panel = $('#forgotPasswordPanel');
    const sendBtn = $('#forgotSendBtn');
    const answerBlock = $('#securityAnswerBlock');
    const questionLabel = $('#securityQuestionLabel');
    const answerInput = $('#securityAnswerInput');
    const answerBtn = $('#securityAnswerSubmitBtn');

    if (!openLink || !panel) return;

    openLink.addEventListener('click', (e) => {
      e.preventDefault();
      $('#loginForm').classList.add('hidden');
      $('#registerForm').classList.add('hidden');
      panel.classList.remove('hidden');
      if (answerBlock) answerBlock.classList.add('hidden');
      if (answerInput) answerInput.value = '';
    });
    backLink.addEventListener('click', (e) => {
      e.preventDefault();
      panel.classList.add('hidden');
      $('#loginForm').classList.remove('hidden');
    });

    sendBtn.addEventListener('click', () => withSubmitLock(sendBtn, async () => {
      const email = $('#forgotEmailInput').value.trim();
      if (!email) return;

      /* One door: the question the account owner set at sign-up.
         The emailed reset code used to be offered first, and with no
         SMTP configured it went to a server log the user cannot read -
         an offer of help that helped nobody. This screen no longer
         touches /auth/forgot-password or /auth/reset-password.

         An address with no question set still gets the same message and
         the same silence about whether it is registered, so this panel
         cannot be used to find out which addresses have accounts. */
      try {
        const q = await window.DWApi.securityQuestion(email);
        if (q && q.question && questionLabel) {
          // textContent: the question is text the account owner wrote,
          // and it is about to be shown to whoever typed the address.
          questionLabel.textContent = q.question;
          answerBlock.classList.remove('hidden');
          if (answerInput) answerInput.focus();
        } else {
          answerBlock.classList.add('hidden');
          window.DWToast.info(window.DWI18n.t('auth_reset_no_question'));
        }
      } catch (err) {
        answerBlock.classList.add('hidden');
        window.DWToast.info(window.DWI18n.t('auth_reset_no_question'));
      }
    }));

    if (answerBtn) {
      answerBtn.addEventListener('click', () => withSubmitLock(answerBtn, async () => {
        const email = $('#forgotEmailInput').value.trim();
        const answer = answerInput ? answerInput.value : '';
        const newPassword = $('#securityNewPasswordInput').value;
        if (!email || !answer || !newPassword) {
          window.DWToast.info(window.DWI18n.t('auth_answer_need_both'));
          return;
        }
        try {
          const res = await window.DWApi.resetPasswordWithAnswer(email, answer, newPassword);
          window.DWApi.setSession(res);
          window.DWToast.success(window.DWI18n.t('auth_reset_done'));
          panel.classList.add('hidden');
          await afterLogin();
        } catch (err) {
          window.DWToast.error(err.message);
        }
      }));
    }

  }

  function wireAuthForms() {
    initAuthTabs();
    wirePasswordToggles(document);
    wireSocialButtons();
    wireForgotPassword();

    $('#loginForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const btn = form.querySelector('button[type="submit"]');
      clearFieldErrors(form);
      const fd = new FormData(form);
      await withSubmitLock(btn, async () => {
        try {
          const res = await window.DWApi.login(fd.get('email'), fd.get('password'));
          window.DWApi.setSession(res);
          window.DWToast.success(window.DWI18n.t('toast_login_ok'));
          await afterLogin();
        } catch (err) {
          /* A failed sign-in used to report the same sentence whatever
             went wrong, which is how a user ends up concluding their
             account does not exist and registering a second one. The
             three causes need three different actions, so they get
             three different messages:

               - the address is not answering, or is not this API at
                 all (status 0, or the not-the-api detector). Nothing
                 to do with the account; re-registering will not help
                 and cannot work either.
               - too many failed attempts (429). Waiting is the fix.
               - the credentials were genuinely rejected (401).

             The address is named in the first case on purpose: two
             copies of the app on different ports is a real thing that
             happens here (run.py picks the next free port when 8000 is
             busy), and it is invisible until something says which one
             you are talking to. */
          let message;
          if (err.fieldErrors) {
            message = window.DWI18n.t('toast_field_error');
          } else if (err.status === 0 || err.status === 501 || err.status === 405) {
            message = err.message || window.DWI18n.t('toast_login_fail');
          } else if (err.status === 429) {
            message = err.message || window.DWI18n.t('toast_login_fail');
          } else if (err.status === 401) {
            message = window.DWI18n.t('toast_login_rejected')
              .replace('{address}', window.DWApi.getBase());
          } else {
            message = err.message || window.DWI18n.t('toast_login_fail');
          }
          window.DWToast.error(message);
          window.DWMascot.react('error');
        }
      });
    });

    $('#registerForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const btn = form.querySelector('button[type="submit"]');
      clearFieldErrors(form);
      if (!$('#termsCheck').checked) {
        window.DWToast.warning(window.DWI18n.t('toast_terms_required'));
        return;
      }
      const fd = new FormData(form);
      await withSubmitLock(btn, async () => {
        try {
          const res = await window.DWApi.register(
            fd.get('email'), fd.get('password'), fd.get('display_name'),
            // The recovery question. Sent from here rather than offered
            // later because the moment somebody needs it is the moment
            // they cannot sign in to set it - and with no mail server
            // configured, the emailed reset code goes to a log the user
            // has no way to read.
            fd.get('security_question'), fd.get('security_answer'),
          );
          window.DWApi.setSession(res);
          window.DWToast.success(window.DWI18n.t('toast_register_ok'));
          // Marked BEFORE afterLogin(), which is what renders the
          // onboarding slides - the flag is what tells them to run the
          // tour first, and setting it afterwards would be too late.
          try { localStorage.setItem(FIRST_RUN_KEY, '1'); } catch (e) {}
          await afterLogin();
        } catch (err) {
          if (err.fieldErrors) {
            Object.entries(err.fieldErrors).forEach(([k, v]) => markFieldError(form, k, v));
          }
          window.DWToast.error(err.message || window.DWI18n.t('toast_register_fail'));
          window.DWMascot.react('error');
        }
      });
    });
  }

  // ===================== ONBOARDING =====================
  /* The tour runs itself once, on the very first screen after signing
     up, and then the slides start. Everywhere else in this app the
     guide is deliberately silent until it is asked (see shell.js) -
     this is the one exception, and it is the moment it earns: a brand
     new account is looking at a screen with no explanation of what any
     of it is for.
     Consumed as it fires, so it happens exactly once even if the page
     is reloaded mid-onboarding. */
  const FIRST_RUN_KEY = 'dwai_first_run_tour';

  function maybeRunFirstRunTour() {
    let pending = false;
    try {
      pending = localStorage.getItem(FIRST_RUN_KEY) === '1';
      if (pending) localStorage.removeItem(FIRST_RUN_KEY);
    } catch (e) { return; }
    if (!pending || !window.DWGuide) return;
    // A beat after the view is up, so the first bubble does not land on
    // a screen still animating in. The tour carries its own visible
    // "skip" for as long as it runs - it arrives uninvited, so leaving
    // it has to be one click and not a keyboard shortcut nobody was
    // told about.
    setTimeout(() => {
      try { window.DWGuide.startTour('welcome', { force: true }); } catch (e) {}
    }, 900);
  }

  function buildOptionList(container, options, stateKey) {
    container.innerHTML = '';
    Object.entries(options).forEach(([label, value]) => {
      const el = document.createElement('div');
      el.className = 'onboard-option';
      // The English key is what identifies the option; `value` is what
      // gets submitted. Only the text the user reads is translated -
      // these lists were English in all four languages.
      el.dataset.optionValue = value;
      el.textContent = window.DWOnboardingOptions.labelFor(value, label);
      el.addEventListener('click', () => {
        $all('.onboard-option', container).forEach((o) => o.classList.remove('selected'));
        el.classList.add('selected');
        state.onboard[stateKey] = value;
      });
      container.appendChild(el);
    });
  }

  function renderOnboarding() {
    state.onboardSlide = 0;
    const goal = localStorage.getItem('dwai_intake_goal');
    buildOptionList($('#goalOptions'), GOAL_OPTIONS, 'goal');
    buildOptionList($('#purposeOptions'), PURPOSE_OPTIONS, 'purpose');
    buildOptionList($('#scheduleOptions'), SCHEDULE_OPTIONS, 'schedule');
    buildOptionList($('#effortOptions'), EFFORT_OPTIONS, 'effort');
    buildOptionList($('#workScreenOptions'), WORK_SCREEN_OPTIONS, 'workScreen');
    if (goal) {
      const match = Object.values(GOAL_OPTIONS).includes(goal) ? goal : null;
      if (match) {
        state.onboard.goal = match;
        $all('.onboard-option', $('#goalOptions')).forEach((o) => {
          if (o.dataset.optionValue === match) o.classList.add('selected');
        });
      }
    }
    renderOnboardSlide();
  }

  /* Onboarding is one question per slide.
     Three questions stacked on a single screen read as a form to get
     through, and the note under the schedule question - the answer that
     actually changes which signals are treated as problems - never got
     read. One at a time is also why the schedule slide can afford to
     explain itself.
     The all-at-once version still exists on the profile page, which is
     where these answers are edited later. */
  const ONBOARD_SLIDES = 6;

  /* Fill the hour/minute selects and keep the hidden "HH:MM" input in
     step with them. See the comment beside the markup for why this is
     not <input type="time">: on a Persian Windows browser that control
     would not accept a new value, so the sleep window everyone is asked
     for could not actually be answered. */
  function wireTimeSelects(prefix, defaultValue) {
    const hourSel = $(`#${prefix}Hour`);
    const minSel = $(`#${prefix}Minute`);
    const hidden = $(`#${prefix}Time`);
    if (!hourSel || !minSel || !hidden) return;

    const [defHour, defMin] = String(defaultValue).split(':');

    for (let h = 0; h < 24; h++) {
      const label = String(h).padStart(2, '0');
      const opt = document.createElement('option');
      opt.value = label;
      opt.textContent = label;
      if (label === defHour) opt.selected = true;
      hourSel.appendChild(opt);
    }
    // Quarter hours. Asking anyone to pick "usually asleep by 23:07"
    // invents a precision the answer does not have.
    ['00', '15', '30', '45'].forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      if (m === defMin) opt.selected = true;
      minSel.appendChild(opt);
    });

    const sync = () => { hidden.value = `${hourSel.value}:${minSel.value}`; };
    hourSel.addEventListener('change', sync);
    minSel.addEventListener('change', sync);
    sync();
  }

  function renderOnboardSlide() {
    $all('[data-onboard-slide]').forEach((el) => {
      el.classList.toggle('hidden', Number(el.dataset.onboardSlide) !== state.onboardSlide);
    });

    const progress = $('#onboardProgress');
    if (progress) {
      progress.innerHTML = '';
      for (let i = 0; i < ONBOARD_SLIDES; i++) {
        const dot = document.createElement('span');
        dot.className = 'onboard-dot' + (i === state.onboardSlide ? ' active' : '')
          + (i < state.onboardSlide ? ' done' : '');
        progress.appendChild(dot);
      }
    }

    const last = state.onboardSlide === ONBOARD_SLIDES - 1;
    $('#onboardBack').classList.toggle('hidden', state.onboardSlide === 0);
    $('#onboardNext').classList.toggle('hidden', last);
    $('#onboardSave').classList.toggle('hidden', !last);
    // "Skip for now" only while there is still something to skip; on
    // the last slide the primary action already covers leaving.
    $('#onboardSkip').classList.toggle('hidden', last);

    if (window.DWGuide) {
      const current = document.querySelector(
        `[data-onboard-slide="${state.onboardSlide}"]`
      );
      if (current) window.DWGuide.autoAttach(current);
    }
  }

  function wireOnboarding() {
    wireTimeSelects('onboardSleep', '23:00');
    wireTimeSelects('onboardWake', '07:00');

    $('#onboardSkip').addEventListener('click', async () => {
      await startWizard();
      // Skipping the questions is still leaving them, and somebody who
      // skipped has MORE reason to be shown around, not less.
      maybeRunFirstRunTour();
    });
    $('#onboardNext').addEventListener('click', () => {
      if (state.onboardSlide < ONBOARD_SLIDES - 1) {
        state.onboardSlide += 1;
        renderOnboardSlide();
      }
    });
    $('#onboardBack').addEventListener('click', () => {
      if (state.onboardSlide > 0) {
        state.onboardSlide -= 1;
        renderOnboardSlide();
      }
    });
    $('#onboardSave').addEventListener('click', async () => {
      try {
        /* Every one of these is now the user's own answer. Four of the
           seven used to be hard-coded here - the app submitted
           "moderate", 23:00, 07:00 and "no" on everybody's behalf, and
           then read none of them back, which made half this screen a
           questionnaire with no reader. Each one changes the weekly
           plan now; the fallbacks below are only for a slide somebody
           skipped past without choosing. */
        const sleepAt = $('#onboardSleepTime');
        const wakeAt = $('#onboardWakeTime');
        await window.DWApi.saveOnboarding({
          primary_goal: state.onboard.goal || 'maintain_habits',
          main_use_purpose: state.onboard.purpose || 'mixed',
          schedule_type: state.onboard.schedule || 'standard_day',
          usual_sleep_time: (sleepAt && sleepAt.value) || '23:00',
          usual_wake_time: (wakeAt && wakeAt.value) || '07:00',
          preferred_effort: state.onboard.effort || 'moderate',
          work_screen_required: state.onboard.workScreen === 'yes',
        });
        window.DWToast.success(window.DWI18n.t('toast_saved'));
      } catch (err) {
        window.DWToast.error(err.message);
      }
      await startWizard();
      maybeRunFirstRunTour();
    });
  }

  // ===================== WIZARD =====================
  async function ensureSchemaLoaded() {
    if (Object.keys(state.featureSchemaMap).length) return;
    const list = await window.DWApi.featureSchema();
    list.forEach((f) => { state.featureSchemaMap[f.name] = f; });
  }
  async function ensureDemoProfiles() {
    if (state.demoProfiles) return;
    state.demoProfiles = await window.DWApi.demoProfiles();
  }

  function fieldDef(name) {
    return window.DWSchema.HELPER_ONLY_FIELDS[name] ||
      (state.featureSchemaMap[name] && {
        label: state.featureSchemaMap[name].label,
        dtype: state.featureSchemaMap[name].dtype,
        minimum: state.featureSchemaMap[name].minimum,
        maximum: state.featureSchemaMap[name].maximum,
        choices: state.featureSchemaMap[name].choices,
        default: window.DWSchema.DEFAULTS[name],
      });
  }

  function buildFieldEl(name) {
    const def = fieldDef(name);
    if (!def) return null;
    const wrap = document.createElement('div');
    wrap.className = 'field';
    wrap.id = `fieldwrap-${name}`;
    const label = document.createElement('label');
    // Through labelFor(), not def.label. `def.label` is the raw English
    // `label=` string from core/feature_schema.py, so the whole check-in
    // form - "Age", "Gender", forty more - stayed in English no matter
    // which language the rest of the app was in. `data-dw-field` lets
    // the language switch below re-label them without rebuilding the
    // form and losing what the user has typed.
    label.dataset.dwField = name;
    label.textContent = labelFor(name) || def.label || name;
    wrap.appendChild(label);

    const currentVal = state.wizardData[name] !== undefined ? state.wizardData[name] : def.default;

    if (def.dtype === 'bool') {
      const row = document.createElement('div');
      row.className = 'checkbox-row';
      const input = document.createElement('input');
      input.type = 'checkbox'; input.className = 'input'; input.id = `field-${name}`; input.name = name;
      input.checked = !!currentVal;
      input.addEventListener('change', () => onFieldChange(name, input.checked));
      row.appendChild(input);
      wrap.appendChild(row);
    } else if (def.choices && def.choices.length) {
      const select = document.createElement('select');
      select.className = 'input'; select.id = `field-${name}`; select.name = name;
      // The option's VALUE stays the exact schema string - that is what
      // gets validated against FEATURE_SCHEMA and sent to the model.
      // Only the text is translated. These dropdowns previously showed
      // raw English in all four languages.
      def.choices.forEach((c) => {
        const opt = document.createElement('option');
        opt.value = String(c);
        opt.textContent = window.DWOnboardingOptions
          ? window.DWOnboardingOptions.labelFor(c, String(c))
          : String(c);
        if (String(c) === String(currentVal)) opt.selected = true;
        select.appendChild(opt);
      });
      select.addEventListener('change', () => onFieldChange(name, select.value));
      wrap.appendChild(select);
    } else if (window.DWSchema.SLIDER_FIELDS.has(name)) {
      const row = document.createElement('div');
      row.className = 'range-row';
      const input = document.createElement('input');
      input.type = 'range'; input.id = `field-${name}`; input.name = name;
      input.min = def.minimum ?? 0; input.max = def.maximum ?? 100; input.step = 0.5;
      input.value = currentVal ?? def.minimum ?? 0;
      const valueBox = document.createElement('span');
      valueBox.className = 'range-value mono'; valueBox.textContent = input.value;
      input.addEventListener('input', () => { valueBox.textContent = input.value; onFieldChange(name, parseFloat(input.value)); });
      row.appendChild(input); row.appendChild(valueBox);
      wrap.appendChild(row);
    } else {
      const input = document.createElement('input');
      input.type = 'number'; input.className = 'input'; input.id = `field-${name}`; input.name = name;
      if (def.minimum !== undefined && def.minimum !== null) input.min = def.minimum;
      if (def.maximum !== undefined && def.maximum !== null) input.max = def.maximum;
      input.step = def.dtype === 'int' ? 1 : 0.5;
      input.value = currentVal ?? def.minimum ?? 0;
      input.addEventListener('input', () => onFieldChange(name, input.value === '' ? '' : parseFloat(input.value)));
      wrap.appendChild(input);
    }

    const err = document.createElement('div');
    err.className = 'err';
    wrap.appendChild(err);
    return wrap;
  }

  function onFieldChange(name, value) {
    state.wizardData[name] = value;
    state.demoActive = false;
    // The prefill stops being a prefill the moment it is edited. From
    // here on these are the user's own answers and switching to "just
    // testing" must not clear them - see syncCheckInMode.
    state.prefilledFromToday = false;
    updateDerivedPanel();
  }

  function updateDerivedPanel() {
    // Demo fixtures already carry their own exact, backend-generated
    // derived values - only recompute for a manual (non-demo) entry, so
    // loading a demo profile never silently drifts it from the real
    // config/demo_profiles.py output (see schema.js's applyCalendarDefaults
    // docstring for the day_index/is_weekend half of this same rule).
    const derived = state.demoActive
      ? state.wizardData
      : window.DWSchema.applyCalendarDefaults(window.DWSchema.deriveFeatures(state.wizardData));
    if (!state.demoActive) Object.assign(state.wizardData, derived);
    const panel = $('#derivedPanel');
    const title = panel.querySelector('p');
    panel.innerHTML = '';
    if (title) panel.appendChild(title);
    const items = [
      ['total_screen_min', 'Total screen (min)'],
      ['screen_vs_baseline_pct', 'Vs. baseline (%)'],
      ['fragmentation_index_0_100', 'Fragmentation'],
      ['digital_dependence_0_100', 'Dependence'],
      ['notification_density', 'Notif density'],
    ];
    items.forEach(([key, label]) => {
      const div = document.createElement('div');
      div.className = 'derived-item';
      const v = derived[key];
      div.innerHTML = `<div class="val">${typeof v === 'number' ? Math.round(v * 100) / 100 : v}</div><div class="lbl">${label}</div>`;
      panel.appendChild(div);
    });
  }

  function renderProgress() {
    const wrap = $('#wizardProgress');
    wrap.innerHTML = '';
    activeSteps().forEach((s, i) => {
      const dot = document.createElement('div');
      dot.className = 'dot' + (i < state.stepIndex ? ' done' : i === state.stepIndex ? ' active' : '');
      wrap.appendChild(dot);
    });
  }

  function renderStep() {
    renderProgress();
    const step = activeSteps()[state.stepIndex];
    $('#wizardStepTitle').textContent = window.DWI18n.t(step.titleKey);
    const fieldsWrap = $('#wizardFields');
    fieldsWrap.innerHTML = '';
    fieldsWrap.classList.remove('step-in'); void fieldsWrap.offsetWidth; fieldsWrap.classList.add('step-in');
    step.fields.forEach((name) => {
      const el = buildFieldEl(name);
      if (el) fieldsWrap.appendChild(el);
    });
    updateDerivedPanel();

    $('#wizardBack').disabled = state.stepIndex === 0;
    const isLast = state.stepIndex === activeSteps().length - 1;
    $('#wizardNext').textContent = isLast ? window.DWI18n.t('predict_submit') : window.DWI18n.t('predict_next');

    // The guide explains each wizard step the first time it's reached,
    // so a first-time user is told what a screen is asking for and why
    // it matters rather than facing a bare form.
    if (window.DWGuide) {
      // autoAttach only: each field group explains itself when tapped.
      // This used to also fire explain('wizard_<step>') on a timer, so
      // the guide popped up again on EVERY step of the wizard - six
      // bubbles to fill in one form.
      window.DWGuide.autoAttach(fieldsWrap);
    }
  }

  function resetWizard() {
    state.wizardData = { ...window.DWSchema.DEFAULTS };
    state.stepIndex = 0;
    state.demoActive = false;
    state.excludeFromAnalysis = false;
    const cb = $('#excludeFromAnalysisCheck');
    if (cb) cb.checked = false;
    // Re-derived a moment later by refreshTodayCheckIn() from what the
    // SERVER says about today - never carried over from the last visit,
    // which is how a stale tick would turn a fresh check-in into an
    // "update" of a day it knows nothing about.
    state.editToday = false;
    state.prefilledFromToday = false;
    state.todayCheckIn = null;
    const editRow = $('#editTodayRow');
    if (editRow) editRow.classList.add('hidden');
    const editCb = $('#editTodayCheck');
    if (editCb) { editCb.checked = false; editCb.disabled = false; }
  }

  function findStepForField(name) {
    return activeSteps().findIndex((s) => s.fields.includes(name));
  }

  /* Everything Section E's games might need, gathered from the same
     endpoints the rest of the app already calls - nothing here invents a
     data source. Each fetch is independently try/caught so one endpoint
     being unavailable only removes the games that depended on it (G4),
     never the check-in flow itself. */
  async function buildGamesContext(result) {
    const context = {
      score: result.regression_score,
      shapFeatures: result.shap_features || [],
      dimensions: (result.dimension_breakdown && result.dimension_breakdown.dimensions) || [],
      confidenceLevel: result.confidence_label && result.confidence_label.level,
      confidencePercent: result.confidence_percent,
      futureClass: result.prediction,
    };

    try {
      const history = await window.DWApi.history(1, 50);
      const entries = history.items || [];
      context.entryCount = entries.length;
      // Skips today: a day is easier to judge as an exception once it is
      // actually over, not the moment it was logged.
      const today = new Date().toISOString().slice(0, 10);
      context.unlabelledDay = entries.find(
        (e) => e.date && e.date !== today && !e.excluded && e.health_score != null
      ) || null;
      context.pastScores = entries
        .filter((e) => !e.excluded && e.health_score != null)
        .map((e) => e.health_score);
    } catch (e) { /* no history - those games simply will not appear */ }

    try {
      const cards = await window.DWApi.insightCards();
      context.correlation = (cards && cards.correlation) || null;
    } catch (e) { /* no insight cards - that game simply will not appear */ }

    try {
      const progress = await window.DWApi.progressSummary();
      // The endpoint returns these flat, not nested. grace_days_remaining
      // is not exposed there, and the game handles its absence by simply
      // omitting that sentence rather than guessing a number.
      context.streak = progress ? { current_streak: progress.current_streak } : null;
    } catch (e) { /* no streak data - that game simply will not appear */ }

    try {
      const analytics = await window.DWApi.analyticsSummary();
      context.weekdayVsWeekend = (analytics && analytics.weekday_vs_weekend) || null;
    } catch (e) { /* not enough history for this yet - that game simply will not appear */ }

    try {
      const badgesResp = await window.DWApi.badges();
      // Never a private awareness indicator (G1 - those are not a
      // competition), and only ones this user's own history can actually
      // answer.
      context.lockedBadges = ((badgesResp && badgesResp.badges) || []).filter(
        (b) => !b.earned && b.evaluable && !b.private && b.category === 'achievement'
      );
    } catch (e) { /* no badge data - that game simply will not appear */ }

    return context;
  }

  async function submitPrediction() {
    // A real, recorded check-in never asks which day it is - it always
    // uses today's actual weekday, since that's the day it genuinely
    // happened on. Only a hypothetical entry the user has explicitly
    // excluded from weekly analysis keeps the day they picked in the
    // (now-shown) time step.
    if (!state.demoActive && !state.excludeFromAnalysis) {
      state.wizardData.day_of_week = window.DWSchema.todaysWeekday();
    }
    const payload = state.demoActive
      ? { ...state.wizardData }
      : window.DWSchema.applyCalendarDefaults(window.DWSchema.deriveFeatures(state.wizardData));
    state.lastPayload = payload;

    try {
      // The processing screen waits on the REAL request - it never
      // fabricates delay beyond its minimum presentation window.
      const result = await window.DWProcessing.run(
        window.DWApi.predict(payload, !state.excludeFromAnalysis, state.editToday), { flow: 'predict' }
      );
      /* Only a day the server actually RECORDED becomes "your latest
         result". The "I'm only testing this" tick posts persist:false,
         and this used to cache it anyway - so a throwaway 53.06 stood
         in for a real, recorded 87.67 everywhere afterwards: the Coach
         answered about it, the dashboard showed it, the weekly plan and
         the simulator started from it. DWLastResult.set() refuses a
         non-persisted result outright; the payload is held to the same
         rule here, because everything that reads one reads the other
         and a mismatched pair is its own bug. */
      if (result.persisted !== false) {
        window.DWLastResult.set(result);
        localStorage.setItem('dwai_last_payload', JSON.stringify(payload));
      }
      if (state.excludeFromAnalysis) {
        window.DWToast.info(window.DWI18n.t('toast_not_recorded'));
      } else if (result.replaced_existing) {
        // Say "updated", not "saved". The user replaced a real recorded
        // result, and everything built on top of that day - the weekly
        // plan and the improvements - has to be rebuilt from the new
        // answers or it keeps describing a day that no longer exists.
        window.DWToast.success(window.DWI18n.t('toast_checkin_updated'));
        lockEditForToday();
        refreshDownstreamOfCheckIn();
      }

      // Section E. The prediction is already in hand at this point - the
      // request is never delayed for a game. Only the moment the RESULT
      // VIEW appears moves, and only when there is a real 'pre' game to
      // show: off in Settings or nothing eligible (G4) skips straight to
      // the result, exactly as before.
      //
      // Games are split by phase (see games.js). 'pre' games commit to a
      // guess about a number - the score, the confidence - before that
      // number exists anywhere on screen, so they run in the gap between
      // processing and the result view. 'post' games read secondary
      // context (SHAP factors, streak, badges) that does not spoil
      // anything and is written assuming the result is already visible,
      // so they render further down the result page itself, once it is
      // showing. Both phases share one context object, built once.
      let gamesContext = null;
      if (window.DWGames && window.DWGames.isEnabled()) {
        try { gamesContext = await buildGamesContext(result); } catch (e) { gamesContext = null; }
      }

      const showResult = () => {
        // Show the view BEFORE rendering: the wave bars size themselves
        // from getBoundingClientRect(), which is 0x0 while the section is
        // still display:none (that left the confidence bar blank).
        showView('view-result');
        renderResult(result);
        wirePersonaLine(payload);
        // "That day sits outside your week's range." Asked after the
        // result is on screen, never before: the question quotes the
        // day's own score back, and asking about a number the user has
        // not been shown yet is asking them to judge something they
        // cannot see. The module returns without rendering on an
        // ordinary day - the server decides, not this page.
        if (window.DWBandDecision) {
          window.DWBandDecision.maybeAsk($('#bandDecisionMount'));
        }
        if (gamesContext) {
          try {
            window.DWGames.render($('#gamesAfterMount'), gamesContext, { limit: 2, phase: 'post' });
          } catch (e) { /* the result itself already rendered - a game failing here is not fatal */ }
        }
      };

      let preGamesShown = 0;
      if (gamesContext) {
        try {
          preGamesShown = window.DWGames.render($('#gamesPageMount'), gamesContext, { limit: 2, phase: 'pre' });
        } catch (e) { preGamesShown = 0; }
      }
      if (preGamesShown > 0) {
        showView('view-games');
        const continueBtn = $('#gamesContinueBtn');
        // G2: this button is the only way off this view besides the
        // per-card dismiss (×) - nothing here can lock the page.
        if (continueBtn) continueBtn.onclick = showResult;
      } else {
        showResult();
      }
    } catch (err) {
      if (err.code === 'already_checked_in_today') {
        // Not a failure the user caused by entering something wrong -
        // the day is simply already recorded. Point at the control that
        // resolves it and show it, rather than reporting a bare 409.
        window.DWToast.error(window.DWI18n.t('toast_already_checked_in'));
        refreshTodayCheckIn().then(() => {
          const row = $('#editTodayRow');
          if (row) {
            row.classList.remove('hidden');
            row.classList.add('edit-today-row--flash');
            row.scrollIntoView({ block: 'center', behavior: 'smooth' });
            setTimeout(() => row.classList.remove('edit-today-row--flash'), 1600);
          }
        });
        window.DWMascot.react('thinking');
      } else if (err.fieldErrors) {
        const firstField = Object.keys(err.fieldErrors)[0];
        const stepI = findStepForField(firstField);
        if (stepI >= 0) { state.stepIndex = stepI; renderStep(); }
        Object.entries(err.fieldErrors).forEach(([k, v]) => {
          const wrap = document.getElementById(`fieldwrap-${k}`);
          if (wrap) { wrap.classList.add('has-error'); wrap.querySelector('.err').textContent = v; }
        });
        window.DWToast.error(window.DWI18n.t('toast_field_error'));
      } else {
        window.DWToast.error(err.message || window.DWI18n.t('toast_predict_fail'));
      }
      window.DWMascot.react('confused');
    }
  }

  function wirePersonaLine(payload) {
    window.DWApi.personaAssign(payload).then((p) => {
      if (p && p.available) {
        $('#personaLine').textContent = `${window.DWI18n.t('result_persona')}: ${p.persona_name}`;
        localStorage.setItem('dwai_last_persona', p.persona_name);
      }
    }).catch(() => {});
  }

  /* The two ticks are opposites and must never both be on.

     "Edit today's check-in" means REPLACE the day already recorded.
     "Don't record this - just testing" means record nothing at all.
     They were independent checkboxes, and because the edit tick is
     auto-ticked whenever today already exists, the ordinary path was:
     check in, come back, tick "just testing", submit - and the test run
     went out with edit_today still true and OVERWROTE the real day. The
     user's actual score for the day was replaced by a hypothetical they
     were only trying out, silently, with no way back.

     So ticking either one clears the other, here, in one function both
     handlers call - not in two handlers that have to agree. */
  function syncCheckInMode(source) {
    const excludeCheck = $('#excludeFromAnalysisCheck');
    const editCheck = $('#editTodayCheck');

    if (source === 'exclude' && state.excludeFromAnalysis && state.editToday) {
      state.editToday = false;
      if (editCheck) editCheck.checked = false;
    }

    /* And the form goes back to blank.
       This is the other half of the same bug. The edit tick auto-fills
       the form with today's recorded answers, so a user who then ticked
       "just testing" and pressed through got the SAME score back and
       reasonably concluded the test had been counted as their real day.
       It had not - but a test that silently starts as a copy of today
       cannot tell you anything you did not already know.
       Only an UNTOUCHED prefill is cleared: once a field has been
       edited, the answers are the user's own and are left alone. */
    if (source === 'exclude' && state.excludeFromAnalysis && state.prefilledFromToday) {
      state.wizardData = { ...window.DWSchema.DEFAULTS };
      state.prefilledFromToday = false;
      window.DWToast.info(window.DWI18n.t('test_mode_form_reset'));
    }
    if (source === 'edit' && state.editToday && state.excludeFromAnalysis) {
      state.excludeFromAnalysis = false;
      if (excludeCheck) excludeCheck.checked = false;
    }

    /* The edit tick is force-ticked and disabled once today is recorded
       (see editLockedToday), which is what made this dangerous: the user
       could not untick it themselves. While "just testing" is on, that
       lock is released - a test run is not an edit of anything, so the
       tick is cleared, disabled and greyed rather than left asserting
       something untrue. */
    if (editCheck) {
      const testing = !!state.excludeFromAnalysis;
      editCheck.disabled = testing || (!testing && editLockedToday());
      if (testing) editCheck.checked = false;
      const row = $('#editTodayRow');
      if (row) row.classList.toggle('is-superseded', testing);
    }

    const note = $('#editTodayNote');
    if (note) {
      note.textContent = window.DWI18n.t(
        state.excludeFromAnalysis ? 'edit_today_note_testing'
          : editLockedToday() ? 'edit_today_note_locked'
          : 'edit_today_note',
      );
    }
  }

  function wireWizard() {
    const excludeCheck = $('#excludeFromAnalysisCheck');
    if (excludeCheck) {
      excludeCheck.addEventListener('change', (e) => {
        state.excludeFromAnalysis = e.target.checked;
        syncCheckInMode('exclude');
        state.stepIndex = 0;
        renderStep();
      });
    }
    const editCheck = $('#editTodayCheck');
    if (editCheck) {
      editCheck.addEventListener('change', (e) => {
        state.editToday = e.target.checked;
        syncCheckInMode('edit');
        // Ticking it is what makes the form an edit rather than a
        // retype, so it fills in what was actually submitted today.
        // Unticking does NOT wipe the form - the user may have already
        // corrected a field, and throwing that away as a side effect of
        // a checkbox would be its own small data loss.
        if (e.target.checked) applyTodayAnswers();
      });
    }

    const wizardNextBtn = $('#wizardNext');
    wizardNextBtn.addEventListener('click', () => {
      const isLast = state.stepIndex === activeSteps().length - 1;
      // Same guard auth forms already use (see withSubmitLock above) -
      // without it, a slow connection or an impatient double-click fires
      // submitPrediction() twice. Each call creates its OWN processing
      // overlay (DWProcessing.run() appends a fresh element rather than
      // reusing one), so a second call leaves a second overlay stacked
      // on top of the page - one that keeps blocking every click for its
      // own full presentation window even after the first call has
      // already shown the games/result view underneath it.
      if (isLast) { withSubmitLock(wizardNextBtn, submitPrediction); return; }
      state.stepIndex++;
      renderStep();
    });
    $('#wizardBack').addEventListener('click', () => {
      if (state.stepIndex > 0) { state.stepIndex--; renderStep(); }
    });

    $all('[data-demo]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        await Promise.all([ensureSchemaLoaded(), ensureDemoProfiles()]);
        const keyMap = {
          healthy: 'Healthy - balanced digital habits',
          borderline: 'Borderline - mixed signals',
          at_risk: 'At Risk - heavy, late-night use',
          baseline: 'Baseline - neutral midpoint values',
        };
        const label = keyMap[btn.dataset.demo];
        const profile = state.demoProfiles[label];
        if (!profile) return;
        state.wizardData = { ...profile };
        state.demoActive = true;
        state.stepIndex = 0;
        renderStep();
        window.DWToast.info(`Loaded "${label}" demo profile.`);
      });
    });

    $('#runAgainBtn').addEventListener('click', () => startWizard());
  }

  // ===================== CSV BULK IMPORT =====================

  /* Reads just enough of the file, in the browser, to be able to ASK a
     sensible question before anything is sent: how many rows, which
     days, and how many of those days the user has already logged.
     Nothing here validates the file - the server does that - so a
     malformed file simply yields no dates and the chooser says so. */
  function readCsvFileFacts(file) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onerror = () => resolve({ rows: 0, dates: [], firstRow: {}, firstDate: null });
      reader.onload = () => {
        const lines = String(reader.result || '')
          .replace(/^﻿/, '')
          .split(/\r?\n/)
          .filter((l) => l.trim().length);
        if (lines.length < 2) { resolve({ rows: 0, dates: [], firstRow: {}, firstDate: null }); return; }
        const split = (window.DWCsvLibrary && window.DWCsvLibrary.splitCsvLine)
          || ((line) => line.split(','));
        const header = split(lines[0]).map((h) => h.trim().toLowerCase());
        const dateAt = header.indexOf('date');
        const dates = [];
        for (let i = 1; i < lines.length; i += 1) {
          if (dateAt < 0) break;
          const cell = (split(lines[i])[dateAt] || '').trim();
          if (/^\d{4}-\d{2}-\d{2}$/.test(cell)) dates.push(cell);
        }
        /* The first data row as a {field: value} object, for the
           "fill the questionnaire" option. Only the first: that choice
           loads ONE day into a form that holds one day, and quietly
           picking a row out of twelve would be a guess. The chooser
           says which one it took. */
        const firstRow = {};
        if (lines.length > 1) {
          const cells = split(lines[1]);
          header.forEach((name, index) => {
            if (!name || name === 'date') return;
            const raw = (cells[index] || '').trim();
            if (raw === '') return;
            const asNumber = Number(raw);
            firstRow[name] = (raw !== '' && Number.isFinite(asNumber)) ? asNumber : raw;
          });
        }
        resolve({ rows: lines.length - 1, dates, firstRow, firstDate: dates[0] || null });
      };
      reader.readAsText(file);
    });
  }

  /* The days this account has already recorded, as a Set. Best effort:
     if the call fails the chooser still opens, it just cannot say how
     many days would be replaced - and the server still refuses to
     overwrite anything the user did not agree to. */
  async function recordedDates() {
    try {
      const history = await window.DWApi.history(1, 200);
      return new Set((history.items || []).map((e) => e.date).filter(Boolean));
    } catch (e) {
      return null;
    }
  }

  /* The question the upload used to skip.

     What it replaces: every upload was a save attempt, so a file
     covering a day already logged came back as an error telling the
     user to switch on "edit today's check-in" - the very tick that
     overwrites the day they were trying to look at. Someone who only
     wanted to SEE what a file scores had no way to say so, and someone
     who did want to replace a day had to find a checkbox on another
     part of the page first. Now the app asks, and sets the flags
     itself. */
  async function askCsvIntent(facts, existing) {
    const t = (k) => window.DWI18n.t(k);
    const esc = window.DWSheet.esc;
    const clashes = existing
      ? facts.dates.filter((d) => existing.has(d))
      : [];

    const factList = [
      `<li>${esc(t('csv_choice_fact_rows').replace('{count}', facts.rows || '?'))}</li>`,
    ];
    if (clashes.length) {
      factList.push(
        `<li class="is-clash">${esc(t('csv_choice_fact_clash').replace('{count}', clashes.length))}</li>`,
      );
    } else if (existing && facts.dates.length) {
      factList.push(`<li>${esc(t('csv_choice_fact_all_new'))}</li>`);
    }

    const body =
      `<p>${esc(t('csv_choice_intro'))}</p>`
      + `<ul class="dw-csv-choice-facts">${factList.join('')}</ul>`
      + (clashes.length
        ? `<p class="dw-csv-choice-days" dir="ltr">${esc(clashes.slice(0, 8).join('  ·  '))}`
          + `${clashes.length > 8 ? ' …' : ''}</p>`
        : '');

    const fieldCount = Object.keys(facts.firstRow || {}).length;

    const buttons = [];

    /* Load it into the form instead of sending it anywhere.
       The three options are genuinely different destinations - the
       questionnaire, a dry run, your history - and this one was
       missing, so a user who wanted to start from a file they already
       had was left retyping forty fields beside a working importer.
       Offered first, and only when the file actually carries fields to
       load, so it never appears as a button that does nothing. */
    if (fieldCount > 0) {
      buttons.push({
        label: t('csv_choice_fill_btn'),
        hint: t('csv_choice_fill_hint')
          .replace('{count}', fieldCount)
          .replace('{date}', facts.firstDate || '—'),
        value: 'fill',
        style: 'primary',
        autofocus: true,
      });
    }

    buttons.push(
      {
        label: t('csv_choice_test_btn'),
        hint: t('csv_choice_test_hint'),
        value: 'test',
        style: fieldCount > 0 ? 'ghost' : 'primary',
        autofocus: fieldCount === 0,
      },
      {
        label: clashes.length
          ? t('csv_choice_replace_btn').replace('{count}', clashes.length)
          : t('csv_choice_save_btn'),
        hint: clashes.length
          ? t('csv_choice_replace_hint').replace('{count}', clashes.length)
          : t('csv_choice_save_hint'),
        value: 'save',
        style: clashes.length ? 'danger' : 'ghost',
      },
      { label: t('csv_choice_cancel'), value: null, style: 'ghost' },
    );

    const choice = await window.DWSheet.open({
      title: t('csv_choice_title'),
      bodyHtml: body,
      buttons,
      choice: true,
      size: 'sm',
    });
    return choice ? { mode: choice, clashes } : null;
  }

  /* A dry run's whole output is the scores, so it gets its own panel
     rather than a one-line toast: the point of "just test it" is to
     read the numbers. */
  function showCsvPreview(result) {
    const t = (k) => window.DWI18n.t(k);
    const esc = window.DWSheet.esc;
    const rows = (result.previews || []).map((p) => {
      const score = Number.isFinite(p.health_score) ? Math.round(p.health_score) : '—';
      return `<li><b dir="ltr">${esc(score)}</b> <span dir="ltr">${esc(p.date)}</span>`
        + `${p.health_class ? ` <span class="muted">${esc(p.health_class)}</span>` : ''}</li>`;
    });
    const failed = (result.failed_rows || []).length;
    const body =
      `<p>${esc(t('csv_preview_intro').replace('{count}', rows.length))}</p>`
      + `<ul class="dw-csv-choice-facts">${rows.join('')}</ul>`
      + (failed
        ? `<p class="dw-csv-choice-days">${esc(t('csv_preview_failed').replace('{count}', failed))}</p>`
        : '');
    window.DWSheet.open({
      title: t('csv_preview_title'),
      bodyHtml: rows.length ? body : `<p>${esc(t('csv_import_none_imported'))}</p>`,
      buttons: [{ label: t('csv_preview_close'), value: null, style: 'primary', autofocus: true }],
    });
  }

  function wireCsvImport() {
    const templateBtn = $('#csvTemplateBtn');
    if (templateBtn) templateBtn.href = window.DWApi.csvTemplateUrl();

    const uploadBtn = $('#csvUploadBtn');
    const uploadInput = $('#csvUploadInput');
    const resultEl = $('#csvImportResult');
    if (!uploadBtn || !uploadInput) return;

    uploadBtn.addEventListener('click', () => uploadInput.click());
    uploadInput.addEventListener('change', async (e) => {
      const file = e.target.files && e.target.files[0];
      uploadInput.value = '';
      if (!file) return;

      const facts = await readCsvFileFacts(file);
      const existing = await recordedDates();
      const intent = window.DWSheet ? await askCsvIntent(facts, existing) : { mode: 'save', clashes: [] };
      if (!intent) return;  // backed out; nothing sent, nothing changed

      /* "Fill the questionnaire" never reaches the server at all - the
         file was read in the browser and the answers go straight into
         the form, where the user can look at them, change any of them,
         and decide for themselves whether to record the day. */
      if (intent.mode === 'fill') {
        const loaded = Object.keys(facts.firstRow || {}).length;
        state.wizardData = { ...window.DWSchema.DEFAULTS, ...facts.firstRow };
        state.demoActive = false;
        // Not a prefill of TODAY, so ticking "just testing" must not
        // clear it - these are answers the user brought with them.
        state.prefilledFromToday = false;
        state.stepIndex = 0;
        renderStep();
        if (resultEl) {
          resultEl.textContent = window.DWI18n.t('csv_filled_form')
            .replace('{count}', loaded)
            .replace('{date}', facts.firstDate || '—');
          resultEl.classList.remove('hidden');
        }
        window.DWToast.success(window.DWI18n.t('csv_filled_toast').replace('{count}', loaded));
        return;
      }

      // This is the "auto-tick" half. Choosing to replace IS the edit
      // consent, so the flag is set here and the tick on the page is
      // brought in line with it rather than being a second thing to
      // find and click.
      const replacing = intent.mode === 'save' && intent.clashes.length > 0;
      if (replacing) {
        state.editToday = true;
        const editCheck = $('#editTodayCheck');
        if (editCheck && !editCheck.disabled) editCheck.checked = true;
      }

      try {
        const result = await window.DWApi.importHistoryCsv(
          file, intent.mode === 'save' ? (replacing || state.editToday) : false,
          { dryRun: intent.mode === 'test' },
        );
        if (result.dry_run) {
          if (resultEl) {
            resultEl.textContent = window.DWI18n.t('csv_preview_intro')
              .replace('{count}', (result.previews || []).length);
            resultEl.classList.remove('hidden');
          }
          showCsvPreview(result);
          return;
        }
        const parts = [];
        if (result.imported_count > 0) {
          parts.push(window.DWI18n.t('csv_import_success').replace('{count}', result.imported_count));
        }
        // A row refused for landing on an already-recorded day is not a
        // broken file - it is the one-check-in-a-day rule, and the fix
        // is a tick on this same page. Shown as its own sentence,
        // translated, instead of leaking the server's English
        // "already_recorded: ..." string into a Persian UI.
        const blocked = (result.failed_rows || []).filter(
          (f) => String((f.errors && f.errors.date) || '').indexOf('already_recorded') === 0
        );
        const otherFailures = (result.failed_rows || []).filter((f) => blocked.indexOf(f) === -1);
        if (blocked.length) {
          parts.push(
            window.DWI18n.t('csv_import_needs_edit_tick')
              .replace('{days}', blocked.map((f) => f.date).filter(Boolean).join(', '))
          );
        }
        if (otherFailures.length) {
          const lines = otherFailures.map((f) => {
            const firstError = Object.entries(f.errors)[0];
            const detail = firstError ? `${firstError[0]}: ${firstError[1]}` : '';
            return `${window.DWI18n.t('csv_import_row_label')} ${f.row_number}${f.date ? ' (' + f.date + ')' : ''} — ${detail}`;
          });
          parts.push(window.DWI18n.t('csv_import_failed_count').replace('{count}', otherFailures.length) + '\n' + lines.join('\n'));
        }
        if (resultEl) {
          resultEl.textContent = parts.join(' ');
          resultEl.classList.remove('hidden');
        }
        if (result.imported_count > 0) {
          window.DWToast.success(window.DWI18n.t('csv_import_success').replace('{count}', result.imported_count));
          if (window.DWMascot) window.DWMascot.react('neutral');
          // The upload may have created or replaced today's check-in,
          // which is what the tick and the whole edit flow key off.
          refreshTodayCheckIn();
        } else if (blocked.length && !otherFailures.length) {
          // Nothing imported *because* the rule stopped it. Saying
          // "none imported" here would read as a broken file and send
          // the user hunting for a formatting problem that is not
          // there.
          window.DWToast.error(window.DWI18n.t('csv_import_needs_edit_tick').replace('{days}', ''));
          refreshTodayCheckIn();
        } else {
          window.DWToast.error(window.DWI18n.t('csv_import_none_imported'));
        }
      } catch (err) {
        window.DWToast.error(err.message);
      }
    });
  }

  // ===================== RESULT =====================
  function classBadgeClass(pred) {
    const p = (pred || '').toLowerCase();
    if (p.includes('healthy')) return 'badge--healthy';
    if (p.includes('risk')) return 'badge--risk';
    return 'badge--moderate';
  }

  /* Narrative one-liner shown ABOVE the numbers, so the user meets a
     human sentence before a score. Uses only values the model already
     returned - it never introduces a new judgement. */
  function narrativeSummary(result) {
    const score = Math.round(result.regression_score ?? 0);
    const top = (result.shap_features || [])[0];
    const topLabel = top ? labelFor(top.feature) : '';
    const lang = window.DWI18n.get();
    const band = score >= 80 ? 'great' : score >= 66 ? 'good' : score >= 40 ? 'borderline' : 'risk';

    const T = {
      en: {
        great: `You scored ${score} out of 100 — a strong week. ${topLabel ? topLabel + ' is doing the most work in your favour.' : ''}`,
        good: `You scored ${score} out of 100 — a good place to be. ${topLabel ? topLabel + ' is the biggest single factor right now.' : ''}`,
        borderline: `You scored ${score} out of 100 — right around the middle. ${topLabel ? topLabel + ' is the factor moving your score most.' : ''}`,
        risk: `You scored ${score} out of 100. That is low, and the biggest driver is ${topLabel || 'the factors below'} — which is something you can change.`,
      },
      fa: {
        great: `امتیاز تو ${score} از ۱۰۰ شد — هفته‌ی قوی‌ای بوده. ${topLabel ? '«' + topLabel + '» بیشترین نقش را به نفع تو داشته.' : ''}`,
        good: `امتیاز تو ${score} از ۱۰۰ شد — جای خوبی هستی. ${topLabel ? '«' + topLabel + '» در حال حاضر مهم‌ترین عامل است.' : ''}`,
        borderline: `امتیاز تو ${score} از ۱۰۰ شد — تقریباً وسط. ${topLabel ? '«' + topLabel + '» بیشترین جابه‌جایی را در امتیازت ایجاد کرده.' : ''}`,
        risk: `امتیاز تو ${score} از ۱۰۰ شد. این پایین است، و مهم‌ترین عاملش ${topLabel ? '«' + topLabel + '»' : 'موارد پایین'} است — چیزی که می‌توانی تغییرش بدهی.`,
      },
      ar: {
        great: `درجتك ${score} من 100 — أسبوع قوي. ${topLabel ? '«' + topLabel + '» يقدّم أكبر دعم لصالحك.' : ''}`,
        good: `درجتك ${score} من 100 — وضع جيد. ${topLabel ? '«' + topLabel + '» هو أكبر عامل منفرد الآن.' : ''}`,
        borderline: `درجتك ${score} من 100 — في المنتصف تقريبًا. ${topLabel ? '«' + topLabel + '» هو العامل الأكثر تأثيراً على درجتك.' : ''}`,
        risk: `درجتك ${score} من 100. هذه منخفضة، والعامل الأكبر تأثيراً هو ${topLabel ? '«' + topLabel + '»' : 'العوامل أدناه'} — وهو شيء يمكنك تغييره.`,
      },
      zh: {
        great: `你的分数是 ${score}/100 —— 表现很好的一周。${topLabel ? `「${topLabel}」对你的帮助最大。` : ''}`,
        good: `你的分数是 ${score}/100 —— 状态不错。${topLabel ? `「${topLabel}」是目前最大的单一因素。` : ''}`,
        borderline: `你的分数是 ${score}/100 —— 大致处于中间。${topLabel ? `「${topLabel}」是影响你分数最大的因素。` : ''}`,
        risk: `你的分数是 ${score}/100。这个分数偏低，最大的影响因素是${topLabel ? `「${topLabel}」` : '下面列出的因素'}——这是你可以改变的。`,
      },
    };
    return ((T[lang] || T.en)[band] || '').trim();
  }

  function excludeRecommendationCategory(category) {
    let list = [];
    try { list = JSON.parse(localStorage.getItem('dwai_excluded_rec_categories') || '[]'); } catch (e) {}
    if (!list.includes(category)) list.push(category);
    localStorage.setItem('dwai_excluded_rec_categories', JSON.stringify(list));
  }

  /* Split out of renderResult() so a language switch can re-render just
     this section from the already-fetched result - re-running the whole
     result view would replay the score-ring water-fill and its chime.
     `result` is a parameter rather than closed over so both the initial
     render and the dwai:langchange handler below call the same code
     against explicit state. */
  function renderRecommendationCards(result) {
    const recWrap = $('#recCards');
    recWrap.innerHTML = '';
    if (!result.recommendations || result.recommendations.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'rec-card';
      empty.innerHTML = `<div class="rec-title">🌿 ${window.DWI18n.t('rec_none_title')}</div><p class="rec-desc">${window.DWI18n.t('rec_none_desc')}</p>`;
      recWrap.appendChild(empty);
    }
    (result.recommendations || []).forEach((r) => {
      const card = document.createElement('div');
      card.className = 'rec-card';
      const prio = (r.priority || 'low').toLowerCase();
      /* C-2/A-2: the rule text arrives in all four languages with this
         user's own numbers already substituted, computed by the same
         deterministic rules the engine has always used. `text_i18n` is
         the single source shared with the PDF; the flat English fields
         remain as the fallback for a rule that has no entry yet. */
      const t18 = r.text_i18n || {};
      const part = (name, fallback) => {
        const table = t18[name];
        if (!table) return fallback;
        return table[window.DWI18n.get()] || table.en || fallback;
      };
      const recTitle = part('title', r.title);
      const recDesc = part('description', r.description);
      const recAction = part('action', r.action);
      const recMetric = part('success_metric', r.success_metric);
      // priority/safety_note aren't per-rule text (three safety notes
      // and three priority levels cover every rule), so they arrive as
      // flat {lang: text} rather than the {part: {lang: text}} shape
      // above - both used to render in raw English here regardless of
      // language.
      const recPriority = (r.priority_i18n && (r.priority_i18n[window.DWI18n.get()] || r.priority_i18n.en)) || r.priority;
      const recSafety = (r.safety_note_i18n && (r.safety_note_i18n[window.DWI18n.get()] || r.safety_note_i18n.en)) || r.safety_note;
      // Tie the advice back to the exact number that earned it - the
      // real value the user just submitted for this recommendation's
      // source SHAP feature, never a fabricated or averaged one.
      let yourNumberLine = '';
      if (r.source_field && state.lastPayload && state.lastPayload[r.source_field] !== undefined) {
        const rawVal = state.lastPayload[r.source_field];
        const label = labelFor(r.source_field);
        if (rawVal !== null && typeof rawVal !== 'object') {
          yourNumberLine = `<p class="rec-your-number">📌 ${window.DWI18n.t('rec_your_value') || 'Your number'}: <strong>${label} = ${rawVal}</strong></p>`;
        }
      }
      card.innerHTML = `
        <div class="rec-head">
          <span class="rec-title">${r.icon || '💡'} ${recTitle}</span>
          <span class="badge badge--priority-${prio}">${recPriority}</span>
        </div>
        <p class="rec-desc">${recDesc}</p>
        ${yourNumberLine}
        <p class="rec-action">➜ ${recAction}</p>
        <div class="rec-meta"><strong>${window.DWI18n.t('rec_success_label')}:</strong> ${recMetric || '—'}<br/><span class="rec-safety">${recSafety || ''}</span></div>
        <button type="button" class="rec-exclude-btn" data-category="${r.category}">🚫 ${window.DWI18n.t('rec_exclude_btn')}</button>
      `;
      card.querySelector('.rec-exclude-btn').addEventListener('click', (e) => {
        excludeRecommendationCategory(r.category);
        e.target.closest('.rec-card').remove();
        window.DWToast.info(window.DWI18n.t('rec_exclude_confirm').replace('{category}', r.category));
      });
      recWrap.appendChild(card);
    });
    window.DWMotion.stagger(recWrap.children, { gap: 110 });
  }

  function renderResult(result) {
    const score = Math.max(0, Math.min(100, result.regression_score ?? 0));

    state.lastResult = result;
    // Default to "this is a fresh result". openPastDay() re-shows the
    // banner right after calling this, so a reopened day cannot leave
    // its banner behind on the next real check-in of the same session.
    state.viewingPastDay = null;
    const pastBanner = $('#pastDayBanner');
    if (pastBanner) pastBanner.classList.add('hidden');
    const summaryEl = $('#resultNarrative');
    // Prefer the server's tone-aware framing (it knows the user's saved
    // tone preference); fall back to the local narrative when absent.
    if (summaryEl) {
      // The server sends this line in every language because it does not
      // know which one the reader picked. Fall back to the English field
      // (older responses carry only that), then to the locally composed
      // summary - never to a blank opening line.
      // Read inline rather than through DWServerText: this one is a flat
      // {lang: text} map (there is only one sentence), not the
      // {part: {lang: text}} shape that helper reads.
      const framed = (result.result_framing_i18n || {})[window.DWI18n.get()];
      summaryEl.textContent = framed || result.result_framing || narrativeSummary(result);
    }

    // Four-arc ring: centre keeps the real regression score (drawn/counted
    // by DWScoreRing itself); the arcs are the transparent dimension
    // breakdown, each with a genuine water-wave fill and a "ding" per
    // arc completion. A final happy/sad chime plays once every arc with
    // data has finished, matching whether the result itself is good.
    const ringWrap = $('#scoreRingWrap');
    const dims = (result.dimension_breakdown && result.dimension_breakdown.dimensions) || [];
    if (ringWrap && window.DWScoreRing) {
      // Pass the server's calibrated interval so the ring can present the
      // score as a range (C-6-3) instead of a falsely precise single
      // number. Absent or unavailable uncertainty simply falls back to the
      // previous single-number centre - never a fabricated interval.
      const unc = result.uncertainty;
      const range = (unc && unc.available
        && unc.regression_lower != null && unc.regression_upper != null)
        ? { lower: unc.regression_lower, upper: unc.regression_upper }
        : null;
      window.DWScoreRing.render(ringWrap, {
        score, dimensions: dims, range,
        onAllArcsComplete: () => { if (window.DWSound) window.DWSound.resultChime(score >= 50); },
      });
    }

    const badge = $('#classBadge');
    badge.textContent = result.prediction;
    badge.className = 'badge ' + classBadgeClass(result.prediction);

    /* The two horizons. `regression_score` is TODAY (regressor target:
       health_score_0_100) and `prediction` is SEVEN DAYS OUT
       (classifier target: future_health_class_7d). They were being
       shown as one reading. `future_score` is the band that class
       typically covers - explicitly not a projection of this user's own
       number, which is why the class is the headline of that card and
       the range sits under it in smaller type. */
    const todayEl = $('#horizonTodayScore');
    if (todayEl) todayEl.textContent = Math.round(score);
    const futureClassEl = $('#horizonFutureClass');
    if (futureClassEl) futureClassEl.textContent = result.prediction || '--';
    const futureBandEl = $('#horizonFutureBand');
    if (futureBandEl) {
      /* Output 1 ships `available: false` with basis "class_only" - the
         class is deliberately the whole answer there, and printing an
         empty range or a dash would suggest a number went missing. */
      const fs = result.future_score;
      futureBandEl.textContent = (fs && fs.available && fs.lower != null && fs.upper != null)
        ? `${Math.round(fs.lower)}–${Math.round(fs.upper)}`
        : '';
      futureBandEl.classList.toggle('hidden', !(fs && fs.available));

      /* The band is not class-typical any more: the user's own recent
         days move it (services/insight/future_score_service.py `_momentum`).
         A number that shifted for a reason should say the reason -
         otherwise two people with the same day see different bands and
         neither is told why. */
      const momentumEl = $('#horizonMomentum');
      if (momentumEl) {
        const shift = fs && fs.available ? Number(fs.momentum_shift || 0) : 0;
        const days = fs ? Number(fs.momentum_days || 0) : 0;
        if (Math.abs(shift) >= 0.5 && days >= 3) {
          momentumEl.textContent = window.DWI18n
            .t(shift > 0 ? 'horizon_momentum_up' : 'horizon_momentum_down')
            .replace('{points}', Math.abs(shift).toFixed(1))
            .replace('{days}', days);
          momentumEl.classList.remove('hidden');
        } else {
          momentumEl.classList.add('hidden');
        }
      }
    }

    // Confidence as a wave-filling bar.
    const confBar = $('#confidenceBar');
    confBar.dataset.fill = String((result.confidence_percent || 0) / 100);
    window.DWMotion.waveFill(confBar, (result.confidence_percent || 0) / 100, { delay: 200 });
    window.DWMotion.countUp($('#confidenceNum'), result.confidence_percent || 0, {
      decimals: 0, duration: 1200, format: (v) => `${Math.round(v)}%`,
    });
    $('#personaLine').textContent = '';

    // Plain-language confidence reading, and an honest warning when the
    // inputs sit at the edge of what the model has actually seen.
    const cl = result.confidence_label;
    const clEl = $('#confidenceLabel');
    if (clEl && cl) {
      clEl.className = `confidence-label level-${cl.level}`;
      // Server-composed sentences, sent in every language because the
      // server does not know which one the reader picked. Falls back to
      // the flat English fields for an older response.
      const headline = window.DWServerText.pick(cl, 'headline');
      const detail = window.DWServerText.pick(cl, 'detail');
      clEl.innerHTML = '';
      const strong = document.createElement('strong');
      strong.textContent = headline;
      clEl.appendChild(strong);
      clEl.appendChild(document.createTextNode(' ' + detail));
    }
    const oodEl = $('#oodWarning');
    if (oodEl) {
      const ood = result.ood;
      if (ood && ood.is_out_of_distribution) {
        oodEl.textContent = '⚠️ ' + window.DWServerText.pick(ood, 'message');
        oodEl.classList.remove('hidden');
      } else {
        oodEl.classList.add('hidden');
      }
    }

    const u = result.uncertainty;
    const uNote = $('#uncertaintyNote');
    if (u && u.available) {
      let text = u.explanation || '';
      if (u.regression_lower != null && u.regression_upper != null) {
        // Was a hardcoded English sentence appended to a translated
        // explanation, so every non-English reader got a mixed-language
        // line here. The range itself is now the ring's headline, so this
        // note explains WHY there is a range rather than repeating it.
        const why = window.DWI18n ? window.DWI18n.t('score_range_note') : '';
        if (why) text += ' ' + why;
      }
      uNote.textContent = text;
      uNote.classList.remove('hidden');
    } else {
      uNote.classList.add('hidden');
    }

    // ---- SHAP bars (wave fill, staggered, only once in view) ----
    const shapWrap = $('#shapBars');
    shapWrap.innerHTML = '';
    (result.shap_features || []).slice(0, 8).forEach((f) => {
      const row = document.createElement('div');
      row.className = 'shap-bar-row';
      const pct = Math.min(100, Math.abs(f.score || 0));
      const isHarmful = f.direction === 'decrease';
      row.innerHTML = `
        <div class="name">${labelFor(f.feature)}</div>
        <div class="shap-bar-track">
          <div class="wave-bar shap-wave ${f.direction}" data-fill="${pct / 100}"></div>
        </div>
        <div class="shap-dir ${f.direction}" title="${isHarmful ? 'pulling score down' : 'pushing score up'}">${isHarmful ? '↓' : '↑'}</div>
      `;
      shapWrap.appendChild(row);
    });
    window.DWMotion.waveFillOnView(shapWrap, '.shap-wave', { gap: 130 });

    // ---- Wellness dimension breakdown (transparent, non-ML rollup) ----
    const dimWrap = $('#dimensionBars');
    if (dimWrap) {
      dimWrap.innerHTML = '';
      const dims = (result.dimension_breakdown && result.dimension_breakdown.dimensions) || [];
      dims.forEach((d) => {
        const row = document.createElement('div');
        row.className = 'dimension-row';
        row.innerHTML = `
          <div class="name">${window.DWI18n.t('dim_' + d.key) || d.label}</div>
          <div class="dimension-track">
            <div class="wave-bar dim-wave" data-fill="${d.score / 100}"></div>
          </div>
          <div class="mono">${Math.round(d.score)}</div>
        `;
        dimWrap.appendChild(row);
      });
      window.DWMotion.waveFillOnView(dimWrap, '.dim-wave', { gap: 110 });
    }

    renderRecommendationCards(result);

    // Expression + tone come from the real score, using the same bands
    // the colour ring uses. A moment later the generic line is replaced
    // by one built from this specific result's own numbers.
    window.DWMascot.reactToScore(score);
    const personalLine = personalizedGuideLine(result);
    if (personalLine) {
      // This one line stays (it is built from THIS result's own numbers,
      // not a generic greeting) but it no longer speaks out loud on its
      // own - `speak: false`. Unprompted speech on arrival was reported
      // as the most irritating behaviour in the app; reading it is
      // useful, being talked at is not. Tapping the mascot still reads
      // things aloud for anyone who wants that.
      setTimeout(
        () => window.DWMascot.say(personalLine, { attention: true, duration: 12000, speak: false }),
        1500,
      );
    }

    renderRoadmap(result);
    renderFutureSelf(result);
  }

  /* A sentence built only from this result's own real numbers - the top
     SHAP factor and the value the user actually typed for it, plus the
     single weakest dimension when it's genuinely low. Never a canned
     line: if the numbers aren't there, this returns ''. */
  function formatRawVal(feature, value) {
    // *_ratio fields are 0-1 shares of screen time (see
    // core/feature_schema.py: "... Share of Screen Time (0-1)") - showing
    // the raw fraction ("0.0357") reads as a bug, not a number, to anyone
    // who isn't expecting a 0-1 scale. Every other numeric field (hours,
    // counts, 0-10 scales) already reads fine as typed.
    if (/_ratio$/.test(feature) && typeof value === 'number') {
      return `${Math.round(value * 100)}%`;
    }
    // A field the schema declares as an int has no fractional part to
    // show. The future-path cards were printing "notifications down to
    // 985.7", which reads as a bug rather than as a target.
    const def = state.featureSchemaMap[feature];
    if (def && def.dtype === 'int' && typeof value === 'number') {
      return String(Math.round(value));
    }
    if (typeof value === 'number' && !Number.isInteger(value)) {
      return String(Math.round(value * 10) / 10);
    }
    return String(value);
  }

  function personalizedGuideLine(result) {
    const lang = window.DWI18n.get();
    const top = (result.shap_features || [])[0];
    if (!top) return '';
    const topLabel = labelFor(top.feature);
    const rawVal = state.lastPayload ? state.lastPayload[top.feature] : null;
    const hasRaw = rawVal !== null && rawVal !== undefined && typeof rawVal !== 'object';
    const formattedVal = hasRaw ? formatRawVal(top.feature, rawVal) : '';
    const dims = (result.dimension_breakdown && result.dimension_breakdown.dimensions) || [];
    const weakest = dims.length ? dims.reduce((a, b) => (a.score < b.score ? a : b)) : null;
    const weakLabel = weakest ? (window.DWI18n.t('dim_' + weakest.key) || weakest.label) : '';
    const cl = result.confidence_label;
    const weakestScore = weakest ? Math.round(weakest.score) : 0;

    const topPart = window.DWI18n.pick({
      en: `Looking at your actual numbers: ${topLabel}${hasRaw ? ` (you logged ${formattedVal})` : ''} moved this result the most.`,
      fa: `با نگاهی به اعداد واقعی خودت: «${topLabel}»${hasRaw ? ` (که ${formattedVal} ثبت کردی)` : ''} بیشترین اثر را روی این نتیجه گذاشته.`,
      ar: `بالنظر إلى أرقامك الحقيقية: «${topLabel}»${hasRaw ? ` (سجّلت ${formattedVal})` : ''} كان له أكبر تأثير على هذه النتيجة.`,
      zh: `看看你的真实数据：「${topLabel}」${hasRaw ? `（你记录的是 ${formattedVal}）` : ''} 对这次结果的影响最大。`,
    });
    let s = topPart;
    if (weakest && weakest.score < 55) {
      s += ' ' + window.DWI18n.pick({
        en: `Your ${weakLabel.toLowerCase()} score is your softest area right now, at ${weakestScore}/100.`,
        fa: `امتیاز «${weakLabel}» تو الان ضعیف‌ترین بخش است: ${weakestScore} از ۱۰۰.`,
        ar: `درجة «${weakLabel}» هي أضعف مجال لديك الآن، بـ ${weakestScore}/100.`,
        zh: `你的「${weakLabel}」分数目前是最薄弱的部分，为 ${weakestScore}/100。`,
      });
    }
    if (cl && cl.level === 'low') {
      s += ' ' + window.DWI18n.pick({
        en: "I'd hold this result loosely — the model isn't fully confident yet.",
        fa: 'این نتیجه را خیلی قطعی نگیر — مدل هنوز کاملاً به آن مطمئن نیست.',
        ar: 'لا تأخذ هذه النتيجة كأمر مؤكد تماماً — النموذج ليس واثقاً منها بالكامل بعد.',
        zh: '不要把这个结果看得太绝对——模型对此还不完全有把握。',
      });
    }
    return s;
  }

  /* Inline 7-day roadmap on the result page itself, reusing the exact
     same rule-based plan generator as the Weekly Plan page - never a
     second, divergent implementation. Shown as a condensed day-by-day
     list (theme + first task) since the full checklist UI belongs on
     the Weekly page. */
  async function renderRoadmap(result) {
    const list = $('#roadmapList');
    if (!list) return;
    list.innerHTML = `<li class="muted">${window.DWI18n.t('loading') || 'Loading…'}</li>`;
    try {
      // On a language switch the plan is already in hand and already
      // holds all four languages, so re-rendering is enough - refetching
      // would be wasted work and one more place for the network to fail
      // mid-read.
      const plan = state.lastPlan || await window.DWApi.generatePlan({
        health_class: result.prediction,
        wellness_score: result.regression_score,
        persona: result.persona || null,
        user_data: state.lastPayload || {},
      });
      // The plan arrives in all four languages - the exercises always
      // did, and the wrapper text (day label, theme, tip) does too. This
      // block used to render `day.day_label` / `day.theme` /
      // `task.text`, i.e. the flat English fallback fields, so the
      // result page's whole 7-day roadmap stayed in English no matter
      // which language the reader had chosen. The Weekly Plan page has
      // read text_i18n since it was written; this one never did.
      const lang = window.DWI18n.get();
      const serverText = (payload, part, fallback) => {
        const table = ((payload && payload.text_i18n) || {})[part];
        if (table) return table[lang] || table.en || fallback || '';
        return fallback || '';
      };

      list.innerHTML = '';
      (plan.days || []).forEach((day) => {
        const li = document.createElement('li');
        li.className = 'roadmap-item';
        const firstTask = (day.tasks || [])[0];
        // A task's own text_i18n is a flat {lang: text}, not the
        // {part: {lang: text}} shape the day carries.
        const taskText = firstTask
          ? ((firstTask.text_i18n && (firstTask.text_i18n[lang] || firstTask.text_i18n.en))
            || firstTask.text)
          : '';
        li.innerHTML = `
          <span class="roadmap-day">${day.icon || '📅'} ${serverText(day, 'day_label', day.day_label)}</span>
          <span class="roadmap-theme">${serverText(day, 'theme', day.theme)}</span>
          ${taskText ? `<span class="roadmap-task">${taskText}</span>` : ''}
        `;
        list.appendChild(li);
      });
      window.DWMotion.stagger(list.children, { gap: 70 });
      // Kept so a language switch can re-render without asking the
      // server for the same plan again.
      state.lastPlan = plan;
    } catch (e) {
      list.innerHTML = `<li class="muted">${window.DWI18n.t('roadmap_unavailable') || 'Your roadmap will appear here.'}</li>`;
    }
  }

  /* "Talk to your future self": real re-runs of the same trained model
     on named future behavior patterns (services/insight/future_path_service.py)
     - never a scripted motivational line. Only the two forward-looking,
     non-drift paths are shown here (status quo is the baseline, drift
     is covered elsewhere) to keep this block encouraging rather than a
     full scenario table. */
  /* Future-path copy.

     Two problems were fused into one line here. First, "the model says
     your score becomes X" asserts a definite future for what is a
     simulation of a hypothetical pattern - the model does not know what
     you will do. Second, both paths rendered from that one template, so
     "Gradual improvement" and "Committed change" differed only in their
     heading and read as the same card twice.

     Each path now has its own framing, and all of it is conditional
     ("could reach", not "becomes"). Four languages, because the previous
     `lang === 'fa' ? … : …` form served English to Arabic and Chinese. */
  const FUTURE_PATH_NAMES = {
    gradual_improvement: { en: 'Gradual improvement', fa: 'بهبود تدریجی', ar: 'تحسّن تدريجي', zh: '渐进改善' },
    committed_change: { en: 'Committed change', fa: 'تلاش جدی', ar: 'تغيير جادّ', zh: '全力投入' },
    continued_drift: { en: 'If nothing changes', fa: 'اگر چیزی تغییر نکند', ar: 'إن لم يتغير شيء', zh: '如果什么都不改变' },
  };

  const FUTURE_PATH_LEADS = {
    gradual_improvement: {
      en: 'Nudging a few habits slightly, the simulation lands around',
      fa: 'با تغییر ملایم چند عادت، شبیه‌سازی حدود این عدد را نشان می‌دهد:',
      ar: 'بتعديل بضع عادات قليلاً، تصل المحاكاة إلى نحو',
      zh: '把几个习惯稍作调整，模拟结果大约落在',
    },
    committed_change: {
      en: 'Sustaining a real effort across several habits, the simulation reaches around',
      fa: 'با تلاش واقعی و پیوسته روی چند عادت، شبیه‌سازی حدود این عدد را نشان می‌دهد:',
      ar: 'بجهد حقيقي ومستمر عبر عدة عادات، تبلغ المحاكاة نحو',
      zh: '在多个习惯上持续付出真实努力，模拟结果达到大约',
    },
    continued_drift: {
      en: 'Carrying on exactly as now, the simulation drifts toward',
      fa: 'با ادامه‌ی دقیقاً وضع فعلی، شبیه‌سازی به سمت این عدد می‌رود:',
      ar: 'بالاستمرار تماماً كما الآن، تنجرف المحاكاة نحو',
      zh: '完全照现在这样继续下去，模拟结果偏向',
    },
  };

  const FUTURE_PATH_DELTA = {
    same: { en: 'not a meaningful change from today', fa: 'تفاوت محسوسی با امروز ندارد', ar: 'ليس تغيّراً ذا معنى عن اليوم', zh: '与今天相比没有实质变化' },
    vs: { en: 'vs. today', fa: 'نسبت به امروز', ar: 'مقارنةً باليوم', zh: '相比今天' },
  };

  /* Said instead of the flat "not a meaningful change" when the reason
     the number barely moves is that there is barely anywhere left to
     go. Above the mid-eighties the model's own range runs out, so a
     bigger effort and a smaller one land on the same score - and
     "no meaningful change" on BOTH cards reads as the feature having
     given up, when it is actually reporting a very good position.
     The ceiling is real and measured: scoring inputs at the healthy end
     of every field tops out around 87 (see services/demo/demo_service.py's
     calibration note). */
  const FUTURE_PATH_NEAR_CEILING = {
    en: 'the same score, because at {score} you are close to the top of what this model can award - the effort still counts, the number has just run out of room',
    fa: 'همان امتیاز، چون در {score} به سقف چیزی که این مدل می‌تواند بدهد نزدیک شده‌ای — تلاش هنوز ارزش دارد، فقط عدد جا برای بالا رفتن ندارد',
    ar: 'الدرجة نفسها، لأنك عند {score} قريب من أعلى ما يمنحه هذا النموذج — الجهد ما زال مهماً، لكن الرقم لم يعد أمامه مجال',
    zh: '同样的分数，因为在 {score} 分你已经接近这个模型能给出的上限——努力依然算数，只是数字没有上升的空间了',
  };

  /* What the path would actually DO. Two cards showing the same number
     read as one card printed twice; two cards showing "an hour less
     screen time" against "two and a half hours less" read as two
     different lives, which is what the section is for. Built from the
     server's own `adjustments` list, so it is the real simulated shift
     and not a restatement of the path's name. */
  const FUTURE_PATH_MEANS = {
    en: 'What it means in practice: {changes}.',
    fa: 'در عمل یعنی: {changes}.',
    ar: 'ماذا يعني عملياً: {changes}.',
    zh: '具体来说：{changes}。',
  };
  const FUTURE_CHANGE_DIR = {
    down: { en: '{label} down to {to}', fa: '{label} تا {to}', ar: '{label} إلى {to}', zh: '{label}降到 {to}' },
    up: { en: '{label} up to {to}', fa: '{label} تا {to}', ar: '{label} إلى {to}', zh: '{label}提到 {to}' },
  };

  /* The three biggest moves, in the reader's language, as a phrase.
     Three because two reads as thin and four wraps to a third line on a
     phone. */
  function futurePathChanges(p) {
    const rows = (p.adjustments || [])
      .filter((a) => a && a.field && a.new_value != null && a.old_value != null)
      .map((a) => {
        const span = Math.abs(Number(a.new_value) - Number(a.old_value));
        const feature = state.featureSchemaMap[a.field];
        const range = feature && feature.maximum != null && feature.minimum != null
          ? Math.abs(feature.maximum - feature.minimum) || 1
          : 1;
        // Ranked by how big the move is relative to the field's own
        // range, so "20 fewer notifications" does not outrank "an hour
        // less screen time" purely because its numbers are bigger.
        return { a, weight: span / range, span };
      })
      .filter((r) => r.span > 0)
      .sort((x, y) => y.weight - x.weight)
      .slice(0, 3);
    if (!rows.length) return '';
    const phrases = rows.map(({ a }) => {
      const dir = Number(a.new_value) < Number(a.old_value) ? 'down' : 'up';
      const to = formatRawVal(a.field, Number(a.new_value));
      return window.DWI18n.pick(FUTURE_CHANGE_DIR[dir])
        .replace('{label}', labelFor(a.field))
        .replace('{to}', to);
    });
    const joiner = { en: ', ', fa: '، ', ar: '، ', zh: '，' }[window.DWI18n.get()] || ', ';
    return window.DWI18n.pick(FUTURE_PATH_MEANS).replace('{changes}', phrases.join(joiner));
  }

  /* When a path could not change anything because the user is already
     at or past the healthy target on every habit it adjusts. Showing
     the same number twice with no explanation reads as a broken
     feature; this says the true and much better thing. */
  const FUTURE_PATH_AT_TARGET = {
    en: 'There is nothing here for this path to change — on every habit it can adjust, you are already at or past the healthy level. Holding it is the whole task.',
    fa: 'اینجا چیزی برای تغییر دادن باقی نمانده — در هر عادتی که این مسیر می‌تواند جابه‌جا کند، از قبل در سطح سالم یا بهتر از آن هستی. نگه‌داشتنش تمام کار است.',
    ar: 'لا شيء هنا ليغيّره هذا المسار — في كل عادة يستطيع تعديلها، أنت بالفعل عند المستوى الصحي أو أفضل منه. الحفاظ عليه هو المهمة كلها.',
    zh: '这条路径已经没有什么可改的了——在它能调整的每一个习惯上，你都已经达到或超过了健康水平。保持住，就是全部的任务。',
  };

  /* Shown INSTEAD of two identical cards when every simulated path has
     nothing left to change. Previously each path rendered the same
     at-target sentence with no number at all, so a strong result got
     two visually identical cards of dry text - reported, correctly, as
     the section looking broken. This says the same honest thing once,
     and puts the user's real number in it. */
  const FUTURE_PATH_ALL_AT_TARGET = {
    title: {
      en: "You're already there", fa: 'تو همین حالا آنجایی',
      ar: 'أنت بالفعل هناك', zh: '你已经在那里了',
    },
    body: {
      en: 'Every habit these paths could improve is already at or past its healthy level, so the simulation has nothing left to move — it returns your own {score}/100. That is not the model running out of ideas; it is the rare case where the honest advice is "keep doing exactly this". The place to look for change now is a habit you care about that the model does not track.',
      fa: 'هر عادتی که این مسیرها می‌توانستند بهترش کنند، از قبل در سطح سالم یا بالاتر است؛ پس شبیه‌سازی چیزی برای جابه‌جا کردن ندارد و همان {score} از ۱۰۰ خودت را برمی‌گرداند. این یعنی مدل ایده کم نیاورده — این همان حالت کمیابی است که توصیه‌ی صادقانه‌اش «دقیقاً همین را ادامه بده» است. جای تغییر را حالا باید در عادتی بگردی که برایت مهم است ولی مدل ردیابی‌اش نمی‌کند.',
      ar: 'كل عادة كان بإمكان هذه المسارات تحسينها هي بالفعل عند مستواها الصحي أو أفضل، فلم يبقَ للمحاكاة ما تحركه وتعيد لك درجتك أنت {score}/100. هذا ليس نفاد أفكار من النموذج؛ إنها الحالة النادرة التي تكون فيها النصيحة الصادقة "واصل هذا بالضبط". مكان التغيير الآن هو عادة تهمّك ولا يتتبعها النموذج.',
      zh: '这些路径能改善的每一个习惯，都已经达到或超过了健康水平，所以模拟没有什么可以移动的，它返回的就是你自己的 {score}/100。这不是模型没主意了；这是少见的、诚实建议就是"继续保持"的情况。现在该找的改变，是模型没有追踪、但你在意的那个习惯。',
    },
  };

  function futurePathName(p) {
    const table = FUTURE_PATH_NAMES[p.key];
    return table ? window.DWI18n.pick(table) : (p.name || '');
  }

  function futurePathLine(p, meaningful, delta) {
    if (p.already_at_target) {
      // Still carry the number. A card with no figure at all is what
      // made this section read as broken; "nothing to change, you stay
      // at 84" is a real answer, "nothing to change" alone is not.
      const held = Math.round(p.regression_score);
      return `${window.DWI18n.pick(FUTURE_PATH_AT_TARGET)} (${held}/100)`;
    }
    const lead = FUTURE_PATH_LEADS[p.key] || FUTURE_PATH_LEADS.gradual_improvement;
    const score = Math.round(p.regression_score);
    // Near the top of the scale a bigger effort and a smaller one land
    // on the same number, and the bare "no meaningful change" was
    // landing on BOTH cards - which reads as the feature giving up
    // rather than as the compliment it actually is.
    const nearCeiling = !meaningful && score >= 80;
    const tail = meaningful
      ? ` (${delta > 0 ? '+' : ''}${delta.toFixed(1)} ${window.DWI18n.pick(FUTURE_PATH_DELTA.vs)})`
      : ` (${nearCeiling
        ? window.DWI18n.pick(FUTURE_PATH_NEAR_CEILING).replace('{score}', score)
        : window.DWI18n.pick(FUTURE_PATH_DELTA.same)})`;
    return `${window.DWI18n.pick(lead)} ${score}${tail}.`;
  }

  async function renderFutureSelf(result) {
    const wrap = $('#futureSelfCards');
    if (!wrap || !state.lastPayload) return;
    wrap.innerHTML = `<p class="muted">${window.DWI18n.t('loading') || 'Loading…'}</p>`;
    try {
      const comparison = await window.DWApi.futurePathCompare(state.lastPayload, ['gradual_improvement', 'committed_change']);
      const lang = window.DWI18n.get();
      wrap.innerHTML = '';

      /* When EVERY path has nothing left to change, two cards would
         repeat the same sentence word for word. Say it once, with the
         user's real number in it, instead of looking like a rendering
         fault. */
      const shown = (comparison.paths || []).filter((p) => p.regression_score != null);
      if (shown.length && shown.every((p) => p.already_at_target)) {
        const score = Math.round(shown[0].regression_score);
        const card = document.createElement('div');
        card.className = 'future-self-card';
        card.innerHTML =
          `<div class="future-self-name">${window.DWI18n.pick(FUTURE_PATH_ALL_AT_TARGET.title)}</div>`
          + `<p class="future-self-line">${window.DWI18n.pick(FUTURE_PATH_ALL_AT_TARGET.body).replace('{score}', score)}</p>`;
        wrap.appendChild(card);
        window.DWMotion.stagger(wrap.children, { gap: 100 });
        return;
      }

      shown.forEach((p) => {
        /* The server owns the noise floor now (FuturePathComparison
           .NOISE_FLOOR). Duplicating the 1.5 here meant two places
           could disagree about whether a delta was real. */
        const meaningful = !!p.delta_is_meaningful;
        const delta = p.score_delta_vs_status_quo;
        const card = document.createElement('div');
        card.className = 'future-self-card';
        const name = futurePathName(p);
        const line = futurePathLine(p, meaningful, delta);
        // The two paths are different LIVES, not two numbers. When the
        // scores converge - which they do near the top of the scale -
        // this is the only thing left telling them apart, and it was
        // missing: the cards carried a name, a sentence and a figure,
        // and nothing about what the path would have you actually do.
        const changes = p.already_at_target ? '' : futurePathChanges(p);
        card.innerHTML = `<div class="future-self-name">${name}</div>`
          + `<p class="future-self-line">${line}</p>`
          + (changes ? `<p class="future-self-changes">${changes}</p>` : '');
        wrap.appendChild(card);
      });
      if (!wrap.children.length) wrap.innerHTML = `<p class="muted">${window.DWI18n.t('roadmap_unavailable') || ''}</p>`;
      window.DWMotion.stagger(wrap.children, { gap: 100 });
    } catch (e) {
      wrap.innerHTML = '';
    }
  }

  /* ---------------------------------------------------------------
     Saved check-ins (DWCsvLibrary). Saving from the result page writes
     the answers that produced THIS result - state.lastPayload, the
     exact object that was sent - so a reloaded file reproduces the run
     rather than approximating it.
     --------------------------------------------------------------- */
  function wireCsvSave() {
    const btn = $('#csvSaveBtn');
    const input = $('#csvSaveName');
    const status = $('#csvSaveStatus');
    if (!btn || !input || !window.DWCsvLibrary) return;

    const doSave = () => {
      const name = input.value.trim();
      if (!name) {
        status.textContent = window.DWI18n.t('csv_save_needs_name');
        input.focus();
        return;
      }
      if (!state.lastPayload) return;
      const result = window.DWCsvLibrary.save(name, state.lastPayload, {
        excluded: state.excludeFromAnalysis,
        score: state.lastResult ? state.lastResult.regression_score : null,
      });
      if (!result) return;
      // The file is the durable copy, so it downloads even if the
      // browser refused to grow localStorage.
      window.DWCsvLibrary.download(result.entry);
      status.textContent = result.stored
        ? window.DWI18n.t('csv_save_done').replace('{name}', result.entry.name)
        : window.DWI18n.t('csv_save_downloaded_not_listed');
      input.value = '';
      renderCsvHistory();
    };

    btn.addEventListener('click', doSave);
    // Enter in the name box saves, as asked - the field exists to be
    // typed into and confirmed, not to need a mouse trip.
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); doSave(); }
    });
  }

  // Dates in the saved list follow the UI language, same mapping
  // weekly-card.js already uses.
  const LOCALE_FOR_LANG = { en: 'en-US', fa: 'fa-IR', ar: 'ar-SA', zh: 'zh-CN' };

  let csvHistoryKind = 'main';

  function renderCsvHistory() {
    const card = $('#csvHistoryCard');
    const listEl = $('#csvHistoryList');
    if (!card || !listEl || !window.DWCsvLibrary) return;

    const all = window.DWCsvLibrary.list();
    card.classList.toggle('hidden', all.length === 0);
    if (!all.length) return;

    $all('.csv-tab', card).forEach((t) => {
      t.classList.toggle('active', t.dataset.kind === csvHistoryKind);
    });

    const rows = window.DWCsvLibrary.list(csvHistoryKind);
    listEl.innerHTML = '';
    if (!rows.length) {
      listEl.innerHTML = `<p class="muted">${window.DWI18n.t('csv_history_empty_shelf')}</p>`;
      return;
    }

    rows.forEach((entry) => {
      const row = document.createElement('div');
      row.className = 'csv-history-row';
      const when = new Date(entry.savedAt).toLocaleDateString(
        LOCALE_FOR_LANG[window.DWI18n.get()] || 'en-US',
        { month: 'short', day: 'numeric' },
      );
      const score = entry.score != null
        ? `<span class="csv-history-score" dir="ltr">${entry.score}</span>` : '';
      row.innerHTML =
        `<button type="button" class="csv-history-load" data-id="${entry.id}">`
        + `<span class="csv-history-name"></span>`
        + `<span class="csv-history-meta" dir="ltr">${when}</span>${score}</button>`
        + `<button type="button" class="csv-history-dl" data-dl="${entry.id}"`
        + ` title="${window.DWI18n.t('csv_history_download')}" aria-label="${window.DWI18n.t('csv_history_download')}">⬇️</button>`
        + `<button type="button" class="csv-history-del" data-del="${entry.id}"`
        + ` title="${window.DWI18n.t('csv_history_delete')}" aria-label="${window.DWI18n.t('csv_history_delete')}">×</button>`;
      // textContent, never innerHTML: the name is user input.
      row.querySelector('.csv-history-name').textContent = entry.name;
      listEl.appendChild(row);
    });
  }

  function applySavedCheckin(id) {
    const entry = window.DWCsvLibrary.get(id);
    if (!entry || !entry.payload) return;
    // Start from the schema defaults so a file saved before a field
    // existed cannot leave that field undefined, then lay the saved
    // answers over the top.
    state.wizardData = { ...window.DWSchema.DEFAULTS, ...entry.payload };
    state.demoActive = false;
    state.stepIndex = 0;
    renderStep();
    window.DWToast.success(
      window.DWI18n.t('csv_history_loaded').replace('{name}', entry.name),
    );
  }

  function wireCsvHistory() {
    const card = $('#csvHistoryCard');
    if (!card || !window.DWCsvLibrary) return;

    card.addEventListener('click', (e) => {
      const tab = e.target.closest('.csv-tab');
      if (tab) { csvHistoryKind = tab.dataset.kind; renderCsvHistory(); return; }

      const del = e.target.closest('[data-del]');
      if (del) { window.DWCsvLibrary.remove(del.dataset.del); renderCsvHistory(); return; }

      const dl = e.target.closest('[data-dl]');
      if (dl) {
        const entry = window.DWCsvLibrary.get(dl.dataset.dl);
        if (entry) window.DWCsvLibrary.download(entry);
        return;
      }

      const load = e.target.closest('.csv-history-load');
      if (load) applySavedCheckin(load.dataset.id);
    });

    renderCsvHistory();
  }

  function wireResultActions() {
    $('#downloadPdfBtn').addEventListener('click', async () => {
      if (!state.lastPayload) return;
      try {
        const blob = await window.DWApi.reportPdf(state.lastPayload, false);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'wellness_report.pdf';
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
      } catch (err) {
        window.DWToast.error(err.message);
      }
    });
  }

  // ===================== SETTINGS =====================
  function wireSettings() {
    /* Built from app-chrome.js's single template, exactly like every
       other page. This page used to carry its own hardcoded copy of
       the panel in app.html; because ensureSettingsModal() reuses any
       #settingsModal it finds, that copy won a race it should never
       have been in, and it had never gained the Digital guide section -
       so the guide's switches were unreachable from the check-in page.
       One template, one panel, no drift. */
    if (window.DWChrome && window.DWChrome.ensureSettingsModal) {
      window.DWChrome.ensureSettingsModal();
    }
    const modal = $('#settingsModal');
    if (!modal) return;
    $('#settingsBtn').addEventListener('click', () => {
      $('#settingsThemeSwitch').checked = window.DWTheme.get() === 'dark';
      $('#settingsMotionSwitch').checked = window.DWMotion.prefersReduced();
      let excluded = [];
      try { excluded = JSON.parse(localStorage.getItem('dwai_excluded_rec_categories') || '[]'); } catch (e) {}
      $('#settingsExcludedRow').style.display = excluded.length ? 'flex' : 'none';
      modal.classList.add('show');
    });
    $('#settingsCloseBtn').addEventListener('click', () => modal.classList.remove('show'));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });
    $('#settingsResetExcludedBtn').addEventListener('click', () => {
      localStorage.removeItem('dwai_excluded_rec_categories');
      $('#settingsExcludedRow').style.display = 'none';
      window.DWToast.success(window.DWI18n.t('settings_reset_done'));
    });

    if (window.DWChrome) {
      window.DWChrome.wireCommonToggles(modal);
      window.DWChrome.removeStraySoundFxWidgetButton();
      window.DWChrome.wireNotifBell();
    }
    $('#settingsLogoutBtn').addEventListener('click', doLogout);
    $('#logoutBtn').addEventListener('click', doLogout);
  }

  function doLogout() {
    // Server first, while the token is still valid: clearing local
    // storage on its own leaves a thirty-day refresh token alive on the
    // server, so "log out" would delete the app's copy of a credential
    // that still works. Fire-and-forget - a failed call must not trap
    // somebody in a session they asked to leave.
    window.DWApi.logout();
    window.DWApi.clearToken();
    state.account = null;
    $('#logoutBtn').classList.add('hidden');
    $('#appNavRow').classList.add('hidden');
    $('#settingsModal').classList.remove('show');
    window.DWToast.info(window.DWI18n.t('toast_logged_out'));
    showView('view-auth');
  }

  // ===================== INIT =====================
  document.addEventListener('DOMContentLoaded', () => {
    window.DWI18n.init();
    window.DWMascot.init({
      // Tapping the mascot re-explains whichever view is on screen, so
      // the guide is reachable at every point in the flow.
      onClick: () => {
        if (!window.DWGuide) return;
        const view = document.querySelector('.view.active');
        const topic = view && view.id === 'view-result' ? 'result_ring' : 'checkin';
        window.DWGuide.explain(topic, { force: true });
      },
    });
    window.DWMusic.init();
    if (window.DWGuide) window.DWGuide.autoAttach();

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    }

    const canvas = document.getElementById('bgCanvas');
    if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

    wireAuthForms();
    wireOnboarding();
    wireWizard();
    wireCsvImport();
    wireResultActions();
    wireCsvSave();
    wireCsvHistory();
    wireSettings();

    document.addEventListener('dwai:langchange', () => {
      // The check-in form's own field titles. Re-labelled in place
      // rather than by rebuilding the wizard, because rebuilding would
      // throw away every answer typed so far - switching language
      // mid-questionnaire is exactly when someone would do it.
      $all('label[data-dw-field]').forEach((el) => {
        const translated = labelFor(el.dataset.dwField);
        if (translated) el.textContent = translated;
      });

      if (!state.lastResult) return;
      const el = $('#resultNarrative');
      if (el) el.textContent = narrativeSummary(state.lastResult);
      // Recommendation cards used to stay in whatever language was
      // active when the result was first rendered - switching language
      // updated the chrome around them but not the cards themselves.
      renderRecommendationCards(state.lastResult);
      // Same for the 7-day roadmap. The plan already holds all four
      // languages, so this re-renders from what is in hand rather than
      // asking the server for the same plan again.
      renderRoadmap(state.lastResult);
    });

    document.addEventListener('dwai:unauthorized', () => {
      showView('view-auth');
      window.DWToast.warning('Session expired — please log in again.');
    });

    // Must run before the isAuthed() check: a GitHub sign-in lands here
    // with the token in the query string, not yet in storage.
    consumeOAuthRedirect();

    if (window.DWApi.isAuthed()) {
      afterLogin();
    } else {
      showView('view-auth');
    }
  });
})();
