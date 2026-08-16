/*
  First-run intro slideshow. Shown once automatically (localStorage
  flag), replayable any time from Settings. Auto-advances every 6s,
  fully skippable at any point (click, Esc, or the Skip button), and
  never blocks the app underneath - closing it always leaves the user
  exactly where they were.

  Every slide's icon is the exact SVG used in that page's own nav link
  (see app-nav-row across the HTML pages) - so the tour visually
  rehearses the real icon the user will click next, instead of an
  unrelated emoji.
*/
(function () {
  const SEEN_KEY = 'dwai_intro_seen';
  const AUTOADVANCE_MS = 6500;

  const ICONS = {
    welcome: '<path d="M12 2.5l2.1 5.9 6.1.6-4.7 4 1.5 6-5-3.5-5 3.5 1.5-6-4.7-4 6.1-.6L12 2.5Z"/>',
    dashboard: '<path d="M4 11 12 4l8 7"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/>',
    checkin: '<rect x="5" y="3.5" width="14" height="17" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    coach: '<path d="M12 4a7 7 0 0 0-7 7c0 2 .8 3.7 2 5l-1 4 4.3-1.4A7 7 0 1 0 12 4Z"/><circle cx="9.2" cy="11" r="1" fill="currentColor"/><circle cx="12" cy="11" r="1" fill="currentColor"/><circle cx="14.8" cy="11" r="1" fill="currentColor"/>',
    weekly: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 9.5h16M8 3v4M16 3v4"/><path d="M8.5 13.5h2M13.5 13.5h2M8.5 17h2"/>',
    analytics: '<path d="M4 20V4"/><path d="M4 20h16"/><rect x="7" y="12" width="3" height="8"/><rect x="12" y="8" width="3" height="12"/><rect x="17" y="14" width="3" height="6"/>',
    whatif: '<path d="M10 3h4"/><path d="M10.5 3v5.2L6 17a2 2 0 0 0 1.8 3h8.4A2 2 0 0 0 18 17l-4.5-8.8V3"/><path d="M8.5 14h7"/>',
    model: '<path d="M12 2 4 5.5v5c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10v-5L12 2Z"/><path d="m9.2 12 1.9 1.9 3.7-3.9"/>',
    profile: '<circle cx="12" cy="8.3" r="3.3"/><path d="M5.5 20c1.2-3.6 3.9-5.5 6.5-5.5s5.3 1.9 6.5 5.5"/>',
    settings: '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 13.5a7.6 7.6 0 0 0 0-3l2-1.5-2-3.4-2.3.9a7.7 7.7 0 0 0-2.6-1.5L14 2h-4l-.5 2.4a7.7 7.7 0 0 0-2.6 1.5l-2.3-.9-2 3.4 2 1.5a7.6 7.6 0 0 0 0 3l-2 1.6 2 3.4 2.3-1a7.7 7.7 0 0 0 2.6 1.5L10 22h4l.5-2.4a7.7 7.7 0 0 0 2.6-1.5l2.3 1 2-3.4-2-1.6Z"/>',
    league: '<path d="M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M16.5 11.2a2.6 2.6 0 1 0 0-5.2"/><path d="M2 19.5c.7-3.4 2.9-5.3 6-5.3s5.3 1.9 6 5.3"/><path d="M15 14.6c2.3.4 3.9 2.1 4.5 4.9"/>',
    privacy: '<rect x="5" y="10.5" width="14" height="9" rx="2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/><circle cx="12" cy="15" r="1.3" fill="currentColor"/>',
    about: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.3"/><circle cx="12" cy="8.1" r="0.15" fill="currentColor" stroke-width="1.6"/>',
    ready: '<path d="M12 2.5c2.6 1.8 4.3 5.4 4.3 8.8 0 1.9-.6 3.6-1.4 4.9l-.9-2.7-2 2.3-2-2.3-.9 2.7c-.8-1.3-1.4-3-1.4-4.9 0-3.4 1.7-7 4.3-8.8Z"/><circle cx="12" cy="10" r="1.3" fill="currentColor"/><path d="M9.3 16.5 7 20M14.7 16.5 17 20"/>',
  };

  function slidesFor(lang) {
    const pick = (t) => t[lang] || t.en;
    const S = (icon, t) => ({ icon, title: pick(t.title), body: pick(t.body) });
    return [
      S(ICONS.welcome, {
        title: {
          en: 'Welcome to Digital Wellness AI', fa: 'به Digital Wellness AI خوش آمدی',
          ar: 'مرحباً بك في Digital Wellness AI', zh: '欢迎使用 Digital Wellness AI',
        },
        body: {
          en: "No horoscopes, no fabricated averages. A real, trained machine-learning model turns your own daily habits into every number you'll see here. Let's walk through every corner of the app in the next 60 seconds.",
          fa: 'اینجا فال یا میانگین ساختگی خبری نیست. یک مدل یادگیری ماشین واقعی، آموزش‌دیده روی عادت‌های روزانه، هر عددی که می‌بینی را مستقیم از داده‌ی خودت می‌سازد. بیا در ۶۰ ثانیه همه‌ی بخش‌ها را با هم ببینیم.',
          ar: 'لا أبراج، ولا متوسطات مُختلَقة. نموذج تعلّم آلي حقيقي ومدرَّب على العادات اليومية يحوّل عاداتك أنت إلى كل رقم تراه هنا. لنتجوّل معاً في كل زاوية من التطبيق خلال الستين ثانية القادمة.',
          zh: '没有星座运势，没有虚构的平均值。一个基于日常习惯训练的真实机器学习模型，把你自己的数据变成你在这里看到的每一个数字。接下来六十秒，一起走一遍应用的每个角落。',
        },
      }),
      S(ICONS.dashboard, {
        title: {
          en: 'Dashboard: your life, at a glance', fa: 'داشبورد: عکس لحظه‌ای زندگی‌ات',
          ar: 'لوحة التحكم: حياتك في لمحة', zh: '仪表盘：一眼看清你的生活',
        },
        body: {
          en: "The moment you land, your latest score, your recent trend, and the fastest path to your next check-in are all right there — zero extra clicks.",
          fa: 'همین که وارد می‌شوی، آخرین امتیاز، روند اخیر و سریع‌ترین راه به بررسی بعدی را یکجا می‌بینی — بدون کلیک اضافه.',
          ar: 'من اللحظة التي تصل فيها، تجد أحدث درجاتك واتجاهك الأخير وأسرع طريق إلى تسجيلك التالي في مكان واحد — بلا أي نقرة إضافية.',
          zh: '你一进来，最新分数、近期趋势，以及去下一次记录最快的路径，全都在那里——不用多点一次。',
        },
      }),
      S(ICONS.checkin, {
        title: {
          en: 'Check-in & the score ring', fa: 'چک‌این و دایره‌ی امتیاز',
          ar: 'التسجيل وحلقة الدرجة', zh: '打卡与分数环',
        },
        body: {
          en: "A short daily check-in, and you get a real prediction back instantly. The ring's glowing center is your real regression-model score; the four arcs around it are a transparent breakdown of your digital-wellness dimensions. If a check-in shouldn't count toward your weekly analysis, there's a checkbox for exactly that right above the questionnaire.",
          fa: 'یک بررسی روزانه‌ی کوتاه پر می‌کنی و بلافاصله یک پیش‌بینی واقعی می‌گیری. دایره‌ی رنگی مرکزش امتیاز واقعی مدل رگرسیون است؛ ۴ کمانِ درخشانِ دورش تفکیک شفاف ابعاد سلامت دیجیتال توست. اگر یک بررسی نمی‌خواهی در تحلیل هفتگی‌ات حساب شود، همان بالای پرسشنامه یک تیک برای همین کار هست.',
          ar: 'تملأ تسجيلاً يومياً قصيراً وتحصل على تنبؤ حقيقي فوراً. مركز الحلقة المتوهج هو درجتك الحقيقية من نموذج الانحدار؛ والأقواس الأربعة حولها تفصيل شفاف لأبعاد عافيتك الرقمية. وإن كان تسجيل ما لا ينبغي أن يُحتسب في تحليلك الأسبوعي، فهناك مربع اختيار لذلك بالضبط أعلى الاستبيان مباشرة.',
          zh: '填写一份简短的每日打卡，立刻得到一个真实的预测。圆环发光的中心是回归模型给出的真实分数；周围的四段弧线，是你数字健康各维度的透明拆解。如果某次打卡不该计入你的每周分析，问卷正上方就有一个专门的勾选框。',
        },
      }),
      S(ICONS.coach, {
        title: { en: 'Your AI Coach', fa: 'مربی هوش مصنوعی', ar: 'مربيك الذكي', zh: '你的 AI 教练' },
        /* The "200" here is a claim about the real assembled menu
           (ai-menu.js ITEMS plus every generated family), and it is
           checked against that real number by
           tests/test_intro_slide_claims.py - a rounded-down floor
           rather than the exact count, so adding menu items can never
           turn this sentence into a lie. It said 140 while the menu
           had already grown past 200. */
        body: {
          en: "More than 200 ready-made questions, each answered from your own real, current data — plus a free-text chat. Honestly: it's a smart rule-based engine, not an external language model — which is exactly why every answer traces back to your own numbers.",
          fa: 'بیش از ۲۰۰ سوال آماده داری که هرکدام از داده‌ی واقعی و فعلی‌ات پاسخ می‌گیرند، به‌علاوه یک چت آزاد. صادقانه: این یک موتور قانون‌محورِ هوشمند است، نه یک مدل زبانی بیرونی — و دقیقاً برای همین هر جواب قابل ردیابی به داده‌ی خودت است.',
          ar: 'أكثر من 200 سؤال جاهز، تُجاب جميعها من بياناتك الحقيقية والحالية — بالإضافة إلى محادثة نصية حرة. بصراحة: هذا محرك ذكي قائم على قواعد، لا نموذج لغوي خارجي — ولهذا بالضبط يمكن تتبّع كل إجابة إلى أرقامك أنت.',
          zh: '两百多个现成问题，每一个都用你真实的当前数据来回答——此外还有自由文本聊天。说实话：这是一个聪明的规则引擎，不是外部语言模型——这正是为什么每个回答都能追溯到你自己的数字。',
        },
      }),
      S(ICONS.weekly, {
        title: {
          en: 'Weekly plan & shareable card', fa: 'برنامه‌ی هفتگی و کارت هفته',
          ar: 'الخطة الأسبوعية والبطاقة القابلة للمشاركة', zh: '每周计划与可分享卡片',
        },
        body: {
          en: "A 7-day plan, built just for you, from your last check-in's weakest signals — gradually targeting exactly those points. At the end, download a shareable image card built from your real week, not a generic template.",
          fa: 'یک برنامه‌ی ۷ روزه، مخصوص خودت، از ضعیف‌ترین سیگنال‌های آخرین بررسی‌ات ساخته می‌شود و کم‌کم همان نقطه‌ها را هدف می‌گیرد. در پایان هم یک کارت تصویری قابل‌دانلود از هفته‌ی واقعی‌ات می‌سازی — نه یک قالب عمومی.',
          ar: 'خطة سبعة أيام، مبنية خصيصاً لك، من أضعف إشارات تسجيلك الأخير — تستهدف تلك النقاط تدريجياً. وفي النهاية، حمّل بطاقة صورة قابلة للمشاركة مبنية من أسبوعك الحقيقي، لا من قالب عام.',
          zh: '一份为你量身定制的七天计划，来自你上次打卡中最弱的信号——逐步针对这些具体的点。最后，下载一张基于你真实一周制作的可分享图片卡片，而不是通用模板。',
        },
      }),
      S(ICONS.analytics, {
        title: {
          en: 'Analytics: watch your trends clearly', fa: 'آنالیتیکس: روندها را واضح ببین',
          ar: 'التحليلات: راقب اتجاهاتك بوضوح', zh: '分析：清楚地看见你的趋势',
        },
        body: {
          en: "Interactive charts built from your real history — score, dimensions, weekly wins — surfacing patterns a single number could never show.",
          fa: 'نمودارهای تعاملی از تاریخچه‌ی واقعی‌ات — امتیاز، ابعاد، و بردهای هفتگی — تا الگوهایی را ببینی که در یک عدد تنها هرگز دیده نمی‌شوند.',
          ar: 'رسوم بيانية تفاعلية مبنية من سجلك الحقيقي — الدرجة، الأبعاد، وانتصارات الأسبوع — تكشف أنماطاً لن يظهرها رقم واحد أبداً.',
          zh: '基于你真实历史构建的交互式图表——分数、维度、每周的小胜利——揭示出单个数字永远显示不出来的模式。',
        },
      }),
      S(ICONS.whatif, {
        title: {
          en: 'The "What-if" simulator', fa: 'حالت شبیه‌سازی «اگر...؟»',
          ar: 'محاكي "ماذا لو؟"', zh: '「假如……」模拟器',
        },
        body: {
          en: "Nudge your habits hypothetically and watch the model's predicted score update instantly — nothing here ever touches your real recorded history.",
          fa: 'عادت‌هایت را فرضی جابه‌جا کن و همان لحظه ببین مدل چه امتیازی پیش‌بینی می‌کند — بدون اینکه چیزی در تاریخچه‌ی واقعی‌ات ثبت شود.',
          ar: 'حرّك عاداتك افتراضياً وشاهد الدرجة التي يتنبأ بها النموذج تتحدث فورياً — لا شيء هنا يمسّ سجلك الحقيقي المسجَّل أبداً.',
          zh: '假设性地调整你的习惯，立刻看到模型预测的分数随之变化——这里的一切都不会碰到你真实记录的历史。',
        },
      }),
      S(ICONS.model, {
        title: { en: 'Model transparency', fa: 'شفافیت مدل', ar: 'شفافية النموذج', zh: '模型透明度' },
        body: {
          en: "This is where the real model accuracy lives — both the classification model and the regression model — along with why they were chosen. Nothing stays hidden behind the curtain.",
          fa: 'همین‌جا دقت واقعی مدل‌ها را می‌بینی — هم مدل دسته‌بندی و هم مدل رگرسیون — و اینکه چرا این مدل‌ها انتخاب شدند. هیچ عددی پشت پرده قایم نمی‌شود.',
          ar: 'هنا تجد الدقة الحقيقية للنماذج — نموذج التصنيف ونموذج الانحدار كلاهما — إلى جانب سبب اختيارهما. لا شيء يبقى مخفياً خلف الستار.',
          zh: '这里是真实模型精度的所在——分类模型和回归模型都有——以及它们为什么被选中。没有任何数字藏在幕后。',
        },
      }),
      S(ICONS.profile, {
        title: {
          en: 'Profile, persona & badges', fa: 'پروفایل، پرسونا و نشان‌ها',
          ar: 'الملف الشخصي والشخصية والأوسمة', zh: '个人资料、人格画像与徽章',
        },
        body: {
          en: "A digital-wellness persona built from your real behavior, a customizable avatar, and badges that unlock with real progress — never by luck.",
          fa: 'یک پرسونای سلامت دیجیتال بر اساس رفتار واقعی‌ات، آواتار قابل‌شخصی‌سازی، و نشان‌هایی که با پیشرفت واقعی باز می‌شوند — نه با شانس.',
          ar: 'شخصية عافية رقمية مبنية من سلوكك الحقيقي، وصورة رمزية قابلة للتخصيص، وأوسمة تُفتح بتقدّم حقيقي — لا بالحظ أبداً.',
          zh: '一个基于你真实行为构建的数字健康人格画像、一个可自定义的头像，以及只靠真实进步才能解锁的徽章——绝不靠运气。',
        },
      }),
      S(ICONS.settings, {
        title: {
          en: 'Settings, entirely in your hands', fa: 'تنظیمات، دقیقاً دست خودت',
          ar: 'الإعدادات، بين يديك تماماً', zh: '设置，完全由你掌控',
        },
        body: {
          en: "Theme, ambient sound (now real music tracks, not synthesized tones!), sound effects and reduced motion — all fully independent switches. Demo Mode lives here too: one click fills the whole app with a realistic 23-day sample so you can see everything populated.",
          fa: 'تم، صدای محیطی (حالا با موسیقی واقعی، نه سنتز شده!)، جلوه‌های صوتی و کاهش حرکت، همه کلیدهای کاملاً مستقل‌اند. «حالت دمو» هم همین‌جاست — با یک کلیک کل اپ را با یک نمونه‌ی واقع‌گرایانه‌ی ۲۳ روزه پر می‌کند تا همه‌چیز را پر ببینی.',
          ar: 'المظهر، الصوت المحيطي (الآن مقاطع موسيقية حقيقية، لا نغمات مُصنَّعة!)، المؤثرات الصوتية، وتقليل الحركة — كلها مفاتيح مستقلة تماماً. ووضع العرض التجريبي موجود هنا أيضاً — بنقرة واحدة يملأ التطبيق كله بعيّنة واقعية من 23 يوماً لتراه ممتلئاً بالكامل.',
          zh: '主题、环境音效（现在是真实的音乐曲目，不是合成音效！）、音效和减少动效——全都是完全独立的开关。演示模式也在这里：一次点击就用一份真实感十足的 23 天样本数据填满整个应用，让你看到所有内容都被填充的样子。',
        },
      }),
      S(ICONS.league, {
        title: { en: 'Friends League', fa: 'لیگ دوستان', ar: 'دوري الأصدقاء', zh: '好友联赛' },
        body: {
          en: "The main comparison is always about your own past and where your own trajectory is heading — never just a cold leaderboard. A friend only sees anything after they've entered your invite code AND you've approved the request, and only for the exact categories you've ticked. Change or revoke it any time.",
          fa: 'مقایسه‌ی اصلی همیشه با گذشته و مسیر آینده‌ی خودت است، نه یک جدول خشک. یک دوست فقط بعد از اینکه صریحاً کد دعوتت را وارد کرد و تو تاییدش کردی، و فقط برای دسته‌هایی که خودت تیک زده‌ای، چیزی می‌بیند — و هر لحظه می‌توانی این را تغییر بدهی یا کاملاً قطع کنی.',
          ar: 'المقارنة الأساسية دائماً مع ماضيك أنت واتجاه مسارك أنت — لا مجرد جدول ترتيب بارد. لا يرى الصديق شيئاً إلا بعد أن يُدخل كود دعوتك أنت وتوافق أنت على الطلب، وفقط للفئات التي حدّدتها بنفسك بالضبط. غيّر ذلك أو ألغه في أي وقت.',
          zh: '主要的比较对象永远是你自己的过去和你自己的发展方向——绝不只是一份冷冰冰的排行榜。好友只有在输入了你的邀请码、并且你批准了请求之后，才能看到任何东西，而且只能看到你勾选过的那些类别。你可以随时更改或撤销。',
        },
      }),
      S(ICONS.about, {
        title: { en: 'About this project', fa: 'درباره‌ی پروژه', ar: 'حول هذا المشروع', zh: '关于这个项目' },
        body: {
          en: "The story, the architecture, and exactly what these models were trained on — all laid out plainly, with no overstated claims.",
          fa: 'داستان، معماری، و اینکه این مدل‌ها دقیقاً روی چه چیزی آموزش دیده‌اند — همه‌چیز شفاف و بدون ادعای اضافه.',
          ar: 'القصة، والبنية، وما دُرِّبت عليه هذه النماذج بالضبط — كل ذلك موضح بوضوح، دون أي ادعاءات مبالغ فيها.',
          zh: '项目的故事、架构，以及这些模型究竟是在什么数据上训练的——一切都清楚列出，没有任何夸大的说法。',
        },
      }),
      S(ICONS.privacy, {
        title: {
          en: 'Privacy, always in your control', fa: 'حریم خصوصی، همیشه دست خودت',
          ar: 'الخصوصية، دائماً تحت سيطرتك', zh: '隐私，始终由你掌控',
        },
        body: {
          en: "Any time, from your Profile, export everything this app has ever stored about you — or permanently and irreversibly delete your account and full history.",
          fa: 'هر وقت خواستی، از پروفایل خودت می‌توانی همه‌چیزی که این اپ درباره‌ات ذخیره کرده را خروجی بگیری، یا حساب و کل تاریخچه‌ات را برای همیشه و بدون بازگشت حذف کنی.',
          ar: 'في أي وقت، من ملفك الشخصي، صدّر كل ما خزّنه هذا التطبيق عنك على الإطلاق — أو احذف حسابك وسجلك الكامل نهائياً وبلا رجعة.',
          zh: '随时可以从你的个人资料页，导出这个应用曾经存储过的关于你的一切——或者永久且不可撤销地删除你的账户和完整历史。',
        },
      }),
    ];
  }

  function finalSlide(lang) {
    const pick = (t) => t[lang] || t.en;
    return {
      icon: ICONS.ready,
      title: pick({
        en: "Now it's your turn",
        fa: 'حالا نوبت توست',
        ar: 'حان دورك الآن',
        zh: '现在轮到你了',
      }),
      body: pick({
        en: "Run your first real check-in right now and see what the model actually says about you — or if you'd rather see everything populated first, give Demo Mode a spin.",
        fa: 'همین حالا اولین بررسی‌ی واقعی‌ات را بزن و ببین مدل درباره‌ات چه می‌گوید — یا اگر فقط می‌خواهی همه‌چیز را پر و آماده ببینی، حالت دمو را امتحان کن.',
        ar: 'ابدأ الآن بأول تقييم حقيقي لك وشاهد ماذا يقول النموذج فعلاً عنك — أو إذا كنت تفضّل رؤية كل شيء مكتملاً أولاً، جرّب وضع العرض التجريبي.',
        zh: '现在就开始你的第一次真实检查，看看模型究竟怎么评价你——或者如果你想先看到所有内容都填充好，试试演示模式。',
      }),
      final: true,
    };
  }

  let overlay = null, idx = 0, timer = null, list = [];

  function clearTimer() { if (timer) clearInterval(timer); timer = null; }

  function paint() {
    if (!overlay) return;
    const s = list[idx];
    overlay.querySelector('#introIcon').innerHTML =
      `<svg viewBox="0 0 24 24" aria-hidden="true">${s.icon}</svg>`;
    overlay.querySelector('#introTitle').textContent = s.title;
    overlay.querySelector('#introBody').textContent = s.body;
    overlay.querySelector('#introDots').innerHTML = list.map((_, i) =>
      `<span class="intro-dot${i === idx ? ' active' : ''}"></span>`).join('');
    const ctaRow = overlay.querySelector('#introCtaRow');
    const navRow = overlay.querySelector('#introNavRow');
    if (s.final) {
      ctaRow.classList.remove('hidden');
      navRow.classList.add('hidden');
    } else {
      ctaRow.classList.add('hidden');
      navRow.classList.remove('hidden');
    }
  }

  function goTo(i) {
    idx = Math.max(0, Math.min(list.length - 1, i));
    paint();
    restartTimer();
  }

  function restartTimer() {
    clearTimer();
    if (idx >= list.length - 1) return;
    timer = setInterval(() => {
      if (idx < list.length - 1) goTo(idx + 1); else clearTimer();
    }, AUTOADVANCE_MS);
  }

  function close() {
    clearTimer();
    if (overlay) { overlay.remove(); overlay = null; }
    document.body.style.overflow = '';
    try { localStorage.setItem(SEEN_KEY, '1'); } catch (e) {}
  }

  function build() {
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const pick = (table) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(table) : table.en);
    const NAV = {
      skip: { en: 'Skip', fa: 'رد کردن', ar: 'تخطٍّ', zh: '跳过' },
      back: { en: 'Back', fa: 'قبلی', ar: 'السابق', zh: '上一步' },
      next: { en: 'Next', fa: 'بعدی', ar: 'التالي', zh: '下一步' },
      start: { en: 'Run a check-in', fa: 'شروع بررسی', ar: 'ابدأ تسجيلاً', zh: '开始一次记录' },
      demo: { en: 'See a demo', fa: 'دیدن دمو', ar: 'شاهد عرضاً تجريبياً', zh: '查看演示' },
    };
    list = slidesFor(lang).concat([finalSlide(lang)]);
    const el = document.createElement('div');
    el.className = 'intro-overlay';
    el.innerHTML = `
      <div class="intro-box">
        <button type="button" class="intro-skip" id="introSkip">${pick(NAV.skip)} ✕</button>
        <div class="intro-icon" id="introIcon"></div>
        <h2 class="intro-title" id="introTitle"></h2>
        <p class="intro-body" id="introBody"></p>
        <div class="intro-dots" id="introDots"></div>
        <div class="intro-nav-row" id="introNavRow">
          <button type="button" class="btn btn-ghost btn-sm" id="introPrev">${pick(NAV.back)}</button>
          <button type="button" class="btn btn-primary btn-sm" id="introNext">${pick(NAV.next)}</button>
        </div>
        <div class="intro-cta-row hidden" id="introCtaRow">
          <a class="btn btn-primary btn-shine" href="app.html">${pick(NAV.start)}</a>
          <button type="button" class="btn btn-ghost" id="introDemoBtn">${pick(NAV.demo)}</button>
        </div>
      </div>`;
    document.body.appendChild(el);
    overlay = el;

    el.querySelector('#introSkip').addEventListener('click', close);
    el.querySelector('#introPrev').addEventListener('click', () => goTo(idx - 1));
    el.querySelector('#introNext').addEventListener('click', () => goTo(idx + 1));
    el.querySelector('#introDemoBtn').addEventListener('click', () => {
      close();
      if (window.DWDemo) window.DWDemo.run();
    });
    el.addEventListener('click', (e) => { if (e.target === el) close(); });
    document.addEventListener('keydown', function onKey(e) {
      if (!overlay) { document.removeEventListener('keydown', onKey); return; }
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowRight') goTo(idx + 1);
      if (e.key === 'ArrowLeft') goTo(idx - 1);
    });
    document.body.style.overflow = 'hidden';
  }

  function show(opts) {
    opts = opts || {};
    if (!opts.force) {
      let seen = null;
      try { seen = localStorage.getItem(SEEN_KEY); } catch (e) {}
      if (seen === '1') return;
    }
    if (overlay) return;
    idx = 0;
    build();
    paint();
    restartTimer();
  }

  window.DWIntro = { show, close };
})();
