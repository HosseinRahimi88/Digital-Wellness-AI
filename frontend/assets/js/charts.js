/*
  Minimal dependency-free canvas charts (line + bar). Deliberately not
  a CDN charting library: keeps every page fully self-contained and
  testable offline, matching the "vanilla JS" brief. Only draws what
  Analytics/Dashboard/What-if actually need - not a general-purpose
  charting API.
*/
(function () {
  function themeColors() {
    const s = getComputedStyle(document.documentElement);
    return {
      cyan: s.getPropertyValue('--neon-cyan').trim() || '#22f5c6',
      blue: s.getPropertyValue('--neon-blue').trim() || '#3aa7ff',
      text: s.getPropertyValue('--text-secondary').trim() || '#a9c3c0',
      muted: s.getPropertyValue('--text-muted').trim() || '#6f8a89',
      grid: s.getPropertyValue('--surface-border').trim() || 'rgba(255,255,255,.1)',
    };
  }

  function setupCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    return { ctx, w: rect.width, h: rect.height };
  }

  function drawLineChart(canvas, values, labels, opts = {}) {
    const { ctx, w, h } = setupCanvas(canvas);
    const c = themeColors();
    ctx.clearRect(0, 0, w, h);
    if (!values.length) {
      ctx.fillStyle = c.muted; ctx.font = '13px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(opts.emptyText || 'Not enough data yet', w / 2, h / 2);
      return;
    }
    const padL = 34, padB = 24, padT = 14, padR = 14;
    const min = Math.min(...values, opts.minFloor ?? Math.min(...values));
    const max = Math.max(...values, opts.maxCeil ?? Math.max(...values));
    const range = max - min || 1;
    const plotW = w - padL - padR, plotH = h - padT - padB;

    // grid lines
    ctx.strokeStyle = c.grid; ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
      const y = padT + (plotH / 3) * i;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
      const val = max - (range / 3) * i;
      ctx.fillStyle = c.muted; ctx.font = '10px monospace'; ctx.textAlign = 'right';
      ctx.fillText(Math.round(val), padL - 6, y + 3);
    }

    const stepX = values.length > 1 ? plotW / (values.length - 1) : 0;
    const points = values.map((v, i) => ({
      x: padL + stepX * i,
      y: padT + plotH - ((v - min) / range) * plotH,
    }));

    // area fill
    const grad = ctx.createLinearGradient(0, padT, 0, padT + plotH);
    grad.addColorStop(0, c.cyan + '55'); grad.addColorStop(1, c.cyan + '00');
    ctx.beginPath();
    ctx.moveTo(points[0].x, padT + plotH);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, padT + plotH);
    ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();

    // line
    ctx.beginPath();
    points.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
    ctx.strokeStyle = c.cyan; ctx.lineWidth = 2.5; ctx.lineJoin = 'round'; ctx.stroke();

    // points
    points.forEach((p) => {
      ctx.beginPath(); ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = c.blue; ctx.fill();
    });

    // x labels (sparse to avoid overlap)
    if (labels && labels.length) {
      const maxLabels = Math.min(labels.length, Math.floor(plotW / 60) || 1);
      const skip = Math.max(1, Math.ceil(labels.length / maxLabels));
      ctx.fillStyle = c.muted; ctx.font = '10px sans-serif'; ctx.textAlign = 'center';
      labels.forEach((lbl, i) => {
        if (i % skip !== 0 && i !== labels.length - 1) return;
        ctx.fillText(lbl, points[i].x, h - 6);
      });
    }
  }

  function drawBarChart(canvas, values, labels, opts = {}) {
    const { ctx, w, h } = setupCanvas(canvas);
    const c = themeColors();
    ctx.clearRect(0, 0, w, h);
    if (!values.length) {
      ctx.fillStyle = c.muted; ctx.font = '13px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(opts.emptyText || 'No data yet', w / 2, h / 2);
      return;
    }
    const padL = 34, padB = 26, padT = 14, padR = 10;
    const max = opts.maxCeil ?? Math.max(...values, 1);
    const plotW = w - padL - padR, plotH = h - padT - padB;
    const barW = (plotW / values.length) * 0.6;
    const gap = (plotW / values.length) * 0.4;

    ctx.strokeStyle = c.grid; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(padL, padT + plotH); ctx.lineTo(w - padR, padT + plotH); ctx.stroke();

    values.forEach((v, i) => {
      const barH = (v / max) * plotH;
      const x = padL + i * (barW + gap) + gap / 2;
      const y = padT + plotH - barH;
      const grad = ctx.createLinearGradient(0, y, 0, padT + plotH);
      grad.addColorStop(0, c.cyan); grad.addColorStop(1, c.blue);
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(x, y, barW, barH, 4) : ctx.rect(x, y, barW, barH);
      ctx.fill();

      if (labels && labels[i]) {
        ctx.fillStyle = c.muted; ctx.font = '10px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText(labels[i], x + barW / 2, h - 8);
      }
    });
  }

  window.DWCharts = { drawLineChart, drawBarChart };
})();
