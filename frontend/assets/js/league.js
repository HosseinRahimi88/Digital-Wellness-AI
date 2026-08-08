/* Friends League page controller. See services/league_service.py for
   the consent model this mirrors exactly: nothing is visible to a
   friend until both sides have explicitly agreed to it, category by
   category, and either side can change or revoke it at any time. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('league');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  const CATEGORIES = [
    { key: 'persona', en: 'Your persona title', fa: 'عنوان پرسونای تو' },
    { key: 'score', en: 'Your latest score', fa: 'آخرین امتیازت' },
    { key: 'rank', en: 'Your leaderboard rank', fa: 'رتبه‌ات در جدول' },
    { key: 'plan_focus', en: 'Your current top factor', fa: 'مهم‌ترین عامل فعلی‌ات' },
  ];
  const lang = () => (window.DWI18n && window.DWI18n.get()) || 'en';
  const catLabel = (key) => { const c = CATEGORIES.find((x) => x.key === key); return c ? (lang() === 'fa' ? c.fa : c.en) : key; };

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
      label.appendChild(document.createTextNode(' ' + (lang() === 'fa' ? c.fa : c.en)));
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
  };

  function applyStaticCopy() {
    const l = lang();
    document.getElementById('leagueRulesList').innerHTML = RULES[l === 'fa' ? 'fa' : 'en'].map((r) => `<li>${r}</li>`).join('');
  }

  let me;
  try { me = await window.DWApi.leagueMe(); } catch (e) { window.DWToast.error(e.message); return; }

  applyStaticCopy();
  document.addEventListener('dwai:langchange', applyStaticCopy);

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
    renderCategoryChecks(document.getElementById('leagueSendCategories'), []);

    document.getElementById('leagueCopyCodeBtn').addEventListener('click', () => {
      navigator.clipboard && navigator.clipboard.writeText(me.invite_code);
      window.DWToast.success(window.DWI18n.t('toast_saved'));
    }, { once: true });

    document.getElementById('leagueSendRequestBtn').addEventListener('click', async () => {
      const code = document.getElementById('leagueInviteInput').value.trim();
      if (!code) return;
      const categories = readChecked(document.getElementById('leagueSendCategories'));
      try {
        await window.DWApi.leagueRedeemInvite(code, categories);
        window.DWToast.success(lang() === 'fa' ? 'درخواست ارسال شد.' : 'Request sent.');
        document.getElementById('leagueInviteInput').value = '';
        await refreshPending();
      } catch (e) { window.DWToast.error(e.message); }
    }, { once: true });

    await Promise.all([refreshPending(), refreshConnections(), refreshLeaderboard()]);
    if (window.DWChrome) window.DWChrome.refreshNotifBadge();
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
          <span class="muted">${lang() === 'fa' ? 'می‌خواهد وصل شود' : 'wants to connect'}</span>
        </div>
        <p class="muted dimension-hint">${lang() === 'fa' ? 'آنها این‌ها را با تو به اشتراک می‌گذارند اگر تایید کنی' : 'They will share this with you if you approve'}: ${r.visible_to_me.map(catLabel).join(', ') || (lang() === 'fa' ? 'هیچ‌چیز' : 'nothing')}</p>
        <p class="muted dimension-hint" data-i18n-inline>${lang() === 'fa' ? 'تو در ازای آن چه چیزی به اشتراک می‌گذاری؟' : 'What will you share back?'}</p>
        <div class="league-category-checks" id="pendingCats_${r.connection_id}"></div>
        <div class="league-row-actions">
          <button class="btn btn-primary btn-sm" data-approve="${r.connection_id}">${lang() === 'fa' ? 'تایید' : 'Approve'}</button>
          <button class="btn btn-ghost btn-sm" data-decline="${r.connection_id}">${lang() === 'fa' ? 'رد کردن' : 'Decline'}</button>
        </div>
      `;
      wrap.appendChild(row);
      renderCategoryChecks(row.querySelector(`#pendingCats_${r.connection_id}`), []);
      row.querySelector(`[data-approve="${r.connection_id}"]`).addEventListener('click', async () => {
        const categories = readChecked(row.querySelector(`#pendingCats_${r.connection_id}`));
        try {
          await window.DWApi.leagueRespondRequest(r.connection_id, true, categories);
          window.DWToast.success(lang() === 'fa' ? 'وصل شدید.' : 'Connected.');
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
    wrap.innerHTML = list.length ? '' : `<p class="muted">${lang() === 'fa' ? 'هنوز هیچ دوستی متصل نشده.' : 'No friends connected yet.'}</p>`;
    list.forEach((c) => {
      const row = document.createElement('div');
      row.className = 'league-row';
      row.innerHTML = `
        <div class="league-row-head"><strong>${c.other_display_name}</strong></div>
        <p class="muted dimension-hint">${lang() === 'fa' ? 'آنچه می‌بینی' : 'What you can see'}: ${c.visible_to_me.map(catLabel).join(', ') || (lang() === 'fa' ? 'هیچ‌چیز' : 'nothing')}</p>
        <p class="muted dimension-hint">${lang() === 'fa' ? 'آنچه به اشتراک می‌گذاری' : "What you're sharing"}:</p>
        <div class="league-category-checks" id="sharingCats_${c.connection_id}"></div>
        <div class="league-row-actions">
          <button class="btn btn-ghost btn-sm" data-save="${c.connection_id}">${lang() === 'fa' ? 'ذخیره‌ی اشتراک‌گذاری' : 'Save sharing'}</button>
          <button class="btn btn-danger btn-sm" data-revoke="${c.connection_id}">${lang() === 'fa' ? 'قطع ارتباط' : 'Revoke'}</button>
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
    const selfRow = document.createElement('div');
    selfRow.className = 'league-row league-row--self';
    const trend = self.score != null && self.score_7d_ago != null ? self.score - self.score_7d_ago : null;
    selfRow.innerHTML = `
      <div class="league-row-head"><strong>${lang() === 'fa' ? 'خودت' : 'You'}</strong>${self.persona ? ` · ${self.persona}` : ''}</div>
      <p class="mono">${self.score != null ? Math.round(self.score) : '—'}/100${trend != null ? ` (${trend >= 0 ? '+' : ''}${trend.toFixed(1)} ${lang() === 'fa' ? 'نسبت به ۷ روز پیش' : 'vs 7 days ago'})` : ''}</p>
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
      row.innerHTML = `<div class="league-row-head"><strong>${f.display_name}</strong></div><p class="muted">${bits.length ? bits.join(' · ') : (lang() === 'fa' ? 'چیزی به اشتراک نگذاشته' : "hasn't shared anything visible")}</p>`;
      wrap.appendChild(row);
    });
  }

  window.DWMascot.react('neutral');
});
