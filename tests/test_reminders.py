from datetime import datetime

import pytest

from app.utils.validation import ValidationError

D = datetime


def test_reminder_scheduled_and_persisted(commitments, backend, conn):
    c = commitments.create("مهمة", "", D(2026, 10, 14, 10, 0),
                           reminder_enabled=True, reminder_at=D(2026, 10, 14, 9, 30))
    assert backend.scheduled["c%d" % c.id][1] == D(2026, 10, 14, 9, 30)
    stored = commitments.get(c.id)
    assert stored.reminder_enabled and stored.reminder_at == D(2026, 10, 14, 9, 30)


def test_reminder_cancelled_on_complete_archive_disable_and_delete(commitments, backend):
    c = commitments.create("مهمة", "", D(2026, 10, 14, 10, 0), reminder_enabled=True,
                           reminder_at=D(2026, 10, 14, 9, 0))
    key = f"c{c.id}"
    commitments.complete(c.id)
    assert key not in backend.scheduled
    commitments.reopen(c.id)
    assert key in backend.scheduled                    # rescheduled when reopened
    commitments.archive(c.id)
    assert key not in backend.scheduled
    commitments.restore(c.id)
    commitments.update(c.id, "مهمة", "", D(2026, 10, 14, 10, 0), "medium", "", reminder_enabled=False)
    assert key not in backend.scheduled
    commitments.delete(c.id)
    assert key not in backend.scheduled


def test_changing_due_and_reminder_reschedules(commitments, backend):
    c = commitments.create("مهمة", "", D(2026, 10, 14, 10, 0), reminder_enabled=True,
                           reminder_at=D(2026, 10, 14, 9, 0))
    commitments.update(c.id, "مهمة", "", D(2026, 10, 15, 10, 0), "medium", "",
                       reminder_enabled=True, reminder_at=D(2026, 10, 15, 9, 0))
    assert backend.scheduled[f"c{c.id}"][1] == D(2026, 10, 15, 9, 0)


def test_reminder_validation(commitments):
    with pytest.raises(ValidationError):   # enabled but no time
        commitments.create("أ", "", D(2026, 10, 14, 10, 0), reminder_enabled=True)
    with pytest.raises(ValidationError):   # after the due time
        commitments.create("ب", "", D(2026, 10, 14, 10, 0), reminder_enabled=True,
                           reminder_at=D(2026, 10, 14, 11, 0))
    with pytest.raises(ValidationError):   # already in the past
        commitments.create("ج", "", D(2026, 10, 14, 10, 0), reminder_enabled=True,
                           reminder_at=D(2026, 10, 13, 8, 0))


def test_resync_all_restores_schedule(commitments, reminders, backend):
    c = commitments.create("مهمة", "", D(2026, 10, 14, 10, 0), reminder_enabled=True,
                           reminder_at=D(2026, 10, 14, 9, 0))
    backend.scheduled.clear()                          # e.g. the OS lost its alarms
    reminders.resync_all()
    assert f"c{c.id}" in backend.scheduled


def test_in_app_fallback_fires_once(commitments, reminders, clock):
    c = commitments.create("مهمة", "", D(2026, 10, 13, 15, 0), reminder_enabled=True,
                           reminder_at=D(2026, 10, 13, 14, 0))
    assert reminders.due_in_app() == []
    clock.set(D(2026, 10, 13, 14, 1))
    due = reminders.due_in_app()
    assert [d.id for d in due] == [c.id]
    reminders.mark_shown(c.id)
    assert reminders.due_in_app() == []


def test_habit_daily_reminder(habits, backend):
    h = habits.create("قراءة", 15, reminder_enabled=True, reminder_time="21:30")
    assert backend.daily[f"h{h.id}"] == "21:30"
    habits.archive(h.id)
    assert f"h{h.id}" not in backend.daily
