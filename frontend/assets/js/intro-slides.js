/*
  First-run intro slideshow. Shown once automatically (localStorage
  flag), replayable any time from Settings. Auto-advances every 6s,
  fully skippable at any point (click, Esc, or the Skip button), and
  never blocks the app underneath - closing it always leaves the user
  exactly where they were.
*/
(function () {
  const SEEN_KEY = 'dwai_intro_seen';
  const AUTOADVANCE_MS = 6000;

  function slidesFor(lang) {
    const fa = lang === 'fa';
    return [
      {
        icon: '👋',
        title: fa ? 'به Digital Wellness AI خوش آمدی' : 'Welcome to Digital Wellness AI',
        body: fa
          ? 'این اپ عادت‌های واقعی روزانه‌ات را با یک مدل یادگیری ماشین آموزش‌دیده می‌خواند. هر عددی که می‌بینی، از داده‌ی خودت می‌آید — نه یک فال یا میانگین ساختگی.'
          : 'This app reads your real daily habits with a trained machine-learning model. Every number you see comes from your own data — never a horoscope, never a fabricated average.',
      },
      {
        icon: '🎯',
        title: fa ? 'چک‌این و دایره‌ی امتیاز' : 'Check-in & the score ring',
        body: fa
          ? 'یک بررسی روزانه پر می‌کنی و یک پیش‌بینی واقعی می‌گیری. دایره‌ی رنگی مرکزش امتیاز واقعی مدل رگرسیون است؛ ۴ کمانِ دورش تفکیک شفاف ابعاد سلامت تو هستند.'
          : "You fill in a daily check-in and get a real prediction. The ring's center is the real regression model's score; the four arcs around it are a transparent breakdown of your wellness dimensions.",
      },
      {
        icon: '🤖',
        title: fa ? 'مربی هوش مصنوعی' : 'Your AI Coach',
        body: fa
          ? 'بیش از ۵۰ سوال آماده داری که هرکدام از داده‌ی واقعی و فعلی‌ات پاسخ داده می‌شوند — علاوه بر یک چت آزاد. صادقانه بگویم: این یک موتور قانون‌محور هوشمند است، نه یک مدل زبانی بیرونی.'
          : "You get 50+ ready-made questions, each answered from your own real, current data — plus a free-text chat. Honestly: this is a smart rule-based engine, not an external language model.",
      },
      {
        icon: '🗓️',
        title: fa ? 'برنامه‌ی هفتگی و کارت هفته' : 'Weekly plan & shareable card',
        body: fa
          ? 'یک برنامه‌ی ۷ روزه از ضعیف‌ترین سیگنال‌های آخرین بررسی‌ات ساخته می‌شود، و می‌توانی یک کارت تصویری قابل‌دانلود از هفته‌ات بگیری.'
          : 'A 7-day plan is built from your last check-in\'s weakest signals, and you can download a shareable image card of your week.',
      },
      {
        icon: '⚙️',
        title: fa ? 'تنظیمات' : 'Settings',
        body: fa
          ? 'تم، صدای محیطی، جلوه‌های صوتی و کاهش حرکت، همه کلیدهای مستقل‌اند. «حالت دمو» هم آنجاست — با یک کلیک کل اپ را با یک نمونه‌ی واقع‌گرایانه‌ی ۲۳ روزه پر می‌کند.'
          : 'Theme, ambient sound, sound effects and reduced motion are all independent switches. Demo Mode lives there too — one click fills the whole app with a realistic 23-day sample.',
      },
      {
        icon: '🏅',
        title: fa ? 'لیگ دوستان' : 'Friends League',
        body: fa
          ? 'مقایسه‌ی اصلی همیشه با گذشته‌ی خودت است. یک دوست فقط بعد از اینکه صریحاً کد دعوتت را وارد کرد و تو درخواستش را تایید کردی، و فقط برای دسته‌هایی که تیک زده‌ای (پرسونا، امتیاز، رتبه، مهم‌ترین عامل)، چیزی می‌بیند. هر لحظه می‌توانی این را تغییر بدهی یا کاملاً قطع کنی.'
          : "The main comparison is always against your own past. A friend only sees anything after they've entered your invite code AND you've explicitly approved the request, and only for the exact categories you've ticked — persona, score, rank, top factor. You can change or revoke this at any moment.",
      },
      {
        icon: '🔒',
        title: fa ? 'حریم خصوصی' : 'Privacy',
        body: fa
          ? 'هر وقت خواستی، از پروفایل خودت می‌توانی همه‌چیزی که این اپ درباره‌ات ذخیره کرده را خروجی بگیری، یا حساب و تاریخچه‌ات را برای همیشه حذف کنی.'
          : "Any time, from your Profile, you can export everything this app has stored about you, or permanently delete your account and history.",
      },
    ];
  }

  function finalSlide(lang) {
    const fa = lang === 'fa';
    return {
      icon: '🚀',
      title: fa ? 'آماده‌ای؟' : 'Ready?',
      body: fa
        ? 'همین حالا اولین بررسی‌ات را انجام بده، یا اگر فقط می‌خواهی همه‌چیز را با داده‌ی نمایشی ببینی، حالت دمو را امتحان کن.'
        : "Run your first real check-in now, or if you just want to see everything populated, try Demo Mode.",
      final: true,
    };
  }

  let overlay = null, idx = 0, timer = null, list = [];

  function clearTimer() { if (timer) clearInterval(timer); timer = null; }

  function paint() {
    if (!overlay) return;
    const s = list[idx];
    overlay.querySelector('#introIcon').textContent = s.icon;
    overlay.querySelector('#introTitle').textContent = s.title;
    overlay.querySelector('#introBody').textContent = s.body;
    overlay.querySelector('#introDots').innerHTML = list.map((_, i) =>
      `<span class="intro-dot${i === idx ? ' active' : ''}"></span>`).join('');
    const ctaRow = overlay.querySelector('#introCtaRow');
    const navRow = overlay.querySelector('#introNavRow');
    if (s.final) {
      ctaRow.classList.remove('hidden');
      navRow.classList.add('hidden');
    } else {
      ctaRow.classList.add('hidden');
      navRow.classList.remove('hidden');
    }
  }

  function goTo(i) {
    idx = Math.max(0, Math.min(list.length - 1, i));
    paint();
    restartTimer();
  }

  function restartTimer() {
    clearTimer();
    if (idx >= list.length - 1) return;
    timer = setInterval(() => {
      if (idx < list.length - 1) goTo(idx + 1); else clearTimer();
    }, AUTOADVANCE_MS);
  }

  function close() {
    clearTimer();
    if (overlay) { overlay.remove(); overlay = null; }
    document.body.style.overflow = '';
    try { localStorage.setItem(SEEN_KEY, '1'); } catch (e) {}
  }

  function build() {
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    list = slidesFor(lang).concat([finalSlide(lang)]);
    const el = document.createElement('div');
    el.className = 'intro-overlay';
    el.innerHTML = `
      <div class="intro-box">
        <button type="button" class="intro-skip" id="introSkip">${lang === 'fa' ? 'رد کردن' : 'Skip'} ✕</button>
        <div class="intro-icon" id="introIcon"></div>
        <h2 class="intro-title" id="introTitle"></h2>
        <p class="intro-body" id="introBody"></p>
        <div class="intro-dots" id="introDots"></div>
        <div class="intro-nav-row" id="introNavRow">
          <button type="button" class="btn btn-ghost btn-sm" id="introPrev">${lang === 'fa' ? 'قبلی' : 'Back'}</button>
          <button type="button" class="btn btn-primary btn-sm" id="introNext">${lang === 'fa' ? 'بعدی' : 'Next'}</button>
        </div>
        <div class="intro-cta-row hidden" id="introCtaRow">
          <a class="btn btn-primary btn-shine" href="app.html">${lang === 'fa' ? 'شروع بررسی' : 'Run a check-in'}</a>
          <button type="button" class="btn btn-ghost" id="introDemoBtn">${lang === 'fa' ? 'دیدن دمو' : 'See a demo'}</button>
        </div>
      </div>`;
    document.body.appendChild(el);
    overlay = el;

    el.querySelector('#introSkip').addEventListener('click', close);
    el.querySelector('#introPrev').addEventListener('click', () => goTo(idx - 1));
    el.querySelector('#introNext').addEventListener('click', () => goTo(idx + 1));
    el.querySelector('#introDemoBtn').addEventListener('click', () => {
      close();
      if (window.DWDemo) window.DWDemo.run();
    });
    el.addEventListener('click', (e) => { if (e.target === el) close(); });
    document.addEventListener('keydown', function onKey(e) {
      if (!overlay) { document.removeEventListener('keydown', onKey); return; }
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowRight') goTo(idx + 1);
      if (e.key === 'ArrowLeft') goTo(idx - 1);
    });
    document.body.style.overflow = 'hidden';
  }

  function show(opts) {
    opts = opts || {};
    if (!opts.force) {
      let seen = null;
      try { seen = localStorage.getItem(SEEN_KEY); } catch (e) {}
      if (seen === '1') return;
    }
    if (overlay) return;
    idx = 0;
    build();
    paint();
    restartTimer();
  }

  window.DWIntro = { show, close };
})();
