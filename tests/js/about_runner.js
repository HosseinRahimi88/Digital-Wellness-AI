/*
  Loads the REAL About-page modules and dumps what they contain, so
  tests/frontend/test_about_page.py can check the content rather than a
  reimplementation of it.

  The three modules are written to run in a browser, so the sandbox
  below is the smallest thing they will start in: a DWI18n that can be
  pointed at a language, a document that swallows listeners, and the
  DWMotion/DWApi surfaces they touch at load time. Nothing here renders
  - init() is never called; the point is the DATA the modules carry.
*/
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..');
const JS = path.join(ROOT, 'frontend', 'assets', 'js');

let lang = 'en';
const sandbox = {
  console,
  window: {
    DWI18n: { get: () => lang, t: (k) => k, pick: (t) => (t && (t[lang] || t.en)) || '' },
    DWMotion: { prefersReduced: () => false, observeReveals() {}, countUp() {} },
    DWApi: { journalList: async () => ({ entries: [] }) },
    DWToast: { success() {}, error() {}, warning() {}, info() {} },
    DWSheet: { open() {}, close() {}, esc: (s) => String(s) },
  },
  document: {
    addEventListener() {},
    getElementById: () => null,
    querySelectorAll: () => [],
    querySelector: () => null,
    documentElement: { getAttribute: () => 'ltr' },
  },
  localStorage: { getItem: () => null, setItem() {} },
  getComputedStyle: () => ({ display: 'block' }),
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

for (const file of ['about/about-roadmap.js', 'about/about-team.js', 'about/about-journal.js']) {
  vm.runInContext(fs.readFileSync(path.join(JS, file), 'utf8'), sandbox, { filename: file });
}

const LANGS = ['en', 'fa', 'ar', 'zh'];

const head = sandbox.window.DWAboutRoadmap.HEAD;

const stations = sandbox.window.DWAboutRoadmap.STATIONS.map((s) => ({
  phase: s.phase,
  icon: s.icon,
  title: s.title,
  body: s.body,
  proof_label: s.proof && s.proof.label,
  proof_value: s.proof && s.proof.value,
  proof_num: s.proof && s.proof.num,
}));

const members = sandbox.window.DWAboutTeam.MEMBERS.map((m) => ({
  id: m.id,
  initials: m.initials,
  accent: m.accent,
  name: m.name,
  role: m.role,
  tagline: m.tagline,
  summary: m.summary,
  personal: m.personal || [],
  project: m.project || [],
  experience: m.experience || [],
  achievements: m.achievements || [],
  skills: m.skills,
  links: m.links,
}));

// The five panel headings the profile is built from. A panel with no
// heading in one of the four languages would render an empty bar.
const panels = sandbox.window.DWAboutTeam.PANELS;

// The journal module keeps its limits private, so they are read back
// out of the file text. They have to agree with the server's, and a
// test that reimplemented them would agree with nothing.
const journalSrc = fs.readFileSync(path.join(JS, 'about/about-journal.js'), 'utf8');
const maxLen = /const MAX_LEN = (\d+);/.exec(journalSrc);
const moods = [...journalSrc.matchAll(/\{ id: '([a-z]+)', glyph:/g)].map((m) => m[1]);

process.stdout.write(JSON.stringify({
  langs: LANGS,
  head,
  stations,
  members,
  panels,
  journal: {
    max_len: maxLen ? parseInt(maxLen[1], 10) : null,
    moods,
    has_init: typeof sandbox.window.DWAboutJournal.init === 'function',
  },
}, null, 2));
