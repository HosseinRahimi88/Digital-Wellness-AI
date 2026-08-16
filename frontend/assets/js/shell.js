/*
  Shared bootstrap for every logged-in app page except app.html (which
  owns the auth/onboarding/wizard flow itself). Handles: redirecting
  anonymous visitors back to app.html, highlighting the active nav
  link, wiring the shared theme/lang/logout controls, and exposing the
  current account to the page that asked for it.
*/
(function () {
  function requireAuth() {
    if (!window.DWApi.isAuthed()) {
      location.href = 'app.html';
      return false;
    }
    return true;
  }

  function highlightNav(pageKey) {
    document.querySelectorAll('.app-nav-link').forEach((a) => {
      a.classList.toggle('active', a.dataset.page === pageKey);
    });
  }

  function wireLogout() {
    document.querySelectorAll('[data-logout]').forEach((btn) => {
      btn.addEventListener('click', () => {
        window.DWApi.clearToken();
        location.href = 'app.html';
      });
    });
  }

  async function init(pageKey) {
    window.DWI18n.init();
    // Published so the click layer can fall back to this page's own
    // overview topic. Reading it from here rather than re-deriving it
    // from the URL means a page mounted at a different path still
    // resolves to the right topic.
    if (document.body) document.body.dataset.dwPage = pageKey;
    if (window.DWMotion) {
      window.DWMotion.syncReducedClass();
      // The page-in animation is declared on .app-main in animations.css
      // so it is already running at first paint. Adding it here instead
      // meant the content was painted and then snapped back to
      // invisible, which is exactly the half-second blank the fix in
      // that file describes - so this no longer touches the class.
      window.DWMotion.observeReveals();
    }
    if (window.DWMascot.init) {
      // Tapping the mascot re-explains the current page on demand, so
      // the guide is always reachable and never a one-shot popup.
      window.DWMascot.init({
        onClick: () => {
          if (window.DWGuide) window.DWGuide.explain(pageKey, { force: true });
        },
      });
    }
    if (window.DWMusic && window.DWMusic.init) window.DWMusic.init();
    if (!requireAuth()) return null;
    highlightNav(pageKey);
    if (window.DWChrome && window.DWChrome.init) window.DWChrome.init();
    wireLogout();

    if (window.DWGuide) {
      // Section-level help: any element marked data-guide="..." becomes
      // its own help trigger.
      window.DWGuide.autoAttach();
      // The guide NEVER speaks on its own when a page opens. It used to
      // auto-run startTour()/explain() 1.6s after every page load, which
      // meant a bubble (and, with voice on, speech) greeted the user on
      // every single navigation - reported twice as the single most
      // irritating thing in the app.
      //
      // Everything the guide can say is still fully reachable, just
      // always by the user's own action: tapping the mascot explains the
      // current page (see the onClick wired above), any [data-guide]
      // element explains its own section, and [data-guide-tour] runs the
      // full page tour on demand.
      document.querySelectorAll('[data-guide-tour]').forEach((btn) => {
        btn.addEventListener('click', () => window.DWGuide.startTour(pageKey, { force: true }));
      });
    }

    document.addEventListener('dwai:unauthorized', () => { location.href = 'app.html'; });

    try {
      const account = await window.DWApi.me();
      document.querySelectorAll('[data-account-name]').forEach((el) => { el.textContent = account.display_name || account.email; });
      document.querySelectorAll('[data-account-email]').forEach((el) => { el.textContent = account.email; });
      return account;
    } catch (e) {
      location.href = 'app.html';
      return null;
    }
  }

  window.DWShell = { init, requireAuth, highlightNav };
})();
