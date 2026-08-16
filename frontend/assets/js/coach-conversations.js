/*
  DWCoachConversations - saved, renameable coach conversations.

  Before this, the coach kept its turns in a plain array in memory. A
  reload, a navigation, or an accidental back-button lost the whole
  exchange, and there was no way to keep two separate threads - "my
  sleep" and "why is my score down" were the same scrollback.

  Storage is localStorage, deliberately, and per account: the coach
  answers from the user's own numbers, so a conversation is as personal
  as the check-ins behind it and has no business on a server that does
  not need it. The account id is part of the key, so signing in as
  someone else - or entering a demo - shows their threads and not the
  previous user's.

  A conversation is titled from its first user message until the user
  renames it, because "New conversation" repeated eight times is a list
  that cannot be navigated.
*/
(function () {
  const PREFIX = 'dwai_coach_convos_';
  const MAX_CONVERSATIONS = 50;
  const MAX_MESSAGES = 400;
  const TITLE_MAX = 60;

  /* Which account's threads these are. The coach reads the signed-in
     user's data, so keying by account is what stops a demo session -
     or the next person to sign in on a shared machine - opening
     somebody else's conversation. */
  function scope() {
    try {
      const token = (window.DWApi && window.DWApi.getToken && window.DWApi.getToken()) || '';
      if (!token) return 'anon';
      // The JWT's subject, read without trusting it for anything: this
      // is a storage key, never an authorization decision.
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      return String(payload.sub || 'anon').slice(0, 40);
    } catch (e) {
      return 'anon';
    }
  }

  function key() { return PREFIX + scope(); }

  function readAll() {
    try {
      const raw = JSON.parse(localStorage.getItem(key()) || '[]');
      return Array.isArray(raw) ? raw : [];
    } catch (e) {
      return [];
    }
  }

  function writeAll(list) {
    try {
      localStorage.setItem(key(), JSON.stringify(list.slice(0, MAX_CONVERSATIONS)));
    } catch (e) {
      // Quota. Drop the oldest half rather than losing the newest
      // thread, which is the one the user is actually in.
      try {
        localStorage.setItem(key(), JSON.stringify(list.slice(0, Math.ceil(MAX_CONVERSATIONS / 2))));
      } catch (err) { /* storage disabled entirely - stay in memory */ }
    }
  }

  function newId() {
    return 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function titleFrom(text) {
    const clean = String(text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return '';
    return clean.length > TITLE_MAX ? clean.slice(0, TITLE_MAX - 1) + '…' : clean;
  }

  /** Newest first - the list is read top-down and the thread you were
   *  just in should be the one you reach for. */
  function list() {
    return readAll().sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0));
  }

  function get(id) {
    return readAll().find((c) => c.id === id) || null;
  }

  function create(firstMessage) {
    const conversation = {
      id: newId(),
      title: titleFrom(firstMessage) || '',
      renamed: false,
      created_at: Date.now(),
      updated_at: Date.now(),
      messages: [],
    };
    const all = readAll();
    all.unshift(conversation);
    writeAll(all);
    return conversation;
  }

  function append(id, role, content) {
    const all = readAll();
    const conversation = all.find((c) => c.id === id);
    if (!conversation) return null;
    conversation.messages.push({ role, content: String(content || ''), at: Date.now() });
    if (conversation.messages.length > MAX_MESSAGES) {
      conversation.messages = conversation.messages.slice(-MAX_MESSAGES);
    }
    // The first thing the user says names the thread, unless they have
    // taken over the name themselves.
    if (!conversation.renamed && !conversation.title && role === 'user') {
      conversation.title = titleFrom(content);
    }
    conversation.updated_at = Date.now();
    writeAll(all);
    return conversation;
  }

  /* Write a whole thread at once, with its own timestamps and an
     arbitrary marker.

     create()+append() cannot do this: they stamp Date.now() on every
     turn, so a set of threads written in one go all claim to have
     happened in the same second. Demo Mode needs threads dated across
     the demo user's history - a 23-day user who has been talking to the
     coach since day 4 - and needs to know which threads it wrote, so it
     can replace its own without touching one the reviewer typed.

     Marked threads are the ONLY thing DWCoachDemoChats is allowed to
     remove; see coach-demo-chats.js. */
  function importThread(spec) {
    const messages = (spec.messages || []).map((m, i) => ({
      role: m.role === 'user' ? 'user' : 'assistant',
      content: String(m.content || ''),
      // Turns inside a thread are a minute apart, so a replayed thread
      // reads in the order it was written rather than all at once.
      at: (spec.created_at || Date.now()) + i * 60000,
    }));
    const conversation = {
      id: newId(),
      title: titleFrom(spec.title) || '',
      renamed: true,
      created_at: spec.created_at || Date.now(),
      updated_at: spec.updated_at || spec.created_at || Date.now(),
      messages: messages.slice(0, MAX_MESSAGES),
    };
    if (spec.marker) conversation.marker = String(spec.marker);
    // Which language the thread was WRITTEN in. A saved conversation is
    // a record of what was said, so it is never retranslated in place -
    // but a demo's threads are generated, and a reviewer who switches
    // the app to Persian should not be handed an English chat log. The
    // seeder compares this and rewrites its own threads; see
    // coach-demo-chats.js.
    if (spec.lang) conversation.lang = String(spec.lang);
    const all = readAll();
    all.unshift(conversation);
    writeAll(all);
    return conversation;
  }

  /** Every thread carrying `marker`, and nothing else. */
  function listMarked(marker) {
    return readAll().filter((c) => c.marker === marker);
  }

  /** Drop only the threads this marker owns. A thread the user typed
   *  has no marker and is never touched. */
  function removeMarked(marker) {
    writeAll(readAll().filter((c) => c.marker !== marker));
  }

  function rename(id, title) {
    const all = readAll();
    const conversation = all.find((c) => c.id === id);
    if (!conversation) return false;
    const clean = titleFrom(title);
    if (!clean) return false;
    conversation.title = clean;
    // Sticky: an explicit name is never overwritten by a later first
    // message, which is the whole point of having renamed it.
    conversation.renamed = true;
    conversation.updated_at = Date.now();
    writeAll(all);
    return true;
  }

  function remove(id) {
    writeAll(readAll().filter((c) => c.id !== id));
  }

  function clearAll() {
    try { localStorage.removeItem(key()); } catch (e) {}
  }

  /** The turns to replay into a provider, oldest first, capped. */
  function turnsFor(id, limit) {
    const conversation = get(id);
    if (!conversation) return [];
    const messages = conversation.messages.filter((m) => m.role === 'user' || m.role === 'assistant');
    return (limit ? messages.slice(-limit) : messages).map((m) => ({
      role: m.role, content: m.content,
    }));
  }

  window.DWCoachConversations = {
    list, get, create, append, rename, remove, clearAll, turnsFor, titleFrom,
    importThread, listMarked, removeMarked,
    MAX_MESSAGES,
  };
})();
