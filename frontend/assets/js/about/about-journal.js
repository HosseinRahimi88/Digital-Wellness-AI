/*
  DWAboutJournal — the book.

  A bound book that opens, and one page per day inside it. The reader
  writes the day in their own words and it is saved to their account
  through /api/v1/journal (services/identity/journal_service.py), not to this
  browser: a diary that dies with the tab is not a diary.

  Why a book and not a text box
  ------------------------------
  Asked for directly, and it earns its keep: everything else in this
  app is the model's account of your day in numbers. This is yours in
  words, and it should not look like another form. The opening motion
  and the page turn are the whole point of the thing, so they are real
  3D transforms rather than a fade - but every one of them is skipped
  under reduced motion, and the page's content is never withheld
  waiting for one to finish.

  What it will not do
  --------------------
  * It never writes a day that has not happened. The server refuses it
    too (normalise_day), and the book simply does not offer it.
  * It never invents a page. An unwritten day is blank and says so.
  * It does not touch the wellness score. Nothing written here is fed
    to any model - it is text the user owns, and the panel says so.

  Demo Mode
  ----------
  A demo account arrives with its book already written in all four
  languages except for TODAY, which is deliberately blank so a reviewer
  can write a page and watch it save. Demo pages carry `text_i18n` and
  are rendered in whichever language the page is in; a page a real
  person typed is shown exactly as they typed it.
*/
(function () {
  const LANGS = ['en', 'fa', 'ar', 'zh'];
  const LOCALE = { en: 'en-US', fa: 'fa-IR', ar: 'ar-SA', zh: 'zh-CN' };

  function lang() {
    const l = window.DWI18n && window.DWI18n.get ? window.DWI18n.get() : 'en';
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }

  function pick(bundle) {
    if (!bundle) return '';
    if (typeof bundle === 'string') return bundle;
    return bundle[lang()] || bundle.en || '';
  }

  const T = {
    eyebrow: {
      en: 'Your own words', fa: 'به قلم خودت',
      ar: 'بكلماتك أنت', zh: '你自己的话',
    },
    title: {
      en: 'The book of days', fa: 'کتابِ روزها',
      ar: 'كتاب الأيام', zh: '日子之书',
    },
    lede: {
      en: 'Everything else here is the model’s account of your day, in numbers. This is yours, in words — one page per day, saved to your account and never fed to any model.',
      fa: 'هرچیز دیگری در این اپ، روایتِ مدل از روز توست، با عدد. این یکی روایتِ خودت است، با کلمه — روزی یک صفحه، ذخیره‌شده روی حساب خودت و هرگز خوراک هیچ مدلی نمی‌شود.',
      ar: 'كل شيء آخر هنا هو رواية النموذج ليومك بالأرقام. أما هذا فروايتك أنت بالكلمات — صفحة لكل يوم، تُحفظ في حسابك ولا تُغذّى لأي نموذج أبدًا.',
      zh: '这里其他一切，都是模型用数字讲述你的一天。这一处是你自己用文字讲述——每天一页，保存在你的账号里，绝不喂给任何模型。',
    },
    open: { en: 'Open the book', fa: 'کتاب را باز کن', ar: 'افتح الكتاب', zh: '打开这本书' },
    close: { en: 'Close the book', fa: 'بستن کتاب', ar: 'أغلق الكتاب', zh: '合上这本书' },
    cover_title: { en: 'Book of Days', fa: 'کتابِ روزها', ar: 'كتاب الأيام', zh: '日子之书' },
    cover_sub: {
      en: 'one page for every day you lived',
      fa: 'یک صفحه برای هر روزی که زیسته‌ای',
      ar: 'صفحة لكل يوم عشته',
      zh: '你活过的每一天，都有一页',
    },
    index_title: { en: 'Pages', fa: 'صفحه‌ها', ar: 'الصفحات', zh: '页面' },
    // Deliberately not "on the right": on a phone the spread is
    // stacked and today's page is above this one, so a sentence that
    // names a side is wrong half the time - and in Persian and Arabic
    // it is wrong on the other half too.
    index_empty: {
      en: 'Nothing is written yet. Today’s page is open and waiting.',
      fa: 'هنوز چیزی نوشته نشده. صفحه‌ی امروز باز است و منتظر.',
      ar: 'لم يُكتب شيء بعد. صفحة اليوم مفتوحة وتنتظر.',
      zh: '还什么都没写。今天那一页已经翻开，等着你。',
    },
    today: { en: 'Today', fa: 'امروز', ar: 'اليوم', zh: '今天' },
    blank: { en: 'blank', fa: 'خالی', ar: 'فارغة', zh: '空白' },
    placeholder: {
      en: 'How did today actually go?',
      fa: 'امروز واقعاً چطور گذشت؟',
      ar: 'كيف مرّ يومك فعلًا؟',
      zh: '今天到底过得怎么样？',
    },
    save: { en: 'Write it in', fa: 'ثبتش کن', ar: 'اكتبها', zh: '写进去' },
    saving: { en: 'Writing…', fa: 'در حال ثبت…', ar: 'يُكتب…', zh: '正在写入…' },
    edit: { en: 'Rewrite this page', fa: 'بازنویسی این صفحه', ar: 'أعد كتابة الصفحة', zh: '重写这一页' },
    saved: { en: 'Written', fa: 'ثبت شد', ar: 'تمت الكتابة', zh: '已写入' },
    saved_toast: {
      en: 'Page written.', fa: 'صفحه ثبت شد.',
      ar: 'كُتبت الصفحة.', zh: '这一页已写好。',
    },
    save_failed: {
      en: 'The page could not be saved.',
      fa: 'صفحه ذخیره نشد.',
      ar: 'تعذّر حفظ الصفحة.',
      zh: '这一页没能保存。',
    },
    load_failed: {
      en: 'The book could not be opened — the API did not answer.',
      fa: 'کتاب باز نشد — سرور پاسخ نداد.',
      ar: 'تعذّر فتح الكتاب — لم تستجب الواجهة البرمجية.',
      zh: '书没能打开——接口没有响应。',
    },
    empty_refused: {
      en: 'An empty page is not saved.',
      fa: 'صفحه‌ی خالی ذخیره نمی‌شود.',
      ar: 'الصفحة الفارغة لا تُحفظ.',
      zh: '空白页不会被保存。',
    },
    mood: { en: 'How the day felt', fa: 'حالِ آن روز', ar: 'كيف شعرت باليوم', zh: '这一天的感觉' },
    written_on: { en: 'written', fa: 'نوشته‌شده در', ar: 'كُتبت في', zh: '写于' },
    prev: { en: 'Earlier page', fa: 'صفحه‌ی پیش‌تر', ar: 'صفحة أسبق', zh: '更早的一页' },
    next: { en: 'Later page', fa: 'صفحه‌ی بعدتر', ar: 'صفحة أحدث', zh: '更近的一页' },
    counter: { en: 'left', fa: 'باقی‌مانده', ar: 'متبقٍ', zh: '剩余' },
    pdf: { en: 'Download as PDF', fa: 'دانلود PDF', ar: 'تنزيل PDF', zh: '下载 PDF' },
    pdf_working: { en: 'Preparing…', fa: 'در حال آماده‌سازی…', ar: 'قيد التحضير…', zh: '正在准备…' },
    pdf_failed: {
      en: 'The PDF could not be built.',
      fa: 'فایل PDF ساخته نشد.',
      ar: 'تعذّر إنشاء ملف PDF.',
      zh: 'PDF 没能生成。',
    },
    pdf_empty: {
      en: 'There is nothing in the book to export yet.',
      fa: 'هنوز چیزی در کتاب نیست که خروجی بگیری.',
      ar: 'لا يوجد في الكتاب ما يمكن تصديره بعد.',
      zh: '书里还没有可以导出的内容。',
    },
    demo_note: {
      en: 'This is a demo account: the earlier pages came with it. Today’s page is yours.',
      fa: 'این یک حساب نمایشی است: صفحه‌های قبلی همراهش آمده‌اند. صفحه‌ی امروز مال توست.',
      ar: 'هذا حساب تجريبي: الصفحات السابقة جاءت معه. صفحة اليوم لك أنت.',
      zh: '这是一个演示账号：之前那些页是随它一起来的。今天这一页是你的。',
    },
  };

  const MOODS = [
    { id: 'rough', glyph: '✕', label: { en: 'Rough', fa: 'سخت', ar: 'قاسٍ', zh: '难熬' } },
    { id: 'low', glyph: '−', label: { en: 'Low', fa: 'پایین', ar: 'منخفض', zh: '低落' } },
    { id: 'steady', glyph: '=', label: { en: 'Steady', fa: 'یکنواخت', ar: 'ثابت', zh: '平稳' } },
    { id: 'good', glyph: '+', label: { en: 'Good', fa: 'خوب', ar: 'جيد', zh: '不错' } },
    { id: 'great', glyph: '★', label: { en: 'Great', fa: 'عالی', ar: 'ممتاز', zh: '很好' } },
  ];

  const MAX_LEN = 2000;

  function esc(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function todayIso() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    // Built from the LOCAL date, not toISOString(): the server's rule is
    // "not a day that has not happened", and a reader east of UTC would
    // otherwise be told their own today is the future.
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function longDate(iso) {
    try {
      return new Date(`${iso}T00:00:00`).toLocaleDateString(LOCALE[lang()] || 'en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
      });
    } catch (e) { return iso; }
  }

  function shortDate(iso) {
    try {
      return new Date(`${iso}T00:00:00`).toLocaleDateString(LOCALE[lang()] || 'en-US', {
        month: 'short', day: 'numeric',
      });
    } catch (e) { return iso; }
  }

  function stamp(utc) {
    if (!utc) return '';
    try {
      return new Date(utc).toLocaleDateString(LOCALE[lang()] || 'en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
      });
    } catch (e) { return ''; }
  }

  /* The text to show for a page. A demo page carries all four
     languages; a page a person typed carries exactly one, and is shown
     as typed rather than being machine-translated into whatever the UI
     happens to be set to. */
  function textOf(entry) {
    if (!entry) return '';
    const bundle = entry.text_i18n || {};
    return bundle[lang()] || entry.text || '';
  }

  /* The book's own sounds. Every one of them is synthesised in
     assets/js/sound-engine.js - no audio files, so nothing here adds a
     byte to the download - and every one is silent when the app's sound
     switch is off, which is the rule that already governs every other
     cue in the app. */
  function cue(name) {
    try {
      if (window.DWSound && window.DWSound[name]) window.DWSound[name]();
    } catch (e) { /* sound is never worth an error */ }
  }

  function reduced() {
    return !!(window.DWMotion && window.DWMotion.prefersReduced());
  }

  function init(rootId) {
    const root = document.getElementById(rootId);
    if (!root) return;

    const state = {
      opened: false,
      loading: true,
      failed: false,
      entries: [],       // newest first, from the API
      days: [],          // the pages the book has, newest first
      index: 0,
      editing: false,
      draftMood: null,
      busy: false,
      // Text typed but not yet saved, per day. Turning the page used to
      // throw it away without a word, which is the one thing a book
      // must never do to something you wrote in it.
      drafts: {},
    };

    function entryFor(day) {
      return state.entries.find((e) => e.date === day) || null;
    }

    /* Keep whatever is in the textarea before the page it belongs to
       goes away - on a turn, on a language change, on a re-render. */
    function keepDraft() {
      const write = root.querySelector('#jrWrite');
      if (!write) return;
      const day = state.days[state.index];
      if (!day) return;
      const typed = write.value;
      const saved = textOf(entryFor(day));
      if (typed.trim() && typed !== saved) state.drafts[day] = typed;
      else delete state.drafts[day];
    }

    function rebuildDays() {
      const today = todayIso();
      const seen = new Set([today]);
      const days = [today];
      state.entries.forEach((e) => {
        if (seen.has(e.date)) return;
        seen.add(e.date);
        days.push(e.date);
      });
      // Newest first, so page one of the book is the day you are living.
      days.sort((a, b) => (a < b ? 1 : -1));
      state.days = days;
      if (state.index >= days.length) state.index = days.length - 1;
    }

    async function load() {
      state.loading = true;
      render();
      try {
        const data = await window.DWApi.journalList(200);
        state.entries = (data && data.entries) || [];
        state.failed = false;
      } catch (e) {
        state.entries = [];
        state.failed = true;
      }
      state.loading = false;
      rebuildDays();
      // Land on today, which is the page most people want to write.
      state.index = 0;
      state.editing = !entryFor(state.days[0]);
      state.draftMood = null;
      render();
    }

    /* ---- markup -------------------------------------------------- */

    /* Said out loud on a demo account, because a book that is already
       full is the one thing on this page a reviewer could mistake for
       something the app wrote about them. */
    function demoNoteHtml() {
      const inDemo = !!(window.DWDemo && window.DWDemo.isActive && window.DWDemo.isActive());
      return inDemo ? `<p class="jr-note jr-note--demo">${esc(pick(T.demo_note))}</p>` : '';
    }

    function indexHtml() {
      if (state.loading) {
        return `<p class="jr-note">${esc(pick(T.index_title))}…</p>`;
      }
      const written = state.days.filter((d) => entryFor(d));
      if (!written.length) {
        return `<p class="jr-note">${esc(pick(T.index_empty))}</p>`;
      }
      const rows = state.days.map((day, i) => {
        const entry = entryFor(day);
        const isToday = day === todayIso();
        const preview = entry
          ? textOf(entry).slice(0, 64)
          : pick(T.blank);
        return ''
          + `<li><button type="button" class="jr-index-row${i === state.index ? ' is-current' : ''}"`
          + ` data-goto="${i}">`
          + `<span class="jr-index-date">${esc(isToday ? pick(T.today) : shortDate(day))}</span>`
          + `<span class="jr-index-preview${entry ? '' : ' is-blank'}">${esc(preview)}</span>`
          + '</button></li>';
      }).join('');
      return `<ol class="jr-index-list">${rows}</ol>`;
    }

    function moodRowHtml(selected, interactive) {
      const seals = MOODS.map((m) => ''
        + `<button type="button" class="jr-seal${selected === m.id ? ' is-on' : ''}"`
        + ` data-mood="${m.id}"${interactive ? '' : ' disabled'}`
        + ` title="${esc(pick(m.label))}" aria-label="${esc(pick(m.label))}"`
        + ` aria-pressed="${selected === m.id ? 'true' : 'false'}">`
        + `<span class="jr-seal-glyph" aria-hidden="true">${m.glyph}</span>`
        + `<span class="jr-seal-label">${esc(pick(m.label))}</span>`
        + '</button>').join('');
      return `<div class="jr-moods" role="group" aria-label="${esc(pick(T.mood))}">${seals}</div>`;
    }

    function pageHtml() {
      if (state.loading) return '<div class="jr-page-inner"><p class="jr-note">…</p></div>';
      if (state.failed) {
        return `<div class="jr-page-inner"><p class="jr-note jr-note--bad">${esc(pick(T.load_failed))}</p></div>`;
      }

      const day = state.days[state.index];
      const entry = entryFor(day);
      const isToday = day === todayIso();
      const draft = state.drafts[day];
      // An unsaved draft outranks the stored page: it is the newer of
      // the two and the only one that would otherwise be lost.
      const writing = state.editing || !entry || draft !== undefined;
      const text = draft !== undefined ? draft : (entry ? textOf(entry) : '');
      const mood = state.draftMood !== null ? state.draftMood : (entry && entry.mood) || null;

      let body;
      if (writing) {
        body = ''
          + `<textarea class="jr-write" id="jrWrite" maxlength="${MAX_LEN}"`
          + ` placeholder="${esc(pick(T.placeholder))}"`
          + ` aria-label="${esc(longDate(day))}">${esc(text)}</textarea>`
          + moodRowHtml(mood, true)
          + '<div class="jr-write-row">'
          // dir="ltr": "0 / 2000" is a number pair, and bidi reordering
          // turns it into "2000 / 0" on a Persian or Arabic page.
          + `<span class="jr-count" id="jrCount" dir="ltr">${text.length} / ${MAX_LEN}</span>`
          + `<button type="button" class="btn btn-primary btn-sm jr-save" id="jrSave">${esc(pick(T.save))}</button>`
          + '</div>';
      } else {
        body = ''
          + `<div class="jr-written">${esc(text).replace(/\n/g, '<br>')}</div>`
          + (mood ? moodRowHtml(mood, false) : '')
          + '<div class="jr-write-row">'
          + `<span class="jr-count">${esc(pick(T.written_on))} ${esc(stamp(entry.created_at_utc))}</span>`
          + `<button type="button" class="btn btn-ghost btn-sm" id="jrEdit">${esc(pick(T.edit))}</button>`
          + '</div>';
      }

      return ''
        + '<div class="jr-page-inner">'
        + '<header class="jr-page-head">'
        + `<p class="jr-page-date">${esc(longDate(day))}</p>`
        + (isToday ? `<span class="jr-today-pill">${esc(pick(T.today))}</span>` : '')
        + '</header>'
        + body
        + '</div>';
    }

    function render() {
      const openLabel = state.opened ? pick(T.close) : pick(T.open);
      root.innerHTML = ''
        + '<header class="jr-head reveal">'
        + `<p class="jr-eyebrow">${esc(pick(T.eyebrow))}</p>`
        + `<h2 class="jr-heading text-gradient">${esc(pick(T.title))}</h2>`
        + `<p class="jr-lede">${esc(pick(T.lede))}</p>`
        + '</header>'
        + `<div class="jr-stage${state.opened ? ' is-open' : ''}">`
        + '<div class="jr-book" id="jrBook">'
        + '<div class="jr-page jr-page--left"><div class="jr-page-inner">'
        + `<h3 class="jr-index-title">${esc(pick(T.index_title))}</h3>`
        + demoNoteHtml()
        + indexHtml()
        + '</div></div>'
        + `<div class="jr-page jr-page--right" id="jrRight">${pageHtml()}</div>`
        + '<div class="jr-leaf" id="jrLeaf" aria-hidden="true">'
        + '<div class="jr-leaf-face jr-leaf-front"></div>'
        + '<div class="jr-leaf-face jr-leaf-back"></div>'
        + '</div>'
        + '<div class="jr-cover" id="jrCover">'
        + '<div class="jr-cover-plate">'
        + '<svg class="jr-crest" viewBox="0 0 120 120" aria-hidden="true">'
        + '<circle cx="60" cy="60" r="44" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".55"/>'
        + '<circle cx="60" cy="60" r="34" fill="none" stroke="currentColor" stroke-width="1" opacity=".35"/>'
        + '<path d="M60 20v80M20 60h80" stroke="currentColor" stroke-width="1" opacity=".25"/>'
        + '<path d="M60 34c9 12 14 20 14 27a14 14 0 0 1-28 0c0-7 5-15 14-27Z" fill="none" stroke="currentColor" stroke-width="1.6"/>'
        + '<path d="M40 84c6-6 13-9 20-9s14 3 20 9" fill="none" stroke="currentColor" stroke-width="1.4" opacity=".7"/>'
        + '</svg>'
        + `<h3 class="jr-cover-title">${esc(pick(T.cover_title))}</h3>`
        + `<p class="jr-cover-sub">${esc(pick(T.cover_sub))}</p>`
        + '</div>'
        + '<div class="jr-clasp" aria-hidden="true"></div>'
        + '</div>'
        + '</div>'
        + '<div class="jr-controls">'
        + `<button type="button" class="btn btn-ghost btn-sm jr-turn" id="jrPrev" aria-label="${esc(pick(T.prev))}">`
        + '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 6 8 12l6 6"/></svg></button>'
        + `<button type="button" class="btn btn-primary btn-sm jr-open" id="jrOpen">${esc(openLabel)}</button>`
        + `<button type="button" class="btn btn-ghost btn-sm jr-turn" id="jrNext" aria-label="${esc(pick(T.next))}">`
        + '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 6 6 6-6 6"/></svg></button>'
        + `<button type="button" class="btn btn-ghost btn-sm jr-pdf" id="jrPdf">`
        + '<svg viewBox="0 0 24 24" class="jr-pdf-icon" aria-hidden="true">'
        + '<path d="M12 3.5v10"/><path d="m8 10 4 4 4-4"/><path d="M5 18.5h14"/></svg>'
        + `<span>${esc(pick(T.pdf))}</span></button>`
        + '</div>'
        + '</div>';

      wire();
      if (window.DWMotion) window.DWMotion.observeReveals(root);
    }

    /* ---- the motion ---------------------------------------------- */

    function openBook() {
      const stage = root.querySelector('.jr-stage');
      state.opened = true;
      cue('bookOpen');
      stage.classList.add('is-open');
      const btn = root.querySelector('#jrOpen');
      if (btn) btn.textContent = pick(T.close);
      // Focus the writing surface once the cover is out of the way, so
      // a reader who opened the book to write is already in it.
      const focusDelay = reduced() ? 0 : 900;
      setTimeout(() => {
        const write = root.querySelector('#jrWrite');
        if (write && state.opened) write.focus({ preventScroll: true });
      }, focusDelay);
    }

    function closeBook() {
      state.opened = false;
      cue('bookClose');
      root.querySelector('.jr-stage').classList.remove('is-open');
      const btn = root.querySelector('#jrOpen');
      if (btn) btn.textContent = pick(T.open);
    }

    /* A real leaf turning: the outgoing page is cloned onto the front
       face, the incoming onto the back, and the leaf rotates. Cheaper
       and far more convincing than animating the live page, which would
       have to be readable at every angle. */
    function turnTo(index, direction) {
      if (index === state.index || index < 0 || index >= state.days.length) return;
      const right = root.querySelector('#jrRight');
      const leaf = root.querySelector('#jrLeaf');

      keepDraft();
      const outgoing = right.innerHTML;
      state.index = index;
      state.editing = !entryFor(state.days[index]);
      state.draftMood = null;
      const incoming = pageHtml();

      // No leaf to turn on a narrow screen (the spread is stacked there,
      // see about.css), and none under reduced motion. Both swap the
      // page straight away rather than waiting out an animation that is
      // never going to run.
      const leafHidden = !leaf || getComputedStyle(leaf).display === 'none';
      if (reduced() || leafHidden || !state.opened) {
        right.innerHTML = incoming;
        wirePage();
        renderIndex();
        return;
      }

      leaf.querySelector('.jr-leaf-front').innerHTML = outgoing;
      leaf.querySelector('.jr-leaf-back').innerHTML = incoming;
      right.innerHTML = incoming;
      renderIndex();

      leaf.classList.remove('is-turning', 'is-turning-back');
      // Force a reflow so the class change below actually animates.
      void leaf.offsetWidth;
      leaf.classList.add(direction < 0 ? 'is-turning-back' : 'is-turning');
      cue('pageTurn');
      const done = () => {
        leaf.classList.remove('is-turning', 'is-turning-back');
        leaf.querySelector('.jr-leaf-front').innerHTML = '';
        leaf.querySelector('.jr-leaf-back').innerHTML = '';
        wirePage();
      };
      setTimeout(done, 720);
    }

    function renderIndex() {
      const holder = root.querySelector('.jr-page--left .jr-page-inner');
      if (!holder) return;
      holder.innerHTML = `<h3 class="jr-index-title">${esc(pick(T.index_title))}</h3>`
        + demoNoteHtml() + indexHtml();
      holder.querySelectorAll('[data-goto]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const target = parseInt(btn.dataset.goto, 10);
          turnTo(target, target > state.index ? 1 : -1);
        });
      });
    }

    /* ---- saving --------------------------------------------------- */

    async function save() {
      if (state.busy) return;
      const write = root.querySelector('#jrWrite');
      const btn = root.querySelector('#jrSave');
      if (!write) return;
      const text = write.value.trim();
      if (!text) {
        window.DWToast.warning(pick(T.empty_refused));
        write.focus();
        return;
      }
      state.busy = true;
      if (btn) { btn.disabled = true; btn.textContent = pick(T.saving); }
      try {
        const saved = await window.DWApi.journalSave(
          state.days[state.index], text, state.draftMood,
        );
        const existing = state.entries.findIndex((e) => e.date === saved.date);
        if (existing >= 0) state.entries[existing] = saved;
        else state.entries.push(saved);
        state.editing = false;
        state.draftMood = null;
        // Saved is saved: the draft has served its purpose and must not
        // outrank the stored page from here on.
        delete state.drafts[saved.date];
        rebuildDays();
        const right = root.querySelector('#jrRight');
        right.innerHTML = pageHtml();
        right.classList.add('jr-page--sealed');
        cue('penStroke');
        setTimeout(() => right.classList.remove('jr-page--sealed'), 1200);
        wirePage();
        renderIndex();
        window.DWToast.success(pick(T.saved_toast));
      } catch (err) {
        const message = (err && err.message) || pick(T.save_failed);
        window.DWToast.error(message);
        if (btn) { btn.disabled = false; btn.textContent = pick(T.save); }
      } finally {
        state.busy = false;
      }
    }

    /* ---- wiring --------------------------------------------------- */

    function wirePage() {
      const write = root.querySelector('#jrWrite');
      const count = root.querySelector('#jrCount');
      if (write && count) {
        write.addEventListener('input', () => {
          count.textContent = `${write.value.length} / ${MAX_LEN}`;
        });
        // Ctrl/Cmd+Enter saves - the shortcut anyone who writes in a box
        // tries first.
        write.addEventListener('keydown', (e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); save(); }
        });
      }
      const saveBtn = root.querySelector('#jrSave');
      if (saveBtn) saveBtn.addEventListener('click', save);

      const editBtn = root.querySelector('#jrEdit');
      if (editBtn) {
        editBtn.addEventListener('click', () => {
          state.editing = true;
          const right = root.querySelector('#jrRight');
          right.innerHTML = pageHtml();
          wirePage();
          const box = root.querySelector('#jrWrite');
          if (box) box.focus();
        });
      }

      root.querySelectorAll('.jr-seal:not([disabled])').forEach((seal) => {
        seal.addEventListener('click', () => {
          const wanted = seal.dataset.mood;
          state.draftMood = state.draftMood === wanted ? null : wanted;
          root.querySelectorAll('.jr-seal').forEach((s) => {
            const on = s.dataset.mood === state.draftMood;
            s.classList.toggle('is-on', on);
            s.setAttribute('aria-pressed', on ? 'true' : 'false');
          });
        });
      });
    }

    /* The book as a file. The request is authenticated, so it cannot be
       a plain link - the blob is fetched with the token and handed to
       the browser through an object URL, which is then revoked rather
       than left holding the whole PDF in memory. */
    async function downloadPdf() {
      const btn = root.querySelector('#jrPdf');
      if (!btn || btn.disabled) return;
      if (!state.entries.length) {
        window.DWToast.warning(pick(T.pdf_empty));
        return;
      }
      const label = btn.querySelector('span');
      const original = label ? label.textContent : '';
      btn.disabled = true;
      if (label) label.textContent = pick(T.pdf_working);
      try {
        const blob = await window.DWApi.journalPdf(lang());
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'book-of-days.pdf';
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
      } catch (err) {
        window.DWToast.error((err && err.message) || pick(T.pdf_failed));
      } finally {
        btn.disabled = false;
        if (label) label.textContent = original || pick(T.pdf);
      }
    }

    function wire() {
      const openBtn = root.querySelector('#jrOpen');
      const cover = root.querySelector('#jrCover');
      if (openBtn) {
        openBtn.addEventListener('click', () => (state.opened ? closeBook() : openBook()));
      }
      if (cover) cover.addEventListener('click', () => { if (!state.opened) openBook(); });

      const prev = root.querySelector('#jrPrev');
      const next = root.querySelector('#jrNext');
      // "Earlier" walks back in time, which is FORWARD through the list
      // (it is newest-first). The arrows are labelled by time, not by
      // array direction, because that is what the reader is thinking in.
      if (prev) prev.addEventListener('click', () => turnTo(state.index + 1, 1));
      if (next) next.addEventListener('click', () => turnTo(state.index - 1, -1));

      const pdf = root.querySelector('#jrPdf');
      if (pdf) pdf.addEventListener('click', downloadPdf);

      renderIndex();
      wirePage();
    }

    load();

    document.addEventListener('dwai:langchange', () => {
      // Re-render in the new language, keeping the page the reader is on
      // and anything they have typed but not yet saved. The draft is
      // kept in state rather than read back off the new DOM, so it also
      // survives a language change made from another page's control.
      keepDraft();
      render();
      if (state.opened) root.querySelector('.jr-stage').classList.add('is-open');
    });
  }

  window.DWAboutJournal = { init };
})();
