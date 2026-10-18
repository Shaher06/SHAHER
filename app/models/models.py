"""Plain data classes returned by the services (no database code in here)."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.utils import dates


def _dt(value) -> Optional[datetime]:
    return dates.parse_dt(value) if value else None


@dataclass
class Commitment:
    id: int
    title: str
    description: str
    due_at: datetime
    priority: str            # 'low' | 'medium' | 'high'
    category: str
    status: str              # 'open' | 'completed' | 'archived'
    reminder_enabled: bool
    reminder_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    archived_at: Optional[datetime]
    is_demo: bool = False
    focus_date: Optional[date] = None

    @classmethod
    def from_row(cls, row) -> "Commitment":
        return cls(
            id=row["id"], title=row["title"], description=row["description"],
            due_at=_dt(row["due_at"]), priority=row["priority"], category=row["category"],
            status=row["status"], reminder_enabled=bool(row["reminder_enabled"]),
            reminder_at=_dt(row["reminder_at"]), created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]), completed_at=_dt(row["completed_at"]),
            archived_at=_dt(row["archived_at"]), is_demo=bool(row["is_demo"]),
            focus_date=dates.parse_date(row["focus_date"]) if row["focus_date"] else None,
        )

    def is_overdue(self, now: datetime) -> bool:
        return self.status == "open" and self.due_at < now


@dataclass
class Habit:
    id: int
    name: str
    start_date: date
    target_days: int
    reminder_enabled: bool
    reminder_time: Optional[str]   # 'HH:MM'
    status: str                    # 'active' | 'archived'
    created_at: datetime
    archived_at: Optional[datetime]
    is_demo: bool = False

    @classmethod
    def from_row(cls, row) -> "Habit":
        return cls(
            id=row["id"], name=row["name"], start_date=dates.parse_date(row["start_date"]),
            target_days=row["target_days"], reminder_enabled=bool(row["reminder_enabled"]),
            reminder_time=row["reminder_time"], status=row["status"],
            created_at=_dt(row["created_at"]), archived_at=_dt(row["archived_at"]),
            is_demo=bool(row["is_demo"]),
        )


@dataclass
class HabitRecord:
    id: int
    habit_id: int
    record_date: date
    result: str    # 'success' | 'setback'
    note: str

    @classmethod
    def from_row(cls, row) -> "HabitRecord":
        return cls(id=row["id"], habit_id=row["habit_id"],
                   record_date=dates.parse_date(row["record_date"]),
                   result=row["result"], note=row["note"])


@dataclass
class HabitStats:
    current_streak: int
    longest_streak: int
    total_success: int
    total_setbacks: int
    target_days: int
    completed: bool                 # a streak has reached the target
    completed_on: Optional[date]    # the day the target was first reached
    today_state: str                # 'success' | 'setback' | 'pending'

    @property
    def progress(self) -> float:
        """Progress of the CURRENT streak toward the target (0.0 - 1.0)."""
        return min(self.current_streak, self.target_days) / self.target_days
