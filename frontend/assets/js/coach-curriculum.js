/*
  The coach's teaching material: how this system actually works, and the
  mechanisms behind the advice it gives.

  Why this exists separately from coach-knowledge.js
  --------------------------------------------------
  That file answers "what does my number mean". This one answers "how
  does any of this work" - the questions someone asks when they want to
  understand the tool rather than their result. They were missing
  entirely: a user could see a SHAP bar chart and had no way to ask what
  SHAP is, could read a confidence figure and no way to ask whether high
  confidence means correct.

  Two standards every entry here holds to:

  1. It teaches the real thing, including where it is weak. The SHAP
     entry says correlated features share credit in ways that can look
     arbitrary. The interval entry says what a conformal band does NOT
     mean. An explanation that only lists strengths is marketing.

  2. It is about THIS system where it can be. The leakage entry does not
     define leakage in the abstract - it says that leakage happened in
     this project, what the split was, and that the metrics fell after
     it was fixed. That is more useful, and it is checkable.

  No entry needs the user to have run a check-in, so these are always
  answerable - which also makes them the honest fallback when someone
  asks something the data cannot answer.
*/
(function () {
  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : (t && t.en) || '');

  const TOPICS = {
    edu_two_models: {
      cat: "method", icon: "🧠",
      q: { en: "How many models is this app actually running?", fa: "این برنامه واقعاً چند تا مدل اجرا می‌کند؟", ar: "كم نموذجاً يشغّل هذا التطبيق فعلاً؟", zh: "这个应用实际上在运行几个模型？" },
      a: {
        en: "Exactly two, both supervised. A classifier predicts your health class seven days from now, and a regressor predicts your score today on a 0-100 scale. They are trained on different targets, so they can and sometimes do disagree - a good score today with a worse class next week is not a bug, it is the two horizons saying different things. Nothing else in the app is a model: the recommendations, the plan and this coach are all deterministic rules.",
        fa: "دقیقاً دو تا، هر دو نظارت‌شده. یک طبقه‌بند، کلاس سلامتت را برای هفت روز بعد پیش‌بینی می‌کند، و یک رگرسور امتیاز امروزت را روی مقیاس ۰ تا ۱۰۰. روی هدف‌های متفاوتی آموزش دیده‌اند، پس می‌توانند — و گاهی می‌کنند — با هم اختلاف داشته باشند: امتیاز خوبِ امروز با کلاسِ بدترِ هفته‌ی بعد باگ نیست، دو افقِ زمانی‌اند که چیزهای متفاوتی می‌گویند. هیچ چیز دیگری در این برنامه مدل نیست: پیشنهادها، برنامه و همین مربی، همه قاعده‌های قطعی‌اند.",
        ar: "اثنان بالضبط، وكلاهما خاضع للإشراف. مصنِّف يتنبأ بفئتك الصحية بعد سبعة أيام، ومرتدّ يتنبأ بدرجتك اليوم على مقياس 0-100. دُرّبا على هدفين مختلفين، فقد يختلفان وأحياناً يفعلان: درجة جيدة اليوم مع فئة أسوأ الأسبوع القادم ليست خللاً، بل أفقان زمنيان يقولان أمرين مختلفين. لا شيء آخر في التطبيق نموذج: التوصيات والخطة وهذا المدرّب كلها قواعد حتمية.",
        zh: "正好两个，都是有监督模型。一个分类器预测你七天后的健康类别，一个回归器在 0-100 的尺度上预测你今天的分数。它们训练的目标不同，所以可能、有时也确实会不一致——今天分数好而下周类别差，这不是 bug，而是两个时间尺度在说不同的事。应用里其他东西都不是模型：推荐、计划和这个教练都是确定性规则。",
      },
    },
    edu_two_horizons: {
      cat: "method", icon: "⏳",
      q: { en: "Why is my score about today but my class about next week?", fa: "چرا امتیازم درباره‌ی امروز است ولی کلاسم درباره‌ی هفته‌ی بعد؟", ar: "لماذا درجتي عن اليوم وفئتي عن الأسبوع القادم؟", zh: "为什么我的分数是关于今天的，而类别是关于下周的？" },
      a: {
        en: "Because they were trained that way, and mixing them is the single most misleading thing this app could do. The regressor's target is health_score_0_100 for the day you logged. The classifier's target is future_health_class_7d - a label about a week ahead. Showing a number about today next to a label about next week, with neither marked, is how someone ends up believing the app forecast their score and got it wrong. Every place both appear, both are labelled with their horizon.",
        fa: "چون این‌طور آموزش دیده‌اند، و قاطی‌کردنشان گمراه‌کننده‌ترین کاری است که این برنامه می‌توانست بکند. هدف رگرسور، health_score_0_100 برای همان روزی است که ثبت کرده‌ای. هدف طبقه‌بند، future_health_class_7d است — برچسبی درباره‌ی یک هفته بعد. نشان‌دادن عددی درباره‌ی امروز کنار برچسبی درباره‌ی هفته‌ی بعد، بدون علامت‌گذاری هیچ‌کدام، همان راهی است که آدم باور می‌کند برنامه امتیازش را پیش‌بینی کرده و اشتباه کرده. هر جا هر دو می‌آیند، هر دو با افق زمانی‌شان برچسب می‌خورند.",
        ar: "لأنهما دُرّبا هكذا، وخلطهما أكثر ما قد يضلّل في هذا التطبيق. هدف المرتدّ هو health_score_0_100 لليوم الذي سجّلته. وهدف المصنِّف هو future_health_class_7d — تسمية عن أسبوع لاحق. عرض رقم عن اليوم بجانب تسمية عن الأسبوع القادم دون تمييز، هو ما يجعل المرء يظن أن التطبيق تنبّأ بدرجته وأخطأ. وحيثما ظهر كلاهما، وُسم كلاهما بأفقه.",
        zh: "因为它们就是这样训练的，而把两者混在一起，是这个应用可能犯的最具误导性的错误。回归器的目标是你记录那天的 health_score_0_100。分类器的目标是 future_health_class_7d——一个关于一周后的标签。把一个关于今天的数字和一个关于下周的标签并排显示、且都不标注，正是让人误以为应用预测了他的分数并且错了的原因。凡是两者同时出现的地方，都标注了各自的时间范围。",
      },
    },
    edu_shap: {
      cat: "method", icon: "🔬",
      q: { en: "What is SHAP and why should I trust those factor bars?", fa: "SHAP چیست و چرا باید به آن میله‌های عامل اعتماد کنم؟", ar: "ما هو SHAP ولماذا أثق بأشرطة العوامل تلك؟", zh: "什么是 SHAP，我为什么该相信那些因素条？" },
      a: {
        en: "SHAP splits a single prediction into per-feature contributions that add up to it exactly. It is not the model guessing at its own reasoning after the fact - it is an accounting of what each of your values did to this specific output, with a fairness property borrowed from game theory. The practical consequence: two people with the same score can have completely different bars, because the bars are about them, not about the average user. Where it is weak: strongly correlated inputs share credit in ways that can look arbitrary, so read the top few as a group rather than ranking them to the decimal.",
        fa: "SHAP یک پیش‌بینیِ واحد را به سهم‌های هر ویژگی می‌شکند که دقیقاً جمعشان همان می‌شود. این مدل نیست که بعد از کار درباره‌ی استدلال خودش حدس بزند — حسابرسی‌ای است از اینکه هر کدام از مقادیر تو با همین خروجی مشخص چه کرد، با یک خاصیت انصاف که از نظریه‌ی بازی قرض گرفته شده. نتیجه‌ی عملی: دو نفر با امتیاز یکسان می‌توانند میله‌های کاملاً متفاوتی داشته باشند، چون میله‌ها درباره‌ی خودشان است نه درباره‌ی کاربر میانگین. جای ضعفش: ورودی‌های به‌شدت هم‌بسته اعتبار را طوری تقسیم می‌کنند که می‌تواند دلبخواهی به نظر برسد، پس چند تای بالا را به‌صورت گروهی بخوان نه اینکه تا اعشار رتبه‌بندی‌شان کنی.",
        ar: "يقسّم SHAP تنبؤاً واحداً إلى مساهمات لكل سمة تُجمع لتساويه تماماً. ليس النموذج يخمّن تفكيره بأثر رجعي — بل محاسبة لما فعلته كل قيمة من قيمك بهذا المخرج تحديداً، بخاصية إنصاف مستعارة من نظرية الألعاب. النتيجة العملية: قد يحصل شخصان بالدرجة نفسها على أشرطة مختلفة تماماً، لأن الأشرطة عنهما لا عن المستخدم المتوسط. أما ضعفه: المدخلات شديدة الارتباط تتقاسم الفضل بطرق قد تبدو اعتباطية، فاقرأ القلائل الأولى كمجموعة بدل ترتيبها حتى العلامة العشرية.",
        zh: "SHAP 把单次预测拆成每个特征的贡献，而这些贡献加起来正好等于该预测。它不是模型事后猜测自己的推理，而是对你的每个数值对这个具体输出做了什么的一次核算，其公平性属性借自博弈论。实际后果是：分数相同的两个人，条形图可能完全不同，因为条形图讲的是他们自己，而不是平均用户。它的弱点：高度相关的输入会以看起来有些随意的方式分摊功劳，所以要把靠前的几项当作一组来读，而不是精确到小数去排名。",
      },
    },
    edu_conformal: {
      cat: "method", icon: "📏",
      q: { en: "What does the range around my score actually mean?", fa: "بازه‌ی دور امتیازم واقعاً یعنی چه؟", ar: "ما معنى النطاق حول درجتي فعلاً؟", zh: "我分数周围的那个区间到底是什么意思？" },
      a: {
        en: "It is a split-conformal prediction interval, calibrated on a held-out set. Read at the stated coverage - say 80% - it means that across many users like you, the true value fell inside a band built this way about 80% of the time. It is not a confidence interval about a parameter, and it does not mean there is an 80% chance your score is in there. The honest use is comparative: a wide band on your result means the model is less sure about you specifically than about someone with a narrow one.",
        fa: "یک بازه‌ی پیش‌بینیِ conformal تقسیمی است که روی یک مجموعه‌ی کنارگذاشته کالیبره شده. با پوششِ اعلام‌شده — مثلاً ۸۰٪ — بخوانش: یعنی در میان کاربران بسیاری مثل تو، مقدار واقعی حدود ۸۰٪ مواقع داخل باندی که این‌طور ساخته شده افتاده. این بازه‌ی اطمینان درباره‌ی یک پارامتر نیست، و معنی‌اش این نیست که ۸۰٪ احتمال دارد امتیاز تو آنجا باشد. استفاده‌ی صادقانه‌اش مقایسه‌ای است: باندِ پهن روی نتیجه‌ی تو یعنی مدل درباره‌ی مشخصاً تو کم‌مطمئن‌تر است تا درباره‌ی کسی با باند باریک.",
        ar: "إنه فترة تنبؤ conformal مقسومة، معايَرة على مجموعة محجوزة. اقرأها بالتغطية المعلنة — 80% مثلاً — أي أنه عبر كثير من المستخدمين أمثالك، وقعت القيمة الحقيقية داخل نطاق مبني هكذا نحو 80% من المرات. ليست فترة ثقة حول معلمة، ولا تعني أن احتمال وقوع درجتك فيها 80%. استخدامها الصادق مقارن: نطاق واسع على نتيجتك يعني أن النموذج أقل يقيناً بشأنك أنت تحديداً ممن نطاقه ضيق.",
        zh: "这是一个用留出集校准的分裂共形预测区间。按声明的覆盖率来读——比如 80%——意思是：在许多像你这样的用户中，真实值大约有 80% 的时候落在按这种方式构建的区间内。它不是关于某个参数的置信区间，也不意味着你的分数有 80% 的概率在里面。诚实的用法是比较性的：你结果上的区间越宽，说明模型对你本人的把握不如对区间窄的人。",
      },
    },
    edu_confidence_vs_accuracy: {
      cat: "method", icon: "🎯",
      q: { en: "Is a high confidence the same as being right?", fa: "اطمینان بالا یعنی درست بودن؟", ar: "هل الثقة العالية تعني الصواب؟", zh: "高置信度等于正确吗？" },
      a: {
        en: "No, and this project has direct evidence of the gap. Confidence is the model's own probability for its top class. Accuracy is how often it is actually right. A model can be systematically overconfident, and this one's leakage-fixed evaluation showed exactly that on genuinely new users - which is why the app describes a raw 85% as 'reasonably confident, not certain' rather than 'very confident'. Deliberately understating it is the honest choice when the calibration is known to lean the other way.",
        fa: "نه، و این پروژه شواهد مستقیمی از این فاصله دارد. اطمینان، احتمالِ خودِ مدل برای کلاس اولش است. دقت این است که واقعاً چند بار درست می‌گوید. یک مدل می‌تواند به‌طور سیستماتیک بیش‌اطمینان باشد، و ارزیابیِ نشت‌اصلاح‌شده‌ی همین مدل دقیقاً همین را روی کاربران واقعاً جدید نشان داد — به همین دلیل برنامه ۸۵٪ خام را «نسبتاً مطمئن، ولی قطعی نه» توصیف می‌کند نه «خیلی مطمئن». وقتی می‌دانیم کالیبراسیون به سمت دیگر متمایل است، کم‌گفتنِ عمدی انتخابِ صادقانه است.",
        ar: "لا، ولدى هذا المشروع دليل مباشر على الفجوة. الثقة هي احتمال النموذج نفسه لفئته الأولى. أما الدقة فهي كم مرة يصيب فعلاً. قد يكون النموذج مفرط الثقة منهجياً، وقد أظهر تقييم هذا النموذج بعد إصلاح التسريب ذلك تحديداً على مستخدمين جدد فعلاً — ولهذا يصف التطبيق 85% الخام بأنها «واثق إلى حد معقول، لا متيقن» لا «واثق جداً». التقليل المتعمد هو الخيار الصادق حين تُعرف المعايرة بأنها تميل في الاتجاه الآخر.",
        zh: "不是，而且这个项目有关于这个差距的直接证据。置信度是模型对其首选类别给出的概率。准确率是它实际有多少次是对的。模型可能系统性地过度自信，而这个模型在修复数据泄漏后的评估中，恰恰在真正的新用户上表现出了这一点——所以应用把原始的 85% 描述为「有一定把握，但并不确定」，而不是「非常有把握」。当已知校准偏向另一侧时，刻意保守才是诚实的选择。",
      },
    },
    edu_leakage: {
      cat: "method", icon: "🚰",
      q: { en: "What is data leakage and did it happen here?", fa: "نشت داده چیست و اینجا اتفاق افتاده؟", ar: "ما هو تسريب البيانات وهل حدث هنا؟", zh: "什么是数据泄漏，这里发生过吗？" },
      a: {
        en: "Leakage is when information that would not be available at prediction time gets into training - the model then scores brilliantly in evaluation and poorly in reality. It did happen here, and it is documented rather than hidden: the original split put the same user's different days on both sides of the train/test line, so the model was effectively being tested on people it had already met. The fix was a user-level split, and the honest consequence was that the headline metrics fell. Metrics that drop after a leakage fix are the trustworthy ones.",
        fa: "نشت وقتی است که اطلاعاتی که موقع پیش‌بینی در دسترس نخواهد بود وارد آموزش می‌شود — آن‌وقت مدل در ارزیابی درخشان و در واقعیت ضعیف عمل می‌کند. اینجا اتفاق افتاد، و به‌جای پنهان‌شدن مستند شده: تقسیم اولیه روزهای مختلفِ یک کاربر را دو طرفِ خط آموزش/آزمون می‌گذاشت، پس مدل عملاً روی آدم‌هایی آزموده می‌شد که قبلاً دیده بودشان. راه‌حل تقسیم در سطح کاربر بود، و پیامد صادقانه‌اش این بود که معیارهای اصلی افت کردند. معیارهایی که بعد از اصلاح نشت پایین می‌آیند، همان‌های قابل‌اعتمادند.",
        ar: "التسريب هو دخول معلومات لن تكون متاحة وقت التنبؤ إلى التدريب — فيسجّل النموذج نتائج باهرة في التقييم وضعيفة في الواقع. وقد حدث هنا، وهو موثّق لا مخفيّ: وضع التقسيم الأصلي أياماً مختلفة للمستخدم نفسه على جانبَي خط التدريب/الاختبار، فكان النموذج يُختبر عملياً على أشخاص قابلهم من قبل. كان الحل تقسيماً على مستوى المستخدم، وكانت النتيجة الصادقة هبوط المقاييس الرئيسية. والمقاييس التي تهبط بعد إصلاح تسريب هي الجديرة بالثقة.",
        zh: "数据泄漏是指预测时本不可得的信息进入了训练——于是模型在评估中表现极好，在现实中却很差。这里确实发生过，而且是被记录下来而非隐藏的：最初的划分把同一用户的不同日期分到了训练/测试线的两边，所以模型实际上是在它已经见过的人身上被测试。修复方法是按用户划分，诚实的后果是主要指标下降了。修复泄漏后会下降的指标，才是可信的那些。",
      },
    },
    edu_r2: {
      cat: "method", icon: "📊",
      q: { en: "What do R², MAE and RMSE actually tell me?", fa: "R² و MAE و RMSE واقعاً چه می‌گویند؟", ar: "ماذا تخبرني R² و MAE و RMSE فعلاً؟", zh: "R²、MAE 和 RMSE 到底告诉我什么？" },
      a: {
        en: "MAE is the average size of the miss in the units you care about - a MAE of 1.25 means the score is typically off by about a point and a quarter. RMSE is the same idea but squares the errors first, so it punishes rare large misses harder; if RMSE is much bigger than MAE, the model has occasional bad days. R² is the share of variance explained relative to just guessing the mean every time - useful for comparing models on the same data, close to meaningless across different datasets. Read MAE first: it is the only one in the units of your actual score.",
        fa: "MAE اندازه‌ی میانگینِ خطاست در واحدی که برایت مهم است — MAE برابر ۱.۲۵ یعنی امتیاز معمولاً حدود یک و ربع واحد خطا دارد. RMSE همان ایده است ولی اول خطاها را مربع می‌کند، پس خطاهای بزرگِ نادر را سخت‌تر جریمه می‌کند؛ اگر RMSE خیلی بزرگ‌تر از MAE باشد، مدل گاهی روزهای بدی دارد. R² سهم واریانسِ توضیح‌داده‌شده نسبت به این است که هر بار فقط میانگین را حدس بزنی — برای مقایسه‌ی مدل‌ها روی داده‌ی یکسان مفید است و بین مجموعه‌داده‌های متفاوت تقریباً بی‌معنی. اول MAE را بخوان: تنها موردی است که در واحدِ امتیازِ واقعی توست.",
        ar: "MAE هو متوسط حجم الخطأ بالوحدات التي تهمّك — MAE بمقدار 1.25 يعني أن الدرجة تخطئ عادةً بنحو نقطة وربع. وRMSE الفكرة نفسها لكنه يربّع الأخطاء أولاً، فيعاقب الأخطاء الكبيرة النادرة بقسوة أكبر؛ فإن كان RMSE أكبر بكثير من MAE فللنموذج أيام سيئة أحياناً. أما R² فهو نصيب التباين المفسَّر مقارنةً بتخمين المتوسط في كل مرة — مفيد لمقارنة نماذج على البيانات نفسها، وشبه بلا معنى عبر مجموعات بيانات مختلفة. اقرأ MAE أولاً: فهو الوحيد بوحدات درجتك الفعلية.",
        zh: "MAE 是以你关心的单位表示的平均偏差大小——MAE 为 1.25 意味着分数通常偏离约一点二五分。RMSE 是同样的思路，但先把误差平方，因此对罕见的大偏差惩罚更重；如果 RMSE 远大于 MAE，说明模型偶尔会有很糟的时候。R² 是相对于「每次只猜平均值」所解释的方差比例——在同一数据上比较模型时有用，跨不同数据集则几乎没有意义。先看 MAE：它是唯一以你真实分数的单位表示的指标。",
      },
    },
    edu_f1_roc: {
      cat: "method", icon: "🎚️",
      q: { en: "What are F1 and ROC-AUC, in plain terms?", fa: "F1 و ROC-AUC به زبان ساده چه هستند؟", ar: "ما هما F1 و ROC-AUC ببساطة؟", zh: "用大白话说，F1 和 ROC-AUC 是什么？" },
      a: {
        en: "F1 balances two different ways of being wrong: calling something a risk when it is not, and missing a real one. It is a single number for a trade-off, which is why it is preferred to plain accuracy whenever the classes are uneven. ROC-AUC asks a different question: if you drew one person from each class at random, how often would the model rank the right one higher? 0.5 is coin-flipping, 1.0 is perfect separation. A high ROC-AUC with a mediocre F1 usually means the ranking is good but the threshold is set wrong.",
        fa: "F1 دو راهِ متفاوتِ اشتباه‌کردن را متعادل می‌کند: خطر خواندنِ چیزی که خطر نیست، و از دست دادن یک خطر واقعی. یک عدد واحد برای یک بده‌بستان است، و به همین دلیل هر جا کلاس‌ها نامتوازن باشند بر دقتِ ساده ترجیح دارد. ROC-AUC سؤال دیگری می‌پرسد: اگر از هر کلاس یک نفر تصادفی برداری، مدل چند بار درستی را بالاتر رتبه می‌دهد؟ ۰.۵ یعنی شیر یا خط، ۱.۰ یعنی جداسازی کامل. ROC-AUC بالا با F1 متوسط معمولاً یعنی رتبه‌بندی خوب است ولی آستانه اشتباه تنظیم شده.",
        ar: "يوازن F1 بين طريقتين مختلفتين للخطأ: أن تصف شيئاً بالخطر وهو ليس كذلك، وأن تفوّت خطراً حقيقياً. إنه رقم واحد لمقايضة، ولهذا يُفضَّل على الدقة البسيطة كلما كانت الفئات غير متوازنة. أما ROC-AUC فيطرح سؤالاً آخر: لو سحبت شخصاً من كل فئة عشوائياً، كم مرة سيرتّب النموذج الصحيح أعلى؟ 0.5 كرمي عملة، و1.0 فصل تام. ROC-AUC عالٍ مع F1 متوسط يعني عادةً أن الترتيب جيد لكن العتبة مضبوطة خطأ.",
        zh: "F1 平衡了两种不同的错法：把不是风险的说成风险，以及漏掉一个真实的风险。它用一个数字表达一个取舍，所以在类别不均衡时比单纯的准确率更受青睐。ROC-AUC 问的是另一个问题：如果你从每个类别中随机各抽一人，模型有多少次会把正确的那个排得更靠前？0.5 相当于抛硬币，1.0 是完美区分。ROC-AUC 高而 F1 平庸，通常意味着排序不错，但阈值设错了。",
      },
    },
    edu_cv: {
      cat: "method", icon: "🔁",
      q: { en: "What is cross-validation and why does it matter here?", fa: "اعتبارسنجی متقاطع چیست و اینجا چرا مهم است؟", ar: "ما هي المصادقة المتقاطعة ولماذا تهم هنا؟", zh: "什么是交叉验证，它在这里为什么重要？" },
      a: {
        en: "Instead of trusting one lucky split of the data, cross-validation rotates which slice is held out and reports the spread as well as the average. It matters here for one specific reason: with per-user daily records, the folds have to be split by user, not by row. Split by row and the same person appears in training and validation, and the result is a number that flatters the model and predicts nothing about a new user.",
        fa: "به‌جای اعتماد به یک تقسیمِ خوش‌شانسِ داده، اعتبارسنجی متقاطع می‌چرخاند که کدام برش کنار گذاشته شود و علاوه بر میانگین، پراکندگی را هم گزارش می‌کند. اینجا به یک دلیل مشخص مهم است: با رکوردهای روزانه‌ی هر کاربر، فولدها باید بر اساس کاربر تقسیم شوند نه بر اساس ردیف. اگر بر اساس ردیف تقسیم کنی، همان آدم هم در آموزش و هم در اعتبارسنجی ظاهر می‌شود، و نتیجه عددی است که مدل را می‌ستاید و درباره‌ی یک کاربر جدید هیچ پیش‌بینی نمی‌کند.",
        ar: "بدل الوثوق بتقسيم محظوظ واحد للبيانات، تدير المصادقة المتقاطعة أي شريحة تُحجَز وتبلّغ عن التشتّت إلى جانب المتوسط. وتهمّ هنا لسبب محدد: مع سجلات يومية لكل مستخدم، يجب تقسيم الطيّات حسب المستخدم لا حسب الصف. قسّم حسب الصف يظهر الشخص نفسه في التدريب والتحقق، فتكون النتيجة رقماً يجامل النموذج ولا يتنبأ بشيء عن مستخدم جديد.",
        zh: "交叉验证不依赖一次运气好的数据划分，而是轮换被留出的那一份，并同时报告平均值和离散程度。它在这里重要有一个具体原因：面对每个用户的每日记录，折叠必须按用户划分，而不是按行。按行划分的话，同一个人会同时出现在训练和验证中，得到的数字只是在恭维模型，对新用户毫无预测力。",
      },
    },
    edu_baseline: {
      cat: "method", icon: "📉",
      q: { en: "How do I know this model beats just guessing?", fa: "از کجا بدانم این مدل از حدس‌زدن ساده بهتر است؟", ar: "كيف أعرف أن هذا النموذج يتفوّق على مجرد التخمين؟", zh: "我怎么知道这个模型比瞎猜强？" },
      a: {
        en: "By checking it against the dumbest thing that could work, which is the only comparison that means anything. For the regressor that is predicting the mean every time; for the classifier, always predicting the most common class. A model that cannot beat those has learned nothing. This project applies that test as a gate rather than a footnote: a seven-day regressor was trained here and rejected precisely because it failed against its baseline, and the two-stage estimator shipped instead because it beat it by a measured margin.",
        fa: "با سنجیدنش در برابر ابلهانه‌ترین چیزی که ممکن است کار کند — تنها مقایسه‌ای که معنایی دارد. برای رگرسور یعنی هر بار میانگین را پیش‌بینی کردن؛ برای طبقه‌بند، همیشه پرتکرارترین کلاس را گفتن. مدلی که نتواند از این‌ها بهتر باشد چیزی یاد نگرفته. این پروژه آن آزمون را به‌عنوان دروازه به کار می‌برد نه پاورقی: یک رگرسورِ هفت‌روزه اینجا آموزش داده شد و دقیقاً به این دلیل که در برابر خط‌پایه‌اش شکست خورد رد شد، و برآوردگرِ دومرحله‌ای به‌جایش رفت چون با حاشیه‌ای اندازه‌گیری‌شده از آن بهتر بود.",
        ar: "بمقارنته بأغبى ما قد ينجح، وهي المقارنة الوحيدة ذات المعنى. للمرتدّ يعني ذلك التنبؤ بالمتوسط في كل مرة؛ وللمصنِّف، التنبؤ دائماً بالفئة الأكثر شيوعاً. نموذج لا يتفوق على هذين لم يتعلم شيئاً. ويطبّق هذا المشروع ذلك الاختبار كبوابة لا كحاشية: دُرّب هنا مرتدّ لسبعة أيام ورُفض تحديداً لأنه أخفق أمام خط أساسه، وشُحن بدله المقدّر ثنائي المرحلة لأنه تفوق عليه بهامش مقاس.",
        zh: "办法是拿它跟「最笨但能用的方法」比，这是唯一有意义的比较。对回归器来说就是每次都预测平均值；对分类器来说就是永远预测最常见的类别。连这些都赢不了的模型，什么也没学到。这个项目把这个测试当作准入门槛而非脚注：这里曾训练过一个七天回归器，正是因为它输给了自己的基线而被否决，取而代之的两阶段估计器则以可测量的优势胜出。",
      },
    },
    edu_no_llm: {
      cat: "method", icon: "🚫",
      q: { en: "Why does the score not use an AI language model?", fa: "چرا امتیاز از یک مدل زبانی هوش مصنوعی استفاده نمی‌کند؟", ar: "لماذا لا تستخدم الدرجة نموذجاً لغوياً؟", zh: "为什么分数不使用 AI 语言模型？" },
      a: {
        en: "Because a score has to be reproducible and auditable, and a language model is neither. Same inputs, same score, every time, and every step from your numbers to the result can be traced. A language model would give you a fluent explanation that might not correspond to any actual computation - which is the worst possible property for a number someone might act on. The optional connector exists so you can add a language model for conversation, and it is deliberately kept away from the scoring path entirely.",
        fa: "چون یک امتیاز باید تکرارپذیر و قابل‌حسابرسی باشد، و مدل زبانی هیچ‌کدام نیست. ورودی یکسان، امتیاز یکسان، هر بار، و هر قدم از اعدادت تا نتیجه قابل ردیابی است. یک مدل زبانی توضیحی روان می‌داد که ممکن بود با هیچ محاسبه‌ی واقعی متناظر نباشد — که بدترین خاصیت ممکن برای عددی است که کسی ممکن است بر اساسش عمل کند. کانکتور اختیاری هست تا بتوانی برای گفتگو یک مدل زبانی اضافه کنی، و عمداً کاملاً از مسیر امتیازدهی دور نگه داشته شده.",
        ar: "لأن الدرجة يجب أن تكون قابلة للتكرار والتدقيق، والنموذج اللغوي ليس أياً منهما. المدخلات نفسها تعطي الدرجة نفسها في كل مرة، وكل خطوة من أرقامك إلى النتيجة قابلة للتتبع. النموذج اللغوي كان سيعطيك تفسيراً سلساً قد لا يقابل أي حساب فعلي — وهي أسوأ خاصية ممكنة لرقم قد يتصرف أحدهم بناءً عليه. الموصّل الاختياري موجود لتضيف نموذجاً لغوياً للمحادثة، وهو مُبعد عمداً عن مسار التسجيل كلياً.",
        zh: "因为分数必须可复现、可审计，而语言模型两者都不是。相同的输入，每次都得到相同的分数，从你的数字到结果的每一步都可追溯。语言模型会给你一个流畅的解释，但它可能不对应任何真实的计算——对于一个别人可能据此行动的数字来说，这是最糟糕的性质。可选的连接器的存在是让你为对话加上语言模型，而它被刻意完全隔离在评分路径之外。",
      },
    },
    edu_attention_residue: {
      cat: "science", icon: "🧩",
      q: { en: "Why is it so hard to get back to work after a quick check?", fa: "چرا بعد از یک چک کردن سریع، برگشتن به کار این‌قدر سخت است؟", ar: "لماذا يصعب العودة إلى العمل بعد تفقّد سريع؟", zh: "为什么快速看一眼之后，回到工作这么难？" },
      a: {
        en: "Because attention does not resume where it stopped - it restarts. Part of your focus stays with the thing you just glanced at, and the restart costs more than the glance did. This is why pickup count predicts fragmented attention better than total screen time does, and why a two-second look can cost several minutes. The practical move is not resisting the glance harder; it is removing the prompt for it.",
        fa: "چون توجه از جایی که ایستاده بود ادامه نمی‌دهد — از نو شروع می‌شود. بخشی از تمرکزت پیش همان چیزی می‌ماند که تازه نگاهش کرده‌ای، و شروعِ دوباره بیشتر از خودِ نگاه هزینه دارد. به همین دلیل تعداد برداشتن گوشی، توجهِ تکه‌تکه را بهتر از زمان کل صفحه پیش‌بینی می‌کند، و به همین دلیل یک نگاهِ دوثانیه‌ای می‌تواند چند دقیقه خرج بردارد. حرکت عملی، سخت‌تر مقاومت‌کردن در برابر نگاه نیست؛ برداشتنِ چیزی است که به آن دعوت می‌کند.",
        ar: "لأن الانتباه لا يستأنف من حيث توقف — بل يبدأ من جديد. يبقى جزء من تركيزك مع ما ألقيت عليه نظرة للتو، وإعادة البدء تكلّف أكثر من النظرة نفسها. لهذا يتنبأ عدد الالتقاطات بتشتّت الانتباه أفضل من إجمالي وقت الشاشة، ولهذا قد تكلّف نظرة من ثانيتين عدة دقائق. الخطوة العملية ليست مقاومة النظرة بجهد أكبر، بل إزالة ما يدعو إليها.",
        zh: "因为注意力不是从停下的地方继续，而是重新启动。你的一部分注意力还留在刚才瞥过的东西上，而重启的代价比那一瞥本身更大。这就是为什么拿起手机的次数比屏幕总时长更能预测注意力碎片化，也是为什么两秒钟的一瞥可能花掉好几分钟。实际的做法不是更用力地抵抗那一瞥，而是移除那个促使你去看的提示。",
      },
    },
    edu_variable_reward: {
      cat: "science", icon: "🎰",
      q: { en: "Why do I keep checking even when there is nothing there?", fa: "چرا حتی وقتی چیزی نیست باز هم چک می‌کنم؟", ar: "لماذا أستمر في التفقّد حتى حين لا يوجد شيء؟", zh: "为什么明明什么都没有，我还是不停地看？" },
      a: {
        en: "Because unpredictable rewards drive checking harder than reliable ones do. If every check produced something, you would check on a schedule; because most produce nothing and a few produce something, checking becomes constant. This is not a character flaw and willpower is the wrong tool against it - the behaviour is a response to the schedule, so changing the schedule is what works. Turning off the notification that starts the loop beats resisting the loop.",
        fa: "چون پاداش‌های غیرقابل‌پیش‌بینی، چک‌کردن را قوی‌تر از پاداش‌های مطمئن پیش می‌برند. اگر هر چک‌کردن چیزی می‌داد، طبق برنامه چک می‌کردی؛ چون بیشترشان هیچ نمی‌دهند و چند تا چیزی می‌دهند، چک‌کردن دائمی می‌شود. این نقصِ شخصیت نیست و اراده ابزار اشتباهی در برابرش است — رفتار پاسخی به آن برنامه است، پس عوض‌کردن برنامه همان چیزی است که جواب می‌دهد. خاموش‌کردن اعلانی که حلقه را شروع می‌کند از مقاومت در برابر حلقه بهتر است.",
        ar: "لأن المكافآت غير المتوقعة تدفع إلى التفقّد أكثر من المكافآت الموثوقة. لو أعطى كل تفقّد شيئاً لتفقّدت وفق جدول؛ ولأن معظمها لا يعطي شيئاً وقليلها يعطي، صار التفقّد مستمراً. هذا ليس عيباً في الشخصية، وقوة الإرادة أداة خاطئة ضده — فالسلوك استجابة للجدول، وتغيير الجدول هو ما ينجح. إطفاء الإشعار الذي يبدأ الحلقة أفضل من مقاومة الحلقة.",
        zh: "因为不可预测的奖励比稳定的奖励更能驱动查看行为。如果每次查看都有收获，你会按时间表去查看；正因为大多数时候什么都没有、偶尔有一点，查看才变得持续不断。这不是性格缺陷，意志力也是错误的工具——这个行为是对「奖励时间表」的回应，所以改变时间表才有用。关掉启动这个循环的通知，胜过去抵抗这个循环。",
      },
    },
    edu_blue_light: {
      cat: "science", icon: "🔵",
      q: { en: "Is blue light really the problem before bed?", fa: "آیا واقعاً نور آبی مشکل پیش از خواب است؟", ar: "هل الضوء الأزرق هو المشكلة فعلاً قبل النوم؟", zh: "睡前真正的问题是蓝光吗？" },
      a: {
        en: "Partly, and it is usually overstated relative to the other half. Light does delay the melatonin rise that starts sleep, so a bright screen close to your face at midnight is not nothing. But engagement matters at least as much: an argument, a work email or a cliffhanger keeps you alert regardless of the colour temperature. A night-shift filter on a phone you are still arguing on has fixed the smaller half of the problem.",
        fa: "تا حدی، و معمولاً نسبت به نیمه‌ی دیگر بزرگ‌نمایی می‌شود. نور واقعاً بالا آمدن ملاتونین را که خواب را شروع می‌کند عقب می‌اندازد، پس یک صفحه‌ی روشن نزدیک صورتت نصف‌شب هیچ نیست. اما درگیری ذهنی دست‌کم به همان اندازه مهم است: یک بحث، یک ایمیل کاری یا یک پایانِ معلق، فارغ از دمای رنگ، هوشیار نگهت می‌دارد. فیلتر شب روی گوشی‌ای که هنوز داری رویش بحث می‌کنی، نیمه‌ی کوچک‌ترِ مسئله را حل کرده.",
        ar: "جزئياً، وعادةً يُبالغ فيه مقارنةً بالنصف الآخر. الضوء يؤخّر فعلاً ارتفاع الميلاتونين الذي يبدأ به النوم، فالشاشة الساطعة قرب وجهك منتصف الليل ليست بلا أثر. لكن الانخراط لا يقلّ أهمية: جدال أو بريد عمل أو نهاية معلّقة تُبقيك يقظاً بغضّ النظر عن حرارة اللون. فلتر الليل على هاتف ما زلت تتجادل عليه أصلح النصف الأصغر من المشكلة.",
        zh: "部分是，但相对于另一半，它通常被夸大了。光确实会推迟启动睡眠的褪黑素上升，所以半夜里贴近脸的明亮屏幕并非无害。但投入程度至少同样重要：一场争论、一封工作邮件或一个悬念结尾，无论色温如何都会让你保持清醒。在一部你还在上面吵架的手机上开夜间模式，只是解决了问题中较小的那一半。",
      },
    },
    edu_screen_time_weak: {
      cat: "science", icon: "📵",
      q: { en: "Is total screen time a good measure of anything?", fa: "آیا زمان کل صفحه معیار خوبی برای چیزی هست؟", ar: "هل إجمالي وقت الشاشة مقياس جيد لأي شيء؟", zh: "屏幕总时长是衡量任何东西的好指标吗？" },
      a: {
        en: "On its own, no - and this is one of the most robust findings in the area. The same number of minutes can be a good day or a bad one depending on when they happened, what they replaced, and whether they were fragmented. Two hours of video call with someone you love and two hours of scrolling at 1am are the same total and different days. This is why the app measures timing, composition and fragmentation separately rather than reporting one headline number.",
        fa: "به‌تنهایی نه — و این یکی از استوارترین یافته‌های این حوزه است. همان تعداد دقیقه می‌تواند روز خوبی باشد یا بدی، بسته به اینکه کِی اتفاق افتاده، جای چه چیزی را گرفته، و آیا تکه‌تکه بوده. دو ساعت تماس تصویری با کسی که دوستش داری و دو ساعت اسکرول ساعت یک بامداد، عددِ کلِ یکسان و روزهای متفاوت‌اند. به همین دلیل این برنامه زمان‌بندی، ترکیب و تکه‌تکه‌شدگی را جدا می‌سنجد نه اینکه یک عدد سرتیتر گزارش کند.",
        ar: "بمفرده لا — وهذه من أرسخ النتائج في هذا المجال. العدد نفسه من الدقائق قد يكون يوماً جيداً أو سيئاً حسب متى وقعت، وما الذي حلّت محله، وهل كانت مجزّأة. ساعتان من مكالمة مرئية مع من تحب وساعتان من التصفّح في الواحدة فجراً هما الإجمالي نفسه ويومان مختلفان. لهذا يقيس التطبيق التوقيت والتركيب والتجزّؤ منفصلة بدل تقرير رقم واحد بارز.",
        zh: "单独看的话，不是——这是该领域最稳健的发现之一。同样的分钟数，可能是好的一天也可能是糟的一天，取决于它发生在什么时候、替代了什么、以及是否碎片化。和你爱的人视频通话两小时，和凌晨一点刷两小时手机，总量相同却是完全不同的两天。这就是为什么这个应用分别测量时机、构成和碎片化，而不是报告一个头条数字。",
      },
    },
    edu_friction: {
      cat: "science", icon: "🧱",
      q: { en: "Why does the advice keep saying friction instead of willpower?", fa: "چرا توصیه‌ها مدام از اصطکاک می‌گویند نه از اراده؟", ar: "لماذا تتحدث النصائح عن الاحتكاك بدل قوة الإرادة؟", zh: "为什么建议总在说阻力，而不是意志力？" },
      a: {
        en: "Because willpower is a finite, daily-depleting resource and friction is a one-time decision that keeps working while you are tired. Moving an app off the home screen costs you one action and then defends you every evening without effort. Deciding each evening to resist it costs you an act of will every evening, on exactly the evenings you have least left. The strategies that survive a bad week are environmental, not motivational.",
        fa: "چون اراده منبعی محدود و روزانه‌تحلیل‌رونده است و اصطکاک یک تصمیمِ یک‌باره است که وقتی خسته‌ای هم کار می‌کند. برداشتن یک اپ از صفحه‌ی اصلی یک عمل از تو می‌گیرد و بعد هر شب بی‌زحمت ازت دفاع می‌کند. تصمیم‌گرفتن هر شب برای مقاومت، هر شب یک عملِ اراده می‌گیرد — دقیقاً همان شب‌هایی که کمترین باقی‌مانده را داری. راهبردهایی که یک هفته‌ی بد را دوام می‌آورند محیطی‌اند، نه انگیزشی.",
        ar: "لأن قوة الإرادة مورد محدود ينضب يومياً، والاحتكاك قرار لمرة واحدة يظل يعمل وأنت متعب. نقل تطبيق خارج الشاشة الرئيسية يكلّفك فعلاً واحداً ثم يدافع عنك كل مساء بلا جهد. أما أن تقرر كل مساء أن تقاوم فيكلّفك فعل إرادة كل مساء، في الأمسيات التي يتبقى لك فيها أقل ما يكون. الاستراتيجيات التي تصمد في أسبوع سيئ بيئية لا تحفيزية.",
        zh: "因为意志力是有限的、每天都会消耗的资源，而阻力是一次性的决定，在你疲惫时依然生效。把一个应用移出主屏幕，只花你一个动作，之后每晚都毫不费力地保护你。而每晚都决心抵抗它，则每晚都要消耗一次意志——恰恰是在你所剩最少的那些晚上。能熬过糟糕一周的策略是环境性的，不是激励性的。",
      },
    },
    edu_self_report: {
      cat: "science", icon: "📝",
      q: { en: "How reliable are the things I rate myself, like stress or focus?", fa: "چیزهایی که خودم امتیاز می‌دهم مثل استرس یا تمرکز چقدر قابل‌اعتمادند؟", ar: "ما مدى موثوقية ما أقيّمه بنفسي كالتوتر أو التركيز؟", zh: "像压力或专注这种我自己打的分，可靠吗？" },
      a: {
        en: "Noisier than the counted fields, and biased in a predictable direction: people rate the day they are having rather than the day they had, so a rough evening drags the whole day's rating down. That does not make them useless - they capture whether a pattern actually cost you anything, which no counter can see. Read them as a trend across days rather than as a precise reading on any single one.",
        fa: "پرنویزتر از فیلدهای شمارشی، و با سوگیری در جهتی قابل‌پیش‌بینی: آدم‌ها به روزی که دارند می‌گذرانند امتیاز می‌دهند نه به روزی که گذرانده‌اند، پس یک شبِ سخت امتیاز کلِ روز را پایین می‌کشد. این بی‌فایده‌شان نمی‌کند — آن‌ها این را می‌گیرند که آیا یک الگو واقعاً برایت هزینه داشته، چیزی که هیچ شمارنده‌ای نمی‌بیند. آن‌ها را به‌عنوان روند در طول روزها بخوان نه به‌عنوان قرائتی دقیق در یک روزِ واحد.",
        ar: "أكثر ضجيجاً من الحقول المعدودة، ومنحازة في اتجاه متوقَّع: يقيّم الناس اليوم الذي يعيشونه لا اليوم الذي عاشوه، فتسحب أمسية صعبة تقييم اليوم كله للأسفل. هذا لا يجعلها عديمة الفائدة — فهي تلتقط ما إذا كلّفك نمط ما شيئاً فعلاً، وهو ما لا يراه أي عدّاد. اقرأها كاتجاه عبر الأيام لا كقراءة دقيقة في يوم واحد.",
        zh: "比被计数的字段更嘈杂，而且偏差方向可预测：人们评的是「正在过的这一天」而不是「过完的这一天」，所以一个糟糕的傍晚会把整天的评分拉低。这并不意味着它们没用——它们捕捉的是某个模式究竟有没有让你付出代价，而这是任何计数器都看不到的。把它们当作跨天的趋势来读，而不是某一天的精确读数。",
      },
    },
    edu_recovery: {
      cat: "science", icon: "🔋",
      q: { en: "What does recovery actually mean here?", fa: "بازیابی اینجا واقعاً یعنی چه؟", ar: "ماذا يعني التعافي هنا فعلاً؟", zh: "这里说的「恢复」到底是什么意思？" },
      a: {
        en: "Not rest as absence of work, but the state where load stops accumulating. Scrolling on the sofa after a hard day is a break from working and often not recovery, because the attention system is still being asked to switch and respond. What tends to count: sleep, movement, and time where nothing is asking anything of you. This is why the app tracks fatigue separately from screen time - they can move in opposite directions on the same evening.",
        fa: "نه استراحت به معنای نبودِ کار، بلکه حالتی که بار دیگر انباشته نمی‌شود. اسکرول‌کردن روی کاناپه بعد از یک روز سخت، وقفه‌ای از کار است و اغلب بازیابی نیست، چون هنوز از سیستم توجه خواسته می‌شود جابه‌جا شود و پاسخ دهد. چیزی که معمولاً حساب می‌شود: خواب، تحرک، و زمانی که هیچ‌چیز چیزی از تو نمی‌خواهد. به همین دلیل برنامه خستگی را جدا از زمان صفحه دنبال می‌کند — می‌توانند در یک شب در جهت‌های مخالف حرکت کنند.",
        ar: "ليس الراحة بمعنى غياب العمل، بل الحالة التي يتوقف فيها تراكم الحِمل. التصفّح على الأريكة بعد يوم شاق استراحة من العمل وغالباً ليس تعافياً، لأن نظام الانتباه ما زال مطالَباً بالتبديل والاستجابة. ما يُحتسب عادةً: النوم والحركة والوقت الذي لا يطلب فيه شيء منك شيئاً. لهذا يتتبع التطبيق الإرهاق منفصلاً عن وقت الشاشة — فقد يتحركان في اتجاهين متعاكسين في المساء نفسه.",
        zh: "不是「没有工作」意义上的休息，而是负荷停止累积的状态。辛苦一天后瘫在沙发上刷手机，是从工作中抽身，但往往不是恢复，因为注意力系统仍被要求切换和回应。通常算数的是：睡眠、身体活动，以及没有任何东西要求你做什么的时间。这就是为什么应用把疲劳与屏幕时间分开追踪——它们在同一个晚上可能朝相反方向变化。",
      },
    },
    edu_comparison: {
      cat: "science", icon: "🪞",
      q: { en: "Why does social media make me feel worse even when nothing bad happens?", fa: "چرا شبکه‌های اجتماعی حالم را بد می‌کنند حتی وقتی اتفاق بدی نمی‌افتد؟", ar: "لماذا تسوء حالي مع وسائل التواصل حتى دون حدوث شيء سيئ؟", zh: "为什么就算没发生什么坏事，社交媒体也让我感觉更糟？" },
      a: {
        en: "Because a feed is a selection, and you are comparing your inside to other people's outsides. The mechanism is not the time spent but the sample you are shown: a feed weighted toward people doing well produces a steady, unremarkable sense of falling behind, with no single post you could point at. That is why muting a handful of accounts changes more than a time limit does - you are changing the sample, not the dose.",
        fa: "چون فید یک انتخاب است، و تو داری درونِ خودت را با بیرونِ بقیه مقایسه می‌کنی. مکانیزمش زمانِ صرف‌شده نیست بلکه نمونه‌ای است که به تو نشان داده می‌شود: فیدی که به سمت آدم‌هایی که خوب پیش می‌روند وزن دارد، حسی پیوسته و بی‌سروصدا از عقب‌ماندن می‌سازد، بدون اینکه بتوانی به یک پستِ مشخص اشاره کنی. به همین دلیل بی‌صدا کردن چند حساب بیشتر از یک محدودیت زمانی تغییر می‌دهد — داری نمونه را عوض می‌کنی، نه دوز را.",
        ar: "لأن الموجز انتقاء، وأنت تقارن داخلك بخارج الآخرين. الآلية ليست الوقت المنفَق بل العيّنة المعروضة عليك: موجز مرجّح نحو من تسير أمورهم جيداً يُنتج إحساساً ثابتاً وغير لافت بالتخلّف، دون منشور واحد يمكنك الإشارة إليه. لهذا يغيّر كتم حفنة حسابات أكثر مما يغيّر حدّ زمني — فأنت تغيّر العيّنة لا الجرعة.",
        zh: "因为信息流是一种筛选，而你在拿自己的内在和别人的外在比较。机制不在于花了多少时间，而在于你被展示的样本：一个偏向「过得不错的人」的信息流，会产生一种持续、平淡的落后感，却没有哪一条帖子是你能指出来的。这就是为什么静音几个账号比设时间限制更有效——你改变的是样本，不是剂量。",
      },
    },
    edu_phantom: {
      cat: "science", icon: "📳",
      q: { en: "Why do I feel my phone buzz when it did not?", fa: "چرا حس می‌کنم گوشی‌ام لرزید در حالی که نلرزیده؟", ar: "لماذا أشعر باهتزاز هاتفي وهو لم يهتز؟", zh: "为什么我会感觉手机震了，其实并没有？" },
      a: {
        en: "Because expectation shapes perception. When a buzz has reliably meant something, the nervous system starts predicting it, and a prediction with nothing behind it still feels like a sensation. It is extremely common and not a sign of anything wrong. It is, however, a decent proxy for how much of your attention is being held in reserve for the device - and it tends to fade within days of reducing notifications.",
        fa: "چون انتظار، ادراک را شکل می‌دهد. وقتی یک لرزش به‌طور مطمئن معنایی داشته، سیستم عصبی شروع به پیش‌بینی‌اش می‌کند، و پیش‌بینی‌ای که هیچ پشتش نیست هم هنوز شبیه یک حس است. بسیار رایج است و نشانه‌ی هیچ ایرادی نیست. اما شاخصِ نسبتاً خوبی است از اینکه چه مقدار از توجهت در ذخیره برای دستگاه نگه داشته می‌شود — و معمولاً ظرف چند روز از کم‌کردن اعلان‌ها محو می‌شود.",
        ar: "لأن التوقّع يشكّل الإدراك. حين يكون الاهتزاز قد عنى شيئاً بشكل موثوق، يبدأ الجهاز العصبي بتوقّعه، والتوقّع الذي لا شيء وراءه يظل يبدو كإحساس. إنه شائع جداً وليس علامة على خطب ما. لكنه مؤشر لا بأس به على مقدار انتباهك المحجوز للجهاز — ويميل إلى التلاشي خلال أيام من تقليل الإشعارات.",
        zh: "因为预期塑造知觉。当震动一直可靠地意味着什么时，神经系统就开始预测它，而一个背后什么都没有的预测，感觉起来依然像一次真实的触感。这非常常见，也不是任何问题的征兆。不过它是一个不错的代理指标，反映你有多少注意力被预留给了设备——而在减少通知之后，它往往几天内就会消退。",
      },
    },
    edu_one_change: {
      cat: "science", icon: "1️⃣",
      q: { en: "Should I change several habits at once or just one?", fa: "چند عادت را با هم عوض کنم یا فقط یکی؟", ar: "هل أغيّر عدة عادات دفعة واحدة أم واحدة فقط؟", zh: "我应该一次改几个习惯，还是只改一个？" },
      a: {
        en: "One, kept for a week, beats five attempted for two days - and it is not close. Multiple simultaneous changes compete for the same limited attention, and when the week goes badly you cannot tell which one was working. A single change also gives you a clean read: if the score moves, you know why. The plan in this app is built around that, which is why each day asks for a small number of specific things rather than a full overhaul.",
        fa: "یکی، که یک هفته نگهش داری، از پنج تا که دو روز امتحان شوند بهتر است — و فاصله‌شان کم هم نیست. تغییرهای هم‌زمان برای همان توجهِ محدود با هم رقابت می‌کنند، و وقتی هفته بد پیش برود نمی‌توانی بفهمی کدام داشت کار می‌کرد. یک تغییرِ واحد قرائت تمیزی هم به تو می‌دهد: اگر امتیاز جابه‌جا شد، می‌دانی چرا. برنامه‌ی این اپ حول همین ساخته شده، و به همین دلیل هر روز تعداد کمی چیزِ مشخص می‌خواهد نه یک بازسازیِ کامل.",
        ar: "واحدة يُحافَظ عليها أسبوعاً تتفوق على خمس تُجرَّب يومين — والفارق ليس ضئيلاً. التغييرات المتزامنة تتنافس على الانتباه المحدود نفسه، وحين يسوء الأسبوع لا تعرف أيها كان ينجح. التغيير الواحد يمنحك أيضاً قراءة نظيفة: إن تحركت الدرجة عرفت السبب. وخطة هذا التطبيق مبنية على ذلك، ولهذا يطلب كل يوم عدداً صغيراً من الأمور المحددة لا إصلاحاً شاملاً.",
        zh: "一个，坚持一周，胜过五个只试两天——而且差距不小。同时进行的多项改变会争夺同样有限的注意力，而当这一周不顺时，你分不清是哪一个在起作用。单一改变还能给你一个干净的读数：如果分数动了，你知道为什么。这个应用的计划正是围绕这一点设计的，所以每天只要求少数几件具体的事，而不是全面推翻重来。",
      },
    },
  };

  /** Menu entries for every lesson, in all four languages. */
  function menuItems() {
    return Object.keys(TOPICS).map((id) => {
      const t = TOPICS[id];
      const item = { id, cat: t.cat, need: [], icon: t.icon };
      ['en', 'fa', 'ar', 'zh'].forEach((lang) => { item[lang] = t.q[lang]; });
      return item;
    });
  }

  function answer(id) {
    const t = TOPICS[id];
    return t ? pick(t.a) : '';
  }

  function has(id) { return !!TOPICS[id]; }

  function ids() { return Object.keys(TOPICS); }

  window.DWCurriculum = { TOPICS, menuItems, answer, has, ids };
})();
