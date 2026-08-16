"""
Tests: real user data never becomes a tracked file.

storage/ is where the running app writes accounts - email address plus
argon2 password hash - and every user's logged history. Those two files
were tracked, which is how three real accounts reached the public
history of this repository. They are untracked now and the directory's
contents are ignored, but a `git add -f`, a rewritten .gitignore, or a
new storage file added later would put them back with nothing to say
so. Hence this file.

What it cannot do is remove what is already published; see SECURITY.md.

Run: python3 -m unittest tests.storage.test_no_user_data_committed -v
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

PROJECT_ROOT = paths.PROJECT_ROOT
def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=PROJECT_ROOT,
        capture_output=True, text=True, check=False,
    ).stdout


def _is_repo() -> bool:
    return (PROJECT_ROOT / ".git").exists()


class TestStorageIsNotTracked(unittest.TestCase):

    def setUp(self):
        if not _is_repo():
            self.skipTest("not a git checkout (a packaged build, say)")

    def test_no_storage_data_file_is_tracked(self):
        """.gitkeep is the one allowed entry - it exists so the layout
        is visible in a fresh checkout, and it is empty by definition."""
        tracked = [line for line in _git("ls-files", "storage/").splitlines() if line.strip()]
        self.assertEqual(
            [t for t in tracked if not t.endswith(".gitkeep")], [],
            "user data is tracked again: " + ", ".join(tracked),
        )

    def test_the_ignore_rule_actually_covers_the_data_files(self):
        """Asserting the rule's presence in .gitignore is not enough -
        order and negation both matter, so ask git itself."""
        for name in ("storage/accounts.json",
                     "storage/prediction_history.json",
                     "storage/accounts.json.lock"):
            result = _git("check-ignore", "-v", name)
            self.assertTrue(result.strip(), f"{name} is NOT ignored")

    def test_the_directory_marker_survives_the_ignore_rule(self):
        """`storage/*` would swallow .gitkeep too without the negation,
        and then a fresh checkout has no storage directory at all."""
        self.assertIn("storage/.gitkeep", _git("ls-files", "storage/"))

    def test_the_check_is_not_vacuous(self):
        """If `git ls-files` returned nothing for every path, the first
        test would pass no matter what was committed."""
        self.assertTrue(_git("ls-files", "services/").strip())


class TestTheAppNeedsNoSeededStorage(unittest.TestCase):
    """Untracking the files is only safe if their absence is a working
    starting state - otherwise a fresh checkout is broken instead of
    private."""

    def test_reading_a_missing_store_returns_empty_not_an_error(self):
        import tempfile

        import tests._test_support  # noqa: F401
        from services.storage.json_file_storage import JSONFileStorageBackend

        with tempfile.TemporaryDirectory() as tmp:
            backend = JSONFileStorageBackend(Path(tmp) / "nothing-here" / "records.json")
            self.assertEqual(backend.read_all(), [])

    def test_writing_creates_the_directory_and_the_file(self):
        import tempfile

        import tests._test_support  # noqa: F401
        from services.storage.json_file_storage import JSONFileStorageBackend

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "made" / "on" / "demand" / "records.json"
            backend = JSONFileStorageBackend(path)
            with backend.transaction() as records:
                records.append({"hello": "world"})
                backend.commit(records)
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), [{"hello": "world"}])


class TestTheLeakIsDocumented(unittest.TestCase):
    """A fix that leaves no trace of why invites the same mistake."""

    def test_there_is_a_security_note(self):
        self.assertTrue((PROJECT_ROOT / "SECURITY.md").exists())

    def test_it_says_what_was_exposed_and_what_to_do(self):
        text = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
        for phrase in ("storage/", "history", "change that password", "public"):
            self.assertIn(phrase, text, f"SECURITY.md does not mention {phrase!r}")

    def test_it_does_not_repeat_the_exposed_addresses(self):
        """Restating the leaked addresses in a file that is itself
        committed would publish them a second time."""
        text = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertNotIn("@gmail.com", text)


if __name__ == "__main__":
    unittest.main()
