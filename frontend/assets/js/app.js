(function () {
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $all = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  const { GOAL_OPTIONS, PURPOSE_OPTIONS, SCHEDULE_OPTIONS } = window.DWOnboardingOptions;

  const state = {
    featureSchemaMap: {}, demoProfiles: null, account: null,
    wizardData: {}, stepIndex: 0, demoActive: false,
    onboard: { goal: null, purpose: null, schedule: null },
    lastPayload: null, lastResult: null,
  };

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
    $('#logoutBtn').classList.remove('hidden');
    $('#appNavRow').classList.remove('hidden');
    if (!state.account.onboarding_complete) {
      renderOnboarding();
      showView('view-onboarding');
    } else {
      await startWizard();
    }
  }

  async function startWizard() {
    resetWizard();
    await ensureSchemaLoaded();
    renderStep();
    showView('view-predict');
  }

  function wireAuthForms() {
    initAuthTabs();

    $('#loginForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      clearFieldErrors(form);
      const fd = new FormData(form);
      try {
        const res = await window.DWApi.login(fd.get('email'), fd.get('password'));
        window.DWApi.setToken(res.access_token);
        window.DWToast.success(window.DWI18n.t('toast_login_ok'));
        await afterLogin();
      } catch (err) {
        window.DWToast.error(err.fieldErrors ? window.DWI18n.t('toast_field_error') : (err.message || window.DWI18n.t('toast_login_fail')));
        window.DWMascot.react('error');
      }
    });

    $('#registerForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      clearFieldErrors(form);
      if (!$('#termsCheck').checked) {
        window.DWToast.warning(window.DWI18n.t('toast_terms_required'));
        return;
      }
      const fd = new FormData(form);
      try {
        const res = await window.DWApi.register(fd.get('email'), fd.get('password'), fd.get('display_name'));
        window.DWApi.setToken(res.access_token);
        window.DWToast.success(window.DWI18n.t('toast_register_ok'));
        await afterLogin();
      } catch (err) {
        if (err.fieldErrors) {
          Object.entries(err.fieldErrors).forEach(([k, v]) => markFieldError(form, k, v));
        }
        window.DWToast.error(err.message || window.DWI18n.t('toast_register_fail'));
        window.DWMascot.react('error');
      }
    });
  }

  // ===================== ONBOARDING =====================
  function buildOptionList(container, options, stateKey) {
    container.innerHTML = '';
    Object.entries(options).forEach(([label, value]) => {
      const el = document.createElement('div');
      el.className = 'onboard-option';
      el.textContent = label;
      el.addEventListener('click', () => {
        $all('.onboard-option', container).forEach((o) => o.classList.remove('selected'));
        el.classList.add('selected');
        state.onboard[stateKey] = value;
      });
      container.appendChild(el);
    });
  }

  function renderOnboarding() {
    const goal = localStorage.getItem('dwai_intake_goal');
    buildOptionList($('#goalOptions'), GOAL_OPTIONS, 'goal');
    buildOptionList($('#purposeOptions'), PURPOSE_OPTIONS, 'purpose');
    buildOptionList($('#scheduleOptions'), SCHEDULE_OPTIONS, 'schedule');
    if (goal) {
      const match = Object.values(GOAL_OPTIONS).includes(goal) ? goal : null;
      if (match) {
        state.onboard.goal = match;
        $all('.onboard-option', $('#goalOptions')).forEach((o) => {
          if (GOAL_OPTIONS[o.textContent] === match) o.classList.add('selected');
        });
      }
    }
  }

  function wireOnboarding() {
    $('#onboardSkip').addEventListener('click', () => startWizard());
    $('#onboardSave').addEventListener('click', async () => {
      try {
        await window.DWApi.saveOnboarding({
          primary_goal: state.onboard.goal || 'maintain_habits',
          main_use_purpose: state.onboard.purpose || 'mixed',
          schedule_type: state.onboard.schedule || 'standard_day',
          usual_sleep_time: '23:00',
          usual_wake_time: '07:00',
          preferred_effort: 'moderate',
          work_screen_required: false,
        });
        window.DWToast.success(window.DWI18n.t('toast_saved'));
      } catch (err) {
        window.DWToast.error(err.message);
      }
      await startWizard();
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
    label.textContent = def.label || name;
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
      def.choices.forEach((c) => {
        const opt = document.createElement('option');
        opt.value = String(c); opt.textContent = String(c);
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
    window.DWSchema.STEPS.forEach((s, i) => {
      const dot = document.createElement('div');
      dot.className = 'dot' + (i < state.stepIndex ? ' done' : i === state.stepIndex ? ' active' : '');
      wrap.appendChild(dot);
    });
  }

  function renderStep() {
    renderProgress();
    const step = window.DWSchema.STEPS[state.stepIndex];
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
    const isLast = state.stepIndex === window.DWSchema.STEPS.length - 1;
    $('#wizardNext').textContent = isLast ? window.DWI18n.t('predict_submit') : window.DWI18n.t('predict_next');
  }

  function resetWizard() {
    state.wizardData = { ...window.DWSchema.DEFAULTS };
    state.stepIndex = 0;
    state.demoActive = false;
  }

  function findStepForField(name) {
    return window.DWSchema.STEPS.findIndex((s) => s.fields.includes(name));
  }

  async function submitPrediction() {
    const payload = state.demoActive
      ? { ...state.wizardData }
      : window.DWSchema.applyCalendarDefaults(window.DWSchema.deriveFeatures(state.wizardData));
    state.lastPayload = payload;

    try {
      // The processing screen waits on the REAL request - it never
      // fabricates delay beyond its minimum presentation window.
      const result = await window.DWProcessing.run(
        window.DWApi.predict(payload, true), { flow: 'predict' }
      );
      localStorage.setItem('dwai_last_result', JSON.stringify(result));
      localStorage.setItem('dwai_last_payload', JSON.stringify(payload));
      // Show the view BEFORE rendering: the wave bars size themselves
      // from getBoundingClientRect(), which is 0x0 while the section is
      // still display:none (that left the confidence bar blank).
      showView('view-result');
      renderResult(result);

      window.DWApi.personaAssign(payload).then((p) => {
        if (p && p.available) {
          $('#personaLine').textContent = `${window.DWI18n.t('result_persona')}: ${p.persona_name}`;
          localStorage.setItem('dwai_last_persona', p.persona_name);
        }
      }).catch(() => {});
    } catch (err) {
      if (err.fieldErrors) {
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

  function wireWizard() {
    $('#wizardNext').addEventListener('click', () => {
      const isLast = state.stepIndex === window.DWSchema.STEPS.length - 1;
      if (isLast) { submitPrediction(); return; }
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
    const def = top && state.featureSchemaMap[top.feature];
    const topLabel = (def && def.label) || (top && top.feature) || '';
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
        great: `درجتك ${score} من 100 — أسبوع قوي.`,
        good: `درجتك ${score} من 100 — وضع جيد.`,
        borderline: `درجتك ${score} من 100 — في المنتصف تقريبًا.`,
        risk: `درجتك ${score} من 100. هذه منخفضة، والعامل الأكبر شيء يمكنك تغييره.`,
      },
      zh: {
        great: `你的分数是 ${score}/100 —— 表现很好的一周。`,
        good: `你的分数是 ${score}/100 —— 状态不错。`,
        borderline: `你的分数是 ${score}/100 —— 大致处于中间。`,
        risk: `你的分数是 ${score}/100。这个分数偏低，而最大的影响因素是你可以改变的。`,
      },
    };
    return ((T[lang] || T.en)[band] || '').trim();
  }

  function renderResult(result) {
    const score = Math.max(0, Math.min(100, result.regression_score ?? 0));

    state.lastResult = result;
    const summaryEl = $('#resultNarrative');
    if (summaryEl) summaryEl.textContent = narrativeSummary(result);

    // Ring is drawn like a pen stroke; the number counts up to the exact
    // same value the API returned (no rounding change vs. before).
    const ring = $('#scoreRing');
    const scoreColor = score >= 66 ? 'var(--accent-success)' : score >= 40 ? 'var(--accent-amber)' : 'var(--accent-danger)';
    ring.style.stroke = scoreColor;
    window.DWMotion.drawRing(ring, score / 100);
    window.DWMotion.countUp($('#scoreNum'), score, { decimals: 0, duration: 1400 });

    const badge = $('#classBadge');
    badge.textContent = result.prediction;
    badge.className = 'badge ' + classBadgeClass(result.prediction);

    // Confidence as a wave-filling bar.
    const confBar = $('#confidenceBar');
    confBar.dataset.fill = String((result.confidence_percent || 0) / 100);
    window.DWMotion.waveFill(confBar, (result.confidence_percent || 0) / 100, { delay: 200 });
    window.DWMotion.countUp($('#confidenceNum'), result.confidence_percent || 0, {
      decimals: 0, duration: 1200, format: (v) => `${Math.round(v)}%`,
    });
    $('#personaLine').textContent = '';

    const u = result.uncertainty;
    const uNote = $('#uncertaintyNote');
    if (u && u.available) {
      let text = u.explanation || '';
      if (u.regression_lower != null && u.regression_upper != null) {
        text += ` — likely range ${Math.round(u.regression_lower)}–${Math.round(u.regression_upper)}.`;
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
      const def = state.featureSchemaMap[f.feature];
      const row = document.createElement('div');
      row.className = 'shap-bar-row';
      const pct = Math.min(100, Math.abs(f.score || 0));
      const isHarmful = f.direction === 'decrease';
      row.innerHTML = `
        <div class="name">${(def && def.label) || f.feature}</div>
        <div class="shap-bar-track">
          <div class="wave-bar shap-wave ${f.direction}" data-fill="${pct / 100}"></div>
        </div>
        <div class="shap-dir ${f.direction}" title="${isHarmful ? 'pulling score down' : 'pushing score up'}">${isHarmful ? '↓' : '↑'}</div>
      `;
      shapWrap.appendChild(row);
    });
    window.DWMotion.waveFillOnView(shapWrap, '.shap-wave', { gap: 130 });

    // ---- Recommendation cards (staggered entrance) ----
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
      card.innerHTML = `
        <div class="rec-head">
          <span class="rec-title">${r.icon || '💡'} ${r.title}</span>
          <span class="badge badge--priority-${prio}">${r.priority}</span>
        </div>
        <p class="rec-desc">${r.description}</p>
        <p class="rec-action">➜ ${r.action}</p>
        <div class="rec-meta"><strong>${window.DWI18n.t('rec_success_label')}:</strong> ${r.success_metric || '—'}<br/><span class="rec-safety">${r.safety_note || ''}</span></div>
      `;
      recWrap.appendChild(card);
    });
    window.DWMotion.stagger(recWrap.children, { gap: 110 });

    // Expression + tone come from the real score, using the same bands
    // the colour ring uses.
    window.DWMascot.reactToScore(score);
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
    const modal = $('#settingsModal');
    $('#settingsBtn').addEventListener('click', () => {
      $('#settingsThemeSwitch').checked = window.DWTheme.get() === 'dark';
      $('#settingsMotionSwitch').checked = window.DWMotion.prefersReduced();
      modal.classList.add('show');
    });
    $('#settingsCloseBtn').addEventListener('click', () => modal.classList.remove('show'));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });

    $('#settingsThemeSwitch').addEventListener('change', (e) => {
      window.DWTheme.apply(e.target.checked ? 'dark' : 'light');
      localStorage.setItem('dwai_theme', e.target.checked ? 'dark' : 'light');
    });
    $('#settingsMusicSwitch').addEventListener('change', (e) => {
      e.target.checked ? window.DWMusic.play() : window.DWMusic.pause();
    });
    $('#settingsMotionSwitch').checked = window.DWMotion.prefersReduced();
    $('#settingsMotionSwitch').addEventListener('change', (e) => {
      window.DWMotion.setReduced(e.target.checked);
    });
    $('#settingsLogoutBtn').addEventListener('click', doLogout);
    $('#logoutBtn').addEventListener('click', doLogout);
  }

  function doLogout() {
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
    window.DWMascot.init();
    window.DWMusic.init();

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    }

    const canvas = document.getElementById('bgCanvas');
    if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

    wireAuthForms();
    wireOnboarding();
    wireWizard();
    wireResultActions();
    wireSettings();

    document.addEventListener('dwai:langchange', () => {
      if (!state.lastResult) return;
      const el = $('#resultNarrative');
      if (el) el.textContent = narrativeSummary(state.lastResult);
    });

    document.addEventListener('dwai:unauthorized', () => {
      showView('view-auth');
      window.DWToast.warning('Session expired — please log in again.');
    });

    if (window.DWApi.isAuthed()) {
      afterLogin();
    } else {
      showView('view-auth');
    }
  });
})();
