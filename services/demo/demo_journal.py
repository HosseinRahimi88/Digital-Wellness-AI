"""
Demo journal pages
-------------------
What each demo person wrote in their book, in all four languages.

Why this is its own module: services/demo/demo_service.py already carries
the trajectory maths, the friend league and the chat scripts, and this
is four hundred lines of prose that nothing else needs to read.

Why the pages are staged rather than random
--------------------------------------------
Each profile is a story - the improving person starts badly, relapses
in the middle and comes out the other side - and a book whose pages
are shuffled tells no story at all. So each profile has eight pages in
ORDER, and DemoService walks them across the demo's real dates. Page
one of the improving book is the bad night; page eight is the ordinary
day that no longer needs writing about.

Why they carry four languages
------------------------------
A demo page is the one piece of "user-written" text in the app that a
reviewer reads in their own language. A real person's page is in
whatever language they typed it in and stays that way; a demo person
has to be readable in all four, so every page ships as
`{lang: text}` and the client picks - the same `text_i18n` shape the
prediction and plan responses already use.

Nothing here is presented as a real person's diary. These are written
for four synthetic profiles whose numbers are themselves synthetic;
what is real in a demo is the model that scores them.
"""

from __future__ import annotations

from typing import Any

# One page = (mood, {lang: text}). Moods are the closed set in
# services/identity/journal_service.py::MOODS - rough, low, steady, good, great.
Page = tuple[str, dict[str, str]]


