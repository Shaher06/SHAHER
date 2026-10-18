"""Input validation. Errors carry translation keys (see app/i18n)."""
from datetime import datetime
from typing import List, Optional

from app.utils import dates

PRIORITY_KEYS = ("low", "medium", "high")


def priority_label(key):
    from app.i18n import t
    return t("prio." + key)


PRIORITIES = PRIORITY_KEYS

MAX_TITLE = 120
MAX_DESCRIPTION = 1000
MAX_CATEGORY = 40
MAX_NOTE = 300
MAX_TARGET_DAYS = 3650


class ValidationError(Exception):
    """One or more user-facing messages. Each item is a translation key, or (key, params).
    `.errors` returns them translated into the CURRENT language."""

    def __init__(self, errors):
        raw = [errors] if isinstance(errors, (str, tuple)) else list(errors)
        self.items = [(i, {}) if isinstance(i, str) else i for i in raw]
        super().__init__(" | ".join(k for k, _ in self.items))

    @property
    def errors(self) -> List[str]:
        from app.i18n import t
        return [t(k, **p) for k, p in self.items]

    def __str__(self):
        return "؛ ".join(self.errors)


def clean_text(value) -> str:
    return str(value or "").strip()


def validate_commitment(title, description, due_at, priority, category,
                        reminder_enabled, reminder_at) -> dict:
    """Returns cleaned values (datetimes stay datetimes) or raises ValidationError."""
    errors = []
    title = clean_text(title)
    description = clean_text(description)
    category = " ".join(clean_text(category).split())

    if not title:
        errors.append("err.title_required")
    elif len(title) > MAX_TITLE:
        errors.append(("err.title_long", {"n": MAX_TITLE}))
    if len(description) > MAX_DESCRIPTION:
        errors.append(("err.desc_long", {"n": MAX_DESCRIPTION}))
    if len(category) > MAX_CATEGORY:
        errors.append(("err.category_long", {"n": MAX_CATEGORY}))
    if priority not in PRIORITIES:
        errors.append("err.priority_invalid")
    if not isinstance(due_at, datetime):
        errors.append("err.due_required")
    if reminder_enabled and not isinstance(reminder_at, datetime):
        errors.append("err.reminder_time_required")
    if (isinstance(reminder_at, datetime) and isinstance(due_at, datetime)
            and reminder_enabled and reminder_at > due_at):
        errors.append("err.reminder_after_due")
    if errors:
        raise ValidationError(errors)
    return dict(title=title, description=description, due_at=due_at, priority=priority,
                category=category, reminder_enabled=bool(reminder_enabled),
                reminder_at=reminder_at if reminder_enabled else None)


def validate_habit(name, target_days, reminder_enabled, reminder_time) -> dict:
    errors = []
    name = clean_text(name)
    if not name:
        errors.append("err.habit_name_required")
    elif len(name) > MAX_TITLE:
        errors.append(("err.habit_name_long", {"n": MAX_TITLE}))
    try:
        target_days = int(dates.normalize_digits(str(target_days)))
        if not 1 <= target_days <= MAX_TARGET_DAYS:
            raise ValueError
    except (TypeError, ValueError):
        errors.append(("err.target_invalid", {"n": MAX_TARGET_DAYS}))
    cleaned_time: Optional[str] = None
    if reminder_enabled:
        try:
            cleaned_time = dates.parse_time(str(reminder_time)).strftime("%H:%M")
        except ValueError:
            errors.append("err.habit_time_invalid")
    if errors:
        raise ValidationError(errors)
    return dict(name=name, target_days=target_days,
                reminder_enabled=bool(reminder_enabled), reminder_time=cleaned_time)


def validate_note(note) -> str:
    note = clean_text(note)
    if len(note) > MAX_NOTE:
        raise ValidationError(("err.note_long", {"n": MAX_NOTE}))
    return note
