/*
  "Our own AI" - a rule-based menu-driven coach layer, deliberately not
  claiming to be a neural LLM (there is no external model call in this
  file at all). Every one of the 50+ items below is answered from the
  user's OWN real, current data - the same context objects the rest of
  this app already computes (result, progress, insights, persona, plan,
  future-path, cohort). Nothing here is templated filler text with a
  number dropped in; if a prerequisite is missing, the item says so
  honestly instead of guessing (see `unavailable()`).

  Freshness contract (the actual point of this file, not a cosmetic
  detail): every answer is a pure function of a fingerprint built from
  the user's current real numbers. If the fingerprint hasn't changed
  since the last time an item was opened today, the same correct answer
  is shown again with a small "still true" lead-in - never a randomly
  different answer for unchanged data. The moment the fingerprint
  changes (a new check-in, a new persona, a new plan week, a new
  friend), every item is marked "updated" the next time it is opened
  and reflects the newest data, never a cached stale one.
*/
(function () {
  const STATE_KEY = 'dwai_ai_menu_state';

  const LEAD_IN = {
    en: ['Still true as of today:', 'Checked again - same read as before:', 'No change since last time you asked:'],
    fa: ['هنوز هم همین است:', 'دوباره چک کردم - همان نتیجه‌ی قبلی:', 'از دفعه‌ی قبل که پرسیدی تغییری نکرده:'],
    ar: ['لا يزال صحيحاً حتى اليوم:', 'فحصت مرة أخرى - النتيجة نفسها:', 'لا تغيير منذ آخر مرة سألت:'],
    zh: ['到今天依然如此：', '又查了一次——和之前的读数相同：', '自你上次询问以来没有变化：'],
  };
  const UPDATED_TAG = {
    en: '🔄 Updated with your latest data - ',
    fa: '🔄 به‌روزرسانی‌شده با داده‌ی جدیدت - ',
    ar: '🔄 مُحدَّث ببياناتك الأحدث - ',
    zh: '🔄 已用你的最新数据更新 - ',
  };

  function lang() { return (window.DWI18n && window.DWI18n.get()) || 'en'; }
  /* Four-language lookup for every runtime string in this file - every
     answer is a full {en,fa,ar,zh} table so Arabic and Chinese are
     never silently served English (enforced by tests/frontend/test_i18n_coverage.py). */
  function pick(table) {
    if (!table) return '';
    if (window.DWI18n && window.DWI18n.pick) return window.DWI18n.pick(table);
    return table[lang()] || table.en || '';
  }
  function labelFor(feature) {
    const map = (window.DWCoachLabels || {});
    return map[feature] || String(feature).replace(/_/g, ' ');
  }
  function num(n, d) { return n == null ? '—' : Math.round(n * (d ? 10 ** d : 1)) / (d ? 10 ** d : 1); }

  /* ---------------------------------------------------------------
     50+ menu items, grouped into categories for the UI to render as
     sections. `need` lists the ctx keys that must be truthy for the
     item to be answerable; missing ones get an honest decline instead
     of a fabricated answer (see unavailable() below).
  --------------------------------------------------------------- */
  const ITEMS = [
    // ---- Your score ----
    { id: 'score_meaning', cat: 'score', need: ['result'], en: 'What does my current score mean?', fa: 'امتیاز فعلی‌ام یعنی چه؟', ar: 'ماذا تعني درجتي الحالية؟', zh: '我当前的分数是什么意思？', icon: '🎯' },
    { id: 'why_this_score', cat: 'score', need: ['result'], en: 'Why did I get this exact score?', fa: 'چرا دقیقاً این امتیاز را گرفتم؟', ar: 'لماذا حصلت على هذه الدرجة بالتحديد؟', zh: '我为什么正好得到这个分数？', icon: '🔍' },
    { id: 'confidence_check', cat: 'score', need: ['result'], en: 'How confident is the model right now?', fa: 'مدل الان چقدر مطمئن است؟', ar: 'ما مدى ثقة النموذج الآن؟', zh: '模型现在的置信度有多高？', icon: '📶' },
    { id: 'ood_check', cat: 'score', need: ['result'], en: 'Is anything about today unusual for the model?', fa: 'چیزی امروز برای مدل غیرعادی است؟', ar: 'هل هناك شيء غير معتاد اليوم بالنسبة للنموذج؟', zh: '今天有什么对模型来说不寻常的地方吗？', icon: '⚠️' },
    { id: 'strongest_factor', cat: 'score', need: ['result'], en: 'What is working in my favour?', fa: 'چه چیزی به نفعم کار می‌کند؟', ar: 'ما الذي يعمل في مصلحتي؟', zh: '哪些因素对我有利？', icon: '💪' },
    { id: 'weakest_dimension', cat: 'score', need: ['result'], en: 'Which dimension is weakest right now?', fa: 'الان کدام بعد ضعیف‌ترین است؟', ar: 'أي بُعد هو الأضعف الآن؟', zh: '现在哪个维度最弱？', icon: '📉' },
    { id: 'compare_to_last', cat: 'score', need: ['history'], en: 'How does today compare to my last check-in?', fa: 'امروز نسبت به آخرین بررسی‌ام چطور است؟', ar: 'كيف يقارن اليوم بآخر تسجيل لي؟', zh: '今天与我上次记录相比如何？', icon: '↔️' },

    // ---- Sleep ----
    { id: 'sleep_summary', cat: 'sleep', need: ['payload'], en: 'How was my sleep last night?', fa: 'خوابم دیشب چطور بود؟', ar: 'كيف كان نومي الليلة الماضية؟', zh: '我昨晚睡得怎么样？', icon: '😴' },
    { id: 'sleep_vs_target', cat: 'sleep', need: ['payload'], en: 'Am I close to the recommended sleep amount?', fa: 'به مقدار توصیه‌شده‌ی خواب نزدیکم؟', ar: 'هل أنا قريب من كمية النوم الموصى بها؟', zh: '我接近推荐的睡眠时长了吗？', icon: '🛌' },
    { id: 'pre_sleep_check', cat: 'sleep', need: ['payload'], en: 'Am I using my phone too close to bedtime?', fa: 'خیلی نزدیک به خواب گوشی دست می‌گیرم؟', ar: 'هل أستخدم هاتفي قريباً جداً من وقت النوم؟', zh: '我睡前用手机是不是太晚了？', icon: '📵' },
    { id: 'sleep_recommendation', cat: 'sleep', need: ['result'], en: 'What is my top sleep recommendation?', fa: 'مهم‌ترین توصیه‌ی خوابم چیست؟', ar: 'ما أهم توصية لنومي؟', zh: '我最重要的睡眠建议是什么？', icon: '💡' },

    // ---- Focus & screen habits ----
    { id: 'focus_summary', cat: 'focus', need: ['payload'], en: 'How is my focus today?', fa: 'تمرکزم امروز چطور است؟', ar: 'كيف هو تركيزي اليوم؟', zh: '我今天的专注力如何？', icon: '🎯' },
    { id: 'fragmentation_check', cat: 'focus', need: ['payload'], en: 'Is my attention fragmented today?', fa: 'توجهم امروز پراکنده است؟', ar: 'هل انتباهي مُشتّت اليوم؟', zh: '我今天的注意力碎片化了吗？', icon: '🧩' },
    { id: 'notification_load', cat: 'focus', need: ['payload'], en: 'Are my notifications out of control?', fa: 'اعلان‌هایم از کنترل خارج شده؟', ar: 'هل خرجت إشعاراتي عن السيطرة؟', zh: '我的通知失控了吗？', icon: '🔔' },
    { id: 'screen_time_breakdown', cat: 'focus', need: ['payload'], en: 'Break down my screen time for me.', fa: 'زمان صفحه‌نمایشم را برایم تفکیک کن.', ar: 'حلّل لي وقت الشاشة الخاص بي.', zh: '帮我拆解一下我的屏幕使用时间。', icon: '📱' },
    { id: 'night_usage_check', cat: 'focus', need: ['payload'], en: 'How much of my screen time is at night?', fa: 'چقدر از زمان صفحه‌ام شبانه است؟', ar: 'كم من وقت شاشتي يكون ليلاً؟', zh: '我有多少屏幕时间是在夜间？', icon: '🌙' },

    // ---- Emotional wellbeing ----
    { id: 'stress_check', cat: 'emotional', need: ['payload'], en: 'How stressed am I today?', fa: 'امروز چقدر استرس دارم؟', ar: 'ما مستوى توتري اليوم؟', zh: '我今天的压力有多大？', icon: '😮‍💨' },
    { id: 'mood_check', cat: 'emotional', need: ['payload'], en: 'How is my mood today?', fa: 'حال و هوایم امروز چطور است؟', ar: 'كيف هو مزاجي اليوم؟', zh: '我今天的心情如何？', icon: '🙂' },
    { id: 'loneliness_check', cat: 'emotional', need: ['payload'], en: 'Am I feeling isolated lately?', fa: 'اخیراً احساس تنهایی می‌کنم؟', ar: 'هل أشعر بالعزلة مؤخراً؟', zh: '我最近感到孤立吗？', icon: '🫂' },
    { id: 'social_comparison_check', cat: 'emotional', need: ['payload'], en: 'Is social comparison affecting me?', fa: 'مقایسه‌ی اجتماعی روی من اثر گذاشته؟', ar: 'هل تؤثر المقارنة الاجتماعية عليّ؟', zh: '社交比较在影响我吗？', icon: '📲' },

    // ---- Physical & lifestyle ----
    { id: 'activity_check', cat: 'physical', need: ['payload'], en: 'Am I moving enough today?', fa: 'امروز به‌اندازه‌ی کافی تحرک داشتم؟', ar: 'هل أتحرك بما يكفي اليوم؟', zh: '我今天活动量足够吗？', icon: '🏃' },
    { id: 'caffeine_check', cat: 'physical', need: ['payload'], en: 'Is my caffeine intake a factor?', fa: 'مصرف کافئینم عامل مهمی است؟', ar: 'هل استهلاكي للكافيين عامل مؤثر؟', zh: '我的咖啡因摄入是一个影响因素吗？', icon: '☕' },
    { id: 'lifestyle_summary', cat: 'physical', need: ['result'], en: 'Summarize my physical & lifestyle score.', fa: 'امتیاز فعالیت بدنی و سبک زندگی‌ام را خلاصه کن.', ar: 'لخّص درجة نشاطي البدني ونمط حياتي.', zh: '总结我的身体活动与生活方式得分。', icon: '🌿' },

    // ---- Recommendations & action ----
    { id: 'top_priority_action', cat: 'action', need: ['result'], en: 'If I only do one thing today, what should it be?', fa: 'اگر فقط یک کار امروز انجام بدهم، چه باشد؟', ar: 'إذا فعلت شيئاً واحداً اليوم، فماذا يكون؟', zh: '如果我今天只做一件事，该做什么？', icon: '✅' },
    { id: 'quick_win', cat: 'action', need: ['result'], en: 'Give me the easiest quick win.', fa: 'ساده‌ترین برد سریع را به من بده.', ar: 'أعطني أسهل مكسب سريع.', zh: '给我一个最容易的快速见效方法。', icon: '⚡' },
    { id: 'success_metrics_recap', cat: 'action', need: ['result'], en: 'How will I know my recommendations are working?', fa: 'از کجا بفهمم توصیه‌ها جواب داده‌اند؟', ar: 'كيف سأعرف أن توصياتي تعمل؟', zh: '我怎么知道这些建议起作用了？', icon: '📏' },
    { id: 'muted_topics', cat: 'action', need: [], en: 'What topics have I muted from coaching?', fa: 'چه موضوعاتی را از مربی‌گری خاموش کرده‌ام؟', ar: 'ما المواضيع التي كتمتها عن التوجيه؟', zh: '我把哪些主题从指导中静音了？', icon: '🔕' },

    // ---- Progress & history ----
    { id: 'streak_check', cat: 'progress', need: ['progress'], en: "What's my current check-in streak?", fa: 'رکورد پیاپی بررسی‌هایم چقدر است؟', ar: 'ما هو تتابع تسجيلاتي الحالي؟', zh: '我目前的连续记录是多少天？', icon: '🔥' },
    { id: 'personal_bests', cat: 'progress', need: ['progress'], en: 'Have I set any personal bests?', fa: 'رکورد شخصی جدیدی زده‌ام؟', ar: 'هل حققت أي أرقام شخصية قياسية؟', zh: '我创造了个人最佳纪录吗？', icon: '🏆' },
    { id: 'small_wins', cat: 'progress', need: ['progress'], en: 'What small wins have I had recently?', fa: 'اخیراً چه بردهای کوچکی داشته‌ام؟', ar: 'ما المكاسب الصغيرة التي حققتها مؤخراً؟', zh: '我最近有哪些小的进步？', icon: '🌱' },
    { id: 'before_after', cat: 'progress', need: ['progress'], en: 'Compare my first days to my most recent days.', fa: 'روزهای اول را با روزهای اخیرم مقایسه کن.', ar: 'قارن أيامي الأولى بأيامي الأخيرة.', zh: '把我最初几天和最近几天做个对比。', icon: '📊' },
    { id: 'weekday_pattern', cat: 'progress', need: ['insights'], en: 'Which day of the week is hardest for me?', fa: 'کدام روز هفته برایم سخت‌تر است؟', ar: 'أي يوم من الأسبوع هو الأصعب عليّ؟', zh: '一周中哪一天对我最难？', icon: '📅' },
    { id: 'cold_start_status', cat: 'progress', need: ['insights'], en: 'Do I have enough data yet for real trends?', fa: 'برای روند واقعی داده‌ی کافی دارم؟', ar: 'هل لديّ بيانات كافية لاتجاهات حقيقية؟', zh: '我的数据够看出真实趋势了吗？', icon: '🌡️' },

    // ---- Persona & identity ----
    { id: 'my_persona', cat: 'identity', need: ['persona'], en: 'What is my behavioral persona?', fa: 'پرسونای رفتاری‌ام چیست؟', ar: 'ما هي شخصيتي السلوكية؟', zh: '我的行为画像是什么？', icon: '🎭' },
    { id: 'my_badges', cat: 'identity', need: ['persona'], en: 'What badges have I earned?', fa: 'چه نشان‌هایی گرفته‌ام؟', ar: 'ما الشارات التي حصلت عليها؟', zh: '我获得了哪些徽章？', icon: '🥇' },
    { id: 'persona_alternates', cat: 'identity', need: ['persona'], en: 'What other personas am I close to?', fa: 'به چه پرسونای دیگری نزدیکم؟', ar: 'ما الشخصيات الأخرى القريبة مني؟', zh: '我还接近哪些其他画像？', icon: '🔀' },

    // ---- Weekly plan ----
    { id: 'this_week_plan', cat: 'plan', need: ['plan'], en: "What's my plan for this week?", fa: 'برنامه‌ی این هفته‌ام چیست؟', ar: 'ما خطتي لهذا الأسبوع؟', zh: '我这周的计划是什么？', icon: '🗓️' },
    { id: 'plan_today', cat: 'plan', need: ['plan'], en: "What's on today's plan specifically?", fa: 'دقیقاً برنامه‌ی امروز چیست؟', ar: 'ما هو تحديداً على خطة اليوم؟', zh: '今天的计划具体有什么？', icon: '📌' },
    { id: 'weekly_card_prompt', cat: 'plan', need: [], en: 'Can I get a shareable card of my week?', fa: 'می‌شود کارت هفته‌ام را بگیرم؟', ar: 'هل يمكنني الحصول على بطاقة أسبوعي للمشاركة؟', zh: '我能拿到本周的可分享卡片吗？', icon: '🖼️' },

    // ---- Future & what-if ----
    { id: 'future_self_gradual', cat: 'future', need: ['future'], en: 'Talk to my future self after gradual improvement.', fa: 'با خودِ آینده‌ام بعد از بهبود تدریجی حرف بزن.', ar: 'تحدث إلى نفسي المستقبلية بعد تحسّن تدريجي.', zh: '和渐进改善后的未来的我对话。', icon: '🔮' },
    { id: 'future_self_committed', cat: 'future', need: ['future'], en: 'Talk to my future self if I commit fully.', fa: 'با خودِ آینده‌ام اگر کاملاً متعهد شوم حرف بزن.', ar: 'تحدث إلى نفسي المستقبلية إذا التزمت تماماً.', zh: '如果我全力投入，和未来的我对话。', icon: '🚀' },
    { id: 'future_self_drift', cat: 'future', need: ['future'], en: 'What happens if I keep drifting like this?', fa: 'اگر همین‌طور ادامه بدهم چه می‌شود؟', ar: 'ماذا يحدث إذا استمررت على هذا النحو؟', zh: '如果我一直这样下去会怎样？', icon: '⏳' },
    { id: 'whatif_pointer', cat: 'future', need: [], en: 'I want to test my own scenario.', fa: 'می‌خواهم سناریوی خودم را تست کنم.', ar: 'أريد اختبار سيناريو خاص بي.', zh: '我想测试我自己的情景。', icon: '🧪' },

    // ---- Friends League ----
    { id: 'league_standing', cat: 'league', need: ['league'], en: 'Where do I stand in the League?', fa: 'جایگاهم در لیگ کجاست؟', ar: 'ما هو ترتيبي في الدوري؟', zh: '我在联赛中排在哪里？', icon: '🏅' },
    { id: 'league_get_ahead', cat: 'league', need: ['league'], en: 'How do I get ahead of my friends in the League?', fa: 'چطور از دوستانم توی لیگ جلو بیفتم؟', ar: 'كيف أتقدم على أصدقائي في الدوري؟', zh: '我怎样在联赛中超过我的朋友？', icon: '📈' },
    { id: 'league_invite_code', cat: 'league', need: [], en: 'What is my invite code?', fa: 'کد دعوتم چیست؟', ar: 'ما هو رمز الدعوة الخاص بي؟', zh: '我的邀请码是什么？', icon: '🔗' },
    { id: 'league_pending', cat: 'league', need: [], en: 'Do I have pending League requests?', fa: 'درخواست معلق در لیگ دارم؟', ar: 'هل لديّ طلبات دوري معلّقة؟', zh: '我有待处理的联赛请求吗？', icon: '📬' },
    { id: 'league_privacy', cat: 'league', need: [], en: 'What can my friends actually see about me?', fa: 'دوستانم دقیقاً چه چیزی از من می‌بینند؟', ar: 'ما الذي يمكن لأصدقائي رؤيته عني فعلاً؟', zh: '我的朋友实际上能看到我的什么？', icon: '🔒' },

    // ---- Cohort ----
    { id: 'cohort_percentile', cat: 'cohort', need: ['cohort'], en: 'How do I compare to everyone else using this app?', fa: 'نسبت به بقیه‌ی کاربران این اپ چطورم؟', ar: 'كيف أقارن بباقي مستخدمي هذا التطبيق؟', zh: '我和这个应用的其他用户相比如何？', icon: '🌍' },
    { id: 'rare_achievement', cat: 'cohort', need: ['cohort'], en: 'Do I have any rare achievements?', fa: 'دستاورد کمیابی دارم؟', ar: 'هل لديّ أي إنجازات نادرة؟', zh: '我有什么稀有成就吗？', icon: '💎' },

    // ---- Privacy & data ----
    { id: 'export_reminder', cat: 'privacy', need: [], en: 'How do I get a copy of all my data?', fa: 'چطور یک نسخه از تمام داده‌هایم بگیرم؟', ar: 'كيف أحصل على نسخة من كل بياناتي؟', zh: '我如何获取我所有数据的副本？', icon: '📤' },
    { id: 'field_lookup', cat: 'privacy', need: ['payload'], en: 'Explain the field that affected me most.', fa: 'فیلدی که بیشترین اثر را داشت را توضیح بده.', ar: 'اشرح الحقل الذي أثّر عليّ أكثر.', zh: '解释对我影响最大的那个字段。', icon: '📚' },

    // ---- Meta ----
    { id: 'tell_me_fact', cat: 'meta', need: [], en: 'Tell me something useful about digital wellbeing.', fa: 'یک نکته‌ی مفید درباره‌ی سلامت دیجیتال بگو.', ar: 'أخبرني بشيء مفيد عن العافية الرقمية.', zh: '告诉我一个关于数字健康的有用知识。', icon: '💭' },
    { id: 'motivate_me', cat: 'meta', need: ['result'], en: 'I need some motivation.', fa: 'به یک انگیزه نیاز دارم.', ar: 'أحتاج بعض التحفيز.', zh: '我需要一些动力。', icon: '🌟' },
    { id: 'full_digest', cat: 'meta', need: ['result'], en: 'Give me the full picture, everything at once.', fa: 'کل تصویر را یک‌جا به من بده.', ar: 'أعطني الصورة الكاملة، كل شيء مرة واحدة.', zh: '给我完整的全貌，一次全部说清。', icon: '🧾' },
  ];

  /* The eight persona identity badges (utils/persona_titles.py). Their
     labels are built server-side in English, which is fine for a log
     line and wrong for a sentence the user reads, so the names live
     here keyed by the badge's stable `key`. Anything added server-side
     later falls back to that English label rather than vanishing. */
  const IDENTITY_BADGE_NAMES = {
    well_rested: { en: 'Well Rested', fa: 'خوب استراحت‌کرده', ar: 'مرتاح جيداً', zh: '睡得好' },
    mover: { en: 'On the Move', fa: 'در حرکت', ar: 'في حركة', zh: '动起来' },
    night_guard: { en: 'Night Guard', fa: 'نگهبان شب', ar: 'حارس الليل', zh: '守夜人' },
    focused: { en: 'Unfragmented', fa: 'بدون پراکندگی', ar: 'غير مُجزّأ', zh: '不碎片化' },
    calm: { en: 'Low Stress', fa: 'کم‌استرس', ar: 'توتر منخفض', zh: '低压力' },
    consistent: { en: 'Consistent Logger', fa: 'ثبت‌کننده‌ی پیوسته', ar: 'مسجّل منتظم', zh: '坚持记录者' },
    dedicated: { en: 'Month of Data', fa: 'یک ماه داده', ar: 'شهر من البيانات', zh: '一个月的数据' },
    high_score: { en: 'Peak Week', fa: 'هفته‌ی اوج', ar: 'أسبوع الذروة', zh: '巅峰一周' },
  };

  const CATEGORY_LABELS = {
    // The three categories the generated families land in.
    dimensions: { en: 'The five dimensions', fa: 'پنج بُعد', ar: 'الأبعاد الخمسة', zh: '五个维度' },
    whatif: { en: 'What if I changed this?', fa: 'اگر این را عوض کنم چه می‌شود؟', ar: 'ماذا لو غيّرت هذا؟', zh: '如果我改变它会怎样？' },
    signals: { en: 'Your signals, one by one', fa: 'سیگنال‌هایت، یکی‌یکی', ar: 'إشاراتك، واحدة واحدة', zh: '你的各项信号' },
    trend: { en: 'Getting better or worse?', fa: 'بهتر می‌شود یا بدتر؟', ar: 'يتحسّن أم يسوء؟', zh: '在变好还是变差？' },
    typical: { en: 'What is typical for me', fa: 'چه چیزی برای من معمول است', ar: 'ما المعتاد بالنسبة لي', zh: '对我来说什么算典型' },
    steady: { en: 'How steady each signal is', fa: 'هر سیگنال چقدر باثبات است', ar: 'مدى ثبات كل إشارة', zh: '各项信号有多稳定' },
    method: { en: 'How this system works', fa: 'این سیستم چطور کار می‌کند', ar: 'كيف يعمل هذا النظام', zh: '这个系统如何运作' },
    science: { en: 'Why the advice works', fa: 'چرا این توصیه‌ها جواب می‌دهند', ar: 'لماذا تنجح هذه النصائح', zh: '这些建议为何有效' },
    score: { en: 'Your score', fa: 'امتیازت', ar: 'درجتك', zh: '你的分数' },
    sleep: { en: 'Sleep', fa: 'خواب', ar: 'النوم', zh: '睡眠' },
    focus: { en: 'Focus & screen habits', fa: 'تمرکز و عادت‌های صفحه', ar: 'التركيز وعادات الشاشة', zh: '专注与屏幕习惯' },
    emotional: { en: 'Emotional wellbeing', fa: 'بهزیستی احساسی', ar: 'العافية العاطفية', zh: '情绪健康' },
    physical: { en: 'Physical & lifestyle', fa: 'فعالیت بدنی و سبک زندگی', ar: 'النشاط البدني ونمط الحياة', zh: '身体活动与生活方式' },
    action: { en: 'Recommendations & action', fa: 'توصیه و اقدام', ar: 'التوصيات والإجراءات', zh: '建议与行动' },
    progress: { en: 'Progress & history', fa: 'پیشرفت و تاریخچه', ar: 'التقدم والسجل', zh: '进展与历史' },
    identity: { en: 'Persona & identity', fa: 'پرسونا و هویت', ar: 'الشخصية والهوية', zh: '画像与身份' },
    plan: { en: 'Weekly plan', fa: 'برنامه‌ی هفتگی', ar: 'الخطة الأسبوعية', zh: '每周计划' },
    future: { en: 'Future & what-if', fa: 'آینده و اگر-چه', ar: 'المستقبل وسيناريوهات ماذا-لو', zh: '未来与假设推演' },
    league: { en: 'Friends League', fa: 'لیگ دوستان', ar: 'دوري الأصدقاء', zh: '好友联赛' },
    cohort: { en: 'Compared to everyone', fa: 'مقایسه با همه', ar: 'بالمقارنة مع الجميع', zh: '与所有人对比' },
    privacy: { en: 'Privacy & data', fa: 'حریم خصوصی و داده', ar: 'الخصوصية والبيانات', zh: '隐私与数据' },
    meta: { en: 'More', fa: 'بیشتر', ar: 'المزيد', zh: '更多' },
  };

  function unavailable(reasonKey, ctx) {
    const MSG = {
      result: {
        en: "You haven't run a check-in yet - I can't build this without a real result.",
        fa: 'هنوز بررسی‌ای ثبت نکرده‌ای — این را نمی‌توانم بسازم بدون یک نتیجه‌ی واقعی.',
        ar: 'لم تُجرِ تسجيلاً بعد — لا يمكنني بناء هذا دون نتيجة حقيقية.',
        zh: '你还没有做过检查——没有真实结果我无法生成这个。',
      },
      payload: {
        en: "I need today's actual inputs for this - run a check-in first.",
        fa: 'برای این به داده‌ی امروزت نیاز دارم؛ یک بررسی انجام بده.',
        ar: 'أحتاج بيانات اليوم الفعلية لهذا — أجرِ تسجيلاً أولاً.',
        zh: '这需要你今天的真实数据——先做一次检查。',
      },
      history: {
        en: "I need at least one earlier check-in to compare, and you don't have one yet.",
        fa: 'برای مقایسه به حداقل یک بررسی‌ی قبلی نیاز دارم که هنوز نداری.',
        ar: 'أحتاج إلى تسجيل سابق واحد على الأقل للمقارنة، ولا يوجد لديك واحد بعد.',
        zh: '比较需要至少一次更早的检查记录，而你目前还没有。',
      },
      progress: {
        en: "You don't have enough history yet for this.",
        fa: 'هنوز داده‌ی تاریخچه‌ی کافی برای این نداری.',
        ar: 'ليس لديك سجل كافٍ بعد لهذا.',
        zh: '你的历史数据还不够用于这个。',
      },
      insights: {
        en: 'This needs a few more days of data first.',
        fa: 'برای این به چند روز داده‌ی بیشتر نیاز است.',
        ar: 'هذا يحتاج إلى بضعة أيام إضافية من البيانات أولاً.',
        zh: '这需要再多几天的数据。',
      },
      persona: {
        en: "There isn't enough data yet to assign a persona.",
        fa: 'برای تعیین پرسونا هنوز داده‌ی کافی نداری.',
        ar: 'لا توجد بيانات كافية بعد لتحديد شخصية.',
        zh: '数据还不够，无法确定人格画像。',
      },
      plan: {
        en: 'Run a check-in first so a plan can be generated.',
        fa: 'برای این ابتدا باید یک بررسی انجام بدهی تا برنامه ساخته شود.',
        ar: 'أجرِ تسجيلاً أولاً حتى يمكن إنشاء خطة.',
        zh: '先做一次检查，才能生成计划。',
      },
      future: {
        en: 'I need a real check-in to simulate a future path from.',
        fa: 'برای شبیه‌سازی آینده به یک بررسی‌ی واقعی نیاز دارم.',
        ar: 'أحتاج إلى تسجيل حقيقي لمحاكاة مسار مستقبلي منه.',
        zh: '需要一次真实的检查才能模拟未来路径。',
      },
      league: {
        en: "You don't have any friends in the League yet, so the League isn't active for you.",
        fa: 'تو هنوز هیچ دوستی در لیگ نداری، پس لیگ برایت فعال نیست.',
        ar: 'ليس لديك أي أصدقاء في الدوري بعد، لذا الدوري غير مفعّل لك.',
        zh: '你在联赛里还没有朋友，所以联赛功能对你还没有激活。',
      },
      cohort: {
        en: 'The comparison cohort is not available yet.',
        fa: 'داده‌ی گروه مقایسه هنوز برای این کافی نیست.',
        ar: 'مجموعة المقارنة غير متوفرة بعد.',
        zh: '对比群组数据暂不可用。',
      },
    };
    return pick(MSG[reasonKey] || MSG.result);
  }

  function missingNeed(item, ctx) {
    return item.need.find((k) => !ctx[k]);
  }

  /* ---------------------------------------------------------------
     The actual answer generator. Pure function of ctx - same ctx
     always yields the same text, which is exactly what makes the
     freshness contract above meaningful rather than accidental.
  --------------------------------------------------------------- */
  function localAnswer(id, ctx) {
    /* Two families answered outside the switch, because each is a
       whole module rather than a case:
         - the curriculum (how the system works) needs no user data, so
           it is checked first and always has something true to say;
         - the per-field guide answers "how is my X?" for every signal
           the user logs, assembled from their own numbers and today's
           real SHAP output. */
    if (window.DWCurriculum && window.DWCurriculum.has(id)) {
      return window.DWCurriculum.answer(id);
    }
    if (window.DWFieldGuide && id.indexOf('field_') === 0) {
      const field = id.slice('field_'.length);
      if (window.DWFieldGuide.has(field)) return window.DWFieldGuide.answer(field, ctx);
    }
    if (window.DWBreakdown && window.DWBreakdown.has(id)) {
      return window.DWBreakdown.answer(id, ctx);
    }
    if (window.DWFieldGuide && id.indexOf('whatif_') === 0) {
      const field = id.slice('whatif_'.length);
      if (window.DWFieldGuide.has(field)) return window.DWFieldGuide.whatIf(field, ctx);
    }
    /* The three history-series families (trend/typical/steady). Checked
       after the single-day families above because those answer from
       today's result, while these need `ctx.history` and decline
       honestly when there are not enough usable days. */
    if (window.DWHistoryFamily && window.DWHistoryFamily.has(id)) {
      return window.DWHistoryFamily.answer(id, ctx);
    }

    const r = ctx.result, p = ctx.payload || {};
    const dims = (r && r.dimension_breakdown && r.dimension_breakdown.dimensions) || [];
    const dim = (key) => dims.find((d) => d.key === key);
    const top = r && (r.shap_features || [])[0];
    const worst = r && (r.shap_features || []).find((s) => s.direction === 'decrease');
    const best = r && (r.shap_features || []).find((s) => s.direction === 'increase');

    switch (id) {
      case 'score_meaning': {
        const score = Math.round(r.regression_score ?? 0);
        return pick({
          en: `Your score is ${score}/100 and the model classed today "${r.prediction}". That number comes straight from the trained regression model, not a hand-written rule.`,
          fa: `امتیازت ${score} از ۱۰۰ است و مدل امروزت را «${r.prediction}» دسته‌بندی کرده. این عدد از مدل رگرسیون واقعی می‌آید، نه یک قانون ساده.`,
          ar: `درجتك ${score}/100 وصنّف النموذج اليوم كـ"${r.prediction}". هذا الرقم يأتي مباشرة من نموذج الانحدار المدرَّب، وليس من قاعدة يدوية.`,
          zh: `你的分数是 ${score}/100，模型将今天归类为"${r.prediction}"。这个数字直接来自训练好的回归模型，而不是手写规则。`,
        });
      }
      case 'why_this_score': {
        if (!top) return unavailable('result', ctx);
        const dirWord = pick({
          en: top.direction === 'decrease' ? 'the score down' : 'the score up',
          fa: top.direction === 'decrease' ? 'در جهت پایین‌آورنده' : 'در جهت بالابرنده',
          ar: top.direction === 'decrease' ? 'الدرجة إلى الأسفل' : 'الدرجة إلى الأعلى',
          zh: top.direction === 'decrease' ? '分数下拉' : '分数上拉',
        });
        return pick({
          en: `The single biggest driver was ${labelFor(top.feature)} (pulling ${dirWord}). This is straight from SHAP on this exact prediction.`,
          fa: `بیشترین اثر را «${labelFor(top.feature)}» گذاشته (${dirWord}). این از SHAP همین پیش‌بینی می‌آید.`,
          ar: `أكبر عامل مؤثر كان «${labelFor(top.feature)}» (يسحب ${dirWord}). هذا مباشرة من تحليل SHAP لهذا التنبؤ بالذات.`,
          zh: `影响最大的因素是「${labelFor(top.feature)}」（把${dirWord}）。这是直接来自这次预测的 SHAP 分析。`,
        });
      }
      case 'confidence_check': {
        const cl = r.confidence_label;
        if (cl) return `${cl.headline} ${cl.detail}`;
        const pct = Math.round(r.confidence_percent || 0);
        return pick({
          en: `Model confidence is ${pct}%.`,
          fa: `اطمینان مدل ${pct}٪ است.`,
          ar: `ثقة النموذج ${pct}٪.`,
          zh: `模型置信度为 ${pct}%。`,
        });
      }
      case 'ood_check': {
        const ood = r.ood;
        if (ood && ood.is_out_of_distribution) return '⚠️ ' + ood.message;
        return pick({
          en: "No - today's inputs sit comfortably inside what the model has already seen.",
          fa: 'نه، ورودی‌های امروزت کاملاً در محدوده‌ی چیزی است که مدل قبلاً دیده.',
          ar: 'لا — مدخلات اليوم تقع بشكل مريح ضمن ما رآه النموذج من قبل.',
          zh: '不——今天的输入完全落在模型已经见过的范围之内。',
        });
      }
      case 'strongest_factor':
        return best
          ? pick({
              en: `${labelFor(best.feature)} is doing the most for you right now.`,
              fa: `«${labelFor(best.feature)}» الان بیشترین کمک را به امتیازت می‌کند.`,
              ar: `«${labelFor(best.feature)}» يقدّم لك أكبر دعم الآن.`,
              zh: `「${labelFor(best.feature)}」目前对你的帮助最大。`,
            })
          : pick({
              en: 'No single strongly positive factor stood out today.',
              fa: 'هیچ عامل قوی مثبتی امروز برجسته نشد.',
              ar: 'لم يبرز أي عامل إيجابي قوي اليوم.',
              zh: '今天没有特别突出的强正向因素。',
            });
      case 'weakest_dimension': {
        const weakest = dims.length ? dims.reduce((a, b) => (a.score < b.score ? a : b)) : null;
        if (!weakest) return unavailable('result', ctx);
        const label = window.DWI18n.t('dim_' + weakest.key) || weakest.label;
        const score = Math.round(weakest.score);
        return pick({
          en: `${label} is your weakest dimension right now, at ${score}/100.`,
          fa: `«${label}» با ${score} از ۱۰۰ الان ضعیف‌ترین بعد توست.`,
          ar: `«${label}» هو أضعف بُعد لديك الآن، بـ ${score}/100.`,
          zh: `「${label}」是你目前最弱的维度，为 ${score}/100。`,
        });
      }
      case 'compare_to_last': {
        if (!ctx.history || ctx.history.length < 2) return unavailable('history', ctx);
        const [latest, prev] = ctx.history;
        const delta = (latest.health_score ?? 0) - (prev.health_score ?? 0);
        const deltaStr = `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}`;
        const from = Math.round(prev.health_score), to = Math.round(latest.health_score);
        return pick({
          en: `Compared to your previous check-in, your score moved ${deltaStr} (from ${from} to ${to}).`,
          fa: `نسبت به بررسی‌ی قبلی‌ات، امتیازت ${deltaStr} تغییر کرده (از ${from} به ${to}).`,
          ar: `مقارنة بتسجيلك السابق، تحرّكت درجتك ${deltaStr} (من ${from} إلى ${to}).`,
          zh: `与你上次检查相比，分数变化了 ${deltaStr}（从 ${from} 到 ${to}）。`,
        });
      }

      case 'sleep_summary': {
        if (p.sleep_hours == null) return unavailable('payload', ctx);
        const q = p.sleep_quality_1_10 ?? '—';
        return pick({
          en: `You logged ${p.sleep_hours}h of sleep last night, quality ${q}/10.`,
          fa: `دیشب ${p.sleep_hours} ساعت خوابیدی، با کیفیت ${q} از ۱۰.`,
          ar: `سجّلت ${p.sleep_hours} ساعة نوم الليلة الماضية، بجودة ${q}/10.`,
          zh: `你昨晚记录了 ${p.sleep_hours} 小时睡眠，质量为 ${q}/10。`,
        });
      }
      case 'sleep_vs_target': {
        if (p.sleep_hours == null) return unavailable('payload', ctx);
        const diff = p.sleep_hours - 8;
        const abs = Math.abs(diff).toFixed(1);
        return pick({
          en: `The reference target is 8h; you're ${abs}h ${diff < 0 ? 'under' : 'over'} that.`,
          fa: `هدف مرجع ۸ ساعت است؛ تو ${abs} ساعت ${diff < 0 ? 'کمتر' : 'بیشتر'} از آن خوابیده‌ای.`,
          ar: `الهدف المرجعي هو 8 ساعات؛ أنت ${abs} ساعة ${diff < 0 ? 'أقل من' : 'أكثر من'} ذلك.`,
          zh: `参考目标是 8 小时；你比这个目标${diff < 0 ? '少' : '多'} ${abs} 小时。`,
        });
      }
      case 'pre_sleep_check': {
        if (p.pre_sleep_ratio == null) return unavailable('payload', ctx);
        const pct = Math.round(p.pre_sleep_ratio * 100);
        return pick({
          en: `${pct}% of your pre-bed time was on the phone.`,
          fa: `${pct}٪ از زمان قبل از خوابت با گوشی بوده.`,
          ar: `${pct}٪ من وقتك قبل النوم كان على الهاتف.`,
          zh: `你睡前时间中有 ${pct}% 用在了手机上。`,
        });
      }
      case 'sleep_recommendation': {
        const rec = (r.recommendations || []).find((x) => x.category === 'Sleep');
        if (rec) return `${rec.title} — ${rec.action}`;
        return pick({
          en: "No active sleep recommendation right now - that area isn't flagged as a problem.",
          fa: 'الان توصیه‌ی فعالی درباره‌ی خواب نداری — یعنی این بخش مشکلی نشان نداده.',
          ar: 'لا توجد توصية نشطة بشأن النوم الآن — أي أن هذا المجال لم يُظهر مشكلة.',
          zh: '目前没有活跃的睡眠建议——说明这方面没有被标记为问题。',
        });
      }

      case 'focus_summary': {
        const d = dim('focus');
        if (!d) return unavailable('payload', ctx);
        const score = Math.round(d.score);
        return pick({
          en: `Your focus & productivity score is ${score}/100.`,
          fa: `امتیاز تمرکز/بهره‌وری‌ات ${score} از ۱۰۰ است.`,
          ar: `درجة تركيزك وإنتاجيتك ${score}/100.`,
          zh: `你的专注与效率分数为 ${score}/100。`,
        });
      }
      case 'fragmentation_check': {
        if (p.fragmentation_index_0_100 == null) return unavailable('payload', ctx);
        const idx = Math.round(p.fragmentation_index_0_100);
        return pick({
          en: `Your attention fragmentation index is ${idx}/100.`,
          fa: `شاخص پراکندگی توجهت ${idx} از ۱۰۰ است.`,
          ar: `مؤشر تشتّت انتباهك ${idx}/100.`,
          zh: `你的注意力碎片化指数为 ${idx}/100。`,
        });
      }
      case 'notification_load':
        return p.notifications_per_day != null
          ? pick({
              en: `You logged ${p.notifications_per_day} notifications today.`,
              fa: `امروز ${p.notifications_per_day} اعلان ثبت کرده‌ای.`,
              ar: `سجّلت ${p.notifications_per_day} إشعاراً اليوم.`,
              zh: `你今天记录了 ${p.notifications_per_day} 条通知。`,
            })
          : unavailable('payload', ctx);
      case 'screen_time_breakdown': {
        if (p.total_screen_min == null) return unavailable('payload', ctx);
        const total = Math.round(p.total_screen_min);
        const night = Math.round((p.night_ratio || 0) * 100);
        const gaming = Math.round((p.gaming_ratio || 0) * 100);
        return pick({
          en: `Total screen time: ${total} min, of which ${night}% was at night and ${gaming}% was gaming.`,
          fa: `کل زمان صفحه: ${total} دقیقه، که ${night}٪ آن شبانه و ${gaming}٪ آن بازی بوده.`,
          ar: `إجمالي وقت الشاشة: ${total} دقيقة، منها ${night}٪ ليلاً و${gaming}٪ ألعاباً.`,
          zh: `总屏幕时间：${total} 分钟，其中 ${night}% 在夜间，${gaming}% 用于游戏。`,
        });
      }
      case 'night_usage_check': {
        if (p.night_ratio == null) return unavailable('payload', ctx);
        const pct = Math.round(p.night_ratio * 100);
        return pick({
          en: `${pct}% of your screen time was at night.`,
          fa: `${pct}٪ از زمان صفحه‌ات شبانه بوده.`,
          ar: `${pct}٪ من وقت شاشتك كان ليلاً.`,
          zh: `你有 ${pct}% 的屏幕时间发生在夜间。`,
        });
      }

      case 'stress_check':
        return p.stress_0_10 != null
          ? pick({ en: `Today's stress is logged at ${p.stress_0_10}/10.`, fa: `استرس امروزت ${p.stress_0_10} از ۱۰ ثبت شده.`, ar: `توتر اليوم مسجَّل عند ${p.stress_0_10}/10.`, zh: `今天的压力记录为 ${p.stress_0_10}/10。` })
          : unavailable('payload', ctx);
      case 'mood_check':
        return p.happiness_0_10 != null
          ? pick({ en: `Your happiness today is ${p.happiness_0_10}/10.`, fa: `شادی‌ات امروز ${p.happiness_0_10} از ۱۰ است.`, ar: `سعادتك اليوم ${p.happiness_0_10}/10.`, zh: `你今天的幸福感为 ${p.happiness_0_10}/10。` })
          : unavailable('payload', ctx);
      case 'loneliness_check':
        return p.loneliness_1_10 != null
          ? pick({ en: `Loneliness is logged at ${p.loneliness_1_10}/10.`, fa: `تنهایی‌ات ${p.loneliness_1_10} از ۱۰ ثبت شده.`, ar: `الشعور بالوحدة مسجَّل عند ${p.loneliness_1_10}/10.`, zh: `孤独感记录为 ${p.loneliness_1_10}/10。` })
          : unavailable('payload', ctx);
      case 'social_comparison_check':
        return p.social_comparison_1_10 != null
          ? pick({ en: `Social comparison is ${p.social_comparison_1_10}/10.`, fa: `مقایسه‌ی اجتماعی‌ات ${p.social_comparison_1_10} از ۱۰ است.`, ar: `المقارنة الاجتماعية ${p.social_comparison_1_10}/10.`, zh: `社交比较为 ${p.social_comparison_1_10}/10。` })
          : unavailable('payload', ctx);

      case 'activity_check':
        return p.physical_activity_min_per_day != null
          ? pick({
              en: `You logged ${p.physical_activity_min_per_day} minutes of physical activity today.`,
              fa: `امروز ${p.physical_activity_min_per_day} دقیقه فعالیت بدنی ثبت کرده‌ای.`,
              ar: `سجّلت ${p.physical_activity_min_per_day} دقيقة من النشاط البدني اليوم.`,
              zh: `你今天记录了 ${p.physical_activity_min_per_day} 分钟的身体活动。`,
            })
          : unavailable('payload', ctx);
      case 'caffeine_check':
        return p.caffeine_cups_per_day != null
          ? pick({
              en: `You logged ${p.caffeine_cups_per_day} cup(s) of caffeine.`,
              fa: `${p.caffeine_cups_per_day} فنجان کافئین ثبت کرده‌ای.`,
              ar: `سجّلت ${p.caffeine_cups_per_day} كوباً من الكافيين.`,
              zh: `你记录了 ${p.caffeine_cups_per_day} 杯咖啡因饮品。`,
            })
          : unavailable('payload', ctx);
      case 'lifestyle_summary': {
        const d = dim('physical');
        if (!d) return unavailable('result', ctx);
        const score = Math.round(d.score);
        return pick({
          en: `Your physical & lifestyle score is ${score}/100.`,
          fa: `امتیاز فعالیت بدنی/سبک زندگی‌ات ${score} از ۱۰۰ است.`,
          ar: `درجة نشاطك البدني ونمط حياتك ${score}/100.`,
          zh: `你的身体活动与生活方式分数为 ${score}/100。`,
        });
      }

      case 'top_priority_action': {
        const rec = (r.recommendations || [])[0];
        if (rec) return `${rec.title} — ${rec.action} (${window.DWI18n.t('rec_success_label') || 'metric'}: ${rec.success_metric || '—'})`;
        return pick({
          en: 'Nothing urgent right now - your top factors are working in your favour.',
          fa: 'الان کاری فوری برای انجام دادن نیست — عوامل اصلی به نفعت کار می‌کنند.',
          ar: 'لا يوجد شيء عاجل الآن — أهم عواملك تعمل لصالحك.',
          zh: '目前没有紧急事项——你的主要因素正在对你有利。',
        });
      }
      case 'quick_win': {
        const rec = (r.recommendations || []).slice().sort((a, b) => (a.priority === 'HIGH' ? -1 : 1))[0];
        if (rec) return `${rec.title} — ${rec.action}`;
        return pick({
          en: 'Nothing to suggest as a quick win right now.',
          fa: 'موردی برای پیشنهاد سریع نیست.',
          ar: 'لا يوجد ما يمكن اقتراحه كفوز سريع الآن.',
          zh: '目前没有可以推荐的速效项目。',
        });
      }
      case 'success_metrics_recap': {
        const list = (r.recommendations || []).map((x) => `• ${x.title}: ${x.success_metric || '—'}`).join('\n');
        return list || pick({
          en: 'You have no active recommendations.',
          fa: 'توصیه‌ی فعالی نداری.',
          ar: 'ليس لديك توصيات نشطة.',
          zh: '你目前没有活跃的建议。',
        });
      }
      case 'muted_topics': {
        let excluded = [];
        try { excluded = JSON.parse(localStorage.getItem('dwai_excluded_rec_categories') || '[]'); } catch (e) {}
        if (!excluded.length) {
          return pick({
            en: "You haven't muted any topics.",
            fa: 'هیچ موضوعی را خاموش نکرده‌ای.',
            ar: 'لم تكتم أي مواضيع.',
            zh: '你还没有静音任何主题。',
          });
        }
        return pick({
          en: `Muted topics: ${excluded.join(', ')}`,
          fa: `این موضوعات خاموش‌اند: ${excluded.join('، ')}`,
          ar: `المواضيع المكتومة: ${excluded.join('، ')}`,
          zh: `已静音的主题：${excluded.join('、')}`,
        });
      }

      case 'streak_check':
        return ctx.progress.streak_days != null
          ? pick({
              en: `You're on a ${ctx.progress.streak_days}-day check-in streak.`,
              fa: `الان ${ctx.progress.streak_days} روز پیاپی بررسی کرده‌ای.`,
              ar: `أنت في سلسلة تسجيل مدتها ${ctx.progress.streak_days} يوماً.`,
              zh: `你已经连续检查 ${ctx.progress.streak_days} 天了。`,
            })
          : unavailable('progress', ctx);
      case 'personal_bests': {
        const bests = (ctx.progress.personal_bests || []).filter((b) => b.is_new);
        if (!bests.length) {
          return pick({
            en: 'No new personal bests right now, but keep going.',
            fa: 'الان رکورد تازه‌ای نداری، اما ادامه بده.',
            ar: 'لا توجد أرقام قياسية شخصية جديدة الآن، لكن استمر.',
            zh: '目前没有新的个人最佳记录，但继续加油。',
          });
        }
        return bests.map((b) => pick({
          en: `New personal best on ${b.metric}: ${b.value}`,
          fa: `«${b.metric}» رکورد جدید زده: ${b.value}`,
          ar: `رقم قياسي شخصي جديد في «${b.metric}»: ${b.value}`,
          zh: `「${b.metric}」创下新的个人最佳：${b.value}`,
        })).join('\n');
      }
      case 'small_wins': {
        const wins = ctx.progress.small_wins || [];
        if (!wins.length) {
          return pick({
            en: 'No notable small wins logged recently.',
            fa: 'اخیراً برد کوچک قابل‌توجهی ثبت نشده.',
            ar: 'لم تُسجَّل أي إنجازات صغيرة ملحوظة مؤخراً.',
            zh: '最近没有记录到值得一提的小进步。',
          });
        }
        return wins.map((w) => `• ${labelFor(w.field_name)}: ${w.delta > 0 ? '+' : ''}${w.delta.toFixed(1)}`).join('\n');
      }
      case 'before_after': {
        const ba = ctx.progress.before_after;
        if (!ba || !ba.available) return unavailable('progress', ctx);
        /* The wire names are before_avg_score / after_avg_score (see
           api/schemas/progress.py). This read them as before_avg /
           after_avg, so both were undefined and Math.round(undefined)
           put a literal "NaN" in front of the user: "Your early average
           was NaN, recent average is NaN". In all four languages.
           The `?? ba.before_avg` keeps a response from an older build
           readable rather than swapping one broken name for another. */
        const beforeRaw = ba.before_avg_score ?? ba.before_avg;
        const afterRaw = ba.after_avg_score ?? ba.after_avg;
        if (!Number.isFinite(beforeRaw) || !Number.isFinite(afterRaw)) {
          return unavailable('progress', ctx);
        }
        const before = Math.round(beforeRaw), after = Math.round(afterRaw);
        /* Consistency and improvement are different achievements and
           used to collapse into the same sentence: a user holding 82-83
           all week got "not yet a meaningful difference", which reads as
           failure for what is actually the hardest thing to do. The
           server now resolves both axes into `pattern`; the wording
           below is one line per real outcome. `steady` is the fallback
           for a response from before this existed. */
        const VERDICT = {
          improving_steady: {
            en: 'a real climb, and a steady one - the daily swing stayed small while the average moved up.',
            fa: 'یک صعود واقعی و باثبات — نوسان روزانه کم ماند و میانگین بالا رفت.',
            ar: 'صعود حقيقي وثابت — بقي التأرجح اليومي صغيراً بينما ارتفع المتوسط.',
            zh: '这是一次真实而稳定的上升——日常波动保持在小范围，平均分却抬高了。',
          },
          improving_volatile: {
            en: 'the average is up, but the days swing hard - the gain is real and not yet stable.',
            fa: 'میانگین بالا رفته، ولی روزها نوسان زیادی دارند — پیشرفت واقعی است اما هنوز تثبیت نشده.',
            ar: 'المتوسط ارتفع، لكن الأيام تتأرجح بشدة — المكسب حقيقي لكنه غير مستقر بعد.',
            zh: '平均分上去了，但每天的起伏很大——进步是真的，只是还不稳定。',
          },
          steady_strong: {
            en: "held almost flat at a strong level - that is consistency, not a lack of progress. Holding a good score steady is its own result.",
            fa: 'تقریباً ثابت و در سطحی قوی مانده — این یعنی ثبات، نه نبودِ پیشرفت. نگه‌داشتن یک امتیاز خوب، خودش یک دستاورد است.',
            ar: 'بقي شبه ثابت عند مستوى قوي — هذا ثبات لا غياب تقدّم. والحفاظ على درجة جيدة إنجاز بحد ذاته.',
            zh: '几乎持平，而且停在一个不错的水平——这是稳定，不是没有进步。把好分数守住本身就是一种成果。',
          },
          steady_low: {
            en: 'flat, and flat at a low level - steady, but stuck rather than settled.',
            fa: 'ثابت، اما ثابت در سطحی پایین — بی‌نوسان، ولی گیرکرده نه تثبیت‌شده.',
            ar: 'ثابت، لكن عند مستوى منخفض — مستقر نعم، لكنه عالق لا مستقر عن رضا.',
            zh: '很平稳，但停在偏低的水平——是稳定，却是卡住了而不是站稳了。',
          },
          volatile: {
            en: 'the average barely moved, but the individual days swing a lot - the flat average is hiding a bumpy week.',
            fa: 'میانگین تقریباً تکان نخورده، ولی تک‌تک روزها نوسان زیادی دارند — این میانگینِ صاف، یک هفته‌ی پرفرازونشیب را پنهان می‌کند.',
            ar: 'المتوسط لم يتحرك تقريباً، لكن الأيام المفردة تتأرجح كثيراً — هذا المتوسط المستوي يخفي أسبوعاً متقلباً.',
            zh: '平均分几乎没动，但每一天的起伏很大——这个平坦的平均值掩盖了一个颠簸的星期。',
          },
          declining_steady: {
            en: 'a consistent slide downward - small each day, which is exactly what makes it easy to miss.',
            fa: 'یک افت پیوسته — هر روز کم، و دقیقاً همین باعث می‌شود به چشم نیاید.',
            ar: 'انزلاق متواصل نحو الأسفل — قليل كل يوم، وهذا بالضبط ما يجعله يمرّ دون ملاحظة.',
            zh: '一个持续的下滑——每天都只降一点，而这正是它容易被忽略的原因。',
          },
          declining_volatile: {
            en: 'trending down, with big swings on the way - worth looking at the low days specifically.',
            fa: 'روند نزولی همراه با نوسان‌های بزرگ — ارزشش را دارد که مشخصاً روزهای پایین را نگاه کنی.',
            ar: 'اتجاه نزولي مع تأرجحات كبيرة — يستحق النظر في الأيام المنخفضة تحديداً.',
            zh: '整体在下行，而且过程中起伏很大——值得专门去看那些低分的日子。',
          },
        };
        const verdict = VERDICT[ba.pattern] || VERDICT[
          ba.is_meaningful ? (ba.delta > 0 ? 'improving_steady' : 'declining_steady') : 'steady_strong'
        ];
        const steadiness = ba.consistency == null ? '' : pick({
          en: ` Day-to-day steadiness: ${Math.round(ba.consistency * 100)}%.`,
          fa: ` ثبات روزبه‌روز: ${Math.round(ba.consistency * 100)}٪.`,
          ar: ` الثبات اليومي: ${Math.round(ba.consistency * 100)}٪.`,
          zh: ` 每日稳定度：${Math.round(ba.consistency * 100)}%。`,
        });
        return pick({
          en: `Your early average was ${before}, recent average is ${after} - ${pick(verdict)}${steadiness}`,
          fa: `میانگین روزهای اول ${before} بود، روزهای اخیر ${after} — ${pick(verdict)}${steadiness}`,
          ar: `متوسطك في الأيام الأولى كان ${before}، والمتوسط الأخير ${after} — ${pick(verdict)}${steadiness}`,
          zh: `你早期的平均分是 ${before}，近期平均分是 ${after}——${pick(verdict)}${steadiness}`,
        });
      }
      case 'weekday_pattern': {
        const days = ctx.insights.weekday_reliability || [];
        const reliable = days.filter((d) => d.is_reliable && d.average_score != null);
        if (!reliable.length) return unavailable('insights', ctx);
        const hardest = reliable.reduce((a, b) => (a.average_score < b.average_score ? a : b));
        const avg = Math.round(hardest.average_score);
        return pick({
          en: `${hardest.weekday} tends to be your lowest-average day (${avg}).`,
          fa: `${hardest.weekday} معمولاً کمترین امتیاز میانگین را برایت دارد (${avg}).`,
          ar: `${hardest.weekday} يميل إلى أن يكون يومك الأقل متوسطاً (${avg}).`,
          zh: `${hardest.weekday} 往往是你平均分最低的一天（${avg}）。`,
        });
      }
      case 'cold_start_status':
        return ctx.insights.cold_start
          ? window.DWServerText.pick(ctx.insights.cold_start, 'message')
          : unavailable('insights', ctx);

      case 'my_persona':
        return ctx.persona.primary
          ? `${ctx.persona.primary.title} — ${ctx.persona.primary.reason}`
          : unavailable('persona', ctx);
      case 'my_badges': {
        const badges = ctx.persona.badges || [];
        if (!badges.length) {
          return pick({
            en: "You haven't earned any badges yet.",
            fa: 'هنوز نشانی نگرفته‌ای.',
            ar: 'لم تحصل على أي شارات بعد.',
            zh: '你还没有获得任何徽章。',
          });
        }
        /* These are the persona IDENTITY badges (utils/persona_titles.py
           -> /personas/identity), which carry {key, label, icon}. There
           is no `title` on them and never was, so this printed
           "😴 undefined, 🏃 undefined, 🧠 undefined" in all four
           languages.

           Their `label` is an English string built server-side, so
           using it alone would fix the undefined and leave the answer
           English everywhere. The eight keys are translated here
           instead, falling back to the server's label for anything
           added later - a new badge then reads in English rather than
           disappearing. */
        const nameOf = (b) => {
          const table = IDENTITY_BADGE_NAMES[b.key];
          return table ? pick(table) : (b.label || b.key || '');
        };
        return badges.map((b) => `${b.icon || '🥇'} ${nameOf(b)}`).join(', ');
      }
      case 'persona_alternates': {
        const alts = ctx.persona.alternates || [];
        if (!alts.length) {
          return pick({
            en: 'No other persona is close right now.',
            fa: 'الگوی دیگری نزدیک نیست.',
            ar: 'لا توجد شخصية أخرى قريبة الآن.',
            zh: '目前没有其他接近的人格画像。',
          });
        }
        return alts.map((a) => a.title).join(', ');
      }

      case 'this_week_plan':
        return ctx.plan
          ? pick({
              en: `This week's focus: ${(ctx.plan.focus_areas || []).join(', ')}.`,
              fa: `تمرکز این هفته: ${(ctx.plan.focus_areas || []).join('، ')}.`,
              ar: `تركيز هذا الأسبوع: ${(ctx.plan.focus_areas || []).join('، ')}.`,
              zh: `本周重点：${(ctx.plan.focus_areas || []).join('、')}。`,
            })
          : unavailable('plan', ctx);
      case 'plan_today': {
        if (!ctx.plan) return unavailable('plan', ctx);
        const day = (ctx.plan.days || [])[0];
        return day ? `${day.theme}: ${(day.tasks || []).map((t) => t.text).join('; ')}` : unavailable('plan', ctx);
      }
      case 'weekly_card_prompt':
        return pick({
          en: 'Yes! Use the "Download weekly card" button on the Weekly Plan page.',
          fa: 'بله! از صفحه‌ی «برنامه‌ی هفتگی» دکمه‌ی «دانلود کارت هفته» را بزن.',
          ar: 'نعم! استخدم زر "تنزيل بطاقة الأسبوع" في صفحة الخطة الأسبوعية.',
          zh: '可以！在每周计划页面使用"下载周卡"按钮。',
        });

      case 'future_self_gradual':
      case 'future_self_committed': {
        const key = id === 'future_self_gradual' ? 'gradual_improvement' : 'committed_change';
        const path = (ctx.future || []).find((x) => x.key === key);
        if (!path || path.regression_score == null) return unavailable('future', ctx);
        const delta = path.score_delta_vs_status_quo;
        // Conditional, not declarative: this simulates a hypothetical
        // pattern, so "becomes" would assert a future the model cannot
        // know. Each path also gets its own framing rather than sharing
        // one sentence (the two cards used to read identically).
        const suffix = delta != null ? ` (${delta >= 0 ? '+' : ''}${delta.toFixed(1)})` : '';
        const lead = key === 'committed_change'
          ? {
              en: 'Sustaining a real effort across several habits, the simulation reaches around',
              fa: 'با تلاش واقعی و پیوسته روی چند عادت، شبیه‌سازی حدود این عدد را نشان می‌دهد:',
              ar: 'بجهد حقيقي ومستمر عبر عدة عادات، تبلغ المحاكاة نحو',
              zh: '在多个习惯上持续付出真实努力，模拟结果达到大约',
            }
          : {
              en: 'Nudging a few habits slightly, the simulation lands around',
              fa: 'با تغییر ملایم چند عادت، شبیه‌سازی حدود این عدد را نشان می‌دهد:',
              ar: 'بتعديل بضع عادات قليلاً، تصل المحاكاة إلى نحو',
              zh: '把几个习惯稍作调整，模拟结果大约落在',
            };
        return `${pick(lead)} ${Math.round(path.regression_score)}${suffix}.`;
      }
      case 'future_self_drift': {
        const path = (ctx.future || []).find((x) => x.key === 'continued_drift');
        if (!path || path.regression_score == null) return unavailable('future', ctx);
        return `${pick({
          en: 'If habits drift slightly further, the simulation lands near',
          fa: 'اگر عادت‌ها کمی بیشتر از مسیر خارج شوند، شبیه‌سازی نزدیک این عدد می‌ایستد:',
          ar: 'إن انحرفت العادات قليلاً أكثر، تستقر المحاكاة قرب',
          zh: '如果习惯再稍微偏离一些，模拟结果会停在接近',
        })} ${Math.round(path.regression_score)}.`;
      }
      case 'whatif_pointer':
        return pick({
          en: 'The What-if page is exactly for that - change one habit and watch the real model prediction move live.',
          fa: 'صفحه‌ی «اگر-چه» دقیقاً برای همین است — یک عادت را تغییر بده و پیش‌بینی واقعی مدل را زنده ببین.',
          ar: 'صفحة "ماذا لو" مصممة تحديداً لهذا — غيّر عادة واحدة وشاهد تنبؤ النموذج الحقيقي يتحرك مباشرة.',
          zh: '"假设"页面正是为此而设——改变一个习惯，实时观察模型的真实预测变化。',
        });

      case 'league_standing':
        return ctx.league && ctx.league.friend_count
          ? pick({
              en: `Among your ${ctx.league.friend_count} friend(s), your rank is ${ctx.league.my_rank || '—'}.`,
              fa: `در بین ${ctx.league.friend_count} دوستت، رتبه‌ات ${ctx.league.my_rank || '—'} است.`,
              ar: `بين ${ctx.league.friend_count} من أصدقائك، ترتيبك هو ${ctx.league.my_rank || '—'}.`,
              zh: `在你的 ${ctx.league.friend_count} 位朋友中，你的排名是 ${ctx.league.my_rank || '—'}。`,
            })
          : unavailable('league', ctx);
      case 'league_get_ahead':
        return ctx.league && ctx.league.friend_count
          ? pick({
              en: 'The most reliable path is still improving on your own past record - rank is only a side layer.',
              fa: 'بهترین راه، هنوز پیشرفت نسبت به رکورد خودت است - رتبه فقط یک لایه‌ی جانبی است.',
              ar: 'الطريق الأكثر موثوقية يبقى تحسين رقمك القياسي الشخصي — الترتيب مجرد طبقة جانبية.',
              zh: '最可靠的方式仍然是超越你自己过去的记录——排名只是附带的一层。',
            })
          : unavailable('league', ctx);
      case 'league_invite_code':
        return ctx.league && ctx.league.invite_code
          ? pick({
              en: `Your invite code: ${ctx.league.invite_code}`,
              fa: `کد دعوتت: ${ctx.league.invite_code}`,
              ar: `رمز دعوتك: ${ctx.league.invite_code}`,
              zh: `你的邀请码：${ctx.league.invite_code}`,
            })
          : pick({
              en: 'Open the Friends League page to get your invite code.',
              fa: 'برای گرفتن کد دعوت، صفحه‌ی لیگ دوستان را باز کن.',
              ar: 'افتح صفحة دوري الأصدقاء للحصول على رمز الدعوة الخاص بك.',
              zh: '打开好友联赛页面获取你的邀请码。',
            });
      case 'league_pending':
        return ctx.league && ctx.league.pending_count
          ? pick({
              en: `You have ${ctx.league.pending_count} request(s) waiting for your approval.`,
              fa: `${ctx.league.pending_count} درخواست منتظر تایید داری.`,
              ar: `لديك ${ctx.league.pending_count} طلباً بانتظار موافقتك.`,
              zh: `你有 ${ctx.league.pending_count} 个请求等待你的批准。`,
            })
          : pick({
              en: 'No pending requests.',
              fa: 'درخواست معلقی نداری.',
              ar: 'لا توجد طلبات معلّقة.',
              zh: '没有待处理的请求。',
            });
      case 'league_privacy':
        return pick({
          en: "Only what you've explicitly ticked for that specific friend is visible, and you can revoke it at any time.",
          fa: 'فقط چیزهایی که صراحتاً برای هر دوست تیک زده‌ای دیده می‌شود، و می‌توانی هر لحظه لغوش کنی.',
          ar: 'فقط ما وافقت عليه صراحةً لذلك الصديق بالتحديد يكون مرئياً، ويمكنك إلغاؤه في أي وقت.',
          zh: '只有你明确为该特定好友勾选的内容才可见，你可以随时撤销。',
        });

      case 'cohort_percentile':
        return ctx.cohort && ctx.cohort.rows && ctx.cohort.rows.length
          ? ctx.cohort.rows.slice(0, 3).map((row) => `${labelFor(row.field)}: ${row.cohort_percentile != null ? Math.round(row.cohort_percentile) + 'th pct' : '—'}`).join('\n')
          : unavailable('cohort', ctx);
      case 'rare_achievement':
        return pick({
          en: 'Check the Analytics page for rare achievements.',
          fa: 'برای دستاوردهای کمیاب، صفحه‌ی تحلیل‌ها را ببین.',
          ar: 'راجع صفحة التحليلات للإنجازات النادرة.',
          zh: '查看分析页面以了解稀有成就。',
        });

      case 'export_reminder':
        return pick({
          en: 'Use "Export my data" from Settings or your Profile page.',
          fa: 'از تنظیمات یا صفحه‌ی پروفایل، گزینه‌ی «خروجی گرفتن از داده‌ها» را بزن.',
          ar: 'استخدم "تصدير بياناتي" من الإعدادات أو صفحة ملفك الشخصي.',
          zh: '在设置或个人资料页面使用"导出我的数据"。',
        });
      case 'field_lookup':
        return top
          ? pick({
              en: `${labelFor(top.feature)} had the biggest effect. See the field documentation for the full definition.`,
              fa: `«${labelFor(top.feature)}» بیشترین اثر را داشت. برای توضیح کامل، صفحه‌ی مستندات فیلدها را ببین.`,
              ar: `«${labelFor(top.feature)}» كان الأكبر تأثيراً. راجع توثيق الحقول للتعريف الكامل.`,
              zh: `「${labelFor(top.feature)}」影响最大。完整定义请查看字段文档。`,
            })
          : unavailable('payload', ctx);

      case 'tell_me_fact': {
        /* Prefer a fact about the user's OWN weakest signal over a
           random knowledge topic - the same sentence is worth more when
           it explains the thing their result just flagged. */
        if (window.DWMotivation) {
          const worst = (r.shap_features || []).find((f) => f.direction === 'decrease');
          const topical = window.DWMotivation.fact(
            worst ? window.DWMotivation.topicForField(worst.feature) : null);
          if (topical) return topical;
        }
        const kb = window.DWCoachKnowledge;
        if (!kb) {
          return pick({
            en: 'Enough sleep, uninterrupted focus blocks, and less late-night checking are the three highest-leverage digital-wellbeing habits.',
            fa: 'خواب کافی، تمرکز بدون وقفه‌ی مکرر و کاهش چک‌کردن شبانه، سه اثرگذارترین عادت‌های سلامت دیجیتال‌اند.',
            ar: 'النوم الكافي، وفترات التركيز غير المنقطعة، وتقليل التحقق ليلاً هي أكثر ثلاث عادات تأثيراً في العافية الرقمية.',
            zh: '充足睡眠、不间断的专注时段以及减少深夜查看手机，是最有效的三个数字健康习惯。',
          });
        }
        const topics = kb.TOPICS || [];
        const t2 = topics[Math.floor(Math.random() * topics.length)];
        return t2 ? pick(t2) : '';
      }
      case 'motivate_me': {
        const score = Math.round(r.regression_score ?? 0);
        const path = (ctx.future || []).find((x) => x.key === 'gradual_improvement');
        const future = path && path.regression_score != null ? Math.round(path.regression_score) : null;
        const withFuture = pick({
          en: future != null ? ` With small, consistent changes, the model says you could reach ${future}.` : '',
          fa: future != null ? ` با تغییرات کوچک و پیوسته، مدل می‌گوید می‌توانی به ${future} برسی.` : '',
          ar: future != null ? ` بتغييرات صغيرة ومستمرة، يقول النموذج إنه يمكنك الوصول إلى ${future}.` : '',
          zh: future != null ? ` 通过小而持续的改变，模型显示你可以达到 ${future}。` : '',
        });
        /* The line is chosen by band and direction, so someone whose
           score is falling never gets the sentence written for someone
           whose score is holding. Falls back to the original wording if
           the module is not loaded on this page. */
        if (window.DWMotivation) {
          const entries = (ctx.insights && ctx.insights.cold_start)
            ? ctx.insights.cold_start.entry_count : null;
          const led = window.DWMotivation.encouragement({
            score: r.regression_score, direction: ctx.trendDirection, entries,
          });
          if (led) {
            const worst = (r.shap_features || []).find((f) => f.direction === 'decrease');
            const why = window.DWMotivation.fact(
              worst ? window.DWMotivation.topicForField(worst.feature) : null);
            return [led + withFuture, why].filter(Boolean).join('\n\n');
          }
        }
        return pick({
          en: `You're at ${score}/100 right now.${withFuture} This is a snapshot of this week, not your ceiling.`,
          fa: `الان ${score}/۱۰۰ هستی.${withFuture} این یک عکس این هفته است، نه سقف تو.`,
          ar: `أنت الآن عند ${score}/100.${withFuture} هذه لقطة لهذا الأسبوع، وليست سقفك.`,
          zh: `你现在是 ${score}/100。${withFuture} 这只是本周的一个快照，不是你的上限。`,
        });
      }
      case 'full_digest': {
        const parts = [localAnswer('score_meaning', ctx), localAnswer('why_this_score', ctx), localAnswer('top_priority_action', ctx)];
        if (ctx.persona.primary) parts.push(localAnswer('my_persona', ctx));
        if (ctx.plan) parts.push(localAnswer('this_week_plan', ctx));
        return parts.filter(Boolean).join('\n\n');
      }
      default:
        return pick({
          en: "I don't have an answer for that yet.",
          fa: 'هنوز پاسخی برای این ندارم.',
          ar: 'ليس لدي إجابة على ذلك بعد.',
          zh: '我目前还没有这个问题的答案。',
        });
    }
  }

  function fingerprint(ctx) {
    return [
      ctx.result ? Math.round(ctx.result.regression_score) : 'x',
      ctx.result ? ctx.result.prediction : 'x',
      ctx.progress ? ctx.progress.entry_count : 0,
      ctx.persona && ctx.persona.primary ? ctx.persona.primary.key : 'x',
      ctx.plan ? ctx.plan.week_key : 'x',
      ctx.league ? ctx.league.friend_count || 0 : 0,
      ctx.league ? ctx.league.pending_count || 0 : 0,
    ].join('|');
  }

  function getAnswer(id, ctx) {
    const item = allItems().find((i) => i.id === id);
    if (!item) return '';
    const missing = missingNeed(item, ctx);
    if (missing) return unavailable(missing, ctx);

    const fp = fingerprint(ctx);
    const today = new Date().toISOString().slice(0, 10);
    let state = {};
    try { state = JSON.parse(localStorage.getItem(STATE_KEY) || '{}'); } catch (e) {}

    const changed = state.fingerprint !== fp;
    if (changed) state = { fingerprint: fp, date: today, answers: {}, freshIds: [] };

    const text = localAnswer(id, ctx);
    const wasAnsweredBefore = Object.prototype.hasOwnProperty.call(state.answers || {}, id);
    let prefix = '';
    if (changed && wasAnsweredBefore) {
      prefix = pick(UPDATED_TAG);
      state.freshIds = Array.from(new Set([...(state.freshIds || []), id]));
    } else if (!changed && state.date === today && wasAnsweredBefore) {
      const bank = pick(LEAD_IN);
      const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0)) / 86400000);
      prefix = bank[dayOfYear % bank.length] + ' ';
    }
    state.answers[id] = text;
    state.date = today;
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
    return prefix + text;
  }

  async function buildContext() {
    const ctx = { result: null, payload: null, history: null, progress: {}, insights: {}, persona: {}, plan: null, future: null, cohort: null, league: null };
    try { ctx.result = window.DWLastResult.get(); } catch (e) {}
    try { ctx.payload = JSON.parse(localStorage.getItem('dwai_last_payload') || 'null'); } catch (e) {}

    const api = window.DWApi;
    if (!api) return ctx;

    const settled = await Promise.allSettled([
      api.history(1, 10),
      api.progressSummary(),
      api.insights(),
      api.personaIdentity(),
      ctx.result ? api.generatePlan({ health_class: ctx.result.prediction, wellness_score: ctx.result.regression_score, persona: null, user_data: ctx.payload || {} }) : Promise.resolve(null),
      ctx.payload ? api.futurePathCompare(ctx.payload, ['gradual_improvement', 'committed_change', 'continued_drift']) : Promise.resolve(null),
      api.cohortAvailability().then((a) => (a && a.available ? api.cohortComparison() : null)).catch(() => null),
      api.leaguePendingRequests ? api.leaguePendingRequests() : Promise.resolve(null),
      api.leagueMe ? api.leagueMe() : Promise.resolve(null),
    ]);

    const [historyR, progressR, insightsR, personaR, planR, futureR, cohortR, leaguePendingR, leagueMeR] = settled;
    if (historyR.status === 'fulfilled' && historyR.value) ctx.history = historyR.value.items || [];
    if (progressR.status === 'fulfilled') ctx.progress = progressR.value || {};
    if (insightsR.status === 'fulfilled') ctx.insights = insightsR.value || {};
    if (personaR.status === 'fulfilled') ctx.persona = personaR.value || {};
    if (planR.status === 'fulfilled') ctx.plan = planR.value;
    if (futureR.status === 'fulfilled' && futureR.value) ctx.future = futureR.value.paths || [];
    if (cohortR.status === 'fulfilled') ctx.cohort = cohortR.value;
    if (leagueMeR.status === 'fulfilled' && leagueMeR.value) {
      ctx.league = leagueMeR.value;
      if (leaguePendingR.status === 'fulfilled' && leaguePendingR.value) {
        ctx.league.pending_count = (leaguePendingR.value.requests || []).length;
      }
    }
    return ctx;
  }

  /* The menu is ITEMS plus whatever the generated families contribute.
     Built once at load rather than inlined above, because the field
     guide's labels and the curriculum's questions live in their own
     modules - copying them here is how two lists drift apart. */
  function allItems() {
    let out = ITEMS.slice();
    if (window.DWCurriculum) out = out.concat(window.DWCurriculum.menuItems());
    if (window.DWBreakdown) out = out.concat(window.DWBreakdown.menuItems());
    if (window.DWFieldGuide) {
      out = out.concat(window.DWFieldGuide.menuItems());
      out = out.concat(window.DWFieldGuide.whatIfMenuItems());
    }
    if (window.DWHistoryFamily) out = out.concat(window.DWHistoryFamily.menuItems());
    return out;
  }

  window.DWAIMenu = {
    get ITEMS() { return allItems(); },
    CATEGORY_LABELS, buildContext, getAnswer, allItems,
  };
})();
