"""Date helpers.

Date convention (documented in README):
* Everything is stored in the device's LOCAL time, without a timezone.
* Dates are 'YYYY-MM-DD' and date+time values are 'YYYY-MM-DDTHH:MM'.
* A "day" for habits is the local calendar day, so streaks do not shift around
  midnight UTC. If the phone's timezone changes, the day boundary follows the phone.
"""
from datetime import date, datetime, timedelta

DATE_FMT = "%Y-%m-%d"
DT_FMT = "%Y-%m-%dT%H:%M"
TS_FMT = "%Y-%m-%dT%H:%M:%S"

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
          "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]  # Monday=0
MONTHS_EN = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _month(m):      # m = 1..12, in the current UI language
    from app import i18n
    return (MONTHS if i18n.language() == "ar" else MONTHS_EN)[m - 1]


def weekday_name(d, short=False):
    from app import i18n
    name = (WEEKDAYS if i18n.language() == "ar" else WEEKDAYS_EN)[d.weekday()]
    return name[:3] if (short and i18n.language() == "en") else name


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def normalize_digits(text: str) -> str:
    """Accept Arabic-Indic digits typed by the user."""
    return (text or "").translate(_DIGITS).strip()


def to_ts(dt: datetime) -> str:
    return dt.strftime(TS_FMT)


def to_dt_str(dt: datetime) -> str:
    return dt.strftime(DT_FMT)


def parse_dt(value: str) -> datetime:
    value = normalize_digits(value)
    for fmt in (DT_FMT, TS_FMT):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"bad datetime: {value!r}")


def parse_date(value: str) -> date:
    return datetime.strptime(normalize_digits(value), DATE_FMT).date()


def parse_time(value: str):
    """'18:30' or '9:5' -> datetime.time. Raises ValueError."""
    value = normalize_digits(value).replace("：", ":")
    return datetime.strptime(value, "%H:%M").time()


def combine(date_str: str, time_str: str) -> datetime:
    return datetime.combine(parse_date(date_str), parse_time(time_str))


def day_bounds(d: date):
    """(start, end) strings of a local day, for comparing with stored due_at values."""
    start = datetime.combine(d, datetime.min.time())
    return to_dt_str(start), to_dt_str(start + timedelta(days=1))


def date_range(start: date, end: date):
    """Inclusive list of dates."""
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def format_date(d: date) -> str:
    """Localized long date, e.g. 'الثلاثاء 13 أكتوبر 2026' / 'Tuesday, 13 October 2026'."""
    from app import i18n
    if i18n.language() == "ar":
        return f"{weekday_name(d)} {d.day} {_month(d.month)} {d.year}"
    return f"{weekday_name(d)}, {d.day} {_month(d.month)} {d.year}"


format_date_ar = format_date          # old name kept for compatibility


def format_short(d: date) -> str:
    return f"{d.day} {_month(d.month)}"


def format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def friendly_due(due: datetime, today: date) -> str:
    """'اليوم 18:30' / 'غدًا 09:00' / '15 أكتوبر 18:30' (localized)."""
    from app.i18n import t
    delta = (due.date() - today).days
    tm = format_time(due)
    key = {0: "due.today", 1: "due.tomorrow", -1: "due.yesterday"}.get(delta)
    if key:
        return f"{t(key)} {tm}"
    return f"{format_short(due.date())} {tm}"


def greeting_key(dt: datetime) -> str:
    return "greet.morning" if dt.hour < 12 else ("greet.afternoon" if dt.hour < 18 else "greet.evening")


def greeting(dt: datetime) -> str:
    from app.i18n import t
    return t(greeting_key(dt))
