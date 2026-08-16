/*
  Insight cards (D-3, D-4, D-5, D-6, D-9, D-11).

  Rendering rules, taken straight from the global rules the rest of these
  features follow:

    G2 every card is dismissible and nothing blocks the page.
    G3 dismissal is remembered: two dismissals of the same card and it
       stays away for a fortnight. Reuses DWGuide's fatigue store rather
       than inventing a second one, so "I keep waving this away" means the
       same thing everywhere in the app.
    G4 a card the server returned as null is not rendered at all - no
       skeleton, no dashes, no "not enough data yet" placeholder pretending
       to be a feature.
    G5 wording is plain and never scolding: a regression is reported as a
       fact with a next step, not as a failure.
    G6 all four languages, and the numbers inside a sentence stay LTR.

  Correlation wording is the sensitive part. The server marks every
  relationship is_observation_only, and the strings below say "moved
  together with" / "moved opposite to" - never "causes", "leads to" or
  "because of". A statistical association between two things a person
  logged is not a mechanism, and saying otherwise would be the single
  easiest way for this feature to become misinformation.
*/
(function () {
  const DISMISS_PREFIX = 'dwai_guide_dismiss_';   // shared with DWGuide
  const SHOWN_PREFIX = 'dwai_guide_shown_';
  const DISMISSALS_BEFORE_QUIET = 2;
  const QUIET_DAYS = 14;
  const DAY_MS = 86400000;

  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);
  const lang = () => (window.DWI18n && window.DWI18n.get ? window.DWI18n.get() : 'en');

  // Risk alerts are the one card built from server prose (title/message/
  // action) rather than a client-side sentence template - see
  // frontend/assets/js/pages/weekly.js's identical helper for why this reads
  // the reader's own language and falls back to English rather than
  // trusting the flat field, which is whatever language the ALERT
  // happened to be evaluated in.
  const serverText = (payload, part, fallback) => {
    const table = ((payload && payload.text_i18n) || {})[part];
    if (table) {
      const own = table[lang()];
      if (own) return own;
      if (table.en) return table.en;
    }
    return fallback || '';
  };

  const T = {
    heading: { en: 'What your own data shows', fa: 'آنچه داده‌ی خودت نشان می‌دهد', ar: 'ما تُظهره بياناتك', zh: '你的数据显示了什么' },
    dismiss: { en: 'Dismiss', fa: 'بستن', ar: 'إغلاق', zh: '关闭' },
    observation: {
      en: 'Observed together in your own check-ins — not proof that one causes the other.',
      fa: 'در بررسی‌های خودت با هم دیده شده‌اند — دلیلی بر این نیست که یکی باعث دیگری است.',
      ar: 'لوحظا معاً في تسجيلاتك — وليس دليلاً على أن أحدهما يسبب الآخر.',
      zh: '在你自己的记录中一起出现——这不能证明其中一个导致了另一个。',
    },
    basedOn: { en: 'based on', fa: 'بر پایه‌ی', ar: 'استناداً إلى', zh: '基于' },
    days: { en: 'days', fa: 'روز', ar: 'يوماً', zh: '天' },

    corrTitle: { en: 'A relationship in your data', fa: 'یک رابطه در داده‌ات', ar: 'علاقة في بياناتك', zh: '你数据中的一个关联' },
    movedTogether: { en: 'moved together with', fa: 'هم‌جهت حرکت کرده با', ar: 'تحرّك مع', zh: '同向变化于' },
    movedOpposite: { en: 'moved opposite to', fa: 'در جهت مخالف حرکت کرده با', ar: 'تحرّك عكس', zh: '反向变化于' },

    dominoTitle: { en: 'A next-day pattern', fa: 'یک الگوی روز بعد', ar: 'نمط في اليوم التالي', zh: '第二天的一个模式' },
    dominoLead: { en: 'On days with more', fa: 'در روزهایی با', ar: 'في الأيام التي بها المزيد من', zh: '在' },
    dominoTail: { en: 'the next day tended to show', fa: 'روز بعد معمولاً این را نشان داده', ar: 'يميل اليوم التالي إلى إظهار', zh: '较多的日子里，第二天往往表现出' },
    higher: { en: 'higher', fa: 'بالاتر', ar: 'أعلى', zh: '更高' },
    lower: { en: 'lower', fa: 'پایین‌تر', ar: 'أقل', zh: '更低' },

    weekTitle: { en: 'Your week, in a sentence', fa: 'هفته‌ات، در یک جمله', ar: 'أسبوعك في جملة', zh: '一句话总结你这周' },
    weekAvg: { en: 'You averaged', fa: 'میانگینت بوده', ar: 'بلغ متوسطك', zh: '你的平均分是' },
    weekOver: { en: 'over', fa: 'در', ar: 'على مدى', zh: '在' },
    weekBest: { en: 'Best day', fa: 'بهترین روز', ar: 'أفضل يوم', zh: '最好的一天' },
    weekUp: { en: 'up', fa: 'بالاتر', ar: 'أعلى', zh: '上升' },
    weekDown: { en: 'down', fa: 'پایین‌تر', ar: 'أقل', zh: '下降' },
    weekVsPrev: { en: 'vs the week before', fa: 'نسبت به هفته‌ی قبل', ar: 'مقارنة بالأسبوع السابق', zh: '相比上一周' },
    weekImproved: { en: 'Most improved', fa: 'بیشترین بهبود', ar: 'الأكثر تحسناً', zh: '进步最大' },
    weekExceptions: { en: 'exception day(s) left out', fa: 'روز استثنا کنار گذاشته شد', ar: 'يوم/أيام استثناء مستبعدة', zh: '天例外已排除' },

    firstTitle: { en: 'Then and now', fa: 'آن‌وقت و حالا', ar: 'حينها والآن', zh: '当时与现在' },
    firstUp: {
      en: 'Your recent days average {a} points higher than your first ones.',
      fa: 'روزهای اخیرت به‌طور میانگین {a} امتیاز بالاتر از روزهای اولت است.',
      ar: 'متوسط أيامك الأخيرة أعلى بـ {a} نقطة من أيامك الأولى.',
      zh: '你最近这些天的平均分比最初高 {a} 分。',
    },
    firstDown: {
      en: 'Your recent days average {a} points below your first ones. That is worth looking at, not worth beating yourself up over — the next check-in is the only one you can change.',
      fa: 'روزهای اخیرت به‌طور میانگین {a} امتیاز پایین‌تر از روزهای اولت است. این ارزش نگاه‌کردن دارد، نه سرزنش خود — تنها بررسی‌ای که می‌توانی عوضش کنی، بعدی است.',
      ar: 'متوسط أيامك الأخيرة أقل بـ {a} نقطة من أيامك الأولى. هذا يستحق النظر، لا لوم الذات — التسجيل القادم هو الوحيد الذي يمكنك تغييره.',
      zh: '你最近这些天的平均分比最初低 {a} 分。这值得看一看，但不值得自责——你唯一能改变的是下一次记录。',
    },

    winTitle: { en: 'A small win', fa: 'یک برد کوچک', ar: 'مكسب صغير', zh: '一个小小的进步' },
    winUp: { en: 'went up from', fa: 'بالا رفت از', ar: 'ارتفع من', zh: '从' },
    winDown: { en: 'came down from', fa: 'پایین آمد از', ar: 'انخفض من', zh: '从' },
    winTo: { en: 'to', fa: 'به', ar: 'إلى', zh: '降到/升到' },
    winSince: { en: 'since yesterday.', fa: 'نسبت به دیروز.', ar: 'منذ الأمس.', zh: '（与昨天相比）' },

    alertTitle: { en: 'Worth your attention', fa: 'ارزش توجه دارد', ar: 'يستحق انتباهك', zh: '值得你注意' },

    chTitle: { en: 'This week’s challenges', fa: 'چالش‌های این هفته', ar: 'تحديات هذا الأسبوع', zh: '本周挑战' },
    chDone: { en: 'Done', fa: 'انجام شد', ar: 'تم', zh: '已完成' },
    chWhy: {
      en: 'Every target here comes from your own history — not a generic goal, and not something you have to hit.',
      fa: 'هر هدفی که اینجا می‌بینی از سابقه‌ی خودت آمده — نه یک هدف عمومی، و نه چیزی که مجبور باشی به آن برسی.',
      ar: 'كل هدف هنا مأخوذ من سجلك أنت — ليس هدفاً عاماً، وليس شيئاً يجب عليك تحقيقه.',
      zh: '这里的每个目标都来自你自己的历史记录——不是通用目标，也不是你必须达成的事。',
    },
  };

  /* D-8. The server sends an English title/description, because the
     Streamlit page has always rendered those strings directly. This
     four-language client re-writes both from the challenge id, and
     substitutes the numbers the server put in `params` - so a Persian
     page shows a Persian challenge while the target still comes from the
     user's own history and is never invented here. An id with no entry
     below falls back to the server's own text rather than disappearing. */
  const CHALLENGES = {
    daily_checkin_streak: {
      title: { en: 'Check in every day', fa: 'هر روز ثبت کن', ar: 'سجّل كل يوم', zh: '每天记录' },
      desc: {
        en: 'Log a check-in on every day of this week.',
        fa: 'این هفته هر روز یک بررسی ثبت کن.',
        ar: 'سجّل تسجيلاً واحداً في كل يوم من هذا الأسبوع.',
        zh: '本周每天都记录一次。',
      },
    },
    beat_your_typical_score: {
      title: { en: 'Match your own typical score', fa: 'هم‌سطح امتیاز معمول خودت', ar: 'اطابق درجتك المعتادة', zh: '达到你自己的常态分数' },
      desc: {
        en: 'Average {a} or more this week — that number is your own typical score, not a benchmark.',
        fa: 'این هفته میانگین {a} یا بیشتر — این عدد امتیاز معمول خودت است، نه یک معیار بیرونی.',
        ar: 'حقّق متوسطاً {a} أو أكثر هذا الأسبوع — هذا الرقم هو درجتك المعتادة أنت، وليس معياراً خارجياً.',
        zh: '本周平均达到 {a} 或以上——这个数字是你自己的常态分数，不是外部标准。',
      },
      param: 'typical_score',
    },
    screen_time_discipline: {
      title: { en: 'Days under your usual screen time', fa: 'روزهای کمتر از زمان صفحه‌ی همیشگی', ar: 'أيام أقل من وقت شاشتك المعتاد', zh: '低于常态屏幕时间的天数' },
      desc: {
        en: 'Stay at or under your usual {a} minutes on {b} days this week.',
        fa: 'این هفته در {b} روز، در حدِ {a} دقیقه‌ی همیشگی‌ات یا کمتر بمان.',
        ar: 'ابقَ عند {a} دقيقة المعتادة أو أقل في {b} أيام من هذا الأسبوع.',
        zh: '本周有 {b} 天保持在你常态的 {a} 分钟以内。',
      },
      param: 'typical_screen',
    },
    steady_week: {
      title: { en: 'A steady week', fa: 'یک هفته‌ی یکنواخت', ar: 'أسبوع مستقر', zh: '平稳的一周' },
      desc: {
        en: 'Get through the week with no day that stands out statistically from your own baseline.',
        fa: 'هفته را بدون روزی بگذران که از خط پایه‌ی خودت به‌شکل آماری بیرون بزند.',
        ar: 'أنهِ الأسبوع دون يوم يخرج إحصائياً عن خط أساسك أنت.',
        zh: '度过这一周，没有任何一天在统计上明显偏离你自己的基线。',
      },
    },
  };

  function label(field) {
    const map = window.DWCoachLabels || {};
    return map[field] || String(field || '').replace(/_/g, ' ');
  }

  function readInt(key) {
    const raw = localStorage.getItem(key);
    const n = raw == null ? 0 : parseInt(raw, 10);
    return Number.isFinite(n) ? n : 0;
  }

  /* G3. Deliberately the same keys DWGuide uses, so a user who keeps
     dismissing things is heard once rather than per-subsystem. */
  function isQuiet(cardKey) {
    if (readInt(DISMISS_PREFIX + cardKey) < DISMISSALS_BEFORE_QUIET) return false;
    return Date.now() - readInt(SHOWN_PREFIX + cardKey) < QUIET_DAYS * DAY_MS;
  }

  function noteDismissed(cardKey) {
    if (window.DWGuide && window.DWGuide.noteDismissed) {
      window.DWGuide.noteDismissed(cardKey);
      return;
    }
    try { localStorage.setItem(DISMISS_PREFIX + cardKey, String(readInt(DISMISS_PREFIX + cardKey) + 1)); } catch (e) {}
  }

  function num(v) {
    // Numbers stay LTR inside an RTL sentence, or a range/decimal flips.
    const span = document.createElement('span');
    span.dir = 'ltr';
    span.style.unicodeBidi = 'isolate';
    span.textContent = String(v);
    return span.outerHTML;
  }

  function makeCard(key, title, bodyHtml, opts) {
    opts = opts || {};
    const card = document.createElement('div');
    card.className = 'insight-card' + (opts.tone ? ' is-' + opts.tone : '');
    card.dataset.cardKey = key;
    card.innerHTML = `
      <button type="button" class="insight-dismiss" aria-label="${pick(T.dismiss)}" title="${pick(T.dismiss)}">×</button>
      <h4>${title}</h4>
      <div class="insight-body">${bodyHtml}</div>`;
    /* B-3/B-5: clicking a card asks the guide to explain that KIND of
       card - what it is and how to read it - which is also what makes it
       spoken, since all guide speech goes through the one path. The
       dismiss control stops the click so closing a card never triggers an
       explanation of it. */
    if (opts.guideTopic) {
      card.classList.add('has-guide');
      card.setAttribute('tabindex', '0');
      card.setAttribute('role', 'button');
      const explain = (e) => {
        if (e.target.closest('.insight-dismiss')) return;
        if (window.DWGuide) window.DWGuide.explain(opts.guideTopic, { force: true });
      };
      card.addEventListener('click', explain);
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); explain(e); }
      });
    }

    card.querySelector('.insight-dismiss').addEventListener('click', (ev) => {
      ev.stopPropagation();
      noteDismissed(key);
      card.remove();
      if (window.DWSound && window.DWSound.toggleOff) window.DWSound.toggleOff();
    });
    try { localStorage.setItem(SHOWN_PREFIX + key, String(Date.now())); } catch (e) {}
    return card;
  }

  function render(data, mount) {
    if (!mount || !data) return 0;
    mount.innerHTML = '';
    let shown = 0;
    const add = (el) => { if (el) { mount.appendChild(el); shown += 1; } };

    // D-3 risk alerts first: if something needs attention, it leads.
    // These four sentences are server prose (real streak lengths,
    // z-scores, dates), not a client-side template like every other
    // card here - text_i18n carries all four languages so this reads
    // the reader's own instead of whatever RiskAlertService happened to
    // build the flat English fields in.
    (data.risk_alerts || []).forEach((a, i) => {
      const key = 'insight_alert_' + i;
      if (isQuiet(key)) return;
      const title = serverText(a, 'title', a.title) || pick(T.alertTitle);
      const message = serverText(a, 'message', a.message);
      const action = serverText(a, 'action', a.action);
      const body = `<p>${message}</p>` + (action ? `<p class="insight-action">→ ${action}</p>` : '');
      add(makeCard(key, title, body,
        { tone: a.severity === 'critical' ? 'warn' : 'info', guideTopic: 'insight_alert' }));
    });

    // D-4
    const c = data.correlation;
    if (c && !isQuiet('insight_correlation')) {
      const verb = c.direction === 'together' ? pick(T.movedTogether) : pick(T.movedOpposite);
      add(makeCard('insight_correlation', pick(T.corrTitle),
        `<p><strong>${label(c.field_a)}</strong> ${verb} <strong>${label(c.field_b)}</strong>
           <span class="muted">(${pick(T.basedOn)} ${num(c.sample_size)} ${pick(T.days)})</span></p>
         <p class="insight-caveat">${pick(T.observation)}</p>`,
        { guideTopic: 'insight_relationship' }));
    }

    // D-5
    const d = data.domino;
    if (d && !isQuiet('insight_domino')) {
      const dir = d.direction === 'together' ? pick(T.higher) : pick(T.lower);
      add(makeCard('insight_domino', pick(T.dominoTitle),
        `<p>${pick(T.dominoLead)} <strong>${label(d.trigger_field)}</strong>,
           ${pick(T.dominoTail)} ${dir} <strong>${label(d.next_day_field)}</strong>
           <span class="muted">(${pick(T.basedOn)} ${num(d.sample_size)} ${pick(T.days)})</span></p>
         <p class="insight-caveat">${pick(T.observation)}</p>`,
        { guideTopic: 'insight_relationship' }));
    }

    // D-6
    const n = data.narrative;
    if (n && !isQuiet('insight_week')) {
      const parts = [];
      if (n.avg_score != null) parts.push(`${pick(T.weekAvg)} ${num(n.avg_score)} ${pick(T.weekOver)} ${num(n.days)} ${pick(T.days)}.`);
      if (n.best_day && n.best_score != null) parts.push(`${pick(T.weekBest)}: ${num(n.best_day)} (${num(n.best_score)}).`);
      if (n.score_delta_vs_previous_week != null) {
        const up = n.score_delta_vs_previous_week >= 0;
        parts.push(`${up ? pick(T.weekUp) : pick(T.weekDown)} ${num(Math.abs(n.score_delta_vs_previous_week))} ${pick(T.weekVsPrev)}.`);
      }
      if (n.most_improved_field) parts.push(`${pick(T.weekImproved)}: <strong>${label(n.most_improved_field)}</strong>.`);
      if (n.exceptions_marked) parts.push(`<span class="muted">${num(n.exceptions_marked)} ${pick(T.weekExceptions)}.</span>`);
      if (parts.length) add(makeCard('insight_week', pick(T.weekTitle), `<p>${parts.join(' ')}</p>`,
        { guideTopic: 'insight_week' }));
    }

    // D-9
    const f = data.first_vs_now;
    if (f && !isQuiet('insight_first_vs_now')) {
      const tpl = f.improved ? pick(T.firstUp) : pick(T.firstDown);
      add(makeCard('insight_first_vs_now', pick(T.firstTitle),
        `<p>${tpl.replace('{a}', num(Math.abs(f.delta)))}</p>`,
        { tone: f.improved ? 'good' : 'info', guideTopic: 'insight_week' }));
    }

    // D-11
    const w = data.small_win;
    if (w && !isQuiet('insight_small_win')) {
      const verb = w.higher_is_better ? pick(T.winUp) : pick(T.winDown);
      add(makeCard('insight_small_win', pick(T.winTitle),
        `<p><strong>${label(w.field)}</strong> ${verb} ${num(w.yesterday)} ${pick(T.winTo)} ${num(w.today)} ${pick(T.winSince)}</p>`,
        { tone: 'good', guideTopic: 'insight_small_win' }));
    }

    // D-8. One card holding every challenge the user's own history can
    // currently support - the service omits any it cannot ground.
    const challenges = data.weekly_challenges || [];
    if (challenges.length && !isQuiet('insight_challenge')) {
      const rows = challenges.map((c) => {
        const meta = CHALLENGES[c.id];
        const params = c.params || {};
        let title = c.title;
        let desc = c.description;
        if (meta) {
          title = pick(meta.title);
          desc = pick(meta.desc)
            .replace('{a}', meta.param != null ? num(params[meta.param]) : '')
            .replace('{b}', num(c.target));
        }
        const pct = c.target > 0 ? Math.max(0, Math.min(100, (c.progress / c.target) * 100)) : 0;
        return `
          <div class="challenge-row${c.completed ? ' is-done' : ''}">
            <div class="challenge-head">
              <span class="challenge-icon" aria-hidden="true">${c.icon || '🎯'}</span>
              <strong>${title}</strong>
              <span class="challenge-count">${
                c.completed ? pick(T.chDone) : num(c.progress) + ' / ' + num(c.target)
              }</span>
            </div>
            <p class="challenge-desc">${desc}</p>
            <div class="challenge-bar" role="progressbar"
                 aria-valuenow="${c.progress}" aria-valuemin="0" aria-valuemax="${c.target}"
                 aria-label="${title}">
              <span style="width:${pct}%"></span>
            </div>
          </div>`;
      }).join('');
      add(makeCard('insight_challenge', pick(T.chTitle),
        rows + `<p class="insight-caveat">${pick(T.chWhy)}</p>`,
        { tone: 'info', guideTopic: 'insight_challenge' }));
    }

    // G4: nothing worth saying means the section does not appear at all.
    const section = mount.closest('.insight-section');
    if (section) section.classList.toggle('hidden', shown === 0);
    return shown;
  }

  async function load(mount) {
    if (!mount || !window.DWApi || !window.DWApi.insightCards) return 0;
    try {
      const data = await window.DWApi.insightCards();
      const shown = render(data, mount);
      // `data` already carries every language for the one card built
      // from server prose (risk alerts); everything else is a
      // client-side template. Neither needs a re-fetch on a language
      // switch, only a re-render - re-fetching would also be wrong
      // here, since a second call could return DIFFERENT cards (dates
      // move on, a correlation can appear or vanish) for what the
      // reader experiences as just changing the language.
      //
      // The latest payload lives on the element rather than in a
      // closure, and the listener is bound once per mount: a caller
      // that reloads this mount (a refresh button, say) should have its
      // newest data picked up by the SAME listener, not shadowed by an
      // earlier call's stale one.
      mount._dwLastInsightData = data;
      if (!mount.dataset.dwLangBound) {
        mount.dataset.dwLangBound = '1';
        document.addEventListener('dwai:langchange', () => {
          if (mount._dwLastInsightData) render(mount._dwLastInsightData, mount);
        });
      }
      return shown;
    } catch (e) {
      // An insights panel is supplementary; it must never take the page
      // down with it.
      const section = mount.closest('.insight-section');
      if (section) section.classList.add('hidden');
      return 0;
    }
  }

  window.DWInsightCards = { load, render, T };
})();
