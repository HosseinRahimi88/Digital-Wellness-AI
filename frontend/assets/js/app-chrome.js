/*
  Shared "app chrome": the Settings modal, the sound-effects toggle next
  to the music widget, and the Friends League notification bell. Used on
  every logged-in page. app.html already ships its own static Settings
  modal (it has extra rows - muted coaching topics, PDF - that only make
  sense on the result page) so this module never double-injects one;
  everywhere else it builds the modal once and appends it.

  wireCommonToggles() is the single place theme/music/sound-fx/reduced-
  motion get wired, so app.html's own modal and every injected one stay
  behaviourally identical instead of drifting apart.
*/
(function () {
  const ICONS = {
    gear: '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 13.5a7.6 7.6 0 0 0 0-3l2-1.5-2-3.4-2.3.9a7.7 7.7 0 0 0-2.6-1.5L14 2h-4l-.5 2.4a7.7 7.7 0 0 0-2.6 1.5l-2.3-.9-2 3.4 2 1.5a7.6 7.6 0 0 0 0 3l-2 1.6 2 3.4 2.3-1a7.7 7.7 0 0 0 2.6 1.5L10 22h4l.5-2.4a7.7 7.7 0 0 0 2.6-1.5l2.3 1 2-3.4-2-1.6Z"/>',
    bell: '<path d="M6 9a6 6 0 1 1 12 0c0 4 1.4 5.4 2 6H4c.6-.6 2-2 2-6Z"/><path d="M9.5 19a2.6 2.6 0 0 0 5 0"/>',
    soundOn: '<path d="M4 9v6h4l5 4V5L8 9H4Z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/><path d="M19 6a8.5 8.5 0 0 1 0 12"/>',
    soundOff: '<path d="M4 9v6h4l5 4V5L8 9H4Z"/><path d="M16 9l5 6M21 9l-5 6"/>',
  };

  function icon(name) { return `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ''}</svg>`; }

  function modalTemplate() {
    return `
    <div class="modal-backdrop" id="settingsModal">
      <div class="card modal">
        <h3 data-i18n="settings_title">Settings</h3>
        <div class="settings-row">
          <span data-i18n="settings_theme">Dark mode</span>
          <label class="switch"><input type="checkbox" id="settingsThemeSwitch"><span class="track"><span class="thumb"></span></span></label>
        </div>
        <div class="settings-row">
          <span data-i18n="settings_music">Ambient sound</span>
          <label class="switch"><input type="checkbox" id="settingsMusicSwitch"><span class="track"><span class="thumb"></span></span></label>
        </div>
        <div class="settings-row">
          <span data-i18n="settings_soundfx">Sound effects</span>
          <label class="switch"><input type="checkbox" id="settingsSoundFxSwitch"><span class="track"><span class="thumb"></span></span></label>
        </div>
        <div class="settings-row">
          <span data-i18n="settings_reduce_motion">Reduce motion</span>
          <label class="switch"><input type="checkbox" id="settingsMotionSwitch"><span class="track"><span class="thumb"></span></span></label>
        </div>
        <div class="settings-row">
          <span data-i18n="settings_games">Games after a check-in</span>
          <label class="switch"><input type="checkbox" id="settingsGamesSwitch"><span class="track"><span class="thumb"></span></span></label>
        </div>
        <!-- B-2: the guide's own section, separate from the global
             sound/motion switches above but coordinated with them. -->
        <div class="settings-group" id="guideSettingsGroup">
          <h4 class="settings-group-title" data-i18n="settings_guide_title">Digital guide</h4>
          <div class="settings-row">
            <span data-i18n="settings_guide_on">Show the guide</span>
            <label class="switch"><input type="checkbox" id="settingsGuideSwitch"><span class="track"><span class="thumb"></span></span></label>
          </div>
          <div class="settings-row">
            <span data-i18n="settings_guide_voice">Read messages aloud</span>
            <label class="switch"><input type="checkbox" id="settingsGuideVoiceSwitch"><span class="track"><span class="thumb"></span></span></label>
          </div>
          <div class="guide-voice-status" id="guideVoiceStatus"></div>
          <p class="muted guide-voice-hint" data-i18n="settings_guide_voice_hint">Which languages can be read aloud depends on your browser and device, not on this app.</p>
        </div>

        <div class="settings-row">
          <span data-i18n="settings_tour">Site tour</span>
          <button type="button" class="btn btn-ghost btn-sm" id="settingsTourBtn" data-i18n="settings_tour_btn">Take the tour</button>
        </div>
        <div class="settings-row">
          <span data-i18n="settings_demo_mode">Demo Mode</span>
          <button type="button" class="btn btn-ghost btn-sm" id="settingsDemoBtn" data-i18n="settings_demo_btn">Populate demo data</button>
        </div>
        <div class="settings-row">
          <span data-i18n="settings_league">Friends League sharing</span>
          <a class="btn btn-ghost btn-sm" href="league.html" data-i18n="settings_league_btn">Open League settings</a>
        </div>
        <!-- Only meaningful once a topic has actually been muted, so
             app.js shows/hides the row from the stored list. It lived
             only in app.html's own copy of this panel until that copy
             was removed - which is precisely how the two drifted. -->
        <div class="settings-row" id="settingsExcludedRow" style="display:none;">
          <span data-i18n="settings_excluded_topics">Muted coaching topics</span>
          <button type="button" class="btn btn-ghost btn-sm" id="settingsResetExcludedBtn" data-i18n="settings_reset">Reset</button>
        </div>
        <div class="settings-row">
          <span data-i18n="nav_logout">Log out</span>
          <button type="button" class="btn btn-danger btn-sm" id="settingsLogoutBtn" data-logout data-i18n="nav_logout">Log out</button>
        </div>
        <button type="button" class="btn btn-ghost btn-block" id="settingsCloseBtn" style="margin-top:14px;">✕</button>
      </div>
    </div>`;
  }

  /* The ONE settings panel. Every page builds it from the template
     above rather than carrying its own markup: app.html used to ship a
     hardcoded copy, and because this function reuses whatever
     #settingsModal it finds, the check-in page silently kept serving an
     older panel - one that had never gained the Digital guide section.
     The user could only reach the guide's own switches from pages that
     had no copy of their own. Reported as "the coach settings are only
     on the dashboard", and that is exactly what it was. */
  function ensureSettingsModal() {
    if (document.getElementById('settingsModal')) return document.getElementById('settingsModal');
    const wrap = document.createElement('div');
    wrap.innerHTML = modalTemplate();
    const modal = wrap.firstElementChild;
    document.body.appendChild(modal);
    // This panel is injected AFTER DWI18n.init() has already walked the
    // document, so nothing would ever translate it: every [data-i18n]
    // inside kept its English fallback in all four languages. It is
    // reachable from every page, so that was the single most visible
    // untranslated surface in the app.
    localise(modal);
    return modal;
  }

  /* Translate a subtree that was created after i18n's initial pass, and
     keep translating it when the language changes - a panel built once
     and left in the DOM would otherwise freeze at whatever language was
     active when it was first opened. */
  function localise(node) {
    if (!node || !window.DWI18n || !window.DWI18n.applyToDom) return;
    window.DWI18n.applyToDom(node);
    if (node.dataset && !node.dataset.i18nBound) {
      node.dataset.i18nBound = '1';
      document.addEventListener('dwai:langchange', () => {
        if (node.isConnected) window.DWI18n.applyToDom(node);
      });
    }
  }

  function ensureNavButtons() {
    const controls = document.querySelector('.nav-controls');
    if (!controls || document.getElementById('settingsBtn')) return;
    const logoutBtn = controls.querySelector('[data-logout], #logoutBtn');
    const bell = document.createElement('button');
    bell.className = 'icon-btn'; bell.id = 'notifBell'; bell.setAttribute('aria-label', 'Notifications');
    bell.innerHTML = icon('bell') + '<span class="notif-badge hidden" id="notifBadge">0</span>';
    const gear = document.createElement('button');
    gear.className = 'icon-btn'; gear.id = 'settingsBtn'; gear.setAttribute('aria-label', 'Settings');
    gear.setAttribute('data-guide', 'settings_panel');
    gear.innerHTML = icon('gear');
    if (logoutBtn) {
      controls.insertBefore(bell, logoutBtn);
      controls.insertBefore(gear, logoutBtn);
    } else {
      controls.appendChild(bell); controls.appendChild(gear);
    }
  }

  function ensureSoundFxWidgetButton() {
    const widget = document.getElementById('musicWidget');
    if (!widget || document.getElementById('soundFxToggleBtn')) return;
    const btn = document.createElement('button');
    btn.type = 'button'; btn.id = 'soundFxToggleBtn'; btn.className = 'music-upload-btn sound-fx-btn';
    btn.title = 'Toggle sound effects';
    btn.setAttribute('aria-label', 'Toggle sound effects');
    const paint = () => { btn.innerHTML = icon(window.DWSound && !window.DWSound.isEnabled() ? 'soundOff' : 'soundOn'); };
    paint();
    btn.addEventListener('click', () => {
      if (!window.DWSound) return;
      window.DWSound.setEnabled(!window.DWSound.isEnabled());
      paint();
      const fxSwitch = document.getElementById('settingsSoundFxSwitch');
      if (fxSwitch) fxSwitch.checked = window.DWSound.isEnabled();
    });
    widget.appendChild(btn);
  }

  function wireCommonToggles(modal) {
    if (!modal) return;
    const themeSwitch = modal.querySelector('#settingsThemeSwitch');
    const musicSwitch = modal.querySelector('#settingsMusicSwitch');
    const fxSwitch = modal.querySelector('#settingsSoundFxSwitch');
    const motionSwitch = modal.querySelector('#settingsMotionSwitch');
    const gamesSwitch = modal.querySelector('#settingsGamesSwitch');
    const demoBtn = modal.querySelector('#settingsDemoBtn');
    const tourBtn = modal.querySelector('#settingsTourBtn');
    const guideSwitch = modal.querySelector('#settingsGuideSwitch');
    const guideVoiceSwitch = modal.querySelector('#settingsGuideVoiceSwitch');
    const guideVoiceStatus = modal.querySelector('#guideVoiceStatus');

    /* B-1/B-2: report what this device can ACTUALLY speak, per language,
       read from the browser's own voice list rather than assumed. The list
       loads asynchronously and can change when a language pack is
       installed, so this re-renders on the voiceschanged event too. */
    const LANG_NAMES = {
      en: { en: 'English', fa: 'انگلیسی', ar: 'الإنجليزية', zh: '英语' },
      fa: { en: 'Persian', fa: 'فارسی', ar: 'الفارسية', zh: '波斯语' },
      ar: { en: 'Arabic', fa: 'عربی', ar: 'العربية', zh: '阿拉伯语' },
      zh: { en: 'Chinese', fa: 'چینی', ar: 'الصينية', zh: '中文' },
    };
    const VOICE_STATE = {
      on: { en: 'available', fa: 'در دسترس', ar: 'متاحة', zh: '可用' },
      off: { en: 'not available on this device', fa: 'روی این دستگاه در دسترس نیست', ar: 'غير متاحة على هذا الجهاز', zh: '此设备上不可用' },
      unsupported: {
        en: 'This browser cannot read text aloud.',
        fa: 'این مرورگر نمی‌تواند متن را بخواند.',
        ar: 'هذا المتصفح لا يستطيع قراءة النص بصوت عالٍ.',
        zh: '此浏览器无法朗读文本。',
      },
    };
    const pickTable = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);

    function renderVoiceStatus() {
      if (!guideVoiceStatus) return;
      const V = window.DWGuideVoice;
      if (!V || !V.supported()) {
        guideVoiceStatus.textContent = pickTable(VOICE_STATE.unsupported);
        if (guideVoiceSwitch) guideVoiceSwitch.disabled = true;
        return;
      }
      const avail = V.availability();
      guideVoiceStatus.innerHTML = '';
      V.SUPPORTED.forEach((code) => {
        const row = document.createElement('div');
        row.className = 'guide-voice-row' + (avail[code] ? ' is-on' : '');
        const name = document.createElement('span');
        name.textContent = pickTable(LANG_NAMES[code]);
        const state = document.createElement('span');
        state.className = 'guide-voice-state';
        state.textContent = pickTable(avail[code] ? VOICE_STATE.on : VOICE_STATE.off);
        row.appendChild(name);
        row.appendChild(state);
        guideVoiceStatus.appendChild(row);
      });
      // No voice at all anywhere: the switch would be a lie.
      if (guideVoiceSwitch) {
        guideVoiceSwitch.disabled = !V.SUPPORTED.some((c) => avail[c]);
      }
    }

    if (window.DWGuideVoice) {
      const V = window.DWGuideVoice;
      if (guideSwitch) {
        guideSwitch.checked = V.guideEnabled();
        guideSwitch.addEventListener('change', (e) => {
          playToggleSound(e.target.checked);
          V.setGuideEnabled(e.target.checked);
          // Turning the guide off must silence its voice too, and the
          // voice switch should not stay live under a hidden guide.
          if (guideVoiceSwitch) guideVoiceSwitch.disabled = !e.target.checked;
        });
      }
      if (guideVoiceSwitch) {
        guideVoiceSwitch.checked = V.voiceEnabled();
        guideVoiceSwitch.addEventListener('change', (e) => {
          playToggleSound(e.target.checked);
          V.setVoiceEnabled(e.target.checked);
          // Speak a confirmation so the user hears immediately whether
          // their own language actually works, instead of finding out later.
          if (e.target.checked && window.DWMascot) {
            window.DWMascot.say(pickTable({
              en: 'Voice is on. I will read my messages aloud.',
              fa: 'صدا روشن شد. پیام‌هایم را بلند می‌خوانم.',
              ar: 'الصوت مُفعَّل. سأقرأ رسائلي بصوت عالٍ.',
              zh: '语音已开启。我会把消息读出来。',
            }));
          }
        });
      }
      V.ready().then(renderVoiceStatus);
      V.onVoicesChanged(renderVoiceStatus);
      renderVoiceStatus();
    }

    // Every settings switch gets the same tick-on/blip-off confirmation,
    // played BEFORE the underlying state actually changes so flipping
    // the sound-fx switch itself off is still heard once.
    function playToggleSound(checked) {
      if (!window.DWSound) return;
      checked ? window.DWSound.toggleOn() : window.DWSound.toggleOff();
    }

    if (themeSwitch) {
      themeSwitch.addEventListener('change', (e) => {
        playToggleSound(e.target.checked);
        window.DWTheme.apply(e.target.checked ? 'dark' : 'light');
        localStorage.setItem('dwai_theme', e.target.checked ? 'dark' : 'light');
      });
    }
    if (musicSwitch) {
      musicSwitch.addEventListener('change', (e) => {
        playToggleSound(e.target.checked);
        e.target.checked ? window.DWMusic.play() : window.DWMusic.pause();
      });
    }
    if (fxSwitch) {
      fxSwitch.checked = window.DWSound ? window.DWSound.isEnabled() : true;
      fxSwitch.addEventListener('change', (e) => {
        playToggleSound(e.target.checked);
        if (window.DWSound) window.DWSound.setEnabled(e.target.checked);
        const widgetBtn = document.getElementById('soundFxToggleBtn');
        if (widgetBtn && window.DWSound) widgetBtn.innerHTML = icon(window.DWSound.isEnabled() ? 'soundOn' : 'soundOff');
      });
    }
    if (motionSwitch) {
      motionSwitch.checked = window.DWMotion.prefersReduced();
      motionSwitch.addEventListener('change', (e) => {
        playToggleSound(e.target.checked);
        window.DWMotion.setReduced(e.target.checked);
      });
    }
    if (gamesSwitch) {
      gamesSwitch.checked = window.DWGames ? window.DWGames.isEnabled() : true;
      gamesSwitch.addEventListener('change', (e) => {
        playToggleSound(e.target.checked);
        if (window.DWGames) window.DWGames.setEnabled(e.target.checked);
      });
    }
    if (demoBtn) {
      demoBtn.addEventListener('click', () => {
        if (window.DWDemo) window.DWDemo.run();
      });
    }
    if (tourBtn) {
      tourBtn.addEventListener('click', () => {
        modal.classList.remove('show');
        if (window.DWIntro) window.DWIntro.show({ force: true });
      });
    }
  }

  function wireModalOpenClose(modal, onOpen) {
    if (!modal) return;
    const btn = document.getElementById('settingsBtn');
    const closeBtn = modal.querySelector('#settingsCloseBtn');
    if (btn) {
      btn.addEventListener('click', () => {
        const themeSwitch = modal.querySelector('#settingsThemeSwitch');
        const motionSwitch = modal.querySelector('#settingsMotionSwitch');
        if (themeSwitch) themeSwitch.checked = window.DWTheme.get() === 'dark';
        if (motionSwitch) motionSwitch.checked = window.DWMotion.prefersReduced();
        if (typeof onOpen === 'function') onOpen(modal);
        modal.classList.add('show');
        // Forced on purpose: this runs because the user just clicked
        // "settings" open, so it is an answer to an action rather than
        // an unprompted greeting.
        if (window.DWGuide) window.DWGuide.explain('settings_panel', { force: true });
      });
    }
    if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.remove('show'));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });
  }

  let notifTimer = null;
  async function refreshNotifBadge() {
    const badge = document.getElementById('notifBadge');
    if (!badge || !window.DWApi || !window.DWApi.isAuthed()) return;
    try {
      const data = await window.DWApi.leaguePendingRequests();
      const n = (data.requests || []).length;
      badge.textContent = String(n);
      badge.classList.toggle('hidden', n === 0);
    } catch (e) { /* league not reachable yet - stay silent, never block chrome */ }
  }

  function wireNotifBell() {
    const bell = document.getElementById('notifBell');
    if (!bell || bell.dataset.wired) return;
    bell.dataset.wired = '1';
    bell.addEventListener('click', () => {
      if (window.DWLeague && window.DWLeague.openInboxPopover) {
        window.DWLeague.openInboxPopover(bell);
      } else {
        location.href = 'league.html';
      }
    });
    refreshNotifBadge();
    if (!notifTimer) notifTimer = setInterval(refreshNotifBadge, 60000);
  }

  function init() {
    ensureNavButtons();
    ensureSoundFxWidgetButton();
    const modal = ensureSettingsModal();
    wireCommonToggles(modal);
    wireModalOpenClose(modal);
    wireNotifBell();
  }

  /* C-5-5: the settings gear on the pre-login landing page.
     The full init() is written for signed-in pages - it also mounts a
     notification bell and the modal carries Log out, League and Demo rows,
     none of which mean anything to a visitor who has no account yet. So
     this mounts the gear and the modal, then hides the rows that require
     an account, rather than showing controls that would fail if used. */
  function initLanding() {
    const modal = ensureSettingsModal();

    const controls = document.querySelector('.nav-controls');
    if (controls && !document.getElementById('settingsBtn')) {
      const gear = document.createElement('button');
      gear.className = 'icon-btn';
      gear.id = 'settingsBtn';
      gear.setAttribute('aria-label', 'Settings');
      gear.setAttribute('data-guide', 'settings_panel');
      gear.innerHTML = icon('gear');
      // Before the Log in call-to-action, so the primary action stays last.
      const cta = controls.querySelector('a.btn');
      if (cta) controls.insertBefore(gear, cta); else controls.appendChild(gear);
    }

    ['[data-logout]', '#settingsDemoBtn', 'a[href="league.html"]'].forEach((sel) => {
      const el = modal.querySelector(sel);
      const row = el && el.closest('.settings-row');
      if (row) row.style.display = 'none';
    });

    // Both take the modal explicitly - calling them bare makes them
    // return immediately and the gear does nothing.
    wireCommonToggles(modal);
    wireModalOpenClose(modal);
  }

  window.DWChrome = {
    init, initLanding, wireCommonToggles, wireModalOpenClose, ensureSettingsModal,
    ensureSoundFxWidgetButton, ensureNavButtons, wireNotifBell, refreshNotifBadge,
  };
})();
