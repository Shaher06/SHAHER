from datetime import date, datetime, timedelta

import pytest

from app.services.habit_logic import compute_stats, day_state
from app.utils.validation import ValidationError

TODAY = date(2026, 10, 13)


def d(n):
    """n days before TODAY."""
    return TODAY - timedelta(days=n)


def make(habits, clock, name="قراءة", target=15, days_ago=30):
    clock.set(datetime(2026, 10, 13, 12, 0))
    return habits.create(name, target, start_date=d(days_ago))


# ---------- pure logic ----------
def test_consecutive_streak_and_totals():
    s = compute_stats({d(2): "success", d(1): "success", d(0): "success"}, TODAY, 15)
    assert (s.current_streak, s.longest_streak, s.total_success) == (3, 3, 3)


def test_setback_resets_current_but_keeps_history():
    recs = {d(5): "success", d(4): "success", d(3): "success", d(2): "setback", d(1): "success"}
    s = compute_stats(recs, TODAY, 15)
    assert s.current_streak == 1          # restarted after the setback
    assert s.longest_streak == 3          # earlier successes are not erased
    assert s.total_success == 4 and s.total_setbacks == 1


def test_setback_today_sets_current_to_zero():
    s = compute_stats({d(2): "success", d(1): "success", d(0): "setback"}, TODAY, 15)
    assert s.current_streak == 0 and s.longest_streak == 2 and s.today_state == "setback"


def test_new_streak_after_setback():
    recs = {d(4): "success", d(3): "setback", d(2): "success", d(1): "success", d(0): "success"}
    s = compute_stats(recs, TODAY, 15)
    assert s.current_streak == 3 and s.longest_streak == 3


def test_unrecorded_day_is_not_success_and_breaks_streak():
    recs = {d(4): "success", d(3): "success", d(1): "success"}      # d(2) unrecorded
    s = compute_stats(recs, TODAY, 15)
    assert s.longest_streak == 2 and s.current_streak == 1 and s.total_success == 3


def test_today_unrecorded_does_not_break_streak():
    s = compute_stats({d(2): "success", d(1): "success"}, TODAY, 15)
    assert s.current_streak == 2 and s.today_state == "pending"


def test_two_unrecorded_days_end_current_streak():
    s = compute_stats({d(3): "success", d(2): "success"}, TODAY, 15)   # yesterday and today empty
    assert s.current_streak == 0 and s.longest_streak == 2


def test_target_completion_requires_consecutive_days():
    gap = {d(i): "success" for i in range(10, 0, -1) if i != 5}       # 9 days with a gap
    assert not compute_stats(gap, TODAY, 10).completed
    full = {d(i): "success" for i in range(9, -1, -1)}                # 10 in a row
    s = compute_stats(full, TODAY, 10)
    assert s.completed and s.completed_on == TODAY and s.progress == 1.0


def test_completion_is_kept_after_a_later_setback():
    recs = {d(i): "success" for i in range(12, 2, -1)}                 # 10 in a row, ending d(3)
    recs[d(1)] = "setback"
    s = compute_stats(recs, TODAY, 10)
    assert s.completed and s.current_streak == 0


def test_progress_fraction():
    s = compute_stats({d(1): "success", d(0): "success"}, TODAY, 8)
    assert s.progress == 0.25


def test_day_states():
    recs = {d(1): "success"}
    assert day_state(recs, d(1), TODAY) == "success"
    assert day_state(recs, d(2), TODAY) == "missed"
    assert day_state(recs, d(0), TODAY) == "pending"
    assert day_state(recs, TODAY + timedelta(days=1), TODAY) == "future"


# ---------- service ----------
def test_default_target_is_15(habits):
    assert habits.create("مشي").target_days == 15


def test_record_and_stats(habits, clock):
    h = make(habits, clock)
    for i in (3, 2, 1, 0):
        habits.record_day(h.id, d(i), "success")
    s = habits.stats(h.id)
    assert s.current_streak == 4 and s.total_success == 4


def test_duplicate_record_for_same_day_prevented(habits, clock, conn):
    h = make(habits, clock)
    habits.record_day(h.id, d(0), "success")
    with pytest.raises(ValidationError):
        habits.record_day(h.id, d(0), "setback")
    assert conn.execute("SELECT COUNT(*) FROM habit_records").fetchone()[0] == 1
    assert habits.get_record(h.id, d(0)).result == "success"


