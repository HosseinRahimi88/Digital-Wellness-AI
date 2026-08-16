/*
  Guide content for the badge features (C-3, D-2), registered through
  DWGuide.register() so it ships with the feature rather than as a later
  editing pass on guide-tips.js (B-5).

  Per-badge explanations are NOT here on purpose: there are 63 of them
  and each one has to quote the user's own numbers, so they are composed
  at click time by DWBadgeText.speech() from the badge registry. These
  entries explain the two surfaces.
*/
(function () {
  if (!window.DWGuide || !window.DWGuide.register) return;

  window.DWGuide.register({
    hall_of_fame: {
      face: 'great',
      priority: 58,
      en: "This wall is your own history, sorted by how hard each thing is to reach. Every badge here has a criterion I actually compute from your check-ins - nothing unlocks just for showing up and looking at it. The blurred ones are not things you failed; they are the ones your data has not answered yet, and some of them need two full weeks before I can even tell. Click any badge and I'll say what it is, exactly how it is earned, and where you currently stand.",
      fa: "این دیوار، سابقه‌ی خودت است، مرتب‌شده بر اساس اینکه رسیدن به هرکدام چقدر سخت است. هر نشانی که اینجاست معیاری دارد که واقعاً از بررسی‌های تو حساب می‌کنم — هیچ‌چیز فقط با سر زدن و نگاه کردن باز نمی‌شود. آن‌های محو، چیزهایی نیستند که در آن‌ها شکست خورده باشی؛ آن‌هایی‌اند که داده‌ات هنوز جوابشان را نداده، و بعضی‌شان دو هفته‌ی کامل لازم دارند تا اصلاً بتوانم بگویم. روی هر نشان کلیک کن تا بگویم چیست، دقیقاً چطور به دست می‌آید، و الان کجای کاری.",
      ar: "هذا الجدار هو سجلك أنت، مرتباً حسب صعوبة الوصول إلى كل شيء فيه. كل وسام هنا له معيار أحسبه فعلاً من تسجيلاتك — لا شيء يُفتح لمجرد المرور والنظر. المطموسة ليست أشياء أخفقت فيها؛ بل تلك التي لم تجب عنها بياناتك بعد، وبعضها يحتاج أسبوعين كاملين قبل أن أستطيع الحكم أصلاً. انقر أي وسام وسأقول لك ما هو، وكيف يُكتسب بالضبط، وأين تقف الآن.",
      zh: "这面墙就是你自己的历史，按照每一项有多难达成来排列。这里的每一枚徽章都有一个我真正从你的记录里算出来的标准——没有任何东西会因为你来看一眼就解锁。那些模糊的并不是你失败的东西；它们是你的数据还没能回答的，其中有些需要整整两周我才说得准。点任意一枚徽章，我会告诉你它是什么、究竟怎样获得，以及你现在到了哪里。",
    },

    awareness_indicators: {
      face: 'thinking',
      priority: 57,
      en: "This part is private, and it stays private - it is never sent to the league, never on a share card, and the server does not even include it in the list your friends' side can request. Each one names a pattern in your recent days and nothing more: a description, not a judgement, and never a diagnosis. Each comes with one concrete step, because pointing at something and walking away would be the least useful thing I could do. If nothing is listed, nothing stood out.",
      fa: "این بخش خصوصی است و خصوصی می‌ماند — هرگز به لیگ فرستاده نمی‌شود، هرگز روی کارت اشتراک‌گذاری نمی‌آید، و سرور اصلاً آن را در فهرستی که سمت دوستانت می‌تواند بخواهد نمی‌گذارد. هرکدام فقط الگویی در روزهای اخیرت را نام می‌برد و بس: یک توصیف، نه یک قضاوت، و هرگز یک تشخیص. هرکدام یک قدم مشخص همراه دارد، چون اشاره‌کردن به چیزی و رفتن، بی‌فایده‌ترین کاری است که می‌توانستم بکنم. اگر چیزی فهرست نشده، یعنی چیزی برجسته نبوده.",
      ar: "هذا الجزء خاص، ويبقى خاصاً — لا يُرسل إلى الدوري أبداً، ولا يظهر على بطاقة مشاركة، والخادم لا يضعه أصلاً في القائمة التي يستطيع جانب أصدقائك طلبها. كل عنصر يسمّي نمطاً في أيامك الأخيرة ولا شيء أكثر: وصف، لا حكم، ولا تشخيص أبداً. ويأتي كل منها بخطوة ملموسة، لأن الإشارة إلى شيء ثم الانصراف أقل ما يمكنني فعله نفعاً. وإن لم يُدرَج شيء، فلم يبرز شيء.",
      zh: "这一部分是私密的，而且会一直保持私密——它绝不会被发送到排行榜，绝不会出现在分享卡片上，服务器甚至不会把它放进你好友那边能够请求的列表里。每一条只是命名你最近这些天里的一个模式，仅此而已：是描述，不是评判，更绝不是诊断。每一条都带着一个具体的步骤，因为指出一件事然后走开，是我能做的最没用的事。如果这里什么都没有列出，那就是没有什么特别突出的。",
    },
  });
})();
