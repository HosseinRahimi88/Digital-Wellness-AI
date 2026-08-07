/*
  Shared motion utilities.

  Everything here has exactly one hard rule: **information is never
  withheld by an animation**. In reduced-motion mode (OS setting or the
  in-app toggle) every helper below still puts the final value on screen
  immediately - it just skips the travel. Nothing is hidden waiting for
  a transition that will never run.

  Also: every entrance animation can be skipped by any interaction, and
  is only played once per session per element, so a returning user is
  not forced to sit through the show again.
*/
(function () {
  const REDUCE_KEY = 'dwai_reduce_motion';

  function prefersReduced() {
    if (localStorage.getItem(REDUCE_KEY) === '1') return true;
    if (localStorage.getItem(REDUCE_KEY) === '0') return false;
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function setReduced(on) {
    localStorage.setItem(REDUCE_KEY, on ? '1' : '0');
    document.documentElement.classList.toggle('force-reduce-motion', on);
    document.dispatchEvent(new CustomEvent('dwai:motionchange', { detail: { reduced: on } }));
  }

  function syncReducedClass() {
    document.documentElement.classList.toggle('force-reduce-motion', prefersReduced());
  }

  const easeOutCubic = (p) => 1 - Math.pow(1 - p, 3);

  /* ---- Number count-up ------------------------------------------- */
  function countUp(el, to, opts) {
    opts = opts || {};
    const decimals = opts.decimals || 0;
    const duration = opts.duration || 1200;
    const format = opts.format || ((v) => v.toFixed(decimals));
    const from = opts.from || 0;

    if (prefersReduced()) { el.textContent = format(to); return; }

    const start = performance.now();
    function frame(now) {
      const p = Math.min(1, (now - start) / duration);
      el.textContent = format(from + (to - from) * easeOutCubic(p));
      if (p < 1) requestAnimationFrame(frame);
      else el.textContent = format(to);
    }
    requestAnimationFrame(frame);
  }

  /* ---- Staggered entrance ---------------------------------------- */
  function stagger(elements, opts) {
    opts = opts || {};
    const gap = opts.gap || 70;
    const list = Array.from(elements);
    if (prefersReduced()) {
      list.forEach((el) => el.classList.add('is-in'));
      return;
    }
    list.forEach((el, i) => {
      el.classList.add('stagger-item');
      el.style.setProperty('--stagger-delay', `${i * gap}ms`);
      requestAnimationFrame(() => el.classList.add('is-in'));
    });
  }

  /* ---- Reveal on scroll ------------------------------------------ */
  function observeReveals(root) {
    const scope = root || document;
    const els = scope.querySelectorAll('.reveal:not(.is-visible)');
    if (prefersReduced()) {
      els.forEach((el) => el.classList.add('is-visible'));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    els.forEach((el) => io.observe(el));
  }

  /* ---- Wave-filling bars ----------------------------------------- *
     A bar is a <div class="wave-bar"> with a --fill (0..1). The liquid
     surface is drawn on a tiny canvas so the crest can keep a small
     residual ripple after settling, which pure CSS cannot do.
     Fill only starts once the bar scrolls into view.                  */
  function waveFill(el, ratio, opts) {
    opts = opts || {};
    const delay = opts.delay || 0;
    const duration = opts.duration || 1100;
    const target = Math.max(0, Math.min(1, ratio || 0));
    const vertical = !!opts.vertical;

    if (el.__waveStop) el.__waveStop();

    if (prefersReduced()) {
      // Show the value immediately, no travel, no ripple.
      el.style.setProperty('--fill', target);
      el.classList.add('is-filled');
      return;
    }

    let canvas = el.querySelector('canvas.wave-surface');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.className = 'wave-surface';
      canvas.setAttribute('aria-hidden', 'true');
      el.appendChild(canvas);
    }
    const ctx = canvas.getContext('2d');

    let raf = null, startTs = null, current = 0, stopped = false;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    function size() {
      const r = el.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(r.width * dpr));
      canvas.height = Math.max(1, Math.round(r.height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      return r;
    }
    let rect = size();

    // A bar rendered while its container is still display:none measures
    // 0x0 and would draw nothing forever. Re-measure once it actually
    // has a box, then carry on.
    if (rect.width < 2 || rect.height < 1) {
      const ro = new ResizeObserver(() => {
        const r = size();
        if (r.width >= 2 && r.height >= 1) { rect = r; ro.disconnect(); }
      });
      ro.observe(el);
    }

    function palette() {
      const s = getComputedStyle(el);
      return {
        a: (s.getPropertyValue('--wave-a') || '#22f5c6').trim(),
        b: (s.getPropertyValue('--wave-b') || '#3aa7ff').trim(),
      };
    }

    function draw(ts) {
      if (stopped) return;
      if (startTs === null) startTs = ts + delay;
      const elapsed = ts - startTs;
      const p = elapsed <= 0 ? 0 : Math.min(1, elapsed / duration);
      current = target * easeOutCubic(p);

      const w = rect.width, h = rect.height;
      ctx.clearRect(0, 0, w, h);

      // Horizontal bars must fill from the right in RTL so the motion
      // reads the same way the text does.
      const rtl = document.documentElement.getAttribute('dir') === 'rtl';
      const { a, b } = palette();
      const grad = vertical
        ? ctx.createLinearGradient(0, h, 0, 0)
        : (rtl ? ctx.createLinearGradient(w, 0, 0, 0) : ctx.createLinearGradient(0, 0, w, 0));
      grad.addColorStop(0, a);
      grad.addColorStop(1, b);
      ctx.fillStyle = grad;

      // Residual ripple: large while filling, small but never zero once
      // settled - "settled liquid, not frozen".
      const settle = p >= 1 ? 0.35 : 1;
      const amp = (vertical ? w : h) * 0.16 * settle;
      const time = ts / 1000;

      ctx.beginPath();
      if (vertical) {
        const level = h - current * h;
        ctx.moveTo(0, h);
        for (let x = 0; x <= w; x += 2) {
          const y = level + Math.sin(x / 14 + time * 2.1) * amp * 0.5
                          + Math.sin(x / 7 - time * 1.3) * amp * 0.25;
          ctx.lineTo(x, y);
        }
        ctx.lineTo(w, h);
      } else if (rtl) {
        // Anchored to the right edge, crest travelling leftwards.
        const level = w - current * w;
        ctx.moveTo(w, 0);
        ctx.lineTo(w, h);
        for (let y = h; y >= 0; y -= 2) {
          const x = level - Math.sin(y / 9 + time * 2.4) * amp * 0.5
                          - Math.sin(y / 5 - time * 1.6) * amp * 0.25;
          ctx.lineTo(x, y);
        }
      } else {
        const level = current * w;
        ctx.moveTo(0, 0);
        ctx.lineTo(0, h);
        for (let y = h; y >= 0; y -= 2) {
          const x = level + Math.sin(y / 9 + time * 2.4) * amp * 0.5
                          + Math.sin(y / 5 - time * 1.6) * amp * 0.25;
          ctx.lineTo(x, y);
        }
      }
      ctx.closePath();
      ctx.fill();

      // Fine droplet texture along the crest so the surface reads as
      // liquid rather than a flat gradient edge.
      ctx.globalAlpha = 0.5;
      const dots = vertical ? Math.round(w / 10) : Math.round(h / 8);
      for (let i = 0; i < dots; i++) {
        if (vertical) {
          const x = (i / dots) * w + (Math.sin(time + i) * 3);
          const level = h - current * h;
          const y = level + Math.sin(x / 14 + time * 2.1) * amp * 0.5 - 2 - (i % 3);
          if (y < h && y > 0) { ctx.beginPath(); ctx.arc(x, y, 0.9, 0, Math.PI * 2); ctx.fill(); }
        } else {
          const y = (i / dots) * h + (Math.sin(time + i) * 2);
          const level = rtl ? (w - current * w) : (current * w);
          const crest = rtl
            ? level - Math.sin(y / 9 + time * 2.4) * amp * 0.5 + 2 + (i % 3)
            : level + Math.sin(y / 9 + time * 2.4) * amp * 0.5 - 2 - (i % 3);
          if (crest > 0 && crest < w) { ctx.beginPath(); ctx.arc(crest, y, 0.9, 0, Math.PI * 2); ctx.fill(); }
        }
      }
      ctx.globalAlpha = 1;

      raf = requestAnimationFrame(draw);
    }

    el.__waveStop = () => { stopped = true; if (raf) cancelAnimationFrame(raf); };
    el.classList.add('is-filled');

    const onResize = () => { rect = size(); };
    window.addEventListener('resize', onResize, { passive: true });

    raf = requestAnimationFrame(draw);
  }

  /* Fill bars only once they enter the viewport, staggered in DOM order. */
  function waveFillOnView(container, selector, opts) {
    opts = opts || {};
    const gap = opts.gap || 130;
    const bars = Array.from((container || document).querySelectorAll(selector));
    if (!bars.length) return;

    const run = (bar, i) => waveFill(bar, parseFloat(bar.dataset.fill || '0'), {
      delay: i * gap, vertical: bar.dataset.vertical === 'true',
    });

    if (prefersReduced()) { bars.forEach((b, i) => run(b, i)); return; }

    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        run(e.target, bars.indexOf(e.target));
      });
    }, { threshold: 0.25 });
    bars.forEach((b) => io.observe(b));
  }

  /* ---- Ring draw (score circle) ---------------------------------- */
  function drawRing(circleEl, ratio, opts) {
    opts = opts || {};
    const r = circleEl.r.baseVal.value;
    const circumference = 2 * Math.PI * r;
    const offset = circumference * (1 - Math.max(0, Math.min(1, ratio)));
    circleEl.style.strokeDasharray = String(circumference);
    if (prefersReduced()) {
      circleEl.style.transition = 'none';
      circleEl.style.strokeDashoffset = String(offset);
      return;
    }
    circleEl.style.transition = 'none';
    circleEl.style.strokeDashoffset = String(circumference);
    requestAnimationFrame(() => {
      circleEl.style.transition = `stroke-dashoffset ${opts.duration || 1400}ms cubic-bezier(.16,1,.3,1)`;
      circleEl.style.strokeDashoffset = String(offset);
    });
  }

  syncReducedClass();
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => syncReducedClass();
    mq.addEventListener ? mq.addEventListener('change', onChange) : mq.addListener(onChange);
  }

  window.DWMotion = {
    prefersReduced, setReduced, syncReducedClass,
    countUp, stagger, observeReveals, waveFill, waveFillOnView, drawRing,
  };
})();
