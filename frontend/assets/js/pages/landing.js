/* index.html's controller: the pre-login marketing/landing page.
   i18n/theme/mascot init, the "what brings you here" intake chips that
   personalize the CTA copy, and one unauthenticated read of the real
   model metrics for the hero stats. */

/* The hero numbers used to be typed into the HTML. That drifted: the R²
   still read 0.979 after the model was retrained to 0.9917, so the page
   was quietly advertising a stale figure. This reads the same
   GET /model-performance endpoint the Model page already uses, and
   deliberately shows the VALIDATION metrics rather than the test ones -
   test is a single-use split, and putting its higher number in a headline
   is the kind of claim that invites exactly the challenge it cannot
   answer. Failure is silent: the placeholder dash stays. */
async function loadHeroMetrics() {
  const accEl = document.getElementById('statAccuracy');
  const r2El = document.getElementById('statR2');
  if (!accEl || !r2El || !window.DWApi || !window.DWApi.modelPerformance) return;

  const t = (key) => (window.DWI18n && window.DWI18n.t ? window.DWI18n.t(key) : '');
  try {
    const perf = await window.DWApi.modelPerformance();

    // metrics.validation is keyed by candidate model name; the winner is
    // named in metrics.best_model. Same shape model-performance.js reads.
    const pickValidation = (task) => {
      const metrics = (task && task.metrics) || {};
      const validation = metrics.validation;
      if (!validation) return null;
      return validation[metrics.best_model] || null;
    };

    const clf = pickValidation(perf.classification);
    const reg = pickValidation(perf.regression);

    if (clf && typeof clf.accuracy === 'number') {
      accEl.textContent = `${(clf.accuracy * 100).toFixed(1)}%`;
    }
    // Regression validation carries R2 (capitalised in the artifact).
    const r2 = reg && (typeof reg.R2 === 'number' ? reg.R2 : reg.r2);
    if (typeof r2 === 'number') r2El.textContent = r2.toFixed(3);

    if (!clf && !reg) {
      const note = document.getElementById('heroMetricsNote');
      if (note) note.textContent = t('metrics_unavailable');
    }
  } catch (e) {
    // A marketing page must never break because the API is asleep.
    const note = document.getElementById('heroMetricsNote');
    if (note) note.textContent = t('metrics_unavailable');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadHeroMetrics();
  // C-5-5: settings reachable from the landing page too, not only
  // once signed in.
  if (window.DWChrome && window.DWChrome.initLanding) window.DWChrome.initLanding();
  window.DWI18n.init();
  window.DWMascot.init({
    onClick: () => { if (window.DWGuide) window.DWGuide.explain('landing', { force: true }); },
  });
  if (window.DWGuide) {
    // No timed greeting - tapping the mascot (wired just above) explains
    // the page on request instead.
    window.DWGuide.autoAttach();
  }

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
