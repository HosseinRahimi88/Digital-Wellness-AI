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

  function ensure() {
    bubbleEl = document.getElementById('mascotBubble');
    svgEl = document.getElementById('mascotBtn');
    return !!(bubbleEl && svgEl);
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
    bubbleEl.textContent = text;
    bubbleEl.classList.remove('show');
    void bubbleEl.offsetWidth;
    bubbleEl.classList.add('show');
    if (opts.attention) pulse();
    clearTimeout(hideTimer);
    if (!opts.sticky) {
      hideTimer = setTimeout(() => bubbleEl.classList.remove('show'), opts.duration || 6000);
    }
  }

  function pulse() {
    if (!ensure() || (window.DWMotion && window.DWMotion.prefersReduced())) return;
    svgEl.classList.remove('mascot-attention');
    void svgEl.offsetWidth;
    svgEl.classList.add('mascot-attention');
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
    (function scheduleTilt() {
      const wait = 6000 + Math.random() * 9000;
      setTimeout(() => {
        if (!(window.DWMotion && window.DWMotion.prefersReduced())) {
          svgEl.classList.add('mascot-tilt');
          setTimeout(() => svgEl.classList.remove('mascot-tilt'), 1400);
        }
        scheduleTilt();
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
    setTimeout(() => say(pack().greeting), 900);
  }

  window.DWMascot = { say, react, reactToScore, renderFace, stateForScore, pulse, init };
})();
