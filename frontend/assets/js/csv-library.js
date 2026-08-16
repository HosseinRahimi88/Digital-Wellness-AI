/*
  DWCsvLibrary — the user's own saved check-ins, as CSV.

  The idea this implements: after a check-in you can save the exact
  answers you just gave under a name you choose. That file downloads to
  your machine AND stays listed on the check-in screen, so the next time
  you want to run the same day again - or a small variation of it - you
  pick it from the list and the whole form is already filled in. You
  press Next, not retype forty fields.

  Two shelves, because they are genuinely different things:

    main   - saved from a check-in that was RECORDED to your history.
    test   - saved from a check-in you ticked "don't count this",
             i.e. a hypothetical you were trying out.

  Which shelf an entry lands on is not a second choice to make; it is
  read from the exclude flag that was already set when the prediction
  ran, so the two can never disagree.

  Storage is localStorage, deliberately:
    * these are the user's own answers, and this app's whole posture is
      that such data does not leave the device unless the user sends it;
    * the file they downloaded is the durable copy - this list is a
      convenience index over work they already have;
    * it keeps working with no backend change and no new endpoint to
      secure.
  The cost is that the list is per-browser, which is why the download is
  not optional: the CSV itself is the portable artefact.

  The CSV format is the app's OWN questionnaire format (one header row
  of field names, one row of values), so a file saved here can also be
  opened in a spreadsheet, edited by hand, and loaded back.
*/
(function () {
  const KEY = 'dwai_csv_library';
  const MAX_ENTRIES = 50;

  function readAll() {
    try {
      const raw = JSON.parse(localStorage.getItem(KEY) || '[]');
      return Array.isArray(raw) ? raw : [];
    } catch (e) {
      return [];
    }
  }

  function writeAll(list) {
    try {
      localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX_ENTRIES)));
      return true;
    } catch (e) {
      // Quota exhausted, or storage disabled. The caller still got its
      // download; say so rather than pretending the save worked.
      return false;
    }
  }

  /** Everything saved, newest first, optionally one shelf only. */
  function list(kind) {
    const all = readAll();
    return kind ? all.filter((e) => e.kind === kind) : all;
  }

  function get(id) {
    return readAll().find((e) => e.id === id) || null;
  }

  function remove(id) {
    const next = readAll().filter((e) => e.id !== id);
    writeAll(next);
    return next;
  }

  /* ---------------------------------------------------------------
     CSV encoding. Values are the user's own numbers and short strings,
     but a field could still contain a comma or a quote, so this quotes
     properly rather than assuming it never happens.
     --------------------------------------------------------------- */
  function escapeCell(value) {
    const s = value === null || value === undefined ? '' : String(value);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }

  /* `savedAt` becomes a real `date` column. Without it the file is a
     questionnaire with no day attached, and the bulk importer on the
     check-in page has nothing to file it under - which is exactly why
     a file exported from one account used to be refused by another.
     The date is the one the check-in was actually saved on, so the
     round-trip carries the real day rather than an assumed one. */
  function toCsv(payload, savedAt) {
    const keys = Object.keys(payload || {}).filter(
      (k) => typeof payload[k] !== 'object' || payload[k] === null,
    ).sort().filter((k) => k !== 'date');
    const day = isoDay(savedAt);
    const header = ['date'].concat(keys).map(escapeCell).join(',');
    const row = [day].concat(keys.map((k) => payload[k])).map(escapeCell).join(',');
    return `${header}\n${row}\n`;
  }

  function isoDay(value) {
    const d = value ? new Date(value) : new Date();
    const usable = Number.isFinite(d.getTime()) ? d : new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${usable.getFullYear()}-${pad(usable.getMonth() + 1)}-${pad(usable.getDate())}`;
  }

  /** Parse a one-row questionnaire CSV back into a payload object.
   *  Returns null when the shape is not what we wrote, rather than
   *  half-filling the form with garbage. */
  function fromCsv(text) {
    const lines = String(text || '').split(/\r?\n/).filter((l) => l.trim().length);
    if (lines.length < 2) return null;
    const header = splitCsvLine(lines[0]);
    const values = splitCsvLine(lines[1]);
    if (!header.length || header.length !== values.length) return null;
    const out = {};
    header.forEach((name, i) => {
      const raw = values[i];
      if (raw === '') return;
      const n = Number(raw);
      out[name] = Number.isFinite(n) && raw.trim() !== '' ? n : raw;
    });
    return Object.keys(out).length ? out : null;
  }

  function splitCsvLine(line) {
    const out = [];
    let cur = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i += 1) {
      const c = line[i];
      if (inQuotes) {
        if (c === '"' && line[i + 1] === '"') { cur += '"'; i += 1; }
        else if (c === '"') inQuotes = false;
        else cur += c;
      } else if (c === '"') inQuotes = true;
      else if (c === ',') { out.push(cur); cur = ''; }
      else cur += c;
    }
    out.push(cur);
    return out.map((s) => s.trim());
  }

  /* ---------------------------------------------------------------
     Save + download in one step. The download is the point - the list
     is only an index - so a storage failure still returns the file.
     --------------------------------------------------------------- */
  function save(name, payload, opts) {
    opts = opts || {};
    const clean = String(name || '').trim().slice(0, 60);
    if (!clean) return null;
    if (!payload || typeof payload !== 'object') return null;

    const entry = {
      id: `csv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      name: clean,
      kind: opts.excluded ? 'test' : 'main',
      savedAt: new Date().toISOString(),
      score: typeof opts.score === 'number' ? Math.round(opts.score) : null,
      payload,
    };
    const list_ = readAll();
    list_.unshift(entry);
    const stored = writeAll(list_);
    return { entry, stored };
  }

  function fileNameFor(entry) {
    const safe = entry.name.replace(/[^\w؀-ۿ一-鿿 -]+/g, '').trim() || 'check-in';
    return `${safe}.csv`;
  }

  function download(entry) {
    const blob = new Blob([toCsv(entry.payload, entry.savedAt)], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileNameFor(entry);
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  window.DWCsvLibrary = {
    list, get, save, remove, download, toCsv, fromCsv, fileNameFor,
    KEY, MAX_ENTRIES,
  };
})();