_IMPROVING: tuple[Page, ...] = (
    ("rough", {
        "en": "Logged today because I said I would. The phone was in my hand from the second I woke up until about two in the morning. Not proud of it. Writing it down anyway.",
        "fa": "امروز را ثبت کردم چون قول داده بودم. از لحظه‌ای که بیدار شدم تا حوالی دو بامداد گوشی دستم بود. افتخاری ندارد. باز هم می‌نویسمش.",
        "ar": "سجّلت اليوم لأنني وعدت بذلك. كان الهاتف في يدي من لحظة استيقاظي حتى الثانية فجرًا تقريبًا. لست فخورًا بذلك، لكنني أكتبه على أي حال.",
        "zh": "今天还是记了，因为我答应过自己。从睁眼那一刻到凌晨两点，手机一直在手里。不值得骄傲，但还是写下来。",
    }),
    ("low", {
        "en": "Moved the charger out to the kitchen. Slept badly anyway — but at three in the morning there was nothing to check, so I didn't check anything.",
        "fa": "شارژر را بردم آشپزخانه. باز هم بد خوابیدم — ولی ساعت سه بامداد چیزی نبود که چک کنم، پس چیزی چک نکردم.",
        "ar": "نقلت الشاحن إلى المطبخ. نمت بشكل سيئ رغم ذلك — لكن في الثالثة فجرًا لم يكن هناك ما أتفقده، فلم أتفقد شيئًا.",
        "zh": "把充电器挪到厨房了。还是没睡好——但凌晨三点没有东西可看，所以我什么都没看。",
    }),
    ("steady", {
        "en": "First morning in a long time that didn't start with the feed. Made coffee, sat there, felt strange about it.",
        "fa": "اولین صبح بعد از مدت‌ها که با اسکرول کردن شروع نشد. قهوه درست کردم، نشستم، و حس عجیبی داشت.",
        "ar": "أول صباح منذ وقت طويل لا يبدأ بالتصفّح. أعددت القهوة وجلست، وكان الشعور غريبًا.",
        "zh": "很久以来第一个不是从刷手机开始的早晨。煮了咖啡，坐着，感觉有点怪。",
    }),
    ("rough", {
        "en": "Slipped. Long night, three episodes I didn't really choose to watch. Starting again tomorrow, which I've said before.",
        "fa": "لغزیدم. شبِ درازی بود، سه قسمت پشت هم که واقعاً انتخابشان نکردم. فردا از نو شروع می‌کنم — که قبلاً هم گفته‌ام.",
        "ar": "تعثّرت. ليلة طويلة وثلاث حلقات لم أخترها فعلًا. سأبدأ من جديد غدًا، وقد قلت هذا من قبل.",
        "zh": "又崩了。熬到很晚，连着三集，其实并不是我主动选的。明天重新开始——这话我说过。",
    }),
    ("steady", {
        "en": "Back on it. Turned off every notification that isn't an actual person. The count halved and I haven't missed one of them.",
        "fa": "دوباره برگشتم. هر اعلانی که از طرف یک آدم واقعی نبود را خاموش کردم. تعدادش نصف شد و دلم برای هیچ‌کدامشان تنگ نشده.",
        "ar": "عدت إلى المسار. أوقفت كل إشعار لا يأتي من إنسان حقيقي. انخفض العدد إلى النصف ولم أفتقد أيًا منها.",
        "zh": "回到正轨。把所有不是真人发来的通知都关了。数量少了一半，一个也没想念。",
    }),
    ("good", {
        "en": "Walked in the evening instead of scrolling. Boring, honestly — and I slept through the whole night.",
        "fa": "عصر به‌جای اسکرول کردن پیاده‌روی کردم. راستش حوصله‌سربر بود — و تمام شب را یک‌سره خوابیدم.",
        "ar": "مشيت في المساء بدل التصفّح. كان مملًا بصراحة — ونمت الليل كله دون أن أستيقظ.",
        "zh": "晚上去散步，没刷手机。老实说挺无聊的——然后一觉睡到天亮。",
    }),
    ("good", {
        "en": "Two weeks in. Screen time is down about a third, and I've stopped counting the hours — which is probably the actual change.",
        "fa": "دو هفته گذشت. زمان استفاده حدود یک‌سوم کم شده و دیگر ساعت‌ها را نمی‌شمارم — که احتمالاً تغییر اصلی همین است.",
        "ar": "مرّ أسبوعان. انخفض وقت الشاشة نحو الثلث، وتوقفت عن عدّ الساعات — وهذا على الأرجح التغيير الحقيقي.",
        "zh": "两周了。屏幕时间少了大约三分之一，而且我不再数小时了——这大概才是真正的变化。",
    }),
    ("great", {
        "en": "Today felt ordinary, and ordinary is what I was after. Keeping the same wake-up time at the weekend turns out to be the whole trick.",
        "fa": "امروز عادی بود، و عادی همان چیزی بود که می‌خواستم. معلوم شد کل ترفند همین است: آخر هفته هم ساعت بیداری را عوض نکنی.",
        "ar": "بدا اليوم عاديًا، والعادي هو ما كنت أسعى إليه. اتضح أن الحيلة كلها في الحفاظ على موعد الاستيقاظ نفسه في عطلة الأسبوع.",
        "zh": "今天很平常，而平常正是我想要的。原来诀窍就是周末也保持同样的起床时间。",
    }),
)


