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
      key: 'sleep_debt',
      match: /\b(sleep debt|catch up on sleep|oversleep(ing)? (on )?weekend|sleep in on weekends|make up for lost sleep)(?:s|es|ing)?\b|بدهی خواب|جبران خواب آخر هفته|زیاد خوابیدن آخر هفته|دين النوم|تعويض النوم|نوم في نهاية الأسبوع|أنام متأخرا في العطلة|睡眠债|补觉|周末补眠|睡眠不足补回/i,
      en: "Sleeping in on weekends to 'pay back' a short week doesn't fully undo it — it shifts your body clock instead, which is why Monday can feel worse than the week that caused it. The steadier fix is smaller and less satisfying to hear: keep wake-up time within about an hour of your weekday time, even on weekends, and let bedtime be the thing that moves instead. Consistency tends to matter more than any single night's total.",
      fa: "زیاد خوابیدن در آخر هفته برای «جبران» یک هفته‌ی کم‌خواب واقعاً آن را جبران نمی‌کند — بیشتر ساعت بدن را جابه‌جا می‌کند، برای همین دوشنبه گاهی از خودِ هفته‌ای که باعثش شد بدتر حس می‌شود. راه‌حل پایدارتر کمتر هیجان‌انگیز است: ساعت بیدارشدن را حتی آخر هفته‌ها نزدیک به ساعت روزهای هفته نگه دار، و بگذار ساعت خواب باشد که جابه‌جا می‌شود. ثبات معمولاً از مجموع خواب یک شب مهم‌تر است.",
      ar: "النوم لوقت متأخر في نهاية الأسبوع لتعويض أسبوع قصير لا يمحو أثره تماما — بل يزحزح ساعتك البيولوجية، ولهذا قد يكون يوم الاثنين أسوأ من الأسبوع الذي سبّبه. الحل الأكثر ثباتا أصغر وأقل إمتاعا عند سماعه: أبقِ وقت الاستيقاظ في حدود ساعة من وقتك في أيام العمل، حتى في العطلة. إن كنت بحاجة للتعويض، فالقيلولة القصيرة المبكرة في النهار تكلّف ساعتك البيولوجية أقل بكثير من النوم حتى الظهر.",
      zh: "周末睡到很晚来偿还睡不够的一周，并不能完全抵消它——反而会推移你的生物钟，这就是为什么星期一可能比造成它的那一周更难受。更稳妥的办法听起来更小也更没意思：把起床时间控制在工作日起床时间的一小时之内，周末也一样。如果确实需要补，白天早些时候的短暂小睡对生物钟的代价，远小于一觉睡到中午。",
    },
    {
      key: 'morning_routine',
      match: /\b(morning routine|first thing.*morning|check(ing)? (my )?phone.*wake up|wake up.*check.*phone)(?:s|es|ing)?\b|روتین صبح|صبح اول گوشی|بیدارشدن و چک‌کردن گوشی|روتين الصباح|أول شيء في الصباح|أتحقق من هاتفي عند الاستيقاظ|هاتف بعد الاستيقاظ|早晨习惯|早上第一件事|起床就看手机|晨间流程/i,
      en: "Reaching for the phone the instant you wake up hands the first minutes of your day's attention to whatever is waiting in the notification list, before you've decided anything for yourself. A short, deliberately boring buffer — even just getting up and getting dressed before the first check — tends to change the tone of the whole morning more than the buffer's length would suggest.",
      fa: "برداشتن گوشی درست لحظه‌ی بیدارشدن، اولین دقایق توجه روزت را به هرچیزی که در فهرست اعلان‌ها منتظر است می‌سپارد، قبل از اینکه چیزی را خودت تصمیم بگیری. یک فاصله‌ی کوتاه و عمداً کسل‌کننده — حتی فقط بلندشدن و لباس‌پوشیدن قبل از اولین چک — معمولاً بیشتر از طول‌مدتش لحن کل صبح را تغییر می‌دهد.",
      ar: "الوصول إلى الهاتف في اللحظة التي تستيقظ فيها يسلّم أول دقائق من انتباه يومك إلى ما ينتظر في قائمة الإشعارات، قبل أن تقرر أنت أي شيء لنفسك. الفاصل القصير المُمِل بشكل متعمد — حتى مجرد النهوض وتغيير ملابسك قبل أول تحقق — يرتبط عادة بشعور أهدأ ببداية اليوم. ليست القاعدة أن الصباح مقدس، بل أن أول قرار في اليوم يُفضّل أن يكون قرارك أنت.",
      zh: "一醒来就伸手拿手机，等于把一天中最初几分钟的注意力交给通知列表里等着你的东西，而你还没为自己决定任何事。一段短暂、刻意无聊的缓冲——哪怕只是起床穿好衣服再看第一眼——通常与更平静的一天开端相关。规则不是早晨很神圣，而是一天中的第一个决定最好由你自己做出。",
    },
    {
      key: 'sleep',
      match: /\b(sleep|sleeping|insomnia|bedtime|rest|tired|nap|wake up|awake at night)(?:s|es|ing)?\b|خواب|بی‌خوابی|بیدار|نوم|أنام|أرق|موعد النوم|مستيقظ في الليل|تعبان|قيلولة|睡眠|睡觉|失眠|就寝|夜里醒|困|小睡/i,
      en: "Sleep is one of the strongest signals in this whole model. Two things move it most: consistency (same sleep and wake times, even at weekends) and what happens in the last hour before bed. Bright screens late in the evening are associated with a later body clock, so the practical lever is usually distance rather than willpower — charge the phone across the room, or outside the bedroom entirely. If you only change one thing this week, a fixed cut-off time for screens tends to be the one that carries the most.",
      fa: "خواب یکی از قوی‌ترین سیگنال‌های کل این مدل است. دو چیز بیشترین اثر را دارند: ثبات (ساعت خواب و بیداری یکسان، حتی آخر هفته‌ها) و آنچه در آخرین ساعت قبل از خواب اتفاق می‌افتد. نور شدید صفحه در اواخر شب با به‌تعویق‌افتادن ساعت بدن مرتبط است، پس اهرم عملی معمولاً فاصله است نه اراده — گوشی را آن‌سوی اتاق یا کلاً بیرون از اتاق خواب شارژ کن. اگر فقط یک چیز را این هفته تغییر بدهی، یک ساعت پایان مشخص برای صفحه‌نمایش معمولاً بیشترین اثر را دارد.",
      ar: "النوم من أقوى الإشارات في هذا النموذج كله. شيئان يؤثران فيه أكثر من غيرهما: الثبات (نفس وقت النوم والاستيقاظ، حتى في نهاية الأسبوع) وما يحدث في الساعة الأخيرة قبل النوم. تُربط الشاشات الساطعة في وقت متأخر من المساء بتأخر الساعة البيولوجية، لذا فإن الرافعة العملية غالبا هي المسافة لا قوة الإرادة — اشحن الهاتف في الجهة الأخرى من الغرفة، أو خارج غرفة النوم تماما. إن غيّرت شيئا واحدا هذا الأسبوع، فوقت توقف ثابت للشاشات هو عادة الأكثر أثرا.",
      zh: "睡眠是整个模型中最强的信号之一。影响它最大的有两件事：规律性（睡觉和起床时间一致，周末也一样），以及睡前最后一小时发生了什么。深夜明亮的屏幕与生物钟推迟相关，所以实际可用的杠杆通常是距离而不是意志力——把手机放到房间另一头充电，或者干脆放到卧室外面。如果这周只改一件事，为屏幕设一个固定的截止时间通常收效最大。",
    },
    {
      key: 'focus',
      match: /\b(focus|concentrat|attention|distract|deep work|productiv|procrastinat)(?:s|es|ing)?\b|تمرکز|حواس‌پرت|بهره‌وری|تعلل|تركيز|أركز|انتباه|تشتت|عمل العميق|إنتاجية|تسويف|专注|集中|注意力|分心|深度工作|生产力|拖延|拖延症|تركيز\S*\s*(سيء|ضعيف|مشتت)/i,
      en: "Attention takes real time to recover after an interruption, which is why scattered checking costs far more than the seconds it appears to. In this dataset, how *often* you pick up your device predicts focus better than total hours do. The practical move is batching: pick two or three fixed windows for messages instead of reacting instantly, and protect one 25-minute block a day with the phone in another room. Turning off notifications for your three noisiest apps — not all of them, just the loudest three — is usually the highest-leverage single change.",
      fa: "توجه بعد از هر وقفه واقعاً زمان می‌برد تا بازیابی شود؛ برای همین چک‌کردن‌های پراکنده خیلی بیشتر از چند ثانیه‌ای که به نظر می‌رسند هزینه دارند. در این داده، تعداد دفعاتی که گوشی را برمی‌داری بهتر از مجموع ساعت‌ها تمرکز را پیش‌بینی می‌کند. حرکت عملی دسته‌بندی است: دو سه بازه‌ی مشخص برای پیام‌ها انتخاب کن به‌جای واکنش آنی، و روزی یک بازه‌ی ۲۵ دقیقه‌ای را با گوشی در اتاق دیگر محافظت کن. خاموش‌کردن اعلان سه اپ پرسروصداتر — نه همه، فقط همان سه تا — معمولاً پراثرترین تغییر تکی است.",
      ar: "يحتاج الانتباه وقتا حقيقيا ليتعافى بعد المقاطعة، ولهذا يكلّف التحقق المتقطع أكثر بكثير من الثواني التي يبدو أنه يستهلكها. في هذه البيانات، عدد مرات التقاطك لجهازك يتنبأ بالتركيز أفضل من مجموع الساعات. الخطوة العملية هي التجميع: اختر نافذتين أو ثلاثا ثابتة للرسائل بدلا من التحقق المستمر، وستتحسن أرقام التفتت لديك قبل أن يتغير إجمالي وقت الشاشة.",
      zh: "注意力在被打断后需要真实的时间才能恢复，这就是为什么零散的查看，代价远大于它看起来消耗的那几秒。在这份数据中，你拿起设备的频率比总时长更能预测专注度。可行的做法是批处理：为消息设定两三个固定时段，而不是持续查看；你的碎片化指标会在总屏幕时间变化之前就先改善。",
    },
    {
      key: 'notifications',
      match: /\b(notification|alert|ping|buzz|badge|interrupt)(?:s|es|ing)?\b|اعلان|نوتیف|هشدار|إشعارات|تنبيهات|إشعار|تنبيه|مقاطعة|通知|提醒|消息提示|打扰|中断/i,
      en: "Notification volume and reported stress tend to move together across large samples. The useful framing isn't 'turn everything off' — it's that most people have two or three apps generating the large majority of interruptions. Silence those, keep the ones that genuinely need to reach you, and the density number this app tracks (notifications per hour of screen time) usually drops sharply without you missing anything that mattered.",
      fa: "حجم اعلان‌ها و میزان استرس گزارش‌شده در نمونه‌های بزرگ معمولاً هم‌جهت حرکت می‌کنند. قاب مفید «همه را خاموش کن» نیست — واقعیت این است که برای بیشتر افراد دو سه اپ اکثریت قاطع وقفه‌ها را می‌سازند. همان‌ها را ساکت کن، آن‌هایی که واقعاً باید به تو برسند را نگه دار، و عددی که این اپ ردیابی می‌کند (اعلان در هر ساعت استفاده) معمولاً به‌شدت پایین می‌آید بدون اینکه چیز مهمی را از دست بدهی.",
      ar: "يتحرك حجم الإشعارات والتوتر المُبلَّغ عنه معا عبر عينات كبيرة. الصياغة المفيدة ليست أوقف كل شيء — بل أن معظم الناس لديهم تطبيقان أو ثلاثة تولّد الأغلبية الكبرى من المقاطعات. أسكت تلك، وأبقِ ما يحتاج فعلا للوصول إليك، وتنخفض الكثافة دون أن تفقد شيئا مهما. الاختبار البسيط: بعد أسبوع، هل فاتك أي شيء فعلا؟",
      zh: "在大样本中，通知数量和自我报告的压力往往同向变动。有用的表述不是全部关掉，而是大多数人只有两三个应用产生了绝大部分打扰。把它们静音，保留真正需要触达你的，密度就会下降，而你不会错过重要的事。简单的检验：一周之后，你真的错过了什么吗？",
    },
    {
      key: 'social',
      match: /\b(social media|instagram|tiktok|twitter|scroll|feed|comparison|fomo)(?:s|es|ing)?\b|شبکه اجتماعی|اینستا|اسکرول|مقایسه|فومو|وسائل التواصل|إنستغرام|تيك توك|تويتر|تمرير|مقارنة|خوف من الفوات|社交媒体|微博|抖音|小红书|刷|刷手机|信息流|比较|错失恐惧/i,
      en: "Passive scrolling and active messaging show different associations with mood — how you use an app matters, not just how long. Social comparison is one of the more consistent signals in digital-wellbeing research, which is why this app asks about it directly. A concrete experiment: before opening a social app, name what you actually want from it. If you can't, that's genuinely useful information. Greyscale in the evening also makes feeds noticeably less magnetic.",
      fa: "اسکرول منفعل و گفتگوی فعال ارتباط متفاوتی با حال‌وهوا نشان می‌دهند — نحوه‌ی استفاده مهم است، نه فقط مدتش. مقایسه‌ی اجتماعی یکی از پایدارترین سیگنال‌ها در پژوهش‌های سلامت دیجیتال است؛ برای همین این اپ مستقیم درباره‌اش می‌پرسد. یک آزمایش مشخص: قبل از باز کردن یک اپ اجتماعی، بگو دقیقاً چه می‌خواهی. اگر نتوانستی، همین خودش اطلاعات مفیدی است. حالت سیاه‌وسفید در عصر هم فیدها را محسوس کمتر جذاب می‌کند.",
      ar: "يُظهر التمرير السلبي والمراسلة النشطة ارتباطات مختلفة بالمزاج — فطريقة استخدامك للتطبيق مهمة، لا مدته وحده. المقارنة الاجتماعية من أكثر الإشارات اتساقا في بحوث العافية الرقمية، ولهذا يسألك هذا التطبيق عنها مباشرة. تجربة ملموسة: قبل أن تفتح تطبيقا اجتماعيا، قل لنفسك لماذا تفتحه. إن لم يكن هناك سبب، فذلك بنفسه معلومة مفيدة.",
      zh: "被动刷动态和主动聊天与情绪的关联并不相同——你怎么用这个应用很重要，而不只是用了多久。社交比较是数字健康研究中较为一致的信号之一，这也是本应用直接询问它的原因。一个具体的实验：打开社交应用之前，先说出你为什么要打开它。如果说不出理由，这本身就是有用的信息。",
    },
    {
      key: 'blue_light_debate',
      match: /\b(blue light glasses|blue light filter|night shift mode|does blue light (actually |really )?matter|night mode.*screen)(?:s|es|ing)?\b|عینک نور آبی|فیلتر نور آبی|حالت شب صفحه|نظارات الضوء الأزرق|مرشح الضوء الأزرق|وضع الليلي|هل الضوء الأزرق مهم|防蓝光|蓝光眼镜|蓝光过滤|夜览模式|夜间模式有用吗/i,
      en: "Blue-light filters and glasses shift screen color, and the evidence that this alone meaningfully changes sleep is weaker and more mixed than the marketing suggests — brightness and timing appear to matter more than color temperature. They're not harmful to try, but treat them as a minor add-on, not a substitute for the thing that actually shows up strongly in the data: stopping screen use before bed rather than just tinting it.",
      fa: "فیلترها و عینک‌های نور آبی رنگ صفحه را تغییر می‌دهند، و شواهدی که این به‌تنهایی خواب را به‌طور معنادار تغییر می‌دهد ضعیف‌تر و متناقض‌تر از چیزی است که تبلیغات می‌گویند — روشنایی و زمان‌بندی به‌نظر مهم‌ترند تا دمای رنگ. امتحان‌کردنشان ضرری ندارد، اما آن را یک مکمل کوچک بدان نه جایگزین چیزی که واقعاً در داده قوی ظاهر می‌شود: متوقف‌کردن استفاده از صفحه قبل از خواب، نه فقط رنگی‌کردنش.",
      ar: "تُغيّر مرشحات الضوء الأزرق والنظارات لون الشاشة، والدليل على أن هذا وحده يغيّر النوم بشكل ذي معنى أضعف وأكثر تباينا مما يوحي به التسويق — يبدو أن السطوع والتوقيت أهم من درجة حرارة اللون. ليست مؤذية لتجربتها، لكن اعتبرها إضافة ثانوية لا حلا. الرافعتان الأقوى تبقيان: خفض السطوع، وتقديم وقت التوقف.",
      zh: "防蓝光滤镜和眼镜改变屏幕颜色，但仅凭这一点就能显著改变睡眠的证据，比营销宣传所暗示的要更弱、也更不一致——亮度和时间点看起来比色温更重要。试试无害，但把它当作次要的补充而不是解决方案。更有力的两个杠杆依然是：降低亮度，以及把停用时间提前。",
    },
    {
      key: 'night',
      match: /\b(night|late night|midnight|evening|before bed)(?:s|es|ing)?\b|شب|نیمه‌شب|قبل خواب|ليل|في وقت متأخر|منتصف الليل|مساء|قبل النوم|夜间|深夜|半夜|晚上|睡前/i,
      en: "Night-time use shows up twice in your score: directly, and again through whatever it does to your sleep. The cleanest interventions are structural rather than behavioural — a fixed screen cut-off treated like a real appointment, a charger outside the bedroom, and 'Do Not Disturb' scheduled rather than toggled manually. Anything that removes the decision works better than anything that relies on making the decision correctly at midnight.",
      fa: "استفاده‌ی شبانه دو بار در امتیازت ظاهر می‌شود: مستقیم، و دوباره از طریق اثری که بر خوابت می‌گذارد. تمیزترین مداخله‌ها ساختاری‌اند نه رفتاری — یک ساعت پایان مشخص که مثل یک قرار واقعی با آن رفتار شود، شارژر بیرون از اتاق خواب، و «مزاحم نشوید» زمان‌بندی‌شده به‌جای دستی. هر چیزی که تصمیم را حذف کند بهتر از هر چیزی است که به درست‌تصمیم‌گرفتن در نیمه‌شب تکیه دارد.",
      ar: "يظهر الاستخدام الليلي مرتين في درجتك: مباشرة، ثم مرة أخرى عبر ما يفعله بنومك. أنظف التدخلات بنيوية لا سلوكية — وقت توقف ثابت للشاشة يُعامَل كموعد حقيقي، شاحن خارج غرفة النوم، ووضع عدم الإزعاج مُجدوَل تلقائيا لا مُشغَّلا يدويا كل ليلة. الجدولة تكسب لأنها لا تحتاج أن تتذكرها في اللحظة التي تكون فيها أقل رغبة في تذكرها.",
      zh: "夜间使用在你的分数里出现了两次：一次是直接的，一次是通过它对睡眠的影响。最干净的干预是结构性的而非行为性的——把固定的屏幕截止时间当作真正的约会，把充电器放到卧室外，并让免打扰按计划自动开启，而不是每晚手动打开。计划之所以更有效，是因为它不需要你在最不想记起它的时刻记起它。",
    },
    {
      key: 'stress',
      match: /\b(stress|anxious|anxiety|overwhelm|burnout|pressure|calm|relax)(?:s|es|ing)?\b|استرس|اضطراب|فرسودگی|آرام|توتر|قلق|إرهاق|احتراق|ضغط|هدوء|استرخاء|压力|焦虑|不安|倦怠|过劳|紧张|放松|平静/i,
      en: "I can talk about the habit side of this, not the clinical side. What the data supports: notification load, fragmented attention and short sleep all tend to travel with higher reported stress, and they're the parts you can actually adjust. Short daytime movement breaks are linked with better sustained attention later in the day, which tends to take pressure off the evening. If stress is persistent or heavy, that's a conversation for a qualified professional rather than an app — I'd rather say that plainly than pretend otherwise.",
      fa: "می‌توانم درباره‌ی سمت عادت‌ها صحبت کنم، نه سمت بالینی. آنچه داده پشتیبانی می‌کند: بار اعلان‌ها، توجه تکه‌تکه و خواب کوتاه همگی با استرس گزارش‌شده‌ی بالاتر همراه‌اند، و همین‌ها بخش‌هایی هستند که واقعاً می‌توانی تنظیمشان کنی. وقفه‌های کوتاه حرکتی در طول روز با تمرکز پایدارتر در ادامه‌ی روز مرتبط‌اند، که معمولاً فشار را از روی عصر برمی‌دارد. اگر استرس پایدار یا سنگین است، آن گفتگویی برای یک متخصص واجد شرایط است نه یک اپ — ترجیح می‌دهم این را صریح بگویم.",
      ar: "أستطيع الحديث عن جانب العادات في هذا، لا الجانب العلاجي. ما تدعمه البيانات: حجم الإشعارات، وتفتت الانتباه، وقصر النوم، تسافر جميعها عادة مع توتر مُبلَّغ أعلى — وهي الأجزاء التي يمكنك فعلا تعديلها. وتُربط فترات الحركة القصيرة في النهار بانتباه أفضل استدامة. إن كان ما تشعر به أثقل من ضغط عادات — إن كان مستمرا أو يعطّل حياتك اليومية — فهذا حديث يستحق شخصا مؤهلا لا تطبيقا.",
      zh: "我可以谈习惯层面，但不能谈临床层面。数据支持的是：通知量、注意力碎片化和睡眠不足，通常都与更高的自我报告压力同行——而这些正是你真的可以调整的部分。白天短暂的活动间歇则与更持久的注意力相关。如果你感受到的东西比习惯层面的压力更沉重——如果它持续存在或影响了日常生活——那这件事值得找一位专业人士谈，而不是一个应用。",
    },
    {
      key: 'activity',
      match: /\b(exercise|activity|workout|walk|move|movement|sedentary|gym|steps)(?:s|es|ing)?\b|ورزش|فعالیت|پیاده‌روی|تحرک|حرکت|رياضة|نشاط|تمرين|مشي|حركة|قلة الحركة|خطوات|运动|锻炼|活动|散步|走路|久坐|步数|健身/i,
      en: "Physical activity is one of the few inputs here that improves several others at once — it's associated with better sleep quality and better sustained attention, so it tends to lift more than its own line in the breakdown. The bar is lower than people assume: short movement breaks during the day count, and swapping one scrolling session for a walk is the same time spent with a very different result.",
      fa: "فعالیت بدنی یکی از معدود ورودی‌هایی است که همزمان چند مورد دیگر را هم بهبود می‌دهد — با کیفیت خواب بهتر و تمرکز پایدارتر مرتبط است، پس معمولاً بیشتر از سهم خودش در تفکیک، امتیاز را بالا می‌برد. آستانه‌اش از چیزی که مردم فکر می‌کنند پایین‌تر است: وقفه‌های کوتاه حرکتی در طول روز حساب می‌شوند، و جایگزین‌کردن یک جلسه‌ی اسکرول با پیاده‌روی یعنی همان زمان با نتیجه‌ای کاملاً متفاوت.",
      ar: "النشاط البدني من المدخلات القليلة هنا التي تُحسّن عدة أمور في الوقت نفسه — يُربط بجودة نوم أفضل وانتباه أكثر استدامة، لذا يرفع أكثر من سطره الخاص في التفصيل. والحد أدنى مما يفترضه الناس: فترات الحركة القصيرة خلال النهار تُحتسب، ولا يلزم أن يكون تمرينا منظما ليظهر في بياناتك.",
      zh: "身体活动是这里少数能同时改善好几项指标的输入之一——它与更好的睡眠质量和更持久的注意力相关，所以它提升的不只是明细里自己那一行。门槛比人们以为的低：白天短暂的活动间歇也算，不必是正式的锻炼才能反映在你的数据里。",
    },
    {
      key: 'gaming',
      match: /\b(gaming|video game|video games|console|xbox|playstation|ps5|esports)(?:s|es|ing)?\b|بازی|گیم|کنسول|پلی استیشن|ایکس باکس|ألعاب|ألعاب الفيديو|كونسول|بلايستيشن|إكس بوكس|رياضات الإلكترونية|游戏|打游戏|电子游戏|主机|电竞/i,
      en: "Gaming isn't treated as inherently bad here — the data cares about pattern more than the label 'gaming'. What tends to matter is whether a session has a natural stopping point (a match ending, a level finishing) versus open-ended play with no built-in exit, and whether it's displacing sleep specifically. A concrete boundary that works for a lot of people: decide your stopping point before you start, not while you're already in it.",
      fa: "بازی‌کردن ذاتاً بد در نظر گرفته نمی‌شود — داده بیشتر به الگو اهمیت می‌دهد تا برچسب «بازی». چیزی که معمولاً مهم است این است که آیا یک جلسه نقطه‌ی پایان طبیعی دارد (تمام‌شدن یک مسابقه، تمام‌شدن یک مرحله) در برابر بازی باز بدون خروج داخلی، و اینکه آیا دقیقاً جای خواب را می‌گیرد یا نه. یک مرز مشخص که برای خیلی‌ها جواب می‌دهد: نقطه‌ی توقف را قبل از شروع تعیین کن، نه وسط بازی.",
      ar: "لا تُعامل الألعاب هنا كشيء سيئ بطبيعته — تهتم البيانات بالنمط أكثر من التسمية. ما يهم عادة هو ما إذا كانت الجلسة لها نقطة توقف طبيعية (نهاية مباراة، إكمال مرحلة) مقابل لعب مفتوح بلا مخرج مبني فيه، وما إذا كانت تزحزح النوم تحديدا. جلسة مسائية بحد واضح تختلف في البيانات عن جلسة تمتد إلى ما بعد وقت نومك.",
      zh: "这里并不把游戏当作本身就不好的事——数据关心的是模式，而不是游戏这个标签。通常重要的是：这一局有没有自然的停止点（一场结束、一关通过），还是没有内建出口的开放式游玩；以及它是否具体挤占了睡眠。一个有清晰上限的晚间游戏时段，在数据上与一路玩到超过你就寝时间的时段是不同的。",
    },
    {
      key: 'streaming',
      match: /\b(netflix|streaming|binge.?watch|youtube|watch video|video hours)(?:s|es|ing)?\b|نتفلیکس|استریم|دیدن ویدیو|یوتیوب|نتفليكس|البث|مشاهدة متواصلة|يوتيوب|مشاهدة الفيديو|视频|追剧|刷剧|一口气看完|优酷|B站|看视频/i,
      en: "Streaming and binge-watching are usually low-interaction, low-social-comparison ways to spend screen time — genuinely less associated with the stress signal than scrolling social feeds tends to be. The thing worth watching for is autoplay: it removes the natural stopping point a single episode used to have, so it's the mechanism, not the content, that quietly extends a session past where you meant to stop.",
      fa: "استریم و دیدن پشت‌سرهم اپیزودها معمولاً روش‌هایی با تعامل کم و مقایسه‌ی اجتماعی کم برای گذراندن زمان صفحه‌اند — واقعاً کمتر از اسکرول فیدهای اجتماعی با سیگنال استرس مرتبط‌اند. چیزی که ارزش توجه دارد پخش خودکار است: نقطه‌ی توقف طبیعی که هر اپیزود قبلاً داشت را حذف می‌کند، پس این مکانیزم است نه محتوا که بی‌سروصدا یک جلسه را از جایی که می‌خواستی متوقف شوی جلوتر می‌برد.",
      ar: "البث والمشاهدة المتواصلة عادة طرق منخفضة التفاعل ومنخفضة المقارنة الاجتماعية لإنفاق وقت الشاشة — وترتبط فعلا بإشارة التوتر أقل مما يرتبط تمرير الشبكات الاجتماعية. الشيء الجدير بالمراقبة هو التشغيل التلقائي: فهو يزيل نقطة التوقف الطبيعية التي كانت نهاية الحلقة توفرها. إيقاف التشغيل التلقائي يعيد إليك القرار.",
      zh: "看流媒体和追剧通常是低互动、低社交比较的屏幕时间消耗方式——它与压力信号的关联，确实比刷社交动态要弱。值得留意的是自动播放：它取消了一集结束原本提供的自然停止点。关掉自动播放，就把决定权还给了你。",
    },
    {
      key: 'eye_strain',
      match: /\b(eye ?strain|eyes hurt|hurt my eyes|hurting my eyes|dry eyes|tired eyes|screen headache|sore eyes|eyes are (sore|tired|dry))(?:s|es|ing)?\b|چشم\S*\s*(درد|خست|خشک)|درد\s*چشم|فشار\s*چشم|خستگی\s*چشم|إجهاد العين|عيني تؤلمني|جفاف العين|تعب العين|صداع من الشاشة|眼睛疲劳|眼睛痛|眼干|眼涩|视疲劳|看屏幕头疼|眼睛疼|眼疼|عين\S*\s*(تؤلم|ألم|توجع)|وجع عين/i,
      en: "I can't speak to anything clinical here, but the habit-level pattern people report is real: long unbroken screen sessions are linked with reduced blink rate, which dries the eyes out faster than normal. A simple, low-effort rule some people find useful is looking at something roughly 6 metres away for about 20 seconds every 20 minutes. If discomfort is persistent or getting worse, that's worth raising with an eye-care professional rather than working around it.",
      fa: "درباره‌ی سمت بالینی چیزی نمی‌توانم بگویم، اما الگوی سطح-عادتی که افراد گزارش می‌کنند واقعی است: جلسات طولانی و بی‌وقفه‌ی صفحه با کاهش نرخ پلک‌زدن مرتبط‌اند، که چشم را سریع‌تر از حالت عادی خشک می‌کند. یک قاعده‌ی ساده که برخی مفید می‌دانند: هر ۲۰ دقیقه، حدود ۲۰ ثانیه به چیزی در فاصله‌ی تقریباً ۶ متری نگاه کن. اگر ناراحتی پایدار است یا بدتر می‌شود، مطرح‌کردنش با یک متخصص چشم بهتر از دورزدنش است.",
      ar: "لا أستطيع الحديث عن أي شيء علاجي هنا، لكن النمط على مستوى العادات الذي يُبلّغ عنه الناس حقيقي: تُربط جلسات الشاشة الطويلة غير المتقطعة بانخفاض معدل الرمش، ما يجفف العين أسرع من المعتاد. قاعدة بسيطة قليلة الجهد يجدها بعض الناس مفيدة: انظر إلى شيء يبعد نحو ستة أمتار لبضع ثوان كل عشرين دقيقة تقريبا. إن كان الألم مستمرا، فذلك سؤال لطبيب عيون لا لتطبيق.",
      zh: "关于临床方面我无法置评，但人们报告的习惯层面的模式是真实的：长时间不间断看屏幕与眨眼频率下降相关，这会让眼睛比平常更快变干。一条简单省力、有些人觉得有用的规则：大约每二十分钟，看一下约六米外的东西几秒钟。如果疼痛持续存在，那是该问眼科医生的问题，而不是问应用。",
    },
    {
      key: 'posture',
      match: /\b(neck pain|text neck|tech neck|posture|back pain from (my )?phone|hunched over (my )?phone)(?:s|es|ing)?\b|گردن\S*\s*درد|درد\s*گردن|گردن‌درد|کمر\S*\s*درد|وضعیت بدن هنگام گوشی|ألم الرقبة|رقبة الهاتف|وضعية الجلوس|ألم الظهر من الهاتف|أنحني على هاتفي|颈痛|脖子疼|手机颈|姿势|坐姿|低头|背痛/i,
      en: "This isn't something the model measures directly, but it's a well-known side effect of long phone sessions: looking down at a device held low puts noticeably more load on the neck than holding it at eye level. A cheap habit fix is raising the phone rather than dropping your head, and taking the same movement breaks that help focus — they help this too, since it's largely a 'staying in one position too long' problem.",
      fa: "این چیزی نیست که مدل مستقیم اندازه بگیرد، اما یک اثر جانبی شناخته‌شده‌ی جلسات طولانی گوشی است: نگاه‌کردن به پایین به دستگاهی که پایین گرفته شده، فشار محسوساً بیشتری روی گردن نسبت به نگه‌داشتنش در سطح چشم می‌گذارد. یک اصلاح ارزان این است که گوشی را بالا بیاوری نه سرت را پایین ببری، و همان وقفه‌های حرکتی که به تمرکز کمک می‌کنند اینجا هم کمک می‌کنند — چون بیشتر مسئله‌ی «زیادی در یک حالت ماندن» است.",
      ar: "هذا ليس شيئا يقيسه النموذج مباشرة، لكنه أثر جانبي معروف لجلسات الهاتف الطويلة: النظر إلى جهاز ممسوك منخفضا يضع حملا أكبر بشكل ملحوظ على الرقبة من إمساكه بمستوى العين. إصلاح رخيص للعادة هو رفع الهاتف بدلا من إنزال رأسك، وأخذ نفس فترات الحركة القصيرة التي تساعد بقية درجتك أصلا.",
      zh: "这不是模型直接测量的东西，但它是长时间使用手机的一个众所周知的副作用：低举着设备去看，会比把它举到视线高度给颈部带来明显更大的负荷。一个低成本的习惯改法是把手机举高，而不是把头低下去；再加上那些本来就对你其余分数有帮助的短暂活动间歇。",
    },
    {
      key: 'screen_time',
      match: /\b(screen time|too much (screen|phone|time on my phone)|reduce (my )?(screen|phone)|cut down|limit (my )?(screen|phone)|digital detox|addicted to my phone|dependent on my phone)(?:s|es|ing)?\b|زمان صفحه|زیاد از گوشی استفاده|کم کنم|محدود کردن گوشی|اعتیاد به گوشی|وابستگی به گوشی|وقت الشاشة|وقت طويل على الهاتف|أقلل من الهاتف|حد لوقت الشاشة|屏幕时间|用手机太久|减少手机|限制屏幕|手机时长/i,
      en: "Total hours are the least interesting number in your check-in, honestly. Two people with identical totals can have very different scores here, because fragmentation, timing and category matter more. So 'use it less' is weak advice; 'use it in fewer, longer, more deliberate blocks, and not in the last hour before bed' is what the data actually points at. App timers help only if you let them interrupt you — an ignored limit isn't a limit.",
      fa: "صادقانه بگویم، مجموع ساعت‌ها کم‌جذاب‌ترین عدد در بررسی توست. دو نفر با مجموع یکسان می‌توانند امتیازهای خیلی متفاوتی اینجا داشته باشند، چون پراکندگی، زمان‌بندی و دسته‌ی استفاده مهم‌ترند. پس «کمتر استفاده کن» توصیه‌ی ضعیفی است؛ «در بلوک‌های کمتر، طولانی‌تر و سنجیده‌تر استفاده کن، و نه در آخرین ساعت قبل از خواب» چیزی است که داده واقعاً به آن اشاره می‌کند. تایمر اپ‌ها فقط وقتی کمک می‌کنند که بگذاری کارت را قطع کنند — محدودیتی که نادیده گرفته شود، محدودیت نیست.",
      ar: "مجموع الساعات هو أقل رقم مثير للاهتمام في تسجيلك، بصراحة. شخصان بمجاميع متطابقة قد يحصلان على درجتين مختلفتين تماما هنا، لأن التفتت والتوقيت والفئة أهم. لذا استخدمه أقل نصيحة ضعيفة؛ استخدمه في نوافذ أقل وأطول وأكثر قصدا هو ما تدعمه بياناتك فعلا.",
      zh: "老实说，总时长是你这次记录里最没意思的数字。两个总时长完全相同的人，在这里可能得到非常不同的分数，因为碎片化、时间点和类别更重要。所以少用一点是很弱的建议；在更少、更长、更有意图的时段里使用，才是你的数据真正支持的做法。",
    },
    {
      key: 'score_meaning',
      match: /\b(what does .{0,20}score mean|how is .{0,20}(score|it) calculated|how does this work|what is the score|shap|explain the model)(?:s|es|ing)?\b|امتیاز\S*\s*(یعنی|چیست|چه معن)|چطور محاسبه|چطور کار می‌کند|مدل چیست|ماذا تعني الدرجة|كيف تُحسب الدرجة|كيف يعمل هذا|ما هي الدرجة|اشرح الدرجة|分数是什么意思|分数怎么算|这是怎么工作的|什么是分数|解释一下分数|ماذا تعني\s*\S*درج|درجت\S*\s*تعني|معنى درجت/i,
      en: "Two models run on every check-in. A classifier puts you in a risk category, and a regressor produces the 0–100 score. Then SHAP works out how much each of your inputs pushed that score up or down — that's where the 'what drove this' list comes from, so it's the model explaining itself rather than me guessing. Separately, the dimension breakdown is plain arithmetic over the same inputs, shown next to the model output so you can sanity-check one against the other.",
      fa: "روی هر بررسی دو مدل اجرا می‌شوند. یک طبقه‌بند تو را در یک دسته‌ی ریسک قرار می‌دهد، و یک رگرسور امتیاز ۰ تا ۱۰۰ را تولید می‌کند. بعد SHAP حساب می‌کند هر ورودی چقدر آن امتیاز را بالا یا پایین برده — فهرست «چه چیزی این را ساخت» از همین‌جا می‌آید، پس این خود مدل است که توضیح می‌دهد نه حدس من. جدا از آن، تفکیک ابعاد حساب ساده‌ای روی همان ورودی‌هاست که کنار خروجی مدل نشان داده می‌شود تا بتوانی یکی را با دیگری بسنجی.",
      ar: "يعمل نموذجان على كل تسجيل. مُصنّف يضعك في فئة مخاطرة، ومُنحدِر يُنتج الدرجة من صفر إلى مئة. ثم يحسب شاب مقدار ما دفع به كل مدخل من مدخلاتك تلك الدرجة صعودا أو هبوطا — ومن هناك تأتي قائمة ما الذي سبّب هذا، فهي مبنية على مساهمتك الفعلية لا على قاعدة عامة. الدرجة تقدير له نطاق، لا حكم قاطع.",
      zh: "每次记录都会运行两个模型。一个分类器把你归入某个风险类别，一个回归器生成 0–100 的分数。然后 SHAP 计算你的每一项输入把这个分数推高或压低了多少——这就是是什么造成了这个结果那份清单的来源，它基于你实际的贡献，而不是一条通用规则。分数是一个带区间的估计，不是一个确定的判决。",
    },
    {
      key: 'accuracy',
      match: /\b(accurate|accuracy|trust|reliable|how sure|confidence|wrong|believe)(?:s|es|ing)?\b|دقت|قابل اعتماد|مطمئن|اشتباه|دقة|دقيق|أثق|موثوق|ما مدى تأكدك|ثقة|خطأ|أصدق|准确|准确率|可信|可靠|有多确定|置信度|错了|相信|دقیق/i,
      en: "Fair question, and the honest answer is on the Model page — the real numbers are there, not marketing ones. Two things worth knowing: the model is measured on people it has never seen, which is much harder than it sounds, and it's slightly overconfident on new users, so treat a high confidence figure as 'probably' rather than 'certainly'. The uncertainty range shown with your score exists precisely because a single number would overstate how precise this is.",
      fa: "سؤال منصفانه‌ای است، و پاسخ صادقانه در صفحه‌ی مدل است — اعداد واقعی آنجاست، نه اعداد تبلیغاتی. دو نکته ارزش دانستن دارند: مدل روی افرادی سنجیده می‌شود که هرگز ندیده، که خیلی سخت‌تر از چیزی است که به نظر می‌رسد، و روی کاربران جدید کمی بیش‌ازحد مطمئن است، پس یک عدد اطمینان بالا را «احتمالاً» بخوان نه «قطعاً». بازه‌ی عدم قطعیتی که کنار امتیازت نشان داده می‌شود دقیقاً برای همین وجود دارد که یک عدد تنها، دقت این را بیش از واقع نشان می‌دهد.",
      ar: "سؤال عادل، والجواب الصادق موجود على صفحة النموذج — الأرقام الحقيقية هناك، لا أرقام تسويقية. أمران يستحقان المعرفة: يُقاس النموذج على أشخاص لم يرهم قط، وهذا أصعب بكثير مما يبدو، وهو مفرط الثقة قليلا على المستخدمين الجدد الذين لديهم أيام قليلة من البيانات. لهذا تُعرض الدرجة كنطاق ولهذا تُقال حالة البداية الباردة بصراحة بدلا من إخفائها.",
      zh: "这是个合理的问题，诚实的答案在模型页面上——那里是真实的数字，不是营销数字。两件值得知道的事：模型是在它从未见过的人身上评估的，这比听起来难得多；而对只有几天数据的新用户，它会略微过度自信。这就是为什么分数以区间呈现，也是为什么冷启动状态会被明确说出来而不是藏起来。",
    },
    {
      key: 'privacy',
      match: /\b(privacy|private|data|stored|share|sell|delete (my )?(account|data|history)|export|gdpr)(?:s|es|ing)?\b|حریم خصوصی|داده من|ذخیره|حذف (حساب|داده|تاریخچه)|خروجی|خصوصية|خاص|بياناتي|مخزّنة|تشارك|تبيع|حذف حسابي|تصدير البيانات|隐私|私密|我的数据|存储|分享|出售|删除账户|导出数据|خصوصي/i,
      en: "Your data is used to compute your own predictions and nothing else — not sold, not shared, no third-party analytics on it. Everything is held by this app's own server against your account - not on a third-party cloud, and never on someone else's analytics platform. From your Profile page you can export a full copy of everything held about you as a file, or delete your account and its entire history permanently. If you ever paste an API key into the Coach, it lives in the browser tab's memory only and is gone the moment you close it.",
      fa: "داده‌ی تو برای محاسبه‌ی پیش‌بینی‌های خودت استفاده می‌شود و نه چیز دیگری — نه فروخته می‌شود، نه به اشتراک گذاشته می‌شود، و هیچ تحلیل شخص‌ثالثی روی آن اجرا نمی‌شود. همه‌چیز روی سرور خودِ همین اپ و به حساب تو گره خورده نگه داشته می‌شود - نه روی یک ابر شخص ثالث، و هرگز روی پلتفرم تحلیلی کس دیگری. از صفحه‌ی پروفایل می‌توانی یک نسخه‌ی کامل از هر چیزی که درباره‌ات نگه داشته شده را به‌صورت فایل خروجی بگیری، یا حساب و کل تاریخچه‌اش را برای همیشه حذف کنی. اگر هم کلید API در مربی وارد کنی، فقط در حافظه‌ی همان تب مرورگر می‌ماند و با بستنش از بین می‌رود.",
      ar: "تُستخدم بياناتك لحساب تنبؤاتك الخاصة ولا شيء غير ذلك — لا تُباع، ولا تُشارَك، ولا تحليلات طرف ثالث عليها. كل شيء محفوظ على خادم هذا التطبيق نفسه مرتبطا بحسابك - لا على سحابة طرف ثالث، ولا على منصة تحليلات لأحد آخر. من صفحة ملفك الشخصي يمكنك تصدير نسخة كاملة من كل ما يُحتفظ به عنك كملف، أو حذف حسابك وسجله نهائيا. ولا شيء يُرى من أي صديق إلا ما وافقت عليه صراحة لذلك الصديق تحديدا.",
      zh: "你的数据仅用于计算你自己的预测，别无他用——不出售、不共享、不做第三方分析。所有内容都保存在本应用自己的服务器上、与你的账户绑定——不在第三方云上，也绝不会在别人的分析平台上。在个人资料页，你可以把关于你的全部内容导出为一个文件，或永久删除你的账户及其历史。好友能看到的，只有你明确为那位特定好友勾选同意的部分。",
    },
    {
      key: 'work_study',
      match: /\b(work.life balance|too many meetings|always online for work|can'?t (stop|switch off) (checking )?(email|work)|studying too much|deadline stress)(?:s|es|ing)?\b|تعادل کار زندگی|جلسه زیاد|همیشه آنلاین برای کار|درس زیاد|استرس ددلاین|توازن بين العمل والحياة|اجتماعات كثيرة|متصل دائما للعمل|لا أستطيع التوقف عن تفقد البريد|دراسة|工作生活平衡|会议太多|总在线|停不下来看邮件|学习|念书/i,
      en: "Work and study bleed into evenings more easily on a device that's also your phone, your messenger and your entertainment — there's no physical 'leaving the office' anymore. A boundary that tends to hold better than willpower: a separate notification profile for work apps that's simply off outside agreed hours, so the decision is made once, in advance, instead of every single evening.",
      fa: "کار و درس روی دستگاهی که هم‌زمان گوشی، پیام‌رسان و سرگرمی توست خیلی راحت‌تر به عصرها نشت می‌کند — دیگر «ترک محل کار» فیزیکی وجود ندارد. مرزی که معمولاً بهتر از اراده دوام می‌آورد: یک پروفایل اعلان جدا برای اپ‌های کاری که خارج از ساعت‌های توافق‌شده صرفاً خاموش است، تا تصمیم یک‌بار و از قبل گرفته شود، نه هر عصر دوباره.",
      ar: "يتسرب العمل والدراسة إلى المساء بسهولة أكبر على جهاز هو أيضا هاتفك ومراسلك وترفيهك — لم يبق شيء اسمه مغادرة المكتب جسديا. حد يصمد أفضل من قوة الإرادة: ملف إشعارات منفصل للعمل يُغلق في وقت محدد، وإن أمكن مساحة أو حساب مستخدم مختلف. الهدف ليس عملا أقل بل نهاية واضحة له.",
      zh: "在一台同时是你的手机、聊天工具和娱乐设备的机器上，工作和学习更容易渗进夜晚——再也没有身体上离开办公室这件事了。有一种比意志力更能守住的边界：为工作设一个独立的通知配置，并在固定时间关闭它；如果可以，再用不同的空间或用户账户。目标不是更少的工作，而是一个明确的结束。",
    },
    {
      key: 'multitasking',
      match: /\b(multitask|multi.tasking|switching between apps|task switch|context switch)(?:s|es|ing)?\b|چندوظیفگی|جابجایی بین اپ‌ها|تعویض کار|تعدد المهام|تبديل بين التطبيقات|تبديل المهام|تبديل السياق|多任务|一边一边|切换应用|任务切换|来回切换/i,
      en: "What feels like doing two things at once is usually rapid switching, and each switch carries a small cost in accuracy and speed that people consistently underestimate. The apps this project tracks (pickups per day, fragmentation index) are really trying to measure exactly this. Batching similar tasks together — replying to messages in one block instead of between every other task — tends to beat trying to do everything simultaneously.",
      fa: "چیزی که حس دوکارِ-همزمان می‌دهد معمولاً تعویض سریع است، و هر تعویض هزینه‌ی کوچکی در دقت و سرعت دارد که افراد پیوسته دست‌کم می‌گیرند. چیزهایی که این پروژه ردیابی می‌کند (تعداد برداشتن گوشی در روز، شاخص پراکندگی) دقیقاً همین را می‌سنجند. دسته‌بندی کارهای مشابه — پاسخ به پیام‌ها در یک بلوک به‌جای بین هر کار دیگر — معمولاً از تلاش برای انجام همه‌چیز همزمان بهتر است.",
      ar: "ما يبدو أنه فعل شيئين في الوقت نفسه هو عادة تبديل سريع، وكل تبديل يحمل تكلفة صغيرة في الدقة والسرعة يقلل الناس من تقديرها باستمرار. المقاييس التي يتابعها هذا المشروع (مرات الالتقاط في اليوم، مؤشر التفتت) تحاول فعلا قياس هذا. إن أردت خطوة واحدة: أغلق ما لا تعمل عليه، بدلا من إبقائه مفتوحا في الخلف.",
      zh: "感觉像同时做两件事，实际上通常是快速切换，而每次切换都带有一点准确度和速度上的代价，人们一贯低估它。本项目追踪的指标（每日拿起次数、碎片化指数）真正想衡量的就是这个。如果只做一件事：把你不在处理的东西关掉，而不是让它在后台开着。",
    },
    {
      key: 'phone_free_zones',
      match: /\b(phone.free (zone|room)|no.phone zone|leave (my |the )?phone (in|at) (another|a different) room)(?:s|es|ing)?\b|منطقه بدون گوشی|گوشی را در اتاق دیگر بگذار|منطقة بلا هاتف|غرفة بلا هاتف|أترك هاتفي في غرفة أخرى|طاولة الطعام بلا هاتف|无手机区|不带手机|把手机放另一个房间|餐桌不用手机/i,
      en: "Designating a phone-free space (the dinner table, the bedroom) removes the moment-by-moment decision entirely, which is usually why it works better than an in-the-moment resolution to 'use it less' there. Start with just one room or one recurring time block rather than the whole day — a rule you can actually keep beats an ambitious one you abandon by Wednesday.",
      fa: "تعیین یک فضای بدون گوشی (میز شام، اتاق خواب) کاملاً تصمیم لحظه‌به‌لحظه را حذف می‌کند، و معمولاً برای همین بهتر از یک تصمیم لحظه‌ای برای «کمتر استفاده‌کردن» عمل می‌کند. با فقط یک اتاق یا یک بازه‌ی زمانی تکرارشونده شروع کن نه کل روز — قانونی که واقعاً می‌توانی نگه‌داری بهتر از یک قانون بلندپروازانه است که چهارشنبه رهایش می‌کنی.",
      ar: "تخصيص مساحة بلا هاتف (طاولة العشاء، غرفة النوم) يزيل القرار لحظة بلحظة تماما، وهذا عادة سبب نجاحه أكثر من عزم لحظي على استخدامه أقل هناك. ابدأ بغرفة واحدة أو فترة زمنية متكررة واحدة بدلا من إعلان قواعد كثيرة في وقت واحد — القاعدة الواحدة التي تصمد تتفوق على أربع تنهار في يومين.",
      zh: "指定一个无手机的空间（餐桌、卧室）彻底取消了每时每刻的决定，这通常就是它比临时下决心在那儿少用手机更有效的原因。先从一个房间或一个固定时段开始，而不是一次宣布很多规则——一条能坚持的规则，胜过四条两天就崩掉的规则。",
    },
    {
      key: 'weekend_pattern',
      match: /\b(weekend|weekdays vs weekend|different on weekends|weekend habits)(?:s|es|ing)?\b|آخر هفته|تفاوت روزهای هفته|عادت‌های آخر هفته|نهاية الأسبوع|أيام العمل مقابل نهاية الأسبوع|مختلف في العطلة|عادات نهاية الأسبوع|周末|工作日和周末|周末不一样|周末习惯/i,
      en: "Weekday and weekend patterns are worth comparing on your own Analytics page, because a large swing between them is itself informative — it usually means weekday structure (work, school) is doing more of the regulating than any habit you've actually built. That's not a criticism; it's useful information about where a boundary would need to be deliberate rather than automatic.",
      fa: "مقایسه‌ی الگوی روزهای هفته و آخر هفته در صفحه‌ی تحلیل‌های خودت ارزش دارد، چون یک نوسان بزرگ بین آن‌ها خودش آموزنده است — معمولاً یعنی ساختار روزهای هفته (کار، مدرسه) بیشتر از هر عادتی که واقعاً ساخته‌ای در حال تنظیم‌کردن است. این انتقاد نیست؛ اطلاعات مفیدی است درباره‌ی جایی که یک مرز باید عمدی باشد نه خودکار.",
      ar: "يستحق نمط أيام العمل ونهاية الأسبوع مقارنة على صفحة تحليلاتك، لأن التقلب الكبير بينهما معلومة بنفسه — يعني عادة أن بنية أيام العمل (العمل، الدراسة) تقوم بالتنظيم أكثر من أي عادة بنيتها فعلا. وذلك ليس فشلا، لكنه يفيد في معرفته: العادة التي تحتاج جدولا خارجيا لتصمد ستحتاج دعامة أخرى في العطلة.",
      zh: "工作日与周末的模式值得在你的分析页上做个对比，因为两者之间的巨大摆动本身就是信息——它通常意味着，在起调节作用的更多是工作日的外部结构（工作、上学），而不是你真正养成的某个习惯。这并不是失败，但知道它很有用：一个需要外部日程才能维持的习惯，在周末需要另一个支点。",
    },
    {
      key: 'habit_stacking',
      match: /\b(habit stack|stack (my )?habits|pair.*habit|build.*habit.*existing (habit|routine))(?:s|es|ing)?\b|جفت‌کردن عادت|وصل‌کردن عادت به عادت دیگر|تجميع العادات|أربط عادة بعادة|أبني عادة على روتين قائم|习惯叠加|把习惯绑在一起|在已有习惯后加/i,
      en: "Attaching a new habit to one that's already automatic tends to work better than trying to remember a new habit on its own — 'after I pour my morning coffee, I'll put my phone in another room' borrows the coffee habit's existing momentum. The anchor habit should be something you genuinely never skip; a shaky anchor makes the new habit shaky too.",
      fa: "وصل‌کردن یک عادت جدید به عادتی که از قبل خودکار است معمولاً بهتر از تلاش برای به‌یادآوردن یک عادت جدید به‌تنهایی جواب می‌دهد — «بعد از ریختن قهوه‌ی صبح، گوشی را در اتاق دیگر می‌گذارم» از حرکت از قبل موجودِ عادت قهوه استفاده می‌کند. عادت لنگر باید چیزی باشد که واقعاً هرگز جا نمی‌اندازی؛ لنگر لرزان عادت جدید را هم لرزان می‌کند.",
      ar: "إلحاق عادة جديدة بأخرى صارت تلقائية يعمل عادة أفضل من محاولة تذكر عادة جديدة بمفردها — بعد أن أصب قهوة الصباح، سأضع هاتفي في غرفة أخرى يستعير زخم عادة القهوة القائم. ينبغي أن تكون عادة المرساة شيئا تفعله فعلا كل يوم بلا تفكير، وإلا فأنت تبني على أساس غير موجود.",
      zh: "把一个新习惯挂在一个已经自动化的习惯后面，通常比试图单独记住一个新习惯更有效——倒完早咖啡之后，我就把手机放到另一个房间，借用的是咖啡这个习惯已有的惯性。作为锚点的那个习惯，必须是你真的每天不用想就会做的事，否则你是在一个并不存在的地基上盖房子。",
    },
    {
      key: 'environment_design',
      match: /\b(environment design|design my environment|make it harder to (open|check|use)|remove (the )?temptation)(?:s|es|ing)?\b|طراحی محیط|سخت‌ترکردن دسترسی|حذف وسوسه|تصميم البيئة|أجعله أصعب|أزيل الإغراء|تعديل المحيط|环境设计|让它更难打开|移除诱惑|改造环境/i,
      en: "Changing your environment tends to beat changing your willpower, because it works even on the days your willpower is low. Logging out of an app instead of just closing it, moving it off the home screen, or using a plain text-message-only phone in the evening are all the same move: add enough friction that the default action is no longer 'check it without thinking'.",
      fa: "تغییر محیط معمولاً از تغییر اراده بهتر است، چون حتی روزهایی که اراده‌ات کم است هم کار می‌کند. خروج از یک اپ به‌جای فقط بستنش، برداشتنش از صفحه‌ی اصلی، یا استفاده از یک گوشی ساده‌ی فقط-پیامکی در عصرها، همه یک حرکت‌اند: اضافه‌کردن اصطکاک کافی تا عمل پیش‌فرض دیگر «بی‌فکر چک‌کردن» نباشد.",
      ar: "تغيير بيئتك يتفوق عادة على تغيير قوة إرادتك، لأنه يعمل حتى في الأيام التي تكون فيها إرادتك منخفضة. الخروج من حساب تطبيق بدلا من مجرد إغلاقه، أو نقله بعيدا عن الشاشة الرئيسية، أو استخدام هاتف للرسائل النصية فقط في المساء — كلها تضيف احتكاكا صغيرا في اللحظة الصحيحة. الهدف ليس المنع بل إدخال ثانية من التفكير قبل الفعل.",
      zh: "改变环境通常胜过改变意志力，因为它在你意志力低落的日子里也照样起作用。退出某个应用的登录而不只是关掉它、把它从主屏幕移走、或者晚上只用一台只能收发短信的手机——这些都在恰当的时刻加入了一点摩擦。目标不是禁止，而是在动作之前插入一秒钟的思考。",
    },
    {
      key: 'email_overload',
      match: /\b(email overload|inbox zero|too many emails|can'?t keep up with (my )?email)(?:s|es|ing)?\b|ایمیل زیاد|صندوق ایمیل شلوغ|نمی‌رسم ایمیل‌ها را بخوانم|كثرة البريد|صندوق الوارد|رسائل كثيرة|لا أستطيع متابعة بريدي|邮件太多|收件箱|处理不完邮件|邮件过载/i,
      en: "An always-open inbox turns every arriving email into a live interruption instead of something you choose to look at. Two or three fixed times a day to process email, with notifications off in between, tends to get through the same volume of work with far fewer context switches than reacting to each one as it lands.",
      fa: "صندوق ایمیل همیشه‌بازکه هر ایمیل تازه را به یک وقفه‌ی زنده تبدیل می‌کند به‌جای چیزی که خودت انتخاب می‌کنی نگاهش کنی. دو سه زمان مشخص در روز برای رسیدگی به ایمیل، با اعلان خاموش در فاصله‌ها، معمولاً همان حجم کار را با تعویض زمینه‌ی خیلی کمتر از واکنش به هرکدام لحظه‌ی رسیدن انجام می‌دهد.",
      ar: "صندوق وارد مفتوح دائما يحوّل كل بريد يصل إلى مقاطعة حية بدلا من شيء تختار أن تنظر إليه. مرتان أو ثلاث ثابتة في اليوم لمعالجة البريد، مع إيقاف الإشعارات بينها، تنجز عادة نفس حجم العمل بمقاطعات أقل بكثير. المفاجأة المعتادة هي كم قليلا يهتم أحد بأنك رددت بعد ثلاث ساعات لا ثلاث دقائق.",
      zh: "一个始终开着的收件箱，会把每一封到达的邮件都变成实时打扰，而不是你主动选择去看的东西。每天两三个固定时间处理邮件、期间关掉通知，通常能完成同样的工作量，而打扰少得多。常见的意外发现是：几乎没人在意你是三小时后而不是三分钟后回复的。",
    },
    {
      key: 'video_calls',
      match: /\b(zoom fatigue|video call fatigue|too many video calls|back.to.back (zoom|video) calls)(?:s|es|ing)?\b|خستگی تماس تصویری|زوم زیاد|تماس‌های تصویری پشت‌سرهم|إرهاق المكالمات المرئية|تعب زوم|مكالمات فيديو كثيرة|مكالمات متتالية|视频会议疲劳|视频通话太多|连着开会|会议疲劳/i,
      en: "Video calls ask for a kind of sustained, close-range eye contact that in-person conversation doesn't actually demand continuously, and back-to-back calls remove the walking-between-rooms recovery time a normal day of meetings used to have built in. Even a five-minute gap between calls, camera off, tends to make a noticeable difference over a full day.",
      fa: "تماس‌های تصویری نوعی تماس چشمی پیوسته و نزدیک می‌خواهند که گفتگوی حضوری واقعاً به‌طور مداوم آن را نمی‌طلبد، و تماس‌های پشت‌سرهم آن زمان بازیابیِ راه‌رفتن بین اتاق‌ها که یک روز عادی جلسات قبلاً داشت را حذف می‌کنند. حتی یک فاصله‌ی پنج‌دقیقه‌ای بین تماس‌ها، با دوربین خاموش، معمولاً در طول یک روز کامل تفاوت محسوسی ایجاد می‌کند.",
      ar: "تطلب مكالمات الفيديو نوعا من التواصل البصري القريب المستمر لا يتطلبه الحديث الحضوري فعلا بشكل متصل، والمكالمات المتتالية تزيل وقت التعافي الذي كان المشي بين الغرف يوفره ضمنا في يوم اجتماعات عادي. حتى خمس دقائق بين المكالمات، بعيدا عن الشاشة، تعيد شيئا من ذلك. وإيقاف عرض صورتك الذاتية يقلل حمل مراقبة نفسك.",
      zh: "视频通话要求一种持续的、近距离的目光接触，而面对面交谈其实并不连续地需要这一点；连着开会还取消了原本一天会议中在房间之间走动所自带的恢复时间。哪怕在两个会议之间留五分钟、离开屏幕，也能找回一部分。关掉自己的自视画面，则能减少时刻审视自己的负担。",
    },
    {
      key: 'remote_work_boundaries',
      match: /\b(remote work|working from home|wfh boundaries|always available for work)(?:s|es|ing)?\b|دورکاری|کار از خانه|همیشه در دسترس برای کار|عمل عن بعد|عمل من المنزل|حدود العمل من البيت|متاح دائما للعمل|远程工作|居家办公|在家上班|工作边界|随时在线/i,
      en: "Without a commute or a physical office to leave, 'end of the workday' has to be created on purpose or it simply doesn't happen. A closing ritual — even something as small as closing the laptop and putting it in a bag, or changing the phone's home screen for work hours — gives your brain the boundary signal a commute used to provide for free.",
      fa: "بدون رفت‌وآمد یا محل کار فیزیکی برای ترک‌کردن، «پایان روز کاری» باید عمداً ساخته شود وگرنه اصلاً اتفاق نمی‌افتد. یک آیین پایان‌دادن — حتی چیزی به کوچکی بستن لپ‌تاپ و گذاشتنش در کیف، یا تغییر صفحه‌ی اصلی گوشی برای ساعات کاری — همان سیگنال مرزی را به مغزت می‌دهد که رفت‌وآمد قبلاً رایگان می‌داد.",
      ar: "بدون تنقل أو مكتب مادي تغادره، لا بد أن تُصنَع نهاية يوم العمل بشكل متعمد وإلا فهي لا تحدث ببساطة. طقس إغلاق — حتى شيء صغير كإغلاق الحاسوب ووضعه في حقيبة، أو تغيير شاشة الهاتف الرئيسية بين وضع العمل والمساء — يعطي دماغك الإشارة التي كان التنقل يعطيها. الشكل أقل أهمية من كونه نفس الشيء كل يوم.",
      zh: "没有通勤、也没有一个可以离开的实体办公室，工作日的结束就必须刻意去创造，否则它根本不会发生。一个收尾仪式——哪怕小到合上笔记本电脑放进包里，或在工作与夜间之间切换手机主屏——能给大脑提供通勤原本给的那个信号。具体形式不重要，重要的是每天都一样。",
    },
    {
      key: 'streaks_motivation',
      match: /\b(streak|lost my streak|broke my streak|motivation dip|losing motivation)(?:s|es|ing)?\b|استریک|از دست دادن انگیزه|افت انگیزه|سلسلة الأيام|فقدت سلسلتي|كسرت السلسلة|هبوط الحافز|أفقد الدافع|连续记录|断了|连胜中断|动力下降|没动力/i,
      en: "Losing a streak feels like losing all the progress behind it, but the data underneath it — the actual habit change — doesn't reset just because a counter did. The more useful question after a broken streak isn't 'how do I get the number back' but 'what made that day different', since that's the thing worth actually addressing.",
      fa: "از دست‌دادن یک استریک حس از دست‌دادن تمام پیشرفت پشتش را می‌دهد، اما داده‌ی زیرش — تغییر عادت واقعی — فقط به‌خاطر ریست‌شدن یک شمارنده ریست نمی‌شود. سؤال مفیدتر بعد از شکستن استریک این نیست که «چطور عدد را برگردانم» بلکه «آن روز چه چیزی متفاوت بود» است، چون همان چیزی است که واقعاً ارزش رسیدگی دارد.",
      ar: "يبدو فقدان السلسلة كفقدان كل التقدم خلفها، لكن البيانات تحتها — التغير الفعلي في العادة — لا تُصفَّر لأن عدادا تصفّر. السؤال الأنفع بعد سلسلة مكسورة ليس كيف أعيد الرقم بل ما الذي جعل ذلك اليوم مختلفا. إن كان يوما استثنائيا فعلا، فوسمه كذلك أصدق من احتسابه كفشل.",
      zh: "连续记录中断，感觉像是把它背后的全部进展都丢了，但底下的数据——真实的习惯改变——并不会因为一个计数器归零而归零。连续中断之后，更有用的问题不是我怎么把数字追回来，而是那一天有什么不同。如果那确实是个特殊的日子，把它标记为特殊，比把它算作一次失败更诚实。",
    },
    {
      key: 'digital_minimalism',
      match: /\b(digital minimalism|delete apps|declutter (my )?phone|fewer apps|minimalist phone)(?:s|es|ing)?\b|مینیمالیسم دیجیتال|حذف اپ|پاکسازی گوشی|تبسيط الرقمي|أحذف تطبيقات|أرتب هاتفي|تطبيقات أقل|هاتف مبسط|数字极简|删除应用|整理手机|更少的应用|极简手机/i,
      en: "Deleting an app you rarely open on purpose is a low-cost experiment: nothing stops you from reinstalling it, but the small friction of having to do so is often enough to reveal whether you actually missed it or just missed the reflex of checking it. A useful test before deleting anything: could you name, right now, what you'd use it for today?",
      fa: "حذف عمدی اپی که به‌ندرت باز می‌کنی یک آزمایش کم‌هزینه است: چیزی جلوی نصب دوباره‌اش را نمی‌گیرد، اما اصطکاک کوچکِ نیاز به این کار اغلب کافی است تا نشان دهد واقعاً دلت برایش تنگ شده یا فقط دلت برای رفلکس چک‌کردنش تنگ شده. یک تست مفید قبل از حذف هرچیزی: می‌توانی همین الان بگویی امروز برای چه استفاده‌اش می‌کردی؟",
      ar: "حذف تطبيق تفتحه نادرا بشكل متعمد تجربة منخفضة التكلفة: لا شيء يمنعك من إعادة تثبيته، لكن الاحتكاك الصغير في الاضطرار لذلك يكفي غالبا لكشف ما إذا كنت افتقدته فعلا أم افتقدت مجرد منعكس التحقق. اختبار مفيد لمدة أسبوع: إن لم تلاحظ غيابه، فقد أجبت على السؤال.",
      zh: "刻意删掉一个你很少打开的应用，是一个低成本的实验：没有什么能阻止你重新安装它，但必须重新安装这一点小摩擦，往往就足以揭示你到底是真的怀念它，还是只怀念那个查看的条件反射。一个有用的一周检验：如果你没注意到它不在，你已经回答了这个问题。",
    },
    {
      key: 'driving_safety',
      match: /\b(phone while driving|texting (and|while) driving|driving and texting|use (my )?phone in the car)(?:s|es|ing)?\b|گوشی حین رانندگی|پیامک حین رانندگی|گوشی در ماشین|هاتف أثناء القيادة|رسائل والقيادة|أستخدم هاتفي في السيارة|开车用手机|开车发消息|车里用手机|驾驶时看手机/i,
      en: "This one isn't really a habit-optimization question — using a phone while actively driving is a safety issue, not a digital-wellbeing tradeoff, and I'd rather say that plainly than soften it. Practical fixes that remove the temptation entirely tend to work better than willpower here too: Do Not Disturb While Driving mode, or simply putting the phone in the back seat before you start the car.",
      fa: "این واقعاً یک سؤال بهینه‌سازی عادت نیست — استفاده از گوشی حین رانندگی یک مسئله‌ی ایمنی است نه یک مصالحه‌ی سلامت دیجیتال، و ترجیح می‌دهم این را صریح بگویم نه نرم‌ترش کنم. راه‌حل‌های عملی که کلاً وسوسه را حذف می‌کنند اینجا هم بهتر از اراده عمل می‌کنند: حالت «مزاحم نشوید حین رانندگی»، یا صرفاً گذاشتن گوشی روی صندلی عقب قبل از روشن‌کردن ماشین.",
      ar: "هذا ليس فعلا سؤال تحسين عادات — استخدام الهاتف أثناء القيادة الفعلية مسألة سلامة لا مقايضة عافية رقمية، وأفضّل قول ذلك بصراحة على تلطيفه. الإصلاحات العملية التي تزيل الإغراء تماما تعمل أفضل من العزم: وضع القيادة الذي يُشغَّل تلقائيا، أو الهاتف في الحقيبة على المقعد الخلفي لا في حاضنة أمامك.",
      zh: "这其实不是一个习惯优化的问题——在实际驾驶时使用手机是安全问题，而不是数字健康上的权衡，我宁愿把这一点直接说出来，而不是把它说得柔和些。彻底移除诱惑的实际办法比下决心更有效：自动开启的驾驶模式，或者把手机放进后座的包里，而不是放在你面前的支架上。",
    },
    {
      key: 'dopamine_loops',
      match: /\b(dopamine|reward loop|hooked on (my )?phone|can'?t put (my )?phone down)(?:s|es|ing)?\b|دوپامین|چرخه‌ی پاداش|گوشی\S*\s*(ر[او])?\s*زمین\s*نمی|نمی‌?تون\S*\s*گوشی\S*\s*(ر[او])?\s*زمین|دوبامين|حلقة المكافأة|معلق بهاتفي|لا أستطيع ترك هاتفي|多巴胺|奖赏循环|放不下手机|停不下来刷|上瘾/i,
      en: "Variable, unpredictable rewards — not knowing if the next scroll brings something interesting or nothing — are a well-studied reason certain feeds are harder to put down than others with more predictable content. Naming that mechanism out loud tends to weaken it a little: it's not a personal willpower failure, it's a design choice working exactly as intended, and design can be worked around with design (timers, greyscale, removing the app) rather than sheer effort.",
      fa: "پاداش‌های متغیر و غیرقابل‌پیش‌بینی — ندانستن اینکه اسکرول بعدی چیز جالبی می‌آورد یا هیچ‌چیز — دلیلی خوب‌بررسی‌شده است که چرا برخی فیدها سخت‌تر از فیدهایی با محتوای قابل‌پیش‌بینی‌تر زمین گذاشته می‌شوند. بلندگفتن این مکانیزم کمی تضعیفش می‌کند: این شکست اراده‌ی شخصی نیست، یک انتخاب طراحی است که دقیقاً همان‌طور که قرار بوده کار می‌کند، و طراحی را می‌شود با طراحی (تایمر، سیاه‌وسفید، حذف اپ) دور زد نه فقط با تلاش خالص.",
      ar: "المكافآت المتغيرة غير المتوقعة — ألا تعرف إن كان التمرير التالي سيجلب شيئا مثيرا أو لا شيء — سبب مدروس جيدا لكون بعض الشبكات أصعب في الترك من غيرها ذات المحتوى المتوقع. تسمية هذه الآلية بصوت عال تُضعف قوتها قليلا: أنت لا تبحث عن شيء، أنت تنتظر أن تُكافأ. الرافعة الملموسة هي إزالة اللانهاية — التمرير إلى نقطة توقف محددة سلفا بدلا من التوقف عند الشعور بالكفاية.",
      zh: "可变的、不可预测的奖赏——你不知道下一次滑动会带来有趣的东西还是什么都没有——是某些信息流比内容更可预测的信息流更难放下的一个被充分研究的原因。把这个机制说出口，会让它的力量减弱一点：你不是在寻找什么，你是在等着被奖赏。具体可用的杠杆是移除无限性——滑到一个事先定好的停止点，而不是等到感觉够了才停。",
    },
    {
      key: 'batching_tasks',
      match: /\b(batch(ing)? (my )?(message|email|task)|batching)(?:s|es|ing)?\b|دسته‌بندی پیام|دسته‌بندی کار|دسته‌بندی ایمیل|تجميع الرسائل|تجميع المهام|تجميع البريد|批处理|集中处理消息|集中回邮件|归类处理任务/i,
      en: "Batching means doing a category of small task in one dedicated block instead of scattered throughout the day — messages at 10am and 4pm instead of continuously. It costs a little in immediacy (replies aren't instant) but tends to recover a lot in focus, since it removes the constant low-grade readiness to be interrupted that scattered checking requires.",
      fa: "دسته‌بندی یعنی انجام یک دسته کار کوچک در یک بلوک اختصاصی به‌جای پراکنده در طول روز — پیام‌ها ساعت ۱۰ صبح و ۴ عصر به‌جای پیوسته. کمی در فوریت هزینه دارد (پاسخ‌ها آنی نیستند) اما معمولاً در تمرکز زیاد جبران می‌شود، چون آن آماده‌باش دائمیِ کم‌شدت برای وقفه‌خوردن که چک‌کردن پراکنده می‌طلبد را حذف می‌کند.",
      ar: "التجميع يعني إنجاز فئة من المهام الصغيرة في كتلة مخصصة واحدة بدلا من تفريقها على اليوم — الرسائل في العاشرة والرابعة بدلا من باستمرار. يكلّف قليلا في الفورية (الردود ليست لحظية) لكنه يستعيد كثيرا في التركيز، لأن التكلفة الحقيقية للمقاطعة ليست دقيقة الرد بل إعادة الدخول إلى ما كنت تفعله.",
      zh: "批处理的意思是把一类小任务放进一个专门的时间块里完成，而不是分散在一整天——消息在上午十点和下午四点处理，而不是持续处理。它在即时性上付出一点代价（回复不再是秒回），但在专注上收回很多，因为打扰的真正成本不是回复的那一分钟，而是重新回到你原本在做的事情里。",
    },
    {
      key: 'accountability',
      match: /\b(accountability partner|tell someone (about|my)|make myself accountable)(?:s|es|ing)?\b|فرد پاسخگو|به کسی بگویم|خودم را پاسخگو کنم|شريك المساءلة|أخبر شخصا|أجعل نفسي مسؤولا|监督伙伴|告诉别人|让自己有责任|找人监督/i,
      en: "Telling one other person what you're trying to change, and agreeing on a simple way to check in, is one of the more consistently useful low-cost tools in habit research — it turns an internal, easily-abandoned goal into something with a small social cost to dropping. It doesn't need to be formal; a weekly one-line text to a friend counts.",
      fa: "گفتن به یک نفر دیگر که چه چیزی را می‌خواهی تغییر بدهی، و توافق روی یک راه ساده برای چک‌کردن، یکی از پیوسته‌مفیدترین ابزارهای کم‌هزینه در پژوهش عادت‌هاست — یک هدف درونی و به‌راحتی رهاشدنی را به چیزی با هزینه‌ی اجتماعی کوچک برای رهاکردن تبدیل می‌کند. لازم نیست رسمی باشد؛ یک پیامک یک‌خطی هفتگی به یک دوست هم کافی است.",
      ar: "إخبار شخص واحد آخر بما تحاول تغييره، والاتفاق على طريقة بسيطة للمتابعة، من أكثر الأدوات منخفضة التكلفة اتساقا في بحوث العادات — يحوّل هدفا داخليا يُترك بسهولة إلى شيء له تكلفة اجتماعية صغيرة عند التخلي عنه. لا يلزم أن يكون شخصا يفعل نفس التغيير، فقط شخصا سيسأل.",
      zh: "把你想改变的事情告诉另一个人，并约定一个简单的相互确认方式，是习惯研究中较为一贯有用的低成本工具之一——它把一个内在的、很容易放弃的目标，变成了放弃时有一点社会成本的事。这个人不必也在做同样的改变，只需要是会来问一句的人。",
    },
    {
      key: 'app_blockers',
      match: /\b(app blocker|blocking app|screen.time app|freedom app|forest app|focus app)(?:s|es|ing)?\b|اپ مسدودکننده|اپ محدودکننده|اپ تمرکز|تطبيق حجب|تطبيق تحديد وقت الشاشة|تطبيق تركيز|应用锁|屏幕时间应用|专注应用|限制应用|番茄专注/i,
      en: "Blocker apps work best as a pre-commitment tool, not a willpower substitute — you set the rule while calm and rested, so the in-the-moment version of you (tired, bored, tempted) doesn't get to renegotiate it. The ones that require a genuinely annoying extra step to override tend to outperform ones you can dismiss with a single tap.",
      fa: "اپ‌های مسدودکننده بهترین عملکردشان به‌عنوان ابزار تعهد از قبل است، نه جایگزین اراده — قانون را وقتی آرام و استراحت‌کرده‌ای می‌گذاری، تا نسخه‌ی لحظه‌ای خودت (خسته، بی‌حوصله، وسوسه‌شده) نتواند دوباره مذاکره کند. آن‌هایی که برای دورزدن به یک مرحله‌ی واقعاً آزاردهنده‌ی اضافه نیاز دارند معمولاً بهتر از آن‌هایی عمل می‌کنند که با یک ضربه رد می‌شوند.",
      ar: "تعمل تطبيقات الحجب أفضل كأداة التزام مسبق لا كبديل لقوة الإرادة — تضع القاعدة وأنت هادئ ومرتاح، فلا تحصل نسختك في اللحظة (المتعبة، الضجرة، المُغراة) على حق إعادة التفاوض. تلك التي تتطلب خطوة إضافية مزعجة فعلا للتجاوز تتفوق على تلك التي تُطفأ بضغطة. وإن وجدت نفسك تتجاوزها كل يوم، فذلك ليس فشلا في الإرادة بل معلومة عن كون القاعدة صعبة جدا.",
      zh: "拦截类应用最适合作为预先承诺的工具，而不是意志力的替代品——你在冷静休息好的时候设定规则，于是当下那个（疲惫、无聊、被诱惑的）你就没有重新谈判的权利。那些需要真正麻烦一步才能绕过的，比一按就能关掉的更有效。如果你发现自己每天都在绕过它，那不是意志力的失败，而是关于这条规则太难的信息。",
    },
    {
      key: 'dnd_scheduling',
      match: /(?=.*\b(do not disturb|dnd|silent mode)\b)(?=.*\bschedul)|زمان‌بندی مزاحم نشوید|زمان‌بندی حالت سکوت|مزاحم نشوید.*زمان‌بند|زمان‌بند.*مزاحم نشوید|جدولة عدم الإزعاج|وضع الصامت المجدول|عدم الإزعاج تلقائي|免打扰 定时|定时静音|自动免打扰|勿扰模式 计划/i,
      en: "A manually-toggled Do Not Disturb depends on remembering to turn it on and off every single day, which is exactly the kind of small daily decision that quietly stops happening under stress. Scheduling it once so it runs automatically at the same hours removes that dependency entirely — set it up once when you're motivated, and it keeps working on the days you're not.",
      fa: "«مزاحم نشوید»ی که دستی روشن و خاموش می‌شود به یادآوردن هر روز روشن و خاموش‌کردنش وابسته است، که دقیقاً همان نوع تصمیم کوچک روزانه است که زیر فشار بی‌سروصدا متوقف می‌شود. یک‌بار زمان‌بندی‌کردنش که خودکار در همان ساعت‌ها اجرا شود کاملاً این وابستگی را حذف می‌کند — یک‌بار وقتی انگیزه داری تنظیمش کن، و روزهایی که نداری هم کار می‌کند.",
      ar: "وضع عدم الإزعاج المُشغَّل يدويا يعتمد على تذكر تشغيله وإيقافه كل يوم، وهذا بالضبط نوع القرار اليومي الصغير الذي يتوقف بهدوء تحت الضغط. جدولته مرة واحدة ليعمل تلقائيا في نفس الساعات يزيل القرار من المعادلة تماما — وهو السبب في أن الجدولة تصمد عادة حيث ينهار العزم.",
      zh: "手动切换的免打扰依赖你每天记得开和关，而这恰恰是那种在压力之下会悄悄停止发生的小小日常决定。只设定一次、让它在相同时段自动运行，就把这个决定彻底从方程里移除了——这就是为什么在决心崩掉的地方，计划通常还能守住。",
    },
    {
      key: 'caffeine',
      match: /\b(caffeine|coffee intake|too much coffee|energy drink)(?:s|es|ing)?\b|کافئین|مصرف قهوه|نوشیدنی انرژی‌زا|كافيين|قهوة|قهوة كثيرة|مشروب طاقة|咖啡因|咖啡|喝太多咖啡|能量饮料|提神饮料/i,
      en: "Caffeine late in the day is associated with lighter, more fragmented sleep even in people who feel like it doesn't affect them — the subjective feeling of falling asleep fine is a poor guide to sleep quality later in the night. A simple, low-effort test: try a cutoff of early-to-mid afternoon for a week and compare how mornings feel.",
      fa: "کافئین در اواخر روز حتی در افرادی که حس می‌کنند رویشان اثر ندارد، با خواب سبک‌تر و پراکنده‌تر مرتبط است — حس ذهنیِ راحت به‌خواب‌رفتن راهنمای ضعیفی برای کیفیت خواب در ادامه‌ی شب است. یک تست ساده و کم‌هزینه: یک هفته مرز مصرف را اوایل تا اواسط بعدازظهر بگذار و ببین صبح‌ها چطور حس می‌شوند.",
      ar: "يُربط الكافيين في وقت متأخر من النهار بنوم أخف وأكثر تفتتا حتى عند من يشعرون أنه لا يؤثر فيهم — فالشعور الذاتي بأنك تنام بشكل جيد دليل ضعيف على جودة النوم في وقت لاحق من الليل. اختبار بسيط قليل الجهد: جرّب حدا زمنيا في منتصف بعد الظهر لأسبوع وانظر إلى خط جودة نومك، لا إلى شعورك عند النوم.",
      zh: "白天较晚摄入咖啡因，与更浅、更碎片化的睡眠相关，即使在自认为不受影响的人身上也是如此——主观上觉得自己入睡没问题，并不能很好地反映后半夜的睡眠质量。一个简单省力的检验：试着在下午中段设一个截止时间，坚持一周，然后看你的睡眠质量那条线，而不是看你入睡时的感觉。",
    },
    {
      key: 'hydration_breaks',
      match: /\b(hydration|drink (more )?water|water break)(?:s|es|ing)?\b|آب بخورم|وقفه‌ی آب|نوشیدن آب|شرب الماء|استراحة ماء|أشرب ماء أكثر|喝水|补水|喝水间歇|多喝水/i,
      en: "This isn't something the model scores directly, but it pairs naturally with the movement breaks that do show up in your data: getting up to refill a glass of water is a built-in excuse to stand, walk a few steps and look away from the screen — three things that are individually useful, bundled into one easy-to-remember action.",
      fa: "این چیزی نیست که مدل مستقیم امتیاز بدهد، اما طبیعی با همان وقفه‌های حرکتی جفت می‌شود که در داده‌ات ظاهر می‌شوند: بلندشدن برای پرکردن یک لیوان آب یک بهانه‌ی داخلی برای ایستادن، چند قدم راه‌رفتن و نگاه‌کردن به دور از صفحه است — سه چیز که هرکدام به‌تنهایی مفیدند، در یک عمل ساده و به‌یادماندنی بسته‌بندی شده‌اند.",
      ar: "هذا ليس شيئا يُقيّمه النموذج مباشرة، لكنه يقترن طبيعيا بفترات الحركة التي تظهر فعلا في بياناتك: النهوض لإعادة ملء كأس ماء عذر مبني للوقوف والمشي بضع خطوات والنظر بعيدا عن الشاشة — ثلاثة أمور تساعد أجزاء أخرى من درجتك. اعتبره حصان طروادة لفترة راحة لا هدفا صحيا بنفسه.",
      zh: "这不是模型直接评分的东西，但它与确实出现在你数据里的活动间歇天然配对：起身去倒一杯水，本身就是站起来、走几步、把视线从屏幕上移开的现成理由——而这三件事都对你分数的其他部分有帮助。把它当作一次休息的特洛伊木马，而不是一个本身的健康目标。",
    },
    {
      key: 'jomo',
      match: /\b(jomo|joy of missing out|okay to miss out|fine (to|with) miss(ing)? out)(?:s|es|ing)?\b|شادی از دست ندادن|اشکالی ندارد از دست بدهم|متعة الفوات|لا بأس أن يفوتني|سعادة عدم المتابعة|错失的乐趣|错过也没关系|不怕错过/i,
      en: "JOMO is really just FOMO's mechanism run in the other direction: deliberately deciding in advance that missing a specific thing is fine, so there's nothing left to anxiously check for later. It tends to work best applied narrowly — one specific event or thread you've decided not to track — rather than as a vague overall goal to 'care less', which is much harder to actually act on.",
      fa: "JOMO (شادی از دست‌ندادن) واقعاً همان مکانیزم FOMO است که در جهت دیگر اجرا می‌شود: از قبل و عمداً تصمیم‌گرفتن که از‌دست‌دادن یک چیز مشخص اشکالی ندارد، تا چیزی برای چک‌کردن اضطرابی بعداً نماند. معمولاً وقتی محدود و مشخص اعمال شود بهتر جواب می‌دهد — یک رویداد یا رشته‌ی مشخص که تصمیم گرفته‌ای دنبال نکنی — تا یک هدف کلی و مبهم برای «کمتر اهمیت‌دادن» که عمل‌کردن بهش خیلی سخت‌تر است.",
      ar: "متعة الفوات في الحقيقة ليست إلا آلية الخوف من الفوات معكوسة: أن تقرر مسبقا وبشكل متعمد أن تفويت شيء محدد أمر لا بأس به، فلا يبقى شيء لتتحقق منه بقلق لاحقا. تعمل أفضل عند تطبيقها بضيق — حدث واحد محدد أو خيط محادثة واحد — لا كموقف عام تجاه كل المعلومات.",
      zh: "错失的乐趣其实只是错失恐惧这套机制反过来运行：事先刻意决定错过某件特定的事没关系，于是之后就没有什么需要焦虑地去查看了。它在被窄窄地使用时效果最好——针对某一个具体的活动或某一条对话线——而不是当作对一切信息的笼统态度。",
    },
    {
      key: 'habit_building',
      match: /\b(habit|routine|consistent|stick to|stick|sticking|motivation|discipline|how do i start|willpower)(?:s|es|ing)?\b|عادت|روتین|ثبات|انگیزه|انضباط|از کجا شروع|عادة|روتين|ثبات|التزام|حافز|انضباط|كيف أبدأ|قوة الإرادة|习惯|routine|routine|坚持|一致|动力|自律|怎么开始|意志力/i,
      en: "The pattern that actually works here is unglamorous: one change, made small enough that it survives a bad week. Adding friction beats relying on willpower — moving an app off the home screen, charging the phone elsewhere, scheduling Do Not Disturb. And measure it, which you're already doing; people consistently underestimate their own screen time, usually by a wide margin, so the check-in itself is doing real work even before you change anything.",
      fa: "الگویی که واقعاً اینجا جواب می‌دهد پرزرق‌وبرق نیست: یک تغییر، آن‌قدر کوچک که از یک هفته‌ی بد جان سالم به در ببرد. اضافه‌کردن اصطکاک از تکیه بر اراده بهتر است — برداشتن یک اپ از صفحه‌ی اصلی، شارژ گوشی جای دیگر، زمان‌بندی «مزاحم نشوید». و اندازه‌گیری‌اش کن، که همین حالا داری انجام می‌دهی؛ مردم مدام زمان استفاده‌ی خودشان را کمتر از واقعیت تخمین می‌زنند، اغلب با اختلاف زیاد، پس خود بررسی حتی قبل از هر تغییری دارد کار واقعی انجام می‌دهد.",
      ar: "النمط الذي ينجح فعلا هنا غير براق: تغيير واحد، صغير بما يكفي ليصمد في أسبوع سيئ. إضافة الاحتكاك تتفوق على الاعتماد على الإرادة — نقل تطبيق بعيدا عن الشاشة الرئيسية، شحن الهاتف في مكان آخر، جدولة عدم الإزعاج. وقِس شيئا واحدا فقط، لأن تتبع خمسة تغييرات معا يعني ألا تعرف أيها عمل.",
      zh: "在这里真正有效的模式并不光鲜：一次只改一件事，而且小到能在糟糕的一周里存活下来。增加摩擦胜过依赖意志力——把某个应用从主屏幕移走、在别处给手机充电、给免打扰设定时间。而且只衡量一件事，因为同时追踪五个改变，就等于不知道哪一个起了作用。",
    },
    {
      key: 'app_usage',
      match: /\b(how do i use|what can (you|this) do|help me|features|what should i do here|get started|guide)(?:s|es|ing)?\b|چطور استفاده کنم|چیکار می‌تونی|کمکم کن|از کجا شروع کنم|راهنما|كيف أستخدم|ماذا يمكن أن تفعل|ساعدني|ميزات|ماذا أفعل هنا|كيف أبدأ|دليل|怎么用|你能做什么|帮我|功能|从哪开始|指南|新手/i,
      en: "Here's the short version: run a check-in, and you get a real score with the specific reasons behind it plus recommendations. The Dashboard tracks it over time, the Weekly Plan turns your weakest areas into a seven-day list, What-if lets you test a change before committing to it, and Analytics shows your trend once you have a few days logged. Ask me about any of your results and I'll use your actual data — or tap the guide character on any page and it'll explain what that screen does.",
      fa: "نسخه‌ی کوتاهش این است: یک بررسی انجام بده، و یک امتیاز واقعی با دلایل مشخصش به‌همراه توصیه‌ها می‌گیری. داشبورد آن را در طول زمان ردیابی می‌کند، برنامه‌ی هفتگی ضعیف‌ترین حوزه‌هایت را به یک فهرست هفت‌روزه تبدیل می‌کند، شبیه‌ساز اجازه می‌دهد یک تغییر را قبل از تعهد به آن آزمایش کنی، و تحلیل‌ها بعد از چند روز ثبت، روندت را نشان می‌دهد. درباره‌ی هرکدام از نتایجت از من بپرس تا از داده‌ی واقعی‌ات استفاده کنم — یا روی شخصیت راهنما در هر صفحه بزن تا توضیح بدهد آن صفحه چه می‌کند.",
      ar: "النسخة القصيرة: نفّذ تسجيلا، وتحصل على درجة حقيقية مع الأسباب المحددة خلفها بالإضافة إلى توصيات. لوحة المعلومات تتابعها عبر الوقت، والخطة الأسبوعية تحوّل أضعف مجالاتك إلى قائمة سبعة أيام، وماذا-لو تتيح لك اختبار تغيير قبل القيام به، ودوري الأصدقاء اختياري بالكامل ولا يشارك شيئا لم توافق عليه صراحة. اكتب /fit إن أردت تحميل أحدث تسجيل لك كسياق.",
      zh: "简短版本：做一次记录，你就会得到一个真实的分数、它背后的具体原因，以及相应建议。仪表盘按时间追踪它，每周计划把你最弱的方面变成一份七天清单，假设推演让你在真正行动前先测试一个改变，好友联赛完全可选、且不会分享任何你未明确同意的内容。如果你想让我把你最新的记录作为上下文加载，请输入 /fit。",
    },
    {
      key: 'greeting',
      match: /^(hi|hey|hello|yo|salam|good (morning|evening|afternoon))(?:s|es|ing)?\b|^(سلام|درود|چطوری)|^(مرحبا|أهلا|سلام عليكم|صباح الخير|مساء الخير)|^(你好|您好|嗨|哈喽|早上好|晚上好)/i,
      en: "Hey. I'm here for anything about your digital wellbeing — your score, a specific area like sleep or focus, or what to change first. Type /fit if you want me to load your latest check-in as context.",
      fa: "سلام. برای هر چیزی درباره‌ی سلامت دیجیتالت اینجا هستم — امتیازت، یک حوزه‌ی خاص مثل خواب یا تمرکز، یا اینکه اول چه چیزی را تغییر بدهی. اگر می‌خواهی آخرین بررسی‌ات را به‌عنوان زمینه بارگذاری کنم، /fit را بزن.",
      ar: "أهلا. أنا هنا لأي شيء يتعلق بعافيتك الرقمية — درجتك، أو مجال محدد كالنوم أو التركيز، أو ما ينبغي تغييره أولا. اكتب /fit إن أردت أن أحمّل أحدث تسجيل لك كسياق.",
      zh: "你好。关于你的数字健康，任何问题都可以问我——你的分数、某个具体方面（比如睡眠或专注），或者该先改变什么。如果你想让我把你最新的记录作为上下文加载，请输入 /fit。",
    },
    {
      key: 'thanks',
      match: /\b(thanks|thank you|thx|appreciate|cheers)(?:s|es|ing)?\b|ممنون|مرسی|سپاس|شكرا|شكرًا|ممتن|أشكرك|谢谢|感谢|多谢|谢啦/i,
      en: "Any time. If you want to go deeper on one area, just name it — sleep, focus, notifications, night use, activity.",
      fa: "هر وقت خواستی. اگر می‌خواهی روی یک حوزه عمیق‌تر شویم، فقط اسمش را بگو — خواب، تمرکز، اعلان‌ها، استفاده‌ی شبانه، فعالیت.",
      ar: "في أي وقت. إن أردت التعمق في مجال واحد، فسمّه فقط — النوم، التركيز، الإشعارات، الاستخدام الليلي، النشاط.",
      zh: "随时。如果你想深入某一个方面，直接说出来就行——睡眠、专注、通知、夜间使用、身体活动。",
    },
  ];

  /* Topics contributed by add-on modules (coach-knowledge-*.js). Kept in
     a separate list so this file stays reviewable as the base set grows.

     Ordering is the whole game: the first match wins, so a broad topic
     like `sleep` would swallow a specific one like `naps` or `shift
     work` if it were tested first. Rather than depending on file load
     order, every topic carries a `priority` (default 0) and matching
     runs highest-first. Specific add-ons register at +10; the handful of
     deliberately broad catch-alls in this file sit at -10. */
  const EXTRA_TOPICS = [];

  const BROAD_KEYS = new Set(['sleep', 'focus', 'social', 'screen_time', 'night', 'stress', 'activity']);

  function priorityOf(topic) {
    if (typeof topic.priority === 'number') return topic.priority;
    return BROAD_KEYS.has(topic.key) ? -10 : 0;
  }

  /** Add topics from an add-on module. Later duplicates of a key lose. */
  function register(topics, opts) {
    const priority = (opts && typeof opts.priority === 'number') ? opts.priority : 10;
    const seen = new Set(allTopics().map((t) => t.key));
    (topics || []).forEach((t) => {
      if (!t || !t.key || !t.match || seen.has(t.key)) return;
      EXTRA_TOPICS.push(Object.assign({ priority }, t));
      seen.add(t.key);
    });
    topicsVersion += 1;
  }

  function allTopics() {
    return TOPICS.concat(EXTRA_TOPICS);
  }

  /* ---- Scored fuzzy matching (see coach-nlu.js) ----
     Previously: first regex whose .test() passed won, so a paraphrase or
     a misspelling that didn't hit any exact pattern fell through to a
     generic reply even when a topic below it was a much closer match.
     Now every topic is scored and the best one wins; an exact regex hit
     still scores 1.0 so nothing that used to match stops matching.
     The intent list is rebuilt only when the topic set actually changes
     (register() bumps `topicsVersion`), not on every keystroke. */
  let topicsVersion = 0;
  let intentsCache = null;
  let intentsCacheVersion = -1;

  function intentsForNLU() {
    if (!window.DWCoachNLU) return [];
    if (intentsCache && intentsCacheVersion === topicsVersion) return intentsCache;
    intentsCache = allTopics().map((t) => ({
      key: t.key,
      pattern: t.match,
      keywords: window.DWCoachNLU.extractKeywords(t.match.source),
      weight: priorityOf(t),
      topic: t,
    }));
    intentsCacheVersion = topicsVersion;
    return intentsCache;
  }

  /** Best-scoring topic for this text, or null if nothing clears the
   *  fuzzy-match threshold. Falls back to plain regex testing if
   *  coach-nlu.js somehow failed to load, so this never throws. */
  function findTopic(text) {
    const q = String(text || '');
    if (!q) return null;
    if (!window.DWCoachNLU) {
      const ordered = allTopics().slice().sort((a, b) => priorityOf(b) - priorityOf(a));
      return ordered.find((t) => t.match.test(q)) || null;
    }
    const result = window.DWCoachNLU.classify(q, intentsForNLU());
    return result.match ? result.match.topic : null;
  }

  /** Same as findTopic, but when nothing clears the threshold this also
   *  returns the two closest topics (by score) so the caller can offer an
   *  honest "did you mean" instead of a flat refusal. */
  function findTopicWithSuggestions(text) {
    const q = String(text || '');
    if (!q || !window.DWCoachNLU) return { topic: findTopic(q), near: [] };
    const result = window.DWCoachNLU.classify(q, intentsForNLU());
    if (result.match) return { topic: result.match.topic, near: [] };
    const near = result.ranked
      .filter((r) => r.score > 0)
      .slice(0, 2)
      .map((r) => r.intent.topic);
    return { topic: null, near };
  }

  function topicCount() { return allTopics().length; }

  function textFor(topic, lang) {
    if (!topic) return null;
    return topic[lang] || topic.en;
  }

  /* Follow-up prompts offered as clickable chips, so a user who doesn't
     know what to ask still has a way in. */
  /* Starter prompts. The first two now cover the two halves of the
     week's plan, because a blank chat box is the hardest thing to
     answer and those two questions are the ones the plan can answer
     best - one from the strengthen track, one from the maintain track
     (see coach-chat.js::strengthenAnswer / maintainAnswer). */
  const SUGGESTIONS = {
    en: ['What should I work on?', 'What am I doing well?', 'What is my score?', 'What should I fix first?', 'How is my score calculated?', 'Help me sleep better', 'Why is my focus low?', 'Is my notification load too high?', 'Help me build a habit that sticks'],
    fa: ['روی چی کار کنم؟', 'چی خوب پیش می‌رود؟', 'امتیازم چند است؟', 'اول چه چیزی را درست کنم؟', 'امتیازم چطور محاسبه می‌شود؟', 'برای خواب بهتر کمکم کن', 'چرا تمرکزم پایین است؟', 'اعلان‌هایم زیاد است؟', 'کمکم کن یک عادت پایدار بسازم'],
    ar: ['على ماذا أعمل؟', 'ما الذي أفعله جيدا؟', 'ما هي درجتي؟', 'ما الذي يجب أن أصلحه أولا؟', 'كيف تُحسب درجتي؟', 'ساعدني على نوم أفضل', 'لماذا تركيزي منخفض؟', 'هل حجم إشعاراتي مرتفع جدا؟', 'ساعدني على بناء عادة تدوم'],
    zh: ['我该加强什么？', '我哪里做得好？', '我的分数是多少？', '我该先改善什么？', '我的分数是怎么算的？', '帮我改善睡眠', '我的专注力为什么低？', '我的通知量是不是太大了？', '帮我养成一个能坚持的习惯'],
  };

  function suggestionsFor(lang) {
    return SUGGESTIONS[lang] || SUGGESTIONS.en;
  }

  window.DWCoachKnowledge = { TOPICS, findTopic, findTopicWithSuggestions, textFor, suggestionsFor, register, allTopics, topicCount };
})();
