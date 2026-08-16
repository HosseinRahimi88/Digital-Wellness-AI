/*
  Three more generated menu families, all answered from the user's OWN
  stored history rather than from today's single check-in:

    trend_<field>      "Is my X getting better or worse?"
    typical_<field>    "What is a typical X for me?"
    steady_<field>     "How steady is my X?"

  Why these are separate from coach-field-guide.js's `field_<x>` family:
  that one answers "where is this number today, and how does it compare
  to the reference target". These three need *several days* and say
  something the single-day view cannot - direction, personal baseline,
  and volatility. They are three genuinely different computations over
  the same series, not one answer reworded three times.

  Honesty rules this file follows, same as the rest of the coach:

    - Only fields that are actually persisted per-day are offered.
      services/identity/history_service.py TRACKED_FIELDS is the real list; a
      field the server never stores would produce a trend built from
      nothing, so it is not in the menu at all.
    - Days the user marked as exceptions (`excluded`) are dropped
      before any statistic is computed - the same rule the analytics
      cards use. A day someone explicitly said was unusual must not
      quietly set their baseline.
    - Under MIN_POINTS usable days, every family declines and says how
      many days it has, instead of drawing a trend through two points.
    - "Better" and "worse" are resolved through coach-field-guide.js's
      own `dir` metadata, never assumed: rising sleep_hours is an
      improvement, rising stress_0_10 is not, and this file must not
      get that backwards.
*/
(function () {
  // services/identity/history_service.py TRACKED_FIELDS, intersected at runtime
  // with the field guide (which owns direction/unit metadata). Listed
  // explicitly rather than derived, so that a field disappearing from
  // the server's stored set shows up here as a missing menu item
  // instead of a family quietly answering from absent data.
  const TRACKED = [
    'focus_0_100', 'fragmentation_index_0_100', 'gaming_min', 'night_ratio',
    'night_screen_min', 'notification_density', 'physical_activity_min_per_day',
    'pickups_per_day', 'pre_sleep_screen_min', 'productivity_0_100',
    'sleep_hours', 'sleep_quality_1_10', 'social_comparison_1_10', 'social_min',
    'social_ratio', 'stress_0_10', 'total_screen_min', 'video_min',
    'work_study_ratio',
  ];

  // The wellness score is stored per day like the tracked inputs, but
  // it lives outside the field guide (it is an output, not an input),
  // so it carries its own direction here.
  const SCORE = 'health_score';
  const SCORE_META = { dir: 'higher', unit: '' };

  const MIN_POINTS = 4;

  function lang() { return (window.DWI18n && window.DWI18n.get()) || 'en'; }
  function pick(t) {
    if (!t) return '';
    if (window.DWI18n && window.DWI18n.pick) return window.DWI18n.pick(t);
    return t[lang()] || t.en || '';
  }
  function fill(table, vars) {
    let s = pick(table);
    Object.keys(vars || {}).forEach((k) => { s = s.split('{' + k + '}').join(vars[k]); });
    return s;
  }
  function meta(field) {
    if (field === SCORE) return SCORE_META;
    return ((window.DWFieldGuide || {}).FIELDS || {})[field] || null;
  }
  function fieldName(field, forLang) {
    const raw = ((window.DWCoachLabels || {}).__raw || {})[field];
    if (raw && raw[forLang || lang()]) return raw[forLang || lang()];
    return String(field).replace(/_/g, ' ');
  }
  function round(n, d) {
    const p = 10 ** (d == null ? 1 : d);
    return Math.round(n * p) / p;
  }
  function fmt(field, v) {
    const m = meta(field);
    const unit = (m && m.unit) || '';
    return round(v) + (unit ? ' ' + unit : '');
  }

  /** Usable numeric series for a field, oldest first.
   *  The API hands history back most-recent-first (api/routers/history.py
   *  reverses it), so this reverses again - every statistic below reads
   *  more naturally in chronological order, and getting this backwards
   *  would invert every single trend answer. */
  function series(field, ctx) {
    const rows = ((ctx || {}).history) || [];
    const out = [];
    for (let i = rows.length - 1; i >= 0; i--) {
      const row = rows[i];
      if (!row || row.excluded) continue;
      const v = row[field];
      if (typeof v !== 'number' || Number.isNaN(v)) continue;
      out.push({ value: v, date: row.date });
    }
    return out;
  }

  function mean(nums) {
    if (!nums.length) return 0;
    return nums.reduce((a, b) => a + b, 0) / nums.length;
  }

  const NOT_ENOUGH = {
    en: 'I only have {have} usable day(s) of "{name}" so far, and I will not draw a trend through that. This needs at least {need}. Days you marked as exceptions are left out on purpose, so a few of those can also be why the count is lower than you expect.',
    fa: 'تا الان فقط {have} روزِ قابل‌استفاده از «{name}» دارم و روی این تعداد روند نمی‌کشم. این کار دست‌کم به {need} روز نیاز دارد. روزهایی که خودت استثنا علامت زده‌ای عمداً کنار گذاشته می‌شوند، پس چند تا از آن‌ها هم می‌تواند دلیل کمتر بودن این عدد از انتظارت باشد.',
    ar: 'لديّ حتى الآن {have} يوم/أيام قابلة للاستخدام فقط من «{name}»، ولن أرسم اتجاهاً عبر هذا العدد. هذا يحتاج {need} أيام على الأقل. والأيام التي وسمتها كاستثناءات تُستبعد عن قصد، فقد يكون بعضها أيضاً سبب أن العدد أقل مما تتوقع.',
    zh: '到目前为止「{name}」我只有 {have} 天可用的数据，我不会用这么少的点去画趋势。这至少需要 {need} 天。你标记为例外的日子会被刻意排除，所以其中几天也可能是数量比你预期少的原因。',
  };

  function decline(field, have) {
    return fill(NOT_ENOUGH, { have: have, need: MIN_POINTS, name: fieldName(field) });
  }

  /* ------------------------------------------------------------ trend */
  const TREND = {
    lead: {
      en: 'Over your last {n} logged days, "{name}" went from about {from} to about {to}.',
      fa: 'در {n} روزِ اخیری که ثبت کرده‌ای، «{name}» از حدود {from} به حدود {to} رفته.',
      ar: 'خلال آخر {n} يوماً سجّلتها، انتقل «{name}» من نحو {from} إلى نحو {to}.',
      zh: '在你最近记录的 {n} 天里，「{name}」从大约 {from} 变到了大约 {to}。',
    },
    better: {
      en: 'That is movement in the direction this app treats as healthier for this field. It is your own data saying so, not encouragement.',
      fa: 'این حرکت در همان جهتی است که این برنامه برای این فیلد سالم‌تر می‌داند. این را داده‌ی خودت می‌گوید، نه یک تشویق.',
      ar: 'هذه حركة في الاتجاه الذي يعدّه هذا التطبيق أصحّ لهذا الحقل. بياناتك أنت تقول ذلك، لا كلمة تشجيع.',
      zh: '这个变动方向，正是本应用对该字段视为更健康的方向。这是你自己的数据说的，不是一句鼓励。',
    },
    worse: {
      en: 'That is movement away from the healthier direction for this field. Worth knowing rather than worth panicking about - a few days is a signal, not a verdict.',
      fa: 'این حرکت از جهتِ سالم‌ترِ این فیلد دور می‌شود. ارزش دانستن دارد نه ارزش نگرانی - چند روز یک نشانه است، نه یک حکم.',
      ar: 'هذه حركة مبتعدة عن الاتجاه الأصحّ لهذا الحقل. تستحق أن تُعرف لا أن تُثير القلق - بضعة أيام إشارة لا حكم.',
      zh: '这个变动是在远离该字段更健康的方向。值得知道，但不值得恐慌——几天是一个信号，不是一个定论。',
    },
    flat: {
      en: 'That is close enough to flat that I would call it unchanged rather than read a direction into noise.',
      fa: 'این آن‌قدر به ثابت‌بودن نزدیک است که ترجیح می‌دهم بگویم بدون تغییر، نه اینکه از دلِ نویز جهتی دربیاورم.',
      ar: 'هذا قريب من الثبات لدرجة أنني أصفه بأنه دون تغيير، بدل قراءة اتجاه في الضجيج.',
      zh: '这已经接近持平，我更愿意说它没有变化，而不是从噪声里读出一个方向。',
    },
  };

  function trend(field, ctx) {
    const s = series(field, ctx);
    if (s.length < MIN_POINTS) return decline(field, s.length);
    const half = Math.floor(s.length / 2);
    const older = mean(s.slice(0, half).map((p) => p.value));
    const recent = mean(s.slice(s.length - half).map((p) => p.value));
    const parts = [fill(TREND.lead, {
      n: s.length, name: fieldName(field),
      from: fmt(field, older), to: fmt(field, recent),
    })];
    const delta = recent - older;
    // "Flat" is relative to the field's own magnitude: 0.3 is noise on
    // total_screen_min and a real move on sleep_hours.
    const scale = Math.max(Math.abs(older), 1e-9);
    if (Math.abs(delta) / scale < 0.05) {
      parts.push(pick(TREND.flat));
    } else {
      const m = meta(field);
      const up = delta > 0;
      const good = m && m.dir === 'higher' ? up : !up;
      parts.push(pick(good ? TREND.better : TREND.worse));
    }
    return parts.join(' ');
  }

  /* ---------------------------------------------------------- typical */
  const TYPICAL = {
    lead: {
      en: 'Across your last {n} logged days, "{name}" averages about {avg}, ranging from {min} to {max}.',
      fa: 'در {n} روزِ اخیری که ثبت کرده‌ای، میانگین «{name}» حدود {avg} است و بین {min} تا {max} نوسان دارد.',
      ar: 'عبر آخر {n} يوماً سجّلتها، يبلغ متوسط «{name}» نحو {avg}، ويتراوح بين {min} و{max}.',
      zh: '在你最近记录的 {n} 天里，「{name}」平均约为 {avg}，区间从 {min} 到 {max}。',
    },
    best: {
      en: 'Your healthiest day for this field was {date} at {value}.',
      fa: 'سالم‌ترین روزت برای این فیلد {date} با مقدار {value} بوده.',
      ar: 'أصحّ يوم لك في هذا الحقل كان {date} بقيمة {value}.',
      zh: '这个字段上你最健康的一天是 {date}，数值为 {value}。',
    },
    vsTarget: {
      en: 'The reference this app works toward is {target}, so your own typical value sits {side} it.',
      fa: 'مرجعی که این برنامه به سمتش کار می‌کند {target} است، پس مقدار معمول خودت {side} آن قرار می‌گیرد.',
      ar: 'المرجع الذي يعمل نحوه هذا التطبيق هو {target}، فقيمتك المعتادة تقع {side}.',
      zh: '这个应用参照的目标是 {target}，所以你自己的典型值位于它{side}。',
    },
    sideGood: { en: 'on the healthy side of', fa: 'در سمت سالمِ', ar: 'في الجانب الصحي منه', zh: '更健康的一侧' },
    sideBad: { en: 'on the far side of', fa: 'در سمت دورِ', ar: 'في الجانب البعيد منه', zh: '较远的一侧' },
    why: {
      en: 'This is your own baseline, not a population norm - it is what "a lot for you" or "a good day for you" is measured against everywhere else in the app.',
      fa: 'این خط پایه‌ی خودت است نه یک هنجار جمعیتی - همان چیزی که در بقیه‌ی جاهای برنامه «زیاد برای تو» یا «یک روز خوب برای تو» با آن سنجیده می‌شود.',
      ar: 'هذا خط أساسك أنت لا معيار سكاني - وهو ما يُقاس عليه «الكثير بالنسبة لك» أو «يوم جيد بالنسبة لك» في بقية أنحاء التطبيق.',
      zh: '这是你自己的基线，不是人群标准——应用里其他地方所说的「对你而言算多」或「对你而言是好的一天」，都是以它为参照的。',
    },
  };

  function typical(field, ctx) {
    const s = series(field, ctx);
    if (s.length < MIN_POINTS) return decline(field, s.length);
    const vals = s.map((p) => p.value);
    const avg = mean(vals);
    const lo = Math.min.apply(null, vals);
    const hi = Math.max.apply(null, vals);
    const m = meta(field);
    const higherIsBetter = !m || m.dir === 'higher';
    const bestPoint = s.reduce((a, b) => (
      higherIsBetter ? (b.value > a.value ? b : a) : (b.value < a.value ? b : a)
    ), s[0]);

    const parts = [fill(TYPICAL.lead, {
      n: s.length, name: fieldName(field),
      avg: fmt(field, avg), min: fmt(field, lo), max: fmt(field, hi),
    })];
    parts.push(fill(TYPICAL.best, { date: bestPoint.date, value: fmt(field, bestPoint.value) }));
    if (m && m.target != null) {
      const good = higherIsBetter ? avg >= m.target : avg <= m.target;
      parts.push(fill(TYPICAL.vsTarget, {
        target: fmt(field, m.target),
        side: pick(good ? TYPICAL.sideGood : TYPICAL.sideBad),
      }));
    }
    parts.push(pick(TYPICAL.why));
    return parts.join(' ');
  }

  /* -------------------------------------------------------- steadiness */
  const STEADY = {
    lead: {
      en: 'Across your last {n} logged days, "{name}" varies by about {dev} from its own average on a typical day, in a range of {spread}.',
      fa: 'در {n} روزِ اخیری که ثبت کرده‌ای، «{name}» در یک روز معمولی حدود {dev} از میانگین خودش فاصله می‌گیرد، در بازه‌ای به اندازه‌ی {spread}.',
      ar: 'عبر آخر {n} يوماً سجّلتها، يبتعد «{name}» في يوم معتاد نحو {dev} عن متوسطه، ضمن مدى قدره {spread}.',
      zh: '在你最近记录的 {n} 天里，「{name}」在典型的一天大约偏离自身平均值 {dev}，整体波动范围为 {spread}。',
    },
    steady: {
      en: 'That is a steady field for you. Steady is worth naming: a stable input makes every trend elsewhere easier to read, because it is one less thing moving.',
      fa: 'این برای تو یک فیلد باثبات است. ثبات ارزش نام‌بردن دارد: یک ورودی پایدار خواندن هر روند دیگری را آسان‌تر می‌کند، چون یک چیز کمتر در حال حرکت است.',
      ar: 'هذا حقل ثابت بالنسبة لك. والثبات يستحق الذكر: مدخل مستقر يجعل قراءة أي اتجاه آخر أسهل، لأنه شيء أقل يتحرك.',
      zh: '对你来说这是一个稳定的字段。稳定值得一提：一个平稳的输入会让别处的每一个趋势更容易读懂，因为少了一个在变动的东西。',
    },
    swingy: {
      en: 'That is a swingy field for you - day-to-day it moves a lot relative to its own average. A field like this is where a single unusual day can pull a weekly number around, which is exactly what the exception-day checkbox is for.',
      fa: 'این برای تو یک فیلد پرنوسان است - روز‌به‌روز نسبت به میانگین خودش زیاد جابه‌جا می‌شود. در فیلدی مثل این، یک روزِ غیرعادی به‌تنهایی می‌تواند عدد هفتگی را جابه‌جا کند، و دقیقاً همین است که تیکِ «روز استثنا» برای آن وجود دارد.',
      ar: 'هذا حقل متقلب بالنسبة لك - يتحرك يومياً كثيراً نسبةً إلى متوسطه. وفي حقل كهذا يستطيع يوم واحد غير معتاد أن يجرّ الرقم الأسبوعي معه، وهذا بالضبط ما وُجد له مربع «اليوم الاستثنائي».',
      zh: '对你来说这是一个波动较大的字段——相对于它自己的平均值，它每天变动很多。在这样的字段上，单独一个不寻常的日子就能把一周的数字拉偏，而这正是「例外日」勾选框存在的意义。',
    },
  };

  function steadiness(field, ctx) {
    const s = series(field, ctx);
    if (s.length < MIN_POINTS) return decline(field, s.length);
    const vals = s.map((p) => p.value);
    const avg = mean(vals);
    const dev = mean(vals.map((v) => Math.abs(v - avg)));
    const spread = Math.max.apply(null, vals) - Math.min.apply(null, vals);
    const parts = [fill(STEADY.lead, {
      n: s.length, name: fieldName(field),
      dev: fmt(field, dev), spread: fmt(field, spread),
    })];
    // Relative to the field's own average, so this reads the same way
    // for minutes and for a 0-10 rating.
    const rel = Math.abs(avg) > 1e-9 ? dev / Math.abs(avg) : 0;
    parts.push(pick(rel < 0.15 ? STEADY.steady : STEADY.swingy));
    return parts.join(' ');
  }

  /* -------------------------------------------------------------- menu */
  const Q = {
    trend: {
      en: (n) => `Is my ${n} getting better or worse?`,
      fa: (n) => `«${n}» من دارد بهتر می‌شود یا بدتر؟`,
      ar: (n) => `هل يتحسّن «${n}» لديّ أم يسوء؟`,
      zh: (n) => `我的「${n}」在变好还是变差？`,
    },
    typical: {
      en: (n) => `What is a typical ${n} for me?`,
      fa: (n) => `«${n}» معمولِ من چقدر است؟`,
      ar: (n) => `ما هو «${n}» المعتاد بالنسبة لي؟`,
      zh: (n) => `对我来说典型的「${n}」是多少？`,
    },
    steady: {
      en: (n) => `How steady is my ${n}?`,
      fa: (n) => `«${n}» من چقدر باثبات است؟`,
      ar: (n) => `ما مدى ثبات «${n}» لديّ؟`,
      zh: (n) => `我的「${n}」有多稳定？`,
    },
  };
  const ICON = { trend: '📈', typical: '📊', steady: '⚖️' };
  const CAT = { trend: 'trend', typical: 'typical', steady: 'steady' };

  /** Only fields the field guide can describe (it owns direction and
   *  unit), plus the score. A tracked field with no guide entry is
   *  skipped rather than answered with an assumed direction. */
  function usableFields() {
    const guide = (window.DWFieldGuide || {}).FIELDS || {};
    return TRACKED.filter((f) => guide[f]).concat([SCORE]);
  }

  function menuItems() {
    const out = [];
    usableFields().forEach((field) => {
      Object.keys(Q).forEach((fam) => {
        const item = {
          id: `${fam}_${field}`, cat: CAT[fam], need: ['history'],
          icon: ICON[fam], field: field,
        };
        ['en', 'fa', 'ar', 'zh'].forEach((lg) => {
          item[lg] = Q[fam][lg](fieldName(field, lg));
        });
        out.push(item);
      });
    });
    return out;
  }

  const HANDLERS = { trend: trend, typical: typical, steady: steadiness };

  /** True only for ids this file actually generated - the prefixes are
   *  generic enough that a loose check would swallow other families'
   *  ids and answer them from the wrong function. */
  function has(id) {
    const s = String(id || '');
    const fam = Object.keys(HANDLERS).find((f) => s.indexOf(f + '_') === 0);
    if (!fam) return false;
    return usableFields().indexOf(s.slice(fam.length + 1)) !== -1;
  }

  function answer(id, ctx) {
    const s = String(id || '');
    const fam = Object.keys(HANDLERS).find((f) => s.indexOf(f + '_') === 0);
    if (!fam) return '';
    const field = s.slice(fam.length + 1);
    if (usableFields().indexOf(field) === -1) return '';
    return HANDLERS[fam](field, ctx);
  }

  window.DWHistoryFamily = { menuItems, answer, has, series, MIN_POINTS };
})();
