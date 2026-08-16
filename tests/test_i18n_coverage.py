"""
Tests: i18n coverage — the automated "which keys are missing in which
language" check.

Why this exists
----------------
The four language dictionaries in frontend/assets/js/i18n.js are
maintained by hand, and `t()` deliberately falls back to English when a
key is missing so a gap degrades visibly instead of throwing. That
fallback is good for users mid-session and terrible for maintenance: a
Persian reader silently gets an English sentence and nothing in the test
suite notices. Several rounds of "the page looks half-translated" bugs
traced back to exactly that.

So this module machine-checks three things no code review reliably catches:

  1. All four language blocks declare the SAME key set (no key that
     exists only in English).
  2. Every `data-i18n` / `data-i18n-placeholder` key referenced by any
     page in frontend/*.html actually exists in all four languages —
     a typo'd attribute renders the raw key to the user.
  3. No language block has a value that is byte-identical to English for
     a key where that is implausible (catches copy-paste stubs that were
     never actually translated). This one is reported, not asserted,
     because some values legitimately match across languages (numbers,
     product names, emoji-only strings).

  4. Runtime strings built from *inline* `{en/fa/ar/zh}` tables (the
     second, equally legitimate translation mechanism this codebase
     uses - see `DWI18n.pick()`) declare all four languages. A table
     with only `en` and `fa` silently serves English to Arabic and
     Chinese readers, which is the actual mechanism behind the
     "half-translated page" reports. This is enforced as a ratchet:
     the current known-bad count is pinned in `INLINE_TABLE_BASELINE`
     and the test fails if it grows, so the backlog can be paid down
     incrementally without new gaps sneaking in.

Run standalone for a full report:
    python3 -m tests.test_i18n_coverage
Run as a test:
    python3 -m pytest tests/test_i18n_coverage.py -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
I18N_FILE = PROJECT_ROOT / "frontend" / "assets" / "js" / "i18n.js"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

LANGUAGES = ("en", "fa", "ar", "zh")

JS_DIR = FRONTEND_DIR / "assets" / "js"

# Inline `{en:..., fa:...}` tables still missing `ar`/`zh`, per file.
# These are a real translation gap being paid down incrementally; the
# numbers may only ever go DOWN. Lower a number when you translate a
# file, and delete the entry when it reaches zero.
INLINE_TABLE_BASELINE: dict[str, int] = {
    # Empty: every inline language table now declares all four languages.
    # If this dict is ever repopulated, it means a gap was reintroduced.
}

# Binary "Persian or English" ternaries - `fa ? '...' : '...'`,
# `fa() ? ... : ...`, `lang === 'fa' ? ... : ...`. These are the second
# shape of the same bug: they cannot express Arabic or Chinese at all, so
# those readers always get the English branch. Same ratchet rule as
# above: replace them with a four-language pick() table and lower the
# number. Comments are stripped before counting, so the prose in
# coach.js/league.js/i18n.js documenting this anti-pattern is not
# miscounted as code.
BINARY_TERNARY_BASELINE = {
    # Empty: every file that used to carry binary fa/en ternaries
    # (app.js, model-performance.js, coach-chat.js, weekly-card.js,
    # intro-slides.js, ai-menu.js) has been rewritten onto full
    # {en,fa,ar,zh} pick() tables. Keep this baseline at zero - a
    # regression here should fail the test below, not silently widen it.
}

# Language-keyed CONTAINERS - `const X = { en: [...], fa: [...] }` or
# `{ en: { key: ... }, fa: { key: ... } }` - that omit `ar`/`zh` entirely.
#
# These were invisible to the inline-table check above, which matches only
# innermost brace groups and therefore skips any container holding nested
# objects or arrays. That blind spot hid four content banks, including the
# 55 digital-guide tips and the 30 processing-screen messages, all of which
# fall back to English for Arabic and Chinese readers. Counted per file as
# "entries missing per absent language" so the number reflects the real
# translation debt rather than just the container count.
LANG_CONTAINER_BASELINE: dict[str, int] = {
    # Empty: coach.js and coach-chat.js both reached zero when their
    # tables gained ar/zh blocks. If this dict is ever repopulated, it
    # means a gap was reintroduced.
}

# Values that may legitimately be identical across languages: pure
# punctuation/emoji/latin product names, or short symbolic strings.
_IDENTICAL_OK = re.compile(r"^[\W\d_]*$|^(Digital Wellness AI|SHAP|CSV|PDF|AI|R²)$")


def _extract_language_block(source: str, lang: str) -> str:
    """Return the raw text inside `<lang>: { ... }` from the dict literal.

    Located by brace-depth counting rather than a regex, because the
    values themselves contain braces, quotes and apostrophes.
    """
    marker = re.search(rf"^\s*{lang}:\s*\{{", source, re.MULTILINE)
    if marker is None:
        raise AssertionError(f"No '{lang}:' language block found in {I18N_FILE.name}")
    start = marker.end()  # just past the opening brace
    depth = 1
    i = start
    in_string: str | None = None
    while i < len(source) and depth > 0:
        ch = source[i]
        if in_string is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_string:
                in_string = None
        elif ch in "\"'`":
            in_string = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise AssertionError(f"Unbalanced braces while reading the '{lang}' block")
    return source[start : i - 1]


def _parse_entries(block: str) -> dict[str, str]:
    """Parse a flat `key: 'value'` dictionary body into a Python dict.

    Walks the text tracking string state so that a `:` or `,` inside a
    value never terminates an entry.
    """
    entries: dict[str, str] = {}
    i = 0
    n = len(block)
    while i < n:
        key_match = re.compile(r"([A-Za-z_$][\w$]*)\s*:\s*").match(block, i)
        if key_match is None:
            i += 1
            continue
        key = key_match.group(1)
        j = key_match.end()
        if j >= n or block[j] not in "\"'`":
            # Not a string value (nested object, number, etc.) - skip it.
            i = key_match.end()
            continue
        quote = block[j]
        j += 1
        buf: list[str] = []
        while j < n:
            ch = block[j]
            if ch == "\\":
                buf.append(block[j : j + 2])
                j += 2
                continue
            if ch == quote:
                break
            buf.append(ch)
            j += 1
        entries[key] = "".join(buf)
        i = j + 1
    return entries


def load_dictionaries() -> dict[str, dict[str, str]]:
    source = I18N_FILE.read_text(encoding="utf-8")
    return {lang: _parse_entries(_extract_language_block(source, lang)) for lang in LANGUAGES}


def collect_html_keys() -> dict[str, set[str]]:
    """Map each `frontend/*.html` file to the i18n keys it references."""
    pattern = re.compile(r"""data-i18n(?:-placeholder|-title|-aria)?\s*=\s*["']([^"']+)["']""")
    found: dict[str, set[str]] = {}
    for path in sorted(FRONTEND_DIR.glob("*.html")):
        keys = set(pattern.findall(path.read_text(encoding="utf-8")))
        if keys:
            found[path.name] = keys
    return found


class TestI18nKeyParity(unittest.TestCase):
    """All four languages must declare the same keys."""

    @classmethod
    def setUpClass(cls):
        cls.dicts = load_dictionaries()

    def test_every_language_block_was_parsed(self):
        for lang in LANGUAGES:
            self.assertGreater(
                len(self.dicts[lang]), 100,
                f"Parsed suspiciously few keys for '{lang}' - the parser or the file shape changed",
            )

    def test_all_languages_declare_the_same_keys(self):
        english = set(self.dicts["en"])
        problems: list[str] = []
        for lang in LANGUAGES:
            if lang == "en":
                continue
            keys = set(self.dicts[lang])
            missing = sorted(english - keys)
            extra = sorted(keys - english)
            if missing:
                problems.append(f"  {lang}: missing {len(missing)} key(s): {', '.join(missing[:15])}"
                                + (" ..." if len(missing) > 15 else ""))
            if extra:
                problems.append(f"  {lang}: has {len(extra)} key(s) English lacks: {', '.join(extra[:15])}"
                                + (" ..." if len(extra) > 15 else ""))
        self.assertEqual(
            problems, [],
            "i18n key sets differ between languages:\n" + "\n".join(problems),
        )


class TestHtmlKeysExist(unittest.TestCase):
    """Every key a page asks for must exist in every language."""

    @classmethod
    def setUpClass(cls):
        cls.dicts = load_dictionaries()
        cls.html_keys = collect_html_keys()

    def test_html_pages_were_found(self):
        self.assertGreater(len(self.html_keys), 5, "Expected several frontend pages using data-i18n")

    def test_no_page_references_an_undefined_key(self):
        problems: list[str] = []
        for page, keys in self.html_keys.items():
            for key in sorted(keys):
                absent = [lang for lang in LANGUAGES if key not in self.dicts[lang]]
                if absent:
                    problems.append(f"  {page}: '{key}' missing in {', '.join(absent)}")
        self.assertEqual(
            problems, [],
            "Pages reference i18n keys that are not defined (the raw key would render):\n"
            + "\n".join(problems),
        )


def scan_inline_tables() -> dict[str, int]:
    """Count inline `{en:..., fa:...}` tables per JS file that omit ar/zh.

    Matches innermost brace groups only, which is what an individual
    language table is. A table nested inside a larger object literal is
    still matched on its own.
    """
    table = re.compile(r"\{[^{}]*\ben\s*:[^{}]*\}", re.S)
    counts: dict[str, int] = {}
    for path in sorted(JS_DIR.glob("*.js")):
        source = path.read_text(encoding="utf-8")
        bad = 0
        for match in table.finditer(source):
            blob = match.group(0)
            if not re.search(r"\bfa\s*:", blob):
                continue  # not a language table
            if any(not re.search(rf"\b{lang}\s*:", blob) for lang in ("ar", "zh")):
                bad += 1
        if bad:
            counts[path.name] = bad
    return counts


def _strip_comments(source: str) -> str:
    """Remove /* */ and // comments so prose describing an anti-pattern
    is not counted as an instance of it."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", source, flags=re.MULTILINE)


