import csv
import json
import sqlite3
from datetime import datetime

import pytest

from app.database import migrations
from app.database.db import connect
from app.services import backup_service, data_service
from app.services.demo_data import add_demo_data
from app.services.preferences import Preferences
from app.services.settings_service import SettingsService
from app.utils.validation import ValidationError

D = datetime


def seed(commitments, habits):
    c = commitments.create("التزام مهم", "وصف, بفاصلة \"وعلامات\"", D(2026, 10, 15, 9, 0), "high", "عمل",
                           reminder_enabled=True, reminder_at=D(2026, 10, 15, 8, 30))
    done = commitments.create("خلصان", "", D(2026, 10, 14, 9, 0))
    commitments.complete(done.id)
    h = habits.create("قراءة", 15, start_date=D(2026, 10, 10).date())
    habits.record_day(h.id, D(2026, 10, 12).date(), "success", "ملاحظة")
    return c, h


# ---------------- backup / restore ----------------
def test_backup_restore_roundtrip_brings_data_back(conn, commitments, habits, reminders, tmp_path):
    seed(commitments, habits)
    backup = backup_service.export_backup(conn, tmp_path)
    data_service.delete_all_data(conn, reminders)
    assert commitments.list("all") == [] and habits.list() == []
    safety = data_service.restore_backup(conn, backup, reminders)
    assert safety.exists() and safety.name.startswith("pre_restore_")
    assert {c.title for c in commitments.list("all")} == {"التزام مهم"}
    assert [c.title for c in commitments.list("completed")] == ["خلصان"]
    assert habits.records(habits.list()[0].id)[0].note == "ملاحظة"


def test_restore_saves_the_current_data_first_so_it_can_be_undone(conn, commitments, habits, reminders, tmp_path):
    other = connect(tmp_path / "other.db")                      # a different, valid database
    other.close()
    seed(commitments, habits)
    safety = data_service.restore_backup(conn, tmp_path / "other.db", reminders)
    assert commitments.list("all") == []                         # replaced by the (empty) backup
    back = connect(safety)
    assert back.execute("SELECT COUNT(*) FROM commitments").fetchone()[0] == 2   # nothing lost


def test_restore_reschedules_reminders(conn, commitments, habits, reminders, backend, tmp_path):
    c, _ = seed(commitments, habits)
    backup = backup_service.export_backup(conn, tmp_path)
    backend.scheduled.clear()
    data_service.restore_backup(conn, backup, reminders)
    assert f"c{c.id}" in backend.scheduled


@pytest.mark.parametrize("make", ["garbage", "empty", "wrong_schema", "missing"])
def test_invalid_backups_are_rejected_and_change_nothing(conn, commitments, habits, reminders, tmp_path, make):
    seed(commitments, habits)
    path = tmp_path / "bad.db"
    if make == "garbage":
        path.write_bytes(b"this is not a database" * 50)
    elif make == "empty":
        path.write_bytes(b"")
    elif make == "wrong_schema":
        raw = sqlite3.connect(path)
        raw.execute("CREATE TABLE something_else(x)")
        raw.execute("PRAGMA user_version = 2")
        raw.close()
    else:
        path = tmp_path / "nope.db"
    with pytest.raises(ValidationError):
        data_service.restore_backup(conn, path, reminders)
    assert len(commitments.list("all")) == 1 and len(commitments.list("completed")) == 1


def test_backup_from_a_newer_app_version_is_refused(conn, tmp_path):
    path = tmp_path / "future.db"
    other = connect(path)
    other.execute(f"PRAGMA user_version = {migrations.LATEST_VERSION + 3}")
    other.close()
    with pytest.raises(ValidationError) as e:
        data_service.validate_backup(path)
    assert "err.backup_newer" in str(e.value.items)


def test_restoring_an_older_backup_upgrades_it(conn, tmp_path):
    old_path = tmp_path / "v1.db"
    old = sqlite3.connect(old_path, isolation_level=None)
    migrations.migrate(old, target=1)
    old.execute("INSERT INTO commitments (title, due_at, created_at, updated_at) VALUES "
                "('قديم','2026-10-20T10:00','2026-10-01T00:00:00','2026-10-01T00:00:00')")
    old.close()
    data_service.restore_backup(conn, old_path)
    assert migrations.get_version(conn) == migrations.LATEST_VERSION
    assert conn.execute("SELECT title, focus_date FROM commitments").fetchone()["title"] == "قديم"


