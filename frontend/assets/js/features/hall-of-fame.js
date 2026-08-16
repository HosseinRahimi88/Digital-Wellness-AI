/*
  Hall of Fame (D-2) and the private awareness panel (C-3).

  Two renderers, one file, because they share a tile and must never
  share a surface:

    renderHall(mount)      achievement badges only, on three rarity
                           shelves. Locked badges stay visible but
                           blurred - discovery is the motivation, and a
                           gallery of only what you already have is not
                           a gallery.
    renderAwareness(mount) the private indicators. Fetched from the
                           user's own /badges endpoint, rendered only on
                           their own profile, and every one carries its
                           next step. Nothing here is ever passed to a
                           league view; the server does not even send
                           these on the public endpoint.

  Every tile is clickable and asks the digital guide to say what the
  badge is, how it is earned, where the user stands, and - for an
  awareness indicator - what the next step is. That text is composed by
  DWBadgeText.speech() from the same registry the tile renders from, so
  a badge added tomorrow is spoken correctly with no extra work (B-5).
*/
(function () {
  const TIER_ORDER = ['legendary', 'rare', 'common'];

  const T = {
    hallTitle: { en: 'Hall of fame', fa: 'گالری افتخار', ar: 'قاعة المجد', zh: '荣誉墙' },
    hallLead: {
      en: 'Everything here was computed from your own check-ins. Locked ones are not failures — they are what is still out there.',
      fa: 'هرچه اینجاست از بررسی‌های خودت حساب شده. قفل‌بودن‌ها شکست نیستند — چیزهایی‌اند که هنوز مانده‌اند.',
      ar: 'كل ما هنا محسوب من تسجيلاتك أنت. المقفلة ليست إخفاقات — بل ما لا يزال في الأفق.',
      zh: '这里的一切都是根据你自己的记录算出来的。锁住的不是失败——而是还在前面的东西。',
    },
    awarenessTitle: { en: 'Worth a look', fa: 'ارزش یک نگاه', ar: 'يستحق نظرة', zh: '值得看一看' },
    awarenessLead: {
      en: 'Private to you. These describe a pattern in your recent days and each one comes with a step — none of them is a verdict, and none is ever visible to a friend.',
      fa: 'فقط برای خودت. این‌ها الگویی در روزهای اخیرت را توصیف می‌کنند و هرکدام یک قدم همراه دارند — هیچ‌کدام حکم نیستند، و هیچ‌کدام هرگز برای دوستی دیده نمی‌شوند.',
      ar: 'خاصة بك وحدك. تصف نمطاً في أيامك الأخيرة ويأتي كل منها بخطوة — لا شيء منها حكم، ولا يراه صديق أبداً.',
      zh: '仅你可见。它们描述你最近这些天里的一个模式，并且每一个都带着一个步骤——没有一条是判决，也永远不会被好友看到。',
    },
    empty: {
      en: 'Nothing here yet — a few more check-ins and this fills in.',
      fa: 'هنوز چیزی اینجا نیست — چند بررسی دیگر و اینجا پر می‌شود.',
      ar: 'لا شيء هنا بعد — بضعة تسجيلات أخرى وسيمتلئ هذا.',
      zh: '这里还没有内容——再记录几次就会填满。',
    },
    awarenessEmpty: {
      en: 'Nothing is flagged in your recent days.',
      fa: 'در روزهای اخیرت چیزی علامت نخورده.',
      ar: 'لا شيء مُعلَّم في أيامك الأخيرة.',
      zh: '你最近这些天里没有任何标记。',
    },
    counted: { en: 'earned', fa: 'به دست آمده', ar: 'محقَّق', zh: '已获得' },
  };

  const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);
  const text = () => window.DWBadgeText;

  function num(v) {
    const span = document.createElement('span');
    span.dir = 'ltr';
    span.style.unicodeBidi = 'isolate';
    span.textContent = String(v);
    return span.outerHTML;
  }

  /* One tile. `index` only drives the staggered entrance, and the delay
     is dropped entirely under reduced motion - the brief asks for the
     information to be simplified there, not removed, so the tile still
     renders, just without the cascade. */
  function tile(badge, index) {
    const t = text();
    const el = document.createElement('button');
    el.type = 'button';
    el.className = 'badge-tile-lg'
      + (badge.earned ? ' is-earned' : ' is-locked')
      + (badge.evaluable ? '' : ' is-unknown')
      + (badge.tier ? ' tier-' + badge.tier : '');
    el.dataset.badgeId = badge.id;

    const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduced) el.style.animationDelay = Math.min(index * 45, 900) + 'ms';

    const name = t.name(badge.id);
    const showProgress = !badge.earned && badge.evaluable
      && badge.progress != null && badge.target;

    el.innerHTML = `
      <span class="badge-glyph" aria-hidden="true">${badge.icon || '🏅'}</span>
      <span class="badge-name">${name}</span>
      ${badge.tier ? `<span class="badge-tier">${t.tierLabel(badge.tier)}</span>` : ''}
      <span class="badge-desc">${t.description(badge)}</span>
      ${showProgress ? `<span class="badge-progress">${num(Math.round(badge.progress))} / ${num(Math.round(badge.target))}</span>` : ''}
      ${badge.private && t.nextStep(badge)
        ? `<span class="badge-next"><strong>${t.ui('nextStep')}:</strong> ${t.nextStep(badge)}</span>` : ''}
      ${badge.private ? `<span class="badge-private">${t.ui('privateNote')}</span>` : ''}`;

    // The accessible name has to carry the state too - visually the
    // blur says "locked", and a screen reader gets nothing from a blur.
    el.setAttribute('aria-label', name + '. '
      + (!badge.evaluable ? t.ui('notEnoughData') : badge.earned ? t.ui('earned') : t.ui('locked')));

    // The record itself, so the universal click layer can explain this
    // tile with the same sentence even when it is moved to another page.
    // __dwGuideBound tells that layer this tile answers for itself, which
    // is what stops the badge being spoken twice per click.
    el.__dwBadge = badge;
    el.__dwGuideBound = true;

    el.addEventListener('click', () => {
      if (window.DWSound && window.DWSound.click) window.DWSound.click();
      if (window.DWGuide && window.DWGuide.speak) {
        window.DWGuide.speak(t.speech(badge), {
          face: badge.earned ? 'great' : 'thinking',
          topic: 'badge_' + badge.id,
          force: true,
        });
      }
    });
    return el;
  }

  function shelf(tierKey, badges, startIndex) {
    const t = text();
    const wrap = document.createElement('section');
    wrap.className = 'badge-shelf tier-' + tierKey;
    const earned = badges.filter((b) => b.earned).length;
    wrap.innerHTML = `
      <h4 class="badge-shelf-head">
        <span>${t.tierLabel(tierKey)}</span>
        <span class="muted">${num(earned)} / ${num(badges.length)} ${pick(T.counted)}</span>
      </h4>`;
    const grid = document.createElement('div');
    grid.className = 'badge-grid-lg';
    badges.forEach((b, i) => grid.appendChild(tile(b, startIndex + i)));
    wrap.appendChild(grid);
    return wrap;
  }

  function renderHall(data, mount) {
    if (!mount) return 0;
    mount.innerHTML = '';
    const achievements = (data.badges || []).filter((b) => b.category === 'achievement');
    if (!achievements.length) {
      mount.innerHTML = `<p class="muted">${pick(T.empty)}</p>`;
      return 0;
    }
    let index = 0;
    TIER_ORDER.forEach((tier) => {
      const group = achievements.filter((b) => b.tier === tier);
      if (!group.length) return;
      // Earned first inside a shelf: the wall should open with what the
      // user actually has, not with a row of blurred tiles.
      group.sort((a, b) => Number(b.earned) - Number(a.earned));
      mount.appendChild(shelf(tier, group, index));
      index += group.length;
    });
    return achievements.length;
  }

  function renderAwareness(data, mount) {
    if (!mount) return 0;
    mount.innerHTML = '';
    // Only indicators that actually fired. Listing every pattern a user
    // does *not* have would turn a private note into a checklist of
    // ways to be judged.
    const active = (data.badges || []).filter(
      (b) => b.category === 'awareness' && b.earned
    );
    if (!active.length) {
      mount.innerHTML = `<p class="muted">${pick(T.awarenessEmpty)}</p>`;
      return 0;
    }
    const grid = document.createElement('div');
    grid.className = 'badge-grid-lg is-awareness';
    active.forEach((b, i) => grid.appendChild(tile(b, i)));
    mount.appendChild(grid);
    return active.length;
  }

  async function load(opts) {
    opts = opts || {};
    if (!window.DWApi || !window.DWApi.badges) return null;
    let data;
    try {
      data = await window.DWApi.badges();
    } catch (e) {
      // A badge wall is supplementary; it must never take a page down.
      [opts.hall, opts.awareness].forEach((el) => {
        const section = el && el.closest('.badge-section');
        if (section) section.classList.add('hidden');
      });
      return null;
    }
    if (opts.hall) renderHall(data, opts.hall);
    if (opts.awareness) {
      const shown = renderAwareness(data, opts.awareness);
      const section = opts.awareness.closest('.badge-section');
      // G4: an empty private panel is not worth a heading.
      if (section && !shown && opts.hideAwarenessWhenEmpty) section.classList.add('hidden');
    }
    if (opts.count) {
      opts.count.innerHTML = num(data.earned_count || 0) + ' / ' + num(data.total_count || 0);
    }
    return data;
  }

  window.DWHallOfFame = { load, renderHall, renderAwareness, T };
})();