def scan_binary_ternaries() -> dict[str, int]:
    """Count binary Persian/English ternaries per JS file."""
    patterns = [
        re.compile(r"\bfa\(\)\s*\?"),               # fa() ? ... : ...
        re.compile(r"===?\s*['\"]fa['\"]\s*\?"),    # lang === 'fa' ? ... : ...
        re.compile(r"(?<![\w.$])fa\s*\?\s*['\"`]"),  # const fa = ...; fa ? '...' : '...'
        re.compile(r"(?<![\w.$])f\s*\?\s*['\"`]"),   # const f = fa(); f ? '...' : '...'
    ]
    counts: dict[str, int] = {}
    for path in sorted(JS_DIR.glob("*.js")):
        source = _strip_comments(path.read_text(encoding="utf-8"))
        total = sum(len(p.findall(source)) for p in patterns)
        if total:
            counts[path.name] = total
    return counts


class TestBinaryLanguageTernaries(unittest.TestCase):
    """Binary fa/en ternaries cannot express Arabic or Chinese at all."""

    def test_no_file_has_more_ternaries_than_its_baseline(self):
        counts = scan_binary_ternaries()
        regressions = [
            f"  {name}: {count} binary fa/en ternary(ies) "
            f"(baseline allows {BINARY_TERNARY_BASELINE.get(name, 0)})"
            for name, count in sorted(counts.items())
            if count > BINARY_TERNARY_BASELINE.get(name, 0)
        ]
        self.assertEqual(
            regressions, [],
            "New binary Persian/English ternaries were introduced. Use a "
            "four-language table with DWI18n.pick() instead - a binary "
            "ternary silently serves English to Arabic and Chinese:\n"
            + "\n".join(regressions),
        )

    def test_ternary_baseline_has_no_stale_entries(self):
        counts = scan_binary_ternaries()
        stale = [
            f"  {name}: baseline claims {allowed}, actual is {counts.get(name, 0)}"
            for name, allowed in sorted(BINARY_TERNARY_BASELINE.items())
            if counts.get(name, 0) < allowed
        ]
        self.assertEqual(
            stale, [],
            "BINARY_TERNARY_BASELINE is out of date - lower these numbers "
            "(or delete the entry) now that the ternaries are gone:\n" + "\n".join(stale),
        )