def test_restore_also_restores_preferences(conn, tmp_path):
    Preferences(SettingsService(conn)).set("language", "en")
    backup = backup_service.export_backup(conn, tmp_path)
    Preferences(SettingsService(conn)).set("language", "ar")
    data_service.restore_backup(conn, backup)
    assert Preferences(SettingsService(conn)).get("language") == "en"


# ---------------- export ----------------
def test_csv_export_is_valid_utf8_with_arabic_and_quotes(conn, commitments, habits, tmp_path):
    seed(commitments, habits)
    path = data_service.export_csv(conn, tmp_path)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")             # BOM so Excel shows Arabic
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig", newline="")))
    assert len(rows) == 2
    important = next(r for r in rows if r["title"] == "التزام مهم")
    assert important["description"] == 'وصف, بفاصلة "وعلامات"' and important["priority"] == "high"
    assert set(rows[0]) == set(data_service.COMMITMENT_COLUMNS)


def test_json_export_contains_everything(conn, commitments, habits, tmp_path):
    seed(commitments, habits)
    data = json.loads(data_service.export_json(conn, tmp_path).read_text(encoding="utf-8"))
    assert data["schema_version"] == migrations.LATEST_VERSION
    assert len(data["commitments"]) == 2 and len(data["habits"]) == 1 and len(data["habit_records"]) == 1
    assert "التزام مهم" in {c["title"] for c in data["commitments"]}          # real Arabic, not \u escapes


def test_empty_database_exports_cleanly(conn, tmp_path):
    assert len(list(csv.reader(open(data_service.export_csv(conn, tmp_path), encoding="utf-8-sig")))) == 1
    assert json.loads(data_service.export_json(conn, tmp_path).read_text(encoding="utf-8"))["commitments"] == []


# ---------------- deletion ----------------
def test_delete_all_data_clears_data_and_reminders_but_keeps_preferences(conn, commitments, habits, reminders, backend):
    c, h = seed(commitments, habits)
    Preferences(SettingsService(conn)).set("user_name", "Sara")
    data_service.delete_all_data(conn, reminders)
    for table in ("commitments", "habits", "habit_records"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert f"c{c.id}" not in backend.scheduled
    assert Preferences(SettingsService(conn)).get("user_name") == "Sara"


# ---------------- migration v3 ----------------
def test_migration_3_keeps_existing_commitments_and_habits(tmp_path):
    path = tmp_path / "v2.db"
    old = sqlite3.connect(path, isolation_level=None)
    old.row_factory = sqlite3.Row
    migrations.migrate(old, target=2)
    old.execute("INSERT INTO commitments (title, due_at, priority, category, status, created_at, updated_at, completed_at) "
                "VALUES ('قديم','2026-10-20T10:00','high','عمل','completed','2026-10-01T00:00:00','2026-10-02T00:00:00','2026-10-02T00:00:00')")
    old.execute("INSERT INTO habits (name, start_date, created_at) VALUES ('عادة','2026-10-01','2026-10-01T00:00:00')")
    old.execute("INSERT INTO habit_records (habit_id, record_date, result, created_at, updated_at) "
                "VALUES (1,'2026-10-02','success','x','x')")
    old.close()
    upgraded = connect(path)
    row = upgraded.execute("SELECT * FROM commitments").fetchone()
    assert (row["title"], row["priority"], row["status"], row["focus_date"]) == ("قديم", "high", "completed", None)
    assert upgraded.execute("SELECT COUNT(*) FROM habit_records").fetchone()[0] == 1
    assert migrations.get_version(upgraded) == 3
    from app.models.models import Commitment
    assert Commitment.from_row(row).focus_date is None


def test_demo_data_still_works_after_changes(commitments, habits):
    assert add_demo_data(commitments, habits) > 0
