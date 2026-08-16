/*
  Demo Mode.

  What changed and why
  --------------------
  Demo Mode used to populate the SIGNED-IN account: 23 days written
  straight into the user's own history, next to their real check-ins.
  The old comment called that a feature - "never touches a real check-in
  the user already logged; it only ADDS synthetic days alongside them" -
  but adding is the problem. Once mixed in, demo days count toward the
  user's own averages, trends, badges and weekly plan, and nothing can
  separate them again. A user reported exactly that: the demo finished
  and dropped them back on their real dashboard with demo data in it.

  A demo now runs in its OWN account. The app swaps to a demo token,
  everything behaves normally inside it, and swapping back returns the
  user to their own untouched history. Leaving the demo deletes the
  account, so nothing survives it.

  Sixteen demos, not one: four lengths (3/7/15/23 days) times four
  stories (healthy, improving, borderline, at risk). One "improving"
  demo could only ever show the app being encouraging - a reviewer needs
  to see what it says to someone getting worse, and what it says when
  the signal is genuinely ambiguous.
*/
(function () {
  const REAL_TOKEN_KEY = 'dwai_token_real';
  const DEMO_STATE_KEY = 'dwai_demo_state';

  /* The processing screen holds for a minimum so the narrative has time
     to read, but the old flat 15s was most of why a 3-day demo felt
     broken - the server was done in one second and the user watched a
     progress bar for fourteen more. Scaled to the work now, and always
     skippable. */
  function minMsFor(days, friends) {
    return Math.min(14000, 2500 + days * 220 + friends * 450);
  }

  const pick = (table) =>
    (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(table) : table.en);

  const PROFILE_LABELS = {
    healthy: { en: 'Healthy', fa: 'سالم', ar: 'صحي', zh: '健康' },
    improving: { en: 'Improving', fa: 'رو به بهبود', ar: 'يتحسّن', zh: '正在改善' },
    borderline: { en: 'Borderline', fa: 'مرزی', ar: 'حدّي', zh: '临界' },
    at_risk: { en: 'At risk', fa: 'در معرض خطر', ar: 'في خطر', zh: '有风险' },
  };
  const PROFILE_NOTES = {
    healthy: {
      en: 'Consistently good days. Shows what the app says when there is nothing to fix.',
      fa: 'روزهای پیوسته خوب. نشان می‌دهد وقتی چیزی برای اصلاح نیست، برنامه چه می‌گوید.',
      ar: 'أيام جيدة باستمرار. تُظهر ما يقوله التطبيق حين لا يوجد ما يُصلَح.',
      zh: '持续良好的日子。展示当没有什么需要改进时，应用会说什么。',
    },
    improving: {
      en: 'A recovery story with a relapse in the middle - the fullest picture.',
      fa: 'داستان بهبود با یک لغزش در میانه — کامل‌ترین تصویر.',
      ar: 'قصة تعافٍ مع انتكاسة في المنتصف — الصورة الأكمل.',
      zh: '一个中途有反复的恢复故事——最完整的画面。',
    },
    borderline: {
      en: 'Hovering on the band edge, so the seven-day class actually flips.',
      fa: 'در لبه‌ی باند نوسان می‌کند، پس کلاس هفت‌روزه واقعاً جابه‌جا می‌شود.',
      ar: 'يتأرجح على حافة النطاق، فيتبدّل تصنيف الأيام السبعة فعلاً.',
      zh: '在区间边缘徘徊，所以七天的分类真的会翻转。',
    },
    at_risk: {
      en: 'Declining days. Shows that the app says so plainly instead of flattering.',
      fa: 'روزهای رو به افت. نشان می‌دهد برنامه به‌جای تعارف، صریح می‌گوید.',
      ar: 'أيام متراجعة. تُظهر أن التطبيق يقولها بصراحة بدل المجاملة.',
      zh: '走下坡的日子。展示应用会直说，而不是奉承。',
    },
  };

  const TEXT = {
    title: { en: 'Start a demo', fa: 'شروع یک دمو', ar: 'ابدأ عرضاً', zh: '开始演示' },
    lead: {
      en: 'A demo runs in its own separate account. Your own history is never touched, and leaving the demo deletes it completely.',
      fa: 'دمو در یک حساب جداگانه‌ی خودش اجرا می‌شود. به تاریخچه‌ی خودت هیچ دستی نمی‌خورد و با خروج از دمو کاملاً پاک می‌شود.',
      ar: 'يعمل العرض في حساب منفصل خاص به. لا يُمسّ سجلّك أبداً، والخروج من العرض يحذفه بالكامل.',
      zh: '演示在它自己的独立账号里运行。你自己的历史完全不受影响，退出演示会把它彻底删除。',
    },
    days: { en: 'How many days', fa: 'چند روز', ar: 'كم يوماً', zh: '多少天' },
    lapsed: {
      en: 'Did they keep up with the plan?',
      fa: 'به برنامه‌اش پایبند بوده؟',
      ar: 'هل التزم بالخطة؟',
      zh: '他有跟上计划吗？',
    },
    lapsedOn: {
      en: 'No — they lapsed',
      fa: 'نه — جا انداخته',
      ar: 'لا — تعثّر',
      zh: '没有——他掉队了',
    },
    lapsedNote: {
      en: 'Off: a user who logged every day and did the work. On: real gaps in their history, plan days left undone, badges spent paying for them and violations left over. This is the only way to see the greyed and red days, the violation panel and an empty badge wall — thirty-two demo states rather than sixteen.',
      fa: 'خاموش: کاربری که هر روز ثبت کرده و تمرین‌ها را انجام داده. روشن: شکاف واقعی در تاریخچه، روزهای انجام‌نشده‌ی برنامه، بج‌هایی که خرج جبرانشان شده و تخلف‌هایی که باقی مانده. این تنها راه دیدن روزهای خاکستری و قرمز، بخش تخلف‌ها و دیوار خالی نشان‌هاست — سی‌ودو حالت دمو به‌جای شانزده.',
      ar: 'مطفأ: مستخدم سجّل كل يوم ونفّذ المهام. مُفعّل: فجوات حقيقية في سجلّه، وأيام خطة لم تُنفَّذ، وشارات صُرفت تعويضاً عنها ومخالفات بقيت. هذه الطريقة الوحيدة لرؤية الأيام الرمادية والحمراء ولوحة المخالفات وجدار شارات فارغ — اثنتان وثلاثون حالة عرض بدل ستّ عشرة.',
      zh: '关闭：一个每天都记录、也完成了任务的用户。开启：历史里有真实的缺口、计划的日子没做、徽章被扣去抵偿、还剩下未清的违规。这是看到灰色和红色日子、违规面板以及空徽章墙的唯一方式——演示状态从十六个变成三十二个。',
    },
    story: { en: 'Which story', fa: 'کدام داستان', ar: 'أي قصة', zh: '哪个故事' },
    friends: { en: 'Demo friends', fa: 'دوستان نمایشی', ar: 'أصدقاء تجريبيون', zh: '演示好友' },
    friendsNote: {
      en: 'Each friend gets their own history and opens a chat, so the League has something real to show.',
      fa: 'هر دوست تاریخچه‌ی خودش را دارد و یک گفتگو باز می‌کند، تا لیگ چیز واقعی برای نشان دادن داشته باشد.',
      ar: 'كل صديق له سجلّه الخاص ويفتح محادثة، فيكون لدى الدوري ما يعرضه فعلاً.',
      zh: '每位好友都有自己的历史并开启一段对话，好让联赛真的有东西可展示。',
    },
    // Which of the thirty-two you are about to open, said out loud.
    // Four separate controls with no summary meant a reviewer had to
    // hold the combination in their head, and could not tell a
    // colleague which one to reproduce.
    chosenLabel: { en: 'You are opening', fa: 'داری این را باز می‌کنی', ar: 'أنت تفتح', zh: '你将打开' },
    chosenStable: {
      en: 'The same choice always opens the same person — same numbers, same story, dated to today.',
      fa: 'یک انتخاب همیشه همان فرد را باز می‌کند — همان عددها، همان داستان، با تاریخ امروز.',
      ar: 'الاختيار نفسه يفتح الشخص نفسه دائماً — الأرقام نفسها والقصة نفسها، مؤرَّخة إلى اليوم.',
      zh: '同样的选择总会打开同一个人——同样的数字、同样的故事，日期对齐到今天。',
    },
    // Two short words for the tick's two sides. Written out rather than
    // cut out of the longer labels above with a regex: the Chinese one
    // uses a double em dash, so "everything after the dash" quietly
    // produced a fragment that still began with a dash.
    keptUp: { en: 'kept up', fa: 'پایبند', ar: 'ملتزم', zh: '跟上了' },
    lapsedShort: { en: 'lapsed', fa: 'جا انداخته', ar: 'تعثّر', zh: '掉队了' },
    start: { en: 'Start demo', fa: 'شروع دمو', ar: 'ابدأ العرض', zh: '开始演示' },
    cancel: { en: 'Cancel', fa: 'انصراف', ar: 'إلغاء', zh: '取消' },
    banner: { en: 'Demo mode', fa: 'حالت نمایشی', ar: 'وضع العرض', zh: '演示模式' },
    bannerBody: {
      en: 'You are in a demo account. Your own data is untouched.',
      fa: 'در یک حساب نمایشی هستی. داده‌های خودت دست‌نخورده است.',
      ar: 'أنت في حساب تجريبي. بياناتك الخاصة لم تُمسّ.',
      zh: '你正处在演示账号中。你自己的数据完全没有被动过。',
    },
    exit: { en: 'Leave demo', fa: 'خروج از دمو', ar: 'مغادرة العرض', zh: '退出演示' },
    left: { en: 'Back in your own account.', fa: 'به حساب خودت برگشتی.', ar: 'عدت إلى حسابك.', zh: '已回到你自己的账号。' },
  };

  function state() {
    try { return JSON.parse(localStorage.getItem(DEMO_STATE_KEY) || 'null'); } catch (e) { return null; }
  }
  function isActive() { return !!state(); }

  // ---------------------------------------------------------------
  // The banner. Present on every page for as long as the demo is, so
  // there is never a moment where the user cannot tell which account
  // they are looking at - the single thing the old version got wrong.
  // ---------------------------------------------------------------
  function renderBanner() {
    const existing = document.getElementById('dwDemoBanner');
    if (existing) existing.remove();
    const current = state();
    if (!current) return;

    const bar = document.createElement('div');
    bar.id = 'dwDemoBanner';
    bar.className = 'demo-banner';
    const label = document.createElement('strong');
    label.textContent = pick(TEXT.banner);
    const detail = document.createElement('span');
    detail.textContent = ' · ' + pick(PROFILE_LABELS[current.profile] || PROFILE_LABELS.improving)
      + ' · ' + current.days + 'd';
    const body = document.createElement('span');
    body.className = 'demo-banner-body';
    body.textContent = pick(TEXT.bannerBody);
    const exit = document.createElement('button');
    exit.type = 'button';
    exit.className = 'btn btn-ghost btn-sm';
    exit.textContent = pick(TEXT.exit);
    exit.addEventListener('click', leave);

    bar.append(label, detail, body, exit);
    document.body.insertBefore(bar, document.body.firstChild);
  }

  // ---------------------------------------------------------------
  // Picker
  // ---------------------------------------------------------------
  function openPicker() {
    if (!window.DWApi || !window.DWApi.isAuthed()) return;
    if (isActive()) { leave(); return; }

    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.remove('show');

    const chosen = { days: 23, profile: 'improving', friends: 10, with_violations: false };

    const overlay = document.createElement('div');
    overlay.className = 'demo-picker-overlay';
    overlay.innerHTML = '';

    const card = document.createElement('div');
    card.className = 'demo-picker card';

    const h = document.createElement('h3');
    h.textContent = pick(TEXT.title);
    const lead = document.createElement('p');
    lead.className = 'muted';
    lead.textContent = pick(TEXT.lead);
    card.append(h, lead);

    const group = (labelText) => {
      const wrap = document.createElement('div');
      wrap.className = 'demo-picker-group';
      const lbl = document.createElement('h4');
      lbl.textContent = labelText;
      const row = document.createElement('div');
      row.className = 'demo-picker-row';
      wrap.append(lbl, row);
      card.appendChild(wrap);
      return row;
    };

    const daysRow = group(pick(TEXT.days));
    [3, 7, 15, 23].forEach((d) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip-option' + (d === chosen.days ? ' selected' : '');
      b.textContent = String(d);
      b.dir = 'ltr';
      b.addEventListener('click', () => {
        chosen.days = d;
        Array.from(daysRow.children).forEach((c) => c.classList.remove('selected'));
        b.classList.add('selected');
      });
      daysRow.appendChild(b);
    });

    const storyRow = group(pick(TEXT.story));
    const note = document.createElement('p');
    note.className = 'muted demo-picker-note';
    note.textContent = pick(PROFILE_NOTES[chosen.profile]);
    Object.keys(PROFILE_LABELS).forEach((key) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip-option' + (key === chosen.profile ? ' selected' : '');
      b.textContent = pick(PROFILE_LABELS[key]);
      b.addEventListener('click', () => {
        chosen.profile = key;
        Array.from(storyRow.children).forEach((c) => c.classList.remove('selected'));
        b.classList.add('selected');
        note.textContent = pick(PROFILE_NOTES[key]);
      });
      storyRow.appendChild(b);
    });
    storyRow.parentElement.appendChild(note);

    // The tick that doubles the catalogue. Every other control here
    // picks WHO the demo user is; this one picks whether they kept up,
    // which is the difference between a demo that can show the plan
    // working and one that can show what the app does when it does not.
    const lapsedRow = group(pick(TEXT.lapsed));
    const lapsedLabel = document.createElement('label');
    lapsedLabel.className = 'demo-picker-tick';
    const lapsedBox = document.createElement('input');
    lapsedBox.type = 'checkbox';
    lapsedBox.id = 'demoLapsedTick';
    lapsedBox.checked = !!chosen.with_violations;
    lapsedBox.addEventListener('change', () => {
      chosen.with_violations = lapsedBox.checked;
    });
    const lapsedText = document.createElement('span');
    lapsedText.textContent = pick(TEXT.lapsedOn);
    lapsedLabel.appendChild(lapsedBox);
    lapsedLabel.appendChild(lapsedText);
    lapsedRow.appendChild(lapsedLabel);
    const lnote = document.createElement('p');
    lnote.className = 'muted demo-picker-note';
    lnote.textContent = pick(TEXT.lapsedNote);
    lapsedRow.parentElement.appendChild(lnote);

    const friendRow = group(pick(TEXT.friends));
    [0, 3, 10].forEach((n) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip-option' + (n === chosen.friends ? ' selected' : '');
      b.textContent = String(n);
      b.dir = 'ltr';
      b.addEventListener('click', () => {
        chosen.friends = n;
        Array.from(friendRow.children).forEach((c) => c.classList.remove('selected'));
        b.classList.add('selected');
      });
      friendRow.appendChild(b);
    });
    const fnote = document.createElement('p');
    fnote.className = 'muted demo-picker-note';
    fnote.textContent = pick(TEXT.friendsNote);
    friendRow.parentElement.appendChild(fnote);

    /* The running summary of the four controls above. Repainted by
       every one of them, so it always names the state the button will
       actually open. */
    const summary = document.createElement('p');
    summary.className = 'demo-picker-summary';
    const summaryStable = document.createElement('span');
    summaryStable.className = 'muted demo-picker-note';
    summaryStable.textContent = pick(TEXT.chosenStable);
    const paintSummary = () => {
      const bits = [
        pick(PROFILE_LABELS[chosen.profile]),
        chosen.days + 'd',
        pick(chosen.with_violations ? TEXT.lapsedShort : TEXT.keptUp),
      ];
      summary.textContent = pick(TEXT.chosenLabel) + ': ' + bits.join(' · ');
    };
    paintSummary();
    // Every control repaints it. Wired here rather than inside each
    // handler so adding a fifth control cannot silently leave the
    // summary stale.
    card.addEventListener('click', (e) => {
      if (e.target.closest('.chip-option') || e.target.closest('.demo-picker-tick')) {
        setTimeout(paintSummary, 0);
      }
    });
    card.append(summary, summaryStable);

    const actions = document.createElement('div');
    actions.className = 'demo-picker-actions';
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'btn btn-ghost';
    cancel.textContent = pick(TEXT.cancel);
    cancel.addEventListener('click', () => overlay.remove());
    const go = document.createElement('button');
    go.type = 'button';
    go.className = 'btn btn-primary';
    go.textContent = pick(TEXT.start);
    go.addEventListener('click', () => {
      overlay.remove();
      start(chosen);
    });
    actions.append(cancel, go);
    card.appendChild(actions);

    overlay.appendChild(card);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    document.body.appendChild(overlay);
  }

  // ---------------------------------------------------------------
  // Saved check-in files for a demo
  // ---------------------------------------------------------------

  /* "Day 14 · Tuesday" - the name a person would give the file, not an
     id. The number is the day's position in this demo's own run (day 1
     is the first recorded day, not the 1st of the month), and the
     weekday comes from the real date, localised, so a Persian reader
     gets "روز ۱۴ · سه‌شنبه" rather than a transliterated Tuesday. */
  function demoFileName(row, index, total) {
    const lang = (window.DWI18n && window.DWI18n.get && window.DWI18n.get()) || 'en';
    const locale = { en: 'en-GB', fa: 'fa-IR', ar: 'ar', zh: 'zh-CN' }[lang] || 'en-GB';
    let weekday = row.day_of_week || '';
    try {
      weekday = new Date(`${row.date}T00:00:00`).toLocaleDateString(locale, { weekday: 'long' });
    } catch (e) { /* keep the server's English name */ }
    const n = (index + 1).toLocaleString(locale);
    const word = pick({ en: 'Day', fa: 'روز', ar: 'يوم', zh: '第' });
    return lang === 'zh' ? `${word}${n}天 · ${weekday}` : `${word} ${n} · ${weekday}`;
  }

  async function seedDemoCheckInFiles(expectedDays) {
    if (!window.DWCsvLibrary || !window.DWCsvLibrary.seedDemo) return 0;
    let rows = [];
    try {
      const snap = await window.DWApi.historySnapshots(Math.max(1, expectedDays || 23));
      rows = (snap && snap.entries) || [];
    } catch (e) {
      // Additive: a demo with no shelf is worse than one with, and far
      // better than one that fails to start.
      return 0;
    }
    return window.DWCsvLibrary.seedDemo(
      rows, (row, i) => demoFileName(row, i, rows.length),
    );
  }

  // ---------------------------------------------------------------
  // Start / leave
  // ---------------------------------------------------------------
  async function start(choice) {
    let session;
    try {
      session = await window.DWProcessing.run(
        window.DWApi.demoSession(choice.days, choice.profile, choice.friends, choice.with_violations),
        { flow: 'demo', days: choice.days, minMs: minMsFor(choice.days, choice.friends) },
      );
    } catch (e) {
      if (window.DWToast) window.DWToast.error(e.message);
      return;
    }

    // Keep the real token somewhere the demo cannot reach through the
    // normal token accessor, then switch. Order matters: if the swap
    // failed halfway the user must still be able to get back.
    try {
      localStorage.setItem(REAL_TOKEN_KEY, window.DWApi.getToken() || '');
      localStorage.setItem(DEMO_STATE_KEY, JSON.stringify({
        days: session.days, profile: session.profile,
        friends: session.friends_connected, user_id: session.demo_user_id,
        // Which of the thirty-two states this is. The lapsed half has a
        // different story to tell - missed days, spent badges, an open
        // violation - and the coach's seeded threads say so, so the flag
        // has to survive the navigation to the dashboard.
        lapsed: !!session.with_violations,
      }));
    } catch (e) {}
    // Seed the browser the way a real check-in does. The Weekly Plan,
    // the AI Coach and What-if all read these two keys; without them a
    // 23-day demo showed a populated dashboard and three empty pages,
    // which is the opposite of what a demo is meant to prove.
    try {
      if (session.final_result) {
        window.DWLastResult.set(session.final_result);
      }
      if (session.final_inputs && Object.keys(session.final_inputs).length) {
        localStorage.setItem('dwai_last_payload', JSON.stringify(session.final_inputs));
      }
    } catch (e) { /* a full quota must not stop the demo starting */ }

    window.DWApi.setSession(session);

    // One saved check-in file per recorded day.
    //
    // The demo claims N real check-ins and every other surface shows N -
    // the dashboard, the heatmap, the weekly plan, the coach. The saved
    // check-ins shelf showed zero, which made the one screen that is
    // meant to be "your own files" the one screen that contradicted the
    // story. These are not fabricated: each file holds the answers the
    // model actually scored for that day, read back from the server's
    // snapshot of it, so opening one refills the form with that day.
    await seedDemoCheckInFiles(session.days_created);

    if (session.friend_error && window.DWToast) {
      window.DWToast.error(session.friend_error);
    }
    if (window.DWToast) {
      window.DWToast.success(pick({
        en: `Demo ready: ${session.days_created} days, ${session.friends_connected} friends.`,
        fa: `دمو آماده است: ${session.days_created} روز، ${session.friends_connected} دوست.`,
        ar: `العرض جاهز: ${session.days_created} يوماً، ${session.friends_connected} أصدقاء.`,
        zh: `演示已就绪：${session.days_created} 天，${session.friends_connected} 位好友。`,
      }));
    }
    setTimeout(() => { location.href = 'dashboard.html'; }, 700);
  }

  async function leave() {
    const real = (() => {
      try { return localStorage.getItem(REAL_TOKEN_KEY); } catch (e) { return null; }
    })();

    // Delete the demo account while its own token is still the active
    // one - afterwards there is no way to authenticate as it, and it
    // would sit in storage forever.
    try { await window.DWApi.endDemoSession(); } catch (e) {}

    // Same reason, in the browser: coach threads are keyed by account
    // id, so once the demo account is gone its threads are unreachable
    // but still occupying storage. Dropped here, while the demo token
    // is still the one the key is derived from.
    try {
      if (window.DWCoachConversations) window.DWCoachConversations.clearAll();
    } catch (e) {}

    try {
      localStorage.removeItem(DEMO_STATE_KEY);
      localStorage.removeItem(REAL_TOKEN_KEY);
      // The demo's own leftovers, or the real account inherits them.
      window.DWLastResult.clear();
      localStorage.removeItem('dwai_last_payload');
    } catch (e) {}

    // The demo's saved check-in files. They live under their own key so
    // that dropping them cannot touch the user's real shelf.
    try {
      if (window.DWCsvLibrary) window.DWCsvLibrary.clearDemo();
    } catch (e) {}

    if (real) window.DWApi.setToken(real);
    else window.DWApi.clearToken();

    if (window.DWToast) window.DWToast.success(pick(TEXT.left));
    setTimeout(() => { location.href = real ? 'dashboard.html' : 'app.html'; }, 600);
  }

  function init() {
    renderBanner();
    document.addEventListener('dwai:langchange', renderBanner);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.DWDemo = {
    run: openPicker, leave, isActive, renderBanner, state,
    // Exposed so the saved-check-in files can be rebuilt for a demo
    // that is already running - and so a test can exercise the real
    // seeding path without driving the whole picker.
    seedFiles: seedDemoCheckInFiles,
  };
})();