def scan_lang_if_statements() -> dict[str, int]:
    """Count `if (lang === 'fa') { ... }` / `if (lang() === 'fa') { ... }`
    statement-level branches per file - the third shape (after binary
    ternaries and {en,fa}-only containers) that silently serves English
    to Arabic and Chinese readers, and the one the other two scanners
    above structurally cannot see (they match `?:` expressions and
    top-level `{en, fa}` object literals, not `if` statements).

    Real bug found this way: app.js's personalizedGuideLine() branched
    `if (lang === 'fa') { return <fa text> } return <en text>` - so ar/zh
    users read English there, and neither existing scanner flagged it.
    """
    pattern = re.compile(r"if\s*\(\s*lang\(?\)?\s*===\s*['\"]fa['\"]\s*\)\s*\{")
    counts: dict[str, int] = {}
    for path in sorted(JS_DIR.glob("*.js")):
        source = _strip_comments(path.read_text(encoding="utf-8"))
        n = len(pattern.findall(source))
        if n:
            counts[path.name] = n
    return counts


LANG_IF_STATEMENT_BASELINE: dict[str, int] = {
    # Empty on purpose - the one real instance (app.js's
    # personalizedGuideLine) was rewritten onto a full {en,fa,ar,zh}
    # DWI18n.pick() table. Keep this at zero.
}


