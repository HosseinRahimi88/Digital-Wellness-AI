/*
  Loads the REAL frontend files and asks DWCoachSuggestions for the
  two-section answer, in all four languages, against plan tracks shaped
  exactly like the ones services/wellness/improvement_plan_service.py returns.

  Run by tests/coach/test_coach_suggestions.py.
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
    DWI18n: {
      get: () => lang,
      pick: (table) => (table && (table[lang] || table.en)) || '',
    },
    // The real label table, loaded below, replaces this.
    DWCoachLabels: null,
  },
  document: { addEventListener() {}, querySelectorAll: () => [] },
  localStorage: { getItem: () => null, setItem() {} },
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

for (const file of ['coach/coach-labels.js', 'coach/coach-suggestions.js']) {
  vm.runInContext(fs.readFileSync(path.join(JS, file), 'utf8'), sandbox, { filename: file });
}

// Plan tracks in the server's own shape. Two strengthen, two maintain,
// with real field names and real numbers.
const TRACKS = {
  strengthen: [
    {
      field: 'sleep_hours', theme: 'Sleep Recovery', icon: '😴',
      current: 5.4, target: 7.5, lower_is_better: false, severity: 0.61,
      theme_i18n: { en: 'Sleep Recovery', fa: 'بازیابی خواب', ar: 'استعادة النوم', zh: '睡眠恢复' },
    },
    {
      field: 'notifications_per_day', theme: 'Mindful Notifications', icon: '🔔',
      current: 180, target: 60, lower_is_better: true, severity: 0.48,
      theme_i18n: { en: 'Mindful Notifications', fa: 'اعلان‌های آگاهانه', ar: 'إشعارات واعية', zh: '有意识的通知' },
    },
  ],
  maintain: [
    {
      field: 'physical_activity_min_per_day', theme: 'Movement', icon: '🏃',
      current: 55, target: 30, lower_is_better: false, margin: 0.83,
      theme_i18n: { en: 'Movement', fa: 'تحرک', ar: 'الحركة', zh: '运动' },
    },
    {
      field: 'stress_0_10', theme: 'Stress Reset', icon: '🧘',
      current: 2.0, target: 4.0, lower_is_better: true, margin: 0.5,
      theme_i18n: { en: 'Stress Reset', fa: 'بازنشانی استرس', ar: 'إعادة ضبط التوتر', zh: '压力重置' },
    },
  ],
};

const out = { languages: {}, ideaBank: {} };

for (const l of ['en', 'fa', 'ar', 'zh']) {
  lang = l;
  out.languages[l] = {
    full: sandbox.window.DWCoachSuggestions.build(TRACKS, { seed: 0 }),
    noMaintain: sandbox.window.DWCoachSuggestions.build(
      { strengthen: TRACKS.strengthen, maintain: [] }, { seed: 0 }),
    noStrengthen: sandbox.window.DWCoachSuggestions.build(
      { strengthen: [], maintain: TRACKS.maintain }, { seed: 0 }),
    rotated: sandbox.window.DWCoachSuggestions.build(TRACKS, { seed: 1 }),
    missing: sandbox.window.DWCoachSuggestions.build(null),
  };
}

lang = 'en';
const bank = sandbox.window.DWCoachSuggestions.IDEAS;
for (const field of Object.keys(bank)) {
  out.ideaBank[field] = {};
  for (const half of Object.keys(bank[field])) {
    out.ideaBank[field][half] = bank[field][half].map((idea) =>
      ['en', 'fa', 'ar', 'zh'].filter((l) => !idea[l] || !String(idea[l]).trim()));
  }
}

console.log(JSON.stringify(out));
