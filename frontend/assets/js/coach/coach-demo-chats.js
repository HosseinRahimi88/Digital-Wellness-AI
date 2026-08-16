/*
  DWCoachDemoChats - the coach conversations a demo user has already had.

  The problem
  -----------
  A demo could hand a reviewer twenty-three days of history, a weekly
  plan three weeks in, badges, a League and a violation ledger - and an
  AI Coach with an empty thread list, as though this person had lived
  with the app for a month and never once asked it anything. The coach
  is the part a reviewer is most likely to open, and it was the one part
  of the demo with nothing in it.

  What "real" means here
  ----------------------
  Not transcripts written by hand. Every answer below is produced by
  calling window.DWCoachChat.respond() - the same function the send box
  calls - against the demo user's own loaded context: their score, their
  SHAP factors, their recommendations, the server digest of all their
  check-ins, their two plan tracks. Type any of these questions into the
  box yourself and you get that same answer back, because it IS that
  answer. Nothing here is a canned reply, and nothing here can drift
  away from what the coach actually says, because there is no second
  copy of it to drift.

  What is scripted is the QUESTIONS - which is exactly the part a real
  user supplies - and the thread names. Six threads per state, dated
  across the user's own history rather than all stamped now, and chosen
  to suit who that person is: the at-risk user asks what is pulling them
  down, the healthy one asks what is worth protecting, and only a lapsed
  user asks why a badge was taken away.

  Rules this file holds to
  ------------------------
  · It touches demo accounts only. isDemo() is checked before anything
    is written, so a real user's thread list is never seeded.
  · It removes only its OWN threads (they carry a marker). A thread the
    reviewer typed during the demo survives a re-seed.
  · A question that the coach cannot answer is not shipped. Every one
    below is verified against the real matcher, in all four languages,
    by tests/api/test_demo_coach_chats.py - a thread whose answer is "I'm
    not sure I follow" would make the coach look worse than an empty
    list, not better.
  · Threads are written in the UI language and rewritten if the reviewer
    switches, because a demo in Persian with an English chat log is the
    kind of half-done thing that is worse than nothing.
*/
(function () {
  const MARKER = 'dwai-demo-chat-v1';

  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);
  const lang = () => (window.DWI18n && window.DWI18n.get && window.DWI18n.get()) || 'en';

  /* ------------------------------------------------------------------
     The scripts.

     `profiles` limits a thread to certain demo stories; `lapsed` limits
     it to one side of the tick (true = only the user who fell behind,
     false = only the one who kept up, undefined = both).

     Every question here was chosen by running it through the real
     matcher and keeping the ones that reach the intended answer - the
     obvious phrasing is not always the one that lands, and a question
     that lands somewhere else is worse than one that lands nowhere.
     ------------------------------------------------------------------ */
  const THREADS = [
    {
      key: 'standing',
      title: {
        en: 'Where I actually stand',
        fa: 'واقعاً کجای کار هستم',
        ar: 'أين أقف فعلاً',
        zh: '我到底处在什么位置',
      },
      asks: [
        { en: 'What is my score today?', fa: 'امتیاز امروزم چند است؟', ar: 'ما درجتي اليوم؟', zh: '我今天的分数是多少？' },
        { en: 'Why am I rated this way?', fa: 'چرا امتیازم این شکلی است؟', ar: 'لماذا درجتي هكذا؟', zh: '我的分数为什么是这样？' },
        { en: 'What should I change first?', fa: 'اول چه چیزی را عوض کنم؟', ar: 'ما الذي أغيّره أولاً؟', zh: '我该先改哪一件事？' },
      ],
    },
    {
      key: 'tracks',
      title: {
        en: 'The two halves of my week',
        fa: 'دو نیمه‌ی هفته‌ام',
        ar: 'نصفا أسبوعي',
        zh: '我这一周的两半',
      },
      asks: [
        { en: 'What should I strengthen this week?', fa: 'این هفته چه چیزی را تقویت کنم؟', ar: 'ما الذي أقويه هذا الأسبوع؟', zh: '这周我该加强什么？' },
        { en: 'What should I maintain this week?', fa: 'این هفته چه چیزی را حفظ کنم؟', ar: 'ما الذي أحافظ عليه هذا الأسبوع؟', zh: '这周我该维持什么？' },
      ],
    },
    {
      key: 'trend',
      title: {
        en: 'Is any of this actually working?',
        fa: 'اصلاً این کارها جواب می‌دهد؟',
        ar: 'هل ينفع هذا فعلاً؟',
        zh: '这些到底有没有用',
      },
      asks: [
        { en: 'Am I actually improving or is it noise?', fa: 'واقعاً دارم بهتر می‌شوم یا فقط نوسان است؟', ar: 'هل أتحسّن فعلاً أم هذا تذبذب؟', zh: '我是真的在变好，还是只是波动？' },
        { en: 'Tell me about my sleep', fa: 'درباره‌ی خوابم بگو', ar: 'حدّثني عن نومي', zh: '说说我的睡眠' },
      ],
    },
    {
      key: 'method',
      title: {
        en: 'How the app decides',
        fa: 'برنامه چطور تصمیم می‌گیرد',
        ar: 'كيف يقرّر التطبيق',
        zh: '这个应用是怎么判断的',
      },
      asks: [
        { en: 'How is my score calculated?', fa: 'امتیازم چطور محاسبه می‌شود؟', ar: 'كيف تُحسب درجتي؟', zh: '我的分数是怎么算出来的？' },
        { en: 'What does the confidence percentage mean?', fa: 'درصد اطمینان یعنی چه؟', ar: 'ماذا تعني نسبة الثقة؟', zh: '那个置信度百分比是什么意思？' },
      ],
    },

    // ----------------------------------------------------- per story
    {
      key: 'healthy_keep',
      profiles: ['healthy'],
      title: {
        en: 'Keeping a good run going',
        fa: 'ادامه دادن یک دوره‌ی خوب',
        ar: 'الحفاظ على فترة جيدة',
        zh: '把好状态延续下去',
      },
      asks: [
        { en: 'What are my strengths?', fa: 'نقطه‌ی قوتم چیست؟', ar: 'ما نقطة قوّتي؟', zh: '我的强项是什么？' },
        { en: 'I am proud of how this week went', fa: 'از هفته‌ای که گذشت راضی‌ام', ar: 'أنا فخور بكيف مرّ هذا الأسبوع', zh: '这一周过得让我挺自豪的' },
        { en: 'How do I build a habit that sticks?', fa: 'چطور عادتی بسازم که بماند؟', ar: 'كيف أبني عادة تدوم؟', zh: '怎么养成一个能坚持下来的习惯？' },
      ],
    },
    {
      key: 'improving_back',
      profiles: ['improving'],
      title: {
        en: 'Coming back from a bad stretch',
        fa: 'برگشتن از یک دوره‌ی بد',
        ar: 'العودة بعد فترة سيئة',
        zh: '从一段糟糕的时期走出来',
      },
      asks: [
        { en: 'I want to give up sometimes', fa: 'گاهی می‌خواهم بی‌خیال شوم', ar: 'أحياناً أريد أن أستسلم', zh: '有时候我真想放弃' },
        { en: 'What are my strengths?', fa: 'نقطه‌ی قوتم چیست؟', ar: 'ما نقطة قوّتي؟', zh: '我的强项是什么？' },
        { en: 'How do I build a habit that sticks?', fa: 'چطور عادتی بسازم که بماند؟', ar: 'كيف أبني عادة تدوم؟', zh: '怎么养成一个能坚持下来的习惯？' },
      ],
    },
    {
      key: 'borderline_edge',
      profiles: ['borderline'],
      title: {
        en: 'Why my class keeps moving',
        fa: 'چرا کلاسم مدام جابه‌جا می‌شود',
        ar: 'لماذا تتبدّل فئتي باستمرار',
        zh: '为什么我的类别一直在变',
      },
      asks: [
        { en: 'How is my score calculated?', fa: 'امتیازم چطور محاسبه می‌شود؟', ar: 'كيف تُحسب درجتي؟', zh: '我的分数是怎么算出来的？' },
        { en: 'Tell me about my sleep', fa: 'درباره‌ی خوابم بگو', ar: 'حدّثني عن نومي', zh: '说说我的睡眠' },
        { en: 'What should I change first?', fa: 'اول چه چیزی را عوض کنم؟', ar: 'ما الذي أغيّره أولاً؟', zh: '我该先改哪一件事？' },
      ],
    },
    {
      key: 'at_risk_down',
      profiles: ['at_risk'],
      title: {
        en: 'The number is going the wrong way',
        fa: 'عدد دارد اشتباه جلو می‌رود',
        ar: 'الرقم يسير في الاتجاه الخاطئ',
        zh: '这个数字在往错的方向走',
      },
      asks: [
        { en: 'Why am I rated this way?', fa: 'چرا امتیازم این شکلی است؟', ar: 'لماذا درجتي هكذا؟', zh: '我的分数为什么是这样？' },
        { en: 'I want to give up sometimes', fa: 'گاهی می‌خواهم بی‌خیال شوم', ar: 'أحياناً أريد أن أستسلم', zh: '有时候我真想放弃' },
        { en: 'What should I change first?', fa: 'اول چه چیزی را عوض کنم؟', ar: 'ما الذي أغيّره أولاً؟', zh: '我该先改哪一件事？' },
      ],
    },

    // ------------------------------------------------- the lapsed tick
    {
      key: 'lapsed_missed',
      lapsed: true,
      title: {
        en: 'The days I missed',
        fa: 'روزهایی که جا انداختم',
        ar: 'الأيام التي فوّتُّها',
        zh: '我漏掉的那些天',
      },
      asks: [
        { en: 'What happens if I miss a day of the plan?', fa: 'اگر یک روز برنامه را از دست بدهم چه می‌شود؟', ar: 'ماذا يحدث إن فوّتُّ يوماً من الخطة؟', zh: '如果我漏掉计划里的一天会怎样？' },
        { en: 'Why was a badge taken away from me?', fa: 'چرا نشانم گرفته شد؟', ar: 'لماذا سُحبت شارتي؟', zh: '我的徽章为什么被收走了？' },
        { en: 'What is a violation?', fa: 'تخلف یعنی چه؟', ar: 'ما هي المخالفة؟', zh: '违规是什么意思？' },
      ],
    },
    {
      key: 'lapsed_colours',
      lapsed: true,
      title: {
        en: 'Why some days are red',
        fa: 'چرا بعضی روزها قرمزند',
        ar: 'لماذا بعض الأيام حمراء',
        zh: '为什么有些天是红色的',
      },
      asks: [
        { en: 'What do the colours mean on the dashboard?', fa: 'رنگ روزها در داشبورد یعنی چه؟', ar: 'ماذا تعني ألوان الأيام في لوحة التحكم؟', zh: '仪表盘上日期的颜色是什么意思？' },
        { en: 'Is the penalty part of my wellness number?', fa: 'آن امتیاز منفی جزو نمره‌ی سلامتم است؟', ar: 'هل الخصم جزء من رقم عافيتي؟', zh: '那个扣分算在我的健康数值里吗？' },
      ],
    },
    {
      key: 'kept_up_plan',
      lapsed: false,
      title: {
        en: 'How the week is put together',
        fa: 'هفته چطور چیده شده',
        ar: 'كيف يُبنى الأسبوع',
        zh: '这一周是怎么安排的',
      },
      asks: [
        { en: 'Why must I do the days in order?', fa: 'چرا باید روزها را به ترتیب انجام دهم؟', ar: 'لماذا يجب أن أتبع ترتيب الأيام؟', zh: '为什么必须按顺序做？' },
        { en: 'What happens next week?', fa: 'هفته‌ی بعد چه می‌شود؟', ar: 'ماذا يحدث الأسبوع القادم؟', zh: '下周会怎样？' },
        { en: 'What do the colours mean on the dashboard?', fa: 'رنگ روزها در داشبورد یعنی چه؟', ar: 'ماذا تعني ألوان الأيام في لوحة التحكم؟', zh: '仪表盘上日期的颜色是什么意思？' },
      ],
    },
  ];

  /** Which threads belong to this state. */
  function scriptsFor(profile, lapsed) {
    return THREADS.filter((t) => {
      if (t.profiles && t.profiles.indexOf(profile) === -1) return false;
      if (t.lapsed === true && !lapsed) return false;
      if (t.lapsed === false && lapsed) return false;
      return true;
    });
  }

  function demoState() {
    if (!window.DWDemo || !window.DWDemo.state) return null;
    try { return window.DWDemo.state(); } catch (e) { return null; }
  }

  /* Spread the threads across the days this user has actually been
     using the app, oldest first, ending a day or so ago. A set of
     threads all stamped "just now" reads as generated; a set dated over
     three weeks reads as somebody who has been here. */
  function whenFor(index, count, days) {
    const span = Math.max(1, Math.min(days || 1, 60));
    const ago = Math.round(span * (1 - (index + 1) / (count + 1)));
    return Date.now() - ago * 86400000;
  }

  /**
   * Write this demo user's coach threads, if they are missing or were
   * written in a language the reviewer is no longer reading.
   *
   * Resolves to the number of threads written (0 when there was nothing
   * to do, which is the normal case for a real account).
   */
  async function ensure() {
    const state = demoState();
    if (!state) return 0;

    const store = window.DWCoachConversations;
    const chat = window.DWCoachChat;
    if (!store || !store.importThread || !chat || !chat.respond) return 0;

    const current = lang();
    const mine = store.listMarked(MARKER);
    if (mine.length && mine.every((c) => c.lang === current)) return 0;

    // The same two reads the send box does, so the answers below are
    // composed from exactly what a typed question would see.
    let full = null;
    if (window.DWCoachContext) {
      try { full = await window.DWCoachContext.load({ force: true }); } catch (e) { full = null; }
    }
    const ctx = chat.loadContext();
    // Nothing real to answer from. Seeding here would produce threads
    // full of "I don't have a check-in to work from yet", which is a
    // worse first impression than an empty list.
    //
    // `full` is not a useful truthiness test on its own: load() resolves
    // to enrich(cached || {}) and so hands back an object even when the
    // fetch failed outright. isEmpty() is the question actually being
    // asked - has this user logged anything - and it is the same one
    // the chat itself uses before deciding it has data to talk about.
    const digestEmpty = !full
      || !window.DWCoachContext
      || window.DWCoachContext.isEmpty(full);
    if (!ctx && digestEmpty) return 0;

    store.removeMarked(MARKER);

    const scripts = scriptsFor(state.profile, !!state.lapsed);
    let written = 0;
    scripts.forEach((script, i) => {
      const at = whenFor(i, scripts.length, state.days);
      const messages = [];
      script.asks.forEach((ask) => {
        const text = pick(ask);
        messages.push({ role: 'user', content: text });
        const reply = chat.respond(text, ctx, full);
        messages.push({ role: 'assistant', content: reply.text });
      });
      store.importThread({
        title: pick(script.title),
        messages,
        created_at: at,
        // The thread ran over a few minutes, like a real one.
        updated_at: at + messages.length * 60000,
        marker: MARKER,
        lang: current,
      });
      written += 1;
    });
    return written;
  }

  window.DWCoachDemoChats = { ensure, MARKER, THREADS, scriptsFor };
})();
