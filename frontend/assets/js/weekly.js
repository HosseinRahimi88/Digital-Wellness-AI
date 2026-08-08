/* Weekly Plan page controller: this-week vs. previous-week summaries
   (GET /history/weeks/*) plus the rule-based 7-day improvement plan
   (POST /plan) with persisted per-task checkmarks (PUT /plan/tasks). */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('weekly');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  if (window.DWWeeklyCard) window.DWWeeklyCard.init('weeklyCardCanvas', 'weeklyCardDownloadBtn');

  function renderWeekRows(container, week) {
    container.innerHTML = '';
    if (!week) {
      container.innerHTML = '<p class="muted">No entries yet.</p>';
      return;
    }
    const rows = [
      ['Avg wellness score', week.avg_health_score],
      ['Avg screen time (min)', week.avg_total_screen_min],
      ['Avg sleep (hrs)', week.avg_sleep_hours],
      ['Avg focus (0-100)', week.avg_focus_0_100],
      ['Avg social media (min)', week.avg_social_min],
      ['Avg stress (0-10)', week.avg_stress_0_10],
    ];
    rows.forEach(([label, val]) => {
      const div = document.createElement('div');
      div.className = 'metric-row';
      div.innerHTML = `<span class="name">${label}</span><span class="value">${val != null ? Math.round(val * 10) / 10 : '—'}</span>`;
      container.appendChild(div);
    });
    const meta = document.createElement('p');
    meta.className = 'muted'; meta.style.fontSize = '.76rem'; meta.style.marginTop = '8px';
    meta.textContent = `${week.num_entries} check-in(s), ${week.start_date} → ${week.end_date}`;
    container.appendChild(meta);
  }

  try {
    const current = await window.DWApi.currentWeek();
    renderWeekRows(document.getElementById('weekCurrentRows'), current);
  } catch (e) {
    renderWeekRows(document.getElementById('weekCurrentRows'), null);
  }
  try {
    const previous = await window.DWApi.previousWeek();
    renderWeekRows(document.getElementById('weekPreviousRows'), previous);
  } catch (e) {
    renderWeekRows(document.getElementById('weekPreviousRows'), null);
  }

  // ---- 7-day plan ----
  let lastResult, lastPayload;
  try {
    lastResult = JSON.parse(localStorage.getItem('dwai_last_result') || 'null');
    lastPayload = JSON.parse(localStorage.getItem('dwai_last_payload') || 'null');
  } catch (e) {}

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
  document.getElementById('planIntro').innerHTML = mdBoldToHtml(plan.intro);
  const chips = document.getElementById('planFocusChips');
  (plan.focus_areas || []).forEach((area) => {
    const chip = document.createElement('span');
    chip.className = 'chip-option selected';
    chip.style.cursor = 'default';
    chip.textContent = area;
    chips.appendChild(chip);
  });

  const daysWrap = document.getElementById('planDays');
  plan.days.forEach((day) => {
    const card = document.createElement('div');
    card.className = 'day-card';
    card.innerHTML = `
      <div class="day-card-head"><span class="icon">${day.icon}</span><div><strong>${day.day_label}</strong><div class="muted" style="font-size:.82rem;">${day.theme}</div></div></div>
      <div class="tasks"></div>
      <div class="day-tip">💡 ${day.tip}</div>
    `;
    const tasksWrap = card.querySelector('.tasks');
    day.tasks.forEach((task) => {
      const row = document.createElement('div');
      row.className = 'task-row' + (task.completed ? ' done' : '');
      const id = `task-${day.day_number}-${task.task_index}`;
      row.innerHTML = `<input type="checkbox" id="${id}" ${task.completed ? 'checked' : ''}/><label for="${id}">${task.text}</label>`;
      row.querySelector('input').addEventListener('change', async (e) => {
        row.classList.toggle('done', e.target.checked);
        try {
          await window.DWApi.updatePlanTask(day.day_number, task.task_index, e.target.checked);
          if (e.target.checked) window.DWMascot.react('task_done');
        } catch (err) {
          window.DWToast.error(err.message);
        }
      });
      tasksWrap.appendChild(row);
    });
    daysWrap.appendChild(card);
  });
});
