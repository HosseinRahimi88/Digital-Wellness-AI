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

  /** roundRect as a path, with a manual fallback: the glass tube and
   *  the liquid have to trace the SAME shape (one to stroke, one to
   *  clip), and older Safari has no ctx.roundRect. */
  function roundRectPath(ctx, x, y, w, h, r) {
    const rad = Math.max(0, Math.min(r, w / 2, h / 2));
    ctx.beginPath();
    if (ctx.roundRect) { ctx.roundRect(x, y, w, h, rad); return; }
    ctx.moveTo(x + rad, y);
    ctx.arcTo(x + w, y, x + w, y + h, rad);
    ctx.arcTo(x + w, y + h, x, y + h, rad);
    ctx.arcTo(x, y + h, x, y, rad);
    ctx.arcTo(x, y, x + w, y, rad);
    ctx.closePath();
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

  /**
   * Bar chart with an axis, a mean reference line, a highlighted best
   * bar and hover read-out.
   *
   * The extra marks are not decoration: the gridlines let a bar be read
   * as a number without hovering, the dashed line is this series' own
   * mean so "above/below my average" is visible at a glance, and the
   * highlight names the best bar rather than leaving the reader to
   * eyeball which of seven similar bars is tallest. Everything drawn
   * comes from `values` - nothing is invented to fill space.
   *
   * opts: { maxCeil, emptyText, unit, meanLine (default true),
   *         highlightBest (default true), onHover }
   */
  function drawBarChart(canvas, values, labels, opts = {}) {
    const { ctx, w, h } = setupCanvas(canvas);
    const c = themeColors();
    ctx.clearRect(0, 0, w, h);
    if (!values.length) {
      ctx.fillStyle = c.muted; ctx.font = '13px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(opts.emptyText || 'No data yet', w / 2, h / 2);
      canvas._dwBars = null;
      return;
    }
    const padL = 38, padB = 28, padT = 18, padR = 14;
    const max = opts.maxCeil ?? Math.max(...values, 1);
    const plotW = w - padL - padR, plotH = h - padT - padB;
    const slot = plotW / values.length;
    const barW = Math.min(slot * 0.62, 54);
    const baseY = padT + plotH;

    // ---- horizontal gridlines + value axis -------------------------
    const ticks = 4;
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    for (let t = 0; t <= ticks; t++) {
      const val = (max / ticks) * t;
      const y = baseY - (val / max) * plotH;
      ctx.strokeStyle = c.grid;
      ctx.globalAlpha = t === 0 ? 1 : 0.35;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.fillStyle = c.muted;
      ctx.fillText(String(Math.round(val)), padL - 7, y);
    }

    // ---- this series' own mean, as a reference line -----------------
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const best = values.indexOf(Math.max(...values));
    if (opts.meanLine !== false && values.length > 1) {
      const my = baseY - (mean / max) * plotH;
      ctx.save();
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = c.text; ctx.globalAlpha = 0.5; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(padL, my); ctx.lineTo(w - padR, my); ctx.stroke();
      ctx.restore();
    }

    // ---- bars: an empty glass tube, filled with liquid to the value --
    // Each bar is drawn as a container plus its contents rather than a
    // solid block. The empty part stays visible, so the bar shows what
    // is missing as well as what is there - on a 0-100 score that is
    // real information, not decoration. `fill` is the animation
    // progress (0-1); at rest it is 1 and the shape is identical.
    const boxes = [];
    const fill = typeof opts.fill === 'number' ? Math.max(0, Math.min(1, opts.fill)) : 1;
    const radius = Math.min(7, barW / 2);

    values.forEach((v, i) => {
      const fullH = Math.max((v / max) * plotH, v > 0 ? 2 : 0);
      const barH = fullH * fill;
      const x = padL + i * slot + (slot - barW) / 2;
      const y = baseY - barH;
      const isBest = opts.highlightBest !== false && i === best && values.length > 1;
      const tubeTop = baseY - plotH;

      // The glass: a faint full-height tube behind the liquid.
      ctx.save();
      ctx.globalAlpha = 0.13;
      ctx.fillStyle = c.text;
      ctx.beginPath();
      roundRectPath(ctx, x, tubeTop, barW, plotH, radius);
      ctx.fill();
      ctx.globalAlpha = 0.22;
      ctx.strokeStyle = c.grid; ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();

      // The liquid, clipped to the tube so it keeps the rounded ends.
      ctx.save();
      ctx.beginPath();
      roundRectPath(ctx, x, tubeTop, barW, plotH, radius);
      ctx.clip();

      const grad = ctx.createLinearGradient(x, y, x + barW, baseY);
      grad.addColorStop(0, c.cyan);
      grad.addColorStop(1, c.blue);
      ctx.fillStyle = grad;
      ctx.globalAlpha = isBest ? 1 : 0.88;
      if (isBest) { ctx.shadowColor = c.cyan; ctx.shadowBlur = 16; }
      ctx.fillRect(x, y, barW, barH);
      ctx.shadowBlur = 0;

      if (barH > 3) {
        // Meniscus: a brighter band at the surface, the thing that
        // makes a filled tube read as liquid rather than paint.
        ctx.globalAlpha = 0.95;
        ctx.fillStyle = c.cyan;
        ctx.fillRect(x, y, barW, Math.min(2.5, barH));
        // A soft vertical highlight down the left of the glass.
        const sheen = ctx.createLinearGradient(x, 0, x + barW, 0);
        sheen.addColorStop(0, 'rgba(255,255,255,0.20)');
        sheen.addColorStop(0.35, 'rgba(255,255,255,0.04)');
        sheen.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.globalAlpha = 1;
        ctx.fillStyle = sheen;
        ctx.fillRect(x, y, barW, barH);
      }
      ctx.restore();

      boxes.push({ x, y: baseY - fullH, w: barW, h: fullH, i, value: v, label: (labels && labels[i]) || '' });

      if (labels && labels[i]) {
        ctx.fillStyle = c.muted; ctx.font = '10px sans-serif'; ctx.textAlign = 'center';
        ctx.textBaseline = 'alphabetic';
        ctx.fillText(labels[i], x + barW / 2, h - 8);
      }
    });

    // Geometry kept on the element so the hover layer can hit-test
    // without re-deriving any of it - and so a redraw (resize, language
    // change) automatically updates what hovering reports.
    canvas._dwBars = { boxes, unit: opts.unit || '', mean, best };
    attachBarHover(canvas);
  }

  /* ---- hover read-out ---------------------------------------------
     One listener per canvas, guarded by a flag, because drawBarChart is
     called again on every resize and on language change - binding each
     time would stack duplicate handlers on the same element. */
  function attachBarHover(canvas) {
    if (canvas._dwHoverBound) return;
    canvas._dwHoverBound = true;

    const wrap = canvas.parentElement;
    if (!wrap) return;
    let tip = wrap.querySelector('.chart-tip');
    if (!tip) {
      tip = document.createElement('div');
      tip.className = 'chart-tip';
      tip.setAttribute('role', 'status');
      wrap.appendChild(tip);
    }

    const hide = () => { tip.classList.remove('is-on'); };

    canvas.addEventListener('pointerleave', hide);
    canvas.addEventListener('pointermove', (e) => {
      const data = canvas._dwBars;
      if (!data) return hide();
      const r = canvas.getBoundingClientRect();
      const x = e.clientX - r.left, y = e.clientY - r.top;
      // Hit the whole column, not just the drawn bar: aiming at a short
      // bar is otherwise almost impossible.
      const hit = data.boxes.find((b) => x >= b.x - 6 && x <= b.x + b.w + 6);
      if (!hit || y > r.height) return hide();
      const val = Math.round(hit.value * 10) / 10;
      const rel = hit.value >= data.mean ? '▲' : '▼';
      tip.innerHTML =
        `<span class="tip-label">${hit.label}</span>` +
        `<span class="tip-value">${val}${data.unit}</span> ` +
        `<span class="tip-label">${rel} ${Math.abs(Math.round((hit.value - data.mean) * 10) / 10)}</span>`;
      tip.style.left = `${hit.x + hit.w / 2}px`;
      tip.style.top = `${Math.max(hit.y - 8, 14)}px`;
      tip.classList.add('is-on');
    });
  }

  /**
   * drawBarChart, with the liquid rising from empty once.
   *
   * Separate from drawBarChart rather than built into it because a
   * resize and a language change both redraw, and re-running the
   * animation every time would make the page feel busy rather than
   * alive. Callers animate on first paint and redraw plainly after
   * that. Respects reduce-motion by drawing the final frame directly.
   */
  function drawBarChartAnimated(canvas, values, labels, opts = {}) {
    const reduced = (window.DWMotion && window.DWMotion.prefersReduced && window.DWMotion.prefersReduced())
      || (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    if (reduced || !values || !values.length) {
      drawBarChart(canvas, values, labels, opts);
      return;
    }
    const duration = opts.duration || 620;
    const start = performance.now();
    // Cancel any fill still running on this canvas, so two quick
    // redraws cannot animate over each other.
    if (canvas._dwFillRaf) cancelAnimationFrame(canvas._dwFillRaf);
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      // easeOutCubic: fast at first, settling at the top - liquid
      // finding its level rather than a linear wipe.
      const eased = 1 - Math.pow(1 - t, 3);
      drawBarChart(canvas, values, labels, { ...opts, fill: eased });
      if (t < 1) canvas._dwFillRaf = requestAnimationFrame(step);
      else canvas._dwFillRaf = null;
    };
    canvas._dwFillRaf = requestAnimationFrame(step);
  }

  window.DWCharts = { drawLineChart, drawBarChart, drawBarChartAnimated };
})();
