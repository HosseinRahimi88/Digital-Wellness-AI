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
     the server scores them (see services/wellness/day_status_service.py) and
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

  /* ---- Three days down in a row ----

     The clearest early signal this data produces, and the dashboard
     used to draw it as three slightly shorter bars and say nothing.
     Asked once per run, not once per page load: the answer is stored
     against the run's id, so a new slide asks again and an answered one
     does not.

     The penalty is an accountability figure - it goes in the same
     ledger as missed plan days and is NEVER subtracted from the
     wellness score, which is the model's reading of the habits
     submitted. The sheet says so in as many words. */
  (async () => {
    if (!window.DWSheet || !window.DWApi.declineCheck) return;
    let decline = null;
    try { decline = await window.DWApi.declineCheck(); } catch (e) { return; }
    if (!decline || !decline.declining || decline.acknowledged) return;

    const esc = window.DWSheet.esc;
    const t = (k) => window.DWI18n.t(k);
    const dropText = t('decline_body')
      .replace('{days}', decline.days)
      .replace('{drop}', Math.round(decline.drop))
      .replace('{from}', Math.round(decline.scores[0]))
      .replace('{to}', Math.round(decline.scores[decline.scores.length - 1]));

    const reasons = ['illness', 'work', 'travel', 'sleep', 'mood', 'other'];
    const body =
      `<p>${esc(dropText)}</p>`
      + '<ul class="dw-csv-choice-facts">'
      + decline.scores.map((score, i) =>
        `<li><b dir="ltr">${esc(Math.round(score))}</b> `
        + `<span dir="ltr">${esc(decline.dates[i] || '')}</span></li>`).join('')
      + '</ul>'
      + `<p>${esc(t('decline_ask'))}</p>`
      + '<div class="decline-reasons" id="declineReasons">'
      + reasons.map((r) =>
        `<button type="button" class="decline-reason" data-reason="${r}">`
        + `${esc(t('decline_reason_' + r))}</button>`).join('')
      + '</div>'
      + `<label class="decline-note-label" for="declineNote">${esc(t('decline_note_label'))}</label>`
      + `<textarea id="declineNote" class="input decline-note" rows="2" maxlength="280"></textarea>`
      + `<p class="dw-csv-choice-days">${esc(t('decline_penalty_note')
        .replace('{points}', decline.penalty)
        .replace('{halved}', Math.round(decline.penalty * 5) / 10))}</p>`;

    // The typed answer, mirrored out as it is typed. Reading the
    // textarea after the sheet resolves finds nothing: DWSheet removes
    // its DOM on close, so by then the box is gone and every answer
    // arrived empty.
    let typedReason = '';
    const wireChips = () => {
      const note = document.getElementById('declineNote');
      if (note) note.addEventListener('input', () => { typedReason = note.value; });
      // Chips are a shortcut into the box, not instead of it - clicking
      // one fills the box so the user can still edit what it said.
      document.querySelectorAll('.decline-reason').forEach((btn) => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('.decline-reason').forEach((b) => b.classList.remove('is-on'));
          btn.classList.add('is-on');
          if (note && !note.value.trim()) {
            note.value = btn.textContent;
            typedReason = note.value;
          }
        });
      });
    };
    setTimeout(wireChips, 60);

    const answer = await window.DWSheet.open({
      title: t('decline_title'),
      bodyHtml: body,
      size: 'sm',
      buttons: [
        { label: t('decline_submit'), value: 'ack', style: 'primary', autofocus: true },
        { label: t('decline_later'), value: null, style: 'ghost' },
      ],
    });
    if (answer !== 'ack') return;  // asked again next time, nothing recorded

    try {
      const done = await window.DWApi.acknowledgeDecline(decline.run_id, typedReason);
      window.DWToast.info(t('decline_recorded').replace('{points}', done.penalty));
    } catch (e) {
      window.DWToast.error(e.message);
    }
  })();

  /* ---- "More detail": every day, not only this week ----

     The card shows Monday to Sunday of the current week, which is the
     right default and the wrong ceiling: someone three weeks into the
     app had no way to look at week one from the dashboard at all. This
     opens the whole history, newest week first, with each day's status
     colour, its score, its band, and a click straight into that day's
     check-in.

     It re-fetches rather than reusing the fifty entries loaded at the
     top of the page: fifty is plenty for the tiles and not necessarily
     plenty for "all of it", and this only runs when asked. */
  const moreBtn = document.getElementById('trendMoreBtn');
  if (moreBtn && window.DWSheet) {
    const isoOf = (d) => {
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    };
    const mondayOf = (iso) => {
      const d = new Date(`${iso}T00:00:00`);
      d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
      return isoOf(d);
    };
    const bandOf = (score) => (score >= 80 ? 'healthy' : score >= 50 ? 'moderate' : 'risk');

    const buildDetail = (allEntries, statusByDate) => {
      const esc = window.DWSheet.esc;
      const weeks = new Map();
      allEntries.forEach((e) => {
        if (!e.date) return;
        const key = mondayOf(e.date);
        if (!weeks.has(key)) weeks.set(key, []);
        weeks.get(key).push(e);
      });
      const orderedWeeks = [...weeks.keys()].sort().reverse();

      return orderedWeeks.map((weekStart) => {
        const days = weeks.get(weekStart).slice().sort((a, b) => (a.date < b.date ? 1 : -1));
        const scored = days.filter((d) => !d.excluded && d.health_score != null);
        const avg = scored.length
          ? Math.round(scored.reduce((s, d) => s + d.health_score, 0) / scored.length)
          : null;

        const rows = days.map((e) => {
          const status = statusByDate[e.date];
          const score = e.health_score != null ? Math.round(e.health_score) : null;
          const classes = ['trend-day'];
          if (status && status.status) classes.push('day-' + status.status);
          if (e.excluded) classes.push('is-excluded');
          if (score != null) classes.push('is-open');
          const weekday = new Date(`${e.date}T00:00:00`)
            .toLocaleDateString(window.DWI18n.get() === 'en' ? 'en-GB' : window.DWI18n.get(),
              { weekday: 'long' });
          const note = e.excluded
            ? window.DWI18n.t('trend_day_excluded')
            : (status && status.status
              ? window.DWI18n.t('day_legend_' + status.status)
              : '');
          return `<${score != null ? 'button type="button"' : 'div'} class="${classes.join(' ')}"`
            + `${score != null ? ` data-day="${esc(e.date)}"` : ''}>`
            + '<span class="trend-day-stripe" aria-hidden="true"></span>'
            + '<span class="trend-day-when">'
            + `<span class="trend-day-date" dir="ltr">${esc(e.date)} · ${esc(weekday)}</span>`
            + (note ? `<span class="trend-day-note">${esc(note)}</span>` : '')
            + '</span>'
            + `<span class="trend-day-score" dir="ltr">${score != null ? esc(score) : '—'}</span>`
            + (score != null
              ? `<span class="trend-day-band band-${bandOf(score)}">`
                + `${esc(window.DWI18n.t('band_' + bandOf(score)))}</span>`
              : '')
            + `</${score != null ? 'button' : 'div'}>`;
        }).join('');

        return '<section class="trend-detail-week">'
          + `<h4>${esc(window.DWI18n.t('trend_week_of').replace('{date}', weekStart))}`
          + (avg != null
            ? ` · <span class="wk-avg" dir="ltr">${esc(window.DWI18n.t('trend_week_avg').replace('{score}', avg))}</span>`
            : '')
          + '</h4>'
          + `<div class="trend-detail-days">${rows}</div>`
          + '</section>';
      }).join('');
    };

    moreBtn.addEventListener('click', async () => {
      let allEntries = entries;
      let statusByDate = dayStatus;
      try {
        const full = await window.DWApi.history(1, 400);
        allEntries = full.items || entries;
      } catch (e) { /* fall back to what the page already has */ }
      try {
        // Enough to cover a long history; the endpoint returns what it
        // has rather than padding, so asking for more is cheap.
        const strip = await window.DWApi.dayStatuses(400);
        statusByDate = {};
        ((strip && strip.days) || []).forEach((d) => { statusByDate[d.date] = d; });
      } catch (e) { statusByDate = dayStatus; }

      const html = allEntries.length
        ? `<div class="trend-detail">${buildDetail(allEntries, statusByDate)}</div>`
        : `<p>${window.DWSheet.esc(window.DWI18n.t('trend_detail_empty'))}</p>`;

      await window.DWSheet.open({
        title: window.DWI18n.t('trend_detail_title'),
        bodyHtml: html,
        size: 'lg',
        buttons: [{ label: window.DWI18n.t('trend_detail_close'), value: null, style: 'primary', autofocus: true }],
      });
    });

    // Delegated on the document, because the sheet's DOM is created and
    // destroyed by DWSheet and does not exist to bind to at wire time.
    document.addEventListener('click', (e) => {
      const row = e.target.closest && e.target.closest('.trend-day[data-day]');
      if (!row) return;
      window.location.href = `app.html?day=${encodeURIComponent(row.dataset.day)}`;
    });
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
    const lastResult = window.DWLastResult.get();
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
        // input features DWCoachLabels covers (see services/ml/cohort_service.py's
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
