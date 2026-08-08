/*
  Sound effects engine: short, synthesized one-shot cues (Web Audio API
  oscillators only - no external audio files, same "no external
  dependency" pattern as music-player.js). Separate on/off switch from
  the ambient music player, because a user may want one without the
  other (e.g. music off, but still wants the arc "ding" during a
  result reveal).

  Every public function is a no-op when sound effects are disabled or
  when the browser has no AudioContext, so call sites never need to
  guard themselves.
*/
(function () {
  const KEY = 'dwai_sound_fx';
  let ctx = null;
  let processingNodes = null;
  let lastWaterTick = 0;

  function isEnabled() {
    const v = localStorage.getItem(KEY);
    return v === null ? true : v === '1';
  }

  function setEnabled(on) {
    localStorage.setItem(KEY, on ? '1' : '0');
    if (!on) stopProcessing();
    document.dispatchEvent(new CustomEvent('dwai:soundfxchange', { detail: { enabled: on } }));
  }

  function ensureCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  function tone(freq, opts) {
    if (!isEnabled()) return;
    opts = opts || {};
    let c;
    try { c = ensureCtx(); } catch (e) { return; }
    const t0 = c.currentTime + (opts.start || 0);
    const duration = opts.duration || 0.25;
    const osc = c.createOscillator();
    osc.type = opts.type || 'sine';
    osc.frequency.setValueAtTime(freq, t0);
    if (opts.glideTo) osc.frequency.exponentialRampToValueAtTime(opts.glideTo, t0 + duration);
    const gain = c.createGain();
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, opts.gain || 0.2), t0 + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    let tail = osc;
    if (opts.filterFreq) {
      const filter = c.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = opts.filterFreq;
      osc.connect(filter);
      tail = filter;
    }
    tail.connect(gain).connect(c.destination);
    osc.start(t0);
    osc.stop(t0 + duration + 0.06);
  }

  /* A soft, breathing low hum for the duration of a prediction/processing
     screen - stopped explicitly when the screen closes, never left
     running past its owner. */
  function processingStart() {
    if (!isEnabled()) return;
    let c;
    try { c = ensureCtx(); } catch (e) { return; }
    stopProcessing();
    const osc = c.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = 112;
    const lfo = c.createOscillator();
    lfo.frequency.value = 0.55;
    const lfoGain = c.createGain();
    lfoGain.gain.value = 30;
    lfo.connect(lfoGain).connect(osc.frequency);
    const filter = c.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 480;
    const gain = c.createGain();
    gain.gain.value = 0;
    osc.connect(filter).connect(gain).connect(c.destination);
    osc.start();
    lfo.start();
    gain.gain.linearRampToValueAtTime(0.05, c.currentTime + 1.1);
    processingNodes = { osc, lfo, gain };
  }

  function stopProcessing() {
    if (!processingNodes) return;
    const nodes = processingNodes;
    processingNodes = null;
    try {
      const c = ensureCtx();
      nodes.gain.gain.linearRampToValueAtTime(0, c.currentTime + 0.35);
    } catch (e) {}
    setTimeout(() => {
      try { nodes.osc.stop(); } catch (e) {}
      try { nodes.lfo.stop(); } catch (e) {}
    }, 420);
  }

  /* A soft blip while a bar/arc fills, pitch tracking progress. Throttled
     by the caller's own animation frame cadence; also self-throttles so a
     burst of calls in one frame never turns into a buzz. */
  function waterTick(progressFraction) {
    const now = performance.now();
    if (now - lastWaterTick < 90) return;
    lastWaterTick = now;
    const p = Math.max(0, Math.min(1, progressFraction || 0));
    tone(280 + 260 * p, { type: 'sine', duration: 0.11, gain: 0.07, filterFreq: 1800 });
  }

  /* One clean "ding" - a dimension arc (or a bar) reaching completion. */
  function ding() {
    tone(880, { type: 'sine', duration: 0.5, gain: 0.15, filterFreq: 4200 });
    tone(1318.5, { type: 'sine', start: 0.05, duration: 0.45, gain: 0.09, filterFreq: 4200 });
  }

  /* Final result stinger: a bright rising arpeggio for a good result, a
     descending sigh ("aah") for a poor one - never the reverse, so the
     sound never contradicts the number the user is looking at. */
  function resultChime(isGood) {
    if (isGood) {
      [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => {
        tone(f, { type: 'sine', start: i * 0.1, duration: 0.5, gain: 0.16, filterFreq: 5200 });
      });
    } else {
      tone(392.0, { type: 'sine', duration: 1.0, gain: 0.15, glideTo: 246.9, filterFreq: 1100 });
      tone(196.0, { type: 'triangle', start: 0.18, duration: 1.05, gain: 0.09, glideTo: 130.8, filterFreq: 700 });
    }
  }

  function click() {
    tone(720, { type: 'sine', duration: 0.06, gain: 0.07, filterFreq: 3200 });
  }

  window.DWSound = {
    isEnabled, setEnabled, processingStart, stopProcessing, waterTick, ding, resultChime, click,
  };
})();
