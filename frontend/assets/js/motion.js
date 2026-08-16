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

  /* ---- Glass progress bars ---------------------------------------- *
     A bar is a <div class="wave-bar"> whose fill is a single child
     element animated by a CSS transform.

     This replaced an earlier canvas "liquid wave" renderer. Two reasons
     the canvas version was retired, both worth keeping written down:
       1. Product direction - the wave read as dated next to the rest of
          the glass UI, and the per-frame ripple kept drawing forever on
          every visible bar even after settling.
       2. Cost - every bar held its own rAF loop and 2D context for an
          animation that conveys exactly one number. A GPU-composited
          transform gives the same information for effectively no
          per-frame main-thread work.

     The public signature is unchanged (waveFill / waveFillOnView), so
     every existing call site keeps working untouched. `vertical` bars
     grow upward; horizontal bars grow from the inline-start edge, which
     is automatically the right edge in RTL because the fill is anchored
     with `inset-inline-start`.                                        */
  function waveFill(el, ratio, opts) {
    opts = opts || {};
    const delay = opts.delay || 0;
    const duration = opts.duration || 1100;
    const target = Math.max(0, Math.min(1, ratio || 0));
    const vertical = !!opts.vertical;

    // Retire any canvas left over from the previous renderer so a bar
    // re-rendered in the same session doesn't stack the two.
    if (el.__waveStop) { el.__waveStop(); el.__waveStop = null; }
    const legacyCanvas = el.querySelector('canvas.wave-surface');
    if (legacyCanvas) legacyCanvas.remove();

    let fill = el.querySelector('.glass-fill');
    if (!fill) {
      fill = document.createElement('span');
      fill.className = 'glass-fill';
      fill.setAttribute('aria-hidden', 'true');
      el.appendChild(fill);
    }
    el.classList.toggle('is-vertical', vertical);
    el.classList.add('is-filled');
    el.style.setProperty('--fill', target);

    const axis = vertical ? 'scaleY' : 'scaleX';
    // Start collapsed, then grow. Set the start state without a
    // transition so it can never animate backwards from a stale value.
    fill.style.transition = 'none';
    fill.style.transform = `${axis}(0)`;

    if (prefersReduced()) {
      // Final value immediately - the number is never withheld.
      fill.style.transform = `${axis}(${target})`;
      return;
    }

    requestAnimationFrame(() => {
      fill.style.transition = `transform ${duration}ms cubic-bezier(.16,1,.3,1) ${delay}ms`;
      fill.style.transform = `${axis}(${target})`;
    });
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