class TestLangIfStatementBranching(unittest.TestCase):
    """`if (lang === 'fa') {...}` branches are as English-only-by-default
    as a binary ternary, just spelled as a statement instead of an
    expression."""

    def test_no_file_has_more_than_its_baseline(self):
        counts = scan_lang_if_statements()
        regressions = [
            f"  {name}: {count} if(lang==='fa') branch(es) "
            f"(baseline allows {LANG_IF_STATEMENT_BASELINE.get(name, 0)})"
            for name, count in sorted(counts.items())
            if count > LANG_IF_STATEMENT_BASELINE.get(name, 0)
        ]
        self.assertEqual(
            regressions, [],
            "New if(lang==='fa'){...} branches were introduced. Use a "
            "four-language table with DWI18n.pick() instead - this "
            "silently serves English to Arabic and Chinese exactly like "
            "a binary ternary does:\n" + "\n".join(regressions),
        )

    def test_baseline_has_no_stale_entries(self):
        counts = scan_lang_if_statements()
        stale = [
            f"  {name}: baseline claims {allowed}, actual is {counts.get(name, 0)}"
            for name, allowed in sorted(LANG_IF_STATEMENT_BASELINE.items())
            if counts.get(name, 0) < allowed
        ]
        self.assertEqual(
            stale, [],
            "LANG_IF_STATEMENT_BASELINE is out of date - lower these "
            "numbers (or delete the entry) now that the branches are "
            "gone:\n" + "\n".join(stale),
        )


def _matching_block(source: str, start: int, opener: str) -> str:
    """Return the text inside a bracket pair beginning at `start`."""
    closer = "]" if opener == "[" else "}"
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


