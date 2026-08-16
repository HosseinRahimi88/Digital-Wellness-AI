/* AI Coach page controller: wires the chat UI (send/receive bubbles,
   the /fit context-loading command, the session-only API key panel)
   to the actual response logic in coach-chat.js - this file owns the
   DOM, coach-chat.js owns the guardrails and reply generation. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('coach');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  /* The SERVER decides whether this user has ever checked in - not this
     browser's cache. Reading only the cache is what made this page tell
     somebody who had just recorded a day that there was no coaching yet:
     the day existed, the local copy did not. */
  let result = null;
  try {
    result = await window.DWLastResult.ensure();
  } catch (e) {}

  if (!result) {
    document.getElementById('coachEmpty').classList.remove('hidden');
    return;
  }
  document.getElementById('coachContent').classList.remove('hidden');

  let featureSchemaMap = {};
  try {
    const list = await window.DWApi.featureSchema();
    list.forEach((f) => { featureSchemaMap[f.name] = f; });
  } catch (e) {}

  const classBadgeClass = (pred) => {
    const p = (pred || '').toLowerCase();
    if (p.includes('healthy')) return 'badge--healthy';
    if (p.includes('risk')) return 'badge--risk';
    return 'badge--moderate';
  };

  /* This whole context panel used to be built once, in English
     regardless of language, with nothing here reacting to a later
     switch: the class badge printed the model's raw class string, the
     score/confidence/persona line was a hardcoded English template, the
     SHAP factor names fell back to the server's English feature-schema
     label instead of DWCoachLabels (the table every other page on this
     origin already reads), the empty-recommendations card had no
     translation at all, and the recommendation cards read the flat
     English fields instead of text_i18n/priority_i18n/safety_note_i18n
     - the exact same data the result page (app.js) already renders
     correctly. Wrapped in one function so a language switch re-runs all
     of it from the same cached `result`, no re-fetch. */
  const CLASS_LABEL = {
    Healthy: { en: 'Healthy', fa: 'سالم', ar: 'صحي', zh: '健康' },
    Moderate: { en: 'Moderate', fa: 'متوسط', ar: 'متوسط', zh: '中等' },
    'At Risk': { en: 'At Risk', fa: 'در معرض خطر', ar: 'في خطر', zh: '有风险' },
  };
  const BANNER = {
    score: { en: 'Score', fa: 'امتیاز', ar: 'الدرجة', zh: '分数' },
    confidence: { en: 'Confidence', fa: 'اطمینان', ar: 'الثقة', zh: '置信度' },
    persona: { en: 'Persona', fa: 'پرسونا', ar: 'الشخصية', zh: '人格画像' },
  };
  const recNone = {
    title: { en: 'Nothing to flag right now', fa: 'فعلاً چیزی برای گفتن نیست', ar: 'لا شيء يستحق الإشارة إليه الآن', zh: '目前没有需要提醒的' },
    desc: {
      en: 'Every top factor behind this score is already working in your favor.',
      fa: 'همه‌ی عامل‌های اصلی پشتِ این امتیاز همین حالا به نفعت کار می‌کنند.',
      ar: 'كل العوامل الرئيسية وراء هذه الدرجة تعمل بالفعل لصالحك.',
      zh: '这个分数背后的每一个主要因素目前都在帮助你。',
    },
  };
  const bpick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);

  function renderContextPanel(result) {
    const badge = document.getElementById('coachBadge');
    badge.textContent = bpick(CLASS_LABEL[result.prediction]) || result.prediction;
    badge.className = 'badge ' + classBadgeClass(result.prediction);
    document.getElementById('coachScoreLine').textContent =
      `${bpick(BANNER.score)}: ${Math.round(result.regression_score ?? 0)}/100 · `
      + `${bpick(BANNER.confidence)}: ${Math.round(result.confidence_percent)}%`;
    const persona = localStorage.getItem('dwai_last_persona');
    document.getElementById('coachPersonaLine').textContent = persona ? `${bpick(BANNER.persona)}: ${persona}` : '';

    const shapWrap = document.getElementById('coachShapBars');
    shapWrap.innerHTML = '';
    (result.shap_features || []).forEach((f) => {
      const table = ((window.DWCoachLabels || {}).__raw || {})[f.feature];
      const lang = (window.DWI18n && window.DWI18n.get) ? window.DWI18n.get() : 'en';
      const def = featureSchemaMap[f.feature];
      const name = (table && (table[lang] || table.en)) || (def && def.label) || f.feature;
      const row = document.createElement('div');
      row.className = 'shap-bar-row';
      const pct = Math.min(100, Math.abs(f.score || 0));
      row.innerHTML = `
        <div class="name">${name}</div>
        <div class="shap-bar-track">
          <div class="shap-mid-line"></div>
          <div class="shap-bar-fill ${f.direction}" style="width:${pct / 2}%"></div>
        </div>
      `;
      shapWrap.appendChild(row);
    });

    const recWrap = document.getElementById('coachRecCards');
    recWrap.innerHTML = '';
    if (!result.recommendations || result.recommendations.length === 0) {
      recWrap.innerHTML = `<div class="rec-card"><div class="rec-title">🌿 ${bpick(recNone.title)}</div><p class="rec-desc">${bpick(recNone.desc)}</p></div>`;
    }
    (result.recommendations || []).forEach((r) => {
      const card = document.createElement('div');
      card.className = 'rec-card';
      const prio = (r.priority || 'low').toLowerCase();
      // Same source RecommendationService already fills for the result
      // page: text_i18n covers title/description/action/success_metric
      // (per-rule text with this user's own number substituted);
      // priority_i18n/safety_note_i18n cover the two fields shared
      // across rules that text_i18n does not.
      const lang = (window.DWI18n && window.DWI18n.get) ? window.DWI18n.get() : 'en';
      const t18 = r.text_i18n || {};
      const part = (name, fallback) => {
        const table = t18[name];
        if (!table) return fallback;
        return table[lang] || table.en || fallback;
      };
      const recTitle = part('title', r.title);
      const recDesc = part('description', r.description);
      const recAction = part('action', r.action);
      const recMetric = part('success_metric', r.success_metric);
      const recSafety = (r.safety_note_i18n && (r.safety_note_i18n[lang] || r.safety_note_i18n.en)) || r.safety_note;
      const recPriority = (r.priority_i18n && (r.priority_i18n[lang] || r.priority_i18n.en)) || r.priority;
      card.innerHTML = `
        <div class="rec-head">
          <span class="rec-title">${r.icon || '💡'} ${recTitle}</span>
          <span class="badge badge--priority-${prio}">${recPriority}</span>
        </div>
        <p class="rec-desc">${recDesc}</p>
        <p class="rec-action">➜ ${recAction}</p>
        <div class="rec-meta">📊 ${recMetric || ''}<br/>${recSafety || ''}</div>
      `;
      recWrap.appendChild(card);
    });
  }

  renderContextPanel(result);
  document.addEventListener('dwai:langchange', () => renderContextPanel(result));

  // Expression/tone from the real score, same bands the result page uses.
  window.DWMascot.reactToScore(result.regression_score);
});

