"""Optional demo data. Never added automatically; removable with remove_demo_data()."""
from datetime import timedelta

from app.database.db import transaction
from app.utils import dates


def add_demo_data(commitments, habits) -> int:
    """Adds a few clearly-marked sample rows. Returns how many rows were added."""
    now = commitments.now()
    today9 = now.replace(hour=9, minute=0)
    samples = [
        ("دفع فاتورة الكهرباء", "آخر موعد للسداد", now - timedelta(days=1), "high", "فواتير"),
        ("مراجعة مذكرة المحاضرة", "", now + timedelta(hours=3), "medium", "دراسة"),
        ("مكالمة مع الأهل", "", now + timedelta(days=1), "low", "عائلة"),
        ("تسليم المشروع", "رفع الملفات على المنصة", now + timedelta(days=4), "high", "دراسة"),
    ]
    added = 0
    for title, desc, due, prio, cat in samples:
        commitments.create(title, desc, due.replace(second=0), prio, cat, is_demo=True)
        added += 1
    done = commitments.create("حجز موعد الطبيب", "", today9 - timedelta(days=2), "medium", "صحة", is_demo=True)
    commitments.complete(done.id)
    added += 1

    h = habits.create("المشي 20 دقيقة", 15, is_demo=True, start_date=habits.today() - timedelta(days=6))
    for i in (6, 5, 4, 3, 2, 1):
        habits.record_day(h.id, habits.today() - timedelta(days=i), "success")
    added += 1
    h2 = habits.create("قراءة 10 صفحات", 15, is_demo=True, start_date=habits.today() - timedelta(days=4))
    for i, res in ((4, "success"), (3, "success"), (2, "setback"), (1, "success")):
        habits.record_day(h2.id, habits.today() - timedelta(days=i), res)
    added += 1
    return added


def remove_demo_data(conn, reminders=None) -> int:
    """Delete only rows flagged is_demo=1. Real user data is never touched."""
    ids = [r[0] for r in conn.execute("SELECT id FROM commitments WHERE is_demo = 1")]
    habit_ids = [r[0] for r in conn.execute("SELECT id FROM habits WHERE is_demo = 1")]
    with transaction(conn):
        conn.execute("DELETE FROM commitments WHERE is_demo = 1")
        conn.execute("DELETE FROM habits WHERE is_demo = 1")      # records cascade
    if reminders is not None:
        for i in ids:
            reminders.cancel_commitment(i)
        for i in habit_ids:
            reminders.backend.cancel(f"h{i}")
    return len(ids) + len(habit_ids)
