/* Dark/light theme toggle, persisted to localStorage. Dispatches
   `dwai:themechange` so canvas-based renderers (particles.js) can
   re-read theme-dependent colors without a full page reload. */
(function () {
  const KEY = 'dwai_theme';
  const root = document.documentElement;

  function apply(theme) {
    root.setAttribute('data-theme', theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'light' ? '#f3faf8' : '#05080f');
    const SUN = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.4M12 19.1v2.4M4.2 4.2l1.7 1.7M18.1 18.1l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.2 19.8l1.7-1.7M18.1 5.9l1.7-1.7"/></svg>';
    const MOON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5Z"/></svg>';
    document.querySelectorAll('[data-theme-icon]').forEach((el) => {
      el.innerHTML = theme === 'light' ? MOON : SUN;
    });
    // Canvas-drawn surfaces read their colours from CSS custom
    // properties, so they need an explicit nudge to re-read them.
    document.dispatchEvent(new CustomEvent('dwai:themechange', { detail: { theme } }));
  }

  function get() {
    return localStorage.getItem(KEY) ||
      (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  }

  function toggle() {
    const next = get() === 'dark' ? 'light' : 'dark';
    localStorage.setItem(KEY, next);
    apply(next);
    return next;
  }

  apply(get());

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-theme-toggle]');
    if (btn) toggle();
  });

  window.DWTheme = { get, toggle, apply };
})();
