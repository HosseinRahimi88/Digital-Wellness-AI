"""No file may work out where it is by counting directories.

THIS BUG HAS NOW HAPPENED THREE TIMES IN THIS REPOSITORY.

  1. `services/` was grouped into six packages. Fourteen modules computed
     the project root as `Path(__file__).resolve().parent.parent`, which
     had been correct and was now one level short. The app wrote its
     accounts, history and journal into `services/storage/` for about
     half an hour. Nothing raised. It was found because a directory
     appeared that nobody had created.

  2. Those stray files were then swept into a commit by `git add -A`.

  3. `tests/` was grouped into nine packages. Fifty-two test files did
     the same thing, and ten more located their Node runners with
     `Path(__file__).resolve().parent / "js"`. Those would not have
     raised either - they would have pointed at a directory with no
     frontend and no artifacts in it, found nothing, and gone green by
     asserting over empty lists.

The shape is always the same: a path that is relative to a file's own
position, is correct today, and is silently wrong tomorrow. It never
throws, because a `Path` that does not exist is a perfectly good `Path`.

So it is banned, and the ban is a test rather than a convention, because
conventions do not survive a rename.

THE ONE EXCEPTION
-----------------
`tests/_test_support.py` is what puts the project root on `sys.path`.
Importing `core.paths` to find out where `core` is would be circular, so
it computes the root itself and says so in place. It is named here rather
than pattern-matched, so a second exception has to be added deliberately.
"""
from __future__ import annotations

import re
import unittest

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from core import paths

# Relative to the project root.
ALLOWED = {
    "tests/_test_support.py",
    # Defines PROJECT_ROOT. Something has to.
    "core/paths.py",
    # Stays in the root by construction and checks that it did - see its
    # own guard, which fails loudly rather than silently if it is moved.
    "run.py",
}

# Directories that are not the running application: the frozen Streamlit
# UI has its own bootstrap and is not maintained, and the virtualenv and
# caches are not ours at all.
SKIP_DIRS = {".venv", "__pycache__", ".git", "legacy", "node_modules", "data"}

# `parent.parent`, `parents[1]`, `parent.parent.parent`, ... - anything
# that walks up from __file__ by a fixed number of steps.
BY_DEPTH = re.compile(
    r"Path\(__file__\)\s*\.\s*resolve\(\)\s*\.\s*(?:parents\s*\[\s*\d+\s*\]|parent\s*\.\s*parent)"
)

# A sibling directory addressed from a file's own position. `parent /
# "js"` is how ten test files lost their Node runners: correct while the
# tree was flat, pointing into an empty folder after it was grouped.
SIBLING = re.compile(r"Path\(__file__\)\s*\.\s*resolve\(\)\s*\.\s*parent\s*/\s*[\"']")


def _code_only(source: str) -> str:
    """The file with every string and comment blanked out.

    Without this the checker flags its own docstring, which names the
    pattern it is banning - and would flag any comment that quoted it.
    Line numbers are preserved so the offenders it reports are findable.
    """
    import io
    import tokenize

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source  # unparseable: scan it raw rather than skip it

    lines = source.split("\n")
    for token in tokens:
        if token.type not in (tokenize.STRING, tokenize.COMMENT):
            continue
        (r1, c1), (r2, c2) = token.start, token.end
        for row in range(r1 - 1, r2):
            line = lines[row]
            start = c1 if row == r1 - 1 else 0
            end = c2 if row == r2 - 1 else len(line)
            lines[row] = line[:start] + " " * (end - start) + line[end:]
    return "\n".join(lines)


def _python_files():
    for path in paths.PROJECT_ROOT.rglob("*.py"):
        relative = path.relative_to(paths.PROJECT_ROOT)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        yield relative, path


class TestNoPathIsComputedByDepth(unittest.TestCase):
    def test_nothing_walks_up_from_its_own_file(self):
        offenders = []
        for relative, path in _python_files():
            if str(relative).replace("\\", "/") in ALLOWED:
                continue
            source = _code_only(path.read_text(encoding="utf-8", errors="ignore"))
            for match in BY_DEPTH.finditer(source):
                line = source[: match.start()].count("\n") + 1
                offenders.append(f"{relative}:{line}")

        self.assertEqual(
            offenders, [],
            "These compute a directory by walking up from their own file. That is "
            "correct until something moves, and then it is silently wrong - it does "
            "not raise, it just points somewhere else.\n\n"
            "  Use:  from core import paths  ->  paths.PROJECT_ROOT\n\n"
            + "\n".join(f"  {o}" for o in offenders),
        )

    def test_nothing_addresses_a_sibling_directory_from_its_own_file(self):
        offenders = []
        for relative, path in _python_files():
            if str(relative).replace("\\", "/") in ALLOWED:
                continue
            source = _code_only(path.read_text(encoding="utf-8", errors="ignore"))
            for match in SIBLING.finditer(source):
                line = source[: match.start()].count("\n") + 1
                offenders.append(f"{relative}:{line}")

        self.assertEqual(
            offenders, [],
            "These address a directory relative to their own file's position:\n\n"
            + "\n".join(f"  {o}" for o in offenders)
            + "\n\n  Use an absolute path from paths.PROJECT_ROOT instead.",
        )

    def test_the_exceptions_are_real_files_that_still_need_to_be_exceptions(self):
        # An allowlist that outlives the reason for its entries is how a
        # rule quietly stops applying.
        for name in ALLOWED:
            with self.subTest(file=name):
                path = paths.PROJECT_ROOT / name
                self.assertTrue(path.exists(), f"{name} is allowlisted but does not exist")
                self.assertRegex(
                    path.read_text(encoding="utf-8", errors="ignore"),
                    r"(?s)(PROJECT_ROOT|project root)",
                    f"{name} is allowlisted for computing the project root but no "
                    f"longer appears to do so - drop it from ALLOWED.",
                )


class TestTheProjectRootIsWhereItSaysItIs(unittest.TestCase):
    """The definition everything else now depends on."""

    def test_it_points_at_the_repository(self):
        for marker in ("api/main.py", "core/feature_schema.py", "run.py", "requirements.txt"):
            with self.subTest(marker=marker):
                self.assertTrue(
                    (paths.PROJECT_ROOT / marker).exists(),
                    f"paths.PROJECT_ROOT does not contain {marker} - it is pointing "
                    f"at {paths.PROJECT_ROOT}, which is not the project root.",
                )

    def test_the_derived_directories_hang_off_it(self):
        self.assertEqual(paths.STORAGE_DIR.parent, paths.PROJECT_ROOT)
        self.assertEqual(paths.ARTIFACTS_DIR.parent, paths.PROJECT_ROOT)
        self.assertEqual(paths.storage_file("x.json").parent, paths.STORAGE_DIR)
        self.assertEqual(paths.artifact("x.pkl").parent, paths.ARTIFACTS_DIR)

    def test_artifacts_actually_holds_the_shipped_models(self):
        # If PROJECT_ROOT were wrong, everything above would still pass -
        # the paths would simply be built from the wrong parent. This is
        # the check that would not.
        for name in ("health_classifier.pkl", "health_regressor.pkl", "persona_model.pkl"):
            with self.subTest(artifact=name):
                self.assertTrue(paths.artifact(name).exists())


if __name__ == "__main__":
    unittest.main()
