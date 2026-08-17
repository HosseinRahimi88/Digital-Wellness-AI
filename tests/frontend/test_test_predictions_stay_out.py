"""A check-in the server did not record must not answer for the user.

THE DEFECT, AS REPORTED

    "I ran a test assessment once, and when I went to the coach it
     ignores the real assessment I did before the test one and uses the
     test one. The coach must not accept test assessments at all."

Reproduced in a real browser before the fix: the server held a recorded
87.67, a throwaway test check-in scored 53.06 with `persisted: false`,
and DWLastResult.get() - which the Coach, the dashboard, the weekly
plan, the league, the band card and the simulator all read - returned
53.06.

THE CAUSE

app.js's submitPrediction() wrote every response into the cache:

    window.DWLastResult.set(result);
    localStorage.setItem('dwai_last_payload', JSON.stringify(payload));

unconditionally, including when the user had ticked "don't record this"
and the request went out with `persist: false`. /predict has always
returned `persisted` saying which it did; the flag was simply thrown
away at the cache boundary, so nothing downstream could have known.

TWO HALVES, ONE RULE

The result and the answers behind it are a pair - a result from one day
beside the answers from another is worse than either alone - and seven
modules were reading the payload straight out of localStorage. So the
payload is read through DWLastResult too, and comes back only when the
result standing next to it survived.

The behaviour itself is exercised against the real module by
tests/js/last_result_runner.js, run below. What this file adds is the
call-site check: that app.js does not write the cache for a result the
server refused to record, and that nothing has gone back to reading the
payload key directly.

Run: python3 -m unittest tests.frontend.test_test_predictions_stay_out -v
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest

from core import paths

REPO_ROOT = paths.PROJECT_ROOT
JS = REPO_ROOT / "frontend" / "assets" / "js"
RUNNER = REPO_ROOT / "tests" / "js" / "last_result_runner.js"

# Everything that reads the last check-in. Each one was a way for a
# test result to reach the user as though it were real.
PAYLOAD_READERS = [
    JS / "coach" / "coach-context.js",
    JS / "coach" / "coach-chat.js",
    JS / "coach" / "ai-menu.js",
    JS / "pages" / "weekly.js",
    JS / "pages" / "whatif.js",
    JS / "pages" / "league.js",
    JS / "features" / "band-decision.js",
]


def strip_comments(source: str) -> str:
    """Source with comments blanked out, line numbering preserved.

    Every one of these modules explains the defect in a comment that
    names the key, so a plain substring search finds the prose as
    readily as the code. Newlines are kept so a reported line number
    still points at the right line.
    """
    out = []
    i, n = 0, len(source)
    in_block = in_line = in_string = False
    quote = ""
    while i < n:
        two = source[i:i + 2]
        if in_block:
            if two == "*/":
                in_block = False
                out.append("  ")
                i += 2
                continue
            out.append("\n" if source[i] == "\n" else " ")
        elif in_line:
            if source[i] == "\n":
                in_line = False
                out.append("\n")
            else:
                out.append(" ")
        elif in_string:
            out.append(source[i])
            if source[i] == "\\":
                if i + 1 < n:
                    out.append(source[i + 1])
                i += 2
                continue
            if source[i] == quote:
                in_string = False
        elif two == "/*":
            in_block = True
            out.append("  ")
            i += 2
            continue
        elif two == "//":
            in_line = True
            out.append("  ")
            i += 2
            continue
        elif source[i] in "'\"`":
            in_string, quote = True, source[i]
            out.append(source[i])
        else:
            out.append(source[i])
        i += 1
    return "".join(out)


class TheCacheModuleEnforcesIt(unittest.TestCase):
    def test_the_real_module_refuses_a_non_persisted_result(self):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        result = subprocess.run(
            [node, str(RUNNER)], capture_output=True, text=True, timeout=60)
        self.assertEqual(
            result.returncode, 0,
            f"last-result.js behaviour check failed:\n{result.stdout}\n{result.stderr}")
        self.assertIn("passed", result.stdout)


class TheCheckInPageDoesNotCacheATestRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (JS / "pages" / "app.js").read_text(encoding="utf-8")

    def test_the_cache_write_is_guarded_by_persisted(self):
        # The write and the guard have to be in the same block. Matching
        # the guard alone would pass on a file where it guards something
        # else entirely.
        match = re.search(
            r"if\s*\(\s*result\.persisted\s*!==\s*false\s*\)\s*\{(.*?)\}",
            self.source, re.S)
        self.assertIsNotNone(
            match, "app.js should only cache a result the server recorded")
        guarded = match.group(1)
        self.assertIn("DWLastResult.set(result)", guarded)
        self.assertIn("dwai_last_payload", guarded)

    def test_the_guarded_call_site_is_the_only_one(self):
        # A second, unguarded write anywhere else in the file would
        # reopen the defect while leaving the test above passing.
        code = strip_comments(self.source)
        self.assertEqual(
            code.count("DWLastResult.set("), 1,
            "app.js should cache the result in exactly one place, inside the guard")


class NobodyReadsThePayloadKeyDirectly(unittest.TestCase):
    """`dwai_last_payload` has one owner now.

    Seven modules reached into localStorage for it. That is what made
    the defect survive a fix to the result cache alone: healing one key
    and not the other leaves the answers from an unrecorded day
    describing the user.
    """

    def test_every_reader_goes_through_dwlastresult(self):
        for module in PAYLOAD_READERS:
            code = strip_comments(module.read_text(encoding="utf-8"))
            for line_no, line in enumerate(code.splitlines(), 1):
                if "dwai_last_payload" not in line:
                    continue
                with self.subTest(module=module.name, line=line_no):
                    self.fail(
                        f"{module.name}:{line_no} reads dwai_last_payload directly; "
                        f"use DWLastResult.payload() so a test check-in cannot leak in")

    def test_the_comment_stripper_does_not_hide_real_code(self):
        # Guards the guard: if strip_comments blanked everything, the
        # check above would pass on a file that reads the key on every
        # line. These modules must still contain the call they were
        # moved onto.
        for module in PAYLOAD_READERS:
            code = strip_comments(module.read_text(encoding="utf-8"))
            with self.subTest(module=module.name):
                self.assertIn("DWLastResult.payload()", code)

    def test_the_owner_still_reads_it(self):
        # Guards the guard: if the key were renamed and this test list
        # not updated, the check above would pass vacuously.
        owner = (JS / "core" / "last-result.js").read_text(encoding="utf-8")
        self.assertIn("dwai_last_payload", owner)
        self.assertIn("function payload()", owner)

    def test_the_check_in_page_is_the_only_writer(self):
        writers = []
        for module in sorted(JS.rglob("*.js")):
            source = module.read_text(encoding="utf-8")
            if re.search(r"setItem\(\s*['\"]dwai_last_payload['\"]", source):
                writers.append(module.relative_to(JS).as_posix())
        # app.js writes it after a recorded check-in; demo.js seeds it
        # from a demo session, whose days ARE recorded server-side.
        self.assertEqual(sorted(writers), ["features/demo.js", "pages/app.js"])


if __name__ == "__main__":
    unittest.main()
