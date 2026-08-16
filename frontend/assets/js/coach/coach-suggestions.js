/*
  DWCoachSuggestions — "what should I actually do?", answered in two
  halves.

  What this replaces
  ------------------
  The coach could already answer "what is weak?" and "what am I doing
  well?" - two separate questions, each returning a list of signals with
  the user's number against its target. Read as advice that is thin: it
  names the signal and stops. "Sleep 5.4 / 7.5" is a diagnosis, not
  something to do tonight.

  And nobody asks two questions. Someone opening the coach asks one -
  "how do I get better" - and the honest answer to that has two halves,
  because the two are genuinely different work:

    1. the habits already holding, and how to keep them holding. This is
       the cheaper half and the one that gets dropped first, so it goes
       FIRST rather than as an afterthought.
    2. the habits that need work, and specific ways in.

  Each half carries several ideas, not one, because one idea that does
  not suit you is the same as no idea.

  What is real here and what is written
  -------------------------------------
  Which signals appear, which half they land in, and every number quoted
  are the plan's own (`plan_tracks` from services/improvement_plan_service
  .py) - the same arithmetic the 7-day plan uses, so the coach and the
  plan can never disagree about what is wrong.

  The IDEAS are written, and they have to be: no model in this app
  produces behavioural advice, and generating a sentence that sounds like
  advice is exactly the failure mode this codebase avoids everywhere
  else. They are indexed by signal and by half, so an idea can only ever
  be shown against the signal it was written for.
*/
(function () {
  const P = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);

  /* Ideas per signal. Two banks per field:
       fix  - shown when the signal is on the strengthen list
       keep - shown when it is on the maintain list
     Three each, because the point is to offer a choice. They are
     deliberately concrete and small - "put the charger in another room"
     is something a person can do tonight; "improve your sleep hygiene"
     is not. */
  const IDEAS = {
    sleep_hours: {
      fix: [
        { en: 'Pick a lights-out time and set an alarm for it, not just for waking.',
          fa: 'یک ساعت خاموشی چراغ انتخاب کن و برایش زنگ بگذار — نه فقط برای بیدارشدن.',
          ar: 'اختر وقتاً لإطفاء الضوء واضبط له منبّهاً، لا للاستيقاظ فقط.',
          zh: '定一个熄灯时间，并为它设个闹钟——不只为起床设。' },
        { en: 'Charge the phone in another room. The walk back is usually enough of a barrier.',
          fa: 'گوشی را در اتاق دیگری شارژ کن. همان چند قدم راه معمولاً کافی است.',
          ar: 'اشحن الهاتف في غرفة أخرى. تلك الخطوات القليلة حاجز كافٍ عادةً.',
          zh: '把手机放到另一个房间充电。走那几步路通常就够挡住它了。' },
        { en: 'Move the wake-up time later by 20 minutes for a week before touching bedtime — it is the easier end to shift.',
          fa: 'یک هفته وقت بیدارشدن را ۲۰ دقیقه دیرتر کن، قبل از اینکه به وقت خواب دست بزنی — این سمت آسان‌ترش است.',
          ar: 'أخّر وقت الاستيقاظ ٢٠ دقيقة لأسبوع قبل أن تمسّ وقت النوم — هذا الطرف الأسهل.',
          zh: '先把起床时间往后挪 20 分钟，坚持一周，再去动睡觉时间——这一头更容易挪。' },
      ],
      keep: [
        { en: 'Keep the wake-up time fixed even at weekends — that is what is holding the rest steady.',
          fa: 'ساعت بیدارشدن را حتی آخر هفته ثابت نگه دار — همین است که بقیه را سرِ جا نگه داشته.',
          ar: 'أبقِ وقت الاستيقاظ ثابتاً حتى في العطلة — هو ما يُبقي البقية مستقرة.',
          zh: '连周末也保持起床时间不变——正是它稳住了其他一切。' },
        { en: 'Protect the hour before bed the way you would protect a meeting.',
          fa: 'از ساعت قبل از خواب همان‌طور محافظت کن که از یک جلسه محافظت می‌کنی.',
          ar: 'احمِ الساعة التي تسبق النوم كما تحمي موعداً مهماً.',
          zh: '像守住一个会议一样守住睡前那一小时。' },
        { en: 'When a late night happens, treat it as one night. The streak is the asset, not the perfect record.',
          fa: 'اگر شبی دیر خوابیدی، همان یک شب حسابش کن. چیزی که ارزش دارد تداوم است، نه پرونده‌ی بی‌نقص.',
          ar: 'إن سهرت ليلة، فاعتبرها ليلة واحدة. الاستمرارية هي الرصيد، لا السجل المثالي.',
          zh: '偶尔晚睡就当作只是那一晚。有价值的是连续性，不是完美记录。' },
      ],
    },
    social_min: {
      fix: [
        { en: 'Move the two apps you open most off the home screen. Reaching for them should take a search.',
          fa: 'دو اپی که بیشتر از همه باز می‌کنی را از صفحه‌ی اصلی بردار. رسیدن به آن‌ها باید یک جست‌وجو لازم داشته باشد.',
          ar: 'انقل التطبيقين الأكثر فتحاً بعيداً عن الشاشة الرئيسية. الوصول إليهما يجب أن يتطلّب بحثاً.',
          zh: '把你最常打开的两个应用移出主屏。要用它们，得先搜索一下。' },
        { en: 'Give yourself one named window for it — after dinner, say — instead of trying to use less all day.',
          fa: 'یک بازه‌ی مشخص برایش تعیین کن — مثلاً بعد از شام — به‌جای اینکه تمام روز سعی کنی کمتر استفاده کنی.',
          ar: 'خصّص نافذة واحدة محدّدة له — بعد العشاء مثلاً — بدل محاولة التقليل طوال اليوم.',
          zh: '给它一个明确的时段——比如晚饭后——而不是整天都在试着少用。' },
        { en: 'Log out of one of them. Re-typing a password is a small cost that lands at exactly the right moment.',
          fa: 'از یکی‌شان خارج شو. تایپ‌کردن دوباره‌ی رمز هزینه‌ی کوچکی است که دقیقاً در لحظه‌ی درست وارد می‌شود.',
          ar: 'سجّل الخروج من أحدها. إعادة كتابة كلمة المرور تكلفة صغيرة تأتي في اللحظة المناسبة تماماً.',
          zh: '从其中一个退出登录。重新输密码的代价很小，却正好落在关键的那一刻。' },
      ],
      keep: [
        { en: 'Whatever boundary you are already keeping, name it out loud to yourself — unnamed rules erode quietly.',
          fa: 'هر مرزی که الان رعایت می‌کنی، برای خودت به زبان بیاور — قاعده‌ی بی‌نام بی‌سروصدا فرسوده می‌شود.',
          ar: 'أياً كان الحدّ الذي تلتزم به، سمِّه لنفسك بصوت مسموع — القواعد بلا اسم تتآكل بهدوء.',
          zh: '你现在守着的那条界线，给它起个名字说出来——没名字的规则会悄悄瓦解。' },
        { en: 'Watch the first ten minutes after you unlock. That is where the number usually starts to slip.',
          fa: 'ده دقیقه‌ی اول بعد از باز کردن قفل را حواست باشد. عدد معمولاً از همان‌جا شروع به لغزیدن می‌کند.',
          ar: 'راقب أول عشر دقائق بعد فتح القفل. من هناك يبدأ الرقم في الانزلاق عادةً.',
          zh: '留意解锁后的头十分钟。数字通常就是从那里开始往上滑的。' },
        { en: 'Keep one screen-free evening a week as the anchor, even in a good week.',
          fa: 'یک شبِ بدون صفحه‌نمایش در هفته را به‌عنوان لنگر نگه دار، حتی در هفته‌ی خوب.',
          ar: 'احتفظ بمساء واحد بلا شاشات كل أسبوع كمرساة، حتى في أسبوع جيد.',
          zh: '每周留一个无屏幕的夜晚当作锚点，即使这周本来就不错。' },
      ],
    },
    stress_0_10: {
      fix: [
        { en: 'Put a five-minute gap between finishing work and picking the phone back up.',
          fa: 'بین تمام‌شدن کار و برداشتن دوباره‌ی گوشی، پنج دقیقه فاصله بگذار.',
          ar: 'اترك خمس دقائق بين انتهاء العمل والتقاط الهاتف من جديد.',
          zh: '在结束工作和重新拿起手机之间，留出五分钟的空档。' },
        { en: 'Write the three things on your mind on paper before bed. It is the rehearsing that costs, not the thinking.',
          fa: 'سه چیزی که ذهنت را مشغول کرده قبل از خواب روی کاغذ بنویس. چیزی که هزینه دارد مرور کردن است، نه فکر کردن.',
          ar: 'اكتب الأشياء الثلاثة التي تشغل بالك على ورق قبل النوم. المكلف هو الاجترار لا التفكير.',
          zh: '睡前把心里的三件事写在纸上。真正消耗你的是反复咀嚼，不是思考本身。' },
        { en: 'Pick the one recurring thing that spikes it and change one detail of it, not all of it.',
          fa: 'آن یک چیز تکرارشونده که استرست را بالا می‌برد پیدا کن و فقط یک جزئیاتش را عوض کن، نه همه‌اش.',
          ar: 'حدّد الشيء المتكرّر الذي يرفعه، وغيّر تفصيلاً واحداً فيه لا كلّه.',
          zh: '找出那件反复让你紧绷的事，只改它的一个细节，而不是全部。' },
      ],
      keep: [
        { en: 'Whatever is currently absorbing it — keep doing exactly that, especially on the busy weeks.',
          fa: 'هر چیزی که الان دارد جذبش می‌کند — دقیقاً همان را ادامه بده، مخصوصاً در هفته‌های شلوغ.',
          ar: 'أياً كان ما يمتصّه الآن — واصله بالضبط، خاصة في الأسابيع المزدحمة.',
          zh: '现在是什么在替你消化压力——就继续那样做，尤其在忙碌的那几周。' },
        { en: 'Notice which day of the week it climbs. Knowing the shape is most of managing it.',
          fa: 'حواست باشد کدام روز هفته بالا می‌رود. شناختن الگو بیشترِ مدیریت‌کردنش است.',
          ar: 'لاحظ في أي يوم من الأسبوع يرتفع. معرفة النمط هي معظم إدارته.',
          zh: '留意它在一周的哪一天升高。看清形状，就管住了大半。' },
        { en: 'Do not add anything. A low number here is usually the result of something you already dropped.',
          fa: 'چیزی اضافه نکن. عدد پایین اینجا معمولاً نتیجه‌ی چیزی است که قبلاً کنار گذاشته‌ای.',
          ar: 'لا تُضف شيئاً. الرقم المنخفض هنا عادةً نتيجة شيء تخلّيت عنه بالفعل.',
          zh: '别再加东西了。这里的低数值，通常来自你已经放下的某件事。' },
      ],
    },
    physical_activity_min_per_day: {
      fix: [
        { en: 'Attach it to something you already do — the walk happens after the coffee, not "sometime today".',
          fa: 'به کاری که همین حالا انجام می‌دهی وصلش کن — پیاده‌روی بعد از قهوه اتفاق می‌افتد، نه «یک وقتی در روز».',
          ar: 'اربطه بشيء تفعله أصلاً — المشي يأتي بعد القهوة، لا "في وقت ما اليوم".',
          zh: '把它挂在你已有的习惯上——散步安排在喝完咖啡之后，而不是"今天找个时间"。' },
        { en: 'Ten minutes counts. The number this is measured against is a daily average, not a workout.',
          fa: 'ده دقیقه هم حساب است. عددی که با آن سنجیده می‌شوی میانگین روزانه است، نه یک تمرین.',
          ar: 'عشر دقائق تُحتسب. الرقم المقارن هنا متوسط يومي لا تمرين.',
          zh: '十分钟也算数。这里比对的是每日平均值，不是一次锻炼。' },
        { en: 'Leave the shoes where you will trip over them. Most of the resistance is at the door.',
          fa: 'کفش‌ها را جایی بگذار که پایت به آن‌ها بخورد. بیشترِ مقاومت پشت در است.',
          ar: 'ضع الحذاء حيث تتعثّر به. معظم المقاومة عند الباب.',
          zh: '把鞋放在你会绊到的地方。大部分阻力都卡在门口。' },
      ],
      keep: [
        { en: 'Keep the time of day fixed. Movement that has an hour survives a busy week; movement that floats does not.',
          fa: 'ساعتش را ثابت نگه دار. حرکتی که ساعت دارد از هفته‌ی شلوغ جان سالم به در می‌برد؛ حرکتِ شناور نه.',
          ar: 'أبقِ توقيته ثابتاً. الحركة التي لها ساعة تنجو من أسبوع مزدحم، والعائمة لا.',
          zh: '把时间固定下来。有固定钟点的运动能熬过忙碌的一周，飘着的不能。' },
        { en: 'On a bad day, do a short version rather than none. The habit is the streak, not the distance.',
          fa: 'در روز بد، نسخه‌ی کوتاهش را انجام بده نه هیچ. عادت یعنی تداوم، نه مسافت.',
          ar: 'في يوم سيئ، افعل نسخة قصيرة بدل لا شيء. العادة هي الاستمرار لا المسافة.',
          zh: '状态差的日子，做个缩短版，而不是完全不做。习惯在于连续，不在于距离。' },
        { en: 'This one tends to carry sleep and stress with it. Protecting it protects two other numbers.',
          fa: 'این یکی معمولاً خواب و استرس را هم با خودش می‌برد. محافظت از آن یعنی محافظت از دو عدد دیگر.',
          ar: 'هذا عادةً يجرّ معه النوم والتوتر. حمايته حماية لرقمين آخرين.',
          zh: '这一项通常会带动睡眠和压力。守住它，等于守住另外两个数字。' },
      ],
    },
    notifications_per_day: {
      fix: [
        { en: 'Turn off notifications for everything that is not a person. Almost nothing else needs to interrupt you.',
          fa: 'اعلان هر چیزی که آدم نیست را خاموش کن. تقریباً هیچ‌چیز دیگری لازم نیست حرفت را قطع کند.',
          ar: 'أوقف إشعارات كل ما ليس إنساناً. لا شيء آخر تقريباً يحتاج أن يقاطعك.',
          zh: '关掉所有"不是人"发来的通知。几乎没有别的东西需要打断你。' },
        { en: 'Batch them: two scheduled deliveries a day beats a hundred arrivals.',
          fa: 'دسته‌بندی‌شان کن: دو بار تحویلِ زمان‌بندی‌شده در روز بهتر از صد بار رسیدن است.',
          ar: 'اجمعها دفعات: تسليمتان مجدولتان يومياً أفضل من مئة وصول.',
          zh: '把它们打包：一天两次定时送达，胜过一百次随机到达。' },
        { en: 'Start with the noisiest single app. One switch usually takes a third of the count with it.',
          fa: 'از پرسروصداترین اپ شروع کن. یک کلید معمولاً یک‌سوم این عدد را با خودش می‌برد.',
          ar: 'ابدأ بأكثر تطبيق ضجيجاً. مفتاح واحد يأخذ عادةً ثلث العدد معه.',
          zh: '从最吵的那一个应用开始。一个开关通常就能带走三分之一的数量。' },
      ],
      keep: [
        { en: 'Re-check it after every app install — new apps arrive loud by default.',
          fa: 'بعد از هر بار نصب اپ دوباره بررسی‌اش کن — اپ‌های تازه به‌طور پیش‌فرض پرسروصدا می‌آیند.',
          ar: 'راجعها بعد كل تثبيت تطبيق — التطبيقات الجديدة تأتي صاخبة افتراضياً.',
          zh: '每装一个新应用就复查一次——新应用默认都是吵的。' },
        { en: 'A quiet phone is doing more work for your focus number than anything else on this list.',
          fa: 'یک گوشی ساکت بیشتر از هر چیز دیگری در این فهرست دارد برای عدد تمرکزت کار می‌کند.',
          ar: 'هاتف هادئ يخدم رقم تركيزك أكثر من أي شيء آخر في هذه القائمة.',
          zh: '一部安静的手机，对你的专注分数的贡献比这份清单上任何一项都大。' },
        { en: 'Keep one app allowed to interrupt you. Zero is brittle; one is a rule you will keep.',
          fa: 'یک اپ را مجاز نگه دار که حرفت را قطع کند. صفر شکننده است؛ یکی قاعده‌ای است که نگهش می‌داری.',
          ar: 'أبقِ تطبيقاً واحداً مسموحاً له بمقاطعتك. الصفر هشّ، والواحد قاعدة ستلتزم بها.',
          zh: '留一个应用有权打断你。零很脆弱；一个才是你守得住的规则。' },
      ],
    },
    focus_0_100: {
      fix: [
        { en: 'Work in one 25-minute block with the phone in a drawer. One block beats an intention.',
          fa: 'یک بلوک ۲۵ دقیقه‌ای کار کن و گوشی را در کشو بگذار. یک بلوک از یک تصمیم بهتر است.',
          ar: 'اعمل كتلة واحدة من ٢٥ دقيقة والهاتف في الدرج. كتلة واحدة أفضل من نيّة.',
          zh: '把手机放进抽屉，做一个 25 分钟的整块。一个整块胜过一个打算。' },
        { en: 'Close every tab that is not this task. Fragmentation is the number this is really measuring.',
          fa: 'هر تبی که مربوط به این کار نیست ببند. چیزی که این عدد واقعاً می‌سنجد، پراکندگی است.',
          ar: 'أغلق كل تبويب لا يخصّ هذه المهمة. التشتّت هو ما يقيسه هذا الرقم فعلاً.',
          zh: '关掉所有与这项任务无关的标签页。这个数字真正衡量的是碎片化。' },
        { en: 'Decide the first sentence before you sit down. Most lost focus is spent choosing where to start.',
          fa: 'قبل از نشستن تصمیم بگیر اولین جمله چیست. بیشترِ تمرکزِ ازدست‌رفته صرف انتخاب نقطه‌ی شروع می‌شود.',
          ar: 'قرّر الجملة الأولى قبل أن تجلس. معظم التركيز الضائع يُنفق في اختيار نقطة البداية.',
          zh: '坐下之前先定好第一句话。大部分注意力，都耗在决定从哪儿开始上了。' },
      ],
      keep: [
        { en: 'Whatever your best block of the day is, defend its hour before anything else gets it.',
          fa: 'بهترین بلوک روزت هرچه هست، از ساعتش دفاع کن قبل از اینکه چیز دیگری آن را بگیرد.',
          ar: 'أياً كانت أفضل كتلة في يومك، دافع عن ساعتها قبل أن يأخذها شيء آخر.',
          zh: '不管你一天中最好的那个时段是什么，先替它守住那一小时。' },
        { en: 'This number falls before you feel it fall. Watching it weekly is how you catch it early.',
          fa: 'این عدد قبل از اینکه حسش کنی می‌افتد. بررسی هفتگی‌اش راهِ زود گرفتنش است.',
          ar: 'هذا الرقم يهبط قبل أن تشعر بهبوطه. متابعته أسبوعياً هي طريقة اللحاق به مبكراً.',
          zh: '这个数字会在你察觉之前先掉下来。每周看一眼，才能早点接住它。' },
        { en: 'Keep the notification count where it is — that is most of what is holding this up.',
          fa: 'تعداد اعلان‌ها را همان‌جا که هست نگه دار — بیشترِ چیزی که این را بالا نگه داشته همان است.',
          ar: 'أبقِ عدد الإشعارات كما هو — فهو معظم ما يرفع هذا الرقم.',
          zh: '把通知数量维持在现在的水平——撑住这个分数的，大半是它。' },
      ],
    },
  };

  const HEADINGS = {
    keepTitle: {
      en: '① What is already working — and how to keep it',
      fa: '① چیزی که همین حالا جواب داده — و چطور نگهش داری',
      ar: '① ما ينجح بالفعل — وكيف تحافظ عليه',
      zh: '① 已经在起作用的——以及怎么守住它',
    },
    fixTitle: {
      en: '② What needs work — and where to start',
      fa: '② چیزی که کار دارد — و از کجا شروع کنی',
      ar: '② ما يحتاج عملاً — ومن أين تبدأ',
      zh: '② 需要下功夫的——以及从哪里开始',
    },
    keepEmpty: {
      en: 'Nothing is clear of its target by a comfortable margin yet, so I am not going to name a strength you do not have. That changes fast — one steady week usually does it.',
      fa: 'هنوز هیچ سیگنالی با فاصله‌ی راحت از هدفش عبور نکرده، پس نقطه‌قوتی که نداری را نام نمی‌برم. این زود عوض می‌شود — معمولاً یک هفته‌ی پیوسته کافی است.',
      ar: 'لا شيء تجاوز هدفه بفارق مريح بعد، ولن أسمّي قوة لا تملكها. هذا يتغيّر سريعاً — أسبوع ثابت واحد يكفي عادةً.',
      zh: '目前还没有哪一项以舒适的余量越过目标，所以我不会给你安一个并不存在的强项。这变得很快——通常一个稳定的星期就够了。',
    },
    fixEmpty: {
      en: 'Nothing is flagged as weak. Rather than invent something to fix, the honest answer is: hold this, and the next thing worth changing is one the model does not track.',
      fa: 'هیچ‌چیز به‌عنوان ضعف علامت نخورده. به‌جای اینکه چیزی برای درست‌کردن بتراشم، جواب صادقانه این است: همین را نگه دار، و چیز بعدی که ارزش تغییر دارد چیزی است که مدل ردیابی‌اش نمی‌کند.',
      ar: 'لا شيء مُعلَّم كنقطة ضعف. بدل اختلاق شيء لإصلاحه، الجواب الصادق: حافظ على هذا، والشيء التالي الجدير بالتغيير لا يتتبعه النموذج.',
      zh: '没有任何一项被标记为弱项。与其硬找一个来"修"，诚实的回答是：守住现在这样，而下一件值得改变的事，模型并不追踪。',
    },
    lead: {
      en: 'Two halves, because they are different work — the first is cheaper and gets dropped first.',
      fa: 'دو بخش، چون دو کارِ متفاوت‌اند — اولی ارزان‌تر است و زودتر از همه رها می‌شود.',
      ar: 'نصفان، لأنهما عملان مختلفان — الأول أرخص وهو أول ما يُهمَل.',
      zh: '分成两半，因为这是两种不同的功夫——前一半更省力，也最先被丢掉。',
    },
  };

  /* One signal's block: its own numbers, then its ideas. `seed` rotates
     which ideas come first so the same person asking twice in a week
     does not get a word-for-word repeat - the SET is fixed, only the
     order moves, so nothing is invented to keep it fresh. */
  function block(entry, half, seed) {
    const label = (window.DWCoachLabels && window.DWCoachLabels[entry.field])
      || (entry.theme_i18n ? P(entry.theme_i18n) : entry.theme)
      || entry.field;
    const bank = (IDEAS[entry.field] || {})[half] || [];
    const icon = entry.icon ? entry.icon + ' ' : '';
    const head = `${icon}${label} — ${entry.current} / ${entry.target}`;
    if (!bank.length) return head;
    const start = Math.abs(seed) % bank.length;
    const ordered = bank.slice(start).concat(bank.slice(0, start));
    return head + '\n' + ordered.map((idea) => `   • ${P(idea)}`).join('\n');
  }

  /**
   * The whole answer. `tracks` is plan_tracks from the server; anything
   * missing produces null so the caller can say it could not read the
   * plan rather than answering from nothing.
   *
   * `perHalf` is how many signals each half names - two, so each half
   * carries up to six ideas and still fits on a phone screen.
   */
  function build(tracks, options) {
    if (!tracks) return null;
    const opts = options || {};
    const perHalf = opts.perHalf || 2;
    const seed = Number.isFinite(opts.seed) ? opts.seed : new Date().getDate();

    const keep = (tracks.maintain || []).slice(0, perHalf);
    const fix = (tracks.strengthen || []).slice(0, perHalf);

    const parts = [P(HEADINGS.lead), '', P(HEADINGS.keepTitle)];
    parts.push(keep.length
      ? keep.map((e, i) => block(e, 'keep', seed + i)).join('\n')
      : P(HEADINGS.keepEmpty));
    parts.push('', P(HEADINGS.fixTitle));
    parts.push(fix.length
      ? fix.map((e, i) => block(e, 'fix', seed + i)).join('\n')
      : P(HEADINGS.fixEmpty));
    return parts.join('\n');
  }

  window.DWCoachSuggestions = { build, IDEAS, HEADINGS };
})();
