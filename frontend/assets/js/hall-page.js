/*
  hall.html's controller. Loads the badge wall and the private awareness
  panel, then hands the guide something to say about the page as a whole.
*/
(function () {
  /* The violations panel under the wall.
     Only rendered when there is something to say - a section reading
     "0 open violations" on a page about achievements would turn a
     clean record into a scolding, which is the opposite of what the
     rest of this page is for (see services/badge_service.py's header
     on why nothing here ever tells a user they failed).
     Every number comes from the server's ledger; nothing is counted
     locally. */
  function renderViolations(data) {
    const section = document.getElementById('violationsSection');
    if (!section) return;
    const open = data.open_violations || 0;
    const revoked = (data.revoked_badges || []).length;
    const withheld = (data.withheld_badges || []).length;

    if (!open && !revoked && !withheld) {
      section.classList.add('hidden');
      return;
    }
    section.classList.remove('hidden');

    const count = document.getElementById('violationsCount');
    if (count) {
      // dir/isolate for the same reason the badge counts carry it: a
      // bare number inside RTL prose gets reordered against neighbouring
      // punctuation without it.
      count.dir = 'ltr';
      count.style.unicodeBidi = 'isolate';
      count.textContent = String(open);
    }

    const detail = document.getElementById('violationsDetail');
    if (!detail) return;
    const lines = [];
    if (revoked) {
      lines.push(window.DWI18n.t('violations_revoked').replace('{count}', revoked));
    }
    if (withheld) {
      lines.push(window.DWI18n.t('violations_withheld').replace('{count}', withheld));
    }
    detail.textContent = lines.join(' ');
    detail.classList.toggle('hidden', lines.length === 0);
  }

  async function run() {
    /* Every other logged-in page starts with DWShell.init(), and this
       one did not. That single missing call is why the Hall of Fame
       rendered entirely in English with the ambient music stopped:
       init() is what applies the saved language (DWI18n.init), starts
       the music player (DWMusic.init), wires the shared chrome
       (theme/lang/logout/notification bell), highlights the nav, and
       redirects an anonymous visitor. Without it none of that ran, so
       the page fell back to the untranslated markup and silence.

       Awaited, and the badge wall only loads for a real account, so an
       expired session lands on app.html instead of rendering a wall of
       empty badges. */
    const account = await window.DWShell.init('hall');
    if (!account) return;

    if (!window.DWHallOfFame) return;
    window.DWHallOfFame.load({
      hall: document.getElementById('hallMount'),
      awareness: document.getElementById('awarenessMount'),
      count: document.getElementById('hallCount'),
    }).then((data) => {
      if (!data) return;
      renderViolations(data);
      // C-4: a newly earned badge is the one thing on this page worth a
      // sound. It only fires when the count actually went up since the
      // last visit, so re-opening the page is silent.
      try {
        const key = 'dwai_badges_seen_count';
        const before = parseInt(localStorage.getItem(key) || '0', 10);
        const now = data.earned_count || 0;
        if (now > before && window.DWSound && window.DWSound.badge) window.DWSound.badge();
        localStorage.setItem(key, String(now));
      } catch (e) { /* storage disabled - the wall still renders */ }
      // No automatic guide bubble here - same reason as shell.js and
      // app.js. Tapping the mascot, or any badge, still explains it.
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
