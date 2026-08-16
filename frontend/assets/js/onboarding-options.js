/*
  Mirrors config/onboarding_options.py's GOAL_OPTIONS / PURPOSE_OPTIONS /
  SCHEDULE_OPTIONS label->value maps, so both the first-time Onboarding
  view (app.html) and the editable Profile page use the exact same
  option set instead of two hand-copied lists drifting apart.
*/
(function () {
  const GOAL_OPTIONS = {
    'Build a better pre-sleep routine': 'better_sleep',
    'Reduce late-night device use': 'reduce_night_use',
    'Improve focus and reduce interruptions': 'improve_focus',
    'Check my device less frequently': 'reduce_pickups',
    'Manage notifications more intentionally': 'manage_notifications',
    'Improve work, study, and leisure balance': 'improve_balance',
    'Create more screen-free activity time': 'increase_activity',
    'Maintain my current healthy habits': 'maintain_habits',
  };
  const PURPOSE_OPTIONS = {
    'Work or career': 'work_career', 'Education or study': 'education', 'Social connection': 'social_connection',
    'Entertainment': 'entertainment', 'News or information': 'news_information', 'Content creation': 'content_creation',
    'A mixture of purposes': 'mixed', 'Other': 'other',
  };
  const SCHEDULE_OPTIONS = {
    'Standard daytime schedule': 'standard_day', 'Early shift': 'early_shift', 'Late shift': 'late_shift',
    'Rotating shifts': 'rotating_shift', 'Student or flexible schedule': 'student_flexible', 'Irregular schedule': 'irregular', 'Other': 'other',
  };

  /* The display text for each stored value, in every shipped language.
     The maps above stay the source of truth for what gets SUBMITTED -
     those values are what the backend and the model see, and they must
     never change with the interface language. This table only decides
     what the user reads.

     Without it, the goal, purpose and schedule pickers on both the
     onboarding view and the profile page were English in all four
     languages - about twenty options a Persian, Arabic or Chinese user
     had to choose between without being able to read them. */
  const OPTION_LABELS = {
    better_sleep: { en: "Build a better pre-sleep routine", fa: "ساختن یک روال بهتر پیش از خواب", ar: "بناء روتين أفضل قبل النوم", zh: "建立更好的睡前习惯" },
    reduce_night_use: { en: "Reduce late-night device use", fa: "کم کردن استفاده از دستگاه در آخر شب", ar: "تقليل استخدام الجهاز في وقت متأخر", zh: "减少深夜使用设备" },
    improve_focus: { en: "Improve focus and reduce interruptions", fa: "بهتر کردن تمرکز و کم کردن وقفه‌ها", ar: "تحسين التركيز وتقليل المقاطعات", zh: "提升专注、减少打断" },
    reduce_pickups: { en: "Check my device less frequently", fa: "کمتر سراغ دستگاهم رفتن", ar: "تفقّد جهازي بوتيرة أقل", zh: "减少查看设备的次数" },
    manage_notifications: { en: "Manage notifications more intentionally", fa: "مدیریت آگاهانه‌تر اعلان‌ها", ar: "إدارة الإشعارات بقصد أوضح", zh: "更有意识地管理通知" },
    improve_balance: { en: "Improve work, study, and leisure balance", fa: "بهتر کردن تعادل کار، تحصیل و فراغت", ar: "تحسين التوازن بين العمل والدراسة والترفيه", zh: "改善工作、学习与休闲的平衡" },
    increase_activity: { en: "Create more screen-free activity time", fa: "ساختن زمان بیشتر برای فعالیت بدون صفحه", ar: "إتاحة وقت أكبر لنشاط بلا شاشات", zh: "创造更多无屏幕的活动时间" },
    maintain_habits: { en: "Maintain my current healthy habits", fa: "حفظ عادت‌های سالم فعلی‌ام", ar: "الحفاظ على عاداتي الصحية الحالية", zh: "保持我现有的健康习惯" },
    work_career: { en: "Work or career", fa: "کار یا حرفه", ar: "العمل أو المهنة", zh: "工作或职业" },
    education: { en: "Education or study", fa: "تحصیل یا مطالعه", ar: "التعليم أو الدراسة", zh: "教育或学习" },
    social_connection: { en: "Social connection", fa: "ارتباط اجتماعی", ar: "التواصل الاجتماعي", zh: "社交联系" },
    entertainment: { en: "Entertainment", fa: "سرگرمی", ar: "الترفيه", zh: "娱乐" },
    news_information: { en: "News or information", fa: "خبر یا اطلاعات", ar: "الأخبار أو المعلومات", zh: "新闻或资讯" },
    content_creation: { en: "Content creation", fa: "تولید محتوا", ar: "صناعة المحتوى", zh: "内容创作" },
    mixed: { en: "A mixture of purposes", fa: "ترکیبی از هدف‌ها", ar: "مزيج من الأغراض", zh: "多种用途混合" },
    other: { en: "Other", fa: "سایر", ar: "أخرى", zh: "其他" },
    standard_day: { en: "Standard daytime schedule", fa: "برنامه‌ی روزانه‌ی معمول", ar: "جدول نهاري اعتيادي", zh: "常规白班作息" },
    early_shift: { en: "Early shift", fa: "شیفت صبح زود", ar: "وردية مبكرة", zh: "早班" },
    late_shift: { en: "Late shift", fa: "شیفت شب", ar: "وردية متأخرة", zh: "晚班" },
    rotating_shift: { en: "Rotating shifts", fa: "شیفت‌های چرخشی", ar: "ورديات متناوبة", zh: "轮班" },
    student_flexible: { en: "Student or flexible schedule", fa: "برنامه‌ی دانشجویی یا منعطف", ar: "جدول طالب أو مرن", zh: "学生或弹性作息" },
    irregular: { en: "Irregular schedule", fa: "برنامه‌ی نامنظم", ar: "جدول غير منتظم", zh: "不规律作息" },

    /* ----------------------------------------------------------------
       Every categorical choice in core/feature_schema.py. These are the
       questionnaire's own dropdowns and the What-if simulator's option
       lists, which until now rendered their raw English schema values in
       all four languages.

       The keys are the exact schema strings, because that is what gets
       stored, sent to the model and read back. Only the display text is
       translated - translating the value itself would break validation
       against FEATURE_SCHEMA's `value in choices` check.

       Platform names stay in Latin script in Persian and Arabic, which
       is how they are actually written there. Chinese uses the names
       those services are actually known by locally where one exists
       (RedNote is 小红书), and the Latin name where it does not.
       ---------------------------------------------------------------- */

    // gender
    Male: { en: "Male", fa: "مرد", ar: "ذكر", zh: "男" },
    Female: { en: "Female", fa: "زن", ar: "أنثى", zh: "女" },
    "Non-binary": { en: "Non-binary", fa: "دگرباش جنسیتی", ar: "غير ثنائي", zh: "非二元性别" },

    // occupation_group
    Student: { en: "Student", fa: "دانشجو یا دانش‌آموز", ar: "طالب", zh: "学生" },
    Employee: { en: "Employee", fa: "کارمند", ar: "موظف", zh: "雇员" },
    "Self-employed": { en: "Self-employed", fa: "خویش‌فرما", ar: "يعمل لحسابه", zh: "自雇" },
    Freelancer: { en: "Freelancer", fa: "فریلنسر", ar: "عمل حر", zh: "自由职业" },
    Unemployed: { en: "Unemployed", fa: "بیکار", ar: "بلا عمل", zh: "待业" },
    Retired: { en: "Retired", fa: "بازنشسته", ar: "متقاعد", zh: "退休" },
    "Caregiver/Home": { en: "Caregiver/Home", fa: "مراقبت یا خانه‌داری", ar: "رعاية أو منزل", zh: "照护或持家" },

    // region_group
    Asia: { en: "Asia", fa: "آسیا", ar: "آسيا", zh: "亚洲" },
    Europe: { en: "Europe", fa: "اروپا", ar: "أوروبا", zh: "欧洲" },
    "North America": { en: "North America", fa: "آمریکای شمالی", ar: "أمريكا الشمالية", zh: "北美洲" },
    "Latin America": { en: "Latin America", fa: "آمریکای لاتین", ar: "أمريكا اللاتينية", zh: "拉丁美洲" },
    Africa: { en: "Africa", fa: "آفریقا", ar: "أفريقيا", zh: "非洲" },
    "Middle East": { en: "Middle East", fa: "خاورمیانه", ar: "الشرق الأوسط", zh: "中东" },
    Oceania: { en: "Oceania", fa: "اقیانوسیه", ar: "أوقيانوسيا", zh: "大洋洲" },

    // education_group
    "High School or Below": { en: "High School or Below", fa: "دیپلم یا پایین‌تر", ar: "ثانوية أو أقل", zh: "高中及以下" },
    "Some College/Vocational": { en: "Some College/Vocational", fa: "کاردانی یا فنی‌وحرفه‌ای", ar: "دراسة جامعية جزئية أو مهنية", zh: "大专或职业教育" },
    Bachelor: { en: "Bachelor", fa: "کارشناسی", ar: "بكالوريوس", zh: "本科" },
    Master: { en: "Master", fa: "کارشناسی ارشد", ar: "ماجستير", zh: "硕士" },
    Doctoral: { en: "Doctoral", fa: "دکتری", ar: "دكتوراه", zh: "博士" },

    // device_category
    Smartphone: { en: "Smartphone", fa: "گوشی هوشمند", ar: "هاتف ذكي", zh: "智能手机" },
    Tablet: { en: "Tablet", fa: "تبلت", ar: "جهاز لوحي", zh: "平板" },
    Desktop: { en: "Desktop", fa: "رایانه‌ی رومیزی", ar: "حاسوب مكتبي", zh: "台式电脑" },
    "Smart TV": { en: "Smart TV", fa: "تلویزیون هوشمند", ar: "تلفاز ذكي", zh: "智能电视" },
    Wearable: { en: "Wearable", fa: "دستگاه پوشیدنی", ar: "جهاز يُرتدى", zh: "可穿戴设备" },

    // primary_platform - brand names, kept as brands
    Instagram: { en: "Instagram", fa: "اینستاگرام", ar: "إنستغرام", zh: "Instagram" },
    TikTok: { en: "TikTok", fa: "تیک‌تاک", ar: "تيك توك", zh: "TikTok" },
    YouTube: { en: "YouTube", fa: "یوتیوب", ar: "يوتيوب", zh: "YouTube" },
    Facebook: { en: "Facebook", fa: "فیسبوک", ar: "فيسبوك", zh: "脸书" },
    "X (Twitter)": { en: "X (Twitter)", fa: "ایکس (توییتر)", ar: "إكس (تويتر)", zh: "X（推特）" },
    Snapchat: { en: "Snapchat", fa: "اسنپ‌چت", ar: "سناب شات", zh: "Snapchat" },
    WhatsApp: { en: "WhatsApp", fa: "واتساپ", ar: "واتساب", zh: "WhatsApp" },
    Telegram: { en: "Telegram", fa: "تلگرام", ar: "تليغرام", zh: "Telegram" },
    Reddit: { en: "Reddit", fa: "ردیت", ar: "ريديت", zh: "Reddit" },
    LinkedIn: { en: "LinkedIn", fa: "لینکدین", ar: "لينكد إن", zh: "领英" },
    Discord: { en: "Discord", fa: "دیسکورد", ar: "ديسكورد", zh: "Discord" },
    Pinterest: { en: "Pinterest", fa: "پینترست", ar: "بنترست", zh: "Pinterest" },
    Threads: { en: "Threads", fa: "تردز", ar: "ثريدز", zh: "Threads" },
    Bluesky: { en: "Bluesky", fa: "بلواسکای", ar: "بلوسكاي", zh: "Bluesky" },
    RedNote: { en: "RedNote", fa: "ردنوت", ar: "ريد نوت", zh: "小红书" },

    // purpose_group (the schema's own spellings)
    "Work/Career": { en: "Work/Career", fa: "کار یا حرفه", ar: "العمل أو المهنة", zh: "工作或职业" },
    Education: { en: "Education", fa: "تحصیل", ar: "التعليم", zh: "教育" },
    "Social Connection": { en: "Social Connection", fa: "ارتباط اجتماعی", ar: "التواصل الاجتماعي", zh: "社交联系" },
    Entertainment: { en: "Entertainment", fa: "سرگرمی", ar: "الترفيه", zh: "娱乐" },
    "News/Information": { en: "News/Information", fa: "خبر یا اطلاعات", ar: "الأخبار أو المعلومات", zh: "新闻或资讯" },
    "Content Creation": { en: "Content Creation", fa: "تولید محتوا", ar: "صناعة المحتوى", zh: "内容创作" },
    Shopping: { en: "Shopping", fa: "خرید", ar: "التسوق", zh: "购物" },

    // day_of_week
    Monday: { en: "Monday", fa: "دوشنبه", ar: "الاثنين", zh: "星期一" },
    Tuesday: { en: "Tuesday", fa: "سه‌شنبه", ar: "الثلاثاء", zh: "星期二" },
    Wednesday: { en: "Wednesday", fa: "چهارشنبه", ar: "الأربعاء", zh: "星期三" },
    Thursday: { en: "Thursday", fa: "پنجشنبه", ar: "الخميس", zh: "星期四" },
    Friday: { en: "Friday", fa: "جمعه", ar: "الجمعة", zh: "星期五" },
    Saturday: { en: "Saturday", fa: "شنبه", ar: "السبت", zh: "星期六" },
    Sunday: { en: "Sunday", fa: "یکشنبه", ar: "الأحد", zh: "星期日" },

    // shared / fallback values
    Other: { en: "Other", fa: "سایر", ar: "أخرى", zh: "其他" },
    Unknown: { en: "Unknown", fa: "نامشخص", ar: "غير معروف", zh: "未知" },
  };

  /** Display text for a stored value; falls back to the English key so
   *  a value added later is readable rather than blank. */
  function labelFor(value, fallback) {
    const table = OPTION_LABELS[value];
    if (!table) return fallback || value || '';
    const lang = (window.DWI18n && window.DWI18n.get) ? window.DWI18n.get() : 'en';
    return table[lang] || table.en || fallback || value;
  }

  /** [{ value, label }] for a map, already translated and in order. */
  function entries(map) {
    return Object.keys(map).map((englishLabel) => ({
      value: map[englishLabel],
      label: labelFor(map[englishLabel], englishLabel),
    }));
  }

  window.DWOnboardingOptions = {
    GOAL_OPTIONS, PURPOSE_OPTIONS, SCHEDULE_OPTIONS,
    OPTION_LABELS, labelFor, entries,
  };
})();
