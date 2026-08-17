/* "That day was outside your range - what was it?"
   ------------------------------------------------
   The weekly plan is aimed at a RANGE, not at one number. From the
   second logged day of a week onward a day can land outside that range,
   and there are two genuinely different things that can mean:

     * it was an unusual day - travel, illness, a deadline - and letting
       it steer the plan would drag the rest of the week toward a life
       the user is not living;
     * it was a real change, and the plan should follow it.

   Neither is a safe default, which is exactly why this asks instead of
   deciding. Everything that decides WHETHER to ask - the band, the
   day's position in the week, the score - is computed on the server
   (GET /plan/day-status); this module only renders the question and
   sends the answer back. A browser that recomputed any of it would
   either nag someone about an ordinary day or quietly skip a real one.

   Shared by the check-in result screen and the weekly page so the
   question is asked once, the same way, wherever the user happens to
   be - rather than living twice and drifting. */
(function () {
  const T = (key) => (window.DWI18n && window.DWI18n.t ? window.DWI18n.t(key) : key);

  let lastStatus = null;
  // Kept so a language switch can re-render the question without
  // losing what the page asked to happen after it is answered - the
  // weekly page uses it to re-read the plan when a day is counted.
  let lastOnDecided = null;

  /* The server's view of today. Never throws outward: this is an extra
     question, and a page that fails to load it should simply not ask,
     not break the screen it is sitting on. */
  async function status() {
    try {
      lastStatus = await window.DWApi.planDayStatus();
    } catch (e) {
      lastStatus = null;
    }
    return lastStatus;
  }

  function fmt(value) {
    return (value === null || value === undefined) ? '—' : Number(value).toFixed(1);
  }

  function fill(template, data) {
    return String(template || '').replace(/\{(\w+)\}/g, (m, k) => (
      Object.prototype.hasOwnProperty.call(data, k) ? data[k] : m
    ));
  }

  /* Builds the card. Kept as DOM construction rather than an innerHTML
     template so the numbers go in as text - they come from the server,
     but the habit of building this kind of panel with string
     concatenation is how a value that later becomes user-controlled
     ends up as markup. */
  function build(state, onDecided) {
    const card = document.createElement('div');
    card.className = 'band-decision card';
    card.setAttribute('role', 'group');

    const title = document.createElement('h3');
    title.className = 'band-decision-title';
    title.textContent = T('band_decision_title');
    card.appendChild(title);

    const lead = document.createElement('p');
    lead.className = 'band-decision-lead';
    lead.textContent = fill(T('band_decision_lead'), {
      score: fmt(state.score),
      low: fmt(state.band_low),
      high: fmt(state.band_high),
    });
    card.appendChild(lead);

    const options = document.createElement('div');
    options.className = 'band-decision-options';

    const make = (decision, labelKey, noteKey, variant) => {
      const wrap = document.createElement('div');
      wrap.className = 'band-decision-option';

      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn ' + variant;
      button.textContent = T(labelKey);
      button.addEventListener('click', () => decide(decision, card, onDecided));
      wrap.appendChild(button);

      const note = document.createElement('p');
      note.className = 'band-decision-note muted';
      note.textContent = fill(T(noteKey), {
        percent: Math.round((state.exception_weight || 0) * 100),
      });
      wrap.appendChild(note);
      options.appendChild(wrap);
    };

    make('exception', 'band_decision_exception', 'band_decision_exception_note', 'btn-ghost');
    make('counted', 'band_decision_counted', 'band_decision_counted_note', 'btn-primary');
    card.appendChild(options);

    // Deliberately no dismiss control. The question has exactly two
    // real answers and closing it would leave the week in neither
    // state - which is the ambiguity this whole flow exists to remove.
    return card;
  }

  async function decide(decision, card, onDecided) {
    card.querySelectorAll('button').forEach((b) => { b.disabled = true; });
    let payload = null;
    // Paired with the result - see DWLastResult.payload().
    try { payload = window.DWLastResult.payload(); } catch (e) {}
    try {
      const result = await window.DWApi.planDayDecision(decision, payload || {});
      lastStatus = result;
      card.classList.add('band-decision--done');
      card.innerHTML = '';
      const done = document.createElement('p');
      done.className = 'band-decision-done';
      done.textContent = T(
        decision === 'exception' ? 'band_decision_done_exception' : 'band_decision_done_counted'
      );
      card.appendChild(done);
      if (window.DWToast) {
        window.DWToast.success(T(
          decision === 'exception' ? 'band_decision_done_exception' : 'band_decision_done_counted'
        ));
      }
      if (typeof onDecided === 'function') onDecided(decision, result);
    } catch (e) {
      card.querySelectorAll('button').forEach((b) => { b.disabled = false; });
      if (window.DWToast) window.DWToast.error(e.message);
    }
  }

  /* Renders the question into `mount` if today actually needs one.
     Returns true when it asked, so a caller can hold back something
     else (a games screen, a scroll) until the week is unambiguous. */
  async function maybeAsk(mount, onDecided) {
    if (!mount) return false;
    const state = await status();
    if (!state || !state.needs_decision) return false;
    lastOnDecided = typeof onDecided === 'function' ? onDecided : null;
    mount.innerHTML = '';
    mount.appendChild(build(state, lastOnDecided));
    mount.classList.remove('hidden');
    return true;
  }

  window.DWBandDecision = { maybeAsk, status, get last() { return lastStatus; } };

  // i18n.js dispatches this on `document` with no `bubbles`, so a
  // listener on `window` would never fire - every other page listens
  // here too. Re-renders the already-asked question in the new language
  // rather than re-fetching: the numbers do not change with language.
  document.addEventListener('dwai:langchange', () => {
    document.querySelectorAll('.band-decision').forEach((card) => {
      if (card.classList.contains('band-decision--done') || !lastStatus) return;
      const mount = card.parentElement;
      if (!mount) return;
      mount.innerHTML = '';
      mount.appendChild(build(lastStatus, lastOnDecided));
    });
  });
})();
