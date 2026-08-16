"""
Tests: every click in the app resolves to something the guide can say.

guide-click.js turns any click into a guide line by walking outward from
the clicked node through a fixed chain of rules. That chain is only as
good as three things it cannot check itself, so they are checked here:

  1. **Dead selectors.** The control table names real ids and attributes
     from the markup (`[data-lang-select]`, `#wizardNext`, ...). Rename
     one in the HTML and the resolver does not error - it silently falls
     through to the page overview, so every control on the page starts
     giving the same generic answer. Nothing in the browser would report
     that. Here it is a failing test.

  2. **Topics with no copy.** A rule can point at `ctl_music` before
     anyone writes `ctl_music`. explain() returns false for a missing
     topic, which again degrades to silence rather than an error.

  3. **Pages that never load the layer.** The script has to be on every
     page, or click coverage is "complete" on eleven pages and absent on
     the twelfth - which is the exact inconsistency the feature exists
     to remove.

The badge half of the requirement is checked the same way: every surface
that renders a badge must mark it with `data-badge-id`, because that
attribute is the entire contract between a badge tile and the guide.

Run standalone:
    python3 -m unittest tests.test_guide_click_coverage -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = PROJECT_ROOT / "frontend"
JS_DIR = FRONTEND / "assets" / "js"

CLICK_JS = JS_DIR / "guide-click.js"
CONTROLS_JS = JS_DIR / "guide-content-controls.js"

LANGUAGES = ("en", "fa", "ar", "zh")

# Pages that carry the app shell. terms.html is deliberately excluded:
# it is a standalone static document with no scripts, no mascot and no
# i18n at all, so there is nothing for the click layer to attach to.
SHELL_PAGES = sorted(
    p for p in FRONTEND.glob("*.html") if p.name != "terms.html"
)


def _control_table() -> list[tuple[str, str]]:
    """The [selector, topic] pairs, read out of the JS source itself so
    the test cannot drift from the thing it is testing."""
    source = CLICK_JS.read_text(encoding="utf-8")
    body = source[source.index("const CONTROL_TOPICS = ["):]
    body = body[: body.index("\n  ];")]
    return re.findall(r"\['([^']+)',\s*'([^']+)'\]", body)


def _page_fallbacks() -> dict[str, str]:
    source = CLICK_JS.read_text(encoding="utf-8")
    body = source[source.index("const PAGE_OF_FILE = {"):]
    body = body[: body.index("\n  };")]
    return dict(re.findall(r"'([^']*)':\s*'([^']+)'", body))


def _registered_topics() -> set[str]:
    """Every topic key the guide can speak: the core TIPS table plus
    everything any guide-content-*.js registers."""
    topics: set[str] = set()

    tips = (JS_DIR / "guide-tips.js").read_text(encoding="utf-8")
    block = tips[tips.index("const TIPS = {"): tips.index("const PAGE_TOURS = {")]
    for match in re.finditer(r"^    en:\s*\{", block, re.M):
        start = match.end()
        depth, i = 1, start
        while depth:
            if block[i] == "{":
                depth += 1
            elif block[i] == "}":
                depth -= 1
            i += 1
        topics |= set(re.findall(r"^      ([A-Za-z_]\w*)\s*:", block[start:i], re.M))

    for path in JS_DIR.glob("guide-content-*.js"):
        source = path.read_text(encoding="utf-8")
        topics |= set(re.findall(r"^    ([A-Za-z_]\w*)\s*:\s*\{", source, re.M))

    return topics


def _selector_alternatives(selector: str) -> list[str]:
    return [part.strip() for part in selector.split(",") if part.strip()]


def _markup() -> str:
    """Every piece of markup a user can actually click.

    The pages, plus app-chrome.js's settings-panel template. That
    template IS markup - it is the only definition of the settings
    panel now that app.html's hardcoded duplicate has gone, and the
    duplicate is exactly why it went: ensureSettingsModal() reuses any
    #settingsModal it finds, so the stale copy silently won and the
    Digital guide switches were unreachable from the check-in page.
    Scanning only .html files would now report the tour and guide
    controls as missing when they are simply built at runtime.
    """
    parts = [p.read_text(encoding="utf-8") for p in SHELL_PAGES]
    chrome = FRONTEND / "assets" / "js" / "app-chrome.js"
    if chrome.exists():
        text = chrome.read_text(encoding="utf-8")
        start = text.find("function modalTemplate()")
        end = text.find("function ensureSettingsModal")
        if start != -1 and end > start:
            parts.append(text[start:end])
    return "\n".join(parts)


def _selector_present(alternative: str, markup: str) -> bool:
    """Does anything in the shipped HTML match this simple selector?

    Only the shapes the control table actually uses are supported - id,
    class, attribute, tag, and attribute-with-value. Anything more
    elaborate would need a real parser, and the table is kept simple
    precisely so this stays checkable.
    """
    alternative = alternative.strip()
    if alternative.startswith("#"):
        return f'id="{alternative[1:]}"' in markup
    if alternative.startswith("."):
        return re.search(rf'class="[^"]*\b{re.escape(alternative[1:])}\b', markup) is not None
    attr = re.fullmatch(r"(\w*)\[([\w-]+)(?:([~*^$]?)=\"?([^\]\"]*)\"?)?\]", alternative)
    if attr:
        name, operator, value = attr.group(2), attr.group(3), attr.group(4)
        if not value:
            # Bare presence, e.g. [data-logout].
            return re.search(rf"\b{re.escape(name)}\b(?==|[\s>/])", markup) is not None
        for raw in re.findall(rf'{re.escape(name)}="([^"]*)"', markup):
            if operator == "*" and value in raw:
                return True
            if operator == "^" and raw.startswith(value):
                return True
            if operator == "$" and raw.endswith(value):
                return True
            if operator == "" and raw == value:
                return True
        return False
    if re.fullmatch(r"\w+", alternative):
        return re.search(rf"<{alternative}\b", markup) is not None
    return False


class TestControlTable(unittest.TestCase):

    def setUp(self):
        self.table = _control_table()
        self.topics = _registered_topics()

    def test_the_table_is_not_empty(self):
        """A vacuous pass here would make every other test in the class
        trivially true."""
        self.assertGreater(len(self.table), 10)

    def test_every_control_topic_has_copy(self):
        for selector, topic in self.table:
            self.assertIn(topic, self.topics, f"{selector} points at unwritten topic {topic}")

    def test_every_control_selector_matches_real_markup(self):
        markup = _markup()
        for selector, topic in self.table:
            alternatives = _selector_alternatives(selector)
            self.assertTrue(
                any(_selector_present(a, markup) for a in alternatives),
                f"none of {alternatives} ({topic}) exists in any page - clicks fall through to the page topic",
            )

    def test_the_selector_checker_is_not_vacuous(self):
        """The check above is worthless if _selector_present returns True
        for anything, so prove it says no to something absent."""
        self.assertFalse(_selector_present("#thisIdDoesNotExistAnywhere", _markup()))
        self.assertFalse(_selector_present(".no-such-class-at-all", _markup()))

    def test_generic_rules_come_last(self):
        """`input, textarea, select` and the nav container match huge
        parts of the page. If either sat above the specific rules, the
        language <select> would be explained as 'a form field' and every
        nav click as 'this is the navigation'."""
        topics_in_order = [topic for _, topic in self.table]
        self.assertEqual(topics_in_order[-1], "ctl_field")
        self.assertLess(topics_in_order.index("ctl_language"), topics_in_order.index("ctl_field"))
        self.assertLess(topics_in_order.index("ctl_export"), topics_in_order.index("ctl_primary_action"))


class TestControlCopy(unittest.TestCase):
    """Level 2 of the brief: complete in four languages, no mixing."""

    def setUp(self):
        self.source = CONTROLS_JS.read_text(encoding="utf-8")
        self.keys = re.findall(r"^    ([A-Za-z_]\w*)\s*:\s*\{", self.source, re.M)

    def test_there_is_copy_to_check(self):
        self.assertGreaterEqual(len(self.keys), 12)

    def test_every_control_topic_exists_in_all_four_languages(self):
        for language in LANGUAGES:
            found = len(re.findall(rf"^      {language}: \"", self.source, re.M))
            self.assertEqual(
                found, len(self.keys),
                f"{language}: {found} strings for {len(self.keys)} topics",
            )

    def test_no_topic_asserts_a_medical_or_diagnostic_fact(self):
        """Level 1 of the brief bans medical claims - it does not ban the
        word 'diagnostic', and the strongest sentence in this file is the
        one that says none of this IS a diagnosis. So the check is for
        the claim shape, not the vocabulary: an assertion about the
        reader's health rather than a denial of one."""
        claims = (
            r"you (?:have|show|display|suffer)\b[^.]{0,40}\b(?:disorder|addiction|depression|anxiety disorder)",
            r"\bsymptoms? of\b",
            r"\bdiagnos(?:is|ed|e) (?:of|with|you)\b",
            r"\btreatment for\b",
            r"\byou should (?:see|consult) a\b",
        )
        lowered = self.source.lower()
        for pattern in claims:
            self.assertIsNone(
                re.search(pattern, lowered), f"control copy makes a medical claim matching /{pattern}/",
            )

    def test_the_claim_checker_is_not_vacuous(self):
        self.assertIsNotNone(re.search(r"\bsymptoms? of\b", "these are symptoms of something"))

    def test_the_legal_topic_states_the_limit_out_loud(self):
        """The one place the guide has to say the boundary rather than
        merely respect it."""
        legal = self.source[self.source.index("ctl_legal:"):].lower()
        self.assertIn("medical or diagnostic statement", legal)
        self.assertIn("nothing here is", legal)


