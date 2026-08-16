/* Analytics page controller: fetches the authenticated user's real
   history-derived trend data (score-over-time, weekday pattern, field
   averages) from GET /analytics/summary and renders it with charts.js. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('analytics');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  let summary;
  try {
    summary = await window.DWApi.analyticsSummary();
  } catch (e) {
    window.DWToast.error(e.message);
    return;
  }

  if (!summary.entry_count) {
    document.getElementById('analyticsEmpty').classList.remove('hidden');
    return;
  }
  document.getElementById('analyticsContent').classList.remove('hidden');

  // Insight cards render themselves, or the whole section stays hidden.
  if (window.DWInsightCards) {
    window.DWInsightCards.load(document.getElementById('insightCards'));
  }

  /* D-10. Composed from the same insight payload rather than its own
     data source, and only offered once there is enough history for the
     letter to be about this reader (G4). */
  if (window.DWFutureLetter && window.DWApi.insightCards) {
    window.DWApi.insightCards().then((cards) => {
      const ctx = window.DWFutureLetter.contextFrom(cards, stats && stats.direction);
      const letter = window.DWFutureLetter.compose(ctx);
      if (!letter) return;
      const section = document.getElementById('letterSection');
      section.classList.remove('hidden');
      document.getElementById('openLetterBtn').addEventListener('click', (e) => {
        window.DWFutureLetter.render(letter, document.getElementById('letterMount'));
        e.target.style.display = 'none';
      });
    }).catch(() => {});
  }

  /* A-1: a compact strip plus a stated verdict, instead of a tall chart
     that left the reader to eyeball the direction. The note underneath was
     also hardcoded English, so every non-English reader saw a mixed
     sentence here. */
  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);
  const TREND_TEXT = {
    up:   { en: 'Trending up', fa: 'روند رو به بالا', ar: 'اتجاه صاعد', zh: '趋势向上' },
    down: { en: 'Trending down', fa: 'روند رو به پایین', ar: 'اتجاه هابط', zh: '趋势向下' },
    flat: { en: 'Holding steady', fa: 'تقریباً ثابت', ar: 'مستقر تقريباً', zh: '基本持平' },
    unknown: { en: 'Not enough days yet to call a direction',
               fa: 'هنوز روزهای کافی برای گفتن جهت نیست',
               ar: 'لا توجد أيام كافية بعد لتحديد اتجاه',
               zh: '天数还不够，无法判断方向' },
    over: { en: 'across', fa: 'در طول', ar: 'عبر', zh: '在' },
    days: { en: 'days', fa: 'روز', ar: 'يوماً', zh: '天内' },
    exceptions: { en: 'day(s) you marked as exceptions are shown hollow and left out of the trend',
                  fa: 'روزهایی که استثنا علامت زده‌ای توخالی نشان داده و از روند کنار گذاشته شده‌اند',
                  ar: 'الأيام التي علّمتها كاستثناءات تظهر مفرغة وتُستثنى من الاتجاه',
                  zh: '你标记为例外的日子以空心显示，并且不计入趋势' },
  };

  const trendCanvas = document.getElementById('trendChart');
  const stats = window.DWTrendStrip.draw(trendCanvas, summary.score_history, { height: 86 });

  const verdictEl = document.getElementById('trendVerdict');
  const noteEl = document.getElementById('trendNote');
  if (stats && verdictEl) {
    const arrow = stats.direction === 'up' ? '▲' : stats.direction === 'down' ? '▼' : '■';
    verdictEl.className = 'trend-verdict is-' + stats.direction;
    if (stats.direction === 'unknown') {
      verdictEl.textContent = pick(TREND_TEXT.unknown);
    } else {
      const delta = stats.change;
      const sign = delta > 0 ? '+' : '';
      verdictEl.textContent = `${arrow} ${pick(TREND_TEXT[stats.direction])} · ${sign}${delta.toFixed(1)} `
        + `${pick(TREND_TEXT.over)} ${stats.used} ${pick(TREND_TEXT.days)}`;
    }
  }
  if (noteEl) {
    noteEl.textContent = stats && stats.exceptions
      ? `${stats.exceptions} ${pick(TREND_TEXT.exceptions)}`
      : '';
  }

  const weekdayCanvas = document.getElementById('weekdayChart');
  if (summary.weekday_pattern) {
    const order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const wLabels = order.filter((d) => d in summary.weekday_pattern);
    const wValues = wLabels.map((d) => summary.weekday_pattern[d]);
    window.DWCharts.drawBarChartAnimated(weekdayCanvas, wValues, wLabels.map((d) => d.slice(0, 3)), { maxCeil: 100 });

    /* The finding, in words, under the bars.
       A weekday chart exists to answer one question - which day is
       hardest - and until now the reader had to work that out by
       comparing seven bars by eye. The chart is half the height it was;
       this is what the space went to.

       Named only when the gap is big enough to be a pattern rather than
       noise: below MIN_SPREAD points the days are the same day and
       saying otherwise would invent a habit out of rounding. */
    const MIN_SPREAD = 3;
    const verdict = document.getElementById('weekdayVerdict');
    if (verdict && wValues.length >= 3) {
      const pairs = wLabels.map((day, i) => ({ day, value: wValues[i] }))
        .filter((p) => typeof p.value === 'number' && Number.isFinite(p.value))
        .sort((a, b) => b.value - a.value);
      const best = pairs[0];
      const worst = pairs[pairs.length - 1];
      const spread = best && worst ? best.value - worst.value : 0;
      const dayName = (key) => window.DWI18n.t('weekday_' + key.toLowerCase()) || key;

      if (spread >= MIN_SPREAD) {
        verdict.innerHTML =
          `<span class="weekday-verdict-best">${window.DWI18n.t('analytics_weekday_best')
            .replace('{day}', dayName(best.day))
            .replace('{score}', Math.round(best.value))}</span>`
          + `<span class="weekday-verdict-worst">${window.DWI18n.t('analytics_weekday_worst')
            .replace('{day}', dayName(worst.day))
            .replace('{score}', Math.round(worst.value))}</span>`
          + `<span class="weekday-verdict-gap muted">${window.DWI18n.t('analytics_weekday_gap')
            .replace('{points}', Math.round(spread))}</span>`;
      } else {
        verdict.innerHTML =
          `<span class="muted">${window.DWI18n.t('analytics_weekday_flat')}</span>`;
      }
    }
  } else {
    window.DWCharts.drawBarChart(weekdayCanvas, [], [], {
      emptyText: window.DWI18n ? window.DWI18n.t('analytics_not_enough_data') : 'Not enough data yet',
    });
  }

  const avgWrap = document.getElementById('fieldAverages');
  /* The row names were the raw column names with the underscores taken
     out - "total screen min" - in every language, because this card
     never went through the label table the rest of the app uses.
     DWCoachLabels is already loaded on this page and already carries all
     four languages for these fields; the underscore form is kept only as
     the fallback for a field the table has yet to name. */
  const labelFor = (field) => {
    const lang = window.DWI18n ? window.DWI18n.get() : 'en';
    const entry = window.DWCoachLabels && window.DWCoachLabels[field];
    return (entry && (entry[lang] || entry.en)) || field.replace(/_/g, ' ');
  };
  Object.entries(summary.field_averages || {}).forEach(([field, val]) => {
    const div = document.createElement('div');
    div.className = 'metric-row';
    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = labelFor(field);
    const value = document.createElement('span');
    value.className = 'value';
    value.textContent = Math.round(val * 100) / 100;
    div.appendChild(name);
    div.appendChild(value);
    avgWrap.appendChild(div);
  });
  if (!Object.keys(summary.field_averages || {}).length) {
    const empty = document.createElement('p');
    empty.className = 'muted';
    empty.textContent = window.DWI18n
      ? window.DWI18n.t('analytics_no_averages') : 'No field averages yet.';
    avgWrap.innerHTML = '';
    avgWrap.appendChild(empty);
  }

  window.addEventListener('resize', () => {
    window.DWTrendStrip.draw(trendCanvas, summary.score_history, { height: 86 });
    if (summary.weekday_pattern) {
      const order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
      const wLabels = order.filter((d) => d in summary.weekday_pattern);
      const wValues = wLabels.map((d) => summary.weekday_pattern[d]);
      window.DWCharts.drawBarChart(weekdayCanvas, wValues, wLabels.map((d) => d.slice(0, 3)), { maxCeil: 100 });
    }
  });
});
