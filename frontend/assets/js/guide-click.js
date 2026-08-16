/*
  DWGuideClick - every click in the app gets an answer.

  Before this file, the guide spoke for 42 hand-marked [data-guide]
  elements and stayed silent everywhere else. That is a guide that is
  present on some parts of a page and absent on others, and a user
  learns that distinction fast: two taps that produce nothing and they
  stop tapping. The requirement here is the opposite one - whatever you
  click, I say something about it.

  How it decides what to say, walking outward from the clicked node to
  <body> and stopping at the first hit:

    1. a badge tile              -> that badge, composed by DWBadgeText
    2. [data-guide]              -> its topic (deferred if already bound)
    3. [data-guide-topic]        -> an explicit hint on a control
    4. a nav link                -> the page it leads to
    5. a known control selector  -> the matching ctl_* topic
    6. nothing matched           -> the page's own overview topic

  Step 6 is what makes the coverage total rather than nearly-total: the
  fallback is never silence. Clicking a decorative panel tells you what
  page you are on and what it is for, which is a worse answer than the
  specific ones above but a better one than nothing.

  Two things this deliberately does NOT do:

  - It does not fire twice. Elements wired by DWGuide.attach() (and the
    Hall of Fame tiles) already speak on their own click handler, so
    they are marked __dwGuideBound and this layer stands down for them.
    The listener runs in the CAPTURE phase precisely so that attach()'s
    stopPropagation() cannot hide a click from the resolver - it sees
    every click, then decides whether to yield.

  - It does not repeat itself. Clicking five times inside the same card
    speaks once; a different topic always interrupts immediately. Without
    that, a double-click read as two bubbles and the second one cut the
    first one's voice off mid-sentence.

  Fatigue rules do not apply here on purpose. Auto-shown help backs off
  when dismissed (see guide-tips.js), but a click is a request, and
  refusing to answer a request is the one behaviour that would make the
  guide feel broken rather than polite.
*/
(function () {
  /* Same-topic clicks inside this window are treated as one gesture -
     long enough to swallow a double-click and an accidental
     click-through, short enough that genuinely asking again works. */
  const REPEAT_MS = 1200;

  /* Which overview topic each page falls back to. Keyed by file name so
     it works from a static file server and from the API's mount alike. */
  const PAGE_OF_FILE = {
    'dashboard.html': 'dashboard',
    'app.html': 'checkin',
    'weekly.html': 'weekly',
    'coach.html': 'coach',
    'analytics.html': 'analytics',
    'whatif.html': 'whatif',
    'model-performance.html': 'model',
    'profile.html': 'profile',
    'league.html': 'league',
    'hall.html': 'hall_of_fame',
    'about.html': 'about',
    'terms.html': 'ctl_legal',
    'index.html': 'landing',
    '': 'landing',
  };

  /* Controls, most specific first. The selectors are the ones actually
     in the markup - checked against the pages rather than invented, so
     a rename breaks the test in tests/test_guide_click_coverage.py
     instead of silently falling through to the page topic. */
  const CONTROL_TOPICS = [
    ['#mascotBtn, .mascot-btn, #mascotBubble', 'ctl_mascot'],
    ['[data-guide-tour], #settingsTourBtn', 'ctl_tour'],
    ['[data-lang-select], .select-pill', 'ctl_language'],
    ['[data-theme-toggle], #settingsThemeSwitch', 'ctl_theme'],
    ['#settingsSoundFxSwitch, #soundFxToggleBtn, [data-sound-toggle]', 'ctl_sound_fx'],
    ['#musicWidget, #settingsMusicSwitch', 'ctl_music'],
    ['#settingsMotionSwitch', 'ctl_motion'],
    ['[data-logout], #logoutBtn, #settingsLogoutBtn', 'ctl_logout'],
    ['#settingsCloseBtn, .modal-close, [data-close]', 'ctl_dismiss'],
    ['#settingsBtn, #settingsModal', 'ctl_settings'],
    ['#wizardNext, #wizardBack, .wizard-nav, [data-step-next], [data-step-prev]', 'ctl_step_nav'],
    ['#exportDataBtn, #exportCsvBtn, #downloadPdfBtn, #weeklyCardDownloadBtn, #csvTemplateBtn', 'ctl_export'],
    ['a[href*="terms"]', 'ctl_legal'],
    ['.navbar, .app-nav-row', 'ctl_nav'],
    ['button[type="submit"], .btn-primary', 'ctl_primary_action'],
    ['input, textarea, select, .switch', 'ctl_field'],
  ];

  /* Never speak for these. The bubble's own close button is the one that
     matters: answering it would reopen the bubble the user just shut,
     which is a loop, not a feature. */
  const IGNORE = '.mascot-bubble-close, [data-guide-ignore]';

  let lastTopic = null;
  let lastAt = 0;

  function pageTopic() {
    const declared = document.body && document.body.dataset.dwPage;
    if (declared) return declared;
    const file = (location.pathname.split('/').pop() || '').toLowerCase();
    return PAGE_OF_FILE[file] || 'dashboard';
  }

  /* A badge object for DWBadgeText. Tiles that hold the real record
     expose it directly; the rest carry enough on data-* attributes to
     compose a correct sentence, which is what lets a badge rendered by
     any page be explained without that page knowing about the guide. */
  function badgeFrom(el) {
    if (el.__dwBadge) return el.__dwBadge;
    const d = el.dataset;
    return {
      id: d.badgeId,
      earned: d.badgeEarned === '1',
      evaluable: d.badgeEvaluable !== '0',
      private: d.badgePrivate === '1',
      tier: d.badgeTier || null,
      progress: d.badgeProgress ? Number(d.badgeProgress) : null,
      target: d.badgeTarget ? Number(d.badgeTarget) : null,
      params: {},
    };
  }

  function speakBadge(el) {
    const T = window.DWBadgeText;
    if (!T || !window.DWGuide || !window.DWGuide.speak) return false;
    const badge = badgeFrom(el);
    if (!badge.id || !T.has(badge.id)) return false;
    const topic = 'badge_' + badge.id;
    if (topic === lastTopic && Date.now() - lastAt < REPEAT_MS) return true;
    lastTopic = topic;
    lastAt = Date.now();
    return window.DWGuide.speak(T.speech(badge), {
      face: badge.earned ? 'great' : 'thinking',
      topic: topic,
      force: true,
    });
  }

  function speakTopic(topic) {
    if (!topic || !window.DWGuide) return false;
    if (topic === lastTopic && Date.now() - lastAt < REPEAT_MS) return true;
    lastTopic = topic;
    lastAt = Date.now();
    // force: a click is an explicit request, so the cooldown and the
    // global quiet window both stand aside for it.
    return window.DWGuide.explain(topic, { force: true });
  }

  function matches(el, selector) {
    return el.matches ? el.matches(selector) : false;
  }

  /** What a click on `target` should produce. Exported for the tests,
   *  which drive it with detached DOM rather than real clicks. */
  function resolve(target) {
    let el = target;
    while (el && el.nodeType === 1 && el !== document.body) {
      if (matches(el, IGNORE)) return { kind: 'ignore', node: el };
      if (el.dataset && el.dataset.badgeId) {
        return { kind: el.__dwGuideBound ? 'bound' : 'badge', node: el };
      }
      if (el.dataset && el.dataset.guide) {
        return { kind: el.__dwGuideBound ? 'bound' : 'topic', topic: el.dataset.guide, node: el };
      }
      if (el.dataset && el.dataset.guideTopic) {
        return { kind: 'topic', topic: el.dataset.guideTopic, node: el };
      }
      // A nav link explains where it goes, which is more useful than
      // explaining that it is a link.
      if (matches(el, 'a[data-page]')) {
        return { kind: 'topic', topic: el.dataset.page, node: el };
      }
      for (let i = 0; i < CONTROL_TOPICS.length; i += 1) {
        if (matches(el, CONTROL_TOPICS[i][0])) {
          return { kind: 'topic', topic: CONTROL_TOPICS[i][1], node: el };
        }
      }
      el = el.parentElement;
    }
    return { kind: 'topic', topic: pageTopic(), node: null };
  }

  function onClick(e) {
    if (!e.target || e.target.nodeType !== 1) return;
    const found = resolve(e.target);
    if (found.kind === 'ignore' || found.kind === 'bound') return;
    if (found.kind === 'badge') { speakBadge(found.node); return; }
    speakTopic(found.topic);
  }

  document.addEventListener('click', onClick, true);

  window.DWGuideClick = {
    resolve, speakBadge, speakTopic, pageTopic,
    CONTROL_TOPICS, PAGE_OF_FILE,
  };
})();