def test_independent_histories(habits, clock):
    a, b = make(habits, clock, "أ"), make(habits, clock, "ب")
    habits.record_day(a.id, d(1), "success")
    habits.record_day(a.id, d(0), "success")
    habits.record_day(b.id, d(1), "setback")
    assert habits.stats(a.id).current_streak == 2
    assert habits.stats(b.id).current_streak == 0 and habits.stats(b.id).total_success == 0
    assert len(habits.records(a.id)) == 2 and len(habits.records(b.id)) == 1


def test_setback_preserves_earlier_records_in_database(habits, clock):
    h = make(habits, clock)
    habits.record_day(h.id, d(2), "success")
    habits.record_day(h.id, d(1), "success")
    habits.record_day(h.id, d(0), "setback", "تعبت")
    assert [r.result for r in habits.records(h.id)] == ["setback", "success", "success"]
    assert habits.stats(h.id).longest_streak == 2


def test_correction_recalculates_streaks(habits, clock):
    h = make(habits, clock)
    for i in (3, 2, 1, 0):
        habits.record_day(h.id, d(i), "success")
    assert habits.stats(h.id).current_streak == 4
    habits.correct_record(h.id, d(2), "setback", "كنت مخطئًا")
    s = habits.stats(h.id)
    assert s.current_streak == 2 and s.longest_streak == 2
    habits.correct_record(h.id, d(2), "success")
    assert habits.stats(h.id).current_streak == 4


def test_correction_requires_existing_record_and_clear_makes_unrecorded(habits, clock):
    h = make(habits, clock)
    with pytest.raises(ValidationError):
        habits.correct_record(h.id, d(1), "success")
    habits.record_day(h.id, d(1), "success")
    habits.clear_record(h.id, d(1))
    assert habits.get_record(h.id, d(1)) is None


def test_cannot_record_future_or_before_start_or_archived(habits, clock):
    h = make(habits, clock, days_ago=3)
    with pytest.raises(ValidationError):
        habits.record_day(h.id, d(-1), "success")
    with pytest.raises(ValidationError):
        habits.record_day(h.id, d(10), "success")
    habits.archive(h.id)
    with pytest.raises(ValidationError):
        habits.record_day(h.id, d(0), "success")


def test_archive_keeps_history(habits, clock):
    h = make(habits, clock)
    habits.record_day(h.id, d(0), "success")
    habits.archive(h.id)
    assert h.id not in [x.id for x in habits.list()]
    assert h.id in [x.id for x in habits.list(include_archived=True)]
    assert len(habits.records(h.id)) == 1
    habits.restore(h.id)
    assert habits.get(h.id).status == "active"


def test_unopened_app_creates_no_setbacks(habits, clock, conn):
    h = make(habits, clock, days_ago=10)
    clock.set(datetime(2026, 10, 20, 9, 0))       # a week passes without recording anything
    assert conn.execute("SELECT COUNT(*) FROM habit_records").fetchone()[0] == 0
    s = habits.stats(h.id)
    assert s.total_setbacks == 0 and s.current_streak == 0


def test_midnight_boundary_uses_local_calendar_day(habits, clock):
    clock.set(datetime(2026, 10, 13, 23, 59, 59))
    h = habits.create("ليلي", 15, start_date=date(2026, 10, 12))
    habits.record_day(h.id, date(2026, 10, 13), "success")
    clock.set(datetime(2026, 10, 14, 0, 0, 1))                 # just after midnight
    s = habits.stats(h.id)
    assert s.current_streak == 1 and s.today_state == "pending"   # today is not "missed" yet
    habits.record_day(h.id, date(2026, 10, 14), "success")
    assert habits.stats(h.id).current_streak == 2


def test_history_view(habits, clock):
    h = make(habits, clock, days_ago=3)
    habits.record_day(h.id, d(2), "success")
    hist = habits.history(h.id)
    assert [x[0] for x in hist] == [d(0), d(1), d(2), d(3)]
    assert [x[1] for x in hist] == ["pending", "missed", "success", "missed"]


@pytest.mark.parametrize("name,target,rem,time", [
    ("", 15, False, None), ("ع", 0, False, None), ("ع", "abc", False, None), ("ع", 15, True, "25:99"),
])
def test_habit_validation(habits, name, target, rem, time):
    with pytest.raises(ValidationError):
        habits.create(name, target, reminder_enabled=rem, reminder_time=time)
