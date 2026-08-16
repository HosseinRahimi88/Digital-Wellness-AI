"""
Tests: digital-guide content registry invariants.

The guide's copy lives in frontend/assets/js/guide/guide-tips.js and its
per-topic metadata (which face to wear, how important the topic is, and
whether it may auto-repeat) lives beside it in the same module. Three
things about that arrangement can break silently in the browser, so they
are checked here instead:

  1. A `face` value that is not one of mascot.js's FACES keys. renderFace
     falls back rather than throwing, so a typo would just quietly show
     the wrong expression forever - which is exactly the bug this registry
     was added to fix (explain() used to render 'neutral' for all 55
     topics).

  2. Metadata for a topic that has no copy, or vice versa. Both directions
     are dead weight that reads as a wired-up feature.

  3. The bubble's dismiss control losing `pointer-events: auto`.
     `.mascot-bubble` deliberately sets `pointer-events: none` so speech
     never blocks a tap underneath it; the close button therefore has to
     opt back in explicitly. Without that single line it renders, looks
     interactive, and cannot be clicked - and the whole fatigue mechanism
     depends on it, because dismissal is what gets counted.

Run standalone:
    python3 -m tests.frontend.test_guide_registry
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

PROJECT_ROOT = paths.PROJECT_ROOT
JS_DIR = PROJECT_ROOT / "frontend" / "assets" / "js"
CSS_DIR = PROJECT_ROOT / "frontend" / "assets" / "css"

GUIDE_JS = JS_DIR / "guide/guide-tips.js"
MASCOT_JS = JS_DIR / "chrome/mascot.js"
COMPONENTS_CSS = CSS_DIR / "components.css"


def _block(source: str, start: int, opener: str = "{") -> str:
    closer = "}" if opener == "{" else "]"
    depth = 1
    i = start
    quote: str | None = None
    while i < len(source) and depth:
        c = source[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
        i += 1
    return source[start : i - 1]


def mascot_face_names() -> set[str]:
    src = MASCOT_JS.read_text(encoding="utf-8")
    m = re.search(r"const FACES = \{", src)
    assert m, "FACES table not found in mascot.js"
    body = _block(src, m.end())
    return set(re.findall(r"^\s*([A-Za-z_$][\w$]*)\s*:", body, re.MULTILINE))


def guide_meta() -> dict[str, dict[str, str]]:
    """topic -> {face, priority, cooldownDays} as declared in META."""
    src = GUIDE_JS.read_text(encoding="utf-8")
    m = re.search(r"const META = \{", src)
    assert m, "META table not found in guide-tips.js"
    body = _block(src, m.end())
    out: dict[str, dict[str, str]] = {}
    for entry in re.finditer(
        r"^\s*([A-Za-z_$][\w$]*)\s*:\s*\{([^}]*)\}", body, re.MULTILINE
    ):
        fields = {}
        for f in re.finditer(r"([A-Za-z_$][\w$]*)\s*:\s*('([^']*)'|[\d.]+)", entry.group(2)):
            fields[f.group(1)] = f.group(3) if f.group(3) is not None else f.group(2)
        out[entry.group(1)] = fields
    return out


def guide_topics() -> set[str]:
    """Topic keys declared in the English copy block."""
    src = GUIDE_JS.read_text(encoding="utf-8")
    m = re.search(r"const TIPS = \{\s*\n\s*en:\s*\{", src)
    assert m, "TIPS.en block not found in guide-tips.js"
    body = _block(src, m.end())
    return set(re.findall(r"^\s*([A-Za-z_$][\w$]*)\s*:", body, re.MULTILINE))


class TestGuideRegistry(unittest.TestCase):

    def test_tables_were_parsed(self):
        """Guard against the parsers silently matching nothing, which would
        make the assertions below pass vacuously."""
        self.assertGreater(len(mascot_face_names()), 3, "FACES parse looks wrong")
        self.assertGreater(len(guide_meta()), 30, "META parse looks wrong")
        self.assertGreater(len(guide_topics()), 30, "TIPS.en parse looks wrong")

    def test_every_face_is_a_real_mascot_expression(self):
        faces = mascot_face_names()
        bad = {
            topic: fields["face"]
            for topic, fields in guide_meta().items()
            if "face" in fields and fields["face"] not in faces
        }
        self.assertEqual(
            bad, {},
            "Guide topics name expressions that mascot.js's FACES does not "
            f"define (valid: {sorted(faces)}): {bad}",
        )

    def test_metadata_and_copy_cover_the_same_topics(self):
        meta = set(guide_meta())
        topics = guide_topics()
        self.assertEqual(
            sorted(meta - topics), [],
            "META declares topics that have no copy in TIPS.en",
        )
        self.assertEqual(
            sorted(topics - meta), [],
            "Topics have copy but no metadata, so they fall back to the "
            "default face/priority instead of a deliberate one",
        )

    def test_faces_are_not_all_the_same(self):
        """The point of the registry is that expression follows content."""
        faces = [f["face"] for f in guide_meta().values() if "face" in f]
        self.assertGreater(
            len(set(faces)), 2,
            "Guide expressions barely vary - explain() used to hardcode "
            "'neutral' for every topic and this check exists so that "
            "cannot quietly come back",
        )

    def test_dismiss_control_can_actually_be_clicked(self):
        css = COMPONENTS_CSS.read_text(encoding="utf-8")
        bubble = re.search(r"\.mascot-bubble\s*\{[^}]*\}", css, re.S)
        self.assertIsNotNone(bubble, ".mascot-bubble rule not found")
        self.assertIn(
            "pointer-events: none", bubble.group(0),
            "Assumption changed: .mascot-bubble no longer disables pointer "
            "events, so re-check whether the close button still needs to "
            "opt back in",
        )
        close = re.search(r"\.mascot-bubble-close\s*\{[^}]*\}", css, re.S)
        self.assertIsNotNone(close, ".mascot-bubble-close rule not found")
        self.assertIn(
            "pointer-events: auto", close.group(0),
            "The dismiss control sits inside a pointer-events: none bubble, "
            "so without pointer-events: auto it is visible but unclickable - "
            "and the guide's fatigue memory counts dismissals, so it would "
            "silently never trigger",
        )

    def test_registry_api_is_exported(self):
        src = GUIDE_JS.read_text(encoding="utf-8")
        m = re.search(r"window\.DWGuide\s*=\s*\{(.*?)\};", src, re.S)
        self.assertIsNotNone(m, "DWGuide export not found")
        exported = m.group(1)
        for name in ("register", "metaFor", "canShow", "explainBest", "noteDismissed"):
            self.assertIn(
                name, exported,
                f"DWGuide.{name} is not exported, so feature modules cannot "
                "register their own guide content",
            )

    def test_register_creates_missing_language_blocks(self):
        """TIPS declares only en/fa today. register() must create ar/zh
        rather than skip them, or supplied translations vanish silently."""
        src = GUIDE_JS.read_text(encoding="utf-8")
        m = re.search(r"function register\(entries\) \{", src)
        self.assertIsNotNone(m, "register() not found")
        body = _block(src, m.end())
        self.assertIn(
            "if (!TIPS[lang]) TIPS[lang] = {}", body,
            "register() must create an absent language block; guarding on "
            "TIPS[lang] instead quietly discards ar/zh copy",
        )


def _main() -> None:
    faces = mascot_face_names()
    meta = guide_meta()
    print(f"mascot expressions : {sorted(faces)}")
    print(f"guide topics       : {len(guide_topics())}")
    print(f"topics with meta   : {len(meta)}")
    used = sorted({f['face'] for f in meta.values() if 'face' in f})
    print(f"expressions in use : {used}")


if __name__ == "__main__":
    _main()


class TheGuideTalksToTheReader(unittest.TestCase):
    """The guide's voice, pinned where it is actually heard.

    WHAT WAS WRONG. Measured across the English copy, 168 of 235 topics
    contained no second person at all - not one "you" or "your". They
    read as reference documentation attached to a character: correct,
    impersonal, and not what somebody tapping a face on the screen is
    expecting to hear back.

    WHAT IS PINNED. The page-level topics, because those are the ones
    that open every tour and every "explain this page" - they are the
    guide's voice as anybody actually experiences it. If one of them
    drifts back to describing the software in the third person, this
    fails.

    The section topics are deliberately NOT covered. Some of them
    genuinely are statements about the model rather than about the
    reader, and forcing a "you" into those would produce worse copy in
    service of a test.
    """

    PAGE_TOPICS = (
        "dashboard", "checkin", "weekly", "coach", "analytics", "whatif",
        "model", "profile", "league", "about", "you", "landing",
    )

    # Marker sets per language, checked against impersonal prose below
    # so they cannot quietly become vacuous. Arabic and Persian carry
    # the second person as an ATTACHED pronoun far more often than as a
    # separate word, so a list of standalone words misses most of it -
    # the first version of this test failed its own Arabic copy for
    # exactly that reason.
    SECOND_PERSON = {
        "en": (" you ", " you.", " you,", " your ", "you're", "yourself", "You "),
        # Persian: attached -t/-at, the pronoun, and second-person verbs.
        "fa": ("خودت", "تو ", "‌ات ", "ت ", "می‌کنی", "می‌بینی", "می‌گیری",
               "بپرس", "بخوان", "بده", "داری", "کرده‌ای", "ات،"),
        # Arabic: attached -ka, the pronoun, and the taa- verb prefix
        # that marks the second person.
        "ar": ("أنت", "لك", "ك ", "ك،", "كِ", "ترى", "تستطيع", "تصفه",
               "اسأل", "اقرأ", "سجّلت", "حمِّل", "غيّر", "يخاطبك", "يعطيك"),
        "zh": ("你",),
    }

    @classmethod
    def setUpClass(cls):
        cls.source = (
            paths.PROJECT_ROOT / "frontend" / "assets" / "js" / "guide" / "guide-tips.js"
        ).read_text(encoding="utf-8")

    def _texts(self, topic):
        """Both quote styles. The file uses single quotes for copy that
        contains a double quote and vice versa, so matching only one
        silently finds three of the four languages - and then zips the
        wrong text against the wrong marker set, which is a failure
        that points at the wrong thing entirely."""
        return re.findall(
            rf"""^      {topic}: (["'])(.+)\1,$""", self.source, re.M,
        )

    def test_every_page_topic_exists_in_four_languages(self):
        for topic in self.PAGE_TOPICS:
            with self.subTest(topic=topic):
                self.assertEqual(
                    len(self._texts(topic)), 4,
                    f"{topic} is not written in all four languages",
                )

    def test_every_page_topic_addresses_the_reader(self):
        languages = ("en", "fa", "ar", "zh")
        for topic in self.PAGE_TOPICS:
            for language, (_quote, text) in zip(languages, self._texts(topic)):
                with self.subTest(topic=topic, language=language):
                    markers = self.SECOND_PERSON[language]
                    self.assertTrue(
                        any(marker in text for marker in markers),
                        f"{topic} ({language}) never addresses the reader - it "
                        f"describes the software instead: {text[:90]}",
                    )

    def test_the_marker_check_is_not_vacuous(self):
        """A test that passes on anything is worse than no test. Prose
        with no second person in it must fail the same check."""
        impersonal = {
            "en": "The model computes a score from the submitted fields.",
            "fa": "مدل از روی فیلدهای ارسال‌شده یک نمره حساب می‌کند.",
            "ar": "يحسب النموذج درجة من الحقول المرسلة.",
            "zh": "模型根据提交的字段计算出一个分数。",
        }
        for language, text in impersonal.items():
            with self.subTest(language=language):
                markers = self.SECOND_PERSON[language]
                self.assertFalse(
                    any(marker in text for marker in markers),
                    f"the {language} marker set matches impersonal prose",
                )
