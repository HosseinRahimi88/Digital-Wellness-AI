"""
Tests: digital-guide content registry invariants.

The guide's copy lives in frontend/assets/js/guide-tips.js and its
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
    python3 -m tests.test_guide_registry
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JS_DIR = PROJECT_ROOT / "frontend" / "assets" / "js"
CSS_DIR = PROJECT_ROOT / "frontend" / "assets" / "css"

GUIDE_JS = JS_DIR / "guide-tips.js"
MASCOT_JS = JS_DIR / "mascot.js"
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
