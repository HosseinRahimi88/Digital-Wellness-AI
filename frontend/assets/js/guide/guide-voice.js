/*
  Digital Guide voice — browser-native speech only.

  Hard constraint: no API, no cloud service, no key. This uses the
  browser's built-in SpeechSynthesis, which runs on the user's own device
  and costs nothing to operate. There is no network call anywhere in this
  file.

  The part that actually matters for quality is voice selection. Handing
  Persian text to an English voice does not produce accented Persian - it
  produces the engine spelling out letters it does not recognise, which
  sounds broken. So a language is only ever spoken when the device
  genuinely has a voice for it, and `utterance.lang` is always set to the
  matched voice's own tag. If Persian has no voice installed, Persian
  speech is silently disabled while English, Arabic and Chinese keep
  working independently - one missing voice must not mute the others.

  Availability is re-read rather than cached forever: voice lists load
  asynchronously in most browsers (getVoices() is commonly empty on the
  first call and fills in later via the voiceschanged event), and the set
  changes when the user installs a language pack or switches device.

  Public API:
    DWGuideVoice.ready()                 -> Promise, resolves once voices load
    DWGuideVoice.availability()          -> { en: bool, fa: bool, ar: bool, zh: bool }
    DWGuideVoice.isAvailable(lang)       -> bool for one language
    DWGuideVoice.speak(text, opts)       -> speaks; opts: { lang, onStart, onBoundary, onEnd }
    DWGuideVoice.cancel()                -> stop immediately
    DWGuideVoice.isSpeaking()            -> bool
    DWGuideVoice.guideEnabled() / setGuideEnabled(bool)
    DWGuideVoice.voiceEnabled() / setVoiceEnabled(bool)
    DWGuideVoice.onVoicesChanged(fn)     -> subscribe to availability changes
*/
(function () {
  const GUIDE_KEY = 'dwai_guide_enabled';
  const VOICE_KEY = 'dwai_guide_voice_enabled';

  const SUPPORTED = ['en', 'fa', 'ar', 'zh'];

  /* Tags a device might expose for each of our four languages. Matching is
     done on the primary subtag, so `fa-IR`, `fa` and `fa_IR` all count as
     Persian; the extra entries cover engines that label a language by a
     regional variant we would otherwise miss. */
  const LANG_TAGS = {
    en: ['en'],
    fa: ['fa', 'per', 'fas'],
    ar: ['ar'],
    zh: ['zh', 'cmn', 'yue'],
  };

  const synth = (typeof window !== 'undefined' && window.speechSynthesis) || null;

  let voices = [];
  let voicesLoaded = false;
  let readyPromise = null;
  const listeners = [];
  let currentUtterance = null;

  function supported() {
    return !!(synth && typeof window.SpeechSynthesisUtterance === 'function');
  }

  function normalizeTag(tag) {
    return String(tag || '').toLowerCase().replace('_', '-');
  }

  function primarySubtag(tag) {
    return normalizeTag(tag).split('-')[0];
  }

  function refreshVoices() {
    if (!supported()) return [];
    try {
      voices = synth.getVoices() || [];
    } catch (e) {
      voices = [];
    }
    if (voices.length) voicesLoaded = true;
    return voices;
  }

  /* Resolves when the voice list is populated. Chrome fires
     `voiceschanged` shortly after load; Safari usually has voices
     immediately. The timeout means a browser that never fires the event
     still resolves rather than leaving the settings panel spinning
     forever - it just resolves with whatever is there. */
  function ready() {
    if (!supported()) return Promise.resolve([]);
    if (readyPromise) return readyPromise;

    readyPromise = new Promise((resolve) => {
      refreshVoices();
      if (voices.length) { resolve(voices); return; }

      let settled = false;
      const finish = () => {
        if (settled) return;
        settled = true;
        refreshVoices();
        resolve(voices);
      };
      try {
        synth.addEventListener('voiceschanged', finish, { once: true });
      } catch (e) {
        if ('onvoiceschanged' in synth) synth.onvoiceschanged = finish;
      }
      setTimeout(finish, 1500);
    });
    return readyPromise;
  }

  /* Keep reacting to later changes (installing a language pack mid-session
     should light the language up without a reload). */
  if (supported()) {
    const onChange = () => {
      const before = JSON.stringify(availability());
      refreshVoices();
      const after = JSON.stringify(availability());
      if (before !== after) listeners.forEach((fn) => { try { fn(availability()); } catch (e) {} });
    };
    try { synth.addEventListener('voiceschanged', onChange); } catch (e) {}
  }

  /** Best voice for one of our four languages, or null when the device
   *  has none. Prefers a local (offline) voice, then a default one -
   *  remote voices can lag or fail without network. */
  function voiceFor(lang) {
    if (!supported()) return null;
    if (!voicesLoaded) refreshVoices();
    const tags = LANG_TAGS[lang] || [lang];
    const matches = voices.filter((v) => tags.indexOf(primarySubtag(v.lang)) !== -1);
    if (!matches.length) return null;
    return matches.find((v) => v.localService && v.default)
      || matches.find((v) => v.localService)
      || matches.find((v) => v.default)
      || matches[0];
  }

  function isAvailable(lang) {
    return !!voiceFor(lang);
  }

  function availability() {
    const out = {};
    SUPPORTED.forEach((l) => { out[l] = isAvailable(l); });
    return out;
  }

  function onVoicesChanged(fn) {
    if (typeof fn === 'function') listeners.push(fn);
  }

  // ---- User preferences -------------------------------------------

  function readFlag(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return fallback;
      return raw === '1';
    } catch (e) { return fallback; }
  }

  function writeFlag(key, value) {
    try { localStorage.setItem(key, value ? '1' : '0'); } catch (e) {}
  }

  // The guide itself stays on by default (it is a core part of the
  // product); its VOICE stays off by default, because audio that starts
  // talking unprompted is exactly the behaviour people disable a feature
  // over. The user turns speech on deliberately.
  function guideEnabled() { return readFlag(GUIDE_KEY, true); }
  function setGuideEnabled(v) { writeFlag(GUIDE_KEY, v); if (!v) cancel(); }
  function voiceEnabled() { return readFlag(VOICE_KEY, false); }
  function setVoiceEnabled(v) { writeFlag(VOICE_KEY, v); if (!v) cancel(); }

  // ---- Speaking ----------------------------------------------------

  function cancel() {
    currentUtterance = null;
    if (!supported()) return;
    try { synth.cancel(); } catch (e) {}
  }

  function isSpeaking() {
    return !!(supported() && synth.speaking);
  }

  /**
   * Speak `text` in the current (or given) language.
   *
   * Returns false without speaking when: speech is unsupported, the guide
   * or its voice is switched off, or this specific language has no voice
   * on this device. Callers treat false as "show the bubble silently",
   * which is why a missing Persian voice degrades to text rather than to
   * nothing.
   */
  function speak(text, opts) {
    opts = opts || {};
    if (!supported() || !text) return false;
    if (!guideEnabled() || !voiceEnabled()) return false;

    const lang = opts.lang || (window.DWI18n && window.DWI18n.get()) || 'en';
    const voice = voiceFor(lang);
    // No voice for THIS language: stay silent for it and leave the other
    // languages alone. Speaking it with a mismatched voice would read the
    // text as gibberish.
    if (!voice) return false;

    cancel();

    const utterance = new window.SpeechSynthesisUtterance(String(text));
    utterance.voice = voice;
    // Always the matched voice's own tag, never the app's language code -
    // some engines re-select a voice from `lang` and would otherwise
    // switch back to a mismatched one.
    utterance.lang = voice.lang;
    utterance.rate = opts.rate || 0.98;
    utterance.pitch = opts.pitch || 1;
    // Reduced motion signals "less sensory load", so speech comes in
    // softer rather than at full volume.
    const reduced = !!(window.DWMotion && window.DWMotion.prefersReduced());
    utterance.volume = opts.volume != null ? opts.volume : (reduced ? 0.65 : 0.9);

    if (typeof opts.onStart === 'function') utterance.onstart = opts.onStart;
    if (typeof opts.onBoundary === 'function') utterance.onboundary = opts.onBoundary;
    const done = (e) => {
      currentUtterance = null;
      if (typeof opts.onEnd === 'function') opts.onEnd(e);
    };
    utterance.onend = done;
    utterance.onerror = done;

    currentUtterance = utterance;
    try {
      synth.speak(utterance);
    } catch (e) {
      currentUtterance = null;
      return false;
    }
    return true;
  }

  window.DWGuideVoice = {
    supported, ready, availability, isAvailable, voiceFor,
    speak, cancel, isSpeaking, onVoicesChanged,
    guideEnabled, setGuideEnabled, voiceEnabled, setVoiceEnabled,
    SUPPORTED,
  };
})();
