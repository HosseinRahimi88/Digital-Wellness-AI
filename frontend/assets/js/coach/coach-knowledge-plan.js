/*
  Knowledge base: the weekly plan's own machinery.

  Why this file exists
  --------------------
  The weekly plan grew a set of rules that change what the app does to
  you - one main check-in a day, days that have to be walked in order, a
  day that can be marked an exception, a missed day that costs a badge,
  a violation ledger when the badges run out, and four colours on the
  dashboard that each mean something different. Not one of them was
  answerable. Asked "why was a badge taken away from me?", the coach
  reached for the nearest thing it did know and explained SHAP - which is
  worse than not answering, because it sounds like an answer.

  These are the rules that cost the user something. A rule that takes a
  badge away has to be explainable on demand, in the user's own
  language, or it reads as the app being arbitrary.

  Every answer below is checked against the service that implements it:
    · services/wellness/day_status_service.py    - the four colours and the halves
    · services/wellness/violation_service.py     - badge spent, then violation
    · services/wellness/day_decision_service.py  - exception vs counted, 0.25
    · services/wellness/plan_lock_service.py     - one plan per ISO week
    · services/wellness/plan_progress_service.py - ticks per (week, day, task)

  Same flat-alternatives rule as coach-knowledge-app.js: coach-nlu.js's
  extractKeywords() splits a regex source on EVERY "|" with no bracket
  awareness, so a nested group produces fragments that match nothing.
  Every alternative here is written out in full.
*/
(function () {
  if (!window.DWCoachKnowledge || !window.DWCoachKnowledge.register) return;

  const TOPICS = [

    // =================== The day, and its colours ===================
    {
      key: 'plan_day_colours',
      match: /\b(what do the colours mean|what do the colors mean|why is that day red|why is that day grey|why is that day gray|why is that day orange|what does the red day mean|what does the grey day mean|what does the orange day mean|colour of the day|color of the day)(?:s|es|ing)?\b|رنگ روزها یعنی چه|چرا آن روز قرمز است|چرا آن روز خاکستری است|چرا آن روز نارنجی است|معنی رنگ روز|ماذا تعني ألوان الأيام|لماذا هذا اليوم أحمر|لماذا هذا اليوم رمادي|لماذا هذا اليوم برتقالي|日期的颜色是什么意思|那天为什么是红色|那天为什么是灰色|那天为什么是橙色/i,
      en: "A day is scored on two independent halves: did you log the main check-in, and did you do that day's plan task. Green means both. Orange means you checked in but left the task undone. Grey means you did the work but never logged the day. Red means neither. Orange and grey both cost half a point, deliberately equal - one loses the app its data, the other loses you your plan, and neither is worse than the other. Red costs a full point, because only then is there nothing to build on. Today is shown in its current colour but never charged: it is not over.",
      fa: "هر روز روی دو نیمه‌ی مستقل سنجیده می‌شود: بررسی اصلی آن روز را ثبت کردی، و تمرین آن روز از برنامه را انجام دادی. سبز یعنی هر دو. نارنجی یعنی ثبت کردی ولی تمرین را انجام ندادی. خاکستری یعنی تمرین را انجام دادی ولی روز را ثبت نکردی. قرمز یعنی هیچ‌کدام. نارنجی و خاکستری هر دو نیم امتیاز منفی دارند و این برابری عمدی است — یکی داده را از برنامه می‌گیرد و دیگری برنامه را از تو، و هیچ‌کدام بدتر از آن یکی نیست. قرمز یک امتیاز کامل منفی دارد، چون فقط آنجاست که هیچ چیزی برای ساختن روی آن نمانده. امروز با رنگ فعلی‌اش نشان داده می‌شود ولی هرگز جریمه نمی‌شود: هنوز تمام نشده.",
      ar: "يُقيَّم اليوم على نصفين مستقلين: هل سجّلت الفحص الرئيسي، وهل نفّذت مهمة ذلك اليوم من الخطة. الأخضر يعني الاثنين معاً. البرتقالي يعني أنك سجّلت لكنك تركت المهمة. الرمادي يعني أنك نفّذت العمل لكنك لم تسجّل اليوم. الأحمر يعني لا هذا ولا ذاك. البرتقالي والرمادي يكلّفان نصف نقطة، وتساويهما مقصود — أحدهما يفقد التطبيق بياناته والآخر يفقدك خطتك، وليس أحدهما أسوأ من الآخر. الأحمر يكلّف نقطة كاملة، لأنه وحده ما لا يترك شيئاً يُبنى عليه. أما اليوم الجاري فيُعرض بلونه الحالي ولا يُحاسَب أبداً: فهو لم ينتهِ بعد.",
      zh: "一天是按两个互相独立的部分来评的：你有没有记录当天的主要打卡，以及有没有完成当天的计划任务。绿色表示两件都做了。橙色表示你打了卡，但任务没做。灰色表示你做了任务，却没有记录当天。红色表示两件都没有。橙色和灰色各扣半分，这种相等是刻意的——一个让应用失去数据，另一个让你失去计划，谁也不比谁更糟。红色扣满一分，因为只有那种情况才什么都没留下。今天会按当前颜色显示，但永远不会被扣分：它还没结束。",
    },

    {
      key: 'plan_penalty_and_score',
      match: /\b(do those penalties lower my score|does a missed day lower my score|is the penalty part of my score|does the penalty affect my wellness score)(?:s|es|ing)?\b|آن امتیاز منفی نمره‌ام را کم میکند|جریمه روی امتیاز سلامتم اثر دارد|روز از دست رفته نمره را کم میکند|هل تخفض تلك الخصومات درجتي|هل الخصم جزء من رقم عافيتي|هل الخصم جزء من رقم عافیتی|هل يؤثر الخصم على درجة العافية|那些扣分会降低我的分数吗|错过的一天会拉低分数吗|扣分算在我的健康数值里吗|扣分会影响健康分数吗/i,
      en: "No, and that is on purpose. The wellness score is the model's reading of your habits from the numbers you entered. The day penalties are a record of how you engaged with the app. Folding one into the other would make a single number mean two different things, and you could no longer tell a genuinely worse week from a week you forgot to log. So the penalty total is reported next to the day strip, and never subtracted from the score. Where a missed day actually costs you something is the plan's own ledger: a badge, and then a violation.",
      fa: "نه، و این عمدی است. امتیاز سلامت، خوانش مدل از عادت‌های توست بر اساس عددهایی که وارد کرده‌ای. امتیازهای منفیِ روز، ثبتِ نحوه‌ی تعامل تو با برنامه است. قاطی‌کردن این دو باعث می‌شد یک عدد دو معنی متفاوت بدهد و دیگر نمی‌شد هفته‌ای که واقعاً بدتر بوده را از هفته‌ای که یادت رفته ثبت کنی تشخیص داد. پس جمع امتیاز منفی کنار نوار روزها گزارش می‌شود و هرگز از امتیاز کم نمی‌شود. جایی که یک روز از دست رفته واقعاً هزینه دارد، دفترِ خود برنامه است: یک نشان، و بعد یک تخلف.",
      ar: "لا، وهذا مقصود. درجة العافية هي قراءة النموذج لعاداتك من الأرقام التي أدخلتها. أما خصومات الأيام فهي سجل لكيفية تفاعلك مع التطبيق. ودمج أحدهما في الآخر يجعل رقماً واحداً يعني أمرين مختلفين، فلا تعود تميّز أسبوعاً أسوأ فعلاً عن أسبوع نسيت أن تسجّله. لذا يُعرض مجموع الخصم بجانب شريط الأيام ولا يُطرح من الدرجة أبداً. أما حيث يكلّفك اليوم الضائع شيئاً فعلاً فهو دفتر الخطة نفسه: شارة، ثم مخالفة.",
      zh: "不会，而且这是刻意的。健康分数是模型根据你填入的数字对你习惯的判读；日扣分则是你与这个应用互动情况的记录。把两者合在一起，会让同一个数字同时表达两件事，你也就再分不清「这周真的更差」和「这周忘了记录」。所以扣分合计显示在日期条旁边，永远不会从分数里减掉。错过一天真正付出代价的地方，是计划自己的账本：先是一枚徽章，然后是一次违规。",
    },

    // ================ Missed days, badges, violations ================
    {
      key: 'plan_missed_day',
      match: /\b(what happens if i miss a day|what if i miss a day|i missed a day of the plan|i missed some days|what happens when i skip a day|i skipped a plan day)(?:s|es|ing)?\b|اگر یک روز را از دست بدهم چه میشود|یک روز برنامه را انجام ندادم|چند روز را جا انداختم|اگر روزی را رد کنم چه میشود|ماذا يحدث إن فوّت يوماً|فوّتُّ يوماً من الخطة|فوّتُّ عدة أيام|错过一天会怎样|漏掉计划里的一天|我漏了计划里的一天|我漏了好几天/i,
      en: "A day of the plan that goes by undone is charged once, after its date has passed - never on the day itself, and never twice for the same day. The first thing it takes is a badge you had earned: it is spent paying for the day. If you have no badges left, the day is recorded as a violation instead. Violations do not accumulate against you forever: while any are outstanding, a newly earned badge clears one instead of joining your wall. So the way back is the ordinary one - earn badges the way you already did, and they pay the debt down.",
      fa: "روزی از برنامه که انجام‌نشده می‌گذرد، یک بار و پس از گذشتن تاریخش حساب می‌شود — هرگز در همان روز، و هرگز دو بار برای یک روز. اولین چیزی که می‌گیرد، نشانی است که به دست آورده بودی: خرج جبران آن روز می‌شود. اگر دیگر نشانی نمانده باشد، آن روز به‌جایش به‌عنوان تخلف ثبت می‌شود. تخلف‌ها تا ابد روی هم جمع نمی‌شوند: تا وقتی تخلفی باز است، نشانی که تازه به دست می‌آوری به‌جای نشستن روی دیوارت، یکی از آن‌ها را پاک می‌کند. پس راه برگشت همان راه همیشگی است — نشان به دست بیاور، همان‌طور که قبلاً می‌آوردی، و بدهی را کم می‌کنند.",
      ar: "يوم من الخطة يمرّ دون تنفيذ يُحاسَب مرة واحدة، بعد انقضاء تاريخه — لا في اليوم نفسه، ولا مرتين لليوم ذاته. أول ما يأخذه شارة كنت قد كسبتها: تُصرف تعويضاً عن ذلك اليوم. وإن لم تبقَ لديك شارات، سُجّل اليوم مخالفةً بدلاً من ذلك. والمخالفات لا تتراكم عليك إلى الأبد: ما دامت واحدة قائمة، فإن شارة تكسبها حديثاً تمسح واحدة بدل أن تنضم إلى جدارك. فطريق العودة هو الطريق المعتاد — اكسب الشارات كما كنت تفعل، وهي تسدّد الدين.",
      zh: "计划里没有完成的一天，会在它过去之后被结算一次——绝不在当天结算，同一天也绝不结算两次。它首先拿走的是你已经赚到的一枚徽章：那枚徽章被花掉，用来抵这一天。如果你已经没有徽章了，这一天就会被记为一次违规。违规不会永远累积：只要还有未清的违规，你新赚到的徽章就会去清掉一次，而不是挂上你的徽章墙。所以回来的路还是那条老路——照你原来的方式赚徽章，它们会把欠账还掉。",
    },

    {
      key: 'plan_what_is_violation',
      match: /\b(what is a violation|what does violation mean|what are violations|why do i have a violation|violations in the plan)(?:s|es|ing)?\b|تخلف یعنی چه|تخلف چیست|چرا تخلف دارم|تخلفات برنامه چیست|ما هي المخالفة|ماذا تعني المخالفة|لماذا لدي مخالفة|违规是什么意思|什么是违规|我为什么有违规/i,
      en: "A violation is a count of plan days that went by undone after your earned badges had already been spent covering earlier ones. It is a number with a way out, not a mark against you: every new badge you earn clears one before it goes on your wall. The app deliberately never phrases it as a judgement about you - it says how many days, and what clears them. You will see them in the Hall of Fame beside the badges, which is the honest place for them: the same page that shows what you kept up should show what you did not.",
      fa: "تخلف، شمارشِ روزهایی از برنامه است که انجام‌نشده گذشته‌اند، بعد از اینکه نشان‌های به‌دست‌آورده‌ات قبلاً خرج جبران روزهای قبلی شده باشند. این یک عدد است با راه خروج، نه لکه‌ای روی تو: هر نشان تازه‌ای که می‌گیری، پیش از آنکه روی دیوارت برود، یکی از آن‌ها را پاک می‌کند. برنامه عمداً هرگز آن را به‌عنوان قضاوتی درباره‌ی تو بیان نمی‌کند — می‌گوید چند روز، و چه چیزی پاکشان می‌کند. آن‌ها را در تالار افتخارات کنار نشان‌ها می‌بینی، که جای صادقانه‌شان است: همان صفحه‌ای که نشان می‌دهد چه چیزی را نگه داشته‌ای، باید نشان دهد چه چیزی را نداشته‌ای.",
      ar: "المخالفة هي عدّ لأيام الخطة التي مرّت دون تنفيذ بعد أن صُرفت شاراتك المكتسبة في تغطية أيام سابقة. إنها رقم له مخرج، لا وصمة عليك: كل شارة جديدة تكسبها تمسح واحدة قبل أن تصعد إلى جدارك. والتطبيق يتعمّد ألا يصوغها حكماً عليك — بل يقول كم يوماً، وما الذي يمحوها. تراها في قاعة المشاهير بجانب الشارات، وهو مكانها الصادق: الصفحة نفسها التي تُظهر ما حافظت عليه ينبغي أن تُظهر ما لم تحافظ عليه.",
      zh: "违规是对「计划中未完成的天数」的计数——发生在你赚到的徽章已经被拿去抵扣更早那些天之后。它是一个有出路的数字，不是给你的评价：你每赚到一枚新徽章，它会先去清掉一次违规，然后才挂上你的徽章墙。应用刻意不把它说成对你这个人的判断——它只说有多少天，以及什么能把它清掉。你会在荣誉墙上、徽章旁边看到它们，那是它们该在的地方：展示你坚持住了什么的那一页，也应该展示你没坚持住什么。",
    },

    {
      key: 'plan_badge_revoked',
      match: /\b(why was a badge taken away|why did i lose a badge|why did my badge disappear|where did my badge go|my badges are gone|badge was revoked)(?:s|es|ing)?\b|چرا نشانم گرفته شد|چرا یک نشان از دست دادم|نشانم کجا رفت|نشان هایم ناپدید شدند|چرا نشانم پس گرفته شد|لماذا سُحبت شارتي|لماذا فقدت شارة|أين ذهبت شارتي|徽章为什么被收走|我为什么少了一枚徽章|我的徽章去哪了/i,
      en: "It was spent, not deleted. A plan day that went by undone is paid for with a badge you had already earned, newest first. The history that earned it is still true and still in your record - what changed is that the badge was used as payment, so it is filtered out of your wall and marked revoked. Only public achievement badges can be spent this way. The private awareness indicators are never taken, because those name a pattern worth a look rather than something you won, and taking one away would be punishing you for noticing something.",
      fa: "خرج شد، حذف نشد. روزی از برنامه که انجام‌نشده گذشته، با نشانی که قبلاً به دست آورده بودی پرداخت می‌شود، از تازه‌ترین. تاریخچه‌ای که آن نشان را ساخت هنوز درست است و هنوز در سابقه‌ات هست — چیزی که عوض شد این است که آن نشان به‌عنوان پرداخت استفاده شد، پس از دیوارت فیلتر می‌شود و «پس‌گرفته‌شده» علامت می‌خورد. فقط نشان‌های دستاوردِ عمومی این‌طور خرج می‌شوند. شاخص‌های خصوصیِ خودآگاهی هرگز گرفته نمی‌شوند، چون آن‌ها الگویی را نام می‌برند که ارزش نگاه‌کردن دارد، نه چیزی که برده باشی؛ و گرفتنشان یعنی تنبیه‌کردنت به‌خاطر متوجه‌شدن یک چیز.",
      ar: "صُرفت، ولم تُحذف. يوم خطة مرّ دون تنفيذ يُدفع ثمنه بشارة سبق أن كسبتها، من الأحدث فالأقدم. والسجل الذي كسبها لا يزال صحيحاً ولا يزال في سِجلّك — ما تغيّر أن الشارة استُخدمت دفعاً، فرُشّحت خارج جدارك ووُسمت مسحوبة. ولا يُصرف بهذه الطريقة إلا شارات الإنجاز العلنية. أما مؤشرات الوعي الخاصة فلا تُؤخذ أبداً، لأنها تسمّي نمطاً يستحق النظر لا شيئاً ربحته، وأخذها يعني معاقبتك على أنك لاحظت شيئاً.",
      zh: "它是被花掉了，不是被删掉了。计划中未完成的一天，会用你已经赚到的徽章来支付，从最新的开始。赚到它的那段历史依然真实、依然在你的记录里——变的只是这枚徽章被当作支付使用了，所以它从你的徽章墙上被过滤掉并标记为已收回。只有公开的成就徽章会以这种方式被花掉。私密的觉察指示从不会被拿走，因为它们指出的是值得一看的模式，而不是你赢来的东西；拿走它等于因为你注意到了某件事而惩罚你。",
    },

    // ===================== How the week behaves =====================
    {
      key: 'plan_days_in_order',
      match: /\b(why must i do the days in order|why is day three locked|why cant i skip ahead|why is the next day locked|do i have to do them in order)(?:s|es|ing)?\b|چرا باید روزها را به ترتیب انجام دهم|چرا روز بعد قفل است|چرا نمیتوانم جلو بزنم|آیا باید به ترتیب باشد|لماذا يجب أن أتبع ترتيب الأيام|لماذا اليوم التالي مقفل|لماذا لا أستطيع التقدّم|为什么必须按顺序做|为什么下一天是锁住的|我可以跳过去吗/i,
      en: "Because a week done out of order is not the week the plan describes. The days build on each other: the later ones assume the earlier ones happened, so a checkmark on day five with day four untouched would be recording something that has nothing under it. Day 1 is always open, and day N+1 opens once day N is fully ticked — every task on it, not most of them. That is also the only thing that makes \"you missed a day\" mean anything: without the sequence, a skipped day is just a day you have not got to yet.",
      fa: "چون هفته‌ای که بی‌ترتیب انجام شود، آن هفته‌ای نیست که برنامه توصیف می‌کند. روزها روی هم ساخته می‌شوند: روزهای بعدی فرض می‌گیرند روزهای قبلی اتفاق افتاده‌اند، پس تیک روز پنجم وقتی روز چهارم دست‌نخورده مانده، ثبت چیزی است که زیرش خالی است. روز ۱ همیشه باز است، و روز بعدی وقتی باز می‌شود که روز قبلی کامل تیک خورده باشد — همه‌ی تمرین‌هایش، نه بیشترشان. همین است که به «یک روز را از دست دادی» معنا می‌دهد: بدون ترتیب، روزِ رد شده فقط روزی است که هنوز به آن نرسیده‌ای.",
      ar: "لأن أسبوعاً يُنفَّذ بغير ترتيبه ليس الأسبوع الذي تصفه الخطة. فالأيام يُبنى بعضها على بعض: اللاحقة تفترض أن السابقة قد حدثت، وعلامة على اليوم الخامس واليوم الرابع لم يُمسّ تسجّل شيئاً لا أساس تحته. اليوم الأول مفتوح دائماً، واليوم التالي يُفتح متى اكتمل تعليم اليوم الذي قبله — كل مهامه لا معظمها. وهذا وحده ما يجعل عبارة «فوّتَّ يوماً» ذات معنى: فبلا تسلسل، اليوم المتخطَّى مجرد يوم لم تصل إليه بعد.",
      zh: "因为打乱顺序做完的一周，并不是计划所描述的那一周。这些天是层层叠上去的：后面的天假设前面的天已经发生，所以第四天原封不动却勾掉第五天，记录的是一件下面什么都没有的事。第一天始终开放，而下一天要等前一天被完全勾完才会打开——是它的每一项任务，不是大部分。这也是「你漏了一天」这句话唯一有意义的原因：没有这个顺序，跳过的一天不过是你还没做到的一天。",
    },

    {
      key: 'plan_one_checkin_a_day',
      match: /\b(why can i only check in once a day|can i check in twice|i already checked in today|how do i change todays check in|can i edit todays check in)(?:s|es|ing)?\b|چرا روزی یک بار میتوانم ثبت کنم|میتوانم دوبار ثبت کنم|امروز قبلا ثبت کردم|چطور ثبت امروز را عوض کنم|میتوانم بررسی امروز را ویرایش کنم|لماذا تسجيل واحد في اليوم|هل أستطيع التسجيل مرتين|سجّلت اليوم بالفعل|كيف أعدّل تسجيل اليوم|为什么一天只能打卡一次|我可以打卡两次吗|我今天已经打过卡了|怎么修改今天的记录/i,
      en: "One day, one main check-in - because a day with three check-ins is not three days, and letting it count as such would quietly inflate every average, streak and trend built on top of it. What you can do is edit today's: reopen it, change what was wrong, and it replaces the day rather than adding to it. Yesterday and earlier stay as they were logged. That is the difference between correcting a record and rewriting history, and only the first one is offered.",
      fa: "یک روز، یک بررسی اصلی — چون روزی با سه بررسی، سه روز نیست، و به‌حساب‌آوردنش این‌طور، هر میانگین و رشته و روندی که رویش ساخته شده را بی‌سروصدا باد می‌کند. کاری که می‌توانی بکنی ویرایش بررسی امروز است: بازش کن، چیزی که غلط بوده را عوض کن، و جای همان روز را می‌گیرد نه اینکه به آن اضافه شود. دیروز و پیش از آن همان‌طور که ثبت شده‌اند می‌مانند. این تفاوتِ اصلاحِ یک سابقه با بازنویسی تاریخ است، و فقط اولی پیشنهاد می‌شود.",
      ar: "يوم واحد، تسجيل رئيسي واحد — لأن يوماً بثلاثة تسجيلات ليس ثلاثة أيام، واحتسابه كذلك ينفخ بهدوء كل متوسط وسلسلة واتجاه مبني فوقه. ما يمكنك فعله هو تعديل تسجيل اليوم: أعِد فتحه، وغيّر ما كان خطأ، فيحلّ محلّ اليوم بدل أن يُضاف إليه. أما الأمس وما قبله فيبقى كما سُجّل. هذا هو الفرق بين تصحيح سِجل وإعادة كتابة التاريخ، ولا يُتاح إلا الأول.",
      zh: "一天一次主要打卡——因为一天打三次卡并不等于三天，把它当成三天，会悄悄地把建立在其上的每一个平均值、连续天数和趋势都吹大。你可以做的是编辑今天这一次：重新打开它，改掉记错的地方，它会替换掉那一天，而不是往上再加一条。昨天和更早的日子则保持记录时的样子。这就是「更正一条记录」和「改写历史」的区别，而只有前者是被提供的。",
    },

    {
      key: 'plan_exception_day',
      match: /\b(what is an exception day|should i mark this day as an exception|what does marking a day unusual do|i was travelling that day|i was ill that day|unusual day)(?:s|es|ing)?\b|روز استثنا چیست|این روز را استثنا علامت بزنم|علامت زدن روز غیرعادی چه میکند|آن روز سفر بودم|آن روز مریض بودم|ما هو اليوم الاستثنائي|هل أعلّم هذا اليوم استثناءً|كنت مسافراً ذلك اليوم|كنت مريضاً ذلك اليوم|什么是例外日|要不要把这天标记为例外|把一天标记为特殊会怎样|那天我在出差|那天我生病了/i,
      en: "When a day lands outside the range your week's plan was built for, you get asked what it was, because there are two genuinely different answers and neither is a safe default. Marked an exception, it stays in your history and stays on the dashboard - it is not deleted - but it moves the week's range by a quarter of a normal day instead of a whole one. Let it count, and the plan rewrites the rest of the week around the new range, keeping the days you have already lived and their checkmarks. The reason an exception still counts for something: a day that counted for nothing would let anyone curate their own trend into a straight line.",
      fa: "وقتی روزی بیرون از بازه‌ای می‌افتد که برنامه‌ی هفته‌ات برایش ساخته شده، از تو پرسیده می‌شود آن روز چه بود، چون دو پاسخ واقعاً متفاوت وجود دارد و هیچ‌کدام پیش‌فرضِ امنی نیست. اگر استثنا علامت بخورد، در تاریخچه‌ات می‌ماند و روی داشبورد هم می‌ماند — حذف نمی‌شود — ولی بازه‌ی هفته را به‌اندازه‌ی یک‌چهارمِ یک روز عادی جابه‌جا می‌کند نه یک روز کامل. اگر بگذاری به حساب بیاید، برنامه بقیه‌ی هفته را حول بازه‌ی تازه بازنویسی می‌کند و روزهایی که قبلاً زندگی کرده‌ای و تیک‌هایشان را نگه می‌دارد. دلیل اینکه استثنا هم چیزی به حساب می‌آید: روزی که هیچ به حساب نیاید، به هر کسی اجازه می‌دهد روند خودش را به یک خط صاف تبدیل کند.",
      ar: "حين يقع يوم خارج النطاق الذي بُنيت عليه خطة أسبوعك، يُسألك ما كان ذلك اليوم، لأن هناك إجابتين مختلفتين فعلاً وليست إحداهما افتراضاً آمناً. إن وُسم استثناءً، بقي في سجلّك وبقي على لوحة التحكم — فهو لا يُحذف — لكنه يحرّك نطاق الأسبوع بمقدار ربع يوم عادي بدل يوم كامل. وإن تركته يُحتسب، أعادت الخطة كتابة بقية الأسبوع حول النطاق الجديد، مع الإبقاء على الأيام التي عشتها وعلاماتها. وسبب بقاء وزن ما للاستثناء: يوم لا يُحتسب إطلاقاً يتيح لأي أحد أن ينحت اتجاهه الخاص خطاً مستقيماً.",
      zh: "当某一天落在你这周计划所针对的区间之外时，应用会问你那天是怎么回事，因为有两个真正不同的答案，而且哪一个都不是安全的默认值。标记为例外，它仍留在你的历史里、仍显示在仪表盘上——它不会被删除——但它对本周区间的影响只有正常一天的四分之一。让它照常计入，计划就会围绕新的区间重写本周剩下的日子，同时保留你已经过完的那些天和它们的对勾。例外之所以仍然算一点：一个完全不算数的日子，会让任何人都能把自己的趋势修成一条直线。",
    },

    {
      key: 'plan_locked_to_the_week',
      match: /\b(why doesnt my plan change|why is my plan the same all week|my score changed but the plan did not|when does my plan update|why is the plan frozen)(?:s|es|ing)?\b|چرا برنامه‌ام عوض نمیشود|چرا برنامه تمام هفته یکی است|امتیازم عوض شد ولی برنامه نه|برنامه کی بروز میشود|چرا برنامه قفل است|لماذا لا تتغير خطتي|لماذا الخطة نفسها طوال الأسبوع|تغيّرت درجتي ولم تتغير الخطة|متى تتحدث خطتي|为什么我的计划不变|为什么整周都是同一个计划|我分数变了计划却没变|计划什么时候更新/i,
      en: "The plan is generated once for its ISO week and then served back unchanged, which is what makes it a weekly plan rather than a daily one repeated seven times. It used to regenerate from whatever prediction was newest, and two check-ins on the same day could produce two completely different plans - worse, your checkmarks bled onto tasks that no longer said the same thing, because a tick is stored against a day and a slot, not against wording. What does still update inside the week is the numbers quoted in a task, so it stays true after a new check-in. A real change of direction is deliberate: let an out-of-band day count, and the rest of the week is rewritten.",
      fa: "برنامه یک بار برای هفته‌ی ایزوی خودش ساخته می‌شود و بعد بدون تغییر پس داده می‌شود، و همین است که آن را برنامه‌ی هفتگی می‌کند نه یک برنامه‌ی روزانه که هفت بار تکرار شده. قبلاً از هر پیش‌بینی‌ای که تازه‌تر بود دوباره ساخته می‌شد و دو بررسی در یک روز می‌توانست دو برنامه‌ی کاملاً متفاوت بسازد — بدتر اینکه تیک‌هایت روی تمرین‌هایی می‌نشست که دیگر همان را نمی‌گفتند، چون تیک روی یک روز و یک جایگاه ذخیره می‌شود نه روی متن. چیزی که داخل هفته هنوز به‌روز می‌شود، عددهایی است که در متن یک تمرین آمده، تا بعد از بررسی تازه هم درست بماند. تغییر واقعیِ مسیر عمدی است: بگذار روزی که بیرون از باند افتاده به حساب بیاید، آن‌وقت بقیه‌ی هفته بازنویسی می‌شود.",
      ar: "تُولَّد الخطة مرة واحدة لأسبوعها الآيزو ثم تُقدَّم كما هي، وهذا ما يجعلها خطة أسبوعية لا خطة يومية مكرّرة سبع مرات. كانت تُعاد توليدها من أحدث تنبؤ، وقد ينتج عن تسجيلين في اليوم نفسه خطتان مختلفتان تماماً — والأسوأ أن علاماتك كانت تنزلق إلى مهام لم تعد تقول الشيء ذاته، لأن العلامة تُخزَّن مقابل يوم وموضع لا مقابل نص. أما ما يظل يتحدث داخل الأسبوع فهو الأرقام المذكورة داخل المهمة، لتبقى صحيحة بعد تسجيل جديد. وتغيير الاتجاه الحقيقي قرار صريح: دع يوماً خارج النطاق يُحتسب، فتُعاد كتابة بقية الأسبوع.",
      zh: "计划在它所属的 ISO 周里只生成一次，之后原样返回——正是这一点让它成为「每周计划」，而不是把日计划重复七遍。以前它会依据最新的那次预测重新生成，同一天打两次卡就可能产出两个完全不同的计划——更糟的是，你的对勾会串到内容已经不同的任务上，因为对勾是按「哪一天、第几项」存的，不是按文字存的。周内仍会更新的，是任务里引用的那些数字，好让它在新一次打卡后依然属实。真正的方向调整是明确的动作：让一个越界的日子照常计入，本周剩下的部分就会被重写。",
    },

    {
      key: 'plan_next_week',
      match: /\b(what happens next week|how is next weeks plan made|will i get a new plan|does the plan get harder|what about week two)(?:s|es|ing)?\b|هفته بعد چه میشود|هفته بعد چه می شود|هفته ی بعد چه می شود|برنامه هفته بعد چطور ساخته میشود|برنامه جدید میگیرم|برنامه سخت تر میشود|هفته دوم چه میشود|ماذا يحدث الأسبوع القادم|كيف تُبنى خطة الأسبوع القادم|هل أحصل على خطة جديدة|هل تصعب الخطة|下周会怎样|下周的计划怎么生成|我会拿到新计划吗|计划会变难吗/i,
      en: "A new plan is built for the new ISO week, and from week two onward it is built against your own previous week rather than from scratch. A theme you kept up carries forward at the tier you actually reached, so the week after a good week asks for a little more instead of repeating the same task; a theme that did not hold comes back at the level it did hold. That is why the plan can only get harder as fast as you actually got better - it is reading your record, not a curve someone drew.",
      fa: "برای هفته‌ی ایزوی تازه یک برنامه‌ی جدید ساخته می‌شود، و از هفته‌ی دوم به بعد بر اساس هفته‌ی قبلیِ خودت ساخته می‌شود نه از صفر. موضوعی که به آن پایبند بوده‌ای، در همان سطحی که واقعاً رسیده‌ای جلو می‌آید، پس هفته‌ی بعد از یک هفته‌ی خوب کمی بیشتر می‌خواهد نه تکرار همان تمرین؛ و موضوعی که نگرفته، در سطحی که گرفته بود برمی‌گردد. برای همین برنامه فقط به همان سرعتی سخت‌تر می‌شود که تو واقعاً بهتر شده‌ای — دارد سابقه‌ی تو را می‌خواند، نه منحنی‌ای که کسی کشیده باشد.",
      ar: "تُبنى خطة جديدة للأسبوع الآيزو الجديد، ومن الأسبوع الثاني فصاعداً تُبنى على أسبوعك السابق أنت لا من الصفر. الموضوع الذي حافظت عليه ينتقل عند المستوى الذي بلغته فعلاً، فالأسبوع الذي يلي أسبوعاً جيداً يطلب قليلاً أكثر بدل تكرار المهمة نفسها؛ والموضوع الذي لم يثبت يعود عند المستوى الذي ثبت عنده. لهذا لا تصعب الخطة إلا بقدر ما تحسّنت أنت فعلاً — فهي تقرأ سِجلّك، لا منحنى رسمه أحد.",
      zh: "新的 ISO 周会生成一份新计划，而且从第二周起，它是以你自己上一周为基础生成的，而不是从零开始。你坚持住的主题会按你实际达到的档位往前推，所以好的一周之后，下一周会多要求一点，而不是重复同一个任务；没能守住的主题，则会回到它确实守住的那个档位。这就是为什么计划变难的速度，只会和你实际变好的速度一样快——它读的是你的记录，不是谁画出来的一条曲线。",
    },

  ];

  window.DWCoachKnowledge.register(TOPICS, { priority: 10 });
})();
