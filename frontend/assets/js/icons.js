/*
  DWIcon - the project's own inline-SVG icon set.

  Why a module and not more emoji: an emoji is drawn by the operating
  system, so the same "🔊" is a flat glyph on one machine, a colourful
  cartoon on another, and a missing box on a third. For interface
  controls - play, pause, volume, send, close - that inconsistency reads
  as unfinished, and none of them can be recoloured or sized to match
  the rest of the design.

  Every path below is drawn for this project against one shared grid:
  24x24, 1.8 stroke, round caps and joins, `currentColor` so an icon
  inherits its button's colour and its theme. They are stroke-only by
  design, which is what makes them sit next to the existing navigation
  icons without looking like a second set.

  Emoji are deliberately KEPT for badge and game glyphs. Sixty-three
  badges need sixty-three distinguishable pictures; drawing those as
  bespoke line icons is a design project rather than a code change, and
  a set of near-identical abstract marks would be worse than the emoji
  it replaced - the user could no longer tell one badge from another at
  a glance, which is the only job that icon has.

  Usage:  el.innerHTML = DWIcon.get('play');
          DWIcon.set(el, 'pause');            // replaces content
*/
(function () {
  const VIEWBOX = '0 0 24 24';

  /* Path data only - the wrapper is shared, so no icon can drift away
     from the common stroke width or grid. */
  const PATHS = {
    play: 'M8 5.2v13.6l11-6.8z',
    pause: 'M9.5 5v14M14.5 5v14',
    next: 'M6 5.2v13.6l9-6.8zM17.5 5v14',
    volume: 'M4 9.5h3.2L12 5.5v13l-4.8-4H4z',
    volumeWave: 'M15.5 9.2a4 4 0 0 1 0 5.6M18 6.8a7.5 7.5 0 0 1 0 10.4',
    volumeMute: 'M4 9.5h3.2L12 5.5v13l-4.8-4H4zM16 10l5 4M21 10l-5 4',
    upload: 'M12 16.5V4.5M8 8l4-3.5L16 8M4.5 15v3.5a1 1 0 0 0 1 1h13a1 1 0 0 0 1-1V15',
    close: 'M6.5 6.5l11 11M17.5 6.5l-11 11',
    send: 'M4 12l16-7-7 16-2.2-6.8z',
    chat: 'M20 12a7.5 7.5 0 0 1-10.9 6.7L4.5 20l1.3-4.4A7.5 7.5 0 1 1 20 12z',
    group: 'M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM16.8 11.2a2.6 2.6 0 1 0 0-5.2M2.5 19.5c.8-3.4 3-5.3 6.5-5.3s5.7 1.9 6.5 5.3M16 14.4c2.3.4 3.9 2.1 4.5 4.9',
    leave: 'M14 19.5H6a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1h8M12.5 12h8M17.5 8.5l3.5 3.5-3.5 3.5',
    report: 'M12 4.5v10M12 18v1.5M12 4.5l8 13.5H4z',
    block: 'M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM6 6l12 12',
    settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.2 14.4l1.6 1a8.6 8.6 0 0 0 0-6.8l-1.6 1M4.8 9.6l-1.6-1a8.6 8.6 0 0 0 0 6.8l1.6-1M14.4 4.8l1-1.6a8.6 8.6 0 0 0-6.8 0l1 1.6M9.6 19.2l-1 1.6a8.6 8.6 0 0 0 6.8 0l-1-1.6',
    download: 'M12 4.5v11M8 11.5l4 4 4-4M4.5 19.5h15',
    check: 'M5 12.5l4.5 4.5L19 7.5',
    info: 'M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM12 11v5.5M12 7.8v.2',
    lock: 'M6.5 11V8.5a5.5 5.5 0 0 1 11 0V11M5.5 11h13a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1z',
    spark: 'M12 3.5l2 5.6 5.6 2-5.6 2-2 5.6-2-5.6-5.6-2 5.6-2z',
  };

  /* Icons whose shape is a solid mark rather than an outline. Keeping
     the list here rather than per-path means the wrapper stays the one
     place that decides fill vs stroke. */
  const FILLED = new Set(['play', 'next', 'send', 'spark']);

  function get(name, opts) {
    opts = opts || {};
    const path = PATHS[name];
    if (!path) return '';
    const size = opts.size || 20;
    const filled = FILLED.has(name);
    const extra = name === 'volume' && opts.waves ? `<path d="${PATHS.volumeWave}"/>` : '';
    return `<svg class="dw-icon dw-icon-${name}" viewBox="${VIEWBOX}" width="${size}" height="${size}"
      fill="${filled ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="1.8"
      stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"
    ><path d="${path}"/>${extra}</svg>`;
  }

  function set(element, name, opts) {
    if (!element) return;
    element.innerHTML = get(name, opts);
  }

  /* Replaces the content of every [data-dw-icon] on the page. Lets
     static markup declare an icon without each page's controller having
     to know about it. */
  function hydrate(root) {
    (root || document).querySelectorAll('[data-dw-icon]').forEach((el) => {
      set(el, el.getAttribute('data-dw-icon'), {
        size: parseInt(el.getAttribute('data-dw-icon-size'), 10) || undefined,
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => hydrate());
  } else {
    hydrate();
  }

  window.DWIcon = { get, set, hydrate, names: () => Object.keys(PATHS) };
})();
