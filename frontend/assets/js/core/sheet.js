/*
  DWSheet — one modal for the whole app.

  Written because three separate screens needed the same thing at once
  and there was no modal anywhere in the codebase: the CSV upload has to
  ASK whether a file is a test or a real save before it does either, the
  three-day-decline check has to interrupt with a question, and "more
  detail" on the dashboard trend needs somewhere to put a long list.
  Three hand-rolled overlays would have been three sets of the same
  focus, Escape and scroll-lock bugs.

  Deliberately small. It renders a title, some body HTML the caller owns,
  and a row of buttons; it returns a promise that resolves with the
  chosen button's value (or null if the user backed out). It does not
  know about CSVs, scores, or anything else in this app.

  Accessibility is not optional here, because this thing takes over the
  screen: role="dialog" + aria-modal, focus moves in and is restored on
  close, Escape and backdrop-click both cancel, Tab is trapped inside,
  and the page behind cannot scroll while it is open.
*/
(function () {
  let openSheet = null;

  function t(key, fallback) {
    const s = window.DWI18n && window.DWI18n.t ? window.DWI18n.t(key) : null;
    // DWI18n.t returns the key itself when a string is missing; that is
    // fine in a label but useless in a button, so fall back explicitly.
    return !s || s === key ? fallback : s;
  }

  function close(result) {
    if (!openSheet) return;
    const { root, onDone, previousFocus, keyHandler } = openSheet;
    openSheet = null;
    document.removeEventListener('keydown', keyHandler, true);
    document.body.classList.remove('dw-sheet-open');
    root.classList.add('dw-sheet--leaving');
    const finish = () => {
      root.remove();
      if (previousFocus && previousFocus.focus) {
        try { previousFocus.focus(); } catch (e) { /* element went away */ }
      }
      onDone(result);
    };
    // Match the CSS exit; if motion is reduced the transition never
    // fires, so never depend on transitionend alone.
    setTimeout(finish, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 160);
  }

  /**
   * open({ title, body, bodyHtml, buttons, size, dismissable })
   *
   *   title      plain text heading
   *   body       plain text paragraph (escaped for you)
   *   bodyHtml   markup, when the caller needs structure. The caller is
   *              responsible for escaping anything user-supplied inside
   *              it - see esc() below, exported for exactly that.
   *   buttons    [{ label, value, style: 'primary'|'ghost'|'danger', autofocus }]
   *   size       'sm' | 'md' | 'lg'
   *   className  extra class on the root, for a caller styling its own
   *              panel contents (e.g. 'dw-sheet--profile')
   *   dismissable  false to require an explicit button (default true)
   *
   * Resolves with the chosen `value`, or null when dismissed.
   */
  function open(options) {
    const opts = options || {};
    // Only one at a time. A second call replaces the first rather than
    // stacking, and the first resolves null so nobody is left awaiting.
    if (openSheet) close(null);

    return new Promise((resolve) => {
      const root = document.createElement('div');
      root.className = `dw-sheet dw-sheet--${opts.size || 'md'}`;
      // A chooser's options ARE the content, so they are laid out as
      // full-width option rows rather than a footer of pill buttons -
      // a pill with a sentence in it clips its own label.
      if (opts.choice) root.classList.add('dw-sheet--choice');
      // One extra class, so a caller with its own layout inside the
      // panel (the team profile) can style it without a second modal
      // implementation existing in the codebase.
      if (opts.className) root.classList.add(opts.className);
      const labelId = `dwSheetTitle_${Date.now()}`;

      const buttons = Array.isArray(opts.buttons) && opts.buttons.length
        ? opts.buttons
        : [{ label: t('sheet_close', 'Close'), value: null, style: 'ghost', autofocus: true }];

      root.innerHTML =
        '<div class="dw-sheet-backdrop" data-dismiss="1"></div>'
        + '<div class="dw-sheet-panel" role="dialog" aria-modal="true"'
        + ` aria-labelledby="${labelId}">`
        + `<h2 class="dw-sheet-title" id="${labelId}"></h2>`
        + '<div class="dw-sheet-body"></div>'
        + '<div class="dw-sheet-actions"></div>'
        + '</div>';

      root.querySelector('.dw-sheet-title').textContent = opts.title || '';
      const bodyEl = root.querySelector('.dw-sheet-body');
      if (opts.bodyHtml) bodyEl.innerHTML = opts.bodyHtml;
      else if (opts.body) {
        const p = document.createElement('p');
        p.textContent = opts.body;
        bodyEl.appendChild(p);
      }

      const actions = root.querySelector('.dw-sheet-actions');
      buttons.forEach((b) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `btn btn-${b.style || 'ghost'} dw-sheet-btn`;
        if (b.hint) {
          const main = document.createElement('span');
          main.className = 'dw-sheet-btn-label';
          main.textContent = b.label;
          const hint = document.createElement('span');
          hint.className = 'dw-sheet-btn-hint';
          hint.textContent = b.hint;
          btn.append(main, hint);
        } else {
          btn.textContent = b.label;
        }
        btn.addEventListener('click', () => close(b.value === undefined ? null : b.value));
        actions.appendChild(btn);
      });

      const dismissable = opts.dismissable !== false;
      if (dismissable) {
        root.querySelector('.dw-sheet-backdrop')
          .addEventListener('click', () => close(null));
      }

      const keyHandler = (e) => {
        if (e.key === 'Escape' && dismissable) { e.preventDefault(); close(null); return; }
        if (e.key !== 'Tab') return;
        // Trap Tab inside the panel, so the user cannot tab onto the
        // page behind a modal they have not answered yet.
        const focusable = root.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      };

      openSheet = {
        root,
        onDone: resolve,
        previousFocus: document.activeElement,
        keyHandler,
      };
      document.addEventListener('keydown', keyHandler, true);
      document.body.classList.add('dw-sheet-open');
      document.body.appendChild(root);
      // Next frame, so the entry transition has a starting state.
      requestAnimationFrame(() => root.classList.add('dw-sheet--in'));

      const wanted = buttons.findIndex((b) => b.autofocus);
      const target = actions.children[wanted >= 0 ? wanted : buttons.length - 1];
      // preventScroll matters on a long panel: the actions row is at the
      // bottom, so focusing it normally scrolls the reader straight past
      // the content they asked to see.
      if (target) {
        target.focus({ preventScroll: true });
        root.querySelector('.dw-sheet-panel').scrollTop = 0;
      }
    });
  }

  function esc(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  window.DWSheet = { open, close, esc };
})();