class TestPageWiring(unittest.TestCase):

    def test_every_shell_page_loads_the_click_layer(self):
        for page in SHELL_PAGES:
            source = page.read_text(encoding="utf-8")
            self.assertIn("guide-click.js", source, page.name)
            self.assertIn("guide-content-controls.js", source, page.name)

    def test_the_click_layer_loads_after_the_registry_it_extends(self):
        """register() is a no-op if DWGuide is not defined yet, and the
        control copy would vanish without a single error in the console."""
        for page in SHELL_PAGES:
            source = page.read_text(encoding="utf-8")
            self.assertLess(
                source.index("guide-tips.js"), source.index("guide-content-controls.js"), page.name,
            )

    def test_every_page_fallback_topic_has_copy(self):
        topics = _registered_topics()
        for filename, topic in _page_fallbacks().items():
            self.assertIn(topic, topics, f"{filename or '<root>'} falls back to unwritten topic {topic}")

    def test_every_shell_page_has_a_fallback_entry(self):
        fallbacks = _page_fallbacks()
        for page in SHELL_PAGES:
            self.assertIn(page.name, fallbacks, f"{page.name} has no fallback topic")

    def test_the_shell_publishes_the_page_key(self):
        """The fallback prefers body[data-dw-page] over the file name."""
        shell = (JS_DIR / "shell.js").read_text(encoding="utf-8")
        self.assertIn("dataset.dwPage = pageKey", shell)


