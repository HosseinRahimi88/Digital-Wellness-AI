"""JSON files were never going to take a second worker.

Every write rewrote a whole file and every read-modify-write queued
behind one OS advisory lock, so the cost of saving one journal page grew
with the size of every account's journal, and two processes was not a
supported deployment.

This pins the replacement:

  * it implements the SAME StorageBackend contract, so the fifty-nine
    services that were written against JSON keep working untouched -
    tested by running the real AccountService and JournalService against
    it rather than by asserting the methods exist;
  * a transaction is a real one: a failure part-way leaves nothing
    behind, and the interleaving that loses an update on a naive
    implementation does not;
  * the schema is versioned and migrations run once, in order - the
    thing a JSON file never needed and a database cannot do without;
  * the JSON backend stays the default, because switching it would
    silently strand every existing install behind an empty database.

Run: python3 -m unittest tests.storage.test_sqlite_storage -v
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from services.storage.migrations import MIGRATIONS, SCHEMA_VERSION, current_version, migrate
from services.storage.sqlite_storage import (
    SQLiteStorageBackend, backend_for, close_all, connection_for, describe, selected_backend,
)


class SQLiteCase(unittest.TestCase):
    def setUp(self):
        close_all()
        self._dir = tempfile.TemporaryDirectory()
        self.db = Path(self._dir.name) / "test.db"
        self.backend = SQLiteStorageBackend("history.json", path=self.db)

    def tearDown(self):
        close_all()
        self._dir.cleanup()


class TestTheContract(SQLiteCase):
    """Everything StorageBackend promises, kept."""

    def test_an_empty_store_reads_as_an_empty_list(self):
        self.assertEqual(self.backend.read_all(), [])

    def test_write_then_read_round_trips(self):
        rows = [{"user_id": "u1", "n": 1}, {"user_id": "u2", "n": 2}]
        self.backend.write_all(rows)
        self.assertEqual(self.backend.read_all(), rows)

    def test_order_is_preserved(self):
        rows = [{"i": i} for i in range(50)]
        self.backend.write_all(rows)
        self.assertEqual([r["i"] for r in self.backend.read_all()], list(range(50)))

    def test_write_all_replaces_rather_than_appends(self):
        self.backend.write_all([{"a": 1}])
        self.backend.write_all([{"b": 2}])
        self.assertEqual(self.backend.read_all(), [{"b": 2}])

    def test_unicode_survives(self):
        # Four languages of user-written journal text go through here.
        rows = [{"text": "سلام دنیا"}, {"text": "你好世界"}, {"text": "مرحبا"}]
        self.backend.write_all(rows)
        self.assertEqual(self.backend.read_all(), rows)

    def test_nested_structures_survive(self):
        row = {"user_id": "u", "plan": {"days": [{"tasks": ["a", "b"]}]}, "n": None}
        self.backend.write_all([row])
        self.assertEqual(self.backend.read_all(), [row])

    def test_transaction_yields_the_current_rows_and_commits_the_new_ones(self):
        self.backend.write_all([{"a": 1}])
        with self.backend.transaction() as rows:
            self.assertEqual(rows, [{"a": 1}])
            self.backend.commit(list(rows) + [{"b": 2}])
        self.assertEqual(len(self.backend.read_all()), 2)

    def test_a_failed_transaction_leaves_nothing_behind(self):
        self.backend.write_all([{"keep": True}])
        with self.assertRaises(RuntimeError):
            with self.backend.transaction() as rows:
                self.backend.commit([{"gone": True}])
                raise RuntimeError("boom")
        self.assertEqual(self.backend.read_all(), [{"keep": True}])

    def test_a_nested_transaction_is_refused_rather_than_deadlocking(self):
        # The JSON backend raises here too, for the same reason: the
        # alternative is a request that never answers.
        with self.backend.transaction():
            with self.assertRaises(RuntimeError):
                with self.backend.transaction():
                    pass

    def test_stores_do_not_see_each_other(self):
        other = SQLiteStorageBackend("journal.json", path=self.db)
        self.backend.write_all([{"kind": "history"}])
        other.write_all([{"kind": "journal"}])
        self.assertEqual(self.backend.read_all(), [{"kind": "history"}])
        self.assertEqual(other.read_all(), [{"kind": "journal"}])

    def test_rewriting_one_store_leaves_the_others_alone(self):
        other = SQLiteStorageBackend("journal.json", path=self.db)
        other.write_all([{"page": i} for i in range(10)])
        self.backend.write_all([{"day": 1}])
        self.assertEqual(len(other.read_all()), 10)

    def test_a_non_dict_row_is_dropped_rather_than_stored(self):
        self.backend.write_all([{"ok": 1}, "not a record", 42, None])  # type: ignore[list-item]
        self.assertEqual(self.backend.read_all(), [{"ok": 1}])

    def test_the_database_refuses_to_store_malformed_json(self):
        # Stronger than the JSON backend manages. There, a hand-edited
        # file is discovered at read time and the whole store reads as
        # empty; here the generated user_id column runs json_extract on
        # write, so a bad row cannot get in at all.
        self.backend.write_all([{"good": 1}])
        with self.assertRaises(sqlite3.OperationalError):
            connection_for(self.db).execute(
                "INSERT INTO records (store, data) VALUES (?, ?)", ("history.json", "{not json"),
            )
        self.assertEqual(self.backend.read_all(), [{"good": 1}])

    def test_a_row_that_is_valid_json_but_not_an_object_is_skipped_on_read(self):
        # json_extract accepts a bare array, so this one does get in -
        # and the read path drops it rather than handing a list to a
        # caller expecting a record.
        self.backend.write_all([{"good": 1}])
        connection_for(self.db).execute(
            "INSERT INTO records (store, data) VALUES (?, ?)", ("history.json", "[1, 2, 3]"),
        )
        self.assertEqual(self.backend.read_all(), [{"good": 1}])


class TestItIsActuallyADatabase(SQLiteCase):
    def test_the_user_id_column_is_generated_from_the_payload(self):
        # Not a second copy that can drift - a generated column, so it
        # cannot disagree with the JSON it is derived from.
        self.backend.write_all([{"user_id": "u7", "x": 1}])
        row = connection_for(self.db).execute(
            "SELECT user_id FROM records WHERE store='history.json'"
        ).fetchone()
        self.assertEqual(row["user_id"], "u7")

    def test_the_per_user_lookup_uses_an_index(self):
        # The reason this is worth doing at all. Without the index this
        # is a scan of every account's rows for every request.
        plan = connection_for(self.db).execute(
            "EXPLAIN QUERY PLAN SELECT data FROM records "
            "WHERE store = 'history.json' AND user_id = 'u1'"
        ).fetchall()
        self.assertIn("USING INDEX", " ".join(str(row[3]) for row in plan))

    def test_writes_are_stamped(self):
        self.backend.write_all([{"a": 1}])
        row = connection_for(self.db).execute(
            "SELECT written_at_utc FROM records LIMIT 1"
        ).fetchone()
        self.assertTrue(row["written_at_utc"])

    def test_concurrent_writers_do_not_lose_an_update(self):
        # The race the JSON backend's file lock exists to prevent. Ten
        # threads each add one row inside a transaction; a backend that
        # let them interleave would finish with fewer than ten.
        self.backend.write_all([])
        errors: list[Exception] = []

        def add(index: int) -> None:
            try:
                backend = SQLiteStorageBackend("history.json", path=self.db)
                with backend.transaction() as rows:
                    backend.commit(list(rows) + [{"i": index}])
            except Exception as error:  # noqa: BLE001
                errors.append(error)

        threads = [threading.Thread(target=add, args=(i,)) for i in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [], f"threads raised: {errors}")
        self.assertEqual(len(self.backend.read_all()), 10)


class TestMigrations(SQLiteCase):
    def test_a_fresh_database_lands_on_the_current_version(self):
        self.backend.read_all()
        self.assertEqual(self.backend.schema_version(), SCHEMA_VERSION)

    def test_migrations_are_numbered_from_one_with_no_gaps(self):
        numbers = [number for number, _, _ in MIGRATIONS]
        self.assertEqual(numbers, list(range(1, len(MIGRATIONS) + 1)))

    def test_running_them_twice_applies_nothing_the_second_time(self):
        connection = connection_for(self.db)
        self.assertEqual(migrate(connection), 0)

    def test_an_old_database_is_brought_forward(self):
        # A database that stopped at version 1 - which is what somebody
        # who installed a month ago actually has.
        path = Path(self._dir.name) / "old.db"
        connection = sqlite3.connect(str(path))
        current_version(connection)
        number, name, step = MIGRATIONS[0]
        with connection:
            step(connection)
            connection.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)", (number, name),
            )
        connection.execute("INSERT INTO records (store, data) VALUES ('x.json', '{\"user_id\":\"u\"}')")
        connection.commit()
        connection.close()

        backend = SQLiteStorageBackend("x.json", path=path)
        self.assertEqual(backend.read_all(), [{"user_id": "u"}])  # data survived
        self.assertEqual(backend.schema_version(), SCHEMA_VERSION)

    def test_a_failing_migration_leaves_the_version_where_it_was(self):
        path = Path(self._dir.name) / "broken.db"
        connection = sqlite3.connect(str(path))
        before = current_version(connection)

        def explode(_):
            raise RuntimeError("bad migration")

        with mock.patch(
            "services.storage.migrations.MIGRATIONS",
            [(1, "explodes", explode)],
        ):
            with self.assertRaises(RuntimeError):
                migrate(connection)
        self.assertEqual(current_version(connection), before)
        connection.close()


class TestBackendSelection(unittest.TestCase):
    def test_json_is_the_default(self):
        # Switching this silently would strand every existing install
        # behind an empty database.
        with mock.patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("DWAI_STORAGE_BACKEND", None)
            self.assertEqual(selected_backend(), "json")

    def test_the_env_var_switches_it(self):
        with mock.patch.dict("os.environ", {"DWAI_STORAGE_BACKEND": "sqlite"}):
            self.assertEqual(selected_backend(), "sqlite")

    def test_an_unrecognised_value_falls_back_to_json(self):
        with mock.patch.dict("os.environ", {"DWAI_STORAGE_BACKEND": "postgres"}):
            self.assertEqual(selected_backend(), "json")

    def test_backend_for_returns_the_json_backend_by_default(self):
        from services.storage.json_file_storage import JSONFileStorageBackend

        import os

        with mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("DWAI_STORAGE_BACKEND", None)
            self.assertIsInstance(backend_for(Path("/tmp/accounts.json")), JSONFileStorageBackend)

    def test_backend_for_names_the_store_after_the_file(self):
        with mock.patch.dict("os.environ", {"DWAI_STORAGE_BACKEND": "sqlite"}):
            backend = backend_for(Path("/somewhere/accounts.json"))
            self.assertIsInstance(backend, SQLiteStorageBackend)
            self.assertEqual(backend.store, "accounts.json")

    def test_describe_reports_what_is_in_use(self):
        with mock.patch.dict("os.environ", {"DWAI_STORAGE_BACKEND": "sqlite"}):
            self.assertEqual(describe()["backend"], "sqlite")
            self.assertEqual(describe()["schema_version"], SCHEMA_VERSION)


class TestTheRealServicesRunOnIt(SQLiteCase):
    """The claim that matters: fifty-nine services, untouched.

    Asserting the three interface methods exist proves nothing - the
    services do upsert-by-key, cross-user deletes and read-modify-write
    inside transactions. So the real ones are pointed at a SQLite
    backend and exercised.
    """

    def test_account_service_works_end_to_end(self):
        from services.identity.account_service import AccountService

        service = AccountService(backend=SQLiteStorageBackend("accounts.json", path=self.db))
        account = service.register(
            email="sqlite@example.com", password="password123", display_name="SQLite",
        )
        self.assertEqual(service.get_by_email("sqlite@example.com").user_id, account.user_id)
        self.assertIsNotNone(
            service.authenticate(email="sqlite@example.com", password="password123")
        )
        self.assertTrue(service.delete_account(account.user_id))
        self.assertIsNone(service.get_by_email("sqlite@example.com"))

    def test_the_password_hash_is_stored_hashed(self):
        from services.identity.account_service import AccountService

        service = AccountService(backend=SQLiteStorageBackend("accounts.json", path=self.db))
        service.register(email="hash@example.com", password="password123", display_name="H")
        raw = json.dumps([dict(r) for r in connection_for(self.db).execute("SELECT data FROM records")])
        self.assertNotIn("password123", raw)

    def test_journal_upsert_by_day_still_upserts(self):
        from services.identity.journal_service import JournalService

        service = JournalService("u1", backend=SQLiteStorageBackend("journal.json", path=self.db))
        service.save("2026-01-01", "first", "good")
        service.save("2026-01-01", "second", "great")
        pages = service.get_all()
        self.assertEqual(len(pages), 1, "the upsert wrote a second row instead of replacing")
        self.assertEqual(pages[0].text, "second")

    def test_refresh_tokens_rotate_correctly_on_sqlite(self):
        from datetime import datetime, timedelta, timezone

        from services.identity.refresh_token_service import RefreshTokenService

        service = RefreshTokenService(
            "u1", backend=SQLiteStorageBackend("refresh_tokens.json", path=self.db),
        )
        service.issue("jti-1", datetime.now(timezone.utc) + timedelta(days=30))
        self.assertEqual(service.consume("jti-1"), (True, "ok"))
        self.assertEqual(service.consume("jti-1")[1], "reused")

    def test_one_users_delete_does_not_touch_another(self):
        from services.identity.journal_service import JournalService

        backend = SQLiteStorageBackend("journal.json", path=self.db)
        JournalService("u1", backend=backend).save("2026-01-01", "mine", "good")
        JournalService("u2", backend=backend).save("2026-01-01", "theirs", "good")
        JournalService("u1", backend=backend).delete_users(["u1"])
        self.assertEqual(len(JournalService("u2", backend=backend).get_all()), 1)
        self.assertEqual(len(JournalService("u1", backend=backend).get_all()), 0)


class TestTheImporter(SQLiteCase):
    def test_a_dry_run_writes_nothing(self):
        from services.storage import import_json

        source = Path(self._dir.name) / "json"
        source.mkdir()
        (source / "accounts.json").write_text(json.dumps([{"user_id": "u1"}]), encoding="utf-8")

        import_json.main(["--source", str(source), "--db", str(self.db)])
        self.assertEqual(SQLiteStorageBackend("accounts.json", path=self.db).read_all(), [])

    def test_write_imports_every_store(self):
        from services.storage import import_json

        source = Path(self._dir.name) / "json"
        source.mkdir()
        (source / "accounts.json").write_text(json.dumps([{"user_id": "u1"}]), encoding="utf-8")
        (source / "journal.json").write_text(
            json.dumps([{"user_id": "u1", "text": "hi"}]), encoding="utf-8",
        )

        import_json.main(["--source", str(source), "--db", str(self.db), "--write"])
        self.assertEqual(
            SQLiteStorageBackend("accounts.json", path=self.db).read_all(), [{"user_id": "u1"}],
        )
        self.assertEqual(len(SQLiteStorageBackend("journal.json", path=self.db).read_all()), 1)

    def test_importing_twice_does_not_duplicate(self):
        from services.storage import import_json

        source = Path(self._dir.name) / "json"
        source.mkdir()
        (source / "accounts.json").write_text(json.dumps([{"user_id": "u1"}]), encoding="utf-8")

        for _ in range(2):
            import_json.main(["--source", str(source), "--db", str(self.db), "--write"])
        self.assertEqual(len(SQLiteStorageBackend("accounts.json", path=self.db).read_all()), 1)

    def test_the_json_files_are_left_alone(self):
        from services.storage import import_json

        source = Path(self._dir.name) / "json"
        source.mkdir()
        original = source / "accounts.json"
        original.write_text(json.dumps([{"user_id": "u1"}]), encoding="utf-8")

        import_json.main(["--source", str(source), "--db", str(self.db), "--write"])
        self.assertTrue(original.exists(), "the importer deleted the source it copied from")

    def test_a_malformed_store_is_skipped_not_fatal(self):
        from services.storage import import_json

        source = Path(self._dir.name) / "json"
        source.mkdir()
        (source / "broken.json").write_text("{not json", encoding="utf-8")
        (source / "fine.json").write_text(json.dumps([{"a": 1}]), encoding="utf-8")

        self.assertEqual(
            import_json.main(["--source", str(source), "--db", str(self.db), "--write"]), 0,
        )
        self.assertEqual(len(SQLiteStorageBackend("fine.json", path=self.db).read_all()), 1)


if __name__ == "__main__":
    unittest.main()
