/* Friends League page controller. See services/social/league_service.py for
   the consent model this mirrors exactly: nothing is visible to a
   friend until both sides have explicitly agreed to it, category by
   category, and either side can change or revoke it at any time. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('league');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  const lang = () => (window.DWI18n && window.DWI18n.get()) || 'en';
  /* Every runtime string on this page goes through DWI18n.pick(), which
     requires each entry to name all four languages. The previous
     `lang === 'fa' ? fa : en` form silently served English to Arabic and
     Chinese readers, which is what made this page look half-translated. */
  const pick = (table) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(table) : (table.en || ''));

  const CATEGORIES = [
    { key: 'persona', en: 'Your persona title', fa: 'عنوان پرسونای تو', ar: 'عنوان شخصيتك', zh: '你的人格画像称号' },
    { key: 'score', en: 'Your latest score', fa: 'آخرین امتیازت', ar: 'أحدث نتيجة لك', zh: '你的最新分数' },
    { key: 'rank', en: 'Your leaderboard rank', fa: 'رتبه‌ات در جدول', ar: 'ترتيبك في اللوحة', zh: '你的排行榜名次' },
    { key: 'plan_focus', en: 'Your current top factor', fa: 'مهم‌ترین عامل فعلی‌ات', ar: 'أهم عامل لديك حالياً', zh: '你当前的首要因素' },
  ];
  const catLabel = (key) => { const c = CATEGORIES.find((x) => x.key === key); return c ? pick(c) : key; };

  const L = {
    not_enough_history: { en: 'not enough history yet', fa: 'هنوز داده‌ی کافی نیست', ar: 'لا يوجد سجل كافٍ بعد', zh: '历史数据还不够' },
    request_sent: { en: 'Request sent.', fa: 'درخواست ارسال شد.', ar: 'تم إرسال الطلب.', zh: '请求已发送。' },
    wants_to_connect: { en: 'wants to connect', fa: 'می‌خواهد وصل شود', ar: 'يريد التواصل معك', zh: '想与你连接' },
    they_share_if_approve: { en: 'They will share this with you if you approve', fa: 'آنها این‌ها را با تو به اشتراک می‌گذارند اگر تایید کنی', ar: 'سيشاركون هذا معك إذا وافقت', zh: '如果你批准，他们将与你分享' },
    nothing: { en: 'nothing', fa: 'هیچ‌چیز', ar: 'لا شيء', zh: '无' },
    what_share_back: { en: 'What will you share back?', fa: 'تو در ازای آن چه چیزی به اشتراک می‌گذاری؟', ar: 'ماذا ستشارك في المقابل؟', zh: '你将回馈分享什么？' },
    approve: { en: 'Approve', fa: 'تایید', ar: 'موافقة', zh: '批准' },
    decline: { en: 'Decline', fa: 'رد کردن', ar: 'رفض', zh: '拒绝' },
    connected: { en: 'Connected.', fa: 'وصل شدید.', ar: 'تم الاتصال.', zh: '已连接。' },
    no_friends: { en: 'No friends connected yet.', fa: 'هنوز هیچ دوستی متصل نشده.', ar: 'لا يوجد أصدقاء متصلون بعد.', zh: '还没有已连接的好友。' },
    what_you_see: { en: 'What you can see', fa: 'آنچه می‌بینی', ar: 'ما يمكنك رؤيته', zh: '你能看到的内容' },
    what_youre_sharing: { en: "What you're sharing", fa: 'آنچه به اشتراک می‌گذاری', ar: 'ما تشاركه أنت', zh: '你正在分享的内容' },
    save_sharing: { en: 'Save sharing', fa: 'ذخیره‌ی اشتراک‌گذاری', ar: 'حفظ المشاركة', zh: '保存分享设置' },
    revoke: { en: 'Revoke', fa: 'قطع ارتباط', ar: 'إلغاء الاتصال', zh: '解除连接' },
    you: { en: 'You', fa: 'خودت', ar: 'أنت', zh: '你' },
    vs_7_days: { en: 'vs 7 days ago', fa: 'نسبت به ۷ روز پیش', ar: 'مقارنةً بقبل ٧ أيام', zh: '相比 7 天前' },
    hasnt_shared: { en: "hasn't shared anything visible", fa: 'چیزی به اشتراک نگذاشته', ar: 'لم يشارك أي شيء مرئي', zh: '未分享任何可见内容' },
    awaiting_approval: { en: 'awaiting their approval', fa: 'در انتظار تایید او', ar: 'بانتظار موافقتهم', zh: '等待对方批准' },
    awaiting_name: { en: 'Your friend', fa: 'دوست تو', ar: 'صديقك', zh: '你的好友' },
    you_offered: { en: "You offered to share", fa: 'تو پیشنهاد دادی این‌ها را به اشتراک بگذاری', ar: 'عرضتَ مشاركة', zh: '你提出分享' },
    signed_in_as: { en: 'Signed in as', fa: 'وارد شده به‌عنوان', ar: 'مسجَّل الدخول باسم', zh: '当前登录账号' },
  };

  function renderCategoryChecks(container, preselected) {
    container.innerHTML = '';
    CATEGORIES.forEach((c) => {
      const label = document.createElement('label');
      label.className = 'league-cat-check';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.value = c.key;
      input.checked = (preselected || []).includes(c.key);
      label.appendChild(input);
      label.appendChild(document.createTextNode(' ' + pick(c)));
      container.appendChild(label);
    });
  }
  function readChecked(container) {
    return Array.from(container.querySelectorAll('input:checked')).map((i) => i.value);
  }

  const RULES = {
    en: [
      'A friend sees NOTHING about you until you explicitly approve their request.',
      'You choose exactly which categories they see - persona, score, rank, current top factor - one at a time.',
      'They can never see your raw survey answers, habit minutes, or anything you have not explicitly ticked.',
      'You can change what you share, or end the connection entirely, at any moment from this page.',
      'The comparison is built around your own past first - friends are shown alongside, not instead of it.',
    ],
    fa: [
      'یک دوست تا وقتی درخواستش را صریحاً تایید نکنی، هیچ‌چیزی درباره‌ی تو نمی‌بیند.',
      'تو دقیقاً انتخاب می‌کنی چه دسته‌هایی را ببیند — پرسونا، امتیاز، رتبه، مهم‌ترین عامل فعلی — یکی‌یکی.',
      'او هرگز پاسخ‌های خام پرسشنامه، دقیقه‌های عادت، یا هرچیزی که تیک نزده‌ای را نمی‌بیند.',
      'هر لحظه از همین صفحه می‌توانی چیزی که به اشتراک می‌گذاری را تغییر بدهی یا کلاً ارتباط را قطع کنی.',
      'مقایسه اول حول گذشته‌ی خودت ساخته شده — دوستان کنارش نشان داده می‌شوند، نه به‌جایش.',
    ],
    ar: [
      'لا يرى الصديق أي شيء عنك حتى توافق صراحةً على طلبه.',
      'أنت تختار بالضبط الفئات التي يراها — الشخصية، النتيجة، الترتيب، أهم عامل حالي — واحدة تلو الأخرى.',
      'لا يمكنه أبداً رؤية إجاباتك الخام أو دقائق عاداتك أو أي شيء لم تحدده صراحةً.',
      'يمكنك تغيير ما تشاركه، أو إنهاء الاتصال تماماً، في أي لحظة من هذه الصفحة.',
      'المقارنة مبنية أولاً حول ماضيك أنت — يُعرض الأصدقاء إلى جانبه، لا بدلاً منه.',
    ],
    zh: [
      '在你明确批准好友的请求之前，对方看不到关于你的任何信息。',
      '你逐项精确选择对方能看到哪些类别——人格画像、分数、名次、当前首要因素。',
      '对方永远无法看到你的原始问卷答案、习惯时长，或任何你未明确勾选的内容。',
      '你可以随时在本页面更改分享内容，或彻底结束该连接。',
      '对比首先围绕你自己的过去构建——好友是并列展示，而不是取而代之。',
    ],
  };

  function applyStaticCopy() {
    document.getElementById('leagueRulesList').innerHTML = pick(RULES).map((r) => `<li>${r}</li>`).join('');
  }

  let me;
  try { me = await window.DWApi.leagueMe(); } catch (e) { window.DWToast.error(e.message); return; }

  applyStaticCopy();
  document.addEventListener('dwai:langchange', applyStaticCopy);

  // Your own progress + future path - always shown, never gated behind
  // League rules acceptance (it's your own data, not a friend's), and
  // rendered first so it reads as the headline of the page, with the
  // friends leaderboard as secondary context below it.
  await loadProgress();

  async function loadProgress() {
    let data;
    try { data = await window.DWApi.leagueLeaderboard(); } catch (e) { return; }
    const self = data.self_entry || {};
    const grid = document.getElementById('leagueProgressGrid');
    const futureWrap = document.getElementById('leagueFutureWrap');
    const emptyWrap = document.getElementById('leagueProgressEmpty');

    if (self.score == null) {
      grid.classList.add('hidden');
      futureWrap.classList.add('hidden');
      emptyWrap.classList.remove('hidden');
      return;
    }
    grid.classList.remove('hidden');
    emptyWrap.classList.add('hidden');

    document.getElementById('leagueProgressCurrent').textContent = `${Math.round(self.score)}/100`;

    const deltaEl = document.getElementById('leagueProgressDelta');
    deltaEl.classList.remove('is-up', 'is-down');
    if (self.score_7d_ago != null) {
      const delta = self.score - self.score_7d_ago;
      deltaEl.textContent = `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}`;
      if (Math.abs(delta) >= 0.5) deltaEl.classList.add(delta > 0 ? 'is-up' : 'is-down');
    } else {
      deltaEl.textContent = pick(L.not_enough_history);
    }

    await loadFuturePreview(futureWrap);
  }

  async function loadFuturePreview(futureWrap) {
    let payload;
    try { payload = JSON.parse(localStorage.getItem('dwai_last_payload') || 'null'); } catch (e) { payload = null; }
    if (!payload) { futureWrap.classList.add('hidden'); return; }

    let result;
    try {
      result = await window.DWApi.futurePathCompare(payload, ['status_quo', 'gradual_improvement', 'committed_change']);
    } catch (e) { futureWrap.classList.add('hidden'); return; }

    const paths = (result.paths || []).filter((p) => p.regression_score != null);
    if (!paths.length) { futureWrap.classList.add('hidden'); return; }

    const FUTURE_LABELS = {
      status_quo: { en: 'If nothing changes', fa: 'اگر چیزی تغییر نکند', ar: 'إذا لم يتغير شيء', zh: '如果什么都不改变' },
      gradual_improvement: { en: 'Small, steady changes', fa: 'تغییرات کوچک و پیوسته', ar: 'تغييرات صغيرة ومستمرة', zh: '小而稳定的改变' },
      committed_change: { en: 'A real, committed effort', fa: 'تلاش واقعی و پیوسته', ar: 'جهد حقيقي وملتزم', zh: '真正投入的努力' },
    };
    const row = document.getElementById('leagueFutureRow');
    row.innerHTML = '';
    paths.forEach((p) => {
      const chip = document.createElement('div');
      chip.className = 'league-future-chip';
      const isBest = p.key === result.best_path_key;
      const l = FUTURE_LABELS[p.key];
      chip.innerHTML = `
        <div class="num${isBest ? ' is-best' : ''}">${Math.round(p.regression_score)}/100</div>
        <div class="lbl">${l ? pick(l) : p.name}</div>
      `;
      row.appendChild(chip);
    });
    futureWrap.classList.remove('hidden');
  }
  document.addEventListener('dwai:langchange', () => { loadProgress(); });

  if (!me.rules_accepted) {
    document.getElementById('leagueRulesGate').classList.remove('hidden');
    const checkbox = document.getElementById('leagueRulesCheckbox');
    const acceptBtn = document.getElementById('leagueAcceptBtn');
    checkbox.addEventListener('change', () => { acceptBtn.disabled = !checkbox.checked; });
    acceptBtn.addEventListener('click', async () => {
      try {
        me = await window.DWApi.leagueAcceptRules();
        document.getElementById('leagueRulesGate').classList.add('hidden');
        document.getElementById('leagueContent').classList.remove('hidden');
        await loadAll();
      } catch (e) { window.DWToast.error(e.message); }
    });
    if (window.DWGuide) window.DWGuide.explain('league_rules', { force: true });
    return;
  }

  document.getElementById('leagueContent').classList.remove('hidden');
  await loadAll();

  async function loadAll() {
    document.getElementById('leagueMyCode').textContent = me.invite_code;

    // Invite codes and inboxes are per-account, but the login token lives
    // in this browser's localStorage - so testing two accounts in one
    // browser silently keeps you as the first one. Naming the current
    // account here makes that immediately obvious instead of looking
    // like a duplicated code or a lost request.
    const who = document.getElementById('leagueWhoAmI');
    if (who) who.textContent = `${pick(L.signed_in_as)}: ${account.display_name || account.email}`;
    renderCategoryChecks(document.getElementById('leagueSendCategories'), []);

    // These were bound with { once: true }, which removed the listener
    // after a single use - so a failed send (or a second invite) left a
    // dead button until the page was reloaded. Bind once per page load
    // via a guard flag instead, and keep the listener alive.
    if (!loadAll.__wired) {
      loadAll.__wired = true;

      document.getElementById('leagueCopyCodeBtn').addEventListener('click', () => {
        navigator.clipboard && navigator.clipboard.writeText(me.invite_code);
        window.DWToast.success(window.DWI18n.t('toast_saved'));
      });

      document.getElementById('leagueSendRequestBtn').addEventListener('click', async () => {
        const btn = document.getElementById('leagueSendRequestBtn');
        const code = document.getElementById('leagueInviteInput').value.trim();
        if (!code || btn.disabled) return;
        const categories = readChecked(document.getElementById('leagueSendCategories'));
        btn.disabled = true;
        try {
          await window.DWApi.leagueRedeemInvite(code, categories);
          window.DWToast.success(pick(L.request_sent));
          if (window.DWSound) window.DWSound.ding();
          document.getElementById('leagueInviteInput').value = '';
          await Promise.all([refreshPending(), refreshSent()]);
        } catch (e) {
          window.DWToast.error(e.message);
        } finally {
          btn.disabled = false;
        }
      });
    }

    await Promise.all([refreshPending(), refreshSent(), refreshConnections(), refreshLeaderboard()]);
    if (window.DWChrome) window.DWChrome.refreshNotifBadge();
  }

  /* Outgoing requests. The backend always tracked these, but nothing
     surfaced them - so after sending an invite you saw no trace of it
     anywhere and it looked like the request had vanished. */
  async function refreshSent() {
    const card = document.getElementById('leagueSentCard');
    const wrap = document.getElementById('leagueSentList');
    if (!card || !wrap) return;
    let data;
    try { data = await window.DWApi.leagueSentRequests(); } catch (e) { card.style.display = 'none'; return; }
    const requests = data.requests || [];
    card.style.display = requests.length ? '' : 'none';
    wrap.innerHTML = '';
    requests.forEach((r) => {
      const row = document.createElement('div');
      row.className = 'league-row';
      const name = r.other_display_name || pick(L.awaiting_name);
      row.innerHTML = `
        <div class="league-row-head"><strong>${name}</strong> <span class="league-pill-wait">${pick(L.awaiting_approval)}</span></div>
        <p class="muted dimension-hint">${pick(L.you_offered)}: ${r.shared_by_me.map(catLabel).join(', ') || pick(L.nothing)}</p>
      `;
      wrap.appendChild(row);
    });
  }

  async function refreshPending() {
    const wrap = document.getElementById('leaguePendingList');
    let data;
    try { data = await window.DWApi.leaguePendingRequests(); } catch (e) { wrap.innerHTML = ''; return; }
    const requests = data.requests || [];
    document.getElementById('leaguePendingCard').style.display = requests.length ? '' : 'none';
    wrap.innerHTML = '';
    requests.forEach((r) => {
      const row = document.createElement('div');
      row.className = 'league-row';
      row.innerHTML = `
        <div class="league-row-head">
          <strong>${r.other_display_name}</strong>
          <span class="muted">${pick(L.wants_to_connect)}</span>
        </div>
        <p class="muted dimension-hint">${pick(L.they_share_if_approve)}: ${r.visible_to_me.map(catLabel).join(', ') || (pick(L.nothing))}</p>
        <p class="muted dimension-hint" data-i18n-inline>${pick(L.what_share_back)}</p>
        <div class="league-category-checks" id="pendingCats_${r.connection_id}"></div>
        <div class="league-row-actions">
          <button class="btn btn-primary btn-sm" data-approve="${r.connection_id}">${pick(L.approve)}</button>
          <button class="btn btn-ghost btn-sm" data-decline="${r.connection_id}">${pick(L.decline)}</button>
        </div>
      `;
      wrap.appendChild(row);
      renderCategoryChecks(row.querySelector(`#pendingCats_${r.connection_id}`), []);
      row.querySelector(`[data-approve="${r.connection_id}"]`).addEventListener('click', async () => {
        const categories = readChecked(row.querySelector(`#pendingCats_${r.connection_id}`));
        try {
          await window.DWApi.leagueRespondRequest(r.connection_id, true, categories);
          window.DWToast.success(pick(L.connected));
          if (window.DWMascot) window.DWMascot.react('good');
          if (window.DWSound) window.DWSound.ding();
          await Promise.all([refreshPending(), refreshConnections(), refreshLeaderboard()]);
          if (window.DWChrome) window.DWChrome.refreshNotifBadge();
        } catch (e) { window.DWToast.error(e.message); }
      });
      row.querySelector(`[data-decline="${r.connection_id}"]`).addEventListener('click', async () => {
        try {
          await window.DWApi.leagueRespondRequest(r.connection_id, false, []);
          await refreshPending();
          if (window.DWChrome) window.DWChrome.refreshNotifBadge();
        } catch (e) { window.DWToast.error(e.message); }
      });
    });
  }

  async function refreshConnections() {
    const wrap = document.getElementById('leagueConnectionsList');
    let list;
    try { list = await window.DWApi.leagueConnections(); } catch (e) { wrap.innerHTML = ''; return; }
    wrap.innerHTML = list.length ? '' : `<p class="muted">${pick(L.no_friends)}</p>`;
    list.forEach((c) => {
      const row = document.createElement('div');
      row.className = 'league-row';
      row.innerHTML = `
        <div class="league-row-head"><strong>${c.other_display_name}</strong></div>
        <p class="muted dimension-hint">${pick(L.what_you_see)}: ${c.visible_to_me.map(catLabel).join(', ') || (pick(L.nothing))}</p>
        <p class="muted dimension-hint">${pick(L.what_youre_sharing)}:</p>
        <div class="league-category-checks" id="sharingCats_${c.connection_id}"></div>
        <div class="league-row-actions">
          <button class="btn btn-ghost btn-sm" data-save="${c.connection_id}">${pick(L.save_sharing)}</button>
          <button class="btn btn-danger btn-sm" data-revoke="${c.connection_id}">${pick(L.revoke)}</button>
        </div>
      `;
      wrap.appendChild(row);
      renderCategoryChecks(row.querySelector(`#sharingCats_${c.connection_id}`), c.shared_by_me);
      row.querySelector(`[data-save="${c.connection_id}"]`).addEventListener('click', async () => {
        const categories = readChecked(row.querySelector(`#sharingCats_${c.connection_id}`));
        try {
          await window.DWApi.leagueSharingUpdate(c.connection_id, categories);
          window.DWToast.success(window.DWI18n.t('toast_saved'));
          await refreshLeaderboard();
        } catch (e) { window.DWToast.error(e.message); }
      });
      row.querySelector(`[data-revoke="${c.connection_id}"]`).addEventListener('click', async () => {
        try {
          await window.DWApi.leagueRevoke(c.connection_id);
          await Promise.all([refreshConnections(), refreshLeaderboard()]);
        } catch (e) { window.DWToast.error(e.message); }
      });
    });
  }

  async function refreshLeaderboard() {
    const wrap = document.getElementById('leagueLeaderboardList');
    let data;
    try { data = await window.DWApi.leagueLeaderboard(); } catch (e) { wrap.innerHTML = ''; return; }
    document.getElementById('leagueComparisonNote').textContent = data.comparison_note || '';
    wrap.innerHTML = '';

    const self = data.self_entry;
    const trend = self.score != null && self.score_7d_ago != null ? self.score - self.score_7d_ago : null;

    /* A standings table, above the per-friend cards.
       The page listed everybody at their own score with no ordering, so
       "where do I stand" - the one question a friends league is for -
       took reading every row and doing the comparison yourself. Ranked
       here, with the user's own row marked, and ONLY over the people who
       have actually shared a score: ranking somebody who has shared
       nothing would be inventing a position for them. */
    const ranked = [
      { name: pick(L.you), score: self.score, isSelf: true },
      ...(data.friends || [])
        .filter((f) => typeof f.score === 'number')
        .map((f) => ({ name: f.display_name, score: f.score, isSelf: false })),
    ].filter((r) => typeof r.score === 'number')
     .sort((a, b) => b.score - a.score);

    if (ranked.length >= 2) {
      const table = document.createElement('div');
      table.className = 'league-standings';
      // Equal scores share a rank - the competition-ranking convention,
      // and the honest one when two people genuinely tied.
      let lastScore = null;
      let lastRank = 0;
      ranked.forEach((entry, index) => {
        const rank = (entry.score === lastScore) ? lastRank : index + 1;
        lastScore = entry.score;
        lastRank = rank;
        const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';

        /* Built as nodes, not as an innerHTML string. A friend's display
           name is text THEY chose, and interpolating it into markup is
           how a name becomes a script tag on somebody else's page.
           textContent cannot do that, and needs no escaping helper. */
        const line = document.createElement('div');
        line.className = 'league-standing' + (entry.isSelf ? ' is-self' : '');

        const rankEl = document.createElement('span');
        rankEl.className = 'league-standing-rank';
        rankEl.textContent = medal || String(rank);

        const nameEl = document.createElement('span');
        nameEl.className = 'league-standing-name';
        nameEl.textContent = entry.name || pick(L.awaiting_name);

        const scoreEl = document.createElement('span');
        scoreEl.className = 'league-standing-score mono';
        scoreEl.textContent = String(Math.round(entry.score));

        line.appendChild(rankEl);
        line.appendChild(nameEl);
        line.appendChild(scoreEl);
        table.appendChild(line);
      });
      wrap.appendChild(table);
    }

    const selfRow = document.createElement('div');
    selfRow.className = 'league-row league-row--self';
    selfRow.innerHTML = `
      <div class="league-row-head"><strong>${pick(L.you)}</strong>${self.persona ? ` · ${self.persona}` : ''}</div>
      <p class="mono">${self.score != null ? Math.round(self.score) : '—'}/100${trend != null ? ` (${trend >= 0 ? '+' : ''}${trend.toFixed(1)} ${pick(L.vs_7_days)})` : ''}</p>
    `;
    wrap.appendChild(selfRow);

    (data.friends || []).forEach((f) => {
      const row = document.createElement('div');
      row.className = 'league-row';
      const bits = [];
      if (f.persona != null) bits.push(f.persona);
      if (f.score != null) bits.push(`${Math.round(f.score)}/100`);
      if (f.rank != null) bits.push(`#${f.rank}`);
      if (f.plan_focus != null) bits.push(f.plan_focus.replace(/_/g, ' '));
      row.innerHTML = `<div class="league-row-head"><strong>${f.display_name}</strong></div><p class="muted">${bits.length ? bits.join(' · ') : (pick(L.hasnt_shared))}</p>`;
      /* D-1-b: click a friend -> their info -> a private chat button.
         Opening is a server call that re-checks the connection, so this
         button is a shortcut, never the permission. */
      if (f.user_id) {
        const chatBtn = document.createElement('button');
        chatBtn.type = 'button';
        chatBtn.className = 'btn btn-ghost btn-sm league-chat-btn';
        chatBtn.textContent = '💬 ' + (window.DWI18n.t('chat_open') || 'Chat');
        chatBtn.addEventListener('click', async () => {
          try {
            const conversation = await window.DWApi.chatOpenDirect(f.user_id);
            if (window.DWLeagueChatHandle) window.DWLeagueChatHandle.open(conversation.conversation_id);
            document.querySelector('.chat-card')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
          } catch (e) {
            window.DWToast.error(e.message);
          }
        });
        row.appendChild(chatBtn);
      }
      wrap.appendChild(row);
    });
  }

  /* ---- D-1 chat ----
     The client needs its own user id only to tell "mine" from "theirs"
     when rendering; every authorization decision is the server's. */
  if (window.DWLeagueChat) {
    window.DWChatState.userId = account.user_id;
    const chat = window.DWLeagueChatHandle = window.DWLeagueChat.init({
      listId: 'chatConversationList',
      threadId: 'chatThread',
      composerId: 'chatComposer',
      inputId: 'chatInput',
      sendId: 'chatSendBtn',
      titleId: 'chatThreadTitle',
      leaveId: 'chatLeaveBtn',
    });

    const newGroupBtn = document.getElementById('chatNewGroupBtn');
    if (newGroupBtn) {
      newGroupBtn.addEventListener('click', async () => {
        const title = window.prompt(window.DWI18n.t('chat_new_group') || 'Group name', '');
        if (!title) return;
        try {
          // Everyone the user is actually connected to. The server
          // filters this again - a client-side list is a convenience,
          // never the authorization.
          const connections = await window.DWApi.leagueConnections();
          const ids = (connections.connections || [])
            .map((c) => c.other_user_id).filter(Boolean);
          if (!ids.length) {
            window.DWToast.info(window.DWI18n.t('league_no_friends') || '—');
            return;
          }
          await window.DWApi.chatCreateGroup(title, ids);
          if (chat) chat.refresh();
        } catch (e) {
          window.DWToast.error(e.message);
        }
      });
    }
  }

  window.DWMascot.react('neutral');
});
