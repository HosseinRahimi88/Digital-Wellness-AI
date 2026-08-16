/* Dashboard page controller: the user's landing page after login.
   Renders the last real check-in's score/trend, this-week heatmap,
   SHAP-driven strengths/weaknesses, and a cohort comparison - an
   empty state is shown instead if no check-in has been run yet. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('dashboard');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  if (window.DWIntro) setTimeout(() => window.DWIntro.show(), 500);

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

  // Cold-start honesty: say which of this page's history-dependent
  // views are actually meaningful yet, instead of rendering a thin
  // trend line with no caveat.
  try {
    const ins = await window.DWApi.insights();
    const note = document.getElementById('coldStartNote');
    if (note && ins.cold_start && ins.cold_start.stage !== 'established') {
      note.textContent = window.DWServerText.pick(ins.cold_start, 'message');
      note.classList.remove('hidden');
    }
  } catch (e) { /* insights are additive - never block the dashboard */ }

  // ---- Weekly heatmap (Mon..Sun of the current ISO week) ----
  // Days the user answered "that was an unusual day" about. Recorded
  // separately from the outright "exclude this day" flag above, and
  // shown separately, because they mean different things: an excluded
  // day is "this is not my data", an exception day happened and still
  // counts - just for less. Read from the server, which is the only
  // place that knows.
  let exceptionDays = [];
  try {
    const status = await window.DWApi.planDayStatus();
    exceptionDays = (status && status.exception_days) || [];
  } catch (e) { /* additive - the heatmap is fine without it */ }

  /* How each day actually went, on BOTH halves: was it logged, and was
     its plan task done. The row used to colour a day by the score
     alone, which made three different situations look identical -
     logged but no plan work done, plan work done but never logged, and
     nothing at all. Those are exactly the ones worth telling apart, so
     the server scores them (see services/day_status_service.py) and
     this only paints them. */
  let dayStatus = {};
  let dayPenalty = 0;
  try {
    const strip = await window.DWApi.dayStatuses(28);
    ((strip && strip.days) || []).forEach((d) => { dayStatus[d.date] = d; });
    dayPenalty = (strip && strip.total_penalty) || 0;
  } catch (e) { /* the row still renders on scores alone */ }

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
    const status = dayStatus[iso];
    if (status) {
      // The four states carry their own colour. Applied as a class so
      // one stylesheet owns what each means, and so a day is never
      // simultaneously "green by score" and "red by record".
      cell.classList.add('day-' + status.status);
      cell.dataset.dayStatus = status.status;
      const label = window.DWI18n.t('day_status_' + status.status)
        .replace('{date}', iso)
        .replace('{penalty}', Math.abs(status.penalty).toFixed(1));
      cell.title = label;
      cell.setAttribute('aria-label', label);
    }

    if (entry && entry.health_score != null) {
      const score = entry.health_score;
      if (!status) {
        const hue = Math.max(0, Math.min(140, (score / 100) * 140));
        cell.style.background = `hsla(${hue}, 70%, 45%, .55)`;
      }
      cell.classList.toggle('excluded', !!entry.excluded);

      // The score is its own node now, so the exception toggle below can
      // sit in the corner without textContent wiping it out.
      const num = document.createElement('span');
      num.className = 'heatmap-score';
      num.textContent = Math.round(score);
      cell.appendChild(num);

      // Clicking a day opens that day. It used to silently mark the day
      // as an exception instead, which is a destructive-looking edit to
      // fire from the most obvious gesture on the page - and left no way
      // to actually look at a past check-in.
      cell.title = window.DWI18n.t('heatmap_open_tip').replace('{date}', iso);
      cell.setAttribute('role', 'button');
      cell.setAttribute('tabindex', '0');
      const open = () => { window.location.href = `app.html?day=${encodeURIComponent(iso)}`; };
      cell.addEventListener('click', open);
      cell.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });

      // Marking a day as an exception keeps its own explicit control.
      const mark = document.createElement('button');
      mark.type = 'button';
      mark.className = 'heatmap-flag';
      const labelFor = (excluded) => (excluded
        ? window.DWI18n.t('heatmap_excluded_tip')
        : window.DWI18n.t('heatmap_include_tip')).replace('{date}', iso);
      mark.textContent = entry.excluded ? '⊘' : '·';
      mark.title = labelFor(entry.excluded);
      mark.setAttribute('aria-label', labelFor(entry.excluded));
      mark.setAttribute('aria-pressed', String(!!entry.excluded));
      mark.addEventListener('click', async (e) => {
        e.stopPropagation();  // never opens the day as a side effect
        const next = !entry.excluded;
        try {
          await window.DWApi.setHistoryExcluded(iso, next);
          entry.excluded = next;
          cell.classList.toggle('excluded', next);
          mark.textContent = next ? '⊘' : '·';
          mark.title = labelFor(next);
          mark.setAttribute('aria-label', labelFor(next));
          mark.setAttribute('aria-pressed', String(next));
          window.DWToast.info(window.DWI18n.t(next ? 'heatmap_excluded_toast' : 'heatmap_included_toast'));
        } catch (err) {
          window.DWToast.error(err.message);
        }
      });
      cell.appendChild(mark);

      if (exceptionDays.indexOf(iso) !== -1) {
        cell.classList.add('exception-day');
        const flag = document.createElement('span');
        flag.className = 'heatmap-exception';
        flag.textContent = '~';
        flag.title = window.DWI18n.t('heatmap_exception_tip').replace('{date}', iso);
        flag.setAttribute('aria-label', flag.title);
        cell.appendChild(flag);
      }
    } else if (!status) {
      // No status at all means the day is outside the scored range -
      // in practice, later this week. A day that has not happened yet
      // is not a day you failed, so it gets neither a colour nor a
      // penalty; but left as a plain grey square it was indis-
      // tinguishable from a cell that failed to render, which is what
      // "the days had no colour" turned out to be describing. Marked
      // explicitly instead.
      cell.classList.add('day-upcoming');
      cell.textContent = '·';
      const upcoming = window.DWI18n.t('day_status_upcoming').replace('{date}', iso);
      cell.title = upcoming;
      cell.setAttribute('aria-label', upcoming);
    } else {
      // A day with no check-in still has a state - grey or red - and
      // saying so is the whole point. It gets the dot rather than a
      // score, because there is no score to show and inventing a
      // zero-height bar would read as "you scored 0".
      cell.textContent = '·';
    }
    heatmap.appendChild(cell);
  }

  /* The key to the four colours.

     Without it the meaning was reachable only by hovering a cell, which
     is nothing on a touch screen and nothing at all in a screenshot -
     and this row is the first thing anyone looks at. Built from the
     same four state ids the cells use, so a colour cannot appear on the
     row without appearing here.

     Each swatch carries its state's own class, so the legend and the
     cells are painted by one stylesheet rule rather than two that can
     drift apart. */
  const legend = document.getElementById('heatmapLegend');
  if (legend) {
    const paint = () => {
      legend.innerHTML = '';
      const heading = document.createElement('li');
      heading.className = 'day-legend-title';
      heading.textContent = window.DWI18n.t('day_legend_title');
      legend.appendChild(heading);
      ['green', 'orange', 'grey', 'red'].forEach((state) => {
        const item = document.createElement('li');
        const swatch = document.createElement('span');
        swatch.className = 'day-legend-swatch heatmap-cell day-' + state;
        swatch.setAttribute('aria-hidden', 'true');
        const text = document.createElement('span');
        text.textContent = window.DWI18n.t('day_legend_' + state);
        // The cost, stated on the legend rather than only in a tooltip:
        // "orange" meaning half a point is the part a user needs, and
        // it is the part they cannot guess from the colour.
        const cost = { green: null, orange: '−0.5', grey: '−0.5', red: '−1' }[state];
        item.append(swatch, text);
        if (cost) {
          const tag = document.createElement('span');
          tag.className = 'day-legend-cost';
          tag.textContent = cost;
          item.appendChild(tag);
        }
        legend.appendChild(item);
      });
      const note = document.createElement('li');
      note.className = 'day-legend-note';
      note.textContent = window.DWI18n.t('day_legend_today');
      legend.appendChild(note);
    };
    paint();
    document.addEventListener('dwai:langchange', paint);
  }

  // Named under the heatmap as well as marked on it: a week with three
  // "unusual" days is itself the most useful thing this row can say,
  // and a small corner glyph is easy to never notice.
  const penaltyLine = document.getElementById('heatmapPenaltyLine');
  if (penaltyLine) {
    if (dayPenalty < 0) {
      penaltyLine.textContent = window.DWI18n.t('day_status_penalty_total')
        .replace('{points}', Math.abs(dayPenalty).toFixed(1));
      penaltyLine.classList.remove('hidden');
    } else {
      penaltyLine.classList.add('hidden');
    }
  }

  const exceptionLine = document.getElementById('heatmapExceptionLine');
  if (exceptionLine) {
    const thisWeek = exceptionDays.filter((iso) => byDate[iso]);
    if (thisWeek.length) {
      exceptionLine.textContent = window.DWI18n.t('heatmap_exception_summary')
        .replace('{count}', thisWeek.length)
        .replace('{days}', thisWeek.join(', '));
      exceptionLine.classList.remove('hidden');
    } else {
      exceptionLine.classList.add('hidden');
    }
  }

  if (latest.top_shap_feature) {
    const fieldLabel = (window.DWCoachLabels && window.DWCoachLabels[latest.top_shap_feature])
      || latest.top_shap_feature.replace(/_/g, ' ');
    document.getElementById('topFeatureLine').textContent =
      window.DWI18n.t('dash_top_factor').replace('{field}', fieldLabel);
  }

  // ---- Recommendations from the last real prediction (if run this browser) ----
  const recWrap = document.getElementById('dashRecs');
  try {
    const lastResult = JSON.parse(localStorage.getItem('dwai_last_result') || 'null');
    if (lastResult && lastResult.recommendations && lastResult.recommendations.length) {
      // The recommendation text arrives in all four languages; this
      // was printing the English fields, so the dashboard stayed English
      // even though the same cards on the result page did not.
      const lang = window.DWI18n.get();
      const part = (r, name, fallback) => {
        const table = (r.text_i18n || {})[name];
        return (table && (table[lang] || table.en)) || fallback || '';
      };
      lastResult.recommendations.slice(0, 2).forEach((r) => {
        const card = document.createElement('div');
        card.className = 'rec-card';
        const title = document.createElement('div');
        title.className = 'rec-title';
        title.textContent = `${r.icon || '💡'} ${part(r, 'title', r.title)}`;
        const desc = document.createElement('p');
        desc.className = 'rec-desc';
        desc.textContent = part(r, 'description', r.description);
        card.append(title, desc);
        recWrap.appendChild(card);
      });
    } else {
      recWrap.innerHTML = `<p class="muted">${window.DWI18n.t('dash_no_recs')}</p>`;
    }
  } catch (e) {
    recWrap.innerHTML = `<p class="muted">${window.DWI18n.t('dash_no_recs')}</p>`;
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
        // health_score is a derived cohort field, not one of the 53 real
        // input features DWCoachLabels covers (see services/cohort_service.py's
        // USER_FIELD_TO_COHORT_FIELD) - it needs its own key rather than
        // silently falling through to the raw, untranslated field name.
        const fieldLabel = row.field === 'health_score'
          ? window.DWI18n.t('field_health_score')
          : (window.DWCoachLabels && window.DWCoachLabels[row.field]) || row.field.replace(/_/g, ' ');
        const pctText = row.cohort_percentile != null ? String(Math.round(row.cohort_percentile)) : '—';
        const rowText = window.DWI18n.t('dash_cohort_row')
          .replace('{you}', row.user_value ?? '—')
          .replace('{avg}', row.cohort_mean ?? '—')
          .replace('{pct}', pctText);
        div.innerHTML = `<span class="name">${fieldLabel}</span><span class="value">${rowText}</span>`;
        rowsWrap.appendChild(div);
      });
      if (!comparison.rows || !comparison.rows.length) {
        rowsWrap.innerHTML = `<p class="muted">${window.DWI18n.t('dash_no_cohort_data')}</p>`;
      }
    } else {
      document.getElementById('cohortCard').classList.add('hidden');
    }
  } catch (e) {
    document.getElementById('cohortCard').classList.add('hidden');
  }

  // Section E games moved to their own screen between processing and the
  // result (app.js, view-games) - they no longer render on the dashboard.
  window.DWMascot.react(latest.health_class && latest.health_class.toLowerCase().includes('risk') ? 'risk' : 'neutral');
});
