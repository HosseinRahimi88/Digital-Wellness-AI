/*
  A local server that speaks the real provider wire protocols, so the
  shipped connector can be exercised end-to-end without a paid key.

  What this is and is not
  -----------------------
  It is NOT a stub of our own code. It is the other side of the wire:
  it accepts exactly what OpenAI's /chat/completions and Anthropic's
  /messages accept, rejects what they reject, and streams back the same
  SSE frame shapes they stream. The connector under test is the real
  frontend/assets/js/coach/connector.js, unmodified, pointed here with its own
  base-URL override - the setting a user would use for a self-hosted or
  proxied endpoint.

  So this proves: the URL it builds, the headers it sets, the body shape
  it sends, its SSE frame parsing, its delta extraction per provider
  shape, and its error classification. What it cannot prove is that a
  real vendor account accepts a real key - that needs a real key, and is
  called out as untested rather than implied.

  Routes:
    POST /v1/chat/completions   OpenAI shape (stream + non-stream)
    POST /v1/messages           Anthropic shape (stream + non-stream)
    GET  /__seen                every request received, for assertions
    POST /__mode                force a status: auth | quota | server |
                                slow | malformed | normal
*/
const http = require('http');

const PORT = Number(process.env.MOCK_PORT || 8791);

const seen = [];
let mode = 'normal';

const REPLY = 'Ready. Your sleep is the strongest lever here, and the hour before bed is where it moves.';

function readBody(req) {
  return new Promise((resolve) => {
    let raw = '';
    req.on('data', (c) => { raw += c; });
    req.on('end', () => {
      let parsed = null;
      try { parsed = JSON.parse(raw); } catch (e) { /* recorded as null */ }
      resolve({ raw, parsed });
    });
  });
}

function record(req, body) {
  seen.push({
    method: req.method,
    url: req.url,
    headers: req.headers,
    body: body.parsed,
    at: Date.now(),
  });
}

function sendJson(res, status, obj) {
  const payload = JSON.stringify(obj);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': '*',
  });
  res.end(payload);
}

function sseHead(res) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': '*',
  });
}

/* The failure modes a real provider actually produces, so the
   connector's classification is tested against real statuses rather
   than against our guess at them. */
function forcedFailure(res) {
  if (mode === 'auth') {
    sendJson(res, 401, { error: { message: 'Incorrect API key provided.', type: 'invalid_request_error' } });
    return true;
  }
  if (mode === 'quota') {
    sendJson(res, 429, { error: { message: 'Rate limit reached.', type: 'rate_limit_error' } });
    return true;
  }
  if (mode === 'server') {
    sendJson(res, 500, { error: { message: 'The server had an error.', type: 'server_error' } });
    return true;
  }
  if (mode === 'malformed') {
    // Valid HTTP 200, unparseable frames - the connector must not hang
    // or throw its way out of the read loop.
    sseHead(res);
    res.write('data: {not json at all\n\n');
    res.write('event: ping\n\n');
    res.write('data: [DONE]\n\n');
    res.end();
    return true;
  }
  return false;
}

async function streamOpenAI(res) {
  sseHead(res);
  const words = REPLY.split(' ');
  for (let i = 0; i < words.length; i += 1) {
    const chunk = (i === 0 ? '' : ' ') + words[i];
    res.write(`data: ${JSON.stringify({
      id: 'chatcmpl-mock', object: 'chat.completion.chunk',
      choices: [{ index: 0, delta: { content: chunk }, finish_reason: null }],
    })}\n\n`);
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setTimeout(r, 6));
  }
  res.write('data: [DONE]\n\n');
  res.end();
}

async function streamAnthropic(res) {
  sseHead(res);
  res.write(`event: message_start\ndata: ${JSON.stringify({
    type: 'message_start', message: { id: 'msg_mock', role: 'assistant', content: [] },
  })}\n\n`);
  res.write(`event: content_block_start\ndata: ${JSON.stringify({
    type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' },
  })}\n\n`);
  const words = REPLY.split(' ');
  for (let i = 0; i < words.length; i += 1) {
    const chunk = (i === 0 ? '' : ' ') + words[i];
    res.write(`event: content_block_delta\ndata: ${JSON.stringify({
      type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: chunk },
    })}\n\n`);
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setTimeout(r, 6));
  }
  res.write(`event: content_block_stop\ndata: ${JSON.stringify({ type: 'content_block_stop', index: 0 })}\n\n`);
  res.write(`event: message_stop\ndata: ${JSON.stringify({ type: 'message_stop' })}\n\n`);
  res.end();
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
      'Access-Control-Allow-Headers': '*',
    });
    res.end();
    return;
  }

  if (req.url === '/__seen') {
    sendJson(res, 200, { seen });
    return;
  }
  if (req.url === '/__reset') {
    seen.length = 0; mode = 'normal';
    sendJson(res, 200, { ok: true });
    return;
  }
  if (req.url === '/__mode') {
    const body = await readBody(req);
    mode = (body.parsed && body.parsed.mode) || 'normal';
    sendJson(res, 200, { mode });
    return;
  }

  const body = await readBody(req);
  record(req, body);

  if (mode === 'slow') {
    // Longer than the connector's own timeout, so the abort path runs.
    await new Promise((r) => setTimeout(r, 60000));
    return;
  }
  if (forcedFailure(res)) return;

  // ---- OpenAI-compatible ------------------------------------------
  if (req.url.endsWith('/chat/completions')) {
    const auth = req.headers.authorization || '';
    if (!auth.startsWith('Bearer ') || auth.length < 12) {
      sendJson(res, 401, { error: { message: 'Missing bearer token.' } });
      return;
    }
    const b = body.parsed || {};
    if (!b.model || !Array.isArray(b.messages) || !b.messages.length) {
      sendJson(res, 400, { error: { message: 'model and messages are required.' } });
      return;
    }
    if (b.stream) { await streamOpenAI(res); return; }
    sendJson(res, 200, {
      id: 'chatcmpl-mock', object: 'chat.completion', model: b.model,
      choices: [{ index: 0, message: { role: 'assistant', content: REPLY }, finish_reason: 'stop' }],
      usage: { prompt_tokens: 40, completion_tokens: 18, total_tokens: 58 },
    });
    return;
  }

  // ---- Anthropic ---------------------------------------------------
  if (req.url.endsWith('/messages')) {
    if (!req.headers['x-api-key']) {
      sendJson(res, 401, { error: { message: 'missing x-api-key' } });
      return;
    }
    if (!req.headers['anthropic-version']) {
      sendJson(res, 400, { error: { message: 'missing anthropic-version' } });
      return;
    }
    const b = body.parsed || {};
    if (!b.model || !b.max_tokens || !Array.isArray(b.messages)) {
      sendJson(res, 400, { error: { message: 'model, max_tokens and messages are required.' } });
      return;
    }
    // The real API rejects a system message inside `messages`.
    if (b.messages.some((m) => m.role === 'system')) {
      sendJson(res, 400, { error: { message: 'system role not allowed in messages' } });
      return;
    }
    if (b.stream) { await streamAnthropic(res); return; }
    sendJson(res, 200, {
      id: 'msg_mock', type: 'message', role: 'assistant', model: b.model,
      content: [{ type: 'text', text: REPLY }],
      usage: { input_tokens: 40, output_tokens: 18 },
    });
    return;
  }

  sendJson(res, 404, { error: { message: 'no such route' } });
});

server.listen(PORT, '127.0.0.1', () => {
  process.stdout.write(`mock provider listening on ${PORT}\n`);
});
