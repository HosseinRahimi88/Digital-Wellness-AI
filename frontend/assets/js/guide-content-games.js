/*
  Guide content for the five Section E games, registered alongside the
  feature rather than added later (B-5).

  Each entry answers the question a user actually has about a small
  interaction, which is never "how do I play" - it is "why is this here,
  and is it telling me something real".
*/
(function () {
  if (!window.DWGuide || !window.DWGuide.register) return;

  window.DWGuide.register({
    game_guess_score: {
      face: 'good',
      priority: 45,
      en: "Committing to a number before you see it is the only way to find out whether you can already read your own day. There is no score for guessing well and nothing is saved - the point is the gap. A large one usually means a single signal, most often sleep or how scattered the day was, carried more weight than it felt like at the time. It only appears once a day, because guessing twice against a number you have already seen is not guessing.",
      fa: "متعهد شدن به یک عدد پیش از دیدنش، تنها راه فهمیدن این است که آیا از قبل می‌توانی روز خودت را بخوانی یا نه. برای حدس خوب امتیازی نیست و چیزی هم ذخیره نمی‌شود — نکته، همان فاصله است. فاصله‌ی زیاد معمولاً یعنی یک سیگنال، اغلب خواب یا میزان پراکندگی روز، بیشتر از آنچه در لحظه حس می‌شد وزن داشته. روزی یک بار ظاهر می‌شود، چون حدس‌زدن دوباره روی عددی که قبلاً دیده‌ای، حدس نیست.",
      ar: "الالتزام برقم قبل رؤيته هو الطريق الوحيد لتعرف إن كنت تستطيع قراءة يومك أصلاً. لا نقاط على التخمين الجيد ولا يُحفظ شيء — المقصود هو الفجوة. والفجوة الكبيرة تعني عادةً أن إشارة واحدة، غالباً النوم أو مدى تشتت اليوم، كان وزنها أكبر مما بدا وقتها. تظهر مرة واحدة يومياً، لأن التخمين مرتين على رقم رأيته سلفاً ليس تخميناً.",
      zh: "在看到之前先给出一个数字，是唯一能知道你是否已经读得懂自己这一天的办法。猜得准没有加分，也不会保存任何东西——重点在于那个差距。差距大通常意味着某一个信号，多半是睡眠或这一天有多零散，它的分量比当时感觉到的更重。它每天只出现一次，因为对一个你已经看过的数字再猜一遍，那不叫猜。",
    },

    game_which_factor: {
      face: 'thinking',
      priority: 45,
      en: "Both options are real factors from your own explanation above, with the model's own SHAP numbers behind them - I am not making up a quiz. I only ask when the two are far enough apart that the answer is not a coin flip. Getting it wrong is the useful outcome: it means the thing you assumed was driving your day was not the thing the model found, and now you know which one it was.",
      fa: "هر دو گزینه عامل‌های واقعی از توضیح خودت در بالا هستند، با اعداد SHAP خودِ مدل پشتشان — من آزمون از خودم نمی‌سازم. فقط وقتی می‌پرسم که این دو به‌اندازه‌ی کافی از هم فاصله داشته باشند تا جواب شیر یا خط نباشد. اشتباه‌گفتن نتیجه‌ی مفید ماجراست: یعنی چیزی که فکر می‌کردی روزت را می‌گرداند، همانی نبوده که مدل پیدا کرده، و حالا می‌دانی کدام بوده.",
      ar: "كلا الخيارين عاملان حقيقيان من تفسيرك أنت أعلاه، وخلفهما أرقام SHAP الخاصة بالنموذج — أنا لا أختلق اختباراً. ولا أسأل إلا حين يكون الفارق بينهما كافياً بحيث لا تكون الإجابة رمية عملة. والخطأ هنا هو النتيجة المفيدة: يعني أن ما ظننته يقود يومك لم يكن ما وجده النموذج، وقد صرت تعرف الآن أيهما كان.",
      zh: "两个选项都是上面你自己那段解释里的真实因素，背后是模型自己的 SHAP 数字——我不会凭空编一道题。而且只有当两者差距足够大、答案不是掷硬币时我才会问。答错才是有用的结果：它意味着你以为在主导这一天的那件事，并不是模型找到的那件，而现在你知道是哪一件了。",
    },

    game_baseline_or_exception: {
      face: 'thinking',
      priority: 48,
      en: "This is the one interaction here that changes the product rather than just talking about it. I cannot tell a genuinely unusual day - a flight, an illness, a deadline - from a bad habit, because they look identical in the numbers. Only you can. Marking one keeps the day in your history but takes it out of every average, every streak and every pattern from then on, which makes all of them more honest. Say a day was normal and it counts; that is equally useful.",
      fa: "این تنها تعاملی است که به‌جای حرف‌زدن درباره‌ی محصول، خودِ محصول را عوض می‌کند. من نمی‌توانم یک روز واقعاً غیرعادی — یک پرواز، یک بیماری، یک ددلاین — را از یک عادت بد تشخیص بدهم، چون در اعداد کاملاً شبیه هم‌اند. فقط تو می‌توانی. علامت‌زدن یک روز، آن را در سابقه‌ات نگه می‌دارد اما از آن پس از هر میانگین و زنجیره و الگویی بیرونش می‌برد، و همین همه را صادق‌تر می‌کند. اگر بگویی روز معمولی بوده، حساب می‌شود؛ آن هم به همان اندازه مفید است.",
      ar: "هذا هو التفاعل الوحيد هنا الذي يغيّر المنتج بدل أن يتحدث عنه فقط. لا أستطيع تمييز يوم غير عادي فعلاً — سفر، مرض، موعد نهائي — عن عادة سيئة، لأنهما متطابقان في الأرقام. أنت وحدك تستطيع. ووضع العلامة يُبقي اليوم في سجلك لكنه يخرجه من كل متوسط وسلسلة ونمط من بعدها، وهذا يجعلها جميعاً أصدق. وإن قلت إن اليوم كان عادياً فهو محسوب؛ وذلك مفيد بالقدر نفسه.",
      zh: "这是这里唯一一个真正改变产品、而不只是在谈论产品的互动。我分不出一个真正不寻常的日子——一次航班、一场生病、一个截止日期——和一个坏习惯，因为它们在数字上完全一样。只有你能。标记之后，那一天仍留在你的历史里，但从此会被排除在每一个平均值、连续记录和模式之外，这让它们全都更诚实。说它是普通的一天，它就算数；这同样有用。",
    },

    game_fill_the_blank: {
      face: 'thinking',
      priority: 45,
      en: "The relationship I am asking about is one that already passed a significance test on your own days - the same test the insight card uses, which corrects for the fact that scanning many pairs of things will always turn up a few that look related by luck alone. So this is not a coincidence dressed up as a question. It is still only a pattern: two things moving together is not one causing the other, and I will not pretend otherwise for the sake of a better answer.",
      fa: "رابطه‌ای که درباره‌اش می‌پرسم، از قبل یک آزمون معناداری را روی روزهای خودت گذرانده — همان آزمونی که کارت بینش استفاده می‌کند و این واقعیت را جبران می‌کند که وقتی جفت‌های زیادی را می‌گردی، همیشه چند تایی صرفاً از شانس مرتبط به‌نظر می‌رسند. پس این یک هم‌زمانی تصادفی نیست که لباس سؤال پوشیده باشد. با این حال هنوز فقط یک الگوست: حرکت هم‌زمان دو چیز یعنی یکی باعث دیگری نیست، و من به‌خاطر جواب جذاب‌تر وانمود به خلافش نمی‌کنم.",
      ar: "العلاقة التي أسأل عنها اجتازت أصلاً اختبار دلالة على أيامك أنت — الاختبار نفسه الذي تستخدمه بطاقة الرؤية، والذي يصحّح لحقيقة أن مسح أزواج كثيرة سيُظهر دائماً بضعة أزواج تبدو مترابطة بالحظ وحده. فهذه ليست مصادفة متنكّرة في هيئة سؤال. ومع ذلك تبقى نمطاً فقط: تحرّك شيئين معاً لا يعني أن أحدهما يسبب الآخر، ولن أتظاهر بغير ذلك من أجل إجابة أجمل.",
      zh: "我问的这个关联，已经在你自己的日子上通过了显著性检验——和洞察卡片用的是同一个检验，它修正了这样一个事实：只要你去扫很多组配对，总会有几组仅凭运气就看起来相关。所以这不是一个装扮成问题的巧合。但它仍然只是一个模式：两件事一起变化并不意味着其中一个导致了另一个，我不会为了一个更漂亮的答案而假装不是这样。",
    },

    game_keep_the_streak: {
      face: 'good',
      priority: 45,
      en: "Most apps zero a streak the moment you miss a day. That turns weeks of real progress into nothing over one ordinary bad evening, and it is the exact moment most people stop opening the app - so this one does not do it. A miss shortens the chain by a few days instead, the first misses each month are absorbed entirely, and a day you marked as an exception costs nothing at all. The record for your longest streak stays strict, because a record that bends is not a record.",
      fa: "بیشتر برنامه‌ها همان لحظه که یک روز را از دست بدهی زنجیره را صفر می‌کنند. این کار هفته‌ها پیشرفت واقعی را به‌خاطر یک عصرِ بدِ معمولی به هیچ تبدیل می‌کند، و دقیقاً همان لحظه‌ای است که بیشتر آدم‌ها دیگر برنامه را باز نمی‌کنند — پس اینجا این‌طور نیست. به‌جایش یک روز خالی زنجیره را چند روز کوتاه می‌کند، اولین روزهای خالی هر ماه کاملاً جذب می‌شوند، و روزی که استثنا علامت زده‌ای اصلاً هزینه‌ای ندارد. رکورد بلندترین زنجیره‌ات سخت‌گیر می‌ماند، چون رکوردی که خم شود دیگر رکورد نیست.",
      ar: "معظم التطبيقات تصفّر السلسلة لحظة تفويتك يوماً. هذا يحوّل أسابيع من التقدّم الحقيقي إلى لا شيء بسبب أمسية سيئة عادية، وهي بالضبط اللحظة التي يتوقف فيها معظم الناس عن فتح التطبيق — لذلك لا نفعل ذلك هنا. اليوم الفائت يقصّر السلسلة ببضعة أيام بدلاً من ذلك، وأول الأيام الفائتة كل شهر تُمتص بالكامل، واليوم الذي وضعت عليه علامة استثناء لا يكلّف شيئاً على الإطلاق. أما رقم أطول سلسلة لك فيبقى صارماً، لأن الرقم القياسي الذي ينحني لم يعد رقماً قياسياً.",
      zh: "大多数应用在你错过一天的那一刻就把连续记录清零。那会因为一个普通的糟糕夜晚，把数周的真实进步变成零，而那正是大多数人不再打开应用的时刻——所以这里不这么做。错过一天只会把链条缩短几天，每个月最开始的几次错过会被完全吸收，而你标记为例外的那一天完全没有代价。但你最长连续记录这个成绩仍然是严格的，因为一个会通融的纪录就不再是纪录了。",
    },

    /* The six added when Section E's games moved to their own screen
       between processing and the result (games.js §6-11). Same rule as
       above: each entry answers "why is this here, is it real" rather
       than "how do I play". */
    game_dimension_duel: {
      face: 'thinking',
      priority: 45,
      en: "This uses the dimension breakdown, not the SHAP panel - a second, plain-arithmetic view over the same inputs, kept deliberately separate from the model so you can check one against the other. I only ask when the gap between the two areas is wide enough to be a real answer, not a coin flip.",
      fa: "این بازی از تفکیک ابعاد استفاده می‌کند، نه پنل SHAP — یک نمای دوم و حساب‌ساده روی همان ورودی‌ها، که عمداً جدا از مدل نگه داشته شده تا بتوانی یکی را با دیگری بسنجی. فقط وقتی می‌پرسم که فاصله‌ی این دو حوزه به‌اندازه‌ی کافی زیاد باشد تا جواب واقعی باشد، نه شیر یا خط.",
      ar: "يستخدم هذا تفصيل الأبعاد لا لوحة SHAP — نظرة ثانية بحساب بسيط على المدخلات نفسها، أُبقيت متعمداً منفصلة عن النموذج كي تتحقق من إحداهما بالأخرى. لا أسأل إلا حين تكون الفجوة بين المجالين كافية لتكون إجابة حقيقية، لا رمية عملة.",
      zh: "这个用的是维度细分，不是 SHAP 面板——对同样输入的第二种视角，用简单算术得出，刻意与模型分开，好让你互相核对。只有当这两个方面的差距足够大、构成一个真实答案而不是掷硬币时，我才会问。",
    },

    game_confidence_guess: {
      face: 'thinking',
      priority: 45,
      en: "Confidence is a real, separate number from the score - it comes from how tightly your inputs cluster inside one category, not from whether the result is good news or bad. Guessing before you see it is a quick check on whether you conflate 'sure' with 'good', which most people do at first.",
      fa: "اطمینان عددی واقعی و جداست از خودِ امتیاز — از این می‌آید که ورودی‌هایت چقدر داخل یک دسته متمرکزند، نه از اینکه نتیجه خبر خوبی است یا بد. حدس‌زدن قبل از دیدنش یک بررسی سریع است که آیا «مطمئن» را با «خوب» اشتباه می‌گیری یا نه، که بیشتر آدم‌ها اولش این کار را می‌کنند.",
      ar: "الثقة رقم حقيقي منفصل عن الدرجة — يأتي من مدى تجمّع مدخلاتك داخل فئة واحدة، لا من كون النتيجة خبراً جيداً أو سيئاً. التخمين قبل رؤيتها فحص سريع لما إذا كنت تخلط بين واثق وجيد، وهو ما يفعله معظم الناس في البداية.",
      zh: "置信度是一个真实、独立于分数本身的数字——它来自你的输入在一个类别内聚集的紧密程度，而不是结果是好消息还是坏消息。在看到它之前先猜一猜，能快速检验你是否把确定和好混为一谈，大多数人一开始都会这样。",
    },

    game_future_class_guess: {
      face: 'thinking',
      priority: 45,
      en: "This is the mistake this app used to make, turned into a question on purpose: today's score and the seven-day class are two different models trained on two different questions, not the same number read twice. Guessing before the reveal is the fastest way to notice when your instinct still treats them as one.",
      fa: "این همان اشتباهی است که این برنامه قبلاً می‌کرد، عمداً به یک سؤال تبدیل شده: امتیاز امروز و دسته‌ی هفت‌روزه دو مدل جدا هستند که روی دو سؤال جدا آموزش دیده‌اند، نه همان عدد که دوبار خوانده شود. حدس‌زدن قبل از دیدن جواب سریع‌ترین راه برای فهمیدن این است که آیا غریزه‌ات هنوز این دو را یکی می‌داند.",
      ar: "هذا هو الخطأ الذي كان هذا التطبيق يرتكبه سابقاً، وقد تحوّل عمداً إلى سؤال: درجة اليوم وفئة السبعة أيام نموذجان مختلفان مدرَّبان على سؤالين مختلفين، لا نفس الرقم يُقرأ مرتين. التخمين قبل الكشف أسرع طريقة لتلاحظ إن كان حدسك ما زال يعاملهما كشيء واحد.",
      zh: "这正是这个应用以前犯过的错误，现在被故意变成了一个问题：今天的分数和七天后的类别是两个训练目标不同的独立模型，不是同一个数字被读了两遍。在揭晓之前先猜一猜，是发现你的直觉是否仍把两者当成一回事的最快方法。",
    },

    game_weekday_or_weekend: {
      face: 'good',
      priority: 45,
      en: "The same weekday_vs_weekend figure the Analytics page computes from your real logged days - never recalculated here, just asked about first. A wide gap usually says more about your week's own structure than about any habit you have deliberately built.",
      fa: "همان عدد weekday_vs_weekend که صفحه‌ی تحلیل‌ها از روزهای واقعی ثبت‌شده‌ات حساب می‌کند — اینجا دوباره محاسبه نمی‌شود، فقط اول درباره‌اش پرسیده می‌شود. فاصله‌ی زیاد معمولاً بیشتر درباره‌ی ساختار خودِ هفته‌ات حرف می‌زند تا هر عادتی که عمداً ساخته باشی.",
      ar: "نفس رقم weekday_vs_weekend الذي تحسبه صفحة التحليلات من أيامك المسجَّلة فعلاً — لا يُعاد حسابه هنا، فقط يُسأل عنه أولاً. الفجوة الكبيرة تقول عادة عن بنية أسبوعك نفسه أكثر مما تقول عن أي عادة بنيتها بقصد.",
      zh: "就是分析页面从你真实记录的日子里算出的同一个 weekday_vs_weekend 数字——这里不会重新计算，只是先问一问。差距大，通常更多说明的是你一周本身的结构，而不是你刻意养成的某个习惯。",
    },

    game_badge_race: {
      face: 'good',
      priority: 45,
      en: "Only achievement badges your own history can actually answer, never a private awareness indicator - those are not a competition (see the Badges page for why). The progress numbers are the exact same ones that page would show; this just asks you to guess first.",
      fa: "فقط نشان‌های دستاورد که تاریخچه‌ی خودت واقعاً می‌تواند جوابشان را بدهد، هرگز یک شاخص آگاهیِ خصوصی — آن‌ها یک مسابقه نیستند (برای دلیلش صفحه‌ی نشان‌ها را ببین). اعداد پیشرفت دقیقاً همان‌هایی هستند که آن صفحه نشان می‌دهد؛ این فقط از تو می‌خواهد اول حدس بزنی.",
      ar: "فقط أوسمة الإنجاز التي يستطيع سجلك فعلاً الإجابة عنها، وليس أبداً مؤشر وعي خاص — تلك ليست مسابقة (انظر صفحة الأوسمة لمعرفة السبب). أرقام التقدّم هي نفسها بالضبط التي تعرضها تلك الصفحة؛ هذا فقط يطلب منك أن تخمّن أولاً.",
      zh: "只涉及你自己历史真正能回答的成就徽章，绝不涉及私密的自我觉察指标——那些不是竞赛（原因见徽章页面）。这里的进度数字与那个页面显示的完全一样；只是要求你先猜一猜。",
    },

    game_score_vs_average: {
      face: 'thinking',
      priority: 45,
      en: "Your own historical average, not 50 and not anyone else's number - the only honest baseline a single day can be measured against. It is the same idea baseline_or_exception is built on, asked from the other direction: instead of labelling a day, you are testing whether you can already sense where it sits.",
      fa: "میانگین تاریخی خودت، نه پنجاه و نه عدد کس دیگری — تنها خط پایه‌ی صادقانه‌ای که می‌شود یک روز تنها را با آن سنجید. همان ایده‌ای است که «روز معمولی یا نه» رویش ساخته شده، فقط از جهت دیگر پرسیده می‌شود: به‌جای علامت‌زدن یک روز، داری آزمایش می‌کنی که آیا از قبل حس می‌کنی کجای طیف قرار دارد.",
      ar: "متوسطك التاريخي أنت، لا خمسون ولا رقم أي شخص آخر — خط الأساس الصادق الوحيد الذي يمكن قياس يوم واحد به. إنها الفكرة نفسها التي بُنيت عليها لعبة يوم عادي أم لا، تُسأل من الاتجاه الآخر: بدل وضع علامة على يوم، تختبر ما إذا كنت تحس مسبقاً أين يقع.",
      zh: "你自己的历史平均值，不是五十，也不是别人的数字——衡量单独一天唯一诚实的基准。这与普通的一天还是不是背后的想法相同，只是从另一个方向来问：这次不是给一天贴标签，而是测试你是否已经能感觉到它大概落在哪里。",
    },

    games_page: {
      face: 'good',
      priority: 40,
      en: "Your result is already computed and waiting - nothing here delays it, this screen just asks one quick thing about it first. Turn it off any time from Settings > Games after a check-in, or just tap through with the button below without playing; nothing on this screen can block you from your result.",
      fa: "نتیجه‌ات از قبل محاسبه شده و منتظر است — هیچ‌چیز اینجا آن را عقب نمی‌اندازد، این صفحه فقط اول یک چیز سریع درباره‌اش می‌پرسد. هر وقت خواستی از تنظیمات > «بازی‌ها بعد از هر بررسی» خاموشش کن، یا بدون بازی‌کردن فقط دکمه‌ی پایین را بزن؛ هیچ‌چیز در این صفحه نمی‌تواند جلوی رسیدنت به نتیجه را بگیرد.",
      ar: "نتيجتك محسوبة بالفعل وبانتظارك — لا شيء هنا يؤخرها، هذه الشاشة فقط تسأل شيئاً سريعاً واحداً عنها أولاً. أوقفها في أي وقت من الإعدادات > الألعاب بعد كل تسجيل، أو فقط اضغط الزر أدناه دون اللعب؛ لا شيء في هذه الشاشة يمكنه منعك من الوصول إلى نتيجتك.",
      zh: "你的结果已经算好，正等着你——这里不会延迟它，这个屏幕只是先快速问一件与它有关的小事。随时可以从设置 > 记录后的小游戏里关掉它，或者不玩、直接点下面的按钮跳过；这个屏幕上没有任何东西能挡住你看到结果。",
    },

    games_after: {
      face: 'good',
      priority: 40,
      en: "The games above asked you to guess before you saw your number - these ones are the opposite, built to be answered now that you have it: which factor really moved it, whether today was ordinary or worth marking as an exception, what your own history predicts. Nothing here recomputes your result; every one just reads a different angle of the same explanation.",
      fa: "بازی‌های بالا از تو خواستند پیش از دیدن عددت حدس بزنی — این‌ها برعکس‌اند، طوری ساخته شده‌اند که حالا که عددت را داری جواب داده شوند: کدام عامل واقعاً آن را جابه‌جا کرد، امروز معمولی بود یا ارزش علامت‌زدن به‌عنوان استثنا را داشت، تاریخچه‌ی خودت چه پیش‌بینی می‌کند. هیچ‌کدام نتیجه‌ات را دوباره حساب نمی‌کنند؛ هرکدام فقط زاویه‌ی دیگری از همان توضیح را می‌خوانند.",
      ar: "الألعاب أعلاه طلبت منك التخمين قبل أن ترى رقمك — وهذه عكسها، مبنية لتُجاب الآن وقد صار الرقم لديك: أي عامل حرّكه فعلاً، وهل كان اليوم عادياً أم يستحق وضع علامة استثناء، وبماذا يتنبأ سجلّك أنت. لا شيء هنا يعيد حساب نتيجتك؛ كل واحدة منها تقرأ فقط زاوية مختلفة من التفسير نفسه.",
      zh: "上面的游戏让你在看到分数之前先猜——这些正相反，是为了现在你已经拿到分数之后来回答的：到底是哪个因素真正推动了它，今天算普通的一天还是值得标记为例外，你自己的历史又预示着什么。这里没有任何一个会重新计算你的结果；每一个都只是从同一份解释里读出不同的角度。",
    },
  });
})();
