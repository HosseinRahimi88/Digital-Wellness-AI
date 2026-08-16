/*
  Per-field coaching: "how is my X, really?" for every signal the user
  actually logs.

  The problem this solves
  -----------------------
  The menu had 55 hand-written questions. The model reads 53 fields.
  So for most of what it measures there was no way to ask about it at
  all - the result page would rank a field as your top factor and the
  coach had nothing to say if you asked about it by name.

  Every answer here is assembled from the user's OWN data, in this
  order, and any part with no real data behind it is dropped rather
  than padded:

    1. what they logged, with its unit
    2. where that sits against the healthy target, and by how much
    3. what the model actually said about it TODAY - pulled from the
       real SHAP output, including its rank and whether it helped or
       hurt. Not "this is usually important": what it did for them.
    4. why the field is in the model at all - the teaching part
    5. the concrete next step, taken from the real recommendation for
       that field when one exists

  Point 3 is the one that makes this worth having. "Your sleep is 6.2h,
  below the 7.5h target" is a spreadsheet. "Your sleep is 6.2h, and it
  was the single largest thing pulling your score down today" is an
  answer.
*/
(function () {
  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : (t && t.en) || '');
  const label = (f) => ((window.DWCoachLabels || {})[f] || String(f || '').replace(/_/g, ' '));

  // dir: which way is better. target: the healthy reference used across
  // the app (config/healthy_targets.py and the schema's own bounds), so
  // this never invents a second opinion about what "good" means.
  const FIELDS = {
    sleep_hours: {
      dir: "higher", target: 7.5, unit: "h", topic: "sleep",
      why: {
        en: "Sleep is the single strongest signal in this model, and it is unusual among the inputs because it is both a cause and an effect: short sleep worsens next-day focus and mood, and a hard day pushes bedtime later. That loop is why a small, repeated gain here moves more than a large one-off change anywhere else.",
        fa: "خواب قوی‌ترین سیگنال این مدل است، و میان ورودی‌ها از این نظر خاص است که هم علت است و هم معلول: خواب کم، تمرکز و خلق فردا را بدتر می‌کند، و یک روز سخت ساعت خواب را عقب می‌اندازد. همین حلقه است که باعث می‌شود یک بردِ کوچکِ تکرارشونده اینجا بیشتر از یک تغییر بزرگِ یک‌باره در هر جای دیگر اثر بگذارد.",
        ar: "النوم أقوى إشارة في هذا النموذج، وهو استثنائي بين المدخلات لأنه سبب ونتيجة معاً: قلة النوم تُضعف تركيز الغد ومزاجه، واليوم الشاق يؤخّر موعد النوم. هذه الحلقة هي سبب أن مكسباً صغيراً متكرراً هنا يتفوّق على تغيير كبير لمرة واحدة في أي مكان آخر.",
        zh: "睡眠是这个模型中最强的单一信号，而且它在所有输入中很特别：它既是因也是果——睡得少会削弱第二天的专注和情绪，而辛苦的一天又会推迟就寝时间。正是这个循环，使得在这里取得一点点反复的进步，比在别处做一次大改变更有效。",
      },
    },
    sleep_quality_1_10: {
      dir: "higher", target: 8.0, unit: "", topic: "sleep",
      why: {
        en: "Quality and duration are separate inputs because they fail separately. Eight fragmented hours and six solid ones are not the same day, and the model sees the difference. Quality is also the more responsive of the two: it moves on what happened in the hour before bed, not on how long you were horizontal.",
        fa: "کیفیت و مدت خواب دو ورودی جدا هستند چون جدا از هم خراب می‌شوند. هشت ساعتِ تکه‌تکه و شش ساعتِ یکپارچه یک روز نیستند، و مدل تفاوتشان را می‌بیند. کیفیت از این دو واکنش‌پذیرتر هم هست: به آنچه در ساعت پیش از خواب گذشته حرکت می‌کند، نه به اینکه چقدر دراز کشیده بوده‌ای.",
        ar: "الجودة والمدة مدخلان منفصلان لأنهما يفشلان منفصلَين. ثماني ساعات متقطعة وستّ ساعات متصلة ليستا اليوم نفسه، والنموذج يرى الفرق. الجودة أيضاً الأسرع استجابة بينهما: تتحرك بما جرى في الساعة التي تسبق النوم، لا بطول استلقائك.",
        zh: "质量和时长是两个独立的输入，因为它们会各自出问题。八小时断断续续和六小时完整并不是同一天，模型能看出区别。质量也是两者中更敏感的一个：它取决于睡前那一小时发生了什么，而不是你躺了多久。",
      },
    },
    pre_sleep_screen_min: {
      dir: "lower", target: 15, unit: "min", topic: "sleep",
      why: {
        en: "This is the highest-leverage minute-for-minute field in the whole schema. The same thirty minutes of screen costs far more at 23:30 than at 15:00, because light and engagement both delay sleep onset. Moving these minutes earlier, rather than deleting them, is usually the cheapest real change available.",
        fa: "این پرلوریج‌ترین فیلد دقیقه‌به‌دقیقه در کل اسکیماست. همان سی دقیقه صفحه، ساعت ۲۳:۳۰ خیلی گران‌تر از ۱۵:۰۰ تمام می‌شود، چون هم نور و هم درگیری ذهنی شروع خواب را عقب می‌اندازند. جابه‌جا کردن این دقیقه‌ها به زودتر — نه حذفشان — معمولاً ارزان‌ترین تغییر واقعیِ در دسترس است.",
        ar: "هذا أعلى الحقول مردوداً لكل دقيقة في المخطط كله. الثلاثون دقيقة نفسها أمام الشاشة تكلّف أكثر بكثير في 23:30 منها في 15:00، لأن الضوء والانخراط كليهما يؤخّران بدء النوم. نقل هذه الدقائق إلى وقت أبكر، بدل حذفها، هو عادةً أرخص تغيير حقيقي متاح.",
        zh: "这是整个字段表中每分钟杠杆最高的一项。同样三十分钟的屏幕时间，在 23:30 的代价远高于 15:00，因为光线和投入程度都会推迟入睡。把这些分钟挪早，而不是删掉，通常是最划算的真实改变。",
      },
    },
    night_ratio: {
      dir: "lower", target: 0.1, unit: "%", topic: "sleep",
      why: {
        en: "Night share asks a different question from total screen time: not how much, but how late. It correlates with sleep debt more tightly than the total does, which is why a modest total can still produce a poor score if most of it lands after dark.",
        fa: "سهم شبانه سؤال دیگری از زمان کل صفحه می‌پرسد: نه چقدر، بلکه چقدر دیر. این با بدهیِ خواب محکم‌تر از عدد کل هم‌بسته است، و به همین دلیل یک زمان کلِ معتدل هم اگر بیشترش بعد از تاریکی بیفتد می‌تواند امتیاز بدی بسازد.",
        ar: "الحصة الليلية تطرح سؤالاً مختلفاً عن إجمالي وقت الشاشة: لا كم، بل كم متأخراً. وترتبط بدَين النوم أوثق من الإجمالي، ولهذا قد ينتج إجمالي معتدل درجة سيئة إن وقع معظمه بعد حلول الظلام.",
        zh: "夜间占比问的问题和屏幕总时长不同：不是多少，而是多晚。它与睡眠债的相关性比总时长更紧密，所以即使总量适中，如果大部分落在天黑之后，分数依然可能不好。",
      },
    },
    night_screen_min: {
      dir: "lower", target: 20, unit: "min", topic: "sleep",
      why: {
        en: "The absolute count behind the night ratio. Two people can share a ratio and differ by an hour of actual late-night use, and the model is given both so it can tell them apart.",
        fa: "شمارشِ مطلقِ پشتِ نسبت شبانه. دو نفر می‌توانند نسبت یکسانی داشته باشند و یک ساعت در استفاده‌ی واقعیِ آخرِ شب تفاوت کنند، و مدل هر دو را می‌گیرد تا بتواند تشخیصشان دهد.",
        ar: "العدد المطلق وراء النسبة الليلية. قد يتشارك شخصان النسبة نفسها ويختلفان بساعة من الاستخدام الليلي الفعلي، والنموذج يتلقى كليهما ليميّز بينهما.",
        zh: "夜间占比背后的绝对数值。两个人可能占比相同，但实际深夜使用相差一小时，模型同时拿到两者才能区分他们。",
      },
    },
    caffeine_cups_per_day: {
      dir: "lower", target: 2, unit: "", topic: "sleep",
      why: {
        en: "Caffeine's half-life is long enough that an afternoon cup is still measurably active at bedtime. It rarely stops you falling asleep; it reliably shallows the sleep you do get, which is why it shows up in quality rather than duration.",
        fa: "نیمه‌عمر کافئین آن‌قدر بلند هست که یک فنجان بعدازظهر موقع خواب هنوز به‌طور قابل‌اندازه‌گیری فعال باشد. به‌ندرت جلوی به‌خواب‌رفتنت را می‌گیرد؛ اما به‌طور مطمئن خوابی را که می‌گیری کم‌عمق‌تر می‌کند، و به همین دلیل در کیفیت ظاهر می‌شود نه در مدت.",
        ar: "عمر النصف للكافيين طويل بما يكفي ليبقى كوب بعد الظهر فاعلاً بشكل قابل للقياس وقت النوم. نادراً ما يمنعك من النوم؛ لكنه يجعل نومك أسطح بشكل موثوق، ولهذا يظهر في الجودة لا في المدة.",
        zh: "咖啡因的半衰期足够长，下午那杯到睡觉时仍有可测量的活性。它很少让你睡不着，但会稳定地让你的睡眠变浅——所以它体现在质量上，而不是时长上。",
      },
    },
    total_screen_min: {
      dir: "lower", target: 300, unit: "min", topic: "screen",
      why: {
        en: "On its own, total screen time is a weak predictor - which surprises people. What carries the signal is when it happened, what it replaced, and how fragmented it was. The total is in the model as context for those, not as the verdict.",
        fa: "زمان کل صفحه به‌تنهایی پیش‌بینی‌کننده‌ی ضعیفی است — و این آدم‌ها را غافلگیر می‌کند. آنچه سیگنال را حمل می‌کند این است که کِی اتفاق افتاده، جای چه چیزی را گرفته، و چقدر تکه‌تکه بوده. عدد کل به‌عنوان زمینه‌ی این‌هاست در مدل، نه به‌عنوان حکم.",
        ar: "بمفرده، إجمالي وقت الشاشة مؤشر ضعيف — وهذا يفاجئ الناس. ما يحمل الإشارة هو متى حدث، وما الذي حلّ محله، وكم كان مجزّأً. الإجمالي موجود في النموذج كسياق لتلك، لا كحُكم.",
        zh: "单看屏幕总时长，其实是个很弱的预测因子——这常让人意外。真正承载信号的是它发生在什么时候、替代了什么、以及有多碎片化。总量在模型里是这些的背景，而不是结论。",
      },
    },
    social_min: {
      dir: "lower", target: 60, unit: "min", topic: "social",
      why: {
        en: "Social minutes affect mood differently depending on whether they were spent producing or consuming. The model cannot see which you did, so it reads the minutes alongside comparison and FOMO to infer it - which is why those three usually move together.",
        fa: "دقیقه‌های اجتماعی بسته به اینکه صرف تولید شده‌اند یا مصرف، اثر متفاوتی روی خلق‌وخو دارند. مدل نمی‌بیند کدام را کرده‌ای، پس دقیقه‌ها را کنار مقایسه و ترس از جاماندن می‌خواند تا حدس بزند — و به همین دلیل این سه معمولاً با هم حرکت می‌کنند.",
        ar: "دقائق التواصل تؤثر في المزاج بشكل مختلف حسب ما إذا أُنفقت في الإنتاج أم الاستهلاك. لا يرى النموذج أيهما فعلت، فيقرأ الدقائق إلى جانب المقارنة والخوف من التفويت ليستنتج — ولهذا تتحرك الثلاثة معاً عادةً.",
        zh: "社交时间对情绪的影响，取决于你是在创作还是在消费。模型看不到你做了哪一种，所以它把分钟数与「社会比较」和「错失恐惧」放在一起读来推断——这就是这三项通常一起变动的原因。",
      },
    },
    social_ratio: {
      dir: "lower", target: 0.25, unit: "%", topic: "social",
      why: {
        en: "The share matters more than the minutes once the total is fixed. Sixty social minutes out of ninety is a different day from sixty out of four hundred, and the ratio is what tells the model which one you had.",
        fa: "وقتی عدد کل ثابت است، سهم از دقیقه‌ها مهم‌تر می‌شود. شصت دقیقه‌ی اجتماعی از نود دقیقه، روزِ دیگری است نسبت به شصت از چهارصد، و همین نسبت است که به مدل می‌گوید کدامش را داشته‌ای.",
        ar: "الحصة أهم من الدقائق متى ثبت الإجمالي. ستون دقيقة تواصل من تسعين يومٌ مختلف عن ستين من أربعمئة، والنسبة هي ما يخبر النموذج أيهما كان يومك.",
        zh: "一旦总量固定，占比就比分钟数更重要。九十分钟里有六十分钟社交，和四百分钟里有六十分钟，是完全不同的一天——占比正是告诉模型你过的是哪一种。",
      },
    },
    gaming_min: {
      dir: "lower", target: 60, unit: "min", topic: "screen",
      why: {
        en: "Gaming is unusual in the schema: it is not harmful in itself and often protective for mood, but it has no natural stopping point. The model reads it in combination with sleep and night share, which is where an unbounded session actually shows up.",
        fa: "بازی در اسکیما خاص است: خودش مضر نیست و اغلب برای خلق‌وخو محافظ است، اما نقطه‌ی توقف طبیعی ندارد. مدل آن را در ترکیب با خواب و سهم شبانه می‌خواند، و همان‌جاست که یک نشستِ بی‌پایان واقعاً خودش را نشان می‌دهد.",
        ar: "اللعب استثنائي في المخطط: ليس ضاراً بذاته وكثيراً ما يحمي المزاج، لكن ليس له نقطة توقف طبيعية. يقرأه النموذج مقترناً بالنوم والحصة الليلية، وهناك تظهر الجلسة غير المحدودة فعلاً.",
        zh: "游戏在这套字段中很特别：它本身并不有害，还常常对情绪有保护作用，但它没有天然的停止点。模型会把它和睡眠、夜间占比结合起来读——一场没有边界的游戏，正是在那里显形。",
      },
    },
    video_min: {
      dir: "lower", target: 60, unit: "min", topic: "screen",
      why: {
        en: "Video is the easiest category to lose track of, because autoplay removes the decision point that every other app still has. That is why it is measured separately rather than folded into the total.",
        fa: "ویدیو آسان‌ترین دسته برای از دست دادن حساب است، چون پخش خودکار نقطه‌ی تصمیمی را که هر اپ دیگری هنوز دارد حذف می‌کند. به همین دلیل جدا اندازه‌گیری می‌شود نه اینکه در عدد کل حل شود.",
        ar: "الفيديو أسهل الفئات فقداناً للحساب، لأن التشغيل التلقائي يزيل نقطة القرار التي ما زالت كل التطبيقات الأخرى تملكها. لذلك يُقاس على حدة بدل دمجه في الإجمالي.",
        zh: "视频是最容易失去时间感的一类，因为自动播放取消了其他应用都还保留的那个决策点。这就是它被单独测量、而不是并入总量的原因。",
      },
    },
    work_study_ratio: {
      dir: "lower", target: 0.5, unit: "%", topic: "focus",
      why: {
        en: "A high work share is not a fault, and the model does not treat it as one. What it does track is whether the day has an end - because recovery is what the other inputs are measuring, and recovery cannot start while the work screen is still open.",
        fa: "سهم بالای کار ایراد نیست، و مدل هم آن را ایراد حساب نمی‌کند. چیزی که دنبال می‌کند این است که آیا روز پایانی دارد یا نه — چون بقیه‌ی ورودی‌ها دارند بازیابی را می‌سنجند، و بازیابی تا وقتی صفحه‌ی کار باز است نمی‌تواند شروع شود.",
        ar: "الحصة العالية للعمل ليست عيباً، والنموذج لا يعاملها كذلك. ما يتتبعه هو ما إذا كان لليوم نهاية — لأن بقية المدخلات تقيس التعافي، والتعافي لا يبدأ وشاشة العمل ما زالت مفتوحة.",
        zh: "工作占比高不是缺点，模型也不把它当缺点。它真正追踪的是这一天有没有结束——因为其他输入衡量的是恢复，而只要工作屏幕还开着，恢复就无法开始。",
      },
    },
    notifications_per_day: {
      dir: "lower", target: 40, unit: "", topic: "focus",
      why: {
        en: "Notifications are the input most under your direct control and the one people most underestimate. Each one is a potential context switch, and the cost is not the glance - it is the restart of whatever you were doing.",
        fa: "اعلان‌ها ورودی‌ای هستند که بیش از همه در کنترل مستقیم توست و بیش از همه دست‌کم گرفته می‌شود. هر کدام یک تعویضِ زمینه‌ی بالقوه است، و هزینه نگاه‌کردن نیست — شروعِ دوباره‌ی هر کاری است که داشتی می‌کردی.",
        ar: "الإشعارات هي المدخل الأكثر خضوعاً لسيطرتك المباشرة والأكثر استهانةً به. كل إشعار تبديل سياق محتمل، والتكلفة ليست النظرة — بل إعادة تشغيل ما كنت تفعله.",
        zh: "通知是最在你直接掌控之中、也最被低估的一项输入。每一条都是一次潜在的情境切换，代价不是你瞥的那一眼——而是你正在做的事被迫重启。",
      },
    },
    notification_density: {
      dir: "lower", target: 20, unit: "", topic: "focus",
      why: {
        en: "Density normalises the count by how long you were actually on the device. Forty notifications across eight hours is a different day from forty across ninety minutes, and only the density separates them.",
        fa: "چگالی، شمارش را بر حسب مدتی که واقعاً روی دستگاه بودی نرمال می‌کند. چهل اعلان در هشت ساعت روزِ دیگری است نسبت به چهل تا در نود دقیقه، و فقط چگالی این دو را جدا می‌کند.",
        ar: "الكثافة تعيّر العدد بحسب مدة وجودك الفعلي على الجهاز. أربعون إشعاراً على مدى ثماني ساعات يومٌ مختلف عن أربعين خلال تسعين دقيقة، والكثافة وحدها تفصل بينهما.",
        zh: "密度把数量按你实际使用设备的时长做了归一化。八小时里四十条通知，和九十分钟里四十条，是不同的一天——只有密度能区分它们。",
      },
    },
    pickups_per_day: {
      dir: "lower", target: 50, unit: "", topic: "focus",
      why: {
        en: "Pickups measure reaching, not using. A high count with low total time is the clearest signature of a checking habit, and it predicts fragmented attention better than duration does.",
        fa: "برداشتن‌ها، سراغ‌رفتن را می‌سنجند نه استفاده را. شمارش بالا با زمان کلِ پایین، واضح‌ترین امضای عادتِ چک‌کردن است، و توجهِ تکه‌تکه را بهتر از مدت پیش‌بینی می‌کند.",
        ar: "الالتقاطات تقيس الامتداد إلى الجهاز لا استخدامه. عدد مرتفع مع وقت إجمالي منخفض هو أوضح توقيع لعادة التفقّد، ويتنبأ بتشتّت الانتباه أفضل من المدة.",
        zh: "拿起次数衡量的是「伸手去拿」，而不是「在用」。次数高但总时长低，是查看习惯最清晰的特征，它对注意力碎片化的预测比时长更准。",
      },
    },
    pickup_density: {
      dir: "lower", target: 25, unit: "", topic: "focus",
      why: {
        en: "Pickups per hour of use. This is the field that distinguishes deliberate use from compulsive checking, because someone using the phone for a purpose picks it up less often per hour than someone checking it.",
        fa: "برداشتن در هر ساعتِ استفاده. این فیلدی است که استفاده‌ی آگاهانه را از چک‌کردنِ اجباری جدا می‌کند، چون کسی که با هدف از گوشی استفاده می‌کند در هر ساعت کمتر از کسی که فقط چکش می‌کند برش می‌دارد.",
        ar: "الالتقاطات لكل ساعة استخدام. هذا الحقل يميّز الاستخدام المقصود عن التفقّد القهري، لأن من يستخدم الهاتف لغرض يلتقطه في الساعة أقل ممن يتفقّده.",
        zh: "每小时使用中的拿起次数。这个字段能区分有目的的使用和强迫性查看，因为带着目的用手机的人，每小时拿起的次数少于只是不停查看的人。",
      },
    },
    app_opens_per_day: {
      dir: "lower", target: 60, unit: "", topic: "focus",
      why: {
        en: "App opens count intent, or the lack of it. Opening without a reason already in mind is what produces the sessions people cannot account for afterwards.",
        fa: "باز کردن اپ‌ها، قصد را می‌شمارد — یا نبودش را. باز کردن بدون اینکه از قبل دلیلی در ذهن باشد، همان چیزی است که نشست‌هایی می‌سازد که آدم بعداً نمی‌تواند حسابشان را بدهد.",
        ar: "فتح التطبيقات يعدّ النية أو غيابها. الفتح دون سبب حاضر في الذهن هو ما يُنتج الجلسات التي لا يستطيع المرء تفسيرها لاحقاً.",
        zh: "应用打开次数计的是「意图」——或意图的缺席。打开时心里没有理由，正是那些事后说不清的时段的来源。",
      },
    },
    app_open_density: {
      dir: "lower", target: 30, unit: "", topic: "focus",
      why: {
        en: "Switching rate per hour. High switching fragments attention even when total time and total opens both look reasonable, which is why it is tracked separately from either.",
        fa: "نرخ جابه‌جایی در هر ساعت. جابه‌جایی زیاد توجه را تکه‌تکه می‌کند حتی وقتی زمان کل و تعداد کلِ باز کردن هر دو معقول به نظر می‌رسند، و به همین دلیل جدا از هر دو دنبال می‌شود.",
        ar: "معدل التبديل في الساعة. التبديل الكثيف يفتّت الانتباه حتى حين يبدو الوقت الإجمالي وعدد الفتحات معقولين، ولهذا يُتتبع منفصلاً عنهما.",
        zh: "每小时的切换率。即使总时长和总打开次数看起来都合理，高频切换依然会把注意力切碎——所以它与这两者分开追踪。",
      },
    },
    fragmentation_index_0_100: {
      dir: "lower", target: 40, unit: "", topic: "focus",
      why: {
        en: "A composite of how broken up your day was. It exists because the individual counts can each look acceptable while the pattern they form does not - this field is what sees the pattern.",
        fa: "ترکیبی از اینکه روزت چقدر تکه‌تکه بوده. وجود دارد چون شمارش‌های تکی می‌توانند هرکدام قابل‌قبول به نظر برسند در حالی که الگویی که می‌سازند نیست — این فیلد همان چیزی است که الگو را می‌بیند.",
        ar: "مؤشر مركّب لمدى تجزّؤ يومك. وُجد لأن الأعداد المفردة قد يبدو كل منها مقبولاً بينما النمط الذي تشكّله ليس كذلك — وهذا الحقل هو ما يرى النمط.",
        zh: "一个反映你的一天有多零碎的综合指标。它之所以存在，是因为各项单独的数值可能都看着还行，但它们构成的模式却不行——这个字段看的正是模式。",
      },
    },
    focus_0_100: {
      dir: "higher", target: 60, unit: "", topic: "focus",
      why: {
        en: "Your own rating of how well attention held. It is self-reported, which makes it noisier than the counted fields, but it captures something they cannot: whether the fragmentation actually cost you anything today.",
        fa: "ارزیابی خودت از اینکه توجه چقدر خوب دوام آورده. خوداظهاری است، که آن را از فیلدهای شمارشی پرنویزتر می‌کند، اما چیزی را می‌گیرد که آن‌ها نمی‌توانند: اینکه آیا آن تکه‌تکه‌شدن امروز واقعاً برایت هزینه داشته یا نه.",
        ar: "تقييمك أنت لمدى ثبات انتباهك. إنه ذاتي التقرير، ما يجعله أكثر ضجيجاً من الحقول المعدودة، لكنه يلتقط ما لا تستطيعه: هل كلّفك ذلك التجزّؤ شيئاً اليوم فعلاً.",
        zh: "这是你自己对注意力保持得如何的评分。它是自评的，因此比那些被计数的字段更嘈杂，但它捕捉到了那些字段做不到的事：今天的碎片化究竟有没有真的让你付出代价。",
      },
    },
    productivity_0_100: {
      dir: "higher", target: 60, unit: "", topic: "focus",
      why: {
        en: "Distinct from focus: you can hold attention on the wrong thing all day. This field is what separates a day that felt busy from one that moved something.",
        fa: "متمایز از تمرکز: می‌شود تمام روز توجهت را روی چیز اشتباهی نگه داری. این فیلد همان چیزی است که روزی را که شلوغ حس شده از روزی که چیزی را جلو برده جدا می‌کند.",
        ar: "مختلف عن التركيز: يمكنك أن تُبقي انتباهك على الشيء الخطأ طوال اليوم. هذا الحقل هو ما يفصل يوماً بدا مزدحماً عن يوم حرّك شيئاً فعلاً.",
        zh: "它和专注不同：你可以一整天都专注在错的事情上。这个字段区分的是「感觉很忙的一天」和「真的推进了什么的一天」。",
      },
    },
    stress_0_10: {
      dir: "lower", target: 3, unit: "", topic: "body",
      why: {
        en: "Stress is both an input and a downstream effect here, which is why it often ranks high in the explanation without being the thing to fix first. Treating the field that drives it usually moves it further than aiming at it directly.",
        fa: "استرس اینجا هم ورودی است و هم اثرِ پایین‌دستی، و به همین دلیل اغلب در توضیح رتبه‌ی بالایی می‌گیرد بدون اینکه چیزی باشد که اول باید درست شود. درمانِ فیلدی که آن را می‌راند معمولاً بیشتر از هدف‌گرفتنِ مستقیمش جابه‌جایش می‌کند.",
        ar: "التوتر هنا مدخل وأثر لاحق معاً، ولهذا يحتل مرتبة عالية في التفسير كثيراً دون أن يكون أول ما يُعالَج. معالجة الحقل الذي يدفعه تحرّكه عادةً أكثر من استهدافه مباشرة.",
        zh: "压力在这里既是输入也是下游结果，所以它常常在解释中排名很高，却并不是该最先处理的东西。处理驱动它的那个字段，通常比直接瞄准它更有效。",
      },
    },
    mental_fatigue_0_10: {
      dir: "lower", target: 4, unit: "", topic: "body",
      why: {
        en: "Fatigue is the signal that recovery has fallen behind load. It is not a call to try harder - pushing through is precisely what keeps it high, and the model will keep reporting it until something in the recovery side changes.",
        fa: "خستگی نشانه‌ی این است که بازیابی از بار عقب افتاده. دعوت به تلاش بیشتر نیست — فشار آوردن دقیقاً همان چیزی است که بالا نگهش می‌دارد، و مدل تا وقتی چیزی در سمت بازیابی عوض نشود همچنان گزارشش می‌کند.",
        ar: "الإرهاق إشارة إلى أن التعافي تخلّف عن الحِمل. ليس دعوة لبذل جهد أكبر — فالدفع رغمه هو تحديداً ما يُبقيه مرتفعاً، وسيظل النموذج يبلّغ عنه حتى يتغير شيء في جانب التعافي.",
        zh: "疲劳是恢复跟不上负荷的信号。它不是让你更努力的召唤——硬撑恰恰是让它居高不下的原因，而模型会一直报告它，直到恢复这一侧发生改变。",
      },
    },
    physical_activity_min_per_day: {
      dir: "higher", target: 45, unit: "min", topic: "body",
      why: {
        en: "One of the fastest levers in the schema for mood and focus, and one where the first ten minutes carry most of the effect. It is also the only input here that improves several others at once.",
        fa: "یکی از سریع‌ترین اهرم‌های اسکیما برای خلق‌وخو و تمرکز، و جایی که ده دقیقه‌ی اول بیشترِ اثر را دارد. تنها ورودی‌ای هم هست که چند تای دیگر را هم‌زمان بهتر می‌کند.",
        ar: "من أسرع الروافع في المخطط للمزاج والتركيز، وأول عشر دقائق فيها تحمل معظم الأثر. وهو أيضاً المدخل الوحيد هنا الذي يحسّن عدة مدخلات أخرى دفعة واحدة.",
        zh: "这是这套字段中对情绪和专注见效最快的杠杆之一，而且前十分钟就承载了大部分效果。它也是这里唯一一个能同时改善其他多项输入的输入。",
      },
    },
    digital_dependence_0_100: {
      dir: "lower", target: 40, unit: "", topic: "screen",
      why: {
        en: "This measures pull, not volume: how strongly the device draws at you regardless of how much you use it. It responds to friction rather than to resolve, which is why the advice for it is always about changing the environment, not trying harder.",
        fa: "این کِشش را می‌سنجد نه حجم را: اینکه دستگاه چقدر قوی تو را می‌کِشد، فارغ از اینکه چقدر ازش استفاده می‌کنی. به اصطکاک پاسخ می‌دهد نه به عزم، و به همین دلیل توصیه‌اش همیشه درباره‌ی عوض‌کردن محیط است، نه بیشتر تلاش‌کردن.",
        ar: "هذا يقيس الشدّ لا الحجم: مدى قوة جذب الجهاز لك بغضّ النظر عن مقدار استخدامك. يستجيب للاحتكاك لا للعزيمة، ولهذا تدور نصيحته دائماً حول تغيير البيئة لا بذل جهد أكبر.",
        zh: "它衡量的是拉力，不是用量：无论你用多少，设备对你的牵引有多强。它回应的是阻力而非决心——所以关于它的建议永远是改变环境，而不是更努力。",
      },
    },
    fomo_1_10: {
      dir: "lower", target: 4, unit: "", topic: "social",
      why: {
        en: "Fear of missing out is measured because it predicts checking behaviour better than any counted field does. It is also the input most reliably reduced by a single experiment: leave one app closed for an evening and see what actually needed you.",
        fa: "ترس از جا ماندن اندازه‌گیری می‌شود چون رفتار چک‌کردن را بهتر از هر فیلد شمارشی پیش‌بینی می‌کند. مطمئن‌ترین ورودی برای کم‌شدن با یک آزمایش هم هست: یک اپ را یک شب بسته بگذار و ببین واقعاً چه چیزی به تو نیاز داشت.",
        ar: "يُقاس الخوف من التفويت لأنه يتنبأ بسلوك التفقّد أفضل من أي حقل معدود. وهو أيضاً المدخل الأكثر استجابة للانخفاض بتجربة واحدة: اترك تطبيقاً مغلقاً مساءً وانظر ما الذي احتاجك فعلاً.",
        zh: "之所以测量错失恐惧，是因为它对查看行为的预测比任何计数字段都准。它也是最容易通过一次实验降下来的输入：让一个应用整晚不开，看看到底有什么真的需要你。",
      },
    },
    social_comparison_1_10: {
      dir: "lower", target: 4, unit: "", topic: "social",
      why: {
        en: "Comparison is driven by who is in the feed rather than by time spent, which makes it one of the few inputs you can change without changing your habits at all - only what you are shown.",
        fa: "مقایسه را این می‌راند که چه کسی در فید هست، نه زمانی که صرف می‌شود، و همین آن را یکی از معدود ورودی‌هایی می‌کند که می‌توانی بدون تغییر دادن هیچ عادتی عوضش کنی — فقط آنچه به تو نشان داده می‌شود.",
        ar: "تحرّك المقارنةَ هويةُ من في الموجز لا الوقت المنفَق، ما يجعلها من المدخلات القليلة التي يمكنك تغييرها دون تغيير عاداتك إطلاقاً — بل ما يُعرض عليك فقط.",
        zh: "驱动比较的是信息流里有谁，而不是花了多少时间——这使它成为少数几个你完全不用改变习惯就能改变的输入：只需改变你被展示的内容。",
      },
    },
  };

  const PERCENT = new Set(['night_ratio', 'social_ratio', 'work_study_ratio',
    'other_ratio', 'pre_sleep_ratio', 'gaming_ratio']);

  function fmt(field, value) {
    if (value == null || Number.isNaN(value)) return null;
    const meta = FIELDS[field] || {};
    if (PERCENT.has(field)) return `${Math.round(value * 1000) / 10}%`;
    const rounded = Math.round(value * 10) / 10;
    return meta.unit ? `${rounded}${meta.unit === '%' ? '%' : ' ' + meta.unit}` : String(rounded);
  }

  /** Where the user's value sits against the healthy reference. */
  function standing(field, value) {
    const meta = FIELDS[field];
    if (!meta || meta.target == null || value == null) return null;
    const better = meta.dir === 'higher' ? value >= meta.target : value <= meta.target;
    const gap = Math.abs(value - meta.target);
    return { better, gap, target: meta.target, dir: meta.dir };
  }

  /** What the model actually said about this field today. */
  function modelVerdict(field, result) {
    const feats = (result && result.shap_features) || [];
    const idx = feats.findIndex((f) => f.feature === field);
    if (idx === -1) return null;
    const f = feats[idx];
    return { rank: idx + 1, direction: f.direction, of: feats.length };
  }

  const T = {
    yours: {
      en: 'You logged {value}.', fa: 'تو {value} ثبت کردی.',
      ar: 'سجّلت {value}.', zh: '你记录的是 {value}。',
    },
    noValue: {
      en: 'You have not logged this one yet, so there is nothing of yours to read here.',
      fa: 'این یکی را هنوز ثبت نکرده‌ای، پس چیزی از خودت اینجا نیست که بخوانم.',
      ar: 'لم تسجّل هذه بعد، فلا يوجد شيء خاص بك لأقرأه هنا.',
      zh: '你还没有记录这一项，所以这里没有属于你的数据可读。',
    },
    okVsTarget: {
      en: 'That is on the healthy side of the {target} reference.',
      fa: 'این سمتِ سالمِ مرجعِ {target} است.',
      ar: 'هذا في الجانب الصحي من المرجع {target}.',
      zh: '这在 {target} 这个参考值的健康一侧。',
    },
    offVsTarget: {
      en: 'The healthy reference is {target}, so you are {gap} away from it.',
      fa: 'مرجع سالم {target} است، پس {gap} با آن فاصله داری.',
      ar: 'المرجع الصحي هو {target}، فأنت على بعد {gap} منه.',
      zh: '健康参考值是 {target}，你与它相差 {gap}。',
    },
    hurtTop: {
      en: 'And it was the single largest thing pulling your score down today.',
      fa: 'و امروز بزرگ‌ترین چیزی بود که امتیازت را پایین می‌کشید.',
      ar: 'وكان أكبر عامل يسحب درجتك للأسفل اليوم.',
      zh: '而且它是今天把你的分数往下拉得最多的一项。',
    },
    hurtRanked: {
      en: 'The model put it at number {rank} among the things pulling your score down today.',
      fa: 'مدل آن را شماره‌ی {rank} میان چیزهایی گذاشت که امروز امتیازت را پایین می‌کشیدند.',
      ar: 'وضعه النموذج في المرتبة {rank} بين ما يسحب درجتك للأسفل اليوم.',
      zh: '模型把它排在今天拉低你分数的因素中的第 {rank} 位。',
    },
    helping: {
      en: 'Today it was working in your favour, not against you.',
      fa: 'امروز به نفعت کار می‌کرد، نه علیهت.',
      ar: 'اليوم كان يعمل لصالحك لا ضدك.',
      zh: '今天它是在帮你，而不是在拖你后腿。',
    },
    notRanked: {
      en: 'It did not make today\'s top factors either way, which means it was not what decided this score.',
      fa: 'در هیچ جهتی جزو عامل‌های اصلی امروز نبود، یعنی چیزی نبود که این امتیاز را تعیین کند.',
      ar: 'لم يدخل ضمن عوامل اليوم الأبرز في أي اتجاه، ما يعني أنه ليس ما حسم هذه الدرجة.',
      zh: '它在任何方向上都没有进入今天的主要因素，也就是说，决定这个分数的不是它。',
    },
    noResult: {
      en: 'Run a check-in and I can tell you what it did to your score, not just what it is.',
      fa: 'یک بررسی بزن تا بتوانم بگویم با امتیازت چه کرد، نه فقط اینکه چقدر است.',
      ar: 'شغّل فحصاً وسأخبرك بما فعله بدرجتك، لا بما هو فقط.',
      zh: '做一次记录，我就能告诉你它对你的分数做了什么，而不只是它是多少。',
    },
    nextStep: { en: 'Next step: ', fa: 'قدم بعدی: ', ar: 'الخطوة التالية: ', zh: '下一步：' },
  };

  const fill = (tpl, vars) => Object.keys(vars || {}).reduce(
    (s, k) => s.replace(new RegExp(`\\{${k}\\}`, 'g'), vars[k]), pick(tpl));

  /**
   * answer(field, ctx) -> string
   * ctx: { payload, result } - the same shape ai-menu.js already builds.
   */
  function answer(field, ctx) {
    ctx = ctx || {};
    const meta = FIELDS[field];
    if (!meta) return '';
    const payload = ctx.payload || {};
    const raw = payload[field];
    const parts = [];

    const value = (typeof raw === 'number' && !Number.isNaN(raw)) ? raw : null;
    if (value == null) {
      parts.push(pick(T.noValue));
    } else {
      parts.push(fill(T.yours, { value: fmt(field, value) }));
      const s = standing(field, value);
      if (s) {
        parts.push(s.better
          ? fill(T.okVsTarget, { target: fmt(field, s.target) })
          : fill(T.offVsTarget, { target: fmt(field, s.target), gap: fmt(field, s.gap) }));
      }
    }

    // What the model actually said today - the part that makes this an
    // answer rather than a lookup.
    if (!ctx.result) {
      parts.push(pick(T.noResult));
    } else {
      const v = modelVerdict(field, ctx.result);
      if (!v) parts.push(pick(T.notRanked));
      else if (v.direction === 'decrease') {
        parts.push(v.rank === 1 ? pick(T.hurtTop) : fill(T.hurtRanked, { rank: v.rank }));
      } else parts.push(pick(T.helping));
    }

    parts.push(pick(meta.why));

    // The real recommendation for this field, if the engine produced one.
    const rec = ((ctx.result && ctx.result.recommendations) || [])
      .find((r) => r.source_field === field);
    if (rec) {
      const lang = (window.DWI18n && window.DWI18n.get) ? window.DWI18n.get() : 'en';
      const action = ((rec.text_i18n || {}).action || {})[lang] || rec.action;
      if (action) parts.push(pick(T.nextStep) + action);
    }

    return parts.filter(Boolean).join(' ');
  }

  /** Menu entries, one per inspectable field, in all four languages. */
  function menuItems() {
    const Q = {
      en: (n) => `How is my ${n}?`,
      fa: (n) => `وضعیت «${n}» من چطور است؟`,
      ar: (n) => `كيف حال «${n}» لديّ؟`,
      zh: (n) => `我的「${n}」怎么样？`,
    };
    return Object.keys(FIELDS).map((key) => {
      const out = { id: `field_${key}`, cat: 'signals', need: ['payload'], icon: '🔎', field: key };
      ['en', 'fa', 'ar', 'zh'].forEach((lang) => {
        // `__raw` is coach-labels.js's own escape hatch for callers that
        // need all four languages at once rather than the current one.
        const table = ((window.DWCoachLabels || {}).__raw || {})[key];
        const name = (table && table[lang]) || label(key);
        out[lang] = Q[lang](name);
      });
      return out;
    });
  }

  function has(field) { return !!FIELDS[field]; }


  /* ---- "What if I changed this?" ---------------------------------
     A second question per field, answered from the same deterministic
     target the recommendation engine uses - not from a model run, and
     never as a promised score change. The honest answer names the
     target and what it would take to get there; it does not claim a
     number the model has not produced. */
  const W = {
    q: {
      en: (n) => `What if I improved my ${n}?`,
      fa: (n) => `اگر «${n}» را بهتر کنم چه می‌شود؟`,
      ar: (n) => `ماذا لو حسّنت «${n}» لديّ؟`,
      zh: (n) => `如果我改善「${n}」会怎样？`,
    },
    from: {
      en: 'You are at {value} now.', fa: 'الان روی {value} هستی.',
      ar: 'أنت الآن عند {value}.', zh: '你现在是 {value}。',
    },
    toward: {
      en: 'The reference this app works toward is {target}.',
      fa: 'مرجعی که این برنامه به سمتش کار می‌کند {target} است.',
      ar: 'المرجع الذي يعمل هذا التطبيق نحوه هو {target}.',
      zh: '这个应用参照的目标是 {target}。',
    },
    already: {
      en: 'You are already on the healthy side of it, so the useful move here is protecting it rather than pushing further.',
      fa: 'همین حالا سمتِ سالمش هستی، پس کار مفید اینجا حفظ کردنش است نه فشار آوردن بیشتر.',
      ar: 'أنت بالفعل في جانبه الصحي، فالخطوة المفيدة هنا حمايته لا الدفع أبعد.',
      zh: '你已经在它的健康一侧了，所以这里有用的做法是守住它，而不是继续推进。',
    },
    honest: {
      en: 'I will not put a score on that change. The model produces a score from your whole day at once, so a single field moved in isolation does not have a number I could honestly quote. What I can tell you is the direction, and that this field is one the engine has a concrete step for.',
      fa: 'روی آن تغییر عددی نمی‌گذارم. مدل امتیاز را از کلِ روزت یک‌جا می‌سازد، پس یک فیلدِ تنها که جدا جابه‌جا شود عددی ندارد که بتوانم صادقانه نقل کنم. چیزی که می‌توانم بگویم جهت است، و اینکه این فیلد از آن‌هایی است که موتور برایش قدم مشخصی دارد.',
      ar: 'لن أضع رقماً على ذلك التغيير. النموذج ينتج الدرجة من يومك كاملاً دفعة واحدة، فحقل واحد يتحرك بمعزل لا يملك رقماً أستطيع نقله بصدق. ما أستطيع قوله هو الاتجاه، وأن هذا الحقل مما للمحرّك خطوة ملموسة بشأنه.',
      zh: '我不会给那个改变安上一个分数。模型是把你一整天的数据一次性算成分数的，所以单独移动一个字段，并没有一个我能诚实引用的数字。我能告诉你的是方向，以及这个字段是引擎有具体步骤可提供的那一类。',
    },
    tryIt: {
      en: 'Want the exact step? Ask how this field is doing and I will give you the one the engine produced from your own number.',
      fa: 'قدم دقیقش را می‌خواهی؟ بپرس وضعیت این فیلد چطور است تا همانی را بدهم که موتور از عدد خودت ساخته.',
      ar: 'تريد الخطوة الدقيقة؟ اسأل عن حال هذا الحقل وسأعطيك ما أنتجه المحرّك من رقمك أنت.',
      zh: '想要确切的步骤？问问这个字段的状况，我会给你引擎根据你自己的数值生成的那一步。',
    },
  };

  function whatIf(field, ctx) {
    const meta = FIELDS[field];
    if (!meta) return '';
    const value = ((ctx || {}).payload || {})[field];
    const parts = [];
    if (typeof value === 'number' && !Number.isNaN(value)) {
      parts.push(fill(W.from, { value: fmt(field, value) }));
      const s = standing(field, value);
      if (s && s.better) {
        parts.push(fill(W.toward, { target: fmt(field, s.target) }));
        parts.push(pick(W.already));
        return parts.join(' ');
      }
      if (s) parts.push(fill(W.toward, { target: fmt(field, s.target) }));
    }
    parts.push(pick(W.honest));
    parts.push(pick(meta.why));
    parts.push(pick(W.tryIt));
    return parts.filter(Boolean).join(' ');
  }

  function whatIfMenuItems() {
    return Object.keys(FIELDS).map((key) => {
      const out = { id: `whatif_${key}`, cat: 'whatif', need: ['payload'], icon: '🔀', field: key };
      ['en', 'fa', 'ar', 'zh'].forEach((lang) => {
        const table = ((window.DWCoachLabels || {}).__raw || {})[key];
        const name = (table && table[lang]) || label(key);
        out[lang] = W.q[lang](name);
      });
      return out;
    });
  }

  window.DWFieldGuide = {
    FIELDS, answer, menuItems, has, standing, modelVerdict,
    whatIf, whatIfMenuItems,
  };
})();
