"""What a whole-project sweep turned up, and the fixes for it.

The sweep loaded all 13 pages in all 4 languages (52 page-loads) in a
real browser and recorded JS errors, failed requests, layout overflow,
broken internal links, unfilled placeholders and visible English on a
non-English page.

Clean: 0 JS errors, 0 failed requests, 0 horizontal overflow, 0 broken
links. The findings were all translation, and two of them were real:

  1. THE ENTIRE SETTINGS PANEL was English in every language, on every
     page. Not for want of translations - all fifteen strings had a
     [data-i18n] key and all four languages already existed. The panel
     is injected into document.body by app-chrome.js AFTER DWI18n has
     already walked the document, and nothing re-applied i18n to the new
     subtree. It is reachable from every page, which made it the single
     most visible untranslated surface in the app, and it was invisible
     to a key-coverage test because the keys were all present.

  2. THE ONBOARDING AND PROFILE PICKERS - goal, purpose and schedule,
     about twenty options - were English in all four languages. Their
     English strings are the keys of a label->value map, and the value
     is what gets submitted, so the display text had simply never been
     separated from the identifier.

Also fixed: a duplicated `settings_reduce_motion` key in the English
dictionary. Same value both times so nothing was visibly wrong, but the
later definition silently wins, so editing the first one would have had
no effect and no error.

Run: python3 -m unittest tests.frontend.test_debug_sweep_fixes -v
"""
from __future__ import annotations

import collections
import re
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

REPO_ROOT = paths.PROJECT_ROOT
FRONTEND = REPO_ROOT / "frontend"
JS = FRONTEND / "assets" / "js"

SETTINGS_KEYS = [
    "settings_title", "settings_theme", "settings_music", "settings_soundfx",
    "settings_reduce_motion", "settings_games", "settings_guide_title",
    "settings_guide_on", "settings_guide_voice", "settings_tour",
    "settings_tour_btn", "settings_demo_mode", "settings_demo_btn",
    "settings_league", "settings_league_btn",
]

SCRIPTS = {
    "fa": re.compile(r"[؀-ۿ]"),
    "ar": re.compile(r"[؀-ۿ]"),
    "zh": re.compile(r"[一-鿿]"),
}

# Platform brands that Chinese writing genuinely keeps in Latin script.
# Persian and Arabic transliterate brand names into their own scripts
# (اینستاگرام / إنستغرام), so they are still held to the normal rule;
# Chinese does not, and forcing a Han-script string here would make the
# picker *less* correct, not more:
#
#   - TikTok is the clearest case. 抖音 is a SEPARATE app for the
#     mainland Chinese market, not a translation - writing it here would
#     name the wrong product.
#   - The rest simply have no established Chinese-language form; Chinese
#     text about them uses the Latin brand.
#
# Deliberately narrow: it applies to zh only, and only to these exact
# values. Platforms that DO have a real Chinese name are not in this set
# and are still required to use it - LinkedIn (领英), RedNote (小红书),
# X (推特) and Facebook (脸书) are all checked by the normal rule above,
# so this exemption cannot quietly grow into "Chinese is optional".
LATIN_IN_CHINESE = {
    "Instagram", "TikTok", "YouTube", "Snapchat", "WhatsApp", "Telegram",
    "Reddit", "Discord", "Pinterest", "Threads", "Bluesky",
}


class TestTheSettingsPanelIsTranslated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chrome = (JS / "chrome/app-chrome.js").read_text(encoding="utf-8")
        cls.i18n = (JS / "core/i18n.js").read_text(encoding="utf-8")

    def test_the_injected_panel_gets_i18n_applied_to_it(self):
        # The fix. Without this line every [data-i18n] inside the modal
        # keeps its English fallback forever.
        idx = self.chrome.index("function ensureSettingsModal")
        body = self.chrome[idx:idx + 900]
        self.assertIn("localise(modal)", body)
        self.assertIn("document.body.appendChild(modal)", body)
        self.assertLess(
            body.index("appendChild(modal)"), body.index("localise(modal)"),
            "i18n is applied before the node is in the document",
        )

    def test_it_keeps_translating_when_the_language_changes(self):
        # The panel is built once and left in the DOM, so a one-shot
        # translation would freeze it at whichever language was active
        # when it was first opened.
        idx = self.chrome.index("function localise")
        body = self.chrome[idx:idx + 600]
        self.assertIn("dwai:langchange", body)
        self.assertIn("applyToDom(node)", body)
        self.assertIn("isConnected", body)

    def test_every_settings_string_has_a_key(self):
        for key in SETTINGS_KEYS:
            with self.subTest(key=key):
                self.assertIn(f'data-i18n="{key}"', self.chrome)

    def test_every_settings_key_exists_exactly_once_per_language(self):
        for key in SETTINGS_KEYS:
            with self.subTest(key=key):
                found = len(re.findall(rf"(?:^|[\s{{,]){key}:", self.i18n, re.MULTILINE))
                self.assertEqual(
                    found, 4,
                    f"{key} appears {found} time(s); expected exactly one per language",
                )

    def test_no_key_is_defined_twice_in_the_same_dictionary(self):
        # A duplicate is silent: the later definition wins, so editing
        # the earlier one does nothing and reports nothing.
        blocks = re.split(r"\n  (en|fa|ar|zh):\s*\{", self.i18n)
        dupes = {}
        for i in range(1, len(blocks), 2):
            lang, body = blocks[i], blocks[i + 1]
            keys = re.findall(r"(?:^|[\s{,])([a-z][a-z0-9_]{2,}):\s*['\"]", body)
            repeated = [k for k, n in collections.Counter(keys).items() if n > 1]
            if repeated:
                dupes[lang] = repeated
        self.assertEqual(dupes, {}, f"duplicate keys: {dupes}")