_HEALTHY: tuple[Page, ...] = (
    ("good", {
        "en": "Good day. Up on time, worked the morning block, put the phone in a drawer for the afternoon.",
        "fa": "روز خوبی بود. سر وقت بیدار شدم، بلوک صبح را کار کردم و بعدازظهر گوشی را گذاشتم توی کشو.",
        "ar": "يوم جيد. استيقظت في الموعد، أنجزت فترة الصباح، ووضعت الهاتف في الدرج بعد الظهر.",
        "zh": "不错的一天。准时起床，上午专注工作，下午把手机放进抽屉。",
    }),
    ("steady", {
        "en": "Slower morning than usual. Still got the walk in before it got hot.",
        "fa": "صبح کندتری از همیشه بود. با این حال قبل از گرم شدن هوا پیاده‌روی را رفتم.",
        "ar": "صباح أبطأ من المعتاد. مع ذلك مشيت قبل أن يشتد الحر.",
        "zh": "早上比平时慢些。还是赶在天热之前去走了走。",
    }),
    ("steady", {
        "en": "Long meeting day and my eyes know it. Screens the whole day — but none of it after dinner.",
        "fa": "روزِ پر از جلسه بود و چشم‌هایم می‌فهمند. تمام روز پای صفحه — ولی بعد از شام هیچ.",
        "ar": "يوم مليء بالاجتماعات وعيناي تشعران بذلك. شاشات طوال اليوم — لكن لا شيء بعد العشاء.",
        "zh": "开了一整天会，眼睛都知道。整天对着屏幕——但晚饭后一点没碰。",
    }),
    ("low", {
        "en": "Slept badly for no reason I can point at. Everything else was the same as yesterday.",
        "fa": "بی‌آنکه دلیلی داشته باشم بد خوابیدم. بقیه‌ی چیزها دقیقاً مثل دیروز بود.",
        "ar": "نمت بشكل سيئ دون سبب أستطيع تحديده. كل شيء آخر كان كما كان بالأمس.",
        "zh": "莫名其妙没睡好。其他一切和昨天一样。",
    }),
    ("good", {
        "en": "Back to normal. Read forty pages before bed instead of the phone, and it worked the way it always does.",
        "fa": "همه‌چیز به حالت عادی برگشت. قبل از خواب به‌جای گوشی چهل صفحه کتاب خواندم و مثل همیشه جواب داد.",
        "ar": "عاد كل شيء إلى طبيعته. قرأت أربعين صفحة قبل النوم بدل الهاتف، ونجح الأمر كما ينجح دائمًا.",
        "zh": "恢复正常。睡前读了四十页书而不是刷手机，还是一样管用。",
    }),
    ("great", {
        "en": "Weekend. Nothing scheduled, no alarm, and I woke up at the same time anyway. That genuinely surprised me.",
        "fa": "آخر هفته. نه برنامه‌ای، نه زنگ ساعتی، و باز هم سر همان ساعت بیدار شدم. واقعاً غافلگیر شدم.",
        "ar": "عطلة نهاية الأسبوع. لا مواعيد ولا منبّه، ومع ذلك استيقظت في الوقت نفسه. فاجأني ذلك فعلًا.",
        "zh": "周末。没有安排，没定闹钟，结果还是同一时间醒了。这真让我意外。",
    }),
    ("good", {
        "en": "Busy but fine. The routine does the work now — I don't have to decide it every morning.",
        "fa": "پرمشغله ولی خوب. حالا خودِ روتین کار را انجام می‌دهد — لازم نیست هر صبح دوباره تصمیم بگیرم.",
        "ar": "يوم مزدحم لكنه جيد. الروتين هو من يقوم بالعمل الآن — لم أعد أقرّره كل صباح.",
        "zh": "很忙但还好。现在是习惯在替我做事——不用每天早上重新决定。",
    }),
    ("great", {
        "en": "Nothing to report, which after this many weeks is itself the report.",
        "fa": "چیزی برای گزارش نیست، و بعد از این‌همه هفته، خودِ همین گزارش است.",
        "ar": "لا شيء يُذكر، وبعد كل هذه الأسابيع فإن هذا بحد ذاته هو التقرير.",
        "zh": "没什么可写的——过了这么多周，这本身就是要写的东西。",
    }),
)


