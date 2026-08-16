/*
  DWAboutRoadmap — the animated map of what this project actually is.

  Fourteen stations along one drawn line: what goes in, what the models
  do, what the app can honestly say about the result, and what the user
  gets out. It exists because "we built an ML wellness app" is a
  sentence nobody can check, and a reviewer with four minutes needs the
  whole chain in front of them at once.

  Every claim on this map is traceable to the repository. The numbers
  are the measured ones (artifacts/metrics.json,
  artifacts/leakage_verification_report.json, the shipped registries) -
  the same figures README.md carries, not a friendlier version of them.
  Two of them are deliberately about what the project REFUSED to claim,
  because a map that only shows the good parts is marketing and a
  reviewer can tell.

  Motion
  -------
  Two layers, and they are not the same kind of thing.

  The SVG layer is the map itself: a real path measured from where the
  markers actually land, rebuilt on resize, so it follows the layout
  instead of being a hand-drawn guess that breaks at the first
  breakpoint. Scroll drives `stroke-dashoffset`; a comet rides the
  drawn end via getPointAtLength; each station lights as the line
  reaches it.

  The CANVAS layer underneath is the film: data flowing down the same
  measured path, tinted by the phase it is passing through, with a
  burst at each station as the line arrives. It is drawn rather than
  recorded - a video file would be a fixed size, a fixed resolution, a
  fixed language and about ten megabytes, and it could not follow a
  path that is measured at runtime. Sampling the real path is what lets
  the two layers stay locked together at any width, in either
  direction, on any screen.

  The film costs one rAF loop, and only while the section is on screen:
  an IntersectionObserver stops it the moment the map scrolls away.

  Under reduced motion the line is drawn complete, every station is
  already lit, the comet never appears and the film never starts. Nothing on this page is ever
  withheld waiting for an animation - that rule is from
  assets/js/motion.js and it applies here too.

  RTL: the list flips through CSS alone, and the spine is measured from
  the flipped positions, so nothing here needs to know which way the
  page runs.
*/
(function () {
  const LANGS = ['en', 'fa', 'ar', 'zh'];

  function lang() {
    const l = window.DWI18n && window.DWI18n.get ? window.DWI18n.get() : 'en';
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }

  function pick(bundle) {
    if (!bundle) return '';
    return bundle[lang()] || bundle.en || '';
  }

  const HEAD = {
    eyebrow: {
      en: 'The whole chain, end to end',
      fa: 'کل زنجیره، از ابتدا تا انتها',
      ar: 'السلسلة كاملة، من أولها إلى آخرها',
      zh: '完整链条，从头到尾',
    },
    title: {
      en: 'How a logged day becomes something you can act on',
      fa: 'یک روزِ ثبت‌شده چطور به چیزی تبدیل می‌شود که بشود رویش عمل کرد',
      ar: 'كيف يتحوّل يوم مُسجَّل إلى شيء يمكنك التصرّف بناءً عليه',
      zh: '记录下来的一天，如何变成你能据此行动的东西',
    },
    lede: {
      en: 'Fourteen stops. Every number below is measured in this repository — including the two stops about what the project decided it could not claim.',
      fa: 'چهارده ایستگاه. هر عددی که پایین می‌بینی در همین مخزن اندازه‌گیری شده — از جمله آن دو ایستگاهی که درباره‌ی چیزهایی‌اند که پروژه تصمیم گرفت ادعایشان نکند.',
      ar: 'أربع عشرة محطة. كل رقم في الأسفل مُقاس داخل هذا المستودع — بما في ذلك المحطتان اللتان تتحدثان عمّا قرّر المشروع أنه لا يستطيع ادّعاءه.',
      zh: '十四站。下面每一个数字都在本仓库中实测得出——包括那两站，讲的是这个项目认为自己不能声称的东西。',
    },
  };

  const PHASES = {
    input: {
      en: 'What goes in', fa: 'آنچه وارد می‌شود',
      ar: 'ما يدخل', zh: '输入什么',
    },
    model: {
      en: 'What the model does', fa: 'کاری که مدل می‌کند',
      ar: 'ما يفعله النموذج', zh: '模型做什么',
    },
    meaning: {
      en: 'What it may honestly say', fa: 'آنچه صادقانه می‌تواند بگوید',
      ar: 'ما يمكنه قوله بصدق', zh: '它能诚实地说什么',
    },
    action: {
      en: 'What you get out', fa: 'آنچه بیرون می‌آید',
      ar: 'ما تحصل عليه', zh: '你得到什么',
    },
  };

  /* Each station: phase, an icon key, title/body in four languages, and
     one piece of PROOF - a measured number with the file it comes from,
     or the file itself when the point is a mechanism rather than a
     figure. `num` is set only where a count-up reads as anything; a
     ratio nobody knows the scale of just flickers. */
  const STATIONS = [
    {
      phase: 'input', icon: 'problem',
      title: {
        en: 'The gap this starts from',
        fa: 'شکافی که کار از آن شروع می‌شود',
        ar: 'الفجوة التي ينطلق منها كل شيء',
        zh: '一切从这个缺口开始',
      },
      body: {
        en: 'Six hours and 140 pickups is a measurement, not an answer. It never says whether that was bad for you, which part of it mattered, or what to change.',
        fa: 'شش ساعت و ۱۴۰ بار برداشتن گوشی یک اندازه‌گیری است، نه یک پاسخ. هیچ‌وقت نمی‌گوید این برای تو بد بود یا نه، کدام بخشش مهم بود، و چه چیزی را باید عوض کنی.',
        ar: 'ست ساعات و ١٤٠ مرة التقاط للهاتف: هذا قياس وليس إجابة. لا يقول أبدًا هل كان ذلك سيئًا لك، وأي جزء منه كان مهمًا، وما الذي ينبغي تغييره.',
        zh: '六小时、140 次拿起手机，这是测量，不是答案。它从不告诉你这对你是否有害、哪一部分才重要、该改什么。',
      },
      proof: {
        value: '2', num: 2,
        label: {
          en: 'horizons, kept separate: today’s score, next week’s class',
          fa: 'افق زمانی، جدا از هم: امتیاز امروز، دسته‌ی هفته‌ی بعد',
          ar: 'أفقان منفصلان: درجة اليوم، وفئة الأسبوع القادم',
          zh: '两个时间尺度，彼此分开：今天的分数、下周的类别',
        },
      },
    },
    {
      phase: 'input', icon: 'form',
      title: {
        en: 'A day, in 53 answers',
        fa: 'یک روز، در ۵۳ پاسخ',
        ar: 'يوم واحد في ٥٣ إجابة',
        zh: '一天，53 个回答',
      },
      body: {
        en: 'Minutes by category, night and pre-sleep screen time, notifications, pickups, sessions, sleep, mood, stress, focus, activity. Or a CSV of many days at once.',
        fa: 'دقیقه‌ها به تفکیک دسته، زمان صفحه در شب و پیش از خواب، اعلان‌ها، برداشتن گوشی، جلسات، خواب، خلق، استرس، تمرکز و فعالیت. یا یک فایل CSV برای چند روز یک‌جا.',
        ar: 'الدقائق حسب الفئة، وقت الشاشة ليلًا وقبل النوم، الإشعارات، مرات الالتقاط، الجلسات، النوم، المزاج، التوتر، التركيز والنشاط. أو ملف CSV لعدة أيام دفعة واحدة.',
        zh: '按类别的分钟数、夜间与睡前屏幕时间、通知、拿起次数、会话、睡眠、情绪、压力、专注、活动。也可以用 CSV 一次导入多天。',
      },
      proof: {
        value: '53', num: 53,
        label: {
          en: 'fields in core/feature_schema.py, each with its own bounds',
          fa: 'فیلد در core/feature_schema.py، هرکدام با محدوده‌ی خودش',
          ar: 'حقلًا في core/feature_schema.py، لكل منها حدوده',
          zh: '个字段，定义在 core/feature_schema.py，各有取值范围',
        },
      },
    },
    {
      phase: 'input', icon: 'derive',
      title: {
        en: 'Checked, then expanded',
        fa: 'اول بررسی، بعد گسترش',
        ar: 'تُفحص أولًا ثم تُوسَّع',
        zh: '先校验，再展开',
      },
      body: {
        en: 'Every field is bounds-checked and reported per field, never silently coerced. Then ratios, densities, an EWMA baseline and a fragmentation index are derived — by the same function at training time and at prediction time, so the two cannot drift apart.',
        fa: 'هر فیلد در برابر محدوده‌اش بررسی می‌شود و خطا برای همان فیلد گزارش می‌شود؛ هیچ‌وقت بی‌صدا اصلاح نمی‌شود. بعد نسبت‌ها، چگالی‌ها، یک خط پایه‌ی EWMA و شاخص تکه‌تکه‌شدن ساخته می‌شوند — با همان تابعی که هنگام آموزش استفاده شده، تا این دو هیچ‌وقت از هم فاصله نگیرند.',
        ar: 'كل حقل يُفحص ضمن حدوده ويُبلَّغ عنه على حدة، ولا يُصحَّح بصمت. ثم تُشتق النسب والكثافات وخط أساس EWMA ومؤشر التجزؤ — بالدالة نفسها المستخدمة أثناء التدريب، حتى لا يفترق الاثنان.',
        zh: '每个字段都按范围校验并逐字段报错，绝不静默修正。随后派生出比率、密度、EWMA 基线和碎片化指数——训练与推理调用同一个函数，二者不会走偏。',
      },
      proof: {
        value: '185', num: 185,
        label: {
          en: 'features reach the regressor after derivation',
          fa: 'ویژگی پس از مشتق‌گیری به مدل رگرسیون می‌رسد',
          ar: 'خاصية تصل إلى نموذج الانحدار بعد الاشتقاق',
          zh: '个特征在派生后进入回归模型',
        },
      },
    },
    {
      phase: 'model', icon: 'score',
      title: {
        en: 'Today’s score',
        fa: 'امتیاز امروز',
        ar: 'درجة اليوم',
        zh: '今天的分数',
      },
      body: {
        en: 'A HistGradientBoostingRegressor returns 0–100 for the day you logged. It was chosen over Logistic Regression and Random Forest baselines by a score that penalises the train/validation gap.',
        fa: 'یک HistGradientBoostingRegressor برای روزی که ثبت کرده‌ای عددی بین ۰ تا ۱۰۰ می‌دهد. این مدل در برابر رگرسیون لجستیک و جنگل تصادفی انتخاب شده، با معیاری که فاصله‌ی آموزش/اعتبارسنجی را جریمه می‌کند.',
        ar: 'يعيد HistGradientBoostingRegressor قيمة بين ٠ و١٠٠ لليوم الذي سجّلته. اختير على حساب الانحدار اللوجستي والغابة العشوائية بمعيار يعاقب الفجوة بين التدريب والتحقق.',
        zh: 'HistGradientBoostingRegressor 为你记录的这一天给出 0–100 的分数。它是在惩罚训练/验证差距的评分下，胜过逻辑回归与随机森林基线而入选的。',
      },
      proof: {
        value: '0.992', num: 0.992, decimals: 3,
        label: {
          en: 'R² on the held-out test split (MAE 0.50)',
          fa: 'R² روی بخش آزمون کنارگذاشته‌شده (MAE ۰٫۵۰)',
          ar: 'R² على مجموعة الاختبار المعزولة (MAE ٠٫٥٠)',
          zh: '留出测试集上的 R²（MAE 0.50）',
        },
      },
    },
    {
      phase: 'model', icon: 'forecast',
      title: {
        en: 'Next week’s class',
        fa: 'دسته‌ی هفته‌ی بعد',
        ar: 'فئة الأسبوع القادم',
        zh: '下周的类别',
      },
      body: {
        en: 'A separate classifier predicts Healthy / Moderate / At Risk seven days ahead. The app labels both horizons everywhere they appear, because showing them together unlabelled reads as a forecast nobody made.',
        fa: 'یک دسته‌بند جداگانه، هفت روز جلوتر را «سالم / متوسط / در معرض خطر» پیش‌بینی می‌کند. اپ هرجا این دو را نشان می‌دهد افقشان را هم می‌نویسد، چون کنار هم گذاشتنشان بدون برچسب، پیش‌بینی‌ای را می‌رساند که هیچ‌کس نکرده.',
        ar: 'مصنّف منفصل يتنبأ بـ «سليم / متوسط / في خطر» بعد سبعة أيام. يوسم التطبيق كلا الأفقين أينما ظهرا، لأن عرضهما معًا دون وسم يُقرأ كتنبؤ لم يقله أحد.',
        zh: '另一个分类器预测七天后的「健康／中等／有风险」。应用在两者出现的每一处都标注时间尺度——不标注地并排显示，会被读成谁也没做过的预测。',
      },
      proof: {
        value: '0.977', num: 0.977, decimals: 3,
        label: {
          en: 'test accuracy (ROC-AUC 0.998)',
          fa: 'دقت روی آزمون (ROC-AUC ۰٫۹۹۸)',
          ar: 'دقة الاختبار (ROC-AUC ٠٫٩٩٨)',
          zh: '测试准确率（ROC-AUC 0.998）',
        },
      },
    },
    {
      phase: 'model', icon: 'split',
      title: {
        en: 'Nobody appears on both sides',
        fa: 'هیچ‌کس دو طرف تقسیم نیست',
        ar: 'لا أحد يظهر على الجانبين',
        zh: '没有人同时出现在两边',
      },
      body: {
        en: 'The split is grouped, not random: rows are grouped by a ten-column respondent key so the same person cannot land in both training and test. Verified, not assumed.',
        fa: 'تقسیم داده گروهی است، نه تصادفی: سطرها با یک کلید ده‌ستونیِ پاسخ‌دهنده گروه‌بندی می‌شوند تا یک نفر نتواند هم در آموزش باشد هم در آزمون. این تأیید شده، نه فرض‌شده.',
        ar: 'التقسيم مجموعاتي لا عشوائي: تُجمَّع الصفوف بمفتاح مستجيب من عشرة أعمدة كي لا يقع الشخص نفسه في التدريب والاختبار معًا. مُتحقَّق منه، لا مفترض.',
        zh: '数据划分是按组而非随机：以十列构成的受访者键分组，同一个人不会同时落在训练集和测试集里。这是验证过的，不是假设的。',
      },
      proof: {
        value: '0', num: 0,
        label: {
          en: 'group overlap across all three splits (104,469 rows, 3,404 groups)',
          fa: 'هم‌پوشانی گروهی میان هر سه بخش (۱۰۴٬۴۶۹ سطر، ۳٬۴۰۴ گروه)',
          ar: 'تداخل بين المجموعات عبر الأقسام الثلاثة (١٠٤٬٤٦٩ صفًا، ٣٬٤٠٤ مجموعة)',
          zh: '三个数据集之间的分组重叠（104,469 行，3,404 组）',
        },
      },
    },
    {
      phase: 'meaning', icon: 'shap',
      title: {
        en: 'Why this number',
        fa: 'چرا این عدد',
        ar: 'لماذا هذا الرقم',
        zh: '为什么是这个数字',
      },
      body: {
        en: 'SHAP runs on every prediction through the fitted pipeline and returns per-feature contributions with direction and size — from this exact prediction, not a canned summary of what usually matters.',
        fa: 'SHAP روی هر پیش‌بینی و از مسیر همان پایپ‌لاین اجرا می‌شود و سهم هر ویژگی را با جهت و اندازه برمی‌گرداند — از همین پیش‌بینی، نه یک خلاصه‌ی از پیش آماده از «معمولاً چه چیزی مهم است».',
        ar: 'يعمل SHAP على كل تنبؤ عبر خط المعالجة نفسه ويعيد مساهمة كل خاصية باتجاهها وحجمها — من هذا التنبؤ بالذات، لا ملخصًا جاهزًا لما يهم عادة.',
        zh: 'SHAP 在同一条流水线上对每一次预测运行，返回每个特征的贡献方向与大小——来自这一次预测本身，而不是「通常什么重要」的套话。',
      },
      proof: {
        value: 'services/ml/shap_service.py',
        label: {
          en: 'the top factors, and the largest downward pull named in plain words',
          fa: 'مهم‌ترین عوامل، و بزرگ‌ترین عامل کاهنده که با زبان ساده نامیده می‌شود',
          ar: 'أهم العوامل، مع تسمية أكبر عامل خافض بلغة واضحة',
          zh: '最主要的因素，并用平实语言点名影响最大的下拉因素',
        },
      },
    },
    {
      phase: 'meaning', icon: 'interval',
      title: {
        en: 'How sure, without theatre',
        fa: 'چقدر مطمئن، بدون نمایش',
        ar: 'مدى اليقين، بلا استعراض',
        zh: '有多确定，不做表演',
      },
      body: {
        en: 'Split conformal prediction wraps the trained models — a residual quantile for the regressor, a nonconformity quantile for the classifier — giving an interval with a real coverage guarantee instead of a softmax percentage dressed up as confidence.',
        fa: 'پیش‌بینی conformal تقسیمی دور مدل‌های آموزش‌دیده پیچیده می‌شود — چندکِ باقی‌مانده برای رگرسیون، چندکِ ناهم‌خوانی برای دسته‌بند — و یک بازه با ضمانت پوشش واقعی می‌دهد، نه یک درصدِ softmax که لباس اطمینان پوشیده باشد.',
        ar: 'يلتف التنبؤ الـ conformal المقسّم حول النماذج المدرَّبة — كمّي البواقي للانحدار وكمّي عدم المطابقة للمصنّف — فيعطي فترة بضمان تغطية حقيقي بدل نسبة softmax متنكّرة في هيئة ثقة.',
        zh: '分裂式 conformal 预测包住训练好的模型——回归用残差分位数，分类用非一致性分位数——给出有真实覆盖保证的区间，而不是把 softmax 百分比装扮成置信度。',
      },
      proof: {
        value: 'services/ml/uncertainty_service.py',
        label: {
          en: 'an interval and a plain-language label — never a bare confidence number',
          fa: 'یک بازه و یک برچسب ساده — هیچ‌وقت یک عدد خالیِ اطمینان',
          ar: 'فترة ووسم بلغة بسيطة — لا رقم ثقة مجرّد',
          zh: '一个区间加一句平实说明——绝不给一个孤零零的置信数字',
        },
      },
    },
    {
      phase: 'meaning', icon: 'refuse',
      title: {
        en: 'What was trained and not shipped',
        fa: 'چیزی که آموزش دید و ارسال نشد',
        ar: 'ما دُرِّب ولم يُشحَن',
        zh: '训练了却没有上线的东西',
      },
      body: {
        en: 'A regressor for the seven-day score was built and failed its own baseline check, so it is not loaded. The seven-day figure is derived from the classifier’s probabilities and presented as a band — because that is what it is. The training data is synthetic, and every metric here says so.',
        fa: 'یک مدل رگرسیون برای امتیاز هفت‌روزه ساخته شد و در آزمون پایه‌ی خودش رد شد، پس بارگذاری نمی‌شود. عدد هفت‌روزه از احتمالات دسته‌بند به دست می‌آید و به‌شکل یک بازه نشان داده می‌شود — چون واقعاً همین است. داده‌ی آموزشی مصنوعی است و همه‌ی سنجه‌های اینجا این را می‌گویند.',
        ar: 'بُني نموذج انحدار للدرجة السباعية ففشل في اختبار خط الأساس الخاص به، لذا لا يُحمَّل. الرقم السباعي مشتق من احتمالات المصنّف ويُعرض كنطاق — لأنه كذلك فعلًا. بيانات التدريب اصطناعية، وكل مقياس هنا يقول ذلك.',
        zh: '为七天分数训练过一个回归模型，它没通过自己的基线检验，因此不加载。七天的数字由分类器概率推导，并以区间呈现——因为它本来就是区间。训练数据是合成的，这里每个指标都如实标明。',
      },
      proof: {
        value: 'beats_baseline: false',
        label: {
          en: 'artifacts/metrics_future_regression.json — the refusal is in the repo',
          fa: 'artifacts/metrics_future_regression.json — خودِ این ردکردن در مخزن هست',
          ar: 'artifacts/metrics_future_regression.json — الرفض نفسه موجود في المستودع',
          zh: 'artifacts/metrics_future_regression.json——这次「不上线」记录在仓库里',
        },
      },
    },
    {
      phase: 'meaning', icon: 'personal',
      title: {
        en: 'A model of you alone',
        fa: 'مدلی فقط از خودِ تو',
        ar: 'نموذج لك وحدك',
        zh: '只属于你的模型',
      },
      body: {
        en: 'Separately from the shipped model, a ridge regression is fitted on YOUR days only, to answer which of your own signals actually move your score. It reports a leave-one-out R² beside the in-sample one, and refuses to fit anything at all below eight days.',
        fa: 'جدا از مدلِ ارسالی، یک رگرسیون ریج فقط روی روزهای خودت برازش می‌شود تا بگوید کدام سیگنالِ خودت واقعاً امتیازت را جابه‌جا می‌کند. کنار R² روی همان داده، R² با حذف یکی هم گزارش می‌شود، و زیر هشت روز اصلاً چیزی برازش نمی‌کند.',
        ar: 'بمعزل عن النموذج المشحون، يُلائم انحدار ريدج على أيامك أنت فقط ليجيب: أي إشاراتك تحرّك درجتك فعلًا. ويُبلّغ عن R² بحذف واحد إلى جانب R² داخل العينة، ويرفض الملاءمة أصلًا دون ثمانية أيام.',
        zh: '与随应用发布的模型分开，另有一个岭回归只在你自己的日子上拟合，回答你的哪些信号真正推动了分数。它在样本内 R² 旁同时给出留一法 R²，并且不足八天时干脆不拟合。',
      },
      proof: {
        value: 'services/insight/personal_model_service.py',
        label: {
          en: 'leave-one-out R² printed beside the in-sample one, because that one is optimistic',
          fa: 'R² با حذف یکی کنار R² روی همان داده چاپ می‌شود، چون دومی خوش‌بینانه است',
          ar: 'يُطبع R² بحذف واحد بجانب R² داخل العينة، لأن الأخير متفائل',
          zh: '留一法 R² 与样本内 R² 并列显示，因为后者过于乐观',
        },
      },
    },
    {
      phase: 'action', icon: 'advice',
      title: {
        en: 'Advice from your own weakest signals',
        fa: 'توصیه از ضعیف‌ترین سیگنال‌های خودت',
        ar: 'نصائح من أضعف إشاراتك أنت',
        zh: '建议来自你自己最弱的信号',
      },
      body: {
        en: 'Recommendations are keyed to the signals that actually moved your score, each with a success metric you can check, and each category can be switched off.',
        fa: 'توصیه‌ها به همان سیگنال‌هایی وصل‌اند که واقعاً امتیازت را جابه‌جا کرده‌اند، هرکدام با معیار موفقیتی که می‌شود بررسی‌اش کرد، و هر دسته را می‌شود خاموش کرد.',
        ar: 'التوصيات مرتبطة بالإشارات التي حرّكت درجتك فعلًا، لكل منها مقياس نجاح يمكنك التحقق منه، ويمكن إيقاف أي فئة منها.',
        zh: '建议对应的是真正推动你分数的那些信号，每条都带一个可核对的成功指标，而且每一类都可以关掉。',
      },
      proof: {
        value: '29', num: 29,
        label: {
          en: 'entries in config/recommendation_registry.py, direction-aware',
          fa: 'مدخل در config/recommendation_registry.py، آگاه به جهت تغییر',
          ar: 'مدخلًا في config/recommendation_registry.py، مراعية للاتجاه',
          zh: '条目，位于 config/recommendation_registry.py，区分变化方向',
        },
      },
    },
    {
      phase: 'action', icon: 'whatif',
      title: {
        en: 'Change one thing and re-run it',
        fa: 'یک چیز را عوض کن و دوباره اجرا کن',
        ar: 'غيّر شيئًا واحدًا وأعد التشغيل',
        zh: '改一件事，再跑一次',
      },
      body: {
        en: 'What-if sweeps a single habit or goal-seeks a target; future paths re-score named scenarios. Both go through the real trained model, so nothing on those screens is an estimate of an estimate.',
        fa: 'بخش «چه می‌شد اگر» یک عادت را جاروب می‌کند یا به‌دنبال رسیدن به یک هدف می‌گردد؛ مسیرهای آینده سناریوهای نام‌دار را دوباره امتیاز می‌دهند. هر دو از مدل واقعیِ آموزش‌دیده رد می‌شوند، پس هیچ‌چیز در آن صفحه‌ها تخمینِ یک تخمین نیست.',
        ar: 'يمسح «ماذا لو» عادة واحدة أو يبحث عن قيمة تحقق هدفًا؛ ومسارات المستقبل تعيد تقييم سيناريوهات مسمّاة. كلاهما يمر عبر النموذج المدرَّب الحقيقي، فلا شيء في تلك الشاشات تقدير لتقدير.',
        zh: '「假如」会扫描单个习惯或反解目标值；未来路径会重新给具名情景打分。两者都走真实的训练模型，所以那些界面上没有「估计的估计」。',
      },
      proof: {
        value: 'services/insight/advanced_whatif_service.py',
        label: {
          en: 'the same predict() the check-in uses',
          fa: 'همان predict() که خودِ ثبت روزانه استفاده می‌کند',
          ar: 'نفس predict() الذي يستخدمه تسجيل اليوم',
          zh: '与每日记录使用的是同一个 predict()',
        },
      },
    },
    {
      phase: 'action', icon: 'book',
      title: {
        en: 'And one page a day that is only yours',
        fa: 'و روزی یک صفحه که فقط مالِ توست',
        ar: 'وصفحة واحدة كل يوم لك وحدك',
        zh: '还有每天一页，只属于你',
      },
      body: {
        en: 'The book at the bottom of this page holds one written page per day, in your own words. It is saved to your account, it is never fed to any model, it never touches your score, and it leaves with you as a PDF.',
        fa: 'کتابِ پایینِ همین صفحه، روزی یک صفحه‌ی نوشته‌شده به قلم خودت را نگه می‌دارد. روی حساب خودت ذخیره می‌شود، هرگز خوراک هیچ مدلی نمی‌شود، هیچ اثری روی امتیازت ندارد، و به‌شکل یک PDF با تو می‌آید.',
        ar: 'الكتاب في أسفل هذه الصفحة يحتفظ بصفحة مكتوبة لكل يوم، بكلماتك أنت. يُحفظ في حسابك، ولا يُغذّى لأي نموذج، ولا يمسّ درجتك، ويغادر معك كملف PDF.',
        zh: '本页底部的那本书，每天保存一页你自己写下的文字。它保存在你的账号里，绝不喂给任何模型，也不影响你的分数，并且可以作为 PDF 随你带走。',
      },
      proof: {
        value: '/journal.pdf',
        label: {
          en: 'the whole book, typeset in your language, Persian and Arabic shaped properly',
          fa: 'کل کتاب، حروف‌چینی‌شده به زبان خودت، با شکل‌دهی درست فارسی و عربی',
          ar: 'الكتاب كاملًا، منضّدًا بلغتك، مع تشكيل صحيح للعربية والفارسية',
          zh: '整本书，按你的语言排版，波斯语与阿拉伯语正确塑形',
        },
      },
    },
    {
      phase: 'action', icon: 'yours',
      title: {
        en: 'It stays yours',
        fa: 'مال خودت می‌ماند',
        ar: 'يبقى ملكك',
        zh: '它一直是你的',
      },
      body: {
        en: 'History is keyed to your account and every read is scoped to it. You can export everything stored about you, or delete the account and its history — including the pages you write in the book below.',
        fa: 'تاریخچه به حساب خودت گره خورده و هر خواندن به همان حساب محدود است. می‌توانی هرچه درباره‌ات ذخیره شده را بیرون بکشی، یا حساب و تاریخچه‌اش را پاک کنی — از جمله صفحه‌هایی که در کتابِ پایینِ همین صفحه می‌نویسی.',
        ar: 'السجل مرتبط بحسابك وكل قراءة محصورة به. يمكنك تصدير كل ما هو مخزَّن عنك، أو حذف الحساب وسجله — بما في ذلك الصفحات التي تكتبها في الكتاب أدناه.',
        zh: '历史记录绑定在你的账号上，每次读取都限定在这个账号内。你可以导出关于你的全部存储内容，也可以删除账号及其历史——包括你在下面这本书里写的每一页。',
      },
      proof: {
        value: '/privacy/export · /privacy/me',
        label: {
          en: 'export everything, or delete it — storage/ is never shipped',
          fa: 'همه‌چیز را بگیر، یا پاکش کن — پوشه‌ی storage/ هیچ‌وقت ارسال نمی‌شود',
          ar: 'صدّر كل شيء أو احذفه — مجلد storage/ لا يُشحن أبدًا',
          zh: '全部导出，或者全部删除——storage/ 目录从不随项目分发',
        },
      },
    },
  ];

  /* Line-art icons, drawn rather than pulled from a font so they carry
     the same stroke weight as the rest of the app's nav icons. */
  const ICONS = {
    problem: '<path d="M4 19h16"/><path d="M6 19V9"/><path d="M11 19V5"/><path d="M16 19v-7"/><path d="M3.5 5.5 8 9"/>',
    form: '<rect x="5" y="3.5" width="14" height="17" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    derive: '<path d="M5 6h6"/><path d="M8 6v12"/><path d="M5 18h6"/><circle cx="17" cy="9" r="2.2"/><circle cx="17" cy="16" r="2.2"/><path d="M11 8.5h3.8M11 15.5h3.8"/>',
    score: '<circle cx="12" cy="12" r="8"/><path d="M12 12 15.5 8.5"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/>',
    forecast: '<path d="M3 17.5 8 11l4 3.5 5-7.5"/><path d="M17 7h3.5v3.5"/><path d="M3 20.5h18" opacity=".4"/>',
    split: '<path d="M12 4v5"/><path d="M12 9 6.5 13v6"/><path d="M12 9l5.5 4v6"/><circle cx="12" cy="3.2" r="1.6"/><circle cx="6.5" cy="20" r="1.6"/><circle cx="17.5" cy="20" r="1.6"/>',
    shap: '<path d="M12 3.5v17"/><rect x="4" y="6" width="6" height="3" rx="1"/><rect x="14" y="11" width="6" height="3" rx="1"/><rect x="6.5" y="16" width="3.5" height="3" rx="1"/>',
    interval: '<path d="M5 12h14"/><path d="M5 8.5v7M19 8.5v7"/><circle cx="12" cy="12" r="2.2"/>',
    refuse: '<circle cx="12" cy="12" r="8"/><path d="m8.5 8.5 7 7"/>',
    advice: '<path d="M12 4a6 6 0 0 0-3.5 10.9V17h7v-2.1A6 6 0 0 0 12 4Z"/><path d="M10 20h4"/>',
    whatif: '<path d="M10 3h4"/><path d="M10.5 3v5.2L6 17a2 2 0 0 0 1.8 3h8.4A2 2 0 0 0 18 17l-4.5-8.8V3"/><path d="M8.5 14h7"/>',
    personal: '<circle cx="12" cy="8" r="3.2"/><path d="M5.5 20c1-3.2 3.5-5 6.5-5s5.5 1.8 6.5 5"/><path d="M3.5 12.5 6 10l2 2 2.5-3" opacity=".6"/>',
    book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19v15H6.5A2.5 2.5 0 0 0 4 20.5Z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H19v3H6.5"/><path d="M8.5 8h7M8.5 11.5h5"/>',
    yours: '<path d="M12 3 5 6v5.5c0 4.3 2.9 7.6 7 8.5 4.1-.9 7-4.2 7-8.5V6l-7-3Z"/><path d="M12 11v4"/><circle cx="12" cy="8.6" r="0.9" fill="currentColor" stroke="none"/>',
  };

  function esc(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function nodeHtml(station, index) {
    const n = String(index + 1).padStart(2, '0');
    const proof = station.proof || {};
    const numeric = typeof proof.num === 'number';
    return ''
      + `<li class="rm-node" data-phase="${esc(station.phase)}" data-index="${index}">`
      + '<div class="rm-marker" aria-hidden="true">'
      + `<svg class="rm-icon" viewBox="0 0 24 24">${ICONS[station.icon] || ICONS.problem}</svg>`
      + `<span class="rm-num">${n}</span>`
      + '</div>'
      + '<article class="rm-card">'
      + `<p class="rm-phase">${esc(pick(PHASES[station.phase]))}</p>`
      + `<h3 class="rm-title">${esc(pick(station.title))}</h3>`
      + `<p class="rm-body">${esc(pick(station.body))}</p>`
      + '<p class="rm-proof">'
      + `<span class="rm-proof-value"${numeric ? ` data-count="${proof.num}" data-decimals="${proof.decimals || 0}"` : ''}>`
      + `${esc(numeric ? (proof.decimals ? (0).toFixed(proof.decimals) : '0') : proof.value)}</span>`
      + `<span class="rm-proof-label">${esc(pick(proof.label))}</span>`
      + '</p>'
      + '</article>'
      + '</li>';
  }

  function render(root) {
    root.innerHTML = ''
      + '<header class="rm-head reveal">'
      + `<p class="rm-eyebrow">${esc(pick(HEAD.eyebrow))}</p>`
      + `<h2 class="rm-heading text-gradient">${esc(pick(HEAD.title))}</h2>`
      + `<p class="rm-lede">${esc(pick(HEAD.lede))}</p>`
      + '</header>'
      + '<div class="rm-track">'
      + '<canvas class="rm-film" aria-hidden="true"></canvas>'
      + '<svg class="rm-spine" aria-hidden="true" preserveAspectRatio="none">'
      + '<defs><linearGradient id="rmSpineGrad" x1="0" y1="0" x2="0" y2="1">'
      + '<stop offset="0%" stop-color="var(--neon-cyan)"/>'
      + '<stop offset="55%" stop-color="var(--neon-blue)"/>'
      + '<stop offset="100%" stop-color="var(--neon-purple)"/>'
      + '</linearGradient></defs>'
      + '<path class="rm-spine-bg" fill="none"/>'
      + '<path class="rm-spine-live" fill="none" stroke="url(#rmSpineGrad)"/>'
      + '<circle class="rm-comet" r="6" fill="var(--neon-cyan)"/>'
      + '</svg>'
      + `<ol class="rm-list">${STATIONS.map(nodeHtml).join('')}</ol>`
      + '</div>';
  }

  /* ---- the drawn line ---------------------------------------------
     Measured from where the markers actually are. A hardcoded path
     would be wrong at the first breakpoint, in RTL, and in any language
     whose cards are taller - which is all of them. */
  function buildPath(track, markers) {
    const box = track.getBoundingClientRect();
    const points = markers.map((m) => {
      const r = m.getBoundingClientRect();
      return {
        x: r.left - box.left + r.width / 2,
        y: r.top - box.top + r.height / 2,
      };
    });
    if (points.length < 2) return { d: '', points };

    // A smooth line through the markers: vertical control handles, so
    // the curve leans into each side without overshooting past it.
    let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
    for (let i = 1; i < points.length; i += 1) {
      const a = points[i - 1];
      const b = points[i];
      const lift = Math.max(24, (b.y - a.y) * 0.45);
      d += ` C ${a.x.toFixed(1)} ${(a.y + lift).toFixed(1)},`
        + ` ${b.x.toFixed(1)} ${(b.y - lift).toFixed(1)},`
        + ` ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
    }
    return { d, points };
  }

  function init(rootId) {
    const root = document.getElementById(rootId);
    if (!root) return;

    let cleanup = [];

    /* ---- the film ---------------------------------------------------
       Particles that ride the SAME path the spine draws. Each carries a
       position along the path (0..1) and only exists where the line has
       actually been drawn, so the flow is always inside the map rather
       than running ahead of it. */
    function makeFilm(canvas, live, track) {
      const ctx = canvas.getContext('2d');
      const PARTICLES = 46;
      const dots = [];
      let raf = 0;
      let length = 0;
      let progress = 0;
      let running = false;
      let sparks = [];

      const PHASE_COLOURS = ['34,245,198', '58,167,255', '155,107,255', '43,232,154'];

      function reset(dot, at) {
        dot.t = at === undefined ? Math.random() : at;
        dot.speed = 0.0009 + Math.random() * 0.0016;
        dot.size = 0.7 + Math.random() * 1.7;
        dot.alpha = 0.25 + Math.random() * 0.5;
      }

      for (let i = 0; i < PARTICLES; i += 1) {
        const dot = {};
        reset(dot, i / PARTICLES);
        dots.push(dot);
      }

      function resize(width, height, pathLength) {
        const ratio = Math.min(2, window.devicePixelRatio || 1);
        canvas.width = Math.max(1, Math.round(width * ratio));
        canvas.height = Math.max(1, Math.round(height * ratio));
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        length = pathLength;
      }

      function colourAt(t) {
        // Four phases over fourteen stations; the tint follows whichever
        // one this stretch of the line belongs to.
        const index = Math.min(PHASE_COLOURS.length - 1, Math.floor(t * PHASE_COLOURS.length));
        return PHASE_COLOURS[index];
      }

      function burst(point) {
        if (!point) return;
        for (let i = 0; i < 14; i += 1) {
          const angle = (Math.PI * 2 * i) / 14 + Math.random();
          sparks.push({
            x: point.x, y: point.y,
            vx: Math.cos(angle) * (0.6 + Math.random() * 1.4),
            vy: Math.sin(angle) * (0.6 + Math.random() * 1.4),
            life: 1,
          });
        }
      }

      function frame() {
        if (!running) return;
        const width = canvas.width / (window.devicePixelRatio || 1);
        const height = canvas.height / (window.devicePixelRatio || 1);
        ctx.clearRect(0, 0, width, height);

        if (length > 0 && progress > 0.004) {
          dots.forEach((dot) => {
            dot.t += dot.speed;
            if (dot.t > 1) reset(dot, 0);
            if (dot.t > progress) return;   // never ahead of the drawn line
            let point;
            try { point = live.getPointAtLength(length * dot.t); } catch (e) { return; }
            // Fades out towards the end of its own run, so nothing
            // vanishes mid-stride.
            const near = Math.min(1, (progress - dot.t) * 14);
            ctx.beginPath();
            ctx.arc(point.x, point.y, dot.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${colourAt(dot.t)},${(dot.alpha * near).toFixed(3)})`;
            ctx.fill();
          });
        }

        sparks = sparks.filter((spark) => spark.life > 0.02);
        sparks.forEach((spark) => {
          spark.x += spark.vx;
          spark.y += spark.vy;
          spark.vx *= 0.94;
          spark.vy *= 0.94;
          spark.life *= 0.93;
          ctx.beginPath();
          ctx.arc(spark.x, spark.y, 1.6 * spark.life + 0.4, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255,255,255,${(spark.life * 0.5).toFixed(3)})`;
          ctx.fill();
        });

        raf = requestAnimationFrame(frame);
      }

      function start() {
        if (running) return;
        running = true;
        raf = requestAnimationFrame(frame);
      }

      function stop() {
        running = false;
        if (raf) cancelAnimationFrame(raf);
        raf = 0;
      }

      // Only while the map is on screen. A canvas animating behind a
      // section nobody is looking at is pure battery.
      const io = new IntersectionObserver((entries) => {
        entries.forEach((entry) => (entry.isIntersecting ? start() : stop()));
      }, { threshold: 0 });
      io.observe(track);

      return {
        resize,
        setProgress: (value) => { progress = value; },
        burst,
        destroy() { stop(); io.disconnect(); },
      };
    }

    function mount() {
      cleanup.forEach((fn) => fn());
      cleanup = [];
      render(root);

      const track = root.querySelector('.rm-track');
      const svg = root.querySelector('.rm-spine');
      const bg = root.querySelector('.rm-spine-bg');
      const live = root.querySelector('.rm-spine-live');
      const comet = root.querySelector('.rm-comet');
      const canvas = root.querySelector('.rm-film');
      const nodes = Array.from(root.querySelectorAll('.rm-node'));
      const markers = nodes.map((n) => n.querySelector('.rm-marker'));
      const reduced = window.DWMotion && window.DWMotion.prefersReduced();

      let length = 0;
      let thresholds = [];
      const film = (reduced || !canvas) ? null : makeFilm(canvas, live, track);

      function measure() {
        const box = track.getBoundingClientRect();
        svg.setAttribute('viewBox', `0 0 ${Math.max(1, box.width)} ${Math.max(1, box.height)}`);
        svg.setAttribute('width', box.width);
        svg.setAttribute('height', box.height);
        const built = buildPath(track, markers);
        if (!built.d) return;
        bg.setAttribute('d', built.d);
        live.setAttribute('d', built.d);
        length = live.getTotalLength();
        live.style.strokeDasharray = String(length);
        // Each station lights when the line reaches its own marker, so
        // the thresholds come from the geometry rather than a guess.
        thresholds = built.points.map((p) => (box.height ? p.y / box.height : 0));
        if (film) film.resize(box.width, box.height, length);
        paint();
      }

      function progress() {
        const box = track.getBoundingClientRect();
        const focus = window.innerHeight * 0.62;   // a little below centre
        return Math.max(0, Math.min(1, (focus - box.top) / Math.max(1, box.height)));
      }

      function paint() {
        if (!length) return;
        const p = reduced ? 1 : progress();
        live.style.strokeDashoffset = String(length * (1 - p));
        if (film) film.setProgress(p);

        if (!reduced && p > 0.001 && p < 0.999) {
          const point = live.getPointAtLength(length * p);
          comet.setAttribute('cx', point.x);
          comet.setAttribute('cy', point.y);
          comet.style.opacity = '1';
        } else {
          comet.style.opacity = '0';
        }

        nodes.forEach((node, i) => {
          const lit = p >= (thresholds[i] || 0) - 0.01;
          if (lit === node.classList.contains('is-lit')) return;
          node.classList.toggle('is-lit', lit);
          if (lit) {
            countIn(node);
            // A burst where the line just arrived, at the marker's own
            // measured position rather than a guess.
            if (film && length) {
              try { film.burst(live.getPointAtLength(length * (thresholds[i] || 0))); }
              catch (e) { /* the path was mid-rebuild */ }
            }
          }
        });
      }

      function countIn(node) {
        const el = node.querySelector('.rm-proof-value[data-count]');
        if (!el || el.dataset.counted) return;
        el.dataset.counted = '1';
        const decimals = parseInt(el.dataset.decimals || '0', 10);
        window.DWMotion.countUp(el, parseFloat(el.dataset.count), {
          decimals, duration: 900,
          format: (v) => v.toFixed(decimals),
        });
      }

      let queued = false;
      function onScroll() {
        if (queued) return;
        queued = true;
        requestAnimationFrame(() => { queued = false; paint(); });
      }

      // Fonts land after first paint and change every card's height, so
      // measuring once is measuring the wrong layout.
      const ro = new ResizeObserver(() => measure());
      ro.observe(track);
      window.addEventListener('scroll', onScroll, { passive: true });
      window.addEventListener('resize', measure);
      cleanup.push(() => {
        if (film) film.destroy();
        ro.disconnect();
        window.removeEventListener('scroll', onScroll);
        window.removeEventListener('resize', measure);
      });

      measure();
      if (window.DWMotion) window.DWMotion.observeReveals(root);
      // Reduced motion means every station is lit from the start, and
      // its number is on screen rather than counting up from zero.
      if (reduced) nodes.forEach((n) => { n.classList.add('is-lit'); countIn(n); });
    }

    mount();
    // The whole section is content, so a language change rebuilds it.
    document.addEventListener('dwai:langchange', mount);
    document.addEventListener('dwai:motionchange', mount);
  }

  window.DWAboutRoadmap = { init, STATIONS, HEAD, PHASES };
})();