class TestBadgesAreClickableEverywhere(unittest.TestCase):
    """`data-badge-id` is the whole contract between a badge tile and
    the guide. A surface that renders badges without it shows badges
    nobody can ask about."""

    def _badge_rendering_files(self) -> list[Path]:
        return [
            path for path in JS_DIR.glob("*.js")
            if re.search(r"badge-tile", path.read_text(encoding="utf-8"))
        ]

    def test_there_is_more_than_one_badge_surface(self):
        self.assertGreaterEqual(len(self._badge_rendering_files()), 2)

    def test_every_badge_surface_marks_its_tiles(self):
        for path in self._badge_rendering_files():
            source = path.read_text(encoding="utf-8")
            self.assertTrue(
                "data-badge-id" in source or "dataset.badgeId" in source,
                f"{path.name} renders badge tiles the guide cannot identify",
            )

    def test_the_profile_preview_reads_the_real_registry(self):
        """It used to render a second, older badge list whose English
        label and description came from the server - so the tiles stayed
        English in all four languages and had nothing to say aloud."""
        source = (JS_DIR / "profile.js").read_text(encoding="utf-8")
        self.assertIn("DWApi.badges()", source)
        self.assertIn("DWBadgeText", source)
        self.assertNotIn("identity.badges", source)

    def test_the_profile_page_loads_the_badge_registry(self):
        source = (FRONTEND / "profile.html").read_text(encoding="utf-8")
        self.assertIn("badge-registry.js", source)
        self.assertLess(source.index("badge-registry.js"), source.index("profile.js"))

    def test_hall_tiles_declare_themselves_bound(self):
        """They speak from their own handler. Without the marker the
        delegated layer would speak the same badge a second time."""
        source = (JS_DIR / "hall-of-fame.js").read_text(encoding="utf-8")
        self.assertIn("__dwGuideBound = true", source)
        self.assertIn("__dwBadge = badge", source)


class TestItDoesNotFightItself(unittest.TestCase):

    def setUp(self):
        self.source = CLICK_JS.read_text(encoding="utf-8")

    def test_it_listens_in_the_capture_phase(self):
        """attach() calls stopPropagation, so a bubble-phase listener on
        document would never see clicks on the 42 marked sections - and
        those are the ones with the best copy."""
        self.assertIn("addEventListener('click', onClick, true)", self.source)

    def test_it_yields_to_elements_that_speak_for_themselves(self):
        self.assertIn("__dwGuideBound", self.source)
        self.assertIn("'bound'", self.source)

    def test_the_bubble_close_button_is_ignored(self):
        """Answering the dismiss control reopens what the user just
        closed, which is a loop rather than a feature."""
        self.assertIn("mascot-bubble-close", self.source)

    def test_repeat_clicks_on_one_topic_are_collapsed(self):
        self.assertIn("REPEAT_MS", self.source)

    def test_a_click_overrides_the_fatigue_rules(self):
        """Auto-shown help backs off when dismissed; an explicit request
        must not, or the guide reads as broken."""
        self.assertIn("force: true", self.source)


if __name__ == "__main__":
    unittest.main()
