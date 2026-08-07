document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('whatif');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  let payload;
  try {
    payload = JSON.parse(localStorage.getItem('dwai_last_payload') || 'null');
  } catch (e) {}

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
  numericFields.forEach((f) => {
    const opt = document.createElement('option');
    opt.value = f.name; opt.textContent = f.label || f.name;
    select.appendChild(opt);
  });
  const preferredDefault = numericFields.find((f) => f.name === 'sleep_hours') || numericFields[0];
  if (preferredDefault) select.value = preferredDefault.name;

  const sweepCanvas = document.getElementById('sweepChart');

  async function runSweep() {
    const field = select.value;
    document.getElementById('runSweepBtn').disabled = true;
    try {
      const res = await window.DWApi.whatifSweep(payload, field, 9);
      const values = res.points.map((p) => p.score ?? 0);
      const labels = res.points.map((p) => Math.round(p.value * 10) / 10);
      window.DWCharts.drawLineChart(sweepCanvas, values, labels, { minFloor: 0, maxCeil: 100 });
      const distinctClasses = [...new Set(res.points.map((p) => p.prediction).filter(Boolean))];
      document.getElementById('sweepNote').textContent = distinctClasses.length > 1
        ? `Predicted class changes across this range: ${distinctClasses.join(' → ')}.`
        : `Predicted class stays "${distinctClasses[0] || '—'}" across this whole range.`;
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
      const wrap = document.getElementById('goalSeekResult');
      if (!res.available) {
        wrap.innerHTML = '<p class="muted">Could not find a value that helps reach that target for this field.</p>';
      } else {
        wrap.innerHTML = `
          <div class="metric-row"><span class="name">Best value found</span><span class="value">${Math.round(res.best_value * 100) / 100}</span></div>
          <div class="metric-row"><span class="name">Resulting score</span><span class="value">${Math.round(res.best_score * 100) / 100}</span></div>
          <div class="metric-row"><span class="name">Distance from target</span><span class="value">${Math.round(res.distance * 100) / 100}</span></div>
        `;
        window.DWMascot.react('neutral');
      }
    } catch (e) {
      window.DWToast.error(e.message);
    } finally {
      btn.disabled = false;
    }
  });
});
