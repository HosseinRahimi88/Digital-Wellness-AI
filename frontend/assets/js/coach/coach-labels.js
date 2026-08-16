/*
  window.DWCoachLabels - the feature-name -> human label table that
  coach-chat.js, ai-menu.js, future-letter.js, insight-cards.js and
  games.js have all called since they were written, but that was never
  actually defined anywhere in the codebase. Every one of those five
  call sites read `window.DWCoachLabels[fieldName]`, got `undefined`
  back every time, and silently fell back to the raw field name with
  underscores turned into spaces - "sleep_hours" instead of "Sleep
  Duration" - in every language, including fa/ar/zh where the raw
  English field name is not even readable as a word.

  The main result page has the SAME underlying gap through a different
  path: its SHAP bars and recommendation panels read
  `state.featureSchemaMap[name].label` (app.js), which comes straight
  from core/feature_schema.py's `label=` field - real text, but English
  only, with no language variants at all. Both paths are fixed here:
  this file's labels are consulted first (translated, all four
  languages); `state.featureSchemaMap[name].label` remains the fallback
  for a field this table has not caught up with yet, which is at least
  readable rather than a raw snake_case name.

  Source of truth for which field names exist and what they mean:
  core/feature_schema.py's `name=`/`label=` pairs (53 fields, the
  model's actual input schema) - every key below matches one exactly,
  checked by tests/coach/test_coach_labels.py so a schema change that adds or
  renames a field is caught here instead of silently falling back.

  API: all five existing call sites use direct bracket access -
  `window.DWCoachLabels[fieldName]` - expecting an already-localized
  string. A Proxy keeps that exact shape (so none of those five files
  need to change) while resolving to the CURRENT UI language on every
  read, so a language switch is reflected immediately with no reload.
*/
(function () {
  const LABELS = {
    /* The wellness score itself. NOT a model input - it is what the
       regressor predicts - so it is absent from core/feature_schema.py
       and was absent here too. That was fine until the cohort table
       started listing it beside the ten inputs, at which point a
       Persian reader got a row labelled "health score 0 100" in raw
       English, because the fallback prints the field name. Kept out of
       the schema-parity test's input list for the same reason it is
       not an input. */
    health_score_0_100: { en: 'Wellness score', fa: 'امتیاز سلامت', ar: 'درجة العافية', zh: '健康分数' },

    age: { en: 'Age', fa: 'سن', ar: 'العمر', zh: '年龄' },
    gender: { en: 'Gender', fa: 'جنسیت', ar: 'الجنس', zh: '性别' },
    occupation_group: { en: 'Occupation', fa: 'شغل', ar: 'المهنة', zh: '职业' },
    region_group: { en: 'Region', fa: 'منطقه', ar: 'المنطقة', zh: '地区' },
    education_group: { en: 'Education level', fa: 'سطح تحصیلات', ar: 'المستوى التعليمي', zh: '教育程度' },
    device_category: { en: 'Primary device', fa: 'دستگاه اصلی', ar: 'الجهاز الأساسي', zh: '主要设备' },
    primary_platform: { en: 'Primary platform', fa: 'پلتفرم اصلی', ar: 'المنصة الأساسية', zh: '主要平台' },
    purpose_group: { en: 'Main purpose of use', fa: 'هدف اصلی استفاده', ar: 'الغرض الرئيسي من الاستخدام', zh: '主要使用目的' },
    is_content_creator: { en: 'Content creator', fa: 'تولیدکننده‌ی محتوا', ar: 'صانع محتوى', zh: '是否是内容创作者' },
    uses_screen_time_limits: { en: 'Uses screen-time limits', fa: 'استفاده از محدودیت زمان صفحه', ar: 'يستخدم حدود وقت الشاشة', zh: '使用屏幕时间限制' },
    day_index: { en: 'Tracking day number', fa: 'شماره‌ی روز ثبت', ar: 'رقم يوم التتبع', zh: '记录天数序号' },
    day_of_week: { en: 'Day of the week', fa: 'روز هفته', ar: 'يوم الأسبوع', zh: '星期几' },
    is_weekend: { en: 'Weekend', fa: 'آخر هفته', ar: 'نهاية الأسبوع', zh: '是否周末' },
    total_screen_min: { en: 'Total screen time', fa: 'مجموع زمان صفحه', ar: 'إجمالي وقت الشاشة', zh: '总屏幕时间' },
    screen_ewma_baseline: { en: 'Personal screen-time baseline', fa: 'خط پایه‌ی شخصیِ زمان صفحه', ar: 'خط الأساس الشخصي لوقت الشاشة', zh: '个人屏幕时间基线' },
    screen_vs_baseline_pct: { en: 'Screen time vs. your baseline', fa: 'زمان صفحه نسبت به خط پایه‌ات', ar: 'وقت الشاشة مقابل خط أساسك', zh: '屏幕时间相对基线的比例' },
    social_min: { en: 'Social media time', fa: 'زمان شبکه‌های اجتماعی', ar: 'وقت وسائل التواصل الاجتماعي', zh: '社交媒体时间' },
    gaming_min: { en: 'Gaming time', fa: 'زمان بازی', ar: 'وقت الألعاب', zh: '游戏时间' },
    work_study_min: { en: 'Work/study screen time', fa: 'زمان صفحه برای کار/درس', ar: 'وقت الشاشة للعمل/الدراسة', zh: '工作/学习屏幕时间' },
    other_min: { en: 'Other screen time', fa: 'زمان صفحه‌ی دیگر', ar: 'وقت شاشة آخر', zh: '其他屏幕时间' },
    social_ratio: { en: 'Social media share of screen time', fa: 'سهم شبکه‌های اجتماعی از زمان صفحه', ar: 'حصة وسائل التواصل من وقت الشاشة', zh: '社交媒体占屏幕时间比例' },
    gaming_ratio: { en: 'Gaming share of screen time', fa: 'سهم بازی از زمان صفحه', ar: 'حصة الألعاب من وقت الشاشة', zh: '游戏占屏幕时间比例' },
    work_study_ratio: { en: 'Work/study share of screen time', fa: 'سهم کار/درس از زمان صفحه', ar: 'حصة العمل/الدراسة من وقت الشاشة', zh: '工作/学习占屏幕时间比例' },
    other_ratio: { en: 'Other share of screen time', fa: 'سهم دیگر از زمان صفحه', ar: 'حصة أخرى من وقت الشاشة', zh: '其他占屏幕时间比例' },
    video_min: { en: 'Video/entertainment time', fa: 'زمان ویدیو/سرگرمی', ar: 'وقت الفيديو/الترفيه', zh: '视频/娱乐时间' },
    night_screen_min: { en: 'Night-time screen use', fa: 'استفاده‌ی شبانه از صفحه', ar: 'استخدام الشاشة الليلي', zh: '夜间屏幕使用' },
    night_ratio: { en: 'Night share of screen time', fa: 'سهم شب از زمان صفحه', ar: 'حصة الليل من وقت الشاشة', zh: '夜间占屏幕时间比例' },
    pre_sleep_screen_min: { en: 'Screen use before sleep', fa: 'استفاده از صفحه قبل از خواب', ar: 'استخدام الشاشة قبل النوم', zh: '睡前屏幕使用' },
    pre_sleep_ratio: { en: 'Pre-sleep share of screen time', fa: 'سهم پیش از خواب از زمان صفحه', ar: 'حصة ما قبل النوم من وقت الشاشة', zh: '睡前占屏幕时间比例' },
    notifications_per_day: { en: 'Notifications per day', fa: 'اعلان در روز', ar: 'الإشعارات في اليوم', zh: '每日通知数' },
    pickups_per_day: { en: 'Phone pickups per day', fa: 'برداشتن گوشی در روز', ar: 'مرات التقاط الهاتف في اليوم', zh: '每日拿起手机次数' },
    app_opens_per_day: { en: 'App opens per day', fa: 'باز کردن اپ در روز', ar: 'مرات فتح التطبيقات في اليوم', zh: '每日打开应用次数' },
    notification_density: { en: 'Notification density', fa: 'تراکم اعلان‌ها', ar: 'كثافة الإشعارات', zh: '通知密度' },
    pickup_density: { en: 'Pickup density', fa: 'تراکم برداشتن گوشی', ar: 'كثافة التقاط الهاتف', zh: '拿起手机密度' },
    app_open_density: { en: 'App-open density', fa: 'تراکم باز کردن اپ', ar: 'كثافة فتح التطبيقات', zh: '打开应用密度' },
    fragmentation_index_0_100: { en: 'Usage fragmentation', fa: 'پراکندگی استفاده', ar: 'تشتت الاستخدام', zh: '使用碎片化程度' },
    sleep_hours: { en: 'Sleep duration', fa: 'مدت خواب', ar: 'مدة النوم', zh: '睡眠时长' },
    // An output, not an input, but it is stored per day like the tracked
    // inputs and the history-series menu families name it out loud - so
    // it needs a label here or those questions read "health score" in
    // every language. Matches services/identity/report_i18n.py FIELD_LABELS.
    health_score: { en: 'Wellness score', fa: 'امتیاز سلامت', ar: 'درجة العافية', zh: '健康分数' },
    sleep_quality_1_10: { en: 'Sleep quality', fa: 'کیفیت خواب', ar: 'جودة النوم', zh: '睡眠质量' },
    stress_0_10: { en: 'Stress level', fa: 'سطح استرس', ar: 'مستوى التوتر', zh: '压力水平' },
    mental_fatigue_0_10: { en: 'Mental fatigue', fa: 'خستگی ذهنی', ar: 'الإرهاق الذهني', zh: '精神疲劳' },
    anxiety_0_27: { en: 'Anxiety', fa: 'اضطراب', ar: 'القلق', zh: '焦虑' },
    low_mood_0_27: { en: 'Low mood', fa: 'حال‌وهوای پایین', ar: 'المزاج المنخفض', zh: '情绪低落' },
    happiness_0_10: { en: 'Happiness', fa: 'شادی', ar: 'السعادة', zh: '幸福感' },
    loneliness_1_10: { en: 'Loneliness', fa: 'تنهایی', ar: 'الشعور بالوحدة', zh: '孤独感' },
    self_esteem_1_10: { en: 'Self-esteem', fa: 'عزت نفس', ar: 'تقدير الذات', zh: '自尊' },
    fomo_1_10: { en: 'Fear of missing out', fa: 'ترس از جا ماندن (FOMO)', ar: 'الخوف من الفوات', zh: '错失恐惧（FOMO）' },
    social_comparison_1_10: { en: 'Social comparison', fa: 'مقایسه‌ی اجتماعی', ar: 'المقارنة الاجتماعية', zh: '社交比较' },
    life_satisfaction_1_10: { en: 'Life satisfaction', fa: 'رضایت از زندگی', ar: 'الرضا عن الحياة', zh: '生活满意度' },
    focus_0_100: { en: 'Focus', fa: 'تمرکز', ar: 'التركيز', zh: '专注力' },
    productivity_0_100: { en: 'Productivity', fa: 'بهره‌وری', ar: 'الإنتاجية', zh: '生产力' },
    digital_dependence_0_100: { en: 'Digital dependence', fa: 'وابستگی دیجیتال', ar: 'الاعتماد الرقمي', zh: '数字依赖度' },
    physical_activity_min_per_day: { en: 'Physical activity', fa: 'فعالیت بدنی', ar: 'النشاط البدني', zh: '身体活动' },
    caffeine_cups_per_day: { en: 'Caffeine intake', fa: 'مصرف کافئین', ar: 'استهلاك الكافيين', zh: '咖啡因摄入量' },

    // Not model inputs, and not in FEATURE_SCHEMA. These two are asked
    // in the check-in form to DERIVE fields that are (see
    // assets/js/schema.js HELPER_ONLY_FIELDS), so the person filling
    // the form sees them exactly like any other question - and saw them
    // in English in every language until they were listed here.
    // Allowlisted in tests/coach/test_coach_labels.py's NON_SCHEMA_LABELS.
    sessions_per_day: {
      en: 'Usage sessions per day', fa: 'تعداد دفعات استفاده در روز',
      ar: 'عدد جلسات الاستخدام يومياً', zh: '每天使用次数',
    },
    first_check_after_waking_min: {
      en: 'Minutes before your first phone check after waking',
      fa: 'چند دقیقه بعد از بیدار شدن سراغ گوشی می‌روی',
      ar: 'كم دقيقة بعد الاستيقاظ حتى أول نظرة إلى الهاتف',
      zh: '醒来后多少分钟第一次看手机',
    },
  };

  const pickLang = () => (window.DWI18n && window.DWI18n.get ? window.DWI18n.get() : 'en');

  window.DWCoachLabels = new Proxy({}, {
    get(_target, prop) {
      // Escape hatch for the coverage test, which needs the full table
      // with all four languages - every real call site only ever reads
      // a field name, never this key, so it cannot collide.
      if (prop === '__raw') return LABELS;
      if (typeof prop !== 'string') return undefined;
      const entry = LABELS[prop];
      if (!entry) return undefined;
      const lang = pickLang();
      return entry[lang] || entry.en;
    },
    has(_target, prop) { return typeof prop === 'string' && prop in LABELS; },
    ownKeys() { return Reflect.ownKeys(LABELS); },
    getOwnPropertyDescriptor(_target, prop) {
      if (typeof prop === 'string' && prop in LABELS) return { enumerable: true, configurable: true, value: undefined };
      return undefined;
    },
  });
})();
