/*
  Optional, OFF-BY-DEFAULT external AI connector.

  Why off by default: the competition brief this project was built for
  is judged assuming zero external API dependency. Whether a user
  supplying their OWN key at runtime would violate that rule is a real
  open question that only the organizers can answer - so this ships
  disabled, behind an explicit opt-in checkbox, and documented as an
  extra outside the competition build rather than claimed as part of it.

  Why it's safe when a user DOES turn it on: every request in this file
  goes straight from this browser tab to the provider's own API. It
  never touches this app's backend, so the key is never seen by our
  server and never stored anywhere but this tab's memory (see
  coach-chat.js's key handling, which this reuses unchanged).
*/
(function () {
  const FLAG_KEY = 'dwai_connector_enabled';
  const DEFAULT_ENDPOINT = 'https://api.openai.com/v1/chat/completions';
  const DEFAULT_MODEL = 'gpt-4o-mini';

  function isEnabled() { return localStorage.getItem(FLAG_KEY) === '1'; }
  function setEnabled(on) {
    localStorage.setItem(FLAG_KEY, on ? '1' : '0');
    document.dispatchEvent(new CustomEvent('dwai:connectorchange', { detail: { enabled: on } }));
  }

  /* Calls the provider directly from the browser - `apiKey` never
     leaves this function call, is never logged, and this file makes no
     other network call anywhere else in the app. */
  async function chatCompletion(apiKey, messages, opts) {
    opts = opts || {};
    let res;
    try {
      res = await fetch(opts.endpoint || DEFAULT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({ model: opts.model || DEFAULT_MODEL, messages, temperature: 0.4 }),
      });
    } catch (e) {
      throw new Error('Could not reach the provider from this browser (network/CORS). The key was not sent anywhere else.');
    }
    if (!res.ok) {
      let detail = '';
      try { detail = (await res.text()).slice(0, 200); } catch (e) {}
      throw new Error(`Provider returned ${res.status}. ${detail}`);
    }
    const data = await res.json();
    const content = data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
    return content || '';
  }

  window.DWConnector = { isEnabled, setEnabled, chatCompletion, DEFAULT_ENDPOINT, DEFAULT_MODEL };
})();
