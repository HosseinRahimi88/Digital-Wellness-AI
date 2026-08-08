/*
  AI Coach knowledge base.

  Separated from coach-chat.js on purpose: that file owns the guards,
  routing and the user's real data; this one is pure content. Keeping
  them apart means the safety logic can be reviewed without scrolling
  past hundreds of lines of copy, and copy can be extended without
  touching a single guard.

  Content rules, enforced by review and by tests/test_coach_knowledge:
  - NO medical, diagnostic or treatment claims anywhere. Research is
    phrased as association ("tends to", "is linked with"), never as a
    causal or clinical statement about the reader.
  - Nothing here refers to the user's own numbers. Personalised answers
    are composed in coach-chat.js, which actually has the data; this
    file only supplies general, verifiable digital-wellbeing knowledge.
  - Every entry exists in English and Persian.
*/
(function () {
  /* Topic entries. `match` is tried against the user's message; the
     first hit wins, so more specific topics are listed first. */
  const TOPICS = [
    {
      key: 'sleep',
      match: /\b(sleep|sleeping|insomnia|bedtime|rest|tired|nap|wake up|awake at night)\b|خواب|بی‌خوابی|بیدار/i,
      en: "Sleep is one of the strongest signals in this whole model. Two things move it most: consistency (same sleep and wake times, even at weekends) and what happens in the last hour before bed. Bright screens late in the evening are associated with a later body clock, so the practical lever is usually distance rather than willpower — charge the phone across the room, or outside the bedroom entirely. If you only change one thing this week, a fixed cut-off time for screens tends to be the one that carries the most.",
      fa: "خواب یکی از قوی‌ترین سیگنال‌های کل این مدل است. دو چیز بیشترین اثر را دارند: ثبات (ساعت خواب و بیداری یکسان، حتی آخر هفته‌ها) و آنچه در آخرین ساعت قبل از خواب اتفاق می‌افتد. نور شدید صفحه در اواخر شب با به‌تعویق‌افتادن ساعت بدن مرتبط است، پس اهرم عملی معمولاً فاصله است نه اراده — گوشی را آن‌سوی اتاق یا کلاً بیرون از اتاق خواب شارژ کن. اگر فقط یک چیز را این هفته تغییر بدهی، یک ساعت پایان مشخص برای صفحه‌نمایش معمولاً بیشترین اثر را دارد.",
    },
    {
      key: 'focus',
      match: /\b(focus|concentrat|attention|distract|deep work|productiv|procrastinat)\b|تمرکز|حواس‌پرت|بهره‌وری|تعلل/i,
      en: "Attention takes real time to recover after an interruption, which is why scattered checking costs far more than the seconds it appears to. In this dataset, how *often* you pick up your device predicts focus better than total hours do. The practical move is batching: pick two or three fixed windows for messages instead of reacting instantly, and protect one 25-minute block a day with the phone in another room. Turning off notifications for your three noisiest apps — not all of them, just the loudest three — is usually the highest-leverage single change.",
      fa: "توجه بعد از هر وقفه واقعاً زمان می‌برد تا بازیابی شود؛ برای همین چک‌کردن‌های پراکنده خیلی بیشتر از چند ثانیه‌ای که به نظر می‌رسند هزینه دارند. در این داده، تعداد دفعاتی که گوشی را برمی‌داری بهتر از مجموع ساعت‌ها تمرکز را پیش‌بینی می‌کند. حرکت عملی دسته‌بندی است: دو سه بازه‌ی مشخص برای پیام‌ها انتخاب کن به‌جای واکنش آنی، و روزی یک بازه‌ی ۲۵ دقیقه‌ای را با گوشی در اتاق دیگر محافظت کن. خاموش‌کردن اعلان سه اپ پرسروصداتر — نه همه، فقط همان سه تا — معمولاً پراثرترین تغییر تکی است.",
    },
    {
      key: 'notifications',
      match: /\b(notification|alert|ping|buzz|badge|interrupt)\b|اعلان|نوتیف|هشدار/i,
      en: "Notification volume and reported stress tend to move together across large samples. The useful framing isn't 'turn everything off' — it's that most people have two or three apps generating the large majority of interruptions. Silence those, keep the ones that genuinely need to reach you, and the density number this app tracks (notifications per hour of screen time) usually drops sharply without you missing anything that mattered.",
      fa: "حجم اعلان‌ها و میزان استرس گزارش‌شده در نمونه‌های بزرگ معمولاً هم‌جهت حرکت می‌کنند. قاب مفید «همه را خاموش کن» نیست — واقعیت این است که برای بیشتر افراد دو سه اپ اکثریت قاطع وقفه‌ها را می‌سازند. همان‌ها را ساکت کن، آن‌هایی که واقعاً باید به تو برسند را نگه دار، و عددی که این اپ ردیابی می‌کند (اعلان در هر ساعت استفاده) معمولاً به‌شدت پایین می‌آید بدون اینکه چیز مهمی را از دست بدهی.",
    },
    {
      key: 'social',
      match: /\b(social media|instagram|tiktok|twitter|scroll|feed|comparison|fomo)\b|شبکه اجتماعی|اینستا|اسکرول|مقایسه|فومو/i,
      en: "Passive scrolling and active messaging show different associations with mood — how you use an app matters, not just how long. Social comparison is one of the more consistent signals in digital-wellbeing research, which is why this app asks about it directly. A concrete experiment: before opening a social app, name what you actually want from it. If you can't, that's genuinely useful information. Greyscale in the evening also makes feeds noticeably less magnetic.",
      fa: "اسکرول منفعل و گفتگوی فعال ارتباط متفاوتی با حال‌وهوا نشان می‌دهند — نحوه‌ی استفاده مهم است، نه فقط مدتش. مقایسه‌ی اجتماعی یکی از پایدارترین سیگنال‌ها در پژوهش‌های سلامت دیجیتال است؛ برای همین این اپ مستقیم درباره‌اش می‌پرسد. یک آزمایش مشخص: قبل از باز کردن یک اپ اجتماعی، بگو دقیقاً چه می‌خواهی. اگر نتوانستی، همین خودش اطلاعات مفیدی است. حالت سیاه‌وسفید در عصر هم فیدها را محسوس کمتر جذاب می‌کند.",
    },
    {
      key: 'night',
      match: /\b(night|late night|midnight|evening|before bed|blue light)\b|شب|نیمه‌شب|قبل خواب|نور آبی/i,
      en: "Night-time use shows up twice in your score: directly, and again through whatever it does to your sleep. The cleanest interventions are structural rather than behavioural — a fixed screen cut-off treated like a real appointment, a charger outside the bedroom, and 'Do Not Disturb' scheduled rather than toggled manually. Anything that removes the decision works better than anything that relies on making the decision correctly at midnight.",
      fa: "استفاده‌ی شبانه دو بار در امتیازت ظاهر می‌شود: مستقیم، و دوباره از طریق اثری که بر خوابت می‌گذارد. تمیزترین مداخله‌ها ساختاری‌اند نه رفتاری — یک ساعت پایان مشخص که مثل یک قرار واقعی با آن رفتار شود، شارژر بیرون از اتاق خواب، و «مزاحم نشوید» زمان‌بندی‌شده به‌جای دستی. هر چیزی که تصمیم را حذف کند بهتر از هر چیزی است که به درست‌تصمیم‌گرفتن در نیمه‌شب تکیه دارد.",
    },
    {
      key: 'stress',
      match: /\b(stress|anxious|anxiety|overwhelm|burnout|pressure|calm|relax)\b|استرس|اضطراب|فرسودگی|آرام/i,
      en: "I can talk about the habit side of this, not the clinical side. What the data supports: notification load, fragmented attention and short sleep all tend to travel with higher reported stress, and they're the parts you can actually adjust. Short daytime movement breaks are linked with better sustained attention later in the day, which tends to take pressure off the evening. If stress is persistent or heavy, that's a conversation for a qualified professional rather than an app — I'd rather say that plainly than pretend otherwise.",
      fa: "می‌توانم درباره‌ی سمت عادت‌ها صحبت کنم، نه سمت بالینی. آنچه داده پشتیبانی می‌کند: بار اعلان‌ها، توجه تکه‌تکه و خواب کوتاه همگی با استرس گزارش‌شده‌ی بالاتر همراه‌اند، و همین‌ها بخش‌هایی هستند که واقعاً می‌توانی تنظیمشان کنی. وقفه‌های کوتاه حرکتی در طول روز با تمرکز پایدارتر در ادامه‌ی روز مرتبط‌اند، که معمولاً فشار را از روی عصر برمی‌دارد. اگر استرس پایدار یا سنگین است، آن گفتگویی برای یک متخصص واجد شرایط است نه یک اپ — ترجیح می‌دهم این را صریح بگویم.",
    },
    {
      key: 'activity',
      match: /\b(exercise|activity|workout|walk|move|movement|sedentary|gym|steps)\b|ورزش|فعالیت|پیاده‌روی|تحرک|حرکت/i,
      en: "Physical activity is one of the few inputs here that improves several others at once — it's associated with better sleep quality and better sustained attention, so it tends to lift more than its own line in the breakdown. The bar is lower than people assume: short movement breaks during the day count, and swapping one scrolling session for a walk is the same time spent with a very different result.",
      fa: "فعالیت بدنی یکی از معدود ورودی‌هایی است که همزمان چند مورد دیگر را هم بهبود می‌دهد — با کیفیت خواب بهتر و تمرکز پایدارتر مرتبط است، پس معمولاً بیشتر از سهم خودش در تفکیک، امتیاز را بالا می‌برد. آستانه‌اش از چیزی که مردم فکر می‌کنند پایین‌تر است: وقفه‌های کوتاه حرکتی در طول روز حساب می‌شوند، و جایگزین‌کردن یک جلسه‌ی اسکرول با پیاده‌روی یعنی همان زمان با نتیجه‌ای کاملاً متفاوت.",
    },
    {
      key: 'screen_time',
      match: /\b(screen time|hours|too much|reduce|cut down|limit|detox|addiction|dependent)\b|زمان صفحه|ساعت|کم کنم|محدود|اعتیاد|وابستگ/i,
      en: "Total hours are the least interesting number in your check-in, honestly. Two people with identical totals can have very different scores here, because fragmentation, timing and category matter more. So 'use it less' is weak advice; 'use it in fewer, longer, more deliberate blocks, and not in the last hour before bed' is what the data actually points at. App timers help only if you let them interrupt you — an ignored limit isn't a limit.",
      fa: "صادقانه بگویم، مجموع ساعت‌ها کم‌جذاب‌ترین عدد در بررسی توست. دو نفر با مجموع یکسان می‌توانند امتیازهای خیلی متفاوتی اینجا داشته باشند، چون پراکندگی، زمان‌بندی و دسته‌ی استفاده مهم‌ترند. پس «کمتر استفاده کن» توصیه‌ی ضعیفی است؛ «در بلوک‌های کمتر، طولانی‌تر و سنجیده‌تر استفاده کن، و نه در آخرین ساعت قبل از خواب» چیزی است که داده واقعاً به آن اشاره می‌کند. تایمر اپ‌ها فقط وقتی کمک می‌کنند که بگذاری کارت را قطع کنند — محدودیتی که نادیده گرفته شود، محدودیت نیست.",
    },
    {
      key: 'score_meaning',
      match: /\b(what does .{0,20}score mean|how is .{0,20}(score|it) calculated|how does this work|what is the score|shap|explain the model)\b|امتیاز یعنی چه|چطور محاسبه|چطور کار می‌کند|مدل چیست/i,
      en: "Two models run on every check-in. A classifier puts you in a risk category, and a regressor produces the 0–100 score. Then SHAP works out how much each of your inputs pushed that score up or down — that's where the 'what drove this' list comes from, so it's the model explaining itself rather than me guessing. Separately, the dimension breakdown is plain arithmetic over the same inputs, shown next to the model output so you can sanity-check one against the other.",
      fa: "روی هر بررسی دو مدل اجرا می‌شوند. یک طبقه‌بند تو را در یک دسته‌ی ریسک قرار می‌دهد، و یک رگرسور امتیاز ۰ تا ۱۰۰ را تولید می‌کند. بعد SHAP حساب می‌کند هر ورودی چقدر آن امتیاز را بالا یا پایین برده — فهرست «چه چیزی این را ساخت» از همین‌جا می‌آید، پس این خود مدل است که توضیح می‌دهد نه حدس من. جدا از آن، تفکیک ابعاد حساب ساده‌ای روی همان ورودی‌هاست که کنار خروجی مدل نشان داده می‌شود تا بتوانی یکی را با دیگری بسنجی.",
    },
    {
      key: 'accuracy',
      match: /\b(accurate|accuracy|trust|reliable|how sure|confidence|wrong|believe)\b|دقت|قابل اعتماد|مطمئن|اشتباه/i,
      en: "Fair question, and the honest answer is on the Model page — the real numbers are there, not marketing ones. Two things worth knowing: the model is measured on people it has never seen, which is much harder than it sounds, and it's slightly overconfident on new users, so treat a high confidence figure as 'probably' rather than 'certainly'. The uncertainty range shown with your score exists precisely because a single number would overstate how precise this is.",
      fa: "سؤال منصفانه‌ای است، و پاسخ صادقانه در صفحه‌ی مدل است — اعداد واقعی آنجاست، نه اعداد تبلیغاتی. دو نکته ارزش دانستن دارند: مدل روی افرادی سنجیده می‌شود که هرگز ندیده، که خیلی سخت‌تر از چیزی است که به نظر می‌رسد، و روی کاربران جدید کمی بیش‌ازحد مطمئن است، پس یک عدد اطمینان بالا را «احتمالاً» بخوان نه «قطعاً». بازه‌ی عدم قطعیتی که کنار امتیازت نشان داده می‌شود دقیقاً برای همین وجود دارد که یک عدد تنها، دقت این را بیش از واقع نشان می‌دهد.",
    },
    {
      key: 'privacy',
      match: /\b(privacy|private|data|stored|share|sell|delete|export|gdpr)\b|حریم خصوصی|داده من|ذخیره|حذف|خروجی/i,
      en: "Your data is used to compute your own predictions and nothing else — not sold, not shared, no third-party analytics on it. Everything is stored locally by this app. From your Profile page you can export a full copy of everything held about you as a file, or delete your account and its entire history permanently. If you ever paste an API key into the Coach, it lives in the browser tab's memory only and is gone the moment you close it.",
      fa: "داده‌ی تو برای محاسبه‌ی پیش‌بینی‌های خودت استفاده می‌شود و نه چیز دیگری — نه فروخته می‌شود، نه به اشتراک گذاشته می‌شود، و هیچ تحلیل شخص‌ثالثی روی آن اجرا نمی‌شود. همه‌چیز به‌صورت محلی توسط همین اپ ذخیره می‌شود. از صفحه‌ی پروفایل می‌توانی یک نسخه‌ی کامل از هر چیزی که درباره‌ات نگه داشته شده را به‌صورت فایل خروجی بگیری، یا حساب و کل تاریخچه‌اش را برای همیشه حذف کنی. اگر هم کلید API در مربی وارد کنی، فقط در حافظه‌ی همان تب مرورگر می‌ماند و با بستنش از بین می‌رود.",
    },
    {
      key: 'habit_building',
      match: /\b(habit|routine|consistent|stick to|motivation|discipline|how do i start|willpower)\b|عادت|روتین|ثبات|انگیزه|انضباط|از کجا شروع/i,
      en: "The pattern that actually works here is unglamorous: one change, made small enough that it survives a bad week. Adding friction beats relying on willpower — moving an app off the home screen, charging the phone elsewhere, scheduling Do Not Disturb. And measure it, which you're already doing; people consistently underestimate their own screen time, usually by a wide margin, so the check-in itself is doing real work even before you change anything.",
      fa: "الگویی که واقعاً اینجا جواب می‌دهد پرزرق‌وبرق نیست: یک تغییر، آن‌قدر کوچک که از یک هفته‌ی بد جان سالم به در ببرد. اضافه‌کردن اصطکاک از تکیه بر اراده بهتر است — برداشتن یک اپ از صفحه‌ی اصلی، شارژ گوشی جای دیگر، زمان‌بندی «مزاحم نشوید». و اندازه‌گیری‌اش کن، که همین حالا داری انجام می‌دهی؛ مردم مدام زمان استفاده‌ی خودشان را کمتر از واقعیت تخمین می‌زنند، اغلب با اختلاف زیاد، پس خود بررسی حتی قبل از هر تغییری دارد کار واقعی انجام می‌دهد.",
    },
    {
      key: 'app_usage',
      match: /\b(how do i use|what can (you|this) do|help me|features|what should i do here|get started|guide)\b|چطور استفاده کنم|چیکار می‌تونی|کمکم کن|از کجا شروع کنم|راهنما/i,
      en: "Here's the short version: run a check-in, and you get a real score with the specific reasons behind it plus recommendations. The Dashboard tracks it over time, the Weekly Plan turns your weakest areas into a seven-day list, What-if lets you test a change before committing to it, and Analytics shows your trend once you have a few days logged. Ask me about any of your results and I'll use your actual data — or tap the guide character on any page and it'll explain what that screen does.",
      fa: "نسخه‌ی کوتاهش این است: یک بررسی انجام بده، و یک امتیاز واقعی با دلایل مشخصش به‌همراه توصیه‌ها می‌گیری. داشبورد آن را در طول زمان ردیابی می‌کند، برنامه‌ی هفتگی ضعیف‌ترین حوزه‌هایت را به یک فهرست هفت‌روزه تبدیل می‌کند، شبیه‌ساز اجازه می‌دهد یک تغییر را قبل از تعهد به آن آزمایش کنی، و تحلیل‌ها بعد از چند روز ثبت، روندت را نشان می‌دهد. درباره‌ی هرکدام از نتایجت از من بپرس تا از داده‌ی واقعی‌ات استفاده کنم — یا روی شخصیت راهنما در هر صفحه بزن تا توضیح بدهد آن صفحه چه می‌کند.",
    },
    {
      key: 'greeting',
      match: /^(hi|hey|hello|yo|salam|good (morning|evening|afternoon))\b|^(سلام|درود|چطوری)/i,
      en: "Hey. I'm here for anything about your digital wellbeing — your score, a specific area like sleep or focus, or what to change first. Type /fit if you want me to load your latest check-in as context.",
      fa: "سلام. برای هر چیزی درباره‌ی سلامت دیجیتالت اینجا هستم — امتیازت، یک حوزه‌ی خاص مثل خواب یا تمرکز، یا اینکه اول چه چیزی را تغییر بدهی. اگر می‌خواهی آخرین بررسی‌ات را به‌عنوان زمینه بارگذاری کنم، /fit را بزن.",
    },
    {
      key: 'thanks',
      match: /\b(thanks|thank you|thx|appreciate|cheers)\b|ممنون|مرسی|سپاس/i,
      en: "Any time. If you want to go deeper on one area, just name it — sleep, focus, notifications, night use, activity.",
      fa: "هر وقت خواستی. اگر می‌خواهی روی یک حوزه عمیق‌تر شویم، فقط اسمش را بگو — خواب، تمرکز، اعلان‌ها، استفاده‌ی شبانه، فعالیت.",
    },
  ];

  /** First topic whose pattern matches, or null. */
  function findTopic(text) {
    const q = String(text || '');
    return TOPICS.find((t) => t.match.test(q)) || null;
  }

  function textFor(topic, lang) {
    if (!topic) return null;
    return topic[lang] || topic.en;
  }

  /* Follow-up prompts offered as clickable chips, so a user who doesn't
     know what to ask still has a way in. */
  const SUGGESTIONS = {
    en: ['What is my score?', 'What should I fix first?', 'How is my score calculated?', 'Help me sleep better', 'Why is my focus low?'],
    fa: ['امتیازم چند است؟', 'اول چه چیزی را درست کنم؟', 'امتیازم چطور محاسبه می‌شود؟', 'برای خواب بهتر کمکم کن', 'چرا تمرکزم پایین است؟'],
  };

  function suggestionsFor(lang) {
    return SUGGESTIONS[lang] || SUGGESTIONS.en;
  }

  window.DWCoachKnowledge = { TOPICS, findTopic, textFor, suggestionsFor };
})();
