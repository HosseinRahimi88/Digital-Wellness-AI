/*
  Narrative processing screen, shared by the prediction flow and the AI
  Coach's /fit preparation step.

  Honesty rules baked in:
  - The step labels describe work the backend genuinely does for that
    flow (validate -> predict -> explain -> recommend -> persist). No
    invented steps.
  - There is a MIN_SHOW floor (~2.8s) so the sequence is legible, but
    NO artificial ceiling: if the real request takes longer, the screen
    keeps waiting honestly instead of lying that it finished. If the
    request finishes first we still finish the remaining steps quickly
    rather than freezing on step 2.
  - Skippable: click, Esc, or any key dismisses the presentation and
    jumps straight to the result. Nothing is gated behind the animation.
*/
(function () {
  /* Minimum time the narrated sequence stays on screen.
     Raised from 2.8s to 9s on an explicit product decision: the steps
     are real work descriptions and the rotating cards teach something,
     so the screen is content rather than a spinner - and in practice a
     real SHAP-explained prediction often takes longer than this anyway,
     in which case the floor never applies at all.
     Two guarantees keep this honest and keep it from being a fake wait:
       - it is a FLOOR, never a ceiling: if the request finishes sooner
         the screen still respects the floor, but if it takes longer the
         screen keeps waiting rather than pretending it finished;
       - it is always skippable (click / Esc / Enter / Space), so nobody
         is ever held here against their will. */
  const MIN_SHOW_MS = 9000;

  const STEPS = {
    predict: {
      en: [
        'Validating your inputs…',
        'Comparing today against your own baseline…',
        'Running the wellness model…',
        'Isolating the signals that moved your score…',
        'Building your recommendations…',
      ],
      fa: [
        'در حال اعتبارسنجی ورودی‌هایت…',
        'مقایسه‌ی امروز با خط پایه‌ی خودت…',
        'اجرای مدل سلامت دیجیتال…',
        'جداکردن سیگنال‌هایی که امتیازت را جابه‌جا کردند…',
        'ساخت توصیه‌های شخصی‌ات…',
      ],
      ar: ['التحقق من مدخلاتك…', 'مقارنة اليوم بخط الأساس الخاص بك…', 'تشغيل نموذج العافية…', 'عزل الإشارات المؤثرة…', 'بناء توصياتك…'],
      zh: ['正在校验你的输入…', '正在与你自己的基线对比…', '正在运行健康模型…', '正在分离影响分数的信号…', '正在生成你的建议…'],
    },
    coach: {
      en: [
        'Loading your latest check-in…',
        'Reading the signals behind your score…',
        'Collecting your current recommendations…',
        'Preparing your coaching context…',
      ],
      fa: [
        'در حال بارگذاری آخرین بررسی‌ات…',
        'خواندن سیگنال‌های پشت امتیازت…',
        'جمع‌آوری توصیه‌های فعلی‌ات…',
        'آماده‌سازی زمینه‌ی گفتگوی مربی…',
      ],
      ar: ['تحميل آخر فحص لك…', 'قراءة الإشارات وراء درجتك…', 'جمع توصياتك الحالية…', 'تهيئة سياق التدريب…'],
      zh: ['正在加载你最近的检测…', '正在读取分数背后的信号…', '正在收集你当前的建议…', '正在准备教练上下文…'],
    },
    demo: {
      en: [
        'Building 23 days of realistic check-ins…',
        'Running each day through the real model…',
        'Assigning a persona from the pattern…',
        'Connecting a demo friend in the League…',
        'Wiring up your Coach, plans, and analytics…',
      ],
      fa: [
        'در حال ساخت ۲۳ روز بررسی واقع‌گرایانه…',
        'اجرای هر روز روی مدل واقعی…',
        'تعیین پرسونا از روی الگو…',
        'وصل‌کردن یک دوست نمایشی در لیگ…',
        'آماده‌سازی مربی، برنامه‌ها و تحلیل‌ها…',
      ],
      ar: ['بناء 23 يوماً من الفحوصات الواقعية…', 'تشغيل كل يوم عبر النموذج الحقيقي…', 'تعيين شخصية من النمط…', 'ربط صديق تجريبي في الدوري…'],
      zh: ['正在构建23天的真实检测…', '正在对每一天运行真实模型…', '正在根据模式分配人格…', '正在联赛中连接一位演示好友…'],
    },
  };

  function stepsFor(flow) {
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const set = STEPS[flow] || STEPS.predict;
    return set[lang] || set.en;
  }

  function buildOverlay() {
    const el = document.createElement('div');
    el.className = 'proc-overlay';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    el.innerHTML = `
      <div class="proc-box">
        <div class="proc-gear-wrap">
          <svg class="proc-gear" viewBox="0 0 120 120" aria-hidden="true">
            <defs>
              <linearGradient id="procGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#22f5c6"/><stop offset="100%" stop-color="#3aa7ff"/>
              </linearGradient>
            </defs>
            <circle class="proc-ring-outer" cx="60" cy="60" r="46" fill="none" stroke="url(#procGrad)" stroke-width="3"
                    stroke-linecap="round" stroke-dasharray="60 230"/>
            <circle class="proc-ring-mid" cx="60" cy="60" r="33" fill="none" stroke="url(#procGrad)" stroke-width="2.5"
                    stroke-linecap="round" stroke-dasharray="40 170" opacity=".75"/>
            <g class="proc-cog">
              <circle cx="60" cy="60" r="15" fill="none" stroke="url(#procGrad)" stroke-width="3"/>
              <g stroke="url(#procGrad)" stroke-width="3" stroke-linecap="round">
                <line x1="60" y1="38" x2="60" y2="45"/><line x1="60" y1="75" x2="60" y2="82"/>
                <line x1="38" y1="60" x2="45" y2="60"/><line x1="75" y1="60" x2="82" y2="60"/>
                <line x1="45" y1="45" x2="50" y2="50"/><line x1="70" y1="70" x2="75" y2="75"/>
                <line x1="75" y1="45" x2="70" y2="50"/><line x1="50" y1="70" x2="45" y2="75"/>
              </g>
            </g>
          </svg>
        </div>

        <ol class="proc-steps" id="procSteps"></ol>
        <div class="proc-progress"><div class="proc-progress-fill" id="procProgressFill"></div></div>

        <div class="proc-tip card" id="procTip">
          <span class="proc-tip-cat" id="procTipCat"></span>
          <p class="proc-tip-text" id="procTipText"></p>
        </div>

        <p class="proc-skip muted" id="procSkip"></p>
      </div>`;
    return el;
  }

  const CAT_LABEL = {
    en: { fact: 'Did you know', tip: 'Try this', motivation: 'Keep going' },
    fa: { fact: 'می‌دانستی', tip: 'این را امتحان کن', motivation: 'ادامه بده' },
    ar: { fact: 'هل تعلم', tip: 'جرّب هذا', motivation: 'واصل' },
    zh: { fact: '你知道吗', tip: '试试这个', motivation: '继续加油' },
  };
  const SKIP_HINT = {
    en: 'Click or press Esc to skip',
    fa: 'برای رد کردن کلیک کن یا Esc را بزن',
    ar: 'انقر أو اضغط Esc للتخطي',
    zh: '点击或按 Esc 跳过',
  };

  /**
   * @param {Promise} work  the real request; the screen waits on it.
   * @param {object}  opts  { flow: 'predict'|'coach' }
   * @returns {Promise} resolves with the work's value once the
   *                    presentation has had its minimum time (or was
   *                    skipped). Rejects if the work rejects.
   */
  function run(work, opts) {
    opts = opts || {};
    const flow = opts.flow || 'predict';
    const minMs = opts.minMs || MIN_SHOW_MS;
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const reduced = window.DWMotion && window.DWMotion.prefersReduced();
    const steps = stepsFor(flow);

    const overlay = buildOverlay();
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';

    const stepsEl = overlay.querySelector('#procSteps');
    steps.forEach((label, i) => {
      const li = document.createElement('li');
      li.className = 'proc-step';
      li.dataset.index = String(i);
      li.innerHTML = `<span class="proc-step-dot" aria-hidden="true"></span><span class="proc-step-label"></span>`;
      li.querySelector('.proc-step-label').textContent = label;
      stepsEl.appendChild(li);
    });
    overlay.querySelector('#procSkip').textContent = SKIP_HINT[lang] || SKIP_HINT.en;

    const fill = overlay.querySelector('#procProgressFill');
    const tipCat = overlay.querySelector('#procTipCat');
    const tipText = overlay.querySelector('#procTipText');
    const tipBox = overlay.querySelector('#procTip');

    const rotator = window.DWLoadingMessages.createRotator(lang);
    function showTip() {
      const m = rotator.next();
      if (!m) return;
      const labels = CAT_LABEL[lang] || CAT_LABEL.en;
      const apply = () => {
        tipCat.textContent = labels[m.c] || '';
        tipCat.className = `proc-tip-cat cat-${m.c}`;
        tipText.textContent = m.t;
        tipBox.classList.remove('fading');
      };
      if (reduced) { apply(); return; }
      tipBox.classList.add('fading');
      setTimeout(apply, 260);
    }
    showTip();
    // Paced so roughly three different cards are seen across the
    // minimum window - long enough to actually read one, short enough
    // that the screen never feels stalled.
    const tipTimer = reduced ? null : setInterval(showTip, 3000);

    let stepIdx = -1;
    function advance(to) {
      if (to <= stepIdx) return;
      stepIdx = Math.min(to, steps.length - 1);
      Array.from(stepsEl.children).forEach((li, i) => {
        li.classList.toggle('is-active', i === stepIdx);
        li.classList.toggle('is-done', i < stepIdx);
      });
      fill.style.width = `${((stepIdx + 1) / steps.length) * 100}%`;
    }
    advance(0);

    // Pace the narrated steps across the minimum window. If the real
    // work is still running when we reach the last step, we simply hold
    // there - honest "still working", not a fake extra step.
    const perStep = minMs / steps.length;
    let stepTimer = setInterval(() => {
      if (stepIdx < steps.length - 1) advance(stepIdx + 1);
    }, perStep);

    const started = performance.now();
    let settled = false;

    function cleanup() {
      if (tipTimer) clearInterval(tipTimer);
      if (stepTimer) clearInterval(stepTimer);
      document.removeEventListener('keydown', onKey, true);
      overlay.removeEventListener('click', onSkip);
      document.body.style.overflow = '';
      overlay.classList.add('is-leaving');
      setTimeout(() => overlay.remove(), reduced ? 0 : 260);
    }

    let skipResolve = null;
    const skipped = new Promise((res) => { skipResolve = res; });
    function onSkip() { if (!settled) { settled = true; skipResolve(); } }
    function onKey(e) {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSkip(); }
    }
    overlay.addEventListener('click', onSkip);
    document.addEventListener('keydown', onKey, true);

    if (window.DWMascot) window.DWMascot.react('thinking', { sticky: true });
    if (window.DWSound) window.DWSound.processingStart();

    return new Promise((resolve, reject) => {
      work.then(
        async (value) => {
          const elapsed = performance.now() - started;
          const remaining = Math.max(0, minMs - elapsed);
          // Race the remaining presentation time against an explicit
          // skip - whichever comes first.
          if (remaining > 0 && !settled) {
            await Promise.race([new Promise((r) => setTimeout(r, remaining)), skipped]);
          }
          advance(steps.length - 1);
          if (window.DWSound) window.DWSound.stopProcessing();
          cleanup();
          resolve(value);
        },
        (err) => { if (window.DWSound) window.DWSound.stopProcessing(); cleanup(); reject(err); }
      );
    });
  }

  window.DWProcessing = { run, MIN_SHOW_MS };
})();
