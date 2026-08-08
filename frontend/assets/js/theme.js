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
    document.querySelectorAll('[data-theme-icon]').forEach((el) => {
      el.textContent = theme === 'light' ? '🌙' : '☀️';
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
