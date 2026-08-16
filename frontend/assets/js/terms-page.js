/*
  Terms & Privacy, in four languages, with no dependencies.

  Why the content lives here rather than in i18n.js: this page has to be
  readable when nothing else works - before sign-in, with the API down,
  opened straight from disk. Every other page can afford to depend on
  the app's script stack; the page that states the app's limits cannot.

  What it covers is the app as it actually shipped, not a generic
  template: the two models and their two horizons, the friends league
  and its per-category consent, private messaging with blocking and
  reporting, the badge system including the private awareness
  indicators, the games, the guide's voice, the optional AI-coach key,
  demo mode, exports and deletion. A rule for a feature nobody has is
  noise; a feature with no rule is the actual problem.
*/
(function () {
  const KEY = 'dwai_lang';                 // the app's own key
  const RTL = ['fa', 'ar'];
  const LANGS = ['en', 'fa', 'ar', 'zh'];

  const T = {
    en: {
      back: 'Back to app',
      title: 'Terms & Privacy Notice',
      updated: 'Last updated: August 2026',
      lede: 'Digital Wellness AI is a research and demonstration project. It is not a medical device, not a clinical tool, and not a certified product. Please read this before you create an account — it describes exactly what the app does with what you tell it, and the things it will never claim.',
      calloutTitle: 'The rule that outranks every other rule here',
      callout: 'Nothing this app produces is a medical or psychological diagnosis, screening result, or treatment recommendation. Words like "risk", "stress", "anxiety" or "low mood" appear because you rated them yourself — they are your own descriptions of your own day, not clinical findings. If you are in distress or in crisis, contact a qualified professional or your local emergency service. This app is not equipped for that and will never tell you otherwise.',

      h_use: '1. Using the app',
      use: [
        'The app gives you an automated, statistical estimate of digital-wellness habits, computed only from the information you enter yourself.',
        'You must be old enough in your jurisdiction to agree to these terms and create an account, or have a guardian\'s permission.',
        'You are responsible for what you enter. Deliberately false entries produce a confident-looking score that describes nobody, and the app cannot detect that.',
        'The app is provided as-is, with no warranty, for personal and educational use. Do not rely on it for any decision that matters medically, legally, or professionally.',
        'Do not use the app to harass anyone, to impersonate anyone, or to attempt to extract another person\'s data.',
      ],

      h_models: '2. What the predictions are — and are not',
      models: [
        'Two separate trained models are used, and they answer two different questions. One estimates a score for the day you just logged. The other estimates which band you are likely to be in seven days from now. They are not the same number and the app labels them separately.',
        'Every accuracy figure shown on the model page is measured on held-out data and is stated openly, including where a model performed worse than a trivial baseline.',
        'The training data is synthetic. It was generated for this project, it does not describe real people, and no real person\'s records were used to build the models.',
        'A seven-day figure is an estimate about a pattern, never a promise about you. It cannot account for anything you have not logged — illness, travel, a change of job, or anything else life does.',
        'If the app cannot honestly produce a number, it says so instead of producing one. An empty or absent value is a deliberate answer, not a failure.',
      ],

      h_data: '3. Your data',
      data: [
        'What you enter — age bracket, screen-time habits, sleep, mood and focus ratings, and the goals you pick — is used only to compute your own score, explanations, history and recommendations.',
        'Your data is stored locally by the copy of the app you are running. Running it on your own machine means it does not leave your machine.',
        'Nothing is sold, and nothing is shared with any third party or advertiser.',
        'You can export everything the app holds about you at any time, as JSON or as a spreadsheet file, from the privacy section.',
        'You can delete your account and its data at any time from the same place. Deletion removes your entries, your history and your badges.',
        'Days you mark as "do not record" are excluded from your trends and averages. They stay excluded until you say otherwise.',
      ],

      h_league: '4. Friends League and sharing',
      league: [
        'The league is off until you turn it on. No connection is ever made automatically, and no one can add you without your explicit acceptance.',
        'Sharing is per-category and per-friend. You tick exactly what a specific person may see, and everything you do not tick stays private.',
        'You can change what a friend sees, or revoke their access entirely, at any moment. Revoking takes effect in the data itself, not merely in the interface — a revoked friend stops receiving your figures immediately.',
        'The main comparison the league shows you is against your own past. Friends are context and are never the headline.',
        'Private awareness indicators are never shared with anyone under any setting, including badges derived from them. They exist only for you.',
      ],

      h_chat: '5. Messages, blocking and reporting',
      chat: [
        'Direct and group messages are available only between people who are already connected and have both accepted.',
        'Every message is authorised individually when it is read or sent. Losing access to a conversation takes effect immediately, including for conversations already open.',
        'Message rate limits apply, to keep the feature from being used to flood anyone.',
        'You can block any user. Blocking is symmetrical: neither of you can message the other afterwards.',
        'You can report a message. Reports are recorded for review and never trigger an automatic penalty against the person reported.',
        'Do not send abusive, harassing, hateful, or unlawful content, and do not share other people\'s private information. Accounts used that way can be removed.',
      ],

      h_badges: '6. Badges, games and streaks',
      badges: [
        'Badges are awarded from values you actually logged. None are given for spending more time in the app.',
        'Achievement badges recognise consistency and improvement. Awareness indicators are private, are never shown to anyone else, and are descriptions rather than verdicts.',
        'When your history cannot yet answer what a badge asks, the app says there is not enough data — it does not guess and it does not imply you failed.',
        'Games are for understanding your own numbers, not for scoring you. Nothing you do in a game changes your wellness score, your history, or any model input.',
        'Streaks are never used to pressure you. Breaking one carries no penalty, and a missed day is not framed as a failure.',
      ],

      h_guide: '7. The digital guide and sound',
      guide: [
        'The guide explains the app. It never diagnoses you and never comments on your worth.',
        'Its voice uses your own browser\'s built-in speech engine. No audio is sent anywhere, no external service is contacted, and no API key is involved.',
        'Which languages can actually be spoken aloud depends on your browser and device, not on this app.',
        'The guide, its voice, sound effects, ambient music and reduced motion are independent switches. Turning any of them off never changes a score, an input, or a stored record.',
      ],

      h_ai: '8. The optional AI coach key',
      ai: [
        'The coach works entirely offline by default, answering from your own logged data.',
        'You may optionally supply your own API key for an external AI provider. It is off unless you enable it yourself.',
        'If you enable it, your questions are sent to that provider under their terms and privacy policy, not ours. Only enable it if you accept that.',
        'The key is stored in your own browser and is never transmitted to us.',
      ],

      h_demo: '9. Demo mode',
      demo: [
        'Demo mode fills the app with a realistic synthetic history so you can explore without logging real days first.',
        'Demo data is clearly synthetic and never mixes with your real entries.',
        'Nothing generated in demo mode is used to train or adjust any model.',
      ],

      h_liability: '10. Limits of liability',
      liability: [
        'This is a student and portfolio project offered free of charge. To the fullest extent the law allows, the authors accept no liability for any loss or harm arising from its use.',
        'Availability is not guaranteed. The app may change or stop working at any time.',
        'Because you run your own copy, keeping a backup of anything you want to keep is your responsibility. The export feature exists for exactly that.',
      ],

      h_changes: '11. Changes to these terms',
      changes: [
        'These terms may be updated as the app changes. The date at the top reflects the current version.',
        'Continuing to use the app after an update means you accept the updated terms.',
      ],

      h_contact: '12. Contact',
      contactLede: 'For questions, data-deletion requests, bug reports, or anything about this notice, get in touch directly:',
      email: 'Email',
      phone: 'Phone',
      contactNote: 'This is a demonstration project maintained by one person. Please allow a reasonable time for a reply.',
    },

    fa: {
      back: 'بازگشت به برنامه',
      title: 'قوانین و حریم خصوصی',
      updated: 'آخرین به‌روزرسانی: مرداد ۱۴۰۵',
      lede: 'Digital Wellness AI یک پروژه‌ی پژوهشی و نمایشی است. نه دستگاه پزشکی است، نه ابزار بالینی، و نه محصولی دارای گواهی. لطفاً پیش از ساختن حساب این متن را بخوان — دقیقاً می‌گوید برنامه با آنچه به آن می‌دهی چه می‌کند، و چه چیزهایی را هرگز ادعا نمی‌کند.',
      calloutTitle: 'قانونی که بالاتر از همه‌ی قوانین دیگرِ این صفحه است',
      callout: 'هیچ‌چیزی که این برنامه تولید می‌کند، تشخیص پزشکی یا روان‌شناختی، نتیجه‌ی غربالگری، یا توصیه‌ی درمانی نیست. کلمه‌هایی مثل «ریسک»، «استرس»، «اضطراب» یا «افت خلق» از این‌رو دیده می‌شوند که خودت به آن‌ها امتیاز داده‌ای — این‌ها توصیفِ خودت از روزِ خودت هستند، نه یافته‌ی بالینی. اگر در وضعیت دشوار یا بحران هستی، با یک متخصص واجد شرایط یا اورژانس محلی تماس بگیر. این برنامه برای آن ساخته نشده و هیچ‌وقت خلافش را نمی‌گوید.',

      h_use: '۱. استفاده از برنامه',
      use: [
        'برنامه یک تخمین آماری و خودکار از عادت‌های سلامت دیجیتال به تو می‌دهد که فقط از اطلاعاتی محاسبه می‌شود که خودت وارد کرده‌ای.',
        'باید در قوانین محل زندگی‌ات به سنی رسیده باشی که بتوانی این شرایط را بپذیری و حساب بسازی، یا اجازه‌ی سرپرست داشته باشی.',
        'مسئولیت آنچه وارد می‌کنی با خودت است. ورودی عمداً نادرست، امتیازی می‌سازد که ظاهرش مطمئن است ولی هیچ‌کس را توصیف نمی‌کند، و برنامه نمی‌تواند این را تشخیص دهد.',
        'برنامه «همان‌طور که هست» و بدون هیچ ضمانتی، برای استفاده‌ی شخصی و آموزشی ارائه می‌شود. برای هیچ تصمیم پزشکی، حقوقی یا شغلیِ مهم به آن تکیه نکن.',
        'از برنامه برای آزار دیگران، جعل هویت، یا تلاش برای بیرون‌کشیدن داده‌ی شخص دیگر استفاده نکن.',
      ],

      h_models: '۲. پیش‌بینی‌ها چه هستند — و چه نیستند',
      models: [
        'دو مدل آموزش‌دیده‌ی جدا استفاده می‌شوند و به دو پرسش متفاوت جواب می‌دهند. یکی امتیاز همان روزی را که ثبت کرده‌ای تخمین می‌زند. دیگری تخمین می‌زند هفت روز بعد احتمالاً در کدام باند خواهی بود. این دو یک عدد نیستند و برنامه جداگانه برچسبشان می‌زند.',
        'هر عدد دقتی که در صفحه‌ی مدل نشان داده می‌شود روی داده‌ی کنارگذاشته‌شده اندازه‌گیری شده و صادقانه بیان می‌شود، از جمله جایی که یک مدل بدتر از یک مبنای ساده عمل کرده است.',
        'داده‌ی آموزشی مصنوعی است. برای همین پروژه ساخته شده، هیچ انسان واقعی را توصیف نمی‌کند، و برای ساخت مدل‌ها از سوابق هیچ فرد واقعی استفاده نشده است.',
        'عدد هفت‌روزه تخمینی درباره‌ی یک الگوست، نه وعده‌ای درباره‌ی تو. نمی‌تواند چیزی را که ثبت نکرده‌ای به حساب بیاورد — بیماری، سفر، تغییر شغل، یا هر چیز دیگری که زندگی می‌کند.',
        'اگر برنامه نتواند صادقانه عددی تولید کند، به‌جای ساختنش می‌گوید که نمی‌تواند. مقدار خالی یا غایب یک پاسخ عمدی است، نه یک خرابی.',
      ],

      h_data: '۳. داده‌های تو',
      data: [
        'آنچه وارد می‌کنی — بازه‌ی سنی، عادت‌های زمان صفحه، خواب، ارزیابی خلق و تمرکز، و هدف‌هایی که انتخاب می‌کنی — فقط برای محاسبه‌ی امتیاز، توضیح‌ها، تاریخچه و پیشنهادهای خودت استفاده می‌شود.',
        'داده‌ات به‌صورت محلی توسط همان نسخه‌ای که اجرا می‌کنی ذخیره می‌شود. اجرای آن روی دستگاه خودت یعنی از دستگاه خودت بیرون نمی‌رود.',
        'هیچ‌چیز فروخته نمی‌شود و هیچ‌چیز با شخص ثالث یا تبلیغ‌کننده‌ای به اشتراک گذاشته نمی‌شود.',
        'هر لحظه می‌توانی همه‌ی آنچه برنامه درباره‌ات نگه داشته را به‌صورت JSON یا فایل صفحه‌گسترده از بخش حریم خصوصی خروجی بگیری.',
        'هر لحظه می‌توانی از همان‌جا حسابت و داده‌هایش را حذف کنی. حذف، ثبت‌ها، تاریخچه و نشان‌هایت را پاک می‌کند.',
        'روزهایی که علامت «ثبت نشود» می‌زنی از روندها و میانگین‌هایت کنار گذاشته می‌شوند و تا وقتی خودت نگویی همان‌طور می‌مانند.',
      ],

      h_league: '۴. لیگ دوستان و اشتراک‌گذاری',
      league: [
        'لیگ تا وقتی خودت روشنش نکنی خاموش است. هیچ ارتباطی خودکار برقرار نمی‌شود و هیچ‌کس بدون پذیرش صریح تو نمی‌تواند تو را اضافه کند.',
        'اشتراک‌گذاری به‌ازای هر دسته و هر دوست جداست. دقیقاً تیک می‌زنی که یک شخص مشخص چه چیزی را ببیند، و هرچه تیک نزنی خصوصی می‌ماند.',
        'هر لحظه می‌توانی آنچه یک دوست می‌بیند را عوض کنی یا دسترسی‌اش را کامل لغو کنی. لغو در خودِ داده اعمال می‌شود نه فقط در ظاهر — دوستِ لغو‌شده بلافاصله دیگر اعداد تو را دریافت نمی‌کند.',
        'مقایسه‌ی اصلی‌ای که لیگ نشانت می‌دهد با گذشته‌ی خودت است. دوستان زمینه‌اند و هیچ‌وقت تیتر اصلی نیستند.',
        'شاخص‌های آگاهیِ خصوصی تحت هیچ تنظیمی با هیچ‌کس به اشتراک گذاشته نمی‌شوند، از جمله نشان‌هایی که از آن‌ها می‌آیند. این‌ها فقط برای خودت وجود دارند.',
      ],

      h_chat: '۵. پیام‌ها، مسدودسازی و گزارش',
      chat: [
        'پیام خصوصی و گروهی فقط بین کسانی در دسترس است که از قبل متصل شده‌اند و هر دو پذیرفته‌اند.',
        'هر پیام هنگام خواندن یا فرستادن، جداگانه مجوزش بررسی می‌شود. از دست دادن دسترسی به یک گفت‌وگو بلافاصله اعمال می‌شود، حتی برای گفت‌وگوهایی که همان لحظه باز هستند.',
        'محدودیت نرخ ارسال پیام اعمال می‌شود تا این قابلیت برای بمباران کسی استفاده نشود.',
        'می‌توانی هر کاربری را مسدود کنی. مسدودسازی دوطرفه است: بعد از آن هیچ‌کدامتان نمی‌توانید به دیگری پیام بدهید.',
        'می‌توانی یک پیام را گزارش کنی. گزارش‌ها برای بررسی ثبت می‌شوند و هرگز به‌طور خودکار جریمه‌ای برای فرد گزارش‌شده ایجاد نمی‌کنند.',
        'محتوای توهین‌آمیز، آزارگرانه، نفرت‌پراکن یا غیرقانونی نفرست و اطلاعات خصوصی دیگران را منتشر نکن. حسابی که این‌طور استفاده شود حذف می‌شود.',
      ],

      h_badges: '۶. نشان‌ها، بازی‌ها و زنجیره‌ها',
      badges: [
        'نشان‌ها از مقادیری داده می‌شوند که واقعاً ثبت کرده‌ای. هیچ نشانی برای وقت بیشتر گذراندن در برنامه داده نمی‌شود.',
        'نشان‌های دستاورد، پایداری و پیشرفت را به رسمیت می‌شناسند. شاخص‌های آگاهی خصوصی‌اند، هرگز به کسی نشان داده نمی‌شوند، و توصیف‌اند نه حکم.',
        'وقتی تاریخچه‌ات هنوز نمی‌تواند به پرسش یک نشان جواب بدهد، برنامه می‌گوید داده کافی نیست — حدس نمی‌زند و القا نمی‌کند که شکست خورده‌ای.',
        'بازی‌ها برای فهمیدن اعداد خودت‌اند، نه برای نمره‌دادن به تو. هیچ کاری در بازی‌ها امتیاز سلامتت، تاریخچه‌ات یا هیچ ورودی مدلی را عوض نمی‌کند.',
        'زنجیره‌ها هیچ‌وقت برای فشار آوردن به تو استفاده نمی‌شوند. شکستنشان جریمه ندارد و یک روزِ ازدست‌رفته شکست تلقی نمی‌شود.',
      ],

      h_guide: '۷. راهنمای دیجیتال و صدا',
      guide: [
        'راهنما برنامه را توضیح می‌دهد. هرگز تو را تشخیص نمی‌دهد و هرگز درباره‌ی ارزشت اظهار نظر نمی‌کند.',
        'صدایش از موتور گفتار داخلیِ خودِ مرورگرت استفاده می‌کند. هیچ صوتی جایی فرستاده نمی‌شود، با هیچ سرویس بیرونی تماس گرفته نمی‌شود، و هیچ کلید API در کار نیست.',
        'اینکه کدام زبان‌ها واقعاً با صدا خوانده می‌شوند به مرورگر و دستگاه تو بستگی دارد، نه به این برنامه.',
        'راهنما، صدایش، جلوه‌های صوتی، موسیقی محیطی و حرکت کاهش‌یافته کلیدهای مستقل‌اند. خاموش‌کردن هرکدام هیچ امتیاز، ورودی یا رکورد ذخیره‌شده‌ای را عوض نمی‌کند.',
      ],

      h_ai: '۸. کلید اختیاری مربی هوش مصنوعی',
      ai: [
        'مربی به‌طور پیش‌فرض کاملاً آفلاین کار می‌کند و از داده‌های ثبت‌شده‌ی خودت جواب می‌دهد.',
        'به‌صورت اختیاری می‌توانی کلید API خودت را برای یک ارائه‌دهنده‌ی بیرونی وارد کنی. تا وقتی خودت فعالش نکنی خاموش است.',
        'اگر فعالش کنی، پرسش‌هایت طبق شرایط و سیاست حریم خصوصیِ آن ارائه‌دهنده به او فرستاده می‌شود، نه ما. فقط در صورتی فعالش کن که این را بپذیری.',
        'کلید در مرورگر خودت ذخیره می‌شود و هرگز به ما منتقل نمی‌شود.',
      ],

      h_demo: '۹. حالت نمایشی',
      demo: [
        'حالت نمایشی برنامه را با یک تاریخچه‌ی مصنوعیِ واقع‌نما پر می‌کند تا بدون ثبت روزهای واقعی بتوانی بگردی.',
        'داده‌ی نمایشی به‌روشنی مصنوعی است و هرگز با ثبت‌های واقعی‌ات مخلوط نمی‌شود.',
        'هیچ‌چیزی که در حالت نمایشی ساخته می‌شود برای آموزش یا تنظیم هیچ مدلی استفاده نمی‌شود.',
      ],

      h_liability: '۱۰. محدودیت مسئولیت',
      liability: [
        'این یک پروژه‌ی دانشجویی و نمونه‌کار است که رایگان ارائه می‌شود. تا حداکثری که قانون اجازه می‌دهد، نویسندگان هیچ مسئولیتی در قبال ضرر یا آسیب ناشی از استفاده از آن نمی‌پذیرند.',
        'در دسترس بودن تضمین نمی‌شود. برنامه ممکن است هر زمان تغییر کند یا از کار بیفتد.',
        'چون نسخه‌ی خودت را اجرا می‌کنی، نگه‌داشتن نسخه‌ی پشتیبان از هرچه می‌خواهی حفظ شود بر عهده‌ی توست. قابلیت خروجی‌گرفتن دقیقاً برای همین هست.',
      ],

      h_changes: '۱۱. تغییر این شرایط',
      changes: [
        'این شرایط ممکن است با تغییر برنامه به‌روز شوند. تاریخ بالای صفحه نسخه‌ی فعلی را نشان می‌دهد.',
        'ادامه‌ی استفاده از برنامه پس از به‌روزرسانی یعنی شرایط به‌روزشده را می‌پذیری.',
      ],

      h_contact: '۱۲. تماس',
      contactLede: 'برای پرسش، درخواست حذف داده، گزارش باگ، یا هر چیزی درباره‌ی این متن، مستقیم در تماس باش:',
      email: 'ایمیل',
      phone: 'شماره تماس',
      contactNote: 'این یک پروژه‌ی نمایشی است که یک نفر آن را نگه می‌دارد. لطفاً برای پاسخ زمان معقولی در نظر بگیر.',
    },

    ar: {
      back: 'العودة إلى التطبيق',
      title: 'الشروط وإشعار الخصوصية',
      updated: 'آخر تحديث: أغسطس ٢٠٢٦',
      lede: 'Digital Wellness AI مشروع بحثي وتجريبي. ليس جهازاً طبياً ولا أداة سريرية ولا منتجاً معتمداً. اقرأ هذا قبل إنشاء حساب — فهو يصف بالضبط ما يفعله التطبيق بما تخبره به، والأشياء التي لن يدّعيها أبداً.',
      calloutTitle: 'القاعدة التي تعلو على كل قاعدة أخرى هنا',
      callout: 'لا شيء ينتجه هذا التطبيق تشخيصٌ طبي أو نفسي، ولا نتيجة فحص، ولا توصية علاجية. تظهر كلمات مثل «الخطر» و«التوتر» و«القلق» و«انخفاض المزاج» لأنك قيّمتها بنفسك — فهي أوصافك أنت ليومك أنت، لا نتائج سريرية. إن كنت في ضيق أو أزمة، فاتصل بمختص مؤهل أو بخدمات الطوارئ المحلية. هذا التطبيق غير مجهّز لذلك ولن يخبرك بغير ذلك أبداً.',

      h_use: '١. استخدام التطبيق',
      use: [
        'يمنحك التطبيق تقديراً إحصائياً آلياً لعادات الصحة الرقمية، محسوباً فقط من المعلومات التي تدخلها بنفسك.',
        'يجب أن تكون في السن التي تسمح لك قوانين بلدك بالموافقة على هذه الشروط وإنشاء حساب، أو أن يكون لديك إذن وليّ أمر.',
        'أنت مسؤول عمّا تدخله. الإدخال الكاذب عمداً ينتج درجة تبدو واثقة لكنها لا تصف أحداً، والتطبيق لا يستطيع كشف ذلك.',
        'يُقدَّم التطبيق «كما هو» دون أي ضمان، للاستخدام الشخصي والتعليمي. لا تعتمد عليه في أي قرار طبي أو قانوني أو مهني مهم.',
        'لا تستخدم التطبيق للتحرش بأحد أو انتحال شخصية أحد أو محاولة استخراج بيانات شخص آخر.',
      ],

      h_models: '٢. ما هي التنبؤات — وما ليست',
      models: [
        'يُستخدَم نموذجان مدرَّبان منفصلان، ويجيبان عن سؤالين مختلفين. أحدهما يقدّر درجة اليوم الذي سجّلته للتو. والآخر يقدّر النطاق الذي يُرجَّح أن تكون فيه بعد سبعة أيام. وهما ليسا الرقم نفسه، والتطبيق يسمّيهما منفصلين.',
        'كل رقم دقة يظهر في صفحة النموذج مقيس على بيانات محجوزة ومذكور بصراحة، بما في ذلك حيث كان أداء نموذج أسوأ من خط أساس بسيط.',
        'بيانات التدريب اصطناعية. أُنشئت لهذا المشروع، ولا تصف أشخاصاً حقيقيين، ولم تُستخدم سجلات أي شخص حقيقي لبناء النماذج.',
        'رقم السبعة أيام تقدير عن نمط، لا وعد عنك. لا يمكنه حساب ما لم تسجّله — مرض أو سفر أو تغيير عمل أو أي شيء آخر تفعله الحياة.',
        'إن لم يستطع التطبيق إنتاج رقم بصدق، قال ذلك بدل أن ينتجه. القيمة الفارغة أو الغائبة إجابة مقصودة لا عطل.',
      ],

      h_data: '٣. بياناتك',
      data: [
        'ما تدخله — الفئة العمرية وعادات وقت الشاشة والنوم وتقييمات المزاج والتركيز والأهداف التي تختارها — يُستخدم فقط لحساب درجتك وشروحك وسجلّك وتوصياتك أنت.',
        'تُخزَّن بياناتك محلياً في النسخة التي تشغّلها. تشغيله على جهازك يعني أنه لا يغادر جهازك.',
        'لا شيء يُباع، ولا شيء يُشارك مع أي طرف ثالث أو مُعلن.',
        'يمكنك تصدير كل ما يحتفظ به التطبيق عنك في أي وقت، بصيغة JSON أو كملف جداول، من قسم الخصوصية.',
        'يمكنك حذف حسابك وبياناته في أي وقت من المكان نفسه. الحذف يزيل تسجيلاتك وسجلّك وشاراتك.',
        'الأيام التي تضع عليها «لا تُسجَّل» تُستثنى من اتجاهاتك ومتوسطاتك، وتبقى مستثناة حتى تقول غير ذلك.',
      ],

      h_league: '٤. دوري الأصدقاء والمشاركة',
      league: [
        'الدوري متوقف حتى تشغّله بنفسك. لا يُنشأ أي اتصال تلقائياً، ولا يستطيع أحد إضافتك دون قبولك الصريح.',
        'المشاركة لكل فئة ولكل صديق على حدة. تؤشّر بالضبط على ما يراه شخص معيّن، وكل ما لا تؤشّر عليه يبقى خاصاً.',
        'يمكنك تغيير ما يراه صديق، أو إلغاء وصوله كلياً، في أي لحظة. الإلغاء يسري في البيانات نفسها لا في الواجهة فقط — فالصديق المُلغى يتوقف فوراً عن تلقي أرقامك.',
        'المقارنة الأساسية التي يعرضها الدوري هي مع ماضيك أنت. الأصدقاء سياق ولا يكونون العنوان أبداً.',
        'مؤشرات الوعي الخاصة لا تُشارَك مع أحد تحت أي إعداد، بما في ذلك الشارات المشتقّة منها. هي موجودة لك وحدك.',
      ],

      h_chat: '٥. الرسائل والحظر والإبلاغ',
      chat: [
        'الرسائل المباشرة والجماعية متاحة فقط بين من هم متصلون بالفعل وقبل كلاهما.',
        'يُصرَّح لكل رسالة على حدة عند قراءتها أو إرسالها. فقدان الوصول إلى محادثة يسري فوراً، حتى للمحادثات المفتوحة أصلاً.',
        'تُطبَّق حدود لمعدل الإرسال، حتى لا تُستخدم الميزة لإغراق أحد بالرسائل.',
        'يمكنك حظر أي مستخدم. الحظر متبادل: لا يستطيع أيٌّ منكما مراسلة الآخر بعده.',
        'يمكنك الإبلاغ عن رسالة. تُسجَّل البلاغات للمراجعة ولا تُوقِع أبداً عقوبة تلقائية على المُبلَّغ عنه.',
        'لا ترسل محتوى مسيئاً أو متحرشاً أو كارهاً أو غير قانوني، ولا تنشر معلومات خاصة بالآخرين. الحسابات التي تُستخدم هكذا يمكن إزالتها.',
      ],

      h_badges: '٦. الشارات والألعاب والسلاسل',
      badges: [
        'تُمنح الشارات من قيم سجّلتها فعلاً. ولا تُمنح أي شارة لقضاء وقت أطول في التطبيق.',
        'شارات الإنجاز تعترف بالانتظام والتحسّن. ومؤشرات الوعي خاصة، ولا تُعرض لأحد أبداً، وهي أوصاف لا أحكام.',
        'حين لا يستطيع سجلّك بعدُ الإجابة عمّا تسأله شارة، يقول التطبيق إن البيانات غير كافية — لا يخمّن ولا يوحي بأنك فشلت.',
        'الألعاب لفهم أرقامك أنت، لا لتقييمك. لا شيء تفعله في لعبة يغيّر درجة صحتك أو سجلّك أو أي مدخل للنموذج.',
        'لا تُستخدم السلاسل للضغط عليك أبداً. كسرها لا يحمل عقوبة، ويوم فائت لا يُصاغ كفشل.',
      ],

      h_guide: '٧. الدليل الرقمي والصوت',
      guide: [
        'الدليل يشرح التطبيق. لا يشخّصك أبداً ولا يعلّق على قيمتك.',
        'صوته يستخدم محرّك النطق المدمج في متصفّحك أنت. لا يُرسَل أي صوت إلى أي مكان، ولا يُتصَل بأي خدمة خارجية، ولا يوجد أي مفتاح API.',
        'أي اللغات يمكن نطقها فعلاً يعتمد على متصفّحك وجهازك، لا على هذا التطبيق.',
        'الدليل وصوته والمؤثرات الصوتية والموسيقى المحيطة والحركة المخفّضة مفاتيح مستقلة. إطفاء أيٍّ منها لا يغيّر درجة ولا مدخلاً ولا سجلاً محفوظاً.',
      ],

      h_ai: '٨. مفتاح مدرّب الذكاء الاصطناعي الاختياري',
      ai: [
        'يعمل المدرّب دون اتصال تماماً بشكل افتراضي، مجيباً من بياناتك المسجَّلة.',
        'يمكنك اختيارياً تقديم مفتاح API خاص بك لمزوّد ذكاء اصطناعي خارجي. وهو مطفأ ما لم تفعّله بنفسك.',
        'إن فعّلته، تُرسَل أسئلتك إلى ذلك المزوّد وفق شروطه وسياسة خصوصيته لا سياستنا. فعّله فقط إن قبلت ذلك.',
        'يُخزَّن المفتاح في متصفّحك أنت ولا يُنقَل إلينا أبداً.',
      ],

      h_demo: '٩. وضع العرض',
      demo: [
        'يملأ وضع العرض التطبيق بسجلّ اصطناعي واقعي لتستكشفه دون تسجيل أيام حقيقية أولاً.',
        'بيانات العرض اصطناعية بوضوح ولا تختلط أبداً بتسجيلاتك الحقيقية.',
        'لا شيء يُولَّد في وضع العرض يُستخدم لتدريب أي نموذج أو تعديله.',
      ],

      h_liability: '١٠. حدود المسؤولية',
      liability: [
        'هذا مشروع طلابي وعرض أعمال يُقدَّم مجاناً. وإلى أقصى حد يسمح به القانون، لا يقبل المؤلفون أي مسؤولية عن أي خسارة أو ضرر ناتج عن استخدامه.',
        'التوافر غير مضمون. قد يتغيّر التطبيق أو يتوقف عن العمل في أي وقت.',
        'ولأنك تشغّل نسختك الخاصة، فالاحتفاظ بنسخة احتياطية لما تريد الاحتفاظ به مسؤوليتك. ميزة التصدير موجودة لهذا بالضبط.',
      ],

      h_changes: '١١. تغييرات هذه الشروط',
      changes: [
        'قد تُحدَّث هذه الشروط مع تغيّر التطبيق. والتاريخ في الأعلى يعكس النسخة الحالية.',
        'استمرارك في استخدام التطبيق بعد التحديث يعني قبولك للشروط المحدَّثة.',
      ],

      h_contact: '١٢. التواصل',
      contactLede: 'للأسئلة أو طلبات حذف البيانات أو بلاغات الأخطاء أو أي شيء يخص هذا الإشعار، تواصل مباشرة:',
      email: 'البريد الإلكتروني',
      phone: 'رقم الهاتف',
      contactNote: 'هذا مشروع تجريبي يتولاه شخص واحد. يُرجى إتاحة وقت معقول للرد.',
    },

    zh: {
      back: '返回应用',
      title: '条款与隐私声明',
      updated: '最后更新：2026 年 8 月',
      lede: 'Digital Wellness AI 是一个研究与演示项目。它不是医疗器械，不是临床工具，也不是经过认证的产品。请在创建账号前阅读本文——它准确说明了这个应用会拿你告诉它的东西做什么，以及它永远不会宣称的事情。',
      calloutTitle: '这里最高于一切的一条规则',
      callout: '这个应用产出的任何东西都不是医学或心理诊断、筛查结果或治疗建议。「风险」「压力」「焦虑」「情绪低落」这类词之所以出现，是因为它们是你自己打的分——它们是你对自己一天的描述，不是临床结论。如果你正处于痛苦或危机之中，请联系合格的专业人士或当地急救服务。这个应用不具备那种能力，也永远不会告诉你相反的话。',

      h_use: '一、使用本应用',
      use: [
        '本应用给你的是一个自动的统计估计，只根据你自己输入的信息计算数字健康习惯。',
        '你必须达到你所在司法辖区同意本条款并创建账号的年龄，或已获得监护人许可。',
        '你对自己输入的内容负责。刻意虚假的记录会产生一个看起来很自信、却谁也不描述的分数，而应用无法察觉这一点。',
        '本应用按「现状」提供，不作任何担保，仅供个人和教育用途。请勿在任何具有医疗、法律或职业重要性的决定上依赖它。',
        '请勿使用本应用骚扰他人、冒充他人，或试图获取他人的数据。',
      ],

      h_models: '二、预测是什么——以及不是什么',
      models: [
        '这里使用两个各自独立训练的模型，它们回答两个不同的问题。一个估计你刚记录那一天的分数。另一个估计你在七天后可能处于哪个区间。它们不是同一个数字，应用会分别标注。',
        '模型页面上展示的每一个准确度数字都是在留出数据上测得的，并且如实呈现，包括某个模型表现不如一个简单基线的情况。',
        '训练数据是合成的。它是为这个项目生成的，不描述任何真实的人，构建模型时也没有使用任何真实个人的记录。',
        '七天的数字是关于一种模式的估计，而不是对你的承诺。它无法把你没有记录的事情计算在内——生病、出行、换工作，或者生活会做的任何其他事。',
        '如果应用无法诚实地给出一个数字，它会直说，而不是造一个出来。空值或缺失是一个有意的回答，不是故障。',
      ],

      h_data: '三、你的数据',
      data: [
        '你输入的内容——年龄区间、屏幕使用习惯、睡眠、情绪与专注度评分，以及你选择的目标——只用于计算你自己的分数、解释、历史和建议。',
        '你的数据由你运行的这份应用在本地存储。在自己的机器上运行，就意味着它不会离开你的机器。',
        '不出售任何数据，也不与任何第三方或广告商共享任何数据。',
        '你随时可以在隐私板块把应用保存的关于你的一切导出为 JSON 或表格文件。',
        '你随时可以在同一处删除账号及其数据。删除会移除你的记录、历史和徽章。',
        '你标记为「不要记录」的日子会被排除在趋势和平均值之外，并一直排除，直到你另行决定。',
      ],

      h_league: '四、好友联赛与分享',
      league: [
        '联赛在你亲自开启之前是关闭的。不会自动建立任何连接，也没有人能在未经你明确接受的情况下加你。',
        '分享是按类别、按好友分别设置的。你精确勾选某个人可以看到什么，凡是你没有勾选的都保持私密。',
        '你随时可以更改某位好友能看到的内容，或彻底撤销其访问权限。撤销作用于数据本身，而不只是界面——被撤销的好友会立即停止收到你的数字。',
        '联赛向你展示的主要比较是与你自己的过去比。好友只是背景，永远不是主角。',
        '私密的觉察指标在任何设置下都不会与任何人共享，由其衍生的徽章也一样。它们只为你而存在。',
      ],

      h_chat: '五、消息、拉黑与举报',
      chat: [
        '私聊和群聊仅在已经建立连接且双方都已接受的人之间可用。',
        '每条消息在读取或发送时都会单独授权。失去某个会话的访问权限会立即生效，包括已经打开的会话。',
        '消息发送有频率限制，以免这项功能被用来刷屏骚扰任何人。',
        '你可以拉黑任何用户。拉黑是双向的：此后你们谁也无法给对方发消息。',
        '你可以举报某条消息。举报会被记录以供审阅，并且绝不会自动对被举报者施加处罚。',
        '请勿发送辱骂、骚扰、仇恨或违法内容，也不要泄露他人的私人信息。以此方式使用的账号可能被移除。',
      ],

      h_badges: '六、徽章、游戏与连续记录',
      badges: [
        '徽章来自你实际记录过的数值。没有任何徽章是因为在应用里待得更久而给的。',
        '成就徽章认可的是坚持和进步。觉察指标是私密的，永远不会展示给别人，而且它们是描述而不是判决。',
        '当你的历史还无法回答某个徽章的问题时，应用会说数据不足——它不猜测，也不暗示你失败了。',
        '游戏是为了帮你理解自己的数字，而不是给你打分。你在游戏里做的任何事都不会改变你的健康分数、历史或任何模型输入。',
        '连续记录绝不用来给你施压。中断没有惩罚，漏掉一天也不会被说成失败。',
      ],

      h_guide: '七、数字向导与声音',
      guide: [
        '向导解释的是这个应用。它从不诊断你，也从不评论你的价值。',
        '它的声音使用你自己浏览器内置的语音引擎。没有音频被发送到任何地方，不联系任何外部服务，也不涉及任何 API 密钥。',
        '哪些语言真的能被朗读出来，取决于你的浏览器和设备，而不是这个应用。',
        '向导、它的声音、音效、环境音乐和减弱动效是各自独立的开关。关掉其中任何一个都不会改变分数、输入或任何已保存的记录。',
      ],

      h_ai: '八、可选的 AI 教练密钥',
      ai: [
        '教练默认完全离线工作，只根据你自己记录的数据作答。',
        '你可以选择性地提供自己的外部 AI 服务商 API 密钥。除非你亲自启用，否则它是关闭的。',
        '如果你启用它，你的问题会按照该服务商的条款和隐私政策发送给他们，而不是我们的。只有在你接受这一点时才启用。',
        '密钥保存在你自己的浏览器里，绝不会传输给我们。',
      ],

      h_demo: '九、演示模式',
      demo: [
        '演示模式会用一段逼真的合成历史填充应用，让你不必先记录真实的日子就能探索。',
        '演示数据明确是合成的，绝不会和你真实的记录混在一起。',
        '演示模式中生成的任何东西都不会用于训练或调整任何模型。',
      ],

      h_liability: '十、责任限制',
      liability: [
        '这是一个免费提供的学生与作品集项目。在法律允许的最大范围内，作者不对因使用本应用而产生的任何损失或损害承担责任。',
        '不保证可用性。应用可能随时变更或停止工作。',
        '因为你运行的是自己的副本，备份你想保留的东西是你自己的责任。导出功能正是为此而存在。',
      ],

      h_changes: '十一、本条款的变更',
      changes: [
        '本条款可能随应用的变化而更新。页首的日期反映当前版本。',
        '在更新后继续使用本应用，即表示你接受更新后的条款。',
      ],

      h_contact: '十二、联系方式',
      contactLede: '如有疑问、数据删除请求、错误报告，或任何与本声明有关的事情，请直接联系：',
      email: '邮箱',
      phone: '电话',
      contactNote: '这是一个由一个人维护的演示项目。回复可能需要一些时间，敬请谅解。',
    },
  };

  // The one pair of facts that must not be translated or reformatted.
  const EMAIL = 'amirhesamhh1378@gmail.com';
  const PHONE = '+98 903 590 6294';
  const PHONE_HREF = '+989035906294';

  function esc(s) {
    return String(s).replace(/[&<>"]/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]
    ));
  }

  function section(heading, items) {
    return `<h2>${esc(heading)}</h2><ul>${
      items.map((li) => `<li>${esc(li)}</li>`).join('')
    }</ul>`;
  }

  /* Note on the phone number below: it carries dir="ltr" and bidi
     isolation because a number dropped into an RTL paragraph otherwise
     renders with the + and the country code flipped to the wrong end.

     Note on comments in general in this function: the markup is built
     in a template literal, and an HTML comment cannot go inside one.
     `<!--` puts the HTML parser into its script-data-escaped state, and
     from there it stops recognising the closing tag where it should -
     the whole script silently fails to run, with no console error to
     say so. Explanatory comments therefore live out here. */
  function render(lang) {
    const t = T[lang] || T.en;
    const rtl = RTL.indexOf(lang) !== -1;
    document.documentElement.setAttribute('lang', lang);
    document.documentElement.setAttribute('dir', rtl ? 'rtl' : 'ltr');

    document.querySelectorAll('[data-t]').forEach((el) => {
      const key = el.getAttribute('data-t');
      if (t[key]) el.textContent = t[key];
    });
    document.querySelectorAll('#docLang button').forEach((b) => {
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    });

    document.getElementById('doc').innerHTML = `
      <h1 class="text-gradient">${esc(t.title)}</h1>
      <p class="doc-updated">${esc(t.updated)}</p>
      <p class="muted lede">${esc(t.lede)}</p>

      <div class="doc-callout">
        <strong>${esc(t.calloutTitle)}</strong><br />${esc(t.callout)}
      </div>

      ${section(t.h_use, t.use)}
      ${section(t.h_models, t.models)}
      ${section(t.h_data, t.data)}
      ${section(t.h_league, t.league)}
      ${section(t.h_chat, t.chat)}
      ${section(t.h_badges, t.badges)}
      ${section(t.h_guide, t.guide)}
      ${section(t.h_ai, t.ai)}
      ${section(t.h_demo, t.demo)}
      ${section(t.h_liability, t.liability)}
      ${section(t.h_changes, t.changes)}

      <h2>${esc(t.h_contact)}</h2>
      <p class="muted">${esc(t.contactLede)}</p>
      <div class="doc-contact">
        <dl>
          <dt>${esc(t.email)}</dt>
          <dd><a href="mailto:${EMAIL}" dir="ltr">${EMAIL}</a></dd>
          <dt>${esc(t.phone)}</dt>
          <dd><a href="tel:${PHONE_HREF}" dir="ltr" style="unicode-bidi:isolate">${PHONE}</a></dd>
        </dl>
        <p class="muted" style="margin-top:14px;margin-bottom:0;font-size:.86rem">${esc(t.contactNote)}</p>
      </div>
    `;
  }

  let current = 'en';
  try {
    const stored = localStorage.getItem(KEY);
    if (stored && LANGS.indexOf(stored) !== -1) current = stored;
  } catch (e) { /* storage disabled - English is a fine default */ }

  document.getElementById('docLang').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-lang]');
    if (!btn) return;
    current = btn.getAttribute('data-lang');
    try { localStorage.setItem(KEY, current); } catch (err) {}
    render(current);
  });

  render(current);
})();
