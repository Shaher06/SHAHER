import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.db import connect                         # noqa: E402
from app.services.commitment_service import CommitmentService  # noqa: E402
from app.services.habit_service import HabitService            # noqa: E402
from app.services.reminder_backends import ReminderBackend      # noqa: E402
from app.services.reminder_service import ReminderService       # noqa: E402


class Clock:
    """A clock the tests can move: clock.now() / clock.set(...)."""
    def __init__(self, start):
        self.current = start

    def now(self):
        return self.current

    def set(self, value):
        self.current = value


class FakeBackend(ReminderBackend):
    name = "fake"

    def __init__(self):
        self.scheduled, self.cancelled, self.daily = {}, [], {}

    def is_supported(self):
        return True

    def schedule(self, key, title, body, fire_at):
        self.scheduled[key] = (title, fire_at)
        return True

    def schedule_daily(self, key, title, body, hhmm):
        self.daily[key] = hhmm
        return True

    def cancel(self, key):
        self.scheduled.pop(key, None)
        self.daily.pop(key, None)
        self.cancelled.append(key)


@pytest.fixture
def clock():
    return Clock(datetime(2026, 10, 13, 12, 0, 0))     # Tuesday noon


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"          # a temp file - never the user's real database


@pytest.fixture
def conn(db_path):
    c = connect(db_path)
    yield c
    c.close()


@pytest.fixture
def backend():
    return FakeBackend()


@pytest.fixture
def reminders(conn, backend, clock):
    return ReminderService(conn, backend, clock.now)


@pytest.fixture
def commitments(conn, reminders, clock):
    return CommitmentService(conn, reminders, clock.now)


@pytest.fixture
def habits(conn, reminders, clock):
    return HabitService(conn, reminders, clock.now)
