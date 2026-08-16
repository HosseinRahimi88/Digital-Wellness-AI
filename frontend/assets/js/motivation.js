/*
  Motivational content, and the rules for when it is allowed to speak.

  Why this is a module and not a longer string in ai-menu.js
  ----------------------------------------------------------
  "Motivate me" used to be one templated sentence built from the score,
  and "tell me a fact" picked a knowledge topic at random. Both were thin
  in the same way: they said something true but generic, and said the
  same thing on the fifth visit as on the first.

  Two rules this file exists to keep:

  1. NOTHING HERE INVENTS A CLAIM ABOUT THE USER. Every line is either a
     general statement about how attention and sleep work, or a frame
     around a number the caller passes in from the user's real result.
     There are no fabricated statistics and no invented research
     citations - the mechanism is stated, not dressed up in a percentage
     nobody can check.

  2. ENCOURAGEMENT IS CHOSEN BY SITUATION, NOT AT RANDOM. Someone whose
     score is falling should not get the line written for someone whose
     score is holding. A cheerful sentence aimed at the wrong person is
     worse than no sentence, because it proves the app is not reading
     what it just measured.

  Rotation is by day, not Math.random(): the same person on the same day
  gets the same line, so re-opening a page does not shuffle the text
  under them, and the day after does not repeat it.
*/
(function () {
  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : (t && t.en) || '');

  /* ---- Facts about how this actually works -------------------------
     Grouped by the habit area they belong to, so the coach can offer one
     that relates to the user's own weakest signal instead of a random
     one. Mechanism statements only - no invented numbers. */
  const FACTS = {
    sleep: [
      {
        en: 'Light in the hour before bed delays the melatonin rise that starts sleep — which is why the last hour matters more than the total.',
        fa: 'نور در ساعت پیش از خواب، بالا آمدن ملاتونین را که خواب را شروع می‌کند عقب می‌اندازد — به همین دلیل آن ساعت آخر از کل زمان مهم‌تر است.',
        ar: 'الضوء في الساعة التي تسبق النوم يؤخّر ارتفاع الميلاتونين الذي يبدأ به النوم — ولهذا تهمّ الساعة الأخيرة أكثر من الإجمالي.',
        zh: '睡前一小时的光线会推迟启动睡眠的褪黑素上升——所以最后这一小时比总时长更重要。',
      },
      {
        en: 'A consistent wake-up time steadies sleep more reliably than a consistent bedtime, because waking is the anchor your body clock reads.',
        fa: 'ساعت بیدارشدنِ ثابت، خواب را مطمئن‌تر از ساعت خوابِ ثابت تنظیم می‌کند، چون بیدارشدن همان لنگری است که ساعت بدنت می‌خواند.',
        ar: 'ثبات وقت الاستيقاظ ينظّم النوم بشكل أوثق من ثبات وقت النوم، لأن الاستيقاظ هو المرساة التي تقرأها ساعتك البيولوجية.',
        zh: '固定的起床时间比固定的入睡时间更能稳定睡眠，因为醒来才是你的生物钟所读取的锚点。',
      },
      {
        en: 'Sleep lost during the week is not fully repaid at the weekend — the body treats it as a new schedule, not as catching up.',
        fa: 'خوابی که در طول هفته از دست می‌رود، آخر هفته کاملاً جبران نمی‌شود — بدن آن را یک برنامه‌ی تازه می‌بیند، نه جبران مافات.',
        ar: 'النوم المفقود خلال الأسبوع لا يُعوَّض بالكامل في عطلة نهايته — يتعامل الجسم معه كجدول جديد لا كتعويض.',
        zh: '工作日欠下的睡眠，周末补不回来——身体把它当作一份新的作息表，而不是补觉。',
      },
    ],
    focus: [
      {
        en: 'After an interruption, attention does not resume where it stopped — it restarts, and the restart is most of the cost.',
        fa: 'بعد از یک وقفه، توجه از جایی که ایستاده بود ادامه نمی‌دهد — از نو شروع می‌شود، و همین شروعِ دوباره بیشترِ هزینه است.',
        ar: 'بعد المقاطعة لا يستأنف الانتباه من حيث توقّف — بل يبدأ من جديد، والبدء من جديد هو معظم التكلفة.',
        zh: '被打断之后，注意力不会从停下的地方继续——它是重新启动的，而重启本身就是大部分代价。',
      },
      {
        en: 'A phone face-down on the desk still costs attention. Being reachable is the part that occupies you, not the screen being lit.',
        fa: 'گوشیِ رو‌به‌پایین روی میز هم توجه می‌گیرد. آنچه ذهنت را اشغال می‌کند در دسترس بودن است، نه روشن بودن صفحه.',
        ar: 'الهاتف المقلوب على المكتب يستهلك انتباهك أيضاً. ما يشغلك هو كونك قابلاً للوصول، لا كون الشاشة مضاءة.',
        zh: '正面朝下放在桌上的手机依然在消耗注意力。占据你的是「随时可被找到」，而不是屏幕亮着。',
      },
      {
        en: 'Deciding what you will do before you open the device is the single change that separates use from drift.',
        fa: 'تصمیم‌گرفتن درباره‌ی کاری که می‌خواهی بکنی، پیش از باز کردن دستگاه، همان یک تغییری است که استفاده را از سرگردانی جدا می‌کند.',
        ar: 'أن تقرّر ما ستفعله قبل أن تفتح الجهاز هو التغيير الوحيد الذي يفصل الاستخدام عن الانجراف.',
        zh: '在打开设备之前先决定要做什么——这一个改变，就把「使用」和「漂流」区分开了。',
      },
    ],
    social: [
      {
        en: 'How social time affects mood depends far more on whether you posted, replied and talked than on how many minutes it took.',
        fa: 'اثر زمان اجتماعی روی خلق‌وخو، خیلی بیشتر به این بستگی دارد که آیا پست گذاشتی، جواب دادی و حرف زدی، تا اینکه چند دقیقه طول کشید.',
        ar: 'تأثير الوقت الاجتماعي في المزاج يتوقف على ما إذا كنت قد نشرت وردّيت وتحدثت، أكثر بكثير من عدد الدقائق.',
        zh: '社交时间如何影响情绪，更多取决于你是否发布、回复和交谈，而不是花了多少分钟。',
      },
      {
        en: 'Comparison tracks who is in your feed, not how long you look at it — which is why muting a few accounts works better than a time limit.',
        fa: 'مقایسه به این بستگی دارد که چه کسی در فید توست، نه اینکه چقدر نگاهش می‌کنی — به همین دلیل بی‌صدا کردن چند حساب بهتر از محدودیت زمانی جواب می‌دهد.',
        ar: 'المقارنة ترتبط بمن يظهر في موجزك، لا بمدة نظرك إليه — ولهذا يعمل كتم بضعة حسابات أفضل من حدّ زمني.',
        zh: '比较取决于谁出现在你的信息流里，而不是你看了多久——所以静音几个账号，比设时间限制更管用。',
      },
    ],
    screen: [
      {
        en: 'Friction beats willpower. An extra step before an app is a decision you only have to make once, not every time.',
        fa: 'اصطکاک از اراده بهتر جواب می‌دهد. یک قدم اضافه پیش از یک اپ، تصمیمی است که فقط یک بار می‌گیری، نه هر بار.',
        ar: 'الاحتكاك يتفوّق على قوة الإرادة. خطوة إضافية قبل التطبيق قرار تتخذه مرة واحدة، لا في كل مرة.',
        zh: '阻力胜过意志力。在应用前多加一步，是你只需要做一次的决定，而不是每次都要做。',
      },
      {
        en: 'Total screen time predicts wellbeing poorly on its own. When it happens, and what it replaced, carry most of the signal.',
        fa: 'زمان کل صفحه به‌تنهایی پیش‌بینی ضعیفی از سلامت است. اینکه کِی اتفاق افتاده و جای چه چیزی را گرفته، بیشترِ سیگنال را حمل می‌کند.',
        ar: 'إجمالي وقت الشاشة وحده مؤشر ضعيف على العافية. متى حدث، وما الذي حلّ محلّه، يحملان معظم الإشارة.',
        zh: '单看屏幕总时长，对幸福感的预测很弱。它发生在什么时候、又替代了什么，才承载了大部分信号。',
      },
    ],
    body: [
      {
        en: 'Short movement changes mood faster than long movement does. The first ten minutes carry most of the effect.',
        fa: 'تحرک کوتاه سریع‌تر از تحرک طولانی خلق‌وخو را عوض می‌کند. ده دقیقه‌ی اول بیشترِ اثر را دارد.',
        ar: 'الحركة القصيرة تغيّر المزاج أسرع من الطويلة. أول عشر دقائق تحمل معظم الأثر.',
        zh: '短时间的活动比长时间更快改变情绪。前十分钟就承载了大部分效果。',
      },
      {
        en: 'Caffeine has a long half-life. The afternoon cup that feels harmless is often still in your system at bedtime.',
        fa: 'کافئین نیمه‌عمر بلندی دارد. فنجان بعدازظهر که بی‌ضرر به نظر می‌رسد، اغلب موقع خواب هنوز در بدنت است.',
        ar: 'للكافيين عمر نصف طويل. كوب بعد الظهر الذي يبدو غير ضار كثيراً ما يظل في جسمك وقت النوم.',
        zh: '咖啡因的半衰期很长。下午那杯看似无害的咖啡，往往到睡觉时还留在体内。',
      },
    ],
  };

  /* ---- Encouragement, chosen by what actually happened -------------
     Keyed by band and by direction. `{score}` and `{target}` are filled
     from the caller's real numbers; a line with no placeholder is one
     where a number would not have added anything. */
  const ENCOURAGEMENT = {
    strong_holding: [
      {
        en: "You're at {score}, and holding there is its own achievement — most people's numbers drift when nobody is watching them.",
        fa: 'روی {score} هستی، و همان‌جا ماندن خودش یک دستاورد است — عدد بیشتر آدم‌ها وقتی کسی نگاهشان نمی‌کند سُر می‌خورد.',
        ar: 'أنت عند {score}، والثبات عندها إنجاز بحد ذاته — أرقام معظم الناس تنزلق حين لا يراقبها أحد.',
        zh: '你在 {score}，能守住本身就是一种成就——大多数人的数字在没人盯着时都会滑落。',
      },
      {
        en: "{score} is a good place to be standing. The question worth asking now is which single habit is holding it up, so you protect that one.",
        fa: '{score} جای خوبی برای ایستادن است. سؤالی که حالا می‌ارزد بپرسی این است که کدام یک عادت دارد نگهش می‌دارد، تا همان را حفظ کنی.',
        ar: '{score} موضع جيد للوقوف فيه. والسؤال الجدير الآن: أي عادة واحدة تسنده، لتحمي تلك تحديداً.',
        zh: '{score} 是个不错的位置。现在值得问的是：是哪一个习惯在撑着它，好让你守住那一个。',
      },
    ],
    strong_rising: [
      {
        en: "You're at {score} and still climbing. Worth naming what changed, because that is the part you will want back if it ever slips.",
        fa: 'روی {score} هستی و هنوز بالا می‌روی. می‌ارزد اسم ببری چه چیزی عوض شد، چون همان چیزی است که اگر روزی سُر خورد دوباره می‌خواهی‌اش.',
        ar: 'أنت عند {score} وما زلت تصعد. يستحق أن تسمّي ما الذي تغيّر، فهو ما ستريد استعادته إن انزلق يوماً.',
        zh: '你在 {score}，而且还在上升。值得说清是什么变了，因为万一有天滑落，你想要回的正是它。',
      },
    ],
    middle_rising: [
      {
        en: "{score}, and the direction is up. Direction matters more than position at this point — you are already doing the harder half.",
        fa: '{score}، و جهت رو به بالاست. در این نقطه جهت از موقعیت مهم‌تر است — نیمه‌ی سخت‌ترش را همین حالا داری انجام می‌دهی.',
        ar: '{score}، والاتجاه صاعد. الاتجاه أهم من الموضع عند هذه النقطة — أنت تؤدي النصف الأصعب بالفعل.',
        zh: '{score}，而且方向向上。在这个阶段，方向比位置更重要——更难的那一半你已经在做了。',
      },
      {
        en: "You're at {score}. Nothing here needs a dramatic week — one signal moved deliberately is what actually shifts this number.",
        fa: 'روی {score} هستی. اینجا هیچ‌چیز به یک هفته‌ی پرهیجان نیاز ندارد — چیزی که واقعاً این عدد را جابه‌جا می‌کند، حرکت‌دادن آگاهانه‌ی یک سیگنال است.',
        ar: 'أنت عند {score}. لا شيء هنا يحتاج أسبوعاً درامياً — ما يحرّك هذا الرقم فعلاً هو إشارة واحدة تُحرَّك بقصد.',
        zh: '你在 {score}。这里不需要一个惊天动地的星期——真正让这个数字移动的，是有意识地改动一个信号。',
      },
    ],
    middle_falling: [
      {
        en: "{score}, and it has been sliding. That is worth taking seriously and it is also the easiest point to turn — the habits behind it have not set yet.",
        fa: '{score}، و داشته سُر می‌خورده. این هم جدی گرفتنش می‌ارزد و هم آسان‌ترین نقطه برای برگرداندن است — عادت‌های پشتش هنوز جا نیفتاده‌اند.',
        ar: '{score}، وقد كان ينزلق. هذا يستحق الأخذ بجدية، وهو أيضاً أسهل نقطة للتحوّل — فالعادات وراءه لم تترسّخ بعد.',
        zh: '{score}，而且一直在下滑。这值得认真对待，同时也是最容易扭转的时候——背后的习惯还没定型。',
      },
    ],
    low_any: [
      {
        en: "{score} is a low number, and I am not going to talk you out of what it says. What it does not say is anything about how fixed it is — every input behind it is something you can change.",
        fa: '{score} عدد پایینی است، و نمی‌خواهم از چیزی که می‌گوید منصرفت کنم. اما چیزی که نمی‌گوید این است که چقدر ثابت است — هر ورودی پشتش چیزی است که می‌توانی عوضش کنی.',
        ar: '{score} رقم منخفض، ولن أحاول أن أثنيك عمّا يقوله. لكنه لا يقول شيئاً عن مدى ثباته — كل مدخل وراءه شيء يمكنك تغييره.',
        zh: '{score} 是个低分，我不会试图说服你它没那么糟。但它没有说的是：它有多难改变——它背后的每一项输入，都是你能动的。',
      },
      {
        en: "At {score}, the useful move is not five changes — it is one, kept for a week. This number responds to repetition much more than to effort.",
        fa: 'روی {score}، کار مفید پنج تغییر نیست — یک تغییر است که یک هفته نگهش داری. این عدد به تکرار خیلی بیشتر از تلاش پاسخ می‌دهد.',
        ar: 'عند {score}، الخطوة المفيدة ليست خمسة تغييرات — بل تغيير واحد يُحافَظ عليه أسبوعاً. هذا الرقم يستجيب للتكرار أكثر بكثير من الجهد.',
        zh: '在 {score} 这个位置，有用的不是五个改变——而是一个改变，坚持一周。这个数字对重复的回应，远大于对努力的回应。',
      },
    ],
    first_time: [
      {
        en: 'One check-in is already more than most people ever log about themselves. The number matters less right now than the fact that you have a baseline at all.',
        fa: 'یک بررسی، همین حالا بیشتر از چیزی است که بیشتر آدم‌ها هرگز درباره‌ی خودشان ثبت می‌کنند. عدد الان کمتر از این اهمیت دارد که اصلاً یک خط پایه داری.',
        ar: 'فحص واحد يفوق بالفعل ما يسجّله معظم الناس عن أنفسهم يوماً. الرقم أقل أهمية الآن من كونك صرت تملك خط أساس أصلاً.',
        zh: '一次记录，已经比大多数人一生中对自己做的记录都多。此刻数字并不重要，重要的是你终于有了一个基准。',
      },
    ],
  };

  /* Same person, same day, same line - so re-opening a page does not
     shuffle the text, and tomorrow is not a repeat. */
  function dayIndex() {
    return Math.floor(Date.now() / 86400000);
  }

  function rotate(list, offset) {
    if (!list || !list.length) return null;
    return list[(dayIndex() + (offset || 0)) % list.length];
  }

  /**
   * bandFor(score, direction, entries) -> key into ENCOURAGEMENT
   * `direction` is 'up' | 'down' | 'flat' | null, `entries` the number
   * of check-ins logged. Thresholds match tone_service.band_for_score,
   * so the encouragement never disagrees with the result framing.
   */
  function bandFor(score, direction, entries) {
    if (entries != null && entries <= 1) return 'first_time';
    if (score == null) return 'middle_rising';
    if (score < 40) return 'low_any';
    if (score >= 80) return direction === 'up' ? 'strong_rising' : 'strong_holding';
    return direction === 'down' ? 'middle_falling' : 'middle_rising';
  }

  /**
   * encouragement({ score, direction, entries }) -> string
   * Returns '' rather than a generic line when there is no score to
   * speak about, so the caller can stay quiet instead of padding.
   */
  function encouragement(ctx) {
    ctx = ctx || {};
    const band = bandFor(ctx.score, ctx.direction, ctx.entries);
    const line = rotate(ENCOURAGEMENT[band], 0);
    if (!line) return '';
    const text = pick(line);
    if (ctx.score == null) return text.replace(/\{score\}/g, '').trim();
    return text.replace(/\{score\}/g, String(Math.round(ctx.score)));
  }

  /**
   * fact(topic) -> string
   * `topic` is one of the FACTS keys; an unknown or absent topic draws
   * from the whole set, so the coach always has something true to say.
   */
  function fact(topic) {
    const group = FACTS[topic];
    if (group) return pick(rotate(group, 0));
    const all = Object.keys(FACTS).reduce((acc, k) => acc.concat(FACTS[k]), []);
    return pick(rotate(all, 0)) || '';
  }

  /* Which fact group belongs to a given model feature, so a fact can be
     chosen to match the user's own weakest signal rather than at random. */
  const TOPIC_FOR_FIELD = {
    sleep_hours: 'sleep', sleep_quality_1_10: 'sleep', pre_sleep_screen_min: 'sleep',
    pre_sleep_ratio: 'sleep', night_ratio: 'sleep', night_screen_min: 'sleep',
    caffeine_cups_per_day: 'sleep',
    focus_0_100: 'focus', productivity_0_100: 'focus', fragmentation_index_0_100: 'focus',
    notifications_per_day: 'focus', notification_density: 'focus',
    pickups_per_day: 'focus', pickup_density: 'focus',
    app_opens_per_day: 'focus', app_open_density: 'focus', work_study_ratio: 'focus',
    social_min: 'social', social_ratio: 'social',
    social_comparison_1_10: 'social', fomo_1_10: 'social',
    total_screen_min: 'screen', gaming_min: 'screen', gaming_ratio: 'screen',
    video_min: 'screen', other_ratio: 'screen', digital_dependence_0_100: 'screen',
    physical_activity_min_per_day: 'body', stress_0_10: 'body', mental_fatigue_0_10: 'body',
  };

  function topicForField(field) {
    return TOPIC_FOR_FIELD[field] || null;
  }

  window.DWMotivation = {
    encouragement, fact, bandFor, topicForField,
    FACTS, ENCOURAGEMENT, TOPIC_FOR_FIELD,
  };
})();
