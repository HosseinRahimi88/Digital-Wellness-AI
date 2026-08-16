/* Weekly Plan page controller: this-week vs. previous-week summaries
   (GET /history/weeks/*) plus the rule-based 7-day improvement plan
   (POST /plan) with persisted per-task checkmarks (PUT /plan/tasks). */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('weekly');
  if (!account) return;

  /* Row labels are built here at render time, so they need the same
     four-language treatment as the static [data-i18n] markup - they used
     to be hardcoded English and stayed English in every language. */
  const P = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  if (window.DWWeeklyCard) window.DWWeeklyCard.init('weeklyCardCanvas', 'weeklyCardDownloadBtn');

  function renderWeekRows(container, week) {
    container.innerHTML = '';
    if (!week) {
      container.innerHTML = `<p class="muted">${P({ en: 'No entries yet.', fa: 'هنوز هیچ ثبتی نیست.', ar: 'لا توجد إدخالات بعد.', zh: '暂无记录。' })}</p>`;
      return;
    }
    const rows = [
      [P({ en: 'Avg wellness score', fa: 'میانگین امتیاز سلامت', ar: 'متوسط نتيجة العافية', zh: '平均健康分数' }), week.avg_health_score],
      [P({ en: 'Avg screen time (min)', fa: 'میانگین زمان صفحه (دقیقه)', ar: 'متوسط وقت الشاشة (دقيقة)', zh: '平均屏幕时间（分钟）' }), week.avg_total_screen_min],
      [P({ en: 'Avg sleep (hrs)', fa: 'میانگین خواب (ساعت)', ar: 'متوسط النوم (ساعة)', zh: '平均睡眠（小时）' }), week.avg_sleep_hours],
      [P({ en: 'Avg focus (0-100)', fa: 'میانگین تمرکز (۰-۱۰۰)', ar: 'متوسط التركيز (0-100)', zh: '平均专注度（0-100）' }), week.avg_focus_0_100],
      [P({ en: 'Avg social media (min)', fa: 'میانگین شبکه اجتماعی (دقیقه)', ar: 'متوسط وسائل التواصل (دقيقة)', zh: '平均社交媒体（分钟）' }), week.avg_social_min],
      [P({ en: 'Avg stress (0-10)', fa: 'میانگین استرس (۰-۱۰)', ar: 'متوسط التوتر (0-10)', zh: '平均压力（0-10）' }), week.avg_stress_0_10],
    ];
    rows.forEach(([label, val]) => {
      const div = document.createElement('div');
      div.className = 'metric-row';
      div.innerHTML = `<span class="name">${label}</span><span class="value">${val != null ? Math.round(val * 10) / 10 : '—'}</span>`;
      container.appendChild(div);
    });
    const meta = document.createElement('p');
    meta.className = 'muted'; meta.style.fontSize = '.76rem'; meta.style.marginTop = '8px';
    meta.textContent = `${week.num_entries} ${P({ en: 'check-in(s)', fa: 'بررسی', ar: 'تسجيل', zh: '次记录' })}, ${week.start_date} → ${week.end_date}`;
    container.appendChild(meta);
  }

  // Kept so the row LABELS (built from P(), not server text) can be
  // rebuilt in the new language on dwai:langchange without re-fetching -
  // the numbers never change with language, only the words next to them.
  let currentWeek = null;
  let previousWeek = null;
  try {
    currentWeek = await window.DWApi.currentWeek();
  } catch (e) { /* renderWeekRows(null) below shows the empty state */ }
  try {
    previousWeek = await window.DWApi.previousWeek();
  } catch (e) { /* renderWeekRows(null) below shows the empty state */ }

  function renderWeekSummaries() {
    renderWeekRows(document.getElementById('weekCurrentRows'), currentWeek);
    renderWeekRows(document.getElementById('weekPreviousRows'), previousWeek);
  }
  renderWeekSummaries();
  document.addEventListener('dwai:langchange', renderWeekSummaries);

  // ---- 7-day plan ----
  let lastResult, lastPayload;
  try {
    lastResult = JSON.parse(localStorage.getItem('dwai_last_result') || 'null');
    lastPayload = JSON.parse(localStorage.getItem('dwai_last_payload') || 'null');
  } catch (e) {}

  /* localStorage is the fast path, not the source of truth. This page
     used to stop here, so a user who signed in on a second device - or
     cleared their browser - was told "No plan yet" while the server was
     holding a fortnight of their check-ins and a frozen plan for the
     week. Everything this page now shows (the locked days, the score
     band, the out-of-band question) lived behind that empty state too.
     Verified in a real browser: a fresh profile with a real account and
     real server history rendered zero day cards.
     So when the browser has nothing, ask the server for the most recent
     stored day and rebuild from that. */
  if (!lastResult || !lastPayload) {
    try {
      const page = await window.DWApi.history(1, 1);
      const newest = ((page && page.items) || [])[0];
      if (newest && newest.date) {
        const detail = await window.DWApi.historyDetail(newest.date);
        if (detail && detail.result && detail.inputs) {
          lastResult = detail.result;
          lastPayload = detail.inputs;
        }
      }
    } catch (e) {
      // Days recorded before result snapshots existed cannot be
      // rebuilt (404 history_detail_unavailable). The empty state
      // below is then the honest answer.
    }
  }

  if (!lastResult || !lastPayload) {
    document.getElementById('planEmpty').classList.remove('hidden');
    return;
  }
  document.getElementById('planContent').classList.remove('hidden');

  let plan;
  try {
    plan = await window.DWApi.generatePlan({
      health_class: lastResult.prediction,
      wellness_score: lastResult.regression_score,
      persona: localStorage.getItem('dwai_last_persona') || null,
      user_data: lastPayload,
    });
  } catch (e) {
    window.DWToast.error(e.message);
    return;
  }

  // ImprovementPlanService's intro/tips are written for Streamlit's
  // st.markdown() (uses **bold**) - converted to <strong> here rather
  // than left as literal asterisks, since this is server-controlled
  // recommendation text (not user input), safe to render as HTML.
  const mdBoldToHtml = (text) => (text || '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  /* The whole plan now arrives translated: the exercises always did, and
     the wrapper text (intro, theme, tip, tier and day labels) does too.
     This reads the reader's language and falls back to the flat English
     field for an older response - it used to render the English fields
     unconditionally, so a Persian reader got translated tasks sitting
     under an English heading with an English tip below them. */
  const lang = () => (window.DWI18n && window.DWI18n.get ? window.DWI18n.get() : 'en');
  const serverText = (payload, part, fallback) => {
    const table = ((payload && payload.text_i18n) || {})[part];
    if (table) {
      const own = table[lang()];
      if (own) return own;
      if (table.en) return table.en;
    }
    return fallback || '';
  };

  /* `plan` already carries every language in text_i18n - generatePlan()
     is not called again here. Re-running this render is enough to pick
     up a language switch, and re-fetching would be wasted work and an
     extra place for the network call to fail.

     This used to run once, inline, at the bottom of the DOMContentLoaded
     handler. Nothing on this page listened for dwai:langchange, so
     switching language after the plan had already rendered left the
     intro, the day cards and every task showing whatever language was
     active at fetch time - the settings-panel switcher updated the
     static chrome around the plan but never the plan itself. */
  function renderPlanBody() {
    document.getElementById('planIntro').innerHTML =
      mdBoldToHtml(serverText(plan, 'intro', plan.intro));

    const chips = document.getElementById('planFocusChips');
    chips.innerHTML = '';
    (plan.focus_areas || []).forEach((area, i) => {
      const chip = document.createElement('span');
      chip.className = 'chip-option selected';
      chip.style.cursor = 'default';
      // focus_areas_i18n is index-aligned with focus_areas by contract, so
      // the chip cannot end up labelled with a different area than it is.
      const translated = (plan.focus_areas_i18n || [])[i];
      chip.textContent = (translated && (translated[lang()] || translated.en)) || area;
      chips.appendChild(chip);
    });

    const daysWrap = document.getElementById('planDays');
    daysWrap.innerHTML = '';
    plan.days.forEach((day) => {
      const card = document.createElement('div');
      // The week runs in order: day N+1 opens once day N is fully
      // ticked. `locked` comes from the server, which also refuses the
      // tick - shown here so a locked day reads as locked instead of
      // letting someone tap it and be told no.
      card.className = 'day-card' + (day.locked ? ' day-card--locked' : '');
      const dayLabel = serverText(day, 'day_label', day.day_label);
      const theme = serverText(day, 'theme', day.theme);
      const tier = serverText(day, 'tier_label', day.tier_label);
      const tip = serverText(day, 'tip', day.tip);
      card.innerHTML = `
        <div class="day-card-head"><span class="icon">${day.icon}</span><div><strong>${dayLabel}</strong><div class="muted" style="font-size:.82rem;">${theme}${tier ? ` <span class="plan-tier-badge">${tier}</span>` : ''}</div></div></div>
        <div class="tasks"></div>
        <div class="day-tip">💡 ${mdBoldToHtml(tip)}</div>
      `;
      if (day.locked) {
        // Says WHY, and which day to finish. "Locked" on its own reads
        // as a fault in the app rather than as the next step.
        const note = document.createElement('p');
        note.className = 'day-locked-note';
        note.textContent = window.DWI18n.t('plan_day_locked_note')
          .replace('{day}', plan.unlocked_through);
        card.querySelector('.day-card-head').insertAdjacentElement('afterend', note);
      }
      const tasksWrap = card.querySelector('.tasks');
      day.tasks.forEach((task) => {
        const row = document.createElement('div');
        row.className = 'task-row' + (task.completed ? ' done' : '');
        const id = `task-${day.day_number}-${task.task_index}`;
        /* The exercises have carried four languages since they were
           composed; this was still printing the English one. */
        const taskText = (task.text_i18n && (task.text_i18n[lang()] || task.text_i18n.en)) || task.text;
        row.innerHTML = `<input type="checkbox" id="${id}" ${task.completed ? 'checked' : ''} ${day.locked ? 'disabled' : ''}/><label for="${id}"></label>`;
        // The exercise text is server-composed but carries the user's own
        // numbers, so it goes in as text rather than markup.
        row.querySelector('label').textContent = taskText;
        row.querySelector('input').addEventListener('change', async (e) => {
          row.classList.toggle('done', e.target.checked);
          try {
            await window.DWApi.updatePlanTask(day.day_number, task.task_index, e.target.checked);
            if (e.target.checked) window.DWMascot.react('task_done');
            // Finishing the last task of a day opens the next one, and
            // un-ticking closes it again. Only the server knows which,
            // so the page re-reads rather than deciding for itself.
            const refreshed = await window.DWApi.generatePlan({
              health_class: lastResult.prediction,
              wellness_score: lastResult.regression_score,
              persona: localStorage.getItem('dwai_last_persona') || null,
              user_data: lastPayload,
            });
            if (refreshed.unlocked_through !== plan.unlocked_through) {
              plan = refreshed;
              renderPlanBody();
            }
          } catch (err) {
            // Roll the box back: the server refused, so leaving it
            // ticked would show the user a completion that does not
            // exist anywhere but on their screen.
            e.target.checked = !e.target.checked;
            row.classList.toggle('done', e.target.checked);
            if (err.code === 'plan_day_locked') {
              window.DWToast.error(window.DWI18n.t('plan_day_locked_toast')
                .replace('{day}', plan.unlocked_through));
            } else {
              window.DWToast.error(err.message);
            }
          }
        });
        tasksWrap.appendChild(row);
      });
      daysWrap.appendChild(card);
    });
  }

  renderPlanBody();
  document.addEventListener('dwai:langchange', renderPlanBody);

  /* "That day sits outside your week's range." Asked here as well as on
     the result screen, because this is where the answer lands: choosing
     "count it" rewrites the rest of the plan shown directly below. The
     module itself decides whether there is anything to ask - it returns
     without rendering on an ordinary day. */
  if (window.DWBandDecision) {
    window.DWBandDecision.maybeAsk(
      document.getElementById('bandDecisionMount'),
      (decision) => {
        // Counting the day rebuilt the rest of the week server-side, so
        // the plan on screen is now the OLD one. Re-read it rather than
        // patching it here: the server is the only thing that knows
        // which days it kept.
        if (decision !== 'counted') return;
        window.DWApi.generatePlan({
          health_class: lastResult.prediction,
          wellness_score: lastResult.regression_score,
          persona: localStorage.getItem('dwai_last_persona') || null,
          user_data: lastPayload,
        }).then((fresh) => {
          plan = fresh;
          renderPlanBody();
        }).catch(() => { /* the next page load reads it fresh anyway */ });
      },
    );
  }
});