def scan_language_containers() -> dict[str, int]:
    """Count untranslated entries in language-keyed containers, per file.

    A container is a `{ en: [...] | {...}, fa: ... }` shape declared at the
    top level of a module. The result is the number of entries in the
    English block multiplied by how many of ar/zh are missing, which is the
    number of strings still to write.
    """
    counts: dict[str, int] = {}
    for path in sorted(JS_DIR.glob("*.js")):
        source = _strip_comments(path.read_text(encoding="utf-8"))
        en = re.search(r"^\s*en:\s*([\[{])", source, re.MULTILINE)
        fa = re.search(r"^\s*fa:\s*([\[{])", source, re.MULTILINE)
        if not (en and fa):
            continue
        absent = [
            lang for lang in ("ar", "zh")
            if not re.search(rf"^\s*{lang}:\s*[\[{{]", source, re.MULTILINE)
        ]
        if not absent:
            continue
        block = _matching_block(source, en.end(), en.group(1))
        # Entries are either `{ c: ..., t: ... }` objects in an array, or
        # `key: 'value'` pairs in an object.
        entries = len(re.findall(r"\{\s*c:", block)) or len(
            re.findall(r"^\s{4,}([A-Za-z_$][\w$]*):", block, re.MULTILINE)
        )
        if entries:
            counts[path.name] = entries * len(absent)
    return counts


class TestLanguageContainers(unittest.TestCase):
    """Language-keyed banks must not silently omit whole languages."""

    def test_no_file_exceeds_its_container_baseline(self):
        counts = scan_language_containers()
        regressions = [
            f"  {name}: {count} untranslated entry-slot(s) "
            f"(baseline allows {LANG_CONTAINER_BASELINE.get(name, 0)})"
            for name, count in sorted(counts.items())
            if count > LANG_CONTAINER_BASELINE.get(name, 0)
        ]
        self.assertEqual(
            regressions, [],
            "A language-keyed content bank grew while still missing ar/zh:\n"
            + "\n".join(regressions),
        )

    def test_container_baseline_has_no_stale_entries(self):
        counts = scan_language_containers()
        stale = [
            f"  {name}: baseline claims {allowed}, actual is {counts.get(name, 0)}"
            for name, allowed in sorted(LANG_CONTAINER_BASELINE.items())
            if counts.get(name, 0) < allowed
        ]
        self.assertEqual(
            stale, [],
            "LANG_CONTAINER_BASELINE is out of date - lower these numbers "
            "(or delete the entry) now that the languages were added:\n"
            + "\n".join(stale),
        )


class TestInlineLanguageTables(unittest.TestCase):
    """Inline runtime language tables must cover all four languages."""

    def test_no_file_has_more_gaps_than_its_baseline(self):
        counts = scan_inline_tables()
        regressions: list[str] = []
        for name, count in sorted(counts.items()):
            allowed = INLINE_TABLE_BASELINE.get(name, 0)
            if count > allowed:
                regressions.append(
                    f"  {name}: {count} inline table(s) missing ar/zh "
                    f"(baseline allows {allowed})"
                )
        self.assertEqual(
            regressions, [],
            "New incomplete inline language tables were introduced. Every "
            "`{en, fa}` table must also declare `ar` and `zh`, or Arabic and "
            "Chinese readers silently get English:\n" + "\n".join(regressions),
        )

    def test_baseline_has_no_stale_entries(self):
        """A file that has been fully translated must be removed from the
        baseline, so the ratchet keeps tightening instead of rotting."""
        counts = scan_inline_tables()
        stale = [
            f"  {name}: baseline claims {allowed} gap(s), actual is {counts.get(name, 0)}"
            for name, allowed in sorted(INLINE_TABLE_BASELINE.items())
            if counts.get(name, 0) < allowed
        ]
        self.assertEqual(
            stale, [],
            "INLINE_TABLE_BASELINE is out of date - lower these numbers "
            "(or delete the entry) now that the gaps are fixed:\n" + "\n".join(stale),
        )


