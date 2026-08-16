"""Versioned schema migrations for the SQLite backend.

WHY THIS EXISTS SEPARATELY
--------------------------
A JSON file has no schema, so the project never needed migrations: a new
field just appeared in newly written records and older ones did without
it. The moment storage becomes a database that stops being true, and the
usual answer - "the app creates its tables on first run" - only works
until the second version of those tables. Then somebody has a database
from last month and no way to move it forward.

So the schema is a list of numbered steps, each applied exactly once, in
order, inside a transaction, recorded in `schema_migrations`. Running the
app against a fresh file and against a file three versions old both end
at the same schema.

RULES FOR ADDING ONE
--------------------
  * append, never edit. A migration that has already run somewhere is
    history, and rewriting it means two databases claiming version N
    with different shapes;
  * never renumber;
  * make it idempotent where SQLite lets you (IF NOT EXISTS), because a
    process killed mid-migration is a real thing;
  * forward only. There are no down-migrations, deliberately: a rollback
    that silently drops a column drops the data in it, and "restore the
    backup" is the honest answer to a bad deploy.

WHAT THE SCHEMA IS
------------------
One table, `records`, holding the same flat list of JSON-like dicts the
StorageBackend interface has always described - `store` names which
logical file a row used to live in, `data` is the record. That is a
deliberate choice over a column-per-field schema: every service currently
writes whatever keys it likes into its own store, and imposing typed
columns on top of that would mean rewriting all fifty-nine of them before
a single row could move. The indexes below are what make it a database
rather than a JSON file with extra steps.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Callable

logger = logging.getLogger(__name__)

Migration = Callable[[sqlite3.Connection], None]


def _v1_records_table(connection: sqlite3.Connection) -> None:
    """The store itself."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS records (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            store   TEXT NOT NULL,
            data    TEXT NOT NULL
        );

        -- Every read is "give me one store", so this index is not an
        -- optimisation, it is the difference between a scan of every
        -- account's everything and a lookup.
        CREATE INDEX IF NOT EXISTS idx_records_store ON records(store);
        """
    )


def _v2_user_id_index(connection: sqlite3.Connection) -> None:
    """A generated column for the one key every store shares.

    Almost every query in the app is "this store, this user". Pulling
    user_id out of the JSON into a real indexed column is what stops that
    being a full scan of the store, and SQLite's generated columns keep
    it in step with `data` automatically - there is no second copy that
    can drift, because it is not a copy.
    """
    columns = {row[1] for row in connection.execute("PRAGMA table_info(records)")}
    if "user_id" not in columns:
        connection.execute(
            "ALTER TABLE records ADD COLUMN user_id TEXT "
            "GENERATED ALWAYS AS (json_extract(data, '$.user_id')) VIRTUAL"
        )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_records_store_user ON records(store, user_id)"
    )


def _v3_written_at(connection: sqlite3.Connection) -> None:
    """When a row was last written.

    Not used by the application - the services all carry their own
    timestamps inside `data`. This is for whoever has to work out what
    happened to a database at three in the morning, which is a use case
    a JSON file served accidentally (via the file mtime) and a table does
    not serve at all unless someone puts it there.
    """
    columns = {row[1] for row in connection.execute("PRAGMA table_info(records)")}
    if "written_at_utc" not in columns:
        # A non-constant default is not allowed in ALTER TABLE ADD COLUMN,
        # so the column is added empty and filled by the backend on write.
        connection.execute("ALTER TABLE records ADD COLUMN written_at_utc TEXT")


# Append only. The index in this list IS the version number.
MIGRATIONS: list[tuple[int, str, Migration]] = [
    (1, "records table", _v1_records_table),
    (2, "user_id generated column and index", _v2_user_id_index),
    (3, "written_at_utc column", _v3_written_at),
]

SCHEMA_VERSION = MIGRATIONS[-1][0]


def current_version(connection: sqlite3.Connection) -> int:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "  version INTEGER PRIMARY KEY,"
        "  name TEXT NOT NULL,"
        "  applied_at_utc TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return int(row[0] or 0)


def migrate(connection: sqlite3.Connection) -> int:
    """Bring a database up to SCHEMA_VERSION. Returns how many ran.

    Each step gets its own transaction, so a failure half way leaves the
    database at the last version that completed rather than in a state
    that is neither. The next run picks up from there.
    """
    applied = 0
    version = current_version(connection)
    for number, name, step in MIGRATIONS:
        if number <= version:
            continue
        logger.info("Applying storage migration %d (%s)", number, name)
        try:
            with connection:  # BEGIN ... COMMIT, or ROLLBACK on error
                step(connection)
                connection.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (number, name),
                )
        except Exception:
            logger.exception(
                "Storage migration %d (%s) failed - the database is left at version %d.",
                number, name, current_version(connection),
            )
            raise
        applied += 1
    return applied
