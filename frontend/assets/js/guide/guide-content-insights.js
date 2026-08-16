/*
  Guide content for the features added in this round (B-5).

  The architecture rule is that a feature ships its guide copy at the same
  time as the feature, not as a sweep at the end - otherwise some things
  talk and some things do not, and the guide reads as half-finished. These
  are the entries for the compact trend strip, the six insight cards, the
  future-self letter, the score range and the guide's own voice settings.

  Registered through DWGuide.register(), so each entry carries its own
  face and priority and is spoken by the same path as every other guide
  line - which means voice coverage (B-3) comes for free rather than
  needing separate wiring.

  Tone matches the existing registry: narrative, plain, direct without
  being condescending. The guide explains the PRODUCT - what a card is and
  how to read it - and never interprets the reader's own numbers, because
  interpreting real values is the job of the layers that actually have the
  data.
*/
(function () {
  if (!window.DWGuide || !window.DWGuide.register) return;

  window.DWGuide.register({
    // ---- A-1: the compact trend strip ----
    analytics_trend: {
      face: 'thinking',
      priority: 60,
      en: "This strip reads left to right, oldest day first. The line above it says the direction in words so you do not have to judge it by eye: up, down, or holding steady, plus how much it moved across the days it used. Days you marked as exceptions are drawn hollow and the line breaks around them — they are shown so the shape of your month stays honest, but they are deliberately left out of the maths. One unusual day should not bend a trend the app then reports back to you as a pattern.",
      fa: "این نوار از چپ به راست خوانده می‌شود، از قدیمی‌ترین روز. خط بالایش جهت را با کلمه می‌گوید تا لازم نباشد با چشم قضاوت کنی: بالا، پایین، یا تقریباً ثابت، به‌علاوه‌ی اینکه در طول روزهایی که استفاده کرده چقدر حرکت کرده. روزهایی که استثنا علامت زده‌ای توخالی کشیده می‌شوند و خط دورشان می‌شکند — نشان داده می‌شوند تا شکل ماهت صادقانه بماند، ولی عمداً از محاسبه کنار گذاشته شده‌اند. یک روز غیرعادی نباید روندی را خم کند که اپ بعداً به‌عنوان یک الگو به تو برمی‌گرداند.",
      ar: "يُقرأ هذا الشريط من اليسار إلى اليمين، بدءاً بأقدم يوم. السطر فوقه يذكر الاتجاه بالكلمات حتى لا تحتاج إلى الحكم بعينك: صاعد أو هابط أو مستقر، مع مقدار التغير عبر الأيام المستخدمة. الأيام التي علّمتها كاستثناءات تُرسم مفرغة وينكسر الخط حولها — تظهر ليبقى شكل شهرك صادقاً، لكنها مستثناة عمداً من الحساب. يوم واحد غير معتاد يجب ألا يثني اتجاهاً يعيده التطبيق إليك بعد ذلك كنمط.",
      zh: "这条带从左往右看，最早的一天在最左边。上面那行用文字说明方向，你不必用眼睛去判断：上升、下降还是基本持平，以及在所用的那些天里变动了多少。你标记为例外的日子画成空心，线条在它们处断开——显示出来是为了让这个月的形状保持诚实，但它们被刻意排除在计算之外。一个不寻常的日子不该扭曲一个趋势，然后由应用当作规律报告给你。",
    },

    // ---- C-6-3: the score presented as a range ----
    result_confidence: {
      face: 'thinking',
      priority: 70,
      en: "The big figure is a range, not one exact number, because the model has a measurable average error and a single value would claim a precision it does not have. The range comes from how far off the model was on a validation split it never trained on — never from the test set, which is kept for one final check. The smaller number underneath is the single best estimate inside that range.",
      fa: "عدد بزرگ یک بازه است نه یک رقم دقیق، چون مدل یک خطای میانگین قابل‌اندازه‌گیری دارد و یک عدد تنها، دقتی را ادعا می‌کند که ندارد. بازه از این می‌آید که مدل روی بخش اعتبارسنجی — که هرگز رویش آموزش ندیده — چقدر خطا داشته؛ هرگز از مجموعه‌ی تست، که برای یک بررسی نهایی نگه داشته می‌شود. عدد کوچک‌تر زیرش، بهترین تخمین نقطه‌ای داخل همان بازه است.",
      ar: "الرقم الكبير مدى وليس رقماً دقيقاً واحداً، لأن للنموذج خطأً متوسطاً قابلاً للقياس، والقيمة المفردة تدّعي دقة لا يملكها. يأتي المدى من مقدار خطأ النموذج على قسم التحقق الذي لم يتدرب عليه قط — لا من مجموعة الاختبار المحفوظة لفحص نهائي واحد. الرقم الأصغر تحته هو أفضل تقدير مفرد داخل ذلك المدى.",
      zh: "那个大数字是一个区间，而不是一个精确值，因为模型有可测量的平均误差，单一数值会宣称它并不具备的精度。这个区间来自模型在它从未训练过的验证集上的误差——绝不来自测试集，那个集合留作一次最终检验。下面那个较小的数字，是这个区间内最佳的单点估计。",
    },

    // ---- D-4 / D-5: relationships found in the reader's own data ----
    insight_relationship: {
      face: 'thinking',
      priority: 55,
      en: "This card comes from your own check-ins, not from anyone else's. It looks for two things you log that tend to move together, or move opposite each other. Read it as an observation and nothing more: two numbers rising together does not mean one is causing the other, and the card says so on purpose. Days you marked as exceptions never contribute, and if the pattern is not strong enough to survive a proper significance test, no card appears at all rather than a weak guess dressed up as a finding.",
      fa: "این کارت از بررسی‌های خودت می‌آید، نه از کس دیگری. دنبال دو چیزی می‌گردد که ثبت می‌کنی و معمولاً با هم یا در خلاف جهت هم حرکت می‌کنند. آن را فقط به‌عنوان یک مشاهده بخوان: بالا رفتن هم‌زمان دو عدد به این معنا نیست که یکی باعث دیگری است، و کارت این را عمداً می‌گوید. روزهای استثنا هرگز سهمی ندارند، و اگر الگو آن‌قدر قوی نباشد که از یک آزمون معناداری واقعی رد شود، اصلاً کارتی نشان داده نمی‌شود — به‌جای یک حدس ضعیف که لباس کشف پوشیده باشد.",
      ar: "تأتي هذه البطاقة من تسجيلاتك أنت، لا من أحد آخر. تبحث عن شيئين تسجّلهما ويميلان إلى التحرك معاً أو في اتجاهين متعاكسين. اقرأها كملاحظة فقط: ارتفاع رقمين معاً لا يعني أن أحدهما يسبب الآخر، والبطاقة تقول ذلك عن قصد. الأيام التي علّمتها كاستثناءات لا تساهم أبداً، وإذا لم يكن النمط قوياً بما يكفي لاجتياز اختبار دلالة حقيقي، فلا تظهر بطاقة إطلاقاً بدلاً من تخمين ضعيف يرتدي ثوب الاكتشاف.",
      zh: "这张卡片来自你自己的记录，而不是别人的。它寻找你记录的两项内容中，往往同向变化或反向变化的一对。请把它当作一个观察而已：两个数字一起上升，并不意味着其中一个导致了另一个，卡片也特意说明了这一点。你标记为例外的日子从不参与计算；如果这个模式不足以通过一次严格的显著性检验，就根本不会出现卡片，而不是把一个薄弱的猜测包装成发现。",
    },

    // ---- D-6 / D-9: week summary and then-versus-now ----
    insight_week: {
      face: 'good',
      priority: 55,
      en: "A plain summary of the week you actually logged: your average, your best day, and how it compares with the week before. If you have enough history there is also a then-and-now line comparing your first days with your recent ones. When that comparison goes the wrong way it still says so plainly — a number that only tells you good news is not worth reading — but it is a fact with a next step, never a verdict on you.",
      fa: "یک خلاصه‌ی ساده از هفته‌ای که واقعاً ثبت کرده‌ای: میانگینت، بهترین روزت، و مقایسه‌اش با هفته‌ی قبل. اگر تاریخچه‌ی کافی داشته باشی، یک خط «آن‌وقت و حالا» هم هست که روزهای اولت را با روزهای اخیرت مقایسه می‌کند. وقتی آن مقایسه در جهت نامطلوب باشد، باز هم صریح می‌گوید — عددی که فقط خبر خوب بدهد ارزش خواندن ندارد — ولی یک واقعیت همراه با قدم بعدی است، نه حکمی درباره‌ی تو.",
      ar: "ملخص بسيط للأسبوع الذي سجّلته فعلاً: متوسطك، وأفضل أيامك، ومقارنته بالأسبوع السابق. إن كان لديك سجل كافٍ، فهناك أيضاً سطر «حينها والآن» يقارن أيامك الأولى بأيامك الأخيرة. وحين تسير تلك المقارنة في الاتجاه غير المرغوب، فإنها تقول ذلك بوضوح — رقم لا يخبرك إلا بالأخبار الجيدة لا يستحق القراءة — لكنه واقعة مصحوبة بخطوة تالية، لا حكماً عليك.",
      zh: "对你实际记录的这一周的朴素总结：你的平均分、最好的一天，以及与上一周的比较。如果你的历史足够长，还会有一行“当时与现在”，把最初几天和最近几天做对比。当这个比较朝不理想的方向走时，它仍会照直说——一个只报喜的数字不值得读——但它是一个带着下一步的事实，而不是对你的判决。",
    },

    // ---- D-11 ----
    insight_small_win: {
      face: 'great',
      priority: 45,
      en: "One thing that moved in your favour since yesterday, and only one. Congratulating six things at once is how congratulation stops meaning anything. Changes smaller than about eight percent are ignored on purpose, because day-to-day numbers wobble on their own and calling that a win would be flattery rather than feedback.",
      fa: "یک چیز که از دیروز به نفعت حرکت کرده، و فقط یکی. تبریک‌گفتن برای شش چیز هم‌زمان همان کاری است که تبریک را بی‌معنا می‌کند. تغییرهای کمتر از حدود هشت درصد عمداً نادیده گرفته می‌شوند، چون اعداد روزبه‌روز خودشان نوسان دارند و برد نامیدن آن، چاپلوسی است نه بازخورد.",
      ar: "شيء واحد تحرّك لصالحك منذ الأمس، وواحد فقط. تهنئتك على ستة أشياء دفعة واحدة هي ما يجعل التهنئة بلا معنى. التغيرات الأقل من نحو ثمانية بالمئة تُتجاهل عمداً، لأن الأرقام اليومية تتذبذب من تلقاء نفسها، وتسمية ذلك مكسباً تملّق لا تغذية راجعة.",
      zh: "自昨天以来对你有利的一项变化，而且只有一项。一次祝贺六件事，正是让祝贺失去意义的做法。小于约百分之八的变化会被刻意忽略，因为每天的数字本身就会波动，把那称为进步是奉承而不是反馈。",
    },

    // ---- D-3 ----
    insight_alert: {
      face: 'borderline',
      priority: 65,
      en: "This appears when a threshold in your own recent history is crossed — a run of lower days, for instance. It is a heads-up, not an alarm and certainly not a diagnosis, so it always arrives with one specific thing you could do rather than just a warning. You can dismiss it, and if you dismiss the same one twice it stops appearing for a while.",
      fa: "این وقتی ظاهر می‌شود که یک آستانه در تاریخچه‌ی اخیر خودت رد شود — مثلاً چند روز پیاپی پایین‌تر. این یک تذکر است، نه زنگ خطر و قطعاً نه تشخیص، پس همیشه با یک کار مشخص که می‌توانی انجام بدهی می‌آید، نه فقط یک هشدار. می‌توانی ببندی‌اش، و اگر همان یکی را دو بار ببندی، مدتی دیگر نشان داده نمی‌شود.",
      ar: "يظهر هذا عند تجاوز عتبة في سجلك الأخير — سلسلة من الأيام الأدنى مثلاً. إنه تنبيه، لا إنذار وبالتأكيد ليس تشخيصاً، لذا يأتي دائماً مع شيء محدد يمكنك فعله بدل مجرد تحذير. يمكنك إغلاقه، وإن أغلقت الشيء نفسه مرتين توقف عن الظهور لفترة.",
      zh: "当你自己最近的记录越过某个阈值时，它会出现——比如连续几天走低。这是一个提醒，不是警报，更不是诊断，所以它总会附带一件你可以去做的具体事情，而不只是一句警告。你可以关掉它；如果同一条你关掉两次，它会有一段时间不再出现。",
    },

    // ---- D-10 ----
    insight_letter: {
      face: 'good',
      priority: 50,
      en: "A short letter written from your own figures — days logged, your recent average, your best day, the thing that moved most. There are two versions and they are genuinely different letters, not one text with a word swapped: one for when things are holding, one for when they are drifting. The drifting one does not soften the fact and does not catastrophise it either; it ends on the nearest single thing you could change. It only appears once you have enough history for it to be about you, and it waits behind a click rather than opening itself.",
      fa: "نامه‌ای کوتاه که از اعداد خودت نوشته می‌شود — روزهای ثبت‌شده، میانگین اخیرت، بهترین روزت، چیزی که بیشترین حرکت را داشته. دو نسخه دارد و واقعاً دو نامه‌ی متفاوت‌اند، نه یک متن با یک کلمه‌ی عوض‌شده: یکی برای وقتی که اوضاع پابرجاست، یکی برای وقتی که دارد افت می‌کند. نسخه‌ی افت، واقعیت را نه ملایم می‌کند و نه فاجعه؛ با نزدیک‌ترین کاری که می‌توانی عوض کنی تمام می‌شود. فقط وقتی ظاهر می‌شود که تاریخچه‌ی کافی داشته باشی تا درباره‌ی تو باشد، و پشت یک کلیک منتظر می‌ماند نه اینکه خودش باز شود.",
      ar: "رسالة قصيرة مكتوبة من أرقامك أنت — أيام سجّلتها، متوسطك الأخير، أفضل أيامك، وأكثر ما تحرّك. لها نسختان وهما رسالتان مختلفتان فعلاً، لا نص واحد بكلمة مُبدَّلة: واحدة حين تكون الأمور ثابتة، وأخرى حين تنحدر. نسخة الانحدار لا تُلطّف الحقيقة ولا تُهوّلها؛ تنتهي بأقرب شيء واحد يمكنك تغييره. تظهر فقط حين يكون لديك سجل كافٍ لتكون عنك، وتنتظر خلف نقرة بدل أن تفتح نفسها.",
      zh: "一封用你自己的数字写成的短信——记录的天数、最近的平均分、最好的一天、变动最大的那一项。它有两个版本，而且确实是两封不同的信，不是同一段文字换个词：一封写给情况稳住的时候，一封写给正在下滑的时候。下滑的那封既不把事实说得柔和，也不把它说成灾难；它以你能改变的最近的一件事作结。只有当你的历史足够长、这封信真的关于你时它才会出现，而且它等在一次点击之后，不会自己打开。",
    },

    // ---- D-8 ----
    insight_challenge: {
      face: 'good',
      priority: 55,
      en: "A few challenges for the week, and every target in them is your own. \"Your typical score\" and \"your usual screen time\" are computed from your real check-ins - the same baselines the rest of the app uses - so nobody is handing you a round number someone else decided on. A challenge that your history cannot support yet simply is not shown, rather than appearing with a made-up target. And none of them are pass or fail: the bar is there to show you where you are this week, not to mark you.",
      fa: "چند چالش برای هفته، و هر هدفی که در آن‌هاست مال خودت است. «امتیاز معمول تو» و «زمان صفحه‌ی همیشگی تو» از بررسی‌های واقعی خودت حساب می‌شوند - همان خط پایه‌هایی که بقیه‌ی برنامه هم از آن‌ها استفاده می‌کند - پس کسی یک عدد رُند که دیگری تعیین کرده به تو نمی‌دهد. چالشی که سابقه‌ات هنوز پشتیبانی‌اش نکند اصلاً نشان داده نمی‌شود، به‌جای اینکه با هدفی ساختگی ظاهر شود. و هیچ‌کدامشان قبولی و ردی نیستند: آن نوار هست تا ببینی این هفته کجایی، نه اینکه نمره‌ات بدهد.",
      ar: "بضعة تحديات للأسبوع، وكل هدف فيها هو هدفك أنت. \"درجتك المعتادة\" و\"وقت شاشتك المعتاد\" محسوبان من تسجيلاتك الحقيقية - وهي نفس خطوط الأساس التي يستخدمها باقي التطبيق - فلا أحد يمنحك رقماً مستديراً قرره شخص آخر. والتحدي الذي لا يدعمه سجلك بعد لا يُعرض أصلاً، بدل أن يظهر بهدف مُختلق. ولا شيء منها نجاح أو رسوب: الشريط موجود ليريك أين أنت هذا الأسبوع، لا ليضع لك علامة.",
      zh: "本周有几个挑战，其中每一个目标都来自你自己。\"你的常态分数\"和\"你常态的屏幕时间\"都是根据你真实的记录算出来的——和应用其他地方使用的是同一套基线——所以没有人塞给你一个别人定下的整数。你的历史还不足以支撑的挑战干脆不会显示，而不是带着一个编造的目标出现。而且它们都不是及格或不及格：那条进度条是让你看看这周走到哪里，不是给你打分。",
    },

    // ---- B-2 ----
    settings_guide_voice: {
      face: 'good',
      priority: 60,
      en: "I can read my messages out loud using a voice built into your browser — nothing is sent anywhere, and there is no account or key involved. Whether a language has a voice at all is decided by your browser and device, not by this app, which is why the list shows each language separately and honestly. If your language has no voice installed, speech simply stays off for that one and the others keep working.",
      fa: "می‌توانم پیام‌هایم را با صدایی که داخل خود مرورگرت هست بلند بخوانم — هیچ‌چیز جایی فرستاده نمی‌شود، و هیچ حساب یا کلیدی در کار نیست. اینکه یک زبان اصلاً صدا دارد یا نه را مرورگر و دستگاه تو تعیین می‌کند، نه این برنامه؛ برای همین فهرست، هر زبان را جدا و صادقانه نشان می‌دهد. اگر زبان تو صدایی نصب نداشته باشد، گفتار فقط برای همان خاموش می‌ماند و بقیه کار می‌کنند.",
      ar: "يمكنني قراءة رسائلي بصوت عالٍ باستخدام صوت مدمج في متصفحك — لا يُرسل شيء إلى أي مكان، ولا حساب ولا مفتاح في الأمر. أما إن كانت لغة ما تملك صوتاً أصلاً فيقرره متصفحك وجهازك لا هذا التطبيق، ولذلك تعرض القائمة كل لغة على حدة وبصدق. إن لم يكن للغتك صوت مثبّت، يبقى النطق مغلقاً لها وحدها وتستمر الأخرى في العمل.",
      zh: "我可以用你浏览器内置的语音把消息读出来——没有任何内容被发送到别处，也不涉及任何账号或密钥。某种语言究竟有没有语音，是由你的浏览器和设备决定的，而不是本应用，所以列表会逐个语言诚实地显示状态。如果你的语言没有安装语音，朗读只会对那一种关闭，其余的照常工作。",
    },
  });
})();