_BORDERLINE: tuple[Page, ...] = (
    ("steady", {
        "en": "Fine day, bad night. I keep telling myself the weekend will sort it out.",
        "fa": "روزِ خوبی بود، شبِ بدی. مدام به خودم می‌گویم آخر هفته درستش می‌کند.",
        "ar": "نهار جيد وليلة سيئة. أظل أقول لنفسي إن عطلة الأسبوع ستصلح الأمر.",
        "zh": "白天还行，晚上糟糕。我一直告诉自己周末就能补回来。",
    }),
    ("low", {
        "en": "Deadline week. The phone is the smallest part of it, but it's the part I can actually see.",
        "fa": "هفته‌ی ددلاین است. گوشی کوچک‌ترین بخش ماجراست، ولی تنها بخشی است که می‌توانم ببینمش.",
        "ar": "أسبوع التسليم. الهاتف أصغر جزء في الأمر، لكنه الجزء الذي أستطيع رؤيته فعلًا.",
        "zh": "赶截止日期的一周。手机是里面最小的部分，但却是我唯一看得见的部分。",
    }),
    ("good", {
        "en": "Better. Left it downstairs and got seven hours for once.",
        "fa": "بهتر بود. گوشی را طبقه‌ی پایین گذاشتم و برای یک بار هم که شده هفت ساعت خوابیدم.",
        "ar": "أفضل. تركته في الطابق السفلي ونمت سبع ساعات لأول مرة منذ مدة.",
        "zh": "好一些。把手机留在楼下，难得睡了七小时。",
    }),
    ("rough", {
        "en": "Undone by one evening. Started at eleven, finished at one, and I don't remember most of what was on.",
        "fa": "یک شب همه‌چیز را خراب کرد. ساعت یازده شروع شد، یک بامداد تمام شد، و بیشترش را اصلاً به یاد ندارم.",
        "ar": "أفسدت أمسية واحدة كل شيء. بدأت في الحادية عشرة وانتهت في الواحدة، ولا أذكر معظم ما كان يُعرض.",
        "zh": "一个晚上就毁了。十一点开始，一点结束，大部分内容我根本不记得。",
    }),
    ("steady", {
        "en": "Middle of the road again. Not bad, not good, and almost exactly the same as last Tuesday.",
        "fa": "باز هم وسطِ کار. نه بد، نه خوب، و تقریباً دقیقاً مثل سه‌شنبه‌ی هفته‌ی پیش.",
        "ar": "في المنتصف مجددًا. ليس سيئًا وليس جيدًا، ويكاد يكون مطابقًا لثلاثاء الأسبوع الماضي.",
        "zh": "又是不上不下。不算差也不算好，几乎和上周二一模一样。",
    }),
    ("steady", {
        "en": "Tried the earlier night. Lay there awake anyway — but I didn't reach for the phone, so I'm counting it.",
        "fa": "زودتر خوابیدن را امتحان کردم. باز هم بیدار ماندم — ولی دستم سمت گوشی نرفت، پس به حسابش می‌گذارم.",
        "ar": "جرّبت النوم مبكرًا. بقيت مستيقظًا رغم ذلك — لكنني لم أمدّ يدي إلى الهاتف، لذا سأحتسبها.",
        "zh": "试着早点睡。还是躺着睡不着——但我没去摸手机，就算它一次。",
    }),
    ("good", {
        "en": "Work calmed down and everything else moved with it. That's the pattern, apparently.",
        "fa": "کار که آرام شد، بقیه‌ی چیزها هم با آن جابه‌جا شدند. ظاهراً الگو همین است.",
        "ar": "هدأ العمل فتحرّك كل شيء آخر معه. يبدو أن هذا هو النمط.",
        "zh": "工作一缓下来，其他都跟着变了。看来这就是规律。",
    }),
    ("good", {
        "en": "Steady week for once. I'd like to know whether that's me or just the deadline being over.",
        "fa": "برای یک بار هم که شده هفته‌ی باثباتی بود. دوست دارم بدانم این خودِ من بودم یا فقط تمام‌شدن ددلاین.",
        "ar": "أسبوع مستقر لمرة واحدة. أودّ أن أعرف إن كان هذا أنا أم مجرد انتهاء الموعد النهائي.",
        "zh": "难得一个平稳的星期。我想知道这是因为我，还是只是因为截止日过去了。",
    }),
)


