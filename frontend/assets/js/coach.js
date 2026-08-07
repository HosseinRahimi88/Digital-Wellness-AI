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

  const lang = () => (window.DWI18n && window.DWI18n.get()) || 'en';

  const T = {
    en: {
      title: 'Talk to your coach', send: 'Send', keyToggle: 'Bring your own key',
      keyNote: 'Optional and entirely for the future. This build makes no external calls at all — replies come from your own check-in data on this device. If you paste a key it is kept in memory for this tab only: never stored, never logged, never sent anywhere, and gone when you close the tab.',
      keySave: 'Save for this session', keyClear: 'Forget', keyLabel: 'API key',
      statusNone: 'No key set — the coach works without one.',
      statusSet: (m) => `Key held in memory for this tab only: ${m}`,
      disclaimer: 'General digital-wellbeing guidance only — never medical advice.',
      placeholder: 'Type /fit to begin',
      fitDone: 'Loaded. Ask me about your score, a specific signal, or what to do first.',
      you: 'You', coach: 'Coach',
    },
    fa: {
      title: 'با مربی‌ات صحبت کن', send: 'ارسال', keyToggle: 'کلید اختصاصی خودت',
      keyNote: 'اختیاری و کاملاً برای آینده. این نسخه هیچ ارتباط خارجی برقرار نمی‌کند — پاسخ‌ها از داده‌ی بررسی خودت روی همین دستگاه ساخته می‌شوند. اگر کلیدی وارد کنی فقط در حافظه‌ی همین تب می‌ماند: هرگز ذخیره نمی‌شود، هرگز لاگ نمی‌شود، هیچ‌جا ارسال نمی‌شود، و با بستن تب پاک می‌شود.',
      keySave: 'ذخیره برای این نشست', keyClear: 'حذف کن', keyLabel: 'کلید API',
      statusNone: 'کلیدی تنظیم نشده — مربی بدون آن هم کار می‌کند.',
      statusSet: (m) => `کلید فقط در حافظه‌ی همین تب نگه داشته می‌شود: ${m}`,
      disclaimer: 'فقط راهنمایی عمومی سلامت دیجیتال — هرگز توصیه‌ی پزشکی نیست.',
      placeholder: 'برای شروع /fit را بزن',
      fitDone: 'بارگذاری شد. درباره‌ی امتیازت، یک سیگنال خاص، یا اینکه اول چه کاری بکنی بپرس.',
      you: 'تو', coach: 'مربی',
    },
  };
  const t = () => T[lang()] || T.en;

  let ctx = null;
  let fitted = false;

  function applyCopy() {
    const c = t();
    document.getElementById('coachChatTitle').textContent = c.title;
    document.getElementById('coachKeyToggleLabel').textContent = c.keyToggle;
    document.getElementById('coachKeyNote').textContent = c.keyNote;
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

  async function runFit() {
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

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    bubble('user', text);

    if (/^\/fit\b/i.test(text)) { await runFit(); return; }

    if (!fitted) { ctx = window.DWCoachChat.loadContext(); fitted = true; }
    const reply = window.DWCoachChat.respond(text, ctx);
    const el = bubble('coach', reply.text);
    if (reply.kind === 'crisis') el.classList.add('chat-crisis');
    if (window.DWMascot && reply.kind === 'crisis') window.DWMascot.renderFace('borderline');
  });

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

  // Key must not outlive the tab or a logout.
  window.addEventListener('beforeunload', () => window.DWCoachChat.clearKey());
  document.querySelectorAll('[data-logout]').forEach((b) =>
    b.addEventListener('click', () => window.DWCoachChat.clearKey()));

  document.addEventListener('dwai:langchange', applyCopy);
  applyCopy();
  greet();
});
