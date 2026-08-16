/* What-if page controller: lets the user sweep one input field across
   its range (POST /whatif/sweep) or goal-seek a target score
   (POST /whatif/goal-seek), both against the real trained model. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('whatif');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  let payload;
  try {
    payload = JSON.parse(localStorage.getItem('dwai_last_payload') || 'null');
  } catch (e) {}

  /* The page used to require `dwai_last_payload` - a value only this
     browser's own last check-in writes - and showed "nothing to
     simulate" without it. An account with fifteen recorded days opened
     on a second device therefore had nothing to simulate, which was
     never true. Now that the day picker reads the server's history, the
     history is a perfectly good starting point: fall back to the most
     recent recorded day and only give up when there is no day at all. */
  let historySnapshots = [];
  try {
    const res = await window.DWApi.historySnapshots(60);
    historySnapshots = ((res && res.entries) || []).filter((e) => e && e.inputs);
    if (!payload && historySnapshots.length) {
      payload = historySnapshots[historySnapshots.length - 1].inputs;
    }
  } catch (e) {
    // No history call, no fallback - the localStorage payload (if any)
    // still stands on its own.
  }

  if (!payload) {
    document.getElementById('whatifEmpty').classList.remove('hidden');
    return;
  }
  document.getElementById('whatifContent').classList.remove('hidden');

  let schemaList = [];
  try {
    schemaList = await window.DWApi.featureSchema();
  } catch (e) {
    window.DWToast.error(e.message);
    return;
  }

  const numericFields = schemaList.filter((f) => (f.dtype === 'int' || f.dtype === 'float') && !f.choices);
  const select = document.getElementById('sweepField');
  // `f.label` is the server's English schema label. DWCoachLabels holds
  // the same field names in all four languages and is what the Coach and
  // the SHAP panels already read, so the simulator names a field the same
  // way the rest of the app does instead of falling back to English.
  function fieldLabel(f) {
    const table = ((window.DWCoachLabels || {}).__raw || {})[f.name];
    const lang = (window.DWI18n && window.DWI18n.get) ? window.DWI18n.get() : 'en';
    return (table && (table[lang] || table.en)) || f.label || f.name;
  }

  numericFields.forEach((f) => {
    const opt = document.createElement('option');
    opt.value = f.name; opt.textContent = fieldLabel(f);
    select.appendChild(opt);
  });
  const preferredDefault = numericFields.find((f) => f.name === 'sleep_hours') || numericFields[0];
  if (preferredDefault) select.value = preferredDefault.name;

  /* ---- which day to simulate ----------------------------------------
     The simulator was pinned to `dwai_last_payload` - the most recent
     check-in - with no way to say otherwise, so a question about a heavy
     Saturday could only ever be asked using a Tuesday's numbers.
     /history/snapshots already returns every recorded day's own answers
     in one call, so the whole picker is a select over that response;
     choosing a day swaps `payload`, which is the only thing the sweep
     and the goal-seek read. Falls back to the last check-in when the
     history call fails or the account has only the one day. */
  const dayList = document.getElementById('whatifDay');
  const dayNote = document.getElementById('whatifDayNote');
  const fieldNow = document.getElementById('fieldNow');
  const targetPct = document.getElementById('fieldTargetPct');
  const targetValue = document.getElementById('fieldTargetValue');
  let snapshots = [];

  function currentFieldValue() {
    const raw = payload ? payload[select.value] : null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }

  /* This field on the chosen day, and what the requested percentage of
     it works out to. Shown rather than left as arithmetic for the
     reader: "60% of my social time" is the question people actually
     ask, and the minutes it lands on is what they have to act on. */
  function renderFieldTarget() {
    const now = currentFieldValue();
    if (now === null) {
      fieldNow.value = '—';
      targetValue.value = '—';
      return;
    }
    fieldNow.value = Math.round(now * 100) / 100;
    const pct = Number(targetPct.value);
    targetValue.value = Number.isFinite(pct)
      ? Math.round(now * (pct / 100) * 100) / 100
      : '—';
  }

  function describeDay(entry) {
    const score = entry.health_score == null
      ? '' : ` · ${Math.round(entry.health_score)}`;
    return `${entry.date}${entry.day_of_week ? ' · ' + entry.day_of_week : ''}${score}`;
  }

  async function buildDayPicker() {
    snapshots = historySnapshots;
    if (snapshots.length < 2) {
      // One day is the day the page already starts from.
      dayList.closest('.card').classList.add('hidden');
      return;
    }
    // Newest first: the day someone wants to ask about is usually recent.
    snapshots.slice().reverse().forEach((entry) => {
      const opt = document.createElement('option');
      opt.value = entry.date;
      opt.textContent = describeDay(entry);
      dayList.appendChild(opt);
    });
    dayList.value = snapshots[snapshots.length - 1].date;
    applyDay(dayList.value);

    dayList.addEventListener('change', () => applyDay(dayList.value));
  }

  function applyDay(date) {
    const entry = snapshots.find((e) => e.date === date);
    if (!entry) return;
    payload = entry.inputs;
    renderFieldTarget();
  }

  select.addEventListener('change', renderFieldTarget);
  targetPct.addEventListener('input', renderFieldTarget);
  renderFieldTarget();
  await buildDayPicker();

  const sweepCanvas = document.getElementById('sweepChart');

  /* Both results below used to be built from hardcoded English string
     literals, so this page stayed English no matter the language.
     They are now rendered from i18n keys, and - because both are built
     once from a fetched response rather than from `data-i18n` markup -
     re-rendered on `dwai:langchange` from the cached response, exactly
     like the weekly plan and the insight cards. Switching language
     after running a sweep must not leave the old language on screen,
     and must not silently re-POST to the model either. */
  const t = (key) => (window.DWI18n && window.DWI18n.t ? window.DWI18n.t(key) : key);

  // The server returns class names in English ("Healthy" / "At Risk");
  // these are the display forms, keyed off that stable server value.
  const CLASS_KEY = {
    healthy: 'cls_healthy',
    moderate: 'cls_moderate',
    'at risk': 'cls_at_risk',
    at_risk: 'cls_at_risk',
  };
  function className(raw) {
    const key = CLASS_KEY[String(raw || '').trim().toLowerCase()];
    return key ? t(key) : String(raw || '—');
  }

  let lastSweepClasses = null;
  let lastGoalSeek = null;

  function renderSweepNote() {
    const note = document.getElementById('sweepNote');
    if (!note || !lastSweepClasses) return;
    const names = lastSweepClasses.map(className);
    note.textContent = names.length > 1
      ? t('whatif_class_changes').replace('{classes}', names.join(' → '))
      : t('whatif_class_stays').replace('{cls}', names[0] || '—');
  }

  function renderGoalSeek() {
    const wrap = document.getElementById('goalSeekResult');
    if (!wrap || !lastGoalSeek) return;
    const res = lastGoalSeek;
    if (!res.available) {
      wrap.innerHTML = `<p class="muted">${t('whatif_goal_none')}</p>`;
      return;
    }
    const n = (v) => Math.round(v * 100) / 100;
    wrap.innerHTML = `
      <div class="metric-row"><span class="name">${t('whatif_best_value')}</span><span class="value">${n(res.best_value)}</span></div>
      <div class="metric-row"><span class="name">${t('whatif_result_score')}</span><span class="value">${n(res.best_score)}</span></div>
      <div class="metric-row"><span class="name">${t('whatif_distance')}</span><span class="value">${n(res.distance)}</span></div>
    `;
  }

  // i18n.js dispatches this on `document` with no `bubbles`, so it never
  // reaches a listener on `window` - every other page listens here too.
  document.addEventListener('dwai:langchange', () => {
    // Re-label the field dropdown too - its option text comes from
    // DWCoachLabels, which is language-dependent.
    const keep = select.value;
    numericFields.forEach((f, i) => {
      if (select.options[i]) select.options[i].textContent = fieldLabel(f);
    });
    select.value = keep;
    renderSweepNote();
    renderGoalSeek();
  });

  async function runSweep() {
    const field = select.value;
    document.getElementById('runSweepBtn').disabled = true;
    try {
      const res = await window.DWApi.whatifSweep(payload, field, 9);
      const values = res.points.map((p) => p.score ?? 0);
      const labels = res.points.map((p) => Math.round(p.value * 10) / 10);
      window.DWCharts.drawLineChart(sweepCanvas, values, labels, { minFloor: 0, maxCeil: 100 });
      const distinctClasses = [...new Set(res.points.map((p) => p.prediction).filter(Boolean))];
      lastSweepClasses = distinctClasses;
      renderSweepNote();
    } catch (e) {
      window.DWToast.error(e.message);
    } finally {
      document.getElementById('runSweepBtn').disabled = false;
    }
  }

  document.getElementById('runSweepBtn').addEventListener('click', runSweep);
  runSweep();

  document.getElementById('runGoalSeekBtn').addEventListener('click', async () => {
    const field = select.value;
    const target = parseFloat(document.getElementById('goalTarget').value) || 80;
    const btn = document.getElementById('runGoalSeekBtn');
    btn.disabled = true;
    try {
      const res = await window.DWApi.whatifGoalSeek(payload, field, target, 15);
      lastGoalSeek = res;
      renderGoalSeek();
      if (res.available) window.DWMascot.react('neutral');
    } catch (e) {
      window.DWToast.error(e.message);
    } finally {
      btn.disabled = false;
    }
  });
});
