/*
  Optional, OFF-BY-DEFAULT external AI connector.

  Why off by default: the competition brief this project was built for is
  judged assuming zero external API dependency. Whether a user supplying
  their OWN key at runtime violates that is a question only the
  organizers can answer, so this ships disabled, behind an explicit
  opt-in, and is documented as an extra rather than claimed as part of
  the competition build.

  Key handling - the part that must be true in code, not just in copy
  ---------------------------------------------------------------------
  Every request here goes straight from this browser tab to the
  provider's own endpoint. It never passes through this app's backend, so
  the key is never seen by our server, never written to storage, and
  never logged. The only copy lives in a module-scoped variable in
  coach-chat.js that dies with the tab. Two rules keep that honest:
    * this file never calls localStorage/sessionStorage with the key, and
    * no error path here interpolates the key into a message, because a
      leaked key in a toast is still a leaked key.

  "Write once, work with everything"
  -------------------------------------
  Rather than hard-coding one vendor, this speaks the two request shapes
  that between them cover essentially every current provider:
    * openai   - the /chat/completions convention, which OpenAI, Groq,
                 Together, OpenRouter, DeepSeek, Mistral, vLLM, Ollama
                 and llama.cpp all implement. A custom base URL makes any
                 self-hosted server work without code changes.
    * anthropic - the /v1/messages shape, which differs enough (auth
                 header, system prompt as a top-level field, distinct SSE
                 event names) that pretending it is OpenAI-shaped would
                 just fail at runtime.
*/
(function () {
  const FLAG_KEY = 'dwai_connector_enabled';
  const PROVIDER_KEY = 'dwai_connector_provider';
  const MODEL_KEY = 'dwai_connector_model';
  const BASEURL_KEY = 'dwai_connector_baseurl';

  // Only non-secret preferences are persisted. The API key is deliberately
  // absent from this list and from this file entirely.
  const REQUEST_TIMEOUT_MS = 60000;
  const MAX_MESSAGES_PER_MINUTE = 12;

  /* Model menus. `tier` is a rough capability/cost hint so the user can
     choose knowingly - the brief asks for that explicitly. These are
     labels for humans, not a pricing API, and the user pays their own
     provider directly either way. */
  const PROVIDERS = {
    openai: {
      label: 'OpenAI',
      shape: 'openai',
      baseUrl: 'https://api.openai.com/v1',
      models: [
        { id: 'gpt-4o-mini', label: 'GPT-4o mini', tier: 'fast · cheap' },
        { id: 'gpt-4o', label: 'GPT-4o', tier: 'strong · mid' },
        { id: 'gpt-4.1', label: 'GPT-4.1', tier: 'strongest · pricier' },
      ],
    },
    anthropic: {
      label: 'Anthropic',
      shape: 'anthropic',
      baseUrl: 'https://api.anthropic.com/v1',
      models: [
        { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5', tier: 'fast · cheap' },
        { id: 'claude-sonnet-5', label: 'Claude Sonnet 5', tier: 'strong · mid' },
        { id: 'claude-opus-5', label: 'Claude Opus 5', tier: 'strongest · pricier' },
      ],
    },
    groq: {
      label: 'Groq',
      shape: 'openai',
      baseUrl: 'https://api.groq.com/openai/v1',
      models: [
        { id: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B', tier: 'fastest · cheapest' },
        { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B', tier: 'strong · mid' },
        { id: 'deepseek-r1-distill-llama-70b', label: 'DeepSeek R1 Distill 70B', tier: 'strongest · reasoning' },
      ],
    },
    openrouter: {
      label: 'OpenRouter',
      shape: 'openai',
      baseUrl: 'https://openrouter.ai/api/v1',
      models: [
        { id: 'openai/gpt-4o-mini', label: 'GPT-4o mini', tier: 'fast · cheap' },
        { id: 'anthropic/claude-sonnet-4.5', label: 'Claude Sonnet 4.5', tier: 'strong · mid' },
        { id: 'anthropic/claude-opus-4.5', label: 'Claude Opus 4.5', tier: 'strongest · pricier' },
      ],
    },
    gemini: {
      label: 'Gemini',
      shape: 'openai', // Google's OpenAI-compatible endpoint - no new transport code needed
      baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
      models: [
        { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash', tier: 'fast · cheap' },
        { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', tier: 'strong · mid' },
        { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', tier: 'strongest · pricier' },
      ],
    },
    grok: {
      label: 'Grok (xAI)',
      shape: 'openai', // xAI also speaks the /chat/completions convention
      baseUrl: 'https://api.x.ai/v1',
      models: [
        { id: 'grok-3-mini', label: 'Grok 3 Mini', tier: 'fast · cheap' },
        { id: 'grok-3', label: 'Grok 3', tier: 'strong · mid' },
        { id: 'grok-4', label: 'Grok 4', tier: 'strongest · pricier' },
      ],
    },
    custom: {
      label: 'Custom / self-hosted',
      shape: 'openai',
      baseUrl: '',           // user supplies it; e.g. http://localhost:11434/v1
      models: [],            // and the model name their server exposes
      freeform: true,
    },
  };

  const DEFAULT_PROVIDER = 'openai';

  /* ------------------------------------------------------------------
     Typed failures. The brief asks for four distinguishable cases, and a
     single "something went wrong" makes all four unactionable: a bad key
     needs re-entry, an exhausted quota needs the provider's billing
     page, a network failure needs a retry, and a slow response needs
     patience or a smaller model.
     ------------------------------------------------------------------ */
  const ERRORS = { AUTH: 'auth', QUOTA: 'quota', NETWORK: 'network', TIMEOUT: 'timeout', PROVIDER: 'provider' };

  class ConnectorError extends Error {
    constructor(kind, message) {
      super(message);
      this.kind = kind;
    }
  }

  function classifyStatus(status, bodyText) {
    if (status === 401 || status === 403) return ERRORS.AUTH;
    if (status === 429) return ERRORS.QUOTA;
    // Providers signal an empty balance as 402, and some fold it into a
    // 400 whose body mentions the quota - check the text before giving up.
    if (status === 402) return ERRORS.QUOTA;
    if (/quota|billing|insufficient|credit/i.test(bodyText || '')) return ERRORS.QUOTA;
    return ERRORS.PROVIDER;
  }

  // ---------------------------------------------------------------- state
  function isEnabled() { return localStorage.getItem(FLAG_KEY) === '1'; }
  function setEnabled(on) {
    localStorage.setItem(FLAG_KEY, on ? '1' : '0');
    document.dispatchEvent(new CustomEvent('dwai:connectorchange', { detail: { enabled: on } }));
  }

  function getProviderKey() { return localStorage.getItem(PROVIDER_KEY) || DEFAULT_PROVIDER; }
  function setProviderKey(k) { if (PROVIDERS[k]) localStorage.setItem(PROVIDER_KEY, k); }
  function getProvider() { return PROVIDERS[getProviderKey()] || PROVIDERS[DEFAULT_PROVIDER]; }

  function getModel() {
    const stored = localStorage.getItem(MODEL_KEY);
    const p = getProvider();
    if (stored) return stored;
    return p.models.length ? p.models[0].id : '';
  }
  function setModel(m) { localStorage.setItem(MODEL_KEY, m || ''); }

  function getBaseUrl() {
    const custom = (localStorage.getItem(BASEURL_KEY) || '').trim();
    return custom || getProvider().baseUrl;
  }
  function setBaseUrl(u) { localStorage.setItem(BASEURL_KEY, (u || '').trim()); }

  function providerList() {
    return Object.entries(PROVIDERS).map(([key, p]) => ({ key, label: p.label, freeform: !!p.freeform }));
  }
  function modelList() { return getProvider().models.slice(); }

  // ------------------------------------------------------- rate limiting
  // Guards the user's own wallet as much as the provider: a runaway loop
  // in the UI would otherwise bill them for it.
  let sentTimestamps = [];
  function rateLimitOk() {
    const cutoff = Date.now() - 60000;
    sentTimestamps = sentTimestamps.filter((t) => t > cutoff);
    return sentTimestamps.length < MAX_MESSAGES_PER_MINUTE;
  }
  function noteSend() { sentTimestamps.push(Date.now()); }
  function secondsUntilFree() {
    if (!sentTimestamps.length) return 0;
    return Math.max(1, Math.ceil((sentTimestamps[0] + 60000 - Date.now()) / 1000));
  }

  // ------------------------------------------------------ request shaping
  function buildRequest(apiKey, systemPrompt, messages, stream) {
    const provider = getProvider();
    const base = getBaseUrl().replace(/\/+$/, '');
    const model = getModel();

    if (provider.shape === 'anthropic') {
      return {
        url: `${base}/messages`,
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          // Required for browser-originated calls; without it the
          // provider rejects the request rather than the key being wrong.
          'anthropic-dangerous-direct-browser-access': 'true',
        },
        body: {
          model,
          max_tokens: 1600,
          system: systemPrompt,          // top-level, not a message
          messages: messages.filter((m) => m.role !== 'system'),
          stream: !!stream,
        },
      };
    }

    return {
      url: `${base}/chat/completions`,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: {
        model,
        messages: [{ role: 'system', content: systemPrompt }].concat(
          messages.filter((m) => m.role !== 'system')
        ),
        temperature: 0.4,
        // Generous enough that a detailed answer is not truncated
        // mid-sentence, which the brief calls out specifically.
        max_tokens: 1600,
        stream: !!stream,
      },
    };
  }

  function extractDelta(shape, payload) {
    if (shape === 'anthropic') {
      if (payload.type === 'content_block_delta') return (payload.delta && payload.delta.text) || '';
      return '';
    }
    const choice = payload.choices && payload.choices[0];
    return (choice && choice.delta && choice.delta.content) || '';
  }

  async function readError(res) {
    let text = '';
    try { text = (await res.text()).slice(0, 400); } catch (e) {}
    const kind = classifyStatus(res.status, text);
    // Provider text is echoed only for the generic case; auth/quota get a
    // fixed message so nothing from the request can be reflected back.
    if (kind === ERRORS.AUTH) return new ConnectorError(kind, 'auth');
    if (kind === ERRORS.QUOTA) return new ConnectorError(kind, 'quota');
    return new ConnectorError(ERRORS.PROVIDER, `HTTP ${res.status}`);
  }

  /**
   * Stream a completion. `onDelta(text)` fires per chunk so the UI can
   * render as it arrives - without it the user stares at an empty box for
   * the whole generation, which the brief flags as unacceptable.
   * Resolves with the full text. Throws ConnectorError.
   */
  async function chatStream(apiKey, systemPrompt, messages, onDelta) {
    if (!apiKey) throw new ConnectorError(ERRORS.AUTH, 'auth');
    if (!rateLimitOk()) {
      throw new ConnectorError(ERRORS.QUOTA, `rate:${secondsUntilFree()}`);
    }
    const provider = getProvider();
    const req = buildRequest(apiKey, systemPrompt, messages, true);
    noteSend();

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let res;
    try {
      res = await fetch(req.url, {
        method: 'POST',
        headers: req.headers,
        body: JSON.stringify(req.body),
        signal: controller.signal,
      });
    } catch (e) {
      clearTimeout(timer);
      if (e && e.name === 'AbortError') throw new ConnectorError(ERRORS.TIMEOUT, 'timeout');
      // A browser CORS rejection is indistinguishable from an offline
      // failure here; both are "we could not reach it from this tab".
      throw new ConnectorError(ERRORS.NETWORK, 'network');
    }

    if (!res.ok) { clearTimeout(timer); throw await readError(res); }
    if (!res.body) {
      clearTimeout(timer);
      throw new ConnectorError(ERRORS.PROVIDER, 'no stream');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let full = '';

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line; keep the trailing
        // partial frame in the buffer for the next read.
        const frames = buffer.split('\n\n');
        buffer = frames.pop() || '';

        for (const frame of frames) {
          for (const line of frame.split('\n')) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data:')) continue;
            const data = trimmed.slice(5).trim();
            if (!data || data === '[DONE]') continue;
            let payload;
            try { payload = JSON.parse(data); } catch (e) { continue; }
            const delta = extractDelta(provider.shape, payload);
            if (delta) { full += delta; if (onDelta) onDelta(delta); }
          }
        }
      }
    } catch (e) {
      if (e && e.name === 'AbortError') throw new ConnectorError(ERRORS.TIMEOUT, 'timeout');
      throw new ConnectorError(ERRORS.NETWORK, 'network');
    } finally {
      clearTimeout(timer);
    }

    return full;
  }

  /** Non-streaming call, used by the /fit key check. */
  async function chatCompletion(apiKey, systemPrompt, messages) {
    if (!apiKey) throw new ConnectorError(ERRORS.AUTH, 'auth');
    const provider = getProvider();
    const req = buildRequest(apiKey, systemPrompt, messages, false);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    let res;
    try {
      res = await fetch(req.url, {
        method: 'POST', headers: req.headers, body: JSON.stringify(req.body), signal: controller.signal,
      });
    } catch (e) {
      clearTimeout(timer);
      if (e && e.name === 'AbortError') throw new ConnectorError(ERRORS.TIMEOUT, 'timeout');
      throw new ConnectorError(ERRORS.NETWORK, 'network');
    }
    clearTimeout(timer);
    if (!res.ok) throw await readError(res);

    const data = await res.json();
    if (provider.shape === 'anthropic') {
      const block = (data.content || []).find((b) => b.type === 'text');
      return (block && block.text) || '';
    }
    const choice = data.choices && data.choices[0];
    return (choice && choice.message && choice.message.content) || '';
  }

  /**
   * One real, minimal call used to validate the key during /fit. Cheap on
   * purpose - the point is proving the credential and model actually
   * work before the user is told they are connected, rather than
   * discovering it on their first real question.
   */
  async function verifyKey(apiKey) {
    const reply = await chatCompletion(
      apiKey,
      'Reply with the single word: ready',
      [{ role: 'user', content: 'ready check' }]
    );
    return String(reply || '').trim().length > 0;
  }

  window.DWConnector = {
    isEnabled, setEnabled,
    getProviderKey, setProviderKey, providerList,
    getModel, setModel, modelList,
    getBaseUrl, setBaseUrl,
    chatStream, chatCompletion, verifyKey,
    rateLimitOk, secondsUntilFree,
    ERRORS, ConnectorError,
    PROVIDERS,
  };
})();
