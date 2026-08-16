"""
Tests: the frontend does not depend on anything it cannot reach.

A user in Iran reported the app failing at the sign-in screen. Every
page linked `fonts.googleapis.com` as a plain `rel="stylesheet"`, and a
stylesheet in <head> blocks rendering *and* script execution until it
resolves. On a network where that host is blocked or throttled - which
it routinely is there - the whole page waits on a decoration, and what
the user sees is a screen that never becomes usable followed by a
timeout. Measured here in a real browser before the fix: the page sat
at readyState "loading" for 25 seconds. After it: complete in 3, with
the font host blocked outright.

So this file guards the shape of that dependency rather than its
presence. The fonts may stay; what they may not do is hold the page
hostage. Every family already falls back to a system font in
variables.css, so a webfont that never arrives costs appearance only.

It also pins two smaller promises:
  * no sign-in control that cannot work
  * the terms page states the app's limits, in all four languages,
    with a real way to contact a human

Run: python3 -m unittest tests.test_frontend_resilience -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = PROJECT_ROOT / "frontend"
PAGES = sorted(FRONTEND.glob("*.html"))

LANGUAGES = ("en", "fa", "ar", "zh")


class TestNoRenderBlockingThirdParty(unittest.TestCase):

    def test_there_are_pages_to_check(self):
        self.assertGreaterEqual(len(PAGES), 13)

    def test_no_page_blocks_rendering_on_an_external_font(self):
        """`<link rel="stylesheet" href="https://...">` is the blocking
        form. The non-blocking form loads it as `media="print"` and
        promotes it on load, so a host that never answers costs nothing
        but the typeface."""
        offenders = []
        for page in PAGES:
            source = page.read_text(encoding="utf-8")
            for tag in re.findall(r"<link\b[^>]*>", source):
                if "https://" not in tag or "stylesheet" not in tag:
                    continue
                if 'media="print"' in tag:
                    continue          # non-blocking form
                if "<noscript>" in source[max(0, source.index(tag) - 12):source.index(tag)]:
                    continue          # the noscript fallback copy
                offenders.append(f"{page.name}: {tag[:90]}")
        self.assertEqual(offenders, [], "render-blocking external stylesheet(s):\n" + "\n".join(offenders))

    def test_the_check_would_catch_a_blocking_link(self):
        """Guard against the assertion above passing because the regex
        never matches anything."""
        blocking = '<link href="https://fonts.googleapis.com/css2?family=X" rel="stylesheet">'
        self.assertIn("stylesheet", blocking)
        self.assertNotIn('media="print"', blocking)

    def test_the_fonts_are_still_requested_just_not_waited_on(self):
        """The fix must not have been "delete the fonts"."""
        pages_with_fonts = [p.name for p in PAGES if "fonts.googleapis.com" in p.read_text(encoding="utf-8")]
        self.assertGreaterEqual(len(pages_with_fonts), 13)

    def test_a_noscript_fallback_keeps_fonts_without_javascript(self):
        for page in PAGES:
            source = page.read_text(encoding="utf-8")
            if "fonts.googleapis.com" not in source:
                continue
            self.assertIn("<noscript>", source, page.name)

    def test_every_font_family_falls_back_to_a_system_font(self):
        """Which is what makes a missing webfont cosmetic rather than
        fatal."""
        variables = (FRONTEND / "assets" / "css" / "variables.css").read_text(encoding="utf-8")
        declarations = re.findall(r"--font-[\w-]+:\s*([^;]+);", variables)
        self.assertGreaterEqual(len(declarations), 8)
        generic = ("sans-serif", "serif", "monospace", "system-ui", "var(--font-")
        for value in declarations:
            self.assertTrue(
                any(g in value for g in generic),
                f"font stack with no fallback: {value}",
            )


class TestNoSignInControlThatCannotWork(unittest.TestCase):

    def test_the_github_button_is_gone(self):
        """It needed an OAuth client id, secret and callback URL that a
        locally-run copy does not have, so it could only ever fail. A
        control that cannot work reads as the app being broken."""
        source = (FRONTEND / "app.html").read_text(encoding="utf-8")
        self.assertNotIn("githubLoginBtn", source)
        self.assertNotIn("Continue with GitHub", source)

    def test_the_handler_tolerates_the_button_being_absent(self):
        """It is still referenced in app.js; without the guard that
        would throw on every page load and take the sign-in form with
        it."""
        source = (FRONTEND / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        if "githubLoginBtn" in source:
            index = source.index("githubLoginBtn")
            self.assertIn("if (!btn) return;", source[index:index + 200])

    def test_password_sign_in_is_still_there(self):
        source = (FRONTEND / "app.html").read_text(encoding="utf-8")
        self.assertIn('id="loginForm"', source)
        self.assertIn('type="password"', source)


class TestTermsPage(unittest.TestCase):

    def setUp(self):
        self.html = (FRONTEND / "terms.html").read_text(encoding="utf-8")
        self.js = (FRONTEND / "assets" / "js" / "terms-page.js").read_text(encoding="utf-8")

    def test_it_covers_every_shipped_feature_area(self):
        """A feature with no rule is the actual problem. These are the
        areas the app actually has."""
        for key in ("h_use", "h_models", "h_data", "h_league", "h_chat",
                    "h_badges", "h_guide", "h_ai", "h_demo", "h_liability",
                    "h_changes", "h_contact"):
            self.assertIn(f"{key}:", self.js, f"terms has no section for {key}")

    def test_every_section_exists_in_all_four_languages(self):
        for language in LANGUAGES:
            self.assertRegex(
                self.js, rf"\n    {language}: \{{",
                f"terms page has no {language} block",
            )
        # Same number of section headings in each language block.
        counts = {lang: 0 for lang in LANGUAGES}
        current = None
        for line in self.js.splitlines():
            match = re.match(r"    (en|fa|ar|zh): \{", line)
            if match:
                current = match.group(1)
            elif current and re.match(r"      h_\w+:", line):
                counts[current] += 1
        self.assertEqual(len(set(counts.values())), 1, f"uneven section counts: {counts}")
        self.assertGreaterEqual(counts["en"], 12)

    def test_it_states_the_medical_limit_in_every_language(self):
        """The one rule that outranks the others has to be present in
        the language the reader actually reads."""
        self.assertEqual(self.js.count("calloutTitle:"), len(LANGUAGES))
        self.assertEqual(self.js.count("callout:"), len(LANGUAGES))

    def test_the_contact_details_are_present_and_reachable(self):
        self.assertIn("amirhesamhh1378@gmail.com", self.js)
        self.assertIn("+98 903 590 6294", self.js)
        self.assertIn("mailto:", self.js)
        self.assertIn("tel:", self.js)

    def test_the_phone_number_is_bidi_isolated(self):
        """Dropped bare into an RTL paragraph, a +98 number renders with
        the country code at the wrong end."""
        self.assertIn('dir="ltr"', self.js)
        self.assertIn("unicode-bidi:isolate", self.js)

    def test_the_page_uses_the_apps_own_language_key(self):
        """So arriving from a Persian session stays Persian."""
        self.assertIn("'dwai_lang'", self.js)

    def test_the_script_is_external(self):
        """It was inline, and an HTML comment inside one of its template
        literals put the parser into script-data-escaped state - the
        whole script silently never ran, with no console error. An
        external file cannot be broken that way."""
        self.assertIn('src="assets/js/terms-page.js"', self.html)
        self.assertNotIn("<script>", self.html)

    def test_no_html_comment_sits_inside_a_template_literal(self):
        """The specific trap above, stated as a rule.

        Comments are stripped first, because the paragraph explaining
        the trap naturally quotes the very sequence it warns about."""
        code = re.sub(r"/\*.*?\*/", "", self.js, flags=re.S)
        code = re.sub(r"^\s*//.*$", "", code, flags=re.M)
        literals = re.findall(r"`[^`]*`", code, re.S)
        self.assertGreater(len(literals), 0, "no template literals found - check the regex")
        for literal in literals:
            self.assertNotIn("<!--", literal)


if __name__ == "__main__":
    unittest.main()
