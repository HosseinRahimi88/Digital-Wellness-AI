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
    if (window.DWMotion) {
      window.DWMotion.syncReducedClass();
      const main = document.querySelector('.app-main');
      if (main && !window.DWMotion.prefersReduced()) main.classList.add('page-enter');
      window.DWMotion.observeReveals();
    }
    if (window.DWMascot.init) window.DWMascot.init();
    if (window.DWMusic && window.DWMusic.init) window.DWMusic.init();
    if (!requireAuth()) return null;
    highlightNav(pageKey);
    wireLogout();

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
