/*
  Digital Guide — the contextual help layer behind the mascot.

  Design intent: a guide that speaks once per page and goes quiet is
  decoration. This module is built so the guide can explain (a) what a
  page is for, (b) what each individual section on it means, (c) what
  each step of the check-in wizard is asking for and why it matters,
  and (d) what to do next from an empty state — all in the user's own
  language, all triggerable on demand.

  Honesty rules, same as the rest of the app:
  - The guide explains the PRODUCT, never the user's own numbers. It
    will say "this ring is your score" but never "your score is bad" —
    interpreting real values is the job of the prediction/coach layers,
    which have the actual data.
  - Nothing here claims a medical or diagnostic fact.
  - Every string exists in English and Persian; ar/zh fall back to
    English rather than shipping a machine translation.

  Public API:
    DWGuide.explain(topicKey, {force})   - speak about one topic
    DWGuide.attach(el, topicKey)         - make any element ask for help
    DWGuide.autoAttach(root)             - wire every [data-guide] in the DOM
    DWGuide.topicsFor(pageKey)           - the tour list for a page
    DWGuide.startTour(pageKey)           - walk that page's sections in order
*/
(function () {
  const SEEN_PREFIX = 'dwai_guide_seen_';
  const TOUR_PREFIX = 'dwai_guide_tour_';

  /* ---------------------------------------------------------------
     Topic copy. Keys are stable ids referenced by data-guide="..."
     attributes in the HTML and by the page tours below.
     --------------------------------------------------------------- */
  const TIPS = {
    en: {
      /* ---- Page-level overviews ---- */
      landing: "Welcome. This app reads your real daily habits with a trained machine-learning model and gives you an honest wellness score plus the exact reasons behind it. Nothing here is a horoscope — every number traces back to something you entered.",
      dashboard: "This is your home base. The ring is your most recent real score, the heatmap shows this week's check-ins, and below that are the exact factors that pushed your score up or down.",
      checkin: "This form is the only place your data comes from — nothing is pre-filled with a fake average. Answer for today, then submit to get a real prediction: a risk class, a 0–100 score, and the reasons why.",
      weekly: "This week versus last, side by side, plus a 7-day plan built from your last check-in's weakest signals — not a generic template.",
      coach: "Ask about your score, a specific area like sleep or focus, or what to prioritise. The Coach reads your real check-in and says so plainly when it doesn't have enough data.",
      analytics: "Your score over time and which weekdays tend to go better or worse — computed from your own logged history, so it gets more meaningful the more you log.",
      whatif: "A sandbox. Change one habit and watch the real model's prediction move, without touching your saved history.",
      model: "The model's real, current accuracy numbers — not marketing claims. Predicting for people it has never seen is genuinely hard, which is why these aren't 99%.",
      profile: "Your identity here: avatar, persona, badges and preferences. These personalise how the app talks to you; they never change what the model sees as input.",
      about: "How this project works, what data it uses, and where its limits are.",

      /* ---- Dashboard sections ---- */
      dash_score: "Your most recent real wellness score, 0–100, from the regression model. The arrow underneath compares it to your previous check-in — not to anyone else.",
      dash_week_avg: "The average score across this calendar week's check-ins. Days you've muted from your trend aren't counted here.",
      dash_entries: "How many check-ins you've logged in total. More entries make every trend on this page more trustworthy.",
      dash_heatmap: "Monday to Sunday of the current week. A filled square is a logged day, coloured by score. Click any square to mute that day from your averages — useful for a day you know was an outlier.",
      dash_recs: "The recommendations from your latest check-in, chosen by which factors the model found were dragging your score down.",
      dash_cohort: "How your averages compare with the wider population in the training data. Context, not a competition.",

      /* ---- Check-in wizard steps ---- */
      wizard_demographics: "Basic context about you. The model uses these to compare like with like — a student's typical pattern isn't a retiree's.",
      wizard_time: "Which day this entry describes. Weekends genuinely behave differently from weekdays in the data, so this matters.",
      wizard_screen: "Your screen minutes split by category. You don't enter a total — the app adds these up for you, so the parts can never contradict the whole.",
      wizard_device: "How fragmented your day was: notifications, pickups, app opens. In this dataset, how often you check tends to predict focus better than total hours do.",
      wizard_sleep: "Hours actually slept, and how rested you feel. Sleep is one of the strongest signals in the whole model.",
      wizard_mental: "Self-reported mood and stress. Answer honestly rather than optimistically — an inflated input gives you an inflated score, which helps nobody.",
      wizard_focus: "Focus, productivity, activity and caffeine. The last few pieces, then you get your result.",
      wizard_derived: "These are calculated from what you typed above — ratios, densities and indices the model expects. You never type these directly, so they can't disagree with your raw numbers.",
      demo_profiles: "In a hurry? Load a ready-made profile to see a full real prediction instantly. It runs the same model on the same pipeline — only the inputs are pre-filled.",
      csv_import: "Already track this elsewhere? Download the template, fill in several days at once, and upload it. Every valid row runs a real prediction and lands in your history immediately.",

      /* ---- Result page sections ---- */
      result_ring: "Your wellness score, 0–100, from the regression model. The colour band matches the same thresholds used everywhere else in the app.",
      result_confidence: "How sure the classifier is about the category it picked. Worth reading alongside the score, not instead of it.",
      result_dimensions: "A transparent, rule-based breakdown of the same inputs by area. This is plain arithmetic you could redo by hand — deliberately separate from the model's own score above.",
      result_shap: "The specific factors that moved your score, from SHAP. Green pushed it up, red pulled it down. This is the model explaining itself, not a guess.",
      result_recs: "Actions matched to the factors that hurt your score. Each one carries a success metric so you can tell whether it worked.",
      result_ood: "A warning that some of today's values sit at the very edge of what the model has seen. The score is still real; just treat it with more caution.",

      /* ---- Other sections ---- */
      weekly_plan: "A seven-day plan generated by rules from your real weakest areas. Tick tasks as you do them — progress is saved permanently, not just for this visit.",
      coach_chat: "Type a question, or /fit to load your latest check-in as context. The Coach only knows what your real data tells it.",
      analytics_trend: "Your score over time. Three or more check-ins make the direction meaningful; below that it's just points on a chart.",
      analytics_weekday: "Average score per weekday. A weekday you've only logged once is marked as low-confidence rather than presented as a pattern.",
      whatif_sweep: "Pick one field, and this runs the real model across its whole range so you can see exactly where your score turns.",
      profile_avatar: "Your picture stays on your own device and in your account record only. It's resized in your browser before saving, and it never reaches the model.",
      profile_persona: "A plain-language archetype derived from your real habits by documented rules — you can always see the numbers that earned it. Shown next to the statistical ML persona, which is a different thing.",
      profile_badges: "Earned strictly from real logged values. Each badge names the threshold it required, so none of them are mysterious.",
      profile_tone: "Changes how advice is worded — gentler, blunter, or clinical. It never changes which recommendations you get or their priority.",
      privacy_controls: "Export everything this app stores about you as a file, or delete your account and all its history permanently. Deletion cannot be undone.",
    },

    fa: {
      landing: 'خوش آمدی. این اپ عادت‌های واقعی روزانه‌ات را با یک مدل یادگیری ماشین آموزش‌دیده می‌خواند و یک امتیاز صادقانه‌ی سلامت به‌همراه دلیل دقیقش به تو می‌دهد. هیچ‌چیز اینجا فال نیست — هر عدد به چیزی که خودت وارد کرده‌ای برمی‌گردد.',
      dashboard: 'اینجا نقطه‌ی شروع توست. حلقه، آخرین امتیاز واقعی‌ات است، نقشه‌ی حرارتی چک‌این‌های این هفته را نشان می‌دهد، و پایین‌تر دقیقاً همان عواملی هستند که امتیازت را بالا یا پایین برده‌اند.',
      checkin: 'این فرم تنها منبع داده‌ی توست — هیچ‌چیزش با یک میانگین ساختگی از پیش پر نشده. برای امروز پاسخ بده و بفرست تا یک پیش‌بینی واقعی بگیری: یک دسته‌ی ریسک، یک امتیاز ۰ تا ۱۰۰، و دلیلش.',
      weekly: 'این هفته در برابر هفته‌ی قبل، کنار هم، به‌همراه یک برنامه‌ی ۷ روزه که از ضعیف‌ترین سیگنال‌های آخرین چک‌این تو ساخته شده — نه یک قالب عمومی.',
      coach: 'درباره‌ی امتیازت، یک حوزه‌ی خاص مثل خواب یا تمرکز، یا اولویت اولت بپرس. مربی داده‌ی واقعی‌ات را می‌خواند و اگر داده‌ی کافی نداشته باشد، صریح می‌گوید.',
      analytics: 'امتیازت در طول زمان و اینکه کدام روزهای هفته بهتر یا بدتر پیش می‌روند — از تاریخچه‌ی واقعی خودت محاسبه شده، پس هرچه بیشتر ثبت کنی معنادارتر می‌شود.',
      whatif: 'یک محیط آزمایشی. یک عادت را تغییر بده و ببین پیش‌بینی مدل واقعی چطور جابه‌جا می‌شود، بدون اینکه به تاریخچه‌ی ذخیره‌شده‌ات دست بخورد.',
      model: 'اعداد واقعی و فعلی دقت مدل — نه ادعای تبلیغاتی. پیش‌بینی برای افرادی که مدل هرگز ندیده واقعاً سخت است؛ برای همین این اعداد ۹۹٪ نیستند.',
      profile: 'هویت تو اینجا: تصویر، پرسونا، نشان‌ها و ترجیحات. این‌ها لحن گفتگوی اپ با تو را شخصی می‌کنند؛ هرگز ورودی مدل را تغییر نمی‌دهند.',
      about: 'اینکه این پروژه چطور کار می‌کند، از چه داده‌ای استفاده می‌کند، و محدودیت‌هایش کجاست.',

      dash_score: 'آخرین امتیاز واقعی سلامت دیجیتال تو، ۰ تا ۱۰۰، از مدل رگرسیون. فلش زیرش آن را با چک‌این قبلی خودت مقایسه می‌کند، نه با کس دیگری.',
      dash_week_avg: 'میانگین امتیاز چک‌این‌های این هفته‌ی تقویمی. روزهایی که از روندت بی‌صدا کرده‌ای اینجا شمرده نمی‌شوند.',
      dash_entries: 'تعداد کل چک‌این‌هایی که ثبت کرده‌ای. هرچه بیشتر باشد، هر روندی در این صفحه قابل‌اعتمادتر است.',
      dash_heatmap: 'دوشنبه تا یکشنبه‌ی هفته‌ی جاری. مربع پرشده یعنی روز ثبت‌شده، با رنگ متناسب امتیاز. روی هر مربع کلیک کن تا آن روز از میانگین‌هایت حذف شود — برای روزی که می‌دانی پرت بوده مفید است.',
      dash_recs: 'توصیه‌های آخرین چک‌این تو، انتخاب‌شده بر اساس عواملی که مدل تشخیص داده امتیازت را پایین می‌کشیدند.',
      dash_cohort: 'مقایسه‌ی میانگین‌های تو با جمعیت گسترده‌تر در داده‌ی آموزشی. زمینه است، نه مسابقه.',

      wizard_demographics: 'زمینه‌ی پایه درباره‌ی تو. مدل از این‌ها برای مقایسه‌ی همسان استفاده می‌کند — الگوی معمول یک دانشجو با یک بازنشسته یکی نیست.',
      wizard_time: 'این ورودی مربوط به کدام روز است. آخر هفته‌ها در داده واقعاً متفاوت رفتار می‌کنند، پس این مهم است.',
      wizard_screen: 'دقایق صفحه‌نمایشت به تفکیک دسته. مجموع را وارد نمی‌کنی — اپ خودش جمع می‌زند، پس اجزا هرگز نمی‌توانند با کل در تناقض باشند.',
      wizard_device: 'اینکه روزت چقدر تکه‌تکه بوده: اعلان‌ها، برداشتن گوشی، باز کردن اپ. در این داده، تعداد دفعات چک‌کردن اغلب بهتر از مجموع ساعت‌ها تمرکز را پیش‌بینی می‌کند.',
      wizard_sleep: 'ساعت‌هایی که واقعاً خوابیده‌ای و اینکه چقدر سرحالی. خواب یکی از قوی‌ترین سیگنال‌های کل مدل است.',
      wizard_mental: 'حال‌وهوا و استرس خوداظهاری. صادقانه پاسخ بده نه خوش‌بینانه — ورودی متورم امتیاز متورم می‌دهد که به درد هیچ‌کس نمی‌خورد.',
      wizard_focus: 'تمرکز، بهره‌وری، فعالیت و کافئین. چند مورد آخر، بعد نتیجه‌ات را می‌گیری.',
      wizard_derived: 'این‌ها از چیزی که بالا نوشتی محاسبه شده‌اند — نسبت‌ها، تراکم‌ها و شاخص‌هایی که مدل انتظار دارد. اینها را مستقیم وارد نمی‌کنی، پس نمی‌توانند با اعداد خامت مخالف باشند.',
      demo_profiles: 'عجله داری؟ یک پروفایل آماده را بارگذاری کن تا فوراً یک پیش‌بینی واقعی کامل ببینی. همان مدل روی همان مسیر اجرا می‌شود — فقط ورودی‌ها از پیش پر شده‌اند.',
      csv_import: 'از قبل جای دیگری ثبت می‌کنی؟ قالب را دانلود کن، چند روز را یکجا پر کن و آپلود کن. هر ردیف معتبر یک پیش‌بینی واقعی اجرا می‌کند و بلافاصله در تاریخچه‌ات می‌نشیند.',

      result_ring: 'امتیاز سلامت دیجیتال تو، ۰ تا ۱۰۰، از مدل رگرسیون. باند رنگی با همان آستانه‌هایی است که در کل اپ استفاده می‌شود.',
      result_confidence: 'اینکه طبقه‌بند چقدر به دسته‌ای که انتخاب کرده مطمئن است. ارزش دارد کنار امتیاز خوانده شود، نه به‌جای آن.',
      result_dimensions: 'یک تفکیک شفاف و قانون‌محور از همین ورودی‌ها بر اساس حوزه. این حساب ساده‌ای است که خودت هم می‌توانی انجام دهی — عمداً جدا از امتیاز خود مدل در بالا.',
      result_shap: 'عوامل مشخصی که امتیازت را جابه‌جا کردند، از SHAP. سبز بالا برده، قرمز پایین کشیده. این خود مدل است که توضیح می‌دهد، نه یک حدس.',
      result_recs: 'اقدام‌هایی متناسب با عواملی که به امتیازت آسیب زدند. هرکدام یک معیار موفقیت دارند تا بفهمی جواب داده یا نه.',
      result_ood: 'هشداری که بعضی از مقادیر امروز درست لبه‌ی چیزی هستند که مدل دیده. امتیاز همچنان واقعی است؛ فقط با احتیاط بیشتری با آن برخورد کن.',

      weekly_plan: 'یک برنامه‌ی هفت‌روزه که با قوانین از ضعیف‌ترین حوزه‌های واقعی تو ساخته شده. کارها را که انجام دادی تیک بزن — پیشرفت برای همیشه ذخیره می‌شود، نه فقط برای همین بازدید.',
      coach_chat: 'یک سؤال بنویس، یا /fit را بزن تا آخرین چک‌این‌ات به‌عنوان زمینه بارگذاری شود. مربی فقط چیزی را می‌داند که داده‌ی واقعی‌ات به او می‌گوید.',
      analytics_trend: 'امتیازت در طول زمان. سه چک‌این یا بیشتر جهت را معنادار می‌کند؛ کمتر از آن فقط چند نقطه روی نمودار است.',
      analytics_weekday: 'میانگین امتیاز به تفکیک روز هفته. روزی که فقط یک‌بار ثبت کرده‌ای به‌جای الگو، کم‌اعتماد علامت زده می‌شود.',
      whatif_sweep: 'یک فیلد انتخاب کن؛ این مدل واقعی را در کل بازه‌اش اجرا می‌کند تا دقیقاً ببینی امتیازت کجا تغییر جهت می‌دهد.',
      profile_avatar: 'تصویر تو فقط روی دستگاه خودت و در رکورد حسابت می‌ماند. قبل از ذخیره در مرورگرت کوچک می‌شود و هرگز به مدل نمی‌رسد.',
      profile_persona: 'یک کهن‌الگوی ساده که با قوانین مستند از عادت‌های واقعی تو استخراج شده — همیشه می‌توانی اعدادی که آن را ساخته‌اند ببینی. کنار پرسونای آماری ML نمایش داده می‌شود که چیز دیگری است.',
      profile_badges: 'صرفاً از مقادیر واقعی ثبت‌شده به دست می‌آیند. هر نشان آستانه‌ای که لازم داشته را نام می‌برد، پس هیچ‌کدام مرموز نیستند.',
      profile_tone: 'نحوه‌ی بیان توصیه‌ها را تغییر می‌دهد — ملایم‌تر، صریح‌تر یا بالینی. هرگز تغییر نمی‌دهد که چه توصیه‌هایی می‌گیری یا اولویتشان چیست.',
      privacy_controls: 'هرچه این اپ درباره‌ی تو ذخیره کرده را به‌صورت فایل خروجی بگیر، یا حساب و کل تاریخچه‌اش را برای همیشه حذف کن. حذف برگشت‌پذیر نیست.',
    },
  };

  /* Ordered section tours per page - used by startTour() and by the
     "explain this page" affordance. */
  const PAGE_TOURS = {
    dashboard: ['dashboard', 'dash_score', 'dash_week_avg', 'dash_entries', 'dash_heatmap', 'dash_recs', 'dash_cohort'],
    checkin: ['checkin', 'demo_profiles', 'csv_import', 'wizard_derived'],
    result: ['result_ring', 'result_confidence', 'result_dimensions', 'result_shap', 'result_recs'],
    weekly: ['weekly', 'weekly_plan'],
    coach: ['coach', 'coach_chat'],
    analytics: ['analytics', 'analytics_trend', 'analytics_weekday'],
    whatif: ['whatif', 'whatif_sweep'],
    model: ['model'],
    profile: ['profile', 'profile_avatar', 'profile_persona', 'profile_badges', 'profile_tone', 'privacy_controls'],
    about: ['about'],
    landing: ['landing'],
  };

  function copyFor(topicKey) {
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const pool = TIPS[lang] || TIPS.en;
    return pool[topicKey] || TIPS.en[topicKey] || null;
  }

  /** Speak about one topic. Auto-shown topics only fire once per
   *  browser; `force: true` (a click) always speaks. */
  function explain(topicKey, opts) {
    opts = opts || {};
    if (!topicKey || !window.DWMascot) return false;
    const text = copyFor(topicKey);
    if (!text) return false;

    const seenKey = SEEN_PREFIX + topicKey;
    if (!opts.force && localStorage.getItem(seenKey) === '1') return false;

    try { localStorage.setItem(seenKey, '1'); } catch (e) {}
    window.DWMascot.renderFace('neutral');
    window.DWMascot.say(text, { attention: !!opts.force, duration: opts.duration || 9500 });
    return true;
  }

  /** Make any element a help trigger for `topicKey`. Adds a keyboard
   *  path too, so the guide isn't mouse-only. */
  function attach(el, topicKey) {
    if (!el || !topicKey || el.__dwGuideBound) return;
    el.__dwGuideBound = true;
    el.classList.add('has-guide');
    if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '0');
    el.setAttribute('role', el.getAttribute('role') || 'button');

    const speak = (e) => { e.stopPropagation(); explain(topicKey, { force: true }); };
    el.addEventListener('click', speak);
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); speak(e); }
    });
  }

  /** Wire every element carrying data-guide="topic" in one pass. */
  function autoAttach(root) {
    (root || document).querySelectorAll('[data-guide]').forEach((el) => {
      attach(el, el.getAttribute('data-guide'));
    });
  }

  function topicsFor(pageKey) {
    return PAGE_TOURS[pageKey] || [];
  }

  /** Walk a page's sections in order, one bubble at a time. Runs once
   *  per page per browser unless forced. */
  function startTour(pageKey, opts) {
    opts = opts || {};
    const topics = topicsFor(pageKey);
    if (!topics.length) return false;

    const tourKey = TOUR_PREFIX + pageKey;
    if (!opts.force && localStorage.getItem(tourKey) === '1') return false;
    try { localStorage.setItem(tourKey, '1'); } catch (e) {}

    const step = opts.stepMs || 7000;
    topics.forEach((topic, i) => {
      setTimeout(() => explain(topic, { force: true, duration: step - 400 }), i * step);
    });
    return true;
  }

  window.DWGuide = { explain, attach, autoAttach, topicsFor, startTour, TIPS };
})();
