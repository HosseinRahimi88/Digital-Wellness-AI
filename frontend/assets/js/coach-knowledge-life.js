/*
  AI Coach knowledge — add-on pack 1: sleep, focus/work, and social.

  Registered through DWCoachKnowledge.register() at priority 10, so these
  specific topics are matched BEFORE the broad catch-alls (`sleep`,
  `focus`, `social`) in the base file. Splitting the packs keeps any one
  file reviewable; the base file owns the matcher and the safety rules.

  Same content rules as the base file, no exceptions:
  - No medical, diagnostic or treatment claims. Research is stated as
    association ("tends to", "is linked with"), never as a clinical fact
    about the reader.
  - Nothing here reads the user's own numbers; coach-chat.js composes
    personalised answers because it is the layer that has the data.
  - Every entry exists in English and Persian.
  - English patterns keep the (?:s|es|ing)? group suffix so plurals match;
    Persian patterns avoid fixed noun+verb order because possessives
    attach to the noun (چشم -> چشمم).
*/
(function () {
  if (!window.DWCoachKnowledge || !window.DWCoachKnowledge.register) return;

  const TOPICS = [
    /* ---------------------------------------------------------------
       Sleep & rest
       --------------------------------------------------------------- */
    {
      key: 'naps',
      match: /\b(nap|power nap|siesta|daytime sleep)(?:s|es|ing)?\b|چرت|خواب نیمروز|خواب کوتاه روز|قيلولة|غفوة|نوم النهار|午睡|小睡|打个盹|白天睡/i,
      en: "A short nap early in the afternoon is generally the least disruptive kind — long or late ones tend to borrow from that night's sleep rather than adding to your total. If you nap because the night before was short, treat that as information about bedtime rather than a fix in itself.",
      fa: "یک چرت کوتاه در اوایل بعدازظهر معمولاً کم‌اختلال‌ترین نوع است — چرت‌های طولانی یا دیرهنگام بیشتر از خواب همان شب قرض می‌گیرند تا اینکه به مجموعش اضافه کنند. اگر چرت می‌زنی چون شب قبل کم خوابیدی، آن را اطلاعاتی درباره‌ی ساعت خوابت بدان، نه راه‌حل.",
      ar: "القيلولة القصيرة في وقت مبكر من بعد الظهر هي عادة الأقل إخلالا — أما الطويلة أو المتأخرة فتستعير من نوم تلك الليلة بدلا من أن تضيف إلى مجموعك. إن كنت تأخذ قيلولة لأن الليلة السابقة كانت قصيرة، فذلك معقول؛ أما إن صارت القيلولة هي ما يجعل الليلة التالية قصيرة، فقد انقلبت الحلقة. عشرون دقيقة قبل الثالثة عصرا هي نقطة البداية المعتادة.",
      zh: "下午早些时候的短暂小睡通常干扰最小——太长或太晚的小睡，往往是从当晚的睡眠里借时间，而不是给你的总量加时间。如果你小睡是因为前一晚睡得太少，那是合理的；但如果小睡本身开始让下一晚变短，这个循环就反过来了。下午三点前、二十分钟左右，是通常的起点。",
    },
    {
      key: 'shift_work',
      match: /\b(shift work|night shift|graveyard shift|rotating shift|work nights)(?:s|es|ing)?\b|شیفت شب|کار شبانه|شیفت گردشی|عمل بنظام الورديات|وردية الليلية|شفت الليلي|أعمل ليلا|轮班|夜班|上夜班|倒班/i,
      en: "Shift work makes the usual advice awkward, because the goal shifts from 'sleep at night' to 'sleep at the same time as often as you can'. What still helps: a dark, cool room whatever the hour, a consistent wind-down whenever your day ends, and treating the drive home as part of the wind-down rather than scroll time.",
      fa: "کار شیفتی توصیه‌های معمول را بی‌ربط می‌کند، چون هدف از «شب بخواب» به «هرچه بیشتر در ساعت ثابت بخواب» تغییر می‌کند. آنچه هنوز کمک می‌کند: اتاق تاریک و خنک در هر ساعتی، یک روتین آرام‌شدن ثابت هر وقت روزت تمام شد، و برخورد با مسیر برگشت به خانه به‌عنوان بخشی از آرام‌شدن نه زمان اسکرول.",
      ar: "العمل بالورديات يجعل النصيحة المعتادة محرجة، لأن الهدف يتحول من نم في الليل إلى نم في نفس الوقت كلما استطعت. ما يبقى مفيدا: غرفة معتمة وباردة أيا كانت الساعة، وروتين ثابت قبل النوم، والحرص على الضوء الساطع في بداية وردية عملك لا في نهايتها. الثبات هنا أهم من التوقيت نفسه.",
      zh: "轮班让常规建议变得别扭，因为目标从在夜里睡觉变成了尽可能在同一时间睡觉。仍然有用的是：无论几点，房间都要暗、要凉；睡前流程保持固定；把明亮的光安排在班次开始时而不是结束时。在这里，规律性比具体几点更重要。",
    },
    {
      key: 'waking_at_night',
      match: /\b(wake up (at|in the) night|can'?t (get back to|fall back) (a)?sleep|3am|middle of the night)(?:s|es|ing)?\b|نیمه‌شب بیدار|وسط شب بیدار|دوباره خوابم نمی‌برد|أستيقظ في الليل|لا أستطيع العودة للنوم|منتصف الليل|ثالثة فجرا|夜里醒|半夜醒来|睡不回去|凌晨三点/i,
      en: "Waking briefly at night is common and not by itself a problem — what tends to extend it is reaching for a bright screen, which both wakes you further and gives the mind something to chase. If you are awake more than about twenty minutes, getting up and doing something dull in dim light is usually easier than lying there negotiating with yourself.",
      fa: "بیدارشدن کوتاه در شب رایج است و خودش به‌تنهایی مشکل نیست — آنچه معمولاً طولانی‌ترش می‌کند برداشتن یک صفحه‌ی روشن است، که هم بیدارترت می‌کند و هم به ذهن چیزی برای دنبال‌کردن می‌دهد. اگر بیش از بیست دقیقه بیداری، بلندشدن و انجام کاری کسل‌کننده در نور کم معمولاً راحت‌تر از دراز‌کشیدن و چانه‌زدن با خودت است.",
      ar: "الاستيقاظ لفترة قصيرة في الليل شائع وليس بنفسه مشكلة — ما يميل إلى تمديده هو الوصول إلى شاشة ساطعة، فهي توقظك أكثر وتعطي الذهن شيئا يطارده. إن كنت مستيقظا لأكثر من عشرين دقيقة، فالنهوض إلى غرفة أخرى بضوء خفيف ونشاط ممل يعمل عادة أفضل من البقاء في السرير محاولا. وإن كان يحدث كل ليلة ويشكّل نهارك، فذلك سؤال لطبيب لا لتطبيق.",
      zh: "夜里短暂醒来很常见，本身不是问题——真正会把它拉长的，是伸手去看明亮的屏幕：它让你更清醒，也给大脑找了个可以追的东西。如果你醒了超过二十分钟，起身到另一个房间、开一盏弱灯做点无聊的事，通常比躺在床上硬睡更有效。如果这每晚都发生并且影响了你的白天，那是该问医生的问题，而不是问应用。",
    },
    {
      key: 'snooze_button',
      match: /\b(snooze|hit snooze|alarm(s)? (again|multiple)|oversleep)(?:s|es|ing)?\b|اسنوز|زنگ رو می‌زنم بخوابم|چند بار زنگ|زر التأجيل|أعيد المنبه|منبهات متعددة|أنام بعد المنبه|贪睡|按掉闹钟|多个闹钟|睡过头/i,
      en: "Snoozing fragments the last stretch of sleep into pieces too short to be restful, which is why nine extra minutes often leaves you groggier than getting up would have. Putting the alarm out of arm's reach converts the decision into a physical action, which is far more reliable than deciding well while half asleep.",
      fa: "اسنوز آخرین بخش خواب را به تکه‌های خیلی کوتاه‌تر از آنکه آرامش‌بخش باشند خرد می‌کند؛ برای همین نُه دقیقه‌ی اضافه اغلب گیج‌ترت می‌کند تا بلندشدن. گذاشتن ساعت بیرون از دسترسِ دست، تصمیم را به یک کار فیزیکی تبدیل می‌کند که خیلی قابل‌اعتمادتر از خوب‌تصمیم‌گرفتن در نیمه‌خواب است.",
      ar: "التأجيل يفتّت آخر مرحلة من النوم إلى قطع أقصر من أن تكون مريحة، ولهذا فإن تسع دقائق إضافية تتركك غالبا أثقل مما لو نهضت. وضع المنبه بعيدا عن مدى الذراع يحوّل القرار إلى حركة، وهذا عادة يكفي. وإن كنت تحتاج ثلاثة منبهات كل صباح، فالمعلومة الحقيقية ليست عن إرادتك بل عن وقت نومك.",
      zh: "贪睡会把睡眠的最后一段切成太短、无法真正休息的碎片，这就是为什么多睡九分钟往往让你比直接起床更昏沉。把闹钟放到手伸不到的地方，就把一个决定变成了一个动作，这通常就够了。而如果你每天早上都需要三个闹钟，真正的信息不是关于你的意志力，而是关于你上床的时间。",
    },
    {
      key: 'sleep_tracking',
      match: /\b(sleep track|sleep app|sleep score|smartwatch sleep|oura|whoop)(?:s|es|ing)?\b|ردیاب خواب|اپ خواب|امتیاز خواب ساعت|تتبع النوم|تطبيق نوم|درجة النوم|ساعة ذكية للنوم|睡眠追踪|睡眠应用|睡眠评分|手环 睡眠|智能手表 睡眠/i,
      en: "Sleep trackers are decent at trends and weak at single nights, so the useful reading is the direction over a couple of weeks rather than last night's grade. Worth watching for the opposite effect too: anxiety about a bad sleep score can cost more sleep than whatever it was measuring.",
      fa: "ردیاب‌های خواب در نشان‌دادن روند خوب‌اند و در یک شب تنها ضعیف، پس خواندنِ مفید جهتِ چند هفته است نه نمره‌ی دیشب. مراقب اثر معکوس هم باش: اضطراب از یک امتیاز خواب بد می‌تواند بیشتر از آنچه اندازه می‌گرفت، خواب از تو بگیرد.",
      ar: "أجهزة تتبع النوم جيدة في الاتجاهات وضعيفة في الليالي المنفردة، فالقراءة المفيدة هي الاتجاه خلال أسبوعين لا درجة ليلة أمس. ويستحق الانتباه للأثر المعاكس أيضا: القلق من الدرجة نفسها يمكن أن يزعج النوم الذي يقيسه. إن جعلك الرقم تنام أسوأ، فذلك سبب وجيه لإخفائه لفترة.",
      zh: "睡眠追踪设备擅长看趋势，不擅长判断单独一晚，所以有用的读法是两周内的方向，而不是昨晚的评分。也值得留意相反的效应：对分数本身的焦虑，可能会干扰它正在测量的睡眠。如果那个数字让你睡得更差，这就是把它先隐藏一段时间的好理由。",
    },
    {
      key: 'bedroom_setup',
      match: /\b(bedroom|dark room|blackout|room temperature|mattress|noise at night)(?:s|es|ing)?\b|اتاق خواب|اتاق تاریک|دمای اتاق|سروصدای شب|غرفة النوم|غرفة معتمة|تعتيم|حرارة الغرفة|مرتبة|ضجيج في الليل|卧室|遮光|房间温度|床垫|夜间噪音/i,
      en: "The room is the part you set once and then stop deciding about: darker, cooler and quieter is the usual direction, and a charger somewhere other than the bedside is the single change that removes the most late-night decisions. Structural fixes beat nightly willpower because they keep working on tired days.",
      fa: "اتاق همان بخشی است که یک بار تنظیمش می‌کنی و بعد دیگر درباره‌اش تصمیم نمی‌گیری: تاریک‌تر، خنک‌تر و ساکت‌تر جهت معمول است، و شارژر در جایی غیر از کنار تخت، تکْ‌تغییری است که بیشترین تصمیم‌های نیمه‌شب را حذف می‌کند. اصلاح ساختاری از اراده‌ی هرشب بهتر است چون روزهای خسته هم کار می‌کند.",
      ar: "الغرفة هي الجزء الذي تضبطه مرة ثم تتوقف عن التفكير فيه: أكثر عتمة وأكثر برودة وأكثر هدوءا هو الاتجاه المعتاد، والشاحن في مكان غير جانب السرير هو التغيير الواحد الذي يزيل نصف الإغراء دون أي قوة إرادة. لهذا يستحق الاستثمار: التغييرات البنيوية لا تحتاج منك أن تتذكرها كل ليلة.",
      zh: "卧室是那种你设置一次、然后就不再需要为它做决定的部分：更暗、更凉、更安静是通常的方向，而把充电器放在床头以外的地方，是那个不需要任何意志力就能消除一半诱惑的单一改变。这就是它值得投入的原因：结构性的改变不需要你每晚都记得它。",
    },

    /* ---------------------------------------------------------------
       Focus, work & study
       --------------------------------------------------------------- */
    {
      key: 'pomodoro',
      match: /\b(pomodoro|25 minute|timer technique|time box|timeboxing)(?:s|es|ing)?\b|پومودورو|تکنیک ۲۵ دقیقه|زمان‌بندی بلوکی|بومودورو|خمس وعشرون دقيقة|تقنية المؤقت|تحديد وقت للمهمة|番茄工作法|番茄钟|25分钟|计时法|时间盒/i,
      en: "Fixed work/break cycles help mostly because they make starting cheap — you are committing to a short block, not to finishing. The length matters less than the rule that the phone stays out of reach for the block; a 25-minute timer with the phone in your hand is just 25 minutes of interruption with a countdown.",
      fa: "چرخه‌های ثابت کار/استراحت بیشتر به این دلیل کمک می‌کنند که شروع‌کردن را ارزان می‌کنند — به یک بلوک کوتاه متعهد می‌شوی، نه به تمام‌کردن. طولش کمتر از این قاعده مهم است که در طول بلوک گوشی دور از دسترس بماند؛ تایمر ۲۵ دقیقه‌ای با گوشی در دست، فقط ۲۵ دقیقه وقفه با شمارش معکوس است.",
      ar: "دورات العمل والراحة الثابتة تساعد أساسا لأنها تجعل البدء رخيصا — أنت تلتزم بكتلة قصيرة لا بالإنهاء. الطول أقل أهمية من قاعدة أن الهاتف يبقى بعيدا عن متناول اليد خلال الكتلة؛ فبدون ذلك الجزء تصير التقنية مؤقتا تشاهده وأنت تتصفح. ابدأ بخمس عشرة دقيقة إن كانت الخمس والعشرون تبدو كثيرة.",
      zh: "固定的工作与休息循环之所以有帮助，主要是因为它让开始变得便宜——你承诺的是一个短时段，而不是完成任务。时长不如那条规则重要：在这个时段里手机要放在手伸不到的地方；没有那一部分，这个方法就只是一个你一边刷手机一边看着的计时器。如果二十五分钟感觉太多，就从十五分钟开始。",
    },
    {
      key: 'to_do_lists',
      match: /\b(to.?do list|task list|todo app|planner|checklist)(?:s|es|ing)?\b|لیست کارها|فهرست کار|اپ برنامه‌ریزی|قائمة المهام|قائمة الأعمال|تطبيق مهام|مخطط|قائمة تحقق|待办|任务清单|待办应用|计划表|清单/i,
      en: "A list that holds everything is a memory aid; a list that says what happens next is a plan. The common failure is length — twenty open items produce avoidance rather than action, so picking the one or two that actually happen today and hiding the rest is usually the fix.",
      fa: "فهرستی که همه‌چیز را نگه دارد کمک‌حافظه است؛ فهرستی که بگوید بعدی چیست برنامه است. شکست رایج طول است — بیست آیتم باز، اجتناب می‌سازد نه عمل؛ پس انتخاب یکی دو موردی که واقعاً امروز انجام می‌شوند و پنهان‌کردن بقیه معمولاً راه‌حل است.",
      ar: "القائمة التي تحتفظ بكل شيء معين للذاكرة؛ والقائمة التي تقول ما يحدث تاليا خطة. الفشل الشائع هو الطول — عشرون بندا مفتوحا تنتج تجنبا لا عملا، لذا فإن اختيار البند أو البندين اللذين يحدثان اليوم فعلا وإخفاء الباقي هو التعديل الذي يهم. القائمة ليست سجل التزامات، بل أداة لاختيار الخطوة التالية.",
      zh: "什么都记下的清单是记忆辅助；说明接下来做什么的清单才是计划。常见的失败是太长——二十个未完成的条目会带来回避而不是行动，所以真正有用的调整是：挑出今天确实会做的那一两项，把其余的收起来。清单不是义务的账本，而是选择下一步的工具。",
    },
    {
      key: 'prioritization',
      match: /\b(priorit|what should i do first|too much to do|overwhelmed by (work|tasks))(?:s|es|ing|ies|ise|ize)?\b|اولویت|اول چه کاری|کار زیاد دارم|غرق کار|أولويات|ما أبدأ به|كثير من العمل|مثقل بالمهام|优先级|先做什么|事情太多|任务压身|分不清主次/i,
      en: "When everything looks urgent, the useful question is not 'what matters most' but 'what is only possible today'. Most lists shrink fast under that test. If two things genuinely tie, doing the one you are avoiding usually frees more attention than finishing the easy one.",
      fa: "وقتی همه‌چیز فوری به نظر می‌رسد، سؤال مفید «چه چیزی مهم‌تر است» نیست بلکه «چه چیزی فقط امروز ممکن است» است. بیشتر فهرست‌ها زیر این آزمون سریع کوچک می‌شوند. اگر دو چیز واقعاً مساوی بودند، انجام‌دادن آن که از آن فرار می‌کنی معمولاً بیشتر از تمام‌کردن کار آسان، توجه آزاد می‌کند.",
      ar: "عندما يبدو كل شيء عاجلا، فالسؤال المفيد ليس ما الأهم بل ما الممكن اليوم فقط. تتقلص معظم القوائم بسرعة تحت هذا الاختبار. وإن تعادل أمران فعلا، فالبدء بما تتجنبه أكثر عادة هو الخيار الأصح، لأن التجنب نفسه صار جزءا من التكلفة.",
      zh: "当所有事都看起来紧急时，有用的问题不是什么最重要，而是什么只有今天才能做。大多数清单在这个测试下会迅速缩短。如果两件事真的不分先后，先做你更想回避的那一件通常更对，因为回避本身已经成了成本的一部分。",
    },
    {
      key: 'perfectionism',
      match: /\b(perfectionist|perfection|perfectionism|good enough|never finish|keep redoing|nitpick)(?:s|es|ing)?\b|کمال‌گرا|هیچ‌وقت تموم نمی‌شه|مدام بازنویسی|وسواس کاری|كمالية|سعي للكمال|جيد بما يكفي|لا أنهي أبدا|أعيد العمل مرارا|完美主义|追求完美|够好就行|总也做不完|反复修改/i,
      en: "Perfectionism usually shows up as delay rather than quality — the work is held back because finishing means being judged. A deliberately rough first pass, made on purpose and labelled as such, tends to unlock more real progress than another round of polishing something unfinished.",
      fa: "کمال‌گرایی معمولاً به‌شکل تعویق ظاهر می‌شود نه کیفیت — کار نگه داشته می‌شود چون تمام‌شدن یعنی قضاوت‌شدن. یک نسخه‌ی اول عمداً خام، که آگاهانه ساخته و همان‌طور هم نامیده شود، معمولاً پیشرفت واقعی بیشتری آزاد می‌کند تا یک دور دیگر صیقل‌دادن چیزی نیمه‌کاره.",
      ar: "الكمالية تظهر عادة كتأخير لا كجودة — يُحتجَز العمل لأن إنهاءه يعني التعرض للحكم. المرور الأول الخشن بشكل متعمد، والمُسمّى كذلك صراحة، يميل إلى تحطيم ذلك أفضل من محاولة الاهتمام أقل. أنت لا تخفض معيارك، أنت تفصل الصنع عن التقييم.",
      zh: "完美主义通常表现为拖延而不是质量——工作被压着不放，是因为完成意味着要被评判。刻意做一个粗糙的初稿，并且明确地把它称为初稿，往往比试图让自己少在意更能打破这一点。你不是降低标准，你是把创作和评判分开。",
    },
    {
      key: 'meetings',
      match: /\b(meeting|calendar full|back.to.back call|standup)(?:s|es|ing)?\b|جلسه|تقویم پر|جلسات پشت‌سرهم|اجتماع|تقويم ممتلئ|مكالمات متتالية|اجتماع يومي|会议|日程排满|连着开会|站会|例会/i,
      en: "Meetings cost more than their length because they slice the day into pieces too small for deep work. Where you have any say, clustering them into one part of the day protects a usable block in the other part — two hours of unbroken time is worth more than four separate half-hours.",
      fa: "جلسات بیشتر از مدت‌شان هزینه دارند چون روز را به تکه‌هایی خرد می‌کنند که برای کار عمیق کوچک‌اند. هرجا اختیاری داری، جمع‌کردنشان در یک بخش روز، یک بلوک قابل‌استفاده در بخش دیگر حفظ می‌کند — دو ساعت پیوسته از چهار نیم‌ساعت جدا ارزش بیشتری دارد.",
      ar: "الاجتماعات تكلّف أكثر من مدتها لأنها تقطع اليوم إلى قطع أصغر من أن تكفي للعمل العميق. حيث يكون لك أي رأي، فتجميعها في جزء واحد من اليوم يحمي كتلة قابلة للاستخدام في الجزء الآخر. ساعتان متصلتان من الاجتماعات أرخص من أربعة اجتماعات موزعة على اليوم كله، حتى لو كان المجموع نفسه.",
      zh: "会议的代价大于它的时长，因为它把一天切成了小到不足以做深度工作的碎片。在你有一点话语权的地方，把它们集中到一天中的某一段，可以保住另一段里一个可用的时间块。连续两小时的会议，比分散在一整天里的四个会议更便宜，即使总时长相同。",
    },
    {
      key: 'study_technique',
      match: /\b(study|revise|revision|exam prep|memoriz|flashcard|active recall|spaced repetition)(?:s|es|ing)?\b|درس خوندن|مرور درس|امتحان|حفظ کردن|فلش کارت|دراسة|مراجعة|تحضير للامتحان|حفظ|بطاقات تعليمية|استدعاء النشط|تكرار المتباعد|学习|复习|备考|背诵|记忆卡|主动回忆|间隔重复/i,
      en: "Testing yourself beats re-reading by a wide margin in the learning literature, and spacing sessions out beats cramming them together — both feel harder, which is exactly why they work better. Re-reading feels productive because it is fluent, not because it is durable.",
      fa: "در پژوهش‌های یادگیری، آزمودن خودت با اختلاف زیاد از بازخوانی بهتر است، و پخش‌کردن جلسات از فشرده‌کردنشان بهتر — هر دو سخت‌تر حس می‌شوند، و دقیقاً به همین دلیل بهتر جواب می‌دهند. بازخوانی حس مفیدبودن می‌دهد چون روان است، نه چون پایدار است.",
      ar: "اختبار نفسك يتفوق على إعادة القراءة بفارق كبير في أدبيات التعلّم، وتوزيع الجلسات يتفوق على حشرها معا — وكلاهما يبدو أصعب، وهذا بالضبط سبب نجاحهما أكثر. إعادة القراءة تعطي شعورا بالإلمام يُخطئ المرء في قراءته كمعرفة. أغلق الملاحظات واكتب ما تتذكره؛ الفراغات هي خطتك الدراسية.",
      zh: "在学习研究文献中，自我测验大幅胜过重读，而把学习分散开也胜过集中突击——两者都感觉更难，而这恰恰是它们更有效的原因。重读会带来一种熟悉感，人们容易把它误读成掌握。合上笔记，写下你记得的内容；那些空白就是你的复习计划。",
    },
    {
      key: 'exam_stress',
      match: /\b(exam stress|test anxiety|before (an|the) exam|finals week)(?:s|es|ing)?\b|استرس امتحان|اضطراب امتحان|شب امتحان|توتر الامتحان|قلق الاختبار|قبل الامتحان|أسبوع الامتحانات|考试压力|考前焦虑|考试焦虑|期末周/i,
      en: "I can speak to the habit side of this, not the clinical side. What the data here supports: short sleep and fragmented attention both travel with higher reported stress, and both get worse in exam weeks precisely when they cost most. Protecting sleep during a heavy week usually buys back more usable hours than the extra late-night studying takes.",
      fa: "می‌توانم درباره‌ی سمت عادت‌ها حرف بزنم، نه سمت بالینی. آنچه داده‌ی اینجا پشتیبانی می‌کند: خواب کوتاه و توجه تکه‌تکه هر دو با استرس گزارش‌شده‌ی بالاتر همراه‌اند، و هر دو دقیقاً در هفته‌های امتحان بدتر می‌شوند که بیشترین هزینه را دارند. محافظت از خواب در یک هفته‌ی سنگین معمولاً ساعت‌های قابل‌استفاده‌ی بیشتری برمی‌گرداند تا آنچه درس‌خواندن تا دیروقت می‌گیرد.",
      ar: "أستطيع الحديث عن جانب العادات هنا، لا الجانب العلاجي. ما تدعمه البيانات هنا: قصر النوم وتفتت الانتباه يسافران معا مع توتر مُبلَّغ أعلى، وكلاهما يسوء في أسبوع الامتحانات تحديدا — وهو الوقت الذي يكون فيه النوم أول ما يُقتطع. الليلة الكاملة قبل الامتحان تتفوق عادة على الساعات الإضافية من المراجعة. وإن كان القلق أكبر من ذلك، فذلك حديث يستحق شخصا مؤهلا.",
      zh: "这里我可以谈习惯层面，不谈临床层面。本项目数据支持的是：睡眠不足和注意力碎片化都与更高的自我报告压力同行，而两者在考试周恰恰会变得更糟——那正是睡眠最先被牺牲的时候。考前睡一个完整的觉，通常胜过多复习的那几个小时。如果焦虑超出了这个范围，那是值得找专业人士谈的事。",
    },
    {
      key: 'research_rabbit_hole',
      match: /\b(rabbit hole|too many tabs|\d+ tabs|tabs open|open tab|wikipedia hole|lost hours online)(?:s|es|ing)?\b|تب زیاد|گم شدن در اینترنت|چاه خرگوش|متاهة البحث|تبويبات كثيرة|علامات تبويب مفتوحة|أضعت ساعات على الإنترنت|标签页太多|开了很多标签|维基百科 迷路|网上耗了几小时|越查越远|تب\S*\s*(زیاد|باز)|标签页/i,
      en: "Open tabs are deferred decisions, and thirty of them is thirty small unfinished obligations sitting in your attention. A written question before you start — one sentence, what am I actually looking for — gives you something to check the next click against, which is what stops the drift.",
      fa: "تب‌های باز تصمیم‌های به‌تعویق‌افتاده‌اند، و سی تا از آن‌ها یعنی سی تعهد کوچک نیمه‌کاره که در توجهت نشسته‌اند. یک سؤال نوشته‌شده قبل از شروع — یک جمله، دقیقاً دنبال چه هستم — چیزی به تو می‌دهد که کلیک بعدی را با آن بسنجی، و همین است که از انحراف جلوگیری می‌کند.",
      ar: "التبويبات المفتوحة قرارات مؤجلة، وثلاثون منها ثلاثون التزاما صغيرا غير منته جالسا في انتباهك. سؤال مكتوب قبل أن تبدأ — جملة واحدة، ما الذي أبحث عنه فعلا — يعطيك شيئا تقيس به ما إذا كان التبويب التالي يخدمه. وعند الانتهاء، أغلق كل شيء لا يجيب عليه، حتى المثير للاهتمام.",
      zh: "开着的标签页是被推迟的决定，三十个标签页就是三十件小小的、未完成的义务停在你的注意力里。开始之前写下一个问题——一句话，我到底在找什么——就给了你一个尺子，用来判断下一个标签页是否服务于它。做完之后，把所有不回答这个问题的标签都关掉，哪怕它很有意思。",
    },
    {
      key: 'background_noise',
      match: /\b(background music|lofi|white noise|noisy office|headphone(s)? (to|for) focus)(?:s|es|ing)?\b|موسیقی پس‌زمینه|نویز سفید|محیط شلوغ کار|موسيقى خلفية|ضوضاء بيضاء|مكتب صاخب|سماعات للتركيز|背景音乐|白噪音|办公室吵|戴耳机专注|听歌工作/i,
      en: "Steady, familiar and lyric-free audio tends to interfere least with work that involves language; anything with words competes for the same channel you are reading or writing with. The honest test is your own output, not how good the playlist feels.",
      fa: "صدای یکنواخت، آشنا و بی‌کلام معمولاً کمترین تداخل را با کارِ زبانی دارد؛ هر چیزی که کلام دارد برای همان کانالی رقابت می‌کند که با آن می‌خوانی یا می‌نویسی. آزمون صادقانه خروجی خودت است، نه اینکه پلی‌لیست چقدر خوب حس می‌شود.",
      ar: "الصوت الثابت والمألوف والخالي من الكلمات يتدخل عادة بأقل قدر في العمل الذي يتضمن اللغة؛ أي شيء فيه كلمات ينافس على نفس القناة التي تقرأ أو تكتب بها. الاختبار الصادق هو نتاجك لا شعورك: جرّب جلستين متطابقتين، واحدة بكلمات وواحدة بدونها، وانظر أيهما أنجز أكثر.",
      zh: "稳定、熟悉、没有歌词的声音，通常对涉及语言的工作干扰最小；任何带词的东西都会和你正在阅读或写作所用的同一条通道竞争。诚实的检验是你的产出而不是你的感觉：做两次条件相同的时段，一次有歌词一次没有，看哪一次完成得更多。",
    },

    /* ---------------------------------------------------------------
       Social media & online life
       --------------------------------------------------------------- */
    {
      key: 'doomscrolling',
      match: /\b(doom.?scroll|bad news|news anxiety|keep reading (the )?news|can'?t stop reading)(?:s|es|ing)?\b|اخبار بد|اضطراب خبر|مدام خبر می‌خونم|تمرير الكارثي|أخبار سيئة|قلق الأخبار|لا أتوقف عن قراءة الأخبار|أتصفح باستمرار|تصفح متواصل|刷负面新闻|坏消息|新闻焦虑|一直刷新闻|停不下来刷/i,
      en: "Following distressing news past the point of being informed is a pattern that feeds itself: the discomfort makes you look for resolution, and the feed always has more. A fixed time and a fixed source turns it back into being informed, which is the part that was actually useful.",
      fa: "دنبال‌کردن اخبار ناراحت‌کننده بیش از حدِ باخبرشدن، الگویی است که خودش را تغذیه می‌کند: ناراحتی وادارت می‌کند دنبال حل‌شدن بگردی، و فید همیشه بیشتر دارد. یک زمان مشخص و یک منبع مشخص، آن را به باخبرشدن برمی‌گرداند، که همان بخش واقعاً مفید بود.",
      ar: "متابعة الأخبار المُقلِقة إلى ما بعد نقطة أن تصبح مطّلعا نمط يغذي نفسه: الانزعاج يجعلك تبحث عن حل، والشبكة لديها دائما المزيد. وقت ثابت ومصدر ثابت مرة في اليوم يبقيك مطّلعا بالفعل بينما يزيل التمرير غير المحدد. الشيء الذي يجعل هذا أسوأ بشكل موثوق هو فعله في السرير.",
      zh: "把令人不安的新闻一直看到早已超过知情所需的程度，是一种自我喂养的模式：不适让你去寻找一个结论，而信息流总还有更多。每天固定一个时间、固定一个来源，能让你真正保持知情，同时去掉无限的滑动。有一件事会可靠地让它更糟：在床上做这件事。",
    },
    {
      key: 'validation_likes',
      match: /\b(like(s)? (count|on my)|validation|how many likes|engagement|follower count)(?:s|es|ing)?\b|تعداد لایک|تایید گرفتن|فالوور|درگیری پست|عدد الإعجابات|تقدير|كم إعجابا|تفاعل|عدد المتابعين|点赞数|多少赞|认可|互动数|粉丝数/i,
      en: "Checking a post repeatedly after publishing it is the mechanism working as designed — unpredictable feedback is what makes it hard to leave alone. Deciding before you post that you will look once, later, removes the loop without requiring you to care less.",
      fa: "چک‌کردن مکرر یک پست بعد از انتشار، همان مکانیزمی است که طراحی شده — بازخورد غیرقابل‌پیش‌بینی همان چیزی است که رهاکردنش را سخت می‌کند. تصمیم‌گرفتن قبل از انتشار که «یک بار، بعداً» نگاه می‌کنی، این چرخه را حذف می‌کند بدون اینکه لازم باشد کمتر اهمیت بدهی.",
      ar: "التحقق من منشور مرارا بعد نشره هو الآلية تعمل كما صُمّمت — فالتغذية الراجعة غير المتوقعة هي ما يجعل تركه صعبا. أن تقرر قبل النشر أنك ستنظر مرة واحدة لاحقا، ثم تفعل ذلك، يعيد القرار إليك. الرقم يقيس التوقيت والخوارزمية أكثر بكثير مما يقيس قيمة ما قلته.",
      zh: "发布之后反复查看，是这套机制按设计在运行——正是不可预测的反馈让人难以放下。在发布之前就决定你稍后只看一次，然后照做，就把决定权拿回来了。那个数字衡量的，更多是发布时间和算法，而不是你说的话的价值。",
    },
    {
      key: 'unfollowing',
      match: /\b(unfollow|mute (someone|account)|curate (my )?feed|clean up (my )?feed)(?:s|es|ing)?\b|آنفالو|میوت کردن|پاکسازی فید|إلغاء المتابعة|كتم حساب|تنظيم متابعاتي|ترتيب الشبكة|取关|屏蔽某人|静音账号|整理关注|清理信息流/i,
      en: "Muting is usually better than unfollowing for people you know: it changes what you see without becoming a social event. The useful filter is simple — after this account, do you generally feel informed, or just worse? You are allowed to act on that answer.",
      fa: "برای کسانی که می‌شناسی، میوت‌کردن معمولاً از آنفالو بهتر است: چیزی که می‌بینی را تغییر می‌دهد بدون اینکه به یک رویداد اجتماعی تبدیل شود. فیلتر مفید ساده است — بعد از این اکانت، عموماً حس باخبرشدن داری یا فقط حس بدتری؟ اجازه داری بر اساس همان جواب عمل کنی.",
      ar: "الكتم عادة أفضل من إلغاء المتابعة لمن تعرفهم: يغيّر ما ترى دون أن يصبح حدثا اجتماعيا. المرشّح المفيد بسيط — بعد هذا الحساب، هل تشعر عموما بأنك مطّلع أم بأنك أسوأ حالا؟ لا حاجة لأن يكون الحكم عادلا على صاحب الحساب؛ إنه شبكتك أنت.",
      zh: "对认识的人来说，静音通常比取关更好：它改变了你看到的内容，而不会变成一件社交事件。有用的筛子很简单——看完这个账号之后，你通常觉得更知情，还是更糟？这个判断不需要对账号主人公平；这是你的信息流。",
    },
    {
      key: 'group_chats',
      match: /\b(group chat|whatsapp group|telegram group|too many messages|reply pressure)(?:s|es|ing)?\b|گروه چت|گروه واتساپ|گروه تلگرام|فشار جواب دادن|محادثة جماعية|مجموعة واتساب|مجموعة تلجرام|رسائل كثيرة|ضغط الرد|群聊|微信群|群消息太多|回复压力|محادث\S*\s*جماعي|جماعية تزعج/i,
      en: "Group chats generate obligation out of proportion to their content, because every message looks like it might need you. Muting a group is not leaving it — the messages are still there when you choose to look, which is the difference between reading and being summoned.",
      fa: "گروه‌های چت تعهدی می‌سازند که با محتوایشان تناسبی ندارد، چون هر پیام به‌نظر می‌رسد ممکن است به تو نیاز داشته باشد. میوت‌کردن یک گروه، ترک‌کردنش نیست — پیام‌ها هنوز آنجا هستند وقتی خودت انتخاب کنی نگاه کنی، و همین تفاوتِ خواندن با احضارشدن است.",
      ar: "المحادثات الجماعية تولّد التزاما غير متناسب مع محتواها، لأن كل رسالة تبدو كأنها قد تحتاجك. كتم مجموعة ليس مغادرتها — الرسائل لا تزال هناك حين تختار أن تنظر، وهذا الفرق هو كل شيء. الاختبار: هل تفتحها لأنك تريد أن تعرف، أم لأن الشارة موجودة؟",
      zh: "群聊产生的义务感与它的内容并不成比例，因为每条消息看起来都像可能需要你。把一个群静音并不等于退出——你选择去看的时候消息都还在，而这个区别就是全部。检验方法：你打开它是因为你想知道，还是因为那个红点在？",
    },
    {
      key: 'reply_pressure',
      match: /\b(reply (fast|immediately|right away)|left on read|seen (message|receipt)|response time)(?:s|es|ing)?\b|سریع جواب دادن|سین کردن|تیک آبی|زمان پاسخ|الرد فورا|الرد بسرعة|تمت القراءة|وقت الاستجابة|إشعار القراءة|马上回复|秒回|已读不回|回复速度|已读/i,
      en: "The expectation of instant replies is mostly assumed rather than stated, and it is usually looser than people fear. Answering in batches a few times a day is rarely noticed by anyone but you — and where it genuinely matters, saying when you check messages sets the expectation instead of guessing at it.",
      fa: "انتظارِ پاسخ آنی بیشتر فرض‌شده است تا گفته‌شده، و معمولاً شُل‌تر از آن است که مردم می‌ترسند. جواب‌دادن دسته‌ای چند بار در روز به‌ندرت جز خودت به چشم کسی می‌آید — و آنجا که واقعاً مهم است، گفتنِ اینکه چه ساعتی پیام‌ها را چک می‌کنی، انتظار را تعیین می‌کند به‌جای حدس‌زدنش.",
      ar: "توقع الردود الفورية مفترض أكثر مما هو معلن، وهو عادة أرخى مما يخشاه الناس. الرد على دفعات بضع مرات في اليوم لا يلاحظه أحد غالبا إلا أنت — وحين يكون شيء عاجلا فعلا، فالناس عادة يقولون ذلك. إن ساعد الأمر، فقُل مرة واحدة صراحة إنك تتحقق من الرسائل في أوقات محددة.",
      zh: "对即时回复的期待，多半是被假设出来的而不是被明说的，而它通常比人们担心的要宽松。每天分几次成批回复，除了你自己往往没人注意——而当真有急事时，人们通常会说出来。如果有帮助，就明确说一次：你在固定的时间查看消息。",
    },
    {
      key: 'short_video',
      match: /\b(reels|shorts|tiktok feed|short video|swipe up|for you page|fyp)(?:s|es|ing)?\b|ریلز|شورتس|ویدیو کوتاه|صفحه برای تو|ريلز|شورتس|فيديو قصير|صفحة لك|تمرير سريع|短视频|抖音|快手|刷视频|推荐页|上下滑/i,
      en: "Short-video feeds remove every natural stopping point: each item ends before you have decided to continue, so continuing is the default rather than a choice. Setting the stopping condition before you open it — a count, or a timer you let interrupt you — puts the decision back where you can make it.",
      fa: "فیدهای ویدیو کوتاه هر نقطه‌ی توقف طبیعی را حذف می‌کنند: هر مورد قبل از اینکه تصمیم به ادامه بگیری تمام می‌شود، پس ادامه‌دادن پیش‌فرض است نه انتخاب. تعیین شرط توقف قبل از بازکردنش — یک تعداد، یا تایمری که بگذاری کارت را قطع کند — تصمیم را به جایی برمی‌گرداند که می‌توانی بگیری‌اش.",
      ar: "شبكات الفيديو القصير تزيل كل نقطة توقف طبيعية: كل مقطع ينتهي قبل أن تقرر المتابعة، فتصبح المتابعة هي الافتراضي لا الخيار. تحديد شرط التوقف قبل أن تفتح — عدد أو منبّه — يعيد نقطة القرار التي أزال التصميم. الفرق بين عشر دقائق وساعة هنا نادرا ما يكون قرارا.",
      zh: "短视频信息流取消了每一个自然的停止点：每一条都在你决定继续之前就结束了，于是继续成了默认，而不是一个选择。在打开之前就设定停止条件——一个数量，或一个提醒——把设计所取消的那个决定点还回来。在这里，十分钟和一小时之间的差别，很少是一个决定。",
    },
    {
      key: 'algorithm_awareness',
      match: /\b(algorithm|recommended (for me|content)|why am i seeing|feed shows me)(?:s|es|ing)?\b|الگوریتم|محتوای پیشنهادی|چرا این رو می‌بینم|خوارزمية|موصى لي|لماذا أرى هذا|شبكة تعرض لي|算法|推荐内容|为什么给我看|信息流推给我/i,
      en: "A feed is optimised for time spent, not for how you feel afterwards — those two come apart most sharply late at night. Knowing that does not make it stop working, but it does reframe a long session as a design outcome rather than a personal failing, which makes design-level fixes the obvious response.",
      fa: "یک فید برای زمانِ صرف‌شده بهینه شده، نه برای اینکه بعدش چه حسی داری — و این دو، شب‌های دیروقت بیشترین فاصله را می‌گیرند. دانستنش باعث نمی‌شود از کار بیفتد، ولی یک نشست طولانی را از «نقص شخصی» به «نتیجه‌ی طراحی» بازقالب می‌کند، و همین اصلاح‌های سطح‌طراحی را پاسخ بدیهی می‌کند.",
      ar: "الشبكة مُحسَّنة للوقت المُنفَق لا لكيف تشعر بعدها — وهذان الأمران يتباعدان بأشد صورة في وقت متأخر من الليل. معرفة ذلك لا تجعلها تتوقف عن العمل، لكنها تعيد تأطير الجلسة الطويلة كنتيجة تصميم لا كفشل شخصي. وهذا التأطير مفيد عمليا: أنت تغيّر الإعداد، لا تلوم نفسك.",
      zh: "信息流是为停留时长而优化的，而不是为你之后的感受而优化的——这两者在深夜分歧最明显。知道这一点并不会让它停止起作用，但它把一次长时间的使用重新框定为设计的结果，而不是个人的失败。这个框定在实践上是有用的：你去改设置，而不是责怪自己。",
    },
    {
      key: 'social_break',
      match: /\b(social media break|quit social|delete instagram|deactivate|log off for a while)(?:s|es|ing)?\b|ترک شبکه اجتماعی|حذف اینستا|فاصله از شبکه‌ها|استراحة من وسائل التواصل|أترك التواصل الاجتماعي|أحذف إنستغرام|تعطيل الحساب|أسجل الخروج لفترة|社交媒体休息|戒社交媒体|退出社交|删掉微博|停用一段时间|离线一阵/i,
      en: "Short, defined breaks tend to work better than open-ended quitting, because an indefinite ban invites a single slip to end the whole attempt. A week, with a named reason and a plan for what fills the gap, gives you real information about what you actually missed versus what you only missed the reflex of.",
      fa: "فاصله‌های کوتاه و مشخص معمولاً بهتر از ترکِ بی‌پایان جواب می‌دهند، چون یک ممنوعیت نامحدود دعوت می‌کند که یک لغزش کل تلاش را تمام کند. یک هفته، با دلیلی مشخص و برنامه‌ای برای پرکردن جای خالی، اطلاعات واقعی می‌دهد که دلت برای چه چیزی تنگ شد در برابر چیزی که فقط دلت برای رفلکسش تنگ شده بود.",
      ar: "الاستراحات القصيرة المحددة تعمل عادة أفضل من الترك المفتوح، لأن المنع غير محدد المدة يجعل زلة واحدة تنهي المحاولة كلها. أسبوع، بسبب مُسمّى وخطة لما يملأ الفراغ، يعلّمك أكثر مما يعلّمه وعد غامض بالتوقف للأبد. الجزء الذي ينساه الناس هو الخطة البديلة: الفراغ يُملأ بشيء، فاختره أنت.",
      zh: "短而明确的休息通常比无限期地戒断更有效，因为没有期限的禁止会让一次失手就终结整个尝试。一周时间、一个说得出的理由、以及一个填补空白的计划，比一个模糊的永远不再的承诺能教你更多。人们忘掉的那部分是替代计划：空白总会被什么填上，那就由你来选。",
    },
    {
      key: 'parasocial',
      match: /\b(parasocial|feel like i know (them|him|her)|creator|influencer|streamer)(?:s|es|ing)?\b|شبه‌اجتماعی|حس نزدیکی با سلبریتی|اینفلوئنسر|استریمر|شبه اجتماعي|أشعر أني أعرفهم|صانع محتوى|مؤثر|بثاث|准社交|单向关系|感觉认识他|博主|网红|主播/i,
      en: "One-sided closeness with people you watch a lot is ordinary, not strange — sustained attention is what the brain normally uses to mark someone as close. It is worth noticing only when it starts substituting for two-way contact, since the reciprocal kind is what the loneliness signal in this app actually responds to.",
      fa: "نزدیکیِ یک‌طرفه با کسانی که زیاد تماشا می‌کنی عادی است، نه عجیب — توجه پیوسته همان چیزی است که مغز معمولاً برای نزدیک‌شمردن کسی استفاده می‌کند. فقط وقتی ارزش توجه دارد که جای ارتباط دوطرفه را بگیرد، چون سیگنال تنهایی در این اپ به نوعِ متقابل واکنش می‌دهد.",
      ar: "القرب أحادي الجانب مع أشخاص تشاهدهم كثيرا أمر عادي لا غريب — فالانتباه المستمر هو ما يستخدمه الدماغ عادة ليضع أحدا في خانة المقربين. يستحق الملاحظة فقط عندما يبدأ في استبدال العلاقات المتبادلة لا في الإضافة إليها، أو حين تكون حياة شخص لا يعرفك مصدرا للمقارنة. الاختبار ليس كم تشاهد، بل ما يحتله ذلك.",
      zh: "对你经常观看的人产生单向的亲近感，是普通的事而不是奇怪的事——持续的注意力，本来就是大脑用来把某人标记为亲近的方式。它只在开始替代而不是补充双向关系时，或者当一个并不认识你的人的生活成了你的比较对象时，才值得留意。检验的标准不是你看了多少，而是它占掉了什么。",
    },
  ];

  window.DWCoachKnowledge.register(TOPICS, { priority: 10 });
})();
