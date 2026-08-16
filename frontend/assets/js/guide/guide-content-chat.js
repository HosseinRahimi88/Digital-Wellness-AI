/*
  Guide content for League chat (D-1), shipped with the feature (B-5).

  What a user actually wants to know before typing into a chat inside a
  wellness app is not how to send a message. It is who can see this, and
  what happens when I stop wanting someone to.
*/
(function () {
  if (!window.DWGuide || !window.DWGuide.register) return;

  window.DWGuide.register({
    league_chat: {
      face: 'good',
      priority: 56,
      en: "A private conversation with someone who accepted you, and group chats you make from those same people. Three things worth knowing before you type. Only members can read a conversation - knowing its address is worth nothing on its own, and every single read and write is checked against who you are right now, not who you were when it opened. Removing a friend closes the chat in the same moment it removes the data sharing; there is no window where they still have the thread. And blocking works both ways at once: neither of you can read or write until it is undone. None of your scores or check-ins are ever attached to a message - if you want to share a number here, you have to type it yourself.",
      fa: "یک گفتگوی خصوصی با کسی که تو را پذیرفته، و گروه‌هایی که از میان همان آدم‌ها می‌سازی. سه چیز پیش از تایپ‌کردن ارزش دانستن دارد. فقط اعضا می‌توانند یک گفتگو را بخوانند — دانستن نشانی‌اش به‌تنهایی هیچ ارزشی ندارد، و هر خواندن و نوشتن در برابر این سنجیده می‌شود که همین حالا که هستی، نه آنکه موقع باز شدنش بودی. حذف یک دوست، در همان لحظه‌ای که اشتراک داده را قطع می‌کند گفتگو را هم می‌بندد؛ هیچ فاصله‌ای نیست که او هنوز رشته را داشته باشد. و مسدودکردن هم‌زمان از هر دو طرف کار می‌کند: تا وقتی برنگردانی، هیچ‌کدامتان نمی‌توانید بخوانید یا بنویسید. هیچ امتیاز یا بررسی‌ای هرگز به پیامی چسبانده نمی‌شود — اگر بخواهی عددی را اینجا به اشتراک بگذاری، باید خودت تایپش کنی.",
      ar: "محادثة خاصة مع شخص قَبِلك، ومجموعات تصنعها من الأشخاص أنفسهم. ثلاثة أمور تستحق المعرفة قبل أن تكتب. الأعضاء وحدهم يقرأون المحادثة — معرفة عنوانها لا تساوي شيئاً بذاتها، وكل قراءة وكتابة تُفحص مقابل من أنت الآن، لا من كنت حين فُتحت. وإزالة صديق تُغلق المحادثة في اللحظة نفسها التي تُنهي فيها مشاركة البيانات؛ لا توجد فترة يبقى فيها الخيط لديه. والحظر يعمل في الاتجاهين معاً: لا أحد منكما يقرأ أو يكتب حتى يُلغى. ولا تُرفق أي من درجاتك أو تسجيلاتك برسالة أبداً — إن أردت مشاركة رقم هنا، فعليك كتابته بنفسك.",
      zh: "与接受了你的人进行的私密对话，以及你从这些人中组建的群聊。在你开始打字之前，有三件事值得知道。只有成员能读一段对话——单知道它的地址毫无价值，而且每一次读和写都会按你此刻的身份来核验，而不是按对话打开时你的身份。移除一位好友，会在切断数据共享的同一时刻关闭聊天；不存在对方还留着这条线的空档。拉黑会同时在两个方向生效：在撤销之前，你们双方都无法阅读或书写。你的任何分数或记录都绝不会附在消息上——如果你想在这里分享一个数字，得你自己打出来。",
    },
    // The two controls a reader hits first and understands least: what
    // a group actually is here, and who a rename is visible to.
    league_new_group: {
      face: 'good',
      priority: 54,
      en: "A group is made only from people who already accepted you - you cannot pull in a stranger, and nobody joins by finding a link. Give it a name you will recognise later, pick the members, and that is the whole thing. Everyone in it sees every message; there are no private replies inside a group. Anyone can leave at any time, and leaving stops both reading and writing immediately. Your scores and check-ins are never attached to anything you send here - if you want to share a number, you type it yourself.",
      fa: "گروه فقط از میان کسانی ساخته می‌شود که قبلاً تو را پذیرفته‌اند — نمی‌توانی غریبه‌ای را وارد کنی، و هیچ‌کس با پیدا کردن یک لینک عضو نمی‌شود. نامی بگذار که بعداً بشناسی‌اش، اعضا را انتخاب کن، و همین. هرکسی که در گروه است همه‌ی پیام‌ها را می‌بیند؛ پاسخ خصوصی داخل گروه وجود ندارد. هرکسی هر وقت بخواهد می‌تواند بیرون برود، و بیرون رفتن بلافاصله هم خواندن و هم نوشتن را قطع می‌کند. امتیازها و بررسی‌هایت هرگز به چیزی که اینجا می‌فرستی چسبانده نمی‌شوند — اگر بخواهی عددی را به اشتراک بگذاری، خودت تایپش می‌کنی.",
      ar: "تُصنع المجموعة فقط ممن قَبِلوك من قبل — لا يمكنك إدخال غريب، ولا ينضم أحد بالعثور على رابط. أعطها اسماً تتعرّف عليه لاحقاً، واختر الأعضاء، وهذا كل شيء. كل من فيها يرى كل رسالة؛ لا توجد ردود خاصة داخل المجموعة. يمكن لأي شخص المغادرة في أي وقت، والمغادرة توقف القراءة والكتابة فوراً. ولا تُرفق درجاتك ولا تسجيلاتك بأي شيء ترسله هنا — إن أردت مشاركة رقم، فاكتبه بنفسك.",
      zh: "群组只能由已经接受了你的人组成——你无法拉进陌生人，也没有人能靠找到链接加入。起一个你以后认得出的名字，选好成员，就这么简单。群里的每个人都能看到每条消息；群内没有私密回复。任何人随时都可以退出，退出会立刻同时停止阅读和书写。你的分数和记录绝不会附在你在这里发送的任何内容上——想分享数字的话，得你自己打出来。",
    },
    league_chat_rename: {
      face: 'neutral',
      priority: 53,
      en: "Renaming is for you to find the thread again - four rows all called the same thing is a list nobody can navigate. One thing to know before you use it: the name is shared, not private. Everyone in the conversation sees whatever you set, including the person on the other side of a direct chat. That is deliberate - two people calling the same thread different names is worse than neither of them being able to rename it. It changes the label only; no message, and nothing about who can read what, is affected.",
      fa: "تغییر نام برای این است که خودت دوباره رشته را پیدا کنی — چهار ردیف که همه یک اسم دارند فهرستی است که هیچ‌کس نمی‌تواند در آن بگردد. یک چیز را پیش از استفاده بدان: این نام مشترک است، نه خصوصی. همه‌ی کسانی که در گفتگو هستند هر چه بگذاری می‌بینند، از جمله طرف مقابلِ یک گفتگوی مستقیم. این عمدی است — اینکه دو نفر یک رشته را به دو اسم صدا کنند بدتر از این است که هیچ‌کدام نتوانند نامش را عوض کنند. فقط برچسب عوض می‌شود؛ نه پیامی، و نه هیچ‌چیز درباره‌ی اینکه چه کسی چه چیزی را می‌تواند بخواند.",
      ar: "إعادة التسمية كي تعثر أنت على المحادثة لاحقاً — أربعة صفوف بالاسم نفسه قائمة لا يستطيع أحد تصفّحها. اعرف أمراً قبل أن تستخدمها: الاسم مشترك، لا خاص. كل من في المحادثة يرى ما تضعه، بمن فيهم الطرف الآخر في محادثة مباشرة. وهذا مقصود — أن يسمّي شخصان المحادثة نفسها باسمين مختلفين أسوأ من ألا يستطيع أيٌّ منهما تسميتها. يتغيّر العنوان وحده؛ لا رسالة تتأثر، ولا شيء يتعلق بمن يقرأ ماذا.",
      zh: "重命名是为了让你以后能重新找到这段对话——四行都叫同一个名字的列表，没人能用。使用前要知道一点：这个名字是共享的，不是私密的。对话中的每个人都会看到你设定的名字，包括私聊里的另一方。这是有意为之——两个人用不同的名字称呼同一段对话，比谁都不能改名更糟。它只改变标签；不影响任何消息，也不影响谁能读到什么。",
    },
  });
})();
