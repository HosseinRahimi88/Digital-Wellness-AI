/*
  Guide content for the app's controls, not its data.

  Everything registered before this file explains a READING - a score, an
  arc, a badge, a trend. That covers the interesting half of the screen
  and leaves the other half silent: the language switcher, the theme
  toggle, the music widget, the Back button, the field you just clicked
  into. A user who taps one of those and gets nothing has learned that
  the guide is decoration on some parts of the page, which is worse than
  a guide that is consistently present.

  So these are the topics the click layer (guide-click.js) falls back
  through when the thing clicked is furniture rather than a figure. They
  are deliberately short - a control needs one sentence about what it
  does and, where it matters, one about what it does NOT do. The
  toggles are the case that matters: users assume switching a toggle
  changes the prediction, and it never does.
*/
(function () {
  if (!window.DWGuide || !window.DWGuide.register) return;

  window.DWGuide.register({
    ctl_nav: {
      face: 'neutral',
      priority: 30,
      en: "This is the way around the app. Every section keeps its own state, so moving between them never discards a check-in you have already saved - and nothing here re-runs the model, so your score cannot change just because you looked at a different page.",
      fa: "این مسیر گشتن در برنامه است. هر بخش وضعیت خودش را نگه می‌دارد، پس جابه‌جا شدن بینشان هیچ‌وقت ثبتی را که ذخیره کرده‌ای دور نمی‌ریزد — و هیچ‌چیز اینجا مدل را دوباره اجرا نمی‌کند، پس امتیازت فقط به این دلیل که صفحه‌ی دیگری را نگاه کرده‌ای عوض نمی‌شود.",
      ar: "هذه طريقة التنقّل في التطبيق. كل قسم يحتفظ بحالته الخاصة، فالانتقال بينها لا يُسقط أبداً تسجيلاً حفظته — ولا شيء هنا يعيد تشغيل النموذج، فدرجتك لا تتغيّر لمجرّد أنك نظرت إلى صفحة أخرى.",
      zh: "这是在应用里走动的方式。每个板块都保留自己的状态，所以在它们之间切换永远不会丢掉你已保存的记录——而且这里没有任何东西会重新运行模型，所以你的分数不会仅仅因为你看了另一个页面就改变。",
    },

    ctl_language: {
      face: 'good',
      priority: 34,
      en: "Four languages, and the switch changes everything at once - the interface, my explanations, the coach, and the direction the page reads in. It changes not one thing the model sees: the same day logged in Persian and in English produces exactly the same score.",
      fa: "چهار زبان، و این کلید همه‌چیز را یک‌جا عوض می‌کند — رابط کاربری، توضیح‌های من، مربی، و جهتی که صفحه در آن خوانده می‌شود. اما حتی یک چیز از آنچه مدل می‌بیند را عوض نمی‌کند: یک روزِ یکسان که به فارسی ثبت شود و به انگلیسی، دقیقاً همان امتیاز را می‌گیرد.",
      ar: "أربع لغات، والمبدّل يغيّر كل شيء دفعة واحدة — الواجهة وشروحي والمدرّب واتجاه قراءة الصفحة. لكنه لا يغيّر شيئاً واحداً مما يراه النموذج: اليوم نفسه مسجَّلاً بالفارسية أو بالإنجليزية ينتج الدرجة ذاتها تماماً.",
      zh: "四种语言，这个开关会一次性改变所有东西——界面、我的讲解、教练，以及页面的阅读方向。它不会改变模型所看到的任何一样东西：同一天用波斯语记录和用英语记录，得到的分数完全一样。",
    },

    ctl_theme: {
      face: 'good',
      priority: 32,
      en: "Light and dark. Your choice is remembered in this browser only, and it is independent of every other switch here - turning the theme over never turns off sound, motion or anything else.",
      fa: "روشن و تاریک. انتخابت فقط در همین مرورگر به‌خاطر سپرده می‌شود و از هر کلید دیگری اینجا مستقل است — عوض‌کردن پوسته هیچ‌وقت صدا، حرکت یا چیز دیگری را خاموش نمی‌کند.",
      ar: "فاتح وداكن. اختيارك محفوظ في هذا المتصفّح وحده، وهو مستقل عن كل مفتاح آخر هنا — قلب السمة لا يُطفئ الصوت ولا الحركة ولا أي شيء آخر.",
      zh: "浅色和深色。你的选择只记在这个浏览器里，并且独立于这里的每一个其他开关——切换主题绝不会关掉声音、动效或别的什么。",
    },

    ctl_sound_fx: {
      face: 'good',
      priority: 32,
      en: "The short sounds - a click, a chime when a score lands. Separate from the ambient music and separate from my voice, so you can keep one and silence the others.",
      fa: "صداهای کوتاه — یک کلیک، یک زنگ وقتی امتیاز می‌نشیند. جدا از موسیقی محیطی و جدا از صدای من، پس می‌توانی یکی را نگه داری و بقیه را ساکت کنی.",
      ar: "الأصوات القصيرة — نقرة، ورنّة حين تستقرّ الدرجة. منفصلة عن الموسيقى المحيطة وعن صوتي، فيمكنك إبقاء واحد وإسكات البقية.",
      zh: "那些短促的声音——一次点击、分数落定时的一记轻响。它与环境音乐分开，也与我的声音分开，所以你可以留下一个、把其他的静音。",
    },

    ctl_music: {
      face: 'good',
      priority: 30,
      en: "Ambient sound while you use the app. It plays from files stored in your own browser, so nothing is streamed and nothing is sent anywhere - and you can add your own track instead of the ones shipped with the app.",
      fa: "صدای محیطی در حین استفاده از برنامه. از فایل‌هایی پخش می‌شود که در مرورگر خودت ذخیره شده‌اند، پس هیچ‌چیز استریم نمی‌شود و هیچ‌چیز جایی فرستاده نمی‌شود — و می‌توانی به‌جای قطعه‌هایی که با برنامه آمده‌اند، قطعه‌ی خودت را اضافه کنی.",
      ar: "صوت محيط أثناء استخدامك للتطبيق. يُشغَّل من ملفات مخزَّنة في متصفّحك أنت، فلا شيء يُبثّ ولا شيء يُرسل إلى أي مكان — ويمكنك إضافة مقطعك الخاص بدل المقاطع المرفقة بالتطبيق.",
      zh: "你使用应用时的环境声音。它播放的是存在你自己浏览器里的文件，所以没有任何东西在流式传输，也没有任何东西被发送到别处——而且你可以加入自己的音轨，替换应用自带的那些。",
    },

    ctl_motion: {
      face: 'thinking',
      priority: 32,
      en: "Reduced motion strips the animation out and leaves every number, every arc and every badge exactly where it was. It simplifies how things arrive on screen, never what is on screen.",
      fa: "حرکت کاهش‌یافته انیمیشن را برمی‌دارد و هر عدد، هر کمان و هر نشان را دقیقاً سر جای خودش می‌گذارد. فقط شیوه‌ی رسیدن چیزها به صفحه را ساده می‌کند، نه آنچه روی صفحه هست.",
      ar: "الحركة المخفَّضة تنزع الرسوم المتحركة وتُبقي كل رقم وكل قوس وكل شارة تماماً في مكانها. تُبسِّط كيف تصل الأشياء إلى الشاشة، لا ما هو على الشاشة.",
      zh: "减弱动效会去掉动画，而把每个数字、每条弧线、每枚徽章都留在原处。它简化的是东西如何出现在屏幕上，而不是屏幕上有什么。",
    },

    ctl_settings: {
      face: 'neutral',
      priority: 34,
      en: "Everything that changes how the app behaves towards you, in one place - and nothing in here is an input to the model. Theme, sound, motion, my voice and Demo Mode are five independent switches; none of them touches a saved check-in.",
      fa: "هر چیزی که رفتار برنامه با تو را عوض می‌کند، یک‌جا — و هیچ‌کدام از اینها ورودی مدل نیست. پوسته، صدا، حرکت، صدای من و حالت نمایشی پنج کلید مستقل‌اند؛ هیچ‌کدام به ثبتِ ذخیره‌شده‌ای دست نمی‌زند.",
      ar: "كل ما يغيّر سلوك التطبيق تجاهك، في مكان واحد — ولا شيء هنا مدخَل للنموذج. السمة والصوت والحركة وصوتي ووضع العرض خمسة مفاتيح مستقلة؛ لا يمسّ أيٌّ منها تسجيلاً محفوظاً.",
      zh: "所有会改变应用对待你的方式的东西，都在这一处——而且这里没有一样是模型的输入。主题、声音、动效、我的声音和演示模式是五个独立开关；它们都不会碰到任何已保存的记录。",
    },

    ctl_logout: {
      face: 'thinking',
      priority: 40,
      en: "Signing out clears the key this browser was using, nothing more. Your check-ins, badges and history stay exactly where they are and come back when you sign in again.",
      fa: "خروج فقط کلیدی را که این مرورگر استفاده می‌کرد پاک می‌کند، نه بیشتر. ثبت‌ها، نشان‌ها و تاریخچه‌ات دقیقاً همان‌جا می‌مانند و وقتی دوباره وارد شوی برمی‌گردند.",
      ar: "تسجيل الخروج يمسح المفتاح الذي كان هذا المتصفّح يستخدمه، لا أكثر. تسجيلاتك وشاراتك وسجلّك تبقى تماماً في مكانها وتعود حين تسجّل الدخول مجدداً.",
      zh: "退出登录只会清掉这个浏览器一直在用的那把钥匙，仅此而已。你的记录、徽章和历史都原封不动地留着，你再次登录时它们就回来了。",
    },

    ctl_tour: {
      face: 'good',
      priority: 38,
      en: "This walks you through the current page one section at a time. It runs by itself on your first visit and then stops - press this whenever you want it back.",
      fa: "این تو را بخش‌به‌بخش در صفحه‌ی فعلی راه می‌برد. بار اولی که می‌آیی خودش اجرا می‌شود و بعد متوقف می‌ماند — هر وقت خواستی برگردد، همین را بزن.",
      ar: "هذا يأخذك في جولة على الصفحة الحالية قسماً قسماً. يعمل من تلقاء نفسه في زيارتك الأولى ثم يتوقّف — اضغط هنا متى أردت عودته.",
      zh: "这会带你一个板块一个板块地走一遍当前页面。第一次来时它会自己运行，之后就停下——想让它回来时按这里就好。",
    },

    ctl_mascot: {
      face: 'great',
      priority: 44,
      en: "That is me. Tap me and I explain wherever you are; tap anything on the page and I explain that instead. If I talk too much, closing me twice on the same subject makes me leave it alone for a while - I stay available, I just stop volunteering.",
      fa: "آن منم. رویم بزن تا هرجا که هستی را توضیح بدهم؛ روی هر چیزی در صفحه بزن تا به‌جایش آن را توضیح بدهم. اگر زیادی حرف زدم، دو بار بستنم روی یک موضوع باعث می‌شود مدتی کاری به آن نداشته باشم — در دسترس می‌مانم، فقط دیگر خودم پیش‌قدم نمی‌شوم.",
      ar: "ذاك أنا. انقرني لأشرح أينما كنت؛ وانقر أي شيء في الصفحة لأشرحه بدلاً من ذلك. وإن أكثرتُ الكلام، فإغلاقي مرتين على الموضوع نفسه يجعلني أتركه فترة — أبقى متاحاً، لكنني أكفّ عن المبادرة.",
      zh: "那就是我。点我，我就讲你所在的地方；点页面上的任何东西，我就改讲那个。如果我话太多，在同一个话题上关我两次，我就会有一阵子不去碰它——我仍然随叫随到，只是不再主动开口。",
    },

    ctl_primary_action: {
      face: 'good',
      priority: 36,
      en: "This is the button that actually does the thing on this page. Where it saves a day or runs a prediction, that is the one moment your history changes - everything else you have clicked so far only looked at it.",
      fa: "این همان دکمه‌ای است که واقعاً کارِ این صفحه را انجام می‌دهد. جایی که روزی را ذخیره می‌کند یا پیش‌بینی‌ای را اجرا می‌کند، همان تنها لحظه‌ای است که تاریخچه‌ات عوض می‌شود — هر چیز دیگری که تا حالا زده‌ای فقط نگاهش کرده است.",
      ar: "هذا هو الزر الذي ينفّذ فعلاً عمل هذه الصفحة. حيث يحفظ يوماً أو يشغّل تنبؤاً، فتلك هي اللحظة الوحيدة التي يتغيّر فيها سجلّك — وكل ما نقرته حتى الآن كان مجرّد نظر إليه.",
      zh: "这是真正执行本页面那件事的按钮。当它保存一天或运行一次预测时，那就是你的历史唯一会改变的时刻——你此前点过的一切都只是在看它。",
    },

    ctl_step_nav: {
      face: 'neutral',
      priority: 30,
      en: "Moving between steps. Going back never loses what you have already typed, and nothing is recorded until you reach the end and submit - so you can walk the whole form and change your mind.",
      fa: "جابه‌جایی بین مرحله‌ها. برگشتن هیچ‌وقت چیزی را که تایپ کرده‌ای از دست نمی‌دهد، و تا به آخر نرسی و ثبت نکنی هیچ‌چیز ضبط نمی‌شود — پس می‌توانی کل فرم را راه بروی و نظرت را عوض کنی.",
      ar: "التنقّل بين الخطوات. الرجوع لا يُفقدك ما كتبته، ولا يُسجَّل شيء حتى تصل إلى النهاية وترسل — فيمكنك المرور بالنموذج كلّه ثم تغيير رأيك.",
      zh: "在步骤之间移动。往回走绝不会丢掉你已经填好的内容，而且在你走到最后并提交之前，什么都不会被记录——所以你可以把整个表单走一遍，再改主意。",
    },

    ctl_field: {
      face: 'thinking',
      priority: 28,
      en: "Whatever you put here is the only thing the model ever sees about this - there is no hidden default and no filled-in average standing in for you. If you are unsure, an honest rough answer is better than a precise invented one, because a made-up number moves the score just as hard as a real one.",
      fa: "هرچه اینجا بگذاری، تنها چیزی است که مدل درباره‌ی این موضوع می‌بیند — هیچ پیش‌فرض پنهانی و هیچ میانگینِ ازپیش‌پرشده‌ای به‌جای تو نیست. اگر مطمئن نیستی، یک جواب تقریبیِ صادقانه بهتر از یک عدد دقیقِ ساختگی است، چون عدد ساختگی به همان اندازه‌ی عدد واقعی امتیاز را جابه‌جا می‌کند.",
      ar: "ما تضعه هنا هو الشيء الوحيد الذي يراه النموذج عن هذا الأمر — لا قيمة افتراضية مخفية ولا متوسّط مملوء سلفاً ينوب عنك. وإن لم تكن متأكداً، فجواب تقريبي صادق أفضل من رقم دقيق مُختلَق، لأن الرقم المختلَق يُحرّك الدرجة بالقوة نفسها التي يحرّكها الرقم الحقيقي.",
      zh: "你在这里填的，是模型关于这件事唯一会看到的东西——没有隐藏的默认值，也没有一个填好的平均数替你顶上。如果你不确定，一个诚实的粗略答案好过一个精确的编造答案，因为编造的数字对分数的推动力和真实数字一样大。",
    },

    ctl_export: {
      face: 'good',
      priority: 36,
      en: "This takes your own data out of the app in a form you can open elsewhere. It is a copy, not a move - nothing is deleted here by exporting, and the file is generated in the language the app is currently showing.",
      fa: "این داده‌های خودت را در قالبی که جای دیگری بتوانی بازش کنی از برنامه بیرون می‌برد. یک رونوشت است، نه جابه‌جایی — با گرفتن خروجی هیچ‌چیز اینجا حذف نمی‌شود، و فایل به همان زبانی ساخته می‌شود که برنامه الان نشان می‌دهد.",
      ar: "هذا يُخرج بياناتك أنت من التطبيق بصيغة يمكنك فتحها في مكان آخر. إنها نسخة لا نقل — لا يُحذف شيء هنا بالتصدير، ويُنشأ الملف باللغة التي يعرضها التطبيق حالياً.",
      zh: "这会把你自己的数据以你能在别处打开的格式导出应用。这是复制，不是搬走——导出不会删掉这里的任何东西，而且文件会按应用当前显示的语言生成。",
    },

    ctl_dismiss: {
      face: 'neutral',
      priority: 26,
      en: "Closing this puts it away without changing anything underneath it. Nothing was saved by opening it and nothing is undone by shutting it.",
      fa: "بستن این، کنارش می‌گذارد بی‌آنکه چیزی را زیرش عوض کند. با بازکردنش چیزی ذخیره نشده و با بستنش چیزی برگردانده نمی‌شود.",
      ar: "إغلاق هذا يُنحّيه جانباً دون تغيير أي شيء تحته. لم يُحفظ شيء بفتحه ولا يُلغى شيء بإغلاقه.",
      zh: "关掉它只是把它收起来，不会改变它底下的任何东西。打开它没有保存什么，关上它也不会撤销什么。",
    },

    csv_save: {
      face: 'good',
      priority: 52,
      en: "Save the answers you just gave under a name you pick. Two things happen at once: the CSV downloads to your machine, and it joins the list on the check-in screen. Next time you want to run this same day again - or the same day with one thing changed - you load it from there instead of retyping forty fields. The downloaded file is the copy that lasts; the list is a shortcut to it.",
      fa: "پاسخ‌هایی که همین حالا دادی را با نامی که خودت انتخاب می‌کنی ذخیره کن. دو چیز هم‌زمان اتفاق می‌افتد: فایل CSV روی دستگاهت دانلود می‌شود، و همان مورد به فهرست صفحه‌ی بررسی اضافه می‌شود. دفعه‌ی بعد که خواستی همین روز را دوباره اجرا کنی — یا همین روز با یک تغییر کوچک — از آنجا بارگذاری‌اش می‌کنی به‌جای اینکه چهل فیلد را دوباره تایپ کنی. فایل دانلودشده نسخه‌ی ماندگار است؛ فهرست فقط میان‌بری به آن است.",
      ar: "احفظ الإجابات التي قدّمتها للتو باسم تختاره أنت. يحدث أمران معاً: يُنزَّل ملف CSV على جهازك، ويُضاف إلى القائمة في شاشة التسجيل. في المرة القادمة التي تريد فيها إعادة تشغيل اليوم نفسه — أو اليوم نفسه مع تغيير واحد — تحمّله من هناك بدل إعادة كتابة أربعين حقلاً. الملف المنزَّل هو النسخة الباقية؛ والقائمة مجرد اختصار إليه.",
      zh: "把你刚填的答案，用你自己起的名字保存下来。两件事同时发生：CSV 文件下载到你的电脑，同时它也会出现在记录页面的列表里。下次你想再跑一遍同样的一天——或者只改一处的同一天——就从那里载入，而不用重新输入四十个字段。下载的文件才是长久的那份；列表只是通往它的快捷方式。",
    },

    csv_history: {
      face: 'good',
      priority: 51,
      en: "Everything you have saved, on two shelves. Real check-ins are the ones that were recorded to your history; test check-ins are the ones you ticked 'don't count this' before running - hypotheticals you were trying out. Which shelf something lands on is not a second decision: it is read from that same tick, so the two can never disagree. Click any entry and the whole form fills with those answers; you look it over and carry on.",
      fa: "هرچه ذخیره کرده‌ای، در دو بخش. «بررسی‌های اصلی» آن‌هایی‌اند که در تاریخچه‌ات ثبت شدند؛ «بررسی‌های تستی» آن‌هایی که قبل از اجرا تیک «این را حساب نکن» را زده بودی — فرض‌هایی که داشتی امتحان می‌کردی. اینکه هر کدام در کدام بخش می‌نشیند تصمیم دوم نیست: از روی همان تیک خوانده می‌شود، پس این دو هرگز نمی‌توانند با هم اختلاف داشته باشند. روی هر مورد کلیک کنی، کل فرم با همان پاسخ‌ها پر می‌شود؛ یک نگاه می‌اندازی و ادامه می‌دهی.",
      ar: "كل ما حفظته، على رفّين. «التسجيلات الحقيقية» هي التي سُجّلت في سجلك؛ و«التسجيلات التجريبية» هي التي أشّرت فيها على «لا تحتسب هذا» قبل التشغيل — فرضيات كنت تجرّبها. الرفّ الذي يقع فيه كل عنصر ليس قراراً ثانياً: يُقرأ من التأشير نفسه، فلا يمكن أن يختلفا. انقر أي عنصر فيمتلئ النموذج كله بتلك الإجابات؛ تراجعه ثم تتابع.",
      zh: "你保存过的一切，分成两栏。「真实记录」是那些已经写进你历史的；「测试记录」是你在运行前勾了「不要计入」的——你当时在试的假设。某一条落在哪一栏不是第二次选择：它直接读自那个勾选，所以两者永远不会矛盾。点任意一条，整张表就会用那份答案填好；你看一眼，然后继续。",
    },

    ctl_legal: {
      face: 'thinking',
      priority: 42,
      en: "Worth reading once, and short on purpose: what this app stores, what it never claims, and the line it will not cross. The important sentence is that nothing here is a medical or diagnostic statement about you, whatever the words on a chart happen to look like.",
      fa: "ارزش دارد یک بار خوانده شود، و عمداً کوتاه است: این برنامه چه چیزی را ذخیره می‌کند، چه چیزی را هرگز ادعا نمی‌کند، و خطی که از آن رد نمی‌شود. جمله‌ی مهمش این است که هیچ‌چیز اینجا یک گزاره‌ی پزشکی یا تشخیصی درباره‌ی تو نیست، کلمه‌های روی یک نمودار هر شکلی که داشته باشند.",
      ar: "يستحق قراءة واحدة، وهو قصير عن قصد: ما يخزّنه هذا التطبيق، وما لا يدّعيه أبداً، والخط الذي لن يتجاوزه. الجملة المهمة أن لا شيء هنا تصريح طبي أو تشخيصي عنك، مهما بدت الكلمات على رسم بياني.",
      zh: "值得读一次，而且是有意写短的：这个应用存了什么、它从不宣称什么，以及它不会越过的那条线。最重要的一句是：这里没有任何东西是关于你的医学或诊断结论，无论图表上的词看起来像什么。",
    },
  });
})();
