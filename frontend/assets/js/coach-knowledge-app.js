/*
  App-help knowledge base: questions about the APP ITSELF, not about
  digital wellness as a topic. coach-knowledge.js and
  coach-knowledge-life.js answer "how do I sleep better"; this file
  answers "why did my CSV get rejected" and "how do I invite a friend".

  Same shape, same engine, same fuzzy-typo tolerance: each entry is
  {key, match, en, fa, ar, zh}, registered through
  window.DWCoachKnowledge.register() exactly like coach-knowledge-life.js,
  which means coach-nlu.js's classify() already covers every entry here
  for misspellings and reordered phrasing - nothing extra to wire.

  Every `match` regex below uses only FLAT top-level "|" alternatives
  (plus the safe "(?:s|es|ing)?" suffix) - never nested alternation
  groups. coach-nlu.js's extractKeywords() splits a regex's source on
  every "|" with no bracket-awareness, so a nested group like
  "what can (i|you) do" gets shredded into the bare, overly-generic
  fragment "i" and the mismatched fragment "you do" instead of the two
  full phrases "what can i do" / "what can you do". Every alternative
  here is written out in full instead.

  Every answer below is checked against the real behavior in this
  codebase (the router, the service, or a file this session actually
  fixed), not written from a guess at what the app probably does.
*/
(function () {
  if (!window.DWCoachKnowledge || !window.DWCoachKnowledge.register) return;

  const TOPICS = [

    // ================= A. Account & getting started =================
    {
      key: 'app_what_is_this',
      match: /\b(what is this app|what does this app do|what can this app do|explain this app|how does this whole thing work)(?:s|es|ing)?\b|این اپ چیست|این برنامه چیکار میکند|چطور کار میکند این برنامه|هذا التطبيق ما هو|ماذا يفعل هذا التطبيق|كيف يعمل هذا التطبيق|这个应用是什么|这个软件是做什么的|这个应用怎么运作/i,
      en: "You log a day's habits (screen time, sleep, mood, and so on) and two trained models score it: a classifier for your current band (Healthy/Moderate/At Risk) and a regressor for a 0-100 wellness score, both explained with your own top factors. Everything else - the weekly plan, the coach, analytics, the Friends League - is built on top of that same real prediction, not a separate guess.",
      fa: "روزت را با عادت‌هایت (زمان صفحه، خواب، خلق‌وخو و غیره) ثبت می‌کنی و دو مدل آموزش‌دیده آن را می‌سنجند: یک طبقه‌بند برای دسته‌ی فعلی‌ات (سالم/متوسط/در معرض خطر) و یک رگرسور برای امتیاز ۰ تا ۱۰۰، هر دو با عامل‌های اصلی خودت توضیح داده می‌شوند. بقیه‌ی اپ - برنامه‌ی هفتگی، مربی، تحلیل‌ها، لیگ دوستان - همه روی همین یک پیش‌بینی واقعی ساخته شده‌اند، نه یک حدس جدا.",
      ar: "تُسجّل عادات يومك (وقت الشاشة، النوم، المزاج وغيرها) ويقيّمها نموذجان مدرَّبان: مصنِّف لفئتك الحالية (صحي/متوسط/في خطر) ونموذج انحدار لدرجة عافية من 0 إلى 100، وكلاهما يُفسَّر بعوامل حقيقية من بياناتك أنت. كل شيء آخر - الخطة الأسبوعية، المدرب، التحليلات، دوري الأصدقاء - مبني على هذا التنبؤ الحقيقي نفسه، لا على تخمين منفصل.",
      zh: "你记录一天的习惯（屏幕时间、睡眠、情绪等），两个训练好的模型会给出评估：一个分类器判定你当前所处的区间（健康/中等/有风险），一个回归模型给出 0-100 的健康分数，两者都用你自己的主要影响因素来解释。其余部分——每周计划、教练、分析、好友联赛——全都建立在这同一次真实预测之上，不是另外的猜测。",
    },

    {
      key: 'app_forgot_password',
      match: /\b(forgot my password|forgot password|reset my password|reset password|locked out of my account|cant log in|can not log in)(?:s|es|ing)?\b|رمزم را فراموش کردم|رمز عبورم یادم رفته|نمیتونم وارد شوم|نسيت كلمة المرور|نسيت كلمة السر|لا أستطيع تسجيل الدخول|忘记密码|密码忘了|无法登录|登录不了/i,
      en: "There's no password-reset flow yet - it's a single-account, no-email-server setup for this build. If you're locked out, register a fresh account rather than waiting on a reset that won't arrive; your old check-ins stay under the old account (nothing is merged automatically).",
      fa: "هنوز مسیر بازیابی رمز عبور وجود ندارد - این نسخه تک‌اکانتی است و سرور ایمیل ندارد. اگر قفل شدی، به‌جای منتظرماندن برای بازیابی‌ای که نمی‌رسد، یک اکانت تازه بساز؛ بررسی‌های قدیمی‌ات زیر اکانت قبلی می‌مانند (چیزی خودکار ادغام نمی‌شود).",
      ar: "لا يوجد مسار لاستعادة كلمة المرور بعد - هذا إصدار بحساب واحد بلا خادم بريد. إن كنت محظورًا، سجّل حسابًا جديدًا بدل انتظار استعادة لن تصل؛ فحوصاتك القديمة تبقى تحت الحساب القديم (لا شيء يُدمج تلقائيًا).",
      zh: "目前还没有找回密码的流程——这个版本是单账号、没有邮件服务器的设置。如果登录不了，直接注册一个新账号，不要等一个不会到来的重置邮件；旧的检测记录会留在旧账号下（不会自动合并）。",
    },

    {
      key: 'app_delete_account',
      match: /\b(delete my account|delete account|how do i delete my account|remove my account)(?:s|es|ing)?\b|حذف حسابم|چطور حسابم را حذف کنم|چگونه اکانتم را پاک کنم|حذف حسابي|كيف أحذف حسابي|إلغاء حسابي|删除我的账户|怎么删除账号|注销账户/i,
      en: "Account deletion is in Settings, and it's real deletion, not deactivation: your check-ins, League connections, chat messages and badges go with it. There's a confirmation step that asks you to type your email back, specifically so this can't happen from one accidental tap.",
      fa: "حذف حساب در تنظیمات است، و حذف واقعی است، نه غیرفعال‌سازی: بررسی‌ها، ارتباط‌های لیگ، پیام‌های چت و نشان‌هایت هم با آن می‌روند. یک مرحله‌ی تأیید دارد که از تو می‌خواهد ایمیلت را دوباره تایپ کنی، دقیقاً برای اینکه با یک لمس تصادفی اتفاق نیفتد.",
      ar: "حذف الحساب موجود في الإعدادات، وهو حذف حقيقي لا تعطيل: فحوصاتك واتصالات الدوري ورسائل الدردشة والشارات تُحذف معه. توجد خطوة تأكيد تطلب منك كتابة بريدك الإلكتروني مجددًا، تحديدًا كي لا يحدث هذا بلمسة عرضية واحدة.",
      zh: "删除账户在设置里，而且是真正的删除，不是停用：你的检测记录、联赛好友关系、聊天消息和徽章都会一起删除。有一个确认步骤会要求你重新输入邮箱，目的就是不让一次误触发生这种事。",
    },

    {
      key: 'app_language_switch',
      match: /\b(change the language|switch language|change app language|how do i change language)(?:s|es|ing)?\b|تغییر زبان|چطور زبان را عوض کنم|عوض کردن زبان برنامه|تغيير اللغة|كيف أغير اللغة|تبديل لغة التطبيق|切换语言|怎么改语言|更改应用语言/i,
      en: "The language switcher sits in the top chrome on every page (usually a globe icon or the four-letter code), and it takes effect immediately - no reload needed for most of what's on screen, since it re-renders live. Your choice is remembered in this browser, per device.",
      fa: "سوییچ زبان در نوار بالای هر صفحه است (معمولاً یک آیکون کره‌ی زمین یا کد چهارحرفی)، و بی‌درنگ اعمال می‌شود - برای بیشتر چیزهای روی صفحه نیازی به رفرش نیست، چون زنده دوباره رندر می‌شود. انتخابت در همین مرورگر، به‌ازای هر دستگاه، به خاطر سپرده می‌شود.",
      ar: "مبدّل اللغة موجود في الشريط العلوي لكل صفحة (عادة أيقونة كرة أرضية أو رمز من أربعة أحرف)، ويُطبَّق فورًا - لا حاجة لإعادة تحميل لمعظم ما هو على الشاشة، لأنه يُعاد رسمه حيًا. اختيارك يُتذكَّر في هذا المتصفح، لكل جهاز على حدة.",
      zh: "语言切换按钮在每个页面顶部的工具条上（通常是一个地球图标或四字母代码），切换会立即生效——屏幕上大部分内容不需要刷新就会实时重新渲染。你的选择会记在这个浏览器里，按设备分别记忆。",
    },

    {
      key: 'app_offline_or_mobile',
      match: /\b(does this work offline|offline mode|use this on my phone|mobile app|is there an app for my phone|works on mobile)(?:s|es|ing)?\b|آفلاین کار میکند|حالت آفلاین|روی گوشی کار میکند|اپلیکیشن موبایل دارد|يعمل بدون انترنت|وضع عدم الاتصال|يعمل على هاتفي|تطبيق للجوال|离线能用吗|离线模式|手机上能用吗|有手机应用吗/i,
      en: "It's a web app, not a native install - open it in your phone's browser and it works the same as on a desktop, responsive layout included. There's no offline mode: a check-in submission is a real request to the model, so it needs a connection at the moment you submit.",
      fa: "این یک وب‌اپ است، نه نصب بومی - در مرورگر گوشی‌ات بازش کن، دقیقاً مثل دسکتاپ کار می‌کند، با چیدمان واکنش‌گرا. حالت آفلاین ندارد: ثبت یک بررسی یک درخواست واقعی به مدل است، پس در لحظه‌ی ثبت به اتصال نیاز دارد.",
      ar: "هذا تطبيق ويب لا تثبيت أصلي - افتحه في متصفح هاتفك ويعمل تمامًا كما على سطح المكتب، بتخطيط متجاوب. لا يوجد وضع بلا إنترنت: تسجيل الفحص طلب حقيقي إلى النموذج، فهو يحتاج اتصالًا لحظة الإرسال.",
      zh: "这是一个网页应用，不是原生安装——在手机浏览器里打开就行，效果和电脑上一样，布局是响应式的。没有离线模式：提交一次检测是对模型的一次真实请求，所以提交那一刻需要联网。",
    },

    
    // ================= B. Check-in questionnaire =================
    {
      key: 'app_checkin_required_fields',
      match: /\b(required fields|required field|which fields are required|why is this field required|field cant be blank|field is empty error)(?:s|es|ing)?\b|فیلدهای اجباری|کدام فیلد اجباری است|این فیلد نمیتواند خالی باشد|الحقول المطلوبة|أي حقل إلزامي|هذا الحقل لا يمكن أن يكون فارغا|必填字段|哪些字段是必填的|这个字段不能为空/i,
      en: "Some fields are required (the ones the model needs a value for) and some are optional context. A blank required field is never silently filled with a guess or a default - you get a clear field-level error naming exactly which one, right where you're editing it.",
      fa: "برخی فیلدها اجباری‌اند (آن‌هایی که مدل به مقدارشان نیاز دارد) و برخی زمینه‌ی اختیاری‌اند. یک فیلد اجباریِ خالی هرگز بی‌صدا با حدس یا مقدار پیش‌فرض پر نمی‌شود - یک خطای دقیق در همان سطح فیلد می‌گیری که مشخص می‌کند دقیقاً کدام است، درست همان‌جا که در حال ویرایشی.",
      ar: "بعض الحقول إلزامية (التي يحتاج النموذج قيمتها) وبعضها سياق اختياري. الحقل الإلزامي الفارغ لا يُملأ أبدًا بصمت بتخمين أو قيمة افتراضية - تحصل على خطأ واضح على مستوى الحقل يسمّي بالضبط أيّه، في نفس مكان التحرير.",
      zh: "有些字段是必填的（模型需要这个值才能计算），有些是可选的背景信息。必填字段留空绝不会被悄悄用猜测值或默认值填上——你会在正在编辑的那个位置得到一条明确指出具体是哪个字段的错误提示。",
    },

    {
      key: 'app_exclude_from_analysis',
      match: /\b(exclude from analysis|exclude this day|mark as exception day|exception day checkbox|test entry that doesnt count|unusual day checkbox)(?:s|es|ing)?\b|حذف از تحلیل|علامت زدن روز استثنا|روز غیرعادی را چطور علامت بزنم|استبعاد من التحليل|تحديد يوم استثنائي|خانة اليوم الاستثنائي|从分析中排除|标记为例外日|排除这一天/i,
      en: "There's a checkbox for exactly this: a hypothetical or test entry can be marked so it produces a real prediction but never enters your averages, streaks or history charts. This is different from Demo Mode - it's for one real check-in you don't want counted, not a whole synthetic history.",
      fa: "برای دقیقاً همین یک چک‌باکس هست: یک ثبت فرضی یا آزمایشی می‌تواند علامت بخورد تا یک پیش‌بینی واقعی بدهد اما هرگز وارد میانگین‌ها، استریک‌ها یا نمودارهای تاریخچه‌ات نشود. این با حالت دمو فرق دارد - این برای یک بررسی واقعی است که نمی‌خواهی حساب شود، نه یک تاریخچه‌ی کاملاً ساختگی.",
      ar: "توجد خانة اختيار لهذا بالضبط: يمكن وضع علامة على إدخال افتراضي أو تجريبي كي ينتج تنبؤًا حقيقيًا لكن لا يدخل أبدًا في متوسطاتك أو سلاسلك أو رسوم تاريخك. هذا يختلف عن وضع العرض التجريبي - هذا لفحص حقيقي واحد لا تريد احتسابه، لا لتاريخ اصطناعي كامل.",
      zh: "正好有一个复选框可以做这件事：把一次假设性或测试性的记录标记出来，它会产生真实的预测，但绝不会计入你的平均值、连续记录或历史图表。这和演示模式不同——这是针对一次不想被计入的真实检测，而不是一整套虚构的历史。",
    },

    {
      key: 'app_reopen_past_day',
      match: /\b(reopen a past day|click on history entry|open an old checkin|view a past result again|see an old prediction again)(?:s|es|ing)?\b|بازکردن روز گذشته|کلیک روی تاریخچه|دیدن دوباره نتیجه قدیمی|إعادة فتح يوم سابق|النقر على سجل قديم|رؤية نتيجة قديمة مرة أخرى|重新打开过去的记录|点击历史记录|再次查看旧结果/i,
      en: "Click any entry in your history and it reopens that exact day's result - the same score, class, factors and confidence it got at the time, replayed from what was saved, not re-predicted. That's deliberate: re-running the model on an old day could give a different number now (your trend features have moved on), which would make your own history chart lie about itself.",
      fa: "روی هر ورودی در تاریخچه‌ات کلیک کن تا دقیقاً نتیجه‌ی همان روز باز شود - همان امتیاز، کلاس، عامل‌ها و اطمینانی که در آن زمان گرفته، از روی چیزی که ذخیره شده بازپخش می‌شود، نه دوباره پیش‌بینی‌شده. این عمدی است: اجرای دوباره‌ی مدل روی یک روز قدیمی می‌تواند الان عدد متفاوتی بدهد (ویژگی‌های روند تو جلو رفته‌اند)، که باعث می‌شود نمودار تاریخچه‌ی خودت درباره‌ی خودش دروغ بگوید.",
      ar: "انقر أي سجل في تاريخك ليعيد فتح نتيجة ذلك اليوم بالضبط - نفس الدرجة والفئة والعوامل والثقة التي حصل عليها وقتها، مُعادة تشغيلها مما حُفظ، لا مُعاد التنبؤ بها. هذا مقصود: إعادة تشغيل النموذج على يوم قديم قد يعطي رقمًا مختلفًا الآن (ميزات اتجاهك تقدّمت)، مما يجعل رسم تاريخك يكذب على نفسه.",
      zh: "点击历史记录里的任意一条，就会重新打开那一天当时的结果——回放当时保存下来的分数、类别、影响因素和置信度，而不是重新预测一次。这是刻意的：对旧的一天重新跑模型，现在可能会得到不同的数字（因为你的趋势特征已经变了），那样会让你自己的历史图表自相矛盾。",
    },

    
    // ================= C. CSV import/export =================
    {
      key: 'app_save_csv_from_checkin',
      match: /\b(save these answers|save csv from checkin|save these answers as csv|export this checkin|save this checkin)(?:s|es|ing)?\b|ذخیره پاسخها|ذخیره چکین به صورت سی اس وی|خروجی گرفتن از این چکین|حفظ هذه الإجابات|حفظ كملف سي إس في|تصدير هذا التسجيل|保存这些答案|保存为csv|导出这次打卡/i,
      en: "On the result page there's a 'Save these answers' card: name the check-in and you get a one-row CSV of everything you just submitted, which also stays in a list on the check-in screen so you can reload the exact same answers later without retyping them. It's a copy, not a move - nothing here is deleted from your account.",
      fa: "روی صفحه‌ی نتیجه یک کارت «این پاسخ‌ها را ذخیره کن» هست: یک اسم برای بررسی بگذار تا یک CSV تک‌سطری از هرچیزی که همین حالا فرستادی بگیری، که در یک لیست روی صفحه‌ی بررسی هم می‌ماند تا بعداً بدون دوباره‌تایپ‌کردن همان پاسخ‌های دقیق را بارگذاری کنی. این یک رونوشت است، نه جابه‌جایی - چیزی از حسابت حذف نمی‌شود.",
      ar: "في صفحة النتيجة توجد بطاقة 'احفظ هذه الإجابات': سمِّ الفحص وتحصل على CSV بسطر واحد لكل ما أرسلته للتو، وهو يبقى أيضًا في قائمة على شاشة الفحص كي تعيد تحميل الإجابات نفسها بالضبط لاحقًا دون إعادة كتابتها. هذه نسخة لا نقل - لا شيء يُحذف من حسابك.",
      zh: "结果页面上有一个「保存这些答案」的卡片：给这次检测起个名字，就能得到一份单行的 CSV，包含你刚提交的所有内容；它也会保留在检测页面的一个列表里，以后可以直接重新加载同样的答案而不用重新输入。这是一份拷贝，不是转移——账户里的任何东西都不会被删除。",
    },

    {
      key: 'app_csv_saved_list_two_tabs',
      match: /\b(two tabs of saved csv|main and test checkins|saved csv list tabs|why are there two lists of csv)(?:s|es|ing)?\b|دو تب سی اس وی ذخیره شده|لیست اصلی و آزمایشی|تبويبان لملفات سي إس في المحفوظة|القائمة الرئيسية وقائمة الاختبار|保存的csv两个标签页|主列表和测试列表/i,
      en: "Saved CSVs are split into two tabs: main check-ins (the ones that count toward your real analysis) and test check-ins (anything you marked excluded). They're kept separate specifically so you don't accidentally reload a test answer set into a real check-in, or the reverse.",
      fa: "CSVهای ذخیره‌شده به دو تب تقسیم می‌شوند: بررسی‌های اصلی (آن‌هایی که در تحلیل واقعی‌ات حساب می‌شوند) و بررسی‌های تستی (هر چیزی که به‌عنوان مستثنی علامت زدی). عمداً جدا نگه داشته می‌شوند تا اشتباهی یک مجموعه‌ی پاسخ تستی را در یک بررسی واقعی بارگذاری نکنی، یا برعکس.",
      ar: "ملفات CSV المحفوظة مقسّمة إلى تبويبين: فحوصات رئيسية (التي تُحتسب في تحليلك الحقيقي) وفحوصات تجريبية (أي شيء وضعت عليه علامة استبعاد). تبقى منفصلة تحديدًا كي لا تعيد تحميل مجموعة إجابات تجريبية في فحص حقيقي بالخطأ، أو العكس.",
      zh: "已保存的 CSV 分成两个标签页：主检测（计入你真实分析的部分）和测试检测（任何你标记为排除的部分）。特意分开是为了避免你不小心把一份测试答案重新加载成真实检测，或者反过来。",
    },

    {
      key: 'app_csv_template_mismatch',
      match: /\b(csv doesnt match|csv doesnt match the template|csv rejected|csv was rejected|template mismatch|wrong csv format|csv format wrong|my csv got rejected|csv upload failed)(?:s|es|ing)?\b|سی اس وی مطابقت ندارد|قالب فایل اشتباه است|فایل من رد شد|فرمت سی اس وی اشتباه|ملف سي إس في غير مطابق|القالب غير متطابق|تم رفض ملفي|تنسيق سي إس في خاطئ|csv不匹配|模板不匹配|我的csv被拒绝了|csv格式错误/i,
      en: "There are two different CSV shapes in this app on purpose: the bulk-import template (many rows, one per day, with a `date` column) and the single-row questionnaire export from a result page. A file saved from the result page now carries its own `date` column and imports cleanly; if you're holding an OLDER export made before that, it still imports today - it just gets dated 'today' instead of the day it was originally saved, and that assumption is reported back to you rather than done silently.",
      fa: "این اپ عمداً دو شکل CSV دارد: قالب ایمپورت انبوه (چند سطر، یکی برای هر روز، با یک ستون `date`) و خروجی تک‌سطریِ پرسشنامه از صفحه‌ی نتیجه. فایلی که از صفحه‌ی نتیجه ذخیره شده الان ستون `date` خودش را دارد و تمیز ایمپورت می‌شود؛ اگر یک خروجیِ قدیمی‌تر از قبل از این تغییر داری، هنوز هم امروز ایمپورت می‌شود - فقط به‌جای روزی که اصلاً ذخیره شده بود، «امروز» تاریخ‌گذاری می‌شود، و این فرض به‌جای انجام بی‌صدا، به تو گزارش داده می‌شود.",
      ar: "يوجد شكلان مختلفان لملف CSV في هذا التطبيق عمدًا: قالب الاستيراد الجماعي (صفوف كثيرة، صف لكل يوم، بعمود `date`) وتصدير الاستبيان بصف واحد من صفحة النتيجة. الملف المحفوظ من صفحة النتيجة يحمل الآن عمود `date` خاصًا به ويُستورد بسلاسة؛ إن كان لديك تصدير أقدم من قبل هذا التغيير، فهو لا يزال يُستورد اليوم - فقط يُؤرَّخ بـ'اليوم' بدل اليوم الذي حُفظ فيه أصلًا، ويُبلَّغ هذا الافتراض إليك بدل أن يحدث بصمت.",
      zh: "这个应用故意有两种不同形状的 CSV：批量导入模板（多行，每行一天，带 `date` 列）和结果页面导出的单行问卷。现在从结果页面保存的文件自带 `date` 列，可以顺利导入；如果你手里的是这次改动之前导出的旧文件，今天仍然能导入——只是会被标记为「今天」的日期，而不是最初保存的那一天，而且这个假设会明确告诉你，不会悄悄发生。",
    },

    {
      key: 'app_csv_missing_date',
      match: /\b(csv missing date|row without a date|date column error|cant parse the date|invalid date in csv)(?:s|es|ing)?\b|سی اس وی بدون تاریخ|ردیف بدون تاریخ|خطای ستون تاریخ|ملف سي إس في بدون تاريخ|صف بدون تاريخ|خطأ عمود التاريخ|csv缺少日期|这一行没有日期|日期列出错/i,
      en: "The bulk importer needs one `date` per row, in YYYY-MM-DD format - a row without one, or with a date it can't parse, fails with an explicit error naming that row rather than silently skipping it or guessing a date. A single-row file with no date column at all is still accepted and dated today, but only when it's exactly one row; several undated rows have no way to be told apart, so each fails.",
      fa: "ایمپورتِ انبوه به یک `date` برای هر سطر نیاز دارد، به فرمت سال-ماه-روز - سطری بدون آن، یا با تاریخی که قابل خواندن نیست، با یک خطای صریح که آن سطر را نام می‌برد شکست می‌خورد، نه بی‌صدا رد شدن یا حدس‌زدن تاریخ. یک فایل تک‌سطری بدون هیچ ستون تاریخی هم پذیرفته و امروز تاریخ‌گذاری می‌شود، اما فقط وقتی دقیقاً یک سطر باشد؛ چند سطر بی‌تاریخ راهی برای تمایز از هم ندارند، پس هرکدام شکست می‌خورند.",
      ar: "يحتاج المستورد الجماعي `date` واحدًا لكل صف، بصيغة YYYY-MM-DD - صف بلا تاريخ، أو بتاريخ لا يمكن تحليله، يفشل بخطأ صريح يسمّي ذلك الصف بدل تخطيه بصمت أو تخمين تاريخ. ملف بصف واحد بلا عمود تاريخ إطلاقًا لا يزال يُقبل ويُؤرَّخ باليوم، لكن فقط عندما يكون صفًا واحدًا بالضبط؛ عدة صفوف بلا تاريخ لا سبيل للتمييز بينها، فيفشل كل منها.",
      zh: "批量导入器要求每一行都有一个 `date`，格式为 YYYY-MM-DD——没有日期的行，或者日期无法解析的行，会明确报错并指出是哪一行，而不是悄悄跳过或猜一个日期。完全没有日期列的单行文件仍然会被接受并标记为今天，但仅限于恰好一行的情况；多行没有日期就没办法区分彼此，所以每一行都会失败。",
    },

    {
      key: 'app_csv_derived_columns_ignored',
      match: /\b(derived columns ignored|computed columns in csv|why are my edited columns ignored|hand edited csv columns|ratio columns recomputed)(?:s|es|ing)?\b|ستون‌های محاسبه‌شده نادیده گرفته می‌شوند|چرا ستون‌های ویرایش‌شده من نادیده گرفته میشود|الأعمدة المحسوبة يتم تجاهلها|لماذا يتم تجاهل الأعمدة التي عدلتها|计算列被忽略|为什么我编辑的列被忽略了/i,
      en: "About 17 columns (ratios, densities, your rolling baseline) are computed FROM your raw numbers, never asked for directly - the importer recomputes them itself and ignores whatever a hand-edited copy of them says, exactly like the live check-in form does. If you want a different ratio, change the raw minutes it's built from instead; the recomputed value will follow.",
      fa: "حدود ۱۷ ستون (نسبت‌ها، چگالی‌ها، خط‌پایه‌ی متحرکت) از روی اعداد خامت محاسبه می‌شوند، هرگز مستقیم پرسیده نمی‌شوند - ایمپورتر خودش دوباره محاسبه‌شان می‌کند و هرچه یک نسخه‌ی دست‌ویرایش‌شده از آن‌ها بگوید نادیده می‌گیرد، دقیقاً مثل فرم زنده‌ی بررسی. اگر نسبت متفاوتی می‌خواهی، به‌جایش دقیقه‌های خامی که از رویش ساخته شده را عوض کن؛ مقدار بازمحاسبه‌شده دنبالش می‌آید.",
      ar: "نحو 17 عمودًا (النسب، الكثافات، خط أساسك المتحرك) تُحسب من أرقامك الخام، لا تُطلب مباشرة أبدًا - المستورد يعيد حسابها بنفسه ويتجاهل ما تقوله نسخة معدَّلة يدويًا منها، تمامًا كما تفعل استمارة الفحص الحية. إن أردت نسبة مختلفة، غيّر بدلًا منها الدقائق الخام التي بُنيت منها؛ القيمة المعاد حسابها ستتبع ذلك.",
      zh: "大约 17 列（比例、密度、你的滚动基线）是从原始数字计算出来的，从来不会直接询问——导入器会自己重新计算它们，并忽略手工编辑过的版本，这和实时的检测表单做法完全一样。如果你想要不同的比例，应该改变构成它的原始分钟数；重新计算出的值会随之改变。",
    },

    {
      key: 'app_csv_cross_account_baseline',
      match: /\b(import a csv from another account|csv from someone else|cross account csv|import friends csv|someone elses baseline)(?:s|es|ing)?\b|وارد کردن سی اس وی از حساب دیگر|فایل شخص دیگر|خط پایه شخص دیگر|استيراد سي إس في من حساب آخر|ملف من شخص آخر|خط الأساس لشخص آخر|从别人账户导入csv|别人的csv文件|别人的基线数据/i,
      en: "You can import a CSV someone else exported from their own account - the derived columns (including their personal screen-time baseline) are dropped and recomputed from scratch under your own account, so their history never bleeds into yours. Only the raw numbers travel across accounts; everything comparative is rebuilt fresh.",
      fa: "می‌توانی یک CSV را که کس دیگری از اکانت خودش خروجی گرفته ایمپورت کنی - ستون‌های مشتق (شامل خط‌پایه‌ی شخصیِ زمان صفحه‌شان) کنار گذاشته و از صفر زیر اکانت خودت بازمحاسبه می‌شوند، پس تاریخچه‌شان هرگز به تاریخچه‌ی تو نشت نمی‌کند. فقط اعداد خام بین اکانت‌ها جابه‌جا می‌شوند؛ هرچیز مقایسه‌ای از نو ساخته می‌شود.",
      ar: "يمكنك استيراد ملف CSV صدّره شخص آخر من حسابه - الأعمدة المشتقة (بما فيها خط أساس وقت شاشته الشخصي) تُسقَط وتُعاد حسابها من الصفر تحت حسابك أنت، فتاريخه لا يتسرّب أبدًا إلى تاريخك. فقط الأرقام الخام تنتقل بين الحسابات؛ كل شيء مقارن يُعاد بناؤه من جديد.",
      zh: "你可以导入别人从自己账户导出的 CSV——派生列（包括他们个人的屏幕时间基线）会被丢弃，在你自己的账户下从头重新计算，所以他们的历史数据绝不会渗入你的历史。只有原始数字会跨账户传递；所有比较性的数值都会重新构建。",
    },

    {
      key: 'app_csv_download_template',
      match: /\b(download csv template|download the template|get the csv template|where is the csv template|template button)(?:s|es|ing)?\b|دانلود قالب سی اس وی|دریافت قالب|دکمه قالب کجاست|تحميل قالب سي إس في|الحصول على القالب|أين زر القالب|下载csv模板|获取模板|模板按钮在哪/i,
      en: "The check-in page has a 'Download CSV template' button that gives you a header row plus two realistic example rows - one healthy-leaning day, one at-risk-leaning day - so the scale of each field is obvious before you fill in your own real days.",
      fa: "صفحه‌ی بررسی یک دکمه‌ی «دانلود قالب CSV» دارد که یک ردیف سرستون به‌علاوه دو ردیف نمونه‌ی واقع‌گرایانه می‌دهد - یک روز رو به سالم، یک روز رو به در معرض خطر - تا پیش از پرکردن روزهای واقعی خودت، مقیاس هر فیلد واضح باشد.",
      ar: "تحتوي صفحة الفحص على زر 'تنزيل قالب CSV' يمنحك صف عناوين إضافة إلى صفَّي مثال واقعيَّين - يوم يميل للصحي، ويوم يميل للخطر - كي يتضح مقياس كل حقل قبل ملء أيامك الحقيقية.",
      zh: "检测页面有一个「下载 CSV 模板」按钮，会给你一个表头行加两个真实感的示例行——一个偏健康的日子，一个偏风险的日子——这样在你填入自己真实的日子之前，每个字段的量级就一目了然。",
    },

    
    // ================= D. Demo Mode =================
    {
      key: 'app_demo_what_is_it',
      match: /\b(what is demo mode|demo mode|what does demo mode do|try the app without my data)(?:s|es|ing)?\b|حالت دمو چیست|دمو مود چیست|بدون داده‌های خودم امتحان کنم|ما هو وضع العرض التجريبي|وضع الديمو|جرب التطبيق بدون بياناتي|演示模式是什么|试玩模式是什么|不用我自己的数据试用/i,
      en: "Demo Mode builds a run of days scored by the real trained model on synthetic-but-realistic inputs, plus a connected demo League friend, so you can explore or record a walkthrough without logging real days first. It swaps your session to a separate demo account behind the scenes - your real account and its real data are never touched.",
      fa: "حالت دمو یک رشته روز می‌سازد که با مدل واقعیِ آموزش‌دیده روی ورودی‌های ساختگی-اما-واقع‌گرایانه امتیازدهی شده، به‌علاوه یک دوست دموی متصل در لیگ، تا بتوانی بدون ثبت روزهای واقعی، اپ را کاوش کنی یا یک واک‌تروی ضبط کنی. در پشت صحنه نشست تو را به یک اکانت دموی جدا سوییچ می‌کند - اکانت واقعی‌ات و داده‌ی واقعی‌اش هرگز دست‌نخورده می‌ماند.",
      ar: "يبني الوضع التجريبي سلسلة أيام يقيّمها النموذج المدرَّب الحقيقي على مدخلات اصطناعية لكن واقعية، بالإضافة إلى صديق دوري تجريبي متصل، كي تستكشف أو تسجل جولة دون تسجيل أيام حقيقية أولًا. يبدّل جلستك خلف الكواليس إلى حساب تجريبي منفصل - حسابك الحقيقي وبياناته الحقيقية لا يُمسّان أبدًا.",
      zh: "演示模式会用真实训练好的模型，对合成但真实感的输入打分，生成一段连续的天数，还会连上一个演示联赛好友，这样你就能在不先记录真实日子的情况下探索应用或录制演示。它在幕后把你的会话切换到一个独立的演示账户——你的真实账户和真实数据永远不会被触碰。",
    },

    {
      key: 'app_demo_how_many_days',
      match: /\b(how many days in demo|demo length|how long is the demo|how many days can i pick for the demo)(?:s|es|ing)?\b|چند روز دمو|طول دمو چقدر است|چند روز میتوانم انتخاب کنم|كم يوما في العرض التجريبي|مدة العرض التجريبي|كم يوما يمكنني اختيار|演示模式有多少天|演示时长|可以选择多少天/i,
      en: "You pick the length: 3, 7, 15 or 23 days. Shorter demos show less trend/history-dependent content (the weekly plan and some analytics cards need real history to appear at all); 23 days is the only one that exercises every feature that depends on an established trend.",
      fa: "طول را خودت انتخاب می‌کنی: ۳، ۷، ۱۵ یا ۲۳ روز. دموهای کوتاه‌تر محتوای وابسته به روند/تاریخچه‌ی کمتری نشان می‌دهند (برنامه‌ی هفتگی و برخی کارت‌های تحلیل اصلاً به تاریخچه‌ی واقعی نیاز دارند تا ظاهر شوند)؛ ۲۳ روز تنها گزینه‌ای است که هر ویژگیِ وابسته به یک روند جاافتاده را تمرین می‌کند.",
      ar: "تختار المدة بنفسك: 3 أو 7 أو 15 أو 23 يومًا. العروض الأقصر تُظهر محتوى أقل يعتمد على الاتجاه/التاريخ (الخطة الأسبوعية وبعض بطاقات التحليل تحتاج تاريخًا حقيقيًا كي تظهر أصلًا)؛ 23 يومًا هي الوحيدة التي تُشغّل كل ميزة تعتمد على اتجاه راسخ.",
      zh: "长度由你选择：3、7、15 或 23 天。较短的演示展示的趋势/历史相关内容较少（每周计划和部分分析卡片需要真实历史才会出现）；23 天是唯一能触发所有依赖于稳定趋势的功能的选项。",
    },

    {
      key: 'app_demo_profile_types',
      match: /\b(demo profile types|healthy improving borderline at risk demo|which demo profile should i pick|demo profiles explained)(?:s|es|ing)?\b|انواع پروفایل دمو|کدام پروفایل دمو را انتخاب کنم|أنواع ملفات العرض التجريبي|أي ملف تجريبي أختار|演示档案类型|该选哪个演示档案/i,
      en: "Four shapes: healthy (stays strong throughout), improving (starts weak, climbs), borderline (wanders right at a class boundary - the one that shows the seven-day class actually flipping), and at-risk (starts moderate, declines). Pick borderline if you specifically want to demonstrate that today's score and the seven-day forecast are two different models that can disagree.",
      fa: "چهار شکل: سالم (تا آخر قوی می‌ماند)، بهبودیابنده (ضعیف شروع می‌شود، بالا می‌رود)، مرزی (درست روی مرز یک کلاس پرسه می‌زند - همانی که نشان می‌دهد کلاس هفت‌روزه واقعاً برمی‌گردد)، و در معرض خطر (متوسط شروع می‌شود، افت می‌کند). اگر می‌خواهی دقیقاً نشان بدهی که امتیاز امروز و پیش‌بینی هفت‌روزه دو مدل جدا هستند که می‌توانند اختلاف داشته باشند، مرزی را انتخاب کن.",
      ar: "أربعة أشكال: صحي (يبقى قويًا طوال الوقت)، متحسّن (يبدأ ضعيفًا ويتصاعد)، حدّي (يتجول عند حدود فئة بالضبط - وهو الذي يُظهر انقلاب فئة السبعة أيام فعلًا)، وفي خطر (يبدأ متوسطًا ويتراجع). اختر الحدّي إن أردت تحديدًا إظهار أن درجة اليوم وتوقع السبعة أيام نموذجان مختلفان قد يختلفان.",
      zh: "四种形态：健康型（全程保持良好）、改善型（开始较弱，逐渐上升）、边界型（正好在类别边界附近徘徊——这是唯一能展示七天预测类别真正翻转的一种）、有风险型（开始中等，逐渐下降）。如果你specifically想展示今天的分数和七天预测是两个可能不一致的独立模型，选边界型。",
    },

    {
      key: 'app_demo_affect_real_data',
      match: /\b(does demo mode affect my real data|demo touch my real checkins|will demo overwrite my data|is demo data mixed with real data)(?:s|es|ing)?\b|آیا دمو روی داده واقعی من اثر میگذارد|دمو با داده واقعی من مخلوط میشود|هل يؤثر الوضع التجريبي على بياناتي الحقيقية|هل تختلط بيانات التجربة ببياناتي|演示模式会影响我的真实数据吗|演示数据会和真实数据混在一起吗/i,
      en: "No - entering Demo Mode swaps your session to a completely separate synthetic account; your real token is stashed and restored the moment you leave. Nothing written during a demo touches your real check-in history, your real League connections, or your real account settings.",
      fa: "نه - ورود به حالت دمو نشست تو را به یک اکانت ساختگیِ کاملاً جدا سوییچ می‌کند؛ توکن واقعی‌ات کنار گذاشته و در همان لحظه‌ای که ترک می‌کنی برمی‌گردد. هیچ‌چیزی که در دموی نوشته می‌شود، تاریخچه‌ی بررسیِ واقعی‌ات، ارتباط‌های واقعی لیگ‌ات، یا تنظیمات اکانت واقعی‌ات را دست نمی‌زند.",
      ar: "لا - دخول الوضع التجريبي يبدّل جلستك إلى حساب اصطناعي منفصل تمامًا؛ رمزك الحقيقي يُخزَّن جانبًا ويُستعاد لحظة خروجك. لا شيء يُكتب أثناء التجربة يلمس تاريخ فحصك الحقيقي، أو اتصالات دوريك الحقيقية، أو إعدادات حسابك الحقيقي.",
      zh: "不会——进入演示模式会把你的会话切换到一个完全独立的虚构账户；你的真实令牌会被暂存，退出的那一刻恢复。演示过程中写入的任何内容都不会碰到你真实的检测历史、真实的联赛好友关系，或真实的账户设置。",
    },

    {
      key: 'app_demo_leave',
      match: /\b(leave demo mode|how do i exit the demo|get out of demo|back to my real account|exit demo)(?:s|es|ing)?\b|خروج از حالت دمو|چطور از دمو خارج شوم|برگشت به حساب واقعی|الخروج من وضع العرض التجريبي|كيف أخرج من الديمو|العودة لحسابي الحقيقي|退出演示模式|怎么退出演示|回到我的真实账户/i,
      en: "There's a 'Leave demo' control (usually near the demo banner or in Settings) that swaps your real token back in and clears the demo state. If you closed the tab instead of using it, reopening the app should still find your real token stashed and restore it the same way.",
      fa: "یک کنترل «خروج از دمو» هست (معمولاً نزدیک بنر دمو یا در تنظیمات) که توکن واقعی‌ات را برمی‌گرداند و وضعیت دمو را پاک می‌کند. اگر به‌جای استفاده از آن تب را بستی، بازکردن دوباره‌ی اپ باید همچنان توکن واقعی‌ات را کنارگذاشته‌شده پیدا کند و به همان شکل برش‌گرداند.",
      ar: "يوجد عنصر تحكم 'الخروج من التجربة' (عادة قرب شريط العرض التجريبي أو في الإعدادات) يعيد رمزك الحقيقي ويمسح حالة العرض. إن أغلقت التبويب بدل استخدامه، فتح التطبيق مجددًا ينبغي أن يجد رمزك الحقيقي مخزَّنًا ويستعيده بالطريقة نفسها.",
      zh: "有一个「退出演示」控件（通常在演示横幅附近或设置里），会把你的真实令牌换回来并清除演示状态。如果你是直接关闭标签页而不是用这个按钮，重新打开应用应该仍然能找到暂存的真实令牌并以同样的方式恢复它。",
    },

    {
      key: 'app_demo_stuck_processing',
      match: /\b(demo stuck processing|demo hangs then kicks me out|demo stuck at processing|demo timed out|demo froze)(?:s|es|ing)?\b|دموی من گیر کرد|دمو در حال پردازش گیر کرده|دمو هنگ کرده|الديمو عالق في المعالجة|الديمو توقف ثم أخرجني|الديمو تجمد|演示卡主了|演示卡在处理中|演示卡死了|演示超时/i,
      en: "If a demo used to hang and then kick you out with a network error near the 45-second mark, that was a real, since-fixed performance bug in how the model prediction step built its input each round - it's several times faster now. If it still stalls, it's worth trying a shorter length (7 or 15 days) first to isolate whether it's your connection or the run itself.",
      fa: "اگر یک دمو قبلاً گیر می‌کرد و بعد نزدیک نشانه‌ی ۴۵ ثانیه با یک خطای شبکه بیرونت می‌انداخت، آن یک باگ عملکردیِ واقعی بود که از الان اصلاح شده - در نحوه‌ای که مرحله‌ی پیش‌بینیِ مدل ورودی‌اش را هر دور می‌ساخت. الان چند برابر سریع‌تر است. اگر هنوز گیر می‌کند، ارزش دارد اول یک طول کوتاه‌تر (۷ یا ۱۵ روز) امتحان کنی تا بفهمی مشکل از اتصال توست یا خودِ اجرا.",
      ar: "إن كان العرض التجريبي يتعلّق سابقًا ثم يخرجك بخطأ شبكة قرب علامة الـ45 ثانية، فتلك كانت مشكلة أداء حقيقية أُصلحت منذ ذلك الحين - في كيفية بناء خطوة تنبؤ النموذج لمدخلها كل دورة. أصبح الآن أسرع بعدة أضعاف. إن كان لا يزال يتعثر، يستحق تجربة مدة أقصر (7 أو 15 يومًا) أولًا لعزل ما إذا كانت المشكلة في اتصالك أم في التشغيل نفسه.",
      zh: "如果之前演示会卡住，然后在接近 45 秒时因网络错误把你踢出来，那是一个真实存在、现已修复的性能问题——出在模型预测步骤每一轮构建输入的方式上。现在速度快了好几倍。如果仍然卡住，值得先试试更短的长度（7 天或 15 天），看看是网络问题还是运行本身的问题。",
    },

    
    // ================= E. Result / prediction page =================
    {
      key: 'app_score_vs_class',
      match: /\b(score vs class|difference between score and class|why do score and class disagree|score and class dont match)(?:s|es|ing)?\b|تفاوت امتیاز و دسته|چرا امتیاز و دسته متفاوتند|الفرق بين الدرجة والفئة|لماذا الدرجة والفئة لا تتفقان|分数和类别的区别|为什么分数和类别不一致/i,
      en: "The class (Healthy/Moderate/At Risk) comes from a classifier; the 0-100 score comes from a separate regressor. They're trained on the same inputs but different targets, so they usually agree but can genuinely disagree at the edges - that's not a bug, it's two honest opinions from two different models rather than one number dressed up two ways.",
      fa: "کلاس (سالم/متوسط/در معرض خطر) از یک طبقه‌بند می‌آید؛ امتیاز ۰ تا ۱۰۰ از یک رگرسور جدا. روی همان ورودی‌ها اما هدف‌های متفاوت آموزش دیده‌اند، پس معمولاً توافق دارند اما می‌توانند در لبه‌ها واقعاً اختلاف داشته باشند - این باگ نیست، دو نظر صادق از دو مدل مختلف است، نه یک عدد که دو جور آراسته شده.",
      ar: "الفئة (صحي/متوسط/في خطر) تأتي من مصنِّف؛ الدرجة من 0 إلى 100 تأتي من نموذج انحدار منفصل. يُدرَّبان على المدخلات نفسها لكن أهداف مختلفة، فيتفقان عادة لكن قد يختلفان فعلًا عند الحواف - هذا ليس عطلاً، بل رأيان صادقان من نموذجين مختلفين، لا رقم واحد مُزيَّن بطريقتين.",
      zh: "类别（健康/中等/有风险）来自分类器；0-100 的分数来自另一个独立的回归模型。它们用相同的输入训练，但目标不同，所以通常一致，但在边界情况下确实可能不一致——这不是 bug，而是两个不同模型给出的两个诚实意见，而不是同一个数字打扮成两种样子。",
    },

    {
      key: 'app_confidence_meaning',
      match: /\b(what does confidence mean|confidence percentage meaning|how is confidence calculated|confidence score explained)(?:s|es|ing)?\b|اطمینان یعنی چه|درصد اطمینان یعنی چه|اطمینان چطور محاسبه میشود|ماذا تعني الثقة|معنى نسبة الثقة|كيف تحسب الثقة|置信度是什么意思|置信度百分比含义|置信度怎么算的/i,
      en: "It's how tightly your inputs cluster inside one class versus spreading across two, not a proxy for whether the score is good or bad - a confident 'At Risk' and an unsure 'At Risk' are both real At Risk predictions, one is just closer to the boundary with another class.",
      fa: "این یعنی ورودی‌هایت چقدر داخل یک کلاس متمرکزند در برابر پخش‌شدن بین دو کلاس، نه نمایانگری از خوب یا بد بودن امتیاز - یک «در معرض خطرِ» مطمئن و یک «در معرض خطرِ» نامطمئن هر دو پیش‌بینیِ واقعیِ در معرض خطرند، فقط یکی به مرز با کلاس دیگر نزدیک‌تر است.",
      ar: "هي مدى تجمّع مدخلاتك داخل فئة واحدة مقابل انتشارها بين فئتين، لا مؤشرًا على كون الدرجة جيدة أو سيئة - 'في خطر' واثقة و'في خطر' غير واثقة كلاهما تنبؤ حقيقي بأنك في خطر، إحداهما فقط أقرب إلى الحد مع فئة أخرى.",
      zh: "它表示你的输入在一个类别内聚集的紧密程度，相对于分散在两个类别之间的程度，而不是分数好坏的代理指标——一个「有风险」且高置信度和一个「有风险」但低置信度都是真实的有风险预测，只是后者离另一个类别的边界更近。",
    },

    {
      key: 'app_shap_factors',
      match: /\b(what are the shap factors|top factors explained|how are my factors calculated|what determines my top factors)(?:s|es|ing)?\b|فاکتورهای شپ چیستند|عوامل اصلی چطور محاسبه میشوند|ما هي عوامل شاب|كيف تحسب العوامل الرئيسية|shap因素是什么|主要因素怎么算出来的/i,
      en: "Those are real SHAP values computed from THIS exact prediction, not a generic list of 'things that matter in general' - each one names a field you actually submitted and how much it pushed your score up or down, so it changes from one check-in to the next.",
      fa: "این‌ها مقادیر واقعیِ SHAP هستند که از دقیقاً همین پیش‌بینی محاسبه شده‌اند، نه یک فهرست عمومی از «چیزهایی که کلاً مهم‌اند» - هرکدام یک فیلدی که واقعاً فرستادی را نام می‌برد و اینکه چقدر امتیازت را بالا یا پایین برده، پس از یک بررسی به بعدی عوض می‌شود.",
      ar: "هذه قيم SHAP حقيقية محسوبة من هذا التنبؤ بالضبط، لا قائمة عامة لـ'أشياء مهمة بشكل عام' - كل واحد يسمّي حقلًا أرسلته فعلًا ومقدار دفعه لدرجتك أعلى أو أسفل، فهي تتغير من فحص لآخر.",
      zh: "这些是从这一次具体预测计算出的真实 SHAP 值，不是「一般来说重要的东西」的通用列表——每一项都指出你实际提交的某个字段，以及它把你的分数推高或拉低了多少，所以每次检测都会不同。",
    },

    {
      key: 'app_download_pdf_report',
      match: /\b(download pdf report|download the report|get a pdf of my result|export result as pdf)(?:s|es|ing)?\b|دانلود گزارش پی دی اف|دریافت پی دی اف نتیجه|تحميل تقرير بي دي اف|الحصول على تقرير بي دي اف|下载pdf报告|获取pdf结果|导出结果为pdf/i,
      en: "The 'Download PDF report' button on the result page builds a real document from that exact prediction - score, class, SHAP factors, recommendations - shaped for your current language and written right-to-left when that language is Persian or Arabic, not a translated screenshot of an English layout.",
      fa: "دکمه‌ی «دانلود گزارش PDF» روی صفحه‌ی نتیجه یک سند واقعی از دقیقاً همین پیش‌بینی می‌سازد - امتیاز، کلاس، عامل‌های SHAP، توصیه‌ها - متناسب با زبان فعلی‌ات، و وقتی آن زبان فارسی یا عربی است راست‌به‌چپ نوشته می‌شود، نه یک اسکرین‌شاتِ ترجمه‌شده از یک چیدمان انگلیسی.",
      ar: "زر 'تنزيل تقرير PDF' في صفحة النتيجة يبني مستندًا حقيقيًا من هذا التنبؤ بالضبط - الدرجة والفئة وعوامل SHAP والتوصيات - مُشكَّلًا بلغتك الحالية، ومكتوبًا من اليمين لليسار حين تكون تلك اللغة الفارسية أو العربية، لا لقطة شاشة مترجَمة من تخطيط إنكليزي.",
      zh: "结果页面的「下载 PDF 报告」按钮会从这次具体的预测生成一份真实文档——分数、类别、SHAP 因素、建议——按你当前的语言排版，当语言是波斯语或阿拉伯语时会以从右到左的方式书写，而不是英文排版的翻译截图。",
    },

    {
      key: 'app_recommendations_empty',
      match: /\b(no recommendations shown|recommendations list is empty|why are there no recommendations|empty recommendation card)(?:s|es|ing)?\b|پیشنهادی نمایش داده نشد|لیست پیشنهادها خالی است|لا توجد توصيات|قائمة التوصيات فارغة|没有显示建议|建议列表是空的|为什么没有推荐/i,
      en: "An empty recommendations list on a genuinely healthy profile is correct behaviour, not a bug: recommendations come from SHAP factors that are actively hurting your score, and a healthy day can have none of those. There's also a fixed list of fields the app will never turn into a recommendation - age, gender, region and six clinical fields like anxiety and loneliness among them - because generic identity fields aren't actionable and clinical ones aren't something an app should be telling you to change.",
      fa: "یک فهرست توصیه‌ی خالی روی یک پروفایل واقعاً سالم رفتار درستی است، نه یک باگ: توصیه‌ها از عامل‌های SHAP می‌آیند که فعالانه به امتیازت آسیب می‌زنند، و یک روز سالم می‌تواند هیچ‌کدام از آن‌ها را نداشته باشد. یک فهرست ثابت از فیلدهایی هم هست که اپ هرگز به توصیه تبدیلشان نمی‌کند - سن، جنسیت، منطقه و شش فیلد بالینی مثل اضطراب و تنهایی از میان آن‌ها - چون فیلدهای هویتیِ عمومی قابل‌اقدام نیستند و بالینی‌ها چیزی نیستند که یک اپ باید بگوید عوضشان کن.",
      ar: "قائمة توصيات فارغة على ملف صحي فعلًا سلوك صحيح لا عطل: التوصيات تأتي من عوامل SHAP التي تضر درجتك فعليًا، ويوم صحي قد لا يملك أيًا منها. توجد أيضًا قائمة ثابتة من الحقول التي لن يحوّلها التطبيق أبدًا إلى توصية - العمر والجنس والمنطقة وستة حقول سريرية كالقلق والوحدة من بينها - لأن حقول الهوية العامة غير قابلة للتنفيذ والحقول السريرية ليست شيئًا ينبغي لتطبيق أن يطلب تغييره.",
      zh: "对一个真正健康的画像来说，建议列表为空是正确的行为，不是 bug：建议来自那些正在实际拉低你分数的 SHAP 因素，健康的一天可能一个都没有。还有一份固定的字段清单，应用永远不会把它们变成建议——年龄、性别、地区，以及焦虑、孤独感等六个临床字段都在其中——因为通用身份字段无法采取行动，临床字段也不是应用该建议你去改变的东西。",
    },

    {
      key: 'app_uncertainty_interval',
      match: /\b(what is the uncertainty interval|prediction interval explained|confidence interval on the score|score range explained)(?:s|es|ing)?\b|بازه عدم قطعیت چیست|بازه اطمینان امتیاز چیست|ما هو نطاق عدم اليقين|نطاق الثقة للدرجة|不确定区间是什么|预测区间是什么意思/i,
      en: "That range comes from split-conformal prediction, calibrated once against a held-out validation set the model never trained on - it's a distribution-free, finite-sample guarantee about coverage, not a rule of thumb. A 90% target means roughly 9 times in 10 your real score should land inside the stated range.",
      fa: "آن بازه از پیش‌بینیِ هم‌ساز تقسیم‌شده می‌آید، یک‌بار در برابر یک مجموعه‌ی اعتبارسنجیِ کنارگذاشته‌شده که مدل هرگز رویش آموزش ندیده کالیبره شده - یک تضمینِ بدون‌فرضِ توزیعی و نمونه‌محدود درباره‌ی پوشش است، نه یک قاعده‌ی سرانگشتی. هدف ۹۰٪ یعنی تقریباً ۹ بار از ۱۰، امتیاز واقعی‌ات باید داخل بازه‌ی گفته‌شده بیفتد.",
      ar: "يأتي ذلك النطاق من التنبؤ المطابق المُقسَّم، معايَر مرة واحدة مقابل مجموعة تحقق مُستبعدة لم يتدرّب النموذج عليها إطلاقًا - إنه ضمان خالٍ من الافتراض التوزيعي ومحدود العينة حول التغطية، لا قاعدة تقريبية. هدف 90% يعني أن درجتك الحقيقية ينبغي أن تقع داخل النطاق المذكور نحو 9 مرات من كل 10.",
      zh: "这个区间来自split-conformal预测方法，通过一个模型从未训练过的留出验证集校准一次得出——这是一个无分布假设、有限样本下的覆盖率保证，不是经验法则。90% 的目标意味着大约每 10 次里有 9 次，你的真实分数应该落在给出的区间内。",
    },

    {
      key: 'app_talk_to_future_self',
      match: /\b(talk to my future self|future self card|what if this continued|future self simulation)(?:s|es|ing)?\b|صحبت با خود آینده|کارت خود آینده|اگر این ادامه پیدا کند|التحدث مع نفسي المستقبلية|بطاقة النفس المستقبلية|ماذا لو استمر هذا|和未来的自己对话|未来自己卡片|如果这样继续下去/i,
      en: "That card re-runs the same trained model against a hypothetical future pattern (like 'if this continued for two more weeks') rather than inventing a number - it's a real prediction on a constructed input, so it's honest about being a projection, not a guarantee.",
      fa: "آن کارت همان مدل آموزش‌دیده را دوباره روی یک الگوی فرضیِ آینده اجرا می‌کند (مثل «اگر این دو هفته‌ی دیگر ادامه پیدا کند») به‌جای اختراع یک عدد - یک پیش‌بینی واقعی روی یک ورودیِ ساخته‌شده است، پس درباره‌ی اینکه یک فرافکنی است صادق است، نه یک تضمین.",
      ar: "تلك البطاقة تُعيد تشغيل النموذج المدرَّب نفسه على نمط مستقبلي افتراضي (مثل 'لو استمر هذا أسبوعين آخرين') بدل اختراع رقم - إنه تنبؤ حقيقي على مدخل مُنشأ، فهو صادق في كونه إسقاطًا لا ضمانًا.",
      zh: "那张卡片是用同一个训练好的模型，针对一个假设的未来模式重新运行一次（比如「如果这种情况再持续两周」），而不是凭空编一个数字——这是对一个构造出来的输入做的真实预测，所以它诚实地表明自己是一种推演，而不是保证。",
    },

    
    // ================= F. Weekly Plan =================
    {
      key: 'app_weekly_plan_how_generated',
      match: /\b(how is the weekly plan generated|how is the weekly plan built|where does the weekly plan come from)(?:s|es|ing)?\b|برنامه هفتگی چطور ساخته میشود|برنامه هفتگی از کجا میاید|كيف يتم إنشاء الخطة الأسبوعية|من أين تأتي الخطة الأسبوعية|每周计划是怎么生成的|每周计划从哪里来/i,
      en: "It's rule-based, not the ML model - built from your latest prediction's weakest signals (whichever fields are hurting your score most) and composed from a large library of theme/template/slot/tier combinations bound to your own numbers, so two people with the same weak signal rarely get the identical sentence.",
      fa: "قانون‌محور است، نه مدل یادگیری ماشین - از روی ضعیف‌ترین سیگنال‌های آخرین پیش‌بینی‌ات (هر فیلدی که بیشترین آسیب را به امتیازت می‌زند) ساخته و از یک کتابخانه‌ی بزرگِ ترکیب‌های موضوع/قالب/بازه/سطح که به اعداد خودت گره خورده‌اند ترکیب می‌شود، پس دو نفر با همان سیگنال ضعیف به‌ندرت یک جمله‌ی یکسان می‌گیرند.",
      ar: "إنها قائمة على القواعد لا على نموذج التعلم الآلي - مبنية من أضعف إشارات تنبؤك الأخير (أيّ الحقول تضر درجتك أكثر) ومركَّبة من مكتبة كبيرة من توليفات موضوع/قالب/فترة/مستوى مرتبطة بأرقامك أنت، فنادرًا ما يحصل شخصان بالإشارة الضعيفة نفسها على الجملة نفسها بالضبط.",
      zh: "它是基于规则的，不是机器学习模型——从你最近一次预测中最薄弱的信号（哪些字段对你的分数伤害最大）构建，并从一个庞大的主题/模板/时段/层级组合库中拼接而成，绑定你自己的数字，所以两个有相同薄弱信号的人很少会得到完全相同的句子。",
    },

    {
      key: 'app_weekly_plan_changes_weekly',
      match: /\b(does the weekly plan change every week|why did my weekly plan change|weekly plan is different this week)(?:s|es|ing)?\b|برنامه هفتگی هر هفته عوض میشود|چرا برنامه هفتگی من عوض شد|هل تتغير الخطة الأسبوعية كل أسبوع|لماذا تغيرت خطتي الأسبوعية|每周计划会每周变化吗|为什么我的每周计划变了/i,
      en: "It's regenerated from your most recent prediction each time you open it, so it tracks whatever is weakest RIGHT NOW rather than being a fixed program - if last week's target was sleep and you fixed it, this week's plan should be pointing somewhere else already.",
      fa: "هر بار که بازش می‌کنی از روی آخرین پیش‌بینی‌ات دوباره ساخته می‌شود، پس دنبال هرچیزی می‌رود که همین حالا ضعیف‌ترین است، نه یک برنامه‌ی ثابت - اگر هدفِ هفته‌ی قبل خواب بود و درستش کردی، برنامه‌ی این هفته باید همین الان جای دیگری اشاره کند.",
      ar: "تُعاد بناؤها من أحدث تنبؤ لك كل مرة تفتحها، فهي تتبع أضعف ما هو الآن، لا برنامجًا ثابتًا - إن كان هدف الأسبوع الماضي النوم وأصلحته، فخطة هذا الأسبوع ينبغي أن تشير إلى مكان آخر بالفعل.",
      zh: "每次打开它都会根据你最新的预测重新生成，所以它跟踪的是此刻最薄弱的部分，而不是一个固定的方案——如果上周的目标是睡眠，你已经改善了，那这周的计划应该已经指向别的地方了。",
    },

    {
      key: 'app_weekly_plan_no_plan_showing',
      match: /\b(no weekly plan showing|weekly plan is empty|weekly plan page is blank|why is there no plan)(?:s|es|ing)?\b|برنامه هفتگی نمایش داده نمیشود|صفحه برنامه هفتگی خالی است|لا تظهر الخطة الأسبوعية|صفحة الخطة الأسبوعية فارغة|没有显示每周计划|每周计划页面是空的/i,
      en: "The weekly plan needs a real prediction to build from - if you haven't submitted any check-in yet in this session, the page shows an empty state on purpose rather than fabricating a generic plan with no data behind it. Submit a check-in first and the plan appears.",
      fa: "برنامه‌ی هفتگی برای ساخته‌شدن به یک پیش‌بینی واقعی نیاز دارد - اگر هنوز در این نشست هیچ بررسی‌ای نفرستاده‌ای، صفحه عمداً یک حالت خالی نشان می‌دهد به‌جای ساختن یک برنامه‌ی عمومی بدون داده‌ی پشتش. اول یک بررسی بفرست تا برنامه ظاهر شود.",
      ar: "تحتاج الخطة الأسبوعية إلى تنبؤ حقيقي لتُبنى منه - إن لم ترسل أي فحص بعد في هذه الجلسة، تُظهر الصفحة حالة فارغة عمدًا بدل اختلاق خطة عامة بلا بيانات خلفها. أرسل فحصًا أولًا وستظهر الخطة.",
      zh: "每周计划需要一个真实的预测才能构建——如果你在这次会话里还没提交过任何检测，页面会故意显示空状态，而不是编造一个没有数据支撑的通用计划。先提交一次检测，计划就会出现。",
    },

    {
      key: 'app_weekly_plan_tasks_checkmarks',
      match: /\b(weekly plan checkmarks|checking off tasks in the weekly plan|do the checkboxes save|weekly plan task checkboxes)(?:s|es|ing)?\b|علامت تیک برنامه هفتگی|آیا تیک زدن وظایف ذخیره میشود|علامات الاختيار في الخطة الأسبوعية|هل تُحفظ صناديق الاختيار|每周计划的勾选|打勾任务会保存吗/i,
      en: "Each day of the plan has small tasks you can check off; that state is saved per ISO week (Monday-Sunday), so checking a box actually persists through a page reload and counts toward your plan-progress tracking rather than just being a visual toggle.",
      fa: "هر روزِ برنامه چند کار کوچک دارد که می‌توانی علامت بزنی؛ آن وضعیت به‌ازای هر هفته‌ی ایزو (دوشنبه تا یکشنبه) ذخیره می‌شود، پس علامت‌زدنِ یک چک‌باکس واقعاً از رفرشِ صفحه عبور می‌کند و در پیگیریِ پیشرفتِ برنامه‌ات حساب می‌شود، نه فقط یک سوییچِ بصری.",
      ar: "كل يوم من الخطة يحتوي مهامًا صغيرة يمكنك تحديدها كمنجزة؛ تُحفظ تلك الحالة لكل أسبوع ISO (الاثنين-الأحد)، فتحديد خانة يستمر فعلًا عبر إعادة تحميل الصفحة ويُحتسب في تتبع تقدم خطتك، لا مجرد مفتاح بصري.",
      zh: "计划中的每一天都有可以打勾的小任务；这个状态按 ISO 周（周一到周日）保存，所以勾选一个框在刷新页面后真的会保留下来，并计入你的计划进度追踪，而不只是一个视觉上的开关。",
    },

    {
      key: 'app_weekly_plan_focus_areas',
      match: /\b(weekly plan focus areas|what are those chips at the top of the plan|focus area chips meaning)(?:s|es|ing)?\b|حوزه‌های تمرکز برنامه هفتگی|آن چیپ‌های بالای برنامه یعنی چه|مجالات التركيز في الخطة الأسبوعية|ماذا تعني تلك الشرائح أعلى الخطة|每周计划的重点领域|计划顶部的标签是什么意思/i,
      en: "Those chips at the top of the plan name the specific weak signals it was built from - clicking through the days shows exercises that map back to exactly those, so the whole week has a visible throughline rather than feeling like seven unrelated tips.",
      fa: "آن تراشه‌های بالای برنامه دقیقاً همان سیگنال‌های ضعیفی را نام می‌برند که برنامه از رویشان ساخته شده - رفتن روی روزها تمرین‌هایی نشان می‌دهد که دقیقاً به همان‌ها برمی‌گردند، پس کل هفته یک خطِ پیوسته و دیدنی دارد، نه اینکه هفت نکته‌ی بی‌ربط حس شود.",
      ar: "تلك الشرائح أعلى الخطة تسمّي بالضبط الإشارات الضعيفة التي بُنيت منها - تصفح الأيام يُظهر تمارين ترتبط بها بالضبط، فالأسبوع كله له خط واضح مرئي بدل أن يبدو سبع نصائح غير مترابطة.",
      zh: "计划顶部的那些标签指出了它所依据的具体薄弱信号——翻看每一天会看到对应回这些信号的练习，所以整周有一条清晰可见的主线，而不是感觉像七条互不相关的小贴士。",
    },

    
    // ================= G. AI Coach itself =================
    {
      key: 'app_coach_menu_vs_chat',
      match: /\b(coach menu vs chat|difference between menu and chat box|what is the coach menu for)(?:s|es|ing)?\b|تفاوت منو و چت مربی|منوی مربی برای چه است|الفرق بين قائمة المدرب والمحادثة|ما فائدة قائمة المدرب|教练菜单和聊天的区别|教练菜单是做什么的/i,
      en: "The menu is a set of ready-made questions, grouped by topic, each wired to read your own real, current data - no free text needed, just click one. The chat box below it is for anything not already in the menu, in your own words, with the same fuzzy typo tolerance either way.",
      fa: "منو مجموعه‌ای از سوالات آماده است، دسته‌بندی‌شده بر اساس موضوع، هرکدام برای خواندنِ داده‌ی واقعی و فعلیِ خودت سیم‌کشی شده - نیازی به متن آزاد نیست، فقط یکی را کلیک کن. کادر چتِ زیرش برای هرچیزی است که هنوز در منو نیست، با کلمات خودت، با همان تحمل غلط املاییِ فازی در هر دو حالت.",
      ar: "القائمة مجموعة أسئلة جاهزة، مصنّفة حسب الموضوع، كل واحد موصول ليقرأ بياناتك الحقيقية الحالية - لا حاجة لنص حر، فقط انقر واحدًا. مربع الدردشة تحته لأي شيء ليس في القائمة بعد، بكلماتك أنت، بنفس تحمّل الأخطاء الإملائية الضبابي في كلتا الحالتين.",
      zh: "菜单是一组按主题分类的现成问题，每一个都连接读取你自己真实的当前数据——不需要输入文字，点一下就行。下面的聊天框用来问菜单里还没有的任何问题，用你自己的话，两种方式都有同样的模糊拼写容错。",
    },

    {
      key: 'app_coach_is_it_real_ai',
      match: /\b(is the coach real ai|is this a real language model|is the coach actually ai|is the coach a chatbot)(?:s|es|ing)?\b|مربی هوش مصنوعی واقعی است|این یک مدل زبانی واقعی است|هل المدرب ذكاء اصطناعي حقيقي|هل هذا نموذج لغوي حقيقي|教练是真的ai吗|这是真的语言模型吗/i,
      en: "By default, no - it's a rule-based engine that matches your question to a topic and answers from your own real data, openly, not dressed up as a language model. If you turn on the optional bring-your-own-key connector, THAT part does talk to a real external model (Gemini, ChatGPT, etc.) directly from your browser - but that's off by default and outside this project's core scope.",
      fa: "به‌طور پیش‌فرض، نه - یک موتور قانون‌محور است که سوالت را به یک موضوع تطبیق می‌دهد و از روی داده‌ی واقعیِ خودت جواب می‌دهد، صادقانه، نه آراسته به‌شکل یک مدل زبانی. اگر رابط اختیاریِ «کلید خودت را بیاور» را روشن کنی، آن بخش واقعاً با یک مدل بیرونیِ واقعی (جمنای، چت‌جی‌پی‌تی و غیره) مستقیم از مرورگرت صحبت می‌کند - اما این پیش‌فرض خاموش است و بیرون از حیطه‌ی اصلی این پروژه.",
      ar: "افتراضيًا، لا - إنه محرك قائم على القواعد يطابق سؤالك مع موضوع ويجيب من بياناتك الحقيقية، بصراحة، لا متزيّنًا كنموذج لغوي. إن فعّلت رابط 'أحضر مفتاحك الخاص' الاختياري، ذلك الجزء يتحدث فعلًا مع نموذج خارجي حقيقي (جيميني، تشات جي بي تي، إلخ) مباشرة من متصفحك - لكنه معطّل افتراضيًا وخارج نطاق هذا المشروع الأساسي.",
      zh: "默认情况下，不是——它是一个基于规则的引擎，把你的问题匹配到一个主题，然后用你自己的真实数据来回答，坦诚地，不伪装成语言模型。如果你打开可选的「自带密钥」连接器，那部分确实会直接从你的浏览器与真实的外部模型（Gemini、ChatGPT 等）对话——但这个默认是关闭的，也不在这个项目的核心范围内。",
    },

    {
      key: 'app_coach_byok_connector',
      match: /\b(byok connector|bring your own key|connect my own api key|use my own gemini key|use my own chatgpt key)(?:s|es|ing)?\b|اتصال با کلید خودم|کلید ای پی آی خودم را وصل کنم|توصيل مفتاح واجهة برمجة التطبيقات الخاص بي|استخدام مفتاحي الخاص|用我自己的api密钥|连接我自己的密钥/i,
      en: "It's an opt-in, off-by-default connector: paste an API key for a provider you already have (Gemini, ChatGPT, x.ai, Anthropic), and your messages go straight from your browser tab to that provider - never through this app's backend, never stored, never logged, gone the moment you close the tab. Turning it on replaces the rule-based coach's answers with the external model's for that session.",
      fa: "یک رابط اختیاری و پیش‌فرض‌خاموش است: یک کلید API برای یک ارائه‌دهنده که از قبل داری (جمنای، چت‌جی‌پی‌تی، ایکس‌ای‌آی، آنتروپیک) بچسبان، و پیام‌هایت مستقیم از تبِ مرورگرت به آن ارائه‌دهنده می‌رود - هرگز از بک‌اندِ این اپ عبور نمی‌کند، هرگز ذخیره نمی‌شود، هرگز لاگ نمی‌شود، همان لحظه‌ای که تب را می‌بندی از بین می‌رود. روشن‌کردنش جواب‌های مربیِ قانون‌محور را برای آن نشست با جواب‌های مدل بیرونی جایگزین می‌کند.",
      ar: "إنه رابط اختياري ومعطّل افتراضيًا: الصق مفتاح API لمزوّد لديك بالفعل (جيميني، تشات جي بي تي، x.ai، أنثروبيك)، ورسائلك تذهب مباشرة من تبويب متصفحك إلى ذلك المزوّد - لا تمر أبدًا عبر خلفية هذا التطبيق، لا تُخزَّن أبدًا، لا تُسجَّل أبدًا، تختفي لحظة إغلاق التبويب. تفعيله يستبدل إجابات المدرب القائم على القواعد بإجابات النموذج الخارجي لتلك الجلسة.",
      zh: "这是一个默认关闭、需要主动开启的连接器：粘贴一个你已有的提供商的 API 密钥（Gemini、ChatGPT、x.ai、Anthropic），你的消息就会直接从浏览器标签页发送到该提供商——绝不经过这个应用的后端，绝不存储，绝不记录日志，一关闭标签页就消失。打开它会在那次会话中用外部模型的回答替代基于规则的教练回答。",
    },

    {
      key: 'app_coach_doesnt_understand',
      match: /\b(coach doesnt understand my question|coach didnt understand|coach gave a did you mean|coach cant answer my question)(?:s|es|ing)?\b|مربی سوال من را متوجه نشد|مربی جواب منظور من نداد|المدرب لم يفهم سؤالي|المدرب لم يجب على سؤالي|教练不理解我的问题|教练没听懂我的问题/i,
      en: "If nothing clears the match threshold, you get an honest 'did you mean X or Y' with the two closest topics rather than a guess dressed up as an answer or a flat refusal - try rephrasing shorter and more literally (what you'd search for, not a full sentence) if that still doesn't land.",
      fa: "اگر چیزی از آستانه‌ی تطبیق رد نشود، یک «منظورت این بود یا آن؟» صادقانه با دو نزدیک‌ترین موضوع می‌گیری، نه یک حدسِ آراسته به‌شکل جواب یا یک ردِ خشک - اگر باز هم جواب نگرفتی، کوتاه‌تر و تحت‌اللفظی‌تر (چیزی که سرچ می‌کردی، نه یک جمله‌ی کامل) دوباره بگو.",
      ar: "إن لم يتجاوز شيء عتبة المطابقة، تحصل على 'أتقصد كذا أم كذا؟' صادقة مع أقرب موضوعين، لا تخمينًا متزيّنًا كجواب أو رفضًا جافًا - إن لم يفلح ذلك، جرّب صياغة أقصر وأكثر حرفية (ما كنت ستبحث عنه، لا جملة كاملة).",
      zh: "如果没有任何内容达到匹配阈值，你会得到一个诚实的「你是说 X 还是 Y？」，附带两个最接近的主题，而不是一个伪装成答案的猜测或干脆的拒绝——如果还是不行，试着把问题说得更短、更直白（像搜索关键词那样，而不是完整的句子）。",
    },

    {
      key: 'app_coach_privacy_of_chat',
      match: /\b(is my chat private|does the coach chat leave my device|coach chat privacy|is my conversation with the coach private)(?:s|es|ing)?\b|چت من خصوصی است|چت مربی از دستگاه من خارج میشود|هل محادثتي خاصة|هل تخرج محادثة المدرب من جهازي|我的聊天是私密的吗|教练聊天会离开我的设备吗/i,
      en: "With the connector off (the default), no external call happens at all - replies come from your own data on this device, and nothing about the exchange leaves your browser except the API request. With the connector on, your messages go directly from your tab to whichever provider you chose, never through this app's servers either way.",
      fa: "با کانکتور خاموش (پیش‌فرض)، اصلاً هیچ تماس بیرونی‌ای اتفاق نمی‌افتد - جواب‌ها از داده‌ی خودت روی همین دستگاه می‌آید، و هیچ‌چیز درباره‌ی این تبادل از مرورگرت بیرون نمی‌رود جز خودِ درخواستِ API. با کانکتورِ روشن، پیام‌هایت مستقیم از تبت به هر ارائه‌دهنده‌ای که انتخاب کردی می‌رود، در هر دو حالت هرگز از سرورهای این اپ عبور نمی‌کند.",
      ar: "مع تعطيل الرابط (الافتراضي)، لا يحدث أي اتصال خارجي إطلاقًا - الإجابات تأتي من بياناتك أنت على هذا الجهاز، ولا شيء من التبادل يغادر متصفحك سوى طلب API نفسه. مع تفعيل الرابط، رسائلك تذهب مباشرة من تبويبك إلى أي مزوّد اخترته، ولا تمر في كلتا الحالتين عبر خوادم هذا التطبيق أبدًا.",
      zh: "在连接器关闭时（默认状态），根本不会发生任何外部调用——回复来自你在这台设备上的自有数据，除了 API 请求本身，交流的任何内容都不会离开你的浏览器。连接器打开时，你的消息会直接从你的标签页发送到你选择的提供商，无论哪种情况都绝不经过这个应用的服务器。",
    },

    {
      key: 'app_coach_slash_fit',
      match: /\b(what does slash fit do|slash fit command|what is fit command in chat)(?:s|es|ing)?\b|دستور اسلش فیت چیست|کاربرد فیت در چت چیست|ماذا يفعل أمر سلاش فيت|ما فائدة أمر فيت في المحادثة|斜杠fit命令是做什么的|聊天里的fit命令是什么/i,
      en: "Typing /fit into the chat box explicitly loads your current check-in context (score, factors, history) into the conversation - useful mainly for the external connector, since a real language model has no way to see your data unless it's placed in the message itself.",
      fa: "تایپ‌کردنِ /fit در کادر چت به‌صراحت زمینه‌ی بررسیِ فعلی‌ات (امتیاز، عامل‌ها، تاریخچه) را در گفتگو بار می‌کند - عمدتاً برای کانکتورِ بیرونی مفید است، چون یک مدل زبانیِ واقعی راهی برای دیدنِ داده‌ات ندارد مگر اینکه در خودِ پیام گذاشته شود.",
      ar: "كتابة /fit في مربع الدردشة تحمّل صراحة سياق فحصك الحالي (الدرجة، العوامل، التاريخ) في المحادثة - مفيد أساسًا لرابط الاتصال الخارجي، لأن نموذجًا لغويًا حقيقيًا لا سبيل له لرؤية بياناتك ما لم توضع في الرسالة نفسها.",
      zh: "在聊天框里输入 /fit 会明确把你当前的检测背景（分数、因素、历史）加载进对话——这主要对外部连接器有用，因为一个真实的语言模型没有办法看到你的数据，除非把它放进消息本身。",
    },

    
    // ================= H. Analytics =================
    {
      key: 'app_analytics_risk_alerts',
      match: /\b(what are risk alerts|how are risk alerts calculated|risk alert card meaning|why did i get a risk alert)(?:s|es|ing)?\b|هشدارهای خطر چیستند|کارت هشدار خطر یعنی چه|چرا هشدار خطر گرفتم|ما هي تنبيهات الخطر|بطاقة تنبيه الخطر تعني ماذا|لماذا تلقيت تنبيه خطر|风险提醒是什么|风险警示卡是什么意思|为什么我收到风险提醒/i,
      en: "Three independent rules, all grounded in your own real check-in history, no model inference involved: a real consecutive At-Risk streak, a real multi-day decline in your score, or today being a genuine statistical outlier against your own typical range. None of them name a medical condition or tell you what to do medically - only what to look at.",
      fa: "سه قاعده‌ی مستقل، همه بر پایه‌ی تاریخچه‌ی واقعیِ بررسیِ خودت، بدون هیچ استنتاج مدلی: یک استریکِ پیاپیِ واقعیِ در معرض خطر، یک افتِ چندروزه‌ی واقعی در امتیازت، یا اینکه امروز یک نقطه‌پرتِ آماریِ واقعی در برابر بازه‌ی معمولِ خودت است. هیچ‌کدام یک شرایط پزشکی نام نمی‌برند یا نمی‌گویند از نظر پزشکی چه کار کنی - فقط اینکه به چه چیزی نگاه کنی.",
      ar: "ثلاث قواعد مستقلة، كلها مبنية على تاريخ فحصك الحقيقي أنت، بلا أي استنتاج نموذجي: سلسلة متتالية حقيقية في خطر، أو تراجع حقيقي متعدد الأيام في درجتك، أو أن اليوم قيمة شاذة إحصائية حقيقية مقابل نطاقك المعتاد. لا شيء منها يسمّي حالة طبية أو يخبرك بما تفعله طبيًا - فقط ما ينبغي النظر إليه.",
      zh: "三条独立规则，全部基于你自己真实的检测历史，不涉及任何模型推断：一个真实的连续「有风险」记录、一个真实的多日分数下降趋势，或者今天相对于你自己的典型范围是一个真实的统计异常值。它们都不会指出某种医学状况，也不会告诉你医学上该怎么做——只是提示你该关注什么。",
    },

    {
      key: 'app_analytics_correlation_not_causation',
      match: /\b(correlation not causation|does this mean it causes it|moved together with meaning|relationship card meaning)(?:s|es|ing)?\b|همبستگی نه علیت|یعنی این باعث آن میشود|کارت رابطه یعنی چه|الارتباط ليس سببية|هل هذا يعني أنه سبب|بطاقة العلاقة تعني ماذا|相关不等于因果|这意味着导致了吗|关系卡片是什么意思/i,
      en: "Every relationship card is explicitly marked observation-only and uses 'moved together with' / 'moved opposite to' language, never 'causes' or 'because of' - it's a real statistical pattern found in your own logged days, Bonferroni-corrected so it isn't just noise dressed up as a finding, but it's still an association, not a mechanism.",
      fa: "هر کارتِ رابطه صریحاً فقط-مشاهده‌ای علامت‌گذاری شده و از زبانِ «هم‌جهت حرکت کرده با» / «مخالف حرکت کرده با» استفاده می‌کند، هرگز «باعث می‌شود» یا «به‌خاطر» - یک الگوی آماریِ واقعی در روزهای ثبت‌شده‌ی خودت است، با تصحیح بونفرونی که یعنی فقط نویزی نیست که به‌شکل یک یافته آراسته شده، اما هنوز یک همبستگی است، نه یک مکانیزم.",
      ar: "كل بطاقة علاقة موسومة صراحة كملاحظة فقط وتستخدم لغة 'تحرّك مع' / 'تحرّك عكس'، لا 'يسبب' أو 'بسبب' أبدًا - إنه نمط إحصائي حقيقي وُجد في أيامك المسجَّلة، مصحَّح ببونفروني بمعنى أنه ليس مجرد ضجيج متزيّن كنتيجة، لكنه لا يزال ارتباطًا لا آلية.",
      zh: "每一张关系卡片都明确标注为「仅供观察」，用的是「与……同向变化」/「与……反向变化」这样的措辞，绝不用「导致」或「因为」——这是在你自己记录的日子里发现的真实统计模式，经过 Bonferroni 校正，意味着它不只是打扮成发现的噪声，但它仍然是一种关联，不是一种机制。",
    },

    {
      key: 'app_analytics_weekly_challenges',
      match: /\b(weekly challenges explained|how are challenge targets set|where do challenge targets come from)(?:s|es|ing)?\b|چالش‌های هفتگی چطور کار میکنند|هدف چالش از کجا میاید|كيف تعمل التحديات الأسبوعية|من أين يأتي هدف التحدي|每周挑战是怎么回事|挑战目标是怎么定的/i,
      en: "Targets are derived from your own typical profile (the same baselines Analytics computes), never a generic number like 'everyone should sleep 8 hours' - one challenge (a daily check-in streak) is unconditional, the rest need enough of your own history to compute a personal target from.",
      fa: "هدف‌ها از روی پروفایلِ معمولِ خودت (همان خط‌پایه‌هایی که تحلیل محاسبه می‌کند) گرفته می‌شوند، هرگز یک عددِ عمومی مثل «همه باید ۸ ساعت بخوابند» - یک چالش (استریکِ روزانه‌ی بررسی) بی‌قیدوشرط است، بقیه به اندازه‌ی کافی تاریخچه‌ی خودت نیاز دارند تا یک هدفِ شخصی از رویش محاسبه شود.",
      ar: "الأهداف مستمَدة من ملفك النمطي أنت (نفس خطوط الأساس التي يحسبها التحليل)، أبدًا رقمًا عامًا مثل 'الجميع يجب أن ينام 8 ساعات' - تحدٍ واحد (سلسلة الفحص اليومي) غير مشروط، والباقي يحتاج تاريخًا كافيًا لك لحساب هدف شخصي منه.",
      zh: "目标是从你自己的典型画像（分析计算出的同一套基线）推导出来的，绝不是「每个人都应该睡 8 小时」这种通用数字——有一个挑战（每日检测连续记录）是无条件的，其余的需要足够多你自己的历史数据才能计算出一个个人化的目标。",
    },

    {
      key: 'app_analytics_exception_day',
      match: /\b(exception day in analytics|unusual day doesnt count|excluded day and analytics)(?:s|es|ing)?\b|روز استثنا در تحلیل‌ها|روز غیرعادی حساب نمیشود|اليوم الاستثنائي في التحليلات|اليوم غير المعتاد لا يُحتسب|分析中的例外日|特殊的一天不计入统计/i,
      en: "The one interaction that changes the product rather than just talking about it: the app can't tell a genuinely unusual day (a flight, an illness) from a bad habit, because they look identical in the numbers - only you can, and marking one removes it from every average, streak and pattern from then on, which makes all of them more honest.",
      fa: "تنها تعاملی که به‌جای حرف‌زدن درباره‌ی محصول، خودِ محصول را عوض می‌کند: اپ نمی‌تواند یک روزِ واقعاً غیرعادی (یک پرواز، یک بیماری) را از یک عادتِ بد تشخیص بدهد، چون در اعداد کاملاً شبیه‌اند - فقط تو می‌توانی، و علامت‌زدن یکی آن را از آن پس از هر میانگین و استریک و الگویی بیرون می‌برد، که همه را صادق‌تر می‌کند.",
      ar: "التفاعل الوحيد الذي يغيّر المنتج بدل أن يتحدث عنه فقط: التطبيق لا يستطيع تمييز يوم غير عادي فعلًا (رحلة طيران، مرض) عن عادة سيئة، لأنهما متطابقان في الأرقام - أنت وحدك تستطيع، ووضع علامة يخرجه من كل متوسط وسلسلة ونمط من بعدها، ما يجعلها جميعًا أصدق.",
      zh: "这是唯一一个真正改变产品本身而不只是谈论产品的交互：应用无法分辨一个真正不寻常的日子（一次航班、一场生病）和一个坏习惯，因为它们在数字上完全一样——只有你能，标记之后它会从此被排除在所有平均值、连续记录和模式之外，这让它们都变得更诚实。",
    },

    {
      key: 'app_analytics_no_data_yet',
      match: /\b(analytics card missing|why is this analytics card not showing|not enough data for analytics|no data yet analytics)(?:s|es|ing)?\b|کارت تحلیل نمایش داده نمیشود|داده کافی برای تحلیل نیست|بطاقة التحليلات لا تظهر|لا توجد بيانات كافية للتحليل|分析卡片没有显示|数据不够无法分析/i,
      en: "Several cards (correlations, weekly comparisons, the risk-decline rule) need a real minimum number of logged days before they can say anything honest - they stay hidden rather than showing a placeholder that pretends to be a finding. Log a few more real days and they appear on their own.",
      fa: "چند کارت (همبستگی‌ها، مقایسه‌های هفتگی، قاعده‌ی افت ریسک) پیش از اینکه بتوانند چیزِ صادقانه‌ای بگویند، به یک حداقلِ واقعیِ روزِ ثبت‌شده نیاز دارند - به‌جای نشان‌دادن یک جانگهدارنده که وانمود می‌کند یافته است، پنهان می‌مانند. چند روزِ واقعیِ دیگر ثبت کن و خودشان ظاهر می‌شوند.",
      ar: "عدة بطاقات (الارتباطات، المقارنات الأسبوعية، قاعدة تراجع الخطر) تحتاج حدًا أدنى حقيقيًا من الأيام المسجَّلة قبل أن تقول شيئًا صادقًا - تبقى مخفية بدل إظهار عنصر نائب يتظاهر بأنه نتيجة. سجّل بضعة أيام حقيقية أخرى وستظهر من تلقاء نفسها.",
      zh: "有几张卡片（相关性、每周对比、风险下降规则）需要真实的最少记录天数才能说出诚实的内容——它们会保持隐藏，而不是显示一个假装是发现的占位符。再记录几天真实的数据，它们就会自己出现。",
    },

    
    // ================= I. Friends League =================
    {
      key: 'app_league_two_accounts_needed',
      match: /\b(need two accounts for league|how do i test the league chat|friends league needs two accounts|testing league with one account)(?:s|es|ing)?\b|برای لیگ دو حساب لازم است|چطور چت لیگ را تست کنم|أحتاج حسابين لدوري الأصدقاء|كيف أختبر محادثة الدوري|好友联赛需要两个账户|怎么测试联赛聊天/i,
      en: "The Friends League and its chat are genuinely two-sided - one account can't demonstrate a conversation any more than one phone can demonstrate a text message. Testing it for real needs two accounts that don't share a browser session (two different browsers, or a normal window plus a private/incognito one); Demo Mode's synthetic friend seeds one opening line but never replies, so it isn't a substitute for a real back-and-forth.",
      fa: "لیگ دوستان و چتش واقعاً دوطرفه‌اند - یک اکانت نمی‌تواند یک گفتگو را نشان دهد، همان‌طور که یک گوشی نمی‌تواند یک پیامک را نشان دهد. تست واقعی‌اش به دو اکانت نیاز دارد که یک نشستِ مرورگر را به‌اشتراک نگذارند (دو مرورگر متفاوت، یا یک پنجره‌ی معمولی به‌علاوه یک پنجره‌ی ناشناس)؛ دوستِ ساختگیِ حالت دمو یک خط آغازین می‌کارد اما هرگز جواب نمی‌دهد، پس جایگزینِ یک رفت‌وبرگشتِ واقعی نیست.",
      ar: "دوري الأصدقاء ودردشته ثنائيان فعلًا - حساب واحد لا يمكنه إظهار محادثة أكثر مما يمكن لهاتف واحد إظهار رسالة نصية. اختباره فعليًا يحتاج حسابين لا يشتركان في جلسة متصفح (متصفحان مختلفان، أو نافذة عادية إضافة إلى نافذة خاصة/تصفح متخفٍّ)؛ صديق الوضع التجريبي الاصطناعي يزرع سطرًا افتتاحيًا واحدًا لكنه لا يرد أبدًا، فهو ليس بديلًا عن تبادل حقيقي.",
      zh: "好友联赛及其聊天功能是真正双向的——一个账号无法展示一段对话，就像一部手机无法展示一条短信一样。真正测试它需要两个不共享浏览器会话的账号（两个不同的浏览器，或一个普通窗口加一个隐私/无痕窗口）；演示模式的虚拟好友只会种下一句开场白，但从不回复，所以它不能替代真实的往返对话。",
    },

    {
      key: 'app_league_invite_code',
      match: /\b(where is my invite code|league invite code|how do i invite a friend|get my invite code)(?:s|es|ing)?\b|کد دعوت من کجاست|کد دعوت لیگ|چطور دوستم را دعوت کنم|أين رمز الدعوة الخاص بي|رمز دعوة الدوري|كيف أدعو صديقا|我的邀请码在哪|联赛邀请码|怎么邀请朋友/i,
      en: "It's shown at the top of the Friends League page once you've accepted the League rules - it's yours alone and doesn't change, so you can hand it to a friend once and it keeps working for future requests too.",
      fa: "بالای صفحه‌ی لیگ دوستان نشان داده می‌شود، به‌محض اینکه قوانین لیگ را پذیرفتی - فقط مالِ خودت است و عوض نمی‌شود، پس می‌توانی یک‌بار به یک دوست بدهی و برای درخواست‌های آینده هم کار می‌کند.",
      ar: "يُعرض أعلى صفحة دوري الأصدقاء بمجرد قبولك قواعد الدوري - إنه ملكك وحدك ولا يتغير، فيمكنك إعطاءه لصديق مرة واحدة وسيستمر بالعمل لطلبات مستقبلية أيضًا.",
      zh: "一旦你接受了联赛规则，它就会显示在好友联赛页面的顶部——它只属于你，而且不会改变，所以你可以给朋友一次，以后的请求它也一直有效。",
    },

    {
      key: 'app_league_sharing_categories',
      match: /\b(what do i share with friends|league sharing categories|persona score rank top factor sharing|what data does my friend see)(?:s|es|ing)?\b|با دوستانم چه چیزی به اشتراک میگذارم|دسته‌بندی‌های اشتراک‌گذاری لیگ|ماذا أشارك مع أصدقائي|فئات المشاركة في الدوري|我和朋友分享了什么|联赛分享的类别|朋友能看到什么数据/i,
      en: "Four categories, each toggled independently: persona, score, rank and top factor. You choose your own set when you send or accept a request, and it's revocable at any time afterward - your friend sees nothing until you've both explicitly agreed, and only exactly what you agreed to.",
      fa: "چهار دسته، هرکدام مستقل روشن/خاموش می‌شود: پرسونا، امتیاز، رتبه و عامل برتر. مجموعه‌ی خودت را وقتی درخواست می‌فرستی یا می‌پذیری انتخاب می‌کنی، و بعدش هر وقت خواستی قابل‌لغو است - دوستت تا وقتی هردوتان صریحاً موافقت نکرده‌اید هیچ‌چیز نمی‌بیند، و فقط دقیقاً همانی که موافقت کردی.",
      ar: "أربع فئات، كل واحدة تُبدَّل باستقلالية: الشخصية، الدرجة، الترتيب، والعامل الأعلى. تختار مجموعتك الخاصة عند إرسال أو قبول طلب، وقابلة للإلغاء لاحقًا في أي وقت - صديقك لا يرى شيئًا حتى توافقا صراحة كلاكما، وفقط بالضبط ما وافقت عليه.",
      zh: "四个类别，各自独立开关：人格画像、分数、排名和最主要因素。你在发送或接受请求时选择自己的组合，之后随时可以撤销——你的朋友在你们双方明确同意之前什么都看不到，而且只看到你确切同意分享的内容。",
    },

    {
      key: 'app_league_block_report',
      match: /\b(how do i block someone|how do i report a message|block a friend in league|report a message in chat)(?:s|es|ing)?\b|چطور کسی را بلاک کنم|چطور پیامی را گزارش کنم|كيف أحظر شخصا|كيف أبلغ عن رسالة|怎么屏蔽某人|怎么举报消息/i,
      en: "Both actions live inside an open chat. Blocking is symmetric and immediate - neither side can read or write until it's undone. Reporting flags a specific message for a human to review and doesn't require blocking at the same time, so you can report without cutting off the conversation if you'd rather not.",
      fa: "هر دو کار داخل یک چتِ باز انجام می‌شوند. بلاک‌کردن متقارن و فوری است - هیچ‌کدام تا برنگردانی نمی‌توانید بخوانید یا بنویسید. گزارش‌کردن یک پیامِ مشخص را برای بررسیِ انسانی پرچم می‌زند و نیازی نیست هم‌زمان بلاک هم بکنی، پس اگر ترجیح می‌دهی گفتگو را قطع نکنی، می‌توانی فقط گزارش کنی.",
      ar: "كلا الإجراءين داخل محادثة مفتوحة. الحظر متماثل وفوري - لا يستطيع أي طرف القراءة أو الكتابة حتى يُلغى. الإبلاغ يضع علامة على رسالة محددة كي يراجعها إنسان ولا يتطلب الحظر بنفس الوقت، فيمكنك الإبلاغ دون قطع المحادثة إن فضّلت ذلك.",
      zh: "这两个操作都在打开的聊天窗口里进行。拉黑是对称且即时的——在撤销之前双方都无法读写。举报会标记一条具体消息供人工审核，并不要求同时拉黑，所以如果你不想中断对话，可以只举报。",
    },

    {
      key: 'app_league_remove_friend',
      match: /\b(remove a friend from league|how do i remove a connection|unfriend someone in league)(?:s|es|ing)?\b|حذف دوست از لیگ|چطور یک ارتباط را حذف کنم|إزالة صديق من الدوري|كيف أزيل اتصالا|从联赛中删除朋友|怎么移除一个联系人/i,
      en: "Removing a connection closes the chat in the same moment it removes the data sharing - there's no window where the other side still has an open thread or can still see your shared categories. It's a one-sided action: your friend just sees the connection is gone.",
      fa: "حذف یک ارتباط، در همان لحظه‌ای که اشتراک داده را قطع می‌کند چت را هم می‌بندد - هیچ فاصله‌ای نیست که طرف مقابل هنوز یک رشته‌ی باز داشته باشد یا هنوز بتواند دسته‌های به‌اشتراک‌گذاشته‌شده‌ات را ببیند. یک اقدامِ یک‌طرفه است: دوستت فقط می‌بیند که ارتباط رفته.",
      ar: "إزالة اتصال تُغلق الدردشة في اللحظة نفسها التي تُنهي فيها مشاركة البيانات - لا توجد فترة يظل فيها الطرف الآخر يملك خيطًا مفتوحًا أو لا يزال يرى فئاتك المشتركة. إنه إجراء أحادي الجانب: صديقك يرى فقط أن الاتصال اختفى.",
      zh: "移除一个联系人会在切断数据共享的同一时刻关闭聊天——不存在对方还留有开放对话线程或仍能看到你共享类别的空档期。这是单方面的操作：你的朋友只会看到联系人消失了。",
    },

    {
      key: 'app_league_group_chat',
      match: /\b(how do i make a group chat|league group chat|create a group in the league)(?:s|es|ing)?\b|چطور گروه چت بسازم|چت گروهی لیگ|كيف أنشئ محادثة جماعية|محادثة جماعية في الدوري|怎么建群聊|联赛群聊/i,
      en: "You can make a group chat from your existing League connections - only people you're already individually connected to (with an accepted request) can be added, so a group can't be used to route around the one-to-one consent model.",
      fa: "می‌توانی از ارتباط‌های موجودِ لیگ‌ات یک چت گروهی بسازی - فقط کسانی که از قبل به‌طور جداگانه به آن‌ها متصلی (با درخواستِ پذیرفته‌شده) قابل‌اضافه‌شدن‌اند، پس یک گروه نمی‌تواند برای دورزدنِ مدلِ رضایتِ یک‌به‌یک استفاده شود.",
      ar: "يمكنك إنشاء دردشة جماعية من اتصالات دوريك الحالية - فقط من أنت متصل بهم فرديًا بالفعل (بطلب مقبول) يمكن إضافتهم، فلا يمكن استخدام المجموعة للالتفاف حول نموذج الموافقة الفردية.",
      zh: "你可以从现有的联赛联系人中创建群聊——只有你已经单独建立联系（已接受请求）的人才能被添加，所以群组无法被用来绕过一对一的同意模式。",
    },

    {
      key: 'app_league_pending_requests',
      match: /\b(pending league requests|requests i sent|waiting for approval league|friend request still pending)(?:s|es|ing)?\b|درخواست‌های در انتظار لیگ|درخواست‌هایی که فرستادم|طلبات الدوري المعلقة|الطلبات التي أرسلتها|联赛待处理请求|我发送的请求/i,
      en: "A request you sent sits under 'Requests you've sent' until the other side responds; one you received sits under 'Waiting for your approval' until you act on it. Nothing about either side's data is visible during that wait - the whole point of two-step consent is that pending means pending.",
      fa: "درخواستی که فرستادی زیر «درخواست‌های ارسالی‌ات» می‌ماند تا طرف مقابل جواب دهد؛ درخواستی که گرفتی زیر «منتظر تاییدت» می‌ماند تا رویش اقدام کنی. در طول آن انتظار هیچ‌چیزی از داده‌ی هیچ‌کدام طرف قابل‌دیدن نیست - کلِ نکته‌ی رضایتِ دومرحله‌ای این است که معلق یعنی معلق.",
      ar: "طلب أرسلته يبقى تحت 'طلبات أرسلتها' حتى يرد الطرف الآخر؛ طلب استلمته يبقى تحت 'بانتظار موافقتك' حتى تتصرف حياله. لا شيء من بيانات أي طرف مرئي خلال ذلك الانتظار - كل الفكرة من الموافقة ذات الخطوتين أن المعلَّق يعني معلَّقًا.",
      zh: "你发出的请求会留在「已发送的请求」下，直到对方回应；你收到的请求会留在「等待你批准」下，直到你处理它。在等待期间，双方的数据都不可见——两步同意的整个意义就在于「待处理」真的意味着待处理。",
    },

    
    // ================= J. What-if simulator =================
    {
      key: 'app_whatif_what_is_it',
      match: /\b(what is the what if simulator|what if simulator explained|how does the what if tool work)(?:s|es|ing)?\b|شبیه‌ساز چه میشود اگر چیست|ابزار چه میشود اگر چطور کار میکند|ما هي محاكاة ماذا لو|كيف تعمل أداة ماذا لو|假设模拟器是什么|假设工具怎么运作/i,
      en: "It sweeps one field across its real range while holding everything else at your own submitted values, running the actual trained model at every point - not an approximation, a real prediction per step, so the curve you see is what the model would genuinely say if that one thing changed.",
      fa: "یک فیلد را در بازه‌ی واقعی‌اش جارو می‌کند درحالی‌که بقیه را روی مقادیرِ فرستاده‌شده‌ی خودت نگه می‌دارد، مدلِ آموزش‌دیده‌ی واقعی را در هر نقطه اجرا می‌کند - نه یک تقریب، یک پیش‌بینیِ واقعی در هر گام، پس منحنی‌ای که می‌بینی همان چیزی است که مدل واقعاً می‌گفت اگر آن یک چیز عوض می‌شد.",
      ar: "يمسح حقلًا واحدًا عبر نطاقه الحقيقي بينما يُبقي كل شيء آخر عند قيمك المُرسَلة أنت، مُشغِّلًا النموذج المدرَّب الحقيقي عند كل نقطة - ليس تقريبًا، بل تنبؤًا حقيقيًا لكل خطوة، فالمنحنى الذي تراه هو ما كان النموذج سيقوله فعلًا لو تغيّر ذلك الشيء الواحد.",
      zh: "它会在一个字段的真实范围内扫描，同时保持其他所有字段为你自己提交的值，在每一个点上运行真实训练好的模型——不是近似值，每一步都是真实预测，所以你看到的曲线就是如果那一件事改变了，模型真正会给出的结果。",
    },

    {
      key: 'app_whatif_changes_my_data',
      match: /\b(does what if change my data|does the simulator save anything|what if tool saved my data)(?:s|es|ing)?\b|آیا شبیه‌ساز داده من را تغییر میدهد|آیا ابزار چه میشود اگر ذخیره میکند|هل تغير المحاكاة بياناتي|هل تحفظ الأداة أي شيء|假设模拟器会改变我的数据吗|这个工具会保存数据吗/i,
      en: "Nothing here is saved or persisted - every sweep runs against your last real submission in memory, and closing or reloading the page discards it. It's for exploring 'what if', not for logging a new day.",
      fa: "هیچ‌چیز اینجا ذخیره یا ماندگار نمی‌شود - هر جاروکردن روی آخرین ارسالِ واقعی‌ات در حافظه اجرا می‌شود، و بستن یا رفرشِ صفحه دورش می‌اندازد. برای کاوشِ «اگر چه» است، نه برای ثبتِ یک روز جدید.",
      ar: "لا شيء هنا يُحفظ أو يستمر - كل مسح يعمل مقابل آخر إرسال حقيقي لك في الذاكرة، وإغلاق أو إعادة تحميل الصفحة يتجاهله. إنه لاستكشاف 'ماذا لو'، لا لتسجيل يوم جديد.",
      zh: "这里的任何东西都不会被保存或持久化——每次扫描都是针对内存中你最后一次真实提交的数据运行的，关闭或刷新页面会丢弃它。它是用来探索「如果……会怎样」的，不是用来记录新的一天的。",
    },

    
    // ================= K. Settings =================
    {
      key: 'app_settings_theme',
      match: /\b(dark mode|light mode|change theme|where is the theme setting|system theme option)(?:s|es|ing)?\b|حالت تیره|حالت روشن|تغییر تم|تنظیمات تم کجاست|الوضع الداكن|الوضع الفاتح|تغيير المظهر|أين إعداد المظهر|深色模式|浅色模式|更改主题|主题设置在哪/i,
      en: "Theme lives in Settings, with a light/dark toggle plus a 'system' option that follows your OS/browser preference automatically. It's saved per browser, same as the language choice.",
      fa: "تم در تنظیمات است، با یک سوییچِ روشن/تاریک به‌علاوه یک گزینه‌ی «سیستم» که ترجیح سیستم‌عامل/مرورگرت را خودکار دنبال می‌کند. مثل انتخابِ زبان، به‌ازای هر مرورگر ذخیره می‌شود.",
      ar: "السمة موجودة في الإعدادات، بمبدّل فاتح/داكن إضافة إلى خيار 'النظام' الذي يتبع تفضيل نظام تشغيلك/متصفحك تلقائيًا. تُحفظ لكل متصفح، تمامًا مثل اختيار اللغة.",
      zh: "主题设置在「设置」里，有一个浅色/深色开关，还有一个「跟随系统」选项，会自动跟随你操作系统/浏览器的偏好。它按浏览器保存，和语言选择一样。",
    },

    {
      key: 'app_settings_games_toggle',
      match: /\b(turn off the games|games after checkin toggle|disable the games|how do i skip games entirely)(?:s|es|ing)?\b|خاموش کردن بازی‌ها|کلید بازی بعد از چکین|غیرفعال کردن بازی‌ها|إيقاف الألعاب|مفتاح الألعاب بعد التسجيل|تعطيل الألعاب|关闭游戏|打卡后游戏开关|禁用游戏/i,
      en: "Settings has a 'Games after a check-in' switch, on by default. Turning it off skips both the pre-result guessing games and the post-result ones entirely - you go straight from processing to your result, no games view in between.",
      fa: "تنظیمات یک سوییچِ «بازی‌ها بعد از هر بررسی» دارد، به‌طور پیش‌فرض روشن. خاموش‌کردنش هم بازی‌های حدس‌زدنِ پیش از نتیجه و هم بازی‌های بعد از نتیجه را کاملاً رد می‌کند - مستقیم از پردازش به نتیجه‌ات می‌روی، بدون نمای بازی در میانه.",
      ar: "الإعدادات تحتوي مفتاح 'ألعاب بعد كل فحص'، مفعّل افتراضيًا. إيقافه يتخطى ألعاب التخمين ما قبل النتيجة وما بعدها كليًا - تذهب مباشرة من المعالجة إلى نتيجتك، بلا شاشة ألعاب بينهما.",
      zh: "设置里有一个「检测后的小游戏」开关，默认开启。关闭它会完全跳过结果前的猜测游戏和结果后的游戏——你会直接从处理阶段进入结果页面，中间没有游戏页面。",
    },

    {
      key: 'app_settings_sound_motion',
      match: /\b(turn off sound|turn off animations|reduce motion setting|mute sound effects)(?:s|es|ing)?\b|خاموش کردن صدا|خاموش کردن انیمیشن‌ها|کاهش حرکت|إيقاف الصوت|إيقاف الرسوم المتحركة|تقليل الحركة|关闭声音|关闭动画|减少动效/i,
      en: "Sound and motion are two separate switches, both in Settings (and sound has a shortcut right next to the music widget too) - muting the synthesized sound effects doesn't turn off animations, and reducing motion doesn't mute sound, so you can pick either independently.",
      fa: "صدا و حرکت دو سوییچِ جدا هستند، هر دو در تنظیمات (و صدا یک میان‌بر درست کنارِ ویجتِ موسیقی هم دارد) - بی‌صداکردنِ افکت‌های صوتیِ ساختگی انیمیشن‌ها را خاموش نمی‌کند، و کاهشِ حرکت صدا را بی‌صدا نمی‌کند، پس می‌توانی هرکدام را مستقل انتخاب کنی.",
      ar: "الصوت والحركة مفتاحان منفصلان، كلاهما في الإعدادات (والصوت له اختصار بجانب أداة الموسيقى أيضًا) - كتم المؤثرات الصوتية المُصنَّعة لا يوقف الرسوم المتحركة، وتقليل الحركة لا يكتم الصوت، فيمكنك اختيار أيّ منهما باستقلالية.",
      zh: "声音和动效是两个独立的开关，都在设置里（声音在音乐小组件旁边还有一个快捷方式）——静音合成音效不会关闭动画，减少动效也不会静音，所以你可以独立选择任意一个。",
    },

    
    // ================= L. History / badges / dashboard =================
    {
      key: 'app_history_missing_days',
      match: /\b(missing days in history|why is a day missing from history|history has gaps|skipped day not in history)(?:s|es|ing)?\b|روزهای گمشده در تاریخچه|چرا یک روز در تاریخچه نیست|أيام مفقودة في السجل|لماذا يوم مفقود من السجل|历史记录缺少几天|为什么历史里少了一天/i,
      en: "History only shows days you actually submitted a check-in for - there's no automatic fill-in for a day you skipped, since inventing a number for a day you didn't log would be exactly the kind of fabrication this app avoids everywhere else. A gap in your chart just means you didn't check in that day.",
      fa: "تاریخچه فقط روزهایی را نشان می‌دهد که واقعاً برایشان بررسی فرستادی - برای روزی که رد کردی هیچ پرکردنِ خودکاری نیست، چون اختراعِ یک عدد برای روزی که ثبتش نکردی دقیقاً همان نوع جعلی است که این اپ همه‌جای دیگر ازش پرهیز می‌کند. یک فاصله در نمودارت فقط یعنی آن روز بررسی نکرده‌ای.",
      ar: "التاريخ يُظهر فقط الأيام التي أرسلت فحصًا حقيقيًا لها - لا تعبئة تلقائية ليوم تخطّيته، لأن اختلاق رقم ليوم لم تسجّله سيكون بالضبط نوع الاختلاق الذي يتجنبه هذا التطبيق في كل مكان آخر. فجوة في رسمك تعني فقط أنك لم تسجّل ذلك اليوم.",
      zh: "历史记录只显示你实际提交过检测的日子——跳过的那天不会自动补全，因为为你没有记录的一天编造一个数字，正是这个应用在其他地方一直避免的那种虚构行为。图表里的空缺只意味着那天你没有做检测。",
    },

    {
      key: 'app_streak_meaning',
      match: /\b(what does streak mean|how is my streak calculated|does missing a day reset my streak)(?:s|es|ing)?\b|استریک یعنی چه|زنجیره روزها چطور محاسبه میشود|آیا از دست دادن یک روز استریک را صفر میکند|ماذا يعني التتابع|كيف يحسب تتابع الأيام|هل فقدان يوم يصفر التتابع|连续打卡是什么意思|连续天数怎么算|错过一天会清零吗/i,
      en: "It's your current run of consecutive days with a real check-in. Missing a day shortens it rather than resetting it to zero outright in most of the streak-facing copy - the framing throughout the app is deliberately about the cost of a gap, not punishment, since a hard reset tends to make people quit rather than restart.",
      fa: "این رشته‌ی جاریِ روزهای پیاپی با یک بررسیِ واقعی است. ازدست‌دادنِ یک روز در بیشترِ متنِ مربوط به استریک آن را کوتاه می‌کند، نه اینکه کاملاً به صفر برگرداند - قاب‌بندیِ سراسرِ اپ عمداً درباره‌ی هزینه‌ی یک فاصله است، نه تنبیه، چون یک ریست سخت معمولاً باعث می‌شود آدم‌ها به‌جای شروعِ دوباره، بی‌خیال شوند.",
      ar: "إنها سلسلتك الحالية من الأيام المتتالية بفحص حقيقي. تفويت يوم يقصّرها بدل إعادة تصفيرها كليًا في معظم النصوص المتعلقة بالسلسلة - الإطار في كل التطبيق يدور عمدًا حول تكلفة الفجوة، لا العقاب، لأن إعادة الضبط الصارمة تدفع الناس للاستسلام بدل إعادة البدء.",
      zh: "这是你当前连续做真实检测的天数。在大部分与连续记录相关的文案中，漏掉一天会缩短它，而不是彻底归零——整个应用的措辞刻意围绕「中断的代价」，而不是「惩罚」，因为强制归零往往会让人放弃而不是重新开始。",
    },

    {
      key: 'app_badges_achievements',
      // "Private badges" deliberately does NOT appear here: it has its
      // own topic (app_badges_private_ones) that explains *why* some
      // badges are private, which is a different question from "how do
      // badges work". Leaving the phrase in both made the general topic
      // win the specific question, since an exact regex hit outranks a
      // fuzzy phrase match.
      match: /\b(how do i get badges|badges and achievements|how are badges earned)(?:s|es|ing)?\b|چطور نشان بگیرم|نشان‌ها و دستاوردها|كيف أحصل على الأوسمة|الأوسمة والإنجازات|怎么获得徽章|徽章和成就/i,
      en: "Badges are computed from your real history (streaks, milestones, behaviors), never awarded manually, and some are marked private on purpose - awareness indicators that flag a pattern worth noticing rather than something to show off, so they stay out of the public Hall of Fame while achievement badges appear there.",
      fa: "نشان‌ها از روی تاریخچه‌ی واقعی‌ات (استریک‌ها، نقاط عطف، رفتارها) محاسبه می‌شوند، هرگز دستی اهدا نمی‌شوند، و برخی عمداً خصوصی علامت‌گذاری شده‌اند - شاخص‌های آگاهی که یک الگوی ارزشِ توجه‌داشتن را پرچم می‌زنند، نه چیزی برای به‌نمایش‌گذاشتن، پس از تالار افتخارِ عمومی بیرون می‌مانند درحالی‌که نشان‌های دستاورد آنجا ظاهر می‌شوند.",
      ar: "الشارات تُحسب من تاريخك الحقيقي (السلاسل، المعالم، السلوكيات)، لا تُمنح يدويًا أبدًا، وبعضها موسوم كخاص عمدًا - مؤشرات وعي تُشير إلى نمط يستحق الملاحظة لا شيئًا للتباهي به، فتبقى خارج قاعة الشهرة العامة بينما شارات الإنجاز تظهر هناك.",
      zh: "徽章是根据你的真实历史（连续记录、里程碑、行为）计算出来的，绝不是手动颁发的，有些故意标记为私密——这些是提示某种值得注意的模式的「意识指标」，而不是拿来炫耀的东西，所以它们不会出现在公开的荣誉殿堂里，而成就徽章会出现在那里。",
    },

    {
      key: 'app_dashboard_overview',
      match: /\b(what is on the dashboard|dashboard overview|what does the dashboard show)(?:s|es|ing)?\b|داشبورد چه چیزی نشان میدهد|نمای کلی داشبورد|ماذا تعرض لوحة التحكم|نظرة عامة على لوحة التحكم|仪表盘上有什么|仪表盘概览/i,
      en: "It's the one-glance summary: your latest score, current streak, recent trend, and quick links into the deeper pages (weekly plan, analytics, coach) - everything on it traces back to the same real prediction and history the rest of the app uses, nothing summarized twice with different numbers.",
      fa: "این خلاصه‌ی یک‌نگاهی است: آخرین امتیازت، استریکِ فعلی، روندِ اخیر، و لینک‌های سریع به صفحات عمیق‌تر (برنامه‌ی هفتگی، تحلیل، مربی) - هرچیز رویش به همان پیش‌بینی و تاریخچه‌ی واقعی‌ای برمی‌گردد که بقیه‌ی اپ استفاده می‌کند، هیچ‌چیز دوبار با اعدادِ متفاوت خلاصه نمی‌شود.",
      ar: "إنها الملخص بنظرة واحدة: آخر درجاتك، سلسلتك الحالية، الاتجاه الأخير، وروابط سريعة للصفحات الأعمق (الخطة الأسبوعية، التحليل، المدرب) - كل شيء عليها يعود لنفس التنبؤ والتاريخ الحقيقيين اللذين يستخدمهما باقي التطبيق، لا شيء يُلخَّص مرتين بأرقام مختلفة.",
      zh: "这是一目了然的总览：你最新的分数、当前连续记录、最近趋势，以及通向更深页面（每周计划、分析、教练）的快捷链接——上面的一切都能追溯到应用其他部分所用的同一个真实预测和历史数据，没有任何东西会用不同的数字被总结两遍。",
    },

    
    // ================= M. Games =================
    {
      key: 'app_games_what_are_they',
      match: /\b(what are the games|what are these mini games|games after checkin explained)(?:s|es|ing)?\b|بازی‌ها چیستند|این بازی‌های کوچک چیستند|ما هي الألعاب|ما هذه الألعاب الصغيرة|这些游戏是什么|打卡后的小游戏/i,
      en: "Small interactions built entirely from your own real data - guess your score before it's revealed, pick which of two real SHAP factors mattered more, that kind of thing. Never a quiz for its own sake, always something that teaches how the score actually works, and every one of them is dismissible with no page ever blocked by one.",
      fa: "تعامل‌های کوچکی که کاملاً از داده‌ی واقعیِ خودت ساخته شده‌اند - امتیازت را پیش از فاش‌شدن حدس بزن، بین دو عاملِ واقعیِ SHAP کدام‌یک بیشتر اثر گذاشته را انتخاب کن، از این دست. هرگز آزمونی برای خودِ آزمون‌بودن نیست، همیشه چیزی است که یاد می‌دهد امتیاز واقعاً چطور کار می‌کند، و هرکدامشان قابلِ‌بستن است بدون اینکه هیچ صفحه‌ای با آن قفل شود.",
      ar: "تفاعلات صغيرة مبنية كليًا من بياناتك الحقيقية أنت - خمّن درجتك قبل كشفها، اختر أيّ عاملَي SHAP حقيقيَّين كان أهم، وما شابه. أبدًا اختبار لذات الاختبار، دائمًا شيء يعلّم كيف تعمل الدرجة فعلًا، وكل واحدة قابلة للإغلاق بلا أي صفحة محظورة بها.",
      zh: "完全用你自己的真实数据构建的小互动——在分数揭晓前猜一猜、在两个真实的 SHAP 因素中选出哪个影响更大，诸如此类。从来不是为了考试而考试，而是总能教会你分数实际是怎么运作的，而且每一个都可以关闭，不会有任何页面被它卡住。",
    },

    {
      key: 'app_games_order_before_after_result',
      match: /\b(why do some games come before the result|games order before and after result|guess the score game order)(?:s|es|ing)?\b|چرا بعضی بازی‌ها قبل از نتیجه هستند|ترتیب بازی‌ها قبل و بعد نتیجه|لماذا بعض الألعاب قبل النتيجة|ترتيب الألعاب قبل وبعد النتيجة|为什么有些游戏在结果之前|游戏在结果前后的顺序/i,
      en: "Games are split into two groups on purpose. Ones that reveal a number you haven't seen yet (guess the score, guess the confidence) run BEFORE the result, so guessing means something. Ones that assume you've already seen your result (comparing SHAP factors, marking an exception day) run further down the result page itself - never mixed together.",
      fa: "بازی‌ها عمداً به دو گروه تقسیم شده‌اند. آن‌هایی که عددی را که هنوز ندیده‌ای فاش می‌کنند (حدسِ امتیاز، حدسِ اطمینان) پیش از نتیجه اجرا می‌شوند، پس حدس‌زدن معنایی دارد. آن‌هایی که فرض می‌کنند نتیجه‌ات را از قبل دیده‌ای (مقایسه‌ی عاملهای SHAP، علامت‌زدنِ روزِ استثنا) پایین‌ترِ خودِ صفحه‌ی نتیجه اجرا می‌شوند - هرگز باهم قاطی نمی‌شوند.",
      ar: "الألعاب مقسّمة إلى مجموعتين عمدًا. تلك التي تكشف رقمًا لم تره بعد (خمّن الدرجة، خمّن الثقة) تعمل قبل النتيجة، فالتخمين يعني شيئًا. تلك التي تفترض أنك رأيت نتيجتك بالفعل (مقارنة عوامل SHAP، وضع علامة يوم استثناء) تعمل أسفل صفحة النتيجة نفسها - لا تُخلط أبدًا.",
      zh: "游戏被特意分成两组。那些会揭示你还没看到的数字的游戏（猜分数、猜置信度）会在结果之前运行，这样猜测才有意义。那些假设你已经看过结果的游戏（比较 SHAP 因素、标记例外日）会在结果页面靠下的位置运行——两者绝不会混在一起。",
    },

    {
      key: 'app_games_can_i_skip',
      match: /\b(can i skip the games|how do i dismiss a game|skip this game|can i skip all the games)(?:s|es|ing)?\b|میتوانم بازی‌ها را رد کنم|چطور یک بازی را ببندم|هل يمكنني تخطي اللعبة|كيف أغلق لعبة|هل يمكنني تخطي كل الألعاب|能跳过游戏吗|怎么关闭一个游戏|能跳过所有游戏吗/i,
      en: "Every game card has a dismiss control and there's always a way through to your result regardless - nothing here can lock the page. If you'd rather never see them, turn the whole feature off in Settings instead of dismissing one at a time.",
      fa: "هر کارتِ بازی یک کنترلِ بستن دارد و همیشه یک راه تا نتیجه‌ات هست صرف‌نظر از هرچیز - هیچ‌چیز اینجا نمی‌تواند صفحه را قفل کند. اگر ترجیح می‌دهی هرگز نبینیشان، کلِ ویژگی را در تنظیمات خاموش کن به‌جای بستنِ یکی‌یکی.",
      ar: "كل بطاقة لعبة لها عنصر تحكم للإغلاق ودائمًا هناك طريق إلى نتيجتك بغض النظر - لا شيء هنا يمكنه قفل الصفحة. إن كنت تفضل عدم رؤيتها إطلاقًا، أوقف الميزة كلها من الإعدادات بدل إغلاق واحدة تلو الأخرى.",
      zh: "每张游戏卡片都有关闭按钮，无论如何都总有办法直达你的结果——这里没有任何东西能锁住页面。如果你宁愿永远不看到它们，去设置里把整个功能关掉，而不是一个一个地关闭。",
    },

    
    // ================= N. Future letter =================
    {
      key: 'app_future_letter_what_is_it',
      match: /\b(what is the future letter|letter from my future self|future letter explained)(?:s|es|ing)?\b|نامه آینده چیست|نامه از خود آینده‌ام|ما هي رسالة المستقبل|رسالة من نفسي المستقبلية|未来信是什么|来自未来自己的信/i,
      en: "A letter written by your future self, assembled from your own real numbers - your score range, direction, best day, the one field that moved most, how many days you've logged. It comes in two genuinely different versions, encouraging and honest, and a sentence with no real number behind it is dropped rather than padded with something vague.",
      fa: "نامه‌ای نوشته‌شده از سوی خودِ آینده‌ات، از روی اعدادِ واقعیِ خودت جمع‌شده - بازه‌ی امتیازت، جهت، بهترین روزت، آن یک فیلدی که بیشتر جابه‌جا شده، چند روز ثبت کرده‌ای. در دو نسخه‌ی واقعاً متفاوت می‌آید، دلگرم‌کننده و صادقانه، و جمله‌ای که هیچ عددِ واقعی‌ای پشتش نباشد، به‌جای پرشدن با چیزی مبهم، حذف می‌شود.",
      ar: "رسالة كتبها نفسك المستقبلي، مجمَّعة من أرقامك الحقيقية أنت - نطاق درجتك، اتجاهها، أفضل يوم لك، الحقل الواحد الذي تحرّك أكثر، كم يومًا سجّلت. تأتي في نسختين مختلفتين فعلًا، مشجّعة وصادقة، وجملة بلا رقم حقيقي خلفها تُحذف بدل حشوها بشيء غامض.",
      zh: "一封由未来的你写的信，用你自己真实的数字拼接而成——你的分数区间、方向、最好的一天、变化最大的那个字段、你记录了多少天。它有两个真正不同的版本，鼓励型和坦诚型，一句话如果背后没有真实数字支撑，会被删掉，而不是用模糊的话填充。",
    },

    {
      key: 'app_future_letter_locked',
      match: /\b(future letter is locked|why cant i read my future letter yet|need seven days for future letter)(?:s|es|ing)?\b|نامه آینده قفل است|چرا هنوز نمیتوانم نامه را بخوانم|رسالة المستقبل مقفلة|لماذا لا يمكنني قراءة رسالتي بعد|未来信被锁定|为什么还不能看未来信/i,
      en: "It needs at least seven logged days before it can arrive - the most sensitive text in the app is read by someone who already knows their own pattern, and seven real days is the floor for that to mean anything. Log a few more days and it unlocks on its own.",
      fa: "پیش از اینکه بتواند برسد به دستِ‌کم هفت روزِ ثبت‌شده نیاز دارد - حساس‌ترین متنِ این اپ توسط کسی خوانده می‌شود که از قبل الگوی خودش را می‌داند، و هفت روزِ واقعی حداقلی است که این معنا داشته باشد. چند روزِ دیگر ثبت کن و خودش باز می‌شود.",
      ar: "تحتاج سبعة أيام مسجَّلة على الأقل قبل أن تصل - أكثر نص حساس في التطبيق يقرأه شخص يعرف نمطه بالفعل، وسبعة أيام حقيقية هي الحد الأدنى كي يعني ذلك شيئًا. سجّل أيامًا أخرى وستُفتح من تلقاء نفسها.",
      zh: "它需要至少七天的记录才能到来——应用里最敏感的一段文字，是给一个已经了解自己模式的人看的，而七个真实的天数是让这有意义的最低门槛。再记录几天，它就会自动解锁。",
    },

    
    // ================= O. Troubleshooting / errors =================
    {
      key: 'app_error_server_did_not_answer',
      match: /\b(server did not answer|request timed out|server not responding|timeout error message)(?:s|es|ing)?\b|سرور پاسخ نداد|درخواست زمانش تمام شد|سرور پاسخگو نیست|الخادم لم يجب|انتهت مهلة الطلب|الخادم لا يستجيب|服务器没有响应|请求超时|服务器无响应/i,
      en: "That message means a request genuinely waited the full timeout window with no answer - it's the app being honest about a request that never came back rather than leaving you staring at a spinner forever. If another copy of the app (another tab) is running, close it first; otherwise it's usually a connectivity issue on your end or the server being briefly overloaded.",
      fa: "آن پیام یعنی یک درخواست واقعاً تا انتهای پنجره‌ی زمانی منتظر ماند بدون جواب - این صداقتِ اپ درباره‌ی درخواستی است که هرگز برنگشت، به‌جای اینکه تا ابد به یک چرخِ در حالِ‌چرخش خیره بمانی. اگر یک نسخه‌ی دیگر از اپ (یک تبِ دیگر) در حال اجراست، اول آن را ببند؛ در غیر این صورت معمولاً یک مسئله‌ی اتصال از طرف توست یا سرور به‌طور کوتاه شلوغ است.",
      ar: "تلك الرسالة تعني أن طلبًا انتظر فعلًا نافذة المهلة الكاملة بلا إجابة - إنه صدق التطبيق حول طلب لم يعد أبدًا بدل تركك تحدّق بمؤشر تحميل للأبد. إن كانت نسخة أخرى من التطبيق (تبويب آخر) تعمل، أغلقها أولًا؛ وإلا فعادة ما تكون مشكلة اتصال من جهتك أو الخادم مثقل مؤقتًا.",
      zh: "那条消息意味着一个请求真的等满了整个超时时间窗口却没有收到回应——这是应用在诚实地告诉你一个永远没回来的请求，而不是让你永远盯着一个转圈的加载动画。如果另一个应用副本（另一个标签页）正在运行，先关掉它；否则通常是你这边的网络问题，或服务器暂时过载。",
    },

    {
      key: 'app_error_blank_page',
      match: /\b(blank page|page is blank|white screen|app shows nothing)(?:s|es|ing)?\b|صفحه خالی است|صفحه سفید|برنامه چیزی نشان نمیدهد|صفحة فارغة|شاشة بيضاء|التطبيق لا يعرض شيئا|白屏|页面是空白的|应用什么都不显示/i,
      en: "A hard refresh (bypassing the browser cache) fixes most blank-page cases, since it's usually a stale cached script from before an update. If that doesn't help, check the browser's own console for a network error - the app is served from one process, so if that process isn't reachable at all, nothing on any page will load.",
      fa: "یک رفرشِ سخت (دورزدنِ کشِ مرورگر) بیشترِ حالت‌های صفحه‌ی سفید را درست می‌کند، چون معمولاً یک اسکریپتِ کش‌شده‌ی کهنه از پیش از یک به‌روزرسانی است. اگر کمک نکرد، کنسولِ خودِ مرورگر را برای یک خطای شبکه چک کن - اپ از یک پروسه سرو می‌شود، پس اگر آن پروسه اصلاً قابل‌دسترسی نباشد، هیچ‌چیز در هیچ صفحه‌ای لود نمی‌شود.",
      ar: "التحديث الصارم (تجاوز ذاكرة تخزين المتصفح المؤقتة) يحل معظم حالات الصفحة الفارغة، لأنه عادة سكربت مخبّأ قديم من قبل تحديث. إن لم يساعد ذلك، تحقق من وحدة تحكم المتصفح نفسها بحثًا عن خطأ شبكة - التطبيق يُخدَّم من عملية واحدة، فإن لم تكن تلك العملية قابلة للوصول إطلاقًا، لن يُحمَّل شيء في أي صفحة.",
      zh: "强制刷新（绕过浏览器缓存）能解决大多数空白页面的问题，因为这通常是更新之前的旧缓存脚本导致的。如果没用，检查浏览器自己的控制台看有没有网络错误——这个应用由一个进程提供服务，所以如果那个进程完全无法访问，任何页面上任何东西都加载不出来。",
    },

    {
      key: 'app_error_double_submit',
      match: /\b(double submit|clicked submit twice|does it submit twice if i click again)(?:s|es|ing)?\b|ارسال دوباره|دو بار روی ارسال کلیک کردم|إرسال مضاعف|ضغطت إرسال مرتين|重复提交|点了两次提交/i,
      en: "Submit buttons are guarded against this - a second click while the first request is still in flight is ignored rather than firing a duplicate submission, so double-clicking (or an impatient re-click on a slow connection) shouldn't create two entries or two overlapping processing screens.",
      fa: "دکمه‌های ارسال در برابر این محافظت شده‌اند - کلیکِ دوم درحالی‌که درخواستِ اول هنوز در حالِ پرواز است نادیده گرفته می‌شود به‌جای اینکه یک ارسالِ تکراری راه بیندازد، پس دوبارکلیک‌کردن (یا یک کلیکِ بی‌صبرانه‌ی دیگر روی یک اتصالِ کند) نباید دو ورودی یا دو صفحه‌ی پردازشِ هم‌پوشان بسازد.",
      ar: "أزرار الإرسال محمية ضد هذا - نقرة ثانية بينما الطلب الأول لا يزال في الطريق تُتجاهل بدل إطلاق إرسال مكرر، فالنقر المزدوج (أو نقرة أخرى غير صبورة على اتصال بطيء) لا ينبغي أن يُنشئ إدخالين أو شاشتَي معالجة متداخلتين.",
      zh: "提交按钮对此有防护——在第一个请求仍在进行时的第二次点击会被忽略，而不会触发重复提交，所以双击（或者在慢速连接上不耐烦地再点一次）不应该产生两条记录或两个重叠的处理界面。",
    },

    {
      key: 'app_error_wrong_language_shown',
      match: /\b(wrong language shown|some text stayed in english|language didnt update everywhere|part of the page is still english)(?:s|es|ing)?\b|زبان اشتباه نشان داده میشود|بخشی از متن انگلیسی ماند|اللغة الخاطئة معروضة|جزء من النص بقي بالإنجليزية|显示的语言不对|有些文字还是英文/i,
      en: "Most of the app updates instantly on a language switch, but some content built once from a fetched result (recommendation cards, the weekly plan body, some analytics cards) used to only update its own static labels and not the content itself if you'd already loaded the page before switching. That's been fixed to re-render fully on a language change - if you're still seeing English somewhere after switching, a reload will force it either way.",
      fa: "بیشترِ اپ بی‌درنگ روی سوییچِ زبان به‌روز می‌شود، اما برخی محتوا که یک‌بار از یک نتیجه‌ی گرفته‌شده ساخته می‌شود (کارت‌های توصیه، بدنه‌ی برنامه‌ی هفتگی، برخی کارت‌های تحلیل) قبلاً فقط برچسب‌های ثابتِ خودش را به‌روز می‌کرد و نه خودِ محتوا را، اگر پیش از سوییچ‌کردن صفحه را از قبل بارگذاری کرده بودی. این اصلاح شده تا کاملاً روی تغییرِ زبان دوباره رندر شود - اگر هنوز جایی انگلیسی می‌بینی، یک رفرش در هر صورت مجبورش می‌کند.",
      ar: "معظم التطبيق يُحدَّث فورًا عند تبديل اللغة، لكن بعض المحتوى المبني مرة واحدة من نتيجة مسترجعة (بطاقات التوصيات، متن الخطة الأسبوعية، بعض بطاقات التحليل) كان يُحدّث فقط تسمياته الثابتة لا المحتوى نفسه إن كنت قد حمّلت الصفحة بالفعل قبل التبديل. أُصلح هذا ليُعاد رسمه كليًا عند تغيير اللغة - إن كنت لا تزال ترى إنجليزية في مكان ما بعد التبديل، إعادة التحميل ستفرضها على أي حال.",
      zh: "大部分应用会在语言切换时立即更新，但有些一次性从获取的结果构建的内容（推荐卡片、每周计划正文、部分分析卡片）以前只会更新自己的静态标签，而不是内容本身——如果你在切换语言之前已经加载过页面的话。这个问题已经修复，语言变化时会完全重新渲染——如果切换后某处仍然显示英文，刷新一下无论如何都会强制更新。",
    },

    {
      key: 'app_error_lost_my_data',
      match: /\b(lost my data|my history disappeared|my checkins are gone|cant find my old data)(?:s|es|ing)?\b|داده‌هایم گم شد|تاریخچه‌ام ناپدید شد|چکین‌های من رفتند|فقدت بياناتي|اختفى سجلي|تسجيلاتي اختفت|我的数据丢了|历史记录消失了|打卡记录不见了/i,
      en: "Check the account you're logged into first - a demo session, a second registration, or a browser profile switch all put you on a genuinely different account with its own separate history, which looks identical to 'lost data' but isn't. Real check-ins tied to an account persist on the server; they don't disappear from a browser refresh or a new device.",
      fa: "اول اکانتی که واردش هستی را چک کن - یک نشستِ دمو، یک ثبت‌نام دوم، یا سوییچِ پروفایلِ مرورگر همه تو را روی یک اکانتِ واقعاً متفاوت با تاریخچه‌ی جداگانه‌ی خودش می‌گذارند، که دقیقاً شبیه «از دست‌دادنِ داده» به‌نظر می‌رسد اما نیست. بررسی‌های واقعیِ گره‌خورده به یک اکانت روی سرور می‌مانند؛ با رفرشِ مرورگر یا یک دستگاهِ جدید ناپدید نمی‌شوند.",
      ar: "تحقق أولًا من الحساب الذي دخلت إليه - جلسة تجريبية، تسجيل ثانٍ، أو تبديل ملف تعريف متصفح، كلها تضعك على حساب مختلف فعلًا بتاريخ منفصل خاص به، يبدو تمامًا كـ'فقدان بيانات' لكنه ليس كذلك. الفحوصات الحقيقية المرتبطة بحساب تستمر على الخادم؛ لا تختفي من إعادة تحميل متصفح أو جهاز جديد.",
      zh: "先检查一下你登录的是哪个账户——演示会话、第二次注册，或者浏览器配置文件切换，都会把你带到一个真正不同的、有自己独立历史的账户，这看起来和「数据丢失」一模一样，但其实不是。绑定在账户上的真实检测记录保存在服务器上；它们不会因为浏览器刷新或换设备而消失。",
    },

    
    // ================= P. Privacy / data =================
    {
      key: 'app_privacy_where_stored',
      match: /\b(where is my data stored|is my data sold|does this app sell my data|is my health data shared with third parties)(?:s|es|ing)?\b|داده‌های من کجا ذخیره میشوند|آیا داده‌های من فروخته میشود|أين تُخزن بياناتي|هل تُباع بياناتي|我的数据存在哪里|我的数据会被卖掉吗/i,
      en: "Your check-ins, account and League data are stored server-side, tied to your account. Nothing about your health data is sent to a third party by default - the only path anything takes off this server at all is the optional connector, and that's off unless you turn it on yourself.",
      fa: "بررسی‌ها، حساب و داده‌ی لیگ‌ات سمتِ سرور ذخیره می‌شوند، گره‌خورده به حسابت. به‌طور پیش‌فرض هیچ‌چیزی از داده‌ی سلامتت به شخصِ ثالث فرستاده نمی‌شود - تنها مسیری که چیزی اصلاً از این سرور بیرون می‌رود کانکتورِ اختیاری است، و آن هم خاموش است مگر خودت روشنش کنی.",
      ar: "فحوصاتك وحسابك وبيانات دوريك تُخزَّن على الخادم، مرتبطة بحسابك. لا شيء من بيانات صحتك يُرسَل إلى طرف ثالث افتراضيًا - المسار الوحيد الذي يغادر فيه أي شيء هذا الخادم إطلاقًا هو الرابط الاختياري، وهو معطّل ما لم تفعّله بنفسك.",
      zh: "你的检测记录、账户和联赛数据都存储在服务器端，与你的账户绑定。默认情况下，你的健康数据不会发送给任何第三方——唯一让任何东西离开这台服务器的途径是那个可选的连接器，而它默认关闭，除非你自己打开它。",
    },

    {
      key: 'app_privacy_export_data',
      match: /\b(export all my data|download everything|full data export|bulk export of my history)(?:s|es|ing)?\b|خروجی گرفتن از تمام داده‌هایم|دانلود همه چیز|تصدير كل بياناتي|تحميل كل شيء|导出我所有的数据|下载全部数据/i,
      en: "Your profile page has a full data export: one file containing everything the app holds about you, available as JSON or as a spreadsheet CSV in your chosen language. Separately, the result page can export a single check-in as a one-row CSV, which is the format the bulk importer reads back.",
      fa: "صفحه‌ی پروفایلت یک خروجی کامل داده دارد: یک فایل شامل هر چیزی که اپ درباره‌ی تو نگه می‌دارد، به‌صورت JSON یا به‌صورت CSVِ صفحه‌گسترده به زبان انتخابی‌ات. جدا از آن، صفحه‌ی نتیجه می‌تواند یک چک‌این را به‌صورت CSV تک‌ردیفی خروجی بدهد، که همان فرمتی است که وارد‌کننده‌ی انبوه دوباره می‌خواند.",
      ar: "في صفحة ملفك الشخصي تصدير كامل للبيانات: ملف واحد يحوي كل ما يحتفظ به التطبيق عنك، متاح بصيغة JSON أو كجدول بيانات سي إس في بلغتك المختارة. وبشكل منفصل، تستطيع صفحة النتيجة تصدير تسجيل واحد كملف سي إس في من صف واحد، وهو التنسيق الذي يقرأه المستورد الجماعي.",
      zh: "你的个人资料页提供完整的数据导出：一个包含应用所保存的关于你的全部内容的文件，可选 JSON 格式，或按你所选语言导出的 CSV 表格。另外，结果页可以把单次打卡导出为单行 CSV，这正是批量导入器能读回的格式。",
    },

    {
      key: 'app_privacy_crisis_guard',
      match: /\b(crisis guard|what happens if i mention self harm|crisis line information|if i say something concerning to the coach)(?:s|es|ing)?\b|محافظ بحران|اگر چیزی نگران‌کننده به مربی بگویم|حارس الأزمة|ماذا يحدث إذا ذكرت إيذاء النفس|危机防护|如果我提到自残会怎样/i,
      en: "If a message to the coach reads as describing real crisis-level distress, the app steps outside its normal rule-based/data-driven answers and responds with grounding language plus real crisis-line information for your region, rather than trying to route it to a topic like everything else - that guard is checked before any normal topic-matching happens, not after.",
      fa: "اگر یک پیام به مربی طوری خوانده شود که واقعاً درباره‌ی پریشانیِ سطحِ بحران باشد، اپ از جواب‌های معمولِ قانون‌محور/داده‌محورش بیرون می‌رود و با زبانِ آرام‌کننده به‌علاوه اطلاعاتِ واقعیِ خطِ بحران برای منطقه‌ات پاسخ می‌دهد، به‌جای اینکه مثل هرچیز دیگر بخواهد به یک موضوع مسیریابی‌اش کند - آن محافظ پیش از اینکه هرگونه تطبیقِ موضوعِ معمولی اتفاق بیفتد چک می‌شود، نه بعدش.",
      ar: "إن قُرئت رسالة إلى المدرب على أنها تصف ضائقة حقيقية بمستوى أزمة، يخرج التطبيق عن إجاباته المعتادة القائمة على القواعد/البيانات ويستجيب بلغة تهدئة إضافة إلى معلومات خط أزمات حقيقية لمنطقتك، بدل محاولة توجيهها إلى موضوع كأي شيء آخر - يُفحص ذلك الحارس قبل حدوث أي مطابقة موضوع عادية، لا بعدها.",
      zh: "如果一条给教练的消息读起来像是在描述真实的危机级别的痛苦，应用会跳出它平常那种基于规则/数据驱动的回答，改用安抚性的语言加上你所在地区真实的危机热线信息来回应，而不是像其他消息一样试图把它路由到某个主题——这个防护会在任何正常的主题匹配发生之前检查，而不是之后。",
    },

    
    // ====== Q. What each questionnaire field actually means ======
    {
      key: 'app_field_fragmentation',
      match: /\b(what is fragmentation|fragmentation index|what does fragmentation mean|fragmentation score explained)(?:s|es|ing)?\b|شاخص پراکندگی چیست|پراکندگی یعنی چه|ما هو مؤشر التجزئة|ماذا يعني التجزؤ|碎片化指数是什么|碎片化是什么意思/i,
      en: "Fragmentation (0-100) is auto-calculated from your pickups and session count: how broken-up your usage was. Two hours in one sitting and two hours in forty scattered pickups are very different days for focus, and this is the field that tells the model which one you had. You never type it - it comes from the numbers you did enter.",
      fa: "پراکندگی (۰ تا ۱۰۰) به‌صورت خودکار از تعداد برداشتن گوشی و تعداد جلسه‌هایت محاسبه می‌شود: یعنی استفاده‌ات چقدر تکه‌تکه بوده. دو ساعت یکجا با دو ساعتِ پخش‌شده در چهل بار برداشتن گوشی، برای تمرکز دو روز کاملاً متفاوت‌اند و همین فیلد است که به مدل می‌گوید کدامش را داشته‌ای. هیچ‌وقت خودت واردش نمی‌کنی - از عددهایی که وارد کرده‌ای درمی‌آید.",
      ar: "التجزئة (0-100) تُحسب تلقائيا من عدد مرات التقاط الهاتف وعدد الجلسات: أي مدى تقطّع استخدامك. ساعتان متواصلتان وساعتان موزعتان على أربعين التقاطة يومان مختلفان تماما بالنسبة للتركيز، وهذا الحقل هو ما يخبر النموذج أيهما كان يومك. لا تُدخله بنفسك أبدا - يُشتق مما أدخلته فعلا.",
      zh: "碎片化（0-100）由你的手机拿起次数和使用时段数自动计算：也就是你的使用被打断得有多厉害。连续两小时和分散在四十次拿起中的两小时，对专注力来说是完全不同的两天，这个字段就是告诉模型你属于哪一种。你从不需要手动填写——它由你已填的数字推导而来。",
    },

    {
      key: 'app_field_notification_density',
      match: /\b(what is notification density|notification density meaning|notifications per hour field)(?:s|es|ing)?\b|چگالی اعلان چیست|تراکم اعلان یعنی چه|ما هي كثافة الإشعارات|كثافة الإشعارات تعني ماذا|通知密度是什么|通知密度什么意思/i,
      en: "Notification density is auto-calculated as notifications per hour of screen time, not a raw daily count. That distinction matters: 200 notifications across ten hours is a very different day from 200 across two, and only the per-hour form tells the model how often you were being interrupted while actually using the phone.",
      fa: "چگالی اعلان به‌صورت خودکار به شکل «تعداد اعلان به ازای هر ساعت زمان صفحه» محاسبه می‌شود، نه شمارش خام روزانه. این تفاوت مهم است: ۲۰۰ اعلان در ده ساعت با ۲۰۰ اعلان در دو ساعت دو روز کاملاً متفاوت‌اند و فقط شکل «در ساعت» به مدل می‌گوید هر چند وقت یک‌بار موقع استفاده‌ی واقعی از گوشی حواست پرت شده.",
      ar: "كثافة الإشعارات تُحسب تلقائيا كعدد إشعارات لكل ساعة من وقت الشاشة، لا كعدّ يومي خام. هذا الفارق مهم: 200 إشعار على مدى عشر ساعات يوم مختلف تماما عن 200 إشعار في ساعتين، وصيغة «لكل ساعة» وحدها هي التي تخبر النموذج كم مرة قوطعت أثناء استخدامك الفعلي للهاتف.",
      zh: "通知密度按「每小时屏幕时间的通知数」自动计算，而不是一天的原始总数。这个区别很重要：十小时内 200 条通知和两小时内 200 条完全是两种日子，只有按小时的形式才能告诉模型你在实际使用手机时被打断的频率。",
    },

    {
      key: 'app_field_pickups',
      match: /\b(what are pickups|pickups per day field|what does pickups mean|phone pickups explained)(?:s|es|ing)?\b|برداشتن گوشی یعنی چه|تعداد برداشتن گوشی چیست|ما معنى التقاط الهاتف|عدد مرات التقاط الهاتف|拿起手机次数是什么|手机拿起次数什么意思/i,
      en: "A pickup is one time you woke the phone and looked at it, however briefly - most phones report this directly in their own screen-time summary. It's tracked separately from total minutes because the count, not the duration, is what predicts fragmented attention: fifty two-minute pickups and one hundred-minute session are the same total and very different days.",
      fa: "هر «برداشتن گوشی» یعنی یک بار که گوشی را روشن کردی و نگاهش کردی، هرچقدر هم کوتاه - بیشتر گوشی‌ها این عدد را مستقیم در گزارش زمان صفحه‌ی خودشان نشان می‌دهند. جدا از مجموع دقیقه‌ها ثبت می‌شود چون این تعداد است که حواس‌پرتی را پیش‌بینی می‌کند، نه مدت: پنجاه بار برداشتنِ دو دقیقه‌ای با یک جلسه‌ی صد دقیقه‌ای مجموعشان یکی است ولی دو روز کاملاً متفاوت‌اند.",
      ar: "الالتقاط هو كل مرة توقظ فيها الهاتف وتنظر إليه مهما قصرت - معظم الهواتف تعرض هذا الرقم مباشرة في ملخص وقت الشاشة الخاص بها. يُسجَّل منفصلا عن مجموع الدقائق لأن العدد، لا المدة، هو ما يتنبأ بتشتت الانتباه: خمسون التقاطة من دقيقتين وجلسة واحدة من مئة دقيقة لهما المجموع نفسه لكنهما يومان مختلفان تماما.",
      zh: "「拿起」指你唤醒手机看一眼的每一次，无论多短——大多数手机的屏幕使用时间报告里会直接给出这个数字。它和总分钟数分开记录，因为预测注意力碎片化的是次数而不是时长：五十次两分钟的拿起和一次一百分钟的使用总量相同，却是完全不同的两天。",
    },

    {
      key: 'app_field_night_ratio',
      match: /\b(what is night ratio|share of use at night|late night screen time field|night screen minutes)(?:s|es|ing)?\b|نسبت شب چیست|سهم استفاده در شب|زمان صفحه آخر شب|ما هي نسبة الليل|حصة الاستخدام ليلا|وقت الشاشة في وقت متأخر|夜间比例是什么|夜间使用占比|深夜屏幕时间/i,
      en: "Night ratio is the auto-calculated share of your total screen time that happened at night - you enter the late-night minutes, the app turns it into a proportion. It's kept as a ratio rather than raw minutes because 90 night minutes out of 120 total is a fundamentally different pattern from 90 out of 600, and the model needs to see which one you are.",
      fa: "نسبت شب، سهمِ خودکارِ محاسبه‌شده از کل زمان صفحه‌ات است که شب اتفاق افتاده - تو دقیقه‌های آخر شب را وارد می‌کنی و اپ آن را به نسبت تبدیل می‌کند. به‌جای دقیقه‌ی خام، نسبت نگه داشته می‌شود چون ۹۰ دقیقه‌ی شبانه از مجموع ۱۲۰ دقیقه، الگویی بنیادی متفاوت از ۹۰ دقیقه از ۶۰۰ است و مدل باید ببیند تو کدامی.",
      ar: "نسبة الليل هي الحصة المحسوبة تلقائيا من إجمالي وقت شاشتك التي وقعت ليلا - أنت تُدخل دقائق وقت متأخر، والتطبيق يحولها إلى نسبة. تُحفظ كنسبة لا كدقائق خام لأن 90 دقيقة ليلية من أصل 120 نمط مختلف جوهريا عن 90 من أصل 600، والنموذج يحتاج أن يرى أيهما أنت.",
      zh: "夜间比例是系统自动算出的、你的总屏幕时间中发生在夜间的那部分占比——你填入深夜的分钟数，应用把它换算成比例。之所以保存为比例而不是原始分钟数，是因为总共 120 分钟里有 90 分钟在夜间，和总共 600 分钟里有 90 分钟，是根本不同的模式，模型需要看出你属于哪一种。",
    },

    {
      key: 'app_field_pre_sleep_screen',
      match: /\b(screen time before sleep|pre sleep screen field|what counts as before sleep)(?:s|es|ing)?\b|زمان صفحه قبل از خواب|چه چیزی قبل از خواب حساب میشود|وقت الشاشة قبل النوم|ما الذي يُحتسب قبل النوم|睡前屏幕时间|什么算睡前使用/i,
      en: "This is the screen time in the stretch right before you actually fell asleep, not just 'evening' generally. It's a separate field from late-night use because they answer different questions: night use is about when in the 24 hours, pre-sleep use is about what happened in the specific window that affects falling asleep. The app also turns it into a pre-sleep ratio automatically.",
      fa: "این زمان صفحه در همان بازه‌ی درست پیش از به‌خواب‌رفتن واقعی توست، نه صرفاً «عصر» به‌طور کلی. فیلدی جدا از استفاده‌ی آخر شب است چون به سؤال‌های متفاوتی جواب می‌دهند: استفاده‌ی شبانه درباره‌ی «کِی در ۲۴ ساعت» است و استفاده‌ی پیش از خواب درباره‌ی «چه چیزی در همان پنجره‌ای که روی به‌خواب‌رفتن اثر می‌گذارد». اپ خودش این را به نسبت پیش از خواب هم تبدیل می‌کند.",
      ar: "هذا هو وقت الشاشة في الفترة التي تسبق نومك الفعلي مباشرة، لا «المساء» عموما. وهو حقل منفصل عن الاستخدام الليلي المتأخر لأنهما يجيبان عن سؤالين مختلفين: الاستخدام الليلي يخص «متى ضمن الأربع والعشرين ساعة»، أما ما قبل النوم فيخص «ما حدث في النافذة التي تؤثر تحديدا على الخلود إلى النوم». والتطبيق يحوّله تلقائيا أيضا إلى نسبة ما قبل النوم.",
      zh: "这指的是你真正入睡前那段时间的屏幕使用，而不是笼统的「晚上」。它和深夜使用是两个独立字段，因为它们回答不同的问题：夜间使用关心的是「在一天 24 小时中的什么时候」，睡前使用关心的是「在直接影响入睡的那个时间窗里发生了什么」。应用还会自动把它换算成睡前比例。",
    },

    {
      key: 'app_field_screen_baseline',
      match: /\b(what is my baseline|screen baseline|ewma baseline|typical screen time baseline)(?:s|es|ing)?\b|خط پایه من چیست|خط پایه زمان صفحه|ما هو خط الأساس|خط أساس وقت الشاشة|我的基线是什么|屏幕时间基线/i,
      en: "Your baseline is your own typical recent daily screen time, carried forward as a rolling average - it's what 'a lot for you' is measured against, so the same 300 minutes reads differently for someone who usually does 200 and someone who usually does 400. On your very first check-in there's no history to average, so it's filled from that entry itself, then it starts tracking you properly.",
      fa: "خط پایه‌ات همان زمان صفحه‌ی معمول اخیر خودت است که به شکل میانگین متحرک حمل می‌شود - معیاری که «زیاد برای تو» با آن سنجیده می‌شود؛ برای همین همان ۳۰۰ دقیقه برای کسی که معمولاً ۲۰۰ دارد با کسی که معمولاً ۴۰۰ دارد معنای متفاوتی می‌دهد. در همان اولین چک‌این، تاریخچه‌ای برای میانگین‌گرفتن وجود ندارد، پس از خودِ همان ثبت پر می‌شود و بعد شروع می‌کند به دنبال‌کردن درستِ تو.",
      ar: "خط أساسك هو وقت شاشتك اليومي المعتاد مؤخرا، محمولا كمتوسط متحرك - وهو ما يُقاس عليه «الكثير بالنسبة لك»، لذا فإن 300 دقيقة نفسها تعني شيئا مختلفا لمن يقضي عادة 200 ولمن يقضي عادة 400. في أول تسجيل لك لا يوجد تاريخ للمتوسط، فيُملأ من ذلك الإدخال نفسه، ثم يبدأ بتتبعك بشكل صحيح.",
      zh: "基线是你自己近期的典型每日屏幕时间，以滚动平均的形式延续下来——它是衡量「对你而言算多」的参照，所以同样是 300 分钟，对平常 200 分钟的人和平常 400 分钟的人意义完全不同。在你的第一次打卡时没有历史可以平均，于是就用那一条记录本身填入，之后才开始真正跟踪你。",
    },

    {
      key: 'app_field_digital_dependence',
      match: /\b(digital dependence score|what is digital dependence|dependence 0 100 field)(?:s|es|ing)?\b|امتیاز وابستگی دیجیتال چیست|وابستگی دیجیتال یعنی چه|درجة الاعتماد الرقمي|ما هو الاعتماد الرقمي|数字依赖分数|数字依赖是什么/i,
      en: "Digital dependence (0-100) is auto-calculated from your recreational, night and morning-check patterns together - it's a composite, not something you rate about yourself. Because it's derived, editing it in an exported CSV does nothing: the importer recomputes it from the raw fields it was built from.",
      fa: "وابستگی دیجیتال (۰ تا ۱۰۰) به‌صورت خودکار از الگوهای تفریحی، شبانه و چک‌کردن صبحگاهی‌ات با هم محاسبه می‌شود - یک شاخص ترکیبی است، نه چیزی که خودت درباره‌ی خودت نمره بدهی. چون مشتق‌شده است، ویرایش‌کردنش در یک فایل CSV صادرشده هیچ اثری ندارد: وارد‌کننده آن را دوباره از همان فیلدهای خامی که از رویشان ساخته شده حساب می‌کند.",
      ar: "الاعتماد الرقمي (0-100) يُحسب تلقائيا من أنماط استخدامك الترفيهي والليلي وفحص الهاتف صباحا مجتمعة - فهو مؤشر مركّب، لا شيء تقيّم به نفسك. ولأنه مشتق، فإن تعديله في ملف سي إس في مُصدَّر لا يفعل شيئا: المستورد يعيد حسابه من الحقول الخام التي بُني منها.",
      zh: "数字依赖（0-100）由你的娱乐使用、夜间使用和晨间查看手机的模式共同自动计算——它是一个复合指标，不是让你自评的项目。正因为它是推导出来的，在导出的 CSV 里手动改它不会有任何效果：导入时会从它所依据的原始字段重新计算。",
    },

    {
      key: 'app_field_social_comparison',
      match: /\b(social comparison field|online comparison 1 10|what is the comparison question)(?:s|es|ing)?\b|فیلد مقایسه اجتماعی|سوال مقایسه آنلاین چیست|حقل المقارنة الاجتماعية|ما هو سؤال المقارنة|社交比较字段|线上比较问题是什么/i,
      en: "Online comparison (1-10) is one of the few genuinely subjective fields: how much you found yourself measuring your life against other people's posts that day. It's asked directly because there's no way to derive it from minutes - two people can spend the same hour on the same app and have completely different experiences of it.",
      fa: "مقایسه‌ی آنلاین (۱ تا ۱۰) یکی از معدود فیلدهای واقعاً ذهنی است: اینکه آن روز چقدر خودت را در حال سنجیدن زندگی‌ات با پست‌های بقیه دیدی. مستقیم پرسیده می‌شود چون هیچ راهی برای استخراجش از دقیقه‌ها نیست - دو نفر می‌توانند همان یک ساعت را در همان اپ بگذرانند و تجربه‌شان کاملاً متفاوت باشد.",
      ar: "المقارنة عبر الإنترنت (1-10) من الحقول الذاتية القليلة فعلا: إلى أي مدى وجدت نفسك ذلك اليوم تقيس حياتك بمنشورات الآخرين. يُسأل عنها مباشرة لأنه لا سبيل لاشتقاقها من الدقائق - شخصان قد يقضيان الساعة نفسها في التطبيق نفسه وتكون تجربتهما مختلفة تماما.",
      zh: "线上比较（1-10）是少数几个真正主观的字段之一：那一天你有多少次发现自己拿别人的动态来衡量自己的生活。之所以直接询问，是因为它无法从分钟数推导出来——两个人可以在同一个应用上花同样一小时，体验却完全不同。",
    },

    {
      key: 'app_field_focus_productivity',
      match: /\b(focus 0 100 field|productivity 0 100 field|difference between focus and productivity)(?:s|es|ing)?\b|فیلد تمرکز صفر تا صد|تفاوت تمرکز و بهره‌وری|حقل التركيز من 0 إلى 100|الفرق بين التركيز والإنتاجية|专注度字段|专注和生产力的区别/i,
      en: "They're deliberately separate: focus is how well you could hold attention, productivity is how much you actually got done. They usually move together, but a day of deep focus on the wrong thing scores high on one and low on the other - and that gap is exactly the kind of pattern the analytics page can surface later.",
      fa: "این دو عمداً جدا هستند: تمرکز یعنی چقدر توانستی حواست را نگه داری، بهره‌وری یعنی واقعاً چقدر کار انجام دادی. معمولاً با هم حرکت می‌کنند، اما یک روزِ تمرکزِ عمیق روی کارِ اشتباه در یکی نمره‌ی بالا و در دیگری نمره‌ی پایین می‌گیرد - و دقیقاً همین فاصله همان الگویی است که صفحه‌ی تحلیل‌ها بعداً می‌تواند نشانت دهد.",
      ar: "هما منفصلان عن قصد: التركيز هو مدى قدرتك على الحفاظ على انتباهك، والإنتاجية هي مقدار ما أنجزته فعلا. عادة يتحركان معا، لكن يوما من التركيز العميق على الشيء الخطأ يسجل مرتفعا في أحدهما ومنخفضا في الآخر - وهذه الفجوة بالذات هي النمط الذي يمكن لصفحة التحليلات أن تُظهره لاحقا.",
      zh: "这两项是刻意分开的：专注度是你能多好地保持注意力，生产力是你实际完成了多少。它们通常同向变动，但一整天深度专注在错误的事情上，会在一项上得高分、另一项上得低分——而这个落差正是分析页面之后能揭示的那类模式。",
    },

    {
      key: 'app_field_activity_minutes',
      match: /\b(physical activity field|activity minutes question|does exercise count here)(?:s|es|ing)?\b|فیلد فعالیت بدنی|دقیقه‌های ورزش را کجا وارد کنم|حقل النشاط البدني|هل تُحتسب الرياضة هنا|身体活动字段|运动算在这里吗/i,
      en: "Physical activity in minutes per day is here because it's one of the strongest non-screen signals in the whole model - it regularly shows up in people's top factors. Count deliberate movement (a walk, a workout, cycling somewhere), not incidental standing around; consistency of how you count matters more than precision.",
      fa: "فعالیت بدنی برحسب دقیقه در روز اینجاست چون یکی از قوی‌ترین سیگنال‌های غیرصفحه‌ای در کل مدل است - مرتب در عامل‌های اصلی افراد ظاهر می‌شود. حرکت عمدی را بشمار (پیاده‌روی، تمرین، دوچرخه‌سواری برای رفتن به جایی)، نه سرپا ایستادن اتفاقی؛ ثابت‌بودنِ روشِ شمردنت از دقتش مهم‌تر است.",
      ar: "النشاط البدني بالدقائق في اليوم موجود هنا لأنه من أقوى الإشارات غير المتعلقة بالشاشة في النموذج كله - يظهر باستمرار ضمن العوامل الرئيسية للناس. احسب الحركة المقصودة (مشي، تمرين، ركوب دراجة للانتقال)، لا الوقوف العارض؛ وثبات طريقة حسابك أهم من دقتها.",
      zh: "每日身体活动分钟数放在这里，是因为它是整个模型中最强的非屏幕信号之一——经常出现在人们的主要影响因素里。计入有意的活动（散步、锻炼、骑车出行），而不是偶然的站立；你计算方式的一致性比精确度更重要。",
    },

    {
      key: 'app_field_category_minutes',
      match: /\b(social gaming video work minutes|category minutes fields|do the categories have to add up|do category minutes need to equal total)(?:s|es|ing)?\b|دقیقه‌های دسته‌بندی|آیا جمع دسته‌ها باید با کل برابر باشد|دقائق الفئات|هل يجب أن يساوي مجموع الفئات الإجمالي|各类别分钟数|分类时间必须等于总时间吗/i,
      en: "The category fields (social, gaming, video, work/study) don't have to sum exactly to your total - anything left over is treated as 'other'. What the model actually uses is the ratio of each category to your total, which is why an honest rough split is more useful than a precise-looking set of numbers you had to invent.",
      fa: "فیلدهای دسته‌بندی (شبکه‌های اجتماعی، بازی، ویدیو، کار/درس) لازم نیست دقیقاً با مجموع کل جمع شوند - هرچه باقی بماند «سایر» در نظر گرفته می‌شود. چیزی که مدل واقعاً استفاده می‌کند نسبت هر دسته به کل توست، و برای همین یک تقسیم‌بندی تقریبی اما صادقانه از یک مجموعه عدد دقیق‌به‌نظر که مجبور شدی از خودت دربیاوری مفیدتر است.",
      ar: "حقول الفئات (التواصل الاجتماعي، الألعاب، الفيديو، العمل/الدراسة) لا يلزم أن يساوي مجموعها إجماليك بالضبط - وما يتبقى يُعامل على أنه «أخرى». ما يستخدمه النموذج فعلا هو نسبة كل فئة إلى إجماليك، ولهذا فإن تقسيما تقريبيا صادقا أنفع من مجموعة أرقام تبدو دقيقة اضطررت إلى اختلاقها.",
      zh: "各类别字段（社交、游戏、视频、工作/学习）不必精确加总到你的总时长——剩余部分会被归为「其他」。模型实际使用的是每个类别占你总时长的比例，所以一个诚实的大致划分，比一组你不得不编造出来的、看起来很精确的数字更有用。",
    },

    {
      key: 'app_field_sleep_quality_vs_hours',
      match: /\b(sleep quality vs sleep hours|why two sleep questions|sleep quality 1 10 field)(?:s|es|ing)?\b|کیفیت خواب در برابر ساعت خواب|چرا دو سوال درباره خواب|جودة النوم مقابل ساعات النوم|لماذا سؤالان عن النوم|睡眠质量和睡眠时长|为什么有两个睡眠问题/i,
      en: "Hours and quality are asked separately because eight bad hours and six good ones are genuinely different days, and the model treats them as different signals. Quality is your own 1-10 judgement of how rested you felt, not a device's sleep score - if you use a tracker, it's fine to translate its number into your own scale, just do it the same way each time.",
      fa: "ساعت و کیفیت جدا پرسیده می‌شوند چون هشت ساعت بد با شش ساعت خوب واقعاً دو روز متفاوت‌اند و مدل هم آن‌ها را دو سیگنال جدا در نظر می‌گیرد. کیفیت، قضاوت خودت از ۱ تا ۱۰ درباره‌ی اینکه چقدر سرحال بیدار شدی است، نه امتیاز خواب یک دستگاه - اگر از ردیاب استفاده می‌کنی، اشکالی ندارد عددش را به مقیاس خودت ترجمه کنی، فقط هر بار به یک شکل این کار را بکن.",
      ar: "تُسأل الساعات والجودة منفصلتين لأن ثماني ساعات سيئة وستّ ساعات جيدة يومان مختلفان فعلا، والنموذج يعاملهما كإشارتين مختلفتين. الجودة هي تقديرك أنت من 1 إلى 10 لمدى شعورك بالراحة، لا درجة نوم يعطيها جهاز - وإن كنت تستخدم متعقبا، فلا بأس أن تترجم رقمه إلى مقياسك الخاص، فقط افعل ذلك بالطريقة نفسها كل مرة.",
      zh: "睡眠时长和质量分开询问，是因为八小时的差觉和六小时的好觉确实是不同的日子，模型也把它们当作不同的信号。质量是你自己 1-10 的主观判断，指你感觉休息得如何，而不是设备给出的睡眠评分——如果你用手环，把它的数字换算成你自己的尺度也没问题，只要每次都用同样的方式换算。",
    },

    {
      key: 'app_field_stress',
      match: /\b(stress 0 10 field|how do i rate my stress|stress question meaning)(?:s|es|ing)?\b|فیلد استرس صفر تا ده|چطور استرسم را نمره بدهم|حقل التوتر من 0 إلى 10|كيف أقيّم توتري|压力字段|怎么给自己的压力打分/i,
      en: "Stress (0-10) is your own read on the day, and like every subjective field here, the value is in rating it consistently rather than accurately in some absolute sense - the model learns from how your own numbers move relative to each other, so a personal scale you apply the same way every day works better than trying to match someone else's idea of a 7.",
      fa: "استرس (۰ تا ۱۰) برداشت خودت از آن روز است و مثل هر فیلد ذهنی دیگری اینجا، ارزشش در این است که به‌طور یکنواخت نمره بدهی، نه اینکه به معنای مطلقی دقیق باشد - مدل از نحوه‌ی حرکت عددهای خودت نسبت به هم یاد می‌گیرد، پس یک مقیاس شخصی که هر روز به یک شکل به کار می‌بری بهتر از تلاش برای تطبیق با تصور کس دیگری از عدد ۷ جواب می‌دهد.",
      ar: "التوتر (0-10) هو قراءتك أنت لليوم، ومثل كل حقل ذاتي هنا، القيمة في تقييمه بثبات لا في دقته بمعنى مطلق - النموذج يتعلم من كيفية تحرك أرقامك أنت بالنسبة لبعضها، لذا فإن مقياسا شخصيا تطبقه بالطريقة نفسها كل يوم أفضل من محاولة مطابقة تصور شخص آخر لرقم 7.",
      zh: "压力（0-10）是你对这一天的主观判断，和这里所有主观字段一样，价值在于打分的一致性，而不是某种绝对意义上的准确——模型学习的是你自己的数字之间如何相对变动，所以每天用同样方式应用的个人尺度，比试图去匹配别人心中的「7 分」更有效。",
    },

    {
      key: 'app_field_where_do_i_find_numbers',
      match: /\b(where do i find these numbers|how do i know my screen time|where does my phone show screen time|how do i get my usage stats)(?:s|es|ing)?\b|این عددها را از کجا پیدا کنم|زمان صفحه گوشی را از کجا ببینم|أين أجد هذه الأرقام|كيف أعرف وقت شاشتي|这些数字在哪里找|怎么知道我的屏幕使用时间/i,
      en: "Both iOS (Settings > Screen Time) and Android (Settings > Digital Wellbeing) give you total time, a per-app breakdown, pickups and notification counts for the day - that covers almost every number this form asks for. The subjective ones (mood, stress, focus, sleep quality, comparison) are yours to judge; nothing is read off your device automatically, this app never has access to it.",
      fa: "هم آی‌اواس (تنظیمات ‹ Screen Time) و هم اندروید (تنظیمات ‹ Digital Wellbeing) زمان کل، تفکیک به‌ازای هر اپ، تعداد برداشتن گوشی و شمار اعلان‌های آن روز را می‌دهند - تقریباً همه‌ی عددهایی که این فرم می‌خواهد همین‌هاست. موارد ذهنی (خلق‌وخو، استرس، تمرکز، کیفیت خواب، مقایسه) قضاوت خودت است؛ هیچ چیزی به‌طور خودکار از دستگاهت خوانده نمی‌شود، این اپ اصلاً به آن دسترسی ندارد.",
      ar: "كل من آي أو إس (الإعدادات ‹ وقت الشاشة) وأندرويد (الإعدادات ‹ الرفاهية الرقمية) يعطيك الوقت الإجمالي، وتفصيلا لكل تطبيق، وعدد الالتقاطات وعدد الإشعارات لذلك اليوم - وهذا يغطي تقريبا كل رقم يطلبه هذا النموذج. أما الحقول الذاتية (المزاج، التوتر، التركيز، جودة النوم، المقارنة) فتقديرك أنت؛ لا شيء يُقرأ من جهازك تلقائيا، فهذا التطبيق لا يملك أي وصول إليه.",
      zh: "iOS（设置 ‹ 屏幕使用时间）和安卓（设置 ‹ 数字健康）都会给出当天的总时长、各应用明细、拿起次数和通知数量——这几乎覆盖了这个表单要求的所有数字。主观项（情绪、压力、专注、睡眠质量、比较）由你自己判断；没有任何内容会自动从你的设备读取，这个应用根本无法访问它。",
    },

    {
      key: 'app_field_estimate_ok',
      match: /\b(can i estimate|what if i dont know the exact number|is it ok to guess a number|do the numbers have to be exact)(?:s|es|ing)?\b|میتوانم تخمین بزنم|اگر عدد دقیق را ندانم چه|آیا عددها باید دقیق باشند|هل يمكنني التقدير|ماذا لو لم أعرف الرقم الدقيق|هل يجب أن تكون الأرقام دقيقة|可以估算吗|不知道确切数字怎么办|数字必须精确吗/i,
      en: "Estimating is fine and expected - the model works on patterns across days, not on any single number being exact to the minute. The one thing that genuinely degrades your results is estimating inconsistently: rounding generously some days and strictly others creates a trend that isn't real, which is worse than being consistently a bit off.",
      fa: "تخمین‌زدن اشکالی ندارد و اتفاقاً انتظار می‌رود - مدل روی الگوهای بین روزها کار می‌کند، نه روی اینکه یک عدد خاص دقیقاً تا دقیقه درست باشد. تنها چیزی که واقعاً نتیجه‌ات را خراب می‌کند تخمین ناهمگون است: بعضی روزها دست‌ودل‌بازانه گرد کردن و بعضی روزها سخت‌گیرانه، روندی می‌سازد که واقعی نیست - و این از یک خطای ثابتِ کوچک بدتر است.",
      ar: "التقدير مقبول ومتوقع - النموذج يعمل على الأنماط عبر الأيام، لا على أن يكون رقم واحد دقيقا حتى الدقيقة. الشيء الوحيد الذي يُفسد نتائجك فعلا هو التقدير غير المتسق: التقريب بسخاء في أيام وبصرامة في أخرى يخلق اتجاها غير حقيقي، وهذا أسوأ من خطأ صغير ثابت.",
      zh: "估算完全可以，而且本来就是预期的做法——模型依据的是跨天的模式，而不是某个数字精确到分钟。真正会削弱你结果的是估算不一致：有些天慷慨取整、有些天严格计算，会造出一个并不存在的趋势，这比一直偏差一点点更糟。",
    },

    
    // ====== R. Reading your result more deeply ======
    {
      key: 'app_what_is_a_good_score',
      match: /\b(what is a good score|what score should i aim for|is my score good|what counts as a good number)(?:s|es|ing)?\b|امتیاز خوب چند است|چه امتیازی باید هدف بگیرم|امتیاز من خوب است|ما هي الدرجة الجيدة|ما الدرجة التي أستهدفها|هل درجتي جيدة|多少分算好|该以多少分为目标|我的分数好吗/i,
      en: "There's no universal target, and the app deliberately doesn't set one - the class bands tell you where you currently sit, and the more useful question is which direction you're moving. A 62 that was 48 last week is a better story than a static 70. If you want a target, take it from your own trend line, not from a number someone else scored.",
      fa: "هدف جهانی‌ای وجود ندارد و اپ عمداً هم تعیینش نمی‌کند - دسته‌بندی‌ها به تو می‌گویند الان کجا ایستاده‌ای، و سؤال مفیدتر این است که به کدام سمت داری حرکت می‌کنی. عدد ۶۲ که هفته‌ی پیش ۴۸ بوده، داستان بهتری از یک ۷۰ ثابت است. اگر هدف می‌خواهی، از خط روند خودت بگیرش، نه از عددی که کس دیگری گرفته.",
      ar: "لا يوجد هدف عالمي، والتطبيق لا يضع واحدا عن قصد - فئات التصنيف تخبرك أين تقف الآن، والسؤال الأنفع هو في أي اتجاه تتحرك. درجة 62 كانت 48 الأسبوع الماضي قصة أفضل من 70 ثابتة. وإن أردت هدفا، فخذه من خط اتجاهك أنت، لا من رقم سجّله شخص آخر.",
      zh: "没有普适的目标分数，应用也刻意不设定一个——类别区间告诉你目前所处的位置，而更有用的问题是你正朝哪个方向移动。上周还是 48、这周到 62，比一个停滞的 70 是更好的故事。如果你想要目标，从你自己的趋势线里取，而不是从别人的分数里取。",
    },

    {
      key: 'app_score_changed_a_lot',
      match: /\b(why did my score change so much|score dropped suddenly|big jump in my score|score changed a lot from yesterday)(?:s|es|ing)?\b|چرا امتیازم اینقدر عوض شد|امتیازم ناگهان افت کرد|پرش بزرگ در امتیاز|لماذا تغيرت درجتي كثيرا|انخفضت درجتي فجأة|قفزة كبيرة في درجتي|为什么我的分数变化这么大|分数突然下降|分数大幅跳动/i,
      en: "The SHAP factors on that day's result are the actual answer - they name which of your own fields moved the score and by how much, for that specific prediction. Comparing today's top factors with the previous day's usually shows one or two fields did most of the work. That's a real explanation of that day's number, not a general theory about scores.",
      fa: "عامل‌های SHAP روی نتیجه‌ی همان روز جواب واقعی‌اند - نام می‌برند که کدام فیلدهای خودت امتیاز را جابه‌جا کرده‌اند و چقدر، برای همان پیش‌بینی مشخص. مقایسه‌ی عامل‌های اصلی امروز با روز قبل معمولاً نشان می‌دهد یکی دو فیلد بیشتر کار را کرده‌اند. این توضیح واقعی عدد همان روز است، نه یک نظریه‌ی کلی درباره‌ی امتیازها.",
      ar: "عوامل شاب في نتيجة ذلك اليوم هي الجواب الفعلي - فهي تسمّي أيّ حقولك حرّك الدرجة وبأي مقدار، لتلك التوقعات بالذات. ومقارنة عوامل اليوم الرئيسية بعوامل اليوم السابق تُظهر عادة أن حقلا أو حقلين قاما بمعظم العمل. هذا تفسير حقيقي لرقم ذلك اليوم، لا نظرية عامة عن الدرجات.",
      zh: "那一天结果页上的 SHAP 因素就是真正的答案——它们指出你自己的哪些字段推动了分数、推动了多少，针对的正是那一次预测。把今天的主要因素和前一天对比，通常会看到一两个字段起了大部分作用。这是对那天数字的真实解释，而不是关于分数的笼统理论。",
    },

    {
      key: 'app_class_boundary',
      match: /\b(class boundary|what makes me at risk instead of moderate|how are the classes decided|threshold between classes)(?:s|es|ing)?\b|مرز بین دسته‌ها|چه چیزی من را در معرض خطر میکند نه متوسط|الحد بين الفئات|ما الذي يجعلني في خطر بدلا من متوسط|类别边界|为什么我是有风险而不是中等/i,
      en: "The class comes from a trained classifier, not from a hand-written cutoff on the score - which is why a small change in your inputs can flip the class while the score barely moves, if you were already sitting near a boundary. The confidence number is what tells you whether you're near one: low confidence usually means exactly that.",
      fa: "دسته از یک طبقه‌بند آموزش‌دیده می‌آید، نه از یک برشِ دستیِ روی امتیاز - و برای همین است که اگر همین حالا نزدیک یک مرز نشسته باشی، یک تغییر کوچک در ورودی‌هایت می‌تواند دسته را عوض کند در حالی که امتیاز به‌سختی تکان می‌خورد. عدد اطمینان همان چیزی است که به تو می‌گوید آیا نزدیک مرزی هستی یا نه: اطمینان پایین معمولاً دقیقاً همین معنا را می‌دهد.",
      ar: "الفئة تأتي من مصنِّف مدرَّب، لا من حدّ يدوي على الدرجة - ولهذا فإن تغييرا صغيرا في مدخلاتك قد يقلب الفئة بينما تكاد الدرجة لا تتحرك، إن كنت أصلا قريبا من حدّ. ورقم الثقة هو ما يخبرك إن كنت قريبا من واحد: الثقة المنخفضة تعني ذلك عادة بالضبط.",
      zh: "类别来自一个训练好的分类器，而不是对分数手工划的一条线——正因如此，如果你本来就处在边界附近，输入上的微小变化就可能翻转类别，而分数几乎没动。置信度数字正是告诉你是否靠近边界的：低置信度通常恰恰意味着这一点。",
    },

    {
      key: 'app_persona_meaning',
      match: /\b(what is my persona|persona meaning|how is my persona decided|what does persona mean here)(?:s|es|ing)?\b|پرسونای من چیست|پرسونا یعنی چه|پرسونا چطور تعیین میشود|ما هي شخصيتي|ماذا تعني الشخصية|كيف تُحدد شخصيتي|我的角色画像是什么|画像是什么意思|画像是怎么定的/i,
      en: "The persona is a separate trained model from the score and the class - it groups your overall pattern of use rather than rating a single day, which is why it changes far less often than your daily score does. It's also one of the four things you can choose to share (or not) with a League friend.",
      fa: "پرسونا مدلی آموزش‌دیده و جدا از امتیاز و دسته است - به‌جای نمره‌دادن به یک روز، الگوی کلی استفاده‌ات را دسته‌بندی می‌کند، و برای همین خیلی کمتر از امتیاز روزانه‌ات تغییر می‌کند. ضمناً یکی از آن چهار چیزی است که می‌توانی انتخاب کنی با یک دوستِ لیگ به اشتراک بگذاری یا نگذاری.",
      ar: "الشخصية نموذج مدرَّب منفصل عن الدرجة والفئة - فهي تجمّع نمط استخدامك العام بدل تقييم يوم واحد، ولهذا تتغير أقل بكثير من درجتك اليومية. وهي أيضا واحدة من الأشياء الأربعة التي يمكنك اختيار مشاركتها (أو عدم مشاركتها) مع صديق في الدوري.",
      zh: "画像来自一个与分数和类别分开的训练模型——它归纳的是你整体的使用模式，而不是给某一天打分，所以它的变化频率远低于你的每日分数。它也是你可以选择是否与联赛好友分享的四项内容之一。",
    },

    {
      key: 'app_dimension_scores',
      match: /\b(what are dimension scores|dimension breakdown|how are the dimensions calculated)(?:s|es|ing)?\b|امتیازهای ابعاد چیستند|تفکیک ابعاد چطور محاسبه میشود|ما هي درجات الأبعاد|كيف تُحسب الأبعاد|维度分数是什么|各维度是怎么算的/i,
      en: "The dimension breakdown is deliberately NOT machine learning - it's a transparent, deterministic rollup of your own raw and derived fields, so you can trace exactly which numbers produced each dimension. That's the point: the score is the model's opinion, the dimensions are arithmetic you could check by hand.",
      fa: "تفکیک ابعاد عمداً یادگیری ماشین نیست - یک جمع‌بندی شفاف و قطعی از فیلدهای خام و مشتق خودت است، طوری که بتوانی دقیقاً ردیابی کنی کدام عددها هر بُعد را ساخته‌اند. نکته هم همین است: امتیاز نظر مدل است، ابعاد حسابی است که خودت می‌توانی با دست چکش کنی.",
      ar: "تفصيل الأبعاد ليس تعلّم آلة عن قصد - إنه تجميع شفاف وحتمي لحقولك الخام والمشتقة، بحيث يمكنك تتبّع أي الأرقام أنتج كل بُعد بالضبط. وهذا هو المقصد: الدرجة رأي النموذج، أما الأبعاد فحساب يمكنك التحقق منه بنفسك.",
      zh: "维度分解刻意不使用机器学习——它是对你自己的原始字段和推导字段做的一次透明、确定性的汇总，所以你可以准确追溯是哪些数字产生了每个维度。这正是重点：分数是模型的判断，而维度是你可以手工核对的算术。",
    },

    {
      key: 'app_result_same_inputs_same_score',
      match: /\b(will the same answers give the same score|is the prediction deterministic|same inputs different score)(?:s|es|ing)?\b|آیا همان پاسخ‌ها همان امتیاز را میدهند|پیش‌بینی قطعی است|هل تعطي الإجابات نفسها الدرجة نفسها|هل التنبؤ حتمي|同样的答案会给同样的分数吗|预测是确定性的吗/i,
      en: "Yes - the same inputs produce the same score every time; there's no randomness in the prediction step. The one thing that can legitimately shift a result on identical answers is your rolling baseline, which depends on your recent history, so the same day submitted after a very different week isn't quite the same input any more.",
      fa: "بله - همان ورودی‌ها هر بار همان امتیاز را می‌دهند؛ هیچ تصادفی‌بودنی در مرحله‌ی پیش‌بینی نیست. تنها چیزی که به‌درستی می‌تواند نتیجه را با پاسخ‌های یکسان جابه‌جا کند خط پایه‌ی متحرک توست که به تاریخچه‌ی اخیرت وابسته است، پس همان روز اگر بعد از هفته‌ای خیلی متفاوت ثبت شود دیگر کاملاً همان ورودی نیست.",
      ar: "نعم - المدخلات نفسها تنتج الدرجة نفسها في كل مرة؛ لا عشوائية في خطوة التنبؤ. الشيء الوحيد الذي قد يغيّر النتيجة بحق مع إجابات متطابقة هو خط أساسك المتحرك، وهو يعتمد على تاريخك الحديث، فاليوم نفسه إن أُرسل بعد أسبوع مختلف تماما لم يعد المدخل ذاته تماما.",
      zh: "会——同样的输入每次都产生同样的分数；预测环节没有任何随机性。唯一可能在答案相同的情况下合理改变结果的是你的滚动基线，它取决于你近期的历史，所以同一天的数据在一个截然不同的一周之后提交，输入其实已经不完全相同了。",
    },

    {
      key: 'app_result_compare_to_others',
      match: /\b(how do i compare to other people|am i worse than average|compare my score to others|what is the average score)(?:s|es|ing)?\b|نسبت به بقیه چطورم|امتیاز من از میانگین بدتر است|میانگین امتیاز چقدر است|كيف أقارن بالآخرين|هل أنا أسوأ من المتوسط|ما هو متوسط الدرجة|我和别人比怎么样|我比平均差吗|平均分是多少/i,
      en: "The app compares you to your own history by default, not to other users - that's a design choice, not a missing feature, because a stranger's 70 says nothing about whether your own 62 is progress. The Friends League is the one place a comparison appears, and only with people you both explicitly connected to and chose to share a score with.",
      fa: "اپ به‌صورت پیش‌فرض تو را با تاریخچه‌ی خودت مقایسه می‌کند، نه با کاربران دیگر - این یک انتخاب طراحی است نه قابلیتی جامانده، چون عدد ۷۰ یک غریبه هیچ چیزی درباره‌ی اینکه ۶۲ خودت پیشرفت هست یا نه نمی‌گوید. لیگ دوستان تنها جایی است که مقایسه ظاهر می‌شود، آن هم فقط با کسانی که هر دو صریحاً به هم وصل شده‌اید و انتخاب کرده‌ای امتیازت را با آن‌ها به اشتراک بگذاری.",
      ar: "يقارنك التطبيق افتراضيا بتاريخك أنت، لا بمستخدمين آخرين - وهذا خيار تصميمي لا ميزة ناقصة، لأن رقم 70 لشخص غريب لا يقول شيئا عمّا إذا كان 62 الخاص بك تقدما. ودوري الأصدقاء هو المكان الوحيد الذي تظهر فيه مقارنة، وفقط مع أشخاص ارتبطتما صراحة واخترت مشاركة درجتك معهم.",
      zh: "应用默认把你和你自己的历史比较，而不是和其他用户比——这是一个设计选择，不是缺失的功能，因为陌生人的 70 分说明不了你自己的 62 分算不算进步。好友联赛是唯一出现比较的地方，而且只针对你们双方明确建立了连接、并且你选择了分享分数的人。",
    },

    {
      key: 'app_result_first_day_accuracy',
      match: /\b(is my first result accurate|first check in result|can it tell anything from one day)(?:s|es|ing)?\b|نتیجه روز اول دقیق است|از یک روز چه چیزی میشود فهمید|هل نتيجة يومي الأول دقيقة|ماذا يمكن معرفته من يوم واحد|第一天的结果准确吗|一天能看出什么/i,
      en: "Your first prediction is a real prediction from the real model - it isn't a placeholder. What it can't do yet is put that number in context: no trend, no baseline of your own, no correlations. Those need several days, and the app hides the cards that depend on them rather than showing a shape drawn from one point.",
      fa: "اولین پیش‌بینی‌ات یک پیش‌بینی واقعی از مدل واقعی است - جانگهدار (placeholder) نیست. کاری که هنوز نمی‌تواند بکند این است که آن عدد را در بافت خودش بگذارد: نه روندی هست، نه خط پایه‌ی مخصوص خودت، نه همبستگی‌ای. این‌ها چند روز لازم دارند و اپ کارت‌هایی را که به آن‌ها وابسته‌اند پنهان می‌کند، به‌جای اینکه شکلی را از روی یک نقطه بکشد.",
      ar: "تنبؤك الأول تنبؤ حقيقي من النموذج الحقيقي - ليس عنصرا نائبا. ما لا يستطيعه بعد هو وضع ذلك الرقم في سياقه: لا اتجاه، ولا خط أساس خاص بك، ولا ارتباطات. هذه تحتاج عدة أيام، والتطبيق يُخفي البطاقات التي تعتمد عليها بدل رسم شكل من نقطة واحدة.",
      zh: "你的第一次预测是真实模型给出的真实预测——不是占位符。它目前做不到的是把这个数字放进语境里：没有趋势、没有属于你自己的基线、没有相关性。这些都需要好几天，应用会隐藏依赖它们的卡片，而不是从一个点画出一条曲线。",
    },

    {
      key: 'app_result_share_screenshot',
      match: /\b(can i share my result|share my score with someone|screenshot my result)(?:s|es|ing)?\b|میتوانم نتیجه‌ام را به اشتراک بگذارم|امتیازم را با کسی به اشتراک بگذارم|هل يمكنني مشاركة نتيجتي|مشاركة درجتي مع شخص|我能分享我的结果吗|把分数分享给别人/i,
      en: "The PDF report is the built-in way to hand your result to someone (a doctor, a coach, yourself later) - it carries the score, class, factors and recommendations from that exact prediction. Inside the app, sharing goes through the Friends League only, one category at a time, and stays revocable.",
      fa: "گزارش PDF راه توکار برای دادن نتیجه‌ات به کسی است (پزشک، مربی، یا خودِ بعدی‌ات) - امتیاز، دسته، عامل‌ها و پیشنهادهای همان پیش‌بینی مشخص را با خود می‌برد. داخل خود اپ، اشتراک‌گذاری فقط از مسیر لیگ دوستان می‌گذرد، هر بار یک دسته، و همیشه قابل پس‌گرفتن است.",
      ar: "تقرير بي دي إف هو الطريقة المدمجة لتسليم نتيجتك لشخص ما (طبيب، مدرب، أو نفسك لاحقا) - وهو يحمل الدرجة والفئة والعوامل والتوصيات من تلك التوقعات بالذات. أما داخل التطبيق فالمشاركة تمر عبر دوري الأصدقاء فقط، فئة واحدة في كل مرة، وتبقى قابلة للإلغاء.",
      zh: "PDF 报告是把结果交给别人（医生、教练，或者以后的自己）的内置方式——它包含那一次预测的分数、类别、影响因素和建议。在应用内部，分享只通过好友联赛进行，一次一个类别，并且始终可以撤回。",
    },

    
    // ====== S. CSV, League, coach, errors and settings: further depth ======
    {
      key: 'app_csv_duplicate_dates',
      match: /\b(duplicate dates in csv|same date twice in my file|what if two rows have the same date)(?:s|es|ing)?\b|تاریخ تکراری در فایل|اگر دو ردیف یک تاریخ داشته باشند|تواريخ مكررة في الملف|ماذا لو تكرر التاريخ في صفين|csv里有重复日期|两行日期相同怎么办/i,
      en: "A date that already exists in your history is a conflict the importer surfaces rather than resolving silently - it will not quietly overwrite a day you already logged, because that would destroy a real entry to make an import succeed. Remove or fix the duplicate row and re-import.",
      fa: "تاریخی که از قبل در تاریخچه‌ات وجود دارد یک تعارض است که وارد‌کننده آن را نشان می‌دهد نه اینکه بی‌صدا حلش کند - روزی را که قبلاً ثبت کرده‌ای بی‌سروصدا بازنویسی نمی‌کند، چون این یعنی نابودکردن یک ثبت واقعی فقط برای اینکه یک ورود موفق شود. ردیف تکراری را حذف یا اصلاح کن و دوباره وارد کن.",
      ar: "التاريخ الموجود مسبقا في سجلك تعارُض يُظهره المستورد بدل حلّه صامتا - فهو لن يستبدل بهدوء يوما سجّلته من قبل، لأن ذلك يعني إتلاف إدخال حقيقي لمجرد إنجاح عملية استيراد. احذف الصف المكرر أو صحّحه ثم أعد الاستيراد.",
      zh: "如果某个日期在你的历史里已经存在，导入器会把它作为冲突提示出来，而不是悄悄处理——它不会默默覆盖你已经记录过的某一天，因为那等于为了让导入成功而毁掉一条真实记录。删除或修正重复的行，然后重新导入。",
    },

    {
      key: 'app_csv_encoding',
      match: /\b(csv opens wrong in excel|csv encoding problem|garbled characters in my csv|utf 8 csv)(?:s|es|ing)?\b|فایل در اکسل درست باز نمیشود|مشکل انکدینگ فایل|کاراکترهای نامفهوم در فایل|الملف يفتح خطأ في إكسل|مشكلة ترميز الملف|أحرف مشوهة في الملف|csv在excel里打开是乱码|csv编码问题|文件里有乱码/i,
      en: "Exports are UTF-8, which Excel on some systems opens with the wrong encoding by default and shows as garbled text - the file itself is fine. Use Excel's Data > From Text/CSV import (choosing UTF-8), or open it in a plain text editor to confirm. Nothing about the garbling affects re-importing it here.",
      fa: "خروجی‌ها UTF-8 هستند که اکسل روی بعضی سیستم‌ها به‌طور پیش‌فرض با انکدینگ اشتباه باز می‌کند و متن نامفهوم نشان می‌دهد - خود فایل سالم است. از مسیر Data ‹ From Text/CSV در اکسل استفاده کن (و UTF-8 را انتخاب کن)، یا برای مطمئن‌شدن با یک ویرایشگر متن ساده بازش کن. این نامفهوم‌شدن هیچ اثری روی وارد‌کردن دوباره‌اش در اینجا ندارد.",
      ar: "الملفات المصدَّرة بترميز UTF-8، وإكسل على بعض الأنظمة يفتحها افتراضيا بترميز خاطئ فتظهر كنص مشوّه - والملف نفسه سليم. استخدم في إكسل مسار Data ‹ From Text/CSV (واختر UTF-8)، أو افتحه بمحرر نصوص بسيط للتأكد. ولا يؤثر هذا التشوّه إطلاقا على إعادة استيراده هنا.",
      zh: "导出文件是 UTF-8 编码，某些系统上的 Excel 默认会用错误的编码打开，显示成乱码——文件本身是好的。在 Excel 里用「数据 ‹ 从文本/CSV」导入（并选择 UTF-8），或者用纯文本编辑器打开确认。乱码显示完全不影响把它重新导入到这里。",
    },

    {
      key: 'app_csv_how_many_rows',
      match: /\b(how many rows can i import|import limit|can i import a year of data|maximum csv size)(?:s|es|ing)?\b|چند ردیف میتوانم وارد کنم|محدودیت ورود داده|یک سال داده وارد کنم|كم صفا يمكنني استيراده|حد الاستيراد|استيراد بيانات سنة|能导入多少行|导入上限|能导入一年的数据吗/i,
      en: "There's no small fixed row cap - a normal personal history (weeks to a couple of years) imports fine in one go. The practical limit is that every row is validated individually, so a very large file takes proportionally longer and reports every bad row rather than stopping at the first one.",
      fa: "سقف ردیفِ کوچکِ ثابتی وجود ندارد - یک تاریخچه‌ی شخصی معمولی (چند هفته تا یکی دو سال) یکجا و بدون مشکل وارد می‌شود. محدودیت عملی این است که هر ردیف جداگانه اعتبارسنجی می‌شود، پس یک فایل خیلی بزرگ به‌تناسب بیشتر طول می‌کشد و همه‌ی ردیف‌های خراب را گزارش می‌کند نه اینکه سر اولی متوقف شود.",
      ar: "لا يوجد سقف صغير ثابت للصفوف - تاريخ شخصي عادي (أسابيع إلى سنتين) يُستورد دفعة واحدة دون مشكلة. الحد العملي هو أن كل صف يُتحقق منه على حدة، فالملف الكبير جدا يستغرق وقتا متناسبا ويُبلّغ عن كل صف معطوب بدل التوقف عند أوله.",
      zh: "没有一个很小的固定行数上限——正常的个人历史（几周到一两年）可以一次性导入。实际的限制在于每一行都会被单独校验，所以非常大的文件会按比例花更长时间，并且会报告所有有问题的行，而不是在第一行就停下。",
    },

    {
      key: 'app_league_real_name',
      match: /\b(does my friend see my real name|is my name visible in league|what name do friends see)(?:s|es|ing)?\b|آیا دوستم نام واقعی من را میبیند|چه نامی برای دوستان دیده میشود|هل يرى صديقي اسمي الحقيقي|أي اسم يراه الأصدقاء|朋友能看到我的真名吗|好友看到的是什么名字/i,
      en: "Friends see the display name you chose at registration, which does not have to be your real name - you can set it to anything. What they see beyond that is strictly the categories you enabled (persona, score, rank, top factor), each one independently, and you can turn any of them back off later.",
      fa: "دوستان همان نام نمایشی‌ای را می‌بینند که موقع ثبت‌نام انتخاب کرده‌ای، و لازم نیست نام واقعی‌ات باشد - می‌توانی هر چیزی بگذاری. فراتر از آن، فقط دسته‌هایی را می‌بینند که فعال کرده‌ای (پرسونا، امتیاز، رتبه، عامل اصلی)، هر کدام مستقل از بقیه، و هر وقت بخواهی می‌توانی هر کدام را دوباره خاموش کنی.",
      ar: "يرى الأصدقاء اسم العرض الذي اخترته عند التسجيل، وليس لزاما أن يكون اسمك الحقيقي - يمكنك ضبطه على أي شيء. وما يرونه بعد ذلك هو حصرا الفئات التي فعّلتها (الشخصية، الدرجة، الترتيب، العامل الرئيسي)، كل واحدة على حدة، ويمكنك إيقاف أي منها لاحقا.",
      zh: "好友看到的是你注册时设置的显示名称，它不必是你的真名——你可以随意设置。除此之外，他们能看到的严格限于你启用的那些类别（画像、分数、排名、主要因素），每一项都是独立的，你之后随时可以把任意一项重新关掉。",
    },

    {
      key: 'app_league_ranking',
      match: /\b(how is the league rank calculated|how does ranking work|why am i ranked here)(?:s|es|ing)?\b|رتبه لیگ چطور محاسبه میشود|رتبه‌بندی چطور کار میکند|كيف يُحسب ترتيب الدوري|كيف يعمل الترتيب|联赛排名怎么算|排名是怎么运作的/i,
      en: "Rank is computed only among the friends you're actually connected to who have chosen to share a score - it's not a global leaderboard, and someone who shares only their persona simply isn't in the ranking. That also means your rank can shift because a friend changed a sharing toggle, not because your own numbers moved.",
      fa: "رتبه فقط میان دوستانی محاسبه می‌شود که واقعاً به آن‌ها وصلی و انتخاب کرده‌اند امتیازشان را به اشتراک بگذارند - یک جدول رده‌بندی جهانی نیست، و کسی که فقط پرسونایش را به اشتراک می‌گذارد اصلاً در رتبه‌بندی نیست. این یعنی رتبه‌ات ممکن است به این خاطر جابه‌جا شود که یک دوست کلید اشتراک‌گذاری‌اش را عوض کرده، نه اینکه عددهای خودت تغییر کرده باشند.",
      ar: "يُحسب الترتيب فقط بين الأصدقاء المرتبطين بك فعلا والذين اختاروا مشاركة درجتهم - فهو ليس لوحة صدارة عالمية، ومن يشارك شخصيته فقط لا يدخل الترتيب أصلا. وهذا يعني أيضا أن ترتيبك قد يتغير لأن صديقا بدّل مفتاح مشاركة، لا لأن أرقامك أنت تحركت.",
      zh: "排名只在你实际连接、并且选择了分享分数的好友之间计算——它不是全局排行榜，只分享画像的人根本不进入排名。这也意味着你的排名可能因为某位好友改动了分享开关而变化，而不是因为你自己的数字变了。",
    },

    {
      key: 'app_league_leave_group',
      match: /\b(can i leave a group chat|leave a league group|exit group chat)(?:s|es|ing)?\b|میتوانم از گروه خارج شوم|خروج از گروه لیگ|هل يمكنني مغادرة محادثة جماعية|الخروج من مجموعة الدوري|能退出群聊吗|离开联赛群组/i,
      en: "Yes - leaving a group is separate from removing the individual connections that got you into it, so you can step out of a group conversation while keeping your one-to-one connection with each person in it.",
      fa: "بله - خارج‌شدن از گروه جدا از حذف‌کردن ارتباط‌های تکی‌ای است که تو را وارد آن کرده، پس می‌توانی از یک گفت‌وگوی گروهی بیرون بیایی و در عین حال ارتباط دو‌نفره‌ات با تک‌تک افراد آن را نگه داری.",
      ar: "نعم - مغادرة المجموعة منفصلة عن إزالة الاتصالات الفردية التي أدخلتك إليها، فيمكنك الخروج من محادثة جماعية مع الاحتفاظ باتصالك الثنائي مع كل شخص فيها.",
      zh: "可以——退出群组和解除把你带进这个群的那些一对一连接是两回事，所以你可以离开群聊，同时保留与其中每个人的一对一连接。",
    },

    {
      key: 'app_coach_sees_my_data',
      match: /\b(can the coach see my data|does the coach know my score|what data does the coach use)(?:s|es|ing)?\b|آیا مربی داده‌های من را میبیند|مربی امتیاز من را میداند|هل يرى المدرب بياناتي|هل يعرف المدرب درجتي|教练能看到我的数据吗|教练知道我的分数吗/i,
      en: "Yes, and that's the point: the menu questions read your own real, current numbers - your latest score, your factors, your history - and answer from them rather than giving generic advice. It's your data in your browser; with the external connector off, nothing about it is sent anywhere.",
      fa: "بله و نکته هم همین است: سؤال‌های منو، عددهای واقعی و فعلی خودت را می‌خوانند - آخرین امتیازت، عامل‌هایت، تاریخچه‌ات - و از روی همان‌ها جواب می‌دهند نه اینکه توصیه‌ی کلی بدهند. این داده‌ی توست در مرورگر خودت؛ با خاموش‌بودن کانکتور بیرونی، هیچ چیزی از آن به جایی فرستاده نمی‌شود.",
      ar: "نعم، وهذا هو المقصد: أسئلة القائمة تقرأ أرقامك الحقيقية الحالية - آخر درجة لك، وعواملك، وتاريخك - وتجيب منها بدل تقديم نصائح عامة. إنها بياناتك في متصفحك؛ ومع إيقاف الموصّل الخارجي لا يُرسل منها شيء إلى أي مكان.",
      zh: "能看到，而这正是重点：菜单里的问题会读取你自己真实的当前数据——最新分数、影响因素、历史记录——并据此作答，而不是给出泛泛的建议。这是你浏览器里属于你的数据；在外部连接器关闭的情况下，其中没有任何内容会被发送出去。",
    },

    {
      key: 'app_coach_languages',
      match: /\b(does the coach speak my language|can i ask in persian|can i ask in arabic|can i ask in chinese)(?:s|es|ing)?\b|مربی به زبان من صحبت میکند|میتوانم فارسی بپرسم|هل يتحدث المدرب لغتي|هل يمكنني السؤال بالعربية|教练会说我的语言吗|我可以用中文提问吗/i,
      en: "Ask in English, Persian, Arabic or Chinese - every topic carries an answer in all four, and the matcher normalizes script variants (Arabic vs Persian yeh/kaf, hamza forms, Arabic-Indic digits) so a different but equally correct spelling isn't treated as a typo. Mixed-language questions usually work too.",
      fa: "به انگلیسی، فارسی، عربی یا چینی بپرس - هر موضوع در هر چهار زبان جواب دارد و موتور تطبیق، گونه‌های نگارشی را یکسان‌سازی می‌کند (ی و ک عربی در برابر فارسی، شکل‌های همزه، ارقام هندی-عربی) تا یک املای متفاوت اما به‌همان‌اندازه درست، تایپی اشتباه به حساب نیاید. سؤال‌های دوزبانه هم معمولاً کار می‌کنند.",
      ar: "اسأل بالإنجليزية أو الفارسية أو العربية أو الصينية - كل موضوع يحمل إجابة باللغات الأربع، والمطابِق يوحّد صيغ الحروف (الياء والكاف العربية مقابل الفارسية، وأشكال الهمزة، والأرقام الهندية العربية) حتى لا يُعامل إملاء مختلف لكنه صحيح تماما على أنه خطأ مطبعي. والأسئلة المختلطة اللغة تعمل عادة أيضا.",
      zh: "用英语、波斯语、阿拉伯语或中文提问都可以——每个主题在四种语言里都有对应答案，而且匹配器会归一化字形变体（阿拉伯语与波斯语的 ye/kaf、hamza 的各种形式、阿拉伯-印度数字），这样一个不同但同样正确的拼写不会被当成拼写错误。混合语言的提问通常也能识别。",
    },

    {
      key: 'app_coach_typos_ok',
      match: /\b(what if i make a typo|does it understand misspelling|i cant spell it right)(?:s|es|ing)?\b|اگر غلط تایپی داشته باشم|غلط املایی را متوجه میشود|ماذا لو أخطأت في الكتابة|هل يفهم الأخطاء الإملائية|打错字怎么办|拼错了能识别吗/i,
      en: "Typos are handled by design, not by luck: matching runs on edit distance with adjacent-transposition counted as a single edit, so 'scroe' still reaches 'score'. Very short words are matched exactly on purpose, because fuzzing three-letter words creates more wrong matches than it fixes.",
      fa: "غلط‌های تایپی از روی طراحی مدیریت می‌شوند نه از روی شانس: تطبیق بر پایه‌ی فاصله‌ی ویرایشی کار می‌کند و جابه‌جایی دو حرف کنار هم یک ویرایش شمرده می‌شود، پس «scroe» همچنان به «score» می‌رسد. واژه‌های خیلی کوتاه عمداً فقط دقیق تطبیق داده می‌شوند، چون فازی‌کردن واژه‌های سه‌حرفی بیشتر از آنکه درست کند تطبیق اشتباه می‌سازد.",
      ar: "الأخطاء المطبعية مُعالَجة بالتصميم لا بالصدفة: تعمل المطابقة على مسافة التحرير مع احتساب تبديل حرفين متجاورين تعديلا واحدا، فتصل «scroe» إلى «score». أما الكلمات القصيرة جدا فتُطابَق تماما عن قصد، لأن التقريب في كلمات من ثلاثة أحرف يُنتج مطابقات خاطئة أكثر مما يُصلح.",
      zh: "错别字是被设计处理过的，不是碰运气：匹配基于编辑距离，相邻字符调换只算一次编辑，所以「scroe」仍然能找到「score」。非常短的词则刻意只做精确匹配，因为对三个字母的词做模糊匹配，制造的错误匹配比它修正的更多。",
    },

    {
      key: 'app_error_logged_out',
      match: /\b(why was i logged out|logged out suddenly|session expired|keeps logging me out)(?:s|es|ing)?\b|چرا از حسابم خارج شدم|ناگهان لاگ‌اوت شدم|نشست منقضی شد|لماذا خرجت من حسابي|تم تسجيل خروجي فجأة|انتهت الجلسة|为什么我被登出了|突然退出登录|会话过期/i,
      en: "Your login is a token held in this browser, so it goes away if the token expires, if you clear site data, or if you open the app in a different browser or a private window. Entering and leaving Demo Mode also swaps tokens deliberately - if you closed the tab mid-demo, reopening the app restores your real session.",
      fa: "ورودت یک توکن است که در همین مرورگر نگه داشته می‌شود، پس اگر توکن منقضی شود، داده‌های سایت را پاک کنی، یا اپ را در مرورگری دیگر یا پنجره‌ی ناشناس باز کنی از بین می‌رود. ورود و خروج از حالت دمو هم عمداً توکن‌ها را جابه‌جا می‌کند - اگر وسط دمو تب را بستی، باز‌کردن دوباره‌ی اپ نشست واقعی‌ات را برمی‌گرداند.",
      ar: "تسجيل دخولك رمز محفوظ في هذا المتصفح، فيزول إن انتهت صلاحيته، أو مسحت بيانات الموقع، أو فتحت التطبيق في متصفح آخر أو نافذة خاصة. كما أن الدخول إلى وضع العرض التجريبي والخروج منه يبدّل الرموز عن قصد - وإن أغلقت التبويب في منتصف العرض، فإعادة فتح التطبيق تستعيد جلستك الحقيقية.",
      zh: "你的登录状态是保存在这个浏览器里的一个令牌，所以令牌过期、清除站点数据、或者在另一个浏览器或无痕窗口打开应用，登录都会消失。进入和离开演示模式也会刻意交换令牌——如果你在演示途中关掉了标签页，重新打开应用会恢复你的真实会话。",
    },

    {
      key: 'app_error_which_browsers',
      match: /\b(which browsers are supported|does it work in safari|browser compatibility|best browser for this)(?:s|es|ing)?\b|کدام مرورگرها پشتیبانی میشوند|در سافاری کار میکند|سازگاری مرورگر|ما المتصفحات المدعومة|هل يعمل في سفاري|توافق المتصفح|支持哪些浏览器|在safari里能用吗|浏览器兼容性/i,
      en: "Any current Chrome, Edge, Firefox or Safari works - it's a standard web app with no plugin and no install. Very old browsers and aggressive script blockers are the two things that actually break it, usually showing up as a blank page rather than an error message.",
      fa: "هر نسخه‌ی به‌روز کروم، اج، فایرفاکس یا سافاری کار می‌کند - یک وب‌اپ استاندارد است بدون افزونه و بدون نصب. تنها دو چیزی که واقعاً خرابش می‌کنند مرورگرهای خیلی قدیمی و مسدودکننده‌های تهاجمی اسکریپت‌اند، که معمولاً به شکل یک صفحه‌ی خالی ظاهر می‌شوند نه یک پیام خطا.",
      ar: "أي إصدار حديث من كروم أو إيدج أو فايرفوكس أو سفاري يعمل - فهو تطبيق ويب قياسي بلا إضافات وبلا تثبيت. والشيئان اللذان يعطلانه فعلا هما المتصفحات القديمة جدا وحاجبات السكربتات الصارمة، وعادة ما يظهر ذلك كصفحة فارغة لا كرسالة خطأ.",
      zh: "任何较新版本的 Chrome、Edge、Firefox 或 Safari 都可以——它是标准的网页应用，无需插件也无需安装。真正会让它出问题的只有两样：非常老旧的浏览器，以及拦截力度很强的脚本屏蔽插件，而且通常表现为白屏而不是错误提示。",
    },

    {
      key: 'app_error_lost_connection_midway',
      match: /\b(what if i lose internet during a check in|connection dropped while submitting|internet cut off mid submit)(?:s|es|ing)?\b|اگر وسط چک‌این اینترنت قطع شود|قطع اتصال هنگام ارسال|ماذا لو انقطع الإنترنت أثناء التسجيل|انقطع الاتصال أثناء الإرسال|打卡时断网怎么办|提交时连接中断/i,
      en: "A submission that never reached the server is not saved - you'll get a clear error rather than a silent partial save, and nothing half-written enters your history. Your typed answers stay on the form, so reconnecting and pressing submit again is normally all it takes.",
      fa: "ثبتی که هرگز به سرور نرسیده ذخیره نمی‌شود - یک خطای شفاف می‌گیری نه یک ذخیره‌ی ناقصِ بی‌صدا، و هیچ چیز نیمه‌نوشته‌ای وارد تاریخچه‌ات نمی‌شود. پاسخ‌هایی که تایپ کرده‌ای روی فرم می‌مانند، پس معمولاً وصل‌شدن دوباره و زدن دکمه‌ی ارسال کافی است.",
      ar: "الإرسال الذي لم يصل إلى الخادم لا يُحفظ - ستحصل على خطأ واضح لا على حفظ جزئي صامت، ولا يدخل سجلك أي شيء مكتوب نصفه. وتبقى إجاباتك المكتوبة في النموذج، فعادة يكفي إعادة الاتصال والضغط على إرسال مجددا.",
      zh: "没有到达服务器的提交不会被保存——你会收到明确的错误提示，而不是悄无声息的部分保存，也不会有任何写了一半的内容进入你的历史。你填写的答案会留在表单上，所以通常只要重新连上网再点一次提交就可以了。",
    },

    {
      key: 'app_error_report_a_bug',
      match: /\b(how do i report a bug|something is broken|where do i report a problem)(?:s|es|ing)?\b|چطور یک باگ گزارش کنم|یک چیزی خراب است|مشکل را کجا گزارش کنم|كيف أبلغ عن خلل|شيء ما معطل|أين أبلغ عن مشكلة|怎么报告bug|有东西坏了|在哪里反馈问题/i,
      en: "The most useful bug report names the page, what you expected, what happened instead, and anything red in the browser console (F12 > Console). A screenshot of the console beats a description of it - most front-end problems in a web app are one specific error line that says exactly what failed.",
      fa: "مفیدترین گزارش باگ صفحه را نام می‌برد، اینکه چه انتظاری داشتی، به‌جایش چه شد، و هر چیز قرمزی که در کنسول مرورگر است (F12 ‹ Console). یک اسکرین‌شات از کنسول از توصیف‌کردنش بهتر است - بیشتر مشکلات سمت کاربر در یک وب‌اپ یک خط خطای مشخص‌اند که دقیقاً می‌گوید چه چیزی شکست خورده.",
      ar: "أنفع بلاغ عن خلل يذكر الصفحة، وما توقعته، وما حدث بدلا منه، وأي شيء أحمر في وحدة تحكم المتصفح (F12 ‹ Console). ولقطة شاشة للوحدة أفضل من وصفها - فمعظم مشاكل الواجهة في تطبيق ويب هي سطر خطأ واحد محدد يقول بالضبط ما الذي فشل.",
      zh: "最有用的问题反馈会说明：哪个页面、你预期的是什么、实际发生了什么，以及浏览器控制台里任何红色的报错（F12 ‹ Console）。控制台的截图比文字描述更有价值——网页应用中大多数前端问题都是一行具体的错误信息，它会准确说明是什么出了问题。",
    },

    {
      key: 'app_change_display_name',
      match: /\b(change my display name|change my name|edit my profile name)(?:s|es|ing)?\b|تغییر نام نمایشی|تغییر نام من|تغيير اسم العرض|تغيير اسمي|修改显示名称|改我的名字/i,
      en: "Your display name is what League friends see, and it's editable in Settings - it doesn't have to be your real name and changing it doesn't affect any of your data or history.",
      fa: "نام نمایشی‌ات همان چیزی است که دوستان لیگ می‌بینند و در تنظیمات قابل ویرایش است - لازم نیست نام واقعی‌ات باشد و عوض‌کردنش هیچ اثری روی داده‌ها یا تاریخچه‌ات ندارد.",
      ar: "اسم العرض هو ما يراه أصدقاء الدوري، وهو قابل للتعديل في الإعدادات - وليس لزاما أن يكون اسمك الحقيقي، وتغييره لا يؤثر على أي من بياناتك أو سجلك.",
      zh: "显示名称是联赛好友看到的名字，可以在设置里修改——它不必是你的真名，改动它也不会影响你的任何数据或历史记录。",
    },

    {
      key: 'app_settings_where_is_it',
      match: /\b(where are the settings|how do i open settings|settings page location)(?:s|es|ing)?\b|تنظیمات کجاست|چطور تنظیمات را باز کنم|أين الإعدادات|كيف أفتح الإعدادات|设置在哪里|怎么打开设置/i,
      en: "Settings is reachable from the top navigation on every page. Theme, language, the games toggle, sound, motion, your display name and account deletion all live there - it's one page, not settings scattered across each feature.",
      fa: "تنظیمات از نوار بالای هر صفحه در دسترس است. تم، زبان، کلید بازی‌ها، صدا، حرکت، نام نمایشی و حذف حساب همه آنجا هستند - یک صفحه است، نه تنظیماتی که در هر بخش پراکنده باشند.",
      ar: "الإعدادات متاحة من شريط التنقل العلوي في كل صفحة. المظهر واللغة ومفتاح الألعاب والصوت والحركة واسم العرض وحذف الحساب كلها هناك - إنها صفحة واحدة، لا إعدادات مبعثرة عبر كل ميزة.",
      zh: "设置可以从每个页面顶部的导航进入。主题、语言、游戏开关、声音、动效、显示名称和账户删除都在那里——它是一个统一的页面，而不是散落在各个功能里的零散设置。",
    },

    
    // ====== T. The coach's own menu, plan, analytics, demo, badges and letter ======
    {
      key: 'app_coach_trend_questions',
      match: /\b(is my sleep getting better|questions about whether something is improving|getting better or worse questions|trend questions in the menu)(?:s|es|ing)?\b|سوال‌های روند در منو|آیا خوابم دارد بهتر میشود|أسئلة الاتجاه في القائمة|هل يتحسن نومي|菜单里的趋势问题|我的睡眠在变好吗/i,
      en: "The menu has a whole family of 'is my X getting better or worse?' questions, one per signal the app stores per day. They're answered from your own history: the answer names the number you started around, the number you're around now, and whether that direction is the healthier one for that specific field - rising sleep hours is an improvement, rising stress is not, and the answer knows the difference.",
      fa: "منو یک خانواده‌ی کامل از سؤال‌های «آیا فلان چیزم دارد بهتر می‌شود یا بدتر؟» دارد، یکی برای هر سیگنالی که اپ روزانه ذخیره می‌کند. جواب‌ها از تاریخچه‌ی خودت می‌آیند: جواب می‌گوید از حدود چه عددی شروع کردی، الان حدود چه عددی هستی، و آیا آن جهت برای همان فیلد جهتِ سالم‌تر است - بالا رفتن ساعت خواب پیشرفت است، بالا رفتن استرس نه، و جواب این تفاوت را می‌داند.",
      ar: "تحتوي القائمة على عائلة كاملة من أسئلة «هل يتحسّن كذا لديّ أم يسوء؟»، واحد لكل إشارة يخزّنها التطبيق يوميا. والإجابات تأتي من تاريخك أنت: تذكر الرقم الذي بدأت عنده تقريبا، والرقم الذي أنت عنده الآن، وما إذا كان ذلك الاتجاه هو الأصحّ لذلك الحقل تحديدا - فارتفاع ساعات النوم تحسّن، وارتفاع التوتر ليس كذلك، والإجابة تعرف الفرق.",
      zh: "菜单里有一整组「我的某项在变好还是变差？」的问题，应用每天存储的每个信号都对应一个。答案来自你自己的历史：会说明你起初大约在什么数值、现在大约在什么数值，以及那个方向对这个特定字段而言是不是更健康的方向——睡眠时长上升是进步，压力上升不是，答案知道这个区别。",
    },

    {
      key: 'app_coach_typical_questions',
      match: /\b(what is typical for me|my own baseline questions|typical value questions in the menu)(?:s|es|ing)?\b|سوال‌های مقدار معمول من|خط پایه خودم در منو|أسئلة القيمة المعتادة لي|خط أساسي في القائمة|我的典型值问题|菜单里的个人基线问题/i,
      en: "There's a 'what is a typical X for me?' question per signal, answered with your own average, your real range, and the actual date of your healthiest day for that field. It also tells you which side of the app's reference target your typical value sits on. This is your personal baseline, not a population norm.",
      fa: "برای هر سیگنال یک سؤال «مقدار معمول فلان چیز برای من چقدر است؟» هست که با میانگین خودت، بازه‌ی واقعی‌ات و تاریخ دقیق سالم‌ترین روزت برای همان فیلد جواب داده می‌شود. ضمناً می‌گوید مقدار معمولت کدام سمت هدف مرجع اپ قرار می‌گیرد. این خط پایه‌ی شخصی توست، نه یک هنجار جمعیتی.",
      ar: "لكل إشارة سؤال «ما القيمة المعتادة لكذا بالنسبة لي؟»، يُجاب عنه بمتوسطك أنت، ومداك الحقيقي، والتاريخ الفعلي لأصحّ يوم لك في ذلك الحقل. ويخبرك أيضا في أي جانب من هدف التطبيق المرجعي تقع قيمتك المعتادة. هذا خط أساسك الشخصي، لا معيار سكاني.",
      zh: "每个信号都有一个「对我来说典型的某项是多少？」的问题，答案会给出你自己的平均值、真实的波动区间，以及你在这个字段上最健康那一天的实际日期。它还会告诉你，你的典型值落在应用参考目标的哪一侧。这是你的个人基线，不是人群标准。",
    },

    {
      key: 'app_coach_steady_questions',
      match: /\b(how steady is my|steadiness questions|how consistent am i|which of my signals swing the most)(?:s|es|ing)?\b|سوال‌های ثبات|کدام سیگنالم بیشترین نوسان را دارد|أسئلة الثبات|أي إشاراتي أكثر تقلبا|稳定性问题|我哪项信号波动最大/i,
      en: "The 'how steady is my X?' family measures how far a typical day sits from your own average for that signal, and calls it steady or swingy relative to its own scale. A swingy field is where one unusual day can drag a weekly number around - which is exactly the situation the exception-day checkbox exists for.",
      fa: "خانواده‌ی «فلان چیزم چقدر باثبات است؟» اندازه می‌گیرد که یک روز معمولی چقدر از میانگین خودت برای آن سیگنال فاصله دارد و آن را نسبت به مقیاس خودش باثبات یا پرنوسان می‌نامد. فیلد پرنوسان همان جایی است که یک روز غیرعادی می‌تواند عدد هفتگی را با خودش بکشد - و دقیقاً همان وضعیتی است که تیک «روز استثنا» برایش وجود دارد.",
      ar: "عائلة «ما مدى ثبات كذا لديّ؟» تقيس كم يبتعد يوم معتاد عن متوسطك أنت في تلك الإشارة، وتصفه بالثابت أو المتقلب نسبةً إلى مقياسه. والحقل المتقلب هو حيث يستطيع يوم واحد غير معتاد أن يجرّ الرقم الأسبوعي معه - وهذا بالضبط الوضع الذي وُجد له مربع «اليوم الاستثنائي».",
      zh: "「我的某项有多稳定？」这一组会衡量典型的一天离你自己在该信号上的平均值有多远，并按它自身的尺度判定为稳定或波动。波动大的字段，正是单独一个异常日就能把一周数字拉偏的地方——而这恰恰是「例外日」勾选框存在的场景。",
    },

    {
      key: 'app_coach_menu_needs_history',
      match: /\b(why does a menu question say not enough days|menu answer says it needs more days|coach says it cant answer yet)(?:s|es|ing)?\b|چرا یک سوال منو میگوید روز کافی نیست|مربی میگوید هنوز نمیتواند جواب بدهد|لماذا يقول سؤال في القائمة لا توجد أيام كافية|المدرب يقول لا يستطيع الإجابة بعد|为什么菜单问题说天数不够|教练说还不能回答/i,
      en: "Some menu questions need several days of history, and when they don't have them they say exactly how many usable days they found instead of drawing a trend through two points. Note that days you marked as exceptions are deliberately left out of that count - so a few of those can be why the number is lower than the number of check-ins you remember doing.",
      fa: "بعضی سؤال‌های منو به چند روز تاریخچه نیاز دارند و وقتی ندارند، دقیقاً می‌گویند چند روزِ قابل‌استفاده پیدا کرده‌اند، به‌جای اینکه از دل دو نقطه روند بکشند. توجه کن که روزهایی که استثنا علامت زده‌ای عمداً از این شمارش کنار گذاشته می‌شوند - پس چند تا از آن‌ها می‌تواند دلیل کمتر بودن این عدد از تعداد چک‌این‌هایی باشد که یادت هست انجام داده‌ای.",
      ar: "بعض أسئلة القائمة تحتاج عدة أيام من التاريخ، وحين لا تتوفر تقول بالضبط كم يوما صالحا وجدت بدل رسم اتجاه عبر نقطتين. ولاحظ أن الأيام التي وسمتها كاستثناءات تُستبعد عمدا من ذلك العدّ - فقد يكون بعضها سبب أن الرقم أقل من عدد التسجيلات التي تذكر أنك قمت بها.",
      zh: "有些菜单问题需要好几天的历史数据，当数据不足时，它会明确说出找到了多少天可用数据，而不是用两个点去画趋势。注意，你标记为例外的日子会被刻意排除在这个计数之外——所以其中几天可能就是这个数字比你记忆中打卡次数更少的原因。",
    },

    {
      key: 'app_weekly_plan_too_hard',
      match: /\b(the plan is too hard|plan tasks are unrealistic|cant do the weekly plan|plan asks too much)(?:s|es|ing)?\b|برنامه خیلی سخت است|کارهای برنامه غیرواقعی است|الخطة صعبة جدا|مهام الخطة غير واقعية|计划太难了|计划的任务不现实/i,
      en: "The plan is built in tiers from how far your weakest signals sit from their targets, so a plan that feels too hard usually means one field is a long way off and the plan is aiming at the gap rather than at your week. Nothing enforces it - checking tasks off is optional, partial weeks are normal, and next week's plan is regenerated from your newest prediction regardless of what you completed.",
      fa: "برنامه به‌صورت پلکانی از روی فاصله‌ی ضعیف‌ترین سیگنال‌هایت تا هدفشان ساخته می‌شود، پس برنامه‌ای که خیلی سخت به نظر می‌رسد معمولاً یعنی یک فیلد خیلی دور است و برنامه دارد آن فاصله را نشانه می‌گیرد نه هفته‌ی تو را. هیچ چیزی اجباری‌اش نمی‌کند - تیک‌زدن کارها اختیاری است، هفته‌های ناقص عادی‌اند، و برنامه‌ی هفته‌ی بعد صرف‌نظر از اینکه چه چیزی را تمام کرده‌ای از روی جدیدترین پیش‌بینی‌ات دوباره ساخته می‌شود.",
      ar: "تُبنى الخطة على مستويات من مدى بُعد أضعف إشاراتك عن أهدافها، فالخطة التي تبدو صعبة جدا تعني عادة أن حقلا واحدا بعيد جدا وأن الخطة تستهدف تلك الفجوة لا أسبوعك. ولا شيء يفرضها - فوضع علامات على المهام اختياري، والأسابيع الجزئية طبيعية، وخطة الأسبوع القادم تُولَّد من أحدث تنبؤ لك بغض النظر عمّا أنجزته.",
      zh: "计划是根据你最弱的几个信号距离其目标有多远，分层级生成的，所以一份感觉太难的计划，通常意味着某个字段偏离很远，而计划瞄准的是那个差距而不是你的一周。没有任何强制——勾选任务是可选的，完成一半很正常，下周的计划无论你完成了什么，都会根据你最新的预测重新生成。",
    },

    {
      key: 'app_weekly_plan_which_week',
      match: /\b(which week is my plan for|does the plan reset on monday|when does the plan week start)(?:s|es|ing)?\b|برنامه برای کدام هفته است|آیا برنامه دوشنبه ریست میشود|لأي أسبوع خطتي|هل تُعاد الخطة يوم الاثنين|计划是哪一周的|计划周一会重置吗/i,
      en: "Plan progress is stored per ISO week, which runs Monday to Sunday - so your checkmarks persist through reloads within that week and a new week starts a fresh set. The plan content itself is rebuilt from your most recent prediction whenever you open the page, so it tracks what's weakest now rather than what was weakest on Monday.",
      fa: "پیشرفت برنامه به‌ازای هر هفته‌ی ISO ذخیره می‌شود که از دوشنبه تا یکشنبه است - پس تیک‌هایت در همان هفته با بارگذاری دوباره باقی می‌مانند و هفته‌ی جدید مجموعه‌ای تازه شروع می‌کند. خودِ محتوای برنامه هر بار که صفحه را باز می‌کنی از روی جدیدترین پیش‌بینی‌ات دوباره ساخته می‌شود، پس چیزی را دنبال می‌کند که همین حالا ضعیف‌ترین است نه آنچه دوشنبه ضعیف‌ترین بود.",
      ar: "يُخزَّن تقدم الخطة لكل أسبوع ISO، ويمتد من الاثنين إلى الأحد - فتبقى علاماتك عبر إعادة التحميل ضمن ذلك الأسبوع، ويبدأ الأسبوع الجديد بمجموعة جديدة. أما محتوى الخطة نفسه فيُعاد بناؤه من أحدث تنبؤ لك كلما فتحت الصفحة، فيتتبع الأضعف الآن لا ما كان الأضعف يوم الاثنين.",
      zh: "计划进度按 ISO 周存储，从周一到周日——所以你的勾选在这一周内重新加载后仍然保留，新的一周会开始一组新的。计划内容本身则会在你每次打开页面时，根据你最新的预测重新生成，因此它跟踪的是现在最弱的项，而不是周一时最弱的项。",
    },

    {
      key: 'app_analytics_how_many_days_needed',
      match: /\b(how many days until analytics works|when will correlations appear|how much data for analytics)(?:s|es|ing)?\b|چند روز تا کار کردن تحلیل‌ها|همبستگی‌ها کی ظاهر میشوند|كم يوما حتى تعمل التحليلات|متى تظهر الارتباطات|多少天后分析才能用|相关性什么时候出现/i,
      en: "Different cards have different floors, which is why they appear one at a time rather than all at once. Roughly: a week gets you the narrative and basic weekly comparisons, and correlation cards need enough days that a relationship isn't just noise. A card staying hidden is it declining to speak, not a bug - the alternative would be a confident-looking pattern drawn from four points.",
      fa: "کارت‌های مختلف کف‌های متفاوتی دارند و برای همین یکی‌یکی ظاهر می‌شوند نه همه با هم. تقریباً: یک هفته روایت و مقایسه‌های هفتگی پایه را به تو می‌دهد، و کارت‌های همبستگی به آن‌قدر روز نیاز دارند که یک رابطه صرفاً نویز نباشد. پنهان‌ماندن یک کارت یعنی دارد از حرف‌زدن خودداری می‌کند، نه اینکه باگ باشد - جایگزینش یک الگوی به‌ظاهر مطمئن بود که از روی چهار نقطه کشیده شده.",
      ar: "لكل بطاقة حدّ أدنى مختلف، ولهذا تظهر واحدة تلو الأخرى لا دفعة واحدة. تقريبا: أسبوع يمنحك السرد والمقارنات الأسبوعية الأساسية، وبطاقات الارتباط تحتاج أياما كافية كي لا تكون العلاقة مجرد ضجيج. وبقاء بطاقة مخفية هو امتناعها عن الكلام لا خلل - فالبديل نمط يبدو واثقا مرسوم من أربع نقاط.",
      zh: "不同卡片有不同的数据下限，所以它们是逐个出现而不是一起出现的。大致来说：一周可以让叙述卡和基本的周对比出现，而相关性卡片需要足够多的天数，才能保证某个关系不只是噪声。卡片保持隐藏是它选择不发言，而不是 bug——另一种做法是用四个点画出一个看起来很有把握的模式。",
    },

    {
      key: 'app_analytics_export_chart',
      match: /\b(can i export the charts|save the analytics chart|download my analytics)(?:s|es|ing)?\b|میتوانم نمودارها را خروجی بگیرم|ذخیره نمودار تحلیل|هل يمكنني تصدير الرسوم البيانية|حفظ رسم التحليلات|能导出图表吗|保存分析图表/i,
      en: "There's no direct chart-image export. What you can export is a PDF report from any result page, which carries that day's score, class, factors and recommendations. For the underlying numbers, the per-day CSV export from a result gives you the raw values to chart yourself in a spreadsheet.",
      fa: "خروجی مستقیم تصویر نمودار وجود ندارد. چیزی که می‌توانی خروجی بگیری گزارش PDF از هر صفحه‌ی نتیجه است که امتیاز، دسته، عامل‌ها و پیشنهادهای همان روز را با خود می‌برد. برای عددهای زیربنایی هم، خروجی CSV به‌ازای هر روز از یک نتیجه، مقادیر خام را به تو می‌دهد تا خودت در یک صفحه‌گسترده نمودار بکشی.",
      ar: "لا يوجد تصدير مباشر لصورة الرسم البياني. ما يمكنك تصديره هو تقرير بي دي إف من أي صفحة نتيجة، يحمل درجة ذلك اليوم وفئته وعوامله وتوصياته. أما الأرقام الأساسية فيمنحك تصدير سي إس في لكل يوم من صفحة نتيجة القيم الخام لترسمها بنفسك في جدول بيانات.",
      zh: "没有直接的图表图片导出。你可以导出的是任意结果页的 PDF 报告，它包含那一天的分数、类别、影响因素和建议。至于底层数字，结果页的按天 CSV 导出会给你原始数值，你可以自己在电子表格里作图。",
    },

    {
      key: 'app_demo_which_profile_for_demo_video',
      match: /\b(best demo profile for a video|which demo shows the most|demo settings for a presentation|what demo should i use to show the app)(?:s|es|ing)?\b|بهترین پروفایل دمو برای ویدیو|کدام دمو بیشترین چیز را نشان میدهد|أفضل ملف تجريبي لفيديو|أي عرض تجريبي يُظهر الأكثر|录视频用哪个演示档案最好|哪个演示展示得最多/i,
      en: "For showing the app off, 23 days plus the borderline profile is the richest combination: 23 days is the only length that unlocks every history-dependent card, and borderline is the profile that actually wanders across a class boundary, so the seven-day class genuinely flips on camera rather than sitting still.",
      fa: "برای نشان‌دادن اپ، ۲۳ روز به‌همراه پروفایل مرزی غنی‌ترین ترکیب است: ۲۳ روز تنها طولی است که همه‌ی کارت‌های وابسته به تاریخچه را باز می‌کند، و «مرزی» همان پروفایلی است که واقعاً از یک مرز دسته‌بندی عبور می‌کند، پس دسته‌ی هفت‌روزه جلوی دوربین واقعاً عوض می‌شود نه اینکه ثابت بماند.",
      ar: "لعرض التطبيق، 23 يوما مع الملف الحدّي هو أغنى تركيبة: 23 يوما هو الطول الوحيد الذي يفتح كل البطاقات المعتمدة على التاريخ، والحدّي هو الملف الذي يتجول فعلا عبر حدّ فئة، فتنقلب فئة الأيام السبعة أمام الكاميرا حقا بدل أن تبقى ثابتة.",
      zh: "如果要展示这个应用，23 天加上「临界」档案是最丰富的组合：23 天是唯一能解锁所有依赖历史数据的卡片的长度，而「临界」正是那个真正会跨越类别边界的档案，所以七天类别会在镜头前真的发生翻转，而不是纹丝不动。",
    },

    {
      key: 'app_badges_private_ones',
      match: /\b(what are private badges|why is a badge private|hidden badges)(?:s|es|ing)?\b|نشان‌های خصوصی چیستند|چرا یک نشان خصوصی است|ما هي الأوسمة الخاصة|لماذا وسام خاص|私密徽章是什么|为什么徽章是私密的/i,
      en: "Some badges are marked private on purpose: they flag a pattern worth noticing about yourself rather than an achievement worth showing off. Making a late-night-usage indicator shareable would turn an awareness signal into something to compete over, which is exactly the wrong incentive, so those stay yours alone.",
      fa: "بعضی نشان‌ها عمداً خصوصی علامت‌گذاری شده‌اند: الگویی را نشان می‌دهند که ارزش توجه‌کردن به آن را درباره‌ی خودت داری، نه دستاوردی که ارزش پز دادن داشته باشد. اشتراک‌پذیر کردن یک نشانگرِ استفاده‌ی آخر شب، یک سیگنالِ آگاهی را به چیزی برای رقابت تبدیل می‌کرد که دقیقاً انگیزه‌ی اشتباهی است، پس آن‌ها فقط مال خودت می‌مانند.",
      ar: "بعض الأوسمة موسومة كخاصة عن قصد: فهي تشير إلى نمط يستحق أن تلاحظه في نفسك، لا إنجازا يستحق التباهي. وجعل مؤشر الاستخدام الليلي قابلا للمشاركة كان سيحوّل إشارة وعي إلى شيء يُتنافس عليه، وهذا بالضبط الحافز الخاطئ، فتبقى تلك لك وحدك.",
      zh: "有些徽章被刻意标记为私密：它们标示的是关于你自己、值得留意的某种模式，而不是值得炫耀的成就。把深夜使用的提示做成可分享的，会把一个自我觉察的信号变成竞争的对象，而这恰恰是错误的激励，所以那些徽章只属于你自己。",
    },

    {
      key: 'app_games_are_they_scored',
      match: /\b(do the games affect my score|does guessing wrong hurt me|are the games graded)(?:s|es|ing)?\b|آیا بازی‌ها روی امتیازم اثر دارند|اگر اشتباه حدس بزنم ضرر میکنم|هل تؤثر الألعاب على درجتي|هل يضرني التخمين الخطأ|游戏会影响我的分数吗|猜错了会有影响吗/i,
      en: "No - nothing you do in a game changes your score, your class, your history or your streak. They read your real data to build the question, but they only write back whether you played, never a result that feeds the model. Guessing wrong costs you nothing.",
      fa: "نه - هیچ کاری که در یک بازی بکنی امتیاز، دسته، تاریخچه یا زنجیره‌ی روزهایت را عوض نمی‌کند. بازی‌ها داده‌ی واقعی‌ات را می‌خوانند تا سؤال را بسازند، اما فقط این را برمی‌گردانند که بازی کرده‌ای یا نه، هرگز نتیجه‌ای که به مدل خورانده شود. اشتباه حدس‌زدن هیچ هزینه‌ای برایت ندارد.",
      ar: "لا - لا شيء تفعله في لعبة يغيّر درجتك أو فئتك أو سجلك أو تتابعك. فهي تقرأ بياناتك الحقيقية لبناء السؤال، لكنها لا تكتب سوى ما إذا كنت قد لعبت، ولا تكتب أبدا نتيجة تُغذّي النموذج. والتخمين الخاطئ لا يكلفك شيئا.",
      zh: "不会——你在游戏里做的任何事都不会改变你的分数、类别、历史记录或连续打卡天数。游戏会读取你的真实数据来出题，但它只回写你是否玩过，绝不会写入任何会喂给模型的结果。猜错没有任何代价。",
    },

    {
      key: 'app_future_letter_two_versions',
      match: /\b(why are there two letters|two versions of the future letter|which letter should i read)(?:s|es|ing)?\b|چرا دو نامه هست|دو نسخه از نامه آینده|لماذا هناك رسالتان|نسختان من رسالة المستقبل|为什么有两封信|未来信的两个版本/i,
      en: "The letter comes in two genuinely different versions built from the same real numbers - one from the future you get if the current pattern holds, one from the future you get if it changes. Both are assembled from your own score range, direction, best day, biggest-moving field and day count. Reading only the flattering one is the least useful way to use it.",
      fa: "نامه در دو نسخه‌ی واقعاً متفاوت می‌آید که از همان عددهای واقعی ساخته شده‌اند - یکی از آینده‌ای که اگر الگوی فعلی ادامه پیدا کند به آن می‌رسی، و یکی از آینده‌ای که اگر تغییر کند. هر دو از بازه‌ی امتیازت، جهتت، بهترین روزت، فیلدی که بیشترین جابه‌جایی را داشته و تعداد روزهایت سرهم می‌شوند. خواندن فقط آن نسخه‌ی خوشایند، کم‌فایده‌ترین راه استفاده از آن است.",
      ar: "تأتي الرسالة في نسختين مختلفتين فعلا مبنيتين على الأرقام الحقيقية نفسها - واحدة من المستقبل الذي تصل إليه إن استمر النمط الحالي، وأخرى من المستقبل الذي تصل إليه إن تغيّر. وكلتاهما تُجمَّع من مدى درجتك واتجاهك وأفضل يوم لديك والحقل الأكثر تحركا وعدد أيامك. وقراءة النسخة الملاطفة وحدها هي أقل الطرق فائدة في استخدامها.",
      zh: "这封信有两个真正不同的版本，都由同样的真实数据构建——一个来自当前模式延续下去所到达的未来，一个来自模式改变后所到达的未来。两者都是从你自己的分数区间、变化方向、最好的一天、变动最大的字段和记录天数拼装而成的。只读那封令人愉快的，是使用它最没有价值的方式。",
    },

    
    // ====== U. Trusting the model, and account/data edge cases ======
    {
      key: 'app_model_training_data',
      match: /\b(what data was the model trained on|where does the training data come from|how was the model trained|what is the model trained on)(?:s|es|ing)?\b|مدل روی چه داده‌ای آموزش دیده|داده آموزشی از کجا آمده|على أي بيانات دُرّب النموذج|من أين أتت بيانات التدريب|模型是用什么数据训练的|训练数据从哪来/i,
      en: "The models ship pre-trained on a dataset of daily digital-habit records, split into train/validation/test sets with the split done by user rather than by row - so no single person's days appear on both sides of the split, which would inflate the accuracy numbers. Your own check-ins are not used to retrain anything; they're only scored.",
      fa: "مدل‌ها از پیش روی یک مجموعه‌داده از ثبت‌های روزانه‌ی عادت‌های دیجیتال آموزش دیده‌اند که به بخش‌های آموزش/اعتبارسنجی/آزمون تقسیم شده، و تقسیم بر اساس کاربر انجام شده نه بر اساس ردیف - پس روزهای هیچ فردی در دو طرف تقسیم ظاهر نمی‌شوند، اتفاقی که عددهای دقت را به‌طور کاذب بالا می‌برد. چک‌این‌های خودت برای بازآموزی هیچ چیزی استفاده نمی‌شوند؛ فقط سنجیده می‌شوند.",
      ar: "النماذج تأتي مدرَّبة مسبقا على مجموعة بيانات من سجلات العادات الرقمية اليومية، مقسّمة إلى تدريب/تحقق/اختبار، والتقسيم تم حسب المستخدم لا حسب الصف - فلا تظهر أيام شخص واحد على جانبي التقسيم، وهو ما كان سيضخّم أرقام الدقة. أما تسجيلاتك أنت فلا تُستخدم لإعادة تدريب أي شيء؛ إنما تُقيَّم فقط.",
      zh: "模型是预先在一个每日数字习惯记录的数据集上训练好的，划分为训练/验证/测试集，并且是按用户而不是按行划分——这样同一个人的日子不会同时出现在划分的两边，否则会虚高准确率数字。你自己的打卡记录不会用于重新训练任何东西；它们只被用来评分。",
    },

    {
      key: 'app_model_accuracy_numbers',
      match: /\b(how accurate is the model|what is the model accuracy|how good is the prediction|can i see the model performance)(?:s|es|ing)?\b|مدل چقدر دقیق است|دقت مدل چقدر است|عملکرد مدل را ببینم|ما مدى دقة النموذج|ما هي دقة النموذج|أداء النموذج|模型有多准确|模型准确率是多少|能看模型性能吗/i,
      en: "There's a model-performance view in the app showing the real metrics from the held-out test set - not numbers typed into a slide. The honest framing: it's good at ranking days and spotting patterns for a person, and it is not a diagnostic instrument. Treat a single day's score as one reading, and the direction across days as the part worth acting on.",
      fa: "در اپ یک نمای عملکرد مدل هست که سنجه‌های واقعی روی مجموعه‌ی آزمونِ کنارگذاشته‌شده را نشان می‌دهد - نه عددهایی که در یک اسلاید تایپ شده باشند. قاب‌بندی صادقانه‌اش این است: در رتبه‌بندی روزها و دیدن الگو برای یک شخص خوب است، و یک ابزار تشخیص پزشکی نیست. امتیاز یک روز را یک قرائت در نظر بگیر، و جهت در طول روزها را همان بخشی که ارزش عمل‌کردن دارد.",
      ar: "يوجد في التطبيق عرض لأداء النموذج يُظهر المقاييس الحقيقية من مجموعة الاختبار المحجوزة - لا أرقاما مكتوبة في شريحة عرض. والصياغة الصادقة: إنه جيد في ترتيب الأيام ورصد الأنماط لشخص واحد، وليس أداة تشخيص طبي. اعتبر درجة يوم واحد قراءة واحدة، والاتجاه عبر الأيام هو الجزء الذي يستحق التصرف بناءً عليه.",
      zh: "应用里有一个模型性能视图，展示的是留出测试集上的真实指标——不是写在幻灯片上的数字。诚实的说法是：它擅长为一个人排序不同的日子、发现模式，但它不是诊断工具。把某一天的分数当作一次读数，而跨越多天的方向才是值得据以行动的部分。",
    },

    {
      key: 'app_model_can_it_be_wrong',
      match: /\b(can the model be wrong|what if the score is wrong|i disagree with my score|the score doesnt match how i feel)(?:s|es|ing)?\b|مدل میتواند اشتباه کند|با امتیازم موافق نیستم|امتیاز با حال من نمیخواند|هل يمكن أن يخطئ النموذج|لا أتفق مع درجتي|الدرجة لا تطابق شعوري|模型会出错吗|我不同意我的分数|分数和我的感受不符/i,
      en: "Yes, it can be wrong, and the app gives you two things to check rather than asking you to just accept it: the confidence number, which is low exactly when your inputs sit between classes, and the SHAP factors, which name which of your fields drove the result. If the factors look right but the verdict feels wrong, the score is probably reading something real that your mood that day isn't. If the factors themselves look wrong, check your inputs for that day.",
      fa: "بله، می‌تواند اشتباه کند، و اپ به‌جای اینکه بخواهد فقط قبولش کنی دو چیز برای چک‌کردن می‌دهد: عدد اطمینان، که دقیقاً وقتی ورودی‌هایت بین دو دسته قرار می‌گیرند پایین است، و عامل‌های SHAP که نام می‌برند کدام فیلدهایت نتیجه را ساخته‌اند. اگر عامل‌ها درست به نظر می‌رسند ولی حکم غلط حس می‌شود، احتمالاً امتیاز دارد چیز واقعی‌ای را می‌خواند که حال‌وهوای آن روزت نمی‌خواند. اگر خودِ عامل‌ها غلط به نظر می‌رسند، ورودی‌های آن روز را چک کن.",
      ar: "نعم، يمكن أن يخطئ، والتطبيق يمنحك شيئين للتحقق بدل أن يطلب منك قبوله فحسب: رقم الثقة، وهو منخفض تحديدا حين تقع مدخلاتك بين فئتين، وعوامل شاب التي تسمّي أي حقولك قاد النتيجة. فإن بدت العوامل صحيحة والحكم خاطئا في شعورك، فالأرجح أن الدرجة تقرأ شيئا حقيقيا لا يقرأه مزاجك ذلك اليوم. وإن بدت العوامل نفسها خاطئة، فراجع مدخلاتك لذلك اليوم.",
      zh: "会出错，而应用给了你两样可以核对的东西，而不是要求你直接接受：置信度数字，它恰恰在你的输入处于两个类别之间时会偏低；以及 SHAP 因素，它指出是你的哪些字段主导了结果。如果因素看起来是对的但结论感觉不对，那分数很可能读到了某种真实的东西，只是你那天的心情没读到。如果因素本身看起来就不对，那就检查那天的输入。",
    },

    {
      key: 'app_not_medical_advice',
      match: /\b(is this medical advice|can this diagnose me|is this a doctor|should i use this instead of a doctor)(?:s|es|ing)?\b|این توصیه پزشکی است|این میتواند تشخیص بدهد|به‌جای پزشک استفاده کنم|هل هذه نصيحة طبية|هل يمكن أن يشخّصني|أستخدمه بدل الطبيب|这是医疗建议吗|这能诊断我吗|可以用它代替医生吗/i,
      en: "No. This is a wellness-tracking tool built on a model trained to spot habit patterns, not a diagnostic instrument, and nothing here is medical advice or a substitute for a clinician. If something in your sleep, mood or functioning is genuinely worrying you, that's a conversation for a professional - the app's own data can be useful material to bring to it, but it is not the assessment.",
      fa: "نه. این یک ابزار پیگیری سلامت است که روی مدلی ساخته شده که برای دیدن الگوهای عادتی آموزش دیده، نه یک ابزار تشخیصی، و هیچ چیز اینجا توصیه‌ی پزشکی یا جایگزین یک درمانگر نیست. اگر چیزی در خواب، خلق‌وخو یا کارکردت واقعاً نگرانت کرده، این گفت‌وگویی برای یک متخصص است - داده‌ی خود اپ می‌تواند مادّه‌ی مفیدی باشد که با خودت ببری، اما خودش آن ارزیابی نیست.",
      ar: "لا. هذه أداة لتتبع العافية مبنية على نموذج مدرَّب على رصد أنماط العادات، لا أداة تشخيص، ولا شيء هنا نصيحة طبية أو بديل عن مختص. وإن كان شيء في نومك أو مزاجك أو أدائك يقلقك فعلا، فتلك محادثة تخص مختصا - وبيانات التطبيق نفسها قد تكون مادة مفيدة تصطحبها معك، لكنها ليست التقييم.",
      zh: "不是。这是一个健康追踪工具，建立在一个被训练来识别习惯模式的模型之上，它不是诊断工具，这里的任何内容都不是医疗建议，也不能替代临床专业人员。如果你的睡眠、情绪或日常功能中有什么真正让你担心，那是需要和专业人士谈的事——应用的数据可以作为有用的材料带过去，但它本身不是那个评估。",
    },

    {
      key: 'app_multiple_accounts',
      match: /\b(can i have two accounts|multiple accounts|separate account for work|can i make another account)(?:s|es|ing)?\b|میتوانم دو حساب داشته باشم|چند حساب|حساب جدا بسازم|هل يمكنني امتلاك حسابين|حسابات متعددة|حساب منفصل|我能有两个账户吗|多个账户|另建一个账户/i,
      en: "Nothing stops you registering more than one account, and it's the normal way to test the Friends League with yourself. Be aware they're completely separate: separate history, separate baseline, separate badges - a second account is a fresh start, not a second view of the same data, so don't split your real logging across two.",
      fa: "هیچ چیزی جلوی ثبت‌نام بیش از یک حساب را نمی‌گیرد و این روش عادی تست‌کردن لیگ دوستان با خودت است. حواست باشد که کاملاً جدا هستند: تاریخچه‌ی جدا، خط پایه‌ی جدا، نشان‌های جدا - حساب دوم یک شروع تازه است نه نمای دومی از همان داده، پس ثبت واقعی‌ات را بین دو حساب تقسیم نکن.",
      ar: "لا شيء يمنعك من تسجيل أكثر من حساب، وهي الطريقة المعتادة لاختبار دوري الأصدقاء مع نفسك. لكن انتبه أنهما منفصلان تماما: سجل منفصل، وخط أساس منفصل، وأوسمة منفصلة - فالحساب الثاني بداية جديدة لا عرض ثانٍ للبيانات نفسها، فلا توزّع تسجيلك الحقيقي بين اثنين.",
      zh: "没有任何限制阻止你注册多个账户，而且这是自己测试好友联赛的常规做法。但要注意它们是完全独立的：独立的历史、独立的基线、独立的徽章——第二个账户是全新的开始，不是同一份数据的第二个视图，所以不要把你真实的记录分散在两个账户里。",
    },

    {
      key: 'app_change_a_past_entry',
      match: /\b(can i edit a past check in|fix a mistake in an old entry|change a day i already submitted|i entered the wrong number)(?:s|es|ing)?\b|میتوانم چک‌این گذشته را ویرایش کنم|عدد اشتباه وارد کردم|روز ثبت‌شده را تغییر بدهم|هل يمكنني تعديل تسجيل سابق|أدخلت رقما خاطئا|تغيير يوم أرسلته|能修改过去的打卡吗|我填错了数字|更改已提交的某天/i,
      en: "Reopening a past day from history shows you exactly what that day was scored, replayed from what was saved rather than re-predicted. If a day is genuinely wrong, the cleanest options are to mark it as an exception so it stops affecting your averages, or to re-import a corrected row - a duplicate date is surfaced as a conflict rather than silently overwriting, so you'll know it happened.",
      fa: "بازکردن دوباره‌ی یک روز گذشته از تاریخچه دقیقاً نشانت می‌دهد آن روز چه امتیازی گرفته، بازپخش‌شده از آنچه ذخیره شده نه پیش‌بینی دوباره. اگر روزی واقعاً غلط است، تمیزترین گزینه‌ها این‌اند که استثنا علامتش بزنی تا دیگر روی میانگین‌هایت اثر نگذارد، یا یک ردیف اصلاح‌شده را دوباره وارد کنی - تاریخ تکراری به‌عنوان تعارض نشان داده می‌شود نه بازنویسی بی‌صدا، پس متوجه می‌شوی که اتفاق افتاده.",
      ar: "إعادة فتح يوم سابق من السجل تُظهر لك بالضبط الدرجة التي ناله ذلك اليوم، معادةً من المحفوظ لا معاد التنبؤ بها. وإن كان يوم ما خاطئا فعلا، فأنظف الخيارات أن تسمه كاستثناء فيتوقف تأثيره على متوسطاتك، أو أن تستورد صفا مصححا - والتاريخ المكرر يظهر كتعارض لا كاستبدال صامت، فتعرف أنه حدث.",
      zh: "从历史里重新打开过去的某一天，会准确显示那天得到的分数，是从保存的内容回放的，而不是重新预测。如果某一天确实错了，最干净的做法是把它标记为例外日，让它不再影响你的平均值；或者重新导入一行修正过的数据——重复日期会作为冲突提示出来，而不是悄悄覆盖，所以你会知道发生了什么。",
    },

    {
      key: 'app_what_happens_if_i_skip_days',
      match: /\b(what if i skip a few days|i missed a week|does skipping days break anything|coming back after a break)(?:s|es|ing)?\b|اگر چند روز را رد کنم چه|یک هفته را از دست دادم|بعد از وقفه برگردم|ماذا لو تخطيت بضعة أيام|فاتني أسبوع|العودة بعد انقطاع|跳过几天会怎样|我漏了一周|中断后回来/i,
      en: "Nothing breaks. Skipped days simply aren't there - the app never invents a value for a day you didn't log. Your streak shortens, and history-dependent cards use whatever real days exist. Coming back after a gap is completely normal; the trend just picks up from the days you actually have.",
      fa: "هیچ چیزی خراب نمی‌شود. روزهای ردشده صرفاً وجود ندارند - اپ هرگز برای روزی که ثبت نکرده‌ای مقداری از خودش نمی‌سازد. زنجیره‌ات کوتاه می‌شود و کارت‌های وابسته به تاریخچه از هر روز واقعی‌ای که هست استفاده می‌کنند. برگشتن بعد از یک وقفه کاملاً عادی است؛ روند فقط از روزهایی که واقعاً داری ادامه پیدا می‌کند.",
      ar: "لا شيء ينكسر. الأيام المتخطاة ببساطة غير موجودة - فالتطبيق لا يخترع أبدا قيمة ليوم لم تسجّله. يقصر تتابعك، وتستخدم البطاقات المعتمدة على التاريخ ما يوجد فعلا من أيام. والعودة بعد فجوة أمر طبيعي تماما؛ والاتجاه يلتقط ببساطة من الأيام التي لديك فعلا.",
      zh: "什么都不会坏。跳过的日子就是不存在——应用绝不会为你没记录的一天编造数值。你的连续天数会缩短，依赖历史的卡片会使用实际存在的那些天。中断后回来完全正常；趋势只是从你真正拥有的那些天接着算。",
    },

    {
      key: 'app_data_after_deletion',
      match: /\b(what happens to my data if i delete my account|is deletion permanent|can i undo account deletion|can i get my data back after deleting)(?:s|es|ing)?\b|اگر حسابم را حذف کنم داده‌ها چه میشوند|حذف دائمی است|میتوانم حذف را برگردانم|ماذا يحدث لبياناتي إن حذفت حسابي|هل الحذف دائم|هل يمكنني التراجع عن الحذف|删除账户后数据会怎样|删除是永久的吗|能撤销删除吗/i,
      en: "Deletion is real and permanent, not deactivation - check-ins, League connections, chat messages and badges go with it, and there's no undo and no recovery window. That's why there's a confirmation step. If you want a copy of anything first, export it before you delete, because afterwards there is nothing left to export.",
      fa: "حذف واقعی و دائمی است، نه غیرفعال‌سازی - چک‌این‌ها، ارتباط‌های لیگ، پیام‌های چت و نشان‌ها همه با آن می‌روند، و نه بازگردانی هست نه پنجره‌ی بازیابی. برای همین یک مرحله‌ی تأیید وجود دارد. اگر می‌خواهی اول از چیزی نسخه‌ای داشته باشی، قبل از حذف خروجی بگیر، چون بعدش دیگر چیزی برای خروجی‌گرفتن نمانده.",
      ar: "الحذف حقيقي ودائم لا تعطيل - فالتسجيلات واتصالات الدوري ورسائل المحادثة والأوسمة تذهب معه، ولا تراجع ولا نافذة استرجاع. ولهذا توجد خطوة تأكيد. وإن أردت نسخة من أي شيء أولا، فصدّرها قبل الحذف، لأنه بعده لا يبقى شيء لتصديره.",
      zh: "删除是真实且永久的，不是停用——打卡记录、联赛连接、聊天消息和徽章都会随之消失，没有撤销，也没有恢复窗口。这就是为什么有一个确认步骤。如果你想先留一份副本，请在删除之前导出，因为删除之后就没有任何东西可以导出了。",
    },

    
    // ====== V. First-time use, effort, cost and what the app can/cannot see ======
    {
      key: 'app_first_time_what_do_i_do',
      match: /\b(im new what do i do|how do i start|what should i do first|getting started)(?:s|es|ing)?\b|تازه واردم چه کار کنم|چطور شروع کنم|اول چه کار کنم|أنا جديد ماذا أفعل|كيف أبدأ|ماذا أفعل أولا|我是新用户该做什么|怎么开始|第一步做什么/i,
      en: "Do one check-in for today - that's the whole first step, and it takes a couple of minutes. You'll get a real score with your own top factors immediately. Everything else (weekly plan, analytics, the coach's data questions, the League) builds on having check-ins, so the useful next move is just logging a few more days rather than exploring every page first.",
      fa: "برای امروز یک چک‌این انجام بده - کل قدم اول همین است و چند دقیقه طول می‌کشد. بلافاصله یک امتیاز واقعی همراه با عامل‌های اصلی خودت می‌گیری. بقیه‌ی چیزها (برنامه‌ی هفتگی، تحلیل‌ها، سؤال‌های داده‌ای مربی، لیگ) روی داشتن چک‌این ساخته می‌شوند، پس حرکت مفید بعدی صرفاً ثبت چند روز دیگر است نه گشتن در همه‌ی صفحه‌ها.",
      ar: "سجّل تسجيلا واحدا لليوم - هذه هي الخطوة الأولى كاملة، وتستغرق دقيقتين. ستحصل فورا على درجة حقيقية مع عواملك الرئيسية. وكل ما عداها (الخطة الأسبوعية، التحليلات، أسئلة المدرب عن بياناتك، الدوري) مبني على وجود تسجيلات، فالخطوة المفيدة التالية هي ببساطة تسجيل بضعة أيام أخرى لا تصفح كل الصفحات أولا.",
      zh: "先为今天做一次打卡——这就是全部的第一步，只需要几分钟。你会立刻得到一个真实的分数以及属于你自己的主要影响因素。其余的一切（每周计划、分析、教练的数据类问题、好友联赛）都建立在有打卡记录的基础上，所以有用的下一步就是再多记录几天，而不是先把每个页面都逛一遍。",
    },

    {
      key: 'app_how_long_does_checkin_take',
      match: /\b(how long does a check in take|how much time does this take|is it quick to fill in)(?:s|es|ing)?\b|چک‌این چقدر طول میکشد|چقدر وقت میگیرد|كم يستغرق التسجيل|كم من الوقت يأخذ|打卡要多久|这要花多少时间/i,
      en: "A couple of minutes once you know where your phone reports its screen-time numbers - most of the form is copying those across, and the subjective ratings are quick judgements rather than things to agonize over. It gets faster after the first few days because you learn your own typical values.",
      fa: "وقتی بدانی گوشی‌ات عددهای زمان صفحه را کجا گزارش می‌دهد، چند دقیقه - بیشتر فرم همان کپی‌کردن آن‌هاست، و نمره‌های ذهنی قضاوت‌های سریع‌اند نه چیزهایی که رویشان کلنجار بروی. بعد از چند روز اول سریع‌تر هم می‌شود چون مقدارهای معمول خودت را یاد می‌گیری.",
      ar: "دقيقتان بمجرد أن تعرف أين يعرض هاتفك أرقام وقت الشاشة - فمعظم النموذج نقل لتلك الأرقام، والتقييمات الذاتية أحكام سريعة لا أمور تُعذّب نفسك بها. ويصبح أسرع بعد الأيام الأولى لأنك تتعلم قيمك المعتادة.",
      zh: "一旦你知道手机在哪里显示屏幕使用时间的数字，就只需要几分钟——表单的大部分就是把那些数字抄过来，主观评分是快速判断，不需要纠结。头几天之后会更快，因为你会熟悉自己的典型数值。",
    },

    {
      key: 'app_best_time_to_check_in',
      match: /\b(when should i check in|what time of day to log|should i check in at night or morning)(?:s|es|ing)?\b|کی چک‌این کنم|چه ساعتی ثبت کنم|شب ثبت کنم یا صبح|متى أسجّل|في أي وقت من اليوم|أسجّل ليلا أم صباحا|什么时候打卡|一天中什么时间记录|晚上还是早上记录/i,
      en: "End of day is the natural fit, since you're describing a day that has already happened and your phone's screen-time numbers are complete by then. What matters more than the hour is picking one and staying with it - logging some days at noon and others at midnight quietly changes what 'a day' means in your own series.",
      fa: "پایان روز طبیعی‌ترین حالت است، چون داری روزی را توصیف می‌کنی که قبلاً اتفاق افتاده و عددهای زمان صفحه‌ی گوشی‌ات تا آن موقع کامل شده‌اند. چیزی که از خودِ ساعت مهم‌تر است این است که یکی را انتخاب کنی و پایش بمانی - ثبت بعضی روزها ظهر و بعضی نیمه‌شب، بی‌سروصدا معنای «یک روز» را در سری خودت عوض می‌کند.",
      ar: "نهاية اليوم هي الأنسب طبيعيا، لأنك تصف يوما وقع بالفعل وأرقام وقت الشاشة في هاتفك تكون قد اكتملت. والأهم من الساعة نفسها أن تختار واحدة وتلتزم بها - فتسجيل بعض الأيام ظهرا وأخرى منتصف الليل يغيّر بهدوء معنى «اليوم» في سلسلتك أنت.",
      zh: "一天结束时最自然，因为你描述的是一个已经发生的日子，而那时手机的屏幕使用时间数据也已经完整了。比具体几点更重要的是选定一个时间并坚持——有些天中午记录、有些天半夜记录，会悄悄改变「一天」在你自己这组数据里的含义。",
    },

    {
      key: 'app_why_so_many_questions',
      match: /\b(why are there so many questions|why does it ask so much|too many fields in the form)(?:s|es|ing)?\b|چرا این همه سوال هست|چرا این قدر میپرسد|فیلدهای فرم زیاد است|لماذا كل هذه الأسئلة|لماذا يسأل كثيرا|حقول النموذج كثيرة|为什么问题这么多|为什么问这么多|表单字段太多了/i,
      en: "Because the explanation depends on it. A model given three inputs can only ever tell you one of three things is your problem; the reason your result names a specific field and shows how much it moved your score is that it had enough separate signals to distinguish them. Many of the fields are also derived automatically rather than asked - the form is shorter than the feature list.",
      fa: "چون توضیح به آن وابسته است. مدلی که سه ورودی بگیرد فقط می‌تواند بگوید یکی از آن سه مشکل توست؛ دلیل اینکه نتیجه‌ات یک فیلد مشخص را نام می‌برد و نشان می‌دهد چقدر امتیازت را جابه‌جا کرده این است که به‌اندازه‌ی کافی سیگنالِ جدا داشته تا تفکیکشان کند. ضمناً خیلی از فیلدها به‌جای پرسیده‌شدن به‌طور خودکار مشتق می‌شوند - فرم از فهرست ویژگی‌ها کوتاه‌تر است.",
      ar: "لأن التفسير يعتمد عليها. النموذج الذي يُعطى ثلاثة مدخلات لا يستطيع إلا أن يخبرك أن واحدا من ثلاثة هو مشكلتك؛ وسبب أن نتيجتك تسمّي حقلا محددا وتُظهر كم حرّك درجتك هو أنها امتلكت إشارات منفصلة كافية للتمييز بينها. كما أن كثيرا من الحقول تُشتق تلقائيا بدل أن تُسأل - فالنموذج أقصر من قائمة الخصائص.",
      zh: "因为解释能力取决于它们。一个只有三个输入的模型，最多只能告诉你问题出在这三者之一；你的结果之所以能指名某个具体字段、并显示它把分数推动了多少，是因为它有足够多彼此独立的信号来加以区分。而且很多字段是自动推导的而非询问的——表单比特征列表要短。",
    },

    {
      key: 'app_is_it_free',
      match: /\b(is this free|does it cost anything|do i need to pay|is there a subscription)(?:s|es|ing)?\b|این رایگان است|هزینه دارد|باید پول بدهم|هل هذا مجاني|هل يكلف شيئا|هل أحتاج للدفع|这是免费的吗|要收费吗|需要付费吗/i,
      en: "There's no payment, subscription or paywall anywhere in the app - every feature described here is available without paying. The one thing that can cost money is entirely outside the app: if you choose to turn on the optional bring-your-own-key connector, you're billed by that AI provider directly, on your own account, and the app never handles it.",
      fa: "هیچ پرداخت، اشتراک یا دیوار پولی در هیچ‌جای اپ نیست - همه‌ی قابلیت‌هایی که اینجا توصیف شده بدون پرداخت در دسترس‌اند. تنها چیزی که می‌تواند هزینه داشته باشد کاملاً بیرون از اپ است: اگر انتخاب کنی که کانکتور اختیاریِ «کلید خودت را بیاور» را روشن کنی، همان ارائه‌دهنده‌ی هوش مصنوعی مستقیماً روی حساب خودت از تو هزینه می‌گیرد و اپ اصلاً دستی در آن ندارد.",
      ar: "لا يوجد دفع ولا اشتراك ولا جدار دفع في أي مكان من التطبيق - فكل الميزات الموصوفة هنا متاحة دون دفع. والشيء الوحيد الذي قد يكلف مالا يقع خارج التطبيق تماما: إن اخترت تشغيل موصّل «أحضر مفتاحك» الاختياري، فمزوّد الذكاء الاصطناعي ذاك يحاسبك مباشرة على حسابك أنت، والتطبيق لا يتدخل في ذلك أبدا.",
      zh: "应用里没有任何付费、订阅或付费墙——这里描述的每一项功能都无需付费即可使用。唯一可能产生费用的事情完全在应用之外：如果你选择开启可选的「自带密钥」连接器，那家 AI 服务商会直接向你自己的账户计费，应用完全不经手。",
    },

    {
      key: 'app_does_it_track_me_automatically',
      match: /\b(does it track my phone automatically|does it read my screen time by itself|does it monitor my apps|does it run in the background)(?:s|es|ing)?\b|آیا خودکار گوشی من را ردیابی میکند|خودش زمان صفحه را میخواند|در پس‌زمینه اجرا میشود|هل يتتبع هاتفي تلقائيا|هل يقرأ وقت شاشتي بنفسه|هل يعمل في الخلفية|它会自动追踪我的手机吗|它会自己读取屏幕时间吗|会在后台运行吗/i,
      en: "No, and it can't. It's a web page in your browser with no device permissions, no background process and no access to your usage statistics - every number it has is one you typed in yourself. That's a real limitation (you do the typing) and a real privacy property (nothing is collected without you deciding to enter it).",
      fa: "نه، و نمی‌تواند. این یک صفحه‌ی وب در مرورگر توست بدون هیچ مجوز دستگاهی، بدون پردازش پس‌زمینه و بدون دسترسی به آمار استفاده‌ات - هر عددی که دارد همانی است که خودت تایپ کرده‌ای. این هم یک محدودیت واقعی است (تایپش با توست) و هم یک ویژگی واقعیِ حریم خصوصی (هیچ چیزی بدون اینکه خودت تصمیم بگیری واردش کنی جمع‌آوری نمی‌شود).",
      ar: "لا، ولا يستطيع. إنه صفحة ويب في متصفحك بلا أذونات جهاز، وبلا عملية في الخلفية، وبلا وصول إلى إحصاءات استخدامك - فكل رقم لديه هو رقم كتبته أنت. وهذا قيد حقيقي (الكتابة عليك) وخاصية خصوصية حقيقية (لا يُجمع شيء دون أن تقرر أنت إدخاله).",
      zh: "不会，也做不到。它是你浏览器里的一个网页，没有任何设备权限、没有后台进程、也无法访问你的使用统计——它拥有的每一个数字都是你自己输入的。这既是一个真实的局限（需要你自己填写），也是一个真实的隐私特性（没有你主动输入，什么都不会被收集）。",
    },

    {
      key: 'app_who_can_see_my_answers',
      match: /\b(who can see my answers|can anyone else see my check ins|is my data visible to others)(?:s|es|ing)?\b|چه کسی پاسخ‌های من را میبیند|کسی چک‌این‌های من را میبیند|من يستطيع رؤية إجاباتي|هل يرى أحد تسجيلاتي|谁能看到我的答案|别人能看到我的打卡吗/i,
      en: "Your check-ins are tied to your account and nobody else's account can read them. The only way anything about your data reaches another person is the Friends League, where you pick which of four categories (persona, score, rank, top factor) a specific connected friend sees - never the raw check-in - and you can revoke any of it later.",
      fa: "چک‌این‌هایت به حساب خودت گره خورده‌اند و هیچ حساب دیگری نمی‌تواند آن‌ها را بخواند. تنها راهی که چیزی از داده‌ات به شخص دیگری می‌رسد لیگ دوستان است، جایی که انتخاب می‌کنی یک دوستِ متصلِ مشخص کدام‌یک از چهار دسته (پرسونا، امتیاز، رتبه، عامل اصلی) را ببیند - هرگز خودِ چک‌این خام را - و بعداً هم می‌توانی هرکدام را پس بگیری.",
      ar: "تسجيلاتك مرتبطة بحسابك ولا يستطيع أي حساب آخر قراءتها. والسبيل الوحيد لوصول شيء من بياناتك إلى شخص آخر هو دوري الأصدقاء، حيث تختار أيّ الفئات الأربع (الشخصية، الدرجة، الترتيب، العامل الرئيسي) يراها صديق متصل بعينه - لا التسجيل الخام أبدا - ويمكنك سحب أي منها لاحقا.",
      zh: "你的打卡记录与你的账户绑定，其他任何账户都无法读取。你的数据能触及另一个人的唯一途径是好友联赛：你可以选择某位已连接的好友能看到四个类别中的哪些（画像、分数、排名、主要因素）——绝不会是原始打卡内容——而且之后随时可以撤回其中任何一项。",
    },

    
    // ====== W. Every page, and every game explained ======
    {
      key: 'app_page_dashboard',
      match: /\b(what is the dashboard page|what is on the dashboard page|dashboard page)(?:s|es|ing)?\b|صفحه داشبورد چیست|صفحه داشبورد|ما هي صفحة لوحة التحكم|صفحة لوحة التحكم|仪表盘页面是什么|仪表盘页面/i,
      en: "The dashboard is the one-glance summary: your latest score, current streak, recent trend and shortcuts into the deeper pages. Everything on it traces back to your most recent real prediction - it computes nothing new of its own.",
      fa: "داشبورد خلاصه‌ی یک‌نگاهی است: آخرین امتیازت، زنجیره‌ی فعلی، روند اخیر و میان‌برها به صفحه‌های عمیق‌تر. هر چیزی روی آن به آخرین پیش‌بینی واقعی‌ات برمی‌گردد - خودش هیچ چیز تازه‌ای حساب نمی‌کند.",
      ar: "لوحة التحكم هي الملخص السريع: آخر درجة لك، وتتابعك الحالي، واتجاهك الأخير، واختصارات إلى الصفحات الأعمق. وكل ما فيها يعود إلى آخر تنبؤ حقيقي لك - فهي لا تحسب شيئا جديدا بنفسها.",
      zh: "仪表盘是一眼看全的摘要：你最新的分数、当前连续天数、近期趋势，以及通往各深入页面的快捷入口。上面的一切都追溯到你最近一次真实预测——它本身不做任何新的计算。",
    },

    {
      key: 'app_page_analytics',
      match: /\b(what is the analytics page|what is on the analytics page|analytics page)(?:s|es|ing)?\b|صفحه تحلیل‌ها چیست|صفحه تحلیل|ما هي صفحة التحليلات|صفحة التحليلات|分析页面是什么|分析页面/i,
      en: "Analytics is where multi-day patterns live: correlation cards, weekly comparisons, risk alerts, weekly challenges and the letter from your future self. Almost everything here needs several real days before it appears, and stays hidden rather than showing a pattern drawn from too few points.",
      fa: "تحلیل‌ها جایی است که الگوهای چندروزه زندگی می‌کنند: کارت‌های همبستگی، مقایسه‌های هفتگی، هشدارهای خطر، چالش‌های هفتگی و نامه‌ای از خودِ آینده‌ات. تقریباً همه‌چیز اینجا پیش از ظاهرشدن به چند روز واقعی نیاز دارد و به‌جای نشان‌دادن الگویی که از نقاط خیلی کم کشیده شده، پنهان می‌ماند.",
      ar: "التحليلات هي المكان الذي تعيش فيه الأنماط متعددة الأيام: بطاقات الارتباط، والمقارنات الأسبوعية، وتنبيهات الخطر، والتحديات الأسبوعية، ورسالة من نفسك المستقبلية. وكل شيء تقريبا هنا يحتاج عدة أيام حقيقية قبل أن يظهر، ويبقى مخفيا بدل عرض نمط مرسوم من نقاط قليلة جدا.",
      zh: "分析页是多天模式所在的地方：相关性卡片、周对比、风险提醒、每周挑战，以及来自未来自己的信。这里几乎所有内容都需要好几天的真实数据才会出现，而不会用太少的点画出一个模式硬要展示。",
    },

    {
      key: 'app_page_weekly',
      match: /\b(what is the weekly page|weekly plan page|what is on the weekly page)(?:s|es|ing)?\b|صفحه هفتگی چیست|صفحه برنامه هفتگی|ما هي الصفحة الأسبوعية|صفحة الخطة الأسبوعية|每周页面是什么|每周计划页面/i,
      en: "The weekly page holds your seven-day plan, built from your latest prediction's weakest signals, with checkable tasks per day and focus-area chips at the top naming exactly which signals it targeted.",
      fa: "صفحه‌ی هفتگی برنامه‌ی هفت‌روزه‌ات را نگه می‌دارد که از ضعیف‌ترین سیگنال‌های آخرین پیش‌بینی‌ات ساخته شده، با وظیفه‌های قابل‌تیک برای هر روز و چیپ‌های حوزه‌ی تمرکز در بالا که دقیقاً نام می‌برند کدام سیگنال‌ها را هدف گرفته.",
      ar: "تحتوي الصفحة الأسبوعية على خطتك لسبعة أيام، المبنية من أضعف إشارات آخر تنبؤ لك، مع مهام قابلة للتأشير لكل يوم وشرائح مجالات التركيز في الأعلى تسمّي بالضبط أي الإشارات استهدفت.",
      zh: "每周页面放的是你的七天计划，它由你最新预测中最弱的信号构建，每天都有可勾选的任务，顶部的重点领域标签会明确指出它针对的是哪些信号。",
    },

    {
      key: 'app_page_league',
      match: /\b(what is the league page|friends league page|what is on the league page)(?:s|es|ing)?\b|صفحه لیگ چیست|صفحه لیگ دوستان|ما هي صفحة الدوري|صفحة دوري الأصدقاء|联赛页面是什么|好友联赛页面/i,
      en: "The League page is where your invite code, your pending requests, your connected friends, the ranking and the chats all live. Nothing on it works with one account alone - it is genuinely two-sided by design.",
      fa: "صفحه‌ی لیگ جایی است که کد دعوتت، درخواست‌های در انتظار، دوستان متصل، رتبه‌بندی و چت‌ها همه آنجا هستند. هیچ چیزش با یک حساب تنها کار نمی‌کند - از روی طراحی واقعاً دوطرفه است.",
      ar: "صفحة الدوري هي حيث يوجد رمز دعوتك، وطلباتك المعلقة، وأصدقاؤك المتصلون، والترتيب، والمحادثات. ولا شيء فيها يعمل بحساب واحد فقط - فهي ثنائية الطرف بالتصميم فعلا.",
      zh: "联赛页面是你的邀请码、待处理请求、已连接好友、排名和聊天所在的地方。它上面没有任何功能能靠单个账户运作——按设计它就是真正双向的。",
    },

    {
      key: 'app_page_model_performance',
      match: /\b(what is the model performance page|model page|where do i see model metrics)(?:s|es|ing)?\b|صفحه عملکرد مدل چیست|صفحه مدل|ما هي صفحة أداء النموذج|صفحة النموذج|模型性能页面是什么|模型页面/i,
      en: "The model-performance page shows the real metrics from the held-out test set the models were never trained on - the honest numbers behind every prediction the app makes, rather than a marketing claim about accuracy.",
      fa: "صفحه‌ی عملکرد مدل، سنجه‌های واقعی روی همان مجموعه‌ی آزمونِ کنارگذاشته‌شده را نشان می‌دهد که مدل‌ها هرگز رویش آموزش ندیده‌اند - عددهای صادقانه‌ی پشت هر پیش‌بینی‌ای که اپ می‌کند، نه یک ادعای تبلیغاتی درباره‌ی دقت.",
      ar: "تعرض صفحة أداء النموذج المقاييس الحقيقية من مجموعة الاختبار المحجوزة التي لم تُدرَّب عليها النماذج قط - الأرقام الصادقة خلف كل تنبؤ يقدمه التطبيق، لا ادعاء تسويقيا عن الدقة.",
      zh: "模型性能页面展示的是留出测试集上的真实指标，模型从未在这些数据上训练过——这是应用每次预测背后的诚实数字，而不是关于准确率的营销说辞。",
    },

    {
      key: 'app_page_hall_of_fame',
      match: /\b(what is the hall of fame|hall of fame page|what is hall page)(?:s|es|ing)?\b|تالار افتخارات چیست|صفحه تالار مشاهیر|ما هي قاعة المشاهير|صفحة قاعة المشاهير|名人堂是什么|名人堂页面/i,
      en: "The Hall of Fame collects your earned badges and milestones in one place. Badges are computed from your real history rather than awarded manually, and the ones marked private stay visible only to you.",
      fa: "تالار افتخارات نشان‌ها و نقاط عطف کسب‌شده‌ات را یکجا جمع می‌کند. نشان‌ها از تاریخچه‌ی واقعی‌ات محاسبه می‌شوند نه دستی داده شوند، و آن‌هایی که خصوصی علامت خورده‌اند فقط برای خودت دیده می‌شوند.",
      ar: "تجمع قاعة المشاهير أوسمتك ومحطاتك المكتسبة في مكان واحد. والأوسمة تُحسب من تاريخك الحقيقي لا تُمنح يدويا، وتلك الموسومة كخاصة تبقى مرئية لك وحدك.",
      zh: "名人堂把你获得的徽章和里程碑集中在一处。徽章是从你的真实历史计算得出的，而不是人工授予的，被标记为私密的那些只有你自己能看到。",
    },

    {
      key: 'app_page_profile',
      match: /\b(what is the profile page|profile page|what is on my profile)(?:s|es|ing)?\b|صفحه پروفایل چیست|صفحه پروفایل|ما هي صفحة الملف الشخصي|صفحة الملف الشخصي|个人资料页是什么|资料页面/i,
      en: "Your profile holds the onboarding answers that describe you rather than a single day - things like your main platform, device and purpose - plus your display name and badge previews. These are context, not daily inputs.",
      fa: "پروفایلت پاسخ‌های آغازینی را نگه می‌دارد که تو را توصیف می‌کنند نه یک روز خاص - چیزهایی مثل پلتفرم اصلی‌ات، دستگاه و هدفت - به‌علاوه نام نمایشی و پیش‌نمایش نشان‌ها. این‌ها بافت‌اند، نه ورودی‌های روزانه.",
      ar: "يحتفظ ملفك الشخصي بإجابات التهيئة التي تصفك أنت لا يوما بعينه - كمنصتك الأساسية وجهازك وغرضك - إضافة إلى اسم العرض ومعاينات الأوسمة. وهذه سياق، لا مدخلات يومية.",
      zh: "个人资料页保存的是描述「你这个人」而非某一天的引导问题答案——比如你的主要平台、设备和使用目的——以及显示名称和徽章预览。这些是背景信息，不是每日输入。",
    },

    {
      key: 'app_page_about',
      match: /\b(what is the about page|about page|where is the project info)(?:s|es|ing)?\b|صفحه درباره چیست|صفحه درباره ما|ما هي صفحة حول|صفحة حول التطبيق|关于页面是什么|关于页/i,
      en: "The About page explains what the project is, how the models work and what the app deliberately does not claim to be. If you want the honest scope statement rather than the feature list, that's where it is.",
      fa: "صفحه‌ی درباره توضیح می‌دهد این پروژه چیست، مدل‌ها چطور کار می‌کنند و اپ عمداً ادعای چه چیزی را ندارد. اگر به‌جای فهرست قابلیت‌ها بیانیه‌ی صادقانه‌ی دامنه را می‌خواهی، همان‌جاست.",
      ar: "تشرح صفحة «حول» ماهية المشروع، وكيف تعمل النماذج، وما الذي لا يدّعيه التطبيق عن قصد. وإن أردت بيان النطاق الصادق بدل قائمة الميزات، فهو هناك.",
      zh: "关于页面解释了这个项目是什么、模型如何运作，以及应用刻意不宣称自己是什么。如果你想要的是诚实的范围说明而不是功能清单，就在那里。",
    },

    {
      key: 'app_game_guess_score',
      match: /\b(guess the score game|guess my score game)(?:s|es|ing)?\b|بازی حدس امتیاز|لعبة تخمين الدرجة|猜分数游戏/i,
      en: "You guess your wellness score before it's revealed, then see how close you were. It runs BEFORE the result on purpose - guessing a number you've already seen would be meaningless.",
      fa: "قبل از آنکه امتیاز سلامتت نشان داده شود حدسش می‌زنی و بعد می‌بینی چقدر نزدیک بودی. عمداً پیش از نتیجه اجرا می‌شود - حدس‌زدن عددی که قبلاً دیده‌ای بی‌معنا بود.",
      ar: "تخمّن درجة عافيتك قبل الكشف عنها، ثم ترى كم كنت قريبا. وتُشغَّل قبل النتيجة عن قصد - فتخمين رقم رأيته سلفا بلا معنى.",
      zh: "你在健康分数揭晓之前先猜一个，然后看看猜得有多接近。它刻意安排在结果之前——去猜一个你已经看过的数字毫无意义。",
    },

    {
      key: 'app_game_which_factor',
      match: /\b(which factor game|which factor mattered more)(?:s|es|ing)?\b|بازی کدام عامل|لعبة أي عامل|哪个因素游戏/i,
      en: "You pick which of two of your own real SHAP factors pushed your score more, then see the actual values. It runs after the result, since it's built from that day's real explanation.",
      fa: "انتخاب می‌کنی کدام‌یک از دو عامل SHAP واقعی خودت امتیازت را بیشتر جابه‌جا کرده، بعد مقادیر واقعی را می‌بینی. بعد از نتیجه اجرا می‌شود، چون از توضیح واقعی همان روز ساخته شده.",
      ar: "تختار أي عاملَي شاب الحقيقيين لديك دفع درجتك أكثر، ثم ترى القيم الفعلية. وتُشغَّل بعد النتيجة لأنها مبنية على تفسير ذلك اليوم الحقيقي.",
      zh: "你从自己真实的两个 SHAP 因素中挑出哪一个对分数的推动更大，然后看到实际数值。它在结果之后运行，因为它是由那一天真实的解释构建的。",
    },

    {
      key: 'app_game_confidence_guess',
      match: /\b(confidence guess game|guess the confidence)(?:s|es|ing)?\b|بازی حدس اطمینان|لعبة تخمين الثقة|猜置信度游戏/i,
      en: "You estimate how confident the model was before seeing the number. Like the score guess, it runs before the result - it reveals a value you haven't been shown yet.",
      fa: "تخمین می‌زنی مدل چقدر مطمئن بوده، پیش از دیدن عدد. مثل حدس امتیاز، پیش از نتیجه اجرا می‌شود - مقداری را فاش می‌کند که هنوز نشانت نداده‌اند.",
      ar: "تقدّر مدى ثقة النموذج قبل رؤية الرقم. ومثل تخمين الدرجة، تُشغَّل قبل النتيجة - فهي تكشف قيمة لم تُعرض عليك بعد.",
      zh: "你在看到数字之前先估计模型有多确信。和猜分数一样，它在结果之前运行——它揭示的是一个你还没看到的数值。",
    },

    {
      key: 'app_game_score_vs_average',
      match: /\b(score vs average game|am i above my average game)(?:s|es|ing)?\b|بازی امتیاز در برابر میانگین|لعبة الدرجة مقابل المتوسط|分数对比平均游戏/i,
      en: "You predict whether today landed above or below your own running average before the number appears. It needs history to have an average at all, and runs before the result.",
      fa: "پیش از ظاهرشدن عدد پیش‌بینی می‌کنی امروز بالای میانگین متحرک خودت نشسته یا پایینش. برای اینکه اصلاً میانگینی باشد به تاریخچه نیاز دارد و پیش از نتیجه اجرا می‌شود.",
      ar: "تتنبأ إن كان اليوم قد وقع فوق متوسطك المتحرك أم تحته قبل ظهور الرقم. وتحتاج تاريخا كي يوجد متوسط أصلا، وتُشغَّل قبل النتيجة.",
      zh: "你在数字出现之前预测今天是高于还是低于你自己的滚动平均值。它需要有历史数据才会有平均值，并在结果之前运行。",
    },

    {
      key: 'app_game_keep_the_streak',
      match: /\b(keep the streak game|streak game)(?:s|es|ing)?\b|بازی حفظ زنجیره|لعبة الحفاظ على التتابع|保持连续打卡游戏/i,
      en: "A light nudge built from your real current streak - it names the actual number of consecutive days you have, not a generic encouragement, and runs after the result.",
      fa: "یک تلنگر سبک که از زنجیره‌ی واقعی فعلی‌ات ساخته شده - عددِ واقعی روزهای پیاپی‌ات را نام می‌برد، نه یک تشویق کلی، و بعد از نتیجه اجرا می‌شود.",
      ar: "تنبيه خفيف مبني على تتابعك الحالي الحقيقي - يذكر العدد الفعلي لأيامك المتتالية لا تشجيعا عاما، ويُشغَّل بعد النتيجة.",
      zh: "一个轻量的提醒，由你真实的当前连续天数构建——它说的是你实际连续了多少天，而不是一句泛泛的鼓励，并在结果之后运行。",
    },

    {
      key: 'app_game_dimension_duel',
      match: /\b(dimension duel game|dimension game)(?:s|es|ing)?\b|بازی نبرد ابعاد|لعبة مبارزة الأبعاد|维度对决游戏/i,
      en: "Two of your own dimension scores go head to head and you pick the stronger one. Since dimensions are a deterministic rollup of your real fields, you could check the answer by hand.",
      fa: "دو تا از امتیازهای ابعاد خودت رودرروی هم قرار می‌گیرند و تو قوی‌تر را انتخاب می‌کنی. چون ابعاد یک جمع‌بندی قطعی از فیلدهای واقعی‌ات هستند، می‌توانستی جواب را با دست هم چک کنی.",
      ar: "يتواجه اثنان من درجات أبعادك وتختار الأقوى. ولأن الأبعاد تجميع حتمي لحقولك الحقيقية، يمكنك التحقق من الإجابة بنفسك.",
      zh: "你自己的两个维度分数正面对决，由你选出更强的那个。由于维度是对你真实字段的确定性汇总，你完全可以手工核对答案。",
    },

    {
      key: 'app_game_future_class_guess',
      match: /\b(future class guess game|guess my future class)(?:s|es|ing)?\b|بازی حدس دسته آینده|لعبة تخمين الفئة المستقبلية|猜未来类别游戏/i,
      en: "You guess which class the model projects for you if the current pattern continues. It's built from the same real future-path computation the analytics page uses, and runs after the result.",
      fa: "حدس می‌زنی اگر الگوی فعلی ادامه پیدا کند مدل کدام دسته را برایت پیش‌بینی می‌کند. از همان محاسبه‌ی واقعی مسیر آینده ساخته شده که صفحه‌ی تحلیل‌ها استفاده می‌کند، و بعد از نتیجه اجرا می‌شود.",
      ar: "تخمّن أي فئة يتوقعها لك النموذج إن استمر النمط الحالي. وهي مبنية على حساب المسار المستقبلي الحقيقي نفسه الذي تستخدمه صفحة التحليلات، وتُشغَّل بعد النتيجة.",
      zh: "你猜如果当前模式继续下去，模型会为你预测哪个类别。它基于分析页面使用的同一套真实的未来路径计算，并在结果之后运行。",
    },

    {
      key: 'app_game_weekday_or_weekend',
      match: /\b(weekday or weekend game|weekend game)(?:s|es|ing)?\b|بازی روز هفته یا آخر هفته|لعبة يوم الأسبوع أم العطلة|工作日还是周末游戏/i,
      en: "It asks whether your weekdays or your weekends score better, then answers from your own history. Needs enough of both kinds of day to be able to compare honestly.",
      fa: "می‌پرسد روزهای هفته‌ات امتیاز بهتری می‌گیرند یا آخر هفته‌هایت، و بعد از تاریخچه‌ی خودت جواب می‌دهد. برای اینکه بتواند صادقانه مقایسه کند به تعداد کافی از هر دو نوع روز نیاز دارد.",
      ar: "تسأل إن كانت أيام أسبوعك تسجل أفضل أم عطلاتك، ثم تجيب من تاريخك أنت. وتحتاج عددا كافيا من كلا نوعي الأيام كي تقارن بصدق.",
      zh: "它问你是工作日还是周末的分数更好，然后从你自己的历史中给出答案。它需要两类日子都有足够的数据，才能诚实地做比较。",
    },

    {
      key: 'app_game_badge_race',
      match: /\b(badge race game|which badge is closest)(?:s|es|ing)?\b|بازی مسابقه نشان|لعبة سباق الأوسمة|徽章竞赛游戏/i,
      en: "It shows which badge you're closest to earning, computed from your real progress toward each one - not a random pick, and not a badge you already have.",
      fa: "نشان می‌دهد به کسب کدام نشان نزدیک‌تری، که از پیشرفت واقعی‌ات به سمت هرکدام محاسبه شده - نه یک انتخاب تصادفی، و نه نشانی که از قبل داری.",
      ar: "تُظهر أي وسام أنت أقرب إلى كسبه، محسوبا من تقدمك الحقيقي نحو كل منها - لا اختيارا عشوائيا، ولا وساما تملكه أصلا.",
      zh: "它会显示你最接近获得哪一枚徽章，这是根据你朝各枚徽章的真实进度计算出来的——不是随机挑的，也不会是你已经拥有的徽章。",
    },

    {
      key: 'app_game_baseline_or_exception',
      match: /\b(baseline or exception game|was today unusual game)(?:s|es|ing)?\b|بازی خط پایه یا استثنا|لعبة خط الأساس أم الاستثناء|基线还是例外游戏/i,
      en: "It asks whether today looks like your normal baseline or like an unusual day, using your real numbers - and it's the game most likely to make you reach for the exception-day checkbox.",
      fa: "می‌پرسد امروز شبیه خط پایه‌ی معمولت به نظر می‌رسد یا شبیه یک روز غیرعادی، با استفاده از عددهای واقعی‌ات - و همان بازی‌ای است که بیشتر از همه ممکن است دستت را به سمت تیک روز استثنا ببرد.",
      ar: "تسأل إن كان اليوم يبدو كخط أساسك المعتاد أم كيوم غير عادي، مستخدمة أرقامك الحقيقية - وهي اللعبة الأرجح أن تدفعك إلى مربع اليوم الاستثنائي.",
      zh: "它用你的真实数据问你：今天看起来更像你平常的基线，还是像一个不寻常的日子——而它也是最可能让你去勾选「例外日」的那个游戏。",
    },

    {
      key: 'app_game_fill_the_blank',
      match: /\b(fill the blank game|fill in the blank game)(?:s|es|ing)?\b|بازی جای خالی|لعبة املأ الفراغ|填空游戏/i,
      en: "A short fill-in-the-blank built from one of your own real numbers for that day, shown after the result so the value it uses has already been revealed.",
      fa: "یک جای‌خالیِ کوتاه که از یکی از عددهای واقعی خودت برای آن روز ساخته شده، بعد از نتیجه نشان داده می‌شود تا مقداری که استفاده می‌کند قبلاً فاش شده باشد.",
      ar: "فراغ قصير تملؤه، مبني على أحد أرقامك الحقيقية لذلك اليوم، ويُعرض بعد النتيجة كي تكون القيمة المستخدمة قد كُشفت سلفا.",
      zh: "一道简短的填空题，由你那一天自己的某个真实数值构建，显示在结果之后，这样它用到的数值已经揭晓过了。",
    },

    
    // ====== X. Settings, interface features and more troubleshooting ======
    {
      key: 'app_settings_music',
      match: /\b(background music|turn off the music|music player|is there music)(?:s|es|ing)?\b|موسیقی پس‌زمینه|خاموش کردن موسیقی|پخش‌کننده موسیقی|الموسيقى الخلفية|إيقاف الموسيقى|مشغل الموسيقى|背景音乐|关闭音乐|音乐播放器/i,
      en: "There's an optional background music player with its own control, separate from the sound-effects switch. It keeps playing across page navigation rather than restarting on every page, and you can turn it off entirely in Settings.",
      fa: "یک پخش‌کننده‌ی موسیقی پس‌زمینه‌ی اختیاری با کنترل مخصوص خودش هست، جدا از کلید جلوه‌های صوتی. هنگام جابه‌جایی بین صفحه‌ها ادامه می‌دهد به‌جای اینکه هر صفحه از نو شروع شود، و می‌توانی در تنظیمات کاملاً خاموشش کنی.",
      ar: "يوجد مشغل موسيقى خلفية اختياري بعنصر تحكم خاص به، منفصل عن مفتاح المؤثرات الصوتية. ويستمر بالتشغيل عبر التنقل بين الصفحات بدل أن يبدأ من جديد في كل صفحة، ويمكنك إيقافه تماما من الإعدادات.",
      zh: "有一个可选的背景音乐播放器，带独立控制，和音效开关是分开的。它在页面切换时会继续播放，而不是每页重新开始，你也可以在设置里完全关掉它。",
    },

    {
      key: 'app_settings_guide',
      match: /\b(what is the digital guide|guide tips|turn off the guide|guide setting)(?:s|es|ing)?\b|راهنمای دیجیتال چیست|نکات راهنما|خاموش کردن راهنما|ما هو الدليل الرقمي|تلميحات الدليل|إيقاف الدليل|数字指南是什么|指南提示|关闭指南/i,
      en: "The guide is the in-app help layer: contextual tips attached to parts of the interface, explaining what a control or card actually does. It has its own on/off switch in Settings, plus an optional spoken-voice variant.",
      fa: "راهنما لایه‌ی کمکِ درون‌برنامه‌ای است: نکته‌های متنی که به بخش‌های رابط چسبیده‌اند و توضیح می‌دهند یک کنترل یا کارت واقعاً چه کار می‌کند. کلید روشن/خاموش مخصوص خودش را در تنظیمات دارد، به‌علاوه یک حالت گفتاری اختیاری.",
      ar: "الدليل هو طبقة المساعدة داخل التطبيق: تلميحات سياقية مرتبطة بأجزاء الواجهة، تشرح ما يفعله عنصر تحكم أو بطاقة فعلا. وله مفتاح تشغيل/إيقاف خاص في الإعدادات، إضافة إلى نسخة صوتية منطوقة اختيارية.",
      zh: "指南是应用内的帮助层：附着在界面各部分上的情境提示，解释某个控件或卡片实际的作用。它在设置里有独立的开关，另外还有一个可选的语音朗读版本。",
    },

    {
      key: 'app_settings_tour',
      match: /\b(what is the tour|guided tour|take the tour again|restart the tour)(?:s|es|ing)?\b|تور راهنما چیست|دوباره تور را ببینم|ما هي الجولة|إعادة الجولة|导览是什么|再看一次导览/i,
      en: "The tour is a guided walkthrough of the app you can replay any time from Settings - useful if you skipped it at first or want to show someone else around without narrating it yourself.",
      fa: "تور یک گردش راهنماشده در اپ است که هر وقت بخواهی می‌توانی از تنظیمات دوباره اجرایش کنی - به‌درد می‌خورد اگر اولش ردش کردی یا می‌خواهی بدون توضیح‌دادن خودت، جایی را به کسی نشان بدهی.",
      ar: "الجولة عبارة عن استعراض موجَّه للتطبيق يمكنك إعادة تشغيله متى شئت من الإعدادات - مفيد إن تخطيته في البداية أو أردت أن تُري شخصا آخر التطبيق دون أن تشرحه بنفسك.",
      zh: "导览是应用的引导式浏览，你随时可以在设置里重播——如果你一开始跳过了，或者想带别人看一遍而不用自己讲解，会很有用。",
    },

    {
      key: 'app_settings_excluded_topics',
      match: /\b(excluded topics setting|topics i dont want to see|hide certain topics)(?:s|es|ing)?\b|موضوعات کنارگذاشته‌شده|موضوعاتی که نمیخواهم ببینم|المواضيع المستبعدة|مواضيع لا أريد رؤيتها|排除的话题|不想看到的话题/i,
      en: "You can tell the app which topics you'd rather it didn't bring up, and it keeps that list out of recommendations and coach suggestions. It's a boundary setting rather than a filter on your data - your numbers are unaffected.",
      fa: "می‌توانی به اپ بگویی ترجیح می‌دهی چه موضوعاتی را پیش نکشد، و آن فهرست را از پیشنهادها و توصیه‌های مربی بیرون نگه می‌دارد. این یک تنظیم مرزگذاری است نه فیلتری روی داده‌ات - عددهایت دست‌نخورده می‌مانند.",
      ar: "يمكنك إخبار التطبيق بالمواضيع التي تفضّل ألا يطرحها، فيُبقي تلك القائمة خارج التوصيات واقتراحات المدرب. وهو إعداد حدود لا مرشّح على بياناتك - فأرقامك لا تتأثر.",
      zh: "你可以告诉应用哪些话题你不希望它提起，它会把这份清单排除在建议和教练提示之外。这是一个边界设置，而不是对你数据的过滤——你的数字不受影响。",
    },

    {
      key: 'app_settings_reset',
      match: /\b(reset settings|restore defaults|reset the app)(?:s|es|ing)?\b|بازنشانی تنظیمات|برگرداندن به حالت پیش‌فرض|إعادة ضبط الإعدادات|استعادة الافتراضيات|重置设置|恢复默认/i,
      en: "The reset control in Settings puts your preferences (theme, sound, motion, games, guide) back to defaults. It touches preferences only - your check-ins, history, badges and League connections are not affected.",
      fa: "کنترل بازنشانی در تنظیمات، ترجیحاتت (تم، صدا، حرکت، بازی‌ها، راهنما) را به حالت پیش‌فرض برمی‌گرداند. فقط به ترجیحات دست می‌زند - چک‌این‌ها، تاریخچه، نشان‌ها و ارتباط‌های لیگ‌ات دست‌نخورده می‌مانند.",
      ar: "يعيد عنصر إعادة الضبط في الإعدادات تفضيلاتك (المظهر، الصوت، الحركة، الألعاب، الدليل) إلى الافتراضيات. وهو يمس التفضيلات فقط - أما تسجيلاتك وسجلك وأوسمتك واتصالات الدوري فلا تتأثر.",
      zh: "设置里的重置功能会把你的偏好（主题、声音、动效、游戏、指南）恢复为默认值。它只影响偏好设置——你的打卡记录、历史、徽章和联赛连接都不受影响。",
    },

    {
      key: 'app_mascot',
      match: /\b(what is the mascot|the little character|the animated face)(?:s|es|ing)?\b|ماسکوت چیست|آن شخصیت کوچک|ما هي الشخصية الرمزية|تلك الشخصية الصغيرة|吉祥物是什么|那个小角色/i,
      en: "The mascot is a small animated character that reacts to what just happened - a good result, a risky one, a neutral action. It's decoration and feedback, not a source of advice, and it respects the reduce-motion setting.",
      fa: "ماسکوت یک شخصیت متحرک کوچک است که به آنچه همین حالا اتفاق افتاده واکنش نشان می‌دهد - یک نتیجه‌ی خوب، یک نتیجه‌ی پرخطر، یک کنش خنثی. تزئین و بازخورد است نه منبع توصیه، و تنظیم کاهش حرکت را رعایت می‌کند.",
      ar: "الشخصية الرمزية شخصية متحركة صغيرة تتفاعل مع ما حدث للتو - نتيجة جيدة، أو محفوفة بالمخاطر، أو إجراء محايد. وهي زينة وتغذية راجعة لا مصدر نصائح، وتحترم إعداد تقليل الحركة.",
      zh: "吉祥物是一个会对刚发生的事情做出反应的小动画角色——好结果、有风险的结果、中性操作各有不同。它是装饰和反馈，不是建议的来源，并且会遵守「减少动效」设置。",
    },

    {
      key: 'app_ui_particles_background',
      match: /\b(what is the moving background|animated background|the dots in the background)(?:s|es|ing)?\b|پس‌زمینه متحرک چیست|نقطه‌های پس‌زمینه|ما هي الخلفية المتحركة|النقاط في الخلفية|会动的背景是什么|背景上的点/i,
      en: "The drifting network of dots is a decorative canvas background. It carries no information about your data, and it stops if you turn on reduce motion - if it ever distracts you, that switch is the fix.",
      fa: "آن شبکه‌ی شناور از نقطه‌ها یک پس‌زمینه‌ی تزئینی است. هیچ اطلاعاتی درباره‌ی داده‌ات ندارد و اگر کاهش حرکت را روشن کنی متوقف می‌شود - اگر حواست را پرت کرد، همان کلید راه‌حلش است.",
      ar: "شبكة النقاط المنجرفة خلفية زخرفية. لا تحمل أي معلومة عن بياناتك، وتتوقف إن فعّلت تقليل الحركة - فإن شتّتك يوما، فذلك المفتاح هو الحل.",
      zh: "那片飘动的点状网络是装饰性的画布背景。它不携带任何关于你数据的信息，如果你开启「减少动效」它就会停止——万一它让你分心，那个开关就是解决办法。",
    },

    {
      key: 'app_error_page_not_loading_styles',
      match: /\b(page looks broken|styles not loading|layout is broken|page looks unstyled)(?:s|es|ing)?\b|صفحه به‌هم‌ریخته است|استایل‌ها بارگذاری نمیشوند|چیدمان خراب است|الصفحة تبدو معطلة|الأنماط لا تُحمّل|التخطيط معطل|页面看起来坏了|样式没加载|布局乱了/i,
      en: "An unstyled or scrambled page is almost always a stale cached stylesheet from before an update - a hard refresh that bypasses the cache fixes it. If it persists, an aggressive content blocker is the next thing to check.",
      fa: "صفحه‌ی بی‌استایل یا به‌هم‌ریخته تقریباً همیشه یک شیت استایلِ کش‌شده‌ی قدیمی از پیش از یک به‌روزرسانی است - یک ریفرش سخت که کش را دور می‌زند درستش می‌کند. اگر ماند، مسدودکننده‌ی محتوای تهاجمی چیز بعدی است که باید چک کنی.",
      ar: "الصفحة بلا أنماط أو المشوشة هي غالبا ورقة أنماط مخزّنة قديمة من قبل تحديث - وتحديث قسري يتجاوز الذاكرة المؤقتة يصلحها. وإن استمرت، فحاجب المحتوى الصارم هو التالي للفحص.",
      zh: "页面没有样式或排版错乱，几乎总是更新之前遗留的缓存样式表——强制刷新绕过缓存就能解决。如果依然如此，接下来该检查的是拦截力度很强的内容屏蔽插件。",
    },

    {
      key: 'app_error_buttons_do_nothing',
      match: /\b(buttons dont work|clicking does nothing|nothing happens when i click)(?:s|es|ing)?\b|دکمه‌ها کار نمیکنند|کلیک میکنم اتفاقی نمیافتد|الأزرار لا تعمل|لا يحدث شيء عند النقر|按钮没反应|点了没反应/i,
      en: "Buttons that do nothing usually mean a script failed to load, which the browser console (F12) will name in one red line. A stale cache or a script blocker are the two usual causes, and a hard refresh clears the first.",
      fa: "دکمه‌هایی که کاری نمی‌کنند معمولاً یعنی یک اسکریپت بارگذاری نشده، که کنسول مرورگر (F12) در یک خط قرمز نامش را می‌برد. کش قدیمی یا مسدودکننده‌ی اسکریپت دو علت معمولش‌اند و ریفرش سخت اولی را پاک می‌کند.",
      ar: "الأزرار التي لا تفعل شيئا تعني عادة أن سكربتا فشل في التحميل، وستسمّيه وحدة تحكم المتصفح (F12) في سطر أحمر واحد. والذاكرة المؤقتة القديمة أو حاجب السكربتات هما السببان المعتادان، والتحديث القسري يمسح الأول.",
      zh: "按钮没反应通常意味着某个脚本加载失败，浏览器控制台（F12）会用一行红色信息指出是哪个。常见原因是缓存过期或脚本拦截插件，强制刷新可以解决前者。",
    },

    {
      key: 'app_error_numbers_look_wrong',
      match: /\b(the numbers look wrong|my score seems off|the totals dont add up)(?:s|es|ing)?\b|عددها اشتباه به نظر میرسند|مجموع‌ها جور درنمیایند|الأرقام تبدو خاطئة|المجاميع لا تتطابق|数字看起来不对|总数对不上/i,
      en: "First check the day you're looking at - reopening a history entry shows that day's saved result, not a fresh prediction, so an old day legitimately shows old numbers. If today's figures look wrong, compare the SHAP factors against what you actually entered; a mistyped field shows up there immediately.",
      fa: "اول روزی را که نگاه می‌کنی چک کن - بازکردن یک ورودی تاریخچه نتیجه‌ی ذخیره‌شده‌ی همان روز را نشان می‌دهد نه یک پیش‌بینی تازه، پس یک روز قدیمی به‌درستی عددهای قدیمی نشان می‌دهد. اگر ارقام امروز اشتباه به نظر می‌رسند، عامل‌های SHAP را با آنچه واقعاً وارد کرده‌ای مقایسه کن؛ یک فیلد اشتباه‌تایپ‌شده همان‌جا فوراً خودش را نشان می‌دهد.",
      ar: "تحقق أولا من اليوم الذي تنظر إليه - فإعادة فتح مدخل من السجل تعرض نتيجة ذلك اليوم المحفوظة لا تنبؤا جديدا، فاليوم القديم يعرض أرقاما قديمة بحق. وإن بدت أرقام اليوم خاطئة، فقارن عوامل شاب بما أدخلته فعلا؛ فحقل مكتوب خطأ يظهر هناك فورا.",
      zh: "先确认你看的是哪一天——从历史里重新打开某条记录显示的是那天保存的结果，而不是重新预测，所以旧的一天显示旧数字是正确的。如果今天的数字看起来不对，把 SHAP 因素和你实际填写的内容对照一下；某个字段输错了会立刻在那里显现出来。",
    },

    {
      key: 'app_error_slow',
      match: /\b(the app is slow|pages take long to load|its laggy)(?:s|es|ing)?\b|برنامه کند است|صفحه‌ها دیر بالا میایند|التطبيق بطيء|الصفحات تستغرق وقتا|应用很慢|页面加载很久/i,
      en: "Prediction and demo generation genuinely do work on the server, so those steps take a moment by design. Ordinary page navigation being slow is more likely a network or device issue - and if animations are the cost, reduce motion in Settings lightens the page noticeably.",
      fa: "پیش‌بینی و ساخت دمو واقعاً روی سرور کار انجام می‌دهند، پس آن مرحله‌ها از روی طراحی کمی طول می‌کشند. کند بودن ناوبری معمولی بین صفحه‌ها بیشتر احتمال دارد مسئله‌ی شبکه یا دستگاه باشد - و اگر هزینه‌اش انیمیشن‌هاست، کاهش حرکت در تنظیمات صفحه را محسوس سبک‌تر می‌کند.",
      ar: "التنبؤ وتوليد العرض التجريبي يقومان بعمل حقيقي على الخادم، فتلك الخطوات تستغرق لحظة بالتصميم. أما بطء التنقل العادي بين الصفحات فالأرجح أنه مشكلة شبكة أو جهاز - وإن كانت الرسوم المتحركة هي الكلفة، فتقليل الحركة في الإعدادات يخفف الصفحة بوضوح.",
      zh: "预测和演示生成确实需要在服务器上做实际计算，所以那些步骤按设计就需要一点时间。普通页面切换很慢更可能是网络或设备的问题——如果代价来自动画，设置里的「减少动效」会明显让页面变轻。",
    },

    {
      key: 'app_error_text_overflow_rtl',
      match: /\b(text looks wrong in persian|arabic layout is broken|rtl looks wrong|text direction is wrong)(?:s|es|ing)?\b|متن فارسی به‌هم‌ریخته|چیدمان راست‌به‌چپ خراب است|النص العربي يبدو خاطئا|تخطيط من اليمين لليسار معطل|波斯语显示不正常|阿拉伯语布局有问题/i,
      en: "Persian and Arabic switch the whole interface to right-to-left, which is a real layout change rather than a translated string swap. If something looks misaligned in those languages specifically, that's worth reporting with a screenshot - it's a different code path from the English layout.",
      fa: "فارسی و عربی کل رابط را به راست‌به‌چپ می‌برند که یک تغییر واقعی چیدمان است نه صرفاً جابه‌جایی رشته‌های ترجمه‌شده. اگر چیزی دقیقاً در همین زبان‌ها بدجا به نظر می‌رسد، ارزش گزارش‌دادن با اسکرین‌شات را دارد - مسیر کدی متفاوت از چیدمان انگلیسی است.",
      ar: "الفارسية والعربية تحوّلان الواجهة كلها إلى الاتجاه من اليمين إلى اليسار، وهذا تغيير تخطيط حقيقي لا مجرد تبديل نصوص مترجمة. فإن بدا شيء غير محاذٍ في هاتين اللغتين تحديدا، فيستحق الإبلاغ مع لقطة شاشة - فهو مسار شفرة مختلف عن التخطيط الإنجليزي.",
      zh: "波斯语和阿拉伯语会把整个界面切换为从右到左，这是真正的布局变化，而不只是替换翻译文本。如果某处专门在这两种语言下看起来错位，值得附截图反馈——它走的是和英文布局不同的代码路径。",
    },

    {
      key: 'app_error_after_update',
      match: /\b(something broke after an update|it worked yesterday|it used to work)(?:s|es|ing)?\b|بعد از به‌روزرسانی خراب شد|دیروز کار میکرد|شيء تعطل بعد التحديث|كان يعمل أمس|更新后坏了|昨天还能用/i,
      en: "The first thing to try is a hard refresh: the browser can hold on to old scripts after an update and mix them with new ones, which produces strange, inconsistent behaviour rather than a clean error. If it survives that, it's worth reporting with whatever the console shows.",
      fa: "اولین کاری که باید امتحان کنی ریفرش سخت است: مرورگر می‌تواند بعد از یک به‌روزرسانی اسکریپت‌های قدیمی را نگه دارد و با جدیدها قاطی کند، که رفتاری عجیب و ناسازگار می‌سازد نه یک خطای تمیز. اگر از این جان سالم به در برد، ارزش گزارش‌دادن با هر چیزی که کنسول نشان می‌دهد را دارد.",
      ar: "أول ما تجربه هو تحديث قسري: فالمتصفح قد يحتفظ بسكربتات قديمة بعد تحديث ويخلطها بالجديدة، ما ينتج سلوكا غريبا غير متسق لا خطأ نظيفا. وإن نجا من ذلك، فيستحق الإبلاغ مع ما تعرضه وحدة التحكم.",
      zh: "第一件该试的是强制刷新：浏览器可能在更新后仍保留旧脚本并与新脚本混用，这会产生奇怪、不一致的行为，而不是干净的报错。如果这样还不行，就值得附上控制台的内容反馈。",
    },

    
    // ====== Y. League, coach connector, CSV, result and plan: more depth ======
    {
      key: 'app_league_accept_request',
      match: /\b(how do i accept a request|accept a friend request|approve a request)(?:s|es|ing)?\b|چطور درخواست را قبول کنم|تایید درخواست دوستی|كيف أقبل طلبا|قبول طلب صداقة|怎么接受请求|批准好友请求/i,
      en: "Requests you've received sit under 'Waiting for your approval'. Accepting is where you choose which categories you share back - it isn't automatic or symmetric, so you can accept someone who shares four categories while sharing only one yourself.",
      fa: "درخواست‌هایی که گرفته‌ای زیر «در انتظار تأیید تو» می‌نشینند. پذیرفتن همان‌جایی است که انتخاب می‌کنی چه دسته‌هایی را در عوض به اشتراک می‌گذاری - خودکار یا متقارن نیست، پس می‌توانی کسی را بپذیری که چهار دسته به اشتراک می‌گذارد در حالی که خودت فقط یکی می‌گذاری.",
      ar: "الطلبات التي تلقيتها تقع تحت «بانتظار موافقتك». والقبول هو حيث تختار الفئات التي تشاركها بالمقابل - وهو ليس تلقائيا ولا متماثلا، فيمكنك قبول شخص يشارك أربع فئات بينما تشارك أنت واحدة فقط.",
      zh: "你收到的请求会出现在「等待你批准」下。接受时你可以选择自己回share哪些类别——这不是自动的，也不是对称的，所以你可以接受一个分享四个类别的人，而自己只分享一个。",
    },

    {
      key: 'app_league_change_sharing',
      match: /\b(change what i share|update sharing settings|stop sharing my score)(?:s|es|ing)?\b|تغییر چیزی که به اشتراک میگذارم|اشتراک امتیازم را قطع کنم|تغيير ما أشاركه|إيقاف مشاركة درجتي|修改我分享的内容|停止分享我的分数/i,
      en: "Sharing is revocable at any time, per category and per friend - turning off 'score' stops that friend seeing it from that moment, without removing the connection or closing the chat.",
      fa: "اشتراک‌گذاری هر لحظه قابل پس‌گرفتن است، به‌ازای هر دسته و هر دوست - خاموش‌کردن «امتیاز» از همان لحظه جلوی دیدنش را برای آن دوست می‌گیرد، بدون اینکه ارتباط را حذف کند یا چت را ببندد.",
      ar: "المشاركة قابلة للسحب في أي وقت، لكل فئة ولكل صديق - فإيقاف «الدرجة» يمنع ذلك الصديق من رؤيتها من تلك اللحظة، دون إزالة الاتصال أو إغلاق المحادثة.",
      zh: "分享随时可以撤回，按类别、按好友分别设置——关掉「分数」后，那位好友从那一刻起就看不到了，同时不会解除连接，也不会关闭聊天。",
    },

    {
      key: 'app_league_chat_history',
      match: /\b(are chat messages saved|does the chat keep history|can i delete a message)(?:s|es|ing)?\b|پیام‌های چت ذخیره میشوند|میتوانم پیام را حذف کنم|هل تُحفظ رسائل المحادثة|هل يمكنني حذف رسالة|聊天记录会保存吗|能删除消息吗/i,
      en: "Chat messages persist so a conversation survives a page reload. Removing a connection closes the chat at the same moment it stops the data sharing - there's no state where one side still has an open thread.",
      fa: "پیام‌های چت باقی می‌مانند تا یک گفت‌وگو از بارگذاری دوباره‌ی صفحه جان سالم به در ببرد. حذف یک ارتباط، چت را در همان لحظه‌ای می‌بندد که اشتراک داده را قطع می‌کند - حالتی وجود ندارد که یک طرف هنوز رشته‌ی باز داشته باشد.",
      ar: "تبقى رسائل المحادثة محفوظة كي ينجو الحوار من إعادة تحميل الصفحة. وإزالة اتصال تُغلق المحادثة في اللحظة نفسها التي توقف فيها مشاركة البيانات - فلا توجد حالة يبقى فيها لأحد الطرفين خيط مفتوح.",
      zh: "聊天消息会被保存，这样对话在页面重新加载后仍然存在。解除连接会在停止数据分享的同一时刻关闭聊天——不存在一方仍保留着打开的会话的状态。",
    },

    {
      key: 'app_league_friend_not_showing',
      match: /\b(my friend isnt showing up|added a friend but nothing happened|friend not in my list)(?:s|es|ing)?\b|دوستم نمایش داده نمیشود|دوست اضافه کردم ولی چیزی نشد|صديقي لا يظهر|أضفت صديقا ولم يحدث شيء|好友没有显示|加了好友但没反应/i,
      en: "A sent request stays pending until the other side actually accepts it - until then it appears under 'Requests you've sent' and nothing about either person's data is visible. If they say they accepted, have them reload; the list is fetched, not pushed live.",
      fa: "یک درخواست فرستاده‌شده تا وقتی طرف مقابل واقعاً قبولش نکند در انتظار می‌ماند - تا آن موقع زیر «درخواست‌هایی که فرستادی» ظاهر می‌شود و هیچ چیزی از داده‌ی هیچ‌کدام دیده نمی‌شود. اگر می‌گوید قبول کرده، بگو صفحه را دوباره بارگذاری کند؛ فهرست واکشی می‌شود نه اینکه زنده push شود.",
      ar: "الطلب المُرسل يبقى معلقا حتى يقبله الطرف الآخر فعلا - وحتى ذلك الحين يظهر تحت «الطلبات التي أرسلتها» ولا يُرى شيء من بيانات أي منكما. وإن قال إنه قبل، فاطلب منه إعادة التحميل؛ فالقائمة تُجلب ولا تُدفع مباشرة.",
      zh: "已发送的请求会一直处于待处理状态，直到对方真正接受——在那之前它显示在「我发送的请求」下，双方的数据都不可见。如果对方说已经接受了，让他刷新页面；这个列表是拉取的，不是实时推送的。",
    },

    {
      key: 'app_coach_which_providers',
      match: /\b(which ai providers are supported|what api keys can i use|supported providers)(?:s|es|ing)?\b|کدام ارائه‌دهنده‌ها پشتیبانی میشوند|چه کلیدهایی میتوانم استفاده کنم|ما مزودو الذكاء الاصطناعي المدعومون|أي مفاتيح يمكنني استخدامها|支持哪些ai服务商|可以用哪些密钥/i,
      en: "The optional connector supports keys from Gemini, ChatGPT, x.ai and Anthropic. It's off by default, and your key stays in your own browser - the request goes from your tab straight to that provider, never through this app's server.",
      fa: "کانکتور اختیاری کلیدهای Gemini، ChatGPT، x.ai و Anthropic را پشتیبانی می‌کند. به‌طور پیش‌فرض خاموش است و کلیدت در مرورگر خودت می‌ماند - درخواست از تب تو مستقیم به همان ارائه‌دهنده می‌رود، هرگز از سرور این اپ رد نمی‌شود.",
      ar: "يدعم الموصّل الاختياري مفاتيح Gemini وChatGPT وx.ai وAnthropic. وهو مطفأ افتراضيا، ومفتاحك يبقى في متصفحك أنت - فالطلب يذهب من تبويبك مباشرة إلى ذلك المزود، ولا يمر أبدا عبر خادم هذا التطبيق.",
      zh: "可选的连接器支持 Gemini、ChatGPT、x.ai 和 Anthropic 的密钥。它默认关闭，你的密钥保存在你自己的浏览器里——请求从你的标签页直接发往那家服务商，绝不经过这个应用的服务器。",
    },

    {
      key: 'app_coach_connector_error',
      match: /\b(connector isnt working|my api key doesnt work|connector error)(?:s|es|ing)?\b|کانکتور کار نمیکند|کلید من کار نمیکند|الموصّل لا يعمل|مفتاحي لا يعمل|连接器不工作|我的密钥无效/i,
      en: "The usual causes are an expired or mistyped key, no credit on that provider account, or the provider being unreachable from your network. The error the provider returns is shown as-is rather than being swallowed, so the message itself usually names which of the three it is.",
      fa: "علت‌های معمول: کلید منقضی یا اشتباه‌تایپ‌شده، نبود اعتبار روی آن حساب ارائه‌دهنده، یا در دسترس نبودن ارائه‌دهنده از شبکه‌ی تو. خطایی که ارائه‌دهنده برمی‌گرداند همان‌طور که هست نشان داده می‌شود نه اینکه بلعیده شود، پس خودِ پیام معمولاً می‌گوید کدام‌یک از آن سه‌تاست.",
      ar: "الأسباب المعتادة: مفتاح منتهي الصلاحية أو مكتوب خطأ، أو عدم وجود رصيد في حساب المزود، أو تعذر الوصول إلى المزود من شبكتك. والخطأ الذي يعيده المزود يُعرض كما هو لا يُبتلع، فالرسالة نفسها تسمّي عادة أيّ الثلاثة هو.",
      zh: "常见原因是密钥过期或输错、该服务商账户没有余额，或者从你的网络无法访问该服务商。服务商返回的错误会原样显示而不会被吞掉，所以那条信息通常就说明了是三者中的哪一种。",
    },

    {
      key: 'app_coach_clear_chat',
      match: /\b(clear my chat|delete conversation|start a new conversation)(?:s|es|ing)?\b|پاک کردن چت|حذف گفتگو|شروع گفتگوی جدید|مسح محادثتي|حذف المحادثة|بدء محادثة جديدة|清空聊天|删除对话|开始新对话/i,
      en: "You can start a fresh conversation rather than scrolling past an old one; the coach keeps threads so you can come back to something. Nothing in a chat feeds the model or changes your score either way.",
      fa: "می‌توانی به‌جای اسکرول‌کردن از روی یک گفت‌وگوی قدیمی، یکی تازه شروع کنی؛ مربی رشته‌ها را نگه می‌دارد تا بتوانی به چیزی برگردی. هیچ چیزی در یک چت به مدل خورانده نمی‌شود یا امتیازت را عوض نمی‌کند.",
      ar: "يمكنك بدء محادثة جديدة بدل التمرير عبر واحدة قديمة؛ فالمدرب يحتفظ بالخيوط كي تعود إلى شيء ما. ولا شيء في المحادثة يُغذّي النموذج أو يغيّر درجتك بأي حال.",
      zh: "你可以开始一段新对话，而不用一直往下翻旧的；教练会保留会话线程，方便你回头查看。聊天中的任何内容都不会喂给模型，也不会改变你的分数。",
    },

    {
      key: 'app_coach_asks_for_more_days',
      match: /\b(coach says i need more data|coach cant answer without history)(?:s|es|ing)?\b|مربی میگوید داده بیشتری لازم است|مربی بدون تاریخچه جواب نمیدهد|المدرب يقول أحتاج بيانات أكثر|المدرب لا يجيب بلا تاريخ|教练说需要更多数据|教练没有历史无法回答/i,
      en: "Menu questions declare what they need. If a question depends on a prediction you haven't made or on days you haven't logged, it says so plainly instead of producing a plausible answer from nothing - that decline is the feature, not a gap.",
      fa: "سؤال‌های منو اعلام می‌کنند به چه چیزی نیاز دارند. اگر سؤالی به پیش‌بینی‌ای وابسته باشد که نکرده‌ای یا به روزهایی که ثبت نکرده‌ای، صریح می‌گوید به‌جای اینکه از هیچ یک جواب باورپذیر بسازد - همان خودداری، خودِ قابلیت است نه یک کمبود.",
      ar: "أسئلة القائمة تعلن ما تحتاجه. فإن اعتمد سؤال على تنبؤ لم تقم به أو أيام لم تسجّلها، قال ذلك صراحة بدل إنتاج إجابة معقولة من العدم - وذلك الامتناع هو الميزة لا الثغرة.",
      zh: "菜单里的问题会声明自己需要什么。如果某个问题依赖你还没做过的预测或还没记录的天数，它会直说，而不是凭空编出一个听起来合理的答案——这种拒答本身就是功能，不是缺陷。",
    },

    {
      key: 'app_csv_which_columns',
      match: /\b(what columns does the csv need|required csv columns|csv header row)(?:s|es|ing)?\b|سی اس وی چه ستون‌هایی لازم دارد|سطر عنوان فایل|ما الأعمدة التي يحتاجها الملف|صف العناوين|csv需要哪些列|表头行/i,
      en: "Download the template rather than guessing - it ships the exact header row plus two realistic example rows, one healthy-leaning and one at-risk-leaning, so the expected scale of each field is visible rather than described.",
      fa: "به‌جای حدس‌زدن قالب را دانلود کن - دقیقاً همان سطر عنوان به‌علاوه دو ردیف نمونه‌ی واقع‌گرایانه را می‌آورد، یکی متمایل به سالم و یکی متمایل به در معرض خطر، تا مقیاس مورد انتظار هر فیلد دیده شود نه توصیف.",
      ar: "نزّل القالب بدل التخمين - فهو يأتي بصف العناوين بالضبط إضافة إلى صفَّي مثال واقعيين، أحدهما يميل إلى الصحي والآخر إلى الخطر، فتُرى المقاييس المتوقعة لكل حقل بدل وصفها.",
      zh: "与其猜测，不如下载模板——它自带准确的表头行以及两行真实的示例数据，一行偏健康、一行偏风险，这样每个字段的预期量级是看得见的，而不是靠文字描述。",
    },

    {
      key: 'app_csv_partial_import',
      match: /\b(some rows failed to import|partial import|only some days imported)(?:s|es|ing)?\b|بعضی ردیف‌ها وارد نشدند|ورود ناقص|بعض الصفوف فشلت|استيراد جزئي|部分行导入失败|只导入了一部分/i,
      en: "The importer validates each row on its own and reports every bad one by row number rather than stopping at the first failure, so a single malformed day doesn't cost you the rest of the file. Fix the named rows and re-import just those.",
      fa: "وارد‌کننده هر ردیف را جداگانه اعتبارسنجی می‌کند و هر ردیف خراب را با شماره‌اش گزارش می‌دهد نه اینکه سر اولین شکست متوقف شود، پس یک روزِ بدشکل بقیه‌ی فایل را از تو نمی‌گیرد. ردیف‌های نام‌برده‌شده را درست کن و فقط همان‌ها را دوباره وارد کن.",
      ar: "يتحقق المستورد من كل صف على حدة ويُبلّغ عن كل صف معطوب برقمه بدل التوقف عند أول فشل، فلا يكلفك يوم واحد مشوّه بقية الملف. صحّح الصفوف المذكورة وأعد استيرادها وحدها.",
      zh: "导入器会逐行独立校验，并按行号报告每一个有问题的行，而不是在第一个失败处停下，所以一天的格式错误不会让你失去文件其余部分。修正被指出的那些行，只重新导入它们即可。",
    },

    {
      key: 'app_result_where_is_pdf',
      match: /\b(where is the pdf button|cant find the download report button)(?:s|es|ing)?\b|دکمه پی دی اف کجاست|دکمه دانلود گزارش را پیدا نمیکنم|أين زر بي دي إف|لا أجد زر تحميل التقرير|pdf按钮在哪|找不到下载报告按钮/i,
      en: "The PDF button lives on the result page, alongside the save-as-CSV card - both act on that one prediction. Reopening a past day from history gives you the same page for that day, so an old result can be exported the same way.",
      fa: "دکمه‌ی PDF روی صفحه‌ی نتیجه است، کنار کارت ذخیره‌به‌صورت‌CSV - هر دو روی همان یک پیش‌بینی عمل می‌کنند. بازکردن یک روز گذشته از تاریخچه همان صفحه را برای آن روز می‌دهد، پس یک نتیجه‌ی قدیمی هم به همان شکل قابل خروجی‌گرفتن است.",
      ar: "زر بي دي إف موجود في صفحة النتيجة، بجانب بطاقة الحفظ كـسي إس في - وكلاهما يعمل على ذلك التنبؤ الواحد. وإعادة فتح يوم سابق من السجل تمنحك الصفحة نفسها لذلك اليوم، فيمكن تصدير نتيجة قديمة بالطريقة ذاتها.",
      zh: "PDF 按钮在结果页上，紧挨着「保存为 CSV」的卡片——两者作用的都是那一次预测。从历史里重新打开过去的某一天会得到那天的同一个页面，所以旧结果也可以用同样的方式导出。",
    },

    {
      key: 'app_result_top_factors_count',
      match: /\b(why only a few factors|how many factors are shown|why not all fields listed)(?:s|es|ing)?\b|چرا فقط چند عامل|چند عامل نشان داده میشود|لماذا عوامل قليلة فقط|كم عاملا يُعرض|为什么只有几个因素|显示多少个因素/i,
      en: "The result shows your strongest contributors rather than every field, because a list of thirty near-zero contributions hides the two that actually mattered. The ones shown are ranked by real SHAP magnitude for that specific prediction.",
      fa: "نتیجه به‌جای هر فیلد، قوی‌ترین سهم‌گذارانت را نشان می‌دهد، چون فهرستی از سی سهمِ نزدیک‌به‌صفر آن دو تایی را که واقعاً مهم بودند پنهان می‌کند. آن‌هایی که نشان داده می‌شوند بر اساس بزرگی واقعی SHAP برای همان پیش‌بینی مشخص رتبه‌بندی شده‌اند.",
      ar: "تعرض النتيجة أقوى مساهميك بدل كل حقل، لأن قائمة من ثلاثين مساهمة قريبة من الصفر تُخفي الاثنتين اللتين همّتا فعلا. والمعروضة مرتبة حسب حجم شاب الحقيقي لذلك التنبؤ بعينه.",
      zh: "结果页显示的是对你影响最大的几个因素，而不是所有字段，因为三十个接近零的贡献会淹没真正起作用的那两个。显示出来的是按那一次预测的真实 SHAP 幅度排序的。",
    },

    {
      key: 'app_weekly_plan_ignore_a_task',
      match: /\b(can i ignore a task|i dont want to do one of the tasks|skip a plan task)(?:s|es|ing)?\b|میتوانم یک کار را نادیده بگیرم|نمیخواهم یکی از کارها را انجام بدهم|هل يمكنني تجاهل مهمة|لا أريد إحدى المهام|能忽略某个任务吗|不想做其中一个任务/i,
      en: "Nothing in the plan is enforced - skip anything. If a whole theme keeps coming up and you'd rather it didn't, the excluded-topics setting keeps it out of future plans and recommendations entirely.",
      fa: "هیچ چیز در برنامه اجباری نیست - هرچه می‌خواهی رد کن. اگر یک موضوع کامل مدام تکرار می‌شود و ترجیح می‌دهی نباشد، تنظیم «موضوعات کنارگذاشته‌شده» آن را کاملاً از برنامه‌ها و پیشنهادهای آینده بیرون نگه می‌دارد.",
      ar: "لا شيء في الخطة إلزامي - تخطَّ ما تشاء. وإن ظل موضوع كامل يتكرر وتفضّل ألا يظهر، فإعداد المواضيع المستبعدة يبقيه خارج الخطط والتوصيات المستقبلية تماما.",
      zh: "计划里没有任何强制项——想跳过就跳过。如果某个主题反复出现而你希望它别再出现，「排除的话题」设置会把它彻底排除在未来的计划和建议之外。",
    },

    
    // ====== Z. Analytics cards, badges, profile, preferences and project scope ======
    {
      key: 'app_analytics_narrative_card',
      match: /\b(what is the narrative card|the written summary card|story card in analytics)(?:s|es|ing)?\b|کارت روایت چیست|کارت خلاصه نوشتاری|ما هي بطاقة السرد|بطاقة الملخص المكتوب|叙述卡片是什么|文字总结卡/i,
      en: "The narrative card writes a short summary of your recent stretch in plain language, assembled from your real numbers - how many days it covers, which way things moved, what stood out. It needs about a week before it can say anything honest.",
      fa: "کارت روایت خلاصه‌ای کوتاه از دوره‌ی اخیرت را به زبان ساده می‌نویسد که از عددهای واقعی‌ات سرهم شده - چند روز را پوشش می‌دهد، اوضاع به کدام سمت رفته، چه چیزی برجسته بوده. برای اینکه بتواند چیز صادقانه‌ای بگوید حدود یک هفته لازم دارد.",
      ar: "تكتب بطاقة السرد ملخصا قصيرا لفترتك الأخيرة بلغة بسيطة، مجمّعا من أرقامك الحقيقية - كم يوما تغطي، وإلى أي اتجاه تحركت الأمور، وما الذي برز. وتحتاج نحو أسبوع قبل أن تقول شيئا صادقا.",
      zh: "叙述卡片用平实的语言写出你近期这段时间的简短总结，由你的真实数据拼装而成——覆盖了多少天、事情朝哪个方向变化、什么比较突出。它需要大约一周才能说出有依据的内容。",
    },

    {
      key: 'app_analytics_weekly_comparison',
      match: /\b(weekly comparison card|this week vs last week|compare my weeks)(?:s|es|ing)?\b|کارت مقایسه هفتگی|این هفته در برابر هفته گذشته|بطاقة المقارنة الأسبوعية|هذا الأسبوع مقابل الماضي|周对比卡片|本周对比上周/i,
      en: "It compares this ISO week against the previous one on your real logged days. If one week has very few days, the comparison is thin by nature - and days you marked as exceptions are excluded from both sides, so the two weeks stay comparable.",
      fa: "این هفته‌ی ISO را با هفته‌ی قبلی روی روزهای واقعی ثبت‌شده‌ات مقایسه می‌کند. اگر یک هفته روزهای خیلی کمی داشته باشد، مقایسه ذاتاً نازک است - و روزهایی که استثنا علامت زده‌ای از هر دو طرف کنار گذاشته می‌شوند تا دو هفته قابل‌مقایسه بمانند.",
      ar: "تقارن أسبوع ISO الحالي بالسابق على أيامك المسجلة الحقيقية. وإن كان لأسبوع أيام قليلة جدا، فالمقارنة رقيقة بطبيعتها - والأيام التي وسمتها كاستثناءات تُستبعد من الجانبين كي يبقى الأسبوعان قابلين للمقارنة.",
      zh: "它用你真实记录的日子，把当前 ISO 周和上一周做对比。如果某一周的天数很少，这个对比天然就很单薄——而你标记为例外的日子会从两边同时排除，以保证两周之间可比。",
    },

    {
      key: 'app_analytics_best_worst_day',
      match: /\b(my best day|my worst day|when was my best score)(?:s|es|ing)?\b|بهترین روزم|بدترین روزم|بهترین امتیازم کی بود|أفضل يوم لي|أسوأ يوم لي|我最好的一天|我最差的一天/i,
      en: "Best and worst days are read straight off your stored history with the actual dates, not rounded or smoothed. The coach menu also has a 'what is a typical X for me' question per signal that names your healthiest day for that specific field.",
      fa: "بهترین و بدترین روزها مستقیم از تاریخچه‌ی ذخیره‌شده‌ات با تاریخ‌های واقعی خوانده می‌شوند، نه گرد‌شده یا هموارشده. منوی مربی هم برای هر سیگنال یک سؤال «مقدار معمول فلان چیز برای من چقدر است» دارد که سالم‌ترین روزت را برای همان فیلد مشخص نام می‌برد.",
      ar: "يُقرأ أفضل وأسوأ يوم مباشرة من سجلك المحفوظ بالتواريخ الفعلية، لا مقرّبة ولا ممهّدة. كما أن قائمة المدرب فيها سؤال «ما القيمة المعتادة لكذا بالنسبة لي» لكل إشارة، يذكر أصحّ يوم لك في ذلك الحقل بعينه.",
      zh: "最好和最差的一天是直接从你保存的历史中读取的，带有实际日期，没有取整也没有平滑处理。教练菜单里还为每个信号提供了「对我来说典型的某项是多少」的问题，会点出你在那个字段上最健康的一天。",
    },

    {
      key: 'app_badges_how_many',
      match: /\b(how many badges are there|full list of badges|all badges)(?:s|es|ing)?\b|چند نشان وجود دارد|فهرست کامل نشان‌ها|كم عدد الأوسمة|قائمة الأوسمة كاملة|有多少徽章|徽章完整列表/i,
      en: "The Hall of Fame page lists them all, showing which you've earned and which you haven't. The coach also has a 'which badge am I closest to' question answered from your real progress toward each one.",
      fa: "صفحه‌ی تالار افتخارات همه‌شان را فهرست می‌کند و نشان می‌دهد کدام‌ها را گرفته‌ای و کدام‌ها را نه. مربی هم سؤال «به کدام نشان نزدیک‌ترم» را دارد که از پیشرفت واقعی‌ات به سمت هرکدام جواب داده می‌شود.",
      ar: "تسرد صفحة قاعة المشاهير جميعها، مبيّنة ما كسبته وما لم تكسبه. وللمدرب أيضا سؤال «أي وسام أنا أقرب إليه» يُجاب عنه من تقدمك الحقيقي نحو كل منها.",
      zh: "名人堂页面会列出全部徽章，显示哪些你已获得、哪些还没有。教练那里也有「我最接近哪一枚徽章」的问题，答案来自你朝各枚徽章的真实进度。",
    },

    {
      key: 'app_badges_lost_a_badge',
      match: /\b(did i lose a badge|can a badge be taken away|badge disappeared)(?:s|es|ing)?\b|نشانم را از دست دادم|نشان میتواند پس گرفته شود|هل فقدت وساما|هل يُسحب الوسام|徽章会失去吗|徽章不见了/i,
      en: "Badges tied to a milestone you reached stay earned. Ones that describe a current state (an active streak, for instance) reflect where you are now, so they can stop applying without anything being taken from you punitively.",
      fa: "نشان‌هایی که به یک نقطه‌ی عطفِ رسیده‌شده گره خورده‌اند کسب‌شده می‌مانند. آن‌هایی که یک وضعیت فعلی را توصیف می‌کنند (مثلاً یک زنجیره‌ی فعال) بازتاب جایی هستند که الان هستی، پس می‌توانند از اعتبار بیفتند بدون اینکه چیزی به‌عنوان تنبیه از تو گرفته شده باشد.",
      ar: "الأوسمة المرتبطة بمحطة بلغتها تبقى مكتسبة. أما التي تصف حالة راهنة (كتتابع نشط مثلا) فتعكس موضعك الآن، فقد تتوقف عن الانطباق دون أن يُسلب منك شيء عقابا.",
      zh: "与你已达成的里程碑绑定的徽章会一直保留。而描述当前状态的徽章（比如正在进行的连续打卡）反映的是你此刻的情况，所以它们可能不再适用，但这并不是惩罚性地把什么从你身上拿走。",
    },

    {
      key: 'app_onboarding_questions',
      match: /\b(what are the onboarding questions|the questions when i signed up|profile questions)(?:s|es|ing)?\b|سوال‌های اولیه چیستند|سوال‌هایی که موقع ثبت‌نام پرسید|ما هي أسئلة التهيئة|الأسئلة عند التسجيل|注册时的问题是什么|引导问题/i,
      en: "Those describe you rather than a day - your main platform, device, occupation group, purpose. They're context the app keeps on your profile and don't change per check-in, and you can edit them later from the profile page.",
      fa: "آن‌ها تو را توصیف می‌کنند نه یک روز را - پلتفرم اصلی‌ات، دستگاه، گروه شغلی، هدف. بافتی هستند که اپ روی پروفایلت نگه می‌دارد و به‌ازای هر چک‌این عوض نمی‌شوند، و بعداً می‌توانی از صفحه‌ی پروفایل ویرایششان کنی.",
      ar: "تلك تصفك أنت لا يوما بعينه - منصتك الأساسية وجهازك وفئتك المهنية وغرضك. وهي سياق يحتفظ به التطبيق في ملفك ولا يتغير مع كل تسجيل، ويمكنك تعديلها لاحقا من صفحة الملف الشخصي.",
      zh: "那些问题描述的是「你这个人」而不是某一天——你的主要平台、设备、职业类别、使用目的。它们是应用保存在你资料里的背景信息，不会随每次打卡改变，之后可以在资料页修改。",
    },

    {
      key: 'app_change_onboarding_answers',
      match: /\b(change my onboarding answers|edit my profile answers|i picked the wrong platform)(?:s|es|ing)?\b|تغییر پاسخ‌های اولیه|پلتفرم اشتباه انتخاب کردم|تغيير إجابات التهيئة|اخترت المنصة الخطأ|修改引导问题的答案|我选错了平台/i,
      en: "They're editable from your profile page at any time. Changing them updates the context the app uses going forward; it doesn't rewrite the predictions you already have, which were made with what you'd entered at the time.",
      fa: "هر وقت بخواهی از صفحه‌ی پروفایل قابل ویرایش‌اند. عوض‌کردنشان بافتی را که اپ از این به بعد استفاده می‌کند به‌روز می‌کند؛ پیش‌بینی‌هایی را که از قبل داری بازنویسی نمی‌کند، چون آن‌ها با چیزی ساخته شده‌اند که در آن زمان وارد کرده بودی.",
      ar: "يمكن تعديلها من صفحة ملفك في أي وقت. وتغييرها يحدّث السياق الذي يستخدمه التطبيق من الآن فصاعدا؛ ولا يعيد كتابة التنبؤات التي لديك أصلا، فقد صُنعت بما أدخلته حينها.",
      zh: "它们随时可以在资料页修改。修改后会更新应用之后使用的背景信息；但不会改写你已有的预测，那些是用你当时填写的内容做出的。",
    },

    {
      key: 'app_theme_which_is_default',
      match: /\b(what is the default theme|does it follow my system theme|auto dark mode)(?:s|es|ing)?\b|تم پیش‌فرض چیست|از تم سیستم پیروی میکند|ما هو المظهر الافتراضي|هل يتبع مظهر النظام|默认主题是什么|会跟随系统主题吗/i,
      en: "There's a 'system' option that follows your OS or browser preference automatically, alongside explicit light and dark. Whichever you pick is remembered per browser, the same way the language choice is.",
      fa: "یک گزینه‌ی «سیستم» هست که به‌طور خودکار از ترجیح سیستم‌عامل یا مرورگرت پیروی می‌کند، در کنار روشن و تیرهٔ صریح. هرکدام را انتخاب کنی به‌ازای هر مرورگر به خاطر سپرده می‌شود، درست مثل انتخاب زبان.",
      ar: "يوجد خيار «النظام» يتبع تفضيل نظام التشغيل أو المتصفح تلقائيا، إلى جانب الفاتح والداكن الصريحين. وأيّها اخترت يُحفظ لكل متصفح، تماما كخيار اللغة.",
      zh: "除了明确的浅色和深色之外，还有一个「跟随系统」选项，会自动遵循你的操作系统或浏览器偏好。你选的是哪个会按浏览器记住，和语言选择一样。",
    },

    {
      key: 'app_language_persists',
      match: /\b(does my language choice stick|will it remember my language|language resets)(?:s|es|ing)?\b|انتخاب زبانم میماند|زبان را به خاطر میسپارد|هل يبقى اختيار لغتي|هل يتذكر لغتي|语言选择会保留吗|会记住我的语言吗/i,
      en: "The language choice is stored per browser, so it survives reloads and navigation. Opening the app in a different browser or a private window starts from the default again, since that's a separate store.",
      fa: "انتخاب زبان به‌ازای هر مرورگر ذخیره می‌شود، پس از بارگذاری دوباره و ناوبری جان سالم به در می‌برد. باز‌کردن اپ در مرورگر دیگر یا پنجره‌ی ناشناس دوباره از پیش‌فرض شروع می‌کند، چون آن یک انبار جداست.",
      ar: "يُحفظ اختيار اللغة لكل متصفح، فينجو من إعادة التحميل والتنقل. أما فتح التطبيق في متصفح آخر أو نافذة خاصة فيبدأ من الافتراضي مجددا، لأن ذلك مخزن منفصل.",
      zh: "语言选择按浏览器保存，所以刷新和页面跳转都不会丢失。在另一个浏览器或无痕窗口打开应用会重新从默认语言开始，因为那是另一套独立的存储。",
    },

    {
      key: 'app_why_no_notifications',
      match: /\b(does it send notifications|will it remind me|push notifications)(?:s|es|ing)?\b|اعلان میفرستد|یادآوری میکند|هل يرسل إشعارات|هل يذكّرني|会发通知吗|会提醒我吗/i,
      en: "It doesn't send push notifications or reminders - it's a web page with no device permissions, so it can't. Given the subject matter, an app about screen habits adding its own stream of interruptions would be working against itself.",
      fa: "اعلان یا یادآوری نمی‌فرستد - یک صفحه‌ی وب بدون مجوز دستگاه است، پس نمی‌تواند. با توجه به موضوعش، اپی درباره‌ی عادت‌های صفحه که جریان مزاحمت‌های خودش را اضافه کند، علیه خودش کار می‌کرد.",
      ar: "لا يرسل إشعارات دفع ولا تذكيرات - فهو صفحة ويب بلا أذونات جهاز، فلا يستطيع. وبالنظر إلى موضوعه، فإن تطبيقا عن عادات الشاشة يضيف تياره الخاص من المقاطعات كان سيعمل ضد نفسه.",
      zh: "它不发送推送通知或提醒——它是一个没有设备权限的网页，做不到。而且就它的主题而言，一个讲屏幕使用习惯的应用如果再添上自己的一串打扰，那就是在跟自己作对。",
    },

    {
      key: 'app_data_between_devices',
      match: /\b(can i use it on two devices|does my data sync|same account on phone and laptop)(?:s|es|ing)?\b|روی دو دستگاه استفاده کنم|داده‌هایم همگام میشود|هل أستخدمه على جهازين|هل تتزامن بياناتي|能在两个设备上用吗|数据会同步吗/i,
      en: "Your check-ins live on the server against your account, so logging in from another device shows the same history. What stays per-browser is preferences - language, theme, sound - since those are local settings rather than account data.",
      fa: "چک‌این‌هایت روی سرور و به حساب تو گره خورده‌اند، پس ورود از دستگاهی دیگر همان تاریخچه را نشان می‌دهد. چیزی که به‌ازای هر مرورگر می‌ماند ترجیحات است - زبان، تم، صدا - چون آن‌ها تنظیمات محلی‌اند نه داده‌ی حساب.",
      ar: "تسجيلاتك موجودة على الخادم مرتبطة بحسابك، فتسجيل الدخول من جهاز آخر يعرض السجل نفسه. أما ما يبقى لكل متصفح فهو التفضيلات - اللغة والمظهر والصوت - لأنها إعدادات محلية لا بيانات حساب.",
      zh: "你的打卡记录保存在服务器上、与你的账户绑定，所以从另一台设备登录会看到相同的历史。按浏览器保存的是偏好设置——语言、主题、声音——因为那些是本地设置而不是账户数据。",
    },

    {
      key: 'app_who_built_this',
      match: /\b(who made this|who built this app|is this a real product|is this a hackathon project)(?:s|es|ing)?\b|چه کسی این را ساخته|این یک محصول واقعی است|من صنع هذا|هل هذا منتج حقيقي|这是谁做的|这是真实产品吗/i,
      en: "The About page carries the project background. What matters for how much to trust it: the models are genuinely trained and their held-out metrics are published in the app, and the parts that are rule-based (the weekly plan, this coach) say so plainly rather than implying a model is behind them.",
      fa: "صفحه‌ی درباره پیشینه‌ی پروژه را دارد. آنچه برای میزان اعتماد اهمیت دارد این است: مدل‌ها واقعاً آموزش دیده‌اند و سنجه‌های کنارگذاشته‌شده‌شان در اپ منتشر شده، و بخش‌هایی که قانون‌محورند (برنامه‌ی هفتگی، همین مربی) صریح می‌گویند، نه اینکه القا کنند مدلی پشتشان است.",
      ar: "تحمل صفحة «حول» خلفية المشروع. وما يهم بشأن مقدار الثقة: النماذج مدرَّبة فعلا ومقاييسها المحجوزة منشورة داخل التطبيق، والأجزاء القائمة على القواعد (الخطة الأسبوعية، هذا المدرب) تقول ذلك صراحة بدل الإيحاء بأن نموذجا يقف خلفها.",
      zh: "关于页面有项目背景。就「该信任它多少」而言真正重要的是：模型是真正训练过的，其留出集指标就发布在应用里；而那些基于规则的部分（每周计划、这个教练）都会明说，而不是暗示背后有个模型。",
    },

    {
      key: 'app_terms_page',
      match: /\b(terms of use|where are the terms|privacy policy page)(?:s|es|ing)?\b|شرایط استفاده|سیاست حریم خصوصی کجاست|شروط الاستخدام|أين سياسة الخصوصية|使用条款|隐私政策在哪/i,
      en: "There's a terms page linked from the app's footer navigation covering use and data handling. The short version of the data part is on the About page and in the privacy answers here.",
      fa: "یک صفحه‌ی شرایط هست که از ناوبری پاورقی اپ لینک شده و استفاده و نحوه‌ی برخورد با داده را پوشش می‌دهد. نسخه‌ی کوتاه بخش داده روی صفحه‌ی درباره و در پاسخ‌های حریم خصوصی همین‌جاست.",
      ar: "توجد صفحة شروط مرتبطة من تنقل تذييل التطبيق تغطي الاستخدام والتعامل مع البيانات. والنسخة المختصرة من جزء البيانات موجودة في صفحة «حول» وفي إجابات الخصوصية هنا.",
      zh: "应用页脚导航里有一个条款页面，涵盖使用方式和数据处理。数据部分的简版说明在关于页面，以及这里的隐私相关回答中。",
    },

    
    // ====== AA. Result UI, history, future paths, simulator, security and accessibility ======
    {
      key: 'app_score_ring',
      match: /\b(what is the ring|the circle around my score|score ring meaning|the glowing circle)(?:s|es|ing)?\b|حلقه چیست|دایره دور امتیازم|حلقه امتیاز یعنی چه|ما هي الحلقة|الدائرة حول درجتي|那个环是什么|分数外面的圆环/i,
      en: "The glowing centre is your real regression-model score; the arcs around it are the transparent dimension breakdown - a deterministic rollup of your own fields, not a second model. So the middle is the model's opinion and the ring is arithmetic you could verify.",
      fa: "مرکز درخشان امتیاز واقعی مدل رگرسیون توست؛ کمان‌های دورش تفکیک شفاف ابعادند - یک جمع‌بندی قطعی از فیلدهای خودت، نه یک مدل دوم. پس وسط نظر مدل است و حلقه حسابی است که می‌توانستی راستی‌آزمایی کنی.",
      ar: "المركز المتوهج هو درجة نموذج الانحدار الحقيقية لديك؛ والأقواس حوله هي تفصيل الأبعاد الشفاف - تجميع حتمي لحقولك أنت، لا نموذج ثانٍ. فالوسط رأي النموذج، والحلقة حساب يمكنك التحقق منه.",
      zh: "发光的中心是你真实的回归模型分数；围绕它的弧线是透明的维度分解——那是对你自己字段的确定性汇总，不是第二个模型。所以中间是模型的判断，而外环是你可以自行核对的算术。",
    },

    {
      key: 'app_history_page_filter',
      match: /\b(can i filter my history|sort my history|find a specific day)(?:s|es|ing)?\b|میتوانم تاریخچه را فیلتر کنم|یک روز خاص را پیدا کنم|هل يمكنني تصفية سجلي|إيجاد يوم معين|能筛选历史吗|找某一天/i,
      en: "History lists your logged days most recent first, and clicking any entry reopens that exact day's saved result. Days you marked as exceptions are shown as such rather than hidden, so you can see why a day isn't counting toward your averages.",
      fa: "تاریخچه روزهای ثبت‌شده‌ات را از جدیدترین فهرست می‌کند و کلیک روی هر ورودی نتیجه‌ی ذخیره‌شده‌ی دقیقاً همان روز را باز می‌کند. روزهایی که استثنا علامت زده‌ای به همان شکل نشان داده می‌شوند نه پنهان، تا بتوانی ببینی چرا یک روز در میانگین‌هایت حساب نمی‌شود.",
      ar: "يسرد السجل أيامك المسجلة من الأحدث، والنقر على أي مدخل يعيد فتح نتيجة ذلك اليوم المحفوظة بالضبط. والأيام التي وسمتها كاستثناءات تُعرض بهذه الصفة لا تُخفى، فترى لماذا لا يُحتسب يوم في متوسطاتك.",
      zh: "历史按最近优先列出你记录过的日子，点击任意一条会重新打开那一天保存的结果。你标记为例外的日子会被如实标出而不是隐藏，这样你能看到某一天为什么没有计入平均值。",
    },

    {
      key: 'app_streak_broken',
      match: /\b(my streak reset|i lost my streak|streak went back to zero)(?:s|es|ing)?\b|زنجیره‌ام صفر شد|استریکم را از دست دادم|تتابعي عاد إلى الصفر|فقدت تتابعي|连续打卡断了|连续天数归零了/i,
      en: "The streak counts consecutive days with a real check-in, so a missed day shortens it - the app won't fill in a day you didn't log, because inventing a number would be exactly the kind of fabrication it avoids everywhere else. Starting again is normal and costs you no history.",
      fa: "زنجیره روزهای پیاپی با یک چک‌این واقعی را می‌شمارد، پس یک روز از‌دست‌رفته کوتاهش می‌کند - اپ روزی را که ثبت نکرده‌ای پر نمی‌کند، چون ساختن یک عدد دقیقاً همان جعلی است که همه‌جای دیگر از آن پرهیز می‌کند. از نو شروع‌کردن عادی است و هیچ تاریخچه‌ای از تو نمی‌گیرد.",
      ar: "يعدّ التتابع الأيام المتتالية بتسجيل حقيقي، فاليوم الفائت يقصّره - ولن يملأ التطبيق يوما لم تسجّله، لأن اختراع رقم هو بالضبط نوع التلفيق الذي يتجنبه في كل مكان آخر. والبدء من جديد أمر طبيعي ولا يكلفك أي سجل.",
      zh: "连续天数统计的是有真实打卡的连续日子，所以漏掉一天会让它变短——应用不会替你补上没记录的一天，因为编造一个数字正是它在其他地方极力避免的。重新开始很正常，也不会让你失去任何历史记录。",
    },

    {
      key: 'app_cohort_comparison',
      match: /\b(what is the cohort comparison|compared to everyone|how do i compare to others in the data)(?:s|es|ing)?\b|مقایسه با گروه چیست|نسبت به همه|ما هي مقارنة الفئة|بالمقارنة مع الجميع|群体对比是什么|和所有人相比/i,
      en: "The cohort card compares you against the dataset the models were trained on, not against other users of this app - nobody's live account is read. It only appears when there's enough of your own data to place you meaningfully.",
      fa: "کارت گروه تو را با مجموعه‌داده‌ای که مدل‌ها رویش آموزش دیده‌اند مقایسه می‌کند، نه با کاربران دیگر این اپ - هیچ حساب زنده‌ای خوانده نمی‌شود. فقط وقتی ظاهر می‌شود که داده‌ی خودت به‌اندازه‌ی کافی باشد تا جایگاهت معنادار تعیین شود.",
      ar: "تقارنك بطاقة الفئة بمجموعة البيانات التي دُرّبت عليها النماذج، لا بمستخدمي هذا التطبيق الآخرين - فلا يُقرأ حساب حي لأحد. وتظهر فقط حين تتوفر بيانات كافية منك لتحديد موضعك بشكل ذي معنى.",
      zh: "群体对比卡片是把你和模型训练所用的数据集做比较，而不是和这个应用的其他用户比——没有任何人的实时账户被读取。只有当你自己的数据足够多、能有意义地定位你时它才会出现。",
    },

    {
      key: 'app_future_path_cards',
      match: /\b(what are the future path cards|the three future scenarios|future paths)(?:s|es|ing)?\b|کارت‌های مسیر آینده چیستند|سه سناریوی آینده|ما هي بطاقات المسار المستقبلي|السيناريوهات الثلاثة|未来路径卡片是什么|三种未来情景/i,
      en: "Three scenarios - gradual improvement, committed change, continued drift - each run through the real model on a constructed future input rather than being written as encouragement. That's why the numbers differ between them instead of all three saying something vague.",
      fa: "سه سناریو - بهبود تدریجی، تغییر متعهدانه، رانش ادامه‌دار - هرکدام روی یک ورودی ساخته‌شده‌ی آینده از مدل واقعی رد می‌شوند نه اینکه به‌عنوان تشویق نوشته شده باشند. برای همین است که عددهایشان با هم فرق دارد به‌جای اینکه هر سه چیزی مبهم بگویند.",
      ar: "ثلاثة سيناريوهات - تحسّن تدريجي، وتغيير ملتزم، وانجراف مستمر - يمر كل منها عبر النموذج الحقيقي على مدخل مستقبلي مُركَّب لا أن يُكتب تشجيعا. ولهذا تختلف أرقامها بدل أن تقول الثلاثة شيئا غامضا.",
      zh: "三种情景——逐步改善、坚定改变、继续漂移——每一种都是把构造出的未来输入送进真实模型跑出来的，而不是写来鼓励人的。这就是为什么它们的数字彼此不同，而不是三张卡都说些含糊的话。",
    },

    {
      key: 'app_whatif_which_field',
      match: /\b(which field should i sweep|what should i simulate|best field to test)(?:s|es|ing)?\b|کدام فیلد را بررسی کنم|چه چیزی را شبیه‌سازی کنم|أي حقل أفحص|ماذا أحاكي|该模拟哪个字段|测试哪个字段最好/i,
      en: "Start with whatever your result named as a top negative factor - that's the field the model says is costing you most right now, so its sweep is the one most likely to show real movement rather than a flat line.",
      fa: "از همان چیزی شروع کن که نتیجه‌ات به‌عنوان عامل منفی اصلی نام برده - همان فیلدی است که مدل می‌گوید همین حالا بیشترین هزینه را برایت دارد، پس بررسی‌اش محتمل‌ترین چیزی است که حرکت واقعی نشان می‌دهد نه یک خط صاف.",
      ar: "ابدأ بما سمّته نتيجتك عاملا سلبيا رئيسيا - فذلك هو الحقل الذي يقول النموذج إنه يكلفك أكثر الآن، فمسحه هو الأرجح أن يُظهر حركة حقيقية لا خطا مستقيما.",
      zh: "从你的结果里被点名为主要负面因素的那个字段开始——那是模型认为当前对你损耗最大的字段，所以扫描它最可能显示出真实的变化，而不是一条平直的线。",
    },

    {
      key: 'app_whatif_flat_line',
      match: /\b(the sweep is a flat line|nothing changes when i sweep|the graph doesnt move)(?:s|es|ing)?\b|نمودار بررسی صاف است|هیچ چیز تغییر نمیکند|خط المسح مستقيم|لا شيء يتغير|扫描出来是条直线|扫描时没有变化/i,
      en: "A flat sweep is a real result, not a failure: it means that field barely moves your score at your current values. The model weighs your whole day at once, so a field that isn't near a threshold for you can genuinely be inert while another swings a lot.",
      fa: "یک بررسیِ صاف یک نتیجه‌ی واقعی است نه یک شکست: یعنی آن فیلد با مقادیر فعلی تو به‌سختی امتیازت را جابه‌جا می‌کند. مدل کل روزت را یکجا می‌سنجد، پس فیلدی که برای تو نزدیک هیچ آستانه‌ای نیست می‌تواند واقعاً بی‌اثر باشد در حالی که فیلدی دیگر خیلی نوسان می‌کند.",
      ar: "المسح المستقيم نتيجة حقيقية لا فشل: يعني أن ذلك الحقل يكاد لا يحرك درجتك عند قيمك الحالية. فالنموذج يزن يومك كاملا دفعة واحدة، فحقل ليس قريبا من عتبة بالنسبة لك قد يكون خاملا فعلا بينما يتأرجح آخر كثيرا.",
      zh: "扫描结果是一条直线，这是真实的结果而不是故障：它意味着在你当前的数值下，那个字段几乎不影响你的分数。模型是把你一整天的数据一次性权衡的，所以某个对你而言并不接近阈值的字段确实可能毫无作用，而另一个却波动很大。",
    },

    {
      key: 'app_login_security',
      match: /\b(is my password safe|how is my password stored|is login secure)(?:s|es|ing)?\b|رمزم امن است|رمز عبور چطور ذخیره میشود|هل كلمة مروري آمنة|كيف تُخزن كلمة المرور|我的密码安全吗|密码是怎么存储的/i,
      en: "Passwords are stored hashed, never in readable form, and your session is a token held in your browser rather than your password being re-sent. There's no password-reset flow in this build, so a forgotten password means registering again.",
      fa: "رمزهای عبور به‌صورت هش‌شده ذخیره می‌شوند، هرگز به شکل خواندنی، و نشستت یک توکن است که در مرورگرت نگه داشته می‌شود نه اینکه رمزت دوباره فرستاده شود. در این نسخه فرایند بازیابی رمز وجود ندارد، پس رمز فراموش‌شده یعنی ثبت‌نام دوباره.",
      ar: "تُخزَّن كلمات المرور مجزّأة، لا بصيغة قابلة للقراءة أبدا، وجلستك رمز محفوظ في متصفحك لا إعادة إرسال لكلمة مرورك. ولا يوجد مسار لاستعادة كلمة المرور في هذا الإصدار، فنسيانها يعني التسجيل من جديد.",
      zh: "密码以哈希形式存储，绝不以可读形式保存，你的会话是保存在浏览器里的令牌，而不是反复发送你的密码。这个版本没有找回密码的流程，所以忘记密码就意味着需要重新注册。",
    },

    {
      key: 'app_accessibility',
      match: /\b(is it accessible|keyboard navigation|screen reader support|reduce motion accessibility)(?:s|es|ing)?\b|دسترس‌پذیری|ناوبری با کیبورد|پشتیبانی از صفحه‌خوان|إمكانية الوصول|التنقل بلوحة المفاتيح|دعم قارئ الشاشة|无障碍|键盘导航|屏幕阅读器支持/i,
      en: "Reduce-motion is honoured throughout, which turns off the animated background and the mascot's movement, and the theme includes a proper dark mode rather than an inverted filter. If you hit something that can't be reached by keyboard, that's worth reporting specifically.",
      fa: "کاهش حرکت در همه‌جا رعایت می‌شود که پس‌زمینه‌ی متحرک و حرکت ماسکوت را خاموش می‌کند، و تم شامل یک حالت تیره‌ی واقعی است نه یک فیلتر معکوس. اگر به چیزی برخوردی که با کیبورد قابل دسترسی نیست، مشخصاً ارزش گزارش‌دادن دارد.",
      ar: "يُحترم تقليل الحركة في كل مكان، فيوقف الخلفية المتحركة وحركة الشخصية الرمزية، ويتضمن المظهر وضعا داكنا حقيقيا لا مرشّح عكس ألوان. وإن صادفت شيئا لا يمكن الوصول إليه بلوحة المفاتيح، فذلك يستحق الإبلاغ تحديدا.",
      zh: "「减少动效」在全应用生效，会关闭动态背景和吉祥物的动作，主题也包含真正的深色模式而不是反色滤镜。如果你遇到无法用键盘访问的地方，那值得专门反馈。",
    },

    {
      key: 'app_how_much_history_kept',
      match: /\b(how long is my history kept|does old data expire|will my old days be deleted)(?:s|es|ing)?\b|تاریخچه‌ام چقدر نگه داشته میشود|داده قدیمی منقضی میشود|كم يُحفظ سجلي|هل تنتهي صلاحية البيانات القديمة|历史保存多久|旧数据会过期吗/i,
      en: "Nothing expires on its own - your days stay until you delete them or your account. The only thing that thins out over time is what a card chooses to show: most of them focus on recent weeks because that's what a trend is about, not because older days were removed.",
      fa: "هیچ چیزی خودبه‌خود منقضی نمی‌شود - روزهایت می‌مانند تا وقتی خودت یا حسابت را حذف کنی. تنها چیزی که با گذر زمان رقیق می‌شود آن چیزی است که یک کارت انتخاب می‌کند نشان بدهد: بیشترشان روی هفته‌های اخیر تمرکز می‌کنند چون روند درباره‌ی همان است، نه اینکه روزهای قدیمی‌تر حذف شده باشند.",
      ar: "لا شيء تنتهي صلاحيته من تلقاء نفسه - فأيامك تبقى حتى تحذفها أو تحذف حسابك. والشيء الوحيد الذي يقلّ مع الوقت هو ما تختار بطاقة عرضه: فمعظمها يركز على الأسابيع الأخيرة لأن هذا ما يعنيه الاتجاه، لا لأن الأيام الأقدم أُزيلت.",
      zh: "没有任何数据会自行过期——你的记录会一直保留，直到你删除它们或删除账户。随时间「变少」的只是卡片选择展示的内容：大多数卡片聚焦最近几周，因为趋势本来就是这个意思，而不是更早的日子被删掉了。",
    },

    {
      key: 'app_can_i_use_it_for_someone_else',
      match: /\b(can i track someone else|log for my child|use it for another person)(?:s|es|ing)?\b|میتوانم برای کس دیگری ثبت کنم|برای فرزندم استفاده کنم|هل أسجّل لشخص آخر|استخدامه لطفلي|能替别人记录吗|给孩子用/i,
      en: "Nothing stops you making a separate account for that, and separate is the right way - the rolling baseline and the whole history are per-account, so mixing two people's days into one account would make both readings wrong.",
      fa: "هیچ چیزی جلوی ساختن یک حساب جدا برای این کار را نمی‌گیرد، و جدابودن روش درست است - خط پایه‌ی متحرک و کل تاریخچه به‌ازای هر حساب‌اند، پس قاطی‌کردن روزهای دو نفر در یک حساب هر دو قرائت را غلط می‌کرد.",
      ar: "لا شيء يمنعك من إنشاء حساب منفصل لذلك، والفصل هو الطريقة الصحيحة - فخط الأساس المتحرك والسجل كله لكل حساب على حدة، فخلط أيام شخصين في حساب واحد كان سيجعل القراءتين خاطئتين.",
      zh: "没有任何限制阻止你为此单独建一个账户，而且分开才是正确的做法——滚动基线和整个历史都是按账户计算的，把两个人的日子混进一个账户会让两边的读数都出错。",
    },

    {
      key: 'app_result_saved_automatically',
      match: /\b(is my check in saved automatically|do i need to save my result|was my day recorded)(?:s|es|ing)?\b|چک‌این خودکار ذخیره میشود|باید نتیجه را ذخیره کنم|هل يُحفظ تسجيلي تلقائيا|هل أحتاج لحفظ نتيجتي|打卡会自动保存吗|需要手动保存结果吗/i,
      en: "Submitting a check-in records that day - it appears in your history without any extra step. The separate 'save these answers' card is for exporting a CSV copy of what you entered, which is a convenience, not what makes the day count.",
      fa: "ثبت یک چک‌این همان روز را ضبط می‌کند - بدون هیچ قدم اضافه‌ای در تاریخچه‌ات ظاهر می‌شود. کارت جداگانه‌ی «این پاسخ‌ها را ذخیره کن» برای خروجی‌گرفتن یک نسخه‌ی CSV از چیزی است که وارد کرده‌ای، که یک راحتی است نه چیزی که آن روز را به حساب می‌آورد.",
      ar: "إرسال التسجيل يسجّل ذلك اليوم - فيظهر في سجلك دون أي خطوة إضافية. أما بطاقة «احفظ هذه الإجابات» المنفصلة فهي لتصدير نسخة سي إس في مما أدخلته، وهي راحة لا ما يجعل اليوم يُحتسب.",
      zh: "提交打卡就已经记录了那一天——它会出现在你的历史里，不需要额外操作。另外那个「保存这些答案」的卡片是用来导出你所填内容的 CSV 副本的，那是个便利功能，并不是让这一天生效的关键。",
    },

    {
      key: 'app_two_checkins_same_day',
      match: /\b(can i check in twice in one day|two check ins same day|update todays check in)(?:s|es|ing)?\b|دو بار در یک روز چک‌این کنم|چک‌این امروز را به‌روز کنم|هل أسجّل مرتين في اليوم|تحديث تسجيل اليوم|一天能打卡两次吗|更新今天的打卡/i,
      en: "One day is one entry - a second submission for a date you already have is surfaced as a conflict rather than silently replacing the first, for the same reason the CSV importer refuses duplicate dates: overwriting a real entry to make an action succeed loses data you meant to keep.",
      fa: "یک روز یک ورودی است - ثبت دوم برای تاریخی که از قبل داری به‌عنوان تعارض نشان داده می‌شود نه اینکه بی‌صدا جای اولی را بگیرد، به همان دلیلی که وارد‌کننده‌ی CSV تاریخ‌های تکراری را رد می‌کند: بازنویسی یک ورودی واقعی برای موفق‌شدن یک کنش، داده‌ای را که می‌خواستی نگه داری از بین می‌برد.",
      ar: "اليوم الواحد مدخل واحد - والإرسال الثاني لتاريخ لديك أصلا يظهر كتعارض بدل أن يستبدل الأول صامتا، للسبب نفسه الذي يرفض به مستورد سي إس في التواريخ المكررة: فاستبدال مدخل حقيقي لإنجاح إجراء يفقدك بيانات قصدت الاحتفاظ بها.",
      zh: "一天对应一条记录——对已有日期的第二次提交会作为冲突提示出来，而不是悄悄替换第一条，原因和 CSV 导入拒绝重复日期一样：为了让某个操作成功而覆盖一条真实记录，会丢掉你本想保留的数据。",
    },

    
    // ====== AB. Demo details, recommendations, crisis guard and League privacy ======
    {
      key: 'app_demo_friends_count',
      match: /\b(how many demo friends|demo league friends|does demo include friends)(?:s|es|ing)?\b|چند دوست در دمو|دمو دوست دارد|كم صديقا في العرض التجريبي|هل يشمل الديمو أصدقاء|演示有多少好友|演示包含好友吗/i,
      en: "A demo session comes with connected demo friends so the League page has something real to show - rankings and shared categories that behave like the real thing rather than an empty page. They vanish with the demo when you leave.",
      fa: "یک نشست دمو با دوستان دموی متصل می‌آید تا صفحه‌ی لیگ چیز واقعی‌ای برای نشان‌دادن داشته باشد - رتبه‌بندی و دسته‌های اشتراکی که مثل چیز واقعی رفتار می‌کنند نه یک صفحه‌ی خالی. وقتی خارج شوی با دمو ناپدید می‌شوند.",
      ar: "تأتي جلسة العرض التجريبي بأصدقاء تجريبيين متصلين كي يكون لدى صفحة الدوري ما تعرضه فعلا - ترتيب وفئات مشاركة تتصرف كالحقيقية لا صفحة فارغة. ويختفون مع العرض التجريبي حين تغادر.",
      zh: "演示会话自带已连接的演示好友，这样联赛页面才有真实内容可展示——排名和分享类别的表现和真实情况一样，而不是一个空页面。当你退出时，它们会随演示一起消失。",
    },

    {
      key: 'app_demo_can_i_check_in',
      match: /\b(can i check in during a demo|submit a check in in demo mode)(?:s|es|ing)?\b|در حالت دمو میتوانم چک‌این کنم|ثبت در حالت دمو|هل أسجّل أثناء الديمو|إرسال تسجيل في وضع الديمو|演示中能打卡吗|演示模式下提交/i,
      en: "You can use the app normally inside a demo, including submitting a check-in - it just lands on the synthetic demo account, not yours. Nothing you do there reaches your real history, and it all goes away when you leave.",
      fa: "داخل یک دمو می‌توانی به‌طور عادی از اپ استفاده کنی، از جمله ثبت یک چک‌این - فقط روی همان حساب مصنوعی دمو می‌نشیند نه مال تو. هیچ کاری که آنجا می‌کنی به تاریخچه‌ی واقعی‌ات نمی‌رسد و با خروجت همه‌اش از بین می‌رود.",
      ar: "يمكنك استخدام التطبيق بشكل طبيعي داخل العرض التجريبي، بما في ذلك إرسال تسجيل - لكنه يقع على الحساب التجريبي الاصطناعي لا حسابك. ولا شيء تفعله هناك يصل إلى سجلك الحقيقي، ويزول كله عند مغادرتك.",
      zh: "在演示中你可以正常使用应用，包括提交打卡——只是它会落在合成的演示账户上，而不是你的账户。你在那里做的任何事都不会进入你的真实历史，退出时全部消失。",
    },

    {
      key: 'app_demo_realistic',
      match: /\b(is the demo data realistic|is demo data fake|are demo numbers real)(?:s|es|ing)?\b|داده دمو واقع‌گرایانه است|عددهای دمو واقعی‌اند|هل بيانات الديمو واقعية|هل أرقام الديمو حقيقية|演示数据真实吗|演示的数字是真的吗/i,
      en: "The inputs are synthetic but shaped to be realistic; the scores on top of them are produced by the same real trained model that scores your own days. So the pattern is constructed, the prediction is genuine - which is exactly what makes a demo worth showing.",
      fa: "ورودی‌ها مصنوعی‌اند اما طوری شکل گرفته‌اند که واقع‌گرایانه باشند؛ امتیازهای روی آن‌ها را همان مدل آموزش‌دیده‌ی واقعی می‌سازد که روزهای خودت را می‌سنجد. پس الگو ساختگی است و پیش‌بینی اصیل - و دقیقاً همین است که یک دمو را ارزشمند برای نشان‌دادن می‌کند.",
      ar: "المدخلات اصطناعية لكنها مصاغة لتكون واقعية؛ أما الدرجات فوقها فينتجها النموذج المدرَّب الحقيقي نفسه الذي يقيّم أيامك أنت. فالنمط مُركَّب والتنبؤ أصيل - وهذا بالضبط ما يجعل العرض التجريبي جديرا بالعرض.",
      zh: "输入数据是合成的，但被塑造得贴近真实；而基于它们算出的分数，来自与评估你自己那些日子完全相同的真实训练模型。所以模式是构造的，预测是真实的——这正是演示值得展示的原因。",
    },

    {
      key: 'app_import_after_demo',
      match: /\b(import my csv after a demo|does the demo affect my import)(?:s|es|ing)?\b|بعد از دمو فایل وارد کنم|دمو روی ورود داده اثر دارد|استيراد ملفي بعد الديمو|هل يؤثر الديمو على الاستيراد|演示后导入csv|演示会影响导入吗/i,
      en: "Leave the demo first, so you're back on your real account - an import while a demo session is active would land on the synthetic account and disappear with it. Once your real session is restored, the import behaves exactly as normal.",
      fa: "اول از دمو خارج شو تا روی حساب واقعی‌ات برگردی - یک ورود داده در حالی که نشست دمو فعال است روی حساب مصنوعی می‌نشیند و با آن ناپدید می‌شود. وقتی نشست واقعی‌ات برگشت، ورود داده دقیقاً عادی رفتار می‌کند.",
      ar: "غادر العرض التجريبي أولا كي تعود إلى حسابك الحقيقي - فالاستيراد أثناء جلسة تجريبية نشطة سيقع على الحساب الاصطناعي ويختفي معه. وبمجرد استعادة جلستك الحقيقية، يعمل الاستيراد كالمعتاد تماما.",
      zh: "先退出演示，回到你的真实账户——在演示会话仍处于活动状态时导入，数据会落在合成账户上并随之消失。真实会话恢复后，导入的行为就完全正常了。",
    },

    {
      key: 'app_recommendations_how_chosen',
      match: /\b(how are recommendations chosen|where do recommendations come from|why this recommendation)(?:s|es|ing)?\b|پیشنهادها چطور انتخاب میشوند|چرا این پیشنهاد|كيف تُختار التوصيات|لماذا هذه التوصية|建议是怎么选出来的|为什么是这条建议/i,
      en: "They come from the SHAP factors that are actively hurting your score on that prediction, matched to a library of concrete steps for those specific fields - which is why a healthy day can legitimately produce none, and why yours differ from someone else's.",
      fa: "از همان عامل‌های SHAP می‌آیند که در آن پیش‌بینی فعالانه به امتیازت آسیب می‌زنند، و به کتابخانه‌ای از قدم‌های مشخص برای همان فیلدها وصل می‌شوند - برای همین است که یک روز سالم می‌تواند به‌درستی هیچ پیشنهادی تولید نکند، و برای همین مال تو با مال کس دیگری فرق دارد.",
      ar: "تأتي من عوامل شاب التي تضرّ درجتك فعليا في ذلك التنبؤ، مطابَقةً بمكتبة من خطوات ملموسة لتلك الحقول بعينها - ولهذا قد لا ينتج يوم صحي أي توصية بحق، ولهذا تختلف توصياتك عن توصيات غيرك.",
      zh: "它们来自那次预测中正在拉低你分数的 SHAP 因素，并与针对这些具体字段的一套具体行动库相匹配——这就是为什么健康的一天完全可能一条建议都没有，也是为什么你的建议和别人不同。",
    },

    {
      key: 'app_recommendation_priority',
      match: /\b(what does high priority mean|recommendation priority|why is this marked high)(?:s|es|ing)?\b|اولویت بالا یعنی چه|اولویت پیشنهاد|ماذا تعني الأولوية العالية|أولوية التوصية|高优先级是什么意思|建议的优先级/i,
      en: "Priority reflects how much that factor is weighing on your score right now, not how hard the step is. A high-priority item is where the model says the most is at stake for you - it isn't a judgement about your effort.",
      fa: "اولویت بازتاب این است که آن عامل همین حالا چقدر روی امتیازت سنگینی می‌کند، نه اینکه آن قدم چقدر سخت است. یک مورد با اولویت بالا جایی است که مدل می‌گوید بیشترین چیز برای تو در خطر است - قضاوتی درباره‌ی تلاش تو نیست.",
      ar: "تعكس الأولوية مقدار ما يثقل به ذلك العامل على درجتك الآن، لا صعوبة الخطوة. فالبند عالي الأولوية هو حيث يقول النموذج إن الأكثر على المحك بالنسبة لك - وليس حكما على جهدك.",
      zh: "优先级反映的是那个因素当前对你分数的影响有多大，而不是这一步有多难做。高优先级的项目是模型认为对你而言影响最大的地方——它不是对你努力程度的评判。",
    },

    {
      key: 'app_recommendation_safety_note',
      match: /\b(what is the safety note|why does a recommendation have a warning)(?:s|es|ing)?\b|یادداشت ایمنی چیست|چرا پیشنهاد هشدار دارد|ما هي ملاحظة السلامة|لماذا للتوصية تحذير|安全提示是什么|建议为什么带警告/i,
      en: "Some steps carry a note because they aren't right for everyone - a suggestion that suits most people can be wrong if you have a specific condition or circumstance. The note is there so you can judge, rather than the app quietly assuming the general case fits you.",
      fa: "بعضی قدم‌ها یادداشت دارند چون برای همه مناسب نیستند - پیشنهادی که به‌درد بیشتر آدم‌ها می‌خورد می‌تواند اگر شرایط یا وضعیت خاصی داشته باشی اشتباه باشد. یادداشت آنجاست تا خودت قضاوت کنی، نه اینکه اپ بی‌صدا فرض کند حالت عمومی به تو می‌خورد.",
      ar: "بعض الخطوات تحمل ملاحظة لأنها ليست مناسبة للجميع - فاقتراح يلائم معظم الناس قد يكون خاطئا إن كانت لديك حالة أو ظرف خاص. والملاحظة موجودة كي تحكم أنت، بدل أن يفترض التطبيق صامتا أن الحالة العامة تنطبق عليك.",
      zh: "有些建议带有提示，是因为它们并非适合所有人——对多数人合适的建议，如果你有特定的身体状况或处境，可能就不合适。这个提示的存在是为了让你自己判断，而不是让应用默默假定通用情况适用于你。",
    },

    {
      key: 'app_crisis_response',
      match: /\b(what if i say something serious|the app gave me a crisis message|why did it show helplines)(?:s|es|ing)?\b|اگر چیز جدی‌ای بگویم|برنامه پیام بحران داد|ماذا لو قلت شيئا خطيرا|التطبيق أعطاني رسالة أزمة|如果我说了严重的话|应用给了危机提示/i,
      en: "If a message reads as describing real crisis-level distress, the coach steps outside its normal data-driven answers and responds with grounding language plus real crisis-line information. It's deliberately not clever there - a rule-based wellness tool is not the right thing to be improvising in that moment.",
      fa: "اگر پیامی به نظر برسد که پریشانیِ واقعاً بحرانی را توصیف می‌کند، مربی از پاسخ‌های داده‌محور عادی‌اش بیرون می‌آید و با زبانی آرام‌کننده به‌علاوه اطلاعات واقعی خطوط بحران جواب می‌دهد. عمداً آنجا زیرک نیست - یک ابزار سلامتِ قانون‌محور چیز درستی برای بداهه‌گویی در آن لحظه نیست.",
      ar: "إن قُرئت رسالة على أنها تصف ضائقة بمستوى أزمة حقيقية، يخرج المدرب عن إجاباته المعتادة القائمة على البيانات ويردّ بلغة مُطمئنة مع معلومات حقيقية عن خطوط الأزمات. وهو ليس بارعا هناك عن قصد - فأداة عافية قائمة على قواعد ليست الشيء الصحيح للارتجال في تلك اللحظة.",
      zh: "如果某条消息读起来像是在描述真正危机级别的痛苦，教练会跳出它平常基于数据的回答方式，用安抚性的语言加上真实的求助热线信息来回应。它在那里刻意不「聪明」——一个基于规则的健康工具，不该在那种时刻即兴发挥。",
    },

    {
      key: 'app_coach_off_topic',
      match: /\b(coach wont answer my question|it says thats off topic|why did it refuse)(?:s|es|ing)?\b|مربی جواب نمیدهد|میگوید خارج از موضوع است|المدرب يرفض الإجابة|يقول هذا خارج الموضوع|教练不回答我的问题|它说这是无关话题/i,
      en: "The coach keeps to digital wellbeing and this app, and says so instead of improvising an answer about something it has no basis for. If your question was on-topic but got refused, rephrasing it shorter and more concretely usually clears the match threshold.",
      fa: "مربی به بهزیستی دیجیتال و همین اپ می‌چسبد و همین را می‌گوید به‌جای اینکه درباره‌ی چیزی که هیچ مبنایی برایش ندارد جواب بداهه بسازد. اگر سؤالت در موضوع بود ولی رد شد، بازنویسی کوتاه‌تر و مشخص‌تر معمولاً از آستانه‌ی تطبیق رد می‌شود.",
      ar: "يلتزم المدرب بالعافية الرقمية وهذا التطبيق، ويقول ذلك بدل ارتجال إجابة عن شيء لا أساس لديه فيه. وإن كان سؤالك ضمن الموضوع لكنه رُفض، فإعادة صياغته أقصر وأكثر تحديدا تتجاوز عادة عتبة المطابقة.",
      zh: "教练只回答数字健康和这个应用相关的问题，并会直说，而不是就它毫无依据的事情即兴编造答案。如果你的问题本来是相关的却被拒答，把它改得更短、更具体，通常就能越过匹配阈值。",
    },

    {
      key: 'app_where_is_my_invite_code_exactly',
      match: /\b(invite code not visible|cant see my invite code|invite code missing)(?:s|es|ing)?\b|کد دعوت دیده نمیشود|کد دعوتم را نمیبینم|رمز الدعوة غير ظاهر|لا أرى رمز دعوتي|看不到邀请码|邀请码不见了/i,
      en: "The code appears at the top of the League page once you've accepted the League rules - if you haven't done that step yet, that's why it isn't showing. It doesn't change afterwards, so it can be handed out once and keep working.",
      fa: "کد بعد از اینکه قوانین لیگ را پذیرفتی بالای صفحه‌ی لیگ ظاهر می‌شود - اگر هنوز آن مرحله را انجام نداده‌ای، دلیلش همان است. بعدش عوض نمی‌شود، پس می‌شود یک بار دادش و همچنان کار کند.",
      ar: "يظهر الرمز أعلى صفحة الدوري بمجرد قبولك قواعد الدوري - فإن لم تُنجز تلك الخطوة بعد، فهذا سبب عدم ظهوره. ولا يتغير بعدها، فيمكن إعطاؤه مرة ويظل يعمل.",
      zh: "接受联赛规则之后，邀请码会显示在联赛页面顶部——如果你还没完成那一步，那就是它没显示的原因。之后它不会改变，所以给出去一次就可以一直用。",
    },

    {
      key: 'app_league_rules',
      match: /\b(what are the league rules|why do i have to accept rules|league agreement)(?:s|es|ing)?\b|قوانین لیگ چیست|چرا باید قوانین را بپذیرم|ما هي قواعد الدوري|لماذا أقبل القواعد|联赛规则是什么|为什么要接受规则/i,
      en: "Accepting the rules is the point where you acknowledge that the League shares some of your data with people you connect to, and agree to the conduct expectations for chat. It gates the invite code precisely so nobody shares anything before seeing what sharing means.",
      fa: "پذیرفتن قوانین همان نقطه‌ای است که تصدیق می‌کنی لیگ بخشی از داده‌ات را با کسانی که به آن‌ها وصل می‌شوی به اشتراک می‌گذارد، و با انتظارات رفتاری چت موافقت می‌کنی. دقیقاً برای همین جلوی کد دعوت را می‌گیرد تا کسی پیش از دیدن معنای اشتراک‌گذاری چیزی به اشتراک نگذارد.",
      ar: "قبول القواعد هو النقطة التي تقرّ فيها بأن الدوري يشارك بعض بياناتك مع من تتصل بهم، وتوافق على توقعات السلوك في المحادثة. وهو يحجب رمز الدعوة تحديدا كي لا يشارك أحد شيئا قبل أن يرى معنى المشاركة.",
      zh: "接受规则是你确认「联赛会把你的部分数据分享给你连接的人」并同意聊天行为准则的那一步。它之所以卡在邀请码之前，正是为了不让任何人在了解分享含义之前就先分享出去。",
    },

    {
      key: 'app_league_privacy_worry',
      match: /\b(is the league safe|do i have to share anything|can i use the league without sharing)(?:s|es|ing)?\b|لیگ امن است|باید چیزی به اشتراک بگذارم|هل الدوري آمن|هل يجب أن أشارك شيئا|联赛安全吗|必须分享什么吗/i,
      en: "The four sharing categories are all individually optional, so you can connect and share none of them if you like - you'd still get the chat. Sharing is per-friend and revocable at any time, and no raw check-in is ever shared regardless of what you enable.",
      fa: "هر چهار دسته‌ی اشتراک‌گذاری جداگانه اختیاری‌اند، پس اگر بخواهی می‌توانی وصل شوی و هیچ‌کدام را به اشتراک نگذاری - باز هم چت را داری. اشتراک‌گذاری به‌ازای هر دوست است و هر لحظه قابل پس‌گرفتن، و صرف‌نظر از اینکه چه چیزی را فعال کنی هرگز هیچ چک‌این خامی به اشتراک گذاشته نمی‌شود.",
      ar: "فئات المشاركة الأربع كلها اختيارية على حدة، فيمكنك الاتصال دون مشاركة أي منها إن شئت - وستحصل على المحادثة رغم ذلك. والمشاركة لكل صديق وقابلة للسحب في أي وقت، ولا يُشارك أي تسجيل خام أبدا مهما فعّلت.",
      zh: "四个分享类别都是各自可选的，所以你完全可以连接但一个都不分享——聊天照样能用。分享是按好友设置、随时可撤回的，而且无论你启用什么，原始打卡内容都绝不会被分享。",
    },

    {
      key: 'app_dark_mode_at_night',
      match: /\b(is there a night mode|does the theme change at night|auto switch theme)(?:s|es|ing)?\b|حالت شب دارد|تم شب‌ها عوض میشود|هل يوجد وضع ليلي|هل يتغير المظهر ليلا|有夜间模式吗|主题会在晚上自动切换吗/i,
      en: "There's a dark theme, but it doesn't switch itself by clock - it follows your explicit choice, or your system preference if you pick 'system', which is what usually handles the night switch for you at the OS level.",
      fa: "یک تم تیره هست، اما خودش با ساعت عوض نمی‌شود - از انتخاب صریح تو پیروی می‌کند، یا اگر «سیستم» را انتخاب کنی از ترجیح سیستمت، که معمولاً همان است که تعویض شبانه را در سطح سیستم‌عامل برایت انجام می‌دهد.",
      ar: "يوجد مظهر داكن، لكنه لا يتبدّل بالساعة من تلقاء نفسه - بل يتبع اختيارك الصريح، أو تفضيل نظامك إن اخترت «النظام»، وهو ما يتولى عادة التبديل الليلي على مستوى نظام التشغيل.",
      zh: "有深色主题，但它不会按时间自动切换——它遵循你的明确选择，或者在你选「跟随系统」时遵循系统偏好，而系统通常已经在操作系统层面帮你处理了夜间切换。",
    },

    
    // ====== AC. Factors, confidence, challenges, alerts and design rationale ======
    {
      key: 'app_field_why_this_is_a_factor',
      match: /\b(why is this a top factor|why did this field matter|why is sleep my top factor)(?:s|es|ing)?\b|چرا این عامل اصلی است|چرا این فیلد مهم بود|لماذا هذا عامل رئيسي|لماذا همّ هذا الحقل|为什么这是主要因素|为什么这个字段重要/i,
      en: "A field ranks high because its value on that day pushed your score more than the others did, measured against what the model expected. It's about the size of the push, not about the field being important in general - which is why your top factors change between days.",
      fa: "یک فیلد بالا می‌آید چون مقدارش در آن روز بیشتر از بقیه امتیازت را جابه‌جا کرده، سنجیده در برابر آنچه مدل انتظار داشت. درباره‌ی اندازه‌ی هُل‌دادن است نه اینکه آن فیلد به‌طور کلی مهم باشد - و برای همین عامل‌های اصلی‌ات بین روزها عوض می‌شوند.",
      ar: "يرتفع ترتيب حقل لأن قيمته في ذلك اليوم دفعت درجتك أكثر من غيره، مقيسةً بما توقعه النموذج. والأمر يتعلق بحجم الدفع لا بأهمية الحقل عموما - ولهذا تتغير عواملك الرئيسية بين يوم وآخر.",
      zh: "某个字段排名靠前，是因为它那一天的数值相对模型的预期，比其他字段更大地推动了你的分数。这关乎推动的幅度，而不是这个字段本身有多重要——这也是为什么你的主要因素每天都会变。",
    },

    {
      key: 'app_field_positive_factor',
      match: /\b(what is a positive factor|green factor|a factor helping my score)(?:s|es|ing)?\b|عامل مثبت چیست|عاملی که به امتیازم کمک میکند|ما هو العامل الإيجابي|عامل يساعد درجتي|正面因素是什么|帮助我分数的因素/i,
      en: "Factors come with a direction: some pushed your score up, some pulled it down. The ones helping you are worth reading too - they name what's already working, which is what a recommendation list alone never tells you.",
      fa: "عامل‌ها جهت دارند: بعضی امتیازت را بالا برده‌اند و بعضی پایین کشیده‌اند. آن‌هایی که به تو کمک می‌کنند هم ارزش خواندن دارند - نام می‌برند چه چیزی از قبل دارد کار می‌کند، چیزی که فهرست پیشنهادها به‌تنهایی هرگز به تو نمی‌گوید.",
      ar: "للعوامل اتجاه: بعضها دفع درجتك للأعلى وبعضها سحبها للأسفل. وتلك التي تساعدك تستحق القراءة أيضا - فهي تسمّي ما ينجح لديك بالفعل، وهو ما لا تخبرك به قائمة التوصيات وحدها أبدا.",
      zh: "因素是带方向的：有些把你的分数推高，有些往下拉。那些在帮你的因素同样值得看——它们指出了什么已经在起作用，而这是单看建议清单永远得不到的信息。",
    },

    {
      key: 'app_result_confidence_low',
      match: /\b(my confidence is low|why is confidence low|low confidence result)(?:s|es|ing)?\b|اطمینانم پایین است|چرا اطمینان پایین است|ثقتي منخفضة|لماذا الثقة منخفضة|我的置信度很低|为什么置信度低/i,
      en: "Low confidence means your inputs sit between two classes rather than clearly inside one - it says nothing about whether your day was good or bad. It's also the signal that a small change could flip your class while the score barely moves.",
      fa: "اطمینان پایین یعنی ورودی‌هایت به‌جای اینکه به‌روشنی داخل یک دسته باشند بین دو دسته نشسته‌اند - هیچ چیزی درباره‌ی خوب یا بد بودن روزت نمی‌گوید. ضمناً همان سیگنالی است که می‌گوید یک تغییر کوچک می‌تواند دسته‌ات را عوض کند در حالی که امتیاز به‌سختی تکان می‌خورد.",
      ar: "الثقة المنخفضة تعني أن مدخلاتك تقع بين فئتين بدل أن تكون داخل واحدة بوضوح - ولا تقول شيئا عن كون يومك جيدا أو سيئا. وهي أيضا الإشارة إلى أن تغييرا صغيرا قد يقلب فئتك بينما تكاد الدرجة لا تتحرك.",
      zh: "低置信度意味着你的输入处在两个类别之间，而不是清楚地落在某一个类别里——它完全不说明你这一天是好是坏。它同时也是一个信号：微小的变化就可能翻转你的类别，而分数几乎不动。",
    },

    {
      key: 'app_ood_check',
      match: /\b(is today unusual for the model|out of distribution|today is strange for the model)(?:s|es|ing)?\b|امروز برای مدل غیرعادی است|خارج از توزیع|هل اليوم غير معتاد للنموذج|خارج التوزيع|今天对模型来说异常吗|超出分布/i,
      en: "There's a check for whether today's combination of inputs looks unlike what the model was trained on. If it flags, the prediction is still real but deserves more scepticism - the model is extrapolating rather than recognising a familiar pattern.",
      fa: "بررسی‌ای هست برای اینکه آیا ترکیب ورودی‌های امروز شبیه چیزی که مدل رویش آموزش دیده هست یا نه. اگر علامت بزند، پیش‌بینی هنوز واقعی است ولی شک بیشتری می‌طلبد - مدل دارد برون‌یابی می‌کند نه اینکه الگویی آشنا را بشناسد.",
      ar: "يوجد فحص لما إذا كان مزيج مدخلات اليوم يبدو مختلفا عمّا دُرّب عليه النموذج. وإن أشار، فالتنبؤ يبقى حقيقيا لكنه يستحق شكا أكبر - فالنموذج يستقرئ بدل أن يتعرّف على نمط مألوف.",
      zh: "系统会检查今天的输入组合是否和模型训练时见过的数据不太一样。如果被标记出来，预测仍然是真实的，但值得多一分怀疑——模型此时是在外推，而不是识别一个熟悉的模式。",
    },

    {
      key: 'app_weekly_challenge_progress',
      match: /\b(how is challenge progress counted|why is my challenge progress zero|challenge not counting)(?:s|es|ing)?\b|پیشرفت چالش چطور شمرده میشود|چرا پیشرفت چالشم صفر است|كيف يُحتسب تقدم التحدي|لماذا تقدمي صفر|挑战进度怎么算|为什么进度是零/i,
      en: "Progress counts your real logged days in the current week, and days you marked as exceptions are deliberately excluded - a day you explicitly said was unusual shouldn't score you. That's the usual reason a streak challenge reads zero when you know you checked in.",
      fa: "پیشرفت روزهای واقعی ثبت‌شده‌ات در هفته‌ی جاری را می‌شمارد، و روزهایی که استثنا علامت زده‌ای عمداً کنار گذاشته می‌شوند - روزی که خودت صریح گفتی غیرعادی بوده نباید برایت امتیاز بیاورد. همین معمولاً دلیل صفر بودن یک چالش زنجیره‌ای است وقتی می‌دانی چک‌این کرده‌ای.",
      ar: "يعدّ التقدم أيامك المسجلة الحقيقية في الأسبوع الحالي، والأيام التي وسمتها كاستثناءات تُستبعد عمدا - فيوم قلت صراحة إنه غير معتاد لا ينبغي أن يسجّل لك. وهذا عادة سبب قراءة تحدي التتابع صفرا وأنت تعلم أنك سجّلت.",
      zh: "进度统计的是你在本周真实记录的天数，而你标记为例外的日子会被刻意排除——你自己明确说过不寻常的一天，不该为你计分。当你明明打过卡却看到连续挑战显示为零时，这通常就是原因。",
    },

    {
      key: 'app_risk_alert_dismiss',
      match: /\b(can i dismiss a risk alert|how do i clear an alert|alert keeps showing)(?:s|es|ing)?\b|میتوانم هشدار را ببندم|هشدار مدام نمایش داده میشود|هل يمكنني إغلاق تنبيه|التنبيه يستمر بالظهور|能关掉风险提醒吗|提醒一直出现/i,
      en: "Alerts reflect a live condition in your history rather than being messages to acknowledge, so one stays while the pattern that triggered it is still true and goes on its own once the pattern changes. If it feels wrong, the alert names the days it was computed from.",
      fa: "هشدارها به‌جای اینکه پیام‌هایی برای تأیید باشند، یک وضعیت زنده در تاریخچه‌ات را بازتاب می‌دهند، پس تا وقتی الگویی که آن را فعال کرده هنوز درست است می‌ماند و به‌محض تغییر الگو خودش می‌رود. اگر اشتباه حس می‌شود، هشدار روزهایی را که از رویشان محاسبه شده نام می‌برد.",
      ar: "تعكس التنبيهات حالة حية في سجلك بدل أن تكون رسائل تُقرّ باستلامها، فيبقى التنبيه ما دام النمط الذي أطلقه صحيحا ويزول من تلقاء نفسه حين يتغير النمط. وإن بدا خاطئا، فالتنبيه يذكر الأيام التي حُسب منها.",
      zh: "提醒反映的是你历史中一个持续存在的状况，而不是需要你确认的消息，所以只要触发它的模式仍然成立它就会一直在，模式改变后它自己就消失了。如果你觉得它不对，提醒里会说明它是根据哪些天算出来的。",
    },

    {
      key: 'app_correlation_strength',
      match: /\b(how strong is the correlation|is this correlation meaningful|weak correlation)(?:s|es|ing)?\b|همبستگی چقدر قوی است|این همبستگی معنادار است|ما مدى قوة الارتباط|هل هذا الارتباط ذو معنى|相关性有多强|这个相关性有意义吗/i,
      en: "Correlation cards only appear once there are enough days for a relationship not to be noise, and they're phrased as 'moved together with' rather than 'caused'. Two things moving together in your data is a real observation about your data - it is not evidence that one drives the other.",
      fa: "کارت‌های همبستگی فقط وقتی ظاهر می‌شوند که روزهای کافی باشد تا یک رابطه نویز نباشد، و با عبارت «با هم حرکت کردند» بیان می‌شوند نه «باعث شد». حرکت دو چیز با هم در داده‌ی تو یک مشاهده‌ی واقعی درباره‌ی داده‌ی توست - شاهدی بر این نیست که یکی دیگری را می‌راند.",
      ar: "لا تظهر بطاقات الارتباط إلا حين تتوفر أيام كافية كي لا تكون العلاقة ضجيجا، وتُصاغ بعبارة «تحركا معا» لا «تسبّب». وتحرّك شيئين معا في بياناتك ملاحظة حقيقية عن بياناتك - لا دليلا على أن أحدهما يقود الآخر.",
      zh: "相关性卡片只有在天数足够、关系不至于只是噪声时才会出现，并且用「一起变动」而不是「导致」来表述。你的数据里两件事一起变动，是关于你数据的真实观察——但它不是其中一个驱动另一个的证据。",
    },

    {
      key: 'app_export_for_doctor',
      match: /\b(can i show this to my doctor|export for a therapist|take this to a professional)(?:s|es|ing)?\b|میتوانم به پزشکم نشان بدهم|برای درمانگر خروجی بگیرم|هل أريه لطبيبي|تصدير للمعالج|能给医生看吗|导出给治疗师/i,
      en: "The PDF report is built for that: it carries a specific day's score, class, factors and recommendations in your current language. Bring it as material about your habits, not as an assessment - the app is explicit that it isn't a diagnostic instrument.",
      fa: "گزارش PDF برای همین ساخته شده: امتیاز، دسته، عامل‌ها و پیشنهادهای یک روز مشخص را به زبان فعلی‌ات با خود می‌برد. آن را به‌عنوان مادّه‌ای درباره‌ی عادت‌هایت ببر نه به‌عنوان یک ارزیابی - اپ صریح می‌گوید که ابزار تشخیصی نیست.",
      ar: "تقرير بي دي إف مصنوع لذلك: يحمل درجة يوم بعينه وفئته وعوامله وتوصياته بلغتك الحالية. خذه كمادة عن عاداتك لا كتقييم - فالتطبيق صريح في أنه ليس أداة تشخيص.",
      zh: "PDF 报告正是为此而设：它包含某一天的分数、类别、影响因素和建议，并使用你当前的语言。把它当作关于你习惯的素材带过去，而不是一份评估——应用明确说明它不是诊断工具。",
    },

    {
      key: 'app_what_if_i_lie',
      match: /\b(what if i enter wrong numbers on purpose|can i cheat the score|what if i inflate my numbers)(?:s|es|ing)?\b|اگر عمدا عدد اشتباه وارد کنم|میتوانم امتیاز را تقلب کنم|ماذا لو أدخلت أرقاما خاطئة عمدا|هل أغش الدرجة|故意填错数字会怎样|能作弊刷分吗/i,
      en: "You can, and the only person it misleads is you - there's no leaderboard against strangers and no reward for a high number. The app's value is the comparison against your own past, which is exactly what inaccurate entries destroy.",
      fa: "می‌توانی، و تنها کسی را که گمراه می‌کند خودتی - هیچ جدول رده‌بندی در برابر غریبه‌ها نیست و هیچ پاداشی برای عدد بالا. ارزش اپ همان مقایسه با گذشته‌ی خودت است، و دقیقاً همان چیزی است که ورودی‌های نادرست نابودش می‌کنند.",
      ar: "تستطيع، والوحيد الذي يُضلَّل هو أنت - فلا لوحة صدارة أمام غرباء ولا مكافأة على رقم مرتفع. وقيمة التطبيق هي المقارنة بماضيك أنت، وهو بالضبط ما تدمّره الإدخالات غير الدقيقة.",
      zh: "你可以这么做，而唯一被误导的人是你自己——这里没有和陌生人比拼的排行榜，高分也没有任何奖励。应用的价值在于和你自己的过去做比较，而不准确的输入恰恰摧毁的就是这一点。",
    },

    {
      key: 'app_minimum_days_summary',
      match: /\b(how many days do i need|when does everything unlock|what needs how many days)(?:s|es|ing)?\b|چند روز لازم دارم|کی همه چیز باز میشود|كم يوما أحتاج|متى يُفتح كل شيء|我需要多少天|什么时候全部解锁/i,
      en: "Roughly: one day gives you a real score and factors; about a week brings the narrative, weekly comparisons and the letter from your future self; correlation cards and the decline-based risk rule need more than that. Cards stay hidden until they can say something honest rather than showing a placeholder.",
      fa: "تقریباً: یک روز به تو امتیاز واقعی و عامل‌ها می‌دهد؛ حدود یک هفته روایت، مقایسه‌های هفتگی و نامه‌ی خودِ آینده را می‌آورد؛ کارت‌های همبستگی و قاعده‌ی خطرِ مبتنی بر افت بیشتر از این می‌خواهند. کارت‌ها تا وقتی نتوانند چیز صادقانه‌ای بگویند پنهان می‌مانند نه اینکه جانگهدار نشان بدهند.",
      ar: "تقريبا: يوم واحد يمنحك درجة حقيقية وعوامل؛ ونحو أسبوع يجلب السرد والمقارنات الأسبوعية ورسالة نفسك المستقبلية؛ أما بطاقات الارتباط وقاعدة الخطر المبنية على التراجع فتحتاج أكثر. وتبقى البطاقات مخفية حتى تستطيع قول شيء صادق بدل عرض عنصر نائب.",
      zh: "大致来说：一天就能得到真实的分数和影响因素；大约一周会带来叙述卡、周对比和来自未来自己的信；相关性卡片和基于下降趋势的风险规则需要更多天。卡片在能说出有依据的内容之前会一直隐藏，而不是显示占位内容。",
    },

    {
      key: 'app_start_over',
      match: /\b(can i start over|reset my data|delete all my check ins)(?:s|es|ing)?\b|میتوانم از نو شروع کنم|همه چک‌این‌هایم را حذف کنم|هل يمكنني البدء من جديد|حذف كل تسجيلاتي|能重新开始吗|删除我所有的打卡/i,
      en: "There isn't a 'clear my history but keep the account' button. The two real options are marking days as exceptions so they stop affecting your averages while staying visible, or deleting the account and registering again - which is permanent, so export anything you want first.",
      fa: "دکمه‌ی «تاریخچه‌ام را پاک کن ولی حساب را نگه دار» وجود ندارد. دو گزینه‌ی واقعی این‌اند: علامت‌زدن روزها به‌عنوان استثنا تا دیگر روی میانگین‌هایت اثر نگذارند ولی دیده شوند، یا حذف حساب و ثبت‌نام دوباره - که دائمی است، پس اول هرچه می‌خواهی خروجی بگیر.",
      ar: "لا يوجد زر «امسح سجلي واحتفظ بالحساب». والخياران الحقيقيان هما وسم الأيام كاستثناءات فتتوقف عن التأثير على متوسطاتك مع بقائها مرئية، أو حذف الحساب والتسجيل من جديد - وهو دائم، فصدّر ما تريد أولا.",
      zh: "没有「清空历史但保留账户」这样的按钮。真正的两个选项是：把那些日子标记为例外，让它们不再影响平均值但仍然可见；或者删除账户后重新注册——那是永久性的，所以先导出你想留下的东西。",
    },

    {
      key: 'app_offline_after_load',
      match: /\b(what if i go offline mid session|does it work if my connection drops)(?:s|es|ing)?\b|اگر وسط کار آفلاین شوم|اگر اتصالم قطع شود|ماذا لو انقطع اتصالي أثناء الجلسة|中途断网会怎样|连接断了还能用吗/i,
      en: "Pages you've already loaded stay on screen, but anything that needs the server - submitting, predicting, loading history, the League - will fail with a clear error rather than appearing to work. Nothing is queued for later, so retry once you're back.",
      fa: "صفحه‌هایی که قبلاً بارگذاری شده‌اند روی صفحه می‌مانند، اما هر چیزی که به سرور نیاز دارد - ثبت، پیش‌بینی، بارگذاری تاریخچه، لیگ - با یک خطای شفاف شکست می‌خورد نه اینکه وانمود کند کار می‌کند. هیچ چیزی برای بعد در صف نمی‌ماند، پس وقتی برگشتی دوباره امتحان کن.",
      ar: "الصفحات التي حمّلتها تبقى على الشاشة، لكن أي شيء يحتاج الخادم - الإرسال، التنبؤ، تحميل السجل، الدوري - سيفشل بخطأ واضح لا أن يبدو وكأنه يعمل. ولا شيء يُوضع في طابور للاحق، فأعد المحاولة حين تعود.",
      zh: "已经加载好的页面会留在屏幕上，但任何需要服务器的操作——提交、预测、加载历史、联赛——都会以明确的错误失败，而不是假装成功。没有任何内容会排队等以后再发，所以恢复网络后重试即可。",
    },

    {
      key: 'app_why_rule_based_coach',
      match: /\b(why isnt the coach a real llm|why rule based instead of ai|why not use gpt)(?:s|es|ing)?\b|چرا مربی یک مدل زبانی واقعی نیست|چرا قانون‌محور|لماذا ليس المدرب نموذجا لغويا|لماذا قائم على القواعد|为什么教练不是真的大模型|为什么用规则而不是ai/i,
      en: "Because every answer here is supposed to trace back to your own numbers, and a language model would happily produce a fluent sentence about data it never read. The rule-based engine can only answer from what you actually logged - and when it can't, it says so. The optional connector exists for when you do want a language model.",
      fa: "چون قرار است هر جوابی اینجا به عددهای خودت برگردد، و یک مدل زبانی با کمال میل جمله‌ای روان درباره‌ی داده‌ای که هرگز نخوانده می‌سازد. موتور قانون‌محور فقط می‌تواند از چیزی که واقعاً ثبت کرده‌ای جواب بدهد - و وقتی نمی‌تواند، می‌گوید. کانکتور اختیاری برای وقتی هست که واقعاً یک مدل زبانی بخواهی.",
      ar: "لأن كل إجابة هنا يُفترض أن تعود إلى أرقامك أنت، ونموذج لغوي سينتج بكل سرور جملة سلسة عن بيانات لم يقرأها قط. أما المحرك القائم على القواعد فلا يستطيع الإجابة إلا مما سجّلته فعلا - وحين لا يستطيع، يقول ذلك. والموصّل الاختياري موجود لحين تريد فعلا نموذجا لغويا.",
      zh: "因为这里的每个回答都应当能追溯到你自己的数字，而语言模型会很乐意就它从未读过的数据生成一段流畅的句子。基于规则的引擎只能从你实际记录的内容作答——做不到时它会直说。可选的连接器就是为你确实想要语言模型的时候准备的。",
    },

    
    // ====== AD. Logging cadence, backfilling, chat problems, the letter and training data ======
    {
      key: 'app_checkin_takes_too_long_daily',
      match: /\b(do i have to do this every day|is daily required|what if i only log sometimes)(?:s|es|ing)?\b|باید هر روز انجام بدهم|اگر فقط گاهی ثبت کنم|هل يجب أن أفعل هذا يوميا|ماذا لو سجّلت أحيانا|必须每天做吗|如果只是偶尔记录/i,
      en: "Daily isn't required, but the app compares you to yourself, so scattered days give you a weaker comparison than consistent ones. Logging three or four days a week honestly beats logging seven days with guessed numbers.",
      fa: "روزانه اجباری نیست، اما اپ تو را با خودت مقایسه می‌کند، پس روزهای پراکنده مقایسه‌ی ضعیف‌تری از روزهای منظم به تو می‌دهند. ثبت صادقانه‌ی سه چهار روز در هفته از ثبت هفت روز با عددهای حدسی بهتر است.",
      ar: "اليومي ليس إلزاميا، لكن التطبيق يقارنك بنفسك، فالأيام المتفرقة تمنحك مقارنة أضعف من المنتظمة. وتسجيل ثلاثة أو أربعة أيام أسبوعيا بصدق أفضل من تسجيل سبعة بأرقام مخمّنة.",
      zh: "并不要求每天都做，但应用是拿你和你自己比较的，所以零散的记录比规律的记录得到的对比更弱。诚实地一周记录三四天，胜过七天都填猜出来的数字。",
    },

    {
      key: 'app_forgot_to_log_yesterday',
      match: /\b(i forgot to log yesterday|can i add a past day|backfill a missed day)(?:s|es|ing)?\b|دیروز یادم رفت ثبت کنم|میتوانم روز گذشته را اضافه کنم|نسيت التسجيل أمس|هل أضيف يوما سابقا|昨天忘记记录了|能补录过去的一天吗/i,
      en: "The CSV import is the way to add days you missed - one row per day with its own date, which is exactly what backfilling is. The template gives you the header and two example rows so the format isn't guesswork.",
      fa: "ورود CSV راه اضافه‌کردن روزهایی است که از دست داده‌ای - یک ردیف برای هر روز با تاریخ خودش، که دقیقاً همان پرکردن گذشته است. قالب سطر عنوان و دو ردیف نمونه را به تو می‌دهد تا فرمت حدسی نباشد.",
      ar: "استيراد سي إس في هو طريقة إضافة الأيام التي فاتتك - صف لكل يوم بتاريخه، وهذا بالضبط معنى الملء بأثر رجعي. والقالب يمنحك صف العناوين وصفَّي مثال كي لا يكون التنسيق تخمينا.",
      zh: "CSV 导入就是补录漏掉日子的方式——每天一行、各自带日期，这正是补录的含义。模板会给出表头和两行示例，所以格式不用靠猜。",
    },

    {
      key: 'app_import_vs_manual',
      match: /\b(should i import or type|csv or manual entry|whats the difference between importing and filling the form)(?:s|es|ing)?\b|وارد کنم یا تایپ|تفاوت ورود فایل و پر کردن فرم|أستورد أم أكتب|الفرق بين الاستيراد وملء النموذج|该导入还是手动填|导入和填表有什么区别/i,
      en: "They produce the same thing - a scored day in your history. The form is for today; the import is for many days at once, typically backfilling. The importer recomputes the derived columns either way, so neither route can inject a hand-edited ratio.",
      fa: "هر دو یک چیز تولید می‌کنند - یک روز امتیازگرفته در تاریخچه‌ات. فرم برای امروز است؛ ورود فایل برای چند روز یکجا، معمولاً برای پرکردن گذشته. وارد‌کننده در هر دو حالت ستون‌های مشتق را دوباره حساب می‌کند، پس هیچ‌کدام از این دو راه نمی‌تواند نسبتی که دستی ویرایش شده را تزریق کند.",
      ar: "كلاهما ينتج الشيء نفسه - يوما مقيَّما في سجلك. فالنموذج لليوم الحالي؛ والاستيراد لأيام كثيرة دفعة واحدة، عادة للملء بأثر رجعي. والمستورد يعيد حساب الأعمدة المشتقة في الحالتين، فلا يستطيع أي مسار حقن نسبة عُدّلت يدويا.",
      zh: "两者产生的是同一个结果——你历史中一个已评分的日子。表单用于今天；导入用于一次性处理多天，通常是补录。无论走哪条路，导入器都会重新计算推导列，所以两种方式都无法塞入手工修改过的比例值。",
    },

    {
      key: 'app_score_is_zero_or_missing',
      match: /\b(my score shows a dash|score is empty|no score displayed)(?:s|es|ing)?\b|امتیازم خط تیره است|امتیاز نمایش داده نمیشود|درجتي تظهر شرطة|لا تُعرض درجة|分数显示成横线|没有显示分数/i,
      en: "A dash means there's no value to show rather than a value of zero - usually no prediction has been made in this session yet. Submitting a check-in, or reopening a past day from history, gives the page something real to display.",
      fa: "یک خط تیره یعنی مقداری برای نشان‌دادن نیست، نه اینکه مقدارش صفر باشد - معمولاً یعنی هنوز در این نشست پیش‌بینی‌ای انجام نشده. ثبت یک چک‌این، یا بازکردن یک روز گذشته از تاریخچه، به صفحه چیز واقعی‌ای برای نمایش می‌دهد.",
      ar: "الشرطة تعني أنه لا توجد قيمة لعرضها لا أن القيمة صفر - وعادة يعني أنه لم يُجرَ تنبؤ بعد في هذه الجلسة. وإرسال تسجيل، أو إعادة فتح يوم سابق من السجل، يمنح الصفحة شيئا حقيقيا لعرضه.",
      zh: "横线表示没有可显示的数值，而不是数值为零——通常是因为本次会话中还没有做过预测。提交一次打卡，或者从历史里重新打开过去的某一天，页面就有真实内容可显示了。",
    },

    {
      key: 'app_dimension_low_but_score_high',
      match: /\b(one dimension is low but my score is high|why do the arcs disagree with the score)(?:s|es|ing)?\b|یک بعد پایین است ولی امتیازم بالاست|چرا کمان‌ها با امتیاز نمیخوانند|بُعد منخفض لكن درجتي مرتفعة|لماذا تختلف الأقواس عن الدرجة|某个维度很低但总分很高|为什么弧线和分数不一致/i,
      en: "They're computed differently on purpose: the score is the model's weighting of your whole day, the dimensions are a plain arithmetic rollup treating their inputs evenly. A single weak dimension the model doesn't weigh heavily for you can sit under a high score without either being wrong.",
      fa: "عمداً متفاوت محاسبه می‌شوند: امتیاز وزن‌دهی مدل به کل روز توست، ابعاد یک جمع‌بندی حسابی ساده‌اند که ورودی‌هایشان را یکسان در نظر می‌گیرند. یک بُعد ضعیفِ تنها که مدل برای تو زیاد وزنش نمی‌دهد می‌تواند زیر یک امتیاز بالا بنشیند بدون اینکه هیچ‌کدام اشتباه باشند.",
      ar: "تُحسبان بطريقتين مختلفتين عن قصد: فالدرجة هي ترجيح النموذج ليومك كاملا، والأبعاد تجميع حسابي بسيط يعامل مدخلاته بالتساوي. فبُعد ضعيف واحد لا يرجّحه النموذج كثيرا لديك قد يقبع تحت درجة مرتفعة دون أن يكون أي منهما خاطئا.",
      zh: "它们是刻意用不同方式计算的：分数是模型对你一整天的加权判断，维度则是把各输入平等对待的简单算术汇总。某个模型对你并不特别看重的弱维度，完全可以出现在高分之下，而两者都没有错。",
    },

    {
      key: 'app_league_chat_not_sending',
      match: /\b(my message wont send|chat isnt sending|message stuck)(?:s|es|ing)?\b|پیامم فرستاده نمیشود|چت ارسال نمیکند|رسالتي لا تُرسل|المحادثة لا ترسل|消息发不出去|聊天发送失败/i,
      en: "Check first that the connection is still accepted on both sides - removing a connection or a block closes the chat immediately and symmetrically. If the connection is fine, it's an ordinary request failure, and reloading the page is the quickest way to tell which.",
      fa: "اول چک کن که ارتباط هنوز از هر دو طرف پذیرفته‌شده باشد - حذف یک ارتباط یا یک بلاک، چت را فوراً و متقارن می‌بندد. اگر ارتباط سالم است، یک شکست درخواست معمولی است و بارگذاری دوباره‌ی صفحه سریع‌ترین راه تشخیص است.",
      ar: "تحقق أولا أن الاتصال ما زال مقبولا من الطرفين - فإزالة اتصال أو حظر تُغلق المحادثة فورا وبشكل متماثل. وإن كان الاتصال سليما، فهو فشل طلب عادي، وإعادة تحميل الصفحة أسرع طريقة لمعرفة أيهما.",
      zh: "先确认双方的连接是否仍处于已接受状态——解除连接或屏蔽会立刻、对称地关闭聊天。如果连接没问题，那就是一次普通的请求失败，刷新页面是最快的判断方式。",
    },

    {
      key: 'app_league_blocked_me',
      match: /\b(someone blocked me|i think im blocked|cant message a friend anymore)(?:s|es|ing)?\b|کسی من را بلاک کرده|فکر کنم بلاک شدم|شخص حظرني|أظن أنني محظور|有人屏蔽了我|我好像被屏蔽了/i,
      en: "Blocking is symmetric and immediate - neither side can read or write until it's undone. It's deliberately not announced with a special message, so an unexplained silence in a thread is one of the possibilities.",
      fa: "بلاک‌کردن متقارن و فوری است - تا وقتی برداشته نشود هیچ‌کدام از دو طرف نمی‌توانند بخوانند یا بنویسند. عمداً با پیام ویژه‌ای اعلام نمی‌شود، پس سکوت بی‌توضیح در یک رشته یکی از احتمال‌هاست.",
      ar: "الحظر متماثل وفوري - فلا يستطيع أي من الطرفين القراءة أو الكتابة حتى يُلغى. وهو لا يُعلن برسالة خاصة عن قصد، فالصمت غير المفسَّر في خيط محادثة أحد الاحتمالات.",
      zh: "屏蔽是对称且立即生效的——在解除之前双方都无法读写。它刻意不会用特别的消息来通知，所以会话中无缘无故的沉默是其中一种可能。",
    },

    {
      key: 'app_report_what_happens',
      match: /\b(what happens when i report|who sees a report|does reporting block them)(?:s|es|ing)?\b|وقتی گزارش میدهم چه میشود|گزارش باعث بلاک میشود|ماذا يحدث عند الإبلاغ|هل الإبلاغ يحظر|举报后会怎样|举报会屏蔽对方吗/i,
      en: "Reporting flags a specific message for a human to review and doesn't require you to block first - they're separate actions, so you can report without cutting contact, or block without reporting, depending on what the situation calls for.",
      fa: "گزارش‌دادن یک پیام مشخص را برای بازبینی یک انسان علامت می‌زند و لازم نیست اول بلاک کنی - این‌ها کنش‌های جدایی هستند، پس می‌توانی بدون قطع ارتباط گزارش بدهی یا بدون گزارش بلاک کنی، بسته به اینکه وضعیت چه می‌طلبد.",
      ar: "الإبلاغ يضع علامة على رسالة بعينها ليراجعها إنسان ولا يتطلب منك الحظر أولا - فهما إجراءان منفصلان، فيمكنك الإبلاغ دون قطع التواصل، أو الحظر دون إبلاغ، حسب ما يقتضيه الموقف.",
      zh: "举报会把某条具体消息标记出来交由人工审核，并不要求你先屏蔽——两者是独立的操作，所以你可以举报而不切断联系，也可以屏蔽而不举报，取决于具体情况需要什么。",
    },

    {
      key: 'app_group_chat_who_can_join',
      match: /\b(who can be added to a group|can i add anyone to a group chat)(?:s|es|ing)?\b|چه کسی به گروه اضافه میشود|هرکسی را میتوانم به گروه اضافه کنم|من يمكن إضافته للمجموعة|هل أضيف أي شخص|谁能被加进群|能把任何人加进群聊吗/i,
      en: "Only people you're already individually connected to, with an accepted request, can be added. That rule exists so a group can't be used to route around someone's decision not to connect with you.",
      fa: "فقط کسانی که از قبل به‌صورت تکی و با درخواستِ پذیرفته‌شده به آن‌ها وصلی می‌توانند اضافه شوند. این قاعده وجود دارد تا یک گروه نتواند برای دور‌زدن تصمیم کسی که نخواسته به تو وصل شود استفاده گردد.",
      ar: "لا يمكن إضافة إلا من أنت متصل بهم فرديا أصلا بطلب مقبول. وتوجد هذه القاعدة كي لا تُستخدم المجموعة للالتفاف على قرار شخص بعدم الاتصال بك.",
      zh: "只有那些你已经通过已接受的请求单独建立连接的人才能被加入。这条规则的存在，是为了避免有人用群聊绕过别人「不想和你连接」的决定。",
    },

    {
      key: 'app_future_letter_read_again',
      match: /\b(can i read the letter again|where did my letter go|reread the future letter)(?:s|es|ing)?\b|میتوانم نامه را دوباره بخوانم|نامه‌ام کجا رفت|هل أقرأ الرسالة مجددا|أين ذهبت رسالتي|能再读一次那封信吗|我的信去哪了/i,
      en: "The letter lives on the analytics page and is rebuilt from your current numbers each time, so re-reading it later gives you a letter about where you are then - not a stored copy of the first one. That's deliberate: it's meant to track you, not to be an artifact.",
      fa: "نامه روی صفحه‌ی تحلیل‌ها زندگی می‌کند و هر بار از عددهای فعلی‌ات دوباره ساخته می‌شود، پس خواندن دوباره‌اش بعداً نامه‌ای درباره‌ی جایی که آن‌موقع هستی به تو می‌دهد - نه یک نسخه‌ی ذخیره‌شده از اولی. این عمدی است: قرار است تو را دنبال کند نه اینکه یک شیء یادگاری باشد.",
      ar: "تعيش الرسالة في صفحة التحليلات وتُعاد صياغتها من أرقامك الحالية في كل مرة، فإعادة قراءتها لاحقا تمنحك رسالة عن موضعك حينها - لا نسخة محفوظة من الأولى. وهذا مقصود: فهي معدّة لتتبعك لا لتكون أثرا محفوظا.",
      zh: "这封信在分析页面上，每次都会根据你当前的数据重新生成，所以之后再读会得到一封关于你「那时」状态的信——而不是第一封的存档副本。这是刻意为之：它是用来跟随你的，而不是一件纪念品。",
    },

    {
      key: 'app_future_letter_upsetting',
      match: /\b(the letter was upsetting|the letter felt harsh|i didnt like the letter)(?:s|es|ing)?\b|نامه ناراحت‌کننده بود|نامه تند بود|الرسالة كانت مزعجة|الرسالة بدت قاسية|那封信让我难受|信写得太严厉了/i,
      en: "The letter is the most personal text in the app and it's built from your own real numbers, which is exactly why it can land hard. It requires seven logged days before it appears specifically so it isn't read by someone who doesn't yet know their own pattern - and it's one page among many, not a verdict.",
      fa: "نامه شخصی‌ترین متن اپ است و از عددهای واقعی خودت ساخته شده، و دقیقاً برای همین می‌تواند سنگین بنشیند. مشخصاً به هفت روز ثبت‌شده نیاز دارد پیش از اینکه ظاهر شود تا کسی که هنوز الگوی خودش را نمی‌شناسد آن را نخواند - و یک صفحه است میان صفحه‌های دیگر، نه یک حکم.",
      ar: "الرسالة أكثر النصوص شخصية في التطبيق وهي مبنية من أرقامك الحقيقية، ولهذا بالذات قد تقع ثقيلة. وتشترط سبعة أيام مسجلة قبل ظهورها تحديدا كي لا يقرأها من لا يعرف نمطه بعد - وهي صفحة بين صفحات، لا حكم.",
      zh: "这封信是应用里最私人的文字，而且是由你自己的真实数据构建的，这正是它可能让人难受的原因。它要求先有七天记录才会出现，正是为了不让还不了解自己模式的人读到它——而它只是众多页面之一，不是对你的判决。",
    },

    {
      key: 'app_music_wont_play',
      match: /\b(music doesnt play|no sound from the player|audio not working)(?:s|es|ing)?\b|موسیقی پخش نمیشود|صدایی نمیاید|الموسيقى لا تعمل|لا صوت|音乐播放不了|没有声音/i,
      en: "Browsers block audio from starting until you've interacted with the page, so the first play usually needs a click. Beyond that, check the music control itself and the separate sound-effects switch in Settings - they're independent, so one being off doesn't explain the other.",
      fa: "مرورگرها تا وقتی با صفحه تعامل نکرده باشی جلوی شروع صدا را می‌گیرند، پس اولین پخش معمولاً به یک کلیک نیاز دارد. فراتر از آن، خود کنترل موسیقی و کلید جداگانه‌ی جلوه‌های صوتی در تنظیمات را چک کن - مستقل‌اند، پس خاموش‌بودن یکی دیگری را توضیح نمی‌دهد.",
      ar: "تمنع المتصفحات بدء الصوت حتى تتفاعل مع الصفحة، فأول تشغيل يحتاج نقرة عادة. وبعد ذلك، تحقق من عنصر تحكم الموسيقى نفسه ومن مفتاح المؤثرات الصوتية المنفصل في الإعدادات - فهما مستقلان، وإيقاف أحدهما لا يفسّر الآخر.",
      zh: "浏览器在你与页面产生交互之前会阻止音频自动播放，所以第一次播放通常需要点击一下。除此之外，检查音乐控件本身以及设置里独立的音效开关——它们互相独立，关掉其中一个并不能解释另一个。",
    },

    {
      key: 'app_data_used_for_training',
      match: /\b(is my data used to train the model|do you learn from my check ins|will my data improve the model)(?:s|es|ing)?\b|داده من برای آموزش مدل استفاده میشود|از چک‌این‌های من یاد میگیرید|هل تُستخدم بياناتي لتدريب النموذج|هل تتعلمون من تسجيلاتي|我的数据会用来训练模型吗|会从我的打卡中学习吗/i,
      en: "No. The models ship pre-trained and your check-ins are only scored by them - nothing you log is fed back into training, and there's no learning loop running on your account. Your data changes your own baseline and history, and nothing beyond that.",
      fa: "نه. مدل‌ها از پیش آموزش‌دیده می‌آیند و چک‌این‌هایت فقط توسط آن‌ها سنجیده می‌شوند - هیچ چیزی که ثبت می‌کنی به آموزش برنمی‌گردد، و هیچ حلقه‌ی یادگیری‌ای روی حساب تو در جریان نیست. داده‌ات خط پایه و تاریخچه‌ی خودت را عوض می‌کند و فراتر از آن هیچ.",
      ar: "لا. تأتي النماذج مدرَّبة مسبقا وتسجيلاتك تُقيَّم بها فقط - فلا شيء تسجّله يعود إلى التدريب، ولا توجد حلقة تعلّم تعمل على حسابك. بياناتك تغيّر خط أساسك وسجلك أنت، ولا شيء أبعد من ذلك.",
      zh: "不会。模型是预先训练好的，你的打卡只是被它们评分——你记录的任何内容都不会回流到训练中，你的账户上也没有在运行任何学习循环。你的数据只改变你自己的基线和历史，仅此而已。",
    },

    
    // ====== AE. Field mechanics, the prediction pipeline, CSV format details and language behaviour ======
    {
      key: 'app_field_ratio_vs_minutes',
      match: /\b(why ratios instead of minutes|why does it use proportions|ratio fields)(?:s|es|ing)?\b|چرا نسبت به جای دقیقه|چرا از نسبت استفاده میکند|لماذا النسب بدل الدقائق|حقول النسبة|为什么用比例而不是分钟|比例字段/i,
      en: "Ratios let the model compare people and days with very different totals. Ninety social minutes means something different inside a two-hour day than inside a ten-hour one, and only the proportion captures that - which is why the raw minutes and the ratio both exist rather than one replacing the other.",
      fa: "نسبت‌ها به مدل اجازه می‌دهند افراد و روزهایی با مجموع‌های خیلی متفاوت را مقایسه کند. نود دقیقه شبکه‌ی اجتماعی داخل یک روز دو‌ساعته معنایی متفاوت از داخل یک روز ده‌ساعته دارد، و فقط نسبت این را می‌گیرد - برای همین هم دقیقه‌ی خام و هم نسبت وجود دارند، نه اینکه یکی جای دیگری را بگیرد.",
      ar: "تتيح النسب للنموذج مقارنة أشخاص وأيام بمجاميع مختلفة جدا. فتسعون دقيقة تواصل اجتماعي تعني شيئا مختلفا داخل يوم من ساعتين عنها داخل يوم من عشر ساعات، والنسبة وحدها تلتقط ذلك - ولهذا توجد الدقائق الخام والنسبة معا لا أن تحل إحداهما محل الأخرى.",
      zh: "比例让模型能够比较总量差异很大的人和日子。在两小时的一天里，90 分钟社交的含义和在十小时的一天里完全不同，而只有比例能体现这一点——这就是为什么原始分钟数和比例同时存在，而不是其中一个取代另一个。",
    },

    {
      key: 'app_field_zero_value',
      match: /\b(what if a field is zero|i had no gaming today|can i enter zero)(?:s|es|ing)?\b|اگر یک فیلد صفر باشد|امروز بازی نکردم|ماذا لو كان الحقل صفرا|لم ألعب اليوم|某个字段是零怎么办|今天没玩游戏/i,
      en: "Zero is a real value and should be entered as zero - it tells the model something specific. Leaving a field blank is different: blanks aren't quietly treated as zero, and a required field left empty gives you a clear field-level error rather than a silent default.",
      fa: "صفر یک مقدار واقعی است و باید صفر وارد شود - چیز مشخصی به مدل می‌گوید. خالی‌گذاشتن یک فیلد متفاوت است: خالی‌ها بی‌صدا صفر در نظر گرفته نمی‌شوند، و یک فیلد اجباریِ خالی به تو یک خطای شفافِ سطح‌فیلد می‌دهد نه یک پیش‌فرض بی‌صدا.",
      ar: "الصفر قيمة حقيقية وينبغي إدخاله صفرا - فهو يخبر النموذج بشيء محدد. أما ترك الحقل فارغا فمختلف: الفراغات لا تُعامل صامتة كأصفار، والحقل الإلزامي الفارغ يعطيك خطأ واضحا على مستوى الحقل لا قيمة افتراضية صامتة.",
      zh: "零是一个真实的数值，应该按零来填——它向模型传达了具体的信息。留空则不同：空白不会被悄悄当成零，必填字段留空会给出明确的字段级错误提示，而不是默默套用默认值。",
    },

    {
      key: 'app_field_out_of_range',
      match: /\b(value out of range error|it says my number is too high|validation error on a field)(?:s|es|ing)?\b|خطای خارج از محدوده|میگوید عددم خیلی زیاد است|خطأ خارج النطاق|يقول رقمي مرتفع جدا|数值超出范围的错误|它说我的数字太大/i,
      en: "Each field has a plausible range, and a value outside it is rejected with a message naming that field rather than being clipped silently. Usually it's a units mix-up - hours typed where minutes were asked, or a total that would exceed the day.",
      fa: "هر فیلد یک بازه‌ی منطقی دارد و مقداری بیرون از آن با پیامی که همان فیلد را نام می‌برد رد می‌شود نه اینکه بی‌صدا بریده شود. معمولاً یک اشتباه واحد است - ساعت تایپ‌شده جایی که دقیقه خواسته شده، یا مجموعی که از یک شبانه‌روز بیشتر می‌شود.",
      ar: "لكل حقل نطاق معقول، والقيمة خارجه تُرفض برسالة تسمّي ذلك الحقل بدل قصّها صامتة. وعادة يكون خلطا في الوحدات - ساعات مكتوبة حيث طُلبت دقائق، أو مجموع يتجاوز اليوم.",
      zh: "每个字段都有合理的取值范围，超出范围的值会被拒绝并给出指明该字段的提示，而不是被悄悄截断。通常这是单位搞混了——在要求填分钟的地方填了小时，或者总量超过了一天的时长。",
    },

    {
      key: 'app_prediction_takes_time',
      match: /\b(why does prediction take a few seconds|the processing screen|why is there a loading screen)(?:s|es|ing)?\b|چرا پیش‌بینی چند ثانیه طول میکشد|صفحه پردازش|لماذا يستغرق التنبؤ ثوانٍ|شاشة المعالجة|为什么预测要几秒|处理界面/i,
      en: "Real work happens: validation, two model calls, the SHAP explanation, recommendations and persistence. The processing screen names those steps as they run rather than showing a generic spinner, so you can see it isn't a fake delay.",
      fa: "کار واقعی اتفاق می‌افتد: اعتبارسنجی، دو فراخوان مدل، توضیح SHAP، پیشنهادها و ذخیره‌سازی. صفحه‌ی پردازش همان مرحله‌ها را همان‌طور که اجرا می‌شوند نام می‌برد نه اینکه یک اسپینر کلی نشان دهد، تا ببینی یک تأخیر ساختگی نیست.",
      ar: "يحدث عمل حقيقي: تحقق، واستدعاءان للنموذج، وتفسير شاب، وتوصيات، وحفظ. وشاشة المعالجة تسمّي تلك الخطوات أثناء تنفيذها بدل عرض مؤشر تحميل عام، فترى أنها ليست تأخيرا مصطنعا.",
      zh: "这里确实在做实际工作：校验、两次模型调用、SHAP 解释、生成建议以及持久化。处理界面会在这些步骤执行时逐一点名，而不是显示一个通用的转圈图标，这样你能看出它不是假的延迟。",
    },

    {
      key: 'app_two_models_why',
      match: /\b(why two models|classifier and regressor|why a class and a score)(?:s|es|ing)?\b|چرا دو مدل|طبقه‌بند و رگرسور|لماذا نموذجان|مصنّف ونموذج انحدار|为什么有两个模型|分类器和回归模型/i,
      en: "A class answers 'which band am I in' and a score answers 'how far along am I' - different questions with different training targets. Running both means the class can stay stable while the score moves, which is more informative than forcing one number to do both jobs.",
      fa: "یک دسته به «در کدام باند هستم» جواب می‌دهد و یک امتیاز به «چقدر جلو رفته‌ام» - سؤال‌های متفاوت با هدف‌های آموزشی متفاوت. اجرای هر دو یعنی دسته می‌تواند ثابت بماند در حالی که امتیاز حرکت می‌کند، که آموزنده‌تر از این است که یک عدد را مجبور کنی هر دو کار را بکند.",
      ar: "الفئة تجيب «في أي نطاق أنا» والدرجة تجيب «إلى أي مدى تقدمت» - سؤالان مختلفان بأهداف تدريب مختلفة. وتشغيلهما معا يعني أن الفئة قد تبقى ثابتة بينما تتحرك الدرجة، وهذا أكثر إفادة من إجبار رقم واحد على أداء المهمتين.",
      zh: "类别回答的是「我处在哪个区间」，分数回答的是「我走到了什么程度」——这是两个不同的问题，训练目标也不同。两者同时运行意味着类别可以保持稳定而分数在变动，这比强迫一个数字同时承担两项工作更有信息量。",
    },

    {
      key: 'app_result_page_sections',
      match: /\b(what are the sections on the result page|what do i see after a check in)(?:s|es|ing)?\b|بخش‌های صفحه نتیجه چیستند|بعد از چک‌این چه میبینم|ما أقسام صفحة النتيجة|ماذا أرى بعد التسجيل|结果页有哪些部分|打卡后我会看到什么/i,
      en: "The result page runs: your score ring and class, the confidence, your top factors, the recommendations built from them, the save-as-CSV and PDF options, and further down an interactions section with the post-result games. Reopening a past day gives you the same layout for that day.",
      fa: "صفحه‌ی نتیجه به این ترتیب پیش می‌رود: حلقه‌ی امتیاز و دسته‌ات، اطمینان، عامل‌های اصلی‌ات، پیشنهادهای ساخته‌شده از آن‌ها، گزینه‌های ذخیره‌به‌CSV و PDF، و پایین‌تر یک بخش تعاملات با بازی‌های بعد از نتیجه. بازکردن یک روز گذشته همان چیدمان را برای آن روز می‌دهد.",
      ar: "تسير صفحة النتيجة هكذا: حلقة درجتك وفئتك، ثم الثقة، ثم عواملك الرئيسية، ثم التوصيات المبنية عليها، ثم خيارا الحفظ كـسي إس في وبي دي إف، وأسفلها قسم تفاعلات فيه ألعاب ما بعد النتيجة. وإعادة فتح يوم سابق تمنحك التخطيط نفسه لذلك اليوم.",
      zh: "结果页的顺序是：你的分数环和类别、置信度、主要影响因素、由这些因素生成的建议、保存为 CSV 和 PDF 的选项，再往下是包含结果后游戏的互动区。重新打开过去的某一天会得到那天同样的布局。",
    },

    {
      key: 'app_games_appear_order',
      match: /\b(why did a game appear before my result|games showed up first|order of games and result)(?:s|es|ing)?\b|چرا بازی قبل از نتیجه‌ام آمد|ترتیب بازی و نتیجه|لماذا ظهرت لعبة قبل نتيجتي|ترتيب الألعاب والنتيجة|为什么游戏出现在结果之前|游戏和结果的顺序/i,
      en: "Games are split by what they need. Ones that ask you to predict something unseen - your score, your confidence, whether you beat your average - have to run before the reveal or the guess is worthless. Everything else runs after, in the interactions section below your result.",
      fa: "بازی‌ها بر اساس چیزی که لازم دارند تقسیم شده‌اند. آن‌هایی که از تو می‌خواهند چیزی دیده‌نشده را پیش‌بینی کنی - امتیازت، اطمینانت، اینکه از میانگینت جلو زدی یا نه - باید پیش از فاش‌شدن اجرا شوند وگرنه حدس بی‌ارزش است. بقیه بعد اجرا می‌شوند، در بخش تعاملات پایین نتیجه‌ات.",
      ar: "تنقسم الألعاب حسب ما تحتاجه. فتلك التي تطلب منك التنبؤ بشيء لم تره - درجتك أو ثقتك أو هل تجاوزت متوسطك - يجب أن تُشغَّل قبل الكشف وإلا كان التخمين بلا قيمة. وكل ما عداها يُشغَّل بعد ذلك، في قسم التفاعلات أسفل نتيجتك.",
      zh: "游戏是按它们的需求划分的。那些要你预测尚未看到的东西的游戏——你的分数、置信度、是否超过了自己的平均值——必须在揭晓之前运行，否则猜测就毫无意义。其余的都在结果下方的互动区里运行。",
    },

    {
      key: 'app_score_decimal',
      match: /\b(why does my score have decimals|score is 62.4|why not a whole number)(?:s|es|ing)?\b|چرا امتیازم اعشار دارد|چرا عدد صحیح نیست|لماذا لدرجتي كسور عشرية|لماذا ليست عددا صحيحا|分数为什么有小数|为什么不是整数/i,
      en: "The regressor produces a continuous value, so the decimal is the real output rather than a rounded band. It also means small genuine changes are visible instead of being hidden by rounding to the nearest whole number.",
      fa: "رگرسور یک مقدار پیوسته تولید می‌کند، پس اعشار خروجی واقعی است نه یک باند گردشده. ضمناً یعنی تغییرهای کوچکِ واقعی دیده می‌شوند به‌جای اینکه با گردکردن به نزدیک‌ترین عدد صحیح پنهان شوند.",
      ar: "ينتج نموذج الانحدار قيمة متصلة، فالكسر العشري هو المخرج الحقيقي لا نطاقا مقرّبا. ويعني أيضا أن التغيرات الصغيرة الحقيقية تظهر بدل أن تختفي بالتقريب إلى أقرب عدد صحيح.",
      zh: "回归模型产生的是连续值，所以小数就是真实输出，而不是取整后的区间。这也意味着微小但真实的变化能被看见，而不会因为四舍五入到整数而被掩盖。",
    },

    {
      key: 'app_csv_column_order',
      match: /\b(does column order matter in the csv|can i reorder columns|columns in a different order|column order|does column order matter|reorder columns)(?:s|es|ing)?\b|ترتیب ستون‌ها مهم است|میتوانم ستون‌ها را جابه‌جا کنم|هل يهم ترتيب الأعمدة|هل أعيد ترتيب الأعمدة|csv列的顺序重要吗|能调整列顺序吗/i,
      en: "Columns are matched by their header name, not by position, so reordering them is fine. What isn't fine is renaming a header or dropping a required one - that's what produces the 'doesn't match the template' rejection.",
      fa: "ستون‌ها بر اساس نام عنوانشان تطبیق داده می‌شوند نه موقعیتشان، پس جابه‌جا کردنشان اشکالی ندارد. آنچه اشکال دارد تغییر نام یک عنوان یا حذف یکی از اجباری‌هاست - همان چیزی که رد‌شدن با «مطابق قالب نیست» را می‌سازد.",
      ar: "تُطابَق الأعمدة بأسماء عناوينها لا بمواضعها، فإعادة ترتيبها لا بأس بها. أما غير المقبول فهو إعادة تسمية عنوان أو حذف عنوان إلزامي - وهذا ما ينتج رفض «لا يطابق القالب».",
      zh: "列是按表头名称匹配的，不是按位置，所以调整顺序没问题。不行的是改掉表头名称或删掉必需的列——那正是产生「与模板不匹配」这个拒绝提示的原因。",
    },

    {
      key: 'app_csv_extra_columns',
      match: /\b(can my csv have extra columns|unknown columns in csv|extra fields in the file)(?:s|es|ing)?\b|فایلم میتواند ستون اضافه داشته باشد|ستون‌های ناشناخته|هل يمكن أن يحوي ملفي أعمدة إضافية|أعمدة غير معروفة|csv能有多余的列吗|文件里多出来的字段/i,
      en: "Derived columns in a file are ignored and recomputed from your raw values, so their presence is harmless. A required column being absent or renamed is the real failure - the error names which one, so you don't have to diff the whole header row.",
      fa: "ستون‌های مشتق در یک فایل نادیده گرفته و از مقادیر خام تو دوباره محاسبه می‌شوند، پس وجودشان بی‌ضرر است. نبودن یا تغییر نام یک ستون اجباری شکست واقعی است - خطا نام می‌برد کدام‌یک، تا مجبور نباشی کل سطر عنوان را مقایسه کنی.",
      ar: "الأعمدة المشتقة في الملف تُتجاهل ويُعاد حسابها من قيمك الخام، فوجودها غير ضار. أما غياب عمود إلزامي أو إعادة تسميته فهو الفشل الحقيقي - والخطأ يسمّي أيّها، فلا تضطر لمقارنة صف العناوين كله.",
      zh: "文件中的推导列会被忽略并从你的原始数值重新计算，所以它们存在也无妨。真正会失败的是缺少必需列或列名被改动——错误信息会指出是哪一个，你不必去逐一比对整行表头。",
    },

    {
      key: 'app_language_affects_data',
      match: /\b(does changing language change my data|will switching language reset anything)(?:s|es|ing)?\b|تغییر زبان داده‌ام را عوض میکند|عوض کردن زبان چیزی را ریست میکند|هل تغيير اللغة يغيّر بياناتي|هل تبديل اللغة يعيد ضبط شيء|切换语言会改变数据吗|换语言会重置什么吗/i,
      en: "No - language changes only what's displayed. The values you submit and what's stored are identical in every language, which is deliberate: the option you pick sends a stable internal value, never the translated text you see, so switching language can't change what the model receives.",
      fa: "نه - زبان فقط چیزی را که نمایش داده می‌شود عوض می‌کند. مقادیری که ثبت می‌کنی و آنچه ذخیره می‌شود در هر زبانی یکسان‌اند، و این عمدی است: گزینه‌ای که انتخاب می‌کنی یک مقدار داخلیِ پایدار می‌فرستد، نه متن ترجمه‌شده‌ای که می‌بینی، پس عوض‌کردن زبان نمی‌تواند چیزی را که مدل دریافت می‌کند تغییر دهد.",
      ar: "لا - اللغة تغيّر ما يُعرض فقط. فالقيم التي ترسلها وما يُخزَّن متطابقة في كل اللغات، وهذا مقصود: فالخيار الذي تنتقيه يرسل قيمة داخلية ثابتة، لا النص المترجم الذي تراه، فلا يستطيع تبديل اللغة تغيير ما يتلقاه النموذج.",
      zh: "不会——语言只改变显示的内容。你提交的数值和存储的内容在任何语言下都完全相同，这是刻意设计的：你选择的选项发送的是稳定的内部值，而不是你看到的翻译文本，所以切换语言不可能改变模型收到的内容。",
    },

    {
      key: 'app_rtl_language_switch',
      match: /\b(what changes when i pick persian|does arabic flip the layout|rtl mode)(?:s|es|ing)?\b|وقتی فارسی انتخاب میکنم چه عوض میشود|عربی چیدمان را برمیگرداند|ماذا يتغير عند اختيار العربية|هل تقلب العربية التخطيط|选波斯语会有什么变化|阿拉伯语会翻转布局吗/i,
      en: "Persian and Arabic switch the whole interface to right-to-left, which moves navigation, charts and card layouts rather than only swapping text. Most of the app updates instantly on a language switch without a reload.",
      fa: "فارسی و عربی کل رابط را به راست‌به‌چپ می‌برند، که ناوبری، نمودارها و چیدمان کارت‌ها را جابه‌جا می‌کند نه اینکه فقط متن را عوض کند. بیشتر اپ با یک تعویض زبان بدون بارگذاری دوباره فوراً به‌روز می‌شود.",
      ar: "الفارسية والعربية تحوّلان الواجهة كلها إلى اليمين-لليسار، فتنتقل عناصر التنقل والرسوم البيانية وتخطيطات البطاقات لا مجرد تبديل النص. ومعظم التطبيق يتحدث فورا عند تبديل اللغة دون إعادة تحميل.",
      zh: "波斯语和阿拉伯语会把整个界面切换为从右到左，这会移动导航、图表和卡片布局，而不只是替换文字。切换语言后应用的大部分内容会立即更新，无需重新加载。",
    },

    {
      key: 'app_is_there_an_api',
      match: /\b(is there an api|can i access my data programmatically|rest api)(?:s|es|ing)?\b|ای پی آی دارد|میتوانم برنامه‌نویسی به داده‌ام دسترسی پیدا کنم|هل يوجد واجهة برمجية|الوصول البرمجي لبياناتي|有api吗|能通过程序访问数据吗/i,
      en: "The frontend talks to a REST API, so the endpoints exist and the app itself is just one client of them. For your own data the supported path today is the CSV export and import rather than a documented public API - there's no bulk 'download everything' endpoint yet.",
      fa: "فرانت‌اند با یک REST API حرف می‌زند، پس endpointها وجود دارند و خود اپ فقط یکی از کلاینت‌هایشان است. برای داده‌ی خودت، مسیر پشتیبانی‌شده‌ی امروز خروجی و ورود CSV است نه یک API عمومیِ مستندشده - هنوز endpointی برای «دانلود همه‌چیز» یکجا نیست.",
      ar: "تتحدث الواجهة الأمامية مع واجهة REST، فالنقاط الطرفية موجودة والتطبيق نفسه مجرد عميل واحد لها. أما لبياناتك أنت فالمسار المدعوم اليوم هو تصدير واستيراد سي إس في لا واجهة عامة موثّقة - ولا توجد بعد نقطة طرفية لتنزيل كل شيء دفعة واحدة.",
      zh: "前端通过 REST API 通信，所以这些接口是存在的，应用本身只是其中一个客户端。但就你自己的数据而言，目前受支持的路径是 CSV 导出和导入，而不是有文档的公开 API——还没有一次性「下载全部」的接口。",
    },

    
    // ====== AF. Plan vs recommendations, exception days, multi-tab, and testing the League ======
    {
      key: 'app_weekly_plan_same_as_recommendations',
      match: /\b(is the plan the same as the recommendations|plan vs recommendations|difference between plan and advice)(?:s|es|ing)?\b|برنامه با پیشنهادها یکی است|تفاوت برنامه و توصیه|هل الخطة هي التوصيات نفسها|الفرق بين الخطة والتوصيات|计划和建议一样吗|计划和建议的区别/i,
      en: "They come from the same weak signals but do different jobs: the recommendations on your result are single concrete steps for today, while the weekly plan spreads work across seven days with checkable tasks and a visible throughline. Neither is the ML model - both are rule-based on top of it.",
      fa: "از همان سیگنال‌های ضعیف می‌آیند ولی کارهای متفاوتی می‌کنند: پیشنهادهای روی نتیجه‌ات قدم‌های مشخصِ تکی برای امروزند، در حالی که برنامه‌ی هفتگی کار را در هفت روز پخش می‌کند با وظیفه‌های قابل‌تیک و یک رشته‌ی پیوندِ دیدنی. هیچ‌کدام مدل یادگیری ماشین نیستند - هر دو قانون‌محورند روی آن.",
      ar: "تأتيان من الإشارات الضعيفة نفسها لكن بوظيفتين مختلفتين: فتوصيات نتيجتك خطوات ملموسة مفردة لليوم، بينما تنشر الخطة الأسبوعية العمل على سبعة أيام بمهام قابلة للتأشير وخيط ناظم مرئي. وليست أي منهما نموذج تعلّم آلة - كلتاهما قائمة على قواعد فوقه.",
      zh: "它们来自同样的弱信号，但作用不同：结果页上的建议是针对今天的单条具体行动，而每周计划把工作分散到七天，配有可勾选的任务和一条看得见的主线。两者都不是机器学习模型——都是建立在它之上的规则系统。",
    },

    {
      key: 'app_plan_progress_shared',
      match: /\b(can my friends see my plan|is my weekly plan private)(?:s|es|ing)?\b|دوستانم برنامه‌ام را میبینند|برنامه هفتگی‌ام خصوصی است|هل يرى أصدقائي خطتي|هل خطتي الأسبوعية خاصة|朋友能看到我的计划吗|每周计划是私密的吗/i,
      en: "Your plan is private. The four League sharing categories are persona, score, rank and top factor - the plan, your tasks and your raw check-ins are not among them and are never shared with anyone.",
      fa: "برنامه‌ات خصوصی است. چهار دسته‌ی اشتراک‌گذاری لیگ عبارت‌اند از پرسونا، امتیاز، رتبه و عامل اصلی - برنامه، وظیفه‌هایت و چک‌این‌های خامت میانشان نیستند و هرگز با کسی به اشتراک گذاشته نمی‌شوند.",
      ar: "خطتك خاصة. ففئات المشاركة الأربع في الدوري هي الشخصية والدرجة والترتيب والعامل الرئيسي - أما الخطة ومهامك وتسجيلاتك الخام فليست منها ولا تُشارك مع أحد أبدا.",
      zh: "你的计划是私密的。联赛的四个分享类别是画像、分数、排名和主要因素——计划、你的任务和原始打卡都不在其中，绝不会分享给任何人。",
    },

    {
      key: 'app_analytics_after_import',
      match: /\b(will analytics update after i import|do imported days count in analytics)(?:s|es|ing)?\b|بعد از ورود داده تحلیل‌ها به‌روز میشوند|روزهای واردشده در تحلیل حساب میشوند|هل تتحدث التحليلات بعد الاستيراد|هل تُحتسب الأيام المستوردة|导入后分析会更新吗|导入的日子算进分析吗/i,
      en: "Imported days are ordinary days once they land - they count towards trends, correlations, challenges and your baseline exactly like typed ones. That's usually the fastest way to make the history-dependent cards appear if you have past data.",
      fa: "روزهای واردشده به‌محض نشستن، روزهای عادی‌اند - دقیقاً مثل روزهای تایپ‌شده در روندها، همبستگی‌ها، چالش‌ها و خط پایه‌ات حساب می‌شوند. معمولاً اگر داده‌ی گذشته داشته باشی این سریع‌ترین راه ظاهر‌شدن کارت‌های وابسته به تاریخچه است.",
      ar: "الأيام المستوردة أيام عادية بمجرد وصولها - تُحتسب في الاتجاهات والارتباطات والتحديات وخط أساسك تماما كالمكتوبة يدويا. وهذه عادة أسرع طريقة لإظهار البطاقات المعتمدة على التاريخ إن كانت لديك بيانات سابقة.",
      zh: "导入的日子一旦入库就是普通的日子——它们和手动填写的日子一样，计入趋势、相关性、挑战和你的基线。如果你有过去的数据，这通常是让依赖历史的卡片出现的最快方式。",
    },

    {
      key: 'app_history_after_delete_days',
      match: /\b(can i delete a single day|remove one check in|delete just one entry)(?:s|es|ing)?\b|میتوانم یک روز را حذف کنم|حذف یک چک‌این|هل أحذف يوما واحدا|حذف تسجيل واحد|能删除某一天吗|删除单条打卡/i,
      en: "There isn't a per-day delete. Marking a day as an exception is the intended way to neutralise it: it stops counting towards averages, streaks and challenges while staying visible in your history, so you keep the record of what happened without it skewing anything.",
      fa: "حذف به‌ازای هر روز وجود ندارد. علامت‌زدن یک روز به‌عنوان استثنا راه در نظر گرفته‌شده برای خنثی‌کردنش است: در میانگین‌ها، زنجیره‌ها و چالش‌ها دیگر حساب نمی‌شود ولی در تاریخچه‌ات دیده می‌ماند، پس سابقه‌ی آنچه اتفاق افتاده را نگه می‌داری بدون اینکه چیزی را کج کند.",
      ar: "لا يوجد حذف لكل يوم على حدة. ووسم اليوم كاستثناء هو الطريقة المقصودة لتحييده: فيتوقف احتسابه في المتوسطات والتتابعات والتحديات مع بقائه مرئيا في سجلك، فتحتفظ بسجل ما حدث دون أن يحرّف شيئا.",
      zh: "没有按天删除的功能。把某天标记为例外是设计上用来「中和」它的方式：它不再计入平均值、连续天数和挑战，但仍然在历史中可见，这样你保留了发生过什么的记录，同时它也不会扭曲任何统计。",
    },

    {
      key: 'app_excluded_day_still_scored',
      match: /\b(does an excluded day still get a score|exception day prediction)(?:s|es|ing)?\b|روز استثنا هم امتیاز میگیرد|پیش‌بینی روز استثنا|هل ينال اليوم المستبعد درجة|تنبؤ اليوم الاستثنائي|例外日还会有分数吗|例外日的预测/i,
      en: "Yes - an excluded day still produces a real prediction with its own score and factors, so you can see what the model made of it. What changes is that it never enters your averages, streaks, trends or challenges.",
      fa: "بله - یک روز کنارگذاشته‌شده هنوز یک پیش‌بینی واقعی با امتیاز و عامل‌های خودش تولید می‌کند، تا ببینی مدل از آن چه ساخته. چیزی که عوض می‌شود این است که هرگز وارد میانگین‌ها، زنجیره‌ها، روندها یا چالش‌هایت نمی‌شود.",
      ar: "نعم - اليوم المستبعد ينتج تنبؤا حقيقيا بدرجته وعوامله، فترى ما فهمه النموذج منه. وما يتغير هو أنه لا يدخل أبدا في متوسطاتك أو تتابعاتك أو اتجاهاتك أو تحدياتك.",
      zh: "会的——被排除的一天仍然会产生真实的预测，有自己的分数和影响因素，这样你能看到模型是怎么理解它的。改变的只是它绝不会进入你的平均值、连续天数、趋势或挑战。",
    },

    {
      key: 'app_when_to_use_exception',
      match: /\b(when should i mark a day as an exception|what counts as an unusual day|when to mark an exception day)(?:s|es|ing)?\b|کی باید روز را استثنا علامت بزنم|چه چیزی روز غیرعادی حساب میشود|متى أسم يوما كاستثناء|ما الذي يُعد يوما غير عادي|什么时候该标记例外日|什么算不寻常的一天/i,
      en: "Use it when the day genuinely wasn't your life - a flight, an illness, a one-off event - because the app can't tell those apart from a bad habit; in the numbers they look identical. Don't use it just because the score disappointed you: that's the day you most want in the record.",
      fa: "وقتی استفاده کن که آن روز واقعاً زندگی معمولت نبوده - یک پرواز، یک بیماری، یک رویداد یک‌باره - چون اپ نمی‌تواند این‌ها را از یک عادت بد تشخیص دهد؛ در عددها یکسان به نظر می‌رسند. صرفاً به‌خاطر اینکه امتیاز ناامیدت کرد استفاده‌اش نکن: آن روز همان روزی است که بیشتر از همه می‌خواهی در سابقه باشد.",
      ar: "استخدمه حين لا يكون اليوم حياتك حقا - رحلة طيران، أو مرض، أو حدث لمرة واحدة - لأن التطبيق لا يستطيع تمييز تلك عن عادة سيئة؛ فهي في الأرقام متطابقة. ولا تستخدمه لمجرد أن الدرجة خيّبت أملك: فذلك اليوم هو أكثر ما تريده في السجل.",
      zh: "当那一天确实不属于你的日常时才用它——出差飞行、生病、一次性事件——因为应用无法把这些和坏习惯区分开；在数字上它们看起来一模一样。不要仅仅因为分数让你失望就用它：那样的日子恰恰是你最该留在记录里的。",
    },

    {
      key: 'app_score_compared_to_yesterday',
      match: /\b(how does today compare to yesterday|am i better than yesterday)(?:s|es|ing)?\b|امروز نسبت به دیروز چطور است|از دیروز بهترم|كيف يقارن اليوم بالأمس|هل أنا أفضل من أمس|今天和昨天比怎么样|比昨天好吗/i,
      en: "The result page has a direct comparison with your last check-in, and the coach menu has the same question wired to your real numbers. Bear in mind the previous check-in may not be yesterday if you skipped days - the comparison is against your last logged day, not the calendar.",
      fa: "صفحه‌ی نتیجه یک مقایسه‌ی مستقیم با آخرین چک‌این‌ات دارد، و منوی مربی هم همان سؤال را دارد که به عددهای واقعی‌ات وصل است. حواست باشد که چک‌این قبلی ممکن است دیروز نباشد اگر روزهایی را رد کرده‌ای - مقایسه با آخرین روزِ ثبت‌شده‌ات است نه با تقویم.",
      ar: "في صفحة النتيجة مقارنة مباشرة بآخر تسجيل لك، وفي قائمة المدرب السؤال نفسه موصولا بأرقامك الحقيقية. وانتبه أن التسجيل السابق قد لا يكون أمس إن تخطيت أياما - فالمقارنة بآخر يوم سجّلته لا بالتقويم.",
      zh: "结果页有与你上一次打卡的直接对比，教练菜单里也有同样的问题、并接入你的真实数据。要注意，如果你跳过了几天，上一次打卡未必是昨天——对比的是你最后记录的那一天，而不是日历上的昨天。",
    },

    {
      key: 'app_no_internet_needed_for_reading',
      match: /\b(can i read my old results offline|view history without internet)(?:s|es|ing)?\b|نتایج قدیمی را آفلاین ببینم|تاریخچه بدون اینترنت|قراءة نتائجي القديمة بدون إنترنت|السجل بلا اتصال|能离线看旧结果吗|没网能看历史吗/i,
      en: "No - history is fetched from the server each time, so reading a past day needs a connection just like creating a new one does. Nothing is cached locally for offline reading; the PDF export is the way to keep a copy you can open without the app.",
      fa: "نه - تاریخچه هر بار از سرور واکشی می‌شود، پس خواندن یک روز گذشته هم مثل ساختن یک روز جدید به اتصال نیاز دارد. هیچ چیزی به‌صورت محلی برای خواندن آفلاین کش نمی‌شود؛ خروجی PDF راه نگه‌داشتن نسخه‌ای است که بدون اپ باز شود.",
      ar: "لا - يُجلب السجل من الخادم في كل مرة، فقراءة يوم سابق تحتاج اتصالا تماما كإنشاء يوم جديد. ولا شيء يُخزَّن محليا للقراءة دون اتصال؛ وتصدير بي دي إف هو طريقة الاحتفاظ بنسخة تفتحها دون التطبيق.",
      zh: "不能——历史每次都是从服务器获取的，所以查看过去的某一天和创建新记录一样需要网络。本地不会缓存任何内容供离线阅读；PDF 导出才是保留一份可以脱离应用打开的副本的方式。",
    },

    {
      key: 'app_multiple_tabs',
      match: /\b(can i open it in two tabs|two tabs at once|using multiple tabs)(?:s|es|ing)?\b|میتوانم در دو تب باز کنم|استفاده از چند تب|هل أفتحه في تبويبين|استخدام تبويبات متعددة|能开两个标签页吗|同时用多个标签页/i,
      en: "It works, but both tabs share the same stored session and preferences, so entering Demo Mode in one affects the other - the token swap is per-browser, not per-tab. For testing the League you want two different browsers or a private window, not two tabs.",
      fa: "کار می‌کند، اما هر دو تب همان نشست و ترجیحات ذخیره‌شده را به اشتراک می‌گذارند، پس ورود به حالت دمو در یکی روی دیگری اثر می‌گذارد - جابه‌جایی توکن به‌ازای هر مرورگر است نه هر تب. برای تست لیگ به دو مرورگر متفاوت یا یک پنجره‌ی ناشناس نیاز داری، نه دو تب.",
      ar: "يعمل، لكن التبويبين يتشاركان الجلسة والتفضيلات المخزنة نفسها، فدخول وضع العرض التجريبي في أحدهما يؤثر على الآخر - فتبديل الرمز لكل متصفح لا لكل تبويب. ولاختبار الدوري تحتاج متصفحين مختلفين أو نافذة خاصة، لا تبويبين.",
      zh: "可以用，但两个标签页共享同一份存储的会话和偏好设置，所以在其中一个里进入演示模式会影响另一个——令牌交换是按浏览器而不是按标签页的。要测试联赛，你需要两个不同的浏览器或一个无痕窗口，而不是两个标签页。",
    },

    {
      key: 'app_private_window',
      match: /\b(can i use a private window|incognito mode|does it work in private browsing)(?:s|es|ing)?\b|پنجره ناشناس|حالت مخفی|نافذة خاصة|وضع التصفح المتخفي|能用无痕窗口吗|隐身模式/i,
      en: "It works, and a private window is the simplest way to be signed in as a second account at the same time - which is exactly what testing the League chat needs. Just remember the private session's login and preferences vanish when you close it.",
      fa: "کار می‌کند، و یک پنجره‌ی ناشناس ساده‌ترین راه است که هم‌زمان با یک حساب دوم وارد باشی - دقیقاً همان چیزی که تست چت لیگ لازم دارد. فقط یادت باشد ورود و ترجیحات آن نشست ناشناس با بستنش ناپدید می‌شوند.",
      ar: "يعمل، والنافذة الخاصة أبسط طريقة لتكون مسجّل الدخول بحساب ثانٍ في الوقت نفسه - وهو بالضبط ما يحتاجه اختبار محادثة الدوري. فقط تذكّر أن تسجيل دخول تلك الجلسة وتفضيلاتها تزول عند إغلاقها.",
      zh: "可以用，而且无痕窗口是同时以第二个账户登录的最简单方式——这正是测试联赛聊天所需要的。只要记住，无痕会话的登录状态和偏好设置在你关闭它时就会消失。",
    },

    {
      key: 'app_how_to_test_the_league',
      match: /\b(how do i test the league chat myself|try the league alone|demo the league for someone)(?:s|es|ing)?\b|چطور خودم چت لیگ را تست کنم|لیگ را تنهایی امتحان کنم|كيف أختبر محادثة الدوري بنفسي|تجربة الدوري وحدي|我自己怎么测试联赛聊天|一个人试联赛/i,
      en: "Register a second account in a different browser or a private window, take one account's invite code to the other, send and accept the request, then send messages back and forth between the two windows. One account genuinely cannot demonstrate a two-sided conversation.",
      fa: "یک حساب دوم در مرورگری دیگر یا پنجره‌ی ناشناس بساز، کد دعوت یک حساب را به آن یکی ببر، درخواست را بفرست و بپذیر، بعد بین دو پنجره پیام رد و بدل کن. یک حساب واقعاً نمی‌تواند یک گفت‌وگوی دوطرفه را نشان دهد.",
      ar: "سجّل حسابا ثانيا في متصفح آخر أو نافذة خاصة، وانقل رمز دعوة أحد الحسابين إلى الآخر، وأرسل الطلب واقبله، ثم تبادل الرسائل بين النافذتين. فحساب واحد لا يستطيع فعلا عرض محادثة ثنائية الطرف.",
      zh: "在另一个浏览器或无痕窗口里注册第二个账户，把其中一个账户的邀请码拿到另一个账户，发送并接受请求，然后在两个窗口之间来回发消息。单个账户确实无法演示一场双向对话。",
    },

    {
      key: 'app_where_to_start_exploring',
      match: /\b(what should i look at first|best place to explore|show me around)(?:s|es|ing)?\b|اول کجا را ببینم|بهترین جا برای شروع گشت|ماذا أرى أولا|أفضل مكان للاستكشاف|先看哪里好|从哪开始逛/i,
      en: "If you have data, the result page and analytics are where the app is most itself. If you don't, Demo Mode is the honest shortcut - it fills a synthetic account with model-scored days so every history-dependent page has something real to show without you waiting weeks.",
      fa: "اگر داده داری، صفحه‌ی نتیجه و تحلیل‌ها جایی هستند که اپ بیشتر از همه خودش است. اگر نداری، حالت دمو میان‌برِ صادقانه است - یک حساب مصنوعی را با روزهای امتیازگرفته از مدل پر می‌کند تا هر صفحه‌ی وابسته به تاریخچه چیز واقعی‌ای برای نشان‌دادن داشته باشد بدون اینکه هفته‌ها منتظر بمانی.",
      ar: "إن كانت لديك بيانات، فصفحة النتيجة والتحليلات هما حيث يكون التطبيق أكثر ذاته. وإن لم تكن، فوضع العرض التجريبي هو الاختصار الصادق - إذ يملأ حسابا اصطناعيا بأيام مقيَّمة بالنموذج كي يكون لكل صفحة معتمدة على التاريخ ما تعرضه فعلا دون انتظار أسابيع.",
      zh: "如果你已经有数据，结果页和分析页是这个应用最能体现自身价值的地方。如果还没有，演示模式是诚实的捷径——它用模型评分过的日子填满一个合成账户，让每个依赖历史的页面都有真实内容可展示，而不用你等上好几周。",
    },

    {
      key: 'app_feedback_or_suggestion',
      match: /\b(i have a suggestion|how do i give feedback|feature request)(?:s|es|ing)?\b|پیشنهاد دارم|چطور بازخورد بدهم|لدي اقتراح|كيف أقدم ملاحظات|我有个建议|怎么提反馈/i,
      en: "The most actionable feedback names the page, what you expected and what happened instead - the same shape as a bug report. For a feature idea, saying which existing page it belongs on usually makes the difference between a note and something someone can act on.",
      fa: "قابل‌اجراترین بازخورد صفحه را نام می‌برد، اینکه چه انتظاری داشتی و به‌جایش چه شد - همان شکل یک گزارش باگ. برای یک ایده‌ی قابلیت، گفتن اینکه به کدام صفحه‌ی موجود تعلق دارد معمولاً فرق بین یک یادداشت و چیزی که کسی بتواند رویش کار کند را می‌سازد.",
      ar: "أكثر الملاحظات قابلية للتنفيذ تسمّي الصفحة وما توقعته وما حدث بدلا منه - الشكل نفسه لبلاغ خلل. وللفكرة عن ميزة، فذكر الصفحة القائمة التي تنتمي إليها هو ما يصنع الفرق عادة بين ملاحظة وشيء يمكن لأحد التصرف بشأنه.",
      zh: "最可执行的反馈会说明：哪个页面、你预期的是什么、实际发生了什么——和问题报告的结构一样。对于功能建议，说明它应该属于哪个现有页面，通常就是「一条留言」和「有人能着手去做的事」之间的区别。",
    },

    
    // ====== AG. Asking the coach about your own data, saved answers, persona and score meaning ======
    {
      key: 'app_coach_ask_about_my_data',
      match: /\b(can i ask about my own numbers|ask the coach about my score|questions about my data)(?:s|es|ing)?\b|میتوانم درباره عددهای خودم بپرسم|از مربی درباره امتیازم بپرسم|هل أسأل عن أرقامي|أسأل المدرب عن درجتي|能问我自己的数据吗|问教练我的分数/i,
      en: "Yes - that's what most of the menu is. Questions like how today compares to your last check-in, which dimension is weakest, whether a signal is improving, or what's typical for you are all answered from your own stored numbers rather than from general advice.",
      fa: "بله - بیشتر منو همین است. سؤال‌هایی مثل اینکه امروز نسبت به آخرین چک‌این‌ات چطور است، کدام بُعد ضعیف‌ترین است، آیا یک سیگنال دارد بهتر می‌شود، یا چه چیزی برای تو معمول است، همه از عددهای ذخیره‌شده‌ی خودت جواب داده می‌شوند نه از توصیه‌ی کلی.",
      ar: "نعم - وهذا ما تدور حوله معظم القائمة. فأسئلة مثل كيف يقارن اليوم بآخر تسجيل لك، وأي بُعد هو الأضعف، وهل تتحسن إشارة ما، وما المعتاد بالنسبة لك، تُجاب كلها من أرقامك المخزنة أنت لا من نصائح عامة.",
      zh: "可以——菜单里的大部分问题就是这类。比如今天和上次打卡相比如何、哪个维度最弱、某个信号是否在改善、对你来说什么算典型——这些都是从你自己存储的数据中作答的，而不是给出泛泛的建议。",
    },

    {
      key: 'app_coach_suggestions',
      match: /\b(what are the suggested questions|the chips above the chat|suggested prompts)(?:s|es|ing)?\b|سوال‌های پیشنهادی چیستند|چیپ‌های بالای چت|ما هي الأسئلة المقترحة|الشرائح فوق المحادثة|推荐问题是什么|聊天上方的标签/i,
      en: "Those are shortcuts into questions the coach can answer well right now given your data. They shift as your data changes, so a suggestion that appears after a check-in isn't the same set you'd have seen with an empty account.",
      fa: "آن‌ها میان‌برهایی به سؤال‌هایی هستند که مربی با توجه به داده‌ی فعلی‌ات همین حالا می‌تواند خوب جوابشان بدهد. با تغییر داده‌ات جابه‌جا می‌شوند، پس پیشنهادی که بعد از یک چک‌این ظاهر می‌شود همان مجموعه‌ای نیست که با یک حساب خالی می‌دیدی.",
      ar: "تلك اختصارات إلى أسئلة يستطيع المدرب الإجابة عنها جيدا الآن بالنظر إلى بياناتك. وتتبدّل مع تغير بياناتك، فالاقتراح الذي يظهر بعد تسجيل ليس المجموعة نفسها التي كنت ستراها بحساب فارغ.",
      zh: "那些是通往教练在你当前数据下能答得好的问题的快捷方式。它们会随你的数据变化而变化，所以打卡之后出现的推荐，和空账户时看到的并不是同一组。",
    },

    {
      key: 'app_coach_menu_categories',
      match: /\b(what are the coach menu categories|how is the menu organised|menu sections)(?:s|es|ing)?\b|دسته‌بندی‌های منوی مربی|منو چطور سازمان یافته|فئات قائمة المدرب|كيف تُنظَّم القائمة|教练菜单有哪些分类|菜单是怎么组织的/i,
      en: "The menu is grouped by subject - your score, sleep, focus, progress, the weekly plan, the League, privacy, how the system works - plus generated families that produce one question per signal you log, which is why it runs to a couple of hundred entries rather than a short list.",
      fa: "منو بر اساس موضوع گروه‌بندی شده - امتیازت، خواب، تمرکز، پیشرفت، برنامه‌ی هفتگی، لیگ، حریم خصوصی، اینکه سیستم چطور کار می‌کند - به‌علاوه خانواده‌های تولیدشده‌ای که برای هر سیگنالی که ثبت می‌کنی یک سؤال می‌سازند، و برای همین به چند صد ورودی می‌رسد نه یک فهرست کوتاه.",
      ar: "القائمة مجمّعة حسب الموضوع - درجتك، والنوم، والتركيز، والتقدم، والخطة الأسبوعية، والدوري، والخصوصية، وكيف يعمل النظام - إضافة إلى عائلات مولَّدة تنتج سؤالا لكل إشارة تسجّلها، ولهذا تبلغ مئتي مدخل ونيّف لا قائمة قصيرة.",
      zh: "菜单按主题分组——你的分数、睡眠、专注、进展、每周计划、联赛、隐私、系统如何运作——此外还有生成式的问题family，为你记录的每个信号各生成一个问题，这就是为什么它有两百多条而不是一个短列表。",
    },

    {
      key: 'app_coach_same_answer_twice',
      match: /\b(the coach gave the same answer again|why is the answer identical|it repeated itself)(?:s|es|ing)?\b|مربی همان جواب را دوباره داد|چرا جواب تکراری است|المدرب أعطى الإجابة نفسها|لماذا تكررت الإجابة|教练又给了同样的答案|为什么答案重复了/i,
      en: "If your underlying numbers haven't changed, the same question has the same correct answer, and you'll see it again with a short 'still true' lead-in rather than a reworded version. A randomly different answer to unchanged data would be the bug, not this.",
      fa: "اگر عددهای زیربنایی‌ات عوض نشده باشند، همان سؤال همان جواب درست را دارد و آن را دوباره با یک مقدمه‌ی کوتاه «هنوز هم همین است» می‌بینی نه یک نسخه‌ی بازنویسی‌شده. یک جواب تصادفاً متفاوت برای داده‌ی تغییرنکرده باگ بود، نه این.",
      ar: "إن لم تتغير أرقامك الأساسية، فالسؤال نفسه له الإجابة الصحيحة نفسها، وستراها مجددا بمقدمة قصيرة «لا يزال صحيحا» لا بصياغة مختلفة. أما إجابة مختلفة عشوائيا لبيانات لم تتغير فتلك هي الثغرة، لا هذا.",
      zh: "如果你的底层数据没有变化，同一个问题的正确答案也是同一个，你会看到它再次出现，并带上一句简短的「依然如此」，而不是换个说法重写一遍。对没变的数据给出随机不同的答案才是 bug，而不是这个。",
    },

    {
      key: 'app_coach_updated_tag',
      match: /\b(what does the updated tag mean|why does it say updated|the refresh icon on an answer)(?:s|es|ing)?\b|برچسب به‌روزرسانی‌شده یعنی چه|چرا مینویسد به‌روزرسانی شد|ماذا يعني وسم محدَّث|لماذا يقول محدَّث|「已更新」标记是什么意思|为什么显示已更新/i,
      en: "It means your real data changed since the last time you opened that question - a new check-in, a new plan week, a new friend - so the answer you're seeing reflects the newer numbers rather than a cached older one.",
      fa: "یعنی داده‌ی واقعی‌ات از آخرین باری که آن سؤال را باز کردی عوض شده - یک چک‌این جدید، یک هفته‌ی برنامه‌ی جدید، یک دوست جدید - پس جوابی که می‌بینی عددهای تازه‌تر را بازتاب می‌دهد نه یک نسخه‌ی کش‌شده‌ی قدیمی.",
      ar: "يعني أن بياناتك الحقيقية تغيرت منذ آخر مرة فتحت فيها ذلك السؤال - تسجيل جديد، أو أسبوع خطة جديد، أو صديق جديد - فالإجابة التي تراها تعكس الأرقام الأحدث لا نسخة مخزنة أقدم.",
      zh: "它表示自你上次打开那个问题以来，你的真实数据发生了变化——新的打卡、新的计划周、新的好友——所以你看到的答案反映的是更新后的数字，而不是缓存的旧答案。",
    },

    {
      key: 'app_dashboard_empty',
      match: /\b(dashboard is empty|nothing on my dashboard|dashboard shows no data)(?:s|es|ing)?\b|داشبورد خالی است|داشبوردم چیزی نشان نمیدهد|لوحة التحكم فارغة|لا شيء في لوحتي|仪表盘是空的|仪表盘没有数据/i,
      en: "The dashboard summarises your latest prediction, so with no check-in yet there's nothing to summarise - it shows an empty state rather than zeros, which would look like real bad scores. One check-in fills it.",
      fa: "داشبورد آخرین پیش‌بینی‌ات را خلاصه می‌کند، پس بدون هیچ چک‌اینی چیزی برای خلاصه‌کردن نیست - به‌جای صفرها که شبیه امتیازهای واقعیِ بد به نظر می‌رسیدند، یک حالت خالی نشان می‌دهد. یک چک‌این پرش می‌کند.",
      ar: "تلخّص لوحة التحكم آخر تنبؤ لك، فمع عدم وجود تسجيل بعد لا يوجد ما يُلخَّص - وتعرض حالة فارغة بدل أصفار كانت ستبدو كدرجات سيئة حقيقية. وتسجيل واحد يملؤها.",
      zh: "仪表盘汇总的是你最新一次预测，所以在还没有任何打卡时就没有内容可汇总——它会显示空状态，而不是显示零，因为零看起来会像是真实的糟糕分数。做一次打卡就能填满它。",
    },

    {
      key: 'app_import_csv_from_this_app',
      match: /\b(can i reimport a csv this app exported|reuse my own export)(?:s|es|ing)?\b|فایلی که خود اپ ساخته را دوباره وارد کنم|استفاده دوباره از خروجی خودم|إعادة استيراد ملف صدّره التطبيق|إعادة استخدام تصديري|能重新导入应用导出的csv吗|重用我自己的导出文件/i,
      en: "Yes, and that round trip is supported on purpose. Just note there are two shapes: the single-row questionnaire export from a result page, and the multi-row bulk template with a date column. Feeding one where the other is expected is the usual cause of a template-mismatch rejection.",
      fa: "بله، و این رفت‌وبرگشت عمداً پشتیبانی می‌شود. فقط توجه کن دو شکل وجود دارد: خروجی تک‌ردیفی پرسشنامه از یک صفحه‌ی نتیجه، و قالب انبوهِ چندردیفی با ستون تاریخ. دادن یکی جایی که آن یکی انتظار می‌رود علت معمول رد‌شدن با «عدم تطابق قالب» است.",
      ar: "نعم، وهذه الرحلة ذهابا وإيابا مدعومة عن قصد. لكن انتبه أن هناك شكلين: تصدير الاستبيان أحادي الصف من صفحة نتيجة، والقالب الجماعي متعدد الصفوف بعمود تاريخ. وتقديم أحدهما حيث يُتوقع الآخر هو السبب المعتاد لرفض عدم تطابق القالب.",
      zh: "可以，而且这种往返导入是刻意支持的。只要注意有两种格式：结果页导出的单行问卷文件，以及带日期列的多行批量模板。把其中一种用在期待另一种的地方，正是「与模板不匹配」这个拒绝提示最常见的原因。",
    },

    {
      key: 'app_saved_csv_where',
      match: /\b(where are my saved csvs|find my saved check ins|saved answers list)(?:s|es|ing)?\b|فایل‌های ذخیره‌شده کجا هستند|لیست پاسخ‌های ذخیره‌شده|أين ملفاتي المحفوظة|قائمة الإجابات المحفوظة|保存的csv在哪|保存的答案列表/i,
      en: "The saved list is on the check-in screen, split into two tabs - main check-ins and test ones you marked excluded - so you don't accidentally reload a hypothetical entry as if it were a real day.",
      fa: "فهرست ذخیره‌شده روی صفحه‌ی چک‌این است، تقسیم‌شده به دو تب - چک‌این‌های اصلی و آن‌هایی که استثنا علامت زده‌ای - تا تصادفاً یک ورودی فرضی را طوری بارگذاری نکنی که انگار یک روز واقعی است.",
      ar: "القائمة المحفوظة في شاشة التسجيل، مقسّمة إلى تبويبين - التسجيلات الرئيسية وتلك التي وسمتها كمستبعدة - كي لا تعيد تحميل مدخل افتراضي بالخطأ وكأنه يوم حقيقي.",
      zh: "保存列表在打卡界面上，分成两个标签页——主打卡和你标记为排除的测试记录——这样你就不会不小心把一条假设性的记录当成真实的一天重新载入。",
    },

    {
      key: 'app_reload_a_saved_answer_set',
      match: /\b(can i reload a saved answer set|refill the form from a saved csv)(?:s|es|ing)?\b|میتوانم مجموعه پاسخ ذخیره‌شده را دوباره بارگذاری کنم|فرم را از فایل ذخیره‌شده پر کنم|هل أعيد تحميل مجموعة إجابات محفوظة|ملء النموذج من ملف محفوظ|能重新载入保存的答案吗|用保存的csv填表/i,
      en: "That's what the saved list is for - it refills the form so you can submit a similar day without retyping everything, or tweak one field to see what changes. Reloading answers doesn't record a day by itself; submitting does.",
      fa: "فهرست ذخیره‌شده برای همین است - فرم را دوباره پر می‌کند تا بتوانی یک روز مشابه را بدون تایپ دوباره‌ی همه‌چیز ثبت کنی، یا یک فیلد را دستکاری کنی تا ببینی چه عوض می‌شود. بارگذاری دوباره‌ی پاسخ‌ها به‌خودی‌خود روزی را ضبط نمی‌کند؛ ثبت‌کردن این کار را می‌کند.",
      ar: "لهذا وُجدت القائمة المحفوظة - فهي تعيد ملء النموذج كي ترسل يوما مشابها دون إعادة كتابة كل شيء، أو تعدّل حقلا واحدا لترى ما يتغير. وإعادة تحميل الإجابات لا تسجّل يوما بذاتها؛ الإرسال هو ما يفعل.",
      zh: "保存列表就是为此存在的——它会重新填好表单，让你不必全部重打就能提交类似的一天，或者只改一个字段看看会有什么变化。重新载入答案本身并不会记录一天；提交才会。",
    },

    {
      key: 'app_what_is_persona_used_for',
      match: /\b(what is the persona used for|does persona affect my score|why does persona exist)(?:s|es|ing)?\b|پرسونا برای چه استفاده میشود|پرسونا روی امتیازم اثر دارد|فيم تُستخدم الشخصية|هل تؤثر الشخصية على درجتي|画像有什么用|画像会影响分数吗/i,
      en: "The persona describes your overall pattern rather than scoring a day, so it doesn't feed into your wellness score. Its uses are context on the identity page and being one of the four things you can choose to share in the League.",
      fa: "پرسونا الگوی کلی‌ات را توصیف می‌کند نه اینکه به یک روز نمره بدهد، پس به امتیاز سلامتت خورانده نمی‌شود. کاربردهایش بافت‌دادن در صفحه‌ی هویت است و اینکه یکی از آن چهار چیزی است که می‌توانی در لیگ انتخاب کنی به اشتراک بگذاری.",
      ar: "تصف الشخصية نمطك العام لا أنها تقيّم يوما، فهي لا تدخل في درجة عافيتك. واستخداماتها هي السياق في صفحة الهوية، وكونها واحدة من الأشياء الأربعة التي يمكنك اختيار مشاركتها في الدوري.",
      zh: "画像描述的是你的整体模式，而不是给某一天打分，所以它不会进入你的健康分数计算。它的用途是在身份页面提供背景信息，以及作为你可以在联赛中选择分享的四项内容之一。",
    },

    {
      key: 'app_badges_private_vs_shared',
      match: /\b(which badges are shared|are my badges visible to friends)(?:s|es|ing)?\b|کدام نشان‌ها به اشتراک گذاشته میشوند|نشان‌هایم برای دوستان دیده میشود|أي الأوسمة تُشارك|هل يرى أصدقائي أوسمتي|哪些徽章会被分享|朋友能看到我的徽章吗/i,
      en: "Badges aren't one of the four League sharing categories, so they aren't pushed to friends. The ones marked private are additionally kept out of anything outward-facing on purpose, because an awareness indicator shouldn't become something to compete over.",
      fa: "نشان‌ها یکی از آن چهار دسته‌ی اشتراک‌گذاری لیگ نیستند، پس به دوستان فرستاده نمی‌شوند. آن‌هایی که خصوصی علامت خورده‌اند به‌علاوه عمداً از هر چیز رو‌به‌بیرونی بیرون نگه داشته می‌شوند، چون یک نشانگر آگاهی نباید به چیزی برای رقابت تبدیل شود.",
      ar: "الأوسمة ليست إحدى فئات المشاركة الأربع في الدوري، فلا تُدفع إلى الأصدقاء. وتلك الموسومة كخاصة تُبقى إضافةً خارج أي شيء موجَّه للخارج عن قصد، لأن مؤشر الوعي لا ينبغي أن يصير شيئا يُتنافس عليه.",
      zh: "徽章不属于联赛的四个分享类别，所以不会推送给好友。被标记为私密的那些还会被刻意排除在任何对外展示之外，因为一个用于自我觉察的指标不该变成竞争的对象。",
    },

    {
      key: 'app_score_range_0_100',
      match: /\b(is the score out of 100|what is the score scale|max score)(?:s|es|ing)?\b|امتیاز از صد است|مقیاس امتیاز چیست|هل الدرجة من 100|ما مقياس الدرجة|分数是满分100吗|分数的范围/i,
      en: "The wellness score runs 0 to 100. In practice the extremes are rare - the model produces them from real input patterns rather than curving to fill the range, so most days land in a narrower band and small moves within it are still meaningful.",
      fa: "امتیاز سلامت از ۰ تا ۱۰۰ است. در عمل حدهای انتهایی نادرند - مدل آن‌ها را از الگوهای ورودی واقعی می‌سازد نه اینکه برای پرکردن بازه منحنی بکشد، پس بیشتر روزها در باندی باریک‌تر می‌نشینند و حرکت‌های کوچک داخل آن هنوز معنادارند.",
      ar: "تتراوح درجة العافية من 0 إلى 100. وعمليا الأطراف نادرة - فالنموذج ينتجها من أنماط مدخلات حقيقية لا بتقويس لملء المدى، فتقع معظم الأيام في نطاق أضيق وتظل الحركات الصغيرة داخله ذات معنى.",
      zh: "健康分数的范围是 0 到 100。实际上极端值很少见——模型是从真实的输入模式产生这些分数的，而不是为了填满整个区间而做曲线调整，所以大多数日子会落在更窄的区间里，而区间内的小幅变动依然有意义。",
    },

    {
      key: 'app_does_it_judge_me',
      match: /\b(is the app judging me|does a low score mean im failing|i feel bad about my score)(?:s|es|ing)?\b|برنامه من را قضاوت میکند|امتیاز پایین یعنی شکست خوردم|هل يحكم عليّ التطبيق|هل الدرجة المنخفضة تعني فشلي|应用是在评判我吗|低分意味着我失败了吗/i,
      en: "A score is a description of one day's inputs, not a verdict on you. The app deliberately compares you to your own past rather than to other people, has no global leaderboard, and treats direction as more informative than level - a rising 55 is a better signal than a static 75.",
      fa: "یک امتیاز توصیف ورودی‌های یک روز است، نه حکمی درباره‌ی تو. اپ عمداً تو را با گذشته‌ی خودت مقایسه می‌کند نه با آدم‌های دیگر، هیچ جدول رده‌بندی جهانی ندارد، و جهت را آموزنده‌تر از سطح می‌داند - یک ۵۵ صعودی سیگنال بهتری از یک ۷۵ ثابت است.",
      ar: "الدرجة وصف لمدخلات يوم واحد، لا حكم عليك. والتطبيق يقارنك عمدا بماضيك أنت لا بالآخرين، وليس فيه لوحة صدارة عالمية، ويعدّ الاتجاه أكثر إفادة من المستوى - فـ55 صاعدة إشارة أفضل من 75 ثابتة.",
      zh: "分数是对某一天输入数据的描述，不是对你这个人的判决。应用刻意让你和自己的过去比较，而不是和别人比，没有全局排行榜，并且认为方向比水平更有信息量——一个正在上升的 55 分，比一个停滞的 75 分是更好的信号。",
    },

    
    // ====== AH. Demo walkthrough, scope, self-hosting and the coach's own remit ======
    {
      key: 'app_where_is_demo_button',
      match: /\b(where is the demo button|how do i start a demo|cant find demo mode)(?:s|es|ing)?\b|دکمه دمو کجاست|چطور دمو را شروع کنم|أين زر العرض التجريبي|كيف أبدأ الديمو|演示按钮在哪|怎么开始演示/i,
      en: "Demo Mode is started from Settings, and you have to be signed in first - it swaps your session for a synthetic one, so there has to be a real session to stash and restore. The picker then asks for the length and the profile before it builds anything.",
      fa: "حالت دمو از تنظیمات شروع می‌شود و اول باید وارد شده باشی - نشستت را با یک نشست مصنوعی عوض می‌کند، پس باید یک نشست واقعی باشد که کنار گذاشته و بازگردانده شود. بعد انتخابگر پیش از ساختن هر چیزی طول و پروفایل را می‌پرسد.",
      ar: "يبدأ وضع العرض التجريبي من الإعدادات، وعليك تسجيل الدخول أولا - فهو يبدّل جلستك بأخرى اصطناعية، فلا بد من جلسة حقيقية تُحفظ وتُستعاد. ثم يسأل المنتقي عن المدة والملف قبل أن يبني أي شيء.",
      zh: "演示模式从设置里启动，而且你必须先登录——它会把你的会话换成一个合成会话，所以必须有一个真实会话可供暂存和恢复。之后选择器会先询问天数和档案，然后才开始生成。",
    },

    {
      key: 'app_demo_takes_a_while',
      match: /\b(why does the demo take time to build|demo is generating|demo loading)(?:s|es|ing)?\b|چرا ساخت دمو طول میکشد|دمو در حال ساخت است|لماذا يستغرق بناء الديمو وقتا|الديمو قيد التوليد|演示为什么要生成一会儿|演示正在生成/i,
      en: "Each demo day is a real model prediction, not a canned number, so a 23-day demo runs the pipeline 23 times plus builds the League side. The processing screen names the length you actually chose as it goes, so you can see it's working on your selection.",
      fa: "هر روز دمو یک پیش‌بینی واقعی مدل است نه یک عدد آماده، پس یک دموی ۲۳ روزه خط لوله را ۲۳ بار اجرا می‌کند به‌علاوه ساختن سمت لیگ. صفحه‌ی پردازش همان طولی را که واقعاً انتخاب کرده‌ای در حین کار نام می‌برد، تا ببینی دارد روی انتخاب تو کار می‌کند.",
      ar: "كل يوم في العرض التجريبي تنبؤ نموذج حقيقي لا رقما جاهزا، فديمو من 23 يوما يشغّل خط الأنابيب 23 مرة إضافة إلى بناء جانب الدوري. وشاشة المعالجة تذكر المدة التي اخترتها فعلا أثناء العمل، فترى أنها تعمل على اختيارك.",
      zh: "演示里的每一天都是一次真实的模型预测，而不是预设好的数字，所以 23 天的演示会把整条流程跑 23 遍，还要构建联赛那一侧。处理界面会在过程中显示你实际选择的天数，这样你能看出它正在按你的选择工作。",
    },

    {
      key: 'app_demo_shorter_vs_longer',
      match: /\b(should i pick 3 or 23 days|which demo length is best|difference between demo lengths)(?:s|es|ing)?\b|۳ روزه یا ۲۳ روزه|کدام طول دمو بهتر است|أختار 3 أم 23 يوما|أي مدة ديمو أفضل|选3天还是23天|演示时长的区别/i,
      en: "Short demos build fast but leave the history-dependent pages thin, since trends and correlations need days to exist at all. 23 days is the only length where everything has enough behind it - pick short to look around quickly, long to see the app complete.",
      fa: "دموهای کوتاه سریع ساخته می‌شوند اما صفحه‌های وابسته به تاریخچه را نازک می‌گذارند، چون روندها و همبستگی‌ها برای اینکه اصلاً وجود داشته باشند به روز نیاز دارند. ۲۳ روز تنها طولی است که همه‌چیز پشتش به‌اندازه‌ی کافی هست - کوتاه را برای یک نگاه سریع انتخاب کن و بلند را برای دیدن کاملِ اپ.",
      ar: "الديمو القصير يُبنى سريعا لكنه يترك الصفحات المعتمدة على التاريخ رقيقة، لأن الاتجاهات والارتباطات تحتاج أياما كي توجد أصلا. و23 يوما هي المدة الوحيدة التي يكون خلف كل شيء فيها ما يكفي - اختر القصير لجولة سريعة، والطويل لرؤية التطبيق كاملا.",
      zh: "短演示生成得快，但会让依赖历史的页面很单薄，因为趋势和相关性本来就需要足够的天数才能成立。23 天是唯一让所有内容都有足够支撑的长度——想快速看看就选短的，想看到完整的应用就选长的。",
    },

    {
      key: 'app_after_demo_my_data',
      match: /\b(is my data still there after a demo|did the demo delete my history)(?:s|es|ing)?\b|بعد از دمو داده‌هایم هست|دمو تاریخچه‌ام را حذف کرد|هل بياناتي موجودة بعد الديمو|هل حذف الديمو سجلي|演示结束后我的数据还在吗|演示删掉了我的历史吗/i,
      en: "Your real account is untouched. The demo runs on a completely separate synthetic account while your real token is stashed, and leaving swaps it back - nothing written during a demo can reach your history because it was never writing to your account in the first place.",
      fa: "حساب واقعی‌ات دست‌نخورده است. دمو روی یک حساب مصنوعیِ کاملاً جدا اجرا می‌شود در حالی که توکن واقعی‌ات کنار گذاشته شده، و خروج آن را برمی‌گرداند - هیچ چیزی که در حین دمو نوشته شده نمی‌تواند به تاریخچه‌ات برسد چون از اول اصلاً روی حساب تو نمی‌نوشت.",
      ar: "حسابك الحقيقي لم يُمَس. فالديمو يعمل على حساب اصطناعي منفصل تماما بينما يُحفظ رمزك الحقيقي، والمغادرة تعيده - ولا شيء كُتب أثناء الديمو يمكن أن يصل إلى سجلك لأنه لم يكن يكتب إلى حسابك أصلا.",
      zh: "你的真实账户完全没有被触碰。演示运行在一个完全独立的合成账户上，同时你的真实令牌被暂存起来，退出时再换回来——演示期间写入的任何内容都到不了你的历史，因为它从一开始就不是在往你的账户里写。",
    },

    {
      key: 'app_judge_walkthrough',
      match: /\b(how should i demo this to someone|best way to present the app|show the app to a judge)(?:s|es|ing)?\b|چطور این را به کسی نشان بدهم|بهترین راه ارائه اپ|كيف أعرض هذا لشخص|أفضل طريقة لتقديم التطبيق|怎么向别人演示|展示应用的最佳方式/i,
      en: "A 23-day borderline demo, then the result page for the factors and confidence, then analytics for the trend and the future letter, then the coach for questions answered from that data. For the League chat you need a second account in another browser - one account cannot show a conversation.",
      fa: "یک دموی ۲۳ روزه‌ی مرزی، بعد صفحه‌ی نتیجه برای عامل‌ها و اطمینان، بعد تحلیل‌ها برای روند و نامه‌ی آینده، بعد مربی برای سؤال‌هایی که از همان داده جواب داده می‌شوند. برای چت لیگ به یک حساب دوم در مرورگری دیگر نیاز داری - یک حساب نمی‌تواند یک گفت‌وگو را نشان دهد.",
      ar: "ديمو حدّي من 23 يوما، ثم صفحة النتيجة للعوامل والثقة، ثم التحليلات للاتجاه ورسالة المستقبل، ثم المدرب لأسئلة تُجاب من تلك البيانات. أما لمحادثة الدوري فتحتاج حسابا ثانيا في متصفح آخر - فحساب واحد لا يستطيع عرض حوار.",
      zh: "先做一个 23 天的「临界」演示，然后看结果页的影响因素和置信度，接着看分析页的趋势和未来信，最后用教练提问、看它如何基于这些数据作答。至于联赛聊天，你需要在另一个浏览器里再开一个账户——单个账户无法展示一场对话。",
    },

    {
      key: 'app_no_data_yet_what_to_do',
      match: /\b(i have no data yet|brand new account what now|empty account)(?:s|es|ing)?\b|هنوز داده ندارم|حساب کاملا جدید|ليس لدي بيانات بعد|حساب جديد تماما|我还没有数据|全新账户该做什么/i,
      en: "Two routes: log a real check-in, which gives you a genuine score immediately but needs days to unlock trends, or start Demo Mode to see the full app on synthetic-but-model-scored data without waiting. The demo never touches your real account, so you can do both.",
      fa: "دو راه: یک چک‌این واقعی ثبت کن که فوراً یک امتیاز اصیل می‌دهد ولی برای باز‌شدن روندها به روز نیاز دارد، یا حالت دمو را شروع کن تا اپ کامل را روی داده‌ی مصنوعی‌اما‌امتیازگرفته‌از‌مدل ببینی بدون انتظار. دمو هرگز به حساب واقعی‌ات دست نمی‌زند، پس می‌توانی هر دو را انجام دهی.",
      ar: "طريقان: سجّل تسجيلا حقيقيا يمنحك درجة أصيلة فورا لكنه يحتاج أياما لفتح الاتجاهات، أو ابدأ وضع العرض التجريبي لترى التطبيق كاملا على بيانات اصطناعية لكن مقيَّمة بالنموذج دون انتظار. والديمو لا يمس حسابك الحقيقي أبدا، فيمكنك فعل الاثنين.",
      zh: "有两条路：做一次真实打卡，会立刻得到一个真实分数，但需要积累几天才能解锁趋势；或者启动演示模式，无需等待就能在合成但经过模型评分的数据上看到完整的应用。演示绝不会触碰你的真实账户，所以两者都可以做。",
    },

    {
      key: 'app_how_is_this_different',
      match: /\b(how is this different from screen time apps|why not just use my phones screen time|different from screen time apps|difference from screen time apps|why not just screen time)(?:s|es|ing)?\b|تفاوت این با اپ‌های زمان صفحه چیست|چرا از زمان صفحه گوشی استفاده نکنم|كيف يختلف عن تطبيقات وقت الشاشة|لماذا لا أستخدم وقت شاشة هاتفي|和屏幕时间应用有什么不同|为什么不直接用手机的屏幕时间/i,
      en: "Your phone tells you how long you used it. This scores the day against a trained model, names which of your own fields moved that score and by how much, and puts it next to sleep, mood, focus and activity - the point isn't the minutes, it's what they sat alongside.",
      fa: "گوشی‌ات به تو می‌گوید چقدر ازش استفاده کرده‌ای. این، روز را در برابر یک مدل آموزش‌دیده می‌سنجد، نام می‌برد کدام‌یک از فیلدهای خودت آن امتیاز را جابه‌جا کرده و چقدر، و کنار خواب، خلق‌وخو، تمرکز و فعالیت می‌گذاردش - نکته دقیقه‌ها نیستند، نکته این است که کنار چه چیزهایی نشسته‌اند.",
      ar: "هاتفك يخبرك كم استخدمته. أما هذا فيقيّم اليوم مقابل نموذج مدرَّب، ويسمّي أي حقولك أنت حرّك تلك الدرجة وبأي مقدار، ويضعه بجانب النوم والمزاج والتركيز والنشاط - فالمقصد ليس الدقائق بل ما جاورها.",
      zh: "手机告诉你用了多久。而这个应用会用训练过的模型给这一天评分，指出是你自己的哪些字段推动了分数、推动了多少，并把它和睡眠、情绪、专注、身体活动放在一起——重点不是分钟数，而是这些分钟旁边还有什么。",
    },

    {
      key: 'app_privacy_third_party',
      match: /\b(do you share my data with third parties|is anything sent to another company|share my data with third parties|third party data sharing)(?:s|es|ing)?\b|داده‌ام را با شرکت‌های دیگر به اشتراک میگذارید|چیزی به جای دیگری فرستاده میشود|هل تشاركون بياناتي مع أطراف ثالثة|هل يُرسل شيء لشركة أخرى|会把我的数据分享给第三方吗|有内容发送给其他公司吗/i,
      en: "Not by default. The only path anything takes off this server is one you switch on yourself: the optional coach connector, where your message goes from your browser directly to the AI provider whose key you supplied. With it off, nothing leaves.",
      fa: "به‌طور پیش‌فرض نه. تنها مسیری که چیزی از این سرور بیرون می‌رود همانی است که خودت روشنش می‌کنی: کانکتور اختیاری مربی، جایی که پیامت از مرورگرت مستقیم به همان ارائه‌دهنده‌ی هوش مصنوعی که کلیدش را داده‌ای می‌رود. با خاموش‌بودنش، هیچ چیز بیرون نمی‌رود.",
      ar: "ليس افتراضيا. فالمسار الوحيد الذي يخرج به شيء من هذا الخادم هو مسار تشغّله أنت بنفسك: موصّل المدرب الاختياري، حيث تذهب رسالتك من متصفحك مباشرة إلى مزود الذكاء الاصطناعي الذي قدّمت مفتاحه. ومع إيقافه، لا يخرج شيء.",
      zh: "默认不会。唯一会让内容离开这台服务器的路径，是你自己主动开启的：可选的教练连接器——你的消息会从浏览器直接发往你提供密钥的那家 AI 服务商。关闭它时，什么都不会外发。",
    },

    {
      key: 'app_can_i_self_host',
      match: /\b(can i run this myself|self host|run it locally)(?:s|es|ing)?\b|میتوانم خودم اجرایش کنم|اجرای محلی|هل أشغّله بنفسي|تشغيل محلي|我能自己部署吗|本地运行/i,
      en: "It's a FastAPI backend with a static frontend, run from the project's own entry point rather than by opening the HTML files directly - serving the frontend with a plain file server skips the API and the pages won't work. The repository has the setup steps.",
      fa: "یک بک‌اند FastAPI با فرانت‌اند استاتیک است که از نقطه‌ی ورودی خود پروژه اجرا می‌شود نه با باز‌کردن مستقیم فایل‌های HTML - سرو‌کردن فرانت‌اند با یک فایل‌سرور ساده از API رد می‌شود و صفحه‌ها کار نمی‌کنند. مخزن مراحل راه‌اندازی را دارد.",
      ar: "إنه خادم FastAPI مع واجهة أمامية ساكنة، يُشغَّل من نقطة دخول المشروع نفسها لا بفتح ملفات HTML مباشرة - فتقديم الواجهة بخادم ملفات بسيط يتجاوز الواجهة البرمجية ولن تعمل الصفحات. والمستودع يحوي خطوات الإعداد.",
      zh: "它是一个 FastAPI 后端加静态前端，需要从项目自己的入口点启动，而不是直接打开 HTML 文件——用普通文件服务器托管前端会绕过 API，页面无法正常工作。仓库里有安装步骤。",
    },

    {
      key: 'app_tests_and_quality',
      match: /\b(is this tested|how do you know it works|does it have tests)(?:s|es|ing)?\b|این تست شده|از کجا میدانید کار میکند|هل هذا مُختبَر|كيف تعرفون أنه يعمل|有测试吗|你们怎么知道它能用/i,
      en: "There's an automated test suite covering the API, the services and the frontend logic, including the coach's intent matching measured against a corpus of thousands of phrasings and typos in all four languages. That's also why the coach declines rather than guesses - the declines are tested too.",
      fa: "یک مجموعه‌ی تست خودکار هست که API، سرویس‌ها و منطق فرانت‌اند را پوشش می‌دهد، از جمله تطبیق نیت مربی که در برابر کورپوسی از هزاران عبارت و غلط تایپی در هر چهار زبان سنجیده می‌شود. برای همین هم است که مربی به‌جای حدس‌زدن خودداری می‌کند - همان خودداری‌ها هم تست شده‌اند.",
      ar: "توجد مجموعة اختبارات آلية تغطي الواجهة البرمجية والخدمات ومنطق الواجهة الأمامية، بما في ذلك مطابقة نوايا المدرب مقيسةً على مدونة من آلاف الصياغات والأخطاء المطبعية باللغات الأربع. ولهذا أيضا يمتنع المدرب بدل التخمين - فحالات الامتناع مُختبَرة هي الأخرى.",
      zh: "有一套自动化测试，覆盖 API、各项服务和前端逻辑，其中包括教练的意图匹配——它是在一个包含数千条不同表述和拼写错误、涵盖四种语言的语料库上测量的。这也是为什么教练会选择拒答而不是猜测——那些拒答同样是被测试过的。",
    },

    {
      key: 'app_what_is_not_included',
      match: /\b(what doesnt this app do|what are the limitations|what is missing|what this app does not do|limitations of this app)(?:s|es|ing)?\b|این اپ چه کاری نمیکند|محدودیت‌ها چیستند|ما الذي لا يفعله التطبيق|ما هي القيود|这个应用不能做什么|有哪些局限/i,
      en: "It doesn't track anything automatically, send reminders, work offline, diagnose anything, or export your whole history in one file. It also can't tell an unusual day from a bad habit without you marking it. Those are real limits, stated rather than hidden.",
      fa: "چیزی را خودکار ردیابی نمی‌کند، یادآوری نمی‌فرستد، آفلاین کار نمی‌کند، چیزی را تشخیص نمی‌دهد، و کل تاریخچه‌ات را در یک فایل خروجی نمی‌دهد. ضمناً بدون اینکه خودت علامت بزنی نمی‌تواند یک روز غیرعادی را از یک عادت بد تشخیص دهد. این‌ها محدودیت‌های واقعی‌اند که گفته شده‌اند نه پنهان.",
      ar: "لا يتتبع شيئا تلقائيا، ولا يرسل تذكيرات، ولا يعمل دون اتصال، ولا يشخّص شيئا، ولا يصدّر سجلك كله في ملف واحد. كما لا يستطيع تمييز يوم غير عادي عن عادة سيئة دون أن تسمه أنت. وهذه قيود حقيقية مُعلنة لا مخفاة.",
      zh: "它不会自动追踪任何东西，不发提醒，不能离线使用，不做诊断，也不能把你的全部历史导出成一个文件。它同样无法在你不标记的情况下区分「不寻常的一天」和「坏习惯」。这些都是真实的局限，是明说的而不是隐藏的。",
    },

    {
      key: 'app_coach_knows_about_itself',
      match: /\b(can you tell me about the app|help me with the app|i need help using this|help me use the app|help with this app)(?:s|es|ing)?\b|درباره خود اپ به من بگو|در استفاده از اپ کمکم کن|راهنمایی میخواهم|أخبرني عن التطبيق|ساعدني في استخدامه|أحتاج مساعدة|跟我说说这个应用|帮我用这个应用|我需要帮助/i,
      en: "Ask anything about the app and I'll answer from how it actually works - the pages, the check-in fields, CSV import, Demo Mode, the League, the games, errors, privacy, what the models do. Typos and different phrasings are fine; if I still can't place a question I'll name the closest topics rather than guess.",
      fa: "هر چیزی درباره‌ی اپ بپرس و من از روی نحوه‌ی واقعی کارکردنش جواب می‌دهم - صفحه‌ها، فیلدهای چک‌این، ورود CSV، حالت دمو، لیگ، بازی‌ها، خطاها، حریم خصوصی، اینکه مدل‌ها چه می‌کنند. غلط تایپی و عبارت‌بندی متفاوت اشکالی ندارد؛ اگر باز هم نتوانم سؤالی را جا بیندازم، به‌جای حدس‌زدن نزدیک‌ترین موضوع‌ها را نام می‌برم.",
      ar: "اسأل أي شيء عن التطبيق وسأجيب من واقع كيفية عمله فعلا - الصفحات، وحقول التسجيل، واستيراد سي إس في، ووضع العرض التجريبي، والدوري، والألعاب، والأخطاء، والخصوصية، وما تفعله النماذج. والأخطاء المطبعية والصياغات المختلفة لا بأس بها؛ وإن عجزت عن تحديد سؤال فسأسمّي أقرب المواضيع بدل التخمين.",
      zh: "关于这个应用，你可以问任何问题，我会依据它实际的运作方式来回答——各个页面、打卡字段、CSV 导入、演示模式、联赛、游戏、错误、隐私，以及模型都做了什么。有错别字或换个说法都没关系；如果我仍然无法定位你的问题，我会指出最接近的几个主题，而不是瞎猜。",
    },

  ];

  window.DWCoachKnowledge.register(TOPICS, { priority: 10 });
})();
