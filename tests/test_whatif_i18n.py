"""
Tests: the What-if simulator's results are translated.

frontend/assets/js/whatif.js built its two result blocks - the sweep
note and the goal-seek metrics - from hardcoded English string
literals. The field dropdown was already localised, which is what made
this easy to miss: the page looked translated until you actually ran a
sweep, and then answered you in English in every language.

Checked against the real files:
  1. No user-visible English literal is left in whatif.js.
  2. Every i18n key the file uses exists in all four languages in
     i18n.js - a key that resolves to itself renders as the raw key
     name on screen.
  3. The results re-render on `dwai:langchange`, and listen on the
     object i18n.js actually dispatches from. That last part is not
     pedantry: the event is dispatched on `document` without `bubbles`,
     so a `window` listener is never called at all, and the page would
     keep the old language after a switch while looking correctly
     wired.

Run: python3 -m unittest tests.test_whatif_i18n -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import tests._test_support as ts  # noqa: F401 - sys.path bootstrap

REPO_ROOT = Path(__file__).resolve().parents[1]
JS = REPO_ROOT / "frontend" / "assets" / "js"
WHATIF = JS / "whatif.js"
I18N = JS / "i18n.js"

LANGS = ("en", "fa", "ar", "zh")


def _keys_defined_per_language() -> dict[str, set[str]]:
    """Which i18n keys each language block defines."""
    text = I18N.read_text(encoding="utf-8")
    # The language blocks are not all indented identically, so anchor on
    # the newline and allow any leading indent - a fixed two-space
    # pattern silently matches nothing and every check below passes
    # vacuously against empty key sets.
    blocks = re.split(r"\n\s{0,6}(en|fa|ar|zh):\s*\{", text)
    out: dict[str, set[str]] = {}
    for i in range(1, len(blocks), 2):
        lang, body = blocks[i], blocks[i + 1]
        out.setdefault(lang, set()).update(
            re.findall(r"(?:^|[\s{,])([a-z][a-z0-9_]{2,}):\s*['\"]", body)
        )
    return out


class TestWhatIfIsTranslated(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = WHATIF.read_text(encoding="utf-8")
        cls.defined = _keys_defined_per_language()

    def test_no_hardcoded_english_left_in_the_results(self):
        """Any English prose assigned to the DOM, not just bare words.

        Written carefully because the obvious version does not work: the
        original offender was

            wrap.innerHTML = '<p class="muted">Could not find a value…</p>'

        and a naive `['\"`][^'\"`]*` body stops dead at the double quote
        inside class="muted", so the prose after it is never examined and
        the real bug passes. This instead takes the whole literal, strips
        the HTML tags and ${…} interpolations, and looks at the text that
        would actually be rendered.
        """
        offenders = []
        for m in re.finditer(r"(?:textContent|innerHTML)\s*=\s*", self.src):
            i = m.end()
            if i >= len(self.src) or self.src[i] not in "'\"`":
                continue  # assigned from a variable or call, not a literal
            quote = self.src[i]
            j, buf = i + 1, []
            while j < len(self.src):
                if self.src[j] == "\\":
                    j += 2
                    continue
                if self.src[j] == quote:
                    break
                buf.append(self.src[j])
                j += 1
            literal = "".join(buf)
            visible = re.sub(r"\$\{[^}]*\}", " ", literal)   # interpolations
            visible = re.sub(r"<[^>]*>", " ", visible)        # tags + attributes
            # Two consecutive English words is prose; a lone "muted" or
            # "value" left over from markup is not.
            if re.search(r"[A-Za-z]{3,}\s+[A-Za-z]{3,}", visible):
                offenders.append(visible.strip())
        self.assertEqual(
            offenders, [],
            f"hardcoded English prose is still assigned to the DOM in whatif.js: {offenders}",
        )

    def test_every_key_it_uses_exists_in_all_four_languages(self):
        # The `t(` must be the whole function name, not the tail of
        # another one - `react('neutral')`, `init('whatif')` and
        # `createElement('option')` all end in "t(" and would otherwise
        # be mistaken for translation keys.
        used = set(re.findall(r"(?<![A-Za-z_])t\('([a-z][a-z0-9_]{2,})'\)", self.src))
        self.assertTrue(used, "no i18n keys found in whatif.js at all")
        for lang in LANGS:
            missing = sorted(used - self.defined.get(lang, set()))
            with self.subTest(lang=lang):
                self.assertEqual(
                    missing, [],
                    f"whatif.js uses keys missing from the {lang} block: {missing}",
                )

    def test_the_class_names_are_translated_too(self):
        # The server returns "Healthy"/"At Risk" in English; printing
        # those raw is the same bug one layer down.
        for key in ("cls_healthy", "cls_moderate", "cls_at_risk"):
            with self.subTest(key=key):
                self.assertIn(key, self.src)
                for lang in LANGS:
                    self.assertIn(key, self.defined.get(lang, set()), f"{key} missing from {lang}")

    def test_results_are_rerendered_on_a_language_change(self):
        self.assertIn("dwai:langchange", self.src)
        self.assertIn("renderSweepNote", self.src)
        self.assertIn("renderGoalSeek", self.src)

    def test_it_listens_on_the_object_the_event_is_dispatched_from(self):
        # i18n.js: document.dispatchEvent(new CustomEvent('dwai:langchange'...))
        # with no bubbles, so window.addEventListener never fires.
        i18n_src = I18N.read_text(encoding="utf-8")
        self.assertIn("document.dispatchEvent(new CustomEvent('dwai:langchange'", i18n_src)
        self.assertNotIn(
            "window.addEventListener('dwai:langchange'", self.src,
            "whatif.js listens on window, but the event is dispatched on document "
            "without bubbling - the handler would never run",
        )
        self.assertIn("document.addEventListener('dwai:langchange'", self.src)

    def test_a_language_switch_does_not_refetch_from_the_model(self):
        # Re-running the sweep on every language change would re-POST to
        # the model. The handler must render from the cached response.
        handler = self.src[self.src.index("document.addEventListener('dwai:langchange'"):]
        handler = handler[: handler.index("async function runSweep")]
        for forbidden in ("whatifSweep", "whatifGoalSeek", "runSweep("):
            self.assertNotIn(
                forbidden, handler,
                f"the langchange handler calls {forbidden}; it should re-render "
                "from the cached response instead",
            )


if __name__ == "__main__":
    unittest.main()