class TestTheOnboardingPickersAreTranslated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.opts = (JS / "features/onboarding-options.js").read_text(encoding="utf-8")
        cls.app = (JS / "pages/app.js").read_text(encoding="utf-8")
        cls.profile = (JS / "pages/profile.js").read_text(encoding="utf-8")

    def test_every_stored_value_has_a_label_in_four_languages(self):
        # Pull the value->label table and the three value maps, and
        # check nothing selectable is missing its display text.
        table = self.opts[self.opts.index("const OPTION_LABELS"):self.opts.index("function labelFor")]
        labelled = set(re.findall(r"^\s{4}(\w+):\s*\{", table, re.MULTILINE))
        values = set(re.findall(r":\s*'([a-z_]+)'", self.opts[:self.opts.index("const OPTION_LABELS")]))
        missing = values - labelled
        self.assertEqual(missing, set(), f"options with no translated label: {missing}")
        for value in labelled:
            with self.subTest(value=value):
                idx = table.index(f"{value}: {{")
                entry = table[idx:idx + 400]
                for lang in ("en:", "fa:", "ar:", "zh:"):
                    self.assertIn(lang, entry)

    def test_no_label_was_left_as_the_english_string(self):
        table = self.opts[self.opts.index("const OPTION_LABELS"):self.opts.index("function labelFor")]
        for value in re.findall(r"^\s{4}(\w+):\s*\{", table, re.MULTILINE):
            idx = table.index(f"{value}: {{")
            entry = table[idx:table.index("},", idx)]
            en = re.search(r"en:\s*'([^']*)'|en:\s*\"([^\"]*)\"", entry)
            self.assertTrue(en)
            english = en.group(1) or en.group(2)
            for lang, pattern in SCRIPTS.items():
                m = re.search(rf"{lang}:\s*'([^']*)'|{lang}:\s*\"([^\"]*)\"", entry)
                text = (m.group(1) or m.group(2)) if m else ""
                if value in LATIN_IN_CHINESE and lang == "zh":
                    # Asserted the other way round: these must stay the
                    # Latin brand, because inventing a Chinese form would
                    # be wrong, not thorough. See LATIN_IN_CHINESE.
                    with self.subTest(value=value, lang=lang):
                        self.assertEqual(text, english)
                    continue
                with self.subTest(value=value, lang=lang):
                    self.assertNotEqual(text, english)
                    self.assertRegex(text, pattern)

    def test_the_submitted_value_is_never_the_translated_text(self):
        # The whole hazard of translating these: if the display text
        # became the identifier, changing language would change what the
        # backend and the model receive.
        for name, src in (("pages/app.js", self.app), ("pages/profile.js", self.profile)):
            with self.subTest(file=name):
                self.assertIn("labelFor(value", src)
                self.assertIn("dataset.optionValue = value", src)

    def test_restoring_a_saved_choice_does_not_match_on_display_text(self):
        # It used to look the value up by the element's textContent,
        # which stops being the English key the moment it is translated.
        idx = self.app.index("buildOptionList($('#goalOptions')")
        body = self.app[idx:idx + 700]
        self.assertIn("dataset.optionValue === match", body)
        self.assertNotIn("GOAL_OPTIONS[o.textContent]", body)

    def test_the_value_maps_still_match_the_backend(self):
        # These values are stored and read by config/onboarding_options.py;
        # a drift here would silently reject a saved profile.
        import config.onboarding_options as backend

        for js_name, py_name in (("GOAL_OPTIONS", "GOAL_OPTIONS"),
                                 ("PURPOSE_OPTIONS", "PURPOSE_OPTIONS"),
                                 ("SCHEDULE_OPTIONS", "SCHEDULE_OPTIONS")):
            with self.subTest(map=js_name):
                start = self.opts.index(f"const {js_name} = {{")
                block = self.opts[start:self.opts.index("};", start)]
                js_values = set(re.findall(r":\s*'([a-z_]+)'", block))
                py_values = set(getattr(backend, py_name).values())
                self.assertEqual(js_values, py_values)


if __name__ == "__main__":
    unittest.main()
