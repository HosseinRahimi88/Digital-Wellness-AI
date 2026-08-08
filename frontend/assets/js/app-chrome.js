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
        <div class="settings-row">
          <span data-i18n="nav_logout">Log out</span>
          <button type="button" class="btn btn-danger btn-sm" data-logout data-i18n="nav_logout">Log out</button>
        </div>
        <button type="button" class="btn btn-ghost btn-block" id="settingsCloseBtn" style="margin-top:14px;">✕</button>
      </div>
    </div>`;
  }

  function ensureSettingsModal() {
    if (document.getElementById('settingsModal')) return document.getElementById('settingsModal');
    const wrap = document.createElement('div');
    wrap.innerHTML = modalTemplate();
    const modal = wrap.firstElementChild;
    document.body.appendChild(modal);
    return modal;
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
    const demoBtn = modal.querySelector('#settingsDemoBtn');
    const tourBtn = modal.querySelector('#settingsTourBtn');

    if (themeSwitch) {
      themeSwitch.addEventListener('change', (e) => {
        window.DWTheme.apply(e.target.checked ? 'dark' : 'light');
        localStorage.setItem('dwai_theme', e.target.checked ? 'dark' : 'light');
      });
    }
    if (musicSwitch) {
      musicSwitch.addEventListener('change', (e) => { e.target.checked ? window.DWMusic.play() : window.DWMusic.pause(); });
    }
    if (fxSwitch) {
      fxSwitch.checked = window.DWSound ? window.DWSound.isEnabled() : true;
      fxSwitch.addEventListener('change', (e) => {
        if (window.DWSound) window.DWSound.setEnabled(e.target.checked);
        const widgetBtn = document.getElementById('soundFxToggleBtn');
        if (widgetBtn && window.DWSound) widgetBtn.innerHTML = icon(window.DWSound.isEnabled() ? 'soundOn' : 'soundOff');
      });
    }
    if (motionSwitch) {
      motionSwitch.checked = window.DWMotion.prefersReduced();
      motionSwitch.addEventListener('change', (e) => window.DWMotion.setReduced(e.target.checked));
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
        if (window.DWGuide) window.DWGuide.explain('settings_panel');
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

  window.DWChrome = {
    init, wireCommonToggles, wireModalOpenClose, ensureSettingsModal,
    ensureSoundFxWidgetButton, ensureNavButtons, wireNotifBell, refreshNotifBadge,
  };
})();
