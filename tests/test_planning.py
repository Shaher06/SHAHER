from datetime import date, datetime, timedelta

import pytest

from app.utils.validation import ValidationError

D = datetime


def test_reschedule_moves_item_and_keeps_reminder_lead_time(commitments, backend):
    c = commitments.create("مهمة", "", D(2026, 10, 14, 10, 0), reminder_enabled=True, reminder_at=D(2026, 10, 14, 9, 30))
    moved = commitments.reschedule(c.id, D(2026, 10, 16, 15, 0))
    assert moved.due_at == D(2026, 10, 16, 15, 0) and moved.reminder_at == D(2026, 10, 16, 14, 30)
    assert backend.scheduled[f"c{c.id}"][1] == D(2026, 10, 16, 14, 30)      # one reminder, rescheduled
    assert moved.title == "مهمة" and moved.status == "open"


def test_reschedule_overdue_item_into_the_future(commitments):
    c = commitments.create("متأخر", "", D(2026, 10, 10, 9, 0))
    assert commitments.list("overdue")[0].id == c.id
    commitments.reschedule(c.id, D(2026, 10, 15, 9, 0))
    assert commitments.list("overdue") == [] and commitments.list("upcoming")[0].id == c.id


def test_reschedule_disables_a_reminder_that_would_be_in_the_past(commitments, backend):
    c = commitments.create("مهمة", "", D(2026, 10, 14, 18, 0), reminder_enabled=True, reminder_at=D(2026, 10, 14, 12, 30))
    moved = commitments.reschedule(c.id, D(2026, 10, 13, 12, 10))          # due in 10 min; lead was 5.5h
    assert not moved.reminder_enabled and moved.reminder_at is None
    assert f"c{c.id}" not in backend.scheduled


def test_reschedule_only_open_items(commitments):
    c = commitments.create("مهمة", "", D(2026, 10, 14, 9, 0))
    commitments.complete(c.id)
    with pytest.raises(ValidationError):
        commitments.reschedule(c.id, D(2026, 10, 20, 9, 0))


def test_reschedule_many_keeps_time_of_day(commitments):
    a = commitments.create("أ", "", D(2026, 10, 12, 17, 30))
    b = commitments.create("ب", "", D(2026, 10, 13, 15, 0))
    moved = commitments.reschedule_many([a.id, b.id], date(2026, 10, 14))
    assert moved == 2
    assert commitments.get(a.id).due_at == D(2026, 10, 14, 17, 30)
    assert commitments.get(b.id).due_at == D(2026, 10, 14, 15, 0)


def test_focus_items_are_per_day_and_open_only(commitments, clock):
    a = commitments.create("أ", "", D(2026, 10, 13, 20, 0)); b = commitments.create("ب", "", D(2026, 10, 13, 21, 0))
    commitments.set_focus(a.id, True); commitments.set_focus(b.id, True)
    assert {c.id for c in commitments.focus_items()} == {a.id, b.id}
    commitments.set_focus(b.id, False)
    assert [c.id for c in commitments.focus_items()] == [a.id]
    commitments.complete(a.id)
    assert commitments.focus_items() == []
    clock.set(D(2026, 10, 14, 8, 0))
    assert commitments.focus_items() == []                               # yesterday's focus doesn't carry over


def test_daily_progress_uses_real_counts(commitments, clock):
    a = commitments.create("أ", "", D(2026, 10, 13, 20, 0)); commitments.create("ب", "", D(2026, 10, 13, 21, 0))
    commitments.create("ج", "", D(2026, 10, 12, 9, 0))                   # overdue still counts as "to do"
    commitments.create("د", "", D(2026, 10, 14, 9, 0))                   # tomorrow: not part of today
    assert commitments.daily_progress() == (0, 3)
    commitments.complete(a.id)
    assert commitments.daily_progress() == (1, 3) and commitments.completed_today() == 1


def test_week_overview_groups_open_items_by_day(commitments):
    commitments.create("اليوم", "", D(2026, 10, 13, 20, 0)); commitments.create("بعد يومين", "", D(2026, 10, 15, 8, 0))
    commitments.create("بعد يومين 2", "", D(2026, 10, 15, 18, 0))
    done = commitments.create("خلصان", "", D(2026, 10, 15, 9, 0)); commitments.complete(done.id)
    week = commitments.week_overview(date(2026, 10, 13))
    assert [len(items) for _, items in week] == [1, 0, 2, 0, 0, 0, 0]
    assert week[0][0] == date(2026, 10, 13) and week[6][0] == date(2026, 10, 19)


def test_sorting_modes(commitments):
    commitments.create("منخفض صباحًا", "", D(2026, 10, 14, 8, 0), "low")
    commitments.create("عالٍ مساءً", "", D(2026, 10, 14, 20, 0), "high")
    commitments.create("متوسط", "", D(2026, 10, 15, 9, 0), "medium")
    assert [c.title for c in commitments.list("all", sort="date")] == ["منخفض صباحًا", "عالٍ مساءً", "متوسط"]
    assert [c.title for c in commitments.list("all", sort="priority")] == ["عالٍ مساءً", "متوسط", "منخفض صباحًا"]
    assert [c.title for c in commitments.list("all", sort="urgency")] == ["عالٍ مساءً", "منخفض صباحًا", "متوسط"]


def test_new_features_do_not_change_old_behaviour(commitments):
    c = commitments.create("مهمة", "", D(2026, 10, 14, 9, 0))
    assert c.focus_date is None
    commitments.complete(c.id); commitments.reopen(c.id)
    assert commitments.get(c.id).status == "open"
