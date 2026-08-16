/*
  DWAboutPersonal — the dossier: what this app knows about YOU, and how
  it knows it.

  Four things, each from a different source and each allowed to say it
  has nothing:

    1. TIME IN THE APP. Measured, not estimated: the seconds this page
       is actually visible and focused are counted here and sent to
       /personal/heartbeat once a minute. The server caps a beat at five
       minutes and a day at sixteen hours, so a tab left open over a
       weekend cannot post two days of "use".
    2. WHERE YOU SIT. Your own average score against the distribution
       the shipped models were fitted to. The panel names its source -
       the whole training CSV, or the 14KB reference shipped in
       artifacts/ - because those are not the same claim, and it says
       out loud that the cohort is synthetic.
    3. YOUR OWN MODEL. A ridge fit on YOUR days only
       (services/insight/personal_model_service.py), reported with both an
       in-sample R² and a leave-one-out R². The leave-one-out number is
       the one the panel leads with, because the other one is
       optimistic by construction on a handful of days.
    4. WHAT YOUR DAYS ADD UP TO. Facts with the arithmetic behind them,
       plus day-of-life facts if - and only if - a birth date has been
       given. The date is optional, forgettable, and never fed to any
       model.

  Every sentence here is composed in the browser from numbers the
  server measured. The server sends arithmetic; this file owns the
  four languages, the same way the rest of the About page does.
*/
(function () {
  const LANGS = ['en', 'fa', 'ar', 'zh'];
  const LOCALE = { en: 'en-US', fa: 'fa-IR', ar: 'ar-SA', zh: 'zh-CN' };

  function lang() {
    const l = window.DWI18n && window.DWI18n.get ? window.DWI18n.get() : 'en';
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }

  function pick(bundle) {
    if (!bundle) return '';
    if (typeof bundle === 'string') return bundle;
    return bundle[lang()] || bundle.en || '';
  }

  function esc(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* Numbers are shown in the reader's own digits, which is most of what
     makes a Persian or Arabic page read as written rather than
     translated. */
  function num(value, decimals) {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    try {
      return Number(value).toLocaleString(LOCALE[lang()] || 'en-US', {
        minimumFractionDigits: decimals || 0, maximumFractionDigits: decimals || 0,
      });
    } catch (e) { return String(value); }
  }

  function longDate(iso) {
    if (!iso) return '';
    try {
      return new Date(`${iso}T00:00:00`).toLocaleDateString(LOCALE[lang()] || 'en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
      });
    } catch (e) { return iso; }
  }

  const T = {
    eyebrow: {
      en: 'Read from your own days', fa: 'خوانده‌شده از روزهای خودت',
      ar: 'مقروء من أيامك أنت', zh: '读自你自己的日子',
    },
    title: {
      en: 'What this app knows about you', fa: 'این اپ چه چیزی درباره‌ی تو می‌داند',
      ar: 'ما يعرفه هذا التطبيق عنك', zh: '这个应用了解你什么',
    },
    lede: {
      en: 'Four readings, each from a different source, and each allowed to say it has nothing yet. Every number below was measured — none of it is a guess about you.',
      fa: 'چهار خوانش، هرکدام از منبعی متفاوت، و هرکدام مجاز به گفتنِ «هنوز چیزی ندارم». هر عددی که پایین می‌بینی اندازه‌گیری شده — هیچ‌کدام حدس درباره‌ی تو نیست.',
      ar: 'أربع قراءات، كلٌّ من مصدر مختلف، ولكلٍّ أن تقول «لا شيء لديّ بعد». كل رقم في الأسفل مُقاس — لا شيء منه تخمين عنك.',
      zh: '四项读数，各来自不同来源，且每一项都可以说「我还没有数据」。下面每个数字都是实测——没有一个是对你的猜测。',
    },

    usage_title: { en: 'Time in this app', fa: 'زمان در این اپ', ar: 'الوقت داخل التطبيق', zh: '在这个应用里的时间' },
    usage_today: { en: 'today', fa: 'امروز', ar: 'اليوم', zh: '今天' },
    usage_total: { en: 'in total', fa: 'در مجموع', ar: 'الإجمالي', zh: '总计' },
    usage_days: { en: 'days you opened it', fa: 'روزی که بازش کردی', ar: 'يومًا فتحته فيها', zh: '天打开过它' },
    usage_best: { en: 'longest day', fa: 'طولانی‌ترین روز', ar: 'أطول يوم', zh: '最长的一天' },
    minutes: { en: 'min', fa: 'دقیقه', ar: 'دقيقة', zh: '分钟' },
    usage_note: {
      en: 'Counted only while a page of this app is actually visible and focused. A tab left open in the background adds nothing.',
      fa: 'فقط وقتی شمرده می‌شود که صفحه‌ای از این اپ واقعاً دیده می‌شود و فوکوس دارد. تبی که در پس‌زمینه باز مانده چیزی اضافه نمی‌کند.',
      ar: 'يُحتسب فقط أثناء ظهور صفحة من هذا التطبيق فعليًا وتركيزها. التبويب المتروك في الخلفية لا يضيف شيئًا.',
      zh: '只有当本应用的页面真正可见且处于焦点时才计时。留在后台的标签页不会增加任何时间。',
    },
    usage_empty: {
      en: 'Nothing counted yet — this minute is the first one.',
      fa: 'هنوز چیزی شمرده نشده — همین دقیقه اولی است.',
      ar: 'لم يُحتسب شيء بعد — هذه الدقيقة هي الأولى.',
      zh: '还没有计时——这一分钟就是第一分钟。',
    },

    cohort_title: { en: 'Where you sit', fa: 'کجای توزیع ایستاده‌ای', ar: 'أين تقف', zh: '你处在什么位置' },
    cohort_pct: {
      en: 'of the cohort scores at or below your average',
      fa: 'از جمعیت مرجع، امتیازی برابر یا کمتر از میانگین تو دارند',
      ar: 'من المجموعة المرجعية درجاتهم مساوية لمتوسطك أو أقل منه',
      zh: '的参照人群，分数等于或低于你的平均分',
    },
    cohort_mean: { en: 'cohort average', fa: 'میانگین جمعیت مرجع', ar: 'متوسط المجموعة', zh: '参照人群平均分' },
    cohort_direction: {
      en: 'Each bar is where your own average sits in the cohort. On the signals where less is better — screen time, notifications, stress — a longer bar is the worse position, and it is coloured that way.',
      fa: 'هر میله نشان می‌دهد میانگین خودت کجای جمعیت مرجع می‌ایستد. در سیگنال‌هایی که کمتر بهتر است — زمان صفحه، اعلان‌ها، استرس — میله‌ی بلندتر یعنی وضع بدتر، و رنگش هم همین را می‌گوید.',
      ar: 'كل شريط يوضّح أين يقع متوسطك داخل المجموعة. في الإشارات التي يكون الأقل فيها أفضل — وقت الشاشة والإشعارات والتوتر — الشريط الأطول هو الموضع الأسوأ، ولونه يقول ذلك.',
      zh: '每一条都表示你的平均值在参照人群中的位置。在「越少越好」的信号上——屏幕时间、通知、压力——条越长代表位置越差，颜色也据此标示。',
    },
    cohort_you: { en: 'your average', fa: 'میانگین تو', ar: 'متوسطك', zh: '你的平均分' },
    cohort_source_dataset: {
      en: 'Read from the full training set ({n} rows).',
      fa: 'خوانده‌شده از کل مجموعه‌ی آموزشی ({n} سطر).',
      ar: 'مقروء من مجموعة التدريب الكاملة ({n} صفًا).',
      zh: '读自完整训练集（{n} 行）。',
    },
    cohort_source_reference: {
      en: 'Read from the precomputed distribution shipped with the app ({n} rows behind it) — the training CSV itself is not distributed.',
      fa: 'خوانده‌شده از توزیع از پیش محاسبه‌شده‌ای که همراه اپ ارسال می‌شود (پشتش {n} سطر) — خودِ فایل CSV آموزشی ارسال نمی‌شود.',
      ar: 'مقروء من التوزيع المحسوب مسبقًا المرفق مع التطبيق (خلفه {n} صفًا) — ملف التدريب نفسه غير مرفق.',
      zh: '读自随应用一起分发的预计算分布（背后有 {n} 行）——训练用的 CSV 本身并不分发。',
    },
    cohort_synthetic: {
      en: 'That cohort is synthetic training data, not a measurement of any human population. It says where you sit relative to what the model learned — nothing more.',
      fa: 'آن جمعیت، داده‌ی آموزشیِ مصنوعی است، نه اندازه‌گیری هیچ جمعیت انسانی. فقط می‌گوید نسبت به چیزی که مدل یاد گرفته کجا ایستاده‌ای — نه بیشتر.',
      ar: 'تلك المجموعة بيانات تدريب اصطناعية، وليست قياسًا لأي مجتمع بشري. تقول أين تقف بالنسبة لما تعلّمه النموذج — لا أكثر.',
      zh: '那个人群是合成的训练数据，不是对任何真实人群的测量。它只说明你相对于模型所学内容的位置——仅此而已。',
    },
    cohort_unavailable: {
      en: 'No cohort distribution is available in this copy, so there is nothing honest to compare you against.',
      fa: 'در این نسخه توزیع جمعیت مرجع در دسترس نیست، پس چیزی برای مقایسه‌ی صادقانه وجود ندارد.',
      ar: 'لا يتوفر توزيع مرجعي في هذه النسخة، لذا لا يوجد ما يمكن مقارنتك به بصدق.',
      zh: '这个副本里没有参照分布，因此没有可以诚实比较的对象。',
    },
    cohort_no_days: {
      en: 'Log a day and this fills in.',
      fa: 'یک روز ثبت کن تا این پر شود.',
      ar: 'سجّل يومًا وسيمتلئ هذا.',
      zh: '记录一天，这里就会有内容。',
    },

    model_title: { en: 'A model of you alone', fa: 'مدلی فقط از خودِ تو', ar: 'نموذج لك وحدك', zh: '只属于你的模型' },
    model_lede: {
      en: 'Ridge regression fitted on your days only — not the shipped model. It answers a different question: which of your own signals actually move your score.',
      fa: 'رگرسیون ریج که فقط روی روزهای خودت برازش شده — نه مدلِ ارسالی. به پرسش دیگری پاسخ می‌دهد: کدام سیگنالِ خودت واقعاً امتیازت را جابه‌جا می‌کند.',
      ar: 'انحدار ريدج مُلائم على أيامك أنت فقط — لا النموذج المشحون. يجيب عن سؤال آخر: أي إشاراتك تحرّك درجتك فعلًا.',
      zh: '仅在你自己的日子上拟合的岭回归——不是随应用发布的那个模型。它回答另一个问题：你自己的哪些信号真正推动了你的分数。',
    },
    model_r2_loo: { en: 'leave-one-out R²', fa: 'R² با حذف یکی', ar: 'R² بحذف واحد', zh: '留一法 R²' },
    model_r2: { en: 'in-sample R²', fa: 'R² روی همان داده', ar: 'R² داخل العينة', zh: '样本内 R²' },
    model_days: { en: 'days fitted', fa: 'روزِ برازش‌شده', ar: 'يومًا مُلائمًا', zh: '天用于拟合' },
    model_drivers: { en: 'What moves your score', fa: 'چه چیزی امتیازت را جابه‌جا می‌کند', ar: 'ما يحرّك درجتك', zh: '什么在推动你的分数' },
    model_per_sd: {
      en: 'points per standard deviation of this signal',
      fa: 'امتیاز به ازای هر انحراف معیارِ این سیگنال',
      ar: 'نقطة لكل انحراف معياري لهذه الإشارة',
      zh: '分／该信号每变动一个标准差',
    },
    model_up: { en: 'raises', fa: 'بالا می‌برد', ar: 'يرفع', zh: '提升' },
    model_down: { en: 'lowers', fa: 'پایین می‌آورد', ar: 'يخفض', zh: '拉低' },
    model_untrustworthy: {
      en: 'Read this as a first sketch: on your days so far the fit does not yet predict a day it has not seen. The ordering is a hint, not a finding.',
      fa: 'این را یک طرحِ اولیه بخوان: با روزهایی که تا حالا داری، برازش هنوز نمی‌تواند روزی را که ندیده پیش‌بینی کند. ترتیبش یک سرنخ است، نه یک یافته.',
      ar: 'اقرأ هذا كمسودة أولى: بأيامك حتى الآن لا يستطيع النموذج التنبؤ بيوم لم يره. الترتيب مؤشر لا نتيجة.',
      zh: '把这当作初稿：以你目前的天数，这个拟合还无法预测它没见过的一天。这个排序是线索，不是结论。',
    },
    model_reason_not_enough_days: {
      en: 'Not enough days yet. A model of one person needs at least {min} of that person’s days; you have {n}.',
      fa: 'هنوز روزها کافی نیست. مدلِ یک نفر دست‌کم به {min} روز از روزهای خودش نیاز دارد؛ تو {n} روز داری.',
      ar: 'الأيام غير كافية بعد. نموذج شخص واحد يحتاج {min} يومًا على الأقل من أيامه؛ لديك {n}.',
      zh: '天数还不够。只属于一个人的模型至少需要这个人的 {min} 天；你有 {n} 天。',
    },
    model_reason_score_never_moves: {
      en: 'Your score has not moved at all, so there is nothing for a model to explain.',
      fa: 'امتیازت اصلاً جابه‌جا نشده، پس چیزی برای توضیح‌دادن وجود ندارد.',
      ar: 'لم تتحرك درجتك إطلاقًا، فلا شيء ليفسّره النموذج.',
      zh: '你的分数完全没有变化，因此没有什么需要模型解释。',
    },
    model_reason_signals_never_move: {
      en: 'Your signals have not varied enough to fit anything on.',
      fa: 'سیگنال‌هایت آن‌قدر تغییر نکرده‌اند که بشود چیزی رویشان برازش کرد.',
      ar: 'لم تتغيّر إشاراتك بما يكفي لملاءمة أي شيء عليها.',
      zh: '你的信号变化不足，无法在其上拟合任何东西。',
    },
    model_reason_no_clear_driver: {
      en: 'Nothing in your days stands out far enough from the noise to name.',
      fa: 'هیچ‌چیز در روزهایت آن‌قدر از نویز بیرون نزده که بشود اسمش را برد.',
      ar: 'لا شيء في أيامك يبرز فوق الضجيج بما يكفي لتسميته.',
      zh: '你的日子里没有任何东西从噪声中凸显到可以点名的程度。',
    },
    model_reason_fit_failed: {
      en: 'The fit did not converge on your days.',
      fa: 'برازش روی روزهای تو همگرا نشد.',
      ar: 'لم يتقارب الملاءمة على أيامك.',
      zh: '在你的日子上拟合没有收敛。',
    },

    facts_title: { en: 'What your days add up to', fa: 'روزهایت روی هم چه می‌شوند', ar: 'ما تُشكّله أيامك مجتمعة', zh: '你的日子加起来是什么' },
    facts_empty: {
      en: 'Nothing yet — the first logged day starts this.',
      fa: 'هنوز چیزی نیست — اولین روزِ ثبت‌شده این را شروع می‌کند.',
      ar: 'لا شيء بعد — أول يوم مُسجَّل يبدأ هذا.',
      zh: '还没有——第一个记录的日子会开启这里。',
    },

    birth_title: { en: 'Your birth date', fa: 'تاریخ تولدت', ar: 'تاريخ ميلادك', zh: '你的出生日期' },
    birth_why: {
      en: 'Optional, and forgettable. Given one, this panel can say how many days you have been alive next to how many you have logged here. It is never fed to any model.',
      fa: 'اختیاری است و هر وقت بخواهی پاک می‌شود. اگر بدهی‌اش، این بخش می‌تواند بگوید چند روز زنده بوده‌ای و چند روزش را اینجا ثبت کرده‌ای. هرگز خوراک هیچ مدلی نمی‌شود.',
      ar: 'اختياري ويمكن نسيانه. إن أعطيته، تستطيع هذه اللوحة أن تقول كم يومًا عشت مقابل كم يومًا سجّلت هنا. ولا يُغذّى لأي نموذج أبدًا.',
      zh: '可选，也可以随时删除。给了它，这一栏就能说出你活了多少天，以及你在这里记录了多少天。它绝不会被喂给任何模型。',
    },
    birth_save: { en: 'Save', fa: 'ذخیره', ar: 'حفظ', zh: '保存' },
    birth_clear: { en: 'Forget it', fa: 'فراموشش کن', ar: 'انسَ ذلك', zh: '忘掉它' },
    birth_saved: { en: 'Saved.', fa: 'ذخیره شد.', ar: 'تم الحفظ.', zh: '已保存。' },
    birth_cleared: { en: 'Forgotten.', fa: 'پاک شد.', ar: 'تم النسيان.', zh: '已删除。' },
    load_failed: {
      en: 'This panel could not be read — the API did not answer.',
      fa: 'این بخش خوانده نشد — سرور پاسخ نداد.',
      ar: 'تعذّرت قراءة هذه اللوحة — لم تستجب الواجهة البرمجية.',
      zh: '这一栏没能读取——接口没有响应。',
    },
  };

  /* One sentence per fact kind, composed from the numbers the server
     measured. {placeholders} are filled with the reader's own digits. */
  const FACTS = {
    first_day: {
      en: 'You started on {date}, {days_since} days ago, and have logged {logged} days since.',
      fa: 'از {date} شروع کردی، {days_since} روز پیش، و از آن زمان {logged} روز ثبت کرده‌ای.',
      ar: 'بدأت في {date}، قبل {days_since} يومًا، وسجّلت منذ ذلك الحين {logged} يومًا.',
      zh: '你从 {date} 开始，那是 {days_since} 天前，此后共记录了 {logged} 天。',
    },
    personal_best: {
      en: 'Your best day is {score}, on {date}.',
      fa: 'بهترین روزت {score} است، در {date}.',
      ar: 'أفضل أيامك هو {score}، في {date}.',
      zh: '你最好的一天是 {score} 分，在 {date}。',
    },
    longest_streak: {
      en: 'Your longest unbroken run is {days} days.',
      fa: 'طولانی‌ترین زنجیره‌ی بی‌وقفه‌ات {days} روز است.',
      ar: 'أطول سلسلة متصلة لديك {days} يومًا.',
      zh: '你最长的连续记录是 {days} 天。',
    },
    best_weekday: {
      en: 'Your {weekday}s average {average} — your best weekday, over {samples} of them.',
      fa: '{weekday}‌های تو به‌طور میانگین {average} است — بهترین روز هفته‌ات، از روی {samples} مورد.',
      ar: 'أيام {weekday} لديك بمتوسط {average} — أفضل أيام أسبوعك، من {samples} منها.',
      zh: '你的{weekday}平均 {average} 分——是你一周中最好的一天，基于 {samples} 次。',
    },
    hardest_weekday: {
      en: 'Your {weekday}s average {average}, {gap} points below your best weekday.',
      fa: '{weekday}‌های تو به‌طور میانگین {average} است، یعنی {gap} امتیاز پایین‌تر از بهترین روز هفته‌ات.',
      ar: 'أيام {weekday} لديك بمتوسط {average}، أي أقل بـ {gap} نقطة من أفضل أيامك.',
      zh: '你的{weekday}平均 {average} 分，比你最好的那天低 {gap} 分。',
    },
    biggest_climb: {
      en: 'Your biggest single-day climb is {points} points, on {date}.',
      fa: 'بزرگ‌ترین جهش یک‌روزه‌ات {points} امتیاز است، در {date}.',
      ar: 'أكبر قفزة في يوم واحد لديك {points} نقطة، في {date}.',
      zh: '你单日最大的上升是 {points} 分，发生在 {date}。',
    },
    trend_half: {
      en: 'Your first half averaged {early}; your latest half averages {late} — a change of {change}.',
      fa: 'نیمه‌ی اولت به‌طور میانگین {early} بود؛ نیمه‌ی آخرت {late} است — تغییری برابر {change}.',
      ar: 'متوسط نصفك الأول {early}؛ ومتوسط نصفك الأخير {late} — بتغيّر قدره {change}.',
      zh: '你前半段平均 {early} 分，后半段平均 {late} 分——变化 {change} 分。',
    },
    steadiness: {
      en: 'Your scores swing by {sd} on average, across a range of {range} points.',
      fa: 'امتیازهایت به‌طور میانگین {sd} نوسان دارند، در بازه‌ای به پهنای {range} امتیاز.',
      ar: 'تتأرجح درجاتك بمقدار {sd} في المتوسط، ضمن مدى {range} نقطة.',
      zh: '你的分数平均波动 {sd} 分，整体跨度 {range} 分。',
    },
    screen_total: {
      en: 'Across {days} logged days you have recorded {hours} hours of screen time — {daily_average_minutes} minutes a day.',
      fa: 'در {days} روزِ ثبت‌شده، {hours} ساعت زمان صفحه ثبت کرده‌ای — روزی {daily_average_minutes} دقیقه.',
      ar: 'عبر {days} يومًا مُسجَّلًا سجّلت {hours} ساعة أمام الشاشة — {daily_average_minutes} دقيقة يوميًا.',
      zh: '在记录的 {days} 天里，你共记录了 {hours} 小时屏幕时间——平均每天 {daily_average_minutes} 分钟。',
    },
    sleep_average: {
      en: 'You sleep {hours} hours on an average night; your best was {best}, your worst {worst}.',
      fa: 'به‌طور میانگین شبی {hours} ساعت می‌خوابی؛ بهترینت {best} بود و بدترینت {worst}.',
      ar: 'تنام {hours} ساعة في الليلة المتوسطة؛ أفضلها {best} وأسوؤها {worst}.',
      zh: '你平均每晚睡 {hours} 小时；最好的一晚 {best} 小时，最差的 {worst} 小时。',
    },
    days_alive: {
      en: 'You have been alive {days} days — {weeks} weeks — and you were born on a {born_weekday}. You have logged {logged} of those days here.',
      fa: '{days} روز زنده بوده‌ای — {weeks} هفته — و روز تولدت {born_weekday} بوده. از آن روزها {logged} روز را اینجا ثبت کرده‌ای.',
      ar: 'عشت {days} يومًا — {weeks} أسبوعًا — ووُلدت يوم {born_weekday}. سجّلت هنا {logged} من تلك الأيام.',
      zh: '你已经活了 {days} 天——{weeks} 周——出生在{born_weekday}。其中 {logged} 天你在这里记录了。',
    },
    next_birthday: {
      en: 'Your next birthday is {days} days away, on a {weekday}, and you will turn {turning}.',
      fa: 'تولد بعدی‌ات {days} روز دیگر است، روز {weekday}، و {turning} ساله می‌شوی.',
      ar: 'عيد ميلادك القادم بعد {days} يومًا، يوم {weekday}، وستُتم {turning} عامًا.',
      zh: '你的下一个生日还有 {days} 天，是{weekday}，你将满 {turning} 岁。',
    },
    birthday_logged: {
      en: 'You logged your birthday, {date}, and scored {score} — against an average of {average}.',
      fa: 'روز تولدت، {date}، را ثبت کردی و {score} گرفتی — در برابر میانگین {average}.',
      ar: 'سجّلت يوم ميلادك، {date}، وحصلت على {score} — مقابل متوسط {average}.',
      zh: '你记录了自己的生日 {date}，得分 {score}——而你的平均分是 {average}。',
    },
  };

  /* Which of the compared signals are better LOW. A percentile bar is
     a position, not a verdict, and 100th percentile on screen time is
     the opposite of 100th percentile on focus - colouring both the
     same way would be the panel's one dishonest pixel. */
  const LOWER_IS_BETTER = new Set([
    'total_screen_min', 'social_min', 'gaming_min', 'video_min',
    'night_screen_min', 'pre_sleep_screen_min', 'notifications_per_day',
    'pickups_per_day', 'app_opens_per_day', 'stress_0_10',
  ]);

  const WEEKDAYS = {
    monday: { en: 'Monday', fa: 'دوشنبه', ar: 'الإثنين', zh: '周一' },
    tuesday: { en: 'Tuesday', fa: 'سه‌شنبه', ar: 'الثلاثاء', zh: '周二' },
    wednesday: { en: 'Wednesday', fa: 'چهارشنبه', ar: 'الأربعاء', zh: '周三' },
    thursday: { en: 'Thursday', fa: 'پنجشنبه', ar: 'الخميس', zh: '周四' },
    friday: { en: 'Friday', fa: 'جمعه', ar: 'الجمعة', zh: '周五' },
    saturday: { en: 'Saturday', fa: 'شنبه', ar: 'السبت', zh: '周六' },
    sunday: { en: 'Sunday', fa: 'یکشنبه', ar: 'الأحد', zh: '周日' },
  };

  /* Field labels. The coach already owns a translated field table; this
     uses it when it is loaded and falls back to the raw name, which is
     at least true, rather than to a prettier guess. */
  function fieldLabel(name) {
    // DWCoachLabels is a Proxy keyed by field name that already returns
    // the string in the current language - see coach-labels.js. Reading
    // a missing field gives undefined rather than throwing, so the
    // fallback below is the only guard needed.
    try {
      const label = window.DWCoachLabels && window.DWCoachLabels[name];
      if (label) return label;
    } catch (e) { /* fall through */ }
    return name.replace(/_/g, ' ');
  }

  function fill(template, values) {
    return String(template).replace(/\{(\w+)\}/g, (match, key) => {
      const value = values[key];
      if (value === undefined || value === null) return match;
      if (key === 'weekday' || key === 'born_weekday') return pick(WEEKDAYS[value]) || value;
      if (key === 'date') return longDate(value);
      if (typeof value === 'number') {
        const decimals = Number.isInteger(value) ? 0 : 1;
        return num(value, decimals);
      }
      return String(value);
    });
  }

  function factLine(fact) {
    const template = FACTS[fact.kind];
    if (!template) return '';
    return fill(pick(template), fact);
  }

  function init(rootId) {
    const root = document.getElementById(rootId);
    if (!root) return;

    let data = null;
    let failed = false;
    let busy = false;

    /* ---- the heartbeat ------------------------------------------- */

    // Seconds are accumulated locally and posted once a minute. The
    // page only counts time it can prove: visible, and this window
    // focused. Everything else is somebody else's minute.
    let owed = 0;
    let lastTick = Date.now();

    function visible() {
      return document.visibilityState === 'visible' && document.hasFocus();
    }

    function tick() {
      const now = Date.now();
      const elapsed = Math.round((now - lastTick) / 1000);
      lastTick = now;
      // A gap larger than a minute means the machine slept or the tab
      // was frozen; that is not time spent here.
      if (visible() && elapsed > 0 && elapsed <= 60) owed += elapsed;
    }

    async function flush() {
      if (!owed) return;
      const seconds = Math.min(300, owed);
      owed = 0;
      try {
        const usage = await window.DWApi.personalHeartbeat(seconds);
        if (data && usage) {
          data.usage = usage;
          const el = root.querySelector('[data-usage-today]');
          if (el) el.textContent = num(usage.today_minutes, 0);
          const total = root.querySelector('[data-usage-total]');
          if (total) total.textContent = num(usage.total_minutes, 0);
        }
      } catch (e) { /* a lost heartbeat is not worth a message */ }
    }

    setInterval(tick, 5000);
    setInterval(flush, 60000);
    // Post what is owed before the page goes away, so the last minute
    // of a visit is not always lost.
    document.addEventListener('visibilitychange', () => { tick(); if (!visible()) flush(); });
    window.addEventListener('pagehide', () => { tick(); flush(); });

    /* ---- rendering ------------------------------------------------ */

    function statHtml(value, unit, label, attr) {
      return ''
        + '<div class="pi-stat">'
        + `<span class="pi-stat-value"${attr ? ` ${attr}` : ''}>${esc(value)}</span>`
        + (unit ? `<span class="pi-stat-unit">${esc(unit)}</span>` : '')
        + `<span class="pi-stat-label">${esc(label)}</span>`
        + '</div>';
    }

    function usageCard() {
      const usage = (data && data.usage) || {};
      const empty = !usage.total_seconds;
      return ''
        + '<article class="pi-card pi-card--usage">'
        + `<h3 class="pi-card-title">${esc(pick(T.usage_title))}</h3>`
        + '<div class="pi-stats">'
        + statHtml(num(usage.today_minutes || 0, 0), pick(T.minutes), pick(T.usage_today), 'data-usage-today')
        + statHtml(num(usage.total_minutes || 0, 0), pick(T.minutes), pick(T.usage_total), 'data-usage-total')
        + statHtml(num(usage.days_present || 0, 0), '', pick(T.usage_days))
        + statHtml(num(usage.best_day_minutes || 0, 0), pick(T.minutes), pick(T.usage_best))
        + '</div>'
        + `<p class="pi-note">${esc(empty ? pick(T.usage_empty) : pick(T.usage_note))}</p>`
        + '</article>';
    }

    function cohortCard() {
      const cohort = (data && data.cohort) || {};
      let body;
      if (!cohort.available) {
        body = `<p class="pi-note">${esc(pick(T.cohort_unavailable))}</p>`;
      } else if (cohort.score_percentile === null || cohort.score_percentile === undefined) {
        body = `<p class="pi-note">${esc(pick(T.cohort_no_days))}</p>`;
      } else {
        const pct = Math.max(0, Math.min(100, cohort.score_percentile));
        const sourceLine = fill(
          pick(cohort.source === 'dataset' ? T.cohort_source_dataset : T.cohort_source_reference),
          { n: num(cohort.size, 0) },
        );
        body = ''
          + '<div class="pi-percentile">'
          + `<div class="pi-percentile-bar"><span style="inline-size:${pct}%"></span>`
          + `<i class="pi-percentile-you" style="inset-inline-start:${pct}%"></i></div>`
          + '<div class="pi-percentile-row">'
          + `<span class="pi-percentile-value">${esc(num(pct, 1))}%</span>`
          + `<span class="pi-note">${esc(pick(T.cohort_pct))}</span>`
          + '</div></div>'
          + '<div class="pi-stats">'
          + statHtml(num(cohort.score_value, 1), '', pick(T.cohort_you))
          + statHtml(num(cohort.cohort_score_mean, 1), '', pick(T.cohort_mean))
          + '</div>'
          + (cohort.fields || []).map((f) => {
            const high = Math.max(0, Math.min(100, f.percentile));
            // "Good" is high on most signals and low on the ones above.
            const good = LOWER_IS_BETTER.has(f.field) ? high < 50 : high >= 50;
            return ''
              + `<div class="pi-field-row pi-field-row--${good ? 'good' : 'watch'}">`
              + `<span class="pi-field-name">${esc(fieldLabel(f.field))}</span>`
              + `<span class="pi-field-bar"><span style="inline-size:${high}%"></span></span>`
              + `<span class="pi-field-pct">${esc(num(f.percentile, 0))}%</span>`
              + '</div>';
          }).join('')
          + `<p class="pi-note">${esc(pick(T.cohort_direction))}</p>`
          + `<p class="pi-note">${esc(sourceLine)}</p>`
          + `<p class="pi-note pi-note--warn">${esc(pick(T.cohort_synthetic))}</p>`;
      }
      return ''
        + '<article class="pi-card pi-card--cohort">'
        + `<h3 class="pi-card-title">${esc(pick(T.cohort_title))}</h3>`
        + body
        + '</article>';
    }

    function modelCard() {
      const model = (data && data.model) || {};
      let body;
      if (!model.available) {
        const key = `model_reason_${model.reason || 'not_enough_days'}`;
        const template = T[key] || T.model_reason_not_enough_days;
        body = `<p class="pi-note">${esc(fill(pick(template), { n: model.days || 0, min: 8 }))}</p>`;
      } else {
        const widest = Math.max(...model.drivers.map((d) => d.points_per_sd), 1);
        body = ''
          + `<p class="pi-lede">${esc(pick(T.model_lede))}</p>`
          + '<div class="pi-stats">'
          + statHtml(num(model.r2_loo, 2), '', pick(T.model_r2_loo))
          + statHtml(num(model.r2, 2), '', pick(T.model_r2))
          + statHtml(num(model.days, 0), '', pick(T.model_days))
          + '</div>'
          + `<h4 class="pi-sub">${esc(pick(T.model_drivers))}</h4>`
          + model.drivers.map((d) => ''
            + `<div class="pi-driver pi-driver--${esc(d.direction)}">`
            + `<span class="pi-driver-name">${esc(fieldLabel(d.field))}</span>`
            + '<span class="pi-driver-bar"><span style="inline-size:'
            + `${Math.round((d.points_per_sd / widest) * 100)}%"></span></span>`
            + `<span class="pi-driver-value">${esc(num(d.points_per_sd, 2))}</span>`
            + `<span class="pi-driver-dir">${esc(pick(d.direction === 'up' ? T.model_up : T.model_down))}</span>`
            + '</div>').join('')
          + `<p class="pi-note">${esc(pick(T.model_per_sd))}</p>`
          + (model.trustworthy ? '' : `<p class="pi-note pi-note--warn">${esc(pick(T.model_untrustworthy))}</p>`);
      }
      return ''
        + '<article class="pi-card pi-card--model">'
        + `<h3 class="pi-card-title">${esc(pick(T.model_title))}</h3>`
        + body
        + '</article>';
    }

    function factsCard() {
      const facts = (data && data.facts) || [];
      const lines = facts.map(factLine).filter(Boolean);
      return ''
        + '<article class="pi-card pi-card--facts">'
        + `<h3 class="pi-card-title">${esc(pick(T.facts_title))}</h3>`
        + (lines.length
          ? `<ul class="pi-facts">${lines.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>`
          : `<p class="pi-note">${esc(pick(T.facts_empty))}</p>`)
        + '</article>';
    }

    function birthCard() {
      const value = (data && data.birth_date) || '';
      return ''
        + '<article class="pi-card pi-card--birth">'
        + `<h3 class="pi-card-title">${esc(pick(T.birth_title))}</h3>`
        + `<p class="pi-note">${esc(pick(T.birth_why))}</p>`
        + '<div class="pi-birth-row">'
        + `<input type="date" class="pi-birth-input" id="piBirth" value="${esc(value)}" dir="ltr">`
        + `<button type="button" class="btn btn-primary btn-sm" id="piBirthSave">${esc(pick(T.birth_save))}</button>`
        + (value
          ? `<button type="button" class="btn btn-ghost btn-sm" id="piBirthClear">${esc(pick(T.birth_clear))}</button>`
          : '')
        + '</div>'
        + '</article>';
    }

    function render() {
      if (failed) {
        root.innerHTML = ''
          + '<header class="pi-head reveal">'
          + `<p class="pi-eyebrow">${esc(pick(T.eyebrow))}</p>`
          + `<h2 class="pi-heading text-gradient">${esc(pick(T.title))}</h2>`
          + `<p class="pi-note pi-note--warn">${esc(pick(T.load_failed))}</p>`
          + '</header>';
        return;
      }
      root.innerHTML = ''
        + '<header class="pi-head reveal">'
        + `<p class="pi-eyebrow">${esc(pick(T.eyebrow))}</p>`
        + `<h2 class="pi-heading text-gradient">${esc(pick(T.title))}</h2>`
        + `<p class="pi-lede">${esc(pick(T.lede))}</p>`
        + '</header>'
        + '<div class="pi-grid">'
        + usageCard()
        + cohortCard()
        + modelCard()
        + factsCard()
        + birthCard()
        + '</div>';
      wire();
      if (window.DWMotion) window.DWMotion.observeReveals(root);
    }

    async function saveBirth(value) {
      if (busy) return;
      busy = true;
      try {
        data = await window.DWApi.personalBirthDate(value);
        render();
        window.DWToast.success(pick(value ? T.birth_saved : T.birth_cleared));
      } catch (err) {
        window.DWToast.error((err && err.message) || pick(T.load_failed));
      } finally {
        busy = false;
      }
    }

    function wire() {
      const save = root.querySelector('#piBirthSave');
      const clear = root.querySelector('#piBirthClear');
      const input = root.querySelector('#piBirth');
      if (save && input) save.addEventListener('click', () => saveBirth(input.value || null));
      if (clear) clear.addEventListener('click', () => saveBirth(null));
    }

    async function load() {
      try {
        data = await window.DWApi.personalInsight();
        failed = false;
      } catch (e) {
        failed = true;
      }
      render();
    }

    load();
    document.addEventListener('dwai:langchange', render);
  }

  window.DWAboutPersonal = { init, FACTS };
})();
