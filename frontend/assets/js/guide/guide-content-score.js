/*
  Guide content for the score ring and the two horizons.

  Two separate jobs here:

  1. The four dimension arcs. Each number around the ring is a
     composite, and a composite that does not say what went into it is
     just a number with a colour. Clicking one asks for this.

  2. The horizons. This is the important one. The app shows a score for
     TODAY and a class for SEVEN DAYS FROM NOW, from two different
     models with two different targets, and until now it showed them
     side by side as if they were one reading. The entries below are
     what the guide says when a user asks what each figure actually
     means - including the part most apps leave out, which is that the
     seven-day figure is a band typical of a class, not a personal
     forecast of their own number.
*/
(function () {
  if (!window.DWGuide || !window.DWGuide.register) return;

  window.DWGuide.register({
    dimension_sleep: {
      face: 'thinking',
      priority: 50,
      en: "This arc is your sleep, built from three things you logged: how many hours you slept, how you rated the quality, and how much of your screen time landed in the hour before bed. Hours are scored against a target rather than 'more is better' - eleven hours is not twice as good as seven. It is the arc that moves the others most, which is why it is usually the first one worth looking at.",
      fa: "این کمان، خواب توست و از سه چیزی که ثبت کرده‌ای ساخته می‌شود: چند ساعت خوابیده‌ای، کیفیتش را چند داده‌ای، و چقدر از زمان صفحه‌ات در ساعت پیش از خواب بوده. ساعت‌ها نسبت به یک هدف امتیاز می‌گیرند، نه با منطق «هرچه بیشتر بهتر» — یازده ساعت دو برابرِ هفت ساعت خوب نیست. این کمانی است که بیشتر از همه بقیه را جابه‌جا می‌کند، و برای همین معمولاً اولین چیزی است که ارزش نگاه‌کردن دارد.",
      ar: "هذا القوس هو نومك، مبنيّ من ثلاثة أشياء سجّلتها: كم ساعة نمت، وكيف قيّمت الجودة، وكم من وقت شاشتك وقع في الساعة التي تسبق النوم. تُقيَّم الساعات مقابل هدف لا بمنطق «الأكثر أفضل» — إحدى عشرة ساعة ليست ضعف جودة سبع. وهو القوس الأكثر تحريكاً لبقية الأقواس، ولذلك يستحق النظر أولاً عادةً.",
      zh: "这条弧是你的睡眠，由你记录的三样东西构成：睡了几小时、你给质量打了几分，以及你有多少屏幕时间落在睡前那一小时。小时数是对照一个目标来评分的，而不是「越多越好」——十一小时并不比七小时好一倍。它是最能带动其他弧线的一条，所以通常也最值得先看。",
    },

    dimension_focus: {
      face: 'thinking',
      priority: 50,
      en: "Focus here is five signals together: how focused and how productive you rated the day, how fragmented your usage was, how dense the notifications were, and how often you picked the phone up. The last three are the ones you can change today without changing anything about the day itself - which is why this arc often moves before the others do.",
      fa: "تمرکز اینجا پنج سیگنال با هم است: تمرکز و بهره‌وری‌ای که به روزت داده‌ای، اینکه استفاده‌ات چقدر تکه‌تکه بوده، چگالی اعلان‌ها، و اینکه چند بار گوشی را برداشته‌ای. سه تای آخر همان‌هایی‌اند که می‌توانی همین امروز عوضشان کنی بدون اینکه خودِ روز عوض شود — و برای همین این کمان اغلب زودتر از بقیه تکان می‌خورد.",
      ar: "التركيز هنا خمس إشارات معاً: كم قيّمت تركيزك وإنتاجيتك في اليوم، وكم كان استخدامك مجزّأً، وكم كانت كثافة الإشعارات، وكم مرة التقطت الهاتف. الثلاثة الأخيرة هي ما يمكنك تغييره اليوم دون تغيير أي شيء في اليوم نفسه — ولهذا يتحرك هذا القوس قبل غيره غالباً.",
      zh: "这里的专注度是五个信号的合成：你给这一天的专注和效率打了多少分、使用有多碎片化、通知有多密集，以及你拿起手机的次数。后三项是你今天就能改变、而不必改变这一天本身的——所以这条弧往往比其他的先动。",
    },

    dimension_emotional: {
      face: 'thinking',
      priority: 50,
      en: "This is the widest arc: ten things you rated about how the day felt - happiness, satisfaction, self-esteem, stress, fatigue, anxiety, low mood, loneliness, fear of missing out, and how much you compared yourself to others. Every one is your own rating of your own day. None of it is a diagnosis and none of it is a screening result, whatever the words look like.",
      fa: "این پهن‌ترین کمان است: ده چیزی که درباره‌ی حسِ روزت ارزیابی کرده‌ای — شادی، رضایت، عزت نفس، استرس، خستگی، اضطراب، افت خلق، تنهایی، ترس از جاماندن، و اینکه چقدر خودت را با دیگران مقایسه کرده‌ای. هرکدامشان ارزیابی خودت از روز خودت است. هیچ‌کدام تشخیص نیستند و هیچ‌کدام نتیجه‌ی غربالگری نیستند، هر شکلی هم که کلمه‌ها داشته باشند.",
      ar: "هذا أوسع قوس: عشرة أشياء قيّمتها عن شعور اليوم — السعادة، الرضا، تقدير الذات، التوتر، الإرهاق، القلق، انخفاض المزاج، الوحدة، الخوف من الفوات، ومقدار مقارنتك بنفسك مع الآخرين. كل واحد منها تقييمك أنت ليومك أنت. لا شيء منها تشخيص ولا نتيجة فحص، مهما بدت الكلمات.",
      zh: "这是最宽的一条弧：你对这一天感受的十项评分——快乐、满意度、自尊、压力、疲惫、焦虑、情绪低落、孤独、错失恐惧，以及你有多少把自己和别人比较。每一项都是你自己对自己一天的评分。无论这些词看起来像什么，它们都不是诊断，也不是筛查结果。",
    },

    dimension_screen_habits: {
      face: 'thinking',
      priority: 50,
      en: "Screen habits is your total time, how much of it fell in night hours, how dependent the pattern looks, and how much of it was gaming. Note that it is the shape of the usage that matters here more than the total - a long day that is mostly work at sensible hours scores better than a short one that is mostly after midnight.",
      fa: "عادت‌های صفحه یعنی زمان کل، اینکه چقدرش در ساعات شب بوده، اینکه الگو چقدر وابسته به‌نظر می‌رسد، و چقدرش بازی بوده. توجه کن که اینجا شکل استفاده مهم‌تر از مقدار کل است — یک روز طولانی که بیشترش کار در ساعات معقول است، امتیاز بهتری می‌گیرد از یک روز کوتاه که بیشترش بعد از نیمه‌شب بوده.",
      ar: "عادات الشاشة هي وقتك الإجمالي، وكم منه وقع في ساعات الليل، وكم يبدو النمط اعتمادياً، وكم منه كان لعباً. لاحظ أن شكل الاستخدام هنا أهم من الإجمالي — يوم طويل معظمه عمل في ساعات معقولة يسجّل أفضل من يوم قصير معظمه بعد منتصف الليل.",
      zh: "屏幕习惯包括你的总时长、其中有多少落在夜间、这个模式看起来有多依赖，以及有多少是游戏。要注意的是，这里使用的形状比总量更重要——一个大部分是在合理时间工作的长日子，得分会高于一个大部分在午夜之后的短日子。",
    },

    dimension_physical: {
      face: 'thinking',
      priority: 50,
      en: "The smallest arc, and deliberately so: daily movement and caffeine. It is here because both show up in sleep and focus a day later, not because this app has anything to say about fitness.",
      fa: "کوچک‌ترین کمان، و عمداً هم همین‌طور: تحرک روزانه و کافئین. اینجاست چون هر دو یک روز بعد در خواب و تمرکز خودشان را نشان می‌دهند، نه به این دلیل که این برنامه حرفی درباره‌ی تناسب اندام دارد.",
      ar: "أصغر قوس، وعن قصد: الحركة اليومية والكافيين. وهو هنا لأن كليهما يظهر في النوم والتركيز بعد يوم، لا لأن لهذا التطبيق ما يقوله عن اللياقة.",
      zh: "最小的一条弧，而且是有意如此：每日活动量和咖啡因。它在这里，是因为这两者会在一天后体现在睡眠和专注度上，而不是因为这个应用对健身有什么可说的。",
    },

    // ---- the two horizons ------------------------------------------
    score_today: {
      face: 'good',
      priority: 62,
      en: "The big number in the middle is today - the day you just logged, scored by the regression model. The range under it is not decoration: the model has a measured average error, so the honest statement is that your score is somewhere in that range, and the bold number is the middle of it. Eighty and above is the healthy band, sixty to seventy-nine is the middle band, below sixty is the one worth attention.",
      fa: "عدد بزرگ وسط، مربوط به امروز است — همان روزی که تازه ثبت کردی، امتیازدهی‌شده با مدل رگرسیون. بازه‌ی زیرش تزئینی نیست: مدل خطای میانگین اندازه‌گیری‌شده‌ای دارد، پس جمله‌ی صادقانه این است که امتیازت جایی در آن بازه است و عدد پررنگ وسطِ آن. هشتاد و بالاتر باند سالم است، شصت تا هفتادونه باند میانی، و زیر شصت آن باندی که ارزش توجه دارد.",
      ar: "الرقم الكبير في الوسط هو اليوم — اليوم الذي سجّلته للتو، مقيَّماً بنموذج الانحدار. المدى تحته ليس زينة: للنموذج خطأ متوسط مقيس، فالجملة الصادقة هي أن درجتك في مكان ما ضمن ذلك المدى، والرقم الغامق هو منتصفه. ثمانون فأكثر هو النطاق الصحي، وستون إلى تسعة وسبعين النطاق الأوسط، وما دون الستين هو الذي يستحق الانتباه.",
      zh: "中间那个大数字是今天——你刚刚记录的这一天，由回归模型评分。它下面的区间不是装饰：模型有一个实测的平均误差，所以诚实的说法是你的分数落在那个区间里的某处，而加粗的数字是它的中点。八十及以上是健康区间，六十到七十九是中间区间，六十以下则是值得注意的那一个。",
    },

    score_seven_day: {
      face: 'thinking',
      priority: 62,
      en: "The seven-day figure comes from a different model with a different target: it predicts which band you will be in a week from now, and it is right about that band roughly nine times out of ten on data it never trained on. The number beside it is the range that band typically covers - not a forecast of your own number. So if you scored eighty-four today and the seven-day band shows around seventy-two, that is not me predicting you will drop. It is me saying you are heading into the healthy band, and that band usually sits around there.",
      fa: "عدد هفت‌روزه از مدل دیگری با هدف دیگری می‌آید: پیش‌بینی می‌کند یک هفته‌ی دیگر در کدام باند خواهی بود، و روی داده‌ای که هرگز روی آن آموزش ندیده، تقریباً نُه بار از ده بار درباره‌ی همان باند درست می‌گوید. عددی که کنارش است، بازه‌ای است که آن باند معمولاً می‌پوشاند — نه پیش‌بینیِ عددِ خودت. پس اگر امروز هشتادوچهار گرفته‌ای و باند هفت‌روزه حدود هفتادودو را نشان می‌دهد، این یعنی من نمی‌گویم افت می‌کنی. یعنی داری به سمت باند سالم می‌روی، و آن باند معمولاً همان حوالی است.",
      ar: "رقم الأيام السبعة يأتي من نموذج آخر بهدف آخر: يتنبأ بالنطاق الذي ستكون فيه بعد أسبوع، وهو محق بشأن ذلك النطاق نحو تسع مرات من عشر على بيانات لم يتدرب عليها قط. والرقم بجانبه هو المدى الذي يغطيه ذلك النطاق عادةً — لا تنبؤاً برقمك أنت. فإن سجّلت أربعاً وثمانين اليوم وأظهر نطاق الأيام السبعة نحو اثنين وسبعين، فأنا لا أتنبأ بأنك ستنخفض. بل أقول إنك متجه إلى النطاق الصحي، وذلك النطاق يقع عادةً حول هناك.",
      zh: "七天的数字来自另一个模型、另一个目标：它预测你一周后会处在哪个区间，而且在它从未训练过的数据上，大约十次里有九次说对了那个区间。旁边的数字是那个区间通常覆盖的范围——不是对你自己那个数字的预测。所以如果你今天是八十四，而七天区间显示大约七十二，那并不是我在预测你会下滑。我是在说你正走向健康区间，而那个区间通常就在那附近。",
    },
  });
})();
