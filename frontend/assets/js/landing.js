/* index.html's controller: the pre-login marketing/landing page. No
   auth, no API calls - just i18n/theme/mascot init and the "what
   brings you here" intake chips that personalize the CTA copy. */
document.addEventListener('DOMContentLoaded', () => {
  window.DWI18n.init();
  window.DWMascot.init();

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00006, linkDist: 130, speed: 0.2 });

  // Scroll-reveal (honours reduced motion via the shared helper)
  window.DWMotion.observeReveals();

  // Intake chips -> stash preference for onboarding prefill
  const chips = document.querySelectorAll('#intakeChips .chip-option');
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((c) => c.classList.remove('selected'));
      chip.classList.add('selected');
      localStorage.setItem('dwai_intake_goal', chip.dataset.val);
    });
  });

  // Playful live counter tick
  const counter = document.getElementById('liveCounter');
  if (counter) {
    setInterval(() => {
      const base = parseInt(counter.textContent.replace(/,/g, ''), 10) || 1204;
      counter.textContent = (base + Math.floor(Math.random() * 3)).toLocaleString();
    }, 4000);
  }

  // If already logged in, send returning users straight into the app.
  if (window.DWApi.isAuthed()) {
    document.querySelectorAll('a[href="app.html"]').forEach((a) => { a.dataset.i18n = a.dataset.i18n; });
  }
});
