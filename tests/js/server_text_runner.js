/*
  Exercises the real frontend/assets/js/core/server-text.js under node, same
  pattern as the other runners here: stub window, require() the shipped
  file, print one JSON blob.
*/
const path = require('path');

const FRONTEND = path.join(__dirname, '..', '..', 'frontend', 'assets', 'js');

let currentLang = 'en';
global.window = { DWI18n: { get: () => currentLang } };

require(path.join(FRONTEND, 'core/server-text.js'));
const T = window.DWServerText;

const full = {
  message: 'english flat',
  text_i18n: { message: { en: 'hello', fa: 'سلام', zh: '你好' } },
};

const out = {};

currentLang = 'fa';
out.picksFa = T.pick(full, 'message');

currentLang = 'zh';
out.picksZh = T.pick(full, 'message');

// Arabic is absent from this payload -> English, not blank.
currentLang = 'ar';
out.missingLangFallsToEnglish = T.pick(full, 'message');

// An empty string is present but useless; English must still win.
out.emptyTranslationFallsToEnglish = T.pick(
  { message: 'flat', text_i18n: { message: { en: 'hello', ar: '' } } }, 'message',
);

// A response from before text_i18n existed.
out.olderResponse = T.pick({ message: 'legacy english' }, 'message');

// None of these may ever reach the page as "[object Object]" or "undefined".
out.nullPayload = T.pick(null, 'message');
out.emptyPayload = T.pick({}, 'message');
out.unknownPart = T.pick(full, 'no_such_part');

out.typesSeen = [...new Set([
  typeof out.picksFa, typeof out.missingLangFallsToEnglish,
  typeof out.olderResponse, typeof out.nullPayload,
  typeof out.emptyPayload, typeof out.unknownPart,
])].join(',');

console.log(JSON.stringify(out));
