/*
  League chat (D-1-b, D-1-c, D-1-d) - the client.

  Two things this file does deliberately, both of them security rather
  than style:

  1. Message bodies go in as text nodes, never innerHTML. A chat is the
     one surface in this app where the content is written by another
     person, so it is the one place where an injected string would have
     a real author. The server stores bodies exactly as typed - that is
     correct, and it is why the escaping has to happen here, at the only
     point where text becomes DOM.

  2. Nothing about who may read or write is decided here. The client
     never sends a membership list; it asks and renders the answer. A
     403 or 404 is displayed as-is rather than worked around.
*/
(function () {
  const POLL_MS = 6000;
  let pollTimer = null;
  let activeConversationId = null;

  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : (t && t.en) || '');

  const T = {
    title: { en: 'Chats', fa: 'گفتگوها', ar: 'المحادثات', zh: '聊天' },
    empty: {
      en: 'No conversations yet. Open one from a friend in your league.',
      fa: 'هنوز گفتگویی نیست. از یکی از دوستان لیگت یکی را باز کن.',
      ar: 'لا محادثات بعد. افتح واحدة من أحد أصدقاء دوريك.',
      zh: '还没有对话。从你排行榜里的好友那里开一个。',
    },
    emptyThread: {
      en: 'Nothing here yet. Say something.',
      fa: 'هنوز چیزی اینجا نیست. یک چیزی بگو.',
      ar: 'لا شيء هنا بعد. قل شيئاً.',
      zh: '这里还什么都没有。说点什么吧。',
    },
    placeholder: { en: 'Write a message…', fa: 'یک پیام بنویس…', ar: 'اكتب رسالة…', zh: '写点什么…' },
    send: { en: 'Send', fa: 'بفرست', ar: 'إرسال', zh: '发送' },
    rename: { en: 'Rename', fa: 'تغییر نام', ar: 'إعادة تسمية', zh: '重命名' },
    renamePrompt: {
      en: 'New name for this conversation:',
      fa: 'نام تازه برای این گفتگو:',
      ar: 'اسم جديد لهذه المحادثة:',
      zh: '这段对话的新名称：',
    },
    // The name is shared by design (see LeagueChatService.rename_conversation:
    // two people calling one thread different names is worse than neither
    // being able to rename it). Saying so here, because a rename the user
    // believes is private but is not would be the wrong kind of surprise.
    renamed: {
      en: 'Renamed. Everyone in this conversation sees the new name.',
      fa: 'نامش عوض شد. همه‌ی کسانی که در این گفتگو هستند نام تازه را می‌بینند.',
      ar: 'تمت إعادة التسمية. كل من في هذه المحادثة يرى الاسم الجديد.',
      zh: '已重命名。这段对话中的所有人都会看到新名称。',
    },
    newGroup: { en: 'New group', fa: 'گروه تازه', ar: 'مجموعة جديدة', zh: '新建群组' },
    groupName: { en: 'Group name', fa: 'نام گروه', ar: 'اسم المجموعة', zh: '群组名称' },
    create: { en: 'Create', fa: 'بساز', ar: 'إنشاء', zh: '创建' },
    cancel: { en: 'Cancel', fa: 'انصراف', ar: 'إلغاء', zh: '取消' },
    leave: { en: 'Leave group', fa: 'ترک گروه', ar: 'مغادرة المجموعة', zh: '退出群组' },
    deleted: { en: 'message withdrawn', fa: 'پیام پس گرفته شد', ar: 'سُحبت الرسالة', zh: '消息已撤回' },
    retract: { en: 'Retract', fa: 'پس بگیر', ar: 'اسحب', zh: '撤回' },
    report: { en: 'Report', fa: 'گزارش', ar: 'إبلاغ', zh: '举报' },
    block: { en: 'Block', fa: 'مسدود کن', ar: 'حظر', zh: '拉黑' },
    reportPrompt: {
      en: 'What is wrong with this message? A person reads these — it is not automatic.',
      fa: 'مشکل این پیام چیست؟ این‌ها را یک نفر می‌خواند — خودکار نیست.',
      ar: 'ما المشكلة في هذه الرسالة؟ يقرأ هذه شخصٌ ما — ليست تلقائية.',
      zh: '这条消息有什么问题？这些会有人来看——不是自动处理的。',
    },
    reportDone: {
      en: 'Reported. Nothing is shown to them about this.',
      fa: 'گزارش شد. چیزی از این بابت به او نشان داده نمی‌شود.',
      ar: 'تم الإبلاغ. لا يُعرض عليه شيء بخصوص هذا.',
      zh: '已举报。关于这件事不会向对方显示任何内容。',
    },
    blockConfirm: {
      en: 'Block this person? Neither of you will be able to read or write this conversation until you undo it.',
      fa: 'این شخص مسدود شود؟ تا وقتی برنگردانی، هیچ‌کدامتان نمی‌توانید این گفتگو را بخوانید یا بنویسید.',
      ar: 'حظر هذا الشخص؟ لن يتمكن أي منكما من قراءة هذه المحادثة أو الكتابة فيها حتى تتراجع.',
      zh: '拉黑这个人？在你撤销之前，你们双方都无法阅读或书写这段对话。',
    },
    rateLimited: {
      en: 'That is a lot of messages very quickly. Give it a moment.',
      fa: 'این تعداد پیام در این مدت کوتاه زیاد است. کمی صبر کن.',
      ar: 'هذا عدد كبير من الرسائل في وقت قصير جداً. امهله لحظة.',
      zh: '短时间内消息太多了。稍等一下。',
    },
    closed: {
      en: 'This conversation is closed — the connection behind it was removed.',
      fa: 'این گفتگو بسته است — ارتباطی که پشتش بود حذف شده.',
      ar: 'هذه المحادثة مغلقة — أُزيل الاتصال الذي كان خلفها.',
      zh: '这段对话已关闭——它背后的连接已被移除。',
    },
  };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;   // always textContent
    return node;
  }

  function timeLabel(iso) {
    try {
      return new Date(iso).toLocaleTimeString(window.DWI18n.get(), { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '';
    }
  }

  // ---- rendering ----------------------------------------------------
  function renderConversationList(data, mounts, onOpen) {
    const list = mounts.list;
    if (!list) return;
    list.innerHTML = '';
    const conversations = (data && data.conversations) || [];
    if (!conversations.length) {
      list.appendChild(el('p', 'muted', pick(T.empty)));
      return;
    }
    conversations.forEach((c) => {
      const me = window.DWChatState.userId;
      const others = (c.member_ids || []).filter((id) => id !== me);
      // A renamed thread keeps its own name whatever kind it is. Only an
      // unnamed direct chat falls back to who is in it, which is what
      // made four "Direct chat" rows indistinguishable before.
      const name = c.title
        || (c.kind === 'group' ? '' : (c.member_names && c.member_names[others[0]]))
        || '—';

      const row = el('div', 'chat-conversation-row');

      const button = el('button', 'chat-conversation' + (c.conversation_id === activeConversationId ? ' is-active' : ''));
      button.type = 'button';
      button.appendChild(el('span', 'chat-conversation-icon', c.kind === 'group' ? '👥' : '💬'));
      button.appendChild(el('span', 'chat-conversation-name', name));
      button.addEventListener('click', () => onOpen(c));
      row.appendChild(button);

      // Renaming was built on the server and reachable from the API
      // client, but had no control anywhere - so in practice a thread
      // could not be renamed at all.
      const renameBtn = el('button', 'chat-conversation-rename', '✏️');
      renameBtn.type = 'button';
      renameBtn.title = pick(T.rename);
      renameBtn.setAttribute('aria-label', pick(T.rename));
      renameBtn.addEventListener('click', async (e) => {
        e.stopPropagation();  // never opens the thread as a side effect
        const next = window.prompt(pick(T.renamePrompt), c.title || name);
        if (next === null) return;
        const trimmed = next.trim();
        if (!trimmed) return;
        try {
          await window.DWApi.chatRenameConversation(c.conversation_id, trimmed);
          c.title = trimmed;
          renderConversationList(data, mounts, onOpen);
          // The open thread's header shows the same name.
          if (mounts.title && c.conversation_id === activeConversationId) {
            mounts.title.textContent = trimmed;
          }
          if (window.DWToast) window.DWToast.info(pick(T.renamed));
        } catch (err) {
          if (window.DWToast) window.DWToast.error(err.message);
        }
      });
      row.appendChild(renameBtn);

      list.appendChild(row);
    });
  }

  function renderMessages(payload, mounts) {
    const thread = mounts.thread;
    if (!thread) return;
    thread.innerHTML = '';
    const me = window.DWChatState.userId;
    const messages = (payload && payload.messages) || [];
    if (!messages.length) {
      thread.appendChild(el('p', 'muted', pick(T.emptyThread)));
      return;
    }
    messages.forEach((m) => {
      const mine = m.sender_id === me;
      const row = el('div', 'chat-message' + (mine ? ' is-mine' : ''));
      if (!mine && payload.conversation && payload.conversation.kind === 'group') {
        row.appendChild(el('span', 'chat-sender', m.sender_name || '—'));
      }
      // The body: a text node, every time.
      const body = el('p', 'chat-body' + (m.deleted ? ' is-deleted' : ''),
        m.deleted ? pick(T.deleted) : m.body);
      row.appendChild(body);
      row.appendChild(el('time', 'chat-time', timeLabel(m.sent_at_utc)));

      if (!m.deleted) {
        const actions = el('div', 'chat-actions');
        if (mine) {
          const retract = el('button', 'chat-action', pick(T.retract));
          retract.type = 'button';
          retract.addEventListener('click', async () => {
            await window.DWApi.chatDeleteMessage(m.message_id);
            refresh(mounts);
          });
          actions.appendChild(retract);
        } else {
          const report = el('button', 'chat-action', pick(T.report));
          report.type = 'button';
          report.addEventListener('click', async () => {
            const reason = window.prompt(pick(T.reportPrompt), '');
            if (reason === null) return;
            await window.DWApi.chatReport(m.message_id, reason, false);
            window.DWToast.info(pick(T.reportDone));
          });
          const block = el('button', 'chat-action is-danger', pick(T.block));
          block.type = 'button';
          block.addEventListener('click', async () => {
            if (!window.confirm(pick(T.blockConfirm))) return;
            await window.DWApi.chatBlock(m.sender_id);
            activeConversationId = null;
            refresh(mounts);
          });
          actions.appendChild(report);
          actions.appendChild(block);
        }
        row.appendChild(actions);
      }
      thread.appendChild(row);
    });
    thread.scrollTop = thread.scrollHeight;
  }

  // ---- data ---------------------------------------------------------
  async function refresh(mounts) {
    if (!window.DWApi || !window.DWApi.chatConversations) return;
    let list;
    try {
      list = await window.DWApi.chatConversations();
    } catch (e) {
      return;
    }
    renderConversationList(list, mounts, (c) => open(c.conversation_id, mounts));

    if (!activeConversationId) {
      if (mounts.thread) mounts.thread.innerHTML = '';
      if (mounts.composer) mounts.composer.classList.add('hidden');
      return;
    }
    try {
      const payload = await window.DWApi.chatMessages(activeConversationId);
      renderMessages(payload, mounts);
      if (mounts.composer) mounts.composer.classList.remove('hidden');
      if (mounts.title) {
        const me = window.DWChatState.userId;
        const c = payload.conversation;
        const others = c ? (c.member_ids || []).filter((id) => id !== me) : [];
        mounts.title.textContent = c
          ? (c.kind === 'group' ? c.title : (c.member_names && c.member_names[others[0]]) || '')
          : '';
      }
      if (mounts.leave) {
        mounts.leave.classList.toggle(
          'hidden', !(payload.conversation && payload.conversation.kind === 'group'));
      }
    } catch (e) {
      // A closed or blocked conversation answers with an error rather
      // than an empty list, and saying so is the point.
      activeConversationId = null;
      if (mounts.thread) {
        mounts.thread.innerHTML = '';
        mounts.thread.appendChild(el('p', 'muted', pick(T.closed)));
      }
      if (mounts.composer) mounts.composer.classList.add('hidden');
    }
  }

  function open(conversationId, mounts) {
    activeConversationId = conversationId;
    refresh(mounts);
  }

  async function send(mounts) {
    const input = mounts.input;
    if (!input || !activeConversationId) return;
    const body = input.value.trim();
    if (!body) return;
    input.value = '';
    try {
      await window.DWApi.chatSend(activeConversationId, body);
      if (window.DWSound && window.DWSound.messageSend) window.DWSound.messageSend();
      refresh(mounts);
    } catch (e) {
      input.value = body;   // never silently lose what someone typed
      const rateLimited = e && e.fieldErrors == null && /rate|slow/i.test(e.message || '');
      window.DWToast.error(rateLimited ? pick(T.rateLimited) : (e.message || ''));
    }
  }

  function init(opts) {
    const mounts = {
      list: document.getElementById(opts.listId),
      thread: document.getElementById(opts.threadId),
      composer: document.getElementById(opts.composerId),
      input: document.getElementById(opts.inputId),
      sendBtn: document.getElementById(opts.sendId),
      title: document.getElementById(opts.titleId),
      leave: document.getElementById(opts.leaveId),
    };
    if (!mounts.list) return;

    if (mounts.input) {
      mounts.input.placeholder = pick(T.placeholder);
      mounts.input.addEventListener('keydown', (e) => {
        // Enter sends, Shift+Enter is a newline - the convention
        // everywhere else, and getting it backwards is the fastest way
        // to make a chat feel broken.
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(mounts); }
      });
    }
    if (mounts.sendBtn) mounts.sendBtn.addEventListener('click', () => send(mounts));
    if (mounts.leave) {
      mounts.leave.addEventListener('click', async () => {
        if (!activeConversationId) return;
        await window.DWApi.chatLeaveGroup(activeConversationId);
        activeConversationId = null;
        refresh(mounts);
      });
    }

    refresh(mounts);
    // Polling, not a socket: this app has no realtime layer and adding
    // one for a league chat would be a second transport to secure.
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => refresh(mounts), POLL_MS);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') refresh(mounts);
    });
    return { open: (id) => open(id, mounts), refresh: () => refresh(mounts) };
  }

  window.DWChatState = { userId: '' };
  window.DWLeagueChat = { init, T };
})();