class TestUntranslatedValues(unittest.TestCase):
    """Report-only: values identical to English are likely untranslated stubs."""

    @classmethod
    def setUpClass(cls):
        cls.dicts = load_dictionaries()

    def test_report_values_identical_to_english(self):
        english = self.dicts["en"]
        suspects: dict[str, list[str]] = {}
        for lang in ("fa", "ar", "zh"):
            same = [
                key for key, value in self.dicts[lang].items()
                if key in english and value == english[key] and not _IDENTICAL_OK.match(value.strip())
            ]
            if same:
                suspects[lang] = sorted(same)
        if suspects:
            lines = [f"  {lang}: {len(keys)} value(s) identical to English -> {', '.join(keys[:10])}"
                     + (" ..." if len(keys) > 10 else "")
                     for lang, keys in suspects.items()]
            print("\n[i18n] Possibly untranslated (identical to English):\n" + "\n".join(lines))
        # Report-only on purpose - see module docstring.
        self.assertTrue(True)


def _main() -> None:
    dicts = load_dictionaries()
    print("=" * 66)
    print("i18n coverage report")
    print("=" * 66)
    for lang in LANGUAGES:
        print(f"  {lang}: {len(dicts[lang])} keys")

    english = set(dicts["en"])
    print("\n-- Key parity vs English --")
    for lang in LANGUAGES:
        if lang == "en":
            continue
        missing = sorted(english - set(dicts[lang]))
        extra = sorted(set(dicts[lang]) - english)
        status = "OK" if not missing and not extra else "MISMATCH"
        print(f"  {lang}: {status} (missing {len(missing)}, extra {len(extra)})")
        for key in missing:
            print(f"      missing: {key}")
        for key in extra:
            print(f"      extra:   {key}")

    print("\n-- Keys referenced by pages but not defined --")
    html_keys = collect_html_keys()
    undefined_total = 0
    for page, keys in html_keys.items():
        bad = {
            key: [lang for lang in LANGUAGES if key not in dicts[lang]]
            for key in sorted(keys)
        }
        bad = {k: v for k, v in bad.items() if v}
        if bad:
            print(f"  {page}:")
            for key, langs in bad.items():
                undefined_total += 1
                print(f"      {key} -> missing in {', '.join(langs)}")
    if undefined_total == 0:
        print("  none")

    print("\n-- Inline runtime tables missing ar/zh (serves English) --")
    inline = scan_inline_tables()
    if inline:
        for name, count in sorted(inline.items(), key=lambda kv: -kv[1]):
            allowed = INLINE_TABLE_BASELINE.get(name, 0)
            flag = "" if count <= allowed else "  <-- REGRESSION"
            print(f"  {count:4d}  {name} (baseline {allowed}){flag}")
        print(f"  total: {sum(inline.values())}")
    else:
        print("  none")

    print("\n-- Language-keyed banks missing whole languages --")
    containers = scan_language_containers()
    if containers:
        for name, count in sorted(containers.items(), key=lambda kv: -kv[1]):
            allowed = LANG_CONTAINER_BASELINE.get(name, 0)
            flag = "" if count <= allowed else "  <-- REGRESSION"
            print(f"  {count:4d}  {name} (baseline {allowed}){flag}")
        print(f"  total untranslated entry-slots: {sum(containers.values())}")
    else:
        print("  none")

    print("\n-- Binary fa/en ternaries (cannot express ar/zh at all) --")
    ternaries = scan_binary_ternaries()
    if ternaries:
        for name, count in sorted(ternaries.items(), key=lambda kv: -kv[1]):
            allowed = BINARY_TERNARY_BASELINE.get(name, 0)
            flag = "" if count <= allowed else "  <-- REGRESSION"
            print(f"  {count:4d}  {name} (baseline {allowed}){flag}")
        print(f"  total: {sum(ternaries.values())}")
    else:
        print("  none")

    print("\n-- Values identical to English (possible stubs) --")
    for lang in ("fa", "ar", "zh"):
        same = [
            key for key, value in dicts[lang].items()
            if key in dicts["en"] and value == dicts["en"][key] and not _IDENTICAL_OK.match(value.strip())
        ]
        print(f"  {lang}: {len(same)}")
        for key in sorted(same):
            print(f"      {key}")


if __name__ == "__main__":
    _main()
