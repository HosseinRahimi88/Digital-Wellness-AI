/*
  D-10 — a letter from your future self.

  The document calls this the most sensitive text in the product, and it
  is: the "things are drifting" version is read by someone who already
  knows things are drifting. So the rules here are strict.

  What makes it not generic
  --------------------------
  Every letter is assembled from the reader's OWN numbers - their score
  range, their direction, their best day, the one field that moved most,
  how many days they have logged. A sentence with no real number behind it
  is dropped rather than padded with a vague one, so a thin history
  produces a short letter instead of a long empty one.

  The two versions
  ----------------
  They are genuinely different letters, not one template with an adjective
  swapped:

    * Encouraging - names what is holding and asks them to protect it.
    * Honest - names the drift plainly, WITHOUT apology and without
      catastrophe, then spends its last line on the single nearest thing
      they could do. It never predicts a bad outcome, never diagnoses,
      never implies the reader has failed at anything. The closing line is
      always forward-facing; that is the one structural rule that cannot
      be broken.

  There is no "you should" anywhere, and no medical framing of any kind.
*/
(function () {
  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);
  const label = (f) => ((window.DWCoachLabels || {})[f] || String(f || '').replace(/_/g, ' '));

  // Below this there is not enough of the reader's own history for the
  // letter to be about them rather than about nobody (G4). Seven, so the
  // letter can only arrive once a full week of the reader's own days
  // exists behind it.
  const MIN_DAYS = 7;

  // The letter is written as though sent from this far ahead. It is a
  // real date rather than a vague "a few weeks", because the whole
  // conceit is that a specific later day is looking back at this one -
  // and a date the reader can find on a calendar is what makes that land.
  const DAYS_AHEAD = 10;

  const LOCALE_FOR_LANG = { en: 'en-US', fa: 'fa-IR', ar: 'ar-SA', zh: 'zh-CN' };

  /** The dateline, in the reader's own calendar. Falls back to an ISO
   *  date if the locale is unavailable - a plain date still reads. */
  function datelineFor(from) {
    const d = new Date(from ? from.getTime() : Date.now());
    d.setDate(d.getDate() + DAYS_AHEAD);
    const lang = (window.DWI18n && window.DWI18n.get && window.DWI18n.get()) || 'en';
    try {
      return d.toLocaleDateString(LOCALE_FOR_LANG[lang] || 'en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
      });
    } catch (e) { return d.toISOString().slice(0, 10); }
  }

  const L = {
    openGood: {
      en: 'I am you, a few weeks from now. I wanted to write while it is still fresh.',
      fa: 'من تو هستم، چند هفته بعد. خواستم بنویسم تا هنوز تازه است.',
      ar: 'أنا أنت، بعد أسابيع قليلة. أردت أن أكتب بينما الأمر ما زال طازجاً.',
      zh: '我是几周之后的你。趁着记忆还新鲜，我想写点什么。',
    },
    openHonest: {
      en: 'I am you, a few weeks from now. This one is harder to write, so I will be straight with you.',
      fa: 'من تو هستم، چند هفته بعد. نوشتن این یکی سخت‌تر است، پس رک می‌گویم.',
      ar: 'أنا أنت، بعد أسابيع قليلة. كتابة هذه أصعب، لذا سأكون صريحاً معك.',
      zh: '我是几周之后的你。这一封更难写，所以我就直说了。',
    },
    logged: {
      en: 'You have logged {d} days. That is the part most people never do.',
      fa: '{d} روز ثبت کرده‌ای. این همان کاری است که بیشتر آدم‌ها هرگز نمی‌کنند.',
      ar: 'سجّلت {d} يوماً. هذا هو الجزء الذي لا يفعله معظم الناس أبداً.',
      zh: '你已经记录了 {d} 天。这正是大多数人从来不做的那一步。',
    },
    holdingGood: {
      en: 'Your recent days sit around {s}, and the direction has been upward. I remember that stretch — it did not feel like progress at the time, it just felt like ordinary days.',
      fa: 'روزهای اخیرت حول {s} است و جهت رو به بالا بوده. آن دوره را یادم است — آن موقع حس پیشرفت نداشت، فقط حس روزهای معمولی داشت.',
      ar: 'أيامك الأخيرة تدور حول {s}، وكان الاتجاه صاعداً. أتذكر تلك الفترة — لم تكن تبدو تقدماً حينها، بل مجرد أيام عادية.',
      zh: '你最近这些天大约在 {s} 左右，方向一直向上。我记得那段时间——当时并不觉得那是进步，只觉得是普通的日子。',
    },
    holdingHonest: {
      en: 'Your recent days sit around {s}, and the direction has been downward. I am not going to dress that up.',
      fa: 'روزهای اخیرت حول {s} است و جهت رو به پایین بوده. نمی‌خواهم قشنگش کنم.',
      ar: 'أيامك الأخيرة تدور حول {s}، وكان الاتجاه هابطاً. لن أُجمّل ذلك.',
      zh: '你最近这些天大约在 {s} 左右，方向一直在下行。我不打算把这件事说得好听。',
    },
    bestDay: {
      en: 'Your best day was {day}, at {score}. It was not luck — you can look at what that day actually contained.',
      fa: 'بهترین روزت {day} بود، با {score}. شانس نبود — می‌توانی نگاه کنی آن روز واقعاً چه چیزی داشت.',
      ar: 'كان أفضل أيامك {day}، عند {score}. لم يكن حظاً — يمكنك النظر إلى ما احتواه ذلك اليوم فعلاً.',
      zh: '你最好的一天是 {day}，{score} 分。那不是运气——你可以去看看那天究竟包含了什么。',
    },
    movedMost: {
      en: 'The thing that moved most in your favour was {field}. That is the thread worth pulling.',
      fa: 'چیزی که بیشترین حرکت را به نفعت داشت {field} بود. همان نخی است که ارزش کشیدن دارد.',
      ar: 'أكثر ما تحرّك لصالحك كان {field}. هذا هو الخيط الذي يستحق أن تسحبه.',
      zh: '对你最有利的变化是 {field}。这就是值得往下拉的那根线。',
    },
    closeGood: {
      en: 'Nothing here needs a grand plan. Protect the one thing that is already working, and I will keep having good news to write about.',
      fa: 'اینجا هیچ‌چیز به نقشه‌ی بزرگ نیاز ندارد. همان یک چیزی را که دارد کار می‌کند حفظ کن، و من همچنان خبر خوب برای نوشتن خواهم داشت.',
      ar: 'لا شيء هنا يحتاج إلى خطة كبرى. احمِ الشيء الوحيد الذي ينجح بالفعل، وسأظل أملك أخباراً جيدة لأكتب عنها.',
      zh: '这里没有什么需要宏大的计划。守住那件已经在起作用的事，我就会一直有好消息可写。',
    },
    closeHonest: {
      en: 'Here is the only thing I would ask: change one small thing at the next check-in — not five. The next entry is the only one you can still affect, and that is genuinely enough to turn a line around.',
      fa: 'تنها چیزی که می‌خواهم این است: در بررسی بعدی یک چیز کوچک را عوض کن — نه پنج تا. تنها ورودی‌ای که هنوز می‌توانی رویش اثر بگذاری، بعدی است، و همین واقعاً برای برگرداندن یک خط کافی است.',
      ar: 'الشيء الوحيد الذي أطلبه: غيّر شيئاً صغيراً واحداً في التسجيل القادم — لا خمسة. التسجيل التالي هو الوحيد الذي ما زال بإمكانك التأثير فيه، وهذا يكفي فعلاً لتغيير مسار خط.',
      zh: '我只想请你做一件事：在下一次记录时改变一件小事——不是五件。下一条记录是你唯一还能影响的，而这真的足以让一条曲线转向。',
    },
    signOff: { en: '— You, later', fa: '— تو، بعدتر', ar: '— أنت، لاحقاً', zh: '——以后的你' },
    title: { en: 'A letter from you, later', fa: 'نامه‌ای از تو، بعدتر', ar: 'رسالة منك، لاحقاً', zh: '来自以后的你的一封信' },
    open: { en: 'Open the letter', fa: 'باز کردن نامه', ar: 'افتح الرسالة', zh: '打开这封信' },
  };

  /**
   * Build the letter from the reader's own figures.
   * ctx: { days, recentScore, direction, bestDay, bestScore, improvedField }
   * Returns null when there is not enough history to write about them.
   */
  function compose(ctx) {
    ctx = ctx || {};
    if (!ctx.days || ctx.days < MIN_DAYS) return null;

    const good = ctx.direction !== 'down';
    const lines = [];
    lines.push(pick(good ? L.openGood : L.openHonest));
    lines.push(pick(L.logged).replace('{d}', ctx.days));

    if (typeof ctx.recentScore === 'number') {
      lines.push(pick(good ? L.holdingGood : L.holdingHonest)
        .replace('{s}', Math.round(ctx.recentScore)));
    }
    if (ctx.bestDay && typeof ctx.bestScore === 'number') {
      lines.push(pick(L.bestDay).replace('{day}', ctx.bestDay).replace('{score}', Math.round(ctx.bestScore)));
    }
    if (ctx.improvedField) {
      lines.push(pick(L.movedMost).replace('{field}', label(ctx.improvedField)));
    }

    // Structural rule: the letter always ends looking forward.
    lines.push(pick(good ? L.closeGood : L.closeHonest));

    return {
      tone: good ? 'encouraging' : 'honest',
      lines,
      signOff: pick(L.signOff),
      title: pick(L.title),
      dateline: datelineFor(ctx.now),
    };
  }

  /** Build the ctx from what the insight endpoints already return, so the
   *  letter never needs its own data source. */
  function contextFrom(cards, trendDirection) {
    const n = (cards && cards.narrative) || null;
    const f = (cards && cards.first_vs_now) || null;
    if (!n) return null;
    return {
      days: n.days,
      recentScore: f ? f.recent_avg : n.avg_score,
      direction: trendDirection || (f ? (f.improved ? 'up' : 'down') : 'flat'),
      bestDay: n.best_day,
      bestScore: n.best_score,
      improvedField: n.most_improved_field,
    };
  }

  function render(letter, mount) {
    if (!letter || !mount) return false;
    // Text nodes, not innerHTML: every line is assembled from the
    // reader's own stored values (their best day's name among them), and
    // those must never be able to reach the page as markup.
    mount.innerHTML = '';

    const scene = document.createElement('div');
    scene.className = 'letter-scene';

    // The envelope: flap, body, and the sheet that rises out of it. It is
    // pure decoration and carries no text of its own, so a reader who
    // never sees it animate loses nothing.
    const envelope = document.createElement('div');
    envelope.className = 'letter-envelope';
    envelope.setAttribute('aria-hidden', 'true');
    envelope.innerHTML = '<span class="env-back"></span><span class="env-body"></span>'
      + '<span class="env-flap"></span><span class="env-seal">✦</span>';
    scene.appendChild(envelope);

    const card = document.createElement('div');
    card.className = `letter-card is-${letter.tone}`;

    const h = document.createElement('h4');
    h.textContent = letter.title;
    card.appendChild(h);

    if (letter.dateline) {
      // The date this is written from - the reason the letter reads as
      // arriving from a specific later day rather than from nowhere.
      const dl = document.createElement('p');
      dl.className = 'letter-dateline';
      dl.textContent = letter.dateline;
      card.appendChild(dl);
    }

    const body = document.createElement('div');
    body.className = 'letter-body';
    letter.lines.forEach((line) => {
      const p = document.createElement('p');
      p.textContent = line;
      body.appendChild(p);
    });
    card.appendChild(body);

    const sign = document.createElement('p');
    sign.className = 'letter-sign';
    sign.textContent = letter.signOff;
    card.appendChild(sign);

    scene.appendChild(card);
    mount.appendChild(scene);

    // G7: the envelope flourish is motion only; the text is identical
    // either way, so reduced motion loses nothing but the animation. It
    // also has to end with the letter READABLE - a sequence that leaves
    // the sheet inside the envelope would hide the whole point.
    if (window.DWMotion && window.DWMotion.prefersReduced()) {
      scene.classList.add('letter-instant');
    } else {
      scene.classList.add('letter-sealed');
      requestAnimationFrame(() => {
        scene.classList.add('letter-opening');
        if (window.DWSound && window.DWSound.ding) window.DWSound.ding();
      });
      // Belt and braces: if the animation never fires (background tab,
      // an interrupted transition), the letter still ends up open.
      setTimeout(() => {
        scene.classList.remove('letter-sealed');
        scene.classList.add('letter-instant');
      }, 2200);
    }
    if (window.DWMotion && window.DWMotion.prefersReduced()
        && window.DWSound && window.DWSound.ding) {
      window.DWSound.ding();
    }
    return true;
  }

  window.DWFutureLetter = {
    compose, contextFrom, render, datelineFor, MIN_DAYS, DAYS_AHEAD, L,
  };
})();
