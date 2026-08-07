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

  const trendCanvas = document.getElementById('trendChart');
  const values = summary.score_history.map((p) => p.health_score);
  const labels = summary.score_history.map((p) => p.date.slice(5));
  window.DWCharts.drawLineChart(trendCanvas, values, labels, { minFloor: 0, maxCeil: 100 });
  document.getElementById('trendNote').textContent = summary.has_enough_points_for_trend
    ? `${summary.entry_count} check-ins tracked.`
    : `${summary.entry_count} check-in(s) so far — trend gets more meaningful with a few more days.`;

  const weekdayCanvas = document.getElementById('weekdayChart');
  if (summary.weekday_pattern) {
    const order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const wLabels = order.filter((d) => d in summary.weekday_pattern);
    const wValues = wLabels.map((d) => summary.weekday_pattern[d]);
    window.DWCharts.drawBarChart(weekdayCanvas, wValues, wLabels.map((d) => d.slice(0, 3)), { maxCeil: 100 });
  } else {
    window.DWCharts.drawBarChart(weekdayCanvas, [], [], { emptyText: 'Not enough data yet' });
  }

  const avgWrap = document.getElementById('fieldAverages');
  Object.entries(summary.field_averages || {}).forEach(([field, val]) => {
    const div = document.createElement('div');
    div.className = 'metric-row';
    div.innerHTML = `<span class="name">${field.replace(/_/g, ' ')}</span><span class="value">${Math.round(val * 100) / 100}</span>`;
    avgWrap.appendChild(div);
  });
  if (!Object.keys(summary.field_averages || {}).length) {
    avgWrap.innerHTML = '<p class="muted">No field averages yet.</p>';
  }

  window.addEventListener('resize', () => {
    window.DWCharts.drawLineChart(trendCanvas, values, labels, { minFloor: 0, maxCeil: 100 });
    if (summary.weekday_pattern) {
      const order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
      const wLabels = order.filter((d) => d in summary.weekday_pattern);
      const wValues = wLabels.map((d) => summary.weekday_pattern[d]);
      window.DWCharts.drawBarChart(weekdayCanvas, wValues, wLabels.map((d) => d.slice(0, 3)), { maxCeil: 100 });
    }
  });
});
