/* Profile page controller: view/edit the account's onboarding
   preferences (goal, purpose, schedule) via PUT /auth/me/onboarding.
   Shares its option lists with the initial onboarding flow via
   onboarding-options.js so the two never drift apart. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('profile');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  const initials = (account.display_name || account.email || '?').trim().slice(0, 2).toUpperCase();
  document.getElementById('avatarCircle').textContent = initials;

  const { GOAL_OPTIONS, PURPOSE_OPTIONS, SCHEDULE_OPTIONS } = window.DWOnboardingOptions;
  const selected = { goal: account.primary_goal, purpose: account.main_use_purpose, schedule: account.schedule_type };

  function buildOptionList(container, options, stateKey) {
    container.innerHTML = '';
    Object.entries(options).forEach(([label, value]) => {
      const el = document.createElement('div');
      el.className = 'onboard-option' + (selected[stateKey] === value ? ' selected' : '');
      el.dataset.optionValue = value;
      // Translated for reading; `value` is still what gets saved.
      el.textContent = window.DWOnboardingOptions.labelFor(value, label);
      el.addEventListener('click', () => {
        Array.from(container.children).forEach((c) => c.classList.remove('selected'));
        el.classList.add('selected');
        selected[stateKey] = value;
      });
      container.appendChild(el);
    });
  }

  buildOptionList(document.getElementById('goalOptions'), GOAL_OPTIONS, 'goal');
  buildOptionList(document.getElementById('purposeOptions'), PURPOSE_OPTIONS, 'purpose');
  buildOptionList(document.getElementById('scheduleOptions'), SCHEDULE_OPTIONS, 'schedule');

  document.getElementById('saveProfileBtn').addEventListener('click', async () => {
    try {
      await window.DWApi.saveOnboarding({
        primary_goal: selected.goal || 'maintain_habits',
        main_use_purpose: selected.purpose || 'mixed',
        schedule_type: selected.schedule || 'standard_day',
        usual_sleep_time: account.usual_sleep_time || '23:00',
        usual_wake_time: account.usual_wake_time || '07:00',
        preferred_effort: account.preferred_effort || 'moderate',
        work_screen_required: account.work_screen_required || false,
      });
      window.DWToast.success(window.DWI18n.t('toast_saved'));
      window.DWMascot.react('saved');
    } catch (e) {
      window.DWToast.error(e.message);
    }
  });

  // ===================== AVATAR =====================
  // Resized in the browser BEFORE upload: the account record stores the
  // image inline, so sending a full-size camera photo would bloat the
  // store. 256px square is plenty for every place it's displayed.
  const AVATAR_PX = 256;

  function renderAvatar(dataUrl) {
    const circle = document.getElementById('avatarCircle');
    if (dataUrl) {
      circle.style.backgroundImage = `url("${dataUrl}")`;
      circle.classList.add('has-image');
      circle.textContent = '';
    } else {
      circle.style.backgroundImage = '';
      circle.classList.remove('has-image');
      circle.textContent = initials;
    }
  }
  renderAvatar(account.avatar_data_url);

  function downscaleToDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('Could not read that file.'));
      reader.onload = () => {
        const img = new Image();
        img.onerror = () => reject(new Error('That file is not a readable image.'));
        img.onload = () => {
          // Centre-crop to a square, then draw at AVATAR_PX.
          const side = Math.min(img.width, img.height);
          const sx = (img.width - side) / 2;
          const sy = (img.height - side) / 2;
          const canvasEl = document.createElement('canvas');
          canvasEl.width = canvasEl.height = AVATAR_PX;
          const ctx = canvasEl.getContext('2d');
          ctx.drawImage(img, sx, sy, side, side, 0, 0, AVATAR_PX, AVATAR_PX);
          resolve(canvasEl.toDataURL('image/jpeg', 0.85));
        };
        img.src = reader.result;
      };
      reader.readAsDataURL(file);
    });
  }

  const avatarInput = document.getElementById('avatarInput');
  document.getElementById('avatarEditBtn').addEventListener('click', () => avatarInput.click());
  avatarInput.addEventListener('change', async (e) => {
    const file = e.target.files && e.target.files[0];
    avatarInput.value = '';
    if (!file) return;
    try {
      const dataUrl = await downscaleToDataUrl(file);
      await window.DWApi.saveProfileExtras({ avatar_data_url: dataUrl });
      account.avatar_data_url = dataUrl;
      renderAvatar(dataUrl);
      window.DWToast.success(window.DWI18n.t('toast_saved'));
      window.DWMascot.react('saved');
    } catch (err) {
      window.DWToast.error(err.message);
    }
  });

  // ===================== TONE =====================
  const TONE_KEYS = ['gentle', 'direct', 'clinical'];
  let selectedTone = account.recommendation_tone || 'gentle';

  function renderTones() {
    const wrap = document.getElementById('toneOptions');
    wrap.innerHTML = '';
    TONE_KEYS.forEach((key) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip-option' + (selectedTone === key ? ' selected' : '');
      chip.textContent = window.DWI18n.t('tone_' + key);
      chip.addEventListener('click', async () => {
        selectedTone = key;
        renderTones();
        try {
          await window.DWApi.saveProfileExtras({ recommendation_tone: key });
          window.DWToast.success(window.DWI18n.t('toast_saved'));
        } catch (err) { window.DWToast.error(err.message); }
      });
      wrap.appendChild(chip);
    });
  }
  renderTones();
  document.addEventListener('dwai:langchange', renderTones);

  /* Badge preview.
   *
   * This used to render the persona endpoint's own badge list - an
   * older, separate set that ships English label/description strings
   * from the server, shown in a `title=` tooltip. Two things were wrong
   * with that in a four-language app: the text stayed English whatever
   * the user picked, and a tooltip is not an explanation a guide can
   * read aloud. It also meant the profile and the Hall of Fame were
   * showing two different badge sets under the same word.
   *
   * Now it reads the real 63-badge registry and renders the earned ones
   * through DWBadgeText, so the names translate, and each tile carries
   * data-badge-id - which is all guide-click.js needs to explain any of
   * them out loud. The Hall of Fame stays the full view; this is the
   * shelf-front. */
  const BADGE_PREVIEW_MAX = 12;
  let previewBadges = null;

  function renderBadgePreviewTiles() {
    const grid = document.getElementById('badgeGrid');
    if (!grid) return;
    const T = window.DWBadgeText;
    if (!previewBadges || !previewBadges.length || !T) {
      grid.innerHTML = `<p class="muted">${window.DWI18n.t('profile_badges_empty')}</p>`;
      return;
    }
    grid.innerHTML = previewBadges.map((b) => {
      const name = T.name(b.id);
      return `<button type="button" class="badge-tile is-earned${b.tier ? ' tier-' + b.tier : ''}"`
        + ` data-badge-id="${b.id}" data-badge-earned="1"`
        + ` data-badge-evaluable="${b.evaluable === false ? '0' : '1'}"`
        + ` data-badge-private="${b.private ? '1' : '0'}"`
        + ` data-badge-tier="${b.tier || ''}"`
        + ` aria-label="${name}. ${T.ui('earned')}">`
        + `<span class="badge-icon" aria-hidden="true">${b.icon || '🏅'}</span>`
        + `<span class="badge-label">${name}</span></button>`;
    }).join('');
  }

  async function renderBadgePreview() {
    try {
      const data = await window.DWApi.badges();
      const all = (data && data.badges) || [];
      // Earned only on this surface - the locked ones are the Hall of
      // Fame's job, and a profile card full of things you have not done
      // is the shaming pattern the brief rules out.
      previewBadges = all.filter((b) => b.earned).slice(0, BADGE_PREVIEW_MAX);
    } catch (e) {
      previewBadges = [];
    }
    renderBadgePreviewTiles();
  }
  // Names come from the registry, so a language change has to re-render
  // rather than wait for the next page load.
  document.addEventListener('dwai:langchange', renderBadgePreviewTiles);

  // ===================== PERSONA + BADGES =====================
  try {
    const identity = await window.DWApi.personaIdentity();
    const body = document.getElementById('personaBody');
    if (identity.primary) {
      body.innerHTML = `
        <div class="persona-primary">
          <span class="persona-icon">${identity.primary.icon}</span>
          <div>
            <div class="persona-title">${identity.primary.title}</div>
            <div class="persona-tagline">${identity.primary.tagline}</div>
            <div class="persona-reason muted">${identity.primary.reason}</div>
          </div>
        </div>`;
      const chipRow = document.getElementById('personaChipRow');
      chipRow.innerHTML = `<span class="persona-mini-chip">${identity.primary.icon} ${identity.primary.title}</span>` +
        identity.alternates.map((a) => `<span class="persona-mini-chip alt">${a.icon} ${a.title}</span>`).join('');
      if (identity.alternates.length) {
        const alts = document.createElement('p');
        alts.className = 'muted dimension-hint';
        alts.textContent = window.DWI18n.t('profile_persona_alts') + ' ' +
          identity.alternates.map((a) => a.title).join(' · ');
        body.appendChild(alts);
      }
    } else {
      body.innerHTML = `<p class="muted">${window.DWI18n.t('profile_persona_empty')}</p>`;
    }

    await renderBadgePreview();
  } catch (e) {
    document.getElementById('personaCard').classList.add('hidden');
    document.getElementById('badgeCard').classList.add('hidden');
  }

  // ===================== PROGRESS =====================
  try {
    const progress = await window.DWApi.progressSummary();
    const stats = document.getElementById('progressStats');
    stats.innerHTML = `
      <div class="progress-stat"><span class="val">${progress.current_streak}</span><span class="lbl">${window.DWI18n.t('progress_streak')}</span></div>
      <div class="progress-stat"><span class="val">${progress.longest_streak}</span><span class="lbl">${window.DWI18n.t('progress_longest')}</span></div>
      <div class="progress-stat"><span class="val">${progress.entry_count}</span><span class="lbl">${window.DWI18n.t('progress_entries')}</span></div>`;

    const winsWrap = document.getElementById('smallWinsWrap');
    if (progress.small_wins.length) {
      winsWrap.innerHTML = `<h4 class="progress-sub">${window.DWI18n.t('progress_wins')}</h4>` +
        progress.small_wins.map((w) => {
          const dir = w.higher_is_better ? '▲' : '▼';
          return `<div class="small-win"><span class="win-dir">${dir}</span> ${w.label}: ${w.previous_value} → <strong>${w.current_value}</strong></div>`;
        }).join('');
    }

    const baWrap = document.getElementById('beforeAfterWrap');
    const ba = progress.before_after;
    if (ba && ba.available) {
      const arrow = ba.delta >= 0 ? '▲ +' : '▼ ';
      const note = ba.is_meaningful ? '' : ` <span class="muted">(${window.DWI18n.t('progress_within_noise')})</span>`;
      baWrap.innerHTML = `<h4 class="progress-sub">${window.DWI18n.t('progress_before_after')}</h4>
        <p class="muted">${ba.before_avg_score} → <strong>${ba.after_avg_score}</strong> &nbsp; ${arrow}${Math.abs(ba.delta).toFixed(1)}${note}</p>`;
    }
  } catch (e) {
    document.getElementById('progressCard').classList.add('hidden');
  }

  // ===================== PRIVACY =====================
  /* C-5-7. Same authenticated-fetch dance as the JSON export: the
     endpoint needs an Authorization header, which a plain <a href>
     cannot carry. The language is chosen server-side from the query
     parameter DWApi adds. */
  const csvBtn = document.getElementById('exportCsvBtn');
  if (csvBtn) {
    csvBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        const blob = await window.DWApi.exportMyDataCsv();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'digital_wellness_history_' + (window.DWI18n.get() || 'en') + '.csv';
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        if (window.DWSound && window.DWSound.success) window.DWSound.success();
      } catch (err) {
        if (window.DWSound && window.DWSound.error) window.DWSound.error();
        window.DWToast.error(err.message);
      }
    });
  }

  document.getElementById('exportDataBtn').addEventListener('click', async (e) => {
    e.preventDefault();
    try {
      const blob = await window.DWApi.exportMyData();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'digital_wellness_my_data.json';
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      window.DWToast.error(err.message);
    }
  });
  document.getElementById('deleteDataBtn').addEventListener('click', async () => {
    // Destructive and irreversible - require an explicit typed
    // confirmation rather than a single click.
    const expected = (account.email || '').trim();
    const typed = window.prompt(window.DWI18n.t('profile_delete_confirm').replace('{email}', expected));
    if (typed === null) return;
    if (typed.trim().toLowerCase() !== expected.toLowerCase()) {
      window.DWToast.error(window.DWI18n.t('profile_delete_mismatch'));
      return;
    }
    try {
      await window.DWApi.deleteMyData();
      window.DWApi.clearToken();
      window.DWToast.success(window.DWI18n.t('profile_delete_done'));
      setTimeout(() => { location.href = 'index.html'; }, 1200);
    } catch (err) {
      window.DWToast.error(err.message);
    }
  });
});
