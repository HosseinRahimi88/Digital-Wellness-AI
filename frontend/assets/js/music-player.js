/*
  Ambient music player - real, user-provided audio tracks (assets/audio/
  track1..5.mp3), played through a plain <audio> element rather than a
  synthesized Web Audio graph. Simpler and more reliable than the
  earlier oscillator-based version: standard play()/pause()/volume,
  no AudioContext gesture-policy edge cases, no per-tab regeneration.

  A user can still add their own local track on top of these five (the
  file never leaves the browser - played via a local object URL, never
  uploaded anywhere, matching this app's "session-only, never
  persisted" pattern for sensitive input).
*/
(function () {
  const TRACKS = [
    { name: 'Calm Horizon', src: 'assets/audio/track1.mp3' },
    { name: 'Quiet Focus', src: 'assets/audio/track2.mp3' },
    { name: 'Soft Current', src: 'assets/audio/track3.mp3' },
    { name: 'Night Drift', src: 'assets/audio/track4.mp3' },
    { name: 'Clear Mind', src: 'assets/audio/track5.mp3' },
  ];
  const TRACK_KEY = 'dwai_music_track_index';
  const VOLUME_KEY = 'dwai_music_volume';
  /* C-5-4. These three are what makes the music survive a page change.
     Every page in this app is a real document load, so there is no
     JavaScript object that outlives navigation - the only way for a
     track to continue is to write down where it was and pick it up on
     the other side. Position is stored with a timestamp so the few
     hundred milliseconds a navigation takes are added back, otherwise
     every page change would nudge the track slightly backwards. */
  const PLAYING_KEY = 'dwai_music_playing';
  const POSITION_KEY = 'dwai_music_position';
  const POSITION_AT_KEY = 'dwai_music_position_at';

  let audioEl = null;
  let current = 0, playing = false;
  let customTrack = null; // { name, objectUrl } - session-only, never persisted/uploaded
  let usingCustom = false;
  let volume = 0.6;

  function ensureAudioEl() {
    if (audioEl) return audioEl;
    audioEl = new Audio();
    audioEl.loop = true;
    /* 'auto', not 'none'. This app is multi-page, so every navigation
       destroys the audio element and the next page builds a new one -
       with preload='none' the browser did not begin fetching until
       play() was called, which put a fetch + decode + seek entirely
       inside the gap and made the music audibly drop for about a second
       on every single page change. Asking for the data up front lets
       that work overlap the rest of page load instead of following it.
       The files are already local to the app, so this costs no extra
       network trip. */
    audioEl.preload = 'auto';
    audioEl.volume = volume;
    audioEl.addEventListener('error', () => {
      // A missing/blocked audio file must never look like a silent
      // success - the widget visibly drops back to "paused" instead of
      // pretending playback started.
      playing = false;
      updateUI();
    });
    return audioEl;
  }

  function currentSrc() {
    return usingCustom && customTrack ? customTrack.objectUrl : TRACKS[current].src;
  }

  function rememberPosition() {
    if (!audioEl) return;
    try {
      localStorage.setItem(POSITION_KEY, String(audioEl.currentTime || 0));
      localStorage.setItem(POSITION_AT_KEY, String(Date.now()));
      localStorage.setItem(PLAYING_KEY, playing ? '1' : '0');
    } catch (e) { /* storage disabled - playback still works, just not across pages */ }
  }

  function play() {
    const el = ensureAudioEl();
    const wanted = currentSrc();
    // Only reassign .src (which restarts a clip from 0) if it actually
    // changed - toggling play/pause on the SAME track must resume, not
    // restart, from wherever the user left it.
    if (!el.src || !el.src.endsWith(wanted.replace(/^.*\//, ''))) {
      el.src = wanted;
    }
    const p = el.play();
    if (p && p.catch) {
      p.catch(() => {
        // Autoplay refused (no gesture on this page yet). Do not pretend
        // it is playing: the widget shows paused and one tap resumes.
        playing = false;
        try { localStorage.setItem(PLAYING_KEY, '0'); } catch (e) {}
        updateUI();
      });
    }
    playing = true;
    try { localStorage.setItem(PLAYING_KEY, '1'); } catch (e) {}
    updateUI();
  }

  function pause() {
    if (audioEl) audioEl.pause();
    playing = false;
    rememberPosition();
    updateUI();
  }

  function toggle() { playing ? pause() : play(); }

  function next() {
    usingCustom = false;
    current = (current + 1) % TRACKS.length;
    try { localStorage.setItem(TRACK_KEY, String(current)); } catch (e) {}
    if (audioEl) audioEl.src = '';
    if (playing) play(); else updateUI();
  }

  function selectSynthTrack(index) {
    usingCustom = false;
    current = Math.max(0, Math.min(TRACKS.length - 1, index));
    try { localStorage.setItem(TRACK_KEY, String(current)); } catch (e) {}
    if (audioEl) audioEl.src = '';
    if (playing) play(); else updateUI();
  }

  /* C-5-3. The percentage is shown, not just implied by a bar: a slider
     with no number is guesswork, and this one lives in a popover that is
     too small to read a fill against. The speaker glyph tracks the level
     too, so the widget still says something with the popover closed. */
  /* The speaker still reflects the level, now as our own icon: muted
     gets the crossed-out variant, anything audible gets the waves. */
  function applyVolumeIcon(btn) {
    if (!btn) return;
    if (!window.DWIcon) { btn.textContent = volume <= 0.001 ? '🔇' : '🔊'; return; }
    if (volume <= 0.001) window.DWIcon.set(btn, 'volumeMute', { size: 16 });
    else window.DWIcon.set(btn, 'volume', { size: 16, waves: volume >= 0.34 });
  }

  function setVolume(v) {
    volume = Math.max(0, Math.min(1, Number(v) || 0));
    if (audioEl) audioEl.volume = volume;
    try { localStorage.setItem(VOLUME_KEY, String(volume)); } catch (e) {}
    const percent = Math.round(volume * 100);
    const fill = document.getElementById('musicVolumeFill');
    if (fill) fill.style.width = percent + '%';
    const value = document.getElementById('musicVolumeValue');
    if (value) value.textContent = percent + '%';
    const track = document.getElementById('musicVolumeTrack');
    if (track) track.setAttribute('aria-valuenow', String(percent));
    applyVolumeIcon(document.getElementById('musicVolumeBtn'));
  }

  /* Loads a user-provided local audio file. The file never leaves the
     browser - played via a local object URL, never sent to any server,
     and dropped (revoked) on tab close, matching this app's existing
     "session-only, never persisted" pattern for sensitive input. */
  function loadCustomFile(file) {
    if (!file) return;
    if (customTrack) URL.revokeObjectURL(customTrack.objectUrl);
    const objectUrl = URL.createObjectURL(file);
    customTrack = { name: file.name.replace(/\.[^.]+$/, ''), objectUrl };
    usingCustom = true;
    if (audioEl) audioEl.src = '';
    if (playing) play(); else updateUI();
  }

  function updateUI() {
    const widget = document.getElementById('musicWidget');
    const btn = document.getElementById('musicPlayBtn');
    const name = document.getElementById('musicTrackName');
    if (!widget) return;
    widget.classList.toggle('paused', !playing);
    /* Own SVG rather than a text glyph: ▶/❚❚ render differently on every
       platform and cannot inherit the button's colour. */
    if (btn) {
      if (window.DWIcon) window.DWIcon.set(btn, playing ? 'pause' : 'play', { size: 16 });
      else btn.textContent = playing ? '❚❚' : '▶';
    }
    if (name) name.textContent = usingCustom && customTrack ? customTrack.name : TRACKS[current].name;
  }

  function wireVolumePopover() {
    const track = document.getElementById('musicVolumeTrack');
    const popover = document.getElementById('musicVolumePopover');
    const volumeBtn = document.getElementById('musicVolumeBtn');
    if (!track || !popover || !volumeBtn) return;

    volumeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      popover.classList.toggle('show');
    });
    document.addEventListener('click', (e) => {
      if (!popover.contains(e.target) && e.target !== volumeBtn) popover.classList.remove('show');
    });

    function setFromEvent(e) {
      const rect = track.getBoundingClientRect();
      // RTL: the track is mirrored, so the far edge is the zero end.
      const rtl = getComputedStyle(track).direction === 'rtl';
      const raw = (e.clientX - rect.left) / rect.width;
      setVolume(rtl ? 1 - raw : raw);
    }

    // Pointer capture rather than a window-level pointermove listener:
    // the drag keeps working when the pointer leaves the popover, and
    // it stops cleanly if the pointer is lost, which the old version
    // did not - releasing outside the window left `dragging` true and
    // the slider kept following the mouse afterwards.
    track.addEventListener('pointerdown', (e) => {
      track.setPointerCapture(e.pointerId);
      setFromEvent(e);
    });
    track.addEventListener('pointermove', (e) => {
      if (track.hasPointerCapture && track.hasPointerCapture(e.pointerId)) setFromEvent(e);
    });
    track.addEventListener('pointerup', (e) => {
      if (track.hasPointerCapture && track.hasPointerCapture(e.pointerId)) {
        track.releasePointerCapture(e.pointerId);
      }
    });

    // A wheel over the slider is the gesture most people try first.
    track.addEventListener('wheel', (e) => {
      e.preventDefault();
      setVolume(volume + (e.deltaY < 0 ? 0.05 : -0.05));
    }, { passive: false });

    // Keyboard: the slider is a real widget, not a decorative bar.
    track.setAttribute('role', 'slider');
    track.setAttribute('tabindex', '0');
    track.setAttribute('aria-valuemin', '0');
    track.setAttribute('aria-valuemax', '100');
    track.addEventListener('keydown', (e) => {
      const step = e.shiftKey ? 0.2 : 0.05;
      // Left/right are swapped under RTL so the arrow always moves the
      // handle in the direction the key points on screen.
      const rtl = getComputedStyle(track).direction === 'rtl';
      const map = {
        ArrowUp: step, ArrowDown: -step,
        ArrowRight: rtl ? -step : step, ArrowLeft: rtl ? step : -step,
      };
      if (map[e.key] != null) { e.preventDefault(); setVolume(volume + map[e.key]); return; }
      if (e.key === 'Home') { e.preventDefault(); setVolume(0); }
      if (e.key === 'End') { e.preventDefault(); setVolume(1); }
    });
  }

  function init() {
    const btn = document.getElementById('musicPlayBtn');
    const name = document.getElementById('musicTrackName');
    const uploadInput = document.getElementById('musicUploadInput');
    const uploadBtn = document.getElementById('musicUploadBtn');
    if (!btn) return;

    try {
      const savedVol = localStorage.getItem(VOLUME_KEY);
      if (savedVol !== null) volume = Math.max(0, Math.min(1, parseFloat(savedVol)));
    } catch (e) {}

    try {
      const saved = localStorage.getItem(TRACK_KEY);
      if (saved !== null) current = Math.min(TRACKS.length - 1, Math.max(0, parseInt(saved, 10)));
    } catch (e) {}

    btn.addEventListener('click', toggle);
    if (name) name.addEventListener('click', next);
    if (uploadBtn && uploadInput) {
      uploadBtn.addEventListener('click', () => uploadInput.click());
      uploadInput.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        if (file) loadCustomFile(file);
      });
    }
    wireVolumePopover();
    setVolume(volume);
    updateUI();
    resumeAcrossPages();
  }

  /* C-5-4. Picks the track back up where the previous page left it.
     Only ever called when the user had it playing - this never starts
     music on its own, and a browser that refuses the resume leaves the
     widget showing paused rather than lying about it. */
  function resumeAcrossPages() {
    let wasPlaying = false, position = 0, at = 0;
    try {
      wasPlaying = localStorage.getItem(PLAYING_KEY) === '1';
      position = parseFloat(localStorage.getItem(POSITION_KEY) || '0') || 0;
      at = parseInt(localStorage.getItem(POSITION_AT_KEY) || '0', 10) || 0;
    } catch (e) { return; }
    if (!wasPlaying) return;

    const el = ensureAudioEl();
    el.src = currentSrc();
    // Add back the time the navigation itself took, capped so a tab
    // reopened tomorrow does not seek an hour into a five-minute loop.
    const elapsed = at ? Math.min((Date.now() - at) / 1000, 30) : 0;
    const seekTo = position + elapsed;
    const seek = () => {
      if (el.duration && isFinite(el.duration)) el.currentTime = seekTo % el.duration;
      else el.currentTime = seekTo;
    };
    if (el.readyState >= 1) seek();
    else el.addEventListener('loadedmetadata', seek, { once: true });

    /* Fade the first moment back in instead of snapping to full volume.
       Even with preload='auto' a page change cannot be truly gapless in
       a multi-page app - the element is destroyed and rebuilt - so the
       remaining few hundred milliseconds are made to sound deliberate
       rather than like the track was cut. Ramps to whatever volume the
       user actually chose, and restores it exactly even if the fade is
       interrupted by a pause. */
    const target = volume;
    el.volume = 0;
    play();
    const startedAt = Date.now();
    const FADE_MS = 450;
    const ramp = setInterval(() => {
      const t = Math.min(1, (Date.now() - startedAt) / FADE_MS);
      el.volume = target * t;
      if (t >= 1) { clearInterval(ramp); el.volume = target; }
    }, 30);
  }

  /* Write the position down on the way out. pagehide rather than
     unload: unload is unreliable on mobile and blocks the back/forward
     cache, and pagehide fires in both the navigate-away and the
     tab-closed cases. */
  window.addEventListener('pagehide', rememberPosition);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') rememberPosition();
  });
  // A slow, cheap heartbeat so a crash or a force-quit still leaves a
  // recent position behind.
  setInterval(() => { if (playing) rememberPosition(); }, 5000);

  window.DWMusic = { init, play, pause, toggle, next, loadCustomFile, setVolume, TRACKS };
})();
