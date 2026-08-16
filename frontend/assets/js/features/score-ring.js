/*
  Multi-arc score ring for the result page.

  The centre shows the REAL trained-model regression score for TODAY -
  bold, and coloured by its band (80+/60-79/below 60), with the band
  named in words underneath and the model's calibrated interval on the
  line below that.

  Each dimension's own number sits on its own arc rather than in a
  legend below the ring, so nobody has to map four colours back onto
  four shapes. The average-of-arcs chip that used to sit in the centre
  is gone with it: once all four numbers are visible, their average is
  a fifth number that answers nothing and it collided with the interval.

  Each arc gets its own gradient and a moving "water" shimmer (a short
  dash pattern animated forever via CSS), so filling reads as liquid
  moving through a glass tube rather than a bar chart. A dimension with
  no data is drawn as an empty, dashed placeholder arc instead of a
  fabricated value.
*/
(function () {
  const ARC_ORDER = [
    { key: 'emotional', fallbackLabel: 'Life wellbeing', colorA: '#ff6fb0', colorB: '#a06bff' },
    { key: 'sleep', fallbackLabel: 'Sleep health', colorA: '#6ea8ff', colorB: '#7ffbe0' },
    { key: 'screen_habits', fallbackLabel: 'Digital health', colorA: '#22f5c6', colorB: '#2fd0ff' },
    { key: 'focus', fallbackLabel: 'Focus & mind', colorA: '#ffd166', colorB: '#ff9a3c' },
  ];
  const GAP_DEG = 8;
  const ARC_DEG = (360 - ARC_ORDER.length * GAP_DEG) / ARC_ORDER.length;
  const R = 82;
  const CX = 100, CY = 100;

  function polarToCartesian(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function describeArc(startAngle, endAngle, radius) {
    const r = radius || R;
    const s = polarToCartesian(CX, CY, r, startAngle);
    const e = polarToCartesian(CX, CY, r, endAngle);
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    return `M ${s.x.toFixed(2)} ${s.y.toFixed(2)} A ${r} ${r} 0 ${largeArc} 1 ${e.x.toFixed(2)} ${e.y.toFixed(2)}`;
  }

  /* Uncertainty band (C-6-3). The four outer arcs are the dimension
     breakdown, so the score's own confidence interval gets its own inner
     track at a smaller radius rather than competing with them. The track
     is the whole 0-100 scale; the highlighted span is the interval; a tick
     marks the point estimate inside it.

     The interval comes from the API's conformal uncertainty service, which
     calibrates on the VALIDATION split - the test set is single-use and is
     never involved. Nothing here recomputes or adjusts a model number; it
     only draws one the server already produced. */
  const R_RANGE = 64;
  const scoreToAngle = (s) => Math.max(0, Math.min(100, s)) * 3.6;

  /* The three bands the whole app agrees on: 80+ healthy, 60-79
     moderate, below 60 needs attention. They were previously 66/40 here
     and nowhere else, so the colour of the centre number disagreed with
     every other surface's idea of a good day. */
  const BANDS = [
    { min: 80, key: 'healthy', color: 'var(--accent-success, #22f5c6)' },
    { min: 60, key: 'moderate', color: 'var(--accent-amber, #ffd166)' },
    { min: 0, key: 'attention', color: 'var(--accent-danger, #ff6b6b)' },
  ];
  const BAND_LABELS = {
    healthy: { en: 'Healthy', fa: 'سالم', ar: 'صحي', zh: '健康' },
    moderate: { en: 'Moderate', fa: 'متوسط', ar: 'متوسط', zh: '中等' },
    attention: { en: 'Needs attention', fa: 'نیازمند توجه', ar: 'يحتاج انتباهاً', zh: '需要关注' },
  };

  function bandFor(score) {
    return BANDS.find((b) => score >= b.min) || BANDS[BANDS.length - 1];
  }

  const pick = (table) =>
    (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(table) : table.en);

  function describeRangeBand(lower, upper) {
    // A 360-degree sweep cannot be one arc (start would equal end), and an
    // interval that wide would be meaningless anyway - clamp it.
    const a1 = scoreToAngle(lower);
    const a2 = Math.min(scoreToAngle(upper), a1 + 359);
    if (a2 - a1 < 0.5) return null;  // too narrow to render as a band
    return describeArc(a1, a2, R_RANGE);
  }

  function slotAngles(index) {
    const start = index * (ARC_DEG + GAP_DEG);
    return { start, end: start + ARC_DEG };
  }

  let uid = 0;

  /*
    render(wrapEl, { score, dimensions, reduced, onArcComplete })
    - wrapEl: the container that currently holds the old single-circle
      markup (e.g. `.score-ring-wrap`); its content is fully replaced.
    - dimensions: the real `dimension_breakdown.dimensions` array from
      the API (never fabricated - arcs for missing dimensions render
      empty).
  */
  function render(wrapEl, opts) {
    opts = opts || {};
    const score = Math.max(0, Math.min(100, opts.score || 0));
    const dims = {};
    (opts.dimensions || []).forEach((d) => { dims[d.key] = d; });
    const reduced = !!(window.DWMotion && window.DWMotion.prefersReduced());
    const instance = ++uid;

    const available = ARC_ORDER.filter((a) => dims[a.key]);
    const avg = available.length
      ? available.reduce((sum, a) => sum + dims[a.key].score, 0) / available.length
      : null;

    const svgNS = 'http://www.w3.org/2000/svg';
    let defs = '';
    let arcs = '';
    ARC_ORDER.forEach((arc, i) => {
      const gradId = `ringGrad_${instance}_${i}`;
      defs += `<linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="${arc.colorA}"/>
        <stop offset="100%" stop-color="${arc.colorB}"/>
      </linearGradient>`;
      const { start, end } = slotAngles(i);
      const d = describeArc(start, end);
      const dim = dims[arc.key];
      const hasData = !!dim;
      arcs += `
        <path class="ring-arc-track" d="${d}"></path>
        ${hasData ? `
        <path class="ring-arc-fill" data-arc-key="${arc.key}" data-index="${i}"
              d="${d}" stroke="url(#${gradId})"></path>
        <path class="ring-arc-shimmer" data-index="${i}" d="${d}" stroke="${arc.colorA}"></path>
        ` : `<path class="ring-arc-empty" d="${d}"></path>`}
      `;
    });

    /* C-6-3: present the score as the interval it actually is. The model
       has a known average error, so a bare "93" claims a precision it does
       not have. The interval becomes the headline; the point estimate stays
       visible beneath it, because the interval is meaningless without it
       and every other page still shows the single number. */
    const range = opts.range || null;
    const hasRange = !!(range
      && typeof range.lower === 'number' && typeof range.upper === 'number'
      && range.upper >= range.lower);
    const lo = hasRange ? Math.round(range.lower) : null;
    const hi = hasRange ? Math.round(range.upper) : null;
    const t = (key, fallback) => (window.DWI18n && window.DWI18n.t(key)) || fallback;

    /* The inner ring is drawn as a 0-100 gauge, not just a floating band.
       A bare arc segment sitting at some angle communicates nothing - the
       viewer has no scale to read it against. Filling from 0 (top,
       clockwise) up to the score makes the position meaningful, and the
       translucent band across lower..upper then reads as "give or take
       this much" at the end of the fill. */
    let rangeBand = '';
    if (hasRange) {
      const bandPath = describeRangeBand(range.lower, range.upper);
      const scoreAngle = scoreToAngle(score);
      const progressPath = scoreAngle > 0.5 ? describeArc(0, scoreAngle, R_RANGE) : null;
      const tick = polarToCartesian(CX, CY, R_RANGE - 5, scoreAngle);
      const tickOuter = polarToCartesian(CX, CY, R_RANGE + 5, scoreAngle);
      rangeBand = `
        <circle class="ring-range-track" cx="${CX}" cy="${CY}" r="${R_RANGE}"></circle>
        ${progressPath ? `<path class="ring-range-progress" d="${progressPath}"></path>` : ''}
        ${bandPath ? `<path class="ring-range-band" d="${bandPath}"></path>` : ''}
        <line class="ring-range-tick"
              x1="${tick.x.toFixed(2)}" y1="${tick.y.toFixed(2)}"
              x2="${tickOuter.x.toFixed(2)}" y2="${tickOuter.y.toFixed(2)}"></line>
      `;
    }

    const band = bandFor(score);

    /* Each dimension's number sits on its own arc rather than in a
       legend underneath. The position is the arc's own midpoint angle
       at a slightly larger radius, converted to a percentage of the
       200x200 viewBox so plain HTML can be placed over the SVG and stay
       aligned at any size. A legend below the ring made the reader map
       four colours back onto four arcs; this removes that step. */
    const dimensionLabels = `<div class="ring-dim-labels">` + ARC_ORDER.map((arc, i) => {
      const dim = dims[arc.key];
      const { start, end } = slotAngles(i);
      const mid = (start + end) / 2;
      const point = polarToCartesian(CX, CY, R + 21, mid);
      const label = (window.DWI18n && window.DWI18n.t('dim_' + arc.key)) || arc.fallbackLabel;
      const value = dim ? Math.round(dim.score) : null;
      return `
        <span class="ring-dim ${dim ? '' : 'is-empty'}"
              style="left:${(point.x / 2).toFixed(2)}%; top:${(point.y / 2).toFixed(2)}%; --dot:${arc.colorA}"
              data-dim-key="${arc.key}" tabindex="0" role="button">
          <span class="ring-dim-value" dir="ltr">${value == null ? '—' : value}</span>
          <span class="ring-dim-label">${label}</span>
        </span>`;
    }).join('') + `</div>`;

    wrapEl.innerHTML = `
      <svg viewBox="0 0 200 200" class="score-ring-svg">
        <defs>${defs}</defs>
        ${arcs}
        ${rangeBand}
      </svg>
      <div class="score-center">
        <div class="score-big" id="scoreNum" aria-label="${t('result_score_label', 'Wellness score')}">--</div>
        <div class="score-band" id="scoreBand">${pick(BAND_LABELS[band.key])}</div>
        ${hasRange ? `
          <div class="score-range-sub" id="scoreRange">${lo}<span class="dash">–</span>${hi}
            <span class="score-range-word">${t('score_range_label', 'likely range')}</span>
          </div>
        ` : ''}
      </div>
      ${dimensionLabels}
    `;

    /* The number is the headline again, bold and centred, coloured by
       the band it falls in - and the band is named in words underneath,
       because a colour alone is not a reading and is invisible to
       anyone who cannot see it. The interval stays, one line down: the
       score is still not exact, and C-6-3 does not stop applying just
       because the number moved. */
    const numEl = wrapEl.querySelector('#scoreNum');
    if (numEl) numEl.style.color = band.color;
    const bandEl = wrapEl.querySelector('#scoreBand');
    if (bandEl) bandEl.style.color = band.color;

    // Draw each real arc from empty to its dimension score, staggered so
    // they read left-to-right rather than all landing at once; the
    // shimmer arc is a purely decorative animated dash riding on top.
    let completed = 0;
    ARC_ORDER.forEach((arc, i) => {
      const dim = dims[arc.key];
      if (!dim) return;
      const fillPath = wrapEl.querySelector(`.ring-arc-fill[data-index="${i}"]`);
      const shimmerPath = wrapEl.querySelector(`.ring-arc-shimmer[data-index="${i}"]`);
      if (!fillPath) return;
      const total = fillPath.getTotalLength();
      const frac = Math.max(0, Math.min(1, dim.score / 100));
      fillPath.style.strokeDasharray = String(total);
      fillPath.style.strokeDashoffset = String(total);
      if (shimmerPath) {
        const shimmerTotal = shimmerPath.getTotalLength();
        shimmerPath.style.strokeDasharray = `${shimmerTotal * 0.04} ${shimmerTotal * 0.09}`;
      }
      const delay = i * 260;
      const finish = () => {
        completed += 1;
        if (window.DWSound) window.DWSound.ding();
        if (completed === available.length && typeof opts.onAllArcsComplete === 'function') {
          opts.onAllArcsComplete();
        }
      };
      if (reduced) {
        fillPath.style.transition = 'none';
        fillPath.style.strokeDashoffset = String(total * (1 - frac));
        finish();
        return;
      }
      fillPath.addEventListener('transitionend', function handler(e) {
        if (e.propertyName !== 'stroke-dashoffset') return;
        fillPath.removeEventListener('transitionend', handler);
        finish();
      });
      setTimeout(() => {
        fillPath.style.transition = `stroke-dashoffset 1300ms cubic-bezier(.16,1,.3,1)`;
        fillPath.style.strokeDashoffset = String(total * (1 - frac));
      }, delay);
    });

    if (window.DWMotion && numEl) {
      // When the interval is the headline, the point estimate keeps its "≈"
      // through the whole count-up - countUp writes textContent every frame,
      // so the prefix has to come from the formatter rather than the markup.
      window.DWMotion.countUp(numEl, score, {
        decimals: 0,
        duration: 1400,
        format: hasRange
          ? (v) => `≈ ${v.toFixed(0)}`
          : undefined,
      });
    }
    if (!available.length && typeof opts.onAllArcsComplete === 'function') opts.onAllArcsComplete();

    return { average: avg };
  }

  window.DWScoreRing = { render, ARC_ORDER };
})();
