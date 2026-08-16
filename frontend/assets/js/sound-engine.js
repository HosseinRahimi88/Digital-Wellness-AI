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

  C-4's five hard requirements, and where each one lives:

    1. A real global on/off          isEnabled()/setEnabled(), and every
                                     cue routes through tone(), which
                                     checks it. There is no path that
                                     bypasses the switch.
    2. Effects volume independent    setVolume()/getVolume() drive a
       of the ambient music          master gain this engine owns.
                                     music-player.js has its own and the
                                     two never touch.
    3. Never before a first user     ARMED stays false until a real
       interaction                   pointer/key/touch event. Until then
                                     no AudioContext is even created -
                                     browsers block it anyway, and
                                     creating one to have it refuse is
                                     how you get console noise and a
                                     suspended context that later fires
                                     a burst of queued sound.
    4. Reduced motion lowers         REDUCED_GAIN scales every cue.
       intensity                     Sound is not removed - the brief
                                     asks for less, not for silence.
    5. No cue repeats more than      throttled() gates every named cue
       once per second               at ONE_PER_SECOND, with two
                                     deliberate exceptions:
                                     - waterTick, a continuous progress
                                       texture at a tenth of the gain
                                       rather than a repeated alert; a
                                       1s gate would turn a filling bar
                                       into a single blip.
                                     - click and the two switch flips,
                                       gated at INTERACTION_GATE (120ms)
                                       instead. These answer a finger.
                                       Swallowing the second of two
                                       deliberate clicks reads as a
                                       broken button, which is a worse
                                       outcome than the one the rule is
                                       protecting against - machine-gun
                                       repetition, which 120ms already
                                       prevents.
