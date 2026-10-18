import logging
import sqlite3
from datetime import datetime
from typing import Callable, List

from app.i18n import t
from app.models.models import Commitment, Habit
from app.services.reminder_backends import InAppBackend, ReminderBackend
from app.utils import dates

log = logging.getLogger("shaher.reminders")


def commitment_key(commitment_id: int) -> str:
    return f"c{commitment_id}"


def habit_key(habit_id: int) -> str:
    return f"h{habit_id}"


class ReminderService:
    """Keeps scheduled reminders in step with the database."""

    def __init__(self, conn: sqlite3.Connection, backend: ReminderBackend = None,
                 now_fn: Callable[[], datetime] = dates.now):
        self.conn = conn
        self.backend = backend or InAppBackend()
        self.now = now_fn

    # ----- commitments -----
    def sync_commitment(self, c: Commitment) -> None:
        """Schedule when open + reminder on + time in the future; otherwise cancel."""
        key = commitment_key(c.id)
        if c.status == "open" and c.reminder_enabled and c.reminder_at and c.reminder_at > self.now():
            self.backend.schedule(key, c.title, t("notif.commitment_body", when=dates.friendly_due(c.due_at, self.now().date())),
                                  c.reminder_at)
        else:
            self.backend.cancel(key)

    def cancel_commitment(self, commitment_id: int) -> None:
        self.backend.cancel(commitment_key(commitment_id))

    # ----- habits -----
    def sync_habit(self, h: Habit) -> None:
        key = habit_key(h.id)
        if h.status == "active" and h.reminder_enabled and h.reminder_time:
            self.backend.schedule_daily(key, h.name, t("notif.habit_body"), h.reminder_time)
        else:
            self.backend.cancel(key)

    # ----- startup -----
    def resync_all(self) -> int:
        """Called at app start so reminders always match the database (e.g. after a restore)."""
        from app.services.commitment_service import CommitmentService
        from app.services.habit_service import HabitService
        count = 0
        for row in self.conn.execute("SELECT id FROM commitments WHERE reminder_enabled = 1"):
            item = CommitmentService(self.conn, None, self.now).get(row["id"])
            self.sync_commitment(item)
            count += 1
        for habit in HabitService(self.conn, None, self.now).list(include_archived=True):
            self.sync_habit(habit)
        return count

    # ----- in-app fallback (only fires while the app is open) -----
    def due_in_app(self) -> List[Commitment]:
        """Commitment reminders whose time has come and that were not shown yet."""
        from app.services.commitment_service import CommitmentService
        now_s = dates.to_dt_str(self.now())
        rows = self.conn.execute(
            "SELECT id FROM commitments WHERE status='open' AND reminder_enabled=1 "
            "AND reminder_at IS NOT NULL AND reminder_at <= ? AND reminder_sent_at IS NULL", (now_s,))
        svc = CommitmentService(self.conn, None, self.now)
        return [svc.get(r["id"]) for r in rows]

    def mark_shown(self, commitment_id: int) -> None:
        self.conn.execute("UPDATE commitments SET reminder_sent_at=? WHERE id=?",
                          (dates.to_ts(self.now()), commitment_id))

    # ----- diagnostics -----
    def send_test(self) -> bool:
        """Schedule a notification ~5 seconds from now. Returns True if the OS backend took it
        (False means the caller should show the in-app fallback instead)."""
        from datetime import timedelta
        if not self.backend.background:
            return False
        return bool(self.backend.schedule("test", t("notif.test_title"), t("notif.test_body"),
                                          self.now() + timedelta(seconds=5)))
