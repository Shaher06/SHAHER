import sqlite3

import pytest

from app.database import migrations
from app.database.db import connect, transaction


def test_schema_initialisation(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"commitments", "habits", "habit_records", "settings"} <= tables
    assert migrations.get_version(conn) == migrations.LATEST_VERSION
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_reopening_does_not_destroy_data(db_path):
    c1 = connect(db_path)
    c1.execute("INSERT INTO settings(key, value) VALUES('k', 'v')")
    c1.close()
    c2 = connect(db_path)
    assert c2.execute("SELECT value FROM settings WHERE key='k'").fetchone()[0] == "v"


def test_migration_from_v1_keeps_existing_rows(tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path, isolation_level=None)
    old.row_factory = sqlite3.Row
    migrations.migrate(old, target=1)          # a database as an older app version left it
    assert migrations.get_version(old) == 1
    old.execute("INSERT INTO commitments (title, due_at, created_at, updated_at) "
                "VALUES ('قديم', '2026-10-20T10:00', '2026-10-01T00:00:00', '2026-10-01T00:00:00')")
    old.close()
    upgraded = connect(path)
    assert migrations.get_version(upgraded) == migrations.LATEST_VERSION
    row = upgraded.execute("SELECT title, is_demo, reminder_sent_at FROM commitments").fetchone()
    assert (row["title"], row["is_demo"], row["reminder_sent_at"]) == ("قديم", 0, None)


def test_database_newer_than_app_is_refused(tmp_path):
    path = tmp_path / "future.db"
    raw = sqlite3.connect(path)
    raw.execute(f"PRAGMA user_version = {migrations.LATEST_VERSION + 5}")
    raw.close()
    with pytest.raises(RuntimeError):
        connect(path)


def test_foreign_keys_enforced_and_cascade(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO habit_records (habit_id, record_date, result, created_at, updated_at) "
                     "VALUES (999, '2026-10-13', 'success', 'x', 'x')")
    conn.execute("INSERT INTO habits (name, start_date, created_at) VALUES ('h', '2026-10-01', 'x')")
    hid = conn.execute("SELECT id FROM habits").fetchone()[0]
    conn.execute("INSERT INTO habit_records (habit_id, record_date, result, created_at, updated_at) "
                 "VALUES (?, '2026-10-02', 'success', 'x', 'x')", (hid,))
    conn.execute("DELETE FROM habits WHERE id=?", (hid,))
    assert conn.execute("SELECT COUNT(*) FROM habit_records").fetchone()[0] == 0


def test_check_constraints(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO commitments (title, due_at, priority, created_at, updated_at) "
                     "VALUES ('x', '2026-10-13T10:00', 'urgent', 'x', 'x')")


def test_transaction_rolls_back_on_error(conn):
    with pytest.raises(RuntimeError):
        with transaction(conn):
            conn.execute("INSERT INTO settings(key, value) VALUES('a', '1')")
            raise RuntimeError("boom")
    assert conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0


def test_parameterized_queries_treat_input_as_data(commitments, conn):
    from datetime import datetime
    nasty = "x'); DROP TABLE commitments; --"
    commitments.create(nasty, "", datetime(2026, 10, 14, 10, 0))
    assert commitments.list("all", query="'); DROP")[0].title == nasty
    assert conn.execute("SELECT COUNT(*) FROM commitments").fetchone()[0] == 1   # table still exists


def test_search_wildcards_are_literal(commitments):
    from datetime import datetime
    commitments.create("100% جاهز", "", datetime(2026, 10, 14, 10, 0))
    commitments.create("شيء آخر", "", datetime(2026, 10, 14, 11, 0))
    assert [c.title for c in commitments.list("all", query="%")] == ["100% جاهز"]
