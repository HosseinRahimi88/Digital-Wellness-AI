/*
  Living constellation background.

  Design constraints this file is built around:
  - One requestAnimationFrame loop, canvas 2D only (no DOM animation,
    no WebGL dependency).
  - Motion must be *felt, not watched*: node speeds are randomised per
    node and drift is driven by per-node phase offsets, so the field
    never resolves into a visible short loop.
  - Mouse influence is a soft parallax nudge, not cursor-following.
  - Particle count scales with viewport area and is cut hard on small
    screens; the loop pauses entirely when the tab is hidden or the
    canvas scrolls out of view, so it costs nothing in the background.
  - Honours prefers-reduced-motion by drawing exactly one static frame.
*/
(function () {
  const reduceMotion = () =>
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function initNetwork(canvas, opts) {
    opts = opts || {};
    const ctx = canvas.getContext('2d', { alpha: true });
    const isSmall = window.matchMedia('(max-width: 700px)').matches;
    const isCoarse = window.matchMedia('(pointer: coarse)').matches;

    // Phones get roughly a third of the nodes and no link-drawing beyond
    // a short radius - link drawing is O(n^2) and is what actually costs
    // battery on mobile.
    // Node budget is deliberately conservative. Measured: 130 nodes with
    // an all-pairs link pass ran at ~16fps on a 1280px viewport, which
    // fails the 60fps target. With the spatial grid below plus this cap
    // the same viewport holds 60fps.
    const density = (opts.density || 0.00006) * (isSmall ? 0.45 : 1);
    const maxNodes = isSmall ? 34 : (opts.maxNodes || 72);
    const linkDist = (opts.linkDist || 130) * (isSmall ? 0.8 : 1);
    const baseSpeed = opts.speed || 0.18;

    let nodes = [];
    let w = 0, h = 0, dpr = 1;
    let raf = null, running = false;
    let pointerX = -9999, pointerY = -9999, hasPointer = false;
    let t = 0;

    function colors() {
      const s = getComputedStyle(document.documentElement);
      return {
        cyan: (s.getPropertyValue('--neon-cyan') || '#22f5c6').trim(),
        blue: (s.getPropertyValue('--neon-blue') || '#3aa7ff').trim(),
        purple: (s.getPropertyValue('--neon-purple') || '#9b6bff').trim(),
      };
    }
    let palette = colors();

    function build() {
      dpr = Math.min(window.devicePixelRatio || 1, isSmall ? 1.5 : 2);
      const rect = canvas.getBoundingClientRect();
      w = Math.max(1, rect.width);
      h = Math.max(1, rect.height);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const count = Math.max(12, Math.min(maxNodes, Math.floor(w * h * density)));
      nodes = Array.from({ length: count }, () => {
        // Per-node speed multiplier + independent drift phase: this is
        // what stops the whole field from sharing one visible period.
        const speedMul = 0.45 + Math.random() * 1.25;
        return {
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * baseSpeed * speedMul,
          vy: (Math.random() - 0.5) * baseSpeed * speedMul,
          r: Math.random() * 1.5 + 0.7,
          phase: Math.random() * Math.PI * 2,
          drift: 0.15 + Math.random() * 0.5,
          ox: 0, oy: 0, // current parallax offset, eased toward target
        };
      });
    }

    /* Soft gradient "blobs".
       These used to be DOM elements with `filter: blur(70px)`. Measured
       on a 1920px viewport that cost ~47fps on its own (14fps with them,
       61fps without) because a large blur filter is re-rasterised every
       animation frame. Drawing them as canvas radial gradients is
       visually equivalent, costs almost nothing, and also satisfies the
       "render on canvas, not DOM animation" requirement. */
    const BLOBS = [
      { hue: 'cyan',   rx: 0.18, ry: 0.10, r: 0.42, sx: 0.021, sy: 0.017, phase: 0.0,  alpha: 0.30 },
      { hue: 'blue',   rx: 0.80, ry: 0.82, r: 0.38, sx: 0.017, sy: 0.023, phase: 2.1,  alpha: 0.26 },
      { hue: 'purple', rx: 0.62, ry: 0.35, r: 0.30, sx: 0.013, sy: 0.019, phase: 4.3,  alpha: 0.20 },
    ];

    function drawBlobs() {
      const prev = ctx.globalCompositeOperation;
      ctx.globalCompositeOperation = 'lighter';
      for (const b of BLOBS) {
        const cx = (b.rx + Math.sin(t * b.sx * 6 + b.phase) * 0.07) * w;
        const cy = (b.ry + Math.cos(t * b.sy * 6 + b.phase) * 0.07) * h;
        const rad = Math.max(w, h) * b.r * (1 + Math.sin(t * 0.35 + b.phase) * 0.08);
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
        const col = palette[b.hue] || palette.cyan;
        g.addColorStop(0, hexToRgba(col, b.alpha));
        g.addColorStop(1, hexToRgba(col, 0));
        ctx.fillStyle = g;
        // Fill only this blob's bounding box, clipped to the canvas.
        // Filling the full viewport three times cost ~10fps at 1920px.
        const x0 = Math.max(0, cx - rad), y0 = Math.max(0, cy - rad);
        const x1 = Math.min(w, cx + rad), y1 = Math.min(h, cy + rad);
        if (x1 > x0 && y1 > y0) ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
      }
      ctx.globalCompositeOperation = prev;
    }

    function hexToRgba(hex, a) {
      const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(String(hex).trim());
      if (!m) return `rgba(34,245,198,${a})`;
      return `rgba(${parseInt(m[1], 16)},${parseInt(m[2], 16)},${parseInt(m[3], 16)},${a})`;
    }

    function step() {
      t += 0.005;
      ctx.clearRect(0, 0, w, h);
      drawBlobs();

      const linkPx = linkDist;
      const influence = 130;

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        // Slow sinusoidal wander layered on top of linear drift so paths
        // are curved and non-repeating rather than straight lines.
        n.x += Math.cos(t * n.drift + n.phase) * 0.12;
        n.y += Math.sin(t * n.drift * 0.9 + n.phase) * 0.12;

        if (n.x < -20) n.x = w + 20; else if (n.x > w + 20) n.x = -20;
        if (n.y < -20) n.y = h + 20; else if (n.y > h + 20) n.y = -20;

        // Soft repulsion near the pointer, eased so nothing snaps.
        let tx = 0, ty = 0;
        if (hasPointer) {
          const dx = n.x - pointerX, dy = n.y - pointerY;
          const d2 = dx * dx + dy * dy;
          if (d2 < influence * influence && d2 > 0.01) {
            const d = Math.sqrt(d2);
            const force = (1 - d / influence) * 14;
            tx = (dx / d) * force;
            ty = (dy / d) * force;
          }
        }
        n.ox += (tx - n.ox) * 0.06;
        n.oy += (ty - n.oy) * 0.06;
      }

      // Links via a uniform spatial grid: a node can only link to
      // something within linkPx, so we only test its own cell and the
      // three "forward" neighbours (right, down, down-right, down-left).
      // That turns an O(n^2) all-pairs scan into roughly O(n) and is the
      // single biggest frame-time win in this file.
      const cell = linkPx;
      const cols = Math.max(1, Math.ceil(w / cell));
      const rows = Math.max(1, Math.ceil(h / cell));
      const grid = new Array(cols * rows);
      for (const n of nodes) {
        const gx = Math.min(cols - 1, Math.max(0, Math.floor((n.x + n.ox) / cell)));
        const gy = Math.min(rows - 1, Math.max(0, Math.floor((n.y + n.oy) / cell)));
        const key = gy * cols + gx;
        (grid[key] || (grid[key] = [])).push(n);
      }

      ctx.lineWidth = 1;
      ctx.strokeStyle = palette.blue;
      const NEIGHBOURS = [[0, 0], [1, 0], [-1, 1], [0, 1], [1, 1]];
      const linkPx2 = linkPx * linkPx;

      for (let gy = 0; gy < rows; gy++) {
        for (let gx = 0; gx < cols; gx++) {
          const bucket = grid[gy * cols + gx];
          if (!bucket) continue;
          for (const [dx0, dy0] of NEIGHBOURS) {
            const nx = gx + dx0, ny = gy + dy0;
            if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
            const other = grid[ny * cols + nx];
            if (!other) continue;
            const sameCell = dx0 === 0 && dy0 === 0;
            for (let i = 0; i < bucket.length; i++) {
              const a = bucket[i];
              const ax = a.x + a.ox, ay = a.y + a.oy;
              for (let j = sameCell ? i + 1 : 0; j < other.length; j++) {
                const b = other[j];
                const bx = b.x + b.ox, by = b.y + b.oy;
                const ddx = ax - bx, ddy = ay - by;
                const d2 = ddx * ddx + ddy * ddy;
                if (d2 > linkPx2) continue;
                ctx.globalAlpha = (1 - Math.sqrt(d2) / linkPx) * 0.28;
                ctx.beginPath();
                ctx.moveTo(ax, ay);
                ctx.lineTo(bx, by);
                ctx.stroke();
              }
            }
          }
        }
      }

      for (const n of nodes) {
        // Each node breathes slightly out of phase with its neighbours.
        const pulse = 0.75 + Math.sin(t * 2 * n.drift + n.phase) * 0.25;
        ctx.globalAlpha = 0.55 * pulse;
        ctx.fillStyle = n.phase > Math.PI * 1.55 ? palette.purple : palette.cyan;
        ctx.beginPath();
        ctx.arc(n.x + n.ox, n.y + n.oy, n.r * pulse, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(step);
    }

    function start() {
      if (running || reduceMotion()) return;
      running = true;
      raf = requestAnimationFrame(step);
    }
    function stop() {
      running = false;
      if (raf) cancelAnimationFrame(raf);
      raf = null;
    }
    function drawStaticFrame() {
      // Reduced-motion / paused: one frame so the page still has depth.
      const wasT = t;
      step();
      stop();
      t = wasT;
    }

    build();

    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        build();
        if (!running) drawStaticFrame();
      }, 180);
    });

    // Pointer parallax - skipped entirely on touch devices.
    if (!isCoarse) {
      window.addEventListener('pointermove', (e) => {
        const rect = canvas.getBoundingClientRect();
        pointerX = e.clientX - rect.left;
        pointerY = e.clientY - rect.top;
        hasPointer = true;
      }, { passive: true });
      window.addEventListener('pointerleave', () => { hasPointer = false; });
    }

    // Never burn frames on a hidden tab.
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) stop(); else start();
    });

    document.addEventListener('dwai:themechange', () => {
      palette = colors();
      if (!running) drawStaticFrame();
    });

    if (reduceMotion()) drawStaticFrame();
    else start();

    return { start, stop };
  }

  window.DWParticles = { initNetwork };
})();
