"""Copy the JSON stores into SQLite.

    python3 -m services.storage.import_json            # dry run
    python3 -m services.storage.import_json --write

WHY A SEPARATE COMMAND
----------------------
Because the alternative - "the app migrates on first boot" - is how an
install ends up half in one engine and half in the other, with nobody
sure which is authoritative. Moving data is a decision somebody makes
once, deliberately, having read what it is about to do. So the default
is a dry run that prints the plan and touches nothing.

WHAT IT DOES
------------
Reads every `storage/*.json` and writes each one into the `records`
table under a store named after the file. The JSON files are left
exactly where they are: this copies, it never deletes, so a bad import
is recovered by unsetting DWAI_STORAGE_BACKEND rather than by restoring
a backup.

Re-running it is safe. Each store is replaced wholesale, not appended
to, so importing twice leaves one copy - not two.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from core import paths
from services.storage.sqlite_storage import (
    DEFAULT_SQLITE_PATH, SQLiteStorageBackend, _configured_path,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("import_json")

# Written by the running app and meaningless once imported - the lock
# sidecars in particular are not data.
SKIP_SUFFIXES = {".lock", ".tmp"}


def _json_stores(source: Path) -> list[Path]:
    if not source.exists():
        return []
    return sorted(
        path for path in source.glob("*.json")
        if path.suffix not in SKIP_SUFFIXES and path.is_file()
    )


def _read(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("  %s could not be read - skipped", path.name)
        return []
    if not isinstance(data, list):
        logger.warning("  %s is not a list of records - skipped", path.name)
        return []
    return [row for row in data if isinstance(row, dict)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true",
        help="actually import. Without this the plan is printed and nothing changes.",
    )
    parser.add_argument(
        "--source", type=Path, default=paths.STORAGE_DIR,
        help="directory holding the JSON stores (default: storage/)",
    )
    parser.add_argument(
        "--db", type=Path, default=None,
        help=f"target database (default: DWAI_SQLITE_PATH, else {DEFAULT_SQLITE_PATH})",
    )
    args = parser.parse_args(argv)

    target = args.db or _configured_path()
    stores = _json_stores(args.source)
    if not stores:
        logger.info("No JSON stores found in %s - nothing to import.", args.source)
        return 0

    logger.info("Source: %s", args.source)
    logger.info("Target: %s", target)
    logger.info("")

    total = 0
    for path in stores:
        records = _read(path)
        total += len(records)
        logger.info("  %-32s %6d records", path.name, len(records))
        if args.write:
            SQLiteStorageBackend(store=path.name, path=target).write_all(records)

    logger.info("")
    if not args.write:
        logger.info(
            "Dry run - nothing written. %d records across %d stores would be imported.\n"
            "Re-run with --write to do it, then set DWAI_STORAGE_BACKEND=sqlite.",
            total, len(stores),
        )
        return 0

    logger.info(
        "Imported %d records across %d stores.\n"
        "The JSON files were NOT deleted - unset DWAI_STORAGE_BACKEND to go back.\n"
        "Set DWAI_STORAGE_BACKEND=sqlite to start using the database.",
        total, len(stores),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