_AT_RISK: tuple[Page, ...] = (
    ("low", {
        "en": "Late again. Told myself \"one more episode\" about four times.",
        "fa": "باز هم دیر. حدود چهار بار به خودم گفتم «فقط یک قسمت دیگر».",
        "ar": "تأخرت مجددًا. قلت لنفسي «حلقة أخيرة» أربع مرات تقريبًا.",
        "zh": "又熬夜了。「再看一集」这句话我说了大概四遍。",
    }),
    ("low", {
        "en": "Missed lunch, ate at the desk, didn't leave the flat. Screen from nine in the morning until whenever this was.",
        "fa": "ناهار را از دست دادم، پشت میز خوردم، از خانه بیرون نرفتم. از نه صبح تا هر ساعتی که الان است، پای صفحه.",
        "ar": "فوّت الغداء، أكلت أمام المكتب، ولم أغادر الشقة. شاشة من التاسعة صباحًا حتى هذه اللحظة أيًا كانت.",
        "zh": "没吃午饭，在桌前解决，一整天没出门。从早上九点到现在，一直对着屏幕。",
    }),
    ("rough", {
        "en": "Woke up tired, went to bed tired, and the middle was a blur of notifications.",
        "fa": "خسته بیدار شدم، خسته خوابیدم، و وسطش چیزی جز هجوم اعلان‌ها نبود.",
        "ar": "استيقظت متعبًا ونمت متعبًا، وما بينهما كان ضبابًا من الإشعارات.",
        "zh": "醒来是累的，睡下也是累的，中间只剩一团通知。",
    }),
    ("rough", {
        "en": "Not sleeping. Not really trying to, either.",
        "fa": "نمی‌خوابم. راستش خیلی هم تلاش نمی‌کنم.",
        "ar": "لا أنام. ولا أحاول فعلًا أن أنام.",
        "zh": "睡不着。其实也没怎么试着去睡。",
    }),
    ("low", {
        "en": "Everything is switched on and everything is buzzing, and I haven't turned a single one of them off.",
        "fa": "همه‌چیز روشن است و همه‌چیز می‌لرزد، و من حتی یکی‌شان را هم خاموش نکرده‌ام.",
        "ar": "كل شيء مُشغَّل وكل شيء يهتز، ولم أُطفئ ولا واحدًا منها.",
        "zh": "所有东西都开着，所有东西都在震，而我一个都没关。",
    }),
    ("rough", {
        "en": "Skipped the walk again. Third day. Writing it down so I have to look at it.",
        "fa": "باز هم پیاده‌روی را نرفتم. روز سوم. می‌نویسمش تا مجبور باشم نگاهش کنم.",
        "ar": "تخطيت المشي مجددًا. اليوم الثالث. أكتبها لأضطر إلى النظر إليها.",
        "zh": "又没去散步。第三天了。写下来，好让自己不得不看着它。",
    }),
    ("rough", {
        "en": "Bad week. I'm writing this at three in the morning, which tells you most of what you need to know.",
        "fa": "هفته‌ی بدی بود. این را ساعت سه بامداد می‌نویسم، که تقریباً همه‌چیز را می‌گوید.",
        "ar": "أسبوع سيئ. أكتب هذا في الثالثة فجرًا، وهذا يخبرك بمعظم ما تحتاج معرفته.",
        "zh": "糟糕的一周。我是凌晨三点写的这段，这句话本身就说明了大半。",
    }),
    ("low", {
        "en": "I already know what the numbers are going to say. Logging it anyway — that's the only part of this I'm doing right.",
        "fa": "از قبل می‌دانم اعداد چه خواهند گفت. باز هم ثبتش می‌کنم — تنها کاری که درست انجام می‌دهم همین است.",
        "ar": "أعرف مسبقًا ما ستقوله الأرقام. أسجّلها على أي حال — وهذا الجزء الوحيد الذي أفعله بشكل صحيح.",
        "zh": "我已经知道数字会怎么说了。还是记下来——这是我唯一做对的部分。",
    }),
)


PAGES: dict[str, tuple[Page, ...]] = {
    "improving": _IMPROVING,
    "healthy": _HEALTHY,
    "borderline": _BORDERLINE,
    "at_risk": _AT_RISK,
}


def pages_for(profile: str) -> tuple[Page, ...]:
    """The staged book for one profile, oldest page first."""
    return PAGES.get(profile) or PAGES["improving"]


def as_page(entry: Page) -> dict[str, Any]:
    """One page in the shape JournalService.save_many expects."""
    mood, text = entry
    return {"mood": mood, "text_i18n": dict(text), "text": text["en"]}
