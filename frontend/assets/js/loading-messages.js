/*
  Loading-screen copy, game-style.

  Hard rules applied to every line in here:
  - NO medical, diagnostic, or treatment claims. Nothing says a habit
    causes/cures a condition. Where research is referenced it is phrased
    as an association or a general observation, never as advice about a
    disease.
  - Three declared categories: 'fact' (research-flavoured), 'tip'
    (something you can act on today), 'motivation' (encouragement).
  - Every line exists in English and Persian. Arabic/Chinese fall back to
    English rather than shipping a machine-translated approximation.
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
