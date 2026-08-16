/*
  Node-subprocess runner for connector-fit.js's describeError(), plus a
  regression check that coach.js's menu-item error path actually calls it
  instead of interpolating a raw internal ConnectorError message (the bug:
  a menu question asked while the connector was on and failing showed
  "Connector error: auth" / "Connector error: HTTP 500" - an untranslated,
  internal string - while the main chat box already had a proper
  per-kind, translated message for the exact same errors).

  Mirrors the pattern established by tests/js/games_eligibility_runner.js:
  stub window/localStorage, require() the real frontend files, exercise
  the real functions, print JSON, parse in Python.
*/
const path = require('path');

global.window = {};
global.localStorage = {
  data: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this.data, k) ? this.data[k] : null; },
  setItem(k, v) { this.data[k] = String(v); },
};

const FRONTEND = path.join(__dirname, '..', '..', 'frontend', 'assets', 'js');

window.DWI18n = {
  _lang: 'en',
  get() { return this._lang; },
  pick(t) { return (t && (t[this._lang] || t.en)) || ''; },
};

require(path.join(FRONTEND, 'coach/connector.js'));
require(path.join(FRONTEND, 'coach/connector-fit.js'));

const ERRORS = window.DWConnector.ERRORS;

function mkErr(kind, message) {
  const e = new Error(message || kind);
  e.kind = kind;
  return e;
}

const cases = [
  { label: 'auth', err: mkErr(ERRORS.AUTH, 'auth') },
  { label: 'quota', err: mkErr(ERRORS.QUOTA, 'quota') },
  { label: 'network', err: mkErr(ERRORS.NETWORK, 'network') },
  { label: 'timeout', err: mkErr(ERRORS.TIMEOUT, 'timeout') },
  { label: 'provider', err: mkErr(ERRORS.PROVIDER, 'HTTP 500') },
  { label: 'rate', err: mkErr(ERRORS.QUOTA, 'rate:37') },
  { label: 'null', err: null },
];

const out = {};
['en', 'fa', 'ar', 'zh'].forEach((lang) => {
  window.DWI18n._lang = lang;
  out[lang] = {};
  cases.forEach((c) => {
    out[lang][c.label] = window.DWConnectorFit.describeError(c.err);
  });
});

// Regression pin: coach.js's error path must route through describeError,
// never interpolate a raw ConnectorError message directly.
const fs = require('fs');
const coachSrc = fs.readFileSync(path.join(FRONTEND, 'coach/coach.js'), 'utf8');
out._static = {
  usesDescribeError: coachSrc.includes('DWConnectorFit.describeError(e)'),
  noRawConnectorErrorTemplate: !/connectorError:\s*\(m\)/.test(coachSrc),
};

console.log(JSON.stringify(out));