*/
(function () {
  const KEY = 'dwai_sound_fx';
  const VOLUME_KEY = 'dwai_sound_fx_volume';
  const ONE_PER_SECOND = 1000;
  // Direct-interaction cues (click, switch flips) use a shorter gate:
  // long enough that a programmatic burst cannot buzz, short enough
  // that two deliberate clicks each still answer. See the header.
  const INTERACTION_GATE = 120;
  let ctx = null;
  let master = null;
  let processingNodes = null;
  let lastWaterTick = 0;
  let armed = false;
  const lastPlayed = {};

  /* Requirement 3. One listener, removed the moment it fires. */
  function arm() {
    armed = true;
    ['pointerdown', 'keydown', 'touchstart'].forEach((evt) =>
      document.removeEventListener(evt, arm, true));
  }
  ['pointerdown', 'keydown', 'touchstart'].forEach((evt) =>
    document.addEventListener(evt, arm, true));

  function reducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  /* Requirement 2. 0..1, persisted, defaulting to full. */
  function getVolume() {
    const raw = parseFloat(localStorage.getItem(VOLUME_KEY));
    return Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 1;
  }

  function setVolume(v) {
    const clamped = Math.max(0, Math.min(1, Number(v) || 0));
    localStorage.setItem(VOLUME_KEY, String(clamped));
    if (master) master.gain.value = effectiveVolume();
    document.dispatchEvent(new CustomEvent('dwai:soundfxvolume', { detail: { volume: clamped } }));
    return clamped;
  }

  /* Requirement 4 folded into the master gain rather than into each
     cue, so a cue added later cannot forget about it. */
  function effectiveVolume() {
    return getVolume() * (reducedMotion() ? 0.55 : 1);
  }

  /* Requirement 5. Returns true when this cue fired too recently.
     `ms` defaults to the full second; the interaction cues below pass a
     shorter gate. See the note in the header for why. */
  function throttled(name, ms) {
    const now = (window.performance && performance.now) ? performance.now() : Date.now();
    const gate = ms == null ? ONE_PER_SECOND : ms;
    if (lastPlayed[name] != null && now - lastPlayed[name] < gate) return true;
    lastPlayed[name] = now;
    return false;
  }

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
    // Requirement 3: refuse to even construct a context before the user
    // has touched the page.
    if (!armed) throw new Error('audio not armed yet');
    if (!ctx) {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      master = ctx.createGain();
      master.gain.value = effectiveVolume();
      master.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') ctx.resume();
    // Re-read each time: the user may have changed the slider, or
    // switched reduced motion on, since the context was built.
    if (master) master.gain.value = effectiveVolume();
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
    tail.connect(gain).connect(master || c.destination);
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
    osc.connect(filter).connect(gain).connect(master || c.destination);
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
    if (throttled('ding')) return;
    tone(880, { type: 'sine', duration: 0.5, gain: 0.15, filterFreq: 4200 });
    tone(1318.5, { type: 'sine', start: 0.05, duration: 0.45, gain: 0.09, filterFreq: 4200 });
  }

  /* Final result stinger: a bright rising arpeggio for a good result, a
     descending sigh ("aah") for a poor one - never the reverse, so the
     sound never contradicts the number the user is looking at. */
  function resultChime(isGood) {
    if (throttled('resultChime')) return;
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
    if (throttled('click', INTERACTION_GATE)) return;
    tone(720, { type: 'sine', duration: 0.06, gain: 0.07, filterFreq: 3200 });
  }

  /* A crisp little upward "tick" for turning a settings switch on, and
     a duller downward blip for turning one off. Gated by isEnabled()
     like every other cue here - including when the switch being
     flipped IS the sound-effects toggle itself, callers play this
     BEFORE calling setEnabled(false) so the off-confirmation is still
     heard once. */
  function toggleOn() {
    if (throttled('toggleOn', INTERACTION_GATE)) return;
    tone(660, { type: 'sine', duration: 0.09, gain: 0.12, filterFreq: 4000 });
    tone(990, { type: 'sine', start: 0.05, duration: 0.1, gain: 0.09, filterFreq: 4000 });
  }
  function toggleOff() {
    if (throttled('toggleOff', INTERACTION_GATE)) return;
    tone(480, { type: 'sine', duration: 0.1, gain: 0.09, filterFreq: 2200 });
  }

  /* ---- The rest of the C-4 cue list ------------------------------- */

  /* Page change. Deliberately the quietest thing here: it fires on
     every navigation, so anything with presence becomes irritating by
     the third page. */
  function pageChange() {
    if (throttled('pageChange')) return;
    tone(520, { type: 'sine', duration: 0.12, gain: 0.05, glideTo: 660, filterFreq: 2600 });
  }

  /* A new badge. The one cue in the app allowed to feel like an event -
     a rising major triad with a soft bell on top. */
  function badge() {
    if (throttled('badge')) return;
    [587.33, 739.99, 880].forEach((f, i) => {
      tone(f, { type: 'sine', start: i * 0.07, duration: 0.55, gain: 0.13, filterFreq: 5000 });
    });
    tone(1760, { type: 'sine', start: 0.22, duration: 0.7, gain: 0.05, filterFreq: 6000 });
  }

  /* Sending a message to the coach: a short upward breath, so it reads
     as "gone" rather than as "done". */
  function messageSend() {
    if (throttled('messageSend')) return;
    tone(620, { type: 'sine', duration: 0.1, gain: 0.07, glideTo: 880, filterFreq: 3400 });
  }

  /* A message arriving back. */
  function messageReceive() {
    if (throttled('messageReceive')) return;
    tone(880, { type: 'sine', duration: 0.12, gain: 0.07, glideTo: 660, filterFreq: 3400 });
  }

  /* The letter from your future self unfolding: paper, not fanfare. */
  function letterOpen() {
    if (throttled('letterOpen')) return;
    tone(330, { type: 'triangle', duration: 0.45, gain: 0.06, glideTo: 440, filterFreq: 1500 });
    tone(660, { type: 'sine', start: 0.16, duration: 0.5, gain: 0.045, filterFreq: 2600 });
  }

  /* An alert worth attention. Two soft mid-range notes, on purpose:
     this is a wellness app, and a klaxon here would be both wrong and
     the fastest possible way to get every sound switched off. */
  function alert() {
    if (throttled('alert')) return;
    tone(494, { type: 'sine', duration: 0.28, gain: 0.1, filterFreq: 2200 });
    tone(392, { type: 'sine', start: 0.22, duration: 0.34, gain: 0.09, filterFreq: 2000 });
  }

  /* Something went wrong. Low and short - it should not sound like the
     user broke something. */
  function error() {
    if (throttled('error')) return;
    tone(311, { type: 'sine', duration: 0.22, gain: 0.09, glideTo: 233, filterFreq: 1400 });
  }

  /* Something worked. */
  function success() {
    if (throttled('success')) return;
    tone(659.25, { type: 'sine', duration: 0.22, gain: 0.1, filterFreq: 4200 });
    tone(987.77, { type: 'sine', start: 0.09, duration: 0.3, gain: 0.07, filterFreq: 4600 });
  }

  window.DWSound = {
    isEnabled, setEnabled, getVolume, setVolume,
    processingStart, stopProcessing, waterTick, ding, resultChime, click,
    toggleOn, toggleOff,
    pageChange, badge, messageSend, messageReceive, letterOpen, alert, error, success,
    // Exposed for the settings screen and for tests: whether a first
    // user gesture has happened yet, which is what gates all playback.
    isArmed: () => armed,
  };

  /* Requirement 1 applies to page navigation too, and the cue has to be
     attached somewhere. Doing it here rather than in each page's script
     means a new page gets it for free. */
  document.addEventListener('click', (e) => {
    const link = e.target && e.target.closest && e.target.closest('a[href]');
    if (!link) return;
    const href = link.getAttribute('href') || '';
    if (href.startsWith('#') || href.startsWith('javascript:') || link.target === '_blank') return;
    pageChange();
  }, true);
})();
