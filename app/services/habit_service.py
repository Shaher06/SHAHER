import logging
import sqlite3
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

from app.database.db import transaction
from app.models.models import Habit, HabitRecord, HabitStats
from app.services.habit_logic import compute_stats, day_state
from app.utils import dates
from app.utils.validation import ValidationError, validate_habit, validate_note

log = logging.getLogger("shaher.habits")
DEFAULT_TARGET_DAYS = 15
RESULTS = ("success", "setback")


class HabitService:
    def __init__(self, conn: sqlite3.Connection, reminders=None,
                 now_fn: Callable[[], datetime] = dates.now):
        self.conn = conn
        self.reminders = reminders
        self.now = now_fn

    def today(self) -> date:
        return self.now().date()

    # ---------- habits ----------
    def create(self, name, target_days=DEFAULT_TARGET_DAYS, reminder_enabled=False,
               reminder_time=None, is_demo=False, start_date: Optional[date] = None) -> Habit:
        data = validate_habit(name, target_days, reminder_enabled, reminder_time)
        start = start_date or self.today()
        with transaction(self.conn):
            cur = self.conn.execute(
                "INSERT INTO habits (name, start_date, target_days, reminder_enabled, reminder_time, "
                "status, created_at, is_demo) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
                (data["name"], start.strftime(dates.DATE_FMT), data["target_days"],
                 int(data["reminder_enabled"]), data["reminder_time"],
                 dates.to_ts(self.now()), int(is_demo)))
            habit_id = cur.lastrowid
        habit = self.get(habit_id)
        self._sync_reminder(habit)
        return habit

    def update(self, habit_id, name, target_days, reminder_enabled=False, reminder_time=None) -> Habit:
        self._require(habit_id)
        data = validate_habit(name, target_days, reminder_enabled, reminder_time)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE habits SET name=?, target_days=?, reminder_enabled=?, reminder_time=? WHERE id=?",
                (data["name"], data["target_days"], int(data["reminder_enabled"]),
                 data["reminder_time"], habit_id))
        habit = self.get(habit_id)
        self._sync_reminder(habit)
        return habit

    def archive(self, habit_id) -> Habit:
        self._require(habit_id)
        with transaction(self.conn):
            self.conn.execute("UPDATE habits SET status='archived', archived_at=? WHERE id=?",
                              (dates.to_ts(self.now()), habit_id))
        habit = self.get(habit_id)
        self._sync_reminder(habit)
        return habit    # records are kept untouched

    def restore(self, habit_id) -> Habit:
        self._require(habit_id)
        with transaction(self.conn):
            self.conn.execute("UPDATE habits SET status='active', archived_at=NULL WHERE id=?", (habit_id,))
        habit = self.get(habit_id)
        self._sync_reminder(habit)
        return habit

    def get(self, habit_id) -> Optional[Habit]:
        row = self.conn.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()
        return Habit.from_row(row) if row else None

    def list(self, include_archived=False) -> List[Habit]:
        sql = "SELECT * FROM habits" + ("" if include_archived else " WHERE status='active'") + " ORDER BY id"
        return [Habit.from_row(r) for r in self.conn.execute(sql)]

    # ---------- daily records ----------
    def record_day(self, habit_id, day: date, result: str, note: str = "") -> HabitRecord:
        """Record a result for a day. One record per habit per day: a second call for the
        same day is refused (use correct_record to change an existing one on purpose)."""
        habit = self._require(habit_id)
        self._check_recordable(habit, day, result)
        note = validate_note(note)
        ts = dates.to_ts(self.now())
        try:
            with transaction(self.conn):
                self.conn.execute(
                    "INSERT INTO habit_records (habit_id, record_date, result, note, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (habit_id, day.strftime(dates.DATE_FMT), result, note, ts, ts))
        except sqlite3.IntegrityError:
            raise ValidationError("err.record_exists")
        self._sync_reminder(habit)
        return self.get_record(habit_id, day)

    def correct_record(self, habit_id, day: date, result: str, note: str = "") -> HabitRecord:
        """Deliberate correction of an existing record. Streaks are always computed from the
        records, so every affected streak is recalculated automatically."""
        habit = self._require(habit_id)
        if self.get_record(habit_id, day) is None:
            raise ValidationError("err.no_record")
        self._check_recordable(habit, day, result)
        note = validate_note(note)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE habit_records SET result=?, note=?, updated_at=? WHERE habit_id=? AND record_date=?",
                (result, note, dates.to_ts(self.now()), habit_id, day.strftime(dates.DATE_FMT)))
        return self.get_record(habit_id, day)

    def clear_record(self, habit_id, day: date) -> None:
        """Remove a day's record (the day becomes unrecorded). UI should confirm first."""
        self._require(habit_id)
        with transaction(self.conn):
            self.conn.execute("DELETE FROM habit_records WHERE habit_id=? AND record_date=?",
                              (habit_id, day.strftime(dates.DATE_FMT)))

    def get_record(self, habit_id, day: date) -> Optional[HabitRecord]:
        row = self.conn.execute("SELECT * FROM habit_records WHERE habit_id=? AND record_date=?",
                                (habit_id, day.strftime(dates.DATE_FMT))).fetchone()
        return HabitRecord.from_row(row) if row else None

    def records(self, habit_id) -> List[HabitRecord]:
        rows = self.conn.execute("SELECT * FROM habit_records WHERE habit_id=? ORDER BY record_date DESC",
                                 (habit_id,))
        return [HabitRecord.from_row(r) for r in rows]

    def record_map(self, habit_id) -> Dict[date, str]:
        return {r.record_date: r.result for r in self.records(habit_id)}

    # ---------- statistics ----------
    def stats(self, habit_id) -> HabitStats:
        habit = self._require(habit_id)
        return compute_stats(self.record_map(habit_id), self.today(), habit.target_days)

    def history(self, habit_id, max_days: int = 60) -> List[Tuple[date, str, Optional[HabitRecord]]]:
        """Newest first: (date, state, record) from today back to the start (max `max_days`)."""
        habit = self._require(habit_id)
        today = self.today()
        recs = {r.record_date: r for r in self.records(habit_id)}
        states = {d: r.result for d, r in recs.items()}
        first = max(habit.start_date, today - timedelta(days=max_days - 1))
        out = []
        for d in reversed(dates.date_range(min(first, today), today)):
            out.append((d, day_state(states, d, today), recs.get(d)))
        return out

    # ---------- internals ----------
    def _require(self, habit_id) -> Habit:
        habit = self.get(habit_id)
        if habit is None:
            raise ValidationError("err.habit_not_found")
        return habit

    def _check_recordable(self, habit: Habit, day: date, result: str) -> None:
        if result not in RESULTS:
            raise ValidationError("err.result_invalid")
        if habit.status != "active":
            raise ValidationError("err.habit_archived")
        if day > self.today():
            raise ValidationError("err.future_day")
        if day < habit.start_date:
            raise ValidationError("err.before_start")

    def _sync_reminder(self, habit: Habit) -> None:
        if self.reminders is not None:
            try:
                self.reminders.sync_habit(habit)
            except Exception:
                log.exception("could not sync reminder for habit %s", habit.id)
