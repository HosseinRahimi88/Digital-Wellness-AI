/*
  Badge registry (C-3) — every string for every badge, in four languages.

  The API sends ids, numbers and state; not one human-readable word. All
  of it is rendered from here, which is the whole point: a name baked
  into a JSON response is what made half the app English on a Persian
  page (A-2).

  Shape per badge:
    name  {en,fa,ar,zh}   short, never a verdict on the person
    desc  {en,fa,ar,zh}   what the criterion actually is, with {a}/{b}
                          filled from the badge's own params/progress
    next  {en,fa,ar,zh}   awareness indicators only — the concrete step.
                          The brief requires every awareness indicator to
                          arrive with one, so a pattern is never just
                          pointed at and left.

  Tone rules, applied to all 63:
    * Achievement names describe the thing done, not the person.
      "A healthy week", never "Sleep champion".
    * Awareness names describe a pattern, never a failure. "Late nights
      are frequent", never "Bad sleep" — and no "should" anywhere.
    * Numbers are the user's own, substituted at render time.
*/
(function () {
  const BADGES = {

    /* ---------------- showing up ---------------- */
    first_checkin: {
      name: { en: 'First step', fa: 'اولین قدم', ar: 'الخطوة الأولى', zh: '第一步' },
      desc: { en: 'You logged your first check-in.', fa: 'اولین بررسی‌ات را ثبت کردی.', ar: 'سجّلت أول تسجيل لك.', zh: '你完成了第一次记录。' },
    },
    checkins_10: {
      name: { en: 'Ten check-ins', fa: 'ده بررسی', ar: 'عشرة تسجيلات', zh: '十次记录' },
      desc: { en: 'Ten check-ins logged in total.', fa: 'در مجموع ده بررسی ثبت شده.', ar: 'عشرة تسجيلات في المجموع.', zh: '累计记录十次。' },
    },
    checkins_30: {
      name: { en: 'Thirty check-ins', fa: 'سی بررسی', ar: 'ثلاثون تسجيلاً', zh: '三十次记录' },
      desc: { en: 'Thirty check-ins logged in total.', fa: 'در مجموع سی بررسی ثبت شده.', ar: 'ثلاثون تسجيلاً في المجموع.', zh: '累计记录三十次。' },
    },
    checkins_60: {
      name: { en: 'Sixty check-ins', fa: 'شصت بررسی', ar: 'ستون تسجيلاً', zh: '六十次记录' },
      desc: { en: 'Sixty check-ins logged in total.', fa: 'در مجموع شصت بررسی ثبت شده.', ar: 'ستون تسجيلاً في المجموع.', zh: '累计记录六十次。' },
    },
    checkins_100: {
      name: { en: 'One hundred check-ins', fa: 'صد بررسی', ar: 'مئة تسجيل', zh: '一百次记录' },
      desc: { en: 'One hundred check-ins logged in total.', fa: 'در مجموع صد بررسی ثبت شده.', ar: 'مئة تسجيل في المجموع.', zh: '累计记录一百次。' },
    },
    first_week: {
      name: { en: 'A week of data', fa: 'یک هفته داده', ar: 'أسبوع من البيانات', zh: '一周的数据' },
      desc: { en: 'Seven different days recorded — enough for the first real comparisons.', fa: 'هفت روز مختلف ثبت شده — به‌اندازه‌ی اولین مقایسه‌های واقعی.', ar: 'سبعة أيام مختلفة مسجَّلة — تكفي لأول مقارنات حقيقية.', zh: '记录了七个不同的日子——足以进行第一次真正的比较。' },
    },
    first_month: {
      name: { en: 'A month of data', fa: 'یک ماه داده', ar: 'شهر من البيانات', zh: '一个月的数据' },
      desc: { en: 'Thirty different days recorded.', fa: 'سی روز مختلف ثبت شده.', ar: 'ثلاثون يوماً مختلفاً مسجَّلة.', zh: '记录了三十个不同的日子。' },
    },
    first_quarter: {
      name: { en: 'Three months of data', fa: 'سه ماه داده', ar: 'ثلاثة أشهر من البيانات', zh: '三个月的数据' },
      desc: { en: 'Ninety different days recorded — long enough to see seasons in your own habits.', fa: 'نود روز مختلف ثبت شده — به‌اندازه‌ای که فصل‌های عادت‌های خودت را ببینی.', ar: 'تسعون يوماً مختلفاً مسجَّلة — مدة تكفي لرؤية مواسم عاداتك.', zh: '记录了九十个不同的日子——足以看出你自己习惯的季节变化。' },
    },
    consistent_logger: {
      name: { en: 'A well-logged week', fa: 'هفته‌ای پر از ثبت', ar: 'أسبوع مسجَّل جيداً', zh: '记录充分的一周' },
      desc: { en: '{a} check-ins inside a single calendar week.', fa: '{a} بررسی در یک هفته‌ی تقویمی.', ar: '{a} تسجيلات في أسبوع تقويمي واحد.', zh: '在同一个日历周内记录了 {a} 次。' },
    },
    log_streak_7: {
      name: { en: 'Seven days running', fa: 'هفت روز پیاپی', ar: 'سبعة أيام متتالية', zh: '连续七天' },
      desc: { en: 'Seven calendar days in a row with a check-in — including the days that were not good ones.', fa: 'هفت روز تقویمی پشت‌سرهم با ثبت — از جمله روزهایی که خوب نبودند.', ar: 'سبعة أيام تقويمية متتالية بتسجيل — بما فيها الأيام التي لم تكن جيدة.', zh: '连续七个日历日都有记录——包括那些并不顺利的日子。' },
    },
    log_streak_14: {
      name: { en: 'Fourteen days running', fa: 'چهارده روز پیاپی', ar: 'أربعة عشر يوماً متتالياً', zh: '连续十四天' },
      desc: { en: 'Fourteen calendar days in a row with a check-in.', fa: 'چهارده روز تقویمی پشت‌سرهم با ثبت.', ar: 'أربعة عشر يوماً تقويمياً متتالياً بتسجيل.', zh: '连续十四个日历日都有记录。' },
    },
    log_streak_30: {
      name: { en: 'Thirty days running', fa: 'سی روز پیاپی', ar: 'ثلاثون يوماً متتالياً', zh: '连续三十天' },
      desc: { en: 'Thirty calendar days in a row with a check-in.', fa: 'سی روز تقویمی پشت‌سرهم با ثبت.', ar: 'ثلاثون يوماً تقويمياً متتالياً بتسجيل.', zh: '连续三十个日历日都有记录。' },
    },
    two_full_weeks: {
      name: { en: 'Two complete weeks', fa: 'دو هفته‌ی کامل', ar: 'أسبوعان كاملان', zh: '两个完整的周' },
      desc: { en: 'Two weeks with seven days each — the point where week-vs-week comparisons start meaning something.', fa: 'دو هفته که هرکدام هفت روز دارند — جایی که مقایسه‌ی هفته با هفته معنا پیدا می‌کند.', ar: 'أسبوعان كل منهما سبعة أيام — النقطة التي تبدأ عندها مقارنة أسبوع بأسبوع في أن تعني شيئاً.', zh: '两个各有七天的周——从这里开始，周与周的比较才有意义。' },
    },

    /* ---------------- healthy streaks ---------------- */
    streak_3: {
      name: { en: 'Three healthy days', fa: 'سه روز سالم', ar: 'ثلاثة أيام صحية', zh: '三个健康的日子' },
      desc: { en: 'Three days in a row above your healthy-day threshold.', fa: 'سه روز پشت‌سرهم بالاتر از آستانه‌ی روز سالم.', ar: 'ثلاثة أيام متتالية فوق عتبة اليوم الصحي.', zh: '连续三天高于健康日阈值。' },
    },
    streak_7: {
      name: { en: 'A healthy week', fa: 'یک هفته‌ی سالم', ar: 'أسبوع صحي', zh: '健康的一周' },
      desc: { en: 'Seven days in a row above your healthy-day threshold.', fa: 'هفت روز پشت‌سرهم بالاتر از آستانه‌ی روز سالم.', ar: 'سبعة أيام متتالية فوق عتبة اليوم الصحي.', zh: '连续七天高于健康日阈值。' },
    },
    streak_14: {
      name: { en: 'Two healthy weeks', fa: 'دو هفته‌ی سالم', ar: 'أسبوعان صحيان', zh: '健康的两周' },
      desc: { en: 'Fourteen days in a row above your healthy-day threshold.', fa: 'چهارده روز پشت‌سرهم بالاتر از آستانه‌ی روز سالم.', ar: 'أربعة عشر يوماً متتالياً فوق عتبة اليوم الصحي.', zh: '连续十四天高于健康日阈值。' },
    },
    streak_30: {
      name: { en: 'A healthy month', fa: 'یک ماه سالم', ar: 'شهر صحي', zh: '健康的一个月' },
      desc: { en: 'Thirty days in a row above your healthy-day threshold.', fa: 'سی روز پشت‌سرهم بالاتر از آستانه‌ی روز سالم.', ar: 'ثلاثون يوماً متتالياً فوق عتبة اليوم الصحي.', zh: '连续三十天高于健康日阈值。' },
    },

    /* ---------------- score ---------------- */
    high_scorer: {
      name: { en: 'A high day', fa: 'یک روز بالا', ar: 'يوم مرتفع', zh: '高分的一天' },
      desc: { en: 'Your best day reached {a}.', fa: 'بهترین روزت به {a} رسید.', ar: 'بلغ أفضل أيامك {a}.', zh: '你最好的一天达到了 {a}。' },
    },
    score_90: {
      name: { en: 'Ninety', fa: 'نود', ar: 'تسعون', zh: '九十' },
      desc: { en: 'A single day at 90 or above — rare in anyone’s history.', fa: 'یک روز با نود یا بالاتر — در سابقه‌ی هر کسی کمیاب است.', ar: 'يوم واحد عند 90 أو أكثر — نادر في سجل أي شخص.', zh: '有一天达到 90 或以上——在任何人的记录里都很少见。' },
    },
    most_improved: {
      name: { en: 'Biggest climb', fa: 'بیشترین صعود', ar: 'أكبر صعود', zh: '最大的攀升' },
      desc: { en: 'Your best day sits {a} points above your very first one.', fa: 'بهترین روزت {a} امتیاز بالاتر از اولین روزت است.', ar: 'أفضل أيامك أعلى بـ {a} نقطة من أول يوم لك.', zh: '你最好的一天比最初那天高 {a} 分。' },
    },
    personal_best: {
      name: { en: 'Personal best', fa: 'رکورد شخصی', ar: 'أفضل رقم شخصي', zh: '个人最佳' },
      desc: { en: 'Your latest day is the highest you have logged — {a}, past your previous {b}.', fa: 'آخرین روزت بالاترین چیزی است که ثبت کرده‌ای — {a}، بالاتر از {b} قبلی.', ar: 'آخر أيامك هو الأعلى الذي سجّلته — {a}، متجاوزاً {b} السابق.', zh: '你最近这一天是你记录过的最高分——{a}，超过了之前的 {b}。' },
    },
    steady_scores: {
      name: { en: 'A steady fortnight', fa: 'دو هفته‌ی یکنواخت', ar: 'أسبوعان مستقران', zh: '平稳的两周' },
      desc: { en: 'Two weeks with very little swing between days. Steadiness never shows up in an average.', fa: 'دو هفته با نوسان بسیار کم بین روزها. یکنواختی هرگز در میانگین دیده نمی‌شود.', ar: 'أسبوعان بتذبذب ضئيل جداً بين الأيام. الاستقرار لا يظهر أبداً في المتوسط.', zh: '两周之内日与日之间波动很小。平稳从来不会体现在平均值里。' },
    },
    recovery: {
      name: { en: 'Back up again', fa: 'دوباره بالا', ar: 'العودة إلى الأعلى', zh: '重新回升' },
      desc: { en: 'Your score climbed {a} points back from your lowest day.', fa: 'امتیازت {a} امتیاز از پایین‌ترین روزت بالا آمد.', ar: 'ارتفعت درجتك {a} نقطة عن أدنى أيامك.', zh: '你的分数从最低的那一天回升了 {a} 分。' },
    },
    comeback: {
      name: { en: 'Came back', fa: 'برگشتی', ar: 'عُدت', zh: '你回来了' },
      desc: { en: 'You stopped for a while and then came back and stayed. Restarting is harder than continuing.', fa: 'مدتی متوقف شدی و بعد برگشتی و ماندی. شروع دوباره سخت‌تر از ادامه دادن است.', ar: 'توقفت فترة ثم عدت وبقيت. البدء من جديد أصعب من الاستمرار.', zh: '你停了一阵子，然后回来了，并且留了下来。重新开始比一直坚持更难。' },
    },

    /* ---------------- data honesty ---------------- */
    exception_marker: {
      name: { en: 'Honest data', fa: 'داده‌ی صادقانه', ar: 'بيانات صادقة', zh: '诚实的数据' },
      desc: { en: 'You marked a day as an exception. That one action keeps every baseline in this app truthful.', fa: 'یک روز را استثنا علامت زدی. همین یک کار، هر خط پایه‌ی این برنامه را درست نگه می‌دارد.', ar: 'وضعت علامة استثناء على يوم. هذا الفعل وحده يُبقي كل خط أساس في هذا التطبيق صادقاً.', zh: '你把某一天标记为例外。仅这一个动作，就让这个应用里的每条基线都保持真实。' },
    },

    /* ---------------- improvements (first week vs last) ---------------- */
    improve_screen_time: {
      name: { en: 'Less screen time', fa: 'زمان صفحه‌ی کمتر', ar: 'وقت شاشة أقل', zh: '更少的屏幕时间' },
      desc: { en: 'Total screen time is down {a}% from your first week to your last.', fa: 'زمان کل صفحه از هفته‌ی اولت تا آخری {a}٪ کم شده.', ar: 'إجمالي وقت الشاشة انخفض {a}٪ من أسبوعك الأول إلى الأخير.', zh: '从第一周到最近一周，总屏幕时间下降了 {a}%。' },
    },
    improve_night_screen: {
      name: { en: 'Quieter nights', fa: 'شب‌های آرام‌تر', ar: 'ليالٍ أهدأ', zh: '更安静的夜晚' },
      desc: { en: 'Late-night screen time is down {a}% from your first week to your last.', fa: 'زمان صفحه در شب از هفته‌ی اولت تا آخری {a}٪ کم شده.', ar: 'وقت الشاشة في وقت متأخر من الليل انخفض {a}٪ من أسبوعك الأول إلى الأخير.', zh: '从第一周到最近一周，深夜屏幕时间下降了 {a}%。' },
    },
    improve_pre_sleep: {
      name: { en: 'A calmer last hour', fa: 'ساعت آخرِ آرام‌تر', ar: 'ساعة أخيرة أهدأ', zh: '更平静的睡前一小时' },
      desc: { en: 'Screen time in the hour before sleep is down {a}%.', fa: 'زمان صفحه در ساعت پیش از خواب {a}٪ کم شده.', ar: 'وقت الشاشة في الساعة التي تسبق النوم انخفض {a}٪.', zh: '睡前一小时的屏幕时间下降了 {a}%。' },
    },
    improve_sleep_hours: {
      name: { en: 'More sleep', fa: 'خواب بیشتر', ar: 'نوم أكثر', zh: '更多睡眠' },
      desc: { en: 'Sleep is up {a}% from your first week to your last.', fa: 'خواب از هفته‌ی اولت تا آخری {a}٪ بیشتر شده.', ar: 'النوم ارتفع {a}٪ من أسبوعك الأول إلى الأخير.', zh: '从第一周到最近一周，睡眠增加了 {a}%。' },
    },
    improve_sleep_quality: {
      name: { en: 'Better sleep quality', fa: 'کیفیت خواب بهتر', ar: 'جودة نوم أفضل', zh: '更好的睡眠质量' },
      desc: { en: 'Your own sleep-quality rating is up {a}%.', fa: 'امتیازی که خودت به کیفیت خواب می‌دهی {a}٪ بالا رفته.', ar: 'تقييمك أنت لجودة نومك ارتفع {a}٪.', zh: '你自己给睡眠质量的评分提高了 {a}%。' },
    },
    improve_stress: {
      name: { en: 'Less reported stress', fa: 'استرس گزارش‌شده‌ی کمتر', ar: 'توتر مُبلَّغ عنه أقل', zh: '报告的压力更少' },
      desc: { en: 'The stress level you report is down {a}%.', fa: 'سطح استرسی که گزارش می‌کنی {a}٪ کم شده.', ar: 'مستوى التوتر الذي تُبلغ عنه انخفض {a}٪.', zh: '你报告的压力水平下降了 {a}%。' },
    },
    improve_focus: {
      name: { en: 'Sharper focus', fa: 'تمرکز بهتر', ar: 'تركيز أوضح', zh: '更集中的注意力' },
      desc: { en: 'Your focus rating is up {a}%.', fa: 'امتیاز تمرکزت {a}٪ بالا رفته.', ar: 'تقييم تركيزك ارتفع {a}٪.', zh: '你的专注度评分提高了 {a}%。' },
    },
    improve_productivity: {
      name: { en: 'More productive days', fa: 'روزهای پربارتر', ar: 'أيام أكثر إنتاجية', zh: '更有产出的日子' },
      desc: { en: 'Your productivity rating is up {a}%.', fa: 'امتیاز بهره‌وری‌ات {a}٪ بالا رفته.', ar: 'تقييم إنتاجيتك ارتفع {a}٪.', zh: '你的效率评分提高了 {a}%。' },
    },
    improve_activity: {
      name: { en: 'More movement', fa: 'تحرک بیشتر', ar: 'حركة أكثر', zh: '更多活动' },
      desc: { en: 'Daily physical activity is up {a}%.', fa: 'فعالیت بدنی روزانه {a}٪ بیشتر شده.', ar: 'النشاط البدني اليومي ارتفع {a}٪.', zh: '每日身体活动增加了 {a}%。' },
    },
    improve_pickups: {
      name: { en: 'Fewer pickups', fa: 'برداشتن کمترِ گوشی', ar: 'التقاط الهاتف أقل', zh: '更少的拿起次数' },
      desc: { en: 'You pick up your phone {a}% less than in your first week.', fa: 'نسبت به هفته‌ی اولت {a}٪ کمتر گوشی را برمی‌داری.', ar: 'تلتقط هاتفك {a}٪ أقل مما كنت في أسبوعك الأول.', zh: '与第一周相比，你拿起手机的次数少了 {a}%。' },
    },
    improve_notifications: {
      name: { en: 'Fewer interruptions', fa: 'وقفه‌های کمتر', ar: 'مقاطعات أقل', zh: '更少的打断' },
      desc: { en: 'Notification pressure is down {a}%.', fa: 'فشار اعلان‌ها {a}٪ کم شده.', ar: 'ضغط الإشعارات انخفض {a}٪.', zh: '通知带来的压力下降了 {a}%。' },
    },
    improve_fragmentation: {
      name: { en: 'Longer unbroken stretches', fa: 'بازه‌های پیوسته‌ی طولانی‌تر', ar: 'فترات متواصلة أطول', zh: '更长的连续时段' },
      desc: { en: 'Your day is {a}% less fragmented than it was.', fa: 'روزت {a}٪ کمتر از قبل تکه‌تکه شده.', ar: 'يومك أقل تجزؤاً بنسبة {a}٪ عما كان.', zh: '你的一天比过去少了 {a}% 的碎片化。' },
    },
    improve_social_comparison: {
      name: { en: 'Less comparing', fa: 'مقایسه‌ی کمتر', ar: 'مقارنة أقل', zh: '更少的比较' },
      desc: { en: 'How much you compare yourself to others online is down {a}%.', fa: 'میزان مقایسه‌ی خودت با دیگران در فضای آنلاین {a}٪ کم شده.', ar: 'مقدار مقارنتك بنفسك مع الآخرين على الإنترنت انخفض {a}٪.', zh: '你在网上与他人比较的程度下降了 {a}%。' },
    },

    /* ---------------- sustained a level for a full week ---------------- */
    week_of_sleep: {
      name: { en: 'Seven nights of sleep', fa: 'هفت شب خواب', ar: 'سبع ليالٍ من النوم', zh: '七个睡好的夜晚' },
      desc: { en: 'Seven nights in a row at seven hours or more.', fa: 'هفت شب پشت‌سرهم، هفت ساعت یا بیشتر.', ar: 'سبع ليالٍ متتالية بسبع ساعات أو أكثر.', zh: '连续七晚睡够七小时或以上。' },
    },
    week_of_activity: {
      name: { en: 'Seven days of moving', fa: 'هفت روز تحرک', ar: 'سبعة أيام من الحركة', zh: '七天都在活动' },
      desc: { en: 'Half an hour of activity or more, every day for a week.', fa: 'نیم ساعت فعالیت یا بیشتر، هر روز به‌مدت یک هفته.', ar: 'نصف ساعة من النشاط أو أكثر، كل يوم لمدة أسبوع.', zh: '一周里每天都有半小时或更多的活动。' },
    },
    week_of_calm: {
      name: { en: 'A calm week', fa: 'یک هفته‌ی آرام', ar: 'أسبوع هادئ', zh: '平静的一周' },
      desc: { en: 'Seven days in a row with your reported stress at four or below.', fa: 'هفت روز پشت‌سرهم با استرس گزارش‌شده‌ی چهار یا کمتر.', ar: 'سبعة أيام متتالية بتوتر مُبلَّغ عنه أربعة أو أقل.', zh: '连续七天你报告的压力都在四或以下。' },
    },
    week_of_focus: {
      name: { en: 'A focused week', fa: 'یک هفته‌ی متمرکز', ar: 'أسبوع مركَّز', zh: '专注的一周' },
      desc: { en: 'Seven days in a row with focus at 70 or above.', fa: 'هفت روز پشت‌سرهم با تمرکز هفتاد یا بالاتر.', ar: 'سبعة أيام متتالية بتركيز 70 أو أعلى.', zh: '连续七天专注度在 70 或以上。' },
    },
    week_off_late_nights: {
      name: { en: 'A week without late nights', fa: 'یک هفته بدون شب‌بیداری', ar: 'أسبوع بلا سهر', zh: '没有熬夜的一周' },
      desc: { en: 'Seven days in a row with almost no late-night screen time.', fa: 'هفت روز پشت‌سرهم تقریباً بدون زمان صفحه در شب.', ar: 'سبعة أيام متتالية بلا وقت شاشة ليلي تقريباً.', zh: '连续七天几乎没有深夜使用屏幕。' },
    },
    week_of_light_screens: {
      name: { en: 'A light week', fa: 'یک هفته‌ی سبک', ar: 'أسبوع خفيف', zh: '轻松的一周' },
      desc: { en: 'Seven days in a row under five hours of total screen time.', fa: 'هفت روز پشت‌سرهم کمتر از پنج ساعت زمان کل صفحه.', ar: 'سبعة أيام متتالية بأقل من خمس ساعات من إجمالي وقت الشاشة.', zh: '连续七天总屏幕时间低于五小时。' },
    },

    /* ---------------- awareness indicators (private) ---------------- */
    aware_late_night: {
      name: { en: 'Late nights are frequent', fa: 'شب‌بیداری زیاد شده', ar: 'السهر متكرر', zh: '深夜使用频繁' },
      desc: { en: 'Screens were still on late on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، صفحه‌ها تا دیروقت روشن بوده.', ar: 'كانت الشاشات مضاءة حتى وقت متأخر في {a} من آخر {b} أيام لك.', zh: '在你最近的 {b} 天里，有 {a} 天屏幕一直亮到很晚。' },
      next: { en: 'Pick one night this week to put the phone in another room. One night is a real test; seven is a resolution.', fa: 'یک شب از این هفته را انتخاب کن و گوشی را در اتاق دیگری بگذار. یک شب یک آزمایش واقعی است؛ هفت شب یک تصمیم بزرگ.', ar: 'اختر ليلة واحدة هذا الأسبوع تضع فيها الهاتف في غرفة أخرى. ليلة واحدة اختبار حقيقي؛ وسبع ليالٍ قرار كبير.', zh: '这周挑一个晚上，把手机放到另一个房间。一个晚上是真实的尝试；七个晚上则是一项决心。' },
    },
    aware_pre_sleep: {
      name: { en: 'The last hour is busy', fa: 'ساعت آخر شلوغ است', ar: 'الساعة الأخيرة مزدحمة', zh: '睡前一小时很忙碌' },
      desc: { en: 'The hour before sleep had significant screen use on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، ساعت پیش از خواب استفاده‌ی قابل‌توجهی از صفحه داشته.', ar: 'الساعة التي تسبق النوم شهدت استخداماً ملحوظاً للشاشة في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天睡前一小时有明显的屏幕使用。' },
      next: { en: 'Try moving one habit — the last scroll, the last video — to before dinner instead of after it.', fa: 'یک عادت را جابه‌جا کن — آخرین اسکرول، آخرین ویدیو — به قبل از شام به‌جای بعد از آن.', ar: 'جرّب نقل عادة واحدة — آخر تصفح، آخر فيديو — إلى ما قبل العشاء بدل ما بعده.', zh: '试着把一个习惯——最后一次刷手机、最后一个视频——挪到晚饭前而不是晚饭后。' },
    },
    aware_short_sleep: {
      name: { en: 'Short nights', fa: 'شب‌های کوتاه', ar: 'ليالٍ قصيرة', zh: '睡眠偏短' },
      desc: { en: 'Sleep was under six hours on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، خواب کمتر از شش ساعت بوده.', ar: 'كان النوم أقل من ست ساعات في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天睡眠不足六小时。' },
      next: { en: 'Sleep responds to bedtime far more than to wake time. Moving lights-out fifteen minutes earlier is the smallest change that shows up in the data.', fa: 'خواب بیشتر به زمان خوابیدن واکنش نشان می‌دهد تا زمان بیدارشدن. پانزده دقیقه زودتر خاموش‌کردن چراغ، کوچک‌ترین تغییری است که در داده دیده می‌شود.', ar: 'النوم يستجيب لموعد الخلود للفراش أكثر بكثير من موعد الاستيقاظ. تقديم إطفاء الضوء بخمس عشرة دقيقة هو أصغر تغيير يظهر في البيانات.', zh: '睡眠对上床时间的反应远大于对起床时间的反应。把熄灯时间提前十五分钟，是能在数据里看到的最小改变。' },
    },
    aware_high_stress: {
      name: { en: 'Stress has been high', fa: 'استرس بالا بوده', ar: 'التوتر كان مرتفعاً', zh: '压力一直偏高' },
      desc: { en: 'You rated your stress at seven or above on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، استرست را هفت یا بالاتر ارزیابی کردی.', ar: 'قيّمت توترك بسبعة أو أكثر في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天你把压力评为七或以上。' },
      next: { en: 'This is your own rating, not a diagnosis. If it stays here for weeks, talking to someone qualified is a reasonable next step — this app is not one.', fa: 'این ارزیابی خودت است، نه یک تشخیص. اگر هفته‌ها همین‌جا بماند، صحبت با یک فرد متخصص قدم بعدی معقولی است — این برنامه چنین چیزی نیست.', ar: 'هذا تقييمك أنت، لا تشخيص. إن بقي هنا أسابيع، فالتحدث إلى مختص خطوة تالية معقولة — وهذا التطبيق ليس كذلك.', zh: '这是你自己的评分，不是诊断。如果这种情况持续数周，找一位专业人士谈谈是合理的下一步——这个应用不是。' },
    },
    aware_low_focus: {
      name: { en: 'Focus has been scattered', fa: 'تمرکز پراکنده بوده', ar: 'التركيز كان مشتتاً', zh: '注意力比较分散' },
      desc: { en: 'Focus came in under 40 on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، تمرکز زیر چهل بوده.', ar: 'جاء التركيز دون 40 في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天专注度低于 40。' },
      next: { en: 'Focus usually follows sleep and interruptions rather than willpower. Your own data can tell you which of the two moves first.', fa: 'تمرکز معمولاً دنبال خواب و وقفه‌ها می‌آید نه اراده. داده‌ی خودت می‌تواند بگوید کدام‌یک اول تکان می‌خورد.', ar: 'التركيز يتبع عادةً النوم والمقاطعات أكثر من قوة الإرادة. بياناتك أنت تستطيع أن تخبرك أيهما يتحرك أولاً.', zh: '专注度通常跟随睡眠和打断，而不是意志力。你自己的数据能告诉你这两者中哪个先动。' },
    },
    aware_fragmentation: {
      name: { en: 'The day is fragmented', fa: 'روز تکه‌تکه است', ar: 'اليوم مجزّأ', zh: '一天被切得很碎' },
      desc: { en: 'Your day was broken into many short pieces on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، روزت به تکه‌های کوتاه زیادی شکسته شده.', ar: 'تجزأ يومك إلى قطع قصيرة كثيرة في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天你的一天被切成了许多短小的片段。' },
      next: { en: 'One protected thirty-minute block is easier to defend than a whole reorganised day — and it shows up in this number.', fa: 'یک بازه‌ی سی‌دقیقه‌ای محافظت‌شده راحت‌تر از یک روزِ کاملاً بازچینی‌شده حفظ می‌شود — و در همین عدد دیده می‌شود.', ar: 'كتلة واحدة محمية من ثلاثين دقيقة أسهل في الدفاع عنها من إعادة تنظيم يوم كامل — وتظهر في هذا الرقم.', zh: '守住一个受保护的三十分钟时段，比重新安排一整天要容易——而且它会体现在这个数字上。' },
    },
    aware_pickups: {
      name: { en: 'Frequent pickups', fa: 'برداشتن پی‌درپی گوشی', ar: 'التقاط متكرر للهاتف', zh: '频繁拿起手机' },
      desc: { en: 'Your phone was picked up very often on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، گوشی خیلی زیاد برداشته شده.', ar: 'التُقط هاتفك كثيراً جداً في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天你非常频繁地拿起手机。' },
      next: { en: 'Pickups usually track notifications more than intent. Turning off one noisy app is often the whole fix.', fa: 'تعداد برداشتن گوشی بیشتر دنبال اعلان‌هاست تا قصد. خاموش‌کردن اعلان یک برنامه‌ی پرسروصدا اغلب تمام راه‌حل است.', ar: 'عدد مرات الالتقاط يتبع الإشعارات أكثر من النية. كتم تطبيق واحد صاخب غالباً ما يكون الحل كله.', zh: '拿起手机的次数通常更多地跟随通知而非本意。关掉一个吵闹应用的通知，往往就是全部的解法。' },
    },
    aware_notifications: {
      name: { en: 'Notification pressure', fa: 'فشار اعلان‌ها', ar: 'ضغط الإشعارات', zh: '通知的压力' },
      desc: { en: 'Interruption density was high on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، چگالی وقفه‌ها بالا بوده.', ar: 'كانت كثافة المقاطعات عالية في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天打断的密度很高。' },
      next: { en: 'Notifications are the one input here you can change in about a minute, and the change is immediate.', fa: 'اعلان‌ها تنها ورودی اینجاست که در حدود یک دقیقه می‌توانی عوضش کنی، و اثرش فوری است.', ar: 'الإشعارات هي المُدخل الوحيد هنا الذي يمكنك تغييره في دقيقة تقريباً، والتغيير فوري.', zh: '通知是这里唯一一个你大约一分钟就能改变的输入项，而且改变立刻生效。' },
    },
    aware_low_activity: {
      name: { en: 'Little movement', fa: 'تحرک کم', ar: 'حركة قليلة', zh: '活动很少' },
      desc: { en: 'Physical activity stayed under fifteen minutes on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، فعالیت بدنی زیر پانزده دقیقه مانده.', ar: 'بقي النشاط البدني دون خمس عشرة دقيقة في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天身体活动不足十五分钟。' },
      next: { en: 'A ten-minute walk is enough to register here. The number is not asking for a training plan.', fa: 'ده دقیقه پیاده‌روی برای ثبت‌شدن اینجا کافی است. این عدد از تو برنامه‌ی تمرینی نمی‌خواهد.', ar: 'عشر دقائق مشي تكفي لتُسجَّل هنا. هذا الرقم لا يطلب منك خطة تدريب.', zh: '十分钟的散步就足以在这里被记录。这个数字并不是在要求一份训练计划。' },
    },
    aware_social_comparison: {
      name: { en: 'Comparing a lot', fa: 'مقایسه‌ی زیاد', ar: 'مقارنة كثيرة', zh: '比较得比较多' },
      desc: { en: 'You rated online comparison at seven or above on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، مقایسه‌ی آنلاین را هفت یا بالاتر ارزیابی کردی.', ar: 'قيّمت المقارنة على الإنترنت بسبعة أو أكثر في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天你把网上比较评为七或以上。' },
      next: { en: 'This one tends to be about which feeds, not how much time. Muting a handful of accounts moves it further than cutting an hour.', fa: 'این یکی بیشتر به این ربط دارد که کدام فیدها، نه چقدر زمان. بی‌صدا کردن چند حساب بیشتر از کم‌کردن یک ساعت اثر دارد.', ar: 'هذه المسألة تتعلق غالباً بأي المحتوى تتابع، لا بكم الوقت. كتم حفنة من الحسابات يحركها أكثر من اقتطاع ساعة.', zh: '这一项通常关乎你看的是哪些内容，而不是花了多少时间。静音几个账号比少花一小时更有效。' },
    },
    aware_long_screen_days: {
      name: { en: 'Long screen days', fa: 'روزهای طولانیِ صفحه', ar: 'أيام شاشة طويلة', zh: '长时间使用屏幕的日子' },
      desc: { en: 'Total screen time passed eight hours on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، زمان کل صفحه از هشت ساعت گذشته.', ar: 'تجاوز إجمالي وقت الشاشة ثماني ساعات في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天总屏幕时间超过八小时。' },
      next: { en: 'If most of it is work, this number is describing your job, not your habits. The split by category says which.', fa: 'اگر بیشترش کار است، این عدد شغلت را توصیف می‌کند نه عادت‌هایت. تفکیک بر اساس دسته می‌گوید کدام.', ar: 'إن كان معظمه عملاً، فهذا الرقم يصف وظيفتك لا عاداتك. التقسيم حسب الفئة يخبرك أيهما.', zh: '如果其中大部分是工作，这个数字描述的是你的职业而不是你的习惯。按类别的拆分会告诉你是哪一种。' },
    },
    aware_social_heavy: {
      name: { en: 'Social apps lead the day', fa: 'شبکه‌های اجتماعی صدرنشین روزند', ar: 'تطبيقات التواصل تتصدر اليوم', zh: '社交应用占据了一天' },
      desc: { en: 'Social apps went past three hours on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، شبکه‌های اجتماعی از سه ساعت گذشته.', ar: 'تجاوزت تطبيقات التواصل ثلاث ساعات في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天社交应用超过了三小时。' },
      next: { en: 'Worth checking against your comparison rating — the two move together for a lot of people, and only one of them is easy to feel.', fa: 'ارزش دارد با امتیاز مقایسه‌ات بسنجی‌اش — این دو برای خیلی‌ها با هم حرکت می‌کنند، و فقط یکی‌شان به‌راحتی حس می‌شود.', ar: 'يستحق أن تقارنه بتقييم المقارنة لديك — الاثنان يتحركان معاً عند كثيرين، وواحد منهما فقط يسهل الشعور به.', zh: '值得和你的“比较”评分对照看看——对很多人来说这两者一起变化，而其中只有一个容易被察觉。' },
    },
    aware_gaming_heavy: {
      name: { en: 'Long gaming sessions', fa: 'جلسات طولانی بازی', ar: 'جلسات لعب طويلة', zh: '长时间的游戏' },
      desc: { en: 'Gaming went past three hours on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، بازی از سه ساعت گذشته.', ar: 'تجاوز اللعب ثلاث ساعات في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天游戏超过了三小时。' },
      next: { en: 'Gaming is not a problem by itself here — the thing to watch is whether it is landing after midnight. Your night figure answers that.', fa: 'بازی به‌خودی‌خود اینجا مشکل نیست — چیزی که باید حواست باشد این است که بعد از نیمه‌شب می‌افتد یا نه. عدد شبانه‌ات همین را جواب می‌دهد.', ar: 'اللعب بحد ذاته ليس مشكلة هنا — ما يستحق الانتباه هو ما إذا كان يقع بعد منتصف الليل. رقمك الليلي يجيب عن ذلك.', zh: '游戏本身在这里不是问题——要留意的是它是否发生在午夜之后。你的夜间数字能回答这一点。' },
    },
    aware_video_heavy: {
      name: { en: 'Long video stretches', fa: 'بازه‌های طولانی ویدیو', ar: 'فترات فيديو طويلة', zh: '长时间的视频' },
      desc: { en: 'Video went past three hours on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، ویدیو از سه ساعت گذشته.', ar: 'تجاوز الفيديو ثلاث ساعات في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天视频超过了三小时。' },
      next: { en: 'Autoplay is doing some of this. Turning it off is a single setting and changes the shape of an evening.', fa: 'پخش خودکار بخشی از این را انجام می‌دهد. خاموش‌کردنش فقط یک تنظیم است و شکل یک عصر را عوض می‌کند.', ar: 'التشغيل التلقائي مسؤول عن جزء من هذا. إيقافه إعداد واحد ويغيّر شكل الأمسية.', zh: '自动播放促成了其中一部分。关掉它只是一个设置，却会改变一个晚上的形状。' },
    },
    aware_low_productivity: {
      name: { en: 'Productive time is thin', fa: 'زمان پربار کم است', ar: 'الوقت المنتج قليل', zh: '有产出的时间偏少' },
      desc: { en: 'You rated productivity under 40 on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، بهره‌وری را زیر چهل ارزیابی کردی.', ar: 'قيّمت الإنتاجية دون 40 في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天你把效率评为低于 40。' },
      next: { en: 'This is your own rating of your own day, and a quiet week is allowed to be a quiet week.', fa: 'این ارزیابی خودت از روز خودت است، و یک هفته‌ی آرام حق دارد آرام باشد.', ar: 'هذا تقييمك أنت ليومك أنت، ومن حق الأسبوع الهادئ أن يكون هادئاً.', zh: '这是你自己对自己一天的评分，而安静的一周本就可以是安静的一周。' },
    },
    aware_low_sleep_quality: {
      name: { en: 'Sleep feels poor', fa: 'کیفیت خواب پایین حس می‌شود', ar: 'النوم يبدو رديئاً', zh: '睡眠感觉不佳' },
      desc: { en: 'You rated sleep quality at five or below on {a} of your last {b} days.', fa: 'در {a} روز از {b} روز اخیرت، کیفیت خواب را پنج یا کمتر ارزیابی کردی.', ar: 'قيّمت جودة النوم بخمسة أو أقل في {a} من آخر {b} أيام.', zh: '在你最近的 {b} 天里，有 {a} 天你把睡眠质量评为五或以下。' },
      next: { en: 'Quality and hours are different numbers, and yours may disagree. Comparing them is the useful move.', fa: 'کیفیت و ساعت دو عدد متفاوت‌اند و ممکن است با هم نخوانند. مقایسه‌شان کار مفیدی است.', ar: 'الجودة والساعات رقمان مختلفان وقد لا يتفقان لديك. مقارنتهما هي الخطوة المفيدة.', zh: '质量和时长是两个不同的数字，你的这两个也可能并不一致。把它们放在一起比较才有用。' },
    },
    aware_rising_screen_time: {
      name: { en: 'Screen time is climbing', fa: 'زمان صفحه در حال بالا رفتن است', ar: 'وقت الشاشة يتصاعد', zh: '屏幕时间在上升' },
      desc: { en: 'This week is {a}% above last week.', fa: 'این هفته {a}٪ بالاتر از هفته‌ی قبل است.', ar: 'هذا الأسبوع أعلى بـ {a}٪ من الأسبوع الماضي.', zh: '这一周比上一周高出 {a}%。' },
      next: { en: 'One week is a week, not a trend. If it repeats next week, that is when it is telling you something.', fa: 'یک هفته فقط یک هفته است، نه یک روند. اگر هفته‌ی بعد هم تکرار شد، آن‌وقت دارد چیزی می‌گوید.', ar: 'أسبوع واحد هو أسبوع، لا اتجاه. إن تكرر الأسبوع القادم، فعندها يقول لك شيئاً.', zh: '一周就只是一周，不是趋势。如果下周还是这样，那才是它在告诉你什么。' },
    },
    aware_sleep_variability: {
      name: { en: 'Sleep times swing a lot', fa: 'زمان خواب نوسان زیادی دارد', ar: 'أوقات النوم تتذبذب كثيراً', zh: '睡眠时长波动较大' },
      desc: { en: 'Your sleep varies by about {a} hours from night to night.', fa: 'خوابت شب‌به‌شب حدود {a} ساعت فرق می‌کند.', ar: 'يتفاوت نومك بنحو {a} ساعة من ليلة إلى أخرى.', zh: '你的睡眠时长每晚相差大约 {a} 小时。' },
      next: { en: 'Regularity tends to matter as much as total hours. A fixed wake time is usually the easier end to hold.', fa: 'نظم معمولاً به‌اندازه‌ی کل ساعت‌ها اهمیت دارد. ثابت‌نگه‌داشتن زمان بیدارشدن معمولاً سرِ آسان‌تر ماجراست.', ar: 'الانتظام غالباً بأهمية مجموع الساعات. تثبيت وقت الاستيقاظ عادةً هو الطرف الأسهل للحفاظ عليه.', zh: '规律性往往和总时长同样重要。固定起床时间通常是更容易守住的那一端。' },
    },
    aware_score_declining: {
      name: { en: 'The trend has turned down', fa: 'روند رو به پایین شده', ar: 'الاتجاه انعطف نزولاً', zh: '趋势转为下行' },
      desc: { en: 'Your recent week averages {a} points below your first one.', fa: 'میانگین هفته‌ی اخیرت {a} امتیاز پایین‌تر از هفته‌ی اولت است.', ar: 'متوسط أسبوعك الأخير أقل بـ {a} نقطة من أسبوعك الأول.', zh: '你最近一周的平均分比第一周低 {a} 分。' },
      next: { en: 'Worth looking at, not worth beating yourself up over. The only check-in you can change is the next one.', fa: 'ارزش نگاه‌کردن دارد، نه سرزنش خود. تنها بررسی‌ای که می‌توانی عوضش کنی، بعدی است.', ar: 'يستحق النظر، لا لوم الذات. التسجيل الوحيد الذي يمكنك تغييره هو التالي.', zh: '值得看一看，但不值得自责。你唯一能改变的，是下一次记录。' },
    },
  };

  const TIERS = {
    common: { en: 'Common', fa: 'معمولی', ar: 'شائع', zh: '普通' },
    rare: { en: 'Rare', fa: 'کمیاب', ar: 'نادر', zh: '稀有' },
    legendary: { en: 'Legendary', fa: 'افسانه‌ای', ar: 'أسطوري', zh: '传说' },
  };

  const UI = {
    locked: { en: 'Not yet', fa: 'هنوز نه', ar: 'ليس بعد', zh: '还没有' },
    earned: { en: 'Earned', fa: 'به دست آمده', ar: 'محقَّق', zh: '已获得' },
    notEnoughData: { en: 'Not enough data yet', fa: 'هنوز داده کافی نیست', ar: 'لا توجد بيانات كافية بعد', zh: '数据还不够' },
    privateNote: {
      en: 'Private — never shown to friends.',
      fa: 'خصوصی — هرگز به دوستان نشان داده نمی‌شود.',
      ar: 'خاص — لا يُعرض على الأصدقاء أبداً.',
      zh: '私密——绝不会展示给好友。',
    },
    nextStep: { en: 'Next step', fa: 'قدم بعدی', ar: 'الخطوة التالية', zh: '下一步' },
  };

  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : (t && t.en) || '');

  /* Fills {a} and {b} from the badge's own numbers. Which number is
     which depends on the badge's shape, so the mapping lives here rather
     than being guessed per string:
       - a pattern badge counts days, so {a}=days seen, {b}=window
       - an improvement badge reports a percentage, so {a}=change_pct
       - everything else falls back to progress/target */
  function fill(text, badge) {
    const p = badge.params || {};
    let a = p.change_pct != null ? Math.abs(p.change_pct)
      : p.days != null ? p.days
      : p.delta != null ? p.delta
      : p.best != null ? p.best
      : p.latest != null ? p.latest
      : p.spread != null ? p.spread
      : badge.progress;
    let b = p.window != null ? p.window
      : p.previous_best != null ? p.previous_best
      : badge.target;
    const num = (v) => (v == null ? '' : `<span dir="ltr" style="unicode-bidi:isolate">${
      Math.abs(v % 1) > 0.001 ? v : Math.round(v)
    }</span>`);
    return String(text).replace('{a}', num(a)).replace('{b}', num(b));
  }

  const api = {
    has: (id) => Object.prototype.hasOwnProperty.call(BADGES, id),
    name: (id) => (BADGES[id] ? pick(BADGES[id].name) : id),
    description: (badge) => {
      const entry = BADGES[badge.id];
      if (!entry) return '';
      const raw = pick(entry.desc);
      // A badge the user's history cannot answer yet has no numbers to
      // put in the sentence. Rendering it anyway produced "sleep is up
      // %" - a claim with the number missing, which reads as a bug and
      // is worse than saying plainly that there is not enough data. The
      // name and icon still carry the discovery.
      if (badge.evaluable === false && /\{[ab]\}/.test(raw)) return pick(UI.notEnoughData);
      return fill(raw, badge);
    },
    nextStep: (badge) => {
      const entry = BADGES[badge.id];
      return entry && entry.next ? pick(entry.next) : '';
    },
    tierLabel: (tier) => (TIERS[tier] ? pick(TIERS[tier]) : ''),
    ui: (key) => (UI[key] ? pick(UI[key]) : ''),
    /* B-3/B-5: what the guide says out loud when a badge is clicked -
       what it is, how it was earned, and what comes next. Composed from
       this registry rather than from 63 hand-written essays, so a new
       badge is spoken correctly the moment it is added. */
    speech: (badge) => {
      const parts = [api.name(badge.id) + '.', api.description(badge)];
      if (!badge.evaluable) parts.push(api.ui('notEnoughData') + '.');
      else parts.push((badge.earned ? api.ui('earned') : api.ui('locked')) + '.');
      const next = api.nextStep(badge);
      if (next) parts.push(api.ui('nextStep') + ': ' + next);
      if (badge.private) parts.push(api.ui('privateNote'));
      return parts.filter(Boolean).join(' ').replace(/<[^>]+>/g, '');
    },
    ids: () => Object.keys(BADGES),
  };

  window.DWBadgeText = api;
})();
