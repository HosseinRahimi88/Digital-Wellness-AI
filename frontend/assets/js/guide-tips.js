/*
  Digital Guide content — the mascot's contextual explanation layer.

  Previously the mascot only reacted emotionally to events (score
  bands, saves, errors); it never actually explained anything, which
  is what a "guide" character is supposed to do. This module adds one
  short, honest explanation per page: what this screen shows, what its
  key numbers mean, and what to do next. It never invents a claim about
  the user's own data - the text is generic guidance about the page
  itself, not a fabricated interpretation of their specific numbers
  (that's what the real prediction/recommendation text already does).

  Shown once automatically per page per browser (localStorage-tracked),
  and re-triggerable any time by clicking the mascot - shell.js wires
  that click override in on every page that calls DWShell.init().
*/
(function () {
  const SEEN_PREFIX = 'dwai_guide_seen_';

  const TIPS = {
    en: {
      dashboard: "This is your home base. The ring is your most recent real score, the heatmap shows this week's check-ins, and below that are the exact factors — pulled from SHAP — that pushed your score up or down. If it says \"No check-ins yet\", start one from here.",
      checkin: "This form is the only place your data comes from — nothing here is pre-filled with a fake average. Fill in what's true for today (or try a demo profile to see how it works), then submit to get a real prediction: a risk class, a 0–100 score, and the exact reasons why, not a guess.",
      weekly: "This week vs. last week, side by side, plus a 7-day plan built from your last real check-in's weakest signals — not a generic template. Tick tasks off as you do them; that's saved for good, not just for this session.",
      coach: "Ask about your score, a specific area like sleep or focus, or what to prioritize first. The Coach only knows what your last real check-in told it — it will say so plainly if it doesn't have enough data for a question, instead of guessing.",
      analytics: "Your score trend over time and which days of the week tend to be better or worse for you, computed from your own logged history. The more check-ins you run, the more this chart actually means.",
      whatif: "A sandbox: change one habit and see how the real model's prediction moves, without touching your saved history. Useful for testing \"what if I slept an hour more\" before actually committing to it.",
      model: "These are the model's real, current accuracy numbers — not marketing claims. A classification task run on new, never-before-seen data is genuinely harder than it sounds, which is why these numbers aren't 99%.",
      profile: "Your account preferences — what you're aiming for, why you use your devices, your general schedule. These personalize tone and defaults; they never change what the model itself sees as input.",
      about: "Background on how this project works, what data it uses, and its limits — worth a read if you want to know what's really happening behind the score.",
    },
    fa: {
      dashboard: "این‌جا نقطه‌ی شروع توئه. حلقه، آخرین امتیاز واقعی‌ته، نقشه‌ی حرارتی چک-این‌های این هفته رو نشون می‌ده، و پایین‌تر دقیقاً همون عواملی‌ان — از SHAP — که امتیازت رو بالا یا پایین بردن. اگه نوشته «هنوز چک-اینی نیست»، از همین‌جا شروع کن.",
      checkin: "این فرم تنها منبع داده‌ی توئه — هیچ‌چیزش از قبل با یه میانگین ساختگی پر نشده. چیزی که امروز واقعاً درسته رو وارد کن (یا یه پروفایل دمو رو امتحان کن تا ببینی چطور کار می‌کنه)، بعد بفرست تا یه پیش‌بینی واقعی بگیری: یه دسته‌ی ریسک، یه امتیاز ۰ تا ۱۰۰، و دلیل دقیقش — نه یه حدس.",
      weekly: "این هفته در برابر هفته‌ی قبل، کنار هم، به‌همراه یه برنامه‌ی ۷ روزه که از ضعیف‌ترین سیگنال‌های آخرین چک-این واقعی‌ات ساخته شده — نه یه قالب عمومی. کارها رو که انجام دادی تیک بزن؛ برای همیشه ذخیره می‌شه، نه فقط برای همین جلسه.",
      coach: "درباره‌ی امتیازت، یه حوزه‌ی خاص مثل خواب یا تمرکز، یا اینکه اول چه چیزی رو در اولویت بذاری بپرس. مربی فقط چیزی رو می‌دونه که آخرین چک-این واقعی‌ات بهش گفته — اگه برای یه سوال داده‌ی کافی نداشته باشه، صریح می‌گه، نه اینکه حدس بزنه.",
      analytics: "روند امتیازت در طول زمان و اینکه کدوم روزهای هفته معمولاً برات بهتر یا بدتره، از تاریخچه‌ی واقعی خودت محاسبه شده. هرچقدر بیشتر چک-این کنی، این نمودار معنای بیشتری پیدا می‌کنه.",
      whatif: "یه محیط آزمایشی: یه عادت رو تغییر بده و ببین پیش‌بینی مدل واقعی چطور جابه‌جا می‌شه، بدون اینکه به تاریخچه‌ی ذخیره‌شده‌ات دست بخوره. برای تست «اگه یه ساعت بیشتر می‌خوابیدم» قبل از واقعاً امتحان‌کردنش مفیده.",
      model: "این‌ها اعداد واقعی و فعلی دقت مدل هستن — نه ادعای تبلیغاتی. یه تسک طبقه‌بندی که روی داده‌ی جدید و ندیده اجرا می‌شه واقعاً سخت‌تر از چیزیه که به‌نظر می‌رسه، برای همینه که این اعداد ۹۹٪ نیستن.",
      profile: "ترجیحات حساب کاربری‌ات — هدفت، دلیل استفاده‌ات، برنامه‌ی کلی‌ات. این‌ها لحن و پیش‌فرض‌ها رو شخصی‌سازی می‌کنن؛ هیچ‌وقت چیزی که مدل به‌عنوان ورودی می‌بینه رو تغییر نمی‌دن.",
      about: "پس‌زمینه‌ی اینکه این پروژه چطور کار می‌کنه، از چه داده‌ای استفاده می‌کنه، و محدودیت‌هاش چیه — اگه می‌خوای بدونی واقعاً پشت امتیاز چه خبره، ارزش خوندن داره.",
    },
  };

  function copyFor(pageKey) {
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const pool = TIPS[lang] || TIPS.en;
    return pool[pageKey] || TIPS.en[pageKey] || null;
  }

  function explain(pageKey, opts) {
    opts = opts || {};
    if (!pageKey || !window.DWMascot) return;
    const text = copyFor(pageKey);
    if (!text) return;

    const seenKey = SEEN_PREFIX + pageKey;
    const alreadySeen = localStorage.getItem(seenKey) === '1';
    if (alreadySeen && !opts.force) return;

    localStorage.setItem(seenKey, '1');
    window.DWMascot.renderFace('neutral');
    window.DWMascot.say(text, { attention: true, duration: 9000 });
  }

  window.DWGuide = { explain };
})();
