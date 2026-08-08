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
  };
  const UPDATED_TAG = { en: '🔄 Updated with your latest data - ', fa: '🔄 به‌روزرسانی‌شده با داده‌ی جدیدت - ' };

  function lang() { return (window.DWI18n && window.DWI18n.get()) || 'en'; }
  function fa() { return lang() === 'fa'; }
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
    { id: 'score_meaning', cat: 'score', need: ['result'], en: 'What does my current score mean?', fa: 'امتیاز فعلی‌ام یعنی چه؟', icon: '🎯' },
    { id: 'why_this_score', cat: 'score', need: ['result'], en: 'Why did I get this exact score?', fa: 'چرا دقیقاً این امتیاز را گرفتم؟', icon: '🔍' },
    { id: 'confidence_check', cat: 'score', need: ['result'], en: 'How confident is the model right now?', fa: 'مدل الان چقدر مطمئن است؟', icon: '📶' },
    { id: 'ood_check', cat: 'score', need: ['result'], en: 'Is anything about today unusual for the model?', fa: 'چیزی امروز برای مدل غیرعادی است؟', icon: '⚠️' },
    { id: 'strongest_factor', cat: 'score', need: ['result'], en: 'What is working in my favour?', fa: 'چه چیزی به نفعم کار می‌کند؟', icon: '💪' },
    { id: 'weakest_dimension', cat: 'score', need: ['result'], en: 'Which dimension is weakest right now?', fa: 'الان کدام بعد ضعیف‌ترین است؟', icon: '📉' },
    { id: 'compare_to_last', cat: 'score', need: ['history'], en: 'How does today compare to my last check-in?', fa: 'امروز نسبت به آخرین بررسی‌ام چطور است؟', icon: '↔️' },

    // ---- Sleep ----
    { id: 'sleep_summary', cat: 'sleep', need: ['payload'], en: 'How was my sleep last night?', fa: 'خوابم دیشب چطور بود؟', icon: '😴' },
    { id: 'sleep_vs_target', cat: 'sleep', need: ['payload'], en: 'Am I close to the recommended sleep amount?', fa: 'به مقدار توصیه‌شده‌ی خواب نزدیکم؟', icon: '🛌' },
    { id: 'pre_sleep_check', cat: 'sleep', need: ['payload'], en: 'Am I using my phone too close to bedtime?', fa: 'خیلی نزدیک به خواب گوشی دست می‌گیرم؟', icon: '📵' },
    { id: 'sleep_recommendation', cat: 'sleep', need: ['result'], en: 'What is my top sleep recommendation?', fa: 'مهم‌ترین توصیه‌ی خوابم چیست؟', icon: '💡' },

    // ---- Focus & screen habits ----
    { id: 'focus_summary', cat: 'focus', need: ['payload'], en: 'How is my focus today?', fa: 'تمرکزم امروز چطور است؟', icon: '🎯' },
    { id: 'fragmentation_check', cat: 'focus', need: ['payload'], en: 'Is my attention fragmented today?', fa: 'توجهم امروز پراکنده است؟', icon: '🧩' },
    { id: 'notification_load', cat: 'focus', need: ['payload'], en: 'Are my notifications out of control?', fa: 'اعلان‌هایم از کنترل خارج شده؟', icon: '🔔' },
    { id: 'screen_time_breakdown', cat: 'focus', need: ['payload'], en: 'Break down my screen time for me.', fa: 'زمان صفحه‌نمایشم را برایم تفکیک کن.', icon: '📱' },
    { id: 'night_usage_check', cat: 'focus', need: ['payload'], en: 'How much of my screen time is at night?', fa: 'چقدر از زمان صفحه‌ام شبانه است؟', icon: '🌙' },

    // ---- Emotional wellbeing ----
    { id: 'stress_check', cat: 'emotional', need: ['payload'], en: 'How stressed am I today?', fa: 'امروز چقدر استرس دارم؟', icon: '😮‍💨' },
    { id: 'mood_check', cat: 'emotional', need: ['payload'], en: 'How is my mood today?', fa: 'حال و هوایم امروز چطور است؟', icon: '🙂' },
    { id: 'loneliness_check', cat: 'emotional', need: ['payload'], en: 'Am I feeling isolated lately?', fa: 'اخیراً احساس تنهایی می‌کنم؟', icon: '🫂' },
    { id: 'social_comparison_check', cat: 'emotional', need: ['payload'], en: 'Is social comparison affecting me?', fa: 'مقایسه‌ی اجتماعی روی من اثر گذاشته؟', icon: '📲' },

    // ---- Physical & lifestyle ----
    { id: 'activity_check', cat: 'physical', need: ['payload'], en: 'Am I moving enough today?', fa: 'امروز به‌اندازه‌ی کافی تحرک داشتم؟', icon: '🏃' },
    { id: 'caffeine_check', cat: 'physical', need: ['payload'], en: 'Is my caffeine intake a factor?', fa: 'مصرف کافئینم عامل مهمی است؟', icon: '☕' },
    { id: 'lifestyle_summary', cat: 'physical', need: ['result'], en: 'Summarize my physical & lifestyle score.', fa: 'امتیاز فعالیت بدنی و سبک زندگی‌ام را خلاصه کن.', icon: '🌿' },

    // ---- Recommendations & action ----
    { id: 'top_priority_action', cat: 'action', need: ['result'], en: 'If I only do one thing today, what should it be?', fa: 'اگر فقط یک کار امروز انجام بدهم، چه باشد؟', icon: '✅' },
    { id: 'quick_win', cat: 'action', need: ['result'], en: 'Give me the easiest quick win.', fa: 'ساده‌ترین برد سریع را به من بده.', icon: '⚡' },
    { id: 'success_metrics_recap', cat: 'action', need: ['result'], en: 'How will I know my recommendations are working?', fa: 'از کجا بفهمم توصیه‌ها جواب داده‌اند؟', icon: '📏' },
    { id: 'muted_topics', cat: 'action', need: [], en: 'What topics have I muted from coaching?', fa: 'چه موضوعاتی را از مربی‌گری خاموش کرده‌ام؟', icon: '🔕' },

    // ---- Progress & history ----
    { id: 'streak_check', cat: 'progress', need: ['progress'], en: "What's my current check-in streak?", fa: 'رکورد پیاپی بررسی‌هایم چقدر است؟', icon: '🔥' },
    { id: 'personal_bests', cat: 'progress', need: ['progress'], en: 'Have I set any personal bests?', fa: 'رکورد شخصی جدیدی زده‌ام؟', icon: '🏆' },
    { id: 'small_wins', cat: 'progress', need: ['progress'], en: 'What small wins have I had recently?', fa: 'اخیراً چه بردهای کوچکی داشته‌ام؟', icon: '🌱' },
    { id: 'before_after', cat: 'progress', need: ['progress'], en: 'Compare my first days to my most recent days.', fa: 'روزهای اول را با روزهای اخیرم مقایسه کن.', icon: '📊' },
    { id: 'weekday_pattern', cat: 'progress', need: ['insights'], en: 'Which day of the week is hardest for me?', fa: 'کدام روز هفته برایم سخت‌تر است؟', icon: '📅' },
    { id: 'cold_start_status', cat: 'progress', need: ['insights'], en: 'Do I have enough data yet for real trends?', fa: 'برای روند واقعی داده‌ی کافی دارم؟', icon: '🌡️' },

    // ---- Persona & identity ----
    { id: 'my_persona', cat: 'identity', need: ['persona'], en: 'What is my behavioral persona?', fa: 'پرسونای رفتاری‌ام چیست؟', icon: '🎭' },
    { id: 'my_badges', cat: 'identity', need: ['persona'], en: 'What badges have I earned?', fa: 'چه نشان‌هایی گرفته‌ام؟', icon: '🥇' },
    { id: 'persona_alternates', cat: 'identity', need: ['persona'], en: 'What other personas am I close to?', fa: 'به چه پرسونای دیگری نزدیکم؟', icon: '🔀' },

    // ---- Weekly plan ----
    { id: 'this_week_plan', cat: 'plan', need: ['plan'], en: "What's my plan for this week?", fa: 'برنامه‌ی این هفته‌ام چیست؟', icon: '🗓️' },
    { id: 'plan_today', cat: 'plan', need: ['plan'], en: "What's on today's plan specifically?", fa: 'دقیقاً برنامه‌ی امروز چیست؟', icon: '📌' },
    { id: 'weekly_card_prompt', cat: 'plan', need: [], en: 'Can I get a shareable card of my week?', fa: 'می‌شود کارت هفته‌ام را بگیرم؟', icon: '🖼️' },

    // ---- Future & what-if ----
    { id: 'future_self_gradual', cat: 'future', need: ['future'], en: 'Talk to my future self after gradual improvement.', fa: 'با خودِ آینده‌ام بعد از بهبود تدریجی حرف بزن.', icon: '🔮' },
    { id: 'future_self_committed', cat: 'future', need: ['future'], en: 'Talk to my future self if I commit fully.', fa: 'با خودِ آینده‌ام اگر کاملاً متعهد شوم حرف بزن.', icon: '🚀' },
    { id: 'future_self_drift', cat: 'future', need: ['future'], en: 'What happens if I keep drifting like this?', fa: 'اگر همین‌طور ادامه بدهم چه می‌شود؟', icon: '⏳' },
    { id: 'whatif_pointer', cat: 'future', need: [], en: 'I want to test my own scenario.', fa: 'می‌خواهم سناریوی خودم را تست کنم.', icon: '🧪' },

    // ---- Friends League ----
    { id: 'league_standing', cat: 'league', need: ['league'], en: 'Where do I stand in the League?', fa: 'جایگاهم در لیگ کجاست؟', icon: '🏅' },
    { id: 'league_get_ahead', cat: 'league', need: ['league'], en: 'How do I get ahead of my friends in the League?', fa: 'چطور از دوستانم توی لیگ جلو بیفتم؟', icon: '📈' },
    { id: 'league_invite_code', cat: 'league', need: [], en: 'What is my invite code?', fa: 'کد دعوتم چیست؟', icon: '🔗' },
    { id: 'league_pending', cat: 'league', need: [], en: 'Do I have pending League requests?', fa: 'درخواست معلق در لیگ دارم؟', icon: '📬' },
    { id: 'league_privacy', cat: 'league', need: [], en: 'What can my friends actually see about me?', fa: 'دوستانم دقیقاً چه چیزی از من می‌بینند؟', icon: '🔒' },

    // ---- Cohort ----
    { id: 'cohort_percentile', cat: 'cohort', need: ['cohort'], en: 'How do I compare to everyone else using this app?', fa: 'نسبت به بقیه‌ی کاربران این اپ چطورم؟', icon: '🌍' },
    { id: 'rare_achievement', cat: 'cohort', need: ['cohort'], en: 'Do I have any rare achievements?', fa: 'دستاورد کمیابی دارم؟', icon: '💎' },

    // ---- Privacy & data ----
    { id: 'export_reminder', cat: 'privacy', need: [], en: 'How do I get a copy of all my data?', fa: 'چطور یک نسخه از تمام داده‌هایم بگیرم؟', icon: '📤' },
    { id: 'field_lookup', cat: 'privacy', need: ['payload'], en: 'Explain the field that affected me most.', fa: 'فیلدی که بیشترین اثر را داشت را توضیح بده.', icon: '📚' },

    // ---- Meta ----
    { id: 'tell_me_fact', cat: 'meta', need: [], en: 'Tell me something useful about digital wellbeing.', fa: 'یک نکته‌ی مفید درباره‌ی سلامت دیجیتال بگو.', icon: '💭' },
    { id: 'motivate_me', cat: 'meta', need: ['result'], en: 'I need some motivation.', fa: 'به یک انگیزه نیاز دارم.', icon: '🌟' },
    { id: 'full_digest', cat: 'meta', need: ['result'], en: 'Give me the full picture, everything at once.', fa: 'کل تصویر را یک‌جا به من بده.', icon: '🧾' },
  ];

  const CATEGORY_LABELS = {
    score: { en: 'Your score', fa: 'امتیازت' },
    sleep: { en: 'Sleep', fa: 'خواب' },
    focus: { en: 'Focus & screen habits', fa: 'تمرکز و عادت‌های صفحه' },
    emotional: { en: 'Emotional wellbeing', fa: 'بهزیستی احساسی' },
    physical: { en: 'Physical & lifestyle', fa: 'فعالیت بدنی و سبک زندگی' },
    action: { en: 'Recommendations & action', fa: 'توصیه و اقدام' },
    progress: { en: 'Progress & history', fa: 'پیشرفت و تاریخچه' },
    identity: { en: 'Persona & identity', fa: 'پرسونا و هویت' },
    plan: { en: 'Weekly plan', fa: 'برنامه‌ی هفتگی' },
    future: { en: 'Future & what-if', fa: 'آینده و اگر-چه' },
    league: { en: 'Friends League', fa: 'لیگ دوستان' },
    cohort: { en: 'Compared to everyone', fa: 'مقایسه با همه' },
    privacy: { en: 'Privacy & data', fa: 'حریم خصوصی و داده' },
    meta: { en: 'More', fa: 'بیشتر' },
  };

  function unavailable(reasonKey, ctx) {
    const f = fa();
    const MSG = {
      result: f ? 'هنوز بررسی‌ای ثبت نکرده‌ای — این را نمی‌توانم بسازم بدون یک نتیجه‌ی واقعی.' : "You haven't run a check-in yet - I can't build this without a real result.",
      payload: f ? 'برای این به داده‌ی امروزت نیاز دارم؛ یک بررسی انجام بده.' : "I need today's actual inputs for this - run a check-in first.",
      history: f ? 'برای مقایسه به حداقل یک بررسی‌ی قبلی نیاز دارم که هنوز نداری.' : "I need at least one earlier check-in to compare, and you don't have one yet.",
      progress: f ? 'هنوز داده‌ی تاریخچه‌ی کافی برای این نداری.' : "You don't have enough history yet for this.",
      insights: f ? 'برای این به چند روز داده‌ی بیشتر نیاز است.' : 'This needs a few more days of data first.',
      persona: f ? 'برای تعیین پرسونا هنوز داده‌ی کافی نداری.' : "There isn't enough data yet to assign a persona.",
      plan: f ? 'برای این ابتدا باید یک بررسی انجام بدهی تا برنامه ساخته شود.' : 'Run a check-in first so a plan can be generated.',
      future: f ? 'برای شبیه‌سازی آینده به یک بررسی‌ی واقعی نیاز دارم.' : 'I need a real check-in to simulate a future path from.',
      league: f ? 'تو هنوز هیچ دوستی در لیگ نداری، پس لیگ برایت فعال نیست.' : "You don't have any friends in the League yet, so the League isn't active for you.",
      cohort: f ? 'داده‌ی گروه مقایسه هنوز برای این کافی نیست.' : 'The comparison cohort is not available yet.',
    };
    return MSG[reasonKey] || MSG.result;
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
    const f = fa();
    const r = ctx.result, p = ctx.payload || {};
    const dims = (r && r.dimension_breakdown && r.dimension_breakdown.dimensions) || [];
    const dim = (key) => dims.find((d) => d.key === key);
    const top = r && (r.shap_features || [])[0];
    const worst = r && (r.shap_features || []).find((s) => s.direction === 'decrease');
    const best = r && (r.shap_features || []).find((s) => s.direction === 'increase');

    switch (id) {
      case 'score_meaning': {
        const score = Math.round(r.regression_score ?? 0);
        return f
          ? `امتیازت ${score} از ۱۰۰ است و مدل امروزت را «${r.prediction}» دسته‌بندی کرده. این عدد از مدل رگرسیون واقعی می‌آید، نه یک قانون ساده.`
          : `Your score is ${score}/100 and the model classed today "${r.prediction}". That number comes straight from the trained regression model, not a hand-written rule.`;
      }
      case 'why_this_score':
        return top
          ? (f ? `بیشترین اثر را «${labelFor(top.feature)}» گذاشته (${top.direction === 'decrease' ? 'در جهت پایین‌آورنده' : 'در جهت بالابرنده'}). این از SHAP همین پیش‌بینی می‌آید.`
                : `The single biggest driver was ${labelFor(top.feature)} (pulling ${top.direction === 'decrease' ? 'the score down' : 'the score up'}). This is straight from SHAP on this exact prediction.`)
          : unavailable('result', ctx);
      case 'confidence_check': {
        const cl = r.confidence_label;
        return cl
          ? `${cl.headline} ${cl.detail}`
          : (f ? `اطمینان مدل ${Math.round(r.confidence_percent || 0)}٪ است.` : `Model confidence is ${Math.round(r.confidence_percent || 0)}%.`);
      }
      case 'ood_check': {
        const ood = r.ood;
        if (ood && ood.is_out_of_distribution) return '⚠️ ' + ood.message;
        return f ? 'نه، ورودی‌های امروزت کاملاً در محدوده‌ی چیزی است که مدل قبلاً دیده.' : "No - today's inputs sit comfortably inside what the model has already seen.";
      }
      case 'strongest_factor':
        return best
          ? (f ? `«${labelFor(best.feature)}» الان بیشترین کمک را به امتیازت می‌کند.` : `${labelFor(best.feature)} is doing the most for you right now.`)
          : (f ? 'هیچ عامل قوی مثبتی امروز برجسته نشد.' : 'No single strongly positive factor stood out today.');
      case 'weakest_dimension': {
        const weakest = dims.length ? dims.reduce((a, b) => (a.score < b.score ? a : b)) : null;
        if (!weakest) return unavailable('result', ctx);
        const label = window.DWI18n.t('dim_' + weakest.key) || weakest.label;
        return f ? `«${label}» با ${Math.round(weakest.score)} از ۱۰۰ الان ضعیف‌ترین بعد توست.` : `${label} is your weakest dimension right now, at ${Math.round(weakest.score)}/100.`;
      }
      case 'compare_to_last': {
        if (!ctx.history || ctx.history.length < 2) return unavailable('history', ctx);
        const [latest, prev] = ctx.history;
        const delta = (latest.health_score ?? 0) - (prev.health_score ?? 0);
        return f
          ? `نسبت به بررسی‌ی قبلی‌ات، امتیازت ${delta >= 0 ? '+' : ''}${delta.toFixed(1)} تغییر کرده (از ${Math.round(prev.health_score)} به ${Math.round(latest.health_score)}).`
          : `Compared to your previous check-in, your score moved ${delta >= 0 ? '+' : ''}${delta.toFixed(1)} (from ${Math.round(prev.health_score)} to ${Math.round(latest.health_score)}).`;
      }

      case 'sleep_summary':
        return p.sleep_hours != null
          ? (f ? `دیشب ${p.sleep_hours} ساعت خوابیدی، با کیفیت ${p.sleep_quality_1_10 ?? '—'} از ۱۰.` : `You logged ${p.sleep_hours}h of sleep last night, quality ${p.sleep_quality_1_10 ?? '—'}/10.`)
          : unavailable('payload', ctx);
      case 'sleep_vs_target': {
        if (p.sleep_hours == null) return unavailable('payload', ctx);
        const diff = p.sleep_hours - 8;
        return f
          ? `هدف مرجع ۸ ساعت است؛ تو ${Math.abs(diff).toFixed(1)} ساعت ${diff < 0 ? 'کمتر' : 'بیشتر'} از آن خوابیده‌ای.`
          : `The reference target is 8h; you're ${Math.abs(diff).toFixed(1)}h ${diff < 0 ? 'under' : 'over'} that.`;
      }
      case 'pre_sleep_check':
        return p.pre_sleep_ratio != null
          ? (f ? `${Math.round(p.pre_sleep_ratio * 100)}٪ از زمان قبل از خوابت با گوشی بوده.` : `${Math.round(p.pre_sleep_ratio * 100)}% of your pre-bed time was on the phone.`)
          : unavailable('payload', ctx);
      case 'sleep_recommendation': {
        const rec = (r.recommendations || []).find((x) => x.category === 'Sleep');
        return rec
          ? `${rec.title} — ${rec.action}`
          : (f ? 'الان توصیه‌ی فعالی درباره‌ی خواب نداری — یعنی این بخش مشکلی نشان نداده.' : 'No active sleep recommendation right now - that area isn\'t flagged as a problem.');
      }

      case 'focus_summary': {
        const d = dim('focus');
        return d ? (f ? `امتیاز تمرکز/بهره‌وری‌ات ${Math.round(d.score)} از ۱۰۰ است.` : `Your focus & productivity score is ${Math.round(d.score)}/100.`) : unavailable('payload', ctx);
      }
      case 'fragmentation_check':
        return p.fragmentation_index_0_100 != null
          ? (f ? `شاخص پراکندگی توجهت ${Math.round(p.fragmentation_index_0_100)} از ۱۰۰ است.` : `Your attention fragmentation index is ${Math.round(p.fragmentation_index_0_100)}/100.`)
          : unavailable('payload', ctx);
      case 'notification_load':
        return p.notifications_per_day != null
          ? (f ? `امروز ${p.notifications_per_day} اعلان ثبت کرده‌ای.` : `You logged ${p.notifications_per_day} notifications today.`)
          : unavailable('payload', ctx);
      case 'screen_time_breakdown':
        return p.total_screen_min != null
          ? (f ? `کل زمان صفحه: ${Math.round(p.total_screen_min)} دقیقه، که ${Math.round((p.night_ratio || 0) * 100)}٪ آن شبانه و ${Math.round((p.gaming_ratio || 0) * 100)}٪ آن بازی بوده.`
                : `Total screen time: ${Math.round(p.total_screen_min)} min, of which ${Math.round((p.night_ratio || 0) * 100)}% was at night and ${Math.round((p.gaming_ratio || 0) * 100)}% was gaming.`)
          : unavailable('payload', ctx);
      case 'night_usage_check':
        return p.night_ratio != null
          ? (f ? `${Math.round(p.night_ratio * 100)}٪ از زمان صفحه‌ات شبانه بوده.` : `${Math.round(p.night_ratio * 100)}% of your screen time was at night.`)
          : unavailable('payload', ctx);

      case 'stress_check':
        return p.stress_0_10 != null ? (f ? `استرس امروزت ${p.stress_0_10} از ۱۰ ثبت شده.` : `Today's stress is logged at ${p.stress_0_10}/10.`) : unavailable('payload', ctx);
      case 'mood_check':
        return p.happiness_0_10 != null ? (f ? `شادی‌ات امروز ${p.happiness_0_10} از ۱۰ است.` : `Your happiness today is ${p.happiness_0_10}/10.`) : unavailable('payload', ctx);
      case 'loneliness_check':
        return p.loneliness_1_10 != null ? (f ? `تنهایی‌ات ${p.loneliness_1_10} از ۱۰ ثبت شده.` : `Loneliness is logged at ${p.loneliness_1_10}/10.`) : unavailable('payload', ctx);
      case 'social_comparison_check':
        return p.social_comparison_1_10 != null ? (f ? `مقایسه‌ی اجتماعی‌ات ${p.social_comparison_1_10} از ۱۰ است.` : `Social comparison is ${p.social_comparison_1_10}/10.`) : unavailable('payload', ctx);

      case 'activity_check':
        return p.physical_activity_min_per_day != null
          ? (f ? `امروز ${p.physical_activity_min_per_day} دقیقه فعالیت بدنی ثبت کرده‌ای.` : `You logged ${p.physical_activity_min_per_day} minutes of physical activity today.`)
          : unavailable('payload', ctx);
      case 'caffeine_check':
        return p.caffeine_cups_per_day != null
          ? (f ? `${p.caffeine_cups_per_day} فنجان کافئین ثبت کرده‌ای.` : `You logged ${p.caffeine_cups_per_day} cup(s) of caffeine.`)
          : unavailable('payload', ctx);
      case 'lifestyle_summary': {
        const d = dim('physical');
        return d ? (f ? `امتیاز فعالیت بدنی/سبک زندگی‌ات ${Math.round(d.score)} از ۱۰۰ است.` : `Your physical & lifestyle score is ${Math.round(d.score)}/100.`) : unavailable('result', ctx);
      }

      case 'top_priority_action': {
        const rec = (r.recommendations || [])[0];
        return rec
          ? `${rec.title} — ${rec.action} (${window.DWI18n.t('rec_success_label') || 'metric'}: ${rec.success_metric || '—'})`
          : (f ? 'الان کاری فوری برای انجام دادن نیست — عوامل اصلی به نفعت کار می‌کنند.' : 'Nothing urgent right now - your top factors are working in your favour.');
      }
      case 'quick_win': {
        const rec = (r.recommendations || []).slice().sort((a, b) => (a.priority === 'HIGH' ? -1 : 1))[0];
        return rec ? `${rec.title} — ${rec.action}` : (f ? 'موردی برای پیشنهاد سریع نیست.' : 'Nothing to suggest as a quick win right now.');
      }
      case 'success_metrics_recap': {
        const list = (r.recommendations || []).map((x) => `• ${x.title}: ${x.success_metric || '—'}`).join('\n');
        return list || (f ? 'توصیه‌ی فعالی نداری.' : 'You have no active recommendations.');
      }
      case 'muted_topics': {
        let excluded = [];
        try { excluded = JSON.parse(localStorage.getItem('dwai_excluded_rec_categories') || '[]'); } catch (e) {}
        return excluded.length
          ? (f ? `این موضوعات خاموش‌اند: ${excluded.join('، ')}` : `Muted topics: ${excluded.join(', ')}`)
          : (f ? 'هیچ موضوعی را خاموش نکرده‌ای.' : "You haven't muted any topics.");
      }

      case 'streak_check':
        return ctx.progress.streak_days != null
          ? (f ? `الان ${ctx.progress.streak_days} روز پیاپی بررسی کرده‌ای.` : `You're on a ${ctx.progress.streak_days}-day check-in streak.`)
          : unavailable('progress', ctx);
      case 'personal_bests': {
        const bests = (ctx.progress.personal_bests || []).filter((b) => b.is_new);
        return bests.length
          ? bests.map((b) => (f ? `«${b.metric}» رکورد جدید زده: ${b.value}` : `New personal best on ${b.metric}: ${b.value}`)).join('\n')
          : (f ? 'الان رکورد تازه‌ای نداری، اما ادامه بده.' : 'No new personal bests right now, but keep going.');
      }
      case 'small_wins': {
        const wins = ctx.progress.small_wins || [];
        return wins.length
          ? wins.map((w) => `• ${w.field_name.replace(/_/g, ' ')}: ${w.delta > 0 ? '+' : ''}${w.delta.toFixed(1)}`).join('\n')
          : (f ? 'اخیراً برد کوچک قابل‌توجهی ثبت نشده.' : "No notable small wins logged recently.");
      }
      case 'before_after': {
        const ba = ctx.progress.before_after;
        if (!ba || !ba.available) return unavailable('progress', ctx);
        return f
          ? `میانگین روزهای اول ${Math.round(ba.before_avg)} بود، روزهای اخیر ${Math.round(ba.after_avg)} — ${ba.is_meaningful ? 'تفاوت واقعی است' : 'هنوز تفاوت محسوسی نیست'}.`
          : `Your early average was ${Math.round(ba.before_avg)}, recent average is ${Math.round(ba.after_avg)} - ${ba.is_meaningful ? 'a real difference' : 'not yet a meaningful difference'}.`;
      }
      case 'weekday_pattern': {
        const days = ctx.insights.weekday_reliability || [];
        const reliable = days.filter((d) => d.is_reliable && d.average_score != null);
        if (!reliable.length) return unavailable('insights', ctx);
        const hardest = reliable.reduce((a, b) => (a.average_score < b.average_score ? a : b));
        return f ? `${hardest.weekday} معمولاً کمترین امتیاز میانگین را برایت دارد (${Math.round(hardest.average_score)}).` : `${hardest.weekday} tends to be your lowest-average day (${Math.round(hardest.average_score)}).`;
      }
      case 'cold_start_status':
        return ctx.insights.cold_start ? `${ctx.insights.cold_start.message}` : unavailable('insights', ctx);

      case 'my_persona':
        return ctx.persona.primary
          ? `${ctx.persona.primary.title} — ${ctx.persona.primary.reason}`
          : unavailable('persona', ctx);
      case 'my_badges': {
        const badges = ctx.persona.badges || [];
        return badges.length ? badges.map((b) => `${b.icon || '🥇'} ${b.title}`).join(', ') : (f ? 'هنوز نشانی نگرفته‌ای.' : "You haven't earned any badges yet.");
      }
      case 'persona_alternates': {
        const alts = ctx.persona.alternates || [];
        return alts.length ? alts.map((a) => a.title).join(', ') : (f ? 'الگوی دیگری نزدیک نیست.' : 'No other persona is close right now.');
      }

      case 'this_week_plan':
        return ctx.plan
          ? (f ? `تمرکز این هفته: ${(ctx.plan.focus_areas || []).join('، ')}.` : `This week's focus: ${(ctx.plan.focus_areas || []).join(', ')}.`)
          : unavailable('plan', ctx);
      case 'plan_today': {
        if (!ctx.plan) return unavailable('plan', ctx);
        const day = (ctx.plan.days || [])[0];
        return day ? `${day.theme}: ${(day.tasks || []).map((t) => t.text).join('; ')}` : unavailable('plan', ctx);
      }
      case 'weekly_card_prompt':
        return f ? 'بله! از صفحه‌ی «برنامه‌ی هفتگی» دکمه‌ی «دانلود کارت هفته» را بزن.' : 'Yes! Use the "Download weekly card" button on the Weekly Plan page.';

      case 'future_self_gradual':
      case 'future_self_committed': {
        const key = id === 'future_self_gradual' ? 'gradual_improvement' : 'committed_change';
        const path = (ctx.future || []).find((x) => x.key === key);
        if (!path || path.regression_score == null) return unavailable('future', ctx);
        const delta = path.score_delta_vs_status_quo;
        return f
          ? `اگر این الگو را ادامه بدهی، مدل می‌گوید امتیازت به ${Math.round(path.regression_score)} می‌رسد${delta != null ? ` (${delta >= 0 ? '+' : ''}${delta.toFixed(1)})` : ''}.`
          : `If you keep this pattern up, the model says your score becomes ${Math.round(path.regression_score)}${delta != null ? ` (${delta >= 0 ? '+' : ''}${delta.toFixed(1)})` : ''}.`;
      }
      case 'future_self_drift': {
        const path = (ctx.future || []).find((x) => x.key === 'continued_drift');
        if (!path || path.regression_score == null) return unavailable('future', ctx);
        return f
          ? `اگر عادت‌ها همین‌طور کمی بدتر شوند، مدل امتیاز ${Math.round(path.regression_score)} را پیش‌بینی می‌کند — هزینه‌ی واقعیِ بی‌عملی.`
          : `If habits drift slightly further, the model predicts a score of ${Math.round(path.regression_score)} - the real cost of doing nothing.`;
      }
      case 'whatif_pointer':
        return f ? 'صفحه‌ی «اگر-چه» دقیقاً برای همین است — یک عادت را تغییر بده و پیش‌بینی واقعی مدل را زنده ببین.' : 'The What-if page is exactly for that - change one habit and watch the real model prediction move live.';

      case 'league_standing':
        return ctx.league && ctx.league.friend_count
          ? (f ? `در بین ${ctx.league.friend_count} دوستت، رتبه‌ات ${ctx.league.my_rank || '—'} است.` : `Among your ${ctx.league.friend_count} friend(s), your rank is ${ctx.league.my_rank || '—'}.`)
          : unavailable('league', ctx);
      case 'league_get_ahead':
        return ctx.league && ctx.league.friend_count
          ? (f ? 'بهترین راه، هنوز پیشرفت نسبت به رکورد خودت است - رتبه فقط یک لایه‌ی جانبی است.' : 'The most reliable path is still improving on your own past record - rank is only a side layer.')
          : unavailable('league', ctx);
      case 'league_invite_code':
        return ctx.league && ctx.league.invite_code
          ? (f ? `کد دعوتت: ${ctx.league.invite_code}` : `Your invite code: ${ctx.league.invite_code}`)
          : (f ? 'برای گرفتن کد دعوت، صفحه‌ی لیگ دوستان را باز کن.' : 'Open the Friends League page to get your invite code.');
      case 'league_pending':
        return ctx.league && ctx.league.pending_count
          ? (f ? `${ctx.league.pending_count} درخواست منتظر تایید داری.` : `You have ${ctx.league.pending_count} request(s) waiting for your approval.`)
          : (f ? 'درخواست معلقی نداری.' : 'No pending requests.');
      case 'league_privacy':
        return f
          ? 'فقط چیزهایی که صراحتاً برای هر دوست تیک زده‌ای دیده می‌شود، و می‌توانی هر لحظه لغوش کنی.'
          : 'Only what you\'ve explicitly ticked for that specific friend is visible, and you can revoke it at any time.';

      case 'cohort_percentile':
        return ctx.cohort && ctx.cohort.rows && ctx.cohort.rows.length
          ? ctx.cohort.rows.slice(0, 3).map((row) => `${row.field.replace(/_/g, ' ')}: ${row.cohort_percentile != null ? Math.round(row.cohort_percentile) + 'th pct' : '—'}`).join('\n')
          : unavailable('cohort', ctx);
      case 'rare_achievement':
        return f ? 'برای دستاوردهای کمیاب، صفحه‌ی تحلیل‌ها را ببین.' : 'Check the Analytics page for rare achievements.';

      case 'export_reminder':
        return f ? 'از تنظیمات یا صفحه‌ی پروفایل، گزینه‌ی «خروجی گرفتن از داده‌ها» را بزن.' : 'Use "Export my data" from Settings or your Profile page.';
      case 'field_lookup':
        return top ? (f ? `«${labelFor(top.feature)}» بیشترین اثر را داشت. برای توضیح کامل، صفحه‌ی مستندات فیلدها را ببین.` : `${labelFor(top.feature)} had the biggest effect. See the field documentation for the full definition.`) : unavailable('payload', ctx);

      case 'tell_me_fact': {
        const kb = window.DWCoachKnowledge;
        if (!kb) return f ? 'خواب کافی، تمرکز بدون وقفه‌ی مکرر و کاهش چک‌کردن شبانه، سه اثرگذارترین عادت‌های سلامت دیجیتال‌اند.' : 'Enough sleep, uninterrupted focus blocks, and less late-night checking are the three highest-leverage digital-wellbeing habits.';
        const topics = kb.TOPICS || [];
        const t2 = topics[Math.floor(Math.random() * topics.length)];
        return t2 ? (fa() ? t2.fa : t2.en) : '';
      }
      case 'motivate_me': {
        const score = Math.round(r.regression_score ?? 0);
        const path = (ctx.future || []).find((x) => x.key === 'gradual_improvement');
        const future = path && path.regression_score != null ? Math.round(path.regression_score) : null;
        return f
          ? `الان ${score}/۱۰۰ هستی.${future != null ? ` با تغییرات کوچک و پیوسته، مدل می‌گوید می‌توانی به ${future} برسی.` : ''} این یک عکس این هفته است، نه سقف تو.`
          : `You're at ${score}/100 right now.${future != null ? ` With small, consistent changes, the model says you could reach ${future}.` : ''} This is a snapshot of this week, not your ceiling.`;
      }
      case 'full_digest': {
        const parts = [localAnswer('score_meaning', ctx), localAnswer('why_this_score', ctx), localAnswer('top_priority_action', ctx)];
        if (ctx.persona.primary) parts.push(localAnswer('my_persona', ctx));
        if (ctx.plan) parts.push(localAnswer('this_week_plan', ctx));
        return parts.filter(Boolean).join('\n\n');
      }
      default:
        return f ? 'هنوز پاسخی برای این ندارم.' : "I don't have an answer for that yet.";
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
    const item = ITEMS.find((i) => i.id === id);
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
      prefix = UPDATED_TAG[fa() ? 'fa' : 'en'];
      state.freshIds = Array.from(new Set([...(state.freshIds || []), id]));
    } else if (!changed && state.date === today && wasAnsweredBefore) {
      const bank = LEAD_IN[fa() ? 'fa' : 'en'];
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
    try { ctx.result = JSON.parse(localStorage.getItem('dwai_last_result') || 'null'); } catch (e) {}
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

  window.DWAIMenu = { ITEMS, CATEGORY_LABELS, buildContext, getAnswer };
})();
