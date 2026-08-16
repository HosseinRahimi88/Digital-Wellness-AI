/*
  DWAboutTeam — the four people, and the résumé behind each card.

  A grid of cards; clicking one opens that person's profile as FIVE
  separate panels rather than one block of prose:

      Personal details · Role on this project · Experience ·
      Skills · Contact

  Five panels because a résumé is read by scanning, not by reading: a
  reviewer looking for "what did this person actually do here" should
  find it under a heading with that name, not three paragraphs into a
  biography.

  The panel is DWSheet (assets/js/sheet.js) rather than a fourth
  hand-rolled modal, so focus trapping, Escape, the backdrop, the
  scroll lock and focus restoration are the ones the rest of the app
  already uses.

  Register is formal and impersonal throughout - "Integrated five
  official datasets", not "she integrated" - which is how a résumé
  reads in all four of these languages, and which also avoids assigning
  anybody a pronoun they did not state.

  Everything here is what each person supplied about themselves.
  Nothing about anybody's role is inferred: where somebody described a
  contribution to this project it appears under that heading, and where
  they did not, that panel simply does not exist. A team page that
  guesses is worse than one with an uneven shape.
*/
(function () {
  const LANGS = ['en', 'fa', 'ar', 'zh'];

  function lang() {
    const l = window.DWI18n && window.DWI18n.get ? window.DWI18n.get() : 'en';
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }

  function pick(bundle) {
    if (!bundle) return '';
    if (typeof bundle === 'string') return bundle;
    return bundle[lang()] || bundle.en || '';
  }

  function esc(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  const HEAD = {
    eyebrow: { en: 'Innoverse 2026', fa: 'اینوورس ۲۰۲۶', ar: 'إنوفيرس ٢٠٢٦', zh: 'Innoverse 2026' },
    title: {
      en: 'The team', fa: 'تیم', ar: 'الفريق', zh: '团队',
    },
    lede: {
      en: 'Four people, four defined roles on the same system. Select a card to open that person’s full résumé.',
      fa: 'چهار نفر، چهار نقش مشخص روی یک سامانه. برای دیدن رزومه‌ی کامل هر فرد، کارتش را انتخاب کنید.',
      ar: 'أربعة أشخاص، وأربعة أدوار محددة في النظام نفسه. اختر بطاقة لفتح السيرة الذاتية الكاملة لصاحبها.',
      zh: '四个人，在同一个系统上担任四个明确的角色。点击卡片可查看该成员的完整简历。',
    },
    open: { en: 'View résumé', fa: 'مشاهده‌ی رزومه', ar: 'عرض السيرة الذاتية', zh: '查看简历' },
  };

  /* The five panel headings, in the order they are shown. */
  const PANELS = {
    personal: { en: 'Personal details', fa: 'اطلاعات شخصی', ar: 'المعلومات الشخصية', zh: '个人信息' },
    project: { en: 'Role on this project', fa: 'نقش در این پروژه', ar: 'الدور في هذا المشروع', zh: '在本项目中的角色' },
    experience: { en: 'Experience', fa: 'تجربه', ar: 'الخبرة', zh: '经历' },
    achievements: { en: 'Achievements', fa: 'دستاوردها', ar: 'الإنجازات', zh: '成就' },
    skills: { en: 'Skills', fa: 'مهارت‌ها', ar: 'المهارات', zh: '技能' },
    contact: { en: 'Contact', fa: 'راه ارتباطی', ar: 'وسائل التواصل', zh: '联系方式' },
  };

  /* Field labels used inside the personal-details table. */
  const F = {
    role: { en: 'Title', fa: 'عنوان', ar: 'المسمى', zh: '职位' },
    focus: { en: 'Focus', fa: 'حوزه‌ی تمرکز', ar: 'مجال التركيز', zh: '专注领域' },
    status: { en: 'Status', fa: 'وضعیت', ar: 'الحالة', zh: '状态' },
    based: { en: 'Based in', fa: 'محل زندگی', ar: 'مقر الإقامة', zh: '所在地' },
    age: { en: 'Age', fa: 'سن', ar: 'العمر', zh: '年龄' },
    languages: { en: 'Working languages', fa: 'زبان‌های کاری', ar: 'لغات العمل', zh: '工作语言' },
  };

  const MEMBERS = [
    {
      id: 'parisa',
      accent: 'var(--neon-cyan)',
      initials: 'PP',
      name: { en: 'Parisa Pourreza', fa: 'پریسا پوررضا', ar: 'پریسا پوررضا', zh: 'Parisa Pourreza' },
      role: {
        en: 'AI Developer & Programmer',
        fa: 'توسعه‌دهنده‌ی هوش مصنوعی و برنامه‌نویس',
        ar: 'مطوّرة ذكاء اصطناعي ومبرمجة',
        zh: 'AI 开发者与程序员',
      },
      tagline: {
        en: 'Datasets, model training, and the testing that finds what is wrong with them.',
        fa: 'مجموعه‌داده‌ها، آموزش مدل، و آزمونی که ایرادهایشان را پیدا می‌کند.',
        ar: 'مجموعات البيانات وتدريب النماذج والاختبار الذي يكشف عيوبها.',
        zh: '数据集、模型训练，以及找出它们问题的测试。',
      },
      summary: {
        en: 'AI developer and programmer specialising in Python, machine learning and applied AI systems. Principal interest is the path from a working idea to a system that runs, and the use of data to solve problems that are actually in front of the user.',
        fa: 'توسعه‌دهنده‌ی هوش مصنوعی و برنامه‌نویس، با تخصص در پایتون، یادگیری ماشین و سامانه‌های کاربردی هوش مصنوعی. تمرکز اصلی بر مسیرِ تبدیل یک ایده‌ی کارآمد به سامانه‌ای است که واقعاً اجرا می‌شود، و بر استفاده از داده برای حل مسائلی که پیش روی کاربر قرار دارد.',
        ar: 'مطوّرة ذكاء اصطناعي ومبرمجة متخصصة في بايثون وتعلّم الآلة وأنظمة الذكاء الاصطناعي التطبيقية. اهتمامها الأساسي هو المسار من فكرة صالحة إلى نظام يعمل فعلًا، واستخدام البيانات لحل المشكلات القائمة أمام المستخدم.',
        zh: 'AI 开发者与程序员，专长为 Python、机器学习与应用型 AI 系统。核心关注点在于把一个可行的想法转化为真正运行的系统，并用数据解决用户面前的实际问题。',
      },
      personal: [
        { label: F.status, value: { en: 'AI developer, Innoverse 2026 team member', fa: 'توسعه‌دهنده‌ی هوش مصنوعی، عضو تیم اینوورس ۲۰۲۶', ar: 'مطوّرة ذكاء اصطناعي، عضوة فريق إنوفيرس ٢٠٢٦', zh: 'AI 开发者，Innoverse 2026 团队成员' } },
        { label: F.focus, value: { en: 'Machine learning · data preparation · computer vision', fa: 'یادگیری ماشین · آماده‌سازی داده · بینایی ماشین', ar: 'تعلّم الآلة · إعداد البيانات · الرؤية الحاسوبية', zh: '机器学习 · 数据准备 · 计算机视觉' } },
      ],
      project: [
        {
          en: 'Contributed to the conception and the development of Digital Wellness AI from the outset.',
          fa: 'از ابتدا در شکل‌گیری ایده و توسعه‌ی Digital Wellness AI مشارکت داشته است.',
          ar: 'ساهمت في بلورة الفكرة وفي تطوير Digital Wellness AI منذ البداية.',
          zh: '自项目伊始即参与 Digital Wellness AI 的构思与开发。',
        },
        {
          en: 'Integrated five official datasets into a single usable training set.',
          fa: 'پنج مجموعه‌داده‌ی رسمی را در یک مجموعه‌ی آموزشیِ واحد و قابل‌استفاده یکپارچه کرده است.',
          ar: 'دمجت خمس مجموعات بيانات رسمية في مجموعة تدريب واحدة قابلة للاستخدام.',
          zh: '将五个官方数据集整合为一个统一可用的训练集。',
        },
        {
          en: 'Prepared and balanced the data, and trained models on it.',
          fa: 'داده را آماده و متوازن کرده و مدل‌ها را روی آن آموزش داده است.',
          ar: 'أعدّت البيانات ووازنتها ودرّبت النماذج عليها.',
          zh: '完成数据准备与平衡，并在其上训练模型。',
        },
        {
          en: 'Implemented new ideas and tested the results to identify defects and improve the system.',
          fa: 'ایده‌های تازه را پیاده‌سازی کرده و نتایج را آزموده تا ایرادها شناسایی و سامانه بهبود داده شود.',
          ar: 'نفّذت أفكارًا جديدة واختبرت النتائج لتحديد العيوب وتحسين النظام.',
          zh: '实现新的想法并测试结果，以发现缺陷并改进系统。',
        },
      ],
      experience: [
        {
          title: { en: 'Computer vision, OpenCV', fa: 'بینایی ماشین، OpenCV', ar: 'الرؤية الحاسوبية، OpenCV', zh: '计算机视觉，OpenCV' },
          detail: {
            en: 'Face recognition and face tracking; licence-plate processing; image and video processing.',
            fa: 'تشخیص چهره و ردیابی چهره؛ پردازش پلاک خودرو؛ پردازش تصویر و ویدیو.',
            ar: 'التعرّف على الوجوه وتتبّعها؛ معالجة لوحات المركبات؛ معالجة الصور والفيديو.',
            zh: '人脸识别与人脸追踪；车牌处理；图像与视频处理。',
          },
        },
        {
          title: { en: 'Speech processing', fa: 'پردازش گفتار', ar: 'معالجة الكلام', zh: '语音处理' },
          detail: {
            en: 'Speech-to-text systems.',
            fa: 'سامانه‌های تبدیل گفتار به متن.',
            ar: 'أنظمة تحويل الكلام إلى نص.',
            zh: '语音转文字系统。',
          },
        },
        {
          title: { en: 'Objective', fa: 'هدف حرفه‌ای', ar: 'الهدف المهني', zh: '职业目标' },
          detail: {
            en: 'Continued specialisation in AI, and the delivery of useful, reliable AI products for real-world use.',
            fa: 'تخصص‌یابی مستمر در هوش مصنوعی و ارائه‌ی محصولات مفید و قابل‌اتکا برای کاربرد واقعی.',
            ar: 'مواصلة التخصص في الذكاء الاصطناعي وتقديم منتجات مفيدة وموثوقة للاستخدام الواقعي.',
            zh: '在 AI 领域持续深耕，交付面向真实场景的、可用且可靠的 AI 产品。',
          },
        },
      ],
      skills: [
        'Python', 'Machine Learning',
        { en: 'Dataset integration', fa: 'یکپارچه‌سازی مجموعه‌داده', ar: 'دمج مجموعات البيانات', zh: '数据集整合' },
        { en: 'Data preparation', fa: 'آماده‌سازی داده', ar: 'إعداد البيانات', zh: '数据准备' },
        { en: 'Class balancing', fa: 'متوازن‌سازی داده', ar: 'موازنة الفئات', zh: '类别平衡' },
        { en: 'Model training', fa: 'آموزش مدل', ar: 'تدريب النماذج', zh: '模型训练' },
        { en: 'Testing & defect analysis', fa: 'آزمون و تحلیل ایراد', ar: 'الاختبار وتحليل العيوب', zh: '测试与缺陷分析' },
        'OpenCV',
        { en: 'Computer vision', fa: 'بینایی ماشین', ar: 'الرؤية الحاسوبية', zh: '计算机视觉' },
        { en: 'Speech-to-text', fa: 'گفتار به متن', ar: 'الكلام إلى نص', zh: '语音转文字' },
      ],
      links: [
        { kind: 'email', text: 'parisa.developerai@gmail.com', href: 'mailto:parisa.developerai@gmail.com' },
        { kind: 'telegram', text: '@Parisaa_prz', href: 'https://t.me/Parisaa_prz' },
        { kind: 'github', text: 'parisa-dev-ai', href: 'https://github.com/parisa-dev-ai' },
        { kind: 'site', text: 'parisaai.ir', href: 'http://parisaai.ir/index.html' },
      ],
    },

    {
      id: 'hossein',
      accent: 'var(--neon-blue)',
      initials: 'HR',
      name: { en: 'Hossein Rahimi', fa: 'حسین رحیمی', ar: 'حسین رحیمی', zh: 'Hossein Rahimi' },
      role: {
        en: 'AI Developer & Programmer',
        fa: 'توسعه‌دهنده‌ی هوش مصنوعی و برنامه‌نویس',
        ar: 'مطوّر ذكاء اصطناعي ومبرمج',
        zh: 'AI 开发者与程序员',
      },
      tagline: {
        en: 'The ML pipeline, its performance, and the modular architecture holding it together.',
        fa: 'پایپ‌لاین یادگیری ماشین، کارایی آن، و معماری ماژولاری که آن را کنار هم نگه می‌دارد.',
        ar: 'خط معالجة تعلّم الآلة وأداؤه والبنية المعيارية التي تجمعه.',
        zh: '机器学习流水线、其性能，以及支撑它的模块化架构。',
      },
      summary: {
        en: 'Programmer working towards AI development, with a defined interest in deep learning, machine learning and AI that has to operate in production conditions. Principal activity is the construction of AI systems, the improvement of model performance, pipeline optimisation, and the resolution of technical problems by experiment.',
        fa: 'برنامه‌نویس در مسیر توسعه‌ی هوش مصنوعی، با علاقه‌ی مشخص به یادگیری عمیق، یادگیری ماشین و هوش مصنوعی‌ای که باید در شرایط واقعی کار کند. فعالیت اصلی: ساخت سامانه‌های هوش مصنوعی، بهبود کارایی مدل، بهینه‌سازی پایپ‌لاین، و حل مسائل فنی از راه آزمایش.',
        ar: 'مبرمج يتجه نحو تطوير الذكاء الاصطناعي، باهتمام محدد بالتعلّم العميق وتعلّم الآلة والذكاء الاصطناعي الذي يجب أن يعمل في ظروف حقيقية. نشاطه الأساسي بناء أنظمة الذكاء الاصطناعي وتحسين أداء النماذج وتحسين خطوط المعالجة وحل المشكلات التقنية بالتجربة.',
        zh: '走向 AI 开发的程序员，明确关注深度学习、机器学习以及必须在真实条件下运行的 AI。主要工作包括构建 AI 系统、提升模型表现、优化流水线，并通过实验解决技术问题。',
      },
      personal: [
        { label: F.status, value: { en: 'AI developer, Innoverse 2026 team member', fa: 'توسعه‌دهنده‌ی هوش مصنوعی، عضو تیم اینوورس ۲۰۲۶', ar: 'مطوّر ذكاء اصطناعي، عضو فريق إنوفيرس ٢٠٢٦', zh: 'AI 开发者，Innoverse 2026 团队成员' } },
        { label: F.focus, value: { en: 'Deep learning · model optimisation · computer vision', fa: 'یادگیری عمیق · بهینه‌سازی مدل · بینایی ماشین', ar: 'التعلّم العميق · تحسين النماذج · الرؤية الحاسوبية', zh: '深度学习 · 模型优化 · 计算机视觉' } },
      ],
      project: [
        {
          en: 'Developed and optimised parts of the machine-learning pipeline.',
          fa: 'بخش‌هایی از پایپ‌لاین یادگیری ماشین را توسعه داده و بهینه کرده است.',
          ar: 'طوّر وحسّن أجزاءً من خط معالجة تعلّم الآلة.',
          zh: '开发并优化了机器学习流水线的多个部分。',
        },
        {
          en: 'Worked extensively on model performance and on the overall speed of the system.',
          fa: 'به‌طور گسترده روی کارایی مدل و سرعت کلی سامانه کار کرده است.',
          ar: 'عمل بشكل موسّع على أداء النماذج وعلى سرعة النظام ككل.',
          zh: '在模型表现与系统整体速度方面投入大量工作。',
        },
        {
          en: 'Contributed to the modular architecture on which the project is built.',
          fa: 'در معماری ماژولاری که پروژه بر پایه‌ی آن ساخته شده مشارکت داشته است.',
          ar: 'ساهم في البنية المعيارية التي بُني عليها المشروع.',
          zh: '参与构建了项目所依托的模块化架构。',
        },
        {
          en: 'Carried out debugging, testing and resolution of technical issues throughout development.',
          fa: 'در تمام مسیر توسعه، اشکال‌زدایی، آزمون و رفع مسائل فنی را بر عهده داشته است.',
          ar: 'تولّى التصحيح والاختبار وحل المشكلات التقنية طوال فترة التطوير.',
          zh: '在整个开发周期中负责调试、测试与技术问题的解决。',
        },
      ],
      experience: [
        {
          title: { en: '1 IDEA 1 WORLD (1I1W) — international competition', fa: 'مسابقه‌ی بین‌المللی 1 IDEA 1 WORLD (1I1W)', ar: 'مسابقة 1 IDEA 1 WORLD (1I1W) الدولية', zh: '1 IDEA 1 WORLD（1I1W）国际大赛' },
          detail: {
            en: 'Member of a team awarded a Gold Medal at this international innovation, design and startup competition.',
            fa: 'عضو تیمی که در این مسابقه‌ی بین‌المللی نوآوری، طراحی و استارتاپ مدال طلا کسب کرد.',
            ar: 'عضو في فريق نال الميدالية الذهبية في هذه المسابقة الدولية للابتكار والتصميم والشركات الناشئة.',
            zh: '所在团队在该国际创新、设计与创业大赛中获得金牌。',
          },
        },
        {
          title: { en: 'Deep-learning practice', fa: 'کار عملی یادگیری عمیق', ar: 'ممارسة التعلّم العميق', zh: '深度学习实践' },
          detail: {
            en: 'Built and experimented with deep-learning models on that project.',
            fa: 'در همان پروژه مدل‌های یادگیری عمیق را ساخته و روی آن‌ها آزمایش کرده است.',
            ar: 'بنى نماذج تعلّم عميق وأجرى تجارب عليها في ذلك المشروع.',
            zh: '在该项目中构建深度学习模型并开展实验。',
          },
        },
        {
          title: { en: 'Objective', fa: 'هدف حرفه‌ای', ar: 'الهدف المهني', zh: '职业目标' },
          detail: {
            en: 'Deep learning, computer vision, model optimisation, and AI systems that hold up outside a notebook.',
            fa: 'یادگیری عمیق، بینایی ماشین، بهینه‌سازی مدل، و سامانه‌های هوش مصنوعی که بیرون از نوت‌بوک هم دوام می‌آورند.',
            ar: 'التعلّم العميق والرؤية الحاسوبية وتحسين النماذج وأنظمة ذكاء اصطناعي تصمد خارج دفتر التجارب.',
            zh: '深度学习、计算机视觉、模型优化，以及能走出 notebook 的 AI 系统。',
          },
        },
      ],
      skills: [
        'Python', 'Deep Learning', 'Machine Learning', 'Pandas', 'NumPy',
        'scikit-learn', 'XGBoost',
        { en: 'Feature engineering', fa: 'مهندسی ویژگی', ar: 'هندسة الخصائص', zh: '特征工程' },
        { en: 'Model optimisation', fa: 'بهینه‌سازی مدل', ar: 'تحسين النماذج', zh: '模型优化' },
        { en: 'Modular architecture', fa: 'معماری ماژولار', ar: 'بنية معيارية', zh: '模块化架构' },
        { en: 'Debugging', fa: 'اشکال‌زدایی', ar: 'تصحيح الأخطاء', zh: '调试' },
      ],
      links: [
        { kind: 'email', text: 'riarash47@gmail.com', href: 'mailto:riarash47@gmail.com' },
        { kind: 'telegram', text: '@arashh_rahimi', href: 'https://t.me/arashh_rahimi' },
        { kind: 'github', text: 'HosseinRahimi88', href: 'https://github.com/HosseinRahimi88' },
      ],
    },

    {
      id: 'amirhesam',
      accent: 'var(--accent-amber)',
      initials: 'AM',
      name: { en: 'AmirHesam Moharrabi', fa: 'امیرحسام محربی', ar: 'امیرحسام محربی', zh: 'AmirHesam Moharrabi' },
      role: {
        en: 'R&D · Lead Ideator · Technical Strategist',
        fa: 'تحقیق و توسعه · ایده‌پرداز اصلی · استراتژیست فنی',
        ar: 'البحث والتطوير · صاحب الفكرة الرئيسي · استراتيجي تقني',
        zh: '研发 · 首席构想者 · 技术策略',
      },
      tagline: {
        en: 'Where the project’s idea came from, and how its process is run.',
        fa: 'ایده‌ی پروژه از کجا آمد، و روند کار چگونه اداره می‌شود.',
        ar: 'من أين جاءت فكرة المشروع، وكيف تُدار عمليته.',
        zh: '这个项目的想法从何而来，以及它的流程如何推进。',
      },
      summary: {
        en: 'Research and development lead for this project, and its principal ideator. Approximately three years in AI content production, and manager of the international "Hooshmand Sho" team on the AI side. Members of that team have worked with the University of Tehran, Pasargad Insurance, and first-tier national artists on the graphics side.',
        fa: 'مسئول بخش تحقیق و توسعه‌ی این پروژه و ایده‌پرداز اصلی آن. حدود سه سال فعالیت در تولید محتوا با هوش مصنوعی، و مدیر تیم بین‌المللی «هوشمند شو» در بخش هوش مصنوعی. اعضای آن تیم سابقه‌ی همکاری با دانشگاه تهران، بیمه‌ی پاسارگاد و خواننده‌های سطح‌یک کشور را در حوزه‌ی گرافیک دارند.',
        ar: 'مسؤول البحث والتطوير في هذا المشروع وصاحب فكرته الأساسي. نحو ثلاث سنوات في إنتاج محتوى الذكاء الاصطناعي، ومدير فريق «هوشمند شو» الدولي في جانب الذكاء الاصطناعي. عمل أعضاء ذلك الفريق مع جامعة طهران وتأمين باسارغاد ومع فنانين من الصف الأول في مجال الغرافيك.',
        zh: '本项目的研发负责人与主要构想者。约三年 AI 内容制作经验，并担任国际团队「Hooshmand Sho」AI 方向的负责人。该团队成员在图形方向曾与德黑兰大学、Pasargad 保险以及一线艺人合作。',
      },
      personal: [
        { label: F.age, value: { en: '14', fa: '۱۴ سال', ar: '١٤ عامًا', zh: '14 岁' } },
        { label: F.based, value: { en: 'Isfahan, Iran', fa: 'اصفهان، ایران', ar: 'أصفهان، إيران', zh: '伊朗，伊斯法罕' } },
        { label: F.status, value: { en: 'R&D lead, Innoverse 2026 · IFIA member since 2025', fa: 'مسئول تحقیق و توسعه، اینوورس ۲۰۲۶ · عضو IFIA از ۲۰۲۵', ar: 'مسؤول البحث والتطوير، إنوفيرس ٢٠٢٦ · عضو IFIA منذ ٢٠٢٥', zh: '研发负责人，Innoverse 2026 · 自 2025 年起为 IFIA 成员' } },
        { label: F.focus, value: { en: 'Ideation · technical strategy · AI content · team process', fa: 'ایده‌پردازی · استراتژی فنی · محتوای هوش مصنوعی · مدیریت روند تیم', ar: 'توليد الأفكار · الاستراتيجية التقنية · محتوى الذكاء الاصطناعي · إدارة سير العمل', zh: '构想 · 技术策略 · AI 内容 · 团队流程' } },
      ],
      project: [
        {
          en: 'Research and development: principal ideator of the project.',
          fa: 'بخش تحقیق و توسعه: ایده‌پرداز اصلی پروژه.',
          ar: 'البحث والتطوير: صاحب الفكرة الرئيسي للمشروع.',
          zh: '研发：项目的主要构想者。',
        },
        {
          en: 'Technical strategy: direction of what the system should attempt, and in what order.',
          fa: 'استراتژی فنی: تعیین اینکه سامانه چه چیزی را و با چه ترتیبی دنبال کند.',
          ar: 'الاستراتيجية التقنية: تحديد ما ينبغي أن يسعى إليه النظام وبأي ترتيب.',
          zh: '技术策略：确定系统应当尝试什么，以及以什么顺序推进。',
        },
        {
          en: 'Debugging: identification and reproduction of defects across the system.',
          fa: 'دیباگ‌سازی: شناسایی و بازتولید ایرادها در سراسر سامانه.',
          ar: 'التصحيح: تحديد العيوب وإعادة إنتاجها عبر النظام.',
          zh: '调试：在整个系统中定位并复现缺陷。',
        },
        {
          en: 'Team process management: coordination of the work and of its sequence.',
          fa: 'مدیریت روند تیم: هماهنگی کارها و ترتیب انجام آن‌ها.',
          ar: 'إدارة سير عمل الفريق: تنسيق الأعمال وترتيب تنفيذها.',
          zh: '团队流程管理：协调工作内容及其推进顺序。',
        },
      ],
      experience: [
        {
          title: {
            en: 'Silver medal — International Exhibition of Inventions, Switzerland',
            fa: 'مدال نقره — مسابقات بین‌المللی مخترعین جهانی، سوئیس',
            ar: 'ميدالية فضية — المعرض الدولي للاختراعات، سويسرا',
            zh: '银牌 — 瑞士国际发明展',
          },
          detail: {
            en: 'Awarded at the international inventors\' competition in Switzerland.',
            fa: 'گواهی نقره‌ی مسابقات بین‌المللی مخترعین جهانی در سوئیس.',
            ar: 'شهادة فضية من مسابقة المخترعين الدولية في سويسرا.',
            zh: '在瑞士举办的国际发明家竞赛上获得银牌证书。',
          },
        },
        {
          title: { en: 'Manager, "Hooshmand Sho" international team — AI', fa: 'مدیر تیم بین‌المللی «هوشمند شو» — بخش هوش مصنوعی', ar: 'مدير فريق «هوشمند شو» الدولي — الذكاء الاصطناعي', zh: '国际团队「Hooshmand Sho」AI 方向负责人' },
          detail: {
            en: 'Approximately three years in AI content production, latterly leading the AI side of the team.',
            fa: 'حدود سه سال فعالیت در تولید محتوا با هوش مصنوعی، و در ادامه مدیریت بخش هوش مصنوعی تیم.',
            ar: 'نحو ثلاث سنوات في إنتاج محتوى الذكاء الاصطناعي، ثم قيادة جانب الذكاء الاصطناعي في الفريق.',
            zh: '约三年 AI 内容制作经验，后期负责团队的 AI 方向。',
          },
        },
        {
          title: { en: 'Marketing specialist, international holding', fa: 'کارشناس بازاریابی، هلدینگ بین‌المللی', ar: 'أخصائي تسويق، مجموعة دولية', zh: '国际控股公司市场专员' },
          detail: {
            en: 'Approximately one year at an international holding operating in technology and operator services.',
            fa: 'حدود یک سال در یک هلدینگ بین‌المللی فعال در حوزه‌ی تکنولوژی و خدمات اپراتوری.',
            ar: 'نحو عام في مجموعة دولية تعمل في التقنية وخدمات المشغّلين.',
            zh: '在一家从事技术与运营商服务的国际控股公司约一年。',
          },
        },
        {
          title: { en: 'Community response admin, one-million-follower page', fa: 'ادمین پاسخگویی، صفحه‌ی یک‌میلیونی', ar: 'مشرف الردود، صفحة بمليون متابع', zh: '百万粉丝页面答复管理员' },
          detail: {
            en: 'Six months responding for "Gallery-e Amoozesh".',
            fa: 'شش ماه پاسخگویی برای صفحه‌ی «گالری آموزش».',
            ar: 'ستة أشهر من الرد لصفحة «غاليري آموزش».',
            zh: '为「Gallery-e Amoozesh」提供答复服务六个月。',
          },
        },
      ],
      achievements: [
        {
          en: 'Member of the International Federation of Inventors’ Associations (IFIA), 2025 to present.',
          fa: 'عضو سازمان بین‌المللی مخترعین (IFIA)، از ۲۰۲۵ تا کنون.',
          ar: 'عضو في الاتحاد الدولي لجمعيات المخترعين (IFIA) منذ ٢٠٢٥ حتى الآن.',
          zh: '自 2025 年起为国际发明家协会联合会（IFIA）成员。',
        },
        {
          en: 'Silver certificate, international inventions competition, Switzerland.',
          fa: 'گواهی نقره‌ی مسابقات بین‌المللی اختراعات سوئیس.',
          ar: 'شهادة فضية في مسابقة الاختراعات الدولية بسويسرا.',
          zh: '瑞士国际发明展银奖证书。',
        },
        {
          en: 'Winner, video production contest, Money Maker advertising festival, 2024.',
          fa: 'برنده‌ی مسابقه‌ی تولید ویدیو در جشنواره‌ی تبلیغاتی مانی‌میکر، ۲۰۲۴.',
          ar: 'الفائز بمسابقة إنتاج الفيديو في مهرجان «ماني ميكر» الإعلاني، ٢٠٢٤.',
          zh: '2024 年 Money Maker 广告节视频制作比赛冠军。',
        },
        {
          en: 'Author of several digital books: innovation and creativity; marketing, public speaking and personality typing; artificial intelligence; prompt writing.',
          fa: 'نویسنده‌ی چندین کتاب دیجیتال: نوآوری و خلاقیت؛ بازاریابی، فن بیان و شخصیت‌شناسی؛ هوش مصنوعی؛ پرامپت‌نویسی.',
          ar: 'مؤلف عدة كتب رقمية: الابتكار والإبداع؛ التسويق وفن الإلقاء وأنماط الشخصية؛ الذكاء الاصطناعي؛ كتابة الأوامر.',
          zh: '著有多本电子书：创新与创意；营销、表达与性格分析；人工智能；提示词写作。',
        },
      ],
      skills: [
        { en: 'Python', fa: 'پایتون', ar: 'بايثون', zh: 'Python' },
        { en: 'Machine learning', fa: 'یادگیری ماشین', ar: 'تعلّم الآلة', zh: '机器学习' },
        { en: 'Ideation & R&D', fa: 'ایده‌پردازی و تحقیق و توسعه', ar: 'توليد الأفكار والبحث والتطوير', zh: '构想与研发' },
        { en: 'Technical strategy', fa: 'استراتژی فنی', ar: 'الاستراتيجية التقنية', zh: '技术策略' },
        { en: 'Debugging', fa: 'دیباگ‌سازی', ar: 'التصحيح', zh: '调试' },
        { en: 'Team process management', fa: 'مدیریت روند تیم', ar: 'إدارة سير عمل الفريق', zh: '团队流程管理' },
        { en: 'AI motion graphics', fa: 'موشن‌گرافیک با هوش مصنوعی', ar: 'موشن غرافيك بالذكاء الاصطناعي', zh: 'AI 动态图形' },
        { en: 'AI graphics', fa: 'گرافیک با هوش مصنوعی', ar: 'غرافيك بالذكاء الاصطناعي', zh: 'AI 图形设计' },
        { en: 'Prompt writing', fa: 'پرامپت‌نویسی', ar: 'كتابة الأوامر', zh: '提示词写作' },
        { en: 'Scriptwriting', fa: 'سناریونویسی', ar: 'كتابة السيناريو', zh: '脚本创作' },
      ],
      links: [
        { kind: 'email', text: 'amirhesamhh1378@gmail.com', href: 'mailto:amirhesamhh1378@gmail.com' },
        { kind: 'telegram', text: '@Amirhesam139001', href: 'https://t.me/Amirhesam139001' },
        { kind: 'github', text: 'amirhesamhh1378-cell', href: 'https://github.com/amirhesamhh1378-cell' },
      ],
    },

    {
      id: 'parsa',
      accent: 'var(--neon-purple)',
      initials: 'PA',
      name: { en: 'Parsa Abdollahi', fa: 'پارسا عبداللهی', ar: 'پارسا عبداللهی', zh: 'Parsa Abdollahi' },
      role: {
        en: 'AI & Machine Learning Developer',
        fa: 'توسعه‌دهنده‌ی هوش مصنوعی و یادگیری ماشین',
        ar: 'مطوّر ذكاء اصطناعي وتعلّم آلة',
        zh: 'AI 与机器学习开发者',
      },
      tagline: {
        en: 'Data preparation, feature engineering, and the evaluation that decides what ships.',
        fa: 'آماده‌سازی داده، مهندسی ویژگی، و ارزیابی‌ای که تعیین می‌کند چه چیزی نهایی شود.',
        ar: 'إعداد البيانات وهندسة الخصائص والتقييم الذي يحدّد ما يُعتمد.',
        zh: '数据准备、特征工程，以及决定什么能上线的评估。',
      },
      summary: {
        en: 'Student and developer working in artificial intelligence and machine learning. Competent in machine-learning concepts and model development, currently extending into deep learning, with practical experience across preprocessing, feature engineering, training and evaluation.',
        fa: 'دانش‌آموز و توسعه‌دهنده در حوزه‌ی هوش مصنوعی و یادگیری ماشین. مسلط به مفاهیم یادگیری ماشین و ساخت مدل، در حال گسترش دانش به سمت یادگیری عمیق، با تجربه‌ی عملی در پیش‌پردازش، مهندسی ویژگی، آموزش و ارزیابی.',
        ar: 'طالب ومطوّر يعمل في الذكاء الاصطناعي وتعلّم الآلة. متمكّن من مفاهيم تعلّم الآلة وبناء النماذج، ويتوسّع حاليًا نحو التعلّم العميق، مع خبرة عملية في المعالجة المسبقة وهندسة الخصائص والتدريب والتقييم.',
        zh: '从事人工智能与机器学习的学生与开发者。熟悉机器学习概念与模型开发，目前正向深度学习拓展，在预处理、特征工程、训练与评估方面具备实践经验。',
      },
      personal: [
        { label: F.status, value: { en: 'Student · Innoverse 2026 team member', fa: 'دانش‌آموز · عضو تیم اینوورس ۲۰۲۶', ar: 'طالب · عضو فريق إنوفيرس ٢٠٢٦', zh: '学生 · Innoverse 2026 团队成员' } },
        { label: F.focus, value: { en: 'Data preprocessing · feature engineering · model evaluation', fa: 'پیش‌پردازش داده · مهندسی ویژگی · ارزیابی مدل', ar: 'المعالجة المسبقة · هندسة الخصائص · تقييم النماذج', zh: '数据预处理 · 特征工程 · 模型评估' } },
      ],
      project: [
        {
          en: 'Contributed to the development of the team’s AI project at the Innoverse programming competition.',
          fa: 'در مسابقه‌ی برنامه‌نویسی اینوورس، در توسعه‌ی پروژه‌ی هوش مصنوعی تیم مشارکت داشته است.',
          ar: 'ساهم في تطوير مشروع الفريق للذكاء الاصطناعي في مسابقة إنوفيرس البرمجية.',
          zh: '在 Innoverse 编程竞赛中参与团队 AI 项目的开发。',
        },
        {
          en: 'Participated in data preparation and feature engineering.',
          fa: 'در آماده‌سازی داده و مهندسی ویژگی مشارکت داشته است.',
          ar: 'شارك في إعداد البيانات وهندسة الخصائص.',
          zh: '参与数据准备与特征工程。',
        },
        {
          en: 'Contributed to the training and evaluation of the machine-learning models.',
          fa: 'در آموزش و ارزیابی مدل‌های یادگیری ماشین مشارکت داشته است.',
          ar: 'ساهم في تدريب نماذج تعلّم الآلة وتقييمها.',
          zh: '参与机器学习模型的训练与评估。',
        },
        {
          en: 'Collaborated with the team on the design and implementation of a solution to a real problem.',
          fa: 'همراه تیم بر طراحی و پیاده‌سازی راه‌حلی برای یک مسئله‌ی واقعی همکاری کرده است.',
          ar: 'تعاون مع الفريق على تصميم وتنفيذ حل لمشكلة واقعية.',
          zh: '与团队协作，设计并实现针对真实问题的解决方案。',
        },
      ],
      experience: [
        {
          title: { en: 'Programming competitions', fa: 'مسابقات برنامه‌نویسی', ar: 'مسابقات البرمجة', zh: '编程竞赛' },
          detail: {
            en: 'Experience of team-based AI projects and programming competitions.',
            fa: 'تجربه‌ی پروژه‌های تیمی هوش مصنوعی و مسابقات برنامه‌نویسی.',
            ar: 'خبرة في مشاريع الذكاء الاصطناعي الجماعية ومسابقات البرمجة.',
            zh: '具备团队型 AI 项目与编程竞赛经验。',
          },
        },
        {
          title: { en: 'Objective', fa: 'هدف حرفه‌ای', ar: 'الهدف المهني', zh: '职业目标' },
          detail: {
            en: 'Research in AI and machine learning, deep learning, and the solution of real-world challenges through technology.',
            fa: 'پژوهش در هوش مصنوعی و یادگیری ماشین، یادگیری عمیق، و حل چالش‌های واقعی از راه فناوری.',
            ar: 'البحث في الذكاء الاصطناعي وتعلّم الآلة والتعلّم العميق، وحل تحديات واقعية عبر التقنية.',
            zh: 'AI 与机器学习研究、深度学习，以及用技术解决现实挑战。',
          },
        },
      ],
      skills: [
        'Python', 'Machine Learning',
        { en: 'Deep learning (in progress)', fa: 'یادگیری عمیق (در حال یادگیری)', ar: 'التعلّم العميق (قيد التطوير)', zh: '深度学习（学习中）' },
        'Pandas', 'NumPy', 'scikit-learn',
        { en: 'Data preprocessing', fa: 'پیش‌پردازش داده', ar: 'المعالجة المسبقة للبيانات', zh: '数据预处理' },
        { en: 'Feature engineering', fa: 'مهندسی ویژگی', ar: 'هندسة الخصائص', zh: '特征工程' },
        { en: 'Model evaluation', fa: 'ارزیابی مدل', ar: 'تقييم النماذج', zh: '模型评估' },
        { en: 'Problem solving', fa: 'حل مسئله', ar: 'حل المشكلات', zh: '解决问题' },
      ],
      links: [
        { kind: 'email', text: 'parsaabdoollahi1388@gmail.com', href: 'mailto:parsaabdoollahi1388@gmail.com' },
        { kind: 'telegram', text: '@Parsa451290', href: 'https://t.me/Parsa451290' },
        { kind: 'github', text: 'parsa143', href: 'https://github.com/parsa143' },
      ],
    },
  ];

  const LINK_ICONS = {
    email: '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="m3.5 7 8.5 6 8.5-6"/>',
    telegram: '<path d="m21 4-3 16-6-4.5-3 3.5v-5L20 6 6.5 12 3 10.5 21 4Z"/>',
    github: '<path d="M12 3.5a8.5 8.5 0 0 0-2.7 16.6c.4.1.6-.2.6-.4v-1.6c-2.4.5-2.9-1.1-2.9-1.1-.4-1-1-1.3-1-1.3-.8-.5.1-.5.1-.5.9.1 1.3.9 1.3.9.8 1.3 2.1.9 2.6.7.1-.6.3-1 .6-1.2-1.9-.2-3.9-1-3.9-4.2 0-.9.3-1.7.9-2.3-.1-.2-.4-1.1.1-2.3 0 0 .7-.2 2.3.9a8 8 0 0 1 4.2 0c1.6-1.1 2.3-.9 2.3-.9.5 1.2.2 2.1.1 2.3.6.6.9 1.4.9 2.3 0 3.2-2 4-3.9 4.2.3.3.6.8.6 1.7v2.5c0 .2.2.5.6.4A8.5 8.5 0 0 0 12 3.5Z"/>',
    site: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17"/><path d="M12 3.5c2.2 2.4 3.3 5.3 3.3 8.5s-1.1 6.1-3.3 8.5c-2.2-2.4-3.3-5.3-3.3-8.5S9.8 5.9 12 3.5Z"/>',
  };

  function cardHtml(member, index) {
    return ''
      + `<li class="tm-card-wrap reveal" style="--tm-accent:${member.accent};--tm-i:${index}">`
      + `<button type="button" class="tm-card" data-member="${esc(member.id)}"`
      + ` aria-label="${esc(pick(member.name))} — ${esc(pick(HEAD.open))}">`
      + '<span class="tm-card-glow" aria-hidden="true"></span>'
      + `<span class="tm-avatar" aria-hidden="true">${esc(member.initials)}</span>`
      + '<span class="tm-card-text">'
      + `<span class="tm-name">${esc(pick(member.name))}</span>`
      + `<span class="tm-role">${esc(pick(member.role))}</span>`
      + `<span class="tm-tagline">${esc(pick(member.tagline))}</span>`
      + '</span>'
      + `<span class="tm-open">${esc(pick(HEAD.open))}`
      + '<svg viewBox="0 0 24 24" class="tm-open-arrow" aria-hidden="true"><path d="M5 12h13"/><path d="m13 6 6 6-6 6"/></svg>'
      + '</span>'
      + '</button></li>';
  }

  /* ---- the five panels ------------------------------------------- */

  function panel(key, bodyHtml, extraClass) {
    if (!bodyHtml) return '';
    return ''
      + `<section class="tm-panel${extraClass ? ` ${extraClass}` : ''}">`
      + `<h4 class="tm-panel-title">${esc(pick(PANELS[key]))}</h4>`
      + bodyHtml
      + '</section>';
  }

  function personalPanel(member) {
    const rows = (member.personal || []).map((row) => ''
      + '<div class="tm-row">'
      + `<dt>${esc(pick(row.label))}</dt>`
      + `<dd>${esc(pick(row.value))}</dd>`
      + '</div>').join('');
    return panel('personal', ''
      + `<p class="tm-summary">${esc(pick(member.summary))}</p>`
      + (rows ? `<dl class="tm-rows">${rows}</dl>` : ''));
  }

  function bulletPanel(key, items) {
    if (!items || !items.length) return '';
    return panel(key, '<ul class="tm-list">'
      + items.map((i) => `<li>${esc(pick(i))}</li>`).join('')
      + '</ul>');
  }

  function experiencePanel(member) {
    if (!member.experience || !member.experience.length) return '';
    return panel('experience', member.experience.map((entry) => ''
      + '<div class="tm-entry">'
      + `<p class="tm-entry-title">${esc(pick(entry.title))}</p>`
      + `<p class="tm-entry-detail">${esc(pick(entry.detail))}</p>`
      + '</div>').join(''));
  }

  function skillsPanel(member) {
    return panel('skills', '<ul class="tm-chips">'
      + member.skills.map((s) => `<li class="tm-chip">${esc(pick(s))}</li>`).join('')
      + '</ul>');
  }

  function contactPanel(member) {
    return panel('contact', '<div class="tm-links">'
      + (member.links || []).map((l) => ''
        + `<a class="tm-link" href="${esc(l.href)}" target="_blank" rel="noopener noreferrer">`
        + `<svg viewBox="0 0 24 24" class="tm-link-icon" aria-hidden="true">${LINK_ICONS[l.kind] || LINK_ICONS.site}</svg>`
        + `<span dir="ltr">${esc(l.text)}</span></a>`).join('')
      + '</div>');
  }

  function profileHtml(member) {
    return ''
      + `<div class="tm-profile" style="--tm-accent:${member.accent}">`
      + '<header class="tm-profile-head">'
      + `<span class="tm-avatar tm-avatar--lg" aria-hidden="true">${esc(member.initials)}</span>`
      + '<div>'
      + `<p class="tm-profile-role">${esc(pick(member.role))}</p>`
      + `<p class="tm-profile-tagline">${esc(pick(member.tagline))}</p>`
      + '</div></header>'
      + '<div class="tm-panels">'
      + personalPanel(member)
      + bulletPanel('project', member.project)
      + experiencePanel(member)
      + bulletPanel('achievements', member.achievements)
      + skillsPanel(member)
      + contactPanel(member)
      + '</div></div>';
  }

  function openProfile(member) {
    if (!window.DWSheet) return;
    window.DWSheet.open({
      title: pick(member.name),
      bodyHtml: profileHtml(member),
      size: 'lg',
      className: 'dw-sheet--profile',
    });
  }

  function render(root) {
    root.innerHTML = ''
      + '<header class="tm-head reveal">'
      + `<p class="tm-eyebrow">${esc(pick(HEAD.eyebrow))}</p>`
      + `<h2 class="tm-heading text-gradient">${esc(pick(HEAD.title))}</h2>`
      + `<p class="tm-lede">${esc(pick(HEAD.lede))}</p>`
      + '</header>'
      + `<ul class="tm-grid">${MEMBERS.map(cardHtml).join('')}</ul>`;

    root.querySelectorAll('.tm-card').forEach((btn) => {
      btn.addEventListener('click', () => {
        const member = MEMBERS.find((m) => m.id === btn.dataset.member);
        if (member) openProfile(member);
      });
      // The card is already a <button>, so Enter and Space work without
      // a keydown handler of our own - which is the whole reason it is
      // a button and not a div with a click listener.
    });

    if (window.DWMotion) window.DWMotion.observeReveals(root);
  }

  function init(rootId) {
    const root = document.getElementById(rootId);
    if (!root) return;
    render(root);
    document.addEventListener('dwai:langchange', () => {
      // A language change closes any open profile: re-rendering the
      // grid underneath a panel built from the old language leaves the
      // reader looking at two languages at once.
      if (window.DWSheet && window.DWSheet.close) window.DWSheet.close(null);
      render(root);
    });
  }

  window.DWAboutTeam = { init, MEMBERS, PANELS };
})();
