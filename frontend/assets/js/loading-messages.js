/*
  Loading-screen copy, game-style.

  Hard rules applied to every line in here:
  - NO medical, diagnostic, or treatment claims. Nothing says a habit
    causes/cures a condition. Where research is referenced it is phrased
    as an association or a general observation, never as advice about a
    disease.
  - Three declared categories: 'fact' (research-flavoured), 'tip'
    (something you can act on today), 'motivation' (encouragement).
  - Every line exists in all four languages. Arabic and Chinese were
    written rather than machine-translated, which is why they are not
    word-for-word matches of the English - a loading line that reads
    like a translation is worse than one that reads naturally and says
    the same thing.
*/
(function () {
  const MESSAGES = {
    en: [
      { c: 'fact', t: 'Attention takes time to recover after an interruption — which is why scattered checking costs more than the seconds it appears to.' },
      { c: 'fact', t: 'Bright light in the late evening is associated with a later body clock, which is why night-time screen habits show up in sleep data.' },
      { c: 'fact', t: 'People consistently underestimate their own screen time — usually by a wide margin.' },
      { c: 'fact', t: 'The number of times you pick up a device often predicts focus better than total hours does.' },
      { c: 'fact', t: 'Notification volume and reported stress tend to move together across large samples.' },
      { c: 'fact', t: 'Passive scrolling and active messaging show different associations with mood — how you use an app matters, not just how long.' },
      { c: 'fact', t: 'Sleep consistency — same times each day — often tracks wellbeing more closely than total hours slept.' },
      { c: 'fact', t: 'Short daytime movement breaks are linked with better sustained attention later in the day.' },
      { c: 'fact', t: 'Social comparison is one of the more consistent signals in digital-wellbeing research.' },
      { c: 'fact', t: 'Fragmented usage — many short sessions — is a different pattern from long focused sessions, even at identical totals.' },

      { c: 'tip', t: 'Turn off notifications for your three noisiest apps. Not all of them — just the loudest three.' },
      { c: 'tip', t: 'Put the phone on the far side of the room while you sleep. Distance does most of the work.' },
      { c: 'tip', t: 'Batch your message checks into a few set windows instead of reacting instantly.' },
      { c: 'tip', t: 'Try greyscale in the evening. It makes the screen a lot less magnetic.' },
      { c: 'tip', t: 'Move one scrolling session to a walk. Same time, very different result.' },
      { c: 'tip', t: 'Charge your device outside the bedroom tonight and see how the morning feels.' },
      { c: 'tip', t: 'Before opening an app, name what you want from it. If you cannot, that is useful information.' },
      { c: 'tip', t: 'Protect one 25-minute block a day with the phone in another room.' },
      { c: 'tip', t: 'Set an app timer and let it actually interrupt you — an ignored limit is not a limit.' },
      { c: 'tip', t: 'Give yourself a fixed cut-off time for screens and treat it like a meeting.' },

      { c: 'motivation', t: 'Small changes that stick beat dramatic ones that do not.' },
      { c: 'motivation', t: 'You are measuring this. That already puts you ahead of guessing.' },
      { c: 'motivation', t: 'A low number is a snapshot of a week, not a verdict on you.' },
      { c: 'motivation', t: 'Consistency compounds. One better evening is worth more than one perfect day.' },
      { c: 'motivation', t: 'You do not need to quit anything. Adding a little friction is usually enough.' },
      { c: 'motivation', t: 'Progress here is rarely a straight line — the direction matters more than any single day.' },
      { c: 'motivation', t: 'Pick one habit. Just one. That is how this actually works.' },
      { c: 'motivation', t: 'Being honest in the form is the hard part, and you already did it.' },
      { c: 'motivation', t: 'The goal is not a perfect score. It is a week that feels better than the last one.' },
      { c: 'motivation', t: 'Attention is worth protecting. You are allowed to be deliberate about it.' },
    ],
    fa: [
      { c: 'fact', t: 'توجه بعد از هر وقفه زمان می‌برد تا بازیابی شود — به همین دلیل چک‌کردن‌های پراکنده بیشتر از چند ثانیه‌ای که به نظر می‌رسند هزینه دارند.' },
      { c: 'fact', t: 'نور شدید در ساعات پایانی شب با به‌تعویق‌افتادن ساعت بدن مرتبط است؛ برای همین عادت‌های شبانه در داده‌ی خواب دیده می‌شوند.' },
      { c: 'fact', t: 'مردم معمولاً زمان استفاده از صفحه‌نمایش خود را کمتر از واقعیت تخمین می‌زنند — اغلب با اختلاف زیاد.' },
      { c: 'fact', t: 'تعداد دفعاتی که گوشی را برمی‌داری، اغلب بهتر از مجموع ساعت‌ها تمرکز را پیش‌بینی می‌کند.' },
      { c: 'fact', t: 'حجم اعلان‌ها و میزان استرس گزارش‌شده در نمونه‌های بزرگ معمولاً هم‌جهت حرکت می‌کنند.' },
      { c: 'fact', t: 'اسکرول منفعل و گفتگوی فعال ارتباط متفاوتی با حال‌وهوا نشان می‌دهند — نحوه‌ی استفاده مهم است، نه فقط مدت آن.' },
      { c: 'fact', t: 'ثبات خواب — ساعت یکسان در هر روز — اغلب بیشتر از مجموع ساعت‌های خواب با بهزیستی هم‌راستاست.' },
      { c: 'fact', t: 'وقفه‌های کوتاه حرکتی در طول روز با تمرکز پایدارتر در ادامه‌ی روز مرتبط‌اند.' },
      { c: 'fact', t: 'مقایسه‌ی اجتماعی یکی از پایدارترین سیگنال‌ها در پژوهش‌های سلامت دیجیتال است.' },
      { c: 'fact', t: 'استفاده‌ی تکه‌تکه — جلسات کوتاه و پرتعداد — الگویی متفاوت از جلسات طولانی و متمرکز است، حتی با مجموع زمان یکسان.' },

      { c: 'tip', t: 'اعلان سه اپلیکیشن پرسروصداتر را خاموش کن. نه همه‌شان — فقط همان سه تا.' },
      { c: 'tip', t: 'موقع خواب گوشی را آن‌سوی اتاق بگذار. فاصله بیشتر کار را انجام می‌دهد.' },
      { c: 'tip', t: 'به‌جای واکنش آنی، پیام‌ها را در چند بازه‌ی مشخص چک کن.' },
      { c: 'tip', t: 'عصرها حالت سیاه‌وسفید را امتحان کن. صفحه خیلی کمتر جذب‌کننده می‌شود.' },
      { c: 'tip', t: 'یکی از جلسات اسکرول را با پیاده‌روی جایگزین کن. همان زمان، نتیجه‌ای کاملاً متفاوت.' },
      { c: 'tip', t: 'امشب گوشی را بیرون از اتاق خواب شارژ کن و ببین صبح چه حسی دارد.' },
      { c: 'tip', t: 'قبل از باز کردن یک اپ، بگو دقیقاً چه می‌خواهی. اگر نتوانستی، همین خودش اطلاعات مفیدی است.' },
      { c: 'tip', t: 'روزی یک بازه‌ی ۲۵ دقیقه‌ای را با گوشی در اتاق دیگر محافظت کن.' },
      { c: 'tip', t: 'برای اپ‌ها تایمر بگذار و بگذار واقعاً کارت را قطع کند — محدودیتی که نادیده گرفته شود، محدودیت نیست.' },
      { c: 'tip', t: 'یک ساعت مشخص برای پایان کار با صفحه‌نمایش تعیین کن و مثل یک قرار کاری با آن رفتار کن.' },

      { c: 'motivation', t: 'تغییرهای کوچکی که می‌مانند، از تغییرهای بزرگی که نمی‌مانند بهترند.' },
      { c: 'motivation', t: 'تو داری این را اندازه می‌گیری. همین تو را از حدس‌زدن جلوتر می‌برد.' },
      { c: 'motivation', t: 'عدد پایین یک عکس از یک هفته است، نه حکمی درباره‌ی تو.' },
      { c: 'motivation', t: 'ثبات جمع می‌شود. یک عصر بهتر ارزشش از یک روز بی‌نقص بیشتر است.' },
      { c: 'motivation', t: 'لازم نیست چیزی را ترک کنی. معمولاً کمی سخت‌ترکردن دسترسی کافی است.' },
      { c: 'motivation', t: 'پیشرفت اینجا معمولاً خط مستقیم نیست — جهت از هر روز خاصی مهم‌تر است.' },
      { c: 'motivation', t: 'یک عادت انتخاب کن. فقط یکی. واقعاً این‌طوری جواب می‌دهد.' },
      { c: 'motivation', t: 'صادق‌بودن در فرم بخش سخت ماجراست، و تو همین حالا انجامش دادی.' },
      { c: 'motivation', t: 'هدف امتیاز کامل نیست. هدف هفته‌ای است که از هفته‌ی قبل بهتر حس شود.' },
      { c: 'motivation', t: 'توجه‌ات ارزش محافظت دارد. حق داری درباره‌اش سنجیده عمل کنی.' },
    ],
    ar: [
      { c: 'fact', t: 'يحتاج الانتباه وقتاً ليتعافى بعد المقاطعة — ولهذا يكلّف التفقّد المتناثر أكثر من الثواني التي يبدو عليها.' },
      { c: 'fact', t: 'يرتبط الضوء الساطع في وقت متأخر من المساء بساعة بيولوجية متأخرة، ولهذا تظهر عادات الشاشة الليلية في بيانات النوم.' },
      { c: 'fact', t: 'يقلّل الناس باستمرار من تقدير وقت شاشتهم — وبفارق كبير عادةً.' },
      { c: 'fact', t: 'عدد مرات التقاطك للجهاز يتنبأ بالتركيز أفضل من مجموع الساعات في كثير من الأحيان.' },
      { c: 'fact', t: 'يميل حجم الإشعارات والتوتر المُبلَّغ عنه إلى التحرك معاً عبر عينات كبيرة.' },
      { c: 'fact', t: 'يُظهر التصفح السلبي والمراسلة النشطة ارتباطات مختلفة بالمزاج — فطريقة استخدامك للتطبيق تهمّ، لا مدته وحدها.' },
      { c: 'fact', t: 'انتظام النوم — المواعيد نفسها كل يوم — يواكب العافية عن قرب أكثر من مجموع ساعات النوم غالباً.' },
      { c: 'fact', t: 'ترتبط فترات الحركة القصيرة نهاراً بانتباه أفضل وأطول لاحقاً في اليوم.' },
      { c: 'fact', t: 'المقارنة الاجتماعية من أكثر الإشارات اتساقاً في أبحاث العافية الرقمية.' },
      { c: 'fact', t: 'الاستخدام المجزّأ — جلسات قصيرة كثيرة — نمط مختلف عن الجلسات الطويلة المركّزة، حتى عند تساوي المجموع.' },
      { c: 'tip', t: 'أوقف إشعارات أكثر ثلاثة تطبيقات ضجيجاً لديك. ليس كلها — الثلاثة الأعلى صوتاً فقط.' },
      { c: 'tip', t: 'ضع الهاتف في الطرف البعيد من الغرفة أثناء نومك. المسافة تقوم بمعظم العمل.' },
      { c: 'tip', t: 'اجمع تفقّد رسائلك في نوافذ محددة قليلة بدل الرد الفوري.' },
      { c: 'tip', t: 'جرّب التدرّج الرمادي في المساء. يجعل الشاشة أقل جذباً بكثير.' },
      { c: 'tip', t: 'انقل جلسة تصفّح واحدة إلى مشية. الوقت نفسه، ونتيجة مختلفة تماماً.' },
      { c: 'tip', t: 'اشحن جهازك خارج غرفة النوم الليلة وانظر كيف يكون شعور الصباح.' },
      { c: 'tip', t: 'قبل فتح أي تطبيق، سمِّ ما تريده منه. وإن لم تستطع، فتلك معلومة مفيدة.' },
      { c: 'tip', t: 'احمِ كتلة واحدة من خمس وعشرين دقيقة يومياً والهاتف في غرفة أخرى.' },
      { c: 'tip', t: 'اضبط مؤقتاً للتطبيق ودعه يقاطعك فعلاً — الحد الذي يُتجاهَل ليس حداً.' },
      { c: 'tip', t: 'حدّد لنفسك وقت توقف ثابتاً للشاشات وعامله كموعد لا يُلغى.' },
      { c: 'motivation', t: 'التغييرات الصغيرة التي تدوم تتفوق على الكبيرة التي لا تدوم.' },
      { c: 'motivation', t: 'أنت تقيس هذا. وهذا وحده يضعك متقدماً على التخمين.' },
      { c: 'motivation', t: 'الرقم المنخفض لقطة لأسبوع، لا حكم عليك.' },
      { c: 'motivation', t: 'الاستمرار يتراكم. أمسية أفضل واحدة تساوي أكثر من يوم مثالي واحد.' },
      { c: 'motivation', t: 'لا يلزمك أن تقلع عن شيء. إضافة قليل من الاحتكاك تكفي عادةً.' },
      { c: 'motivation', t: 'التقدّم هنا نادراً ما يكون خطاً مستقيماً — الاتجاه أهم من أي يوم بمفرده.' },
      { c: 'motivation', t: 'اختر عادة واحدة. واحدة فقط. هكذا ينجح هذا فعلاً.' },
      { c: 'motivation', t: 'الصدق في النموذج هو الجزء الصعب، وقد فعلته للتو.' },
      { c: 'motivation', t: 'الهدف ليس درجة كاملة. الهدف أسبوع تشعر فيه أفضل من الذي قبله.' },
      { c: 'motivation', t: 'الانتباه يستحق الحماية. ومن حقك أن تكون مقصوداً بشأنه.' },
    ],
    zh: [
      { c: 'fact', t: '注意力在被打断之后需要时间才能恢复——这就是为什么零散地查看，代价远高于它看起来的那几秒。' },
      { c: 'fact', t: '深夜的强光与更晚的生物钟相关联，这就是为什么夜间的屏幕习惯会出现在睡眠数据里。' },
      { c: 'fact', t: '人们总是低估自己的屏幕时间——而且通常低估得很多。' },
      { c: 'fact', t: '你拿起设备的次数，往往比总时长更能预测专注度。' },
      { c: 'fact', t: '在大样本中，通知的数量和人们报告的压力往往一起变化。' },
      { c: 'fact', t: '被动刷屏和主动发消息，与情绪的关联并不相同——你怎么用一个应用，和用了多久同样重要。' },
      { c: 'fact', t: '睡眠的规律性——每天在相同的时间——往往比总睡眠时长更贴近幸福感。' },
      { c: 'fact', t: '白天短暂的活动休息，与当天稍后更持久的注意力有关。' },
      { c: 'fact', t: '社会比较是数字健康研究中较为一致的信号之一。' },
      { c: 'fact', t: '碎片化的使用——很多次短会话——与长时间的专注会话是不同的模式，即便总时长完全相同。' },
      { c: 'tip', t: '关掉你最吵的三个应用的通知。不是全部——只要最响的那三个。' },
      { c: 'tip', t: '睡觉时把手机放在房间的另一头。距离本身就完成了大部分工作。' },
      { c: 'tip', t: '把查看消息集中到几个固定时段，而不是立刻回应。' },
      { c: 'tip', t: '晚上试试灰度模式。它会让屏幕的吸引力小很多。' },
      { c: 'tip', t: '把一次刷手机换成一次散步。同样的时间，结果非常不同。' },
      { c: 'tip', t: '今晚把设备放在卧室外充电，看看早上感觉如何。' },
      { c: 'tip', t: '打开一个应用之前，先说出你想从它那里得到什么。如果说不出来，那本身就是有用的信息。' },
      { c: 'tip', t: '每天守住一个二十五分钟的时段，手机放在另一个房间。' },
      { c: 'tip', t: '设一个应用计时器，并且真的让它打断你——被忽略的限制不是限制。' },
      { c: 'tip', t: '给自己定一个固定的屏幕截止时间，并把它当作一场不能取消的会议。' },
      { c: 'motivation', t: '能坚持下来的小改变，胜过坚持不下来的大改变。' },
      { c: 'motivation', t: '你正在测量这件事。仅这一点就已经胜过凭感觉猜。' },
      { c: 'motivation', t: '一个偏低的数字是一周的快照，不是对你这个人的判决。' },
      { c: 'motivation', t: '坚持会累积。一个更好的夜晚，比一个完美的日子更有价值。' },
      { c: 'motivation', t: '你不需要戒掉任何东西。增加一点点摩擦，通常就够了。' },
      { c: 'motivation', t: '这里的进步很少是一条直线——方向比任何单独的一天都重要。' },
      { c: 'motivation', t: '挑一个习惯。就一个。这才是它真正起作用的方式。' },
      { c: 'motivation', t: '在表单里保持诚实是最难的部分，而你已经做到了。' },
      { c: 'motivation', t: '目标不是满分。目标是一个比上周感觉更好的一周。' },
      { c: 'motivation', t: '注意力值得被保护。你完全可以为它刻意一点。' },
    ],
  };

  function poolFor(lang) {
    return MESSAGES[lang] || MESSAGES.en;
  }

  /* Shuffled queue: guarantees no repeat until the whole pool is used,
     so a user never sees the same line twice in one loading screen. */
  function createRotator(lang) {
    let pool = poolFor(lang).slice();
    let queue = [];
    function refill() {
      queue = pool.slice();
      for (let i = queue.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [queue[i], queue[j]] = [queue[j], queue[i]];
      }
    }
    refill();
    return {
      next() {
        if (!queue.length) refill();
        return queue.pop();
      },
      size: pool.length,
    };
  }

  window.DWLoadingMessages = { createRotator, poolFor, MESSAGES };
})();
