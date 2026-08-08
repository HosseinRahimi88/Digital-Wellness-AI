/* Dashboard page controller: the user's landing page after login.
   Renders the last real check-in's score/trend, this-week heatmap,
   SHAP-driven strengths/weaknesses, and a cohort comparison - an
   empty state is shown instead if no check-in has been run yet. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('dashboard');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  let history;
  try {
    history = await window.DWApi.history(1, 50);
  } catch (e) {
    window.DWToast.error(e.message);
    return;
  }

  const entries = history.items || [];
  if (entries.length === 0) {
    document.getElementById('dashEmpty').classList.remove('hidden');
    return;
  }
  document.getElementById('dashContent').classList.remove('hidden');

  const latest = entries[0];
  const previous = entries[1];
  document.getElementById('statLastScore').textContent = latest.health_score != null ? Math.round(latest.health_score) : '--';
  if (previous && previous.health_score != null && latest.health_score != null) {
    const delta = latest.health_score - previous.health_score;
    const el = document.getElementById('statDelta');
    el.textContent = (delta >= 0 ? '▲ +' : '▼ ') + Math.abs(delta).toFixed(1) + ' vs last check-in';
    el.classList.add(delta >= 0 ? 'up' : 'down');
  }

  try {
    const week = await window.DWApi.currentWeek();
    document.getElementById('statWeekAvg').textContent = week && week.avg_health_score != null ? Math.round(week.avg_health_score) : '--';
  } catch (e) { /* no current-week data yet - leave placeholder */ }

  document.getElementById('statEntries').textContent = entries.length;

  // ---- Weekly heatmap (Mon..Sun of the current ISO week) ----
  const heatmap = document.getElementById('heatmapRow');
  const byDate = {};
  entries.forEach((e) => { byDate[e.date] = e; });
  const today = new Date();
  const dayIdx = (today.getDay() + 6) % 7; // 0=Mon
  const monday = new Date(today);
  monday.setDate(today.getDate() - dayIdx);
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    const iso = d.toISOString().slice(0, 10);
    const entry = byDate[iso];
    const cell = document.createElement('div');
    cell.className = 'heatmap-cell';
    if (entry && entry.health_score != null) {
      const score = entry.health_score;
      const hue = Math.max(0, Math.min(140, (score / 100) * 140));
      cell.style.background = `hsla(${hue}, 70%, 45%, .55)`;
      cell.textContent = Math.round(score);
      cell.classList.toggle('excluded', !!entry.excluded);
      cell.title = entry.excluded
        ? window.DWI18n.t('heatmap_excluded_tip').replace('{date}', iso)
        : window.DWI18n.t('heatmap_include_tip').replace('{date}', iso);
      cell.setAttribute('role', 'button');
      cell.setAttribute('tabindex', '0');
      const toggle = async () => {
        const next = !entry.excluded;
        try {
          await window.DWApi.setHistoryExcluded(iso, next);
          entry.excluded = next;
          cell.classList.toggle('excluded', next);
          cell.title = next
            ? window.DWI18n.t('heatmap_excluded_tip').replace('{date}', iso)
            : window.DWI18n.t('heatmap_include_tip').replace('{date}', iso);
          window.DWToast.info(window.DWI18n.t(next ? 'heatmap_excluded_toast' : 'heatmap_included_toast'));
        } catch (err) {
          window.DWToast.error(err.message);
        }
      };
      cell.addEventListener('click', toggle);
      cell.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
    } else {
      cell.style.background = 'var(--surface-strong)';
      cell.textContent = '·';
    }
    heatmap.appendChild(cell);
  }

  if (latest.top_shap_feature) {
    document.getElementById('topFeatureLine').textContent =
      `Top factor in your last result: ${latest.top_shap_feature.replace(/_/g, ' ')}`;
  }

  // ---- Recommendations from the last real prediction (if run this browser) ----
  const recWrap = document.getElementById('dashRecs');
  try {
    const lastResult = JSON.parse(localStorage.getItem('dwai_last_result') || 'null');
    if (lastResult && lastResult.recommendations && lastResult.recommendations.length) {
      lastResult.recommendations.slice(0, 2).forEach((r) => {
        const card = document.createElement('div');
        card.className = 'rec-card';
        card.innerHTML = `<div class="rec-title">${r.icon || '💡'} ${r.title}</div><p class="rec-desc">${r.description}</p>`;
        recWrap.appendChild(card);
      });
    } else {
      recWrap.innerHTML = '<p class="muted">Run a check-in to get personalized recommendations here.</p>';
    }
  } catch (e) {
    recWrap.innerHTML = '<p class="muted">Run a check-in to get personalized recommendations here.</p>';
  }

  // ---- Cohort comparison ----
  try {
    const avail = await window.DWApi.cohortAvailability();
    if (avail.available) {
      const comparison = await window.DWApi.cohortComparison();
      const rowsWrap = document.getElementById('cohortRows');
      rowsWrap.innerHTML = '';
      (comparison.rows || []).slice(0, 4).forEach((row) => {
        const div = document.createElement('div');
        div.className = 'metric-row';
        div.innerHTML = `<span class="name">${row.field.replace(/_/g, ' ')}</span><span class="value">you: ${row.user_value ?? '—'} | cohort avg: ${row.cohort_mean ?? '—'} (${row.cohort_percentile != null ? Math.round(row.cohort_percentile) + 'th pct' : '—'})</span>`;
        rowsWrap.appendChild(div);
      });
      if (!comparison.rows || !comparison.rows.length) {
        rowsWrap.innerHTML = '<p class="muted">Not enough history yet to compare.</p>';
      }
    } else {
      document.getElementById('cohortCard').classList.add('hidden');
    }
  } catch (e) {
    document.getElementById('cohortCard').classList.add('hidden');
  }

  window.DWMascot.react(latest.health_class && latest.health_class.toLowerCase().includes('risk') ? 'risk' : 'neutral');
});
