"""All business rules for commitments live here (screens never touch SQL)."""
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from app.database.db import transaction
from app.models.models import Commitment
from app.utils import dates
from app.utils.validation import ValidationError, validate_commitment

log = logging.getLogger("shaher.commitments")

VIEWS = ("all", "today", "upcoming", "overdue", "completed", "archived")


class CommitmentService:
    def __init__(self, conn: sqlite3.Connection, reminders=None,
                 now_fn: Callable[[], datetime] = dates.now):
        self.conn = conn
        self.reminders = reminders      # optional ReminderService
        self.now = now_fn

    # ---------- create / update ----------
    def create(self, title, description, due_at, priority="medium", category="",
               reminder_enabled=False, reminder_at=None, is_demo=False) -> Commitment:
        data = validate_commitment(title, description, due_at, priority, category,
                                   reminder_enabled, reminder_at)
        self._check_reminder_in_future(data, previous_reminder=None)
        ts = dates.to_ts(self.now())
        due = dates.to_dt_str(data["due_at"])
        # Guard against double taps / repeated submissions of the same form.
        dup = self.conn.execute(
            "SELECT id FROM commitments WHERE status = 'open' AND due_at = ? "
            "AND lower(title) = lower(?)", (due, data["title"])).fetchone()
        if dup:
            raise ValidationError("err.duplicate_open")
        try:
            with transaction(self.conn):
                cur = self.conn.execute(
                    "INSERT INTO commitments (title, description, due_at, priority, category, status, "
                    "reminder_enabled, reminder_at, created_at, updated_at, is_demo) "
                    "VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)",
                    (data["title"], data["description"], due, data["priority"], data["category"],
                     int(data["reminder_enabled"]), _fmt(data["reminder_at"]), ts, ts, int(is_demo)))
                new_id = cur.lastrowid
        except sqlite3.Error:
            log.exception("create commitment failed")
            raise
        item = self.get(new_id)
        self._sync_reminder(item)
        return item

    def update(self, commitment_id: int, title, description, due_at, priority, category,
               reminder_enabled=False, reminder_at=None) -> Commitment:
        current = self._require(commitment_id)
        data = validate_commitment(title, description, due_at, priority, category,
                                   reminder_enabled, reminder_at)
        self._check_reminder_in_future(data, previous_reminder=current.reminder_at)
        dup = self.conn.execute(
            "SELECT id FROM commitments WHERE status = 'open' AND due_at = ? "
            "AND lower(title) = lower(?) AND id <> ?",
            (dates.to_dt_str(data["due_at"]), data["title"], commitment_id)).fetchone()
        if dup:
            raise ValidationError("err.duplicate_other")
        # Changing the reminder time must allow it to fire again.
        reset_sent = current.reminder_at != data["reminder_at"] or not data["reminder_enabled"]
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE commitments SET title=?, description=?, due_at=?, priority=?, category=?, "
                "reminder_enabled=?, reminder_at=?, updated_at=?"
                + (", reminder_sent_at=NULL" if reset_sent else "") + " WHERE id=?",
                (data["title"], data["description"], dates.to_dt_str(data["due_at"]),
                 data["priority"], data["category"], int(data["reminder_enabled"]),
                 _fmt(data["reminder_at"]), dates.to_ts(self.now()), commitment_id))
        item = self.get(commitment_id)
        self._sync_reminder(item)
        return item

    # ---------- status changes ----------
    def complete(self, commitment_id: int) -> Commitment:
        item = self._require(commitment_id)
        if item.status != "open":
            raise ValidationError("err.only_open_complete")
        ts = dates.to_ts(self.now())
        with transaction(self.conn):
            self.conn.execute("UPDATE commitments SET status='completed', completed_at=?, updated_at=? "
                              "WHERE id=?", (ts, ts, commitment_id))
        return self._after_status_change(commitment_id)

    def reopen(self, commitment_id: int) -> Commitment:
        item = self._require(commitment_id)
        if item.status != "completed":
            raise ValidationError("err.only_completed_reopen")
        with transaction(self.conn):
            self.conn.execute("UPDATE commitments SET status='open', completed_at=NULL, updated_at=? "
                              "WHERE id=?", (dates.to_ts(self.now()), commitment_id))
        return self._after_status_change(commitment_id)

    def archive(self, commitment_id: int) -> Commitment:
        item = self._require(commitment_id)
        if item.status == "archived":
            return item
        ts = dates.to_ts(self.now())
        # completed_at is kept, so the history of a finished task is not lost.
        with transaction(self.conn):
            self.conn.execute("UPDATE commitments SET status='archived', archived_at=?, updated_at=? "
                              "WHERE id=?", (ts, ts, commitment_id))
        return self._after_status_change(commitment_id)

    def restore(self, commitment_id: int) -> Commitment:
        """Bring an archived commitment back (as completed if it had been completed)."""
        item = self._require(commitment_id)
        if item.status != "archived":
            raise ValidationError("err.not_archived")
        new_status = "completed" if item.completed_at else "open"
        with transaction(self.conn):
            self.conn.execute("UPDATE commitments SET status=?, archived_at=NULL, updated_at=? WHERE id=?",
                              (new_status, dates.to_ts(self.now()), commitment_id))
        return self._after_status_change(commitment_id)

    def delete(self, commitment_id: int) -> None:
        """Permanent delete. The UI must ask for confirmation first."""
        self._require(commitment_id)
        with transaction(self.conn):
            self.conn.execute("DELETE FROM commitments WHERE id=?", (commitment_id,))
        if self.reminders:
            self.reminders.cancel_commitment(commitment_id)

    # ---------- reading ----------
    def get(self, commitment_id: int) -> Optional[Commitment]:
        row = self.conn.execute("SELECT * FROM commitments WHERE id=?", (commitment_id,)).fetchone()
        return Commitment.from_row(row) if row else None

    def list(self, view: str = "all", query: str = "", priority: str = "",
             category: str = "", limit: Optional[int] = None, sort: str = "date") -> List[Commitment]:
        """view: all (open ones) | today | upcoming | overdue | completed | archived.

        Partition of OPEN items (they never overlap):
          overdue  = due time already passed
          today    = due later today
          upcoming = due on a later day
        """
        now = self.now()
        now_s = dates.to_dt_str(now)
        _, today_end = dates.day_bounds(now.date())
        where, args, order = [], [], "due_at ASC"
        if view == "completed":
            where.append("status = 'completed'"); order = "completed_at DESC"
        elif view == "archived":
            where.append("status = 'archived'"); order = "archived_at DESC"
        else:
            where.append("status = 'open'")
            if view == "overdue":
                where.append("due_at < ?"); args.append(now_s)
            elif view == "today":
                where.append("due_at >= ? AND due_at < ?"); args += [now_s, today_end]
            elif view == "upcoming":
                where.append("due_at >= ?"); args.append(today_end)
            elif view != "all":
                raise ValueError(f"unknown view {view!r}")
        if query.strip():
            like = f"%{_escape_like(query.strip())}%"
            where.append("(title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\' "
                         "OR category LIKE ? ESCAPE '\\')")
            args += [like, like, like]
        if priority:
            where.append("priority = ?"); args.append(priority)
        if category:
            where.append("category = ?"); args.append(category)
        rank = "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END"
        if view not in ("completed", "archived"):
            if sort == "priority":
                order = f"{rank}, due_at ASC"
            elif sort == "urgency":      # earliest day first; inside one day, high priority first
                order = f"substr(due_at, 1, 10), {rank}, due_at ASC"
        sql = "SELECT * FROM commitments WHERE " + " AND ".join(where) + f" ORDER BY {order}"
        if limit:
            sql += " LIMIT ?"; args = list(args) + [int(limit)]
        return [Commitment.from_row(r) for r in self.conn.execute(sql, args)]

    # ---------- rescheduling, focus, planning ----------
    def reschedule(self, commitment_id: int, new_due: datetime) -> Commitment:
        """Move to a new date/time. A reminder keeps the same lead time; if that moment is
        already past it is switched off (the user is told by the UI)."""
        item = self._require(commitment_id)
        if item.status != "open":
            raise ValidationError("err.only_open_complete")
        new_due = new_due.replace(second=0, microsecond=0)
        reminder_at, enabled = item.reminder_at, item.reminder_enabled
        if enabled and reminder_at:
            reminder_at = new_due - (item.due_at - reminder_at)
            if reminder_at < self.now():
                enabled, reminder_at = False, None
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE commitments SET due_at=?, reminder_enabled=?, reminder_at=?, "
                "reminder_sent_at=NULL, updated_at=? WHERE id=?",
                (dates.to_dt_str(new_due), int(enabled), _fmt(reminder_at),
                 dates.to_ts(self.now()), commitment_id))
        updated = self.get(commitment_id)
        self._sync_reminder(updated)
        return updated

    def reschedule_many(self, ids, day) -> int:
        """Move several open items to `day`, keeping each one's time of day (09:00 if that
        time has already passed on that day). Returns how many moved."""
        moved = 0
        for cid in ids:
            item = self.get(cid)
            if item is None or item.status != "open":
                continue
            due = datetime.combine(day, item.due_at.time())
            if due <= self.now():
                due = datetime.combine(day, datetime.min.time()).replace(hour=9)
            self.reschedule(cid, due)
            moved += 1
        return moved

    def set_focus(self, commitment_id: int, on: bool, day=None) -> None:
        self._require(commitment_id)
        day = day or self.now().date()
        with transaction(self.conn):
            self.conn.execute("UPDATE commitments SET focus_date=? WHERE id=?",
                              (day.strftime(dates.DATE_FMT) if on else None, commitment_id))

    def focus_items(self, day=None) -> List[Commitment]:
        day = day or self.now().date()
        rows = self.conn.execute(
            "SELECT * FROM commitments WHERE focus_date=? AND status='open' ORDER BY due_at",
            (day.strftime(dates.DATE_FMT),))
        return [Commitment.from_row(r) for r in rows]

    def list_day(self, day, include_overdue=False) -> List[Commitment]:
        """Open items due on a given calendar day (optionally also everything overdue before it)."""
        start, end = dates.day_bounds(day)
        if include_overdue:
            rows = self.conn.execute("SELECT * FROM commitments WHERE status='open' AND due_at < ? "
                                     "ORDER BY due_at", (end,))
        else:
            rows = self.conn.execute("SELECT * FROM commitments WHERE status='open' AND due_at >= ? "
                                     "AND due_at < ? ORDER BY due_at", (start, end))
        return [Commitment.from_row(r) for r in rows]

    def week_overview(self, start_day, days: int = 7):
        """[(date, [open commitments due that day])] for `days` days from start_day."""
        out = []
        for i in range(days):
            d = start_day + timedelta(days=i)
            out.append((d, self.list_day(d)))
        return out

    def completed_today(self) -> int:
        start, end = dates.day_bounds(self.now().date())
        start_ts, end_ts = start + ":00", end + ":00"
        return self.conn.execute(
            "SELECT COUNT(*) FROM commitments WHERE status='completed' AND completed_at >= ? AND completed_at < ?",
            (start_ts, end_ts)).fetchone()[0]

    def remaining_today(self) -> int:
        """Open items that are due today or already overdue."""
        _, end = dates.day_bounds(self.now().date())
        return self.conn.execute("SELECT COUNT(*) FROM commitments WHERE status='open' AND due_at < ?",
                                 (end,)).fetchone()[0]

    def daily_progress(self):
        """(done today, done today + still to do today). Honest numbers from the database."""
        done, left = self.completed_today(), self.remaining_today()
        return done, done + left

    def counts(self) -> dict:
        now = self.now()
        return {
            "today": len(self.list("today")),
            "overdue": len(self.list("overdue")),
            "upcoming": len(self.list("upcoming")),
            "completed": len(self.list("completed")),
        }

    def focus_list(self, limit: int = 6) -> List[Commitment]:
        """Most relevant now: overdue first, then today, then upcoming."""
        items = self.list("overdue") + self.list("today") + self.list("upcoming")
        return items[:limit]

    def categories(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT category FROM commitments WHERE category <> '' ORDER BY category")
        return [r[0] for r in rows]

    # ---------- internals ----------
    def _require(self, commitment_id: int) -> Commitment:
        item = self.get(commitment_id)
        if item is None:
            raise ValidationError("err.not_found")
        return item

    def _after_status_change(self, commitment_id: int) -> Commitment:
        item = self.get(commitment_id)
        self._sync_reminder(item)
        return item

    def _sync_reminder(self, item: Commitment) -> None:
        if self.reminders is not None:
            try:
                self.reminders.sync_commitment(item)
            except Exception:  # a reminder problem must never lose or block user data
                log.exception("could not sync reminder for commitment %s", item.id)

    def _check_reminder_in_future(self, data: dict, previous_reminder: Optional[datetime]) -> None:
        r = data["reminder_at"]
        if data["reminder_enabled"] and r is not None and r != previous_reminder and r < self.now():
            raise ValidationError("err.reminder_past")


def _fmt(dt: Optional[datetime]) -> Optional[str]:
    return dates.to_dt_str(dt) if dt else None


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
