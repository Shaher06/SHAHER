"""Pure streak calculations (no database, easy to test).

Rules implemented here:
* Only a 'success' record counts as a successful day. An unrecorded day never counts.
* Consecutive means consecutive calendar days. A setback OR a gap breaks a streak.
* A setback never removes earlier successes: totals and the longest streak keep them.
* Today is never treated as missed before it has ended: if today has no record,
  the current streak simply continues from yesterday.
"""
from datetime import date, timedelta
from typing import Dict

from app.models.models import HabitStats


def compute_stats(records: Dict[date, str], today: date, target_days: int) -> HabitStats:
    success_days = sorted(d for d, r in records.items() if r == "success")
    total_setbacks = sum(1 for r in records.values() if r == "setback")

    longest = run = 0
    completed_on = None
    previous = None
    for d in success_days:
        run = run + 1 if previous is not None and d - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        if run >= target_days and completed_on is None:
            completed_on = d
        previous = d

    today_result = records.get(today)
    if today_result == "setback":
        current = 0
    else:
        cursor = today if today_result == "success" else today - timedelta(days=1)
        current = 0
        while records.get(cursor) == "success":
            current += 1
            cursor -= timedelta(days=1)

    return HabitStats(
        current_streak=current, longest_streak=longest,
        total_success=len(success_days), total_setbacks=total_setbacks,
        target_days=target_days, completed=longest >= target_days,
        completed_on=completed_on,
        today_state=today_result if today_result else "pending",
    )


def day_state(records: Dict[date, str], d: date, today: date) -> str:
    """'success' | 'setback' | 'missed' (past, unrecorded) | 'pending' (today, unrecorded)
    | 'future'.  'missed' is only a display state - nothing is written to the database."""
    if d > today:
        return "future"
    if d in records:
        return records[d]
    return "pending" if d == today else "missed"
