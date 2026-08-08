/* AI Coach page controller: wires the chat UI (send/receive bubbles,
   the /fit context-loading command, the session-only API key panel)
   to the actual response logic in coach-chat.js - this file owns the
   DOM, coach-chat.js owns the guardrails and reply generation. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('coach');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  let result;
  try {
    result = JSON.parse(localStorage.getItem('dwai_last_result') || 'null');
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

  const badge = document.getElementById('coachBadge');
  badge.textContent = result.prediction;
  badge.className = 'badge ' + classBadgeClass(result.prediction);
  document.getElementById('coachScoreLine').textContent = `Score: ${Math.round(result.regression_score ?? 0)}/100 · Confidence: ${Math.round(result.confidence_percent)}%`;
  const persona = localStorage.getItem('dwai_last_persona');
  document.getElementById('coachPersonaLine').textContent = persona ? `Persona: ${persona}` : '';

  const shapWrap = document.getElementById('coachShapBars');
  (result.shap_features || []).forEach((f) => {
    const def = featureSchemaMap[f.feature];
    const row = document.createElement('div');
    row.className = 'shap-bar-row';
    const pct = Math.min(100, Math.abs(f.score || 0));
    row.innerHTML = `
      <div class="name">${(def && def.label) || f.feature}</div>
      <div class="shap-bar-track">
        <div class="shap-mid-line"></div>
        <div class="shap-bar-fill ${f.direction}" style="width:${pct / 2}%"></div>
      </div>
    `;
    shapWrap.appendChild(row);
  });

  const recWrap = document.getElementById('coachRecCards');
  if (!result.recommendations || result.recommendations.length === 0) {
    recWrap.innerHTML = `<div class="rec-card"><div class="rec-title">🌿 Nothing to flag right now</div><p class="rec-desc">Every top factor behind this score is already working in your favor.</p></div>`;
  }
  (result.recommendations || []).forEach((r) => {
    const card = document.createElement('div');
    card.className = 'rec-card';
    const prio = (r.priority || 'low').toLowerCase();
    card.innerHTML = `
      <div class="rec-head">
        <span class="rec-title">${r.icon || '💡'} ${r.title}</span>
        <span class="badge badge--priority-${prio}">${r.priority}</span>
      </div>
      <p class="rec-desc">${r.description}</p>
      <p class="rec-action">➜ ${r.action}</p>
      <div class="rec-meta">📊 ${r.success_metric || ''}<br/>${r.safety_note || ''}</div>
    `;
    recWrap.appendChild(card);
  });

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
      connectorError: (m) => `Connector error: ${m}`,
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
      connectorError: (m) => `خطای کانکتور: ${m}`,
      you: 'تو', coach: 'مربی',
    },
  };
  const t = () => T[lang()] || T.en;

  let ctx = null;
  let fitted = false;
  let menuCtxPromise = null;

  function ensureMenuContext() {
    if (!menuCtxPromise) menuCtxPromise = window.DWAIMenu.buildContext();
    return menuCtxPromise;
  }

  /* ===================== 50+ command menu ===================== */
  function renderMenu() {
    const wrap = document.getElementById('aiMenuGroups');
    if (!wrap || !window.DWAIMenu) return;
    const l = lang();
    document.getElementById('aiMenuTitle').textContent = l === 'fa' ? '۵۰+ چیز برای پرسیدن' : '50+ things to ask';
    document.getElementById('aiMenuHint').textContent = l === 'fa'
      ? 'یکی را انتخاب کن — هر پاسخ از داده‌ی واقعی و فعلی خودت می‌آید، نه یک متن آماده.'
      : 'Pick one — every answer comes from your own real, current data, never a script.';
    wrap.innerHTML = '';
    const byCat = {};
    window.DWAIMenu.ITEMS.forEach((item) => { (byCat[item.cat] = byCat[item.cat] || []).push(item); });
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
        btn.innerHTML = `<span class="ai-menu-icon">${item.icon}</span><span>${l === 'fa' ? item.fa : item.en}</span>`;
        btn.addEventListener('click', () => runMenuItem(item));
        grid.appendChild(btn);
      });
      details.appendChild(grid);
      wrap.appendChild(details);
    });
  }

  async function runMenuItem(item) {
    const l = lang();
    bubble('user', l === 'fa' ? item.fa : item.en);
    const thinking = bubble('coach', l === 'fa' ? 'در حال بررسی داده‌ی واقعی‌ات…' : 'Checking your real data…');
    try {
      const fullCtx = await ensureMenuContext();
      if (connectorActive()) {
        const envelope = window.DWCoachChat.buildPromptEnvelope(l === 'fa' ? item.fa : item.en, { extended: fullCtx });
        const reply = await window.DWConnector.chatCompletion(window.DWCoachChat.getKeyForRequest(), envelope.messages);
        thinking.querySelector('.chat-body').textContent = reply || '';
        return;
      }
      const text = window.DWAIMenu.getAnswer(item.id, fullCtx);
      thinking.querySelector('.chat-body').textContent = text;
    } catch (e) {
      thinking.querySelector('.chat-body').textContent = connectorActive() ? t().connectorError(e.message) : (l === 'fa' ? 'الان نتوانستم داده‌ات را بخوانم.' : "Couldn't read your data right now.");
    }
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

  function bubble(role, text) {
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
    return el;
  }

  function greet() {
    const name = (document.querySelector('[data-account-name]') || {}).textContent || '';
    const raw = window.DWCoachChat.copy().greeting(name.trim());
    bubble('coach', raw.replace(/\*\*/g, ''));
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

  /* Connector /fit: a REAL request to the external provider, from this
     browser tab only. Sends the same context object the local coach
     uses (plus the full 50-item menu context) so the provider genuinely
     reads the user's real data, then asks it to summarize what it saw -
     matching the "type a command, see processing, get a real summary"
     flow the rest of this app already uses for predictions. */
  async function runFitConnector() {
    const l = lang();
    const work = (async () => {
      ctx = window.DWCoachChat.loadContext();
      const menuCtx = await ensureMenuContext();
      const envelope = window.DWCoachChat.buildPromptEnvelope(
        'The user just typed /fit. Read the CONTEXT and reply with a short, honest summary of what you can see about their current digital wellness data - real numbers only, nothing invented.',
        { personal: ctx, extended: menuCtx },
      );
      return window.DWConnector.chatCompletion(window.DWCoachChat.getKeyForRequest(), envelope.messages);
    })();
    let reply;
    try {
      reply = await window.DWProcessing.run(work, { flow: 'coach' });
    } catch (e) {
      bubble('coach', t().connectorError(e.message));
      return;
    }
    fitted = true;
    bubble('coach', reply || t().fitDone);
  }

  async function send(text) {
    if (!text) return;
    bubble('user', text);

    if (/^\/fit\b/i.test(text)) { await runFit(); return; }

    if (connectorActive()) {
      const thinking = bubble('coach', lang() === 'fa' ? 'در حال پرسیدن از سرویس‌دهنده…' : 'Asking the provider…');
      try {
        const menuCtx = await ensureMenuContext();
        const envelope = window.DWCoachChat.buildPromptEnvelope(text, { personal: ctx, extended: menuCtx });
        const reply = await window.DWConnector.chatCompletion(window.DWCoachChat.getKeyForRequest(), envelope.messages);
        thinking.querySelector('.chat-body').textContent = reply || '';
      } catch (e) {
        thinking.querySelector('.chat-body').textContent = t().connectorError(e.message);
      }
      return;
    }

    if (!fitted) { ctx = window.DWCoachChat.loadContext(); fitted = true; }
    const reply = window.DWCoachChat.respond(text, ctx);
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
  applyCopy();
  greet();
});
