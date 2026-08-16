/*
  The guide character ("Pixel").

  Two things this file is careful about:

  1. TONE. The brief asks for a blunt, direct tone on a bad result. That
     is honoured - the at-risk lines name the problem plainly and give a
     concrete next step. What they never do is judge or shame the user
     ("you're ruining your health", "this is bad and it's your fault").
     Shame backfires in a wellbeing context and would also conflict with
     this project's zero-medical-claims rule. Direct and honest, on the
     user's side.

  2. NO MEDICAL CLAIMS. Nothing here diagnoses, or implies a condition,
     or promises a health outcome. It talks about habits and numbers the
     model actually produced.

  Expressions are driven by real state passed in by the caller - they are
  never guessed from anything the character invents.
*/
(function () {
  const EXPRESSIONS = ['great', 'good', 'borderline', 'risk', 'thinking', 'confused', 'neutral'];

  const LINES = {
    en: {
      great: [
        "These numbers look genuinely good. Whatever you're doing, keep the pattern.",
        "Strong result. The habits driving it are worth protecting.",
      ],
      good: [
        "Solid place to be. A couple of small tweaks and it holds steady.",
        "This is a good baseline — the goal now is consistency, not overhaul.",
      ],
      borderline: [
        "You're right on the edge here. Worth acting before it drifts further.",
        "Mixed signals in this one. Two habits are doing most of the damage — start there.",
      ],
      risk: [
        "I'll be straight with you: this score is low. The good news is the top factors are all things you can change.",
        "This isn't a good result, and pretending otherwise wouldn't help you. Pick one item below and start there this week.",
        "Low score. Not a verdict on you — a snapshot of this week's habits. Let's move one of them.",
      ],
      thinking: ["Reading your inputs…", "Working through your numbers…"],
      confused: ["Hmm, something glitched on my end. Mind trying that again?"],
      neutral: [
        "Hey! I'm Pixel. I read the model's real output — no guessing.",
        "Ask me for a check-in whenever you're ready.",
      ],
      greeting: "Hi there! Ready to check in on your digital habits?",
      task_done: 'Nice — one step closer.',
      saved: 'Got it, saved.',
    },
    fa: {
      great: [
        'این اعداد واقعاً خوب‌اند. هر کاری می‌کنی، همین الگو را نگه دار.',
        'نتیجه‌ی قوی. عادت‌هایی که این را ساخته‌اند ارزش محافظت دارند.',
      ],
      good: [
        'جای خوبی هستی. با چند تنظیم کوچک، پایدار می‌ماند.',
        'این یک خط پایه‌ی خوب است — حالا هدف ثبات است، نه زیر و رو کردن همه‌چیز.',
      ],
      borderline: [
        'دقیقاً روی مرز هستی. بهتر است قبل از اینکه بیشتر فاصله بگیرد، کاری بکنی.',
        'سیگنال‌ها این بار مخلوط‌اند. دو عادت بیشترین اثر را دارند — از همان‌ها شروع کن.',
      ],
      risk: [
        'رک می‌گویم: این امتیاز پایین است. خبر خوب اینکه عوامل اصلی‌اش همگی قابل تغییرند.',
        'این نتیجه‌ی خوبی نیست و تعارف کردن کمکی به تو نمی‌کند. یکی از موارد پایین را انتخاب کن و همین هفته شروع کن.',
        'امتیاز پایین. این حکمی درباره‌ی تو نیست — عکسی از عادت‌های این هفته است. بیا یکی‌شان را جابه‌جا کنیم.',
      ],
      thinking: ['دارم ورودی‌هایت را می‌خوانم…', 'دارم روی اعدادت کار می‌کنم…'],
      confused: ['به نظر می‌رسد چیزی از سمت من به مشکل خورد. دوباره امتحان می‌کنی؟'],
      neutral: [
        'سلام! من پیکسل‌ام. خروجی واقعی مدل را می‌خوانم — حدس نمی‌زنم.',
        'هر وقت آماده بودی، برای یک بررسی جدید بگو.',
      ],
      greeting: 'سلام! آماده‌ای عادت‌های دیجیتالت را بررسی کنیم؟',
      task_done: 'خوب بود — یک قدم نزدیک‌تر.',
      saved: 'ثبت شد.',
    },
    ar: {
      great: ['هذه الأرقام جيدة فعلاً. مهما كنت تفعل، حافظ على هذا النمط.'],
      good: ['وضع جيد. تعديلات صغيرة تكفي للحفاظ عليه.'],
      borderline: ['أنت على الحافة تمامًا. من الأفضل التحرك قبل أن يبتعد أكثر.'],
      risk: ['سأكون صريحًا: هذه الدرجة منخفضة. الخبر الجيد أن العوامل الأساسية كلها قابلة للتغيير.'],
      thinking: ['أقرأ مدخلاتك…'],
      confused: ['حدث خلل ما لدي. هل تحاول مرة أخرى؟'],
      neutral: ['مرحبًا! أنا بيكسل. أقرأ المخرجات الحقيقية للنموذج.'],
      greeting: 'مرحبًا! هل أنت مستعد لفحص عاداتك الرقمية؟',
      task_done: 'جميل — خطوة أقرب.',
      saved: 'تم الحفظ.',
    },
    zh: {
      great: ['这些数字确实不错。无论你在做什么，保持这个模式。'],
      good: ['状态不错。一些小调整就能保持稳定。'],
      borderline: ['你正处在临界点。最好在进一步偏离之前采取行动。'],
      risk: ['我直说：这个分数偏低。好消息是，主要影响因素都是你可以改变的。'],
      thinking: ['正在读取你的输入…'],
      confused: ['我这边出了点问题。要再试一次吗？'],
      neutral: ['嗨！我是 Pixel。我读取模型的真实输出。'],
      greeting: '你好！准备好检测一下你的数字习惯了吗？',
      task_done: '很好——又近了一步。',
      saved: '已保存。',
    },
  };

  function pack() {
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    return LINES[lang] || LINES.en;
  }

  let bubbleEl, svgEl, hideTimer, current = 'neutral';
  let lastIndex = {};

  function pick(key) {
    const arr = pack()[key];
    if (!arr) return '';
    if (!Array.isArray(arr)) return arr;
    if (arr.length === 1) return arr[0];
    let i;
    do { i = Math.floor(Math.random() * arr.length); } while (i === lastIndex[key] && arr.length > 1);
    lastIndex[key] = i;
    return arr[i];
  }

  const CLOSE_LABEL = {
    en: 'Dismiss', fa: 'بستن', ar: 'إغلاق', zh: '关闭',
  };

  /* The bubble ships in the HTML of 11 pages as a bare div. Rather than
     editing all of them, the text span and the dismiss control are built
     here on first use and then reused.

     The aria-live region moves from the container onto the text span: with
     it on the container, adding a button meant the button's label was
     re-announced with every message. role="status" already implies
     aria-live="polite", so the container keeps neither. */
  let textEl, closeEl, currentTopic = null;

  function ensure() {
    bubbleEl = document.getElementById('mascotBubble');
    svgEl = document.getElementById('mascotBtn');
    if (!bubbleEl || !svgEl) return false;

    if (!bubbleEl.__dwStructured) {
      bubbleEl.__dwStructured = true;
      const existing = bubbleEl.textContent || '';
      bubbleEl.textContent = '';
      bubbleEl.removeAttribute('aria-live');
      bubbleEl.removeAttribute('role');

      textEl = document.createElement('span');
      textEl.className = 'mascot-bubble-text';
      textEl.setAttribute('role', 'status');
      textEl.setAttribute('aria-live', 'polite');
      textEl.textContent = existing;

      closeEl = document.createElement('button');
      closeEl.type = 'button';
      closeEl.className = 'mascot-bubble-close';
      closeEl.textContent = '×';

      // Dismissal is a signal, not just a hide: the guide layer counts it
      // and goes quiet on topics the user keeps waving away (see
      // guide-tips.js). Without a real control there was nothing to count.
      closeEl.addEventListener('click', (e) => {
        e.stopPropagation();
        if (currentTopic && window.DWGuide && window.DWGuide.noteDismissed) {
          window.DWGuide.noteDismissed(currentTopic);
        }
        currentTopic = null;
        clearTimeout(hideTimer);
        bubbleEl.classList.remove('show');
      });

      bubbleEl.appendChild(textEl);
      bubbleEl.appendChild(closeEl);
    }

    // Label follows the current language, re-applied per show so a
    // language switch mid-session is picked up.
    if (closeEl) {
      const label = (window.DWI18n && window.DWI18n.pick)
        ? window.DWI18n.pick(CLOSE_LABEL)
        : CLOSE_LABEL.en;
      closeEl.setAttribute('aria-label', label);
      closeEl.setAttribute('title', label);
    }
    return true;
  }

  /* ---- Speech-driven mouth (B-4) ----------------------------------

     The mouth is animated from the SpeechSynthesis events themselves, not
     by a fixed loop running next to the audio. `onboundary` fires as the
     engine crosses each word, so the mouth opens on real word starts and
     the animation lasts exactly as long as the speech does - if the
     utterance is cut short, the mouth stops with it.

     Some engines (notably several mobile ones) never fire `onboundary`.
     Rather than leaving the mouth frozen while audio plays, a fallback
     interval drives it between `onstart` and `onend`, which are far more
     widely implemented. Either way the movement is bounded by the real
     start and end of speech. */
  const MOUTH_OPEN = 'M38 64 Q50 76 62 64';
  let mouthTimer = null;
  let boundarySeen = false;
  let restingFace = 'neutral';

  function setMouthPath(d) {
    if (!ensure()) return;
    const mouth = svgEl.querySelector('.mascot-mouth');
    if (mouth) mouth.setAttribute('d', d);
  }

  function flapOnce() {
    if (window.DWMotion && window.DWMotion.prefersReduced()) return;
    setMouthPath(MOUTH_OPEN);
    setTimeout(() => {
      const f = FACES[restingFace] || FACES.neutral;
      setMouthPath(f.mouth);
    }, 110);
  }

  function stopMouth() {
    if (mouthTimer) { clearInterval(mouthTimer); mouthTimer = null; }
    const f = FACES[restingFace] || FACES.neutral;
    setMouthPath(f.mouth);
  }

  function startSpeaking(text) {
    const V = window.DWGuideVoice;
    if (!V) return;
    boundarySeen = false;
    V.speak(text, {
      onStart: () => {
        // Fallback flapping, cancelled the moment a real boundary arrives.
        if (mouthTimer) clearInterval(mouthTimer);
        mouthTimer = setInterval(() => { if (!boundarySeen) flapOnce(); }, 180);
      },
      onBoundary: () => {
        boundarySeen = true;
        if (mouthTimer) { clearInterval(mouthTimer); mouthTimer = null; }
        flapOnce();
      },
      onEnd: stopMouth,
    });
  }

  /* ---- Face rendering -------------------------------------------- */
  const FACES = {
    great:      { eye: 'sparkle', mouth: 'M34 64 Q50 78 66 64', brow: null },
    good:       { eye: 'open',    mouth: 'M36 65 Q50 74 64 65', brow: null },
    borderline: { eye: 'open',    mouth: 'M38 69 Q50 65 62 69', brow: 'worried' },
    risk:       { eye: 'narrow',  mouth: 'M38 70 Q50 63 62 70', brow: 'serious' },
    thinking:   { eye: 'look',    mouth: 'M40 68 L60 68',       brow: null },
    confused:   { eye: 'open',    mouth: 'M38 68 Q44 63 50 68 Q56 73 62 68', brow: 'confused' },
    neutral:    { eye: 'open',    mouth: 'M38 67 Q50 71 62 67', brow: null },
  };

  function renderFace(state) {
    if (!ensure()) return;
    const f = FACES[state] || FACES.neutral;
    // Remembered so the mouth returns to THIS expression after speaking,
    // rather than snapping back to a hardcoded neutral and undoing the
    // expression the guide was set to.
    restingFace = FACES[state] ? state : 'neutral';
    const eyes = svgEl.querySelector('.mascot-eye');
    const mouth = svgEl.querySelector('.mascot-mouth');
    const brows = svgEl.querySelector('.mascot-brows');
    if (!eyes || !mouth) return;

    if (f.eye === 'narrow') {
      eyes.innerHTML =
        '<rect x="30" y="46" r="2" width="12" height="4" rx="2" fill="#04140f"/>' +
        '<rect x="58" y="46" r="2" width="12" height="4" rx="2" fill="#04140f"/>';
    } else if (f.eye === 'sparkle') {
      eyes.innerHTML =
        '<circle cx="36" cy="48" r="6" fill="#04140f"/><circle cx="38.4" cy="45.6" r="2" fill="#fff"/>' +
        '<circle cx="64" cy="48" r="6" fill="#04140f"/><circle cx="66.4" cy="45.6" r="2" fill="#fff"/>';
    } else if (f.eye === 'look') {
      eyes.innerHTML =
        '<circle cx="38" cy="48" r="6" fill="#04140f"/>' +
        '<circle cx="66" cy="48" r="6" fill="#04140f"/>';
    } else {
      eyes.innerHTML =
        '<circle cx="36" cy="48" r="6" fill="#04140f"/>' +
        '<circle cx="64" cy="48" r="6" fill="#04140f"/>';
    }

    mouth.setAttribute('d', f.mouth);

    if (brows) {
      if (f.brow === 'worried') {
        brows.innerHTML = '<path d="M29 37 L43 34" stroke="#04140f" stroke-width="3" stroke-linecap="round"/>' +
                          '<path d="M71 37 L57 34" stroke="#04140f" stroke-width="3" stroke-linecap="round"/>';
      } else if (f.brow === 'serious') {
        brows.innerHTML = '<path d="M29 34 L43 39" stroke="#04140f" stroke-width="3.4" stroke-linecap="round"/>' +
                          '<path d="M71 34 L57 39" stroke="#04140f" stroke-width="3.4" stroke-linecap="round"/>';
      } else if (f.brow === 'confused') {
        brows.innerHTML = '<path d="M29 38 L43 33" stroke="#04140f" stroke-width="3" stroke-linecap="round"/>' +
                          '<path d="M71 36 L57 36" stroke="#04140f" stroke-width="3" stroke-linecap="round"/>';
      } else {
        brows.innerHTML = '';
      }
    }

    svgEl.dataset.state = state;
    current = state;
  }

  /* ---- Speech ----------------------------------------------------- */
  function say(text, opts) {
    opts = opts || {};
    if (!ensure() || !text) return;

    // The guide can be switched off entirely (B-2): no bubble, no speech.
    const V = window.DWGuideVoice;
    if (V && !V.guideEnabled()) return;

    // Text goes in as a text node, never innerHTML - say() is called with
    // strings built from the user's own numbers elsewhere in the app.
    textEl.textContent = text;
    // Remembered so the dismiss control can attribute the dismissal to
    // whatever the guide was talking about.
    currentTopic = opts.topic || null;

    /* B-3: every line the guide shows goes through here, so routing speech
       from this one place is what makes voice coverage complete rather
       than a handful of special-cased messages. Silence is always a valid
       outcome - unsupported browser, voice switched off, or no voice
       installed for this language - and the bubble is shown either way. */
    if (V && opts.speak !== false) {
      startSpeaking(text);
    }

    bubbleEl.classList.remove('show');
    void bubbleEl.offsetWidth;
    bubbleEl.classList.add('show');
    if (opts.attention) pulse();
    clearTimeout(hideTimer);
    if (!opts.sticky) {
      hideTimer = setTimeout(() => bubbleEl.classList.remove('show'), opts.duration || 6000);
    }
  }

  /* ---- Motion ------------------------------------------------------
     One movement per meaning. Before this the guide had a bob, a blink,
     a pulse and a tilt, and the same little jump answered "well done",
     "that went wrong" and "let me think" - so none of them said
     anything. These are distinguishable shapes: a nod travels
     vertically, a shake horizontally, a wobble rotates without
     travelling. You can tell them apart with the sound off. */
  const MOTIONS = {
    attention: 700, nod: 750, shake: 600, bounce: 1050, wobble: 1300,
    spin: 1100, lean: 1100, wave: 1200, sink: 900, perk: 700, tilt: 1400,
  };

  let motionTimer = null;

  /** Play one movement. Silently does nothing under reduced motion. */
  function motion(name) {
    const duration = MOTIONS[name];
    if (!duration || !ensure()) return false;
    if (window.DWMotion && window.DWMotion.prefersReduced()) return false;

    // One at a time. Two transforms on the same element means the
    // second silently wins and the first looks like a dropped frame.
    Object.keys(MOTIONS).forEach((key) => svgEl.classList.remove('mascot-' + key));
    clearTimeout(motionTimer);
    void svgEl.offsetWidth;              // restart even if it repeats
    svgEl.classList.add('mascot-' + name);
    motionTimer = setTimeout(
      () => svgEl.classList.remove('mascot-' + name), duration + 60,
    );
    return true;
  }

  /* The face's own smaller movements, which are most of what makes it
     read as occupied rather than switched off. They run on the eye and
     brow groups, so they compose with whatever the body is doing. */
  function glance() {
    if (!ensure() || (window.DWMotion && window.DWMotion.prefersReduced())) return;
    const eyes = svgEl.querySelector('.mascot-eye');
    if (!eyes) return;
    eyes.classList.remove('is-glancing');
    void eyes.getBoundingClientRect();
    eyes.classList.add('is-glancing');
    setTimeout(() => eyes.classList.remove('is-glancing'), 2500);
  }

  function raiseBrows() {
    if (!ensure() || (window.DWMotion && window.DWMotion.prefersReduced())) return;
    const brows = svgEl.querySelector('.mascot-brows');
    if (!brows) return;
    brows.classList.remove('is-raising');
    void brows.getBoundingClientRect();
    brows.classList.add('is-raising');
    setTimeout(() => brows.classList.remove('is-raising'), 700);
  }

  /* Which movement belongs to which event. Kept as data rather than as
     branches so adding an event is one line, and so the mapping can be
     read in one place and argued with. */
  const MOTION_FOR = {
    great: 'spin', good: 'bounce', task_done: 'bounce', badge: 'spin',
    neutral: 'nod', greeting: 'wave', hello: 'wave',
    thinking: 'wobble', curious: 'lean', listening: 'lean',
    borderline: 'tilt', risk: 'sink', error: 'shake', wrong: 'shake',
    saved: 'nod', streak: 'perk', reminder: 'perk',
  };

  function pulse() {
    motion('attention');
  }

  /* Map a wellness score to an expression using the SAME thresholds the
     result page uses for its colour bands - never a second opinion. */
  function stateForScore(score) {
    if (score == null) return 'neutral';
    if (score >= 80) return 'great';
    if (score >= 66) return 'good';
    if (score >= 40) return 'borderline';
    return 'risk';
  }

  function react(key, opts) {
    opts = opts || {};
    const move = MOTION_FOR[key];
    if (move) motion(move);
    if (key === 'thinking' || key === 'curious') glance();
    if (key === 'great' || key === 'good' || key === 'badge') raiseBrows();
    if (EXPRESSIONS.includes(key)) {
      renderFace(key);
      say(pick(key), opts);
      return;
    }
    // Non-expression events keep the current face.
    const p = pack();
    if (p[key]) say(typeof p[key] === 'string' ? p[key] : pick(key), opts);
  }

  function reactToScore(score, opts) {
    const st = stateForScore(score);
    renderFace(st);
    say(pick(st), Object.assign({ attention: true, duration: 8000 }, opts || {}));
    return st;
  }

  /* ---- Idle life + gaze ------------------------------------------ */
  function startIdle() {
    if (!ensure()) return;
    if (window.DWMotion && window.DWMotion.prefersReduced()) return;

    // Occasional head tilt, on an irregular schedule so it never looks
    // like a metronome.
    /* An idle that varies. One repeated tilt on a timer is the thing
       that makes a character read as a looping GIF; picking from a few
       quiet movements, on an irregular schedule, reads as somebody
       waiting. Nothing here is loud - the noisy ones (bounce, spin,
       shake) are reserved for events that earned them, or the guide
       would be pulling faces at an empty room. */
    const IDLE_MOTIONS = ['tilt', 'lean', 'nod', 'perk'];

    (function scheduleIdle() {
      const wait = 6000 + Math.random() * 9000;
      setTimeout(() => {
        if (!(window.DWMotion && window.DWMotion.prefersReduced())) {
          const roll = Math.random();
          if (roll < 0.30) glance();
          else if (roll < 0.42) raiseBrows();
          else motion(IDLE_MOTIONS[Math.floor(Math.random() * IDLE_MOTIONS.length)]);
        }
        scheduleIdle();
      }, wait);
    })();

    // Very subtle gaze toward the pointer (pupils only, max 2px).
    if (!window.matchMedia('(pointer: coarse)').matches) {
      let tx = 0, ty = 0, cx = 0, cy = 0, raf = null;
      window.addEventListener('pointermove', (e) => {
        const r = svgEl.getBoundingClientRect();
        const dx = e.clientX - (r.left + r.width / 2);
        const dy = e.clientY - (r.top + r.height / 2);
        const d = Math.hypot(dx, dy) || 1;
        tx = (dx / d) * 2;
        ty = (dy / d) * 2;
        if (!raf) raf = requestAnimationFrame(follow);
      }, { passive: true });
      function follow() {
        cx += (tx - cx) * 0.08;
        cy += (ty - cy) * 0.08;
        const eyes = svgEl.querySelector('.mascot-eye');
        if (eyes) eyes.setAttribute('transform', `translate(${cx.toFixed(2)} ${cy.toFixed(2)})`);
        raf = Math.abs(tx - cx) > 0.05 || Math.abs(ty - cy) > 0.05 ? requestAnimationFrame(follow) : null;
      }
    }
  }

  function init(opts) {
    if (!ensure()) return;
    renderFace('neutral');
    svgEl.setAttribute('tabindex', '0');
    svgEl.setAttribute('role', 'button');

    // A page can pass onClick (e.g. the Digital Guide re-explaining the
    // current page) to replace the default "say something" tap - falls
    // back to the generic idle line when no page-specific behavior is given.
    const onClick = (opts && opts.onClick) || (() => react('neutral'));
    svgEl.addEventListener('click', onClick);
    svgEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); }
    });
    svgEl.addEventListener('mouseenter', () => pulse());

    startIdle();

    /* The greeting belongs to signing in, not to arriving on a page.
       This used to fire on EVERY page load, so walking from the
       dashboard to the weekly plan to the coach meant being said hello
       to three times - and with voice on, hearing it three times. What
       a page should offer is an explanation of itself, which it already
       does on tap; what it should not do is reintroduce itself to
       somebody who has been using the app for ten minutes.

       The flag is cleared by DWApi.setToken/clearToken, so a real sign
       in (or a sign out and back in) greets again, and nothing else
       does. Wrapped because a browser with storage disabled should
       still show the app - it simply greets each time, which is the old
       behaviour and is not harmful. */
    greetOnce({ delay: 900 });
  }

  /* Says hello exactly once per signed-in session.

     Two conditions, and both matter. Not greeting an ANONYMOUS visitor
     is the first: app.html shows the sign-in form with the mascot
     already on it, so without this the one greeting a user is entitled
     to gets spent on a screen where they have not even told the app who
     they are - and then never appears again. Not greeting twice is the
     second: this used to run on every page load, so walking from the
     dashboard to the weekly plan to the coach meant being said hello to
     three times, and with voice on, hearing it three times.

     The flag is cleared by DWApi.setToken/clearToken, so signing in
     (or out and back in) greets again and nothing else does. A browser
     with storage disabled falls back to greeting each time, which is
     the old behaviour and is not harmful. */
  function greetOnce(opts) {
    const authed = !!(window.DWApi && window.DWApi.isAuthed && window.DWApi.isAuthed());
    if (!authed) return false;
    let greeted;
    try {
      greeted = localStorage.getItem('dwai_greeted') === '1';
      if (!greeted) localStorage.setItem('dwai_greeted', '1');
    } catch (e) {
      greeted = false;
    }
    if (greeted) return false;
    setTimeout(() => say(pack().greeting), (opts && opts.delay) || 0);
    return true;
  }

  window.DWMascot = {
    say, react, reactToScore, renderFace, stateForScore, pulse, init, greetOnce,
    // The movement vocabulary, so a page can play one directly for
    // something the event table does not cover.
    motion, glance, raiseBrows, MOTIONS,
  };
})();
