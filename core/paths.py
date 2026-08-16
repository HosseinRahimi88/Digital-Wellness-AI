"""
Where the project's own folders are.

One definition, imported by every module that needs to find `storage/`
or `artifacts/`, rather than each one counting `.parent` hops from its
own file.

Why this exists
----------------
Fourteen service modules used to compute the project root as
`Path(__file__).resolve().parent.parent`, which was correct while every
service sat directly in `services/`. Grouping them into subpackages
moved each one a level deeper and silently changed what that expression
meant: the calibration cache started writing to `services/artifacts/`
and every JSON store would have gone to `services/storage/`. Nothing
raised - the directories were simply created in the wrong place, which
is the worst kind of failure this refactor could produce.

The root is anchored to THIS file's own location and nothing else, so
moving any other module cannot change it. If this file itself ever
moves, one line here changes and every caller stays correct.
"""

from __future__ import annotations

from pathlib import Path

# core/paths.py -> core/ -> the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The two directories the running app writes to or reads from. Neither
# is created here: a module that needs one creates it when it writes, so
# importing this file has no side effects.
STORAGE_DIR = PROJECT_ROOT / "storage"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DATA_DIR = PROJECT_ROOT / "data"


def storage_file(name: str) -> Path:
    """A per-store JSON file under storage/ - `storage_file("league.json")`."""
    return STORAGE_DIR / name


def artifact(name: str) -> Path:
    """A model or metrics file under artifacts/."""
    return ARTIFACTS_DIR / name
