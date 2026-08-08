/*
  Lightweight ambient "player" synthesized entirely with the Web Audio
  API. No external audio files/services: avoids licensing questions and
  network dependency. v2 additions per product notes: more moods, a
  context-aware starting suggestion (from the user's own last real
  score - never a fabricated one), manual track selection that's
  remembered, and a genuine "add your own track" option via a local
  file the browser plays directly - never uploaded anywhere, held only
  for the current tab session.
*/
(function () {
  const TRACKS = [
    { name: 'Calm Focus', freqs: [196.0, 246.94, 293.66], type: 'sine', filter: 900, mood: 'calm' },
    { name: 'Night Wind Down', freqs: [130.81, 164.81, 196.0], type: 'sine', filter: 500, mood: 'low' },
    { name: 'Deep Focus Beats', freqs: [220.0, 277.18, 329.63], type: 'triangle', filter: 1200, mood: 'focus' },
    { name: 'Energize', freqs: [261.63, 329.63, 392.0, 523.25], type: 'sine', filter: 1800, mood: 'high' },
    { name: 'Soft Rain Drift', freqs: [174.61, 220.0, 261.63], type: 'sine', filter: 700, mood: 'low' },
    { name: 'Steady Ground', freqs: [146.83, 220.0, 293.66], type: 'triangle', filter: 850, mood: 'calm' },
    { name: 'Bright Momentum', freqs: [293.66, 369.99, 440.0, 587.33], type: 'sine', filter: 2000, mood: 'high' },
    { name: 'Late Night Study', freqs: [164.81, 207.65, 261.63], type: 'triangle', filter: 950, mood: 'focus' },
  ];
  const TRACK_KEY = 'dwai_music_track_index';

  let ctx, masterGain, nodes = [], lfo;
  let current = 0, playing = false;
  let customTrack = null; // { name, audioEl, objectUrl } - session-only, never persisted/uploaded
  let usingCustom = false;

  function buildAudioGraph(track) {
    stopGraph();
    masterGain = ctx.createGain();
    masterGain.gain.value = 0;
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = track.filter;
    masterGain.connect(filter).connect(ctx.destination);

    nodes = track.freqs.map((f, i) => {
      const osc = ctx.createOscillator();
      osc.type = track.type;
      osc.frequency.value = f;
      const gain = ctx.createGain();
      gain.gain.value = 0.18 / track.freqs.length;
      osc.connect(gain).connect(masterGain);
      osc.start();
      return osc;
    });

    lfo = ctx.createOscillator();
    lfo.frequency.value = 0.08;
    const lfoGain = ctx.createGain();
    lfoGain.gain.value = 0.05;
    lfo.connect(lfoGain).connect(masterGain.gain);
    lfo.start();

    masterGain.gain.linearRampToValueAtTime(0.35, ctx.currentTime + 1.2);
  }

  function stopGraph() {
    nodes.forEach((n) => { try { n.stop(); } catch (e) {} });
    nodes = [];
    if (lfo) { try { lfo.stop(); } catch (e) {} lfo = null; }
    if (masterGain) { try { masterGain.disconnect(); } catch (e) {} }
  }

  function ensureCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume();
  }

  /* Suggest a starting mood from the user's own real last result - never
     a fabricated one. Falls back to the first track if no result is
     available. Only used once, to pick where the player starts; it never
     overrides a track the user has explicitly picked before (see init()). */
  function suggestedTrackIndex() {
    let result = null;
    try { result = JSON.parse(localStorage.getItem('dwai_last_result') || 'null'); } catch (e) {}
    let mood = 'calm';
    if (result && typeof result.regression_score === 'number') {
      const score = result.regression_score;
      const hour = new Date().getHours();
      if (score < 45) mood = (hour >= 21 || hour < 5) ? 'low' : 'calm';
      else if (score < 70) mood = 'focus';
      else mood = 'high';
    }
    const idx = TRACKS.findIndex((t) => t.mood === mood);
    return idx >= 0 ? idx : 0;
  }

  function play() {
    if (usingCustom && customTrack) {
      customTrack.audioEl.play();
      playing = true;
      updateUI();
      return;
    }
    ensureCtx();
    buildAudioGraph(TRACKS[current]);
    playing = true;
    updateUI();
  }

  function pause() {
    if (usingCustom && customTrack) {
      customTrack.audioEl.pause();
    } else if (masterGain) {
      masterGain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.4);
      setTimeout(stopGraph, 450);
    }
    playing = false;
    updateUI();
  }

  function toggle() { playing ? pause() : play(); }

  function next() {
    if (usingCustom) { selectSynthTrack(0); return; }
    selectSynthTrack((current + 1) % TRACKS.length);
  }

  function selectSynthTrack(index) {
    usingCustom = false;
    current = index;
    try { localStorage.setItem(TRACK_KEY, String(index)); } catch (e) {}
    if (customTrack) { customTrack.audioEl.pause(); }
    if (playing) play(); else updateUI();
  }

  /* Loads a user-provided local audio file. The file never leaves the
     browser - played via a local object URL, never sent to any server,
     and dropped (revoked) on tab close, matching this app's existing
     "session-only, never persisted" pattern for sensitive input. */
  function loadCustomFile(file) {
    if (!file) return;
    if (customTrack) { customTrack.audioEl.pause(); URL.revokeObjectURL(customTrack.objectUrl); }
    const objectUrl = URL.createObjectURL(file);
    const audioEl = new Audio(objectUrl);
    audioEl.loop = true;
    audioEl.volume = 0.6;
    customTrack = { name: file.name.replace(/\.[^.]+$/, ''), audioEl, objectUrl };
    usingCustom = true;
    stopGraph();
    if (playing) play(); else updateUI();
  }

  function updateUI() {
    const widget = document.getElementById('musicWidget');
    const btn = document.getElementById('musicPlayBtn');
    const name = document.getElementById('musicTrackName');
    if (!widget) return;
    widget.classList.toggle('paused', !playing);
    if (btn) btn.textContent = playing ? '❚❚' : '▶';
    if (name) name.textContent = usingCustom && customTrack ? customTrack.name : TRACKS[current].name;
  }

  function init() {
    const btn = document.getElementById('musicPlayBtn');
    const name = document.getElementById('musicTrackName');
    const uploadInput = document.getElementById('musicUploadInput');
    const uploadBtn = document.getElementById('musicUploadBtn');
    if (!btn) return;

    let startIndex = suggestedTrackIndex();
    try {
      const saved = localStorage.getItem(TRACK_KEY);
      if (saved !== null) startIndex = Math.min(TRACKS.length - 1, Math.max(0, parseInt(saved, 10)));
    } catch (e) {}
    current = startIndex;

    btn.addEventListener('click', toggle);
    if (name) name.addEventListener('click', next);
    if (uploadBtn && uploadInput) {
      uploadBtn.addEventListener('click', () => uploadInput.click());
      uploadInput.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        if (file) loadCustomFile(file);
      });
    }
    updateUI();
  }

  window.DWMusic = { init, play, pause, toggle, next, loadCustomFile };
})();
