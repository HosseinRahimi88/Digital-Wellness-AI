/*
  Guide content for what changed in this pass.

  The guide has to grow with the app: a feature that arrives without a
  line here is a feature the guide goes quiet on, and a guide that is
  present everywhere except the newest thing is worse than one that is
  consistently sparse - the silence lands exactly where the user has the
  most questions.
*/
(function () {
  if (!window.DWGuide || !window.DWGuide.register) return;

  window.DWGuide.register({
    demo_mode_picker: {
      face: 'good',
      priority: 40,
      en: "Sixteen demos, not one: four lengths and four stories. The important part is that a demo runs in its OWN account - your real history is not touched, not added to, and leaving the demo deletes everything it made. Pick 'At risk' if you want to see what this app says to someone whose week is going badly; that is the honest half most demos hide.",
      fa: "شانزده دمو، نه یکی: چهار طول و چهار داستان. نکته‌ی مهم این است که دمو در حساب جداگانه‌ی خودش اجرا می‌شود — به تاریخچه‌ی واقعی‌ات دست نمی‌خورد، چیزی به آن اضافه نمی‌شود، و با خروج از دمو هرچه ساخته پاک می‌شود. اگر می‌خواهی ببینی این برنامه به کسی که هفته‌اش بد پیش رفته چه می‌گوید، «در معرض خطر» را انتخاب کن؛ این همان نیمه‌ی صادقانه‌ای است که بیشتر دموها پنهانش می‌کنند.",
      ar: "ستة عشر عرضاً لا واحد: أربعة أطوال وأربع قصص. المهم أن العرض يعمل في حسابه الخاص — لا يُمسّ سجلّك الحقيقي ولا يُضاف إليه، ومغادرة العرض تحذف كل ما أنشأه. اختر «في خطر» لترى ما يقوله التطبيق لمن كان أسبوعه سيئاً؛ هذا هو النصف الصادق الذي تخفيه معظم العروض.",
      zh: "十六个演示，而不是一个：四种长度乘四个故事。要紧的是演示运行在它自己的账号里——你真实的历史不会被碰、不会被追加，退出演示会删掉它创建的一切。想看看这个应用对一个过得很糟的人说什么，就选「有风险」；那正是大多数演示会藏起来的诚实的一半。",
    },

    demo_banner: {
      face: 'thinking',
      priority: 46,
      en: "This bar means you are inside a demo account, not your own. Everything you see is generated - real model scores on invented days. Your own check-ins are somewhere else entirely and are not affected by anything you do in here. Press 'Leave demo' and you are back, with the demo deleted behind you.",
      fa: "این نوار یعنی داخل یک حساب نمایشی هستی، نه حساب خودت. هرچه می‌بینی ساخته شده — امتیازهای واقعی مدل روی روزهای ساختگی. ثبت‌های خودت کاملاً جای دیگری هستند و هیچ کاری که اینجا بکنی رویشان اثر ندارد. «خروج از دمو» را بزن تا برگردی، و دمو پشت سرت پاک می‌شود.",
      ar: "هذا الشريط يعني أنك داخل حساب تجريبي لا حسابك. كل ما تراه مُولَّد — درجات حقيقية من النموذج على أيام مُختلَقة. تسجيلاتك أنت في مكان آخر تماماً ولا يؤثر عليها شيء تفعله هنا. اضغط «مغادرة العرض» لتعود، ويُحذف العرض خلفك.",
      zh: "这条横幅表示你正在一个演示账号里，而不是你自己的账号。你看到的一切都是生成的——真实的模型分数，配上虚构的日子。你自己的记录在完全另一个地方，你在这里做的任何事都不会影响它们。按「退出演示」就能回去，演示会在你身后被删除。",
    },

    coach_threads: {
      face: 'good',
      priority: 42,
      en: "Your conversations with the coach are saved now, and each one keeps its own thread - 'why is my score down' does not have to share a scrollback with 'help me sleep'. Rename any of them to something you will recognise later. They live in this browser only: the coach answers from your own numbers, so the conversation is as personal as the check-ins behind it and has no reason to sit on a server.",
      fa: "گفتگوهایت با مربی حالا ذخیره می‌شوند و هرکدام رشته‌ی خودش را دارد — «چرا امتیازم پایین آمده» مجبور نیست با «کمکم کن بخوابم» در یک صفحه باشد. هرکدام را می‌توانی به اسمی که بعداً بشناسی تغییر بدهی. فقط در همین مرورگر می‌مانند: مربی از اعداد خودت جواب می‌دهد، پس گفتگو به همان اندازه‌ی ثبت‌های پشتش شخصی است و دلیلی ندارد روی سروری بنشیند.",
      ar: "محادثاتك مع المدرّب صارت محفوظة، ولكل واحدة خيطها الخاص — «لماذا انخفضت درجتي» ليست مضطرة لمشاركة الشاشة مع «ساعدني على النوم». أعد تسمية أي منها بما تتعرّف عليه لاحقاً. تبقى في هذا المتصفّح وحده: المدرّب يجيب من أرقامك أنت، فالمحادثة شخصية بقدر التسجيلات خلفها ولا سبب لوضعها على خادم.",
      zh: "你和教练的对话现在会被保存，而且每一段都有自己的线索——「我的分数为什么下降」不必和「帮我睡个好觉」挤在同一段记录里。你可以把任何一段改成以后认得出的名字。它们只存在这个浏览器里：教练是根据你自己的数字作答的，所以对话和它背后的记录一样私人，没有理由放到服务器上。",
    },

    league_invite_code: {
      face: 'neutral',
      priority: 40,
      en: "This code is how someone adds you, and it is the only way - there is no directory here and nobody can find you by name or email. Share it with a person you actually want in your league, and remember that giving it out is only step one: they still have to send a request and you still have to approve it and choose what they see.",
      fa: "این کد راهی است که کسی تو را اضافه می‌کند، و تنها راه است — اینجا فهرستی وجود ندارد و هیچ‌کس نمی‌تواند با نام یا ایمیل پیدایت کند. آن را با کسی که واقعاً می‌خواهی در لیگت باشد به اشتراک بگذار، و یادت باشد دادنش فقط قدم اول است: او هنوز باید درخواست بفرستد و تو هنوز باید تأیید کنی و انتخاب کنی چه چیزی ببیند.",
      ar: "هذا الرمز هو كيف يضيفك أحدهم، وهو الطريقة الوحيدة — لا يوجد دليل هنا ولا يستطيع أحد إيجادك بالاسم أو البريد. شاركه مع شخص تريده فعلاً في دوريك، وتذكّر أن إعطاءه ليس إلا الخطوة الأولى: عليه أن يرسل طلباً وعليك أن توافق وتختار ما يراه.",
      zh: "这个邀请码是别人加你的方式，也是唯一的方式——这里没有名录，没人能靠姓名或邮箱找到你。把它分享给你真心想加入联赛的人，并且记住：给出邀请码只是第一步，对方仍要发送请求，你仍要批准并选择他能看到什么。",
    },

    league_sent: {
      face: 'thinking',
      priority: 36,
      en: "Requests you have sent and nobody has answered yet. Nothing is shared while a request sits here - the other person sees only that you asked, and your figures stay yours until they accept and you both pick what to share. A request that stays unanswered simply expires into nothing.",
      fa: "درخواست‌هایی که فرستاده‌ای و هنوز کسی جوابشان را نداده. تا وقتی درخواستی اینجاست هیچ‌چیز به اشتراک گذاشته نمی‌شود — طرف مقابل فقط می‌بیند که پرسیده‌ای، و اعدادت تا وقتی او بپذیرد و هر دو انتخاب کنید چه چیزی به اشتراک بگذارید، مال خودت می‌مانند. درخواستی که بی‌جواب بماند، بی‌سروصدا منقضی می‌شود.",
      ar: "طلبات أرسلتها ولم يجب عنها أحد بعد. لا شيء يُشارَك بينما الطلب هنا — الطرف الآخر يرى فقط أنك سألت، وأرقامك تبقى لك حتى يقبل وتختارا معاً ما تتشاركانه. الطلب الذي يبقى بلا جواب ينتهي ببساطة إلى لا شيء.",
      zh: "你已发出、还没有人回应的请求。请求停在这里时不会共享任何东西——对方只看到你发出了请求，而你的数字仍然属于你，直到对方接受、并且你们双方各自选择要共享什么。一直没人回应的请求就会自然失效。",
    },

    league_connections: {
      face: 'neutral',
      priority: 38,
      en: "Everyone currently connected to you, and exactly what each of them can see. Change it whenever you like, or revoke someone entirely - revoking takes effect in the data itself, not just in this list, so a revoked friend stops receiving your figures immediately and their chat with you closes with it.",
      fa: "همه‌ی کسانی که الان به تو وصل‌اند، و دقیقاً اینکه هرکدام چه چیزی می‌بیند. هر وقت خواستی عوضش کن، یا کسی را کاملاً لغو کن — لغو در خودِ داده اعمال می‌شود نه فقط در این فهرست، پس دوستِ لغو‌شده بلافاصله دیگر اعداد تو را دریافت نمی‌کند و گفتگویش با تو هم با آن بسته می‌شود.",
      ar: "كل من هو متصل بك الآن، وما يستطيع كل منهم رؤيته بالضبط. غيّره متى شئت، أو ألغِ وصول أحدهم كلياً — الإلغاء يسري في البيانات نفسها لا في هذه القائمة فقط، فالصديق الملغى يتوقف فوراً عن تلقي أرقامك وتُغلق محادثته معك معه.",
      zh: "当前和你相连的每一个人，以及他们各自到底能看到什么。你随时可以更改，或者彻底撤销某个人——撤销作用于数据本身，而不只是这个列表，所以被撤销的好友会立即停止收到你的数字，你们之间的对话也会随之关闭。",
    },

    league_new_chat_dialog: {
      face: 'good',
      priority: 44,
      en: "This little box is asking for a name for the conversation - nothing more, and nothing is wrong. For a group it is the group's name; for a one-to-one chat it is just a label so you can find the thread again later. You can rename it at any time from the conversation list, and leaving it as it is works fine too.",
      fa: "این کادر کوچک فقط دارد یک نام برای گفتگو می‌خواهد — نه بیشتر، و هیچ چیز خراب نیست. برای گروه، نام گروه است؛ برای گفتگوی دونفره فقط یک برچسب است تا بعداً بتوانی رشته را پیدا کنی. هر وقت خواستی می‌توانی از فهرست گفتگوها اسمش را عوض کنی، و همان‌طور که هست رها کردنش هم اشکالی ندارد.",
      ar: "هذا المربّع الصغير يطلب اسماً للمحادثة — لا أكثر، ولا شيء معطّل. للمجموعة هو اسم المجموعة؛ ولمحادثة ثنائية هو مجرّد تسمية تجد بها الخيط لاحقاً. يمكنك إعادة تسميته في أي وقت من قائمة المحادثات، وتركه كما هو يعمل أيضاً.",
      zh: "这个小方框只是在问这段对话叫什么名字——仅此而已，没有任何东西出错。对群聊来说它是群名；对一对一的聊天来说，它只是一个标签，方便你以后找回这段对话。你随时可以在对话列表里重命名它，就这样放着也完全没问题。",
    },
  });
})();
