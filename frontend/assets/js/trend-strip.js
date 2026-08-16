/*
  Compact wellness-trend strip (A-1).

  The previous chart was a full-size line graph that took a large block of
  the Analytics page and answered almost nothing at a glance: it plotted
  the points and left the reader to eyeball whether things were getting
  better. It also silently dropped the days the user had marked as
  exceptions, so the one chart that should show "which days were unusual"
  was the one place they were invisible.

  This draws the same history in roughly a third of the height and answers
  the two questions the page exists for, before the reader has to
  interpret anything:

    1. Is it going up or down, and by how much? A least-squares fit over
       the real (non-exception) points gives the direction and the change
       across the window, stated in words and points, not left to the eye.
    2. Which days were exceptions? Drawn as hollow, muted markers - present
       so the shape of the month is honest, but visibly not part of the
       trend.

  Exception days are excluded from the fit, the min/max and the reported
  change. A holiday should not bend a slope the app then reports back as a
  behavioural pattern.

  DWTrendStrip.draw(canvas, points, opts)
    points: [{ date, health_score, is_exception }] oldest-first
    -> returns { direction, change, slopePerDay, used, exceptions, best, worst }
       so the caller can render the wording in the user's own language
       (this module deliberately renders no text itself).
*/
(function () {
  const PAD_X = 10;
  const PAD_TOP = 10;
  const PAD_BOTTOM = 16;

  function leastSquaresSlope(values) {
    const n = values.length;
    if (n < 2) return 0;
    const meanX = (n - 1) / 2;
    const meanY = values.reduce((a, b) => a + b, 0) / n;
    let num = 0;
    let den = 0;
    for (let i = 0; i < n; i += 1) {
      num += (i - meanX) * (values[i] - meanY);
      den += (i - meanX) * (i - meanX);
    }
    return den === 0 ? 0 : num / den;
  }

  function cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  function draw(canvas, points, opts) {
    opts = opts || {};
    if (!canvas || !canvas.getContext) return null;

    const all = (points || []).filter((p) => p && typeof p.health_score === 'number');
    const real = all.filter((p) => !p.is_exception);

    // G4: without enough real points there is no trend to state, and
    // inventing a direction from two dots would be exactly the kind of
    // fabricated claim the rest of the app avoids.
    const enough = real.length >= (opts.minPoints || 3);

    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 320;
    const cssH = opts.height || 86;
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    canvas.style.height = cssH + 'px';
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    if (!all.length) return null;

    // Scale to the real points so one wild exception day cannot flatten
    // everything else into a straight line.
    const scaleSource = real.length ? real : all;
    const values = scaleSource.map((p) => p.health_score);
    let lo = Math.min.apply(null, values);
    let hi = Math.max.apply(null, values);
    if (hi - lo < 8) { const mid = (hi + lo) / 2; lo = mid - 4; hi = mid + 4; }
    lo = Math.max(0, lo - 4);
    hi = Math.min(100, hi + 4);

    const plotW = cssW - PAD_X * 2;
    const plotH = cssH - PAD_TOP - PAD_BOTTOM;
    const xAt = (i) => PAD_X + (all.length === 1 ? plotW / 2 : (i / (all.length - 1)) * plotW);
    const yAt = (v) => PAD_TOP + plotH - ((v - lo) / (hi - lo)) * plotH;

    const up = cssVar('--accent-success', '#22f5c6');
    const down = cssVar('--accent-danger', '#ff6b6b');
    const muted = cssVar('--text-muted', '#8b93a7');
    const border = cssVar('--surface-border', '#2a3142');

    const slope = enough ? leastSquaresSlope(real.map((p) => p.health_score)) : 0;
    const direction = !enough ? 'unknown' : (slope > 0.15 ? 'up' : (slope < -0.15 ? 'down' : 'flat'));
    const lineColor = direction === 'up' ? up : direction === 'down' ? down : muted;

    // Baseline at the mean of the real points: the eye reads
    // above/below far faster than it reads absolute height.
    if (enough) {
      const mean = real.reduce((a, p) => a + p.health_score, 0) / real.length;
      ctx.strokeStyle = border;
      ctx.setLineDash([3, 4]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(PAD_X, yAt(mean));
      ctx.lineTo(cssW - PAD_X, yAt(mean));
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // The connecting line follows real points only; an exception day is a
    // gap in the line rather than a spike through it.
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    let started = false;
    all.forEach((p, i) => {
      if (p.is_exception) { started = false; return; }
      const x = xAt(i);
      const y = yAt(p.health_score);
      if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
    });
    ctx.stroke();

    // Markers.
    const bg = cssVar('--bg-1', '#05080f');
    all.forEach((p, i) => {
      const x = xAt(i);
      const y = yAt(p.health_score);
      if (p.is_exception) {
        // Hollow + muted: visible, clearly not part of the trend.
        ctx.beginPath();
        ctx.arc(x, y, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = bg;
        ctx.fill();
        ctx.strokeStyle = muted;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([2, 2]);
        ctx.stroke();
        ctx.setLineDash([]);
      } else {
        ctx.beginPath();
        ctx.arc(x, y, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = lineColor;
        ctx.fill();
      }
    });

    const scores = real.map((p) => p.health_score);
    const best = real.length ? real[scores.indexOf(Math.max.apply(null, scores))] : null;
    const worst = real.length ? real[scores.indexOf(Math.min.apply(null, scores))] : null;

    return {
      direction,
      // Change across the window implied by the fitted line, which is far
      // more stable than last-minus-first on noisy daily data.
      change: enough ? slope * (real.length - 1) : null,
      slopePerDay: enough ? slope : null,
      used: real.length,
      exceptions: all.length - real.length,
      best,
      worst,
    };
  }

  window.DWTrendStrip = { draw };
})();