/* ===================== Conversational coach ===================== */
document.addEventListener('DOMContentLoaded', () => {
  const card = document.getElementById('coachChatCard');
  if (!card) return;

  const log = document.getElementById('coachChatLog');
  const form = document.getElementById('coachChatForm');
  const input = document.getElementById('coachChatInput');
  const keyToggle = document.getElementById('coachKeyToggle');
  const keyPanel = document.getElementById('coachKeyPanel');
  const keyInput = document.getElementById('coachKeyInput');
  const keySave = document.getElementById('coachKeySave');
  const keyClear = document.getElementById('coachKeyClear');
  const keyStatus = document.getElementById('coachKeyStatus');
  const connectorSwitch = document.getElementById('connectorEnableSwitch');
  const connectorLabel = document.getElementById('connectorEnableLabel');

  const lang = () => (window.DWI18n && window.DWI18n.get()) || 'en';
  /* Runtime strings on this page go through pick(), which reads the
     current language off a four-language table. The previous
     `lang() === 'fa' ? fa : en` form silently served English to Arabic
     and Chinese readers - see tests/frontend/test_i18n_coverage.py, which now
     fails the build if a table omits a language. */
  const pick = (table) => (window.DWI18n && window.DWI18n.pick
    ? window.DWI18n.pick(table)
    : (table && (table[lang()] || table.en)) || '');

  /* Persian and Arabic readers get their own digits; a heading that says
     "142" to a Persian reader mid-sentence reads as a foreign insert. */
  const COUNT_DIGITS = {
    fa: ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'],
    ar: ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'],
  };

  function localiseCount(value, language) {
    const digits = COUNT_DIGITS[language];
    const plain = String(value);
    return digits ? plain.replace(/[0-9]/g, (d) => digits[Number(d)]) : plain;
  }

  const T = {
    en: {
      title: 'Talk to your coach', send: 'Send', keyToggle: 'Bring your own key',
      keyNoteOff: 'Optional. While the connector below is OFF (the default), this build makes no external calls at all — replies come from your own check-in data on this device. If you paste a key it is kept in memory for this tab only: never stored, never logged, never sent anywhere, and gone when you close the tab.',
      keyNoteOn: 'Connector is ON: /fit and your messages now go directly from this browser tab to your chosen provider, using your key — never through our backend. This is an experimental extra outside the competition\'s no-external-API scope, off by default for a reason.',
      connectorLabel: 'Enable experimental connector (outside competition scope)',
      keySave: 'Save for this session', keyClear: 'Forget', keyLabel: 'API key',
      statusNone: 'No key set — the coach works without one.',
      statusSet: (m) => `Key held in memory for this tab only: ${m}`,
      disclaimer: 'General digital-wellbeing guidance only — never medical advice.',
      placeholder: 'Type /fit to begin',
      fitDone: 'Loaded. Ask me about your score, a specific signal, or what to do first.',
      fitConnectorIntro: 'Reading your real data and summarizing it…',
      you: 'You', coach: 'Coach',
    },
    fa: {
      title: 'با مربی‌ات صحبت کن', send: 'ارسال', keyToggle: 'کلید اختصاصی خودت',
      keyNoteOff: 'اختیاری. تا وقتی کانکتور پایین خاموش است (پیش‌فرض)، این نسخه هیچ ارتباط خارجی برقرار نمی‌کند — پاسخ‌ها از داده‌ی بررسی خودت روی همین دستگاه ساخته می‌شوند. اگر کلیدی وارد کنی فقط در حافظه‌ی همین تب می‌ماند: هرگز ذخیره نمی‌شود، هرگز لاگ نمی‌شود، هیچ‌جا ارسال نمی‌شود، و با بستن تب پاک می‌شود.',
      keyNoteOn: 'کانکتور روشن است: از این پس /fit و پیام‌هایت مستقیماً از همین مرورگر به سرویس‌دهنده‌ی انتخابی‌ات می‌رود، با کلید خودت — هرگز از سرور ما عبور نمی‌کند. این یک قابلیت آزمایشی و اضافه، خارج از محدوده‌ی «بدون API خارجی» مسابقه است؛ به همین دلیل پیش‌فرض خاموش است.',
      connectorLabel: 'کانکتور آزمایشی را فعال کن (خارج از محدوده‌ی مسابقه)',
      keySave: 'ذخیره برای این نشست', keyClear: 'حذف کن', keyLabel: 'کلید API',
      statusNone: 'کلیدی تنظیم نشده — مربی بدون آن هم کار می‌کند.',
      statusSet: (m) => `کلید فقط در حافظه‌ی همین تب نگه داشته می‌شود: ${m}`,
      disclaimer: 'فقط راهنمایی عمومی سلامت دیجیتال — هرگز توصیه‌ی پزشکی نیست.',
      placeholder: 'برای شروع /fit را بزن',
      fitDone: 'بارگذاری شد. درباره‌ی امتیازت، یک سیگنال خاص، یا اینکه اول چه کاری بکنی بپرس.',
      fitConnectorIntro: 'دارم داده‌ی واقعی‌ات را می‌خوانم و خلاصه می‌کنم…',
      you: 'تو', coach: 'مربی',
    },
    ar: {
      title: 'تحدث مع مربيك', send: 'إرسال', keyToggle: 'استخدم مفتاحك الخاص',
      keyNoteOff: 'اختياري. طالما الموصّل أدناه مُطفأ (الوضع الافتراضي)، لا يجري هذا الإصدار أي اتصال خارجي على الإطلاق — تأتي الردود من بيانات تسجيلك الخاصة على هذا الجهاز. إن لصقت مفتاحاً، يبقى في الذاكرة لهذا التبويب فقط: لا يُخزَّن أبداً، ولا يُسجَّل أبداً، ولا يُرسَل إلى أي مكان، ويختفي عند إغلاق التبويب.',
      keyNoteOn: 'الموصّل مُفعَّل: الآن /fit ورسائلك تذهب مباشرة من هذا التبويب إلى مزوّدك المختار، باستخدام مفتاحك — لا تمر أبداً عبر خادمنا. هذه إضافة تجريبية خارج نطاق «بلا API خارجي» للمسابقة، ومُطفأة افتراضياً لسبب.',
      connectorLabel: 'تفعيل الموصّل التجريبي (خارج نطاق المسابقة)',
      keySave: 'حفظ لهذه الجلسة', keyClear: 'نسيان', keyLabel: 'مفتاح API',
      statusNone: 'لا يوجد مفتاح مضبوط — يعمل المربي دونه.',
      statusSet: (m) => `المفتاح محفوظ في ذاكرة هذا التبويب فقط: ${m}`,
      disclaimer: 'إرشادات عامة للعافية الرقمية فقط — ليست نصيحة طبية أبداً.',
      placeholder: 'اكتب /fit للبدء',
      fitDone: 'تم التحميل. اسألني عن درجتك، إشارة محددة، أو ما يجب فعله أولاً.',
      fitConnectorIntro: 'أقرأ بياناتك الحقيقية وألخّصها…',
      you: 'أنت', coach: 'المربي',
    },
    zh: {
      title: '和你的教练聊聊', send: '发送', keyToggle: '使用你自己的密钥',
      keyNoteOff: '可选。只要下面的连接器处于关闭状态（默认），此版本完全不会发起任何外部调用——回复来自你在这台设备上的真实记录数据。如果你粘贴了密钥，它只会保存在这个标签页的内存里：绝不存储、绝不记录日志、绝不发送到任何地方，关闭标签页后就会消失。',
      keyNoteOn: '连接器已开启：现在 /fit 和你的消息会直接从这个浏览器标签页发送到你选择的服务商，使用你自己的密钥——绝不经过我们的后端。这是竞赛「无外部 API」范围之外的一项实验性附加功能，因此默认关闭。',
      connectorLabel: '启用实验性连接器（超出竞赛范围）',
      keySave: '为本次会话保存', keyClear: '忘记', keyLabel: 'API 密钥',
      statusNone: '未设置密钥——教练没有它也能工作。',
      statusSet: (m) => `密钥仅保存在此标签页内存中：${m}`,
      disclaimer: '仅为一般性数字健康指导——绝不是医疗建议。',
      placeholder: '输入 /fit 开始',
      fitDone: '已加载。可以问我关于你的分数、某个具体信号，或该先做什么。',
      fitConnectorIntro: '正在读取你的真实数据并进行总结……',
      you: '你', coach: '教练',
    },
  };
  const t = () => T[lang()] || T.en;

  let ctx = null;
  let fitted = false;
  let connectorProfile = null;
  /* Conversation memory, this session only - never persisted, which is
     the privacy rule the brief sets. Trimmed to the most recent turns so
     a long chat cannot grow the request (and the user's bill) without
     bound. */
  const conversation = [];
  const MAX_TURNS = 16;

  /* ---- Saved conversations -------------------------------------
     The in-memory `conversation` array above is what gets replayed to a
     provider; this is the durable copy the user can come back to,
     rename, and keep separate from their other threads. Both are kept
     in step by recordTurn() below rather than one being derived from
     the other, because the provider replay is capped at MAX_TURNS while
     the saved thread is not. */
  const Threads = () => window.DWCoachConversations;
  let activeThreadId = null;

  function ensureThread(firstMessage) {
    if (activeThreadId && Threads() && Threads().get(activeThreadId)) return activeThreadId;
    if (!Threads()) return null;
    activeThreadId = Threads().create(firstMessage).id;
    return activeThreadId;
  }

  function recordTurn(role, content) {
    if (!Threads()) return;
    const id = ensureThread(role === 'user' ? content : '');
    if (id) Threads().append(id, role, content);
    renderThreadList();
  }
  let menuCtxPromise = null;

  function ensureMenuContext() {
    if (!menuCtxPromise) menuCtxPromise = window.DWAIMenu.buildContext();
    return menuCtxPromise;
  }

  /* ===================== The command menu =====================
     The heading counts the menu instead of stating a number. It used to
     read "50+" in four languages while the menu had grown well past
     that, and a hand-written count goes stale the moment anyone adds a
     question - which is exactly what happened. */
  function renderMenu() {
    const wrap = document.getElementById('aiMenuGroups');
    if (!wrap || !window.DWAIMenu) return;
    const l = lang();
    const items = window.DWAIMenu.ITEMS;
    const total = localiseCount(items.length, l);
    document.getElementById('aiMenuTitle').textContent = pick({
      en: `${total} things to ask`,
      fa: `${total} چیز برای پرسیدن`,
      ar: `${total} سؤالاً يمكنك طرحه`,
      zh: `${total} 个可以问的问题`,
    });
    document.getElementById('aiMenuHint').textContent = pick({
      en: 'Pick one — every answer comes from your own real, current data, never a script.',
      fa: 'یکی را انتخاب کن — هر پاسخ از داده‌ی واقعی و فعلی خودت می‌آید، نه یک متن آماده.',
      ar: 'اختر واحداً — كل إجابة تأتي من بياناتك الحقيقية والحالية، لا من نص جاهز.',
      zh: '选一个——每个回答都来自你自己真实的当前数据，而不是预写好的稿子。',
    });
    wrap.innerHTML = '';
    const byCat = {};
    items.forEach((item) => { (byCat[item.cat] = byCat[item.cat] || []).push(item); });
    Object.keys(byCat).forEach((cat) => {
      const catLabel = (window.DWAIMenu.CATEGORY_LABELS[cat] || {})[l] || cat;
      const details = document.createElement('details');
      details.className = 'ai-menu-group';
      const summary = document.createElement('summary');
      summary.textContent = `${catLabel} (${byCat[cat].length})`;
      details.appendChild(summary);
      const grid = document.createElement('div');
      grid.className = 'ai-menu-grid';
      byCat[cat].forEach((item) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'ai-menu-item';
        btn.innerHTML = `<span class="ai-menu-icon">${item.icon}</span><span>${pick(item)}</span>`;
        btn.addEventListener('click', () => runMenuItem(item));
        grid.appendChild(btn);
      });
      details.appendChild(grid);
      wrap.appendChild(details);
    });
  }

  async function runMenuItem(item) {
    const label = pick(item);
    bubble('user', label);
    const thinking = bubble('coach', pick({
      en: 'Checking your real data…',
      fa: 'در حال بررسی داده‌ی واقعی‌ات…',
      ar: 'جارٍ فحص بياناتك الحقيقية…',
      zh: '正在查看你的真实数据…',
    }));
    try {
      const fullCtx = await ensureMenuContext();
      if (connectorActive()) {
        // chatCompletion's signature is (apiKey, systemPrompt, messages) and
        // buildPromptEnvelope returns a single array with the system message
        // already inside it. Passing that array straight through left
        // `messages` undefined, and buildRequest calls messages.filter(),
        // so every menu item threw a TypeError as soon as the connector was
        // switched on. Split the envelope into the two arguments it expects.
        const envelope = window.DWCoachChat.buildPromptEnvelope(label, { extended: fullCtx });
        const systemMessage = envelope.messages.find((m) => m.role === 'system');
        const conversationMessages = envelope.messages.filter((m) => m.role !== 'system');
        const reply = await window.DWConnector.chatCompletion(
          window.DWCoachChat.getKeyForRequest(),
          systemMessage ? systemMessage.content : '',
          conversationMessages
        );
        thinking.querySelector('.chat-body').textContent = reply || '';
        return;
      }
      const text = window.DWAIMenu.getAnswer(item.id, fullCtx);
      thinking.querySelector('.chat-body').textContent = text;
    } catch (e) {
      thinking.querySelector('.chat-body').textContent = connectorActive()
        // Same per-kind, translated message the main chat box already uses
        // (auth/quota/network/timeout/rate) - this path used to interpolate
        // the raw internal error string (e.g. "auth", "HTTP 500") straight
        // into an untranslated "Connector error: ..." sentence instead.
        ? (window.DWConnectorFit ? window.DWConnectorFit.describeError(e) : e.message)
        : pick({
            en: "Couldn't read your data right now.",
            fa: 'الان نتوانستم داده‌ات را بخوانم.',
            ar: 'لم أتمكن من قراءة بياناتك الآن.',
            zh: '现在无法读取你的数据。',
          });
    }
  }

  /* Provider / model / base-URL controls. Only these preferences are
     persisted - the API key deliberately is not, and lives in
     coach-chat.js memory for this tab alone. */
  function wireConnectorConfig() {
    const C = window.DWConnector;
    const provEl = document.getElementById('connectorProvider');
    const modelEl = document.getElementById('connectorModel');
    const baseEl = document.getElementById('connectorBaseUrl');
    const baseField = document.getElementById('connectorBaseUrlField');
    if (!C || !provEl || !modelEl || !baseEl) return;

    provEl.innerHTML = C.providerList()
      .map((p) => `<option value="${p.key}">${p.label}</option>`).join('');
    provEl.value = C.getProviderKey();

    function paintModels() {
      const models = C.modelList();
      const freeform = !models.length;
      // A self-hosted server exposes whatever model name it likes, so
      // that case gets a text field rather than a fixed list.
      modelEl.innerHTML = freeform
        ? '<option value="">—</option>'
        : models.map((m) => `<option value="${m.id}">${m.label} · ${m.tier}</option>`).join('');
      modelEl.disabled = freeform;
      if (!freeform) modelEl.value = C.getModel() || models[0].id;
      baseField.style.display = freeform ? '' : 'none';
      baseEl.value = C.getBaseUrl() || '';
    }
    paintModels();

    provEl.addEventListener('change', () => {
      C.setProviderKey(provEl.value);
      C.setModel('');        // previous model belongs to the old provider
      C.setBaseUrl('');
      paintModels();
    });
    modelEl.addEventListener('change', () => C.setModel(modelEl.value));
    baseEl.addEventListener('change', () => C.setBaseUrl(baseEl.value));
  }

  function applyCopy() {
    const c = t();
    document.getElementById('coachChatTitle').textContent = c.title;
    document.getElementById('coachKeyToggleLabel').textContent = c.keyToggle;
    document.getElementById('coachKeyNote').textContent = window.DWConnector && window.DWConnector.isEnabled() ? c.keyNoteOn : c.keyNoteOff;
    if (connectorLabel) connectorLabel.textContent = c.connectorLabel;
    document.getElementById('coachKeyLabel').textContent = c.keyLabel;
    keySave.textContent = c.keySave;
    keyClear.textContent = c.keyClear;
    document.getElementById('coachSendBtn').textContent = c.send;
    document.getElementById('coachDisclaimer').textContent = c.disclaimer;
    input.placeholder = c.placeholder;
    refreshKeyStatus();
  }

  function refreshKeyStatus() {
    const c = t();
    const has = window.DWCoachChat.hasKey();
    keyStatus.textContent = has ? c.statusSet(window.DWCoachChat.maskedKey()) : c.statusNone;
    keyClear.classList.toggle('hidden', !has);
  }

  function bubble(role, text, opts) {
    const el = document.createElement('div');
    el.className = `chat-msg chat-${role}`;
    const who = document.createElement('span');
    who.className = 'chat-who';
    who.textContent = role === 'user' ? t().you : t().coach;
    const body = document.createElement('p');
    body.className = 'chat-body';
    body.textContent = text;
    el.appendChild(who); el.appendChild(body);
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    // Recorded here rather than at each call site: bubble() is the one
    // place every message is rendered, so the saved thread cannot drift
    // out of step with what is on screen. Streamed provider answers are
    // written with an empty body and filled in afterwards, so those are
    // recorded by their caller once complete instead of here.
    //
    // `record: false` exists for the opening greeting. It used to go
    // through here like any other message, so every visit to this page
    // opened a NEW saved thread whose title was empty (a thread is
    // named after the first thing the USER says, and the user had not
    // said anything yet) containing nothing but "hello". Five visits,
    // five nameless threads. A conversation starts when someone asks
    // something.
    if (text && !(opts && opts.record === false)) {
      recordTurn(role === 'user' ? 'user' : 'assistant', text);
    }
    return el;
  }

  function greet() {
    const name = (document.querySelector('[data-account-name]') || {}).textContent || '';
    const raw = window.DWCoachChat.copy().greeting(name.trim());
    bubble('coach', raw.replace(/\*\*/g, ''), { record: false });
  }

  function connectorActive() {
    return !!(window.DWConnector && window.DWConnector.isEnabled() && window.DWCoachChat.hasKey());
  }

  async function runFit() {
    if (connectorActive()) { await runFitConnector(); return; }
    // Same narrative preparation screen as the prediction flow, over the
    // real work of assembling context from the stored prediction.
    const work = new Promise((resolve) => {
      ctx = window.DWCoachChat.loadContext();
      resolve(ctx);
    });
    try {
      await window.DWProcessing.run(work, { flow: 'coach' });
    } catch (e) { /* preparation cannot fail meaningfully */ }
    fitted = true;
    if (!ctx) {
      bubble('coach', window.DWCoachChat.copy().noData);
    } else {
      bubble('coach', t().fitDone);
      if (window.DWMascot) window.DWMascot.react('neutral');
    }
  }

  /* Connector /fit: real key check, real data read, real test reply -
     each step ends the moment its work is done. No padding: a fake
     delay to look busy is a lie about how long something took. */
  async function runFitConnector() {
    const steps = [];
    const work = window.DWConnectorFit.runFit(
      window.DWCoachChat.getKeyForRequest(),
      (i, label) => { steps.push(label); }
    );
    let outcome;
    try {
      outcome = await window.DWProcessing.run(work, { flow: 'coach' });
    } catch (e) {
      bubble('coach', window.DWConnectorFit.describeError(e));
      return;
    }
    fitted = true;
    connectorProfile = outcome.profile || null;
    bubble('coach', outcome.message);
    if (window.DWMascot) window.DWMascot.react(outcome.ok ? 'good' : 'error');
  }

  /* /refit - rebuild the profile against the freshest check-in. Also
     runs automatically after a new prediction, so this is the manual
     escape hatch rather than the only path. */
  async function runRefit() {
    const outcome = await window.DWConnectorFit.runRefit();
    connectorProfile = outcome.profile || null;
    bubble('coach', outcome.message);
  }

  /* ---- Conversation list UI ------------------------------------ */
  const THREAD_TEXT = {
    note: {
      en: 'Your conversations are saved in this browser only. Tap one to reopen it, or rename it to something you will recognise.',
      fa: 'گفتگوهایت فقط در همین مرورگر ذخیره می‌شوند. روی یکی بزن تا دوباره باز شود، یا اسمش را به چیزی عوض کن که بشناسی.',
      ar: 'محادثاتك محفوظة في هذا المتصفّح فقط. انقر واحدة لإعادة فتحها، أو أعد تسميتها بما تتعرّف عليه.',
      zh: '你的对话只保存在这个浏览器里。点一条即可重新打开，或把它改成你认得出的名字。',
    },
    empty: {
      en: 'No saved conversations yet — ask the coach something and it will appear here.',
      fa: 'هنوز گفتگوی ذخیره‌شده‌ای نیست — چیزی از مربی بپرس تا اینجا ظاهر شود.',
      ar: 'لا محادثات محفوظة بعد — اسأل المدرّب شيئاً وستظهر هنا.',
      zh: '还没有保存的对话——问教练一个问题，它就会出现在这里。',
    },
    untitled: { en: 'Untitled', fa: 'بی‌نام', ar: 'بلا عنوان', zh: '未命名' },
    rename: { en: 'Rename', fa: 'تغییر نام', ar: 'إعادة تسمية', zh: '重命名' },
    remove: { en: 'Delete', fa: 'حذف', ar: 'حذف', zh: '删除' },
    renamePrompt: { en: 'New name for this conversation:', fa: 'نام تازه برای این گفتگو:', ar: 'اسم جديد لهذه المحادثة:', zh: '这段对话的新名称：' },
    removeConfirm: { en: 'Delete this conversation?', fa: 'این گفتگو حذف شود؟', ar: 'حذف هذه المحادثة؟', zh: '删除这段对话？' },
    messages: { en: 'messages', fa: 'پیام', ar: 'رسائل', zh: '条消息' },
    // The toggle's own label. It was written into coach.html as the
    // bare English word "Conversations" with no data-i18n, so it stayed
    // English in all four languages - the one control on the page that
    // never translated.
    toggle: { en: 'Conversations', fa: 'گفتگوها', ar: 'المحادثات', zh: '对话' },
  };
  const tp = (table) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(table) : table.en);

  /* "today" / "3 days ago", in the reader's language.
     Whole days rather than hours: a saved conversation is something you
     look for by day, and "17 hours ago" is a precision nobody asked
     for. Returns '' rather than a guess when the stamp is missing, so a
     thread written by an older build shows its message count alone. */
  function relativeDay(stamp) {
    if (!stamp) return '';
    const days = Math.max(0, Math.floor((Date.now() - stamp) / 86400000));
    const table = days === 0
      ? { en: 'today', fa: 'امروز', ar: 'اليوم', zh: '今天' }
      : days === 1
        ? { en: 'yesterday', fa: 'دیروز', ar: 'أمس', zh: '昨天' }
        : {
          en: `${days} days ago`, fa: `${days} روز پیش`,
          ar: `قبل ${days} يوماً`, zh: `${days} 天前`,
        };
    return tp(table);
  }

  function renderThreadList() {
    const list = document.getElementById('coachThreadList');
    const note = document.getElementById('coachThreadsNote');
    if (!list || !Threads()) return;
    if (note) note.textContent = tp(THREAD_TEXT.note);

    const threads = Threads().list();

    /* The count, on the collapsed toggle. Without it the panel gives no
       sign there is anything inside, so six saved conversations sat one
       click away from a user with no reason to make that click - and a
       demo user arrives with several already there. */
    const toggleLabel = document.getElementById('coachThreadsToggleLabel');
    if (toggleLabel) {
      toggleLabel.textContent = threads.length
        ? `${tp(THREAD_TEXT.toggle)} (${threads.length})`
        : tp(THREAD_TEXT.toggle);
    }

    list.innerHTML = '';
    if (!threads.length) {
      const li = document.createElement('li');
      li.className = 'muted coach-thread-empty';
      li.textContent = tp(THREAD_TEXT.empty);
      list.appendChild(li);
      return;
    }

    threads.forEach((thread) => {
      const li = document.createElement('li');
      li.className = 'coach-thread' + (thread.id === activeThreadId ? ' is-active' : '');

      const open = document.createElement('button');
      open.type = 'button';
      open.className = 'coach-thread-open';
      const title = document.createElement('span');
      title.className = 'coach-thread-title';
      title.textContent = thread.title || tp(THREAD_TEXT.untitled);
      const meta = document.createElement('span');
      meta.className = 'coach-thread-meta';
      // When, as well as how many. A list of eight threads all reading
      // "6 messages" gives no way to tell this morning's from last
      // month's, which is exactly what someone scanning for one of them
      // needs. Relative rather than a date, because "3 days ago" is the
      // form the question is actually asked in.
      const when = relativeDay(thread.updated_at || thread.created_at);
      meta.textContent = when
        ? `${thread.messages.length} ${tp(THREAD_TEXT.messages)} · ${when}`
        : `${thread.messages.length} ${tp(THREAD_TEXT.messages)}`;
      open.append(title, meta);
      open.addEventListener('click', () => openThread(thread.id));

      const rename = document.createElement('button');
      rename.type = 'button';
      rename.className = 'coach-thread-action';
      rename.textContent = tp(THREAD_TEXT.rename);
      rename.addEventListener('click', (e) => {
        e.stopPropagation();
        const next = window.prompt(tp(THREAD_TEXT.renamePrompt), thread.title || '');
        if (next && Threads().rename(thread.id, next)) renderThreadList();
      });

      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'coach-thread-action is-danger';
      del.textContent = tp(THREAD_TEXT.remove);
      del.addEventListener('click', (e) => {
        e.stopPropagation();
        if (!window.confirm(tp(THREAD_TEXT.removeConfirm))) return;
        Threads().remove(thread.id);
        if (activeThreadId === thread.id) { activeThreadId = null; log.innerHTML = ''; }
        renderThreadList();
      });

      li.append(open, rename, del);
      list.appendChild(li);
    });
  }

  /** Replay a saved thread into the visible log.
   *
   *  Rendering goes through the DOM directly rather than bubble(),
   *  because bubble() records what it renders - replaying through it
   *  would append the whole thread to itself every time it was opened.
   */
  function openThread(id) {
    const thread = Threads() && Threads().get(id);
    if (!thread) return;
    activeThreadId = id;
    log.innerHTML = '';
    conversation.length = 0;
    thread.messages.forEach((message) => {
      const el = document.createElement('div');
      el.className = `chat-msg chat-${message.role === 'user' ? 'user' : 'coach'}`;
      const who = document.createElement('span');
      who.className = 'chat-who';
      who.textContent = message.role === 'user' ? t().you : t().coach;
      const body = document.createElement('p');
      body.className = 'chat-body';
      body.textContent = message.content;
      el.append(who, body);
      log.appendChild(el);
      conversation.push({ role: message.role, content: message.content });
    });
    log.scrollTop = log.scrollHeight;
    renderThreadList();
  }

  function startNewThread() {
    activeThreadId = null;
    conversation.length = 0;
    log.innerHTML = '';
    renderThreadList();
    if (window.DWGuide && window.DWGuide.explain) window.DWGuide.explain('coach_threads', { force: true });
  }

  function wireThreads() {
    const toggle = document.getElementById('coachThreadsToggle');
    const panel = document.getElementById('coachThreadsPanel');
    if (toggle && panel) {
      toggle.addEventListener('click', () => {
        const open = panel.hasAttribute('hidden');
        if (open) panel.removeAttribute('hidden'); else panel.setAttribute('hidden', '');
        toggle.setAttribute('aria-expanded', String(open));
        if (open) renderThreadList();
      });
    }
    const fresh = document.getElementById('coachNewThread');
    if (fresh) fresh.addEventListener('click', startNewThread);
    document.addEventListener('dwai:langchange', renderThreadList);
    renderThreadList();
    seedDemoThreads();
    // Rewritten in the new language, because a demo run in Persian with
    // an English chat log is worse than no chat log. Only the seeder's
    // own threads are touched; anything typed here survives.
    document.addEventListener('dwai:langchange', seedDemoThreads);
  }

  /* A demo user has been living with this app for up to twenty-three
     days; an empty coach is the one part of that story that did not add
     up. Seeded on arrival rather than when the demo starts, because the
     answers are composed by the real matcher and that only exists on
     this page. Costs nothing for a real account - ensure() checks and
     returns immediately. */
  function seedDemoThreads() {
    if (!window.DWCoachDemoChats) return;
    window.DWCoachDemoChats.ensure()
      .then((written) => { if (written) renderThreadList(); })
      .catch(() => { /* a demo without seeded threads still works */ });
  }

  /* Was this the "I did not understand you" reply? Compared against the
     copy itself rather than sniffed for keywords, so it stays correct in
     all four languages and after any rewording. */
  async function isUnknownReply(reply) {
    const c = window.DWCoachChat.copy();
    const text = (reply && reply.text) || '';
    return text === c.clarify || text.indexOf(c.unknown) === 0;
  }

  /* The best menu item for a typed message, or ''. */
  let menuCtxCache = null;
  async function menuAnswerFor(text) {
    const nlu = window.DWCoachNLU;
    const menu = window.DWAIMenu;
    if (!nlu || !menu) return '';
    const lang = (window.DWI18n && window.DWI18n.get && window.DWI18n.get()) || 'en';

    // Each item's own question text is the keyword phrase - the reader's
    // language first, English alongside it so a mixed-language message
    // still lands.
    const intents = menu.ITEMS
      .map((item) => ({
        key: item.id,
        keywords: [item[lang], item.en].filter(Boolean).map((q) => nlu.normalize(q)),
      }))
      .filter((i) => i.keywords.length);

    const hit = nlu.classify(text, intents, { threshold: 0.78 });
    if (!hit.match) return '';
    try {
      if (!menuCtxCache) menuCtxCache = await menu.buildContext();
      return menu.getAnswer(hit.match.key, menuCtxCache) || '';
    } catch (e) {
      return '';
    }
  }

  async function send(text) {
    if (!text) return;
    bubble('user', text);

    if (/^\/fit\b/i.test(text)) { await runFit(); return; }

    if (/^\/refit\b/i.test(text)) { await runRefit(); return; }

    if (connectorActive()) {
      const thinking = bubble('coach', '');
      const body = thinking.querySelector('.chat-body');
      // Streamed so text appears as it is generated - without this the
      // user watches an empty bubble for the whole generation.
      try {
        if (!connectorProfile) {
          const c = window.DWCoachContext ? await window.DWCoachContext.load() : null;
          connectorProfile = window.DWConnectorFit.buildProfile(c);
        }
        conversation.push({ role: 'user', content: text });
        const full = await window.DWConnector.chatStream(
          window.DWCoachChat.getKeyForRequest(),
          window.DWConnectorFit.buildSystemPrompt(connectorProfile),
          conversation.slice(-MAX_TURNS),
          (delta) => { body.textContent += delta; }
        );
        conversation.push({ role: 'assistant', content: full });
        if (full) recordTurn('assistant', full);
        if (!full) body.textContent = window.DWConnectorFit.describeError(null);
      } catch (e) {
        body.textContent = window.DWConnectorFit.describeError(e);
      }
      return;
    }

    // Read the user's WHOLE picture before composing any answer - not
    // just the one cached result. This runs on every message, not once
    // per session, so a check-in logged mid-conversation is picked up
    // immediately instead of the Coach quoting stale numbers.
    let fullCtx = null;
    if (window.DWCoachContext) {
      try { fullCtx = await window.DWCoachContext.load(); } catch (e) { fullCtx = null; }
    }
    if (!fitted) { ctx = window.DWCoachChat.loadContext(); fitted = true; }

    let reply = window.DWCoachChat.respond(text, ctx, fullCtx);

    /* Last resort: the menu.

       The command menu holds 202 questions, each in four languages,
       each already wired to a real answer. Typing one of them into the
       box instead of clicking it used to be a different code path with
       a different outcome - measured, 37 of the 202 came back "I'm not
       sure I follow", from an app that lists the question in its own
       menu two panels away. That is the single most embarrassing way
       for this coach to fail.

       Tried only AFTER respond() has declined, so nothing that already
       worked can change, and at a deliberately high threshold: the menu
       question has to be most of what the user typed, not merely share
       a word with it. */
    if (reply.kind === 'info' && await isUnknownReply(reply)) {
      const fromMenu = await menuAnswerFor(text);
      if (fromMenu) reply = { text: fromMenu, kind: 'answer' };
    }

    // Show what was actually read, so "it reads your data first" is
    // visible rather than merely claimed.
    if (fullCtx && window.DWCoachContext) {
      const line = window.DWCoachContext.digestLine(fullCtx);
      if (line) {
        const note = bubble('coach', line);
        note.classList.add('chat-digest');
      }
    }

    const el = bubble('coach', reply.text);
    if (reply.kind === 'crisis') el.classList.add('chat-crisis');
    if (window.DWMascot && reply.kind === 'crisis') window.DWMascot.renderFace('borderline');
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    input.value = '';
    await send(text);
  });

  /* Starter prompts. A blank chat box is the hardest thing to answer,
     so the coach offers concrete openers in the active language. */
  function renderSuggestions() {
    const wrap = document.getElementById('coachSuggestions');
    if (!wrap || !window.DWCoachKnowledge) return;
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    wrap.innerHTML = '';
    window.DWCoachKnowledge.suggestionsFor(lang).forEach((prompt) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'coach-suggestion';
      chip.textContent = prompt;
      chip.addEventListener('click', () => send(prompt));
      wrap.appendChild(chip);
    });
  }
  renderSuggestions();
  renderMenu();
  document.addEventListener('dwai:langchange', renderSuggestions);
  document.addEventListener('dwai:langchange', renderMenu);

  keyToggle.addEventListener('click', () => {
    const open = keyPanel.hasAttribute('hidden');
    if (open) keyPanel.removeAttribute('hidden'); else keyPanel.setAttribute('hidden', '');
    keyToggle.setAttribute('aria-expanded', String(open));
  });

  keySave.addEventListener('click', () => {
    const v = keyInput.value.trim();
    if (!v) return;
    window.DWCoachChat.setKey(v);
    // Clear the field immediately so the raw key does not linger in the
    // DOM or get captured by a form autofill/restore.
    keyInput.value = '';
    refreshKeyStatus();
    window.DWToast.success(window.DWI18n.t('toast_saved'));
  });

  keyClear.addEventListener('click', () => {
    window.DWCoachChat.clearKey();
    keyInput.value = '';
    refreshKeyStatus();
  });

  if (connectorSwitch) {
    connectorSwitch.checked = window.DWConnector ? window.DWConnector.isEnabled() : false;
    connectorSwitch.addEventListener('change', (e) => {
      if (window.DWConnector) window.DWConnector.setEnabled(e.target.checked);
      applyCopy();
    });
  }

  // Key must not outlive the tab or a logout.
  window.addEventListener('beforeunload', () => window.DWCoachChat.clearKey());
  document.querySelectorAll('[data-logout]').forEach((b) =>
    b.addEventListener('click', () => window.DWCoachChat.clearKey()));

  document.addEventListener('dwai:langchange', applyCopy);
  wireConnectorConfig();
  wireThreads();
  applyCopy();
  greet();
});
