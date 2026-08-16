/*
  DWApiGuard - notices when the app was started the wrong way, and says
  so before the user wastes a password on it.

  The failure this exists for: the frontend is plain HTML, so a static
  file server (`python -m http.server`, an editor's live preview, or
  double-clicking an .html file) serves every page correctly. The app
  looks completely fine. Then the sign-in button returns

      501 Unsupported method ('POST')

  because a static server implements GET and nothing else, while every
  real action here is a POST. Nothing in that message points at the
  cause. A real user lost an evening to it, concluded the app was
  broken, and was right to - an app that cannot tell you why it will
  not work is broken, whatever the cause.

  So on every page load: one GET to /health. If the answer is not this
  API's health payload, a banner explains what happened and what to do,
  in the user's own language, and stays until it is fixed. The check
  costs one request against a server that is already local.

  It is deliberately a banner rather than a toast: a toast disappears,
  and this condition does not.
*/
(function () {
  const BANNER_ID = 'dwApiGuardBanner';

  const COPY = {
    en: {
      title: 'The app is not fully running',
      body: 'These pages are being served by a plain file server, which can display them but cannot sign you in, save a check-in, or run the model. Every one of those needs the API.',
      fix: 'Close whatever is serving this folder, then start the app properly:',
      cmd: 'python run.py',
      win: 'On Windows you can just double-click start.bat',
      then: 'Then open the address it prints (usually http://127.0.0.1:8000).',
    },
    fa: {
      title: 'برنامه کامل اجرا نشده است',
      body: 'این صفحه‌ها را یک سرور فایل ساده نشان می‌دهد؛ می‌تواند نمایششان بدهد ولی نمی‌تواند تو را وارد کند، ثبت روزانه را ذخیره کند، یا مدل را اجرا کند. هر سه‌ی این‌ها به API نیاز دارند.',
      fix: 'هرچه این پوشه را سرو می‌کند ببند، بعد برنامه را درست اجرا کن:',
      cmd: 'python run.py',
      win: 'در ویندوز کافی است روی start.bat دوبار کلیک کنی',
      then: 'بعد آدرسی را که چاپ می‌کند باز کن (معمولاً http://127.0.0.1:8000).',
    },
    ar: {
      title: 'التطبيق لا يعمل بالكامل',
      body: 'هذه الصفحات يقدّمها خادم ملفات بسيط، يستطيع عرضها ولا يستطيع تسجيل دخولك ولا حفظ تسجيل يومي ولا تشغيل النموذج. كل ذلك يحتاج واجهة البرمجة.',
      fix: 'أغلق ما يقدّم هذا المجلد، ثم شغّل التطبيق بشكل صحيح:',
      cmd: 'python run.py',
      win: 'في ويندوز يكفي النقر المزدوج على start.bat',
      then: 'ثم افتح العنوان الذي يطبعه (غالباً http://127.0.0.1:8000).',
    },
    zh: {
      title: '应用没有完整运行',
      body: '这些页面是由一个普通文件服务器提供的，它能显示页面，但无法为你登录、保存每日记录或运行模型。这些都需要 API。',
      fix: '请关掉正在提供这个文件夹的程序，然后正确启动应用：',
      cmd: 'python run.py',
      win: 'Windows 上双击 start.bat 即可',
      then: '然后打开它输出的地址（通常是 http://127.0.0.1:8000）。',
    },
  };

  function pick() {
    let lang = 'en';
    try {
      lang = (window.DWI18n && window.DWI18n.get && window.DWI18n.get()) || 'en';
    } catch (e) { /* i18n not loaded on this page */ }
    return COPY[lang] || COPY.en;
  }

  function render() {
    const existing = document.getElementById(BANNER_ID);
    if (existing) existing.remove();

    const t = pick();
    const banner = document.createElement('div');
    banner.id = BANNER_ID;
    banner.className = 'api-guard-banner';
    banner.setAttribute('role', 'alert');

    // textContent throughout: none of this is user input, but a banner
    // that only appears when something is already wrong is a poor place
    // to start trusting string concatenation.
    const title = document.createElement('strong');
    title.textContent = t.title;
    const body = document.createElement('p');
    body.textContent = t.body;
    const fix = document.createElement('p');
    fix.textContent = t.fix;
    const cmd = document.createElement('code');
    cmd.textContent = t.cmd;
    cmd.dir = 'ltr';
    const win = document.createElement('p');
    win.className = 'api-guard-hint';
    win.textContent = t.win;
    const then = document.createElement('p');
    then.className = 'api-guard-hint';
    then.textContent = t.then;

    banner.append(title, body, fix, cmd, win, then);
    document.body.insertBefore(banner, document.body.firstChild);
  }

  async function check() {
    if (!window.DWApi || !window.DWApi.probe) return;
    const result = await window.DWApi.probe();
    if (result.ok) {
      const existing = document.getElementById(BANNER_ID);
      if (existing) existing.remove();
      return;
    }
    // "unreachable" is a different problem - the API is simply not
    // started yet, and the pages would not have loaded from it either.
    // Both end in the same instruction, so both get the same banner.
    render();
  }

  function start() {
    check();
    // Re-render in the new language rather than leaving a banner that
    // argues with the rest of the page.
    document.addEventListener('dwai:langchange', () => {
      if (document.getElementById(BANNER_ID)) render();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }

  window.DWApiGuard = { check, render };
})();
