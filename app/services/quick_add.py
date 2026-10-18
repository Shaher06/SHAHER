"""Quick Add: capture a commitment from just a title, using sensible defaults."""
from datetime import datetime, timedelta

from app.models.models import Commitment
from app.services.commitment_service import CommitmentService
from app.services.preferences import Preferences


def default_due(now: datetime) -> datetime:
    """Next full hour today; after 22:00 it becomes tomorrow 09:00."""
    due = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    if due.date() != now.date() or due.hour >= 23:
        due = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    return due


def default_reminder(prefs: Preferences, due: datetime, now: datetime):
    """(enabled, reminder_at) following the user's defaults; disabled if that moment is past."""
    if not prefs.flag("reminder_default_on"):
        return False, None
    at = due - timedelta(minutes=prefs.int("reminder_offset_minutes", 30))
    return (True, at) if at > now else (False, None)


def quick_add(commitments: CommitmentService, prefs: Preferences, title: str) -> Commitment:
    now = commitments.now()
    due = default_due(now)
    enabled, at = default_reminder(prefs, due, now)
    return commitments.create(title, "", due, prefs.get("default_priority"), "", enabled, at)
