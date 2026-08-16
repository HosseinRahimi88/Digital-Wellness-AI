/*
  Ambient music player - real, user-provided audio tracks (assets/audio/
  track1..5.mp3), played through a plain <audio> element rather than a
  synthesized Web Audio graph. Simpler and more reliable than the
  earlier oscillator-based version: standard play()/pause()/volume,
  no AudioContext gesture-policy edge cases, no per-tab regeneration.

  A user can add their own tracks on top of these five. Those files
  never leave the browser: they are stored in IndexedDB on this device
  and played from a local object URL, never uploaded anywhere.

  Why IndexedDB and not the session-only object URL this used to keep:
  every page in this app is a real document load, so an object URL dies
  at the first navigation. A track you added was gone the moment you
  clicked anything - there was no library, no way back to it, and no way
  to remove it either. Keeping the blob is what makes "the songs I
  added" a real list rather than a thing that existed until you moved.
  It stays on the device; nothing about it is sent anywhere, and each
  one has its own delete.
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

  // Which track is selected, as a stable id rather than an index into
  // one of two lists: "built:2" or "added:1699999999999". An index alone
  // could not say WHICH list it indexed, which is how the old code ended
  // up with a separate `usingCustom` flag it had to keep in step.
  const SELECTED_KEY = 'dwai_music_selected';

  const DB_NAME = 'dwai_music';
  const DB_STORE = 'tracks';

  let audioEl = null;
  let current = 0, playing = false;
  let customTrack = null; // { id, name, objectUrl } - the added track now playing
  let usingCustom = false;
  let volume = 0.6;
  // Added tracks, newest first: { id, name, size, addedAt }. Blobs stay
  // in IndexedDB and are only fetched when a track is actually played.
  let added = [];

  /* ------------------------------------------------------------------
     The store. Deliberately tiny and entirely failure-tolerant: every
     call resolves rather than rejects, because a browser with IndexedDB
     blocked (private mode, a strict profile) must still get a working
     player with the five built-in tracks - just without a library.
     ------------------------------------------------------------------ */
  function openDb() {
    return new Promise((resolve) => {
      let request;
      try { request = indexedDB.open(DB_NAME, 1); } catch (e) { resolve(null); return; }
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(DB_STORE)) {
          db.createObjectStore(DB_STORE, { keyPath: 'id' });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(null);
      request.onblocked = () => resolve(null);
    });
  }

  function dbAll() {
    return openDb().then((db) => new Promise((resolve) => {
      if (!db) { resolve([]); return; }
      try {
        const req = db.transaction(DB_STORE, 'readonly').objectStore(DB_STORE).getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => resolve([]);
      } catch (e) { resolve([]); }
    }));
  }

  function dbGet(id) {
    return openDb().then((db) => new Promise((resolve) => {
      if (!db) { resolve(null); return; }
      try {
        const req = db.transaction(DB_STORE, 'readonly').objectStore(DB_STORE).get(id);
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => resolve(null);
      } catch (e) { resolve(null); }
    }));
  }

  function dbPut(record) {
    return openDb().then((db) => new Promise((resolve) => {
      if (!db) { resolve(false); return; }
      try {
        const req = db.transaction(DB_STORE, 'readwrite').objectStore(DB_STORE).put(record);
        req.onsuccess = () => resolve(true);
        req.onerror = () => resolve(false);
      } catch (e) { resolve(false); }
    }));
  }

  function dbDelete(id) {
    return openDb().then((db) => new Promise((resolve) => {
      if (!db) { resolve(false); return; }
      try {
        const req = db.transaction(DB_STORE, 'readwrite').objectStore(DB_STORE).delete(id);
        req.onsuccess = () => resolve(true);
        req.onerror = () => resolve(false);
      } catch (e) { resolve(false); }
    }));
  }

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

  /* The playlist the arrows walk: the five built-in tracks, then every
     track the user has added. One list, so "next" from the last
     built-in track lands on the first of your own rather than looping
     back and pretending yours are not there. */
  function playlist() {
    return TRACKS.map((t, i) => ({ id: 'built:' + i, name: t.name, builtIn: true, index: i }))
      .concat(added.map((a) => ({ id: 'added:' + a.id, name: a.name, builtIn: false, addedId: a.id })));
  }

  function currentId() {
    return usingCustom && customTrack ? 'added:' + customTrack.id : 'built:' + current;
  }

  function step(delta) {
    const list = playlist();
    if (!list.length) return;
    const at = Math.max(0, list.findIndex((t) => t.id === currentId()));
    const to = ((at + delta) % list.length + list.length) % list.length;
    selectTrack(list[to].id);
  }

  function next() { step(1); }
  function prev() { step(-1); }

  /* Selects by id, so a built-in track and an added one go through one
     path. The blob is read from the store at this moment rather than
     being held open: a library of ten tracks should not mean ten live
     object URLs. */
  function selectTrack(id) {
    try { localStorage.setItem(SELECTED_KEY, id); } catch (e) {}
    if (String(id).indexOf('built:') === 0) {
      usingCustom = false;
      if (customTrack) { URL.revokeObjectURL(customTrack.objectUrl); customTrack = null; }
      current = Math.max(0, Math.min(TRACKS.length - 1, parseInt(id.slice(6), 10) || 0));
      try { localStorage.setItem(TRACK_KEY, String(current)); } catch (e) {}
      if (audioEl) audioEl.src = '';
      if (playing) play(); else updateUI();
      renderLibrary();
      return Promise.resolve(true);
    }
    const addedId = id.slice(6);
    return dbGet(addedId).then((record) => {
      if (!record || !record.blob) {
        // The row is gone (cleared storage, another tab deleted it).
        // Falling back to a built-in track is better than silence with
        // no explanation of why.
        added = added.filter((a) => String(a.id) !== String(addedId));
        renderLibrary();
        return selectTrack('built:' + current);
      }
      if (customTrack) URL.revokeObjectURL(customTrack.objectUrl);
      customTrack = { id: record.id, name: record.name, objectUrl: URL.createObjectURL(record.blob) };
      usingCustom = true;
      if (audioEl) audioEl.src = '';
      if (playing) play(); else updateUI();
      renderLibrary();
      return true;
    });
  }

  function selectSynthTrack(index) {
    return selectTrack('built:' + Math.max(0, Math.min(TRACKS.length - 1, index)));
  }

  /* Removes a track the user added - the control the widget had no room
     for while a lone upload button occupied that slot. Deleting the one
     currently playing steps to the next thing in the list rather than
     stopping dead. */
  function removeTrack(addedId) {
    const wasPlayingThis = usingCustom && customTrack && String(customTrack.id) === String(addedId);
    return dbDelete(addedId).then(() => {
      added = added.filter((a) => String(a.id) !== String(addedId));
      if (wasPlayingThis) {
        if (customTrack) { URL.revokeObjectURL(customTrack.objectUrl); customTrack = null; }
        usingCustom = false;
        const list = playlist();
        return selectTrack((list[0] && list[0].id) || 'built:0');
      }
      renderLibrary();
      updateUI();
      return true;
    });
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
    if (!file) return Promise.resolve(false);
    const record = {
      id: String(Date.now()) + '_' + Math.random().toString(36).slice(2, 7),
      name: file.name.replace(/\.[^.]+$/, '').slice(0, 60) || 'Track',
      size: file.size,
      addedAt: new Date().toISOString(),
      blob: file,
    };
    return dbPut(record).then((stored) => {
      const entry = { id: record.id, name: record.name, size: record.size, addedAt: record.addedAt };
      added.unshift(entry);
      if (!stored && window.DWToast && window.DWI18n) {
        // Kept for this page, but it will not be there after a
        // navigation. Saying so beats a library that quietly forgets.
        window.DWToast.info(window.DWI18n.t('music_not_saved'));
      }
      return selectTrack('added:' + record.id);
    });
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

  /* The library. Built-in tracks first, then the ones the user added,
     each with its own delete - the control that had nowhere to live
     while a single upload button occupied that slot. */
  function renderLibrary() {
    const list = document.getElementById('musicLibraryList');
    if (!list) return;
    const t = (k) => (window.DWI18n && window.DWI18n.t ? window.DWI18n.t(k) : k);
    const here = currentId();
    list.innerHTML = '';

    playlist().forEach((track) => {
      const row = document.createElement('div');
      row.className = 'music-library-row' + (track.id === here ? ' is-current' : '');

      const pick = document.createElement('button');
      pick.type = 'button';
      pick.className = 'music-library-pick';
      pick.textContent = track.name;
      pick.title = track.name;
      if (track.id === here) pick.setAttribute('aria-current', 'true');
      pick.addEventListener('click', () => { selectTrack(track.id); });
      row.appendChild(pick);

      if (!track.builtIn) {
        const del = document.createElement('button');
        del.type = 'button';
        del.className = 'music-library-del';
        del.title = t('music_delete_track');
        del.setAttribute('aria-label', `${t('music_delete_track')}: ${track.name}`);
        if (window.DWIcon) window.DWIcon.set(del, 'trash', { size: 13 });
        else del.textContent = '×';
        del.addEventListener('click', (e) => {
          e.stopPropagation();
          removeTrack(track.addedId);
        });
        row.appendChild(del);
      }
      list.appendChild(row);
    });
  }

  function wireLibraryPopover() {
    const btn = document.getElementById('musicLibraryBtn');
    const popover = document.getElementById('musicLibraryPopover');
    if (!btn || !popover) return;
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = popover.classList.toggle('show');
      btn.setAttribute('aria-expanded', String(open));
      if (open) renderLibrary();
    });
    document.addEventListener('click', (e) => {
      if (popover.contains(e.target) || e.target === btn) return;
      popover.classList.remove('show');
      btn.setAttribute('aria-expanded', 'false');
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && popover.classList.contains('show')) {
        popover.classList.remove('show');
        btn.setAttribute('aria-expanded', 'false');
        btn.focus();
      }
    });
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
    // The track name is a LABEL again. Clicking it used to be the only
    // way to change track, which is not a control anybody finds, and it
    // could only ever move forwards.
    if (name) name.removeAttribute('role');

    const prevBtn = document.getElementById('musicPrevBtn');
    const nextBtn = document.getElementById('musicNextBtn');
    if (prevBtn) prevBtn.addEventListener('click', prev);
    if (nextBtn) nextBtn.addEventListener('click', next);

    if (uploadBtn && uploadInput) {
      uploadBtn.addEventListener('click', () => uploadInput.click());
      uploadInput.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        e.target.value = '';  // so re-picking the same file still fires
        if (file) loadCustomFile(file);
      });
    }
    wireLibraryPopover();
    wireVolumePopover();
    setVolume(volume);
    updateUI();

    // The library, then whatever was selected last time - both need the
    // store, so both wait for it. Everything above works without it.
    dbAll().then((records) => {
      added = records
        .map((r) => ({ id: r.id, name: r.name, size: r.size, addedAt: r.addedAt }))
        .sort((a, b) => String(b.addedAt || '').localeCompare(String(a.addedAt || '')));
      renderLibrary();
      let selected = null;
      try { selected = localStorage.getItem(SELECTED_KEY); } catch (e) {}
      if (selected && selected.indexOf('added:') === 0
          && added.some((a) => 'added:' + a.id === selected)) {
        return selectTrack(selected);
      }
      updateUI();
      return null;
    }).then(() => { resumeAcrossPages(); });
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

  window.DWMusic = {
    init, play, pause, toggle, next, prev, selectTrack, removeTrack,
    loadCustomFile, setVolume, TRACKS,
    // Read by the tests, and by anything that wants to show what is
    // in the library without reaching into IndexedDB itself.
    playlist, addedTracks: () => added.slice(),
  };
})();
