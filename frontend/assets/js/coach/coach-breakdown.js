/*
  Two more families the coach could not answer: the five dimensions of
  the result ring, and the seven days of the plan.

  Both were visible on screen and unaskable. A user could look at a
  dimension arc sitting at 41 and had no way to ask what that arc is
  made of or why it is low; they could read "Day 4" and had no way to
  ask what day 4 is for.

  Every answer is built from the payload and the plan the app already
  fetched - nothing here re-derives a score or invents a target. Where
  the data has not been loaded yet, the answer says so rather than
  filling the gap.
*/
(function () {
  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : (t && t.en) || '');
  const t = (k) => (window.DWI18n && window.DWI18n.t ? window.DWI18n.t(k) : k);
  const label = (f) => ((window.DWCoachLabels || {})[f] || String(f || '').replace(/_/g, ' '));

  // Which logged signals each dimension is computed from. Mirrors
  // utils/dimension_scores.py - kept here so the coach can say what an
  // arc is made of, which is the question people actually ask about it.
  const DIMENSION_FIELDS = {
    sleep: ['sleep_hours', 'sleep_quality_1_10', 'pre_sleep_screen_min', 'night_ratio'],
    focus: ['focus_0_100', 'productivity_0_100', 'fragmentation_index_0_100', 'notifications_per_day'],
    emotional: ['stress_0_10', 'mental_fatigue_0_10', 'social_comparison_1_10', 'fomo_1_10'],
    screen_habits: ['total_screen_min', 'social_min', 'pickups_per_day', 'app_opens_per_day'],
    physical: ['physical_activity_min_per_day', 'caffeine_cups_per_day'],
  };

  const D = {
    q: {
      en: (n) => `What is my ${n} dimension made of?`,
      fa: (n) => `بُعد «${n}» من از چه چیزی ساخته شده؟`,
      ar: (n) => `مِمّ يتكوّن بُعد «${n}» لديّ؟`,
      zh: (n) => `我的「${n}」这个维度由什么构成？`,
    },
    score: {
      en: 'Your {name} dimension is at {score} out of 100.',
      fa: 'بُعد «{name}» تو روی {score} از ۱۰۰ است.',
      ar: 'بُعد «{name}» لديك عند {score} من 100.',
      zh: '你的「{name}」维度是 {score} 分（满分 100）。',
    },
    builtFrom: {
      en: 'It is built from these signals: {fields}.',
      fa: 'از این سیگنال‌ها ساخته شده: {fields}.',
      ar: 'يُبنى من هذه الإشارات: {fields}.',
      zh: '它由这些信号构成：{fields}。',
    },
    weakest: {
      en: 'Of those, the one furthest from its reference right now is {field} - that is where this arc is losing most of its points.',
      fa: 'از میان آن‌ها، چیزی که همین حالا بیشترین فاصله را از مرجعش دارد {field} است — همان‌جاست که این کمان بیشترِ امتیازش را از دست می‌دهد.',
      ar: 'من بينها، الأبعد عن مرجعه الآن هو {field} — وهناك يفقد هذا القوس معظم نقاطه.',
      zh: '其中，目前离参考值最远的是 {field}——这道弧线的分数主要就是在那里丢掉的。',
    },
    allFine: {
      en: 'None of them is currently off its reference, which is why this arc is holding.',
      fa: 'هیچ‌کدامشان الان از مرجعش دور نیست، و به همین دلیل این کمان دارد دوام می‌آورد.',
      ar: 'لا شيء منها بعيد عن مرجعه حالياً، ولهذا يصمد هذا القوس.',
      zh: '目前它们都没有偏离各自的参考值，这就是这道弧线保持住的原因。',
    },
    noResult: {
      en: 'Run a check-in and I can tell you where this dimension actually sits.',
      fa: 'یک بررسی بزن تا بتوانم بگویم این بُعد واقعاً کجاست.',
      ar: 'شغّل فحصاً وسأخبرك أين يقع هذا البُعد فعلاً.',
      zh: '做一次记录，我就能告诉你这个维度实际处在什么位置。',
    },
  };

  const P = {
    q: {
      en: (n) => `What is day ${n} of my plan for?`,
      fa: (n) => `روز ${n} برنامه‌ام برای چیست؟`,
      ar: (n) => `لماذا اليوم ${n} من خطتي؟`,
      zh: (n) => `我计划里的第 ${n} 天是做什么的？`,
    },
    head: {
      en: 'Day {n} is a {theme} day{tier}.',
      fa: 'روز {n} یک روزِ «{theme}» است{tier}.',
      ar: 'اليوم {n} يوم «{theme}»{tier}.',
      zh: '第 {n} 天是「{theme}」日{tier}。',
    },
    tierPart: {
      en: ', at the "{tier}" stage', fa: '، در مرحله‌ی «{tier}»',
      ar: '، في مرحلة «{tier}»', zh: '，处于「{tier}」阶段',
    },
    tasks: {
      en: 'It asks for: {tasks}',
      fa: 'این‌ها را می‌خواهد: {tasks}',
      ar: 'يطلب: {tasks}',
      zh: '它要求：{tasks}',
    },
    why: {
      en: 'The theme repeats across the week with a harder version each time it comes back - that escalation is the point, not repetition.',
      fa: 'این تم در طول هفته تکرار می‌شود و هر بار که برمی‌گردد نسخه‌ی سخت‌تری دارد — همین بالا رفتن هدف است، نه تکرار.',
      ar: 'يتكرر الموضوع عبر الأسبوع بنسخة أصعب في كل عودة — هذا التصاعد هو المقصود لا التكرار.',
      zh: '这个主题会在一周中反复出现，每次回来都更进一阶——这种递进才是重点，而不是重复。',
    },
    noPlan: {
      en: 'Your plan has not loaded yet. Open the Weekly Plan page once and I can read it from there.',
      fa: 'برنامه‌ات هنوز بارگذاری نشده. یک بار صفحه‌ی برنامه‌ی هفتگی را باز کن تا بتوانم از آنجا بخوانمش.',
      ar: 'لم تُحمَّل خطتك بعد. افتح صفحة الخطة الأسبوعية مرة وسأقرؤها من هناك.',
      zh: '你的计划还没有加载。打开一次「每周计划」页面，我就能从那里读到它。',
    },
  };

  const fill = (tpl, vars) => Object.keys(vars || {}).reduce(
    (s, k) => s.replace(new RegExp(`\\{${k}\\}`, 'g'), vars[k]), pick(tpl));

  function dimensionAnswer(key, ctx) {
    const dims = ((ctx.result || {}).dimension_breakdown || {}).dimensions || [];
    const found = dims.find((d) => d.key === key);
    const name = t('dim_' + key);
    if (!found) return pick(D.noResult);

    const parts = [fill(D.score, { name, score: Math.round(found.score) })];
    const fields = DIMENSION_FIELDS[key] || [];
    if (fields.length) {
      parts.push(fill(D.builtFrom, { fields: fields.map(label).join('، ') }));

      // Which of this dimension's own signals is furthest off - answered
      // from the field guide's references rather than a second opinion.
      const G = window.DWFieldGuide;
      const payload = ctx.payload || {};
      let worst = null;
      if (G) {
        fields.forEach((f) => {
          const v = payload[f];
          if (typeof v !== 'number') return;
          const s = G.standing(f, v);
          if (!s || s.better) return;
          const rel = s.target ? s.gap / Math.abs(s.target) : s.gap;
          if (!worst || rel > worst.rel) worst = { field: f, rel };
        });
      }
      parts.push(worst ? fill(D.weakest, { field: label(worst.field) }) : pick(D.allFine));
    }
    return parts.join(' ');
  }

  function planDayAnswer(n, ctx) {
    const plan = ctx.plan;
    const days = (plan && plan.days) || [];
    const day = days.find((d) => d.day_number === n);
    if (!day) return pick(P.noPlan);

    const lang = (window.DWI18n && window.DWI18n.get) ? window.DWI18n.get() : 'en';
    const part = (name, flat) => {
      const table = (day.text_i18n || {})[name];
      return (table && (table[lang] || table.en)) || flat || '';
    };
    const tier = part('tier_label', day.tier_label);
    const parts = [fill(P.head, {
      n, theme: part('theme', day.theme),
      tier: tier ? fill(P.tierPart, { tier }) : '',
    })];

    const tasks = (day.tasks || []).map((task) => {
      const ti = task.text_i18n || {};
      return ti[lang] || ti.en || task.text;
    }).filter(Boolean);
    if (tasks.length) parts.push(fill(P.tasks, { tasks: tasks.join(' • ') }));
    parts.push(pick(P.why));
    return parts.join(' ');
  }

  function menuItems() {
    const out = [];
    Object.keys(DIMENSION_FIELDS).forEach((key) => {
      const item = { id: `dim_${key}`, cat: 'dimensions', need: ['result'], icon: '◔' };
      ['en', 'fa', 'ar', 'zh'].forEach((lang) => {
        // The dimension name comes from the same i18n key the ring uses.
        const dict = (window.DWI18n && window.DWI18n.dict) ? window.DWI18n.dict : null;
        const name = (dict && dict[lang] && dict[lang]['dim_' + key]) || key.replace(/_/g, ' ');
        item[lang] = D.q[lang](name);
      });
      out.push(item);
    });
    for (let n = 1; n <= 7; n += 1) {
      const item = { id: `planday_${n}`, cat: 'plan', need: ['plan'], icon: '🗓️' };
      ['en', 'fa', 'ar', 'zh'].forEach((lang) => { item[lang] = P.q[lang](n); });
      out.push(item);
    }
    return out;
  }

  function answer(id, ctx) {
    if (id.indexOf('dim_') === 0) return dimensionAnswer(id.slice(4), ctx || {});
    if (id.indexOf('planday_') === 0) {
      return planDayAnswer(Number(id.slice('planday_'.length)), ctx || {});
    }
    return '';
  }

  function has(id) {
    return (id.indexOf('dim_') === 0 && !!DIMENSION_FIELDS[id.slice(4)])
      || /^planday_[1-7]$/.test(id);
  }

  window.DWBreakdown = { DIMENSION_FIELDS, menuItems, answer, has };
})();
