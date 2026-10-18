from datetime import date, datetime

import pytest

from app.services import backup_service
from app.services.demo_data import add_demo_data, remove_demo_data
from app.services.settings_service import SettingsService
from app.utils import dates
from app.utils.validation import ValidationError, validate_commitment


def test_arabic_digits_are_accepted():
    assert dates.parse_date("٢٠٢٦-١٠-١٣") == date(2026, 10, 13)
    assert dates.parse_time("٠٩:٣٠").hour == 9
    assert dates.combine("2026-10-13", "7:05") == datetime(2026, 10, 13, 7, 5)


@pytest.mark.parametrize("bad", ["2026-13-01", "13/10/2026", "", "abc"])
def test_bad_dates_raise(bad):
    with pytest.raises(ValueError):
        dates.parse_date(bad)


def test_friendly_labels():
    today = date(2026, 10, 13)
    assert dates.friendly_due(datetime(2026, 10, 13, 18, 30), today) == "اليوم 18:30"
    assert dates.friendly_due(datetime(2026, 10, 14, 9, 0), today) == "غدًا 09:00"
    assert dates.format_date_ar(today) == "الثلاثاء 13 أكتوبر 2026"


def test_validate_commitment_collects_all_errors():
    with pytest.raises(ValidationError) as e:
        validate_commitment("", "", None, "bad", "", False, None)
    assert len(e.value.errors) == 3


def test_settings_defaults_and_malformed(conn):
    s = SettingsService(conn)
    assert s.get_int("reminder_offset_minutes", 30) == 30        # default
    s.set("reminder_offset_minutes", "abc")
    assert s.get_int("reminder_offset_minutes", 30) == 30        # malformed -> default
    s.set("reminder_offset_minutes", 60)
    assert s.get_int("reminder_offset_minutes", 30) == 60
    s.set("reminder_offset_minutes", 10)                         # overwrite works
    assert s.get_int("reminder_offset_minutes", 30) == 10


def test_backup_is_a_valid_database(conn, commitments, tmp_path):
    commitments.create("مهمة", "", datetime(2026, 10, 15, 9, 0))
    path = backup_service.export_backup(conn, tmp_path / "bk")
    assert path.exists() and path.stat().st_size > 0
    from app.database.db import connect
    copy = connect(path)
    assert copy.execute("SELECT title FROM commitments").fetchone()[0] == "مهمة"
    assert backup_service.list_backups(tmp_path / "bk") == [path]


def test_demo_data_is_removable_and_leaves_real_data(conn, commitments, habits, reminders):
    real = commitments.create("حقيقي", "", datetime(2026, 10, 20, 9, 0))
    real_habit = habits.create("عادة حقيقية")
    added = add_demo_data(commitments, habits)
    assert added > 0 and len(commitments.list("all")) > 1
    remove_demo_data(conn, reminders)
    assert [c.id for c in commitments.list("all")] == [real.id]
    assert [h.id for h in habits.list()] == [real_habit.id]


def test_nothing_is_created_on_startup(conn):
    for table in ("commitments", "habits", "habit_records"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
