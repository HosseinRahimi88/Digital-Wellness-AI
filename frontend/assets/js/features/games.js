/*
  Section E - the small interactions.

  Eleven now, all following the same shape: each uses the user's OWN
  data, is answerable in under a minute, and teaches something about how
  the score works rather than being a quiz for its own sake.

    guess_score      You commit to a number before the score is
                     revealed. The one that makes a person actually
                     look at their own day instead of scrolling past
                     it, and the cheapest to get right.
    which_factor     Two real SHAP factors from your own result; you
                     pick which one moved the score more. This is the
                     app's central claim - "explainable" - turned into
                     something you do rather than read.
    baseline_or_exception  The only one here that improves the product
                     itself. Labelling a day as an exception feeds
                     every baseline, every streak and every awareness
                     indicator, and it is work only the user can do.
    fill_the_blank   A relationship found in your own history with one
                     side hidden. Uses the same Bonferroni-corrected
                     correlation the insight card uses, so it can never
                     quiz you on a coincidence.
    keep_the_streak  Your real streak, and what it actually costs to
                     miss a day - which in this app is a shortening,
                     never a reset.
    dimension_duel   Two dimensions from the transparent, non-ML
                     breakdown - the app's OTHER explanation, separate
                     from SHAP, so this teaches that the two views exist
                     and can be checked against each other.
    confidence_guess Guess whether the model sounds sure of itself
                     before seeing the percentage. Teaches that
                     confidence is a real, separate number - not a proxy
                     for whether the score is good or bad.
    future_class_guess  Guess the seven-day-ahead class before it is
                     shown. Teaches the thing this app got wrong before
                     it was fixed: today's score and the seven-day class
                     are two different models, not one number read twice.
    weekday_or_weekend  Which one scores higher across your own logged
                     days - the same weekday_vs_weekend figure Analytics
                     computes, never recomputed here.
    badge_race       Which of two unearned badges you are closer to.
                     Never a private awareness indicator (G1) - only
                     achievement badges your own history can answer.
    score_vs_average Today against your own historical average, not
                     against 50 or anyone else's number - the same
                     "your own baseline" idea baseline_or_exception is
                     built on, from the other direction.

  The global rules (G1-G9) are enforced here rather than per game:

    G1  No medical claim anywhere. Nothing in this file names a
        condition, and no answer text tells anyone what to do about
        their health.
    G2  Every card is dismissible and nothing blocks the page.
    G3  Dismissal is remembered, sharing DWGuide's fatigue store, so
        "stop showing me this" means the same thing across the whole
        app rather than per subsystem.
    G4  A game whose data is not sufficient does not render at all -
        no skeleton, no "come back later" placeholder. Each game
        declares `eligible(context)` and that is the only gate.
    G5  The tone never condescends and never scolds. A wrong guess is
        answered with the real number and why, never with a "nope".
    G6  All four languages, RTL included, numbers isolated LTR.
    G7  Reduced motion simplifies - the reveal still happens, without
        the animation.
    G8  No model output is ever altered. Games read the same values the
        rest of the page shows; nothing here re-scores anything.
    G9  Anything persisted goes through the existing data layer
        (DWApi), never a parallel store. Only per-game local state -
        which is UI state - lives in localStorage.
*/
(function () {
  const DISMISS_PREFIX = 'dwai_guide_dismiss_';   // shared with DWGuide (G3)
  const SHOWN_PREFIX = 'dwai_guide_shown_';
  const PLAYED_PREFIX = 'dwai_game_played_';
  const DISMISSALS_BEFORE_QUIET = 2;
  const QUIET_DAYS = 14;
  const DAY_MS = 86400000;
  const ENABLED_KEY = 'dwai_games_enabled';       // Settings > Games after a check-in

  /* On by default - an opt-OUT switch, same convention as sound/motion.
     Absent/anything but the literal string "0" reads as on, so a stray
     localStorage clear (or a browser that blocks it) fails open rather
     than silently turning games off for everyone. */
  function isEnabled() { return localStorage.getItem(ENABLED_KEY) !== '0'; }
  function setEnabled(on) { try { localStorage.setItem(ENABLED_KEY, on ? '1' : '0'); } catch (e) {} }

  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : (t && t.en) || '');

  function num(v) {
    const span = document.createElement('span');
    span.dir = 'ltr';
    span.style.unicodeBidi = 'isolate';
    span.textContent = String(v);
    return span.outerHTML;
  }

  const T = {
    sectionTitle: { en: 'Try one', fa: 'یکی را امتحان کن', ar: 'جرّب واحدة', zh: '来试一个' },
    dismiss: { en: 'Dismiss', fa: 'بستن', ar: 'إغلاق', zh: '关闭' },
    skip: { en: 'Just show me', fa: 'فقط نشانم بده', ar: 'أرني فحسب', zh: '直接告诉我' },
    submit: { en: 'Lock it in', fa: 'ثبت کن', ar: 'ثبّتها', zh: '确定' },
    playAgainNote: {
      en: 'Come back tomorrow — this one only means something once a day.',
      fa: 'فردا برگرد — این یکی فقط روزی یک بار معنا دارد.',
      ar: 'عد غداً — هذه لا تعني شيئاً إلا مرة واحدة في اليوم.',
      zh: '明天再来——这个每天只玩一次才有意义。',
    },
  };

  /* ---- G3: fatigue, shared with the guide ------------------------- */
  function readInt(key) {
    const raw = localStorage.getItem(key);
    const n = raw == null ? 0 : parseInt(raw, 10);
    return Number.isFinite(n) ? n : 0;
  }

  function isQuiet(key) {
    if (readInt(DISMISS_PREFIX + key) < DISMISSALS_BEFORE_QUIET) return false;
    return Date.now() - readInt(SHOWN_PREFIX + key) < QUIET_DAYS * DAY_MS;
  }

  function noteDismissed(key) {
    if (window.DWGuide && window.DWGuide.noteDismissed) {
      window.DWGuide.noteDismissed(key);
      return;
    }
    try { localStorage.setItem(DISMISS_PREFIX + key, String(readInt(DISMISS_PREFIX + key) + 1)); } catch (e) {}
  }

  function playedToday(key) {
    const raw = localStorage.getItem(PLAYED_PREFIX + key);
    return raw === new Date().toISOString().slice(0, 10);
  }

  function markPlayed(key) {
    try { localStorage.setItem(PLAYED_PREFIX + key, new Date().toISOString().slice(0, 10)); } catch (e) {}
  }

  /* ---- shared card shell ------------------------------------------ */
  function card(game, bodyHtml) {
    const el = document.createElement('div');
    el.className = 'game-card';
    el.dataset.gameKey = game.key;
    el.innerHTML = `
      <button type="button" class="game-dismiss" aria-label="${pick(T.dismiss)}" title="${pick(T.dismiss)}">×</button>
      <div class="game-head">
        <span class="game-icon" aria-hidden="true">${game.icon}</span>
        <h4>${pick(game.title)}</h4>
      </div>
      <div class="game-body">${bodyHtml}</div>`;
    el.querySelector('.game-dismiss').addEventListener('click', () => {
      noteDismissed(game.key);
      el.remove();
      if (window.DWSound && window.DWSound.toggleOff) window.DWSound.toggleOff();
    });
    try { localStorage.setItem(SHOWN_PREFIX + game.key, String(Date.now())); } catch (e) {}
    return el;
  }

  /* G5: the answer is always the real number and the reason for it.
     "Close" and "not close" get the same information, only the opening
     clause differs - being wrong is not a thing to be told off about. */
  function verdict(el, closeEnough, headline, explanation) {
    const box = document.createElement('div');
    box.className = 'game-verdict ' + (closeEnough ? 'is-close' : 'is-far');
    box.innerHTML = `<p class="game-verdict-head">${headline}</p><p>${explanation}</p>`;
    el.querySelector('.game-body').appendChild(box);
    if (window.DWSound) {
      if (closeEnough && window.DWSound.success) window.DWSound.success();
      else if (window.DWSound.click) window.DWSound.click();
    }
    const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduced) box.classList.add('is-revealing');   // G7
  }

  // =================================================================
  // 1. Guess your score
  // =================================================================
  const guessScore = {
    key: 'game_guess_score',
    // pre: reveals ctx.score itself, so it only makes sense before the
    // result view has shown that number anywhere else on the page.
    phase: 'pre',
    icon: '🎯',
    title: { en: 'Before you look', fa: 'قبل از اینکه نگاه کنی', ar: 'قبل أن تنظر', zh: '在你看之前' },
    guideTopic: 'game_guess_score',
    eligible: (ctx) => ctx.score != null && !playedToday('game_guess_score'),
    render(ctx) {
      const lead = {
        en: 'You just logged a day. What do you think it scored, out of 100?',
        fa: 'همین حالا یک روز را ثبت کردی. فکر می‌کنی چند از ۱۰۰ گرفته؟',
        ar: 'سجّلت للتو يوماً. كم تظن أنه سجّل من 100؟',
        zh: '你刚记录了一天。你觉得它拿了多少分（满分 100）？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <div class="game-guess-row">
          <input type="range" min="0" max="100" value="50" class="game-slider" aria-label="${pick(this.title)}">
          <output class="game-guess-value" dir="ltr">50</output>
        </div>
        <div class="game-actions">
          <button type="button" class="btn btn-primary btn-sm game-submit">${pick(T.submit)}</button>
          <button type="button" class="btn btn-ghost btn-sm game-skip">${pick(T.skip)}</button>
        </div>`);

      const slider = el.querySelector('.game-slider');
      const out = el.querySelector('.game-guess-value');
      slider.addEventListener('input', () => { out.textContent = slider.value; });

      const reveal = (guess) => {
        markPlayed(this.key);
        el.querySelector('.game-actions').remove();
        el.querySelector('.game-guess-row').classList.add('is-locked');
        const actual = Math.round(ctx.score);
        if (guess == null) {
          verdict(el, true,
            pick({ en: `It scored ${actual}.`, fa: `امتیازش ${actual} شد.`, ar: `سجّل ${actual}.`, zh: `它的分数是 ${actual}。` }),
            pick({
              en: 'No guess, no problem — the number is the same either way.',
              fa: 'حدسی نزدی، مشکلی نیست — عدد در هر صورت همان است.',
              ar: 'لا تخمين، لا مشكلة — الرقم هو نفسه في الحالتين.',
              zh: '没猜也没关系——数字都是一样的。',
            }));
          return;
        }
        const gap = Math.abs(actual - guess);
        const close = gap <= 7;
        const headline = close
          ? pick({ en: `You said ${guess}. It was ${actual}.`, fa: `تو گفتی ${guess}. عدد ${actual} بود.`,
                   ar: `قلت ${guess}. وكان ${actual}.`, zh: `你说 ${guess}。实际是 ${actual}。` })
          : pick({ en: `You said ${guess}. It was ${actual}.`, fa: `تو گفتی ${guess}. عدد ${actual} بود.`,
                   ar: `قلت ${guess}. وكان ${actual}.`, zh: `你说 ${guess}。实际是 ${actual}。` });
        const explanation = close
          ? pick({
              en: 'Within seven points. Knowing roughly how a day went before a model tells you is the whole skill here — most people are off by far more than that at first.',
              fa: 'کمتر از هفت امتیاز اختلاف. اینکه تقریباً بدانی روزت چطور بوده پیش از آنکه مدلی بگوید، تمام مهارت این کار است — بیشتر آدم‌ها اولش خیلی بیشتر از این خطا دارند.',
              ar: 'ضمن سبع نقاط. أن تعرف تقريباً كيف مضى يومك قبل أن يخبرك نموذج هو المهارة كلها هنا — معظم الناس يخطئون بأكثر من ذلك بكثير في البداية.',
              zh: '相差在七分以内。在模型开口之前就大致知道自己这一天过得如何，这就是这里全部的本事——大多数人一开始差得远比这多。',
            })
          : pick({
              en: 'That gap is the interesting part, not a mistake. It usually means one signal — sleep, or how scattered the day was — weighed more than it felt like at the time.',
              fa: 'همین فاصله نکته‌ی جالب ماجراست، نه یک اشتباه. معمولاً یعنی یک سیگنال — خواب، یا اینکه روز چقدر پراکنده بوده — بیشتر از آنچه در لحظه حس می‌شد وزن داشته.',
              ar: 'هذه الفجوة هي الجزء المثير للاهتمام، لا خطأ. تعني عادةً أن إشارة واحدة — النوم، أو مدى تشتت اليوم — كان وزنها أكبر مما بدا وقتها.',
              zh: '这个差距才是有意思的地方，不是失误。它通常意味着某一个信号——睡眠，或者这一天有多零散——的分量比当时感觉到的更重。',
            });
        verdict(el, close, headline, explanation);
      };

      el.querySelector('.game-submit').addEventListener('click', () => reveal(parseInt(slider.value, 10)));
      el.querySelector('.game-skip').addEventListener('click', () => reveal(null));
      return el;
    },
  };

  // =================================================================
  // 2. Which factor mattered more (SHAP)
  // =================================================================
  const whichFactor = {
    key: 'game_which_factor',
    // post: compares two SHAP factors, not the score itself - meant to
    // be explored once the reader has already seen their result.
    phase: 'post',
    icon: '⚖️',
    title: { en: 'Which one weighed more?', fa: 'کدام‌یک وزن بیشتری داشت؟', ar: 'أيهما كان أثقل؟', zh: '哪一个分量更重？' },
    guideTopic: 'game_which_factor',
    eligible: (ctx) => Array.isArray(ctx.shapFeatures) && ctx.shapFeatures.length >= 2,
    render(ctx) {
      /* Two real factors from this user's own explanation, picked so
         the answer is not a coin flip: the top one, and the first one
         whose magnitude is meaningfully smaller. G8 - these are the
         same numbers the SHAP panel above is drawing. */
      const sorted = [...ctx.shapFeatures].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value));
      const top = sorted[0];
      const other = sorted.find((f) => Math.abs(top.shap_value) - Math.abs(f.shap_value) > Math.abs(top.shap_value) * 0.25);
      if (!other) return null;   // too close to be a fair question (G4)

      const label = (f) => (window.DWCoachLabels && window.DWCoachLabels[f.feature])
        || String(f.feature || '').replace(/_/g, ' ');
      const options = Math.random() < 0.5 ? [top, other] : [other, top];

      const lead = {
        en: 'Both of these moved your score today. Which one moved it more?',
        fa: 'هر دوی این‌ها امروز امتیازت را جابه‌جا کردند. کدام‌یک بیشتر؟',
        ar: 'كلاهما حرّك درجتك اليوم. أيهما حرّكها أكثر؟',
        zh: '这两项今天都影响了你的分数。哪一个影响更大？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <div class="game-choices">
          ${options.map((f, i) => `<button type="button" class="game-choice" data-i="${i}">${label(f)}</button>`).join('')}
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          const chosen = options[parseInt(btn.dataset.i, 10)];
          const correct = chosen === top;
          el.querySelectorAll('.game-choice').forEach((b, i) => {
            b.disabled = true;
            b.classList.add(options[i] === top ? 'is-answer' : 'is-other');
          });
          const dir = (f) => (f.shap_value >= 0
            ? pick({ en: 'pushed it up', fa: 'آن را بالا برد', ar: 'رفعها', zh: '把它推高' })
            : pick({ en: 'pulled it down', fa: 'آن را پایین کشید', ar: 'خفضها', zh: '把它拉低' }));
          verdict(el, correct,
            correct
              ? pick({ en: 'That is the one.', fa: 'همان است.', ar: 'هي تلك.', zh: '正是它。' })
              : pick({ en: `It was ${label(top)}.`, fa: `${label(top)} بود.`, ar: `كانت ${label(top)}.`, zh: `是 ${label(top)}。` }),
            `${label(top)} ${dir(top)} ${num(Math.abs(top.shap_value).toFixed(2))}, ${label(other)} ${dir(other)} ${num(Math.abs(other.shap_value).toFixed(2))}. `
            + pick({
                en: 'These are the model’s own numbers from the explanation above — not a rule someone wrote.',
                fa: 'این‌ها اعداد خودِ مدل از توضیح بالاست — نه قاعده‌ای که کسی نوشته باشد.',
                ar: 'هذه أرقام النموذج نفسه من التفسير أعلاه — لا قاعدة كتبها أحد.',
                zh: '这些是上面那段解释里模型自己的数字——不是谁写下的规则。',
              }));
        });
      });
      return el;
    },
  };

  // =================================================================
  // 3. Baseline or exception
  // =================================================================
  const baselineOrException = {
    key: 'game_baseline_or_exception',
    // post: labels a past day, not today's own result - fits after the
    // reader has seen today's number and is looking at it in context.
    phase: 'post',
    icon: '🏷️',
    title: { en: 'Ordinary day, or not?', fa: 'یک روز معمولی، یا نه؟', ar: 'يوم عادي، أم لا؟', zh: '普通的一天，还是不是？' },
    guideTopic: 'game_baseline_or_exception',
    /* Needs a real recent day that has NOT already been labelled, and
       enough history behind it for the label to matter. */
    eligible: (ctx) => !!ctx.unlabelledDay && (ctx.entryCount || 0) >= 5,
    render(ctx) {
      const day = ctx.unlabelledDay;
      const lead = {
        en: 'This is the one job the app cannot do for itself. Was that day a normal one for you?',
        fa: 'این تنها کاری است که برنامه نمی‌تواند خودش انجام دهد. آن روز برایت روزی معمولی بود؟',
        ar: 'هذه المهمة الوحيدة التي لا يستطيع التطبيق أداءها بنفسه. هل كان ذلك اليوم عادياً بالنسبة لك؟',
        zh: '这是应用自己做不了的唯一一件事。那一天对你来说是普通的一天吗？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <p class="game-subject"><strong dir="ltr">${day.date}</strong> · ${num(Math.round(day.health_score))}</p>
        <div class="game-choices">
          <button type="button" class="game-choice" data-answer="normal">${pick({ en: 'A normal day', fa: 'یک روز معمولی', ar: 'يوم عادي', zh: '普通的一天' })}</button>
          <button type="button" class="game-choice" data-answer="exception">${pick({ en: 'Not a normal day', fa: 'روز معمولی نبود', ar: 'لم يكن يوماً عادياً', zh: '不是普通的一天' })}</button>
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const isException = btn.dataset.answer === 'exception';
          el.querySelectorAll('.game-choice').forEach((b) => { b.disabled = true; });
          try {
            // G9: through the existing endpoint, into the real history -
            // this genuinely changes every baseline the app computes.
            if (isException && window.DWApi && window.DWApi.setHistoryExcluded) {
              await window.DWApi.setHistoryExcluded(day.date, true);
            }
            verdict(el, true,
              isException
                ? pick({ en: 'Marked as an exception.', fa: 'به‌عنوان استثنا علامت خورد.', ar: 'وُضعت علامة استثناء.', zh: '已标记为例外。' })
                : pick({ en: 'Left in.', fa: 'در محاسبات ماند.', ar: 'بقي محسوباً.', zh: '保留在计算中。' }),
              isException
                ? pick({
                    en: 'It stays in your history, but it is out of every average, streak and pattern from now on. That is the single most useful thing you can tell this app.',
                    fa: 'در سابقه‌ات می‌ماند، اما از این به بعد از هر میانگین و زنجیره و الگویی بیرون است. این مفیدترین چیزی است که می‌توانی به این برنامه بگویی.',
                    ar: 'يبقى في سجلك، لكنه خارج كل متوسط وسلسلة ونمط من الآن فصاعداً. هذا أنفع شيء يمكنك إخبار هذا التطبيق به.',
                    zh: '它仍留在你的历史里，但从现在起会被排除在每一个平均值、连续记录和模式之外。这是你能告诉这个应用的最有用的一件事。',
                  })
                : pick({
                    en: 'Then it counts, and your baselines just got a little more accurate for it.',
                    fa: 'پس حساب می‌شود، و خط پایه‌هایت با همین کمی دقیق‌تر شدند.',
                    ar: 'إذاً فهو محسوب، وخطوط أساسك صارت أدق قليلاً بفضله.',
                    zh: '那它就算数，而你的基线也因此稍微更准确了一点。',
                  }));
          } catch (e) {
            verdict(el, false,
              pick({ en: 'That did not save.', fa: 'ذخیره نشد.', ar: 'لم يُحفظ ذلك.', zh: '没有保存成功。' }),
              pick({ en: 'You can set it from the dashboard heatmap instead.', fa: 'می‌توانی از نقشه‌ی حرارتی داشبورد تنظیمش کنی.', ar: 'يمكنك ضبطه من الخريطة الحرارية في لوحة التحكم.', zh: '你可以改从仪表盘的热力图里设置。' }));
          }
        });
      });
      return el;
    },
  };

  // =================================================================
  // 4. Fill in the blank
  // =================================================================
  const fillTheBlank = {
    key: 'game_fill_the_blank',
    // post: a historical correlation, not today's own number.
    phase: 'post',
    icon: '🧩',
    title: { en: 'Finish the sentence', fa: 'جمله را کامل کن', ar: 'أكمل الجملة', zh: '把这句话补完' },
    guideTopic: 'game_fill_the_blank',
    /* Only ever asks about a relationship that survived the insight
       service's own significance test - so it cannot quiz anyone on a
       coincidence (G4, and the same statistics as the insight card). */
    eligible: (ctx) => !!(ctx.correlation && ctx.correlation.field_a && ctx.correlation.field_b),
    render(ctx) {
      const c = ctx.correlation;
      const label = (f) => (window.DWCoachLabels && window.DWCoachLabels[f]) || String(f || '').replace(/_/g, ' ');
      const lead = {
        en: 'In your own logged days, one of these two moved with the other. Which way?',
        fa: 'در روزهایی که خودت ثبت کرده‌ای، یکی از این دو با دیگری حرکت کرده. به کدام سمت؟',
        ar: 'في أيامك المسجَّلة، تحرّك أحد هذين مع الآخر. في أي اتجاه؟',
        zh: '在你自己记录的日子里，这两者之一是随着另一个一起变化的。朝哪个方向？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <p class="game-sentence">
          <strong>${label(c.field_a)}</strong>
          <span class="game-blank">?</span>
          <strong>${label(c.field_b)}</strong>
        </p>
        <div class="game-choices">
          <button type="button" class="game-choice" data-answer="together">${pick({ en: 'moved together with', fa: 'هم‌جهت حرکت کرده با', ar: 'تحرّك مع', zh: '同向变化于' })}</button>
          <button type="button" class="game-choice" data-answer="opposite">${pick({ en: 'moved opposite to', fa: 'در جهت مخالف حرکت کرده با', ar: 'تحرّك عكس', zh: '反向变化于' })}</button>
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          const correct = btn.dataset.answer === c.direction;
          el.querySelectorAll('.game-choice').forEach((b) => {
            b.disabled = true;
            b.classList.add(b.dataset.answer === c.direction ? 'is-answer' : 'is-other');
          });
          el.querySelector('.game-blank').textContent = btn.dataset.answer === c.direction
            ? btn.textContent : el.querySelector('.game-choice.is-answer').textContent;
          verdict(el, correct,
            correct
              ? pick({ en: 'That is what your days show.', fa: 'روزهای تو همین را نشان می‌دهند.', ar: 'هذا ما تُظهره أيامك.', zh: '你的日子显示的正是这样。' })
              : pick({ en: 'It went the other way.', fa: 'برعکس بوده.', ar: 'كان الاتجاه الآخر.', zh: '方向是反过来的。' }),
            pick({
              en: `Seen across ${c.sample_size} of your own days. Two things moving together is not one causing the other — it is a pattern worth noticing, nothing more.`,
              fa: `در ${c.sample_size} روز از روزهای خودت دیده شده. حرکت هم‌زمان دو چیز یعنی یکی باعث دیگری نیست — فقط الگویی است که ارزش دیدن دارد، همین.`,
              ar: `لوحظ عبر ${c.sample_size} من أيامك أنت. تحرّك شيئين معاً لا يعني أن أحدهما يسبب الآخر — إنه نمط يستحق الملاحظة، لا أكثر.`,
              zh: `这是在你自己的 ${c.sample_size} 天里观察到的。两件事一起变化并不意味着其中一个导致了另一个——它只是一个值得注意的模式，仅此而已。`,
            }));
        });
      });
      return el;
    },
  };

  // =================================================================
  // 5. Keep the streak
  // =================================================================
  const keepTheStreak = {
    key: 'game_keep_the_streak',
    // post: about the streak, not today's own score.
    phase: 'post',
    icon: '🔥',
    title: { en: 'Your chain', fa: 'زنجیره‌ی تو', ar: 'سلسلتك', zh: '你的连续记录' },
    guideTopic: 'game_keep_the_streak',
    eligible: (ctx) => ctx.streak && (ctx.streak.current_streak || 0) >= 1,
    render(ctx) {
      const s = ctx.streak;
      const current = s.current_streak || 0;
      const grace = s.grace_days_remaining;
      const el = card(this, `
        <p class="game-streak-value">${num(current)}</p>
        <p>${pick({
          en: 'days in a row above your healthy-day line.',
          fa: 'روز پیاپی بالاتر از خط روز سالمت.',
          ar: 'أيام متتالية فوق خط يومك الصحي.',
          zh: '天连续高于你的健康日基准线。',
        })}</p>
        <div class="game-choices">
          <button type="button" class="game-choice" data-answer="zero">${pick({ en: 'A miss resets it to zero', fa: 'یک روز خالی صفرش می‌کند', ar: 'يوم فائت يصفّرها', zh: '错过一天会归零' })}</button>
          <button type="button" class="game-choice" data-answer="shorten">${pick({ en: 'A miss only shortens it', fa: 'یک روز خالی فقط کوتاهش می‌کند', ar: 'يوم فائت يقصّرها فقط', zh: '错过一天只会缩短它' })}</button>
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          const correct = btn.dataset.answer === 'shorten';
          el.querySelectorAll('.game-choice').forEach((b) => {
            b.disabled = true;
            b.classList.add(b.dataset.answer === 'shorten' ? 'is-answer' : 'is-other');
          });
          const graceLine = (grace != null)
            ? ' ' + pick({
                en: `You have ${grace} absorbed miss(es) left this month before it costs anything at all.`,
                fa: `این ماه ${grace} روز جبرانی برایت مانده، پیش از آنکه اصلاً هزینه‌ای داشته باشد.`,
                ar: `لديك ${grace} من الأيام الفائتة الممتصّة هذا الشهر قبل أن يكلفك ذلك شيئاً أصلاً.`,
                zh: `这个月你还有 ${grace} 次被吸收的错过，在那之前它完全不会有任何代价。`,
              })
            : '';
          verdict(el, correct,
            correct
              ? pick({ en: 'Right — it shortens.', fa: 'درست است — کوتاه می‌شود.', ar: 'صحيح — تقصر.', zh: '对——它会缩短。' })
              : pick({ en: 'It only shortens.', fa: 'فقط کوتاه می‌شود.', ar: 'إنها تقصر فقط.', zh: '它只会缩短。' }),
            pick({
              en: 'Zeroing weeks of real progress over one ordinary bad day is punishment dressed up as a metric, and it is the moment most people quit. So a miss costs a few days, not everything — and a day you marked as an exception costs nothing.',
              fa: 'صفرکردن هفته‌ها پیشرفت واقعی به‌خاطر یک روز بدِ معمولی، تنبیهی است که لباس معیار پوشیده، و همان لحظه‌ای است که بیشتر آدم‌ها رها می‌کنند. پس یک روز خالی چند روز هزینه دارد، نه همه‌چیز — و روزی که استثنا علامت زده‌ای هیچ هزینه‌ای ندارد.',
              ar: 'تصفير أسابيع من التقدّم الحقيقي بسبب يوم سيئ عادي عقابٌ متنكّر في هيئة مقياس، وهو اللحظة التي ينسحب فيها معظم الناس. لذا اليوم الفائت يكلّف بضعة أيام، لا كل شيء — واليوم الذي وضعت عليه علامة استثناء لا يكلّف شيئاً.',
              zh: '因为普通的一个糟糕日子就把数周的真实进步清零，那是披着指标外衣的惩罚，也正是大多数人放弃的那一刻。所以错过一天的代价是几天，而不是全部——而你标记为例外的那一天，代价是零。',
            }) + graceLine);
        });
      });
      return el;
    },
  };

  // =================================================================
  // 6. Which dimension is stronger
  // =================================================================
  const dimensionDuel = {
    key: 'game_dimension_duel',
    // post: compares two of the transparent breakdown's dimensions, not
    // the score itself.
    phase: 'post',
    icon: '🧭',
    title: { en: 'Your strongest area', fa: 'قوی‌ترین حوزه‌ات', ar: 'أقوى مجال لديك', zh: '你最强的方面' },
    guideTopic: 'game_dimension_duel',
    // The transparent dimension rollup, not the model's SHAP output -
    // deliberately a different real number than game_which_factor, so
    // the two teach different things instead of asking the same
    // question twice (G8: both are read straight from the response).
    eligible: (ctx) => Array.isArray(ctx.dimensions) && ctx.dimensions.length >= 2,
    render(ctx) {
      const sorted = [...ctx.dimensions].sort((a, b) => b.score - a.score);
      const top = sorted[0];
      const other = sorted.slice(1).find((d) => top.score - d.score >= 8);
      if (!other) return null;   // too close to be a fair question (G4)

      const label = (d) => window.DWI18n.t('dim_' + d.key) || d.label || d.key;
      const options = Math.random() < 0.5 ? [top, other] : [other, top];
      const lead = {
        en: 'Two areas from your dimension breakdown. Which one is doing better right now?',
        fa: 'دو حوزه از تفکیک ابعادت. کدام‌یک الان وضعیت بهتری دارد؟',
        ar: 'مجالان من تفصيل أبعادك. أيهما في حال أفضل الآن؟',
        zh: '来自你维度细分的两个方面。哪一个现在状态更好？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <div class="game-choices">
          ${options.map((d, i) => `<button type="button" class="game-choice" data-i="${i}">${label(d)}</button>`).join('')}
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          const chosen = options[parseInt(btn.dataset.i, 10)];
          const correct = chosen === top;
          el.querySelectorAll('.game-choice').forEach((b, i) => {
            b.disabled = true;
            b.classList.add(options[i] === top ? 'is-answer' : 'is-other');
          });
          verdict(el, correct,
            correct
              ? pick({ en: 'That is the stronger one.', fa: 'همان قوی‌تر است.', ar: 'هذا هو الأقوى.', zh: '正是那个更强。' })
              : pick({ en: `${label(top)} is ahead.`, fa: `${label(top)} جلوتر است.`, ar: `${label(top)} في المقدمة.`, zh: `${label(top)} 更靠前。` }),
            `${label(top)} ${num(Math.round(top.score))}, ${label(other)} ${num(Math.round(other.score))}. `
            + pick({
                en: 'This is the plain-arithmetic breakdown, not the model - a separate view over the same inputs so you can sanity-check one against the other.',
                fa: 'این تفکیک حساب ساده است، نه مدل — یک نمای جدا روی همان ورودی‌ها تا بتوانی یکی را با دیگری بسنجی.',
                ar: 'هذا تفصيل حسابي بسيط، لا النموذج — نظرة منفصلة على المدخلات نفسها كي تتحقق من إحداهما بالأخرى.',
                zh: '这是简单算术得出的细分，不是模型——对同样输入的另一种独立视角，方便你互相核对。',
              }));
        });
      });
      return el;
    },
  };

  // =================================================================
  // 7. Guess the model's confidence
  // =================================================================
  const confidenceGuess = {
    key: 'game_confidence_guess',
    // pre: reveals ctx.confidencePercent itself ("Before the number:").
    phase: 'pre',
    icon: '📶',
    title: { en: 'How sure is it?', fa: 'چقدر مطمئن است؟', ar: 'ما مدى تأكده؟', zh: '它有多确定？' },
    guideTopic: 'game_confidence_guess',
    eligible: (ctx) => !!(ctx.confidenceLevel) && !playedToday('game_confidence_guess'),
    render(ctx) {
      const LEVELS = [
        { key: 'high', label: { en: 'Very sure', fa: 'خیلی مطمئن', ar: 'واثق جداً', zh: '非常确定' } },
        { key: 'moderate', label: { en: 'Somewhat sure', fa: 'تا حدی مطمئن', ar: 'واثق نوعاً ما', zh: '有点确定' } },
        { key: 'low', label: { en: 'Not very sure', fa: 'خیلی مطمئن نیست', ar: 'غير واثق كثيراً', zh: '不太确定' } },
      ];
      const lead = {
        en: 'Before the number: how confident do you think the model is about today’s result?',
        fa: 'قبل از دیدن عدد: فکر می‌کنی مدل چقدر به نتیجه‌ی امروز مطمئن است؟',
        ar: 'قبل الرقم: ما مدى ثقة النموذج برأيك بنتيجة اليوم؟',
        zh: '在看到数字之前：你觉得模型对今天这个结果有多大把握？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <div class="game-choices">
          ${LEVELS.map((l) => `<button type="button" class="game-choice" data-answer="${l.key}">${pick(l.label)}</button>`).join('')}
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          markPlayed(this.key);
          const correct = btn.dataset.answer === ctx.confidenceLevel;
          el.querySelectorAll('.game-choice').forEach((b) => {
            b.disabled = true;
            b.classList.add(b.dataset.answer === ctx.confidenceLevel ? 'is-answer' : 'is-other');
          });
          const pct = Math.round(ctx.confidencePercent || 0);
          verdict(el, correct,
            pick({ en: `It's at ${num(pct + '%')}.`, fa: `${num(pct + '%')} است.`, ar: `إنها ${num(pct + '%')}.`, zh: `是 ${num(pct + '%')}。` }),
            pick({
              en: 'That number comes from how tightly your inputs cluster inside one category versus spreading across two - not a guess, and not the same thing as the score being good or bad.',
              fa: 'این عدد از این می‌آید که ورودی‌هایت چقدر داخل یک دسته متمرکزند در برابر پخش‌شدن بین دو دسته — نه یک حدس، و نه همان چیزی که خوب یا بد بودن امتیاز است.',
              ar: 'يأتي هذا الرقم من مدى تجمّع مدخلاتك داخل فئة واحدة مقابل انتشارها بين فئتين — ليس تخميناً، وليس نفس معنى أن تكون الدرجة جيدة أو سيئة.',
              zh: '这个数字来自你的输入在一个类别内聚集的紧密程度，而不是分散在两个类别之间——不是猜测，也不等于分数的好坏。',
            }));
        });
      });
      return el;
    },
  };

  // =================================================================
  // 8. Guess the seven-day class
  // =================================================================
  const futureClassGuess = {
    key: 'game_future_class_guess',
    // post: its own lead text says "You already saw today's score" - it
    // is written to run after the result, not before it.
    phase: 'post',
    icon: '🔮',
    title: { en: 'Seven days out', fa: 'هفت روز جلوتر', ar: 'بعد سبعة أيام', zh: '七天之后' },
    guideTopic: 'game_future_class_guess',
    // Only the class - never invents or shows a seven-day SCORE here,
    // which is Output 2 and belongs to future-letter.js / the horizon
    // card, not a guessing game (G8: this only echoes result.prediction).
    eligible: (ctx) => !!ctx.futureClass && !playedToday('game_future_class_guess'),
    render(ctx) {
      const CLASSES = [
        { key: 'Healthy', label: { en: 'Healthy', fa: 'سالم', ar: 'صحي', zh: '健康' } },
        { key: 'Moderate', label: { en: 'Moderate', fa: 'متوسط', ar: 'متوسط', zh: '中等' } },
        { key: 'At Risk', label: { en: 'At Risk', fa: 'در معرض خطر', ar: 'في خطر', zh: '有风险' } },
      ];
      const lead = {
        en: 'You already saw today’s score. Which band does the model expect you in seven days from now?',
        fa: 'امتیاز امروز را دیدی. مدل هفت روز دیگر تو را در کدام دسته پیش‌بینی می‌کند؟',
        ar: 'رأيت درجة اليوم بالفعل. في أي فئة يتوقعك النموذج بعد سبعة أيام؟',
        zh: '你已经看到今天的分数了。模型预计七天后你会在哪个区间？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <div class="game-choices">
          ${CLASSES.map((c) => `<button type="button" class="game-choice" data-answer="${c.key}">${pick(c.label)}</button>`).join('')}
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          markPlayed(this.key);
          const correct = btn.dataset.answer === ctx.futureClass;
          el.querySelectorAll('.game-choice').forEach((b) => {
            b.disabled = true;
            b.classList.add(b.dataset.answer === ctx.futureClass ? 'is-answer' : 'is-other');
          });
          const answerLabel = pick((CLASSES.find((c) => c.key === ctx.futureClass) || {}).label || { en: ctx.futureClass });
          verdict(el, correct,
            correct
              ? pick({ en: 'That is the one.', fa: 'همان است.', ar: 'هي تلك.', zh: '正是它。' })
              : pick({ en: `It was ${answerLabel}.`, fa: `${answerLabel} بود.`, ar: `كانت ${answerLabel}.`, zh: `是 ${answerLabel}。` }),
            pick({
              en: 'This is a separate model from today’s score, trained on a different question - not today’s number projected forward. The two can genuinely disagree.',
              fa: 'این یک مدل جداست از امتیاز امروز، که روی سؤال متفاوتی آموزش دیده — نه فرافکنی عدد امروز به جلو. این دو می‌توانند واقعاً با هم اختلاف داشته باشند.',
              ar: 'هذا نموذج منفصل عن درجة اليوم، مدرَّب على سؤال مختلف — لا امتداد لرقم اليوم إلى الأمام. يمكن أن يختلف الاثنان فعلاً.',
              zh: '这是与今天分数不同的一个模型，训练目标也不同——不是把今天的数字往后推。两者完全可能不一致。',
            }));
        });
      });
      return el;
    },
  };

  // =================================================================
  // 9. Weekdays or weekends
  // =================================================================
  const weekdayOrWeekend = {
    key: 'game_weekday_or_weekend',
    // post: an aggregate stat over past days, independent of today's
    // own score.
    phase: 'post',
    icon: '📅',
    title: { en: 'Weekdays or weekends?', fa: 'روزهای هفته یا آخر هفته؟', ar: 'أيام العمل أم نهاية الأسبوع؟', zh: '工作日还是周末？' },
    guideTopic: 'game_weekday_or_weekend',
    // Same weekday_vs_weekend figure the Analytics page shows (Sat/Sun,
    // computed server-side) - never a client-side recomputation that
    // could quietly disagree with it (G8).
    eligible: (ctx) => !!(ctx.weekdayVsWeekend
      && ctx.weekdayVsWeekend.weekday_avg != null && ctx.weekdayVsWeekend.weekend_avg != null),
    render(ctx) {
      const w = ctx.weekdayVsWeekend;
      const lead = {
        en: 'Across your own logged days, which tends to score higher?',
        fa: 'در روزهایی که خودت ثبت کرده‌ای، کدام معمولاً امتیاز بالاتری می‌گیرد؟',
        ar: 'عبر أيامك المسجَّلة، أيهما يميل لتسجيل درجة أعلى؟',
        zh: '在你自己记录的日子里，哪一类通常分数更高？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <div class="game-choices">
          <button type="button" class="game-choice" data-answer="weekday">${pick({ en: 'Weekdays', fa: 'روزهای هفته', ar: 'أيام العمل', zh: '工作日' })}</button>
          <button type="button" class="game-choice" data-answer="weekend">${pick({ en: 'Weekends', fa: 'آخر هفته', ar: 'نهاية الأسبوع', zh: '周末' })}</button>
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          const higher = w.weekday_avg === w.weekend_avg ? null
            : (w.weekday_avg > w.weekend_avg ? 'weekday' : 'weekend');
          const correct = higher == null || btn.dataset.answer === higher;
          el.querySelectorAll('.game-choice').forEach((b) => {
            b.disabled = true;
            if (higher) b.classList.add(b.dataset.answer === higher ? 'is-answer' : 'is-other');
          });
          verdict(el, correct,
            pick({
              en: `Weekdays ${num(w.weekday_avg)}, weekends ${num(w.weekend_avg)}.`,
              fa: `روزهای هفته ${num(w.weekday_avg)}، آخر هفته ${num(w.weekend_avg)}.`,
              ar: `أيام العمل ${num(w.weekday_avg)}، نهاية الأسبوع ${num(w.weekend_avg)}.`,
              zh: `工作日 ${num(w.weekday_avg)}，周末 ${num(w.weekend_avg)}。`,
            }),
            pick({
              en: 'A big gap usually means the structure of your week - work, school, routine - is doing more of the regulating than any habit you have actually built on purpose.',
              fa: 'فاصله‌ی زیاد معمولاً یعنی ساختار هفته‌ات — کار، مدرسه، روتین — بیشتر از هر عادتی که واقعاً عمداً ساخته‌ای در حال تنظیم‌کردن است.',
              ar: 'الفجوة الكبيرة تعني عادةً أن بنية أسبوعك — العمل، الدراسة، الروتين — تقوم بالتنظيم أكثر من أي عادة بنيتها فعلاً بقصد.',
              zh: '差距大通常意味着，起调节作用的更多是你一周的结构——工作、上学、日常安排——而不是你真正刻意养成的习惯。',
            }));
        });
      });
      return el;
    },
  };

  // =================================================================
  // 10. Closer to which badge
  // =================================================================
  const badgeRace = {
    key: 'game_badge_race',
    // post: about achievement badges, unrelated to today's own score.
    phase: 'post',
    icon: '🏅',
    title: { en: 'Closer to which one?', fa: 'به کدام‌یک نزدیک‌تری؟', ar: 'أقرب إلى أيها؟', zh: '离哪个更近？' },
    guideTopic: 'game_badge_race',
    // Never a private awareness indicator (G1 - those are not a
    // competition), and only badges the user's own history can actually
    // answer (evaluable) - a locked-for-lack-of-data badge is not a fair
    // question (G4).
    eligible: (ctx) => Array.isArray(ctx.lockedBadges) && ctx.lockedBadges.length >= 2 && !!window.DWBadgeText,
    render(ctx) {
      const sorted = [...ctx.lockedBadges].sort((a, b) => (b.progress || 0) - (a.progress || 0));
      const top = sorted[0];
      const other = sorted.slice(1).find((b) => (top.progress || 0) - (b.progress || 0) >= 0.15);
      if (!other) return null;   // too close to be a fair question (G4)

      const label = (b) => window.DWBadgeText.name(b.id);
      const options = Math.random() < 0.5 ? [top, other] : [other, top];
      const lead = {
        en: 'Two badges you have not earned yet. Which one are you closer to?',
        fa: 'دو نشانی که هنوز نگرفته‌ای. به کدام‌یک نزدیک‌تری؟',
        ar: 'وسامان لم تحصل عليهما بعد. أيهما أقرب لك؟',
        zh: '两枚你还没拿到的徽章。你离哪一个更近？',
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <div class="game-choices">
          ${options.map((b, i) => `<button type="button" class="game-choice" data-i="${i}">${label(b)}</button>`).join('')}
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          const chosen = options[parseInt(btn.dataset.i, 10)];
          const correct = chosen === top;
          el.querySelectorAll('.game-choice').forEach((b, i) => {
            b.disabled = true;
            b.classList.add(options[i] === top ? 'is-answer' : 'is-other');
          });
          const pct = (b) => num(Math.round((b.progress || 0) * 100) + '%');
          verdict(el, correct,
            correct
              ? pick({ en: 'That is the closer one.', fa: 'همان نزدیک‌تر است.', ar: 'هذا هو الأقرب.', zh: '正是那个更近。' })
              : pick({ en: `${label(top)} is closer.`, fa: `${label(top)} نزدیک‌تر است.`, ar: `${label(top)} أقرب.`, zh: `${label(top)} 更近。` }),
            `${label(top)} ${pct(top)}, ${label(other)} ${pct(other)}. `
            + pick({
                en: 'Straight from your own history, the same progress the Badges page itself would show.',
                fa: 'مستقیم از تاریخچه‌ی خودت، همان پیشرفتی که صفحه‌ی نشان‌ها نشان می‌دهد.',
                ar: 'مباشرة من سجلك، التقدّم نفسه الذي تعرضه صفحة الأوسمة.',
                zh: '直接来自你自己的历史，与徽章页面显示的进度完全一致。',
              }));
        });
      });
      return el;
    },
  };

  // =================================================================
  // 11. Today vs your own average
  // =================================================================
  const scoreVsAverage = {
    key: 'game_score_vs_average',
    // pre: its own lead text says "no peeking" and reveals ctx.score in
    // the same breath as the average - written to run before the score
    // is shown, same family as guess_score and confidence_guess.
    phase: 'pre',
    icon: '📊',
    title: { en: 'Above or below your usual?', fa: 'بالاتر یا پایین‌تر از معمولت؟', ar: 'أعلى أم أقل من معتادك؟', zh: '高于还是低于你的平常？' },
    guideTopic: 'game_score_vs_average',
    // Needs real history behind today, not just today itself - an
    // "average" of one point is not a comparison (G4).
    eligible: (ctx) => ctx.score != null && Array.isArray(ctx.pastScores) && ctx.pastScores.length >= 5,
    render(ctx) {
      const avg = ctx.pastScores.reduce((a, b) => a + b, 0) / ctx.pastScores.length;
      const lead = {
        en: `Your own average over your last ${ctx.pastScores.length} logged days is baked into this - no peeking. Is today above or below it?`,
        fa: `میانگین خودت در ${ctx.pastScores.length} روز اخیرِ ثبت‌شده‌ات پشت این عدد است — دزدکی نگاه نکن. امروز بالاتر است یا پایین‌تر؟`,
        ar: `متوسطك في آخر ${ctx.pastScores.length} يوماً مسجَّلة كامن خلف هذا — بلا غش. هل اليوم أعلى أم أقل منه؟`,
        zh: `你过去 ${ctx.pastScores.length} 天记录的平均值就藏在这个问题背后——别偷看。今天是高于还是低于它？`,
      };
      const el = card(this, `
        <p>${pick(lead)}</p>
        <div class="game-choices">
          <button type="button" class="game-choice" data-answer="above">${pick({ en: 'Above my average', fa: 'بالاتر از میانگینم', ar: 'أعلى من متوسطي', zh: '高于我的平均值' })}</button>
          <button type="button" class="game-choice" data-answer="below">${pick({ en: 'Below my average', fa: 'پایین‌تر از میانگینم', ar: 'أقل من متوسطي', zh: '低于我的平均值' })}</button>
        </div>`);

      el.querySelectorAll('.game-choice').forEach((btn) => {
        btn.addEventListener('click', () => {
          const actual = Math.round(ctx.score);
          const above = actual > avg;
          const correct = (btn.dataset.answer === 'above') === above;
          el.querySelectorAll('.game-choice').forEach((b) => { b.disabled = true; });
          verdict(el, correct,
            pick({
              en: `Today: ${num(actual)}. Your average: ${num(Math.round(avg))}.`,
              fa: `امروز: ${num(actual)}. میانگینت: ${num(Math.round(avg))}.`,
              ar: `اليوم: ${num(actual)}. متوسطك: ${num(Math.round(avg))}.`,
              zh: `今天：${num(actual)}。你的平均值：${num(Math.round(avg))}。`,
            }),
            pick({
              en: 'Your own average is the only honest baseline here - not 50, not anyone else’s number. A day only means something next to your own history.',
              fa: 'میانگین خودت تنها خط پایه‌ی صادقانه اینجاست — نه پنجاه، نه عدد کس دیگری. یک روز فقط کنار تاریخچه‌ی خودت معنا دارد.',
              ar: 'متوسطك أنت هو خط الأساس الصادق الوحيد هنا — لا خمسون، ولا رقم أي شخص آخر. اليوم لا يعني شيئاً إلا بجانب سجلك أنت.',
              zh: '你自己的平均值才是这里唯一诚实的基准——不是五十，也不是别人的数字。一天的意义只有放在你自己的历史旁边才成立。',
            }));
        });
      });
      return el;
    },
  };

  const GAMES = [
    guessScore, whichFactor, baselineOrException, fillTheBlank, keepTheStreak,
    dimensionDuel, confidenceGuess, futureClassGuess, weekdayOrWeekend, badgeRace, scoreVsAverage,
  ];

  /* Renders at most `limit` eligible games. Deliberately not all of
     them at once: five cards in a column is a quiz, not an
     interaction. */
  /* Fisher-Yates - used only to vary which two of the (often several)
     eligible games show on a given visit, so the check-in flow does not
     always land on the same one or two just because they are first in
     GAMES and are almost always eligible (guess_score, in particular,
     needs nothing but a score). Not used anywhere randomness would
     affect an actual answer. */
  function shuffled(arr) {
    const out = arr.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  }

  function render(mount, context, opts) {
    if (!mount) return 0;
    opts = opts || {};
    const limit = opts.limit || 2;
    const only = opts.only || null;
    // `phase` splits the roster by whether the game's own reveal shows
    // a number the result view is about to show anyway. 'pre' games
    // (guess_score, confidence_guess, score_vs_average) commit to a
    // guess before that number appears anywhere, so they render in the
    // gap between processing and the result view. Every other game
    // reads secondary context (SHAP factors, streak, badges, historical
    // stats) that does not spoil anything, and is written assuming the
    // reader has already seen their result - futureClassGuess even says
    // so in its own lead line - so those render further down the
    // result page instead. Omitting `phase` keeps the old
    // everything-together behaviour for any future caller that has no
    // opinion on ordering.
    const byPhase = opts.phase ? GAMES.filter((g) => g.phase === opts.phase) : GAMES;
    // With `only` given (a caller asking for specific games), the
    // caller's own order is the intent - keep it. Without one, shuffle
    // so repeated visits do not always surface the same couple of games.
    const candidates = only ? byPhase : shuffled(byPhase);
    mount.innerHTML = '';
    let shown = 0;
    for (const game of candidates) {
      if (shown >= limit) break;
      if (only && !only.includes(game.key)) continue;
      if (isQuiet(game.key)) continue;                 // G3
      let eligible = false;
      try { eligible = !!game.eligible(context || {}); } catch (e) { eligible = false; }
      if (!eligible) continue;                          // G4
      let el = null;
      try { el = game.render(context || {}); } catch (e) { el = null; }
      if (!el) continue;
      if (game.guideTopic) {
        el.classList.add('has-guide');
        el.querySelector('.game-head').addEventListener('click', () => {
          if (window.DWGuide) window.DWGuide.explain(game.guideTopic, { force: true });
        });
      }
      mount.appendChild(el);
      shown += 1;
    }
    const section = mount.closest('.games-section');
    if (section) section.classList.toggle('hidden', shown === 0);   // G4
    return shown;
  }

  window.DWGames = { render, GAMES, T, isEnabled, setEnabled };
})();
