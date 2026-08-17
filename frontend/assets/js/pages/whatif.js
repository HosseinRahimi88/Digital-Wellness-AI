/* What-if page controller: lets the user sweep one input field across
   its range (POST /whatif/sweep) or goal-seek a target score
   (POST /whatif/goal-seek), both against the real trained model. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('whatif');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  let payload;
  // Through DWLastResult, not straight out of localStorage: the answers
  // and the result they produced are a pair, and a check-in the server
  // did not record ("I'm only testing this") must not become the day
  // the simulator reasons about. See DWLastResult.payload().
  try {
    payload = window.DWLastResult.payload();
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

  /* Only fields the model actually reads FROM THE USER.
     `f.derived` is the server's own measurement (see
     api/routers/schema.py) of which fields derive_features() computes
     and therefore overwrites. Thirteen of the forty-two were offered
     here regardless - total screen time, every ratio, every density,
     fragmentation, dependence - and sweeping any of them set a value
     that derivation replaced a line later, so the chart came back
     perfectly flat across the entire range. Nothing errored, which
     made it read as a finding about the user rather than a field that
     cannot be swept at all. Total screen time was the worst of them:
     the most obvious thing to reach for on this page, and the one
     guaranteed to say nothing. It moves when the five category minutes
     move, and those are still here. */
  /* And the ones that are not a habit at all. A sweep asks "what if I
     did this differently tomorrow", so the list has to be things a
     person can decide. These are not:

       day_index             which day of the year it is
       screen_ewma_baseline  a rolling average OF the user's own past
       age                   not a decision, and sweeping it produced a
                             0.37-point wobble presented as advice

     Left in, the first two swept perfectly flat across their whole
     range - an empty chart with no explanation - and the third invited
     "be 87" as a wellness strategy. */
  const NOT_A_HABIT = new Set(['day_index', 'screen_ewma_baseline', 'age']);
  const numericFields = schemaList.filter(
    (f) => (f.dtype === 'int' || f.dtype === 'float') && !f.choices
      && !f.derived && !NOT_A_HABIT.has(f.name)
  );
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

  /* Declared here, above the first renderer that reads them, rather
     than beside the result blocks further down: `const` bindings are in
     the temporal dead zone until their line runs, and renderFieldTarget
     is called during setup. */
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
      renderPctAnswer(null);
      return;
    }
    fieldNow.value = Math.round(now * 100) / 100;
    const pct = Number(targetPct.value);
    targetValue.value = Number.isFinite(pct)
      ? Math.round(now * (pct / 100) * 100) / 100
      : '—';
    renderPctAnswer(null);
  }

  /* ---- and what that percentage actually SCORES ---------------------
     The three boxes above were arithmetic and nothing else: type 60,
     watch a number appear, and no part of the page ever used it. The
     question the control poses - "what if I cut this to 60%?" - was
     never answered, by the sweep or by anything else. It is answered
     here, with one real prediction at exactly that value, on the same
     model every other number on this page comes from. */
  const pctAnswer = document.getElementById('fieldTargetAnswer');
  const pctRunBtn = document.getElementById('runFieldTargetBtn');
  let lastPctAnswer = null;

  function renderPctAnswer(state) {
    if (state !== undefined) lastPctAnswer = state;
    if (!pctAnswer) return;
    if (!lastPctAnswer) { pctAnswer.textContent = ''; return; }
    const { value, score, base, cls } = lastPctAnswer;
    const delta = Math.round((score - base) * 10) / 10;
    const key = delta > 0.05 ? 'whatif_pct_up' : (delta < -0.05 ? 'whatif_pct_down' : 'whatif_pct_same');
    pctAnswer.textContent = t(key)
      .replace('{value}', Math.round(value * 100) / 100)
      .replace('{score}', Math.round(score * 10) / 10)
      .replace('{delta}', Math.abs(delta))
      .replace('{cls}', className(cls));
  }

  async function runFieldTarget() {
    const now = currentFieldValue();
    const pct = Number(targetPct.value);
    if (now === null || !Number.isFinite(pct)) return;

    // Held inside the field's own schema bounds, or the server refuses
    // the day and the reader gets a validation error for typing 300%.
    const spec = numericFields.find((f) => f.name === select.value) || {};
    let value = now * (pct / 100);
    if (spec.minimum !== null && spec.minimum !== undefined) value = Math.max(value, spec.minimum);
    if (spec.maximum !== null && spec.maximum !== undefined) value = Math.min(value, spec.maximum);

    if (pctRunBtn) pctRunBtn.disabled = true;
    try {
      /* Two real predictions: this day as it stands, and this day with
         the one field moved. `persist: false` - the simulator asks
         hypotheticals and must never write one into the user's history
         or into what the Coach reads back. */
      const [changed, base] = await Promise.all([
        window.DWApi.predict({ ...payload, [select.value]: value }, false, false),
        window.DWApi.predict({ ...payload }, false, false),
      ]);
      renderPctAnswer({
        value,
        score: changed.regression_score,
        base: base.regression_score,
        cls: changed.prediction,
      });
    } catch (e) {
      window.DWToast.error(e.message);
    } finally {
      if (pctRunBtn) pctRunBtn.disabled = false;
    }
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
  if (pctRunBtn) pctRunBtn.addEventListener('click', runFieldTarget);
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
     and must not silently re-POST to the model either.
     (`t` and `className` are declared further up - see the note there.) */

  let lastSweepClasses = null;
  let lastSweepSpread = null;
  let lastGoalSeek = null;

  function renderSweepNote() {
    const note = document.getElementById('sweepNote');
    if (!note || !lastSweepClasses) return;
    const names = lastSweepClasses.map(className);
    const classLine = names.length > 1
      ? t('whatif_class_changes').replace('{classes}', names.join(' → '))
      : t('whatif_class_stays').replace('{cls}', names[0] || '—');
    /* How far the score actually travelled. Without it, a 0.2-point
       wobble and a 20-point swing read identically - both are "the
       class stays Healthy" - and the reader has no way to tell a lever
       that matters from one that does not. */
    const spreadLine = lastSweepSpread === null ? ''
      : ' ' + (lastSweepSpread < 1
        ? t('whatif_spread_flat')
        : t('whatif_spread').replace('{spread}', lastSweepSpread));
    note.textContent = classLine + spreadLine;
  }

  function renderGoalSeek() {
    const wrap = document.getElementById('goalSeekResult');
    if (!wrap || !lastGoalSeek) return;
    const res = lastGoalSeek;
    if (!res.available) {
      wrap.innerHTML = `<p class="muted">${t('whatif_goal_none')}</p>`;
      return;
    }
    const n = (v) => (v === null || v === undefined ? '—' : Math.round(v * 100) / 100);
    const fieldName = fieldLabel(numericFields.find((f) => f.name === res.field) || { name: res.field });

    /* Three outcomes, and the reader is told which one they got.
       This block used to print "Best value found: <number>" for all of
       them, including the case where the target was never reached - and
       because the old search minimised |score - target| in EITHER
       direction, that number was routinely the most harmful value in
       the range: 0 hours of sleep, 10/10 stress, 0 minutes of exercise.
       See services/insight/advanced_whatif_service.py's goal_seek. */
    if (res.already_there) {
      wrap.innerHTML = `
        <p class="whatif-verdict whatif-verdict--good">${
          t('whatif_goal_already')
            .replace('{score}', n(res.current_score))
            .replace('{target}', n(res.target_score))
        }</p>
        <div class="metric-row"><span class="name">${t('whatif_current_value').replace('{field}', fieldName)}</span><span class="value">${n(res.current_value)}</span></div>
      `;
      return;
    }

    if (!res.reached) {
      wrap.innerHTML = `
        <p class="whatif-verdict whatif-verdict--warn">${
          t('whatif_goal_unreachable')
            .replace('{field}', fieldName)
            .replace('{target}', n(res.target_score))
        }</p>
        <div class="metric-row"><span class="name">${t('whatif_best_possible')}</span><span class="value">${n(res.best_score)}</span></div>
        <div class="metric-row"><span class="name">${t('whatif_best_possible_at').replace('{field}', fieldName)}</span><span class="value">${n(res.best_value)}</span></div>
        <div class="metric-row"><span class="name">${t('whatif_shortfall')}</span><span class="value">${n(res.distance)}</span></div>
      `;
      return;
    }

    wrap.innerHTML = `
      <p class="whatif-verdict whatif-verdict--good">${
        t('whatif_goal_reached')
          .replace('{field}', fieldName)
          .replace('{value}', n(res.best_value))
          .replace('{score}', n(res.best_score))
      }</p>
      <div class="metric-row"><span class="name">${t('whatif_current_value').replace('{field}', fieldName)}</span><span class="value">${n(res.current_value)}</span></div>
      <div class="metric-row"><span class="name">${t('whatif_needed_value')}</span><span class="value">${n(res.best_value)}</span></div>
      <div class="metric-row"><span class="name">${t('whatif_result_score')}</span><span class="value">${n(res.best_score)}</span></div>
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
    renderPctAnswer();
  });

  async function runSweep() {
    const field = select.value;
    document.getElementById('runSweepBtn').disabled = true;
    try {
      const res = await window.DWApi.whatifSweep(payload, field, 9);
      /* A point the model could not score is DROPPED, not drawn as
         zero. `p.score ?? 0` put a real-looking 0 on the chart for
         every unscoreable day: sweeping night-screen minutes past the
         day's own screen total made night_ratio exceed 1.0, the
         validator refused those days, and the line fell off a cliff to
         zero at 225 minutes. Nothing about that cliff came from the
         model - it was the chart inventing the one number that says
         "catastrophe" out of the server saying "no answer".

         The server-side range cap now keeps the sweep inside days that
         can exist, so gaps should be rare; this makes the chart honest
         when one happens anyway rather than relying on that. */
      const scored = res.points.filter((p) => p.score !== null && p.score !== undefined);
      const values = scored.map((p) => p.score);
      const labels = scored.map((p) => Math.round(p.value * 10) / 10);
      window.DWCharts.drawLineChart(sweepCanvas, values, labels, {
        minFloor: 0, maxCeil: 100, emptyText: t('whatif_no_points'),
      });
      const distinctClasses = [...new Set(scored.map((p) => p.prediction).filter(Boolean))];
      lastSweepClasses = distinctClasses;
      lastSweepSpread = values.length
        ? Math.round((Math.max(...values) - Math.min(...values)) * 10) / 10
        : null;
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
