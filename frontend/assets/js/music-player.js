/*
  Lightweight ambient "player" synthesized entirely with the Web Audio
  API. No external audio files: avoids licensing questions and network
  dependency for a v1 "playlist" feature. v2 (per product notes) should
  swap this for real uploadable/streamable tracks; the play/pause/track
  UI contract here is written so that swap doesn't need a redesign.
*/
(function () {
  const TRACKS = [
    { name: 'Calm Focus', freqs: [196.0, 246.94, 293.66], type: 'sine', filter: 900 },
    { name: 'Night Wind Down', freqs: [130.81, 164.81, 196.0], type: 'sine', filter: 500 },
    { name: 'Deep Focus Beats', freqs: [220.0, 277.18, 329.63], type: 'triangle', filter: 1200 },
    { name: 'Energize', freqs: [261.63, 329.63, 392.0, 523.25], type: 'sine', filter: 1800 },
  ];

  let ctx, masterGain, nodes = [], lfo;
  let current = 0, playing = false;

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

  function play() {
    ensureCtx();
    buildAudioGraph(TRACKS[current]);
    playing = true;
    updateUI();
  }

  function pause() {
    if (masterGain) {
      masterGain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.4);
      setTimeout(stopGraph, 450);
    }
    playing = false;
    updateUI();
  }

  function toggle() { playing ? pause() : play(); }

  function next() {
    current = (current + 1) % TRACKS.length;
    if (playing) play(); else updateUI();
  }

  function updateUI() {
    const widget = document.getElementById('musicWidget');
    const btn = document.getElementById('musicPlayBtn');
    const name = document.getElementById('musicTrackName');
    if (!widget) return;
    widget.classList.toggle('paused', !playing);
    if (btn) btn.textContent = playing ? '❚❚' : '▶';
    if (name) name.textContent = TRACKS[current].name;
  }

  function init() {
    const btn = document.getElementById('musicPlayBtn');
    const name = document.getElementById('musicTrackName');
    if (!btn) return;
    btn.addEventListener('click', toggle);
    if (name) name.addEventListener('click', next);
    updateUI();
  }

  window.DWMusic = { init, play, pause, toggle, next };
})();
