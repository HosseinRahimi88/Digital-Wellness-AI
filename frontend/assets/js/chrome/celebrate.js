/* DWCelebrate — the one big moment the app allows itself.

   Ticking the last exercise of a day is the only thing in this app that
   is unambiguously worth celebrating: it is the user doing the thing,
   not the app measuring them. Everything else the guide does is small
   and quiet on purpose, so this is deliberately the exception - the
   guide leaves its corner, comes to the middle of the screen, grows,
   blows a kiss, and goes back.

   Three rules it does not break:

     * it never fires twice for the same day. `dayComplete()` is called
       from the tick handler, which re-reads the plan afterwards and can
       easily call again for a day that was already finished; the caller
       passes a key and this remembers it for the session;

     * reduced motion gets the kiss without the journey. Somebody who
       has asked the system for less movement has asked for exactly
       this kind of thing to stop, and "but it is a reward" is not an
       exemption. The heart still appears and the sound still plays;

     * it is entirely non-blocking. The mascot is moved with a transform
       on a clone-free element and put back by a timer; if anything here
       throws, the tick has already been saved and the page is fine. */
(function () {
  const seen = new Set();
  let running = false;

  function reducedMotion() {
    try {
      return document.documentElement.classList.contains('force-reduce-motion')
        || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      return false;
    }
  }

  /* The kiss itself: a heart that leaves the guide's mouth, drifts up
     and fades. Drawn rather than typed, so it is the same on every
     platform - the emoji renders as a different object on each. */
  function heart(host) {
    const mark = document.createElement('div');
    mark.className = 'dw-celebrate-kiss';
    mark.setAttribute('aria-hidden', 'true');
    mark.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 21s-7.5-4.7-9.4-9A5.2 5.2 0 0 1 12 6.6 5.2 5.2 0 0 1 21.4 12c-1.9 4.3-9.4 9-9.4 9Z"/></svg>';
    host.appendChild(mark);
    window.setTimeout(() => mark.remove(), 2400);
  }

  /* Move the guide to the middle of the viewport, using its own current
     position rather than assuming the corner: the widget is bottom-right
     in LTR and bottom-left in RTL, and on a phone it sits closer in. */
  function travel(widget) {
    const box = widget.getBoundingClientRect();
    const dx = (window.innerWidth / 2) - (box.left + box.width / 2);
    const dy = (window.innerHeight / 2) - (box.top + box.height / 2);
    widget.style.setProperty('--dw-celebrate-x', `${Math.round(dx)}px`);
    widget.style.setProperty('--dw-celebrate-y', `${Math.round(dy)}px`);
  }

  /**
   * @param {string} key  Something that identifies the day, so the same
   *                      completion cannot fire this twice.
   */
  function dayComplete(key) {
    try {
      const id = String(key || 'day');
      if (seen.has(id) || running) return false;
      seen.add(id);

      const widget = document.querySelector('.mascot-widget');
      if (!widget) return false;

      running = true;
      if (window.DWMascot && window.DWMascot.react) window.DWMascot.react('good');

      const quiet = reducedMotion();
      if (!quiet) {
        travel(widget);
        widget.classList.add('is-celebrating');
      }

      // The sound is timed to the arrival, not to the tick, so the kiss
      // is heard where it is seen. Under reduced motion there is no
      // journey, so it plays at once.
      const delay = quiet ? 0 : 620;
      window.setTimeout(() => {
        if (window.DWSound && window.DWSound.smooch) window.DWSound.smooch();
        heart(widget);
      }, delay);

      window.setTimeout(() => {
        widget.classList.remove('is-celebrating');
        widget.style.removeProperty('--dw-celebrate-x');
        widget.style.removeProperty('--dw-celebrate-y');
        running = false;
      }, quiet ? 1200 : 2600);
      return true;
    } catch (e) {
      running = false;
      return false;
    }
  }

  /* For a page that legitimately wants to re-arm - the weekly page
     rebuilds itself on a language change and re-reads the plan. */
  function forget(key) { seen.delete(String(key || 'day')); }

  window.DWCelebrate = { dayComplete, forget };
})();
